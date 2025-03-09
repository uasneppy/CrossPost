#!/bin/bash
# Restart script for the Ukrainian TG Community Bot
# This script provides different options for starting the bot

# Function to print usage information
function print_usage {
    echo "Usage: ./restart.sh [option]"
    echo "Options:"
    echo "  prod        - Start in production mode (uWSGI with full features)"
    echo "  simple      - Start with simplified uWSGI configuration"
    echo "  diagnostic  - Start with diagnostic script"
    echo "  web         - Start just the web server"
    echo "  bot         - Start just the bot"
    echo "  combined    - Start web server and bot combined (development mode)"
    echo "  help        - Show this help message"
    echo ""
}

# Check if logs directory exists, create if not
if [ ! -d "logs" ]; then
    mkdir logs
    echo "Created logs directory"
fi

# Check if data directory exists, create if not
if [ ! -d "data" ]; then
    mkdir data
    echo "Created data directory"
fi

# Ensure script is executable
chmod +x start.py

# Process command-line arguments
case "$1" in
    prod)
        echo "Starting in production mode..."
        uwsgi --ini uwsgi.ini
        ;;
    simple)
        echo "Starting with simplified uWSGI configuration..."
        uwsgi --ini uwsgi_simple.ini
        ;;
    diagnostic)
        echo "Starting with diagnostic script..."
        python start.py
        ;;
    web)
        echo "Starting just the web server..."
        python server.py
        ;;
    bot)
        echo "Starting just the bot..."
        python bot.py
        ;;
    combined)
        echo "Starting web server and bot combined (development mode)..."
        python web_server.py
        ;;
    "" | help)
        print_usage
        ;;
    *)
        echo "Unknown option: $1"
        print_usage
        exit 1
        ;;
esac