#!/usr/bin/env python
"""
WSGI entry point for the application.
This file is used by uWSGI to start the application.
"""
import os
import sys
import logging
import threading
import time

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/wsgi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("wsgi")

# Log startup information
logger.info("Starting wsgi application")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")

# Import the Flask application
from server import app

# Try to start the bot in a separate thread
def start_bot_thread():
    """Start the bot in a separate thread."""
    logger.info("Starting bot thread from wsgi.py")
    
    try:
        # First explicitly set the PATH to include current directory
        sys.path.insert(0, os.getcwd())
        
        # Import bot modules
        logger.info("Importing web_server module...")
        import web_server
        logger.info("web_server module imported")
        
        # Start the bot thread
        logger.info("Starting bot thread using web_server.main()")
        thread = threading.Thread(target=web_server.main, daemon=True)
        thread.start()
        logger.info(f"Bot thread started: {thread.is_alive()}")
        
        # Write a marker file to indicate bot thread was started
        with open("logs/wsgi_bot_started.txt", "w") as f:
            f.write(f"Bot thread started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Thread alive: {thread.is_alive()}\n")
        
    except Exception as e:
        logger.error(f"Error starting bot thread: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Start the bot in a separate thread
start_bot_thread()

# Export the Flask application for uWSGI
application = app