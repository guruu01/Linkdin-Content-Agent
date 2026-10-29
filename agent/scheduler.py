import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from agent.config import settings
from agent.workflow import workflow_manager

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def scheduled_job():
    logger.info("Executing scheduled Monday Morning Content Agent Workflow...")
    try:
        workflow_manager.run_weekly_workflow()
    except Exception as e:
        logger.error(f"Scheduled workflow error: {e}")

def init_scheduler():
    if not scheduler.running:
        day_of_week = settings.WORKFLOW_SCHEDULE_DAY.lower()
        time_parts = settings.WORKFLOW_SCHEDULE_TIME.split(":")
        hour = int(time_parts[0]) if len(time_parts) > 0 else 9
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute
        )

        scheduler.add_job(
            scheduled_job,
            trigger=trigger,
            id="weekly_content_workflow",
            name="Weekly Monday Content Pipeline",
            replace_existing=True
        )

        scheduler.start()
        logger.info(f"Scheduler started: Every {day_of_week.upper()} at {hour:02d}:{minute:02d}")

def get_scheduler_status():
    if not scheduler.running:
        return {"running": False, "next_run": None}
    
    job = scheduler.get_job("weekly_content_workflow")
    next_run = str(job.next_run_time) if job and job.next_run_time else None
    return {
        "running": True,
        "schedule": f"Every {settings.WORKFLOW_SCHEDULE_DAY.upper()} at {settings.WORKFLOW_SCHEDULE_TIME}",
        "next_run": next_run
    }

