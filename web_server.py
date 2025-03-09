#!/usr/bin/env python
import os
import threading
import logging
from dotenv import load_dotenv
from server import app

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

def initialize_bot():
    """Initialize the bot without starting polling."""
    try:
        import bot as bot_module
        
        # Use the initialize function from bot.py
        bot_instance = bot_module.initialize()
        if not bot_instance:
            logger.error("Failed to initialize bot")
            return None
            
        return bot_instance
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")
        return None

def run_bot(bot_instance):
    """Run the bot in a separate thread."""
    try:
        logger.info("Starting bot polling in separate thread")
        bot_instance.polling(none_stop=True, interval=0)
    except Exception as e:
        logger.error(f"Error in bot polling: {e}")

def main():
    """Run the web server and bot."""
    # Create directories if they don't exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Check if ADMIN_PASSWORD is set
    if not os.getenv("ADMIN_PASSWORD"):
        logger.warning("ADMIN_PASSWORD environment variable not set. Using default password 'admin'.")
        os.environ["ADMIN_PASSWORD"] = "admin"
    
    # Check if FLASK_SECRET_KEY is set
    if not os.getenv("FLASK_SECRET_KEY"):
        logger.warning("FLASK_SECRET_KEY environment variable not set. Generating a random key.")
        os.environ["FLASK_SECRET_KEY"] = os.urandom(24).hex()
    
    # Initialize the bot
    bot_instance = initialize_bot()
    if bot_instance:
        # Start the bot polling in a separate thread
        bot_thread = threading.Thread(target=run_bot, args=(bot_instance,))
        bot_thread.daemon = True
        bot_thread.start()
    
    # Start the web server
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()