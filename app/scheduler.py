import logging
import re
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app import tracing as app_tracing
from app.config import (
    GMAIL_LABEL_DEFAULT,
    GMAIL_LABEL_KEY,
    GMAIL_LOOKBACK_DAYS_DEFAULT,
    GMAIL_LOOKBACK_DAYS_KEY,
    GMAIL_PROCESSED_LABEL_DEFAULT,
    GMAIL_PROCESSED_LABEL_KEY,
    SCHEDULE_CRON_DEFAULT,
    SCHEDULE_CRON_KEY,
    SCHEDULE_ENABLED_DEFAULT,
    SCHEDULE_ENABLED_KEY,
    get_db_config,
)
from app.database import SessionLocal
from app.models import Episode, Run
from app.pipeline import ingest, process, publish
from app.pipeline.sources.gmail import GmailSource

# APScheduler's from_crontab does not remap crontab day-of-week numbers (0=Sun)
# to its internal convention (0=Mon). "1-5" in crontab means Mon-Fri, but
# APScheduler interprets it as Tue-Sat. We convert numbers to named days instead.
_CRONTAB_DOW = {
    "0": "sun", "1": "mon", "2": "tue", "3": "wed",
    "4": "thu", "5": "fri", "6": "sat", "7": "sun",
}


def make_cron_trigger(cron: str) -> CronTrigger:
    """Build a CronTrigger from a 5-field crontab string with correct day-of-week mapping."""
    parts = cron.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expected 5 cron fields, got {len(parts)}: {cron!r}")
    minute, hour, day, month, dow = parts
    # Replace bare day numbers (not step values after '/') with named equivalents.
    dow_fixed = re.sub(
        r"(?<![/\d])([0-7])(?!\d)",
        lambda m: _CRONTAB_DOW[m.group(1)],
        dow,
    )
    return CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow_fixed)


# AsyncIOScheduler runs inside uvicorn's event loop rather than a separate
# daemon thread. This means it lives and dies with the event loop — there is
# no background thread that can silently crash and stop jobs from firing.
# Sync callables (like run_pipeline) are automatically dispatched to the
# default thread-pool executor so they never block the event loop.
scheduler = AsyncIOScheduler()


class _ListHandler(logging.Handler):
    """Captures log records into a list for per-run storage."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def execute_pipeline(run_id: int) -> None:
    """Run pipeline stages for an existing Run record. Uses its own DB session."""
    handler = _ListHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    app_logger = logging.getLogger("app")
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.DEBUG)

    db = SessionLocal()
    run = None
    try:
        run = db.get(Run, run_id)
        gmail_cfg = {
            "label": get_db_config(db, GMAIL_LABEL_KEY, GMAIL_LABEL_DEFAULT),
            "processed_label": get_db_config(
                db, GMAIL_PROCESSED_LABEL_KEY, GMAIL_PROCESSED_LABEL_DEFAULT
            ),
            "lookback_days": int(
                get_db_config(db, GMAIL_LOOKBACK_DAYS_KEY, GMAIL_LOOKBACK_DAYS_DEFAULT)
            ),
        }
        sources = [GmailSource(db=db, cfg=gmail_cfg)]
        with app_tracing.span("pipeline", attributes={"run_id": run_id}):
            ingest.run(db, run, sources)
            if not run.newsletters_found:
                app_logger.info("No newsletters found — skipping processing")
                for source in sources:
                    source.mark_processed()
                run.status = "success"
                return
            process.run(db, run)
            episode = db.query(Episode).filter(Episode.run_id == run.id).first()
            if episode:
                publish.run(db, episode)
        for source in sources:
            source.mark_processed()
        run.status = "success"
    except Exception as exc:
        if run is not None:
            run.status = "error"
        app_logger.error("Pipeline failed: %s", exc, exc_info=True)
        raise
    finally:
        app_logger.removeHandler(handler)
        if run is not None:
            run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            run.log = "\n".join(handler.lines)
            db.commit()
        db.close()


def run_pipeline() -> None:
    """Called by APScheduler. Creates a Run record then executes the pipeline."""
    db = SessionLocal()
    try:
        run = Run(started_at=datetime.now(timezone.utc).replace(tzinfo=None), status="running")
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    execute_pipeline(run_id)


def start_scheduler() -> None:
    """Start the scheduler with the cron expression from DB config."""
    db = SessionLocal()
    try:
        cron = get_db_config(db, SCHEDULE_CRON_KEY, SCHEDULE_CRON_DEFAULT)
        enabled = get_db_config(db, SCHEDULE_ENABLED_KEY, SCHEDULE_ENABLED_DEFAULT) == "true"
    finally:
        db.close()

    scheduler.add_job(run_pipeline, make_cron_trigger(cron), id="pipeline")
    if not enabled:
        scheduler.pause_job("pipeline")
    scheduler.start()


def get_scheduler_status() -> dict:
    """Return the live state of the pipeline scheduler job.

    Returns a dict with:
      running       – whether the scheduler process is alive
      paused        – True if the job exists but has no next fire time
      next_run_time – aware datetime of the next scheduled fire, or None
    """
    if not scheduler.running:
        return {"running": False, "paused": True, "next_run_time": None}
    job = scheduler.get_job("pipeline")
    if job is None:
        return {"running": True, "paused": True, "next_run_time": None}
    return {
        "running": True,
        "paused": job.next_run_time is None,
        "next_run_time": job.next_run_time,  # timezone-aware datetime or None
    }


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
