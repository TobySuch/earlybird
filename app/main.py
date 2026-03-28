import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import auth as auth_utils
from app.app_config import get_app_config
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.routers import api, auth, ui
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_app_config()  # create data/config.yml from defaults if absent
    init_db()
    start_scheduler()

    # Generate a one-time signup code if no users exist yet
    db = SessionLocal()
    try:
        from app.models import User

        if db.query(User).count() == 0:
            code = auth_utils.generate_signup_code()
            logger.warning("=" * 60)
            logger.warning("FIRST RUN — no users exist.")
            logger.warning("Signup code: %s", code)
            logger.warning("Visit /auth/signup to create your account.")
            logger.warning("=" * 60)
    finally:
        db.close()

    yield
    stop_scheduler()


app = FastAPI(title="Earlybird", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=get_settings().secret_key)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(ui.router)
app.include_router(api.router, prefix="/api")
app.include_router(auth.router, prefix="/auth")


@app.exception_handler(auth_utils.NotAuthenticatedError)
async def not_authenticated_handler(request: Request, exc: auth_utils.NotAuthenticatedError):
    return RedirectResponse(url="/auth/login", status_code=302)
