from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

_ALEMBIC_INI = Path(__file__).parent.parent / "alembic.ini"


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    connect_args = (
        {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    )
    return create_engine(settings.database_url, connect_args=connect_args)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Apply all pending Alembic migrations.

    On first run of an existing DB created before migrations were introduced,
    stamps the current state as head so future migrations apply cleanly.
    """
    alembic_cfg = Config(str(_ALEMBIC_INI))

    existing_tables = inspect(engine).get_table_names()
    if "alembic_version" not in existing_tables and existing_tables:
        # Legacy DB: already at the initial schema state, just record that.
        command.stamp(alembic_cfg, "head")
    else:
        command.upgrade(alembic_cfg, "head")


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
