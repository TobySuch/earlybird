"""TTS provider: ElevenLabs."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None  # type: ignore[assignment,misc]


class ElevenLabsProvider:
    """Calls ElevenLabs TTS API."""

    def __init__(self, api_key: str) -> None:
        self._client = ElevenLabs(api_key=api_key)

    def generate(
        self,
        voice_id: str,
        model_id: str,
        text: str,
        episode_id: int,
        audio_dir: Path,
        *,
        instructions: str = "",
    ) -> Path:
        audio_dir.mkdir(parents=True, exist_ok=True)
        output_path = audio_dir / f"episode_{episode_id}.mp3"
        audio_chunks = self._client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
        with open(output_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)
        return output_path
