import logging
import re
from typing import Dict, List, Any, Optional

import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot import custom_filters

import config
from utils import storage

logger = logging.getLogger(__name__)

# Define state group for channel application
class ChannelStates(StatesGroup):
    waiting_channel_name = State()  # Step 1: User sends channel name
    waiting_channel_url = State()   # Step 2: User sends channel URL
    waiting_emoji = State()         # Step 3: User sends 3 emojis
    waiting_admin_verification = State()  # Step 4: User makes bot admin
    waiting_post_forward = State()  # Step 5: User forwards a post

# Constants
CANCEL_COMMAND = "❌ Cancel Registration"

# User session storage (since telebot doesn't have built-in user_data like python-telegram-bot)
user_sessions = {}

# Start command handler
def start_command(message):
    """Start the bot conversation."""
    user = message.from_user
    response = (
        f"👋 Hello, {user.first_name}!\n\n"
        "I'm a Ukrainian Telegram Community Crossposting Bot. I help connect and promote verified Ukrainian Telegram channels.\n\n"
        "Commands:\n"
        "/apply - Apply to add your channel to our network\n"
        "/settings - Manage your channel's settings\n"
        "/schedule - Set your channel's crossposting schedule\n"
        "/status - Check your channel's status\n"
        "/cancel - Cancel registration process\n"
        "/help - Show this help message\n\n"
        "To get started, use /apply to submit your channel for approval."
    )
    return response

# Help command handler
def help_command(message):
    """Show help information."""
    response = (
        "📚 *Bot Commands*\n\n"
        "/apply - Apply to add your channel to our network\n"
        "/settings - Manage your channel's settings\n"
        "/schedule - Set your channel's crossposting schedule\n"
        "/status - Check your channel's status\n"
        "/cancel - Cancel registration process\n"
        "/help - Show this help message\n\n"
        "*About the Bot*\n"
        "This bot facilitates crossposting between verified Ukrainian Telegram channels. "
        "Channels can opt in or out of crossposting on specific days. "
        "Crossposts happen exactly at 6:00 PM Kyiv time and include a selection of up to 10 channels.\n\n"
        "To get started, use /apply to submit your channel for approval.\n"
        "You can cancel registration at any time by clicking the ❌ Cancel button or using the /cancel command."
    )
    return response

# Cancel command handler
def cancel_command(message, bot):
    """Cancel the current operation and reset state."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} cancelled operation")
    
    # Clear user data
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    # Reset state
    bot.delete_state(message.from_user.id, message.chat.id)
    
    # Send confirmation
    bot.send_message(
        message.chat.id,
        "✅ Registration cancelled. You can start over with /apply when you're ready.",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Apply command handler
def apply_command(message, bot):
    """Start the channel application process."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} started channel application process")
    
    # Initialize user session data
    user_sessions[user_id] = {"channel": {}}
    
    try:
        # Create keyboard with cancel button
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(types.KeyboardButton(CANCEL_COMMAND))
        
        bot.send_message(
            message.chat.id,
            "Let's add your channel to our crossposting network!\n\n"
            "Step 1 of 5: Please enter the name of your channel.\n\n"
            "You can cancel at any time by clicking the button below.",
            reply_markup=markup
        )
        
        # Set state to waiting for channel name
        bot.set_state(message.from_user.id, ChannelStates.waiting_channel_name, message.chat.id)
        logger.info(f"Set state to waiting_channel_name for user {user_id}")
    except Exception as e:
        logger.error(f"Error in apply_command: {e}")
        bot.send_message(message.chat.id, "An error occurred. Please try again later.")

