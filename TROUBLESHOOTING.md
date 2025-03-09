# Troubleshooting Ukrainian TG Community Bot

This guide helps you diagnose and fix common issues with the Ukrainian TG Community Bot deployment.

## Quick Start

The bot can be started in different modes using the `restart.sh` script:

```bash
# Show all available options
./restart.sh help

# Recommended for production:
./restart.sh wsgi

# For development/testing:
./restart.sh combined

# For troubleshooting:
./restart.sh simple
```

## Common Issues

### Bot not starting with uWSGI

If the bot fails to start when using uWSGI, try these steps:

1. **Check logs**: Look for error messages in the `logs` directory:
   ```bash
   tail -n 100 logs/uwsgi.log
   tail -n 100 logs/uwsgi-errors.log
   ```

2. **Try the simplified configuration**:
   ```bash
   ./restart.sh simple
   ```

3. **Try the direct WSGI mode**:
   ```bash
   ./restart.sh wsgi
   ```

4. **Verify environment variables**: Make sure `TELEGRAM_BOT_TOKEN` is set:
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   ```

5. **Check the web server directly**:
   ```bash
   ./restart.sh web
   ```

6. **Check the bot directly**:
   ```bash
   ./restart.sh bot
   ```

### Bot starts but doesn't respond to messages

1. Check if the bot is polling:
   ```bash
   grep "polling" logs/bot.log
   ```

2. Verify your bot token:
   ```bash
   # Set a new token if needed
   export TELEGRAM_BOT_TOKEN="your_new_token"
   ```

3. Restart in combined mode to see real-time logs:
   ```bash
   ./restart.sh combined
   ```

### Web Interface Issues

1. **Can't access web interface**: Make sure the server is binding to 0.0.0.0 instead of localhost:
   ```
   # This should appear in the logs
   * Running on http://0.0.0.0:5000
   ```

2. **Authentication issues**: The default admin password is 'admin' unless you set `ADMIN_PASSWORD`:
   ```bash
   export ADMIN_PASSWORD="your_secure_password"
   ```

3. **Errors loading data**: Check file permissions in the data directory:
   ```bash
   ls -la data/
   chmod 644 data/*.json
   ```

## Environment Setup

The application requires these environment variables:

```bash
# Required
export TELEGRAM_BOT_TOKEN="your_bot_token"

# Optional (defaults will be used if not provided)
export ADMIN_PASSWORD="your_web_admin_password"
export FLASK_SECRET_KEY="your_random_secret_key"
```

For production, you can add these to `/etc/environment` or use a systemd service with environment variables. We've provided two options for running as a background service:

1. **Using the provided systemd service** (recommended for production servers):
   ```bash
   # 1. Edit the service file with your actual values
   nano tg-community-bot.service
   
   # 2. Copy to systemd directory
   sudo cp tg-community-bot.service /etc/systemd/system/
   
   # 3. Reload systemd configuration
   sudo systemctl daemon-reload
   
   # 4. Enable and start the service
   sudo systemctl enable tg-community-bot
   sudo systemctl start tg-community-bot
   
   # 5. Check status
   sudo systemctl status tg-community-bot
   ```

2. **Using the included daemon script** (for systems without systemd):
   ```bash
   # Make the script executable
   chmod +x run_as_daemon.sh
   
   # Start as daemon
   ./run_as_daemon.sh start
   
   # Check status
   ./run_as_daemon.sh status
   
   # Stop daemon
   ./run_as_daemon.sh stop
   ```

## Reset Application State

If you need to reset the application state:

```bash
# Backup current data
mkdir -p data_backup
cp data/*.json data_backup/

# Reset data files
echo "{}" > data/channels.json
echo "{}" > data/pending.json
echo "{}" > data/schedule.json
```

## Contact Support

If you continue to experience issues after trying these troubleshooting steps, please contact the developers with:

1. Relevant log files from the `logs` directory
2. Information about your environment (OS, Python version)
3. Steps you've already tried to resolve the issue