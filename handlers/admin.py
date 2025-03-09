import logging
import os
from typing import Dict, List, Any, Optional

import telebot
from telebot import types

from bot import user_dict

import config
from utils import storage
from utils.scheduler import schedule_immediate_crosspost
from utils.crosspost import update_all_channel_subscribers

logger = logging.getLogger(__name__)

# Check if user is an admin
def is_admin(user_id: int) -> bool:
    """Check if a user is an admin."""
    return user_id in config.ADMIN_IDS

# Admin list command
def admin_list_command(message, bot, args=None):
    """List all channels or pending applications with subscriber counts."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "You don't have permission to use this command.")
        return
    
    # Check for arguments
    show_pending = False
    if args and len(args) > 0 and args[0].lower() == "pending":
        show_pending = True
    
    if show_pending:
        channels = storage.get_pending_channels()
        title = "Pending Channel Applications"
    else:
        channels = storage.get_channels()
        title = "Approved Channels"
    
    if not channels:
        bot.reply_to(message, f"No {title.lower()} found.")
        return
    
    # For approved channels, we'll include buttons for each channel
    # For pending channels, we'll include approval/rejection buttons
    if show_pending:
        # Create a message with inline keyboard for pending channels
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        loading_message = bot.reply_to(message, f"Loading {title.lower()}...")
        
        # Prepare the message text
        message_text = f"*{title}*\n\n"
        
        # Add buttons for each channel
        for idx, (channel_id, channel_data) in enumerate(channels.items(), 1):
            title = channel_data.get("title", "Unknown")
            username = channel_data.get("username", "")
            emojis = " ".join(channel_data.get("emojis", []))
            is_sfw_bool = channel_data.get("is_sfw", True)
            is_sfw = "SFW" if is_sfw_bool else "NSFW"
            is_sfw_icon = "✅" if is_sfw_bool else "🔞"
            
            # Try to get subscriber count (may fail for pending channels)
            try:
                from utils.crosspost import get_channel_subscriber_count
                subscriber_count = get_channel_subscriber_count(channel_id)
                subscriber_text = f"📊 {subscriber_count:,} subscribers"
            except Exception as e:
                logger.error(f"Error getting subscriber count: {e}")
                subscriber_text = "📊 Unknown subscribers"
            
            message_text += f"{idx}. *{title}* {is_sfw_icon}\n"
            message_text += f"   ID: `{channel_id}`\n"
            if username:
                message_text += f"   Username: @{username}\n"
            message_text += f"   Type: {is_sfw} {is_sfw_icon}\n"
            message_text += f"   {subscriber_text}\n"
            if emojis:
                message_text += f"   Emojis: {emojis}\n"
            message_text += "\n"
            
            # Add approve/reject buttons for each channel
            approve_button = types.InlineKeyboardButton(
                "✅ Approve", 
                callback_data=f"approve_{channel_id}"
            )
            reject_button = types.InlineKeyboardButton(
                "❌ Reject", 
                callback_data=f"reject_{channel_id}"
            )
            markup.add(approve_button, reject_button)
        
        # Add a back button to return to admin panel
        markup.add(types.InlineKeyboardButton(
            "« Back to Admin Panel", 
            callback_data="admin_back"
        ))
        
        # Delete the loading message and send the actual response
        bot.delete_message(loading_message.chat.id, loading_message.message_id)
        bot.reply_to(message, message_text, parse_mode="Markdown", reply_markup=markup)
    else:
        # For approved channels, just show a list with details and subscriber counts
        loading_message = bot.reply_to(message, f"Loading {title.lower()} and subscriber counts...")
        
        # Prepare the message text
        message_text = f"*{title}*\n\n"
        
        # Create a separate markup for action buttons
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for idx, (channel_id, channel_data) in enumerate(channels.items(), 1):
            title = channel_data.get("title", "Unknown")
            username = channel_data.get("username", "")
            emojis = " ".join(channel_data.get("emojis", []))
            is_sfw_bool = channel_data.get("is_sfw", True)
            is_sfw = "SFW" if is_sfw_bool else "NSFW"
            is_sfw_icon = "✅" if is_sfw_bool else "🔞"
            
            # Try to get subscriber count
            try:
                from utils.crosspost import get_channel_subscriber_count
                subscriber_count = get_channel_subscriber_count(channel_id)
                subscriber_text = f"📊 {subscriber_count:,} subscribers"
            except Exception as e:
                logger.error(f"Error getting subscriber count: {e}")
                subscriber_text = "📊 Unknown subscribers"
            
            message_text += f"{idx}. *{title}* {is_sfw_icon}\n"
            message_text += f"   ID: `{channel_id}`\n"
            if username:
                message_text += f"   Username: @{username}\n"
            message_text += f"   Type: {is_sfw} {is_sfw_icon}\n"
            message_text += f"   {subscriber_text}\n"
            if emojis:
                message_text += f"   Emojis: {emojis}\n"
            message_text += "\n"
            
            # Add a detailed view button for each channel
            markup.add(types.InlineKeyboardButton(
                f"Manage {title}", 
                callback_data=f"manage_{channel_id}"
            ))
        
        # Add buttons to view pending channels and go back to admin panel
        markup.add(types.InlineKeyboardButton(
            "View Pending Applications", 
            callback_data="view_pending"
        ))
        
        # Add a back button to return to the admin panel
        markup.add(types.InlineKeyboardButton(
            "« Back to Admin Panel", 
            callback_data="admin_back"
        ))
        
        # Delete the loading message and send the actual response
        bot.delete_message(loading_message.chat.id, loading_message.message_id)
        bot.reply_to(message, message_text, parse_mode="Markdown", reply_markup=markup)

# Admin approve command
def admin_approve_command(message, bot):
    """Start the process of approving a pending channel."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "You don't have permission to use this command.")
        return
    
    # Get pending channels
    pending_channels = storage.get_pending_channels()
    
    if not pending_channels:
        bot.reply_to(message, "No pending channel applications found.")
        return
    
    # Create inline keyboard with pending channels
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for channel_id, channel_data in pending_channels.items():
        title = channel_data.get("title", "Unknown")
        button_text = f"{title} ({channel_id})"
        markup.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"approve_{channel_id}"
        ))
    
    bot.reply_to(message, "Select a channel to approve:", reply_markup=markup)

