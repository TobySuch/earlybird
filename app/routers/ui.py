"""HTMX web UI routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Run

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    last_run = db.query(Run).order_by(Run.started_at.desc()).first()
    return templates.TemplateResponse(request, "dashboard.html", {"last_run": last_run})


@router.get("/episodes", response_class=HTMLResponse)
async def episodes(request: Request, db: Session = Depends(get_db)):
    # TODO: paginate episodes
    return templates.TemplateResponse(request, "episodes.html")


@router.get("/sources", response_class=HTMLResponse)
async def sources(request: Request, db: Session = Depends(get_db)):
    # TODO: list and manage sources
    return templates.TemplateResponse(request, "sources.html")


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, db: Session = Depends(get_db)):
    from app.gmail_auth import get_credentials

    creds = get_credentials()
    gmail_connected = creds is not None and creds.valid
    # TODO: load config from DB
    return templates.TemplateResponse(
        request, "settings.html", {"gmail_connected": gmail_connected}
    )


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
