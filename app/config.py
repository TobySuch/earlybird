from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bootstrap settings loaded from .env. All other config lives in the DB."""

    secret_key: str = "changeme"
    database_url: str = "sqlite:///./data/earlybird.db"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_tts_api_key: str = ""
    elevenlabs_api_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    # Set to e.g. https://earlybird.example.com to fix redirect URIs behind a reverse proxy
    public_base_url: str = ""
    llm_max_tokens: int = 4096
    # MLflow tracing — set MLFLOW_TRACKING_URI to enable autologging for LLM calls
    mlflow_tracking_uri: str = ""
    mlflow_experiment_name: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Single source of truth for all DB-backed settings: key → default value
CONFIG_DEFAULTS: dict[str, str] = {
    "gmail.label": "Newsletters",
    "gmail.processed_label": "earlybird-processed",
    "gmail.lookback_days": "7",
    "schedule.cron": "0 7 * * 1-5",
    "schedule.enabled": "true",
    "feed.enabled": "false",
    "feed.token": "",
    "tts.enabled": "false",
    "tts.provider": "elevenlabs",
    "tts.voice_id": "",
    "tts.model_id": "eleven_turbo_v2_5",
    "tts.openai_base_url": "",
    "tts.instructions": (
        "Speak in a warm, engaging tone — like a knowledgeable friend reading the morning news."
    ),
    "llm.provider": "anthropic",
    "llm.model": "claude-haiku-4-5-20251001",
    "llm.prompt": "",
    "llm.openai_base_url": "",
    "llm.work_mode": "digest",  # digest = single LLM call | agent = reporters + editor
    # Agent mode: the editor uses the main llm.* config; reporters can override it.
    # Empty string inherits the llm.* value above.
    "llm.reporter.provider": "",
    "llm.reporter.model": "",
    "llm.reporter.openai_base_url": "",
    "llm.agent.max_parallel_reporters": "4",
    "retention.enabled": "false",
    "retention.max_days": "30",
}


def get_db_config(db, key: str, default: str | None = None) -> str:
    """Read a value from the config key/value table.

    Falls back to CONFIG_DEFAULTS[key] if no explicit default is given.
    """
    from app.models import Config  # local import avoids circular deps at module load

    row = db.query(Config).filter(Config.key == key).first()
    if row:
        return row.value
    return CONFIG_DEFAULTS.get(key, "") if default is None else default


def set_db_config(db, key: str, value: str) -> None:
    """Write a value to the config key/value table (upsert)."""
    from app.models import Config  # local import avoids circular deps at module load

    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))
    db.commit()