# Admin reject command
def admin_reject_command(message, bot):
    """Start the process of rejecting a pending channel."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "You don't have permission to use this command.")
        return
    
    # Get pending channels
    pending_channels = storage.get_pending_channels()
    
    if not pending_channels:
        bot.reply_to(message, "No pending channel applications found.")
        return
    
    # Create inline keyboard with pending channels
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for channel_id, channel_data in pending_channels.items():
        title = channel_data.get("title", "Unknown")
        button_text = f"{title} ({channel_id})"
        markup.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"reject_{channel_id}"
        ))
    
    bot.reply_to(message, "Select a channel to reject:", reply_markup=markup)

# Admin remove command
def admin_remove_command(message, bot):
    """Start the process of removing an approved channel."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "You don't have permission to use this command.")
        return
    
    # Get approved channels
    approved_channels = storage.get_channels()
    
    if not approved_channels:
        bot.reply_to(message, "No approved channels found.")
        return
    
    # Create inline keyboard with approved channels
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for channel_id, channel_data in approved_channels.items():
        title = channel_data.get("title", "Unknown")
        button_text = f"{title} ({channel_id})"
        markup.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"remove_{channel_id}"
        ))
    
    bot.reply_to(message, "Select a channel to remove:", reply_markup=markup)

# Admin post command
def admin_post_command(message, bot):
    """Manually trigger a crosspost."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "You don't have permission to use this command.")
        return
    
    success = schedule_immediate_crosspost()
    
    if success:
        bot.reply_to(message, "Crosspost scheduled to run immediately.")
    else:
        bot.reply_to(message, "Failed to schedule crosspost. No active channels found.")

# Admin update subscribers command
def admin_update_subscribers_command(message, bot):
    """Manually update subscriber counts for all channels."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "You don't have permission to use this command.")
        return
    
    loading_message = bot.reply_to(message, "Updating subscriber counts for all channels...")
    
    try:
        # Run the update function
        update_all_channel_subscribers()
        
        # Confirm completion
        bot.edit_message_text(
            "✅ Subscriber counts updated successfully for all channels!",
            loading_message.chat.id,
            loading_message.message_id
        )
    except Exception as e:
        logger.error(f"Error updating subscriber counts: {e}")
        bot.edit_message_text(
            f"❌ Error updating subscriber counts: {str(e)}",
            loading_message.chat.id,
            loading_message.message_id
        )

