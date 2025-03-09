#!/usr/bin/env python
import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort, g, send_file
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, URL, Length
from dotenv import load_dotenv
from utils.storage import (
    get_channels, get_pending_channels, save_channels, save_pending_channels,
    approve_channel, reject_channel, remove_channel, get_channel_info,
    update_channel_schedule, update_channel_emojis, is_channel_owner,
    get_user_channels
)
from utils.scheduler import schedule_immediate_crosspost
from utils.crosspost import update_all_channel_subscribers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/web.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if admin password is set
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    print("Warning: ADMIN_PASSWORD environment variable not set. Using default password 'admin'.")
    ADMIN_PASSWORD = "admin"

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())
csrf = CSRFProtect(app)

# Route to serve image files
@app.route('/generated-icon.png')
def serve_sfw_image():
    return send_file('generated-icon.png')

@app.route('/nsfw-icon.png')
def serve_nsfw_image():
    return send_file('nsfw-icon.png')

# Load admin user IDs from environment
ADMIN_USER_IDS = []
admin_ids_str = os.getenv("ADMIN_USER_IDS", "1336308262")  # Default to single admin user
for id_str in admin_ids_str.split(","):
    try:
        ADMIN_USER_IDS.append(int(id_str.strip()))
    except ValueError:
        print(f"Warning: Invalid admin user ID: {id_str}")

# Authentication middleware
def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != ADMIN_PASSWORD:
            return authenticate()
        
        # Store authenticated username as user_id in g object for access in views
        # This will be used for ownership checks across the application
        if auth.username and auth.username.isdigit():
            g.user_id = int(auth.username)
        else:
            # If username isn't a valid Telegram ID, use a placeholder
            # This enables admin accounts that aren't tied to a specific user
            g.user_id = None
            
        # IMPORTANT: All authenticated users have admin privileges in the web interface
        # Web interface is only for administrators, user-specific views are handled in Telegram
        g.is_admin = True
            
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

def authenticate():
    """Send a 401 response that enables basic auth."""
    response = app.make_response((
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials',
        401,
        {'Content-Type': 'text/plain'}
    ))
    response.headers['WWW-Authenticate'] = 'Basic realm="Login Required"'
    return response

# Forms
class ChannelForm(FlaskForm):
    title = StringField('Channel Name', validators=[DataRequired(), Length(min=3, max=100)])
    username = StringField('Channel Username', validators=[DataRequired(), Length(min=5, max=100)])
    channel_id = StringField('Channel ID', validators=[DataRequired()])
    emojis = StringField('Emojis (comma separated)', validators=[DataRequired()])
    is_nsfw = BooleanField('NSFW Content')
    subscribers = StringField('Subscriber Count')
    submit = SubmitField('Save Channel')

class PendingChannelForm(FlaskForm):
    approve = SubmitField('Approve')
    reject = SubmitField('Reject')

# Routes
@app.route('/')
@requires_auth
def index():
    # Always show all channels and pending applications - admin-only interface
    channels = get_channels()
    pending = get_pending_channels()
    title = "Admin Dashboard"
    
    logger.info(f"User {g.user_id} accessed admin dashboard with {len(channels)} channels and {len(pending)} pending applications")
    
    return render_template('index.html', 
                           channels=channels, 
                           pending=pending,
                           is_admin=True,
                           title=title,
                           now=datetime.now())

@app.route('/channels')
@requires_auth
def list_channels():
    # Always show all channels - admin-only interface
    channels = get_channels()
    title = "All Approved Channels"
        
    logger.info(f"User {g.user_id} listed {len(channels)} channels")
    
    return render_template('channels.html', 
                           channels=channels,
                           is_admin=True,
                           title=title)

@app.route('/channels/<channel_id>')
@requires_auth
def view_channel(channel_id):
    channel = get_channel_info(channel_id)
    if not channel:
        flash("Channel not found", "error")
        return redirect(url_for('list_channels'))
    
    return render_template('channel_detail.html', 
                           channel=channel,
                           is_owner=True,  # Admin always has owner privileges
                           is_admin=True,
                           title=f"Channel: {channel.get('title', channel.get('name', 'Unknown'))}")

