"""Publishing: generate MP3 via TTS and save to disk."""

import logging

from sqlalchemy.orm import Session

from app import tracing as app_tracing
from app.config import (
    TTS_ENABLED_DEFAULT,
    TTS_ENABLED_KEY,
    TTS_INSTRUCTIONS_DEFAULT,
    TTS_INSTRUCTIONS_KEY,
    TTS_MODEL_ID_DEFAULT,
    TTS_MODEL_ID_KEY,
    TTS_PROVIDER_DEFAULT,
    TTS_PROVIDER_KEY,
    TTS_VOICE_ID_DEFAULT,
    TTS_VOICE_ID_KEY,
    get_db_config,
    get_settings,
)
from app.models import Episode
from app.tts.factory import AUDIO_DIR, get_tts_provider

logger = logging.getLogger(__name__)


def run(db: Session, episode: Episode) -> None:
    """Generate audio via TTS and save to disk.

    Steps:
    1. Check tts.enabled config.
    2. Check the API key for the configured provider.
    3. Generate MP3 from episode.newsletter_text via the provider.
    4. Save to data/audio/episode_{episode.id}.mp3, update episode.audio_path.
    """
    tts_enabled = get_db_config(db, TTS_ENABLED_KEY, TTS_ENABLED_DEFAULT) == "true"
    if not tts_enabled:
        logger.info("TTS disabled — skipping publish")
        return

    settings = get_settings()
    provider_name = get_db_config(db, TTS_PROVIDER_KEY, TTS_PROVIDER_DEFAULT)

    if provider_name == "openai":
        api_key = settings.openai_tts_api_key or settings.openai_api_key
        if not api_key:
            logger.warning("OPENAI_TTS_API_KEY / OPENAI_API_KEY not set — skipping publish")
            return
    else:
        api_key = settings.elevenlabs_api_key
        if not api_key:
            logger.warning("ELEVENLABS_API_KEY not set — skipping publish")
            return

    text = episode.newsletter_text
    if not text:
        logger.warning("Episode %d has no newsletter_text — skipping publish", episode.id)
        return

    voice_id = get_db_config(db, TTS_VOICE_ID_KEY, TTS_VOICE_ID_DEFAULT)
    if not voice_id:
        logger.warning("tts.voice_id not configured — skipping publish")
        return

    model_id = get_db_config(db, TTS_MODEL_ID_KEY, TTS_MODEL_ID_DEFAULT)
    instructions = get_db_config(db, TTS_INSTRUCTIONS_KEY, TTS_INSTRUCTIONS_DEFAULT)

    tts = get_tts_provider(db)
    with app_tracing.span(
        "audio_generation",
        attributes={
            "provider": provider_name,
            "voice_id": voice_id,
            "model_id": model_id,
            "text_length": len(text),
        },
    ):
        audio_path = tts.generate(
            voice_id, model_id, text, episode.id, AUDIO_DIR, instructions=instructions
        )
    episode.audio_path = str(audio_path)
    db.commit()
    logger.info("Audio saved to %s", audio_path)
