import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.app_config import get_app_config
from app.database import SessionLocal
from app.models import Run
from app.pipeline import ingest, process
from app.pipeline.sources.gmail import GmailSource

scheduler = BackgroundScheduler()


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
        cfg = get_app_config()
        sources = [GmailSource(db=db, cfg=cfg["gmail"])]
        ingest.run(db, run, sources)
        if not run.newsletters_found:
            app_logger.info("No newsletters found — skipping processing")
            run.status = "success"
            return
        process.run(db, run)
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
    """Start the scheduler with the cron expression from config."""
    cfg = get_app_config()
    schedule_cfg = cfg.get("schedule", {})
    cron = schedule_cfg.get("cron", "0 7 * * 1-5")
    enabled = schedule_cfg.get("enabled", True)
    scheduler.add_job(run_pipeline, CronTrigger.from_crontab(cron), id="pipeline")
    if not enabled:
        scheduler.pause_job("pipeline")
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
