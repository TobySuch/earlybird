from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bootstrap settings loaded from .env. All other config lives in the DB."""

    secret_key: str = "changeme"
    database_url: str = "sqlite:///./data/earlybird.db"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    abs_url: str = ""
    abs_api_key: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_db_config(db, key: str, default: str = "") -> str:
    """Read a value from the config key/value table. Falls back to default."""
    from app.models import Config  # local import avoids circular deps at module load

    row = db.query(Config).filter(Config.key == key).first()
    return row.value if row else default


def set_db_config(db, key: str, value: str) -> None:
    """Write a value to the config key/value table (upsert)."""
    from app.models import Config  # local import avoids circular deps at module load

    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))
    db.commit()
