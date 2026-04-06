"""TTS provider: OpenAI Audio Speech API (and compatible endpoints)."""

from __future__ import annotations

import logging
from pathlib import Path

import openai

logger = logging.getLogger(__name__)


class OpenAITTSProvider:
    """Calls OpenAI audio.speech.create(). Works with any compatible endpoint."""

    def __init__(self, api_key: str, base_url: str = "") -> None:
        kwargs: dict = {"api_key": api_key}
        if base_url.strip():
            kwargs["base_url"] = base_url.strip()
        self._client = openai.OpenAI(**kwargs)

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
        logger.debug("OpenAITTSProvider.generate model=%s voice=%s", model_id, voice_id)
        kwargs: dict = dict(model=model_id, voice=voice_id, input=text, response_format="mp3")
        if instructions.strip():
            kwargs["instructions"] = instructions.strip()
        response = self._client.audio.speech.create(**kwargs)
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
        return output_path
