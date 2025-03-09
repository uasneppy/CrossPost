import json
import os
import logging
from typing import Dict, List, Any, Optional
import config

logger = logging.getLogger(__name__)

def ensure_data_dir():
    """Ensure the data directory exists."""
    os.makedirs(config.DATA_DIR, exist_ok=True)

def load_json(filename: str) -> Dict:
    """Load data from a JSON file."""
    ensure_data_dir()
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {filename}")
        return {}
    except Exception as e:
        logger.error(f"Error loading data from {filename}: {e}")
        return {}

def save_json(filename: str, data: Dict) -> bool:
    """Save data to a JSON file."""
    ensure_data_dir()
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data to {filename}: {e}")
        return False

def get_channels() -> Dict[str, Dict]:
    """Get all approved channels."""
    return load_json(config.CHANNELS_FILE)

def get_user_channels(user_id: int) -> Dict[str, Dict]:
    """Get all approved channels owned by a specific user."""
    channels = get_channels()
    user_channels = {}
    
    for channel_id, channel_data in channels.items():
        # Check if channel is owned by this user
        if channel_data.get("owner_id") == user_id:
            user_channels[channel_id] = channel_data
            
    return user_channels

def save_channels(channels: Dict[str, Dict]) -> bool:
    """Save all approved channels."""
    return save_json(config.CHANNELS_FILE, channels)

def get_pending_channels() -> Dict[str, Dict]:
    """Get all pending channel applications."""
    return load_json(config.PENDING_FILE)

def get_user_pending_channels(user_id: int) -> Dict[str, Dict]:
    """Get all pending channel applications owned by a specific user."""
    pending = get_pending_channels()
    user_pending = {}
    
    for channel_id, channel_data in pending.items():
        # Check if channel is owned by this user
        if channel_data.get("owner_id") == user_id:
            user_pending[channel_id] = channel_data
            
    return user_pending

def save_pending_channels(pending: Dict[str, Dict]) -> bool:
    """Save all pending channel applications."""
    return save_json(config.PENDING_FILE, pending)

def get_schedule() -> Dict[str, Dict]:
    """Get the crossposting schedule."""
    return load_json(config.SCHEDULE_FILE)

def save_schedule(schedule: Dict[str, Dict]) -> bool:
    """Save the crossposting schedule."""
    return save_json(config.SCHEDULE_FILE, schedule)

def add_pending_channel(channel_id: str, channel_data: Dict) -> bool:
    """Add a channel to the pending list."""
    pending = get_pending_channels()
    pending[channel_id] = channel_data
    return save_pending_channels(pending)

def approve_channel(channel_id: str) -> bool:
    """Move a channel from pending to approved."""
    pending = get_pending_channels()
    channels = get_channels()
    
    if channel_id not in pending:
        return False
    
    channel_data = pending.pop(channel_id)
    channels[channel_id] = channel_data
    
    # Initialize the schedule for this channel
    schedule = get_schedule()
    if channel_id not in schedule:
        # Default schedule: active all days of the week
        schedule[channel_id] = {str(i): True for i in range(7)}
    
    return (save_pending_channels(pending) and 
            save_channels(channels) and 
            save_schedule(schedule))

def reject_channel(channel_id: str) -> bool:
    """Remove a channel from the pending list (reject application)."""
    pending = get_pending_channels()
    
    if channel_id not in pending:
        return False
    
    pending.pop(channel_id)
    return save_pending_channels(pending)

def remove_channel(channel_id: str) -> bool:
    """Remove a channel from the approved list."""
    channels = get_channels()
    schedule = get_schedule()
    
    if channel_id not in channels:
        return False
    
    channels.pop(channel_id)
    if channel_id in schedule:
        schedule.pop(channel_id)
    
    return save_channels(channels) and save_schedule(schedule)

def update_channel_schedule(channel_id: str, day: int, active: Optional[bool] = None) -> bool:
    """Update a channel's schedule for a specific day.
    
    Args:
        channel_id: The ID of the channel
        day: The day of the week (0-6, Monday-Sunday)
        active: True to enable, False to disable, None to toggle current state
        
    Returns:
        True on success, False on failure
    """
    schedule = get_schedule()
    channels = get_channels()
    
    # Make sure the channel exists in approved channels
    if channel_id not in channels:
        logger.error(f"Attempted to update schedule for non-existent channel: {channel_id}")
        return False
    
    # Initialize schedule if not exists
    if channel_id not in schedule:
        schedule[channel_id] = {str(i): True for i in range(7)}
    
    # Toggle mode if active is None
    if active is None:
        current_state = schedule[channel_id].get(str(day), True)
        schedule[channel_id][str(day)] = not current_state
        logger.info(f"Toggled schedule for channel {channel_id} on day {day} to {not current_state}")
    else:
        schedule[channel_id][str(day)] = active
        logger.info(f"Set schedule for channel {channel_id} on day {day} to {active}")
    
    # Also update the channel object's schedule
    if 'schedule' not in channels[channel_id]:
        channels[channel_id]['schedule'] = {str(i): True for i in range(7)}
        
    channels[channel_id]['schedule'][str(day)] = schedule[channel_id][str(day)]
    
    # Save both schedule and channels
    schedule_saved = save_schedule(schedule)
    channels_saved = save_channels(channels)
    
    return schedule_saved and channels_saved

