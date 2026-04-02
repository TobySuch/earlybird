"""LLM provider: OpenAI Chat Completions API (and compatible endpoints)."""

from __future__ import annotations

import logging

import openai

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Calls OpenAI Chat Completions API. Satisfies the LLMProvider Protocol."""

    def __init__(self, api_key: str, model: str, base_url: str = "") -> None:
        kwargs: dict = {"api_key": api_key}
        if base_url.strip():
            kwargs["base_url"] = base_url.strip()
        self._client = openai.OpenAI(**kwargs)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        logger.debug("OpenAIProvider.complete model=%s", self._model)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=4096,
        )
        text = response.choices[0].message.content
        if not text:
            raise ValueError("LLM returned an empty response")
        return text
