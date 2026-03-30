"""HTMX web UI routes."""

import markdown as md
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from app.app_config import get_app_config
from app.auth import require_user
from app.config import get_db_config, set_db_config
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


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    last_run = db.query(Run).order_by(Run.started_at.desc()).first()
    return templates.TemplateResponse(request, "dashboard.html", {"last_run": last_run})


@router.get("/episodes", response_class=HTMLResponse)
async def episodes(request: Request, db: Session = Depends(get_db)):
    episodes = db.query(Episode).join(Episode.run).order_by(Run.started_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "episodes.html", {"episodes": episodes})


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, db: Session = Depends(get_db), saved: bool = False):
    from app.gmail_auth import get_credentials

    creds = get_credentials()
    gmail_connected = creds is not None and creds.valid
    cfg = get_app_config()
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "gmail_connected": gmail_connected,
            "saved": saved,
            "llm_provider": get_db_config(db, LLM_PROVIDER_KEY, DEFAULT_PROVIDER),
            "llm_model": get_db_config(db, LLM_MODEL_KEY, DEFAULT_MODEL),
            "llm_prompt": get_db_config(db, LLM_PROMPT_KEY, ""),
            "schedule_cron": cfg.get("schedule", {}).get("cron", "0 7 * * 1-5"),
        },
    )


@router.post("/settings")
async def settings_post(
    request: Request,
    db: Session = Depends(get_db),
    llm_provider: str = Form(DEFAULT_PROVIDER),
    llm_model: str = Form(DEFAULT_MODEL),
    llm_prompt: str = Form(""),
    schedule_cron: str = Form("0 7 * * 1-5"),
):
    set_db_config(db, LLM_PROVIDER_KEY, llm_provider.strip())
    set_db_config(db, LLM_MODEL_KEY, llm_model.strip())
    set_db_config(db, LLM_PROMPT_KEY, llm_prompt.strip())

    _update_schedule(schedule_cron.strip())

    return RedirectResponse("/settings?saved=1", status_code=303)


def _update_schedule(cron: str) -> None:
    """Write new cron expression to data/config.yml and reschedule the job."""
    import yaml

    from app.app_config import CONFIG_PATH, _reset_cache, get_app_config
    from app.scheduler import scheduler

    cfg = get_app_config()
    if cfg.get("schedule", {}).get("cron") == cron:
        return  # unchanged

    cfg["schedule"]["cron"] = cron
    CONFIG_PATH.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))
    _reset_cache()

    from apscheduler.triggers.cron import CronTrigger

    try:
        scheduler.reschedule_job("pipeline", trigger=CronTrigger.from_crontab(cron))
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
