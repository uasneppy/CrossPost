#!/usr/bin/env python
"""
Simple startup script to run the uWSGI server with better error handling.
This can help diagnose issues when deploying to a new environment.
"""
import os
import sys
import time
import subprocess
import logging

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/startup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("startup")

def ensure_directories():
    """Ensure all required directories exist."""
    logger.info("Creating required directories...")
    directories = ['logs', 'data', 'static', 'templates']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    logger.info("Directories created successfully")

def check_environment():
    """Check if the environment is properly configured."""
    logger.info("Checking environment variables...")
    
    # Check for required environment variables
    missing_vars = []
    
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        missing_vars.append("TELEGRAM_BOT_TOKEN")
        logger.warning("TELEGRAM_BOT_TOKEN environment variable not set.")
    
    if not os.getenv("ADMIN_PASSWORD"):
        logger.warning("ADMIN_PASSWORD environment variable not set. Using default password 'admin'.")
        os.environ["ADMIN_PASSWORD"] = "admin"
    
    if not os.getenv("FLASK_SECRET_KEY"):
        logger.warning("FLASK_SECRET_KEY environment variable not set. Generating a random key.")
        os.environ["FLASK_SECRET_KEY"] = os.urandom(24).hex()
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("Environment check completed")
    return True

def check_files():
    """Check if all required files are present."""
    logger.info("Checking required files...")
    
    required_files = [
        'server.py',
        'bot.py',
        'web_server.py',
        'uwsgi.ini',
        'utils/storage.py',
        'utils/crosspost.py',
        'utils/scheduler.py',
        'handlers/admin.py',
        'handlers/channel.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {', '.join(missing_files)}")
        return False
    
    logger.info("File check completed")
    return True

def start_server():
    """Start the uWSGI server with better error handling."""
    logger.info("Starting uWSGI server...")
    
    try:
        # Try running directly with Python first to catch any Python errors
        logger.info("Testing server.py with Python interpreter...")
        result = subprocess.run(
            [sys.executable, 'server.py'],
            capture_output=True,
            text=True,
            timeout=5  # We just want to test if it starts, not run it fully
        )
        
        if result.returncode != 0:
            logger.error(f"server.py test failed with return code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False
        
        logger.info("server.py test successful")
        
        # Now try running web_server.py to test bot initialization
        logger.info("Testing web_server.py with Python interpreter...")
        # Don't actually run it, just import to check for errors
        import web_server
        logger.info("web_server.py imported successfully")
        
        # Now start uWSGI
        logger.info("Starting uWSGI...")
        cmd = ["uwsgi", "--ini", "uwsgi.ini"]
        
        # We don't capture output here as uWSGI will handle its own logging
        # Just start it and let it run
        process = subprocess.Popen(cmd)
        
        # Wait a bit to make sure it starts successfully
        time.sleep(5)
        
        if process.poll() is not None:
            # If process.poll() returns something, the process has terminated
            logger.error(f"uWSGI terminated unexpectedly with return code {process.returncode}")
            return False
        
        logger.info("uWSGI server started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point for the script."""
    logger.info("Starting up the application...")
    
    ensure_directories()
    
    if not check_environment():
        logger.error("Environment check failed. Please fix the issues and try again.")
        return
    
    if not check_files():
        logger.error("File check failed. Please fix the issues and try again.")
        return
    
    if not start_server():
        logger.error("Server startup failed. Please check the logs for details.")
        return
    
    logger.info("Application startup completed successfully")

if __name__ == "__main__":
    main()