"""Factory: read DB config and return the configured TTSProvider."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_db_config, get_settings

AUDIO_DIR = Path("data/audio")


def get_tts_provider(db: Session):
    """Read DB config, instantiate, and return the appropriate TTSProvider."""
    provider = get_db_config(db, "tts.provider")

    if provider == "elevenlabs":
        from app.tts.elevenlabs_provider import ElevenLabsProvider

        return ElevenLabsProvider(api_key=get_settings().elevenlabs_api_key)

    if provider == "openai":
        from app.tts.openai_provider import OpenAITTSProvider

        settings = get_settings()
        api_key = settings.openai_tts_api_key or settings.openai_api_key
        base_url = get_db_config(db, "tts.openai_base_url")
        return OpenAITTSProvider(api_key=api_key, base_url=base_url)

    raise ValueError(f"Unknown TTS provider: {provider!r}")
