"""JSON API routes."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["api"])


@router.post("/run/trigger")
async def trigger_run(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger the pipeline."""
    # TODO: enqueue pipeline via background task
    return {"status": "queued"}


@router.get("/run/status")
async def run_status(db: Session = Depends(get_db)):
    """Return the status of the most recent run."""
    # TODO: query last run from DB
    return {"status": "idle"}


@router.get("/feed/{token}/feed.xml")
async def podcast_feed(token: str, db: Session = Depends(get_db)):
    """Serve RSS 2.0 podcast feed at a hard-to-guess URL."""
    # TODO: validate token against config, generate RSS XML
    return {"error": "not implemented"}