# Admin stats command
def admin_stats_command(message, bot):
    """View network statistics."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "You don't have permission to use this command.")
        return
    
    approved_channels = storage.get_channels()
    pending_channels = storage.get_pending_channels()
    
    sfw_count = sum(1 for c in approved_channels.values() if c.get("is_sfw", True))
    nsfw_count = len(approved_channels) - sfw_count
    
    stats = (
        "*Network Statistics*\n\n"
        f"Total approved channels: {len(approved_channels)}\n"
        f"SFW channels: {sfw_count}\n"
        f"NSFW channels: {nsfw_count}\n"
        f"Pending applications: {len(pending_channels)}\n"
    )
    
    # Create markup with buttons to view channels and back to admin panel
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("View Approved Channels", callback_data="view_approved"),
        types.InlineKeyboardButton("View Pending Applications", callback_data="view_pending"),
        types.InlineKeyboardButton("« Back to Admin Panel", callback_data="admin_back")
    )
    
    bot.reply_to(message, stats, parse_mode="Markdown", reply_markup=markup)

# Admin callback handler
def admin_callback_handler(call, bot):
    """Handle callbacks for admin actions."""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "You don't have permission to perform this action.")
        return
    
    # Parse the callback data
    data = call.data
    logger.info(f"Admin callback: {data}")
    
    if data.startswith("approve_"):
        channel_id = data[len("approve_"):]
        # Get channel info before approval
        channel_data = storage.get_pending_channels().get(channel_id, {})
        channel_title = channel_data.get("title", "Unknown")
        
        if storage.approve_channel(channel_id):
            success_message = (
                f"✅ Channel *{channel_title}* has been approved!\n\n"
                f"It will now be included in crossposting."
            )
            bot.edit_message_text(
                success_message,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Channel approved!")
            
            # Show an updated list of pending applications
            pending_channels = storage.get_pending_channels()
            if pending_channels:
                # Create a new message with updated list
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton(
                    "View Pending Applications", 
                    callback_data="view_pending"
                ))
                markup.add(types.InlineKeyboardButton(
                    "View Approved Channels", 
                    callback_data="view_approved"
                ))
                markup.add(types.InlineKeyboardButton("« Back to Admin Panel", callback_data="admin_back"))
                
                bot.send_message(
                    call.message.chat.id,
                    f"There are {len(pending_channels)} pending applications remaining.",
                    reply_markup=markup
                )
        else:
            bot.edit_message_text(
                f"❌ Failed to approve channel *{channel_title}*.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Failed to approve channel!")
    
    elif data.startswith("reject_"):
        channel_id = data[len("reject_"):]
        # Get channel info before rejection
        channel_data = storage.get_pending_channels().get(channel_id, {})
        channel_title = channel_data.get("title", "Unknown")
        
        if storage.reject_channel(channel_id):
            success_message = (
                f"❌ Channel *{channel_title}* has been rejected.\n\n"
                f"The application has been removed from the pending list."
            )
            bot.edit_message_text(
                success_message,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Channel rejected!")
            
            # Show an updated list of pending applications
            pending_channels = storage.get_pending_channels()
            if pending_channels:
                # Create a new message with updated list
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton(
                    "View Pending Applications", 
                    callback_data="view_pending"
                ))
                markup.add(types.InlineKeyboardButton(
                    "View Approved Channels", 
                    callback_data="view_approved"
                ))
                markup.add(types.InlineKeyboardButton("« Back to Admin Panel", callback_data="admin_back"))
                
                bot.send_message(
                    call.message.chat.id,
                    f"There are {len(pending_channels)} pending applications remaining.",
                    reply_markup=markup
                )
        else:
            bot.edit_message_text(
                f"Failed to reject channel *{channel_title}*.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Failed to reject channel!")
    
    elif data.startswith("remove_"):
        channel_id = data[len("remove_"):]
        # Get channel info before removal
        channel_data = storage.get_channels().get(channel_id, {})
        channel_title = channel_data.get("title", "Unknown")
        
        if storage.remove_channel(channel_id):
            success_message = (
                f"🗑️ Channel *{channel_title}* has been removed from the network.\n\n"
                f"It will no longer be included in crossposting."
            )
            bot.edit_message_text(
                success_message,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Channel removed!")
            
            # Show an updated list of approved channels
            approved_channels = storage.get_channels()
            if approved_channels:
                # Create a new message with updated list
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton(
                    "View Approved Channels", 
                    callback_data="view_approved"
                ))
                markup.add(types.InlineKeyboardButton("« Back to Admin Panel", callback_data="admin_back"))
                markup.add(types.InlineKeyboardButton(
                    "View Pending Applications", 
                    callback_data="view_pending"
                ))
                
                bot.send_message(
                    call.message.chat.id,
                    f"There are {len(approved_channels)} approved channels remaining.",
                    reply_markup=markup
                )
        else:
            bot.edit_message_text(
                f"Failed to remove channel *{channel_title}*.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Failed to remove channel!")
            
    elif data == "view_pending":
        # Show pending applications
        bot.answer_callback_query(call.id, "Loading pending applications...")
        # Create a fake message object to reuse the admin_list_command
        fake_message = types.Message(
            message_id=call.message.message_id,
            from_user=call.from_user,
            date=call.message.date,
            chat=call.message.chat,
            content_type="text",
            options={},
            json_string=""
        )
        # Call the list command with "pending" argument
        admin_list_command(fake_message, bot, ["pending"])
        
    elif data == "view_approved":
        # Show approved channels
        bot.answer_callback_query(call.id, "Loading approved channels...")
        # Create a fake message object to reuse the admin_list_command
        fake_message = types.Message(
            message_id=call.message.message_id,
            from_user=call.from_user,
            date=call.message.date,
            chat=call.message.chat,
            content_type="text",
            options={},
            json_string=""
        )
        # Call the list command without arguments to show approved channels
        admin_list_command(fake_message, bot)
        
    elif data == "view_stats":
        # Show network statistics
        bot.answer_callback_query(call.id, "Loading network statistics...")
        # Create a fake message object to reuse the admin_stats_command
        fake_message = types.Message(
            message_id=call.message.message_id,
            from_user=call.from_user,
            date=call.message.date,
            chat=call.message.chat,
            content_type="text",
            options={},
            json_string=""
        )
        # Call the stats command
        admin_stats_command(fake_message, bot)
        
    elif data == "update_subscribers":
        # Manually update subscriber counts
        logger.info("Admin callback: update_subscribers")
        bot.answer_callback_query(call.id, "Starting subscriber count update...")
        
        # Display processing message
        processing_message = bot.send_message(
            call.message.chat.id,
            "🔄 Updating subscriber counts for all channels, please wait..."
        )
        
        try:
            # Execute the update function
            update_all_channel_subscribers()
            
            # Update the processing message
            bot.edit_message_text(
                "✅ Subscriber counts updated successfully for all channels!",
                call.message.chat.id,
                processing_message.message_id
            )
            logger.info("Manual subscriber count update completed successfully")
            
            # Return to admin panel after a short delay
            import time
            time.sleep(2)
            
            # Show admin panel
            markup = create_admin_markup()
            bot.send_message(
                call.message.chat.id,
                "*Admin Control Panel*\n\nSelect an option to manage your channel network:",
                parse_mode="Markdown",
                reply_markup=markup
            )
            
        except Exception as e:
            # Update the processing message with error
            error_message = f"❌ Error updating subscriber counts: {str(e)}"
            bot.edit_message_text(
                error_message,
                call.message.chat.id,
                processing_message.message_id
            )
            logger.error(f"Manual subscriber count update failed: {e}")
        
    elif data == "trigger_post":
        # Trigger a manual crosspost
        logger.info("Admin callback: trigger_post")
        bot.answer_callback_query(call.id, "Starting manual crosspost...")
        
        # Display processing message
        processing_message = bot.send_message(
            call.message.chat.id,
            "🔄 Processing manual crosspost, please wait..."
        )
        
        # Execute the crosspost
        success = schedule_immediate_crosspost()
        
        if success:
            # Update the processing message
            bot.edit_message_text(
                "✅ Crosspost completed successfully.",
                call.message.chat.id,
                processing_message.message_id
            )
            logger.info("Manual crosspost completed successfully")
        else:
            # Update the processing message with error
            bot.edit_message_text(
                "❌ Failed to execute crosspost. No active channels found or error occurred.",
                call.message.chat.id,
                processing_message.message_id
            )
            logger.warning("Manual crosspost failed")
    
    elif data == "manage_images":
        # Show image management options
        logger.info("Admin callback: manage_images")
        bot.answer_callback_query(call.id, "Loading image management...")
        
        # Create a keyboard with options for SFW and NSFW images
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Upload SFW Image ✅", callback_data="upload_sfw_image"),
            types.InlineKeyboardButton("Upload NSFW Image 🔞", callback_data="upload_nsfw_image"),
            types.InlineKeyboardButton("« Back to Admin Panel", callback_data="admin_back")
        )
        
        # Show current images
        sfw_image_path = "generated-icon.png"
        nsfw_image_path = "nsfw-icon.png"
        
        sfw_status = "✅ Available" if os.path.exists(sfw_image_path) else "❌ Not set"
        nsfw_status = "✅ Available" if os.path.exists(nsfw_image_path) else "❌ Not set"
        
        message_text = (
            "*Manage Post Images*\n\n"
            f"SFW Image: {sfw_status}\n"
            f"NSFW Image: {nsfw_status}\n\n"
            "Select an option to upload a new image:"
        )
        
        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    elif data == "upload_sfw_image" or data == "upload_nsfw_image":
        # Set the state to wait for an image upload
        image_type = "SFW" if data == "upload_sfw_image" else "NSFW"
        logger.info(f"Admin selected to upload {image_type} image")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("« Cancel", callback_data="manage_images"))
        
        bot.edit_message_text(
            f"*Upload {image_type} Image*\n\n"
            f"Please send a new image for {image_type} crossposting.\n\n"
            "The image should be:\n"
            "- Square or nearly square aspect ratio\n"
            "- Less than 1MB in size\n"
            "- JPG or PNG format\n\n"
            "Note: This will require sending a new message - use the Cancel button to go back.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        # Store the image type in user_dict for this user
        user_id = str(call.from_user.id)
        from bot import user_dict
        user_dict[user_id] = {"waiting_for_image": image_type}
        
        bot.answer_callback_query(call.id, f"Send a {image_type} image")
    
    elif data == "admin_back":
        # Go back to admin panel
        logger.info("Admin callback: admin_back - returning to admin panel")
        bot.answer_callback_query(call.id, "Returning to admin panel...")
        
        # Show admin panel directly instead of calling the handler
        markup = create_admin_markup()
        
        try:
            bot.edit_message_text(
                "*Admin Control Panel*\n\nSelect an option to manage your channel network:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            logger.info("Admin panel markup displayed successfully")
        except Exception as e:
            logger.error(f"Error displaying admin panel: {e}")
            # Try sending a new message instead
            bot.send_message(
                call.message.chat.id,
                "*Admin Control Panel*\n\nSelect an option to manage your channel network:",
                parse_mode="Markdown",
                reply_markup=markup
            )
    
    elif data.startswith("manage_"):
        channel_id = data[len("manage_"):]
        # Get channel info
        channel_data = storage.get_channels().get(channel_id, {})
        
        if not channel_data:
            bot.answer_callback_query(call.id, "Channel not found!")
            return
            
        channel_title = channel_data.get("title", "Unknown")
        channel_username = channel_data.get("username", "")
        channel_emojis = " ".join(channel_data.get("emojis", []))
        is_sfw_bool = channel_data.get("is_sfw", True)
        is_sfw = "SFW" if is_sfw_bool else "NSFW"
        is_sfw_icon = "✅" if is_sfw_bool else "🔞"
        
        # Try to get subscriber count
        try:
            from utils.crosspost import get_channel_subscriber_count
            subscriber_count = get_channel_subscriber_count(channel_id)
            subscriber_text = f"📊 {subscriber_count:,} subscribers"
        except Exception as e:
            logger.error(f"Error getting subscriber count: {e}")
            subscriber_text = "📊 Unknown subscribers"
        
        # Get channel schedule
        schedule = channel_data.get("schedule", {})
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule_text = "📅 Schedule:\n"
        for day_idx, day_name in enumerate(weekdays):
            active = schedule.get(str(day_idx), False)
            status = "✅" if active else "❌"
            schedule_text += f"   {status} {day_name}\n"
        
        # Create inline keyboard with management options
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Toggle SFW/NSFW button with more prominent icon
        toggle_icon = "🔞" if is_sfw == "SFW" else "✅"
        toggle_sfw_text = f"{toggle_icon} Change to NSFW" if is_sfw == "SFW" else f"{toggle_icon} Change to SFW"
        markup.add(types.InlineKeyboardButton(
            toggle_sfw_text, 
            callback_data=f"toggle_sfw_{channel_id}"
        ))
        
        # Edit emojis button
        markup.add(types.InlineKeyboardButton(
            "Edit Emojis", 
            callback_data=f"edit_emojis_{channel_id}"
        ))
        
        # Edit schedule button
        markup.add(types.InlineKeyboardButton(
            "Edit Schedule", 
            callback_data=f"edit_schedule_{channel_id}"
        ))
        
        # Set reserved position button
        markup.add(types.InlineKeyboardButton(
            "🔢 Set Reserved Position", 
            callback_data=f"set_position_{channel_id}"
        ))
        
        # Remove channel button
        markup.add(types.InlineKeyboardButton(
            "🗑️ Remove Channel", 
            callback_data=f"remove_{channel_id}"
        ))
        
        # Back button
        markup.add(types.InlineKeyboardButton(
            "« Back to Channels List", 
            callback_data="view_approved"
        ))
        
        # Format the channel details message
        message_text = (
            f"*Channel Management: {channel_title}*\n\n"
            f"ID: `{channel_id}`\n"
        )
        
        if channel_username:
            message_text += f"Username: @{channel_username}\n"
            
        message_text += f"Type: {is_sfw} {is_sfw_icon}\n"
        message_text += f"{subscriber_text}\n"
        
        # Add reserved position info if present
        if "reserved_position" in channel_data and channel_data["reserved_position"] > 0:
            message_text += f"🔢 Reserved Position: {channel_data['reserved_position']}\n"
        
        if channel_emojis:
            message_text += f"Emojis: {channel_emojis}\n"
            
        message_text += f"\n{schedule_text}"
        
        # Send the message with the management options
        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        
    elif data.startswith("toggle_sfw_"):
        channel_id = data[len("toggle_sfw_"):]
        logger.info(f"Admin toggling SFW status for channel: {channel_id}")
        
        # Get current channel data
        channels = storage.get_channels()
        if channel_id not in channels:
            logger.warning(f"Channel not found when toggling SFW status: {channel_id}")
            bot.answer_callback_query(call.id, "Channel not found!")
            return
            
        channel_data = channels[channel_id]
        channel_title = channel_data.get("title", "Unknown")
        is_currently_sfw = channel_data.get("is_sfw", True)
        old_status = "SFW" if is_currently_sfw else "NSFW"
        
        # Toggle SFW status
        channel_data["is_sfw"] = not is_currently_sfw
        new_status = "SFW" if channel_data["is_sfw"] else "NSFW"
        
        logger.info(f"Changing channel '{channel_title}' ({channel_id}) from {old_status} to {new_status}")
        
        # Save updated channel data
        channels[channel_id] = channel_data
        success = storage.save_channels(channels)
        
        if success:
            # Show confirmation popup
            bot.answer_callback_query(
                call.id, 
                f"✓ Channel '{channel_title}' is now {new_status}",
                show_alert=True
            )
            
            # Notify in chat window
            status_icon = "✅" if new_status == "SFW" else "🔞"
            notification_message = bot.send_message(
                call.message.chat.id,
                f"✓ Successfully changed *{channel_title}* from {old_status} to *{new_status}* {status_icon}",
                parse_mode="Markdown"
            )
            
            # Auto-delete notification after 5 seconds
            # This would normally use threading.Timer, but we'll skip that for simplicity
            
            logger.info(f"Successfully updated channel {channel_id} to {new_status}")
            
            # Refresh the channel management view
            fake_callback = types.CallbackQuery(
                id=call.id,
                from_user=call.from_user,
                message=call.message,
                chat_instance=call.chat_instance,
                data=f"manage_{channel_id}",
                json_string=""
            )
            admin_callback_handler(fake_callback, bot)
        else:
            logger.error(f"Failed to save channel {channel_id} when toggling SFW status")
            bot.answer_callback_query(
                call.id, 
                "Failed to update channel status! Check server logs.",
                show_alert=True
            )
    
    elif data.startswith("edit_schedule_"):
        channel_id = data[len("edit_schedule_"):]
        
        # Get current channel data
        channels = storage.get_channels()
        if channel_id not in channels:
            bot.answer_callback_query(call.id, "Channel not found!")
            return
            
        channel_data = channels[channel_id]
        channel_title = channel_data.get("title", "Unknown")
        schedule = channel_data.get("schedule", {})
        
        # Create a keyboard with toggle buttons for each day
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day_idx, day_name in enumerate(weekdays):
            active = schedule.get(str(day_idx), False)
            status = "✅" if active else "❌"
            
            markup.add(types.InlineKeyboardButton(
                f"{status} {day_name}",
                callback_data=f"toggle_day_{channel_id}_{day_idx}"
            ))
        
        # Add a back button
        markup.add(types.InlineKeyboardButton(
            "« Back to Channel Details",
            callback_data=f"manage_{channel_id}"
        ))
        
        # Send the schedule edit message
        bot.edit_message_text(
            f"*Edit Schedule for {channel_title}*\n\n"
            "Select days to toggle active/inactive status for crossposting:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        
    elif data.startswith("toggle_day_"):
        # Format: toggle_day_<channel_id>_<day_idx>
        parts = data.split("_")
        if len(parts) != 4:
            bot.answer_callback_query(call.id, "Invalid callback data!")
            return
            
        channel_id = parts[2]
        day_idx = int(parts[3])
        
        # Toggle the schedule for this day
        success = storage.update_channel_schedule(channel_id, day_idx, None)  # None means toggle
        
        if success:
            bot.answer_callback_query(call.id, "Schedule updated!")
            
            # Refresh the schedule view
            fake_callback = types.CallbackQuery(
                id=call.id,
                from_user=call.from_user,
                message=call.message,
                chat_instance=call.chat_instance,
                data=f"edit_schedule_{channel_id}",
                json_string=""
            )
            admin_callback_handler(fake_callback, bot)
        else:
            bot.answer_callback_query(call.id, "Failed to update schedule!")
            
    elif data.startswith("edit_emojis_"):
        channel_id = data[len("edit_emojis_"):]
        
        # Get current channel data
        channels = storage.get_channels()
        if channel_id not in channels:
            bot.answer_callback_query(call.id, "Channel not found!")
            return
            
        channel_data = channels[channel_id]
        channel_title = channel_data.get("title", "Unknown")
        current_emojis = channel_data.get("emojis", [])
        
        # Create a message asking the user to enter new emojis
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "« Cancel",
            callback_data=f"manage_{channel_id}"
        ))
        
        # This will require the user to reply with emojis
        # We'll need to add a state handler for this
        bot.edit_message_text(
            f"*Edit Emojis for {channel_title}*\n\n"
            f"Current emojis: {' '.join(current_emojis)}\n\n"
            "Please send 3 new emojis in a message below.\n"
            "Example: 🇺🇦 💻 🎮\n\n"
            "Note: This functionality requires sending a new message - use the Cancel button to go back.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        # Save the channel ID for later processing
        # We would need to add a state system for admin operations
        # This is just a placeholder - actual implementation would need state management
        bot.answer_callback_query(call.id, "Please send new emojis in a message")
        
        # For now, this is not fully implemented since it requires state handling for admin operations
        # In a full implementation, we would add a state handler for emoji messages
    
    elif data.startswith("set_position_"):
        channel_id = data[len("set_position_"):]
        
        # Get current channel data
        channels = storage.get_channels()
        if channel_id not in channels:
            bot.answer_callback_query(call.id, "Channel not found!")
            return
            
        channel_data = channels[channel_id]
        channel_title = channel_data.get("title", "Unknown")
        is_sfw = channel_data.get("is_sfw", True)
        current_position = channel_data.get("reserved_position", 0)
        
        # Create buttons for positions 1-10 and a clear option
        markup = types.InlineKeyboardMarkup(row_width=5)
        
        # First row - positions 1-5
        position_buttons_1 = []
        for i in range(1, 6):
            # Highlight the current position
            btn_text = f"[{i}]" if current_position == i else f"{i}"
            position_buttons_1.append(types.InlineKeyboardButton(
                btn_text, callback_data=f"save_position_{channel_id}_{i}"
            ))
        markup.add(*position_buttons_1)
        
        # Second row - positions 6-10
        position_buttons_2 = []
        for i in range(6, 11):
            # Highlight the current position
            btn_text = f"[{i}]" if current_position == i else f"{i}"
            position_buttons_2.append(types.InlineKeyboardButton(
                btn_text, callback_data=f"save_position_{channel_id}_{i}"
            ))
        markup.add(*position_buttons_2)
        
        # Clear button - remove reserved position
        markup.add(types.InlineKeyboardButton(
            "Clear Reserved Position", 
            callback_data=f"save_position_{channel_id}_0"
        ))
        
        # Back button
        markup.add(types.InlineKeyboardButton(
            "« Back to Channel Details", 
            callback_data=f"manage_{channel_id}"
        ))
        
        # Determine what type of content this is for (SFW or NSFW)
        content_type = "SFW ✅" if is_sfw else "NSFW 🔞"
        
        # Display the position selection UI
        bot.edit_message_text(
            f"*Set Reserved Position for {channel_title}*\n\n"
            f"Channel Type: {content_type}\n"
            f"Current Reserved Position: {current_position if current_position > 0 else 'None'}\n\n"
            "Select a position (1-10) to reserve for this channel in the crosspost list:\n"
            "• Positions 1-5 are typically for channels with fewer subscribers\n"
            "• Positions 6-10 are typically for channels with more subscribers\n\n"
            "A reserved position guarantees this channel will appear in that specific position in the crosspost.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id, "Select a position")
        
    elif data.startswith("save_position_"):
        # Format: save_position_<channel_id>_<position>
        parts = data.split("_")
        if len(parts) != 4:
            bot.answer_callback_query(call.id, "Invalid callback data!")
            return
            
        channel_id = parts[2]
        position = int(parts[3])
        
        # Get channel info before update
        channel_data = storage.get_channels().get(channel_id, {})
        channel_title = channel_data.get("title", "Unknown")
        
        # Set the reserved position
        success = storage.set_channel_reserved_position(channel_id, position)
        
        if success:
            if position == 0:
                feedback = f"Cleared reserved position for {channel_title}"
                bot.answer_callback_query(call.id, feedback)
            else:
                feedback = f"Set reserved position {position} for {channel_title}"
                bot.answer_callback_query(call.id, feedback)
                
            # Send a notification message
            if position == 0:
                notification = f"✓ Cleared reserved position for *{channel_title}*"
            else:
                notification = f"✓ Reserved position *{position}* for *{channel_title}*"
                
            bot.send_message(
                call.message.chat.id,
                notification,
                parse_mode="Markdown"
            )
            
            # Return to channel management screen
            fake_callback = types.CallbackQuery(
                id=call.id,
                from_user=call.from_user,
                message=call.message,
                chat_instance=call.chat_instance,
                data=f"manage_{channel_id}",
                json_string=""
            )
            admin_callback_handler(fake_callback, bot)
        else:
            bot.answer_callback_query(
                call.id,
                "Failed to set reserved position!",
                show_alert=True
            )

def create_admin_markup():
    """Create the admin panel markup with all options."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("View Approved Channels", callback_data="view_approved"),
        types.InlineKeyboardButton("View Pending Applications", callback_data="view_pending"),
        types.InlineKeyboardButton("Network Statistics", callback_data="view_stats"),
        types.InlineKeyboardButton("Trigger Manual Crosspost", callback_data="trigger_post"),
        types.InlineKeyboardButton("Update Subscriber Counts", callback_data="update_subscribers"),
        types.InlineKeyboardButton("Manage Post Images", callback_data="manage_images")
    )
    return markup

