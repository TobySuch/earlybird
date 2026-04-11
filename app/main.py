import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import auth as auth_utils
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.routers import api, auth, ui
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


def _check_env() -> None:
    """Log warnings for missing or default env var values at startup."""
    s = get_settings()

    checks = [
        (
            s.secret_key == "changeme",
            "SECRET_KEY is set to the default 'changeme' — set a strong random value in .env",
        ),
        (not s.gmail_client_id, "GMAIL_CLIENT_ID is not set — Gmail ingest will fail"),
        (not s.gmail_client_secret, "GMAIL_CLIENT_SECRET is not set — Gmail ingest will fail"),
    ]

    if not s.anthropic_api_key and not s.openai_api_key:
        checks.append(
            (
                True,
                "No LLM API key set (ANTHROPIC_API_KEY or OPENAI_API_KEY) — LLM will fail",
            )
        )

    for failed, message in checks:
        if failed:
            logger.warning("Config warning: %s", message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _check_env()
    start_scheduler()

    # Generate a one-time signup code if no users exist yet
    db = SessionLocal()
    try:
        from app.models import User

        if db.query(User).count() == 0:
            code = auth_utils.generate_pairing_code()
            logger.warning("=" * 60)
            logger.warning("FIRST RUN — no users exist.")
            logger.warning("Pairing code: %s", code)
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