# Process channel name
def channel_name_handler(message, bot):
    """Process the channel name input."""
    user_id = message.from_user.id
    logger.info(f"Processing channel name for user {user_id}: {message.text}")
    
    # Check for cancel command
    if message.text == CANCEL_COMMAND:
        cancel_command(message, bot)
        return
    
    if not message.text:
        bot.send_message(
            message.chat.id,
            "Please enter a valid channel name as text."
        )
        logger.warning(f"User {user_id} sent empty channel name")
        return
    
    # Store channel name in user session
    if user_id not in user_sessions:
        logger.info(f"Creating new session for user {user_id}")
        user_sessions[user_id] = {"channel": {}}
    elif "channel" not in user_sessions[user_id]:
        logger.info(f"Creating channel data for existing user {user_id}")
        user_sessions[user_id]["channel"] = {}
    
    # Store the title    
    user_sessions[user_id]["channel"]["title"] = message.text
    logger.info(f"Stored channel title '{message.text}' for user {user_id}")
    
    try:
        # Format the channel name and create a message with the name highlighted
        channel_name = message.text
        
        # Create keyboard with cancel button
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(types.KeyboardButton(CANCEL_COMMAND))
        
        # Move to the next step
        bot.send_message(
            message.chat.id,
            f"Step 2 of 5: Please send the URL of your channel *{channel_name}*.\n\n"
            f"For example: @yourchannel",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        # Update state
        current_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"Current state before transition: {current_state}")
        
        bot.set_state(message.from_user.id, ChannelStates.waiting_channel_url, message.chat.id)
        
        new_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"State transitioned from {current_state} to {new_state}")
    except Exception as e:
        logger.error(f"Error in channel_name_handler: {e}")
        bot.send_message(message.chat.id, "An error occurred. Please try again later.")

# Process channel URL
def channel_url_handler(message, bot):
    """Process the channel URL input."""
    user_id = message.from_user.id
    logger.info(f"Processing channel URL for user {user_id}: {message.text}")
    
    # Check for cancel command
    if message.text == CANCEL_COMMAND:
        cancel_command(message, bot)
        return
    
    if not message.text:
        bot.send_message(
            message.chat.id,
            "Please enter a valid channel URL as text."
        )
        logger.warning(f"User {user_id} sent empty channel URL")
        return
    
    # Clean the URL (remove @ if present)
    channel_url = message.text.strip()
    if channel_url.startswith('@'):
        channel_url = channel_url[1:]
    
    # Store channel username in user session
    if user_id not in user_sessions or "channel" not in user_sessions[user_id]:
        logger.warning(f"User {user_id} has no active session in channel_url_handler")
        bot.send_message(message.chat.id, "Something went wrong. Please start over with /apply.")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    user_sessions[user_id]["channel"]["username"] = channel_url
    logger.info(f"Stored channel username '{channel_url}' for user {user_id}")
    
    try:
        channel_name = user_sessions[user_id]["channel"]["title"]
        channel_url_formatted = f"@{channel_url}"
        
        # Create keyboard with cancel button
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(types.KeyboardButton(CANCEL_COMMAND))
        
        # Move to the next step - emoji selection
        bot.send_message(
            message.chat.id,
            f"Step 3 of 5: Please send 3 emojis that represent your channel *{channel_name}* ({channel_url_formatted}).\n\n"
            "These will be displayed next to your channel in crossposts.\n\n"
            "For example: 🇺🇦 💻 🎮\n\n"
            "Send the emojis in a single message.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        # Update state
        current_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"Current state before transition: {current_state}")
        
        bot.set_state(message.from_user.id, ChannelStates.waiting_emoji, message.chat.id)
        
        new_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"State transitioned from {current_state} to {new_state}")
    except Exception as e:
        logger.error(f"Error in channel_url_handler: {e}")
        bot.send_message(message.chat.id, "An error occurred. Please try again later.")

# Process emoji selection
def emoji_handler(message, bot):
    """Process emoji selection."""
    user_id = message.from_user.id
    logger.info(f"Processing emoji selection for user {user_id}")
    
    # Check for cancel command
    if message.text == CANCEL_COMMAND:
        cancel_command(message, bot)
        return
    
    if user_id not in user_sessions or "channel" not in user_sessions[user_id]:
        logger.warning(f"User {user_id} has no active session in emoji_handler")
        bot.send_message(message.chat.id, "Something went wrong. Please start over with /apply.")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    # Extract emojis from the message
    emoji_pattern = re.compile(
        "["
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0000257F"  # Enclosed characters
        "\U00002580-\U000025FF"  # Box Drawing
        "\U00002600-\U000026FF"  # Miscellaneous Symbols
        "\U00002700-\U000027BF"  # Dingbats
        "\U0000FE00-\U0000FE0F"  # Variation Selectors
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "]+", flags=re.UNICODE
    )
    
    emojis = emoji_pattern.findall(message.text)
    logger.info(f"Found emojis: {emojis}")
    
    if not emojis:
        bot.send_message(
            message.chat.id,
            "I couldn't find any valid emojis in your message. "
            "Please send emojis (like 🇺🇦 💻 🎮)."
        )
        logger.warning(f"User {user_id} sent message with no valid emojis")
        return
    
    # Limit to 3 emojis
    user_sessions[user_id]["channel"]["emojis"] = emojis[:3]
    logger.info(f"Stored emojis {emojis[:3]} for user {user_id}")
    
    try:
        channel_name = user_sessions[user_id]["channel"]["title"]
        channel_url = user_sessions[user_id]["channel"]["username"]
        channel_url_formatted = f"@{channel_url}"
        emoji_list = " ".join(emojis[:3])
        
        # Move to the next step - bot admin verification
        # Create keyboard with both admin confirmation and cancel buttons
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(
            types.KeyboardButton("✅ I've made the bot an admin"),
            types.KeyboardButton(CANCEL_COMMAND)
        )
        
        bot.send_message(
            message.chat.id,
            f"Step 4 of 5: Now, you need to make the bot an administrator in your channel *{channel_name}* ({channel_url_formatted}).\n\n"
            "1. Go to your channel\n"
            "2. Open channel settings\n"
            "3. Go to 'Administrators'\n"
            "4. Add administrator\n"
            "5. Search for this bot's username\n"
            "6. Enable 'Post Messages' permission\n"
            "7. Save the changes\n\n"
            f"Selected emojis: {emoji_list}\n\n"
            "When you've done this, click the button below to continue.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        # Update state
        current_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"Current state before transition: {current_state}")
        
        bot.set_state(message.from_user.id, ChannelStates.waiting_admin_verification, message.chat.id)
        
        new_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"State transitioned from {current_state} to {new_state}")
    except Exception as e:
        logger.error(f"Error in emoji_handler: {e}")
        bot.send_message(message.chat.id, "An error occurred. Please try again later.")

# Process admin verification
def admin_verification_handler(message, bot):
    """Process admin verification."""
    user_id = message.from_user.id
    logger.info(f"Processing admin verification for user {user_id}")
    
    # Check for cancel command
    if message.text == CANCEL_COMMAND:
        cancel_command(message, bot)
        return
    
    if user_id not in user_sessions or "channel" not in user_sessions[user_id]:
        logger.warning(f"User {user_id} has no active session in admin_verification_handler")
        bot.send_message(message.chat.id, "Something went wrong. Please start over with /apply.")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    # Log the channel data we have so far
    logger.info(f"Channel data so far: {user_sessions[user_id]['channel']}")
    
    # We'll assume the user has made the bot an admin for now
    # In a real implementation, you would verify this using getChatMember
    logger.info(f"Skipping admin verification check for now")
    
    try:
        channel_name = user_sessions[user_id]["channel"]["title"]
        channel_url = user_sessions[user_id]["channel"]["username"]
        channel_url_formatted = f"@{channel_url}"
        emoji_list = " ".join(user_sessions[user_id]["channel"]["emojis"])
        
        # Move to the final step - forward a post
        # Create keyboard with cancel button for the last step
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(types.KeyboardButton(CANCEL_COMMAND))
        
        bot.send_message(
            message.chat.id,
            f"Step 5 of 5: Finally, please forward a post from your channel *{channel_name}* ({channel_url_formatted}).\n\n"
            f"Selected emojis: {emoji_list}\n\n"
            "This will help us verify your ownership and complete the application process.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        # Update state
        current_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"Current state before transition: {current_state}")
        
        bot.set_state(message.from_user.id, ChannelStates.waiting_post_forward, message.chat.id)
        
        new_state = bot.get_state(user_id, message.chat.id)
        logger.info(f"State transitioned from {current_state} to {new_state}")
    except Exception as e:
        logger.error(f"Error in admin_verification_handler: {e}")
        bot.send_message(message.chat.id, "An error occurred. Please try again later.")

# Process forwarded post
def post_forward_handler(message, bot):
    """Process a forwarded post from a channel."""
    user_id = message.from_user.id
    logger.info(f"Processing forwarded post from user {user_id}")
    
    # Check if this is a cancel command - need special handling since this accepts all content types
    if hasattr(message, 'text') and message.text == CANCEL_COMMAND:
        cancel_command(message, bot)
        return
    
    # Log message details for debugging
    logger.info(f"Message details: forward_from_chat={getattr(message, 'forward_from_chat', None)}")
    if hasattr(message, 'forward_from_chat'):
        logger.info(f"Chat type: {getattr(message.forward_from_chat, 'type', 'unknown')}")
    
    # Check if the message is a forwarded post from a channel
    if not hasattr(message, 'forward_from_chat') or not message.forward_from_chat or message.forward_from_chat.type != "channel":
        bot.send_message(
            message.chat.id,
            "That doesn't look like a forwarded post from a channel. "
            "Please forward any post from your channel."
        )
        logger.warning(f"User {user_id} sent a message that is not a forward from a channel")
        return
    
    channel = message.forward_from_chat
    logger.info(f"Processing channel: {channel.id} - {getattr(channel, 'title', 'Unknown')}")
    
    # Store channel ID in user session
    if user_id not in user_sessions or "channel" not in user_sessions[user_id]:
        bot.send_message(message.chat.id, "Something went wrong. Please start over with /apply.")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
        
    user_sessions[user_id]["channel"]["id"] = channel.id
    
    # Check if the channel is already in the system
    if storage.is_channel_approved(str(channel.id)):
        bot.send_message(
            message.chat.id,
            f"Your channel '{user_sessions[user_id]['channel']['title']}' is already approved and part of our network!\n\n"
            "You can use /settings to manage your channel's settings or /schedule to update your crossposting schedule."
        )
        # Reset state
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    if storage.is_channel_pending(str(channel.id)):
        bot.send_message(
            message.chat.id,
            f"Your channel '{user_sessions[user_id]['channel']['title']}' is already pending approval.\n\n"
            "Please wait for an admin to review your application. You can check the status with /status."
        )
        # Reset state
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    # Verify that the forwarded channel matches the entered URL
    entered_username = user_sessions[user_id]["channel"].get("username", "").lower()
    forwarded_username = channel.username.lower() if hasattr(channel, "username") and channel.username else ""
    
    if entered_username and forwarded_username and entered_username != forwarded_username:
        bot.send_message(
            message.chat.id,
            f"The forwarded post is from @{forwarded_username}, but you entered @{entered_username}.\n"
            "Please forward a post from the correct channel or start over with /apply."
        )
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    # Default to SFW (Safe for Work)
    user_sessions[user_id]["channel"]["is_sfw"] = True
    
    # Set up default schedule (all days active)
    user_sessions[user_id]["channel"]["schedule"] = {str(i): True for i in range(7)}
    
    # Submit application
    channel_data = user_sessions[user_id]["channel"]
    channel_id = str(channel_data["id"])
    
    success = storage.add_pending_channel(channel_id, channel_data)
    
    if success:
        channel_name = user_sessions[user_id]["channel"]["title"]
        channel_url = user_sessions[user_id]["channel"]["username"]
        channel_url_formatted = f"@{channel_url}"
        
        bot.send_message(
            message.chat.id,
            f"Thank you! Your channel *{channel_name}* ({channel_url_formatted}) has been submitted for review.\n\n"
            "An admin will verify and approve your channel soon. "
            "You can check the status of your application with /status.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            message.chat.id,
            "There was an error submitting your application. Please try again later."
        )
    
    # Clear state
    bot.delete_state(message.from_user.id, message.chat.id)



