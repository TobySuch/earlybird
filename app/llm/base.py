"""LLM provider abstraction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Structural interface for any LLM backend.

    Any object with a ``complete`` method of the correct signature satisfies
    this protocol — no inheritance needed.
    """

    def complete(self, system: str, user: str) -> str:
        """Send a chat completion request and return the response text."""
        ...
