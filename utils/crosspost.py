import logging
import random
from typing import List, Optional
import os
from datetime import datetime

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
from utils import storage

logger = logging.getLogger(__name__)

# Store a reference to the bot instance for later use
_bot = None

def get_bot_instance():
    """Get the bot instance."""
    global _bot
    if _bot is None:
        # This is a fallback - bot should be set by init_bot
        _bot = telebot.TeleBot(config.TOKEN)
    return _bot

def init_bot(bot):
    """Initialize with the active bot instance."""
    global _bot
    _bot = bot
    
def get_channel_subscriber_count(channel_id: str) -> int:
    """Get the number of subscribers for a channel.
    
    Args:
        channel_id: The ID of the channel
        
    Returns:
        The number of subscribers or 0 if there was an error
    """
    bot = get_bot_instance()
    try:
        # Convert string ID to int
        chat_id = int(channel_id)
        # Get chat info from Telegram
        chat_info = bot.get_chat(chat_id)
        # Get member count
        member_count = bot.get_chat_member_count(chat_id)
        return member_count
    except Exception as e:
        logger.error(f"Error getting subscriber count for channel {channel_id}: {e}")
        return 0
        
def update_all_channel_subscribers():
    """Update subscriber counts for all channels from Telegram API.
    
    This function should be run periodically to ensure statistics are accurate.
    """
    logger.info("Updating subscriber counts for all channels")
    channels = storage.get_channels()
    updated_count = 0
    
    for channel_id, channel_data in channels.items():
        try:
            # Get current subscriber count from Telegram
            subscriber_count = get_channel_subscriber_count(channel_id)
            
            if subscriber_count > 0:
                # Update the channel data
                channel_data['subscribers'] = subscriber_count
                updated_count += 1
            else:
                logger.warning(f"Failed to get subscriber count for channel {channel_id}")
        except Exception as e:
            logger.error(f"Error updating subscribers for channel {channel_id}: {e}")
    
    # Save the updated channel data
    if updated_count > 0:
        if storage.save_channels(channels):
            logger.info(f"Successfully updated subscriber counts for {updated_count} channels")
        else:
            logger.error("Failed to save updated channel data")
    else:
        logger.warning("No channel subscriber counts were updated")

def create_and_send_crosspost(active_channels: List[str]):
    """Create and send a crosspost message to all active channels."""
    logger.info(f"Creating crosspost for {len(active_channels)} active channels")
    
    if not active_channels:
        logger.warning("No active channels provided for crosspost")
        return

    # Get channel data for all active channels
    channels_data = storage.get_channels()
    channels_to_post = []
    
    for channel_id in active_channels:
        if channel_id in channels_data:
            channels_to_post.append({
                "id": channel_id,
                "title": channels_data[channel_id].get("title", "Unknown Channel"),
                "username": channels_data[channel_id].get("username", ""),
                "emojis": channels_data[channel_id].get("emojis", []),
                "is_sfw": channels_data[channel_id].get("is_sfw", True)
            })
    
    if not channels_to_post:
        logger.warning("No valid channels found for crosspost")
        return
    
    # Split into SFW and NSFW groups
    sfw_channels = [c for c in channels_to_post if c["is_sfw"]]
    nsfw_channels = [c for c in channels_to_post if not c["is_sfw"]]
    
    # Process SFW channels if there are any
    if sfw_channels:
        process_crosspost_group(sfw_channels, is_sfw=True)
    
    # Process NSFW channels if there are any
    if nsfw_channels:
        process_crosspost_group(nsfw_channels, is_sfw=False)

