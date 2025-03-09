#!/bin/bash
# Script to run the Ukrainian TG Community Bot as a background daemon
# This script allows the bot to continue running even when the terminal is closed

# Change to the script's directory
cd "$(dirname "$0")"

# Check if nohup is available
if ! command -v nohup &> /dev/null; then
    echo "Error: nohup command not found. Please install it or use systemd service."
    exit 1
fi

# Setup and create required directories
mkdir -p logs data

# Check for environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Warning: TELEGRAM_BOT_TOKEN environment variable not set."
    echo "You should set this variable before running the bot."
    echo "Attempting to load from .env file if it exists."
    
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
        echo "Loaded environment from .env file."
    fi
fi

# Get the process ID if the bot is already running
PID=$(pgrep -f "python web_server.py" || echo "")

if [ -n "$PID" ]; then
    echo "Bot is already running with PID $PID."
    echo "Use './run_as_daemon.sh stop' to stop it."
    exit 0
fi

# Function to start the bot as daemon
start_daemon() {
    echo "Starting Ukrainian TG Community Bot as daemon..."
    nohup python web_server.py > logs/daemon.log 2>&1 &
    PID=$!
    
    echo $PID > logs/daemon.pid
    echo "Bot started with PID $PID. Log output will be in logs/daemon.log"
    echo "Use './run_as_daemon.sh stop' to stop the bot."
}

# Function to stop the bot
stop_daemon() {
    if [ -f "logs/daemon.pid" ]; then
        PID=$(cat logs/daemon.pid)
        if ps -p $PID > /dev/null; then
            echo "Stopping bot with PID $PID..."
            kill $PID
            rm logs/daemon.pid
            echo "Bot stopped."
        else
            echo "Bot process is not running. Cleaning up..."
            rm logs/daemon.pid
        fi
    else
        PID=$(pgrep -f "python web_server.py" || echo "")
        if [ -n "$PID" ]; then
            echo "Stopping bot with PID $PID..."
            kill $PID
            echo "Bot stopped."
        else
            echo "Bot is not running."
        fi
    fi
}

# Function to check status
status_daemon() {
    if [ -f "logs/daemon.pid" ]; then
        PID=$(cat logs/daemon.pid)
        if ps -p $PID > /dev/null; then
            echo "Bot is running with PID $PID."
            echo "Log file: logs/daemon.log"
        else
            echo "Bot process is not running, but PID file exists."
            echo "The bot may have crashed or been terminated."
            echo "Check logs/daemon.log for details."
        fi
    else
        PID=$(pgrep -f "python web_server.py" || echo "")
        if [ -n "$PID" ]; then
            echo "Bot is running with PID $PID (no PID file)."
        else
            echo "Bot is not running."
        fi
    fi
}

# Process command-line arguments
case "$1" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        stop_daemon
        sleep 2
        start_daemon
        ;;
    status)
        status_daemon
        ;;
    "")
        # Default action is to start if no arguments provided
        start_daemon
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0