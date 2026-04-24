"""HTMX web UI routes."""

import markdown as md
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import CONFIG_DEFAULTS, get_db_config, set_db_config
from app.database import get_db
from app.models import Episode, Run
from app.scheduler import get_scheduler_status

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
        {
            "last_run": last_run,
            "episode_count": episode_count,
            "latest_episode": latest_episode,
            "scheduler_status": get_scheduler_status(),
        },
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


@router.delete("/episodes/{episode_id}")
async def episode_delete(episode_id: int, db: Session = Depends(get_db)):
    from pathlib import Path

    from fastapi import HTTPException

    episode = db.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")

    if episode.audio_path:
        try:
            Path(episode.audio_path).unlink(missing_ok=True)
        except OSError:
            pass  # best-effort cleanup

    db.delete(episode)
    db.commit()
    return Response(status_code=204)


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, db: Session = Depends(get_db), saved: bool = False):
    from app.gmail_auth import get_credentials

    creds = get_credentials()
    gmail_connected = creds is not None and creds.valid

    feed_token = get_db_config(db, "feed.token")
    base = str(request.base_url).rstrip("/")
    feed_url = f"{base}/api/feed/{feed_token}" if feed_token else ""

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "gmail_connected": gmail_connected,
            "saved": saved,
            "gmail_label": get_db_config(db, "gmail.label"),
            "gmail_processed_label": get_db_config(db, "gmail.processed_label"),
            "gmail_lookback_days": get_db_config(db, "gmail.lookback_days"),
            "llm_provider": get_db_config(db, "llm.provider"),
            "llm_model": get_db_config(db, "llm.model"),
            "llm_prompt": get_db_config(db, "llm.prompt"),
            "llm_base_url": get_db_config(db, "llm.openai_base_url"),
            "schedule_cron": get_db_config(db, "schedule.cron"),
            "schedule_enabled": get_db_config(db, "schedule.enabled") == "true",
            "tts_enabled": get_db_config(db, "tts.enabled") == "true",
            "tts_provider": get_db_config(db, "tts.provider"),
            "tts_voice_id": get_db_config(db, "tts.voice_id"),
            "tts_model_id": get_db_config(db, "tts.model_id"),
            "tts_openai_base_url": get_db_config(db, "tts.openai_base_url"),
            "tts_instructions": get_db_config(db, "tts.instructions"),
            "feed_enabled": get_db_config(db, "feed.enabled") == "true",
            "feed_token": feed_token,
            "feed_url": feed_url,
            "retention_enabled": get_db_config(db, "retention.enabled") == "true",
            "retention_max_days": get_db_config(db, "retention.max_days"),
            "scheduler_status": get_scheduler_status(),
        },
    )


