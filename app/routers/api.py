"""JSON API routes."""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.auth import require_user_api
from app.config import (
    FEED_ENABLED_DEFAULT,
    FEED_ENABLED_KEY,
    FEED_TOKEN_DEFAULT,
    FEED_TOKEN_KEY,
    get_db_config,
    get_settings,
)
from app.database import get_db
from app.models import Episode, Run

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


def _validate_feed_token(token: str, db: Session) -> tuple[bool, bool]:
    """Return (enabled, valid_token) for the feed."""
    enabled = get_db_config(db, FEED_ENABLED_KEY, FEED_ENABLED_DEFAULT) == "true"
    stored = get_db_config(db, FEED_TOKEN_KEY, FEED_TOKEN_DEFAULT)
    return enabled, bool(stored) and stored == token


@router.get("/feed/{token}/feed.xml")
async def podcast_feed(token: str, request: Request, db: Session = Depends(get_db)):
    """Serve RSS 2.0 podcast feed at a hard-to-guess URL."""
    enabled, valid = _validate_feed_token(token, db)
    if not enabled:
        return Response(status_code=503)
    if not valid:
        return Response(status_code=404)

    episodes = (
        db.query(Episode)
        .join(Episode.run)
        .filter(Episode.audio_path.isnot(None))
        .order_by(Run.started_at.desc())
        .limit(50)
        .all()
    )

    # Use PUBLIC_BASE_URL when set (needed behind a reverse proxy like Traefik);
    # fall back to the request base_url for local dev.
    _pub = get_settings().public_base_url
    base = _pub.rstrip("/") if _pub else str(request.base_url).rstrip("/")

    itunes_ns = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    atom_ns = "http://www.w3.org/2005/Atom"
    feed_url = f"{base}/api/feed/{token}/feed.xml"

    # register_namespace alone adds xmlns declarations; don't also pass them as
    # explicit attributes or they appear twice (invalid XML).
    ET.register_namespace("itunes", itunes_ns)
    ET.register_namespace("atom", atom_ns)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")

    # Required channel fields
    ET.SubElement(channel, "title").text = "Earlybird"
    ET.SubElement(channel, "link").text = base
    ET.SubElement(channel, "description").text = "Your personalised newsletter digest, read aloud."
    ET.SubElement(channel, "language").text = "en"

    # atom:link self-reference (best practice; some validators require it)
    ET.SubElement(
        channel,
        f"{{{atom_ns}}}link",
        href=feed_url,
        rel="self",
        type="application/rss+xml",
    )

    # iTunes channel metadata required by Apple Podcasts
    ET.SubElement(channel, f"{{{itunes_ns}}}author").text = "Earlybird"
    ET.SubElement(channel, f"{{{itunes_ns}}}explicit").text = "no"
    ET.SubElement(channel, f"{{{itunes_ns}}}type").text = "episodic"
    cover_url = f"{base}/static/web-app-manifest-512x512.png"
    ET.SubElement(channel, f"{{{itunes_ns}}}image", href=cover_url)

    for episode in episodes:
        pub_dt = episode.run.started_at
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        title = f"Earlybird \u2013 {pub_dt.strftime('%B %-d, %Y')}"

        try:
            length = os.path.getsize(episode.audio_path)
        except OSError:
            length = 0

        audio_url = f"{base}/api/feed/{token}/audio/{episode.id}.mp3"

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "guid", isPermaLink="false").text = f"earlybird-episode-{episode.id}"
        ET.SubElement(item, "pubDate").text = format_datetime(pub_dt)
        ET.SubElement(item, "enclosure", url=audio_url, length=str(length), type="audio/mpeg")
        ET.SubElement(item, f"{{{itunes_ns}}}explicit").text = "no"
        if episode.newsletter_text:
            summary = episode.newsletter_text.strip()[:500]
            ET.SubElement(item, f"{{{itunes_ns}}}summary").text = summary

    xml_bytes = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode").encode()
    )
    return Response(content=xml_bytes, media_type="application/rss+xml; charset=utf-8")


@router.get("/feed/{token}/audio/{episode_id}.mp3")
async def feed_audio(token: str, episode_id: int, db: Session = Depends(get_db)):
    """Serve episode audio at a token-protected public URL for podcast clients."""
    from pathlib import Path

    from fastapi import HTTPException

    enabled, valid = _validate_feed_token(token, db)
    if not enabled:
        return Response(status_code=503)
    if not valid:
        return Response(status_code=404)

    episode = db.get(Episode, episode_id)
    if episode is None or not episode.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    path = Path(episode.audio_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    return FileResponse(str(path), media_type="audio/mpeg")
