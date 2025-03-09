# Troubleshooting Guide

This guide provides solutions for common issues when deploying the Ukrainian TG Community Bot.

## Internal Server Error (500)

If you're getting a 500 Internal Server Error when starting with uWSGI, try these steps:

1. **Check environment variables**

   Make sure you have set the required environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token_here"
   export ADMIN_PASSWORD="your_admin_password"  # defaults to 'admin' if not set
   export FLASK_SECRET_KEY="your_secret_key"    # generated randomly if not set
   ```

2. **Check logs**

   Look at the logs for detailed error information:
   ```bash
   cat logs/uwsgi.log
   cat logs/uwsgi-errors.log
   cat logs/uwsgi-startup.log
   cat logs/web.log
   ```

3. **Try the simple configuration**

   Use the simplified uWSGI configuration:
   ```bash
   uwsgi --ini uwsgi_simple.ini
   ```

4. **Try running with the diagnostic script**

   Use our diagnostic start script:
   ```bash
   python start.py
   ```

5. **Try running without uWSGI**

   Test if the Flask app runs directly:
   ```bash
   python server.py
   ```

   Test if the combined app (web+bot) runs directly:
   ```bash
   python web_server.py
   ```

## Authentication Issues

If you're having problems with authentication:

1. **Reset credentials**

   Set a simple password for testing:
   ```bash
   export ADMIN_PASSWORD="admin"
   ```

2. **Clear browser cache**

   Your browser might be caching failed authentication attempts.

3. **Check the log**

   Look for authentication-related messages in the logs.

## Bot Not Working

If the Telegram bot isn't responding:

1. **Verify token**

   Make sure your `TELEGRAM_BOT_TOKEN` is correctly set and valid.

2. **Check logs**

   Look for bot-specific errors in `logs/bot.log` and `logs/web.log`.

3. **Check internet connectivity**

   Make sure your server can reach api.telegram.org.

4. **Try running bot separately**

   Test the bot component in isolation:
   ```bash
   python bot.py
   ```

## Permission Issues

If you're experiencing permission problems:

1. **Check directory permissions**

   Make sure all directories are writable:
   ```bash
   chmod -R 755 ./logs
   chmod -R 755 ./data
   chmod -R 755 ./static
   chmod -R 755 ./templates
   ```

2. **Create missing directories**

   Ensure all required directories exist:
   ```bash
   mkdir -p logs data static templates
   ```

## Missing Dependencies

If you're missing dependencies:

1. **Install all required packages**

   ```bash
   pip install -r project_requirements.txt
   ```

2. **Check for system dependencies**

   Some packages may require system libraries.

## Specific Cloud Provider Issues

### Replit

- Make sure your secrets are properly set in the Replit secrets panel.
- Use port 5000 as it's the default for Replit.

### DigitalOcean / AWS / GCP

- Check firewall settings to ensure port 5000 is accessible.
- Consider using a proper reverse proxy like Nginx for production.

### Shared Hosting

- Many shared hosts don't support long-running processes. Consider using a VPS instead.

## Advanced Troubleshooting

If you're still having issues:

1. **Enable debug mode temporarily**

   Edit server.py to set debug=True (but remember to set it back to False for production).

2. **Check thread management**

   If the bot works alone but not with uWSGI, there might be threading issues.

3. **Examine uwsgi.ini**

   Try adjusting the number of processes and threads if your server has limited resources.

4. **Check system resources**

   Make sure you have enough RAM and CPU available.

## Getting Help

If you're still experiencing issues after trying these solutions:

1. Open an issue on the project repository with detailed error logs.
2. Include information about your deployment environment.
3. List the steps you've already taken to troubleshoot.