from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.app_config import get_app_config
from app.config import get_settings
from app.database import init_db
from app.routers import api, auth, ui
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_app_config()  # create data/config.yml from defaults if absent
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Earlybird", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=get_settings().secret_key)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(ui.router)
app.include_router(api.router, prefix="/api")
app.include_router(auth.router, prefix="/auth")
