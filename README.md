# Ukrainian Telegram Community Crossposting Bot

A sophisticated Telegram bot designed to manage cross-posting between Ukrainian channels, with intelligent subscriber-based prioritization and automated scheduling.

## Features

- **Automated Daily Crossposting**: Posts channel promotions every day at exactly 6 PM Kyiv time
- **Smart Channel Prioritization**: Smaller channels (<300 subscribers) get priority placement in positions 1-5
- **Position Reservation System**: Admins can reserve specific positions (1-10) for important channels
- **SFW/NSFW Content Separation**: Separate handling for SFW and NSFW channels with distinct visuals
- **Channel Verification System**: All channels must be manually approved by the bot owner
- **Admin Control Panel**: Comprehensive management interface for all network operations
- **Fair Promotion**: Channels never see themselves in their own crosspost
- **Web Interface**: User-friendly web dashboard for channel management and analytics

## Setup

1. Set the following environment variables:
   - `TELEGRAM_BOT_TOKEN` - Your bot token from [@BotFather](https://t.me/BotFather)
   - `ADMIN_PASSWORD` - Password for web interface access (defaults to 'admin' if not set)
   - `FLASK_SECRET_KEY` - Secret key for Flask sessions (generated randomly if not set)
   - `PORT` - Web server port (defaults to 5000)

2. Install dependencies:
   ```
   pip install -r project_requirements.txt
   ```

3. Run the bot with web interface:
   ```
   python web_server.py
   ```
   
   Or run just the bot without web interface:
   ```
   python bot.py
   ```

## Admin Commands (Telegram)

- `/admin` - Open the admin control panel
- `/list` - List all approved channels
- `/list pending` - List all pending channel applications
- `/approve` - Approve a pending channel application
- `/reject` - Reject a pending channel application
- `/remove` - Remove an approved channel
- `/post` - Manually trigger a crosspost
- `/stats` - View network statistics

When managing a channel, admins can:
- Set a reserved position (1-10) for the channel in crosspost lists
- Clear a channel's reserved position
- View which position is currently reserved for each channel

## User Commands (Telegram)

- `/start` - Start interacting with the bot
- `/help` - Get help information
- `/apply` - Start the channel application process
- `/settings` - Manage your channel settings
- `/schedule` - Manage your channel's crossposting schedule
- `/status` - Check your channel's status

## Web Interface

The web interface provides an easier way to manage channels and view statistics:

- **Dashboard**: View network statistics and recent activities
- **Channels**: List, view, edit, and remove approved channels
- **Pending Applications**: Review and approve/reject pending channel applications
- **Channel Schedule**: Manage which days each channel participates in crossposting
- **Mobile-Friendly**: Responsive design works on desktop and mobile devices

Access the web interface at `http://yourdomain:port/` (default: `http://localhost:5000/`)

## Dependencies

- pyTelegramBotAPI (>=4.26.0)
- APScheduler (==3.6.3)
- pytz (>=2025.1)
- Flask (>=3.1.0)
- Flask-WTF (>=1.2.0)
- python-dotenv (>=1.0.0)

## Post Format

Each crosspost includes:
- "Українське ТҐ-Комʼюніті Презентує:" header
- A list of channels (max 10), selected according to these rules:
  - Channels with reserved positions (1-10) get those exact spots
  - Remaining positions prioritize smaller channels (<300 subscribers) in positions 1-5
  - Larger channels fill the remaining positions
- Custom emoji for each channel
- A call-to-action button

## Production Deployment with uWSGI

For production environments, the project is configured to use uWSGI, a high-performance application server:

1. Install uWSGI:
   ```
   pip install uwsgi
   ```

2. Run the application with uWSGI:
   ```
   uwsgi --ini uwsgi.ini
   ```

3. For troubleshooting, you can use the simplified configuration:
   ```
   uwsgi --ini uwsgi_simple.ini
   ```

4. Or use the diagnostic startup script:
   ```
   python start.py
   ```

This provides several advantages over the development server:
- Multi-process and multi-threaded capabilities for better performance
- Process monitoring and auto-restart for reliability
- Socket management for integration with Nginx or Apache
- Memory management and optimization
- Watchdog mechanisms to prevent application freezes
- Detailed logging and statistics collection

To customize the uWSGI configuration, edit the `uwsgi.ini` file. The default configuration includes:
- 4 worker processes with 2 threads each
- HTTP access on port 5000
- Automatic process monitoring
- Detailed logging to `./logs/uwsgi.log`
- Stats server for monitoring
- Automatic reload on Python code changes

## Production Deployment on Cloud Platforms

### Replit

To deploy on Replit:

1. Set up the required secrets in the Replit Secrets panel:
   - `TELEGRAM_BOT_TOKEN`
   - `ADMIN_PASSWORD` (optional)
   - `FLASK_SECRET_KEY` (optional)

2. Configure `web-interface-workflow` to run the application:
   ```
   uwsgi --ini uwsgi.ini
   ```

3. If you encounter issues, try the simplified configuration:
   ```
   uwsgi --ini uwsgi_simple.ini
   ```

### DigitalOcean, AWS, GCP, or Azure

For deployment on major cloud platforms:

1. Set up environment variables through the platform's environment management:
   - `TELEGRAM_BOT_TOKEN`
   - `ADMIN_PASSWORD`
   - `FLASK_SECRET_KEY`

2. For optimal security and performance, use a reverse proxy:
   
   Example Nginx configuration:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           include uwsgi_params;
           uwsgi_pass 127.0.0.1:5000;
       }
       
       location /static {
           alias /path/to/app/static;
       }
   }
   ```

3. Set up a process manager to ensure the application runs continuously:
   
   Example systemd service file (/etc/systemd/system/tg-community-bot.service):
   ```ini
   [Unit]
   Description=Ukrainian TG Community Bot
   After=network.target
   
   [Service]
   User=yourusername
   WorkingDirectory=/path/to/app
   Environment="TELEGRAM_BOT_TOKEN=your_token_here"
   Environment="ADMIN_PASSWORD=your_password_here"
   ExecStart=/usr/local/bin/uwsgi --ini uwsgi.ini
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

## Troubleshooting

If you encounter issues during deployment, please refer to the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) document for detailed solutions to common problems.

Key troubleshooting steps:
1. Check the logs in the `logs/` directory
2. Verify environment variables are correctly set
3. Try the simplified configuration with `uwsgi_simple.ini`
4. Run the diagnostic script with `python start.py`

For persistent issues, you can run each component separately to isolate the problem:
- Web server only: `python server.py`
- Bot only: `python bot.py`
- Combined with verbose logging: `python web_server.py`