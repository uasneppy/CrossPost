import os
from datetime import time
from zoneinfo import ZoneInfo

import pytz

# Telegram Bot API token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Admin user IDs (comma-separated list of Telegram user IDs)
# Support both environment variable and hardcoded admin IDs
env_admins = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "").split(",") if id_str]
ADMIN_IDS = env_admins + [1336308262]  # Adding your Telegram ID

# Path for storing data
DATA_DIR = "data"
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
PENDING_FILE = os.path.join(DATA_DIR, "pending.json")
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.json")

# Crossposting settings
MAX_CHANNELS_PER_POST = 10
KYIV_TIMEZONE = ZoneInfo("Europe/Kiev")  # For Python 3.9+ compatibility 
CROSSPOST_START_TIME = time(15, 0, 0)  # 3:00 PM Kyiv time
CROSSPOST_END_TIME = time(18, 0, 0)    # 6:00 PM Kyiv time

# Default message text
CROSSPOST_HEADER = "Українське ТҐ-Комʼюніті Презентує:"
CROSSPOST_HEADER_SFW = "Українське ТҐ-Комʼюніті Презентує: SFW Канали"
CROSSPOST_HEADER_NSFW = "Українське ТҐ-Комʼюніті Презентує: NSFW Канали 🔞"
CTA_BUTTON_TEXT = "Додати Свій Канал"

# Command descriptions
COMMANDS = {
    "start": "Start using the bot",
    "help": "Show help information",
    "apply": "Apply to add your channel to the crossposting network",
    "settings": "Manage your channel's crossposting settings",
    "schedule": "Set your channel's crossposting schedule",
    "status": "Check your channel's status",
}

# Admin commands
ADMIN_COMMANDS = {
    "admin": "Open admin control panel",
    "approve": "Approve a pending channel",
    "reject": "Reject a pending channel",
    "remove": "Remove a channel from the network",
    "list": "List all channels or pending applications",
    "post": "Manually trigger a crosspost",
    "stats": "View network statistics",
}

# Application states
class States:
    CHANNEL_APPLICATION = "CHANNEL_APPLICATION"
    WAITING_CHANNEL = "WAITING_CHANNEL"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    WAITING_SFW_NSFW = "WAITING_SFW_NSFW"
    WAITING_EMOJI = "WAITING_EMOJI"
    WAITING_SCHEDULE = "WAITING_SCHEDULE"
    
    # Admin states
    ADMIN_APPROVE = "ADMIN_APPROVE"
    ADMIN_REJECT = "ADMIN_REJECT"
    ADMIN_REMOVE = "ADMIN_REMOVE"
