import logging
import random
from datetime import datetime, time, timedelta
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

import config
from utils import storage
from utils.crosspost import create_and_send_crosspost, update_all_channel_subscribers

logger = logging.getLogger(__name__)

# Create a pytz timezone for Kyiv instead of using ZoneInfo
KYIV_TIMEZONE_PYTZ = pytz.timezone('Europe/Kiev')

# Global scheduler instance
scheduler = BackgroundScheduler(timezone=KYIV_TIMEZONE_PYTZ)

def init_scheduler():
    """Initialize the scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
        
        # Schedule daily crosspost
        scheduler.add_job(
            schedule_daily_crosspost,
            CronTrigger(hour=0, minute=0, timezone=KYIV_TIMEZONE_PYTZ),  # Run at midnight to schedule for the day
            id='schedule_daily_crosspost',
            replace_existing=True
        )
        
        # Schedule hourly subscriber count updates
        scheduler.add_job(
            update_all_channel_subscribers,
            CronTrigger(minute=0, timezone=KYIV_TIMEZONE_PYTZ),  # Run at the start of every hour
            id='update_subscribers',
            replace_existing=True
        )
        
        # Call it immediately to set up today's schedule
        schedule_daily_crosspost()
        
        # Also update subscriber counts immediately on startup
        update_all_channel_subscribers()

def schedule_daily_crosspost():
    """Schedule the crosspost for today at exactly 6 PM Kyiv time."""
    # Get current date in Kyiv timezone
    now = datetime.now(KYIV_TIMEZONE_PYTZ)
    today_day_of_week = now.weekday()  # 0-6 (Monday to Sunday)
    
    # Get the channels that participate in crossposting today
    active_channels = storage.get_channels_for_day(today_day_of_week)
    
    if not active_channels:
        logger.info(f"No active channels for today (day {today_day_of_week})")
        return
    
    # Set the exact time to 6:00 PM (18:00) Kyiv time
    target_time = time(18, 0, 0)  # 6:00 PM exactly
    post_time = KYIV_TIMEZONE_PYTZ.localize(datetime.combine(now.date(), target_time))
    
    # If current time is already past 6 PM, skip today
    if now.time() > target_time:
        logger.info("Current time is past 6 PM Kyiv time, skipping today")
        return
    
    logger.info(f"Scheduling crosspost for exactly 6 PM Kyiv time: {post_time}")
    
    # Schedule the crosspost
    scheduler.add_job(
        create_and_send_crosspost,
        DateTrigger(run_date=post_time, timezone=KYIV_TIMEZONE_PYTZ),
        id='daily_crosspost',
        replace_existing=True,
        args=[active_channels]
    )

def schedule_immediate_crosspost(active_channels: Optional[List[str]] = None):
    """Schedule a crosspost to happen immediately."""
    logger.info("Scheduling immediate crosspost")
    
    if active_channels is None:
        # Get current day of week
        today_day_of_week = datetime.now(KYIV_TIMEZONE_PYTZ).weekday()
        active_channels = storage.get_channels_for_day(today_day_of_week)
    
    if not active_channels:
        logger.warning("No active channels for immediate crosspost")
        return False
    
    logger.info(f"Found {len(active_channels)} active channels for immediate crosspost")
    
    # Instead of scheduling, run immediately for manual trigger
    try:
        # Import here to avoid circular imports
        from utils.crosspost import create_and_send_crosspost
        
        # Execute directly for immediate feedback
        create_and_send_crosspost(active_channels)
        logger.info("Successfully executed manual crosspost")
        return True
    except Exception as e:
        logger.error(f"Failed to execute manual crosspost: {e}")
        return False