# Settings command handler
def settings_command(message, bot):
    """Manage channel settings."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested settings")
    
    # Get all approved channels
    all_channels = storage.get_channels()
    logger.info(f"Found {len(all_channels)} approved channels")
    
    # For now, we'll show all channels that the user might own
    # In production, you would filter based on channel ownership
    # by checking if the user is an admin in each channel
    
    # For demonstration purposes, we'll just show all channels
    # This would need to be replaced with proper ownership verification
    if not all_channels:
        bot.send_message(
            message.chat.id,
            "There are no approved channels in the network yet.\n\n"
            "Use /apply to submit a channel for approval."
        )
        logger.info("No approved channels found")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for channel_id, channel_data in all_channels.items():
        channel_title = channel_data.get("title", "Unknown")
        markup.add(types.InlineKeyboardButton(
            channel_title,
            callback_data=f"settings_{channel_id}"
        ))
        logger.info(f"Added channel {channel_id}: {channel_title} to menu")
    
    bot.send_message(
        message.chat.id,
        "Select a channel to manage:",
        reply_markup=markup
    )

# Schedule command handler
def schedule_command(message, bot):
    """Manage channel crossposting schedule."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested schedule management")
    
    # Get all approved channels
    all_channels = storage.get_channels()
    logger.info(f"Found {len(all_channels)} approved channels")
    
    # For demonstration purposes, show all channels
    # In production, you would filter based on channel ownership
    if not all_channels:
        bot.send_message(
            message.chat.id,
            "There are no approved channels in the network yet.\n\n"
            "Use /apply to submit a channel for approval."
        )
        logger.info("No approved channels found")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for channel_id, channel_data in all_channels.items():
        channel_title = channel_data.get("title", "Unknown")
        markup.add(types.InlineKeyboardButton(
            channel_title,
            callback_data=f"schedule_{channel_id}"
        ))
        logger.info(f"Added channel {channel_id}: {channel_title} to schedule menu")
    
    bot.send_message(
        message.chat.id,
        "Select a channel to manage its schedule:",
        reply_markup=markup
    )

# Status command handler
def status_command(message, bot):
    """Check channel status."""
    user_id = message.from_user.id
    
    # For demonstration purposes, show all channels and pending applications
    # In a real implementation, you'd need to verify ownership
    approved_channels = storage.get_channels()
    pending_channels = storage.get_pending_channels()
    
    # In a real implementation, filter by user ownership
    # For now, we'll show all (this would be a security issue in production)
    user_approved = list(approved_channels.items())
    user_pending = list(pending_channels.items())
    
    if not user_approved and not user_pending:
        bot.send_message(
            message.chat.id,
            "You don't have any channels in our network yet.\n\n"
            "Use /apply to submit a channel for approval."
        )
        return
    
    message_text = "*Your Channel Status*\n\n"
    
    if user_approved:
        message_text += "*Approved Channels:*\n"
        for channel_id, channel_data in user_approved:
            title = channel_data.get("title", "Unknown")
            message_text += f"• {title}\n"
        message_text += "\n"
    
    if user_pending:
        message_text += "*Pending Approval:*\n"
        for channel_id, channel_data in user_pending:
            title = channel_data.get("title", "Unknown")
            message_text += f"• {title}\n"
        message_text += "\n"
    
    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

