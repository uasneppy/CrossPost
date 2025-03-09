#!/usr/bin/env python
import os
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, URL, Length
from dotenv import load_dotenv
from utils.storage import (
    get_channels, get_pending_channels, save_channels, save_pending_channels,
    approve_channel, reject_channel, remove_channel, get_channel_info,
    update_channel_schedule, update_channel_emojis
)

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

# Authentication middleware
def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != ADMIN_PASSWORD:
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

def authenticate():
    """Send a 401 response that enables basic auth."""
    return (
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials'
    ), 401, {'WWW-Authenticate': 'Basic realm="Login Required"', 'Content-Type': 'text/plain'}

# Forms
class ChannelForm(FlaskForm):
    title = StringField('Channel Name', validators=[DataRequired(), Length(min=3, max=100)])
    username = StringField('Channel Username', validators=[DataRequired(), Length(min=5, max=100)])
    channel_id = StringField('Channel ID', validators=[DataRequired()])
    url = StringField('Channel URL', validators=[DataRequired(), URL()])
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
    channels = get_channels()
    pending = get_pending_channels()
    return render_template('index.html', 
                           channels=channels, 
                           pending=pending, 
                           now=datetime.now())

@app.route('/channels')
@requires_auth
def list_channels():
    channels = get_channels()
    return render_template('channels.html', 
                           channels=channels,
                           title="Approved Channels")

@app.route('/channels/<channel_id>')
@requires_auth
def view_channel(channel_id):
    channel = get_channel_info(channel_id)
    if not channel:
        flash("Channel not found", "error")
        return redirect(url_for('list_channels'))
    
    return render_template('channel_detail.html', 
                           channel=channel,
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
        channel['url'] = form.url.data
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
    form.url.data = channel.get('url', '')
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
    if request.method == 'POST':
        if remove_channel(channel_id):
            flash("Channel removed successfully", "success")
        else:
            flash("Failed to remove channel", "error")
        return redirect(url_for('list_channels'))
    
    channel = get_channel_info(channel_id)
    if not channel:
        flash("Channel not found", "error")
        return redirect(url_for('list_channels'))
    
    return render_template('confirm_remove.html', 
                           channel=channel,
                           title=f"Remove Channel: {channel.get('title', channel.get('name', 'Unknown'))}")

@app.route('/pending')
@requires_auth
def list_pending():
    pending = get_pending_channels()
    return render_template('pending.html', 
                           pending=pending,
                           title="Pending Applications")

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
                           title=f"Pending: {channel.get('title', channel.get('name', 'Unknown'))}")

@app.route('/api/stats')
@requires_auth
def api_stats():
    channels = get_channels()
    pending = get_pending_channels()
    
    # Calculate statistics
    total_subscribers = sum(ch.get('subscribers', 0) for ch in channels.values())
    sfw_count = sum(1 for ch in channels.values() if ch.get('is_sfw', True))
    nsfw_count = sum(1 for ch in channels.values() if not ch.get('is_sfw', True))
    
    stats = {
        'total_channels': len(channels),
        'pending_applications': len(pending),
        'total_subscribers': total_subscribers,
        'sfw_channels': sfw_count,
        'nsfw_channels': nsfw_count
    }
    
    return jsonify(stats)

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Start server
    app.run(host='0.0.0.0', port=5000, debug=True)