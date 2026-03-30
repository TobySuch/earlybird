"""HTMX web UI routes."""

import markdown as md
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from app.auth import require_user
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
    TTS_ENABLED_DEFAULT,
    TTS_ENABLED_KEY,
    TTS_MODEL_ID_DEFAULT,
    TTS_MODEL_ID_KEY,
    TTS_VOICE_ID_DEFAULT,
    TTS_VOICE_ID_KEY,
    get_db_config,
    set_db_config,
)
from app.database import get_db
from app.llm.factory import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    LLM_MODEL_KEY,
    LLM_PROMPT_KEY,
    LLM_PROVIDER_KEY,
)
from app.models import Episode, Run

router = APIRouter(dependencies=[Depends(require_user)])
templates = Jinja2Templates(directory="templates")
templates.env.filters["markdown"] = lambda text: Markup(
    md.markdown(text or "", extensions=["nl2br"])
)


def _timeago(dt) -> str:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = int((now - dt).total_seconds())
    if diff < 60:
        return "just now"
    if diff < 3600:
        m = diff // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if diff < 86400:
        h = diff // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = diff // 86400
    return f"{d} day{'s' if d != 1 else ''} ago"


templates.env.filters["timeago"] = _timeago


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    last_run = db.query(Run).order_by(Run.started_at.desc()).first()
    episode_count = db.query(Episode).count()
    latest_episode = db.query(Episode).join(Episode.run).order_by(Run.started_at.desc()).first()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"last_run": last_run, "episode_count": episode_count, "latest_episode": latest_episode},
    )


@router.get("/episodes", response_class=HTMLResponse)
async def episodes(request: Request, db: Session = Depends(get_db)):
    episodes = db.query(Episode).join(Episode.run).order_by(Run.started_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "episodes.html", {"episodes": episodes})


@router.get("/episodes/{episode_id}/audio")
async def episode_audio(episode_id: int, db: Session = Depends(get_db)):
    from pathlib import Path

    from fastapi import HTTPException

    episode = db.get(Episode, episode_id)
    if episode is None or not episode.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    path = Path(episode.audio_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    return FileResponse(str(path), media_type="audio/mpeg")


@router.get("/episodes/{episode_id}", response_class=HTMLResponse)
async def episode_detail(episode_id: int, request: Request, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if episode is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Episode not found")
    return templates.TemplateResponse(request, "episode_detail.html", {"episode": episode})


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, db: Session = Depends(get_db), saved: bool = False):
    from app.gmail_auth import get_credentials

    creds = get_credentials()
    gmail_connected = creds is not None and creds.valid
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "gmail_connected": gmail_connected,
            "saved": saved,
            "gmail_label": get_db_config(db, GMAIL_LABEL_KEY, GMAIL_LABEL_DEFAULT),
            "gmail_processed_label": get_db_config(
                db, GMAIL_PROCESSED_LABEL_KEY, GMAIL_PROCESSED_LABEL_DEFAULT
            ),
            "gmail_lookback_days": get_db_config(
                db, GMAIL_LOOKBACK_DAYS_KEY, GMAIL_LOOKBACK_DAYS_DEFAULT
            ),
            "llm_provider": get_db_config(db, LLM_PROVIDER_KEY, DEFAULT_PROVIDER),
            "llm_model": get_db_config(db, LLM_MODEL_KEY, DEFAULT_MODEL),
            "llm_prompt": get_db_config(db, LLM_PROMPT_KEY, ""),
            "schedule_cron": get_db_config(db, SCHEDULE_CRON_KEY, SCHEDULE_CRON_DEFAULT),
            "schedule_enabled": get_db_config(db, SCHEDULE_ENABLED_KEY, SCHEDULE_ENABLED_DEFAULT)
            == "true",
            "tts_enabled": get_db_config(db, TTS_ENABLED_KEY, TTS_ENABLED_DEFAULT) == "true",
            "tts_voice_id": get_db_config(db, TTS_VOICE_ID_KEY, TTS_VOICE_ID_DEFAULT),
            "tts_model_id": get_db_config(db, TTS_MODEL_ID_KEY, TTS_MODEL_ID_DEFAULT),
            "tts_model_id_default": TTS_MODEL_ID_DEFAULT,
        },
    )


@router.post("/settings")
async def settings_post(
    request: Request,
    db: Session = Depends(get_db),
    gmail_label: str = Form(GMAIL_LABEL_DEFAULT),
    gmail_processed_label: str = Form(GMAIL_PROCESSED_LABEL_DEFAULT),
    gmail_lookback_days: str = Form(GMAIL_LOOKBACK_DAYS_DEFAULT),
    llm_provider: str = Form(DEFAULT_PROVIDER),
    llm_model: str = Form(DEFAULT_MODEL),
    llm_prompt: str = Form(""),
    schedule_cron: str = Form(SCHEDULE_CRON_DEFAULT),
    schedule_enabled: str | None = Form(None),
    tts_enabled: str | None = Form(None),
    tts_voice_id: str = Form(TTS_VOICE_ID_DEFAULT),
    tts_model_id: str = Form(TTS_MODEL_ID_DEFAULT),
):
    set_db_config(db, GMAIL_LABEL_KEY, gmail_label.strip())
    set_db_config(db, GMAIL_PROCESSED_LABEL_KEY, gmail_processed_label.strip())
    set_db_config(db, GMAIL_LOOKBACK_DAYS_KEY, gmail_lookback_days.strip())
    set_db_config(db, LLM_PROVIDER_KEY, llm_provider.strip())
    set_db_config(db, LLM_MODEL_KEY, llm_model.strip())
    set_db_config(db, LLM_PROMPT_KEY, llm_prompt.strip())

    enabled = schedule_enabled is not None
    set_db_config(db, SCHEDULE_CRON_KEY, schedule_cron.strip())
    set_db_config(db, SCHEDULE_ENABLED_KEY, "true" if enabled else "false")
    _reschedule(schedule_cron.strip(), enabled=enabled)

    set_db_config(db, TTS_ENABLED_KEY, "true" if tts_enabled is not None else "false")
    set_db_config(db, TTS_VOICE_ID_KEY, tts_voice_id.strip())
    set_db_config(db, TTS_MODEL_ID_KEY, tts_model_id.strip())

    return RedirectResponse("/settings?saved=1", status_code=303)


def _reschedule(cron: str, enabled: bool = True) -> None:
    """Update the running APScheduler job with the new cron/enabled state."""
    from apscheduler.triggers.cron import CronTrigger

    from app.scheduler import scheduler

    try:
        scheduler.reschedule_job("pipeline", trigger=CronTrigger.from_crontab(cron))
        if enabled:
            scheduler.resume_job("pipeline")
        else:
            scheduler.pause_job("pipeline")
    except Exception:
        pass  # scheduler may not be running in test/dev contexts


@router.get("/run-log", response_class=HTMLResponse)
async def run_log(request: Request, db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(Run.started_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "run_log.html", {"runs": runs})


@router.get("/run-log/{run_id}", response_class=HTMLResponse)
async def run_detail(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")
    return templates.TemplateResponse(request, "run_detail.html", {"run": run})
