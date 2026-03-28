"""JSON API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Run

router = APIRouter(tags=["api"])


@router.post("/run/trigger")
async def trigger_run(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger the pipeline. Creates a Run record and queues execution."""
    from app.scheduler import execute_pipeline

    run = Run(started_at=datetime.now(timezone.utc).replace(tzinfo=None), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(execute_pipeline, run.id)
    return {"status": "queued", "run_id": run.id}


@router.get("/run/status")
async def run_status(db: Session = Depends(get_db)):
    """Return the status of the most recent run."""
    run = db.query(Run).order_by(Run.started_at.desc()).first()
    if run is None:
        return {"status": "idle"}
    return {
        "status": run.status,
        "run_id": run.id,
        "started_at": run.started_at.isoformat(),
        "stories_found": run.stories_found,
    }


@router.get("/feed/{token}/feed.xml")
async def podcast_feed(token: str, db: Session = Depends(get_db)):
    """Serve RSS 2.0 podcast feed at a hard-to-guess URL."""
    # TODO: validate token against config, generate RSS XML
    return {"error": "not implemented"}