def get_channel_schedule(channel_id: str) -> Dict[str, bool]:
    """Get a channel's schedule."""
    schedule = get_schedule()
    return schedule.get(channel_id, {str(i): True for i in range(7)})

def update_channel_emojis(channel_id: str, emojis: List[str]) -> bool:
    """Update a channel's custom emojis."""
    channels = get_channels()
    
    if channel_id not in channels:
        return False
    
    # Keep only up to 3 emojis
    channels[channel_id]['emojis'] = emojis[:3]
    return save_channels(channels)

def get_channels_for_day(day_of_week: int) -> List[str]:
    """Get all channels that are active for a specific day of the week."""
    channels = get_channels()
    schedule = get_schedule()
    
    active_channels = []
    for channel_id, channel_data in channels.items():
        channel_schedule = schedule.get(channel_id, {str(i): True for i in range(7)})
        if channel_schedule.get(str(day_of_week), True):
            active_channels.append(channel_id)
    
    return active_channels

def get_channel_info(channel_id: str) -> Optional[Dict]:
    """Get information about a specific channel."""
    channels = get_channels()
    return channels.get(channel_id)

def is_channel_pending(channel_id: str) -> bool:
    """Check if a channel is in the pending list."""
    pending = get_pending_channels()
    return channel_id in pending

def is_channel_approved(channel_id: str) -> bool:
    """Check if a channel is in the approved list."""
    channels = get_channels()
    return channel_id in channels
    
def is_channel_owner(channel_id: str, user_id: int) -> bool:
    """Check if a user owns a specific channel.
    
    Args:
        channel_id: The ID of the channel
        user_id: The ID of the user
        
    Returns:
        True if the user owns the channel, False otherwise
    """
    # Check in approved channels
    channels = get_channels()
    if channel_id in channels and channels[channel_id].get("owner_id") == user_id:
        return True
    
    # Check in pending channels
    pending = get_pending_channels()
    if channel_id in pending and pending[channel_id].get("owner_id") == user_id:
        return True
        
    return False

def set_channel_reserved_position(channel_id: str, position: int) -> bool:
    """Set a reserved position for a channel in crosspost lists.
    
    Args:
        channel_id: The ID of the channel
        position: The position to reserve (1-10, or 0 to remove reservation)
        
    Returns:
        True on success, False on failure
    """
    channels = get_channels()
    
    if channel_id not in channels:
        logger.error(f"Attempted to set reserved position for non-existent channel: {channel_id}")
        return False
    
    # If position is 0, remove the reserved position
    if position == 0:
        if 'reserved_position' in channels[channel_id]:
            del channels[channel_id]['reserved_position']
            logger.info(f"Removed reserved position for channel {channel_id}")
    else:
        # Validate position (1-10)
        if position < 1 or position > 10:
            logger.error(f"Invalid position {position} for channel {channel_id}")
            return False
            
        # Set the reserved position
        channels[channel_id]['reserved_position'] = position
        logger.info(f"Set reserved position {position} for channel {channel_id}")
    
    return save_channels(channels)

def get_channels_with_reserved_positions(is_sfw: Optional[bool] = None) -> Dict[int, str]:
    """Get all channels with reserved positions.
    
    Args:
        is_sfw: If provided, filter channels by SFW/NSFW status
        
    Returns:
        Dictionary mapping position -> channel_id
    """
    channels = get_channels()
    reserved_positions = {}
    
    for channel_id, channel_data in channels.items():
        # Skip if channel doesn't have a reserved position
        if 'reserved_position' not in channel_data:
            continue
            
        # Skip if we're filtering by SFW/NSFW and this channel doesn't match
        if is_sfw is not None and channel_data.get('is_sfw', True) != is_sfw:
            continue
            
        position = channel_data['reserved_position']
        reserved_positions[position] = channel_id
    
    return reserved_positions
