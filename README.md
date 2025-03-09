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

## Note on Deployment

The bot must be running continuously to maintain the scheduler functionality. Consider using a service like systemd on Linux servers or a cloud hosting solution for production deployment.