#!/usr/bin/env python
import os
import sys
import threading
import logging
import time
import signal
import atexit
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
        # Check if token is available
        if not os.getenv("TELEGRAM_BOT_TOKEN"):
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            logger.error("Please set the TELEGRAM_BOT_TOKEN environment variable")
            return None
            
        # Try to import the bot module
        try:
            import sys
            logger.info(f"Python path: {sys.path}")
            import bot as bot_module
            logger.info("Successfully imported bot module")
        except ImportError as e:
            logger.error(f"Failed to import bot module: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        except Exception as e:
            logger.error(f"Unknown error importing bot module: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        
        # Try to initialize the bot
        try:
            logger.info("Initializing bot...")
            bot_instance = bot_module.initialize()
            
            if not bot_instance:
                logger.error("Bot initialization returned None")
                return None
                
            logger.info("Bot instance created successfully")
            return bot_instance
            
        except AttributeError as e:
            logger.error(f"Bot module doesn't have initialize function: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        except Exception as e:
            logger.error(f"Error during bot initialization: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in initialize_bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def heartbeat_middleware(bot_instance):
    """Create a middleware to update heartbeat on every bot activity."""
    # Create a wrapper for the process_new_updates method
    original_process_new_updates = bot_instance.process_new_updates
    
    def process_new_updates_with_heartbeat(updates):
        update_heartbeat()  # Update the heartbeat timestamp
        return original_process_new_updates(updates)
    
    # Replace the method with our wrapper
    bot_instance.process_new_updates = process_new_updates_with_heartbeat
    
    return bot_instance

def run_bot(bot_instance):
    """Run the bot in a separate thread with automatic reconnection and heartbeat."""
    global _heartbeat_timestamp
    
    max_retries = 10
    retry_count = 0
    retry_delay = 5  # seconds
    
    # Apply heartbeat middleware
    bot_instance = heartbeat_middleware(bot_instance)
    
    while True:
        try:
            # Update heartbeat before starting
            _heartbeat_timestamp = time.time()
            
            logger.info("Starting bot polling in separate thread")
            # Log heartbeat every minute
            last_log = time.time()
            
            # Custom polling loop to update heartbeat regularly
            bot_instance.polling(none_stop=True, interval=1, timeout=30)
            
            # If we get here, polling has stopped normally
            logger.info("Bot polling ended normally")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Error in bot polling (attempt {retry_count}/{max_retries}): {e}")
            
            # Update heartbeat to show we're still alive
            _heartbeat_timestamp = time.time()
            
            if retry_count >= max_retries:
                logger.critical("Max retries reached. Restarting bot instance...")
                # Reinitialize the bot
                try:
                    import bot as bot_module
                    new_bot_instance = bot_module.initialize()
                    if new_bot_instance:
                        # Apply heartbeat middleware to new instance
                        new_bot_instance = heartbeat_middleware(new_bot_instance)
                        bot_instance = new_bot_instance
                        logger.info("Bot instance reinitialized successfully")
                        retry_count = 0
                    else:
                        logger.error("Failed to reinitialize bot instance")
                except Exception as e:
                    logger.error(f"Error reinitializing bot: {e}")
            
            # Wait before retrying
            time.sleep(retry_delay)

# Global variables for watchdog
_bot_thread = None
_bot_instance = None
_heartbeat_timestamp = 0
_shutdown_flag = False

def watchdog_thread():
    """Monitor the bot thread and restart if needed."""
    global _bot_thread, _bot_instance, _heartbeat_timestamp, _shutdown_flag
    
    logger.info("Watchdog thread started")
    failure_count = 0
    
    while not _shutdown_flag:
        try:
            # Check if bot thread is alive
            if _bot_thread and not _bot_thread.is_alive():
                logger.warning("Bot thread is dead. Attempting to restart...")
                
                # Try to restart the bot thread
                if _bot_instance:
                    _bot_thread = threading.Thread(target=run_bot, args=(_bot_instance,), daemon=True)
                    _bot_thread.start()
                    logger.info("Bot thread restarted successfully")
                    failure_count = 0
                else:
                    logger.error("Cannot restart bot thread: no bot instance available")
                    failure_count += 1
            
            # Check if the bot hasn't sent a heartbeat in too long
            current_time = time.time()
            if _heartbeat_timestamp > 0 and (current_time - _heartbeat_timestamp) > 300:  # 5 minutes
                logger.warning(f"Bot heartbeat timeout: {current_time - _heartbeat_timestamp} seconds since last activity")
                
                # Try to restart the bot completely
                if failure_count > 3:
                    logger.critical("Multiple bot failures detected. Reinitializing bot...")
                    _bot_instance = initialize_bot()
                    if _bot_instance:
                        if _bot_thread and _bot_thread.is_alive():
                            logger.info("Stopping existing bot thread...")
                            # Let the existing thread terminate naturally
                            # The polling loop should detect exceptions and exit
                            
                        _bot_thread = threading.Thread(target=run_bot, args=(_bot_instance,), daemon=True)
                        _bot_thread.start()
                        logger.info("Bot reinitialized and restarted successfully")
                        _heartbeat_timestamp = time.time()  # Reset heartbeat
                        failure_count = 0
                    else:
                        logger.error("Failed to reinitialize bot")
                        failure_count += 1
                else:
                    failure_count += 1
            
            # Avoid high CPU usage
            time.sleep(30)
        
        except Exception as e:
            logger.error(f"Error in watchdog thread: {e}")
            time.sleep(60)  # Longer sleep on error

def update_heartbeat():
    """Update the timestamp of the bot's last activity."""
    global _heartbeat_timestamp
    _heartbeat_timestamp = time.time()

def shutdown_handler():
    """Handle graceful shutdown."""
    global _shutdown_flag
    logger.info("Shutdown requested. Cleaning up...")
    _shutdown_flag = True
    
    # Add any cleanup code here
    logger.info("Cleanup complete. Exiting.")

def main():
    """Run the web server and bot with enhanced error handling and watchdog."""
    global _bot_thread, _bot_instance, _heartbeat_timestamp, _shutdown_flag
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda sig, frame: shutdown_handler())
    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown_handler())
    atexit.register(shutdown_handler)
    
    # Create directories if they don't exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Log environment and runtime information
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Running as user: {os.getenv('USER', 'unknown')}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"TELEGRAM_BOT_TOKEN set: {'Yes' if os.getenv('TELEGRAM_BOT_TOKEN') else 'No'}")
    
    # Check if running under uWSGI
    is_uwsgi = bool(os.environ.get("UWSGI_ORIGINAL_PROC_NAME"))
    logger.info(f"Running under uWSGI: {is_uwsgi}")
    
    # Check if ADMIN_PASSWORD is set
    if not os.getenv("ADMIN_PASSWORD"):
        logger.warning("ADMIN_PASSWORD environment variable not set. Using default password 'admin'.")
        os.environ["ADMIN_PASSWORD"] = "admin"
    
    # Check if FLASK_SECRET_KEY is set
    if not os.getenv("FLASK_SECRET_KEY"):
        logger.warning("FLASK_SECRET_KEY environment variable not set. Generating a random key.")
        os.environ["FLASK_SECRET_KEY"] = os.urandom(24).hex()
    
    # Write a marker file to indicate the bot is starting
    with open("logs/bot_starting.txt", "w") as f:
        f.write(f"Bot starting at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Running under uWSGI: {is_uwsgi}\n")
    
    # Import bot modules directly to catch any import errors
    try:
        logger.info("Importing bot module...")
        import bot as bot_module
        logger.info("Bot module imported successfully")
    except Exception as e:
        logger.critical(f"Failed to import bot module: {e}")
        import traceback
        logger.critical(traceback.format_exc())
    
    # Initialize the bot with retry logic
    _bot_instance = None
    max_init_retries = 5
    for i in range(max_init_retries):
        try:
            logger.info(f"Attempting to initialize bot ({i+1}/{max_init_retries})...")
            _bot_instance = initialize_bot()
            if _bot_instance:
                logger.info(f"Bot initialized successfully on attempt {i+1}/{max_init_retries}")
                break
            else:
                logger.error(f"Bot initialization returned None on attempt {i+1}/{max_init_retries}")
        except Exception as e:
            logger.error(f"Error initializing bot on attempt {i+1}/{max_init_retries}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        if i < max_init_retries - 1:
            logger.info("Retrying bot initialization in 5 seconds...")
            time.sleep(5)
    
    if _bot_instance:
        # Initialize heartbeat
        _heartbeat_timestamp = time.time()
        
        # Start the bot polling in a separate thread
        try:
            logger.info("Starting bot thread...")
            _bot_thread = threading.Thread(target=run_bot, args=(_bot_instance,), daemon=True)
            _bot_thread.start()
            logger.info("Bot thread started successfully")
            
            # Start the watchdog thread
            watchdog = threading.Thread(target=watchdog_thread, daemon=True)
            watchdog.start()
            logger.info("Watchdog thread started")
        except Exception as e:
            logger.critical(f"Failed to start bot thread: {e}")
            import traceback
            logger.critical(traceback.format_exc())
    else:
        logger.critical("Failed to initialize bot after multiple attempts. Web server will run without bot functionality.")
    
    # Write a marker file to indicate the bot has started
    with open("logs/bot_started.txt", "w") as f:
        f.write(f"Bot started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Bot instance created: {bool(_bot_instance)}\n")
        f.write(f"Bot thread created: {bool(_bot_thread) if '_bot_thread' in locals() else False}\n")
    
    # Let uWSGI handle the web server
    # We don't need to manually start Flask as uWSGI will handle it
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Web application ready to be served on port {port}")
    
    if is_uwsgi:
        logger.info("Running under uWSGI - Flask application instance is already being served")
    else:
        # This will be reached when running directly, not through uWSGI
        logger.info("Running in direct execution mode, starting Flask server for development")
        try:
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
            shutdown_handler()
        except Exception as e:
            logger.critical(f"Web server error: {e}")
            import traceback
            logger.critical(traceback.format_exc())

if __name__ == "__main__":
    main()