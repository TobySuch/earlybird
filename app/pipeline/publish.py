"""Publishing: generate MP3 via ElevenLabs TTS."""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import (
    TTS_ENABLED_DEFAULT,
    TTS_ENABLED_KEY,
    TTS_MODEL_ID_DEFAULT,
    TTS_MODEL_ID_KEY,
    TTS_VOICE_ID_DEFAULT,
    TTS_VOICE_ID_KEY,
    get_db_config,
    get_settings,
)
from app.models import Episode

logger = logging.getLogger(__name__)

AUDIO_DIR = Path("data/audio")

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None  # type: ignore[assignment,misc]


def run(db: Session, episode: Episode) -> None:
    """Generate audio via ElevenLabs TTS and save to disk.

    Steps:
    1. Check tts.enabled config and ELEVENLABS_API_KEY env var.
    2. Generate MP3 from episode.newsletter_text via ElevenLabs.
    3. Save to data/audio/episode_{episode.id}.mp3, update episode.audio_path.
    """
    tts_enabled = get_db_config(db, TTS_ENABLED_KEY, TTS_ENABLED_DEFAULT) == "true"
    if not tts_enabled:
        logger.info("TTS disabled — skipping publish")
        return

    settings = get_settings()
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

    audio_path = _generate_audio(api_key, voice_id, model_id, text, episode.id)
    episode.audio_path = str(audio_path)
    db.commit()
    logger.info("Audio saved to %s", audio_path)


def _generate_audio(
    api_key: str,
    voice_id: str,
    model_id: str,
    text: str,
    episode_id: int,
    audio_dir: Path = AUDIO_DIR,
) -> Path:
    """Call ElevenLabs TTS and write the MP3 to disk. Returns the file path."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / f"episode_{episode_id}.mp3"

    client = ElevenLabs(api_key=api_key)
    audio_chunks = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        output_format="mp3_44100_128",
    )
    with open(output_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)

    return output_path