@app.route('/channels/<channel_id>/edit', methods=['GET', 'POST'])
@requires_auth
def edit_channel(channel_id):
    channels = get_channels()
    if channel_id not in channels:
        flash("Channel not found", "error")
        return redirect(url_for('list_channels'))
    
    channel = channels[channel_id]
    form = ChannelForm(obj=None)
    
    if form.validate_on_submit():
        channel['title'] = form.title.data
        # Keep backward compatibility with 'name' field
        channel['name'] = form.title.data
        channel['username'] = form.username.data
        channel['is_sfw'] = not form.is_nsfw.data
        
        # Handle emojis
        if form.emojis.data:
            emojis = [e.strip() for e in form.emojis.data.split(',') if e.strip()]
            if emojis:
                update_channel_emojis(channel_id, emojis)
        
        # Try to convert subscribers to int if not empty
        if form.subscribers.data:
            try:
                channel['subscribers'] = int(form.subscribers.data)
            except ValueError:
                flash("Subscriber count must be a number", "error")
        
        if save_channels(channels):
            flash("Channel updated successfully", "success")
            return redirect(url_for('view_channel', channel_id=channel_id))
        else:
            flash("Failed to update channel", "error")
    
    # Pre-fill form
    form.title.data = channel.get('title', channel.get('name', ''))
    form.username.data = channel.get('username', '')
    form.channel_id.data = channel_id
    form.is_nsfw.data = not channel.get('is_sfw', True)
    form.subscribers.data = str(channel.get('subscribers', 0))
    form.emojis.data = ', '.join(channel.get('emojis', []))
    
    return render_template('channel_form.html', 
                           form=form, 
                           channel=channel,
                           title="Edit Channel")

@app.route('/channels/<channel_id>/schedule', methods=['GET', 'POST'])
@requires_auth
def edit_schedule(channel_id):
    channel = get_channel_info(channel_id)
    if not channel:
        flash("Channel not found", "error")
        return redirect(url_for('list_channels'))
        
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    schedule = channel.get('schedule', {})
    
    if request.method == 'POST':
        new_schedule = {}
        for i, day in enumerate(days):
            day_key = str(i)
            new_schedule[day_key] = day_key in request.form
            
        for day_idx, active in new_schedule.items():
            day_idx = int(day_idx)
            update_channel_schedule(channel_id, day_idx, active)
            
        flash("Schedule updated successfully", "success")
        return redirect(url_for('view_channel', channel_id=channel_id))
    
    return render_template('schedule_form.html', 
                           channel=channel,
                           schedule=schedule,
                           days=days,
                           title=f"Edit Schedule: {channel.get('title', channel.get('name', 'Unknown'))}")

@app.route('/channels/<channel_id>/remove', methods=['GET', 'POST'])
@requires_auth
def remove_channel_route(channel_id):
    channel = get_channel_info(channel_id)
    if not channel:
        flash("Channel not found", "error")
        return redirect(url_for('list_channels'))
    
    if request.method == 'POST':
        if remove_channel(channel_id):
            logger.info(f"Channel {channel_id} removed by user {g.user_id}")
            flash("Channel removed successfully", "success")
        else:
            logger.error(f"Failed to remove channel {channel_id}")
            flash("Failed to remove channel", "error")
        return redirect(url_for('list_channels'))
    
    return render_template('confirm_remove.html', 
                           channel=channel,
                           title=f"Remove Channel: {channel.get('title', channel.get('name', 'Unknown'))}")

@app.route('/pending')
@requires_auth
def list_pending():
    # Always show all pending channels - admin-only interface
    pending = get_pending_channels()
    title = "All Pending Applications"
    
    logger.info(f"User {g.user_id} listed {len(pending)} pending channels")
    
    return render_template('pending.html', 
                           pending=pending,
                           is_admin=True,
                           title=title)