@router.post("/settings")
async def settings_post(
    request: Request,
    db: Session = Depends(get_db),
    gmail_label: str = Form(CONFIG_DEFAULTS["gmail.label"]),
    gmail_processed_label: str = Form(CONFIG_DEFAULTS["gmail.processed_label"]),
    gmail_lookback_days: str = Form(CONFIG_DEFAULTS["gmail.lookback_days"]),
    llm_provider: str = Form(CONFIG_DEFAULTS["llm.provider"]),
    llm_model: str = Form(CONFIG_DEFAULTS["llm.model"]),
    llm_prompt: str = Form(""),
    llm_base_url: str = Form(""),
    schedule_cron: str = Form(CONFIG_DEFAULTS["schedule.cron"]),
    schedule_enabled: str | None = Form(None),
    tts_enabled: str | None = Form(None),
    tts_provider: str = Form(CONFIG_DEFAULTS["tts.provider"]),
    tts_voice_id: str = Form(""),
    tts_model_id: str = Form(CONFIG_DEFAULTS["tts.model_id"]),
    tts_openai_base_url: str = Form(""),
    tts_instructions: str = Form(CONFIG_DEFAULTS["tts.instructions"]),
    feed_enabled: str | None = Form(None),
    retention_enabled: str | None = Form(None),
    retention_max_days: str = Form(CONFIG_DEFAULTS["retention.max_days"]),
):
    import secrets

    set_db_config(db, "gmail.label", gmail_label.strip())
    set_db_config(db, "gmail.processed_label", gmail_processed_label.strip())
    set_db_config(db, "gmail.lookback_days", gmail_lookback_days.strip())
    set_db_config(db, "llm.provider", llm_provider.strip())
    set_db_config(db, "llm.model", llm_model.strip())
    set_db_config(db, "llm.prompt", llm_prompt.strip())
    set_db_config(db, "llm.openai_base_url", llm_base_url.strip())

    enabled = schedule_enabled is not None
    set_db_config(db, "schedule.cron", schedule_cron.strip())
    set_db_config(db, "schedule.enabled", "true" if enabled else "false")
    _reschedule(schedule_cron.strip(), enabled=enabled)

    set_db_config(db, "tts.enabled", "true" if tts_enabled is not None else "false")
    set_db_config(db, "tts.provider", tts_provider.strip())
    set_db_config(db, "tts.voice_id", tts_voice_id.strip())
    set_db_config(db, "tts.model_id", tts_model_id.strip())
    set_db_config(db, "tts.openai_base_url", tts_openai_base_url.strip())
    set_db_config(db, "tts.instructions", tts_instructions.strip())

    feed_on = feed_enabled is not None
    set_db_config(db, "feed.enabled", "true" if feed_on else "false")
    if feed_on and not get_db_config(db, "feed.token"):
        set_db_config(db, "feed.token", secrets.token_urlsafe(32))

    set_db_config(db, "retention.enabled", "true" if retention_enabled is not None else "false")
    set_db_config(db, "retention.max_days", retention_max_days.strip())

    return RedirectResponse("/settings?saved=1", status_code=303)


@router.post("/settings/feed/regenerate-token")
async def regenerate_feed_token(request: Request, db: Session = Depends(get_db)):
    import secrets

    set_db_config(db, "feed.token", secrets.token_urlsafe(32))
    set_db_config(db, "feed.enabled", "true")
    if request.headers.get("HX-Request"):
        return Response(headers={"HX-Redirect": "/settings?saved=1"})
    return RedirectResponse("/settings?saved=1", status_code=303)


def _reschedule(cron: str, enabled: bool = True) -> None:
    """Update the running APScheduler job with the new cron/enabled state."""
    from app.scheduler import make_cron_trigger, scheduler

    try:
        scheduler.reschedule_job("pipeline", trigger=make_cron_trigger(cron))
        if enabled:
            scheduler.resume_job("pipeline")
        else:
            scheduler.pause_job("pipeline")
    except Exception:
        pass  # scheduler may not be running in test/dev contexts


@router.get("/run-log", response_class=HTMLResponse)
async def run_log(request: Request, db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(Run.started_at.desc()).limit(50).all()
    has_running = any(r.status == "running" for r in runs)
    return templates.TemplateResponse(
        request, "run_log.html", {"runs": runs, "has_running": has_running}
    )


@router.get("/partials/last-run", response_class=HTMLResponse)
async def last_run_partial(request: Request, db: Session = Depends(get_db)):
    last_run = db.query(Run).order_by(Run.started_at.desc()).first()
    response = templates.TemplateResponse(
        request,
        "partials/last_run.html",
        {"last_run": last_run, "scheduler_status": get_scheduler_status()},
    )
    if last_run and last_run.status == "running":
        response.headers["HX-Reswap"] = "none"
    return response


@router.get("/partials/run-log-rows", response_class=HTMLResponse)
async def run_log_rows_partial(request: Request, db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(Run.started_at.desc()).limit(50).all()
    has_running = any(r.status == "running" for r in runs)
    response = templates.TemplateResponse(
        request, "partials/run_log_tbody.html", {"runs": runs, "has_running": has_running}
    )
    if has_running:
        response.headers["HX-Reswap"] = "none"
    return response


@router.get("/partials/run-detail/{run_id}", response_class=HTMLResponse)
async def run_detail_partial(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")
    response = templates.TemplateResponse(request, "partials/run_detail_content.html", {"run": run})
    if run.status == "running":
        response.headers["HX-Reswap"] = "none"
    return response


@router.get("/run-log/{run_id}", response_class=HTMLResponse)
async def run_detail(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")
    return templates.TemplateResponse(request, "run_detail.html", {"run": run})