def process_crosspost_group(channels: List[dict], is_sfw: bool):
    """Process a group of channels (either SFW or NSFW) for crossposting."""
    bot = get_bot_instance()
    from utils import storage
    
    # Get subscriber counts for all channels and categorize them
    small_channels = []  # Channels with less than 300 subscribers (priority)
    large_channels = []  # Channels with 300+ subscribers
    
    for channel in channels:
        # Get subscriber count
        subscriber_count = get_channel_subscriber_count(channel["id"])
        channel["subscribers"] = subscriber_count
        
        if subscriber_count < 300:
            small_channels.append(channel)
        else:
            large_channels.append(channel)
    
    logger.info(f"Found {len(small_channels)} small channels (<300 subscribers) and {len(large_channels)} large channels")
    
    # Get channels with reserved positions for this content type (SFW/NSFW)
    reserved_positions = storage.get_channels_with_reserved_positions(is_sfw=is_sfw)
    logger.info(f"Found {len(reserved_positions)} channels with reserved positions for {'SFW' if is_sfw else 'NSFW'} content")
    
    # Create a final list with placeholders for reserved positions
    final_channels = [None] * config.MAX_CHANNELS_PER_POST
    
    # Fill in any reserved positions
    reserved_channel_ids = set()
    for position, channel_id in reserved_positions.items():
        # Position is 1-based in admin interface, but 0-based in the array
        array_position = position - 1
        
        # Skip if position is out of bounds
        if array_position < 0 or array_position >= config.MAX_CHANNELS_PER_POST:
            logger.warning(f"Reserved position {position} out of bounds, skipping")
            continue
            
        # Find the channel data for this ID
        channel_data = None
        for channel in channels:
            if str(channel["id"]) == str(channel_id):
                channel_data = channel
                break
                
        if channel_data:
            final_channels[array_position] = channel_data
            reserved_channel_ids.add(str(channel_id))
            logger.info(f"Reserved position {position} filled with channel {channel_data['title']}")
    
    # Filter out channels that already have reserved positions
    available_small_channels = [c for c in small_channels if str(c["id"]) not in reserved_channel_ids]
    available_large_channels = [c for c in large_channels if str(c["id"]) not in reserved_channel_ids]
    
    # Shuffle both lists to ensure randomness within each group
    random.shuffle(available_small_channels)
    random.shuffle(available_large_channels)
    
    # Create a pool of channels to fill non-reserved positions
    pool = []
    
    # First, take up to 5 small channels (priority)
    pool.extend(available_small_channels[:5])
    
    # Then, fill the remaining slots with large channels
    remaining_slots = config.MAX_CHANNELS_PER_POST - len(pool) - len([c for c in final_channels if c is not None])
    pool.extend(available_large_channels[:remaining_slots])
    
    # If we don't have enough channels total, use more small channels if available
    if len(pool) < (config.MAX_CHANNELS_PER_POST - len([c for c in final_channels if c is not None])) and len(available_small_channels) > 5:
        # Add more small channels to fill the post if needed
        additional_small = min(
            len(available_small_channels) - 5, 
            config.MAX_CHANNELS_PER_POST - len(pool) - len([c for c in final_channels if c is not None])
        )
        pool.extend(available_small_channels[5:5+additional_small])
    
    # Fill in the non-reserved positions
    for i in range(config.MAX_CHANNELS_PER_POST):
        if final_channels[i] is None and pool:
            final_channels[i] = pool.pop(0)
    
    # Remove None values from final_channels
    selected_channels = [c for c in final_channels if c is not None]
    
    # Use the appropriate header based on whether this is SFW or NSFW
    if is_sfw:
        header = config.CROSSPOST_HEADER_SFW
    else:
        header = config.CROSSPOST_HEADER_NSFW
    
    # Create the message text
    message_text = f"{header}\n\n"
    
    # Add type indicator for better visibility
    type_tag = "SFW" if is_sfw else "NSFW 🔞"
    message_text += f"#{type_tag}\n\n"
    
    # If we don't have enough channels total, use all available ones
    if len(selected_channels) < config.MAX_CHANNELS_PER_POST and len(channels) < config.MAX_CHANNELS_PER_POST:
        # Make sure we don't have any duplicates
        channel_ids = {str(c["id"]) for c in selected_channels}
        for channel in channels:
            if str(channel["id"]) not in channel_ids:
                selected_channels.append(channel)
                channel_ids.add(str(channel["id"]))
        
        logger.info(f"Only {len(selected_channels)} channels available, using all of them")
    else:
        logger.info(f"Selected {len(selected_channels)} channels for posting")
    
    for idx, channel in enumerate(selected_channels, 1):
        # Format channel with emojis
        emoji_str = " ".join(channel["emojis"]) if channel["emojis"] else ""
        if emoji_str:
            emoji_str = f" {emoji_str} "
        
        # Always use the channel title with a link
        if channel["username"]:
            channel_link = f"[{channel['title']}](https://t.me/{channel['username']})"
        else:
            channel_link = f"[{channel['title']}](https://t.me/{channel['id'].replace('@', '')})"
        
        message_text += f"{idx}. {emoji_str}{channel_link}\n"
    
    # Add the CTA button
    bot_info = bot.get_me()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(config.CTA_BUTTON_TEXT, url=f"https://t.me/{bot_info.username}"))
    
    # Choose the appropriate icon based on content type
    if is_sfw:
        icon_path = "generated-icon.png"  # Default icon for SFW
    else:
        # Check if a NSFW-specific icon exists, otherwise fall back to default
        nsfw_icon_path = "nsfw-icon.png"
        icon_path = nsfw_icon_path if os.path.exists(nsfw_icon_path) else "generated-icon.png"
    
    # Log the crosspost details
    logger.info(f"Preparing {type_tag} crosspost for {len(selected_channels)} channels")
    
    # Send to each channel in the group
    for target_channel in channels:
        # Only send to channels of the same type (SFW->SFW, NSFW->NSFW)
        if target_channel["is_sfw"] != is_sfw:
            logger.warning(f"Skipping channel {target_channel['id']} - content type mismatch")
            continue
        
        # Create a custom message for each channel that excludes itself from the list
        custom_selected_channels = [ch for ch in selected_channels if ch["id"] != target_channel["id"]]
        
        if not custom_selected_channels:
            logger.warning(f"No other channels to promote to {target_channel['id']}, skipping")
            continue
            
        # Recreate the message text for this specific channel (without itself)
        custom_message_text = f"{header}\n\n"
        custom_message_text += f"#{type_tag}\n\n"
        
        # Add each channel (except the current one) to the message
        for idx, channel in enumerate(custom_selected_channels, 1):
            # Format channel with emojis
            emoji_str = " ".join(channel["emojis"]) if channel["emojis"] else ""
            if emoji_str:
                emoji_str = f" {emoji_str} "
            
            # Always use the channel title with a link
            if channel["username"]:
                channel_link = f"[{channel['title']}](https://t.me/{channel['username']})"
            else:
                channel_link = f"[{channel['title']}](https://t.me/{channel['id'].replace('@', '')})"
            
            custom_message_text += f"{idx}. {emoji_str}{channel_link}\n"
            
        try:
            # Check if the icon exists
            if os.path.exists(icon_path):
                # Send message with image
                with open(icon_path, 'rb') as photo:
                    bot.send_photo(
                        chat_id=target_channel["id"],
                        photo=photo,
                        caption=custom_message_text,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
            else:
                # Fallback to text-only message if image doesn't exist
                bot.send_message(
                    chat_id=target_channel["id"],
                    text=custom_message_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
            logger.info(f"Sent {type_tag} crosspost to channel {target_channel['id']} (excluding itself from list)")
        except Exception as e:
            logger.error(f"Failed to send crosspost to channel {target_channel['id']}: {e}")
    
    logger.info(f"Completed crosspost for {type_tag} group")
