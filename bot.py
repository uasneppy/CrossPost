import os
import logging
import json
from datetime import datetime, timezone

import telebot
from telebot.types import BotCommand
from telebot.storage import StateMemoryStorage

import config
from utils.scheduler import init_scheduler
from utils.storage import ensure_data_dir
from utils.crosspost import init_bot

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot with state storage
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(config.TOKEN, state_storage=state_storage)

# Dictionary to store user states for special operations
user_dict = {}

logger.info("Bot initialized with state storage")

def setup_commands():
    """Setup bot commands."""
    # Set commands for normal users
    commands = [BotCommand(cmd, desc) for cmd, desc in config.COMMANDS.items()]
    bot.set_my_commands(commands)
    
    # Set admin commands for each admin (note: telebot doesn't support setting different commands per user)
    # This limitation is present in the telebot API
    logger.info("Admin commands will be handled based on user ID since telebot doesn't support scoped commands")

def register_handlers():
    """Register message handlers."""
    from handlers.channel import register_channel_handlers
    from handlers.admin import register_admin_handlers
    
    # Register channel handlers
    register_channel_handlers(bot)
    
    # Register admin handlers
    register_admin_handlers(bot)
    
def main() -> None:
    """Run the bot."""
    # Check if token is provided
    if not config.TOKEN:
        logger.error("No token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    # Ensure data directory exists
    ensure_data_dir()
    
    # Initialize the crosspost module with the bot
    init_bot(bot)
    
    # Register handlers
    register_handlers()
    
    # Setup commands
    setup_commands()
    
    # Initialize the scheduler
    init_scheduler()
    
    logger.info("Bot started")
    
    # Start the Bot (this should be the last step as it's blocking)
    bot.polling(none_stop=True, interval=0)

def initialize() -> telebot.TeleBot:
    """Initialize the bot without starting polling.
    
    Returns:
        The initialized bot instance.
    """
    # Check if token is provided
    if not config.TOKEN:
        logger.error("No token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return None
    
    # Ensure data directory exists
    ensure_data_dir()
    
    # Initialize the crosspost module with the bot
    init_bot(bot)
    
    # Register handlers
    register_handlers()
    
    # Setup commands
    setup_commands()
    
    # Initialize the scheduler
    init_scheduler()
    
    logger.info("Bot started")
    
    return bot

if __name__ == '__main__':
    main()
