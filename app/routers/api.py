"""JSON API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.auth import require_user_api
from app.database import get_db
from app.models import Run

router = APIRouter(tags=["api"])


@router.post("/run/trigger", dependencies=[Depends(require_user_api)])
async def trigger_run(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger the pipeline. Creates a Run record and queues execution."""
    from app.scheduler import execute_pipeline

    run = Run(started_at=datetime.now(timezone.utc).replace(tzinfo=None), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(execute_pipeline, run.id)
    return {"status": "queued", "run_id": run.id}


@router.get("/run/status", dependencies=[Depends(require_user_api)])
async def run_status(db: Session = Depends(get_db)):
    """Return the status of the most recent run."""
    run = db.query(Run).order_by(Run.started_at.desc()).first()
    if run is None:
        return {"status": "idle"}
    return {
        "status": run.status,
        "run_id": run.id,
        "started_at": run.started_at.isoformat(),
        "newsletters_found": run.newsletters_found,
    }


@router.get("/unprocessed-count", dependencies=[Depends(require_user_api)])
async def unprocessed_count(db: Session = Depends(get_db)):
    """Count unprocessed Gmail messages using the same config as the pipeline."""
    from datetime import timedelta

    from app.config import (
        GMAIL_LABEL_DEFAULT,
        GMAIL_LABEL_KEY,
        GMAIL_LOOKBACK_DAYS_DEFAULT,
        GMAIL_LOOKBACK_DAYS_KEY,
        GMAIL_PROCESSED_LABEL_DEFAULT,
        GMAIL_PROCESSED_LABEL_KEY,
        get_db_config,
    )
    from app.pipeline.sources.gmail import GmailSource

    lookback_days = int(get_db_config(db, GMAIL_LOOKBACK_DAYS_KEY, GMAIL_LOOKBACK_DAYS_DEFAULT))
    cfg = {
        "label": get_db_config(db, GMAIL_LABEL_KEY, GMAIL_LABEL_DEFAULT),
        "processed_label": get_db_config(
            db, GMAIL_PROCESSED_LABEL_KEY, GMAIL_PROCESSED_LABEL_DEFAULT
        ),
        "lookback_days": lookback_days,
    }
    source = GmailSource(db=db, cfg=cfg)
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    try:
        count = source.count_unprocessed(since)
    except Exception as exc:
        return {"count": None, "error": str(exc)}

    return {"count": count}


@router.get("/feed/{token}/feed.xml")
async def podcast_feed(token: str, db: Session = Depends(get_db)):
    """Serve RSS 2.0 podcast feed at a hard-to-guess URL."""
    # TODO: validate token against config, generate RSS XML
    return {"error": "not implemented"}
