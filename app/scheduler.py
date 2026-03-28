from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()


def run_pipeline() -> None:
    """Entry point called by APScheduler. Runs ingest → process → publish."""
    # TODO: import and call pipeline stages in sequence
    # from app.pipeline import ingest, process, publish
    # run = ingest.run()
    # process.run(run)
    # publish.run(run)
    pass


def start_scheduler() -> None:
    """Start the scheduler with the cron expression from DB config."""
    # TODO: read cron expression from DB config table
    default_cron = "0 7 * * 1-5"  # weekdays at 07:00
    scheduler.add_job(run_pipeline, CronTrigger.from_crontab(default_cron), id="pipeline")
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
