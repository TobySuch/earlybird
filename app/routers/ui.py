"""HTMX web UI routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # TODO: query latest episode and last run, pass to template
    return templates.TemplateResponse(request, "dashboard.html")


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
    # TODO: load config from DB
    return templates.TemplateResponse(request, "settings.html")


@router.get("/run-log", response_class=HTMLResponse)
async def run_log(request: Request, db: Session = Depends(get_db)):
    # TODO: paginate runs
    return templates.TemplateResponse(request, "run_log.html")
