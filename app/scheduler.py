import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app import tracing as app_tracing
from app.config import get_db_config
from app.database import SessionLocal
from app.models import Episode, NewsSource, Run
from app.pipeline import ingest, process, publish
from app.pipeline.sources.gmail import GmailSource

# APScheduler's from_crontab does not remap crontab day-of-week numbers (0=Sun)
# to its internal convention (0=Mon). "1-5" in crontab means Mon-Fri, but
# APScheduler interprets it as Tue-Sat. We convert numbers to named days instead.
_CRONTAB_DOW = {
    "0": "sun",
    "1": "mon",
    "2": "tue",
    "3": "wed",
    "4": "thu",
    "5": "fri",
    "6": "sat",
    "7": "sun",
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
            "label": get_db_config(db, "gmail.label"),
            "processed_label": get_db_config(db, "gmail.processed_label"),
            "lookback_days": int(get_db_config(db, "gmail.lookback_days")),
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


def run_retention() -> None:
    """Delete episodes (and their runs and sources) older than retention.max_days."""
    db = SessionLocal()
    try:
        if get_db_config(db, "retention.enabled") != "true":
            return
        max_days = int(get_db_config(db, "retention.max_days"))
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=max_days)
        old_episodes = db.query(Episode).filter(Episode.created_at < cutoff).all()
        for episode in old_episodes:
            if episode.audio_path:
                try:
                    Path(episode.audio_path).unlink(missing_ok=True)
                except OSError:
                    pass
            run_id = episode.run_id
            db.delete(episode)
            db.flush()  # remove Episode FK ref before deleting NewsSource/Run
            db.query(NewsSource).filter(NewsSource.run_id == run_id).delete()
            run = db.get(Run, run_id)
            if run is not None:
                db.delete(run)
        db.commit()
        if old_episodes:
            logging.getLogger(__name__).info("Retention: deleted %d episode(s)", len(old_episodes))
    except Exception:
        logging.getLogger(__name__).exception("Retention job failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the scheduler with the cron expression from DB config."""
    db = SessionLocal()
    try:
        cron = get_db_config(db, "schedule.cron")
        enabled = get_db_config(db, "schedule.enabled") == "true"
    finally:
        db.close()

    scheduler.add_job(run_pipeline, make_cron_trigger(cron), id="pipeline")
    if not enabled:
        scheduler.pause_job("pipeline")

    # Always register the retention job; it checks the enabled flag at runtime.
    # Fires 60 s after startup, then every 24 h.
    scheduler.add_job(
        run_retention,
        IntervalTrigger(hours=24),
        id="retention",
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=60),
    )

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