# Callback query handler
def callback_query_handler(call, bot):
    """Handle callback queries."""
    logger.info(f"Callback query: {call.data}")
    data = call.data
    
    if data.startswith("settings_"):
        channel_id = data[len("settings_"):]
        channel_info = storage.get_channel_info(channel_id)
        
        if not channel_info:
            bot.answer_callback_query(call.id, "Channel not found")
            return
        
        # Create inline keyboard for channel settings
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Add buttons for different settings
        markup.add(
            types.InlineKeyboardButton(
                "📅 Manage Schedule", 
                callback_data=f"schedule_{channel_id}"
            ),
            types.InlineKeyboardButton(
                "😀 Change Emojis", 
                callback_data=f"emojis_{channel_id}"
            ),
            types.InlineKeyboardButton(
                "ℹ️ Channel Info", 
                callback_data=f"info_{channel_id}"
            )
        )
        
        # Send the settings menu
        bot.edit_message_text(
            f"Settings for channel: *{channel_info.get('title', 'Unknown')}*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
    
    elif data.startswith("schedule_"):
        channel_id = data[len("schedule_"):]
        channel_info = storage.get_channel_info(channel_id)
        
        if not channel_info:
            bot.answer_callback_query(call.id, "Channel not found")
            return
        
        # Get current schedule
        schedule = storage.get_channel_schedule(channel_id)
        
        # Create schedule management keyboard
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Add day toggle buttons
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day_idx, day_name in enumerate(days):
            # Use emoji to indicate active status
            status = "✅" if schedule.get(str(day_idx), False) else "❌"
            markup.add(types.InlineKeyboardButton(
                f"{day_name}: {status}",
                callback_data=f"toggle_day_{channel_id}_{day_idx}"
            ))
        
        # Add back button
        markup.add(types.InlineKeyboardButton(
            "⬅️ Back to Settings",
            callback_data=f"settings_{channel_id}"
        ))
        
        # Send the schedule menu
        bot.edit_message_text(
            f"Schedule for channel: *{channel_info.get('title', 'Unknown')}*\n\n"
            f"Toggle days when you want your channel to participate in crossposts:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
    
    elif data.startswith("toggle_day_"):
        # Format: toggle_day_CHANNEL_ID_DAY_INDEX
        parts = data.split("_")
        if len(parts) != 4:
            bot.answer_callback_query(call.id, "Invalid callback data")
            return
        
        _, _, channel_id, day_idx = parts
        
        try:
            day_idx = int(day_idx)
        except ValueError:
            bot.answer_callback_query(call.id, "Invalid day index")
            return
        
        # Toggle the day in the schedule
        success = storage.update_channel_schedule(channel_id, day_idx, None)  # None means toggle
        
        if success:
            # Inform user about successful update
            bot.answer_callback_query(call.id, "Schedule updated")
            
            # Use a simpler approach - just refresh the message directly
            channel_info = storage.get_channel_info(channel_id)
            if channel_info:
                # Get current schedule
                schedule = storage.get_channel_schedule(channel_id)
                
                # Create schedule management keyboard
                markup = types.InlineKeyboardMarkup(row_width=2)
                
                # Add day toggle buttons
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                for day_idx, day_name in enumerate(days):
                    # Use emoji to indicate active status
                    status = "✅" if schedule.get(str(day_idx), False) else "❌"
                    markup.add(types.InlineKeyboardButton(
                        f"{day_name}: {status}",
                        callback_data=f"toggle_day_{channel_id}_{day_idx}"
                    ))
                
                # Add back button
                markup.add(types.InlineKeyboardButton(
                    "⬅️ Back to Settings",
                    callback_data=f"settings_{channel_id}"
                ))
                
                # Update the message
                bot.edit_message_text(
                    f"Schedule for channel: *{channel_info.get('title', 'Unknown')}*\n\n"
                    f"Toggle days when you want your channel to participate in crossposts:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
        else:
            bot.answer_callback_query(call.id, "Failed to update schedule")
    
    elif data.startswith("emojis_"):
        channel_id = data[len("emojis_"):]
        channel_info = storage.get_channel_info(channel_id)
        
        if not channel_info:
            bot.answer_callback_query(call.id, "Channel not found")
            return
        
        # Show current emojis
        current_emojis = channel_info.get("emojis", [])
        emoji_text = ", ".join(current_emojis) if current_emojis else "No custom emojis set"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "⬅️ Back to Settings",
            callback_data=f"settings_{channel_id}"
        ))
        
        bot.edit_message_text(
            f"Emojis for channel: *{channel_info.get('title', 'Unknown')}*\n\n"
            f"Current emojis: {emoji_text}\n\n"
            f"To change emojis, use the /apply command again.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
    
    elif data.startswith("info_"):
        channel_id = data[len("info_"):]
        channel_info = storage.get_channel_info(channel_id)
        
        if not channel_info:
            bot.answer_callback_query(call.id, "Channel not found")
            return
        
        # Get subscriber count
        try:
            from utils import crosspost
            sub_count = crosspost.get_channel_subscriber_count(channel_id)
        except Exception as e:
            logger.error(f"Failed to get subscriber count: {e}")
            sub_count = 0
        
        # Format channel info
        title = channel_info.get("title", "Unknown")
        url = channel_info.get("url", "Unknown")
        is_sfw = "SFW" if channel_info.get("is_sfw", True) else "NSFW"
        emojis = ", ".join(channel_info.get("emojis", [])) or "None"
        
        # Create back button
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "⬅️ Back to Settings",
            callback_data=f"settings_{channel_id}"
        ))
        
        # Send channel info
        bot.edit_message_text(
            f"*Channel Information*\n\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"Type: {is_sfw}\n"
            f"Subscribers: {sub_count}\n"
            f"Custom Emojis: {emojis}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

def register_channel_handlers(bot):
    """Register all channel-related handlers with the bot."""
    # Register the state filter
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    
    # Register command handlers
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        response = start_command(message)
        bot.send_message(message.chat.id, response)
    
    @bot.message_handler(commands=['help'])
    def handle_help(message):
        response = help_command(message)
        bot.send_message(message.chat.id, response, parse_mode="Markdown")
    
    @bot.message_handler(commands=['apply'])
    def handle_apply(message):
        apply_command(message, bot)
        
    # Cancel command to cancel any application process
    @bot.message_handler(commands=['cancel'])
    def handle_cancel_command(message):
        cancel_command(message, bot)
    
    @bot.message_handler(commands=['settings'])
    def handle_settings(message):
        settings_command(message, bot)
    
    @bot.message_handler(commands=['schedule'])
    def handle_schedule(message):
        schedule_command(message, bot)
    
    @bot.message_handler(commands=['status'])
    def handle_status(message):
        status_command(message, bot)
    
    # Register state handlers
    @bot.message_handler(state=ChannelStates.waiting_channel_name, content_types=['text'])
    def handle_waiting_channel_name(message):
        logger.info(f"Handling waiting_channel_name state for user {message.from_user.id}")
        channel_name_handler(message, bot)
        
    @bot.message_handler(state=ChannelStates.waiting_channel_url, content_types=['text'])
    def handle_waiting_channel_url(message):
        logger.info(f"Handling waiting_channel_url state for user {message.from_user.id}")
        channel_url_handler(message, bot)
    
    @bot.message_handler(state=ChannelStates.waiting_emoji, content_types=['text'])
    def handle_waiting_emoji(message):
        logger.info(f"Handling waiting_emoji state for user {message.from_user.id}")
        emoji_handler(message, bot)
        
    @bot.message_handler(state=ChannelStates.waiting_admin_verification, content_types=['text'])
    def handle_waiting_admin_verification(message):
        logger.info(f"Handling waiting_admin_verification state for user {message.from_user.id}")
        admin_verification_handler(message, bot)
        
    @bot.message_handler(state=ChannelStates.waiting_post_forward, content_types=['text', 'photo', 'video', 'document', 'audio', 'animation', 'sticker', 'video_note', 'voice', 'location', 'contact', 'poll'])
    def handle_waiting_post_forward(message):
        logger.info(f"Handling waiting_post_forward state for user {message.from_user.id}")
        post_forward_handler(message, bot)
    
    # Register callback query handler
    @bot.callback_query_handler(func=lambda call: call.data.startswith(("settings_", "schedule_", "toggle_day_", "emojis_", "info_")))
    def handle_callback_query(call):
        logger.info(f"Handling callback query: {call.data}")
        callback_query_handler(call, bot)
    
    logger.info("Channel handlers registered")
