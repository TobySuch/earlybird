from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
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

    alembic_tracked = False
    if "alembic_version" in existing_tables:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            alembic_tracked = row is not None

    if existing_tables and not alembic_tracked:
        # Existing DB with no Alembic tracking (legacy or empty alembic_version).
        # Stamp as head so future migrations apply cleanly without re-running.
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