def handle_admin_photo(message, bot):
    """Handle photo uploads from admins."""
    user_id = str(message.from_user.id)
    
    # Check if the user is an admin and is in the expected state
    if not is_admin(message.from_user.id) or user_id not in user_dict or "waiting_for_image" not in user_dict[user_id]:
        return
    
    # Get the image type the admin wanted to upload
    image_type = user_dict[user_id]["waiting_for_image"]
    logger.info(f"Admin {user_id} uploading {image_type} image")
    
    # Determine the filename based on image type
    if image_type == "SFW":
        filename = "generated-icon.png"
    else:  # NSFW
        filename = "nsfw-icon.png"
    
    # Get the largest photo size
    photo = max(message.photo, key=lambda p: p.file_size)
    file_info = bot.get_file(photo.file_id)
    
    # Download the file
    downloaded_file = bot.download_file(file_info.file_path)
    
    # Save the file
    with open(filename, 'wb') as new_file:
        new_file.write(downloaded_file)
    
    # Send confirmation to the user
    bot.reply_to(
        message,
        f"✅ Successfully uploaded {image_type} image!\n"
        f"The image will be used in future crossposts for {image_type} channels.",
        parse_mode="Markdown"
    )
    
    # Clear the user state
    user_dict.pop(user_id, None)
    
    # Show the admin panel again
    bot.send_message(
        message.chat.id,
        "*Admin Control Panel*\n\nSelect an option to manage your channel network:",
        parse_mode="Markdown",
        reply_markup=create_admin_markup()
    )