@app.route('/pending/<channel_id>', methods=['GET', 'POST'])
@requires_auth
def view_pending(channel_id):
    pending = get_pending_channels()
    if channel_id not in pending:
        flash("Pending application not found", "error")
        return redirect(url_for('list_pending'))
    
    channel = pending[channel_id]
        
    form = PendingChannelForm()
    
    if form.validate_on_submit():
        if form.approve.data:
            if approve_channel(channel_id):
                flash(f"Channel {channel.get('title', channel.get('name', 'Unknown'))} approved", "success")
                return redirect(url_for('list_channels'))
            else:
                flash("Failed to approve channel", "error")
        elif form.reject.data:
            if reject_channel(channel_id):
                flash(f"Channel {channel.get('title', channel.get('name', 'Unknown'))} rejected", "success")
                return redirect(url_for('list_pending'))
            else:
                flash("Failed to reject channel", "error")
    
    return render_template('pending_detail.html', 
                           channel=channel,
                           form=form,
                           is_admin=True,
                           title=f"Pending: {channel.get('title', channel.get('name', 'Unknown'))}")

@app.route('/trigger_post')
@requires_auth
def trigger_post():
    """Trigger an immediate crosspost."""
    success = schedule_immediate_crosspost()
    
    if success:
        logger.info(f"User {g.user_id} triggered a manual crosspost")
        flash("Crosspost scheduled to run immediately", "success")
    else:
        logger.error("Failed to schedule crosspost - no active channels found")
        flash("Failed to schedule crosspost. No active channels found for today", "error")
    
    return redirect(url_for('index'))

@app.route('/update_subscribers')
@requires_auth
def update_subscribers():
    """Update subscriber counts for all channels."""
    try:
        update_all_channel_subscribers()
        logger.info(f"User {g.user_id} updated subscriber counts")
        flash("Subscriber counts updated successfully", "success")
    except Exception as e:
        logger.error(f"Error updating subscriber counts: {e}")
        flash(f"Failed to update subscriber counts: {str(e)}", "error")
    
    return redirect(url_for('index'))

@app.route('/manage_images', methods=['GET', 'POST'])
@requires_auth
def manage_images():
    """Manage post images for crossposting (SFW/NSFW)."""
    if request.method == 'POST':
        # Handle the image uploads
        sfw_image = request.files.get('sfw_image')
        nsfw_image = request.files.get('nsfw_image')
        
        if sfw_image and sfw_image.filename:
            sfw_image.save('generated-icon.png')
            flash("SFW image updated successfully", "success")
            logger.info(f"User {g.user_id} updated SFW image")
            
        if nsfw_image and nsfw_image.filename:
            nsfw_image.save('nsfw-icon.png')
            flash("NSFW image updated successfully", "success")
            logger.info(f"User {g.user_id} updated NSFW image")
            
        return redirect(url_for('manage_images'))
    
    # Check if current images exist
    sfw_exists = os.path.exists('generated-icon.png')
    nsfw_exists = os.path.exists('nsfw-icon.png')
    
    return render_template('manage_images.html', 
                          title="Manage Post Images",
                          sfw_exists=sfw_exists,
                          nsfw_exists=nsfw_exists)

@app.route('/api/stats')
@requires_auth
def api_stats():
    # Always show network-wide statistics - admin-only interface
    channels = get_channels()
    pending = get_pending_channels()
    stat_scope = "network"
    
    # Calculate statistics
    total_subscribers = sum(ch.get('subscribers', 0) for ch in channels.values())
    sfw_count = sum(1 for ch in channels.values() if ch.get('is_sfw', True))
    nsfw_count = sum(1 for ch in channels.values() if not ch.get('is_sfw', True))
    
    stats = {
        'total_channels': len(channels),
        'pending_applications': len(pending),
        'total_subscribers': total_subscribers,
        'sfw_channels': sfw_count,
        'nsfw_channels': nsfw_count,
        'scope': stat_scope,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"User {g.user_id} retrieved stats with scope: {stat_scope}")
    return jsonify(stats)

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Start server
    app.run(host='0.0.0.0', port=5000, debug=True)