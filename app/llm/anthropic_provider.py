"""Anthropic Claude implementation of LLMProvider."""

from __future__ import annotations

import logging

import anthropic

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Calls Anthropic Messages API. Satisfies the LLMProvider Protocol."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        logger.debug("AnthropicProvider.complete model=%s", self._model)
        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if not message.content:
            raise ValueError("LLM returned an empty response")
        return message.content[0].text
