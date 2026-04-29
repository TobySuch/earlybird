"""Anthropic Claude implementation of LLMProvider."""

from __future__ import annotations

import logging

import anthropic

logger = logging.getLogger(__name__)


_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/TobySuch/earlybird",
    "X-OpenRouter-Title": "Earlybird",
    "X-OpenRouter-Categories": "personal-agent",
}


class AnthropicProvider:
    """Calls Anthropic Messages API. Satisfies the LLMProvider Protocol."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096) -> None:
        self._client = anthropic.Anthropic(api_key=api_key, default_headers=_OPENROUTER_HEADERS)
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        logger.debug("AnthropicProvider.complete model=%s", self._model)
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if not message.content:
            raise ValueError("LLM returned an empty response")
        return message.content[0].text
