from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bootstrap settings loaded from .env. All other config lives in the DB."""

    secret_key: str = "changeme"
    database_url: str = "sqlite:///./data/earlybird.db"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    elevenlabs_api_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


# DB config keys for settings previously stored in config.yml
GMAIL_LABEL_KEY = "gmail.label"
GMAIL_PROCESSED_LABEL_KEY = "gmail.processed_label"
GMAIL_LOOKBACK_DAYS_KEY = "gmail.lookback_days"
SCHEDULE_CRON_KEY = "schedule.cron"
SCHEDULE_ENABLED_KEY = "schedule.enabled"

GMAIL_LABEL_DEFAULT = "Newsletters"
GMAIL_PROCESSED_LABEL_DEFAULT = "earlybird-processed"
GMAIL_LOOKBACK_DAYS_DEFAULT = "7"
SCHEDULE_CRON_DEFAULT = "0 7 * * 1-5"
SCHEDULE_ENABLED_DEFAULT = "true"

TTS_ENABLED_KEY = "tts.enabled"
TTS_VOICE_ID_KEY = "tts.voice_id"
TTS_MODEL_ID_KEY = "tts.model_id"

TTS_ENABLED_DEFAULT = "false"
TTS_VOICE_ID_DEFAULT = ""
TTS_MODEL_ID_DEFAULT = "eleven_turbo_v2_5"


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
