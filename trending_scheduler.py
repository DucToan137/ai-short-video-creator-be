"""
Background scheduler to automatically fetch trending topics from internet
Run this as a background service or cron job
"""
import asyncio
import schedule
import time
import logging
from datetime import datetime
from services.trending_topics import fetch_and_update_internet_trends
from config.mongodb_config import test_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("trending_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def update_trends_job():
    """Job to update trending topics"""
    try:
        logger.info(f"Starting trending topics update at {datetime.now()}")
        
        # Test connection first
        connected = await test_connection()
        if not connected:
            logger.error("Failed to connect to MongoDB")
            return
        
        # Fetch and update trends
        result = await fetch_and_update_internet_trends()
        
        if result["success"]:
            logger.info(f"Successfully updated trends: {result['message']}")
        else:
            logger.error(f"Failed to update trends: {result['message']}")
            
    except Exception as e:
        logger.error(f"Error in update trends job: {e}")

def run_async_job():
    """Wrapper to run async job in sync context"""
    asyncio.run(update_trends_job())

def setup_scheduler():
    """Setup the scheduler for automatic trend updates"""
    # Schedule updates every 2 hours
    schedule.every(2).hours.do(run_async_job)
    
    # Schedule updates at specific times (morning, afternoon, evening)
    schedule.every().day.at("08:00").do(run_async_job)
    schedule.every().day.at("14:00").do(run_async_job)
    schedule.every().day.at("20:00").do(run_async_job)
    
    logger.info("Scheduler setup complete. Will update trending topics every 2 hours and at 8:00, 14:00, 20:00 daily.")

def run_scheduler():
    """Run the scheduler"""
    setup_scheduler()
    
    # Run initial update
    logger.info("Running initial trending topics update...")
    run_async_job()
    
    # Keep running
    logger.info("Starting scheduler loop...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    logger.info("Starting Trending Topics Scheduler...")
    
    try:
        run_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