def register_admin_handlers(bot):
    """Register all admin handlers with the bot."""
    # Register photo handler for image uploads
    @bot.message_handler(content_types=['photo'])
    def handle_photos(message):
        handle_admin_photo(message, bot)
    
    # Register command handlers (only accessible to admins)
    @bot.message_handler(commands=['list'])
    def handle_list(message):
        # Extract arguments after the command
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        admin_list_command(message, bot, args)
    
    @bot.message_handler(commands=['approve'])
    def handle_approve(message):
        admin_approve_command(message, bot)
    
    @bot.message_handler(commands=['reject'])
    def handle_reject(message):
        admin_reject_command(message, bot)
    
    @bot.message_handler(commands=['remove'])
    def handle_remove(message):
        admin_remove_command(message, bot)
    
    @bot.message_handler(commands=['post'])
    def handle_post(message):
        admin_post_command(message, bot)
    
    @bot.message_handler(commands=['stats'])
    def handle_stats(message):
        admin_stats_command(message, bot)
        
    @bot.message_handler(commands=['updatesubscribers', 'update_subscribers'])
    def handle_update_subscribers(message):
        admin_update_subscribers_command(message, bot)
    
    # Add a command to show the admin panel
    @bot.message_handler(commands=['admin'])
    def handle_admin_panel(message):
        user_id = message.from_user.id
        if is_admin(user_id):
            # Use the create_admin_markup function
            markup = create_admin_markup()
            
            bot.send_message(
                message.chat.id,
                "*Admin Control Panel*\n\nSelect an option to manage your channel network:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            bot.reply_to(message, "You don't have permission to use this command.")
    
    # Register callback query handler for admin actions
    @bot.callback_query_handler(func=lambda call: call.data.startswith((
        "approve_", "reject_", "remove_", "manage_", "view_", "toggle_sfw_", 
        "edit_emojis_", "edit_schedule_", "trigger_", "upload_", "toggle_day_",
        "set_position_", "save_position_"
    )) or call.data in ["manage_images", "admin_back", "update_subscribers"])
    def handle_admin_callbacks(call):
        admin_callback_handler(call, bot)
    
    logger.info("Admin handlers registered")
