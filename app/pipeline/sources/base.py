"""Source abstraction for the ingest pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class SourceItem:
    """A single item returned by any newsletter source."""

    title: str
    raw_content: str
    source_type: str  # connector type: "gmail" | "imap" | "rss"
    source_name: str | None = None  # optional user-friendly label for the source instance
    url: str | None = None
    published_at: datetime | None = None


@runtime_checkable
class NewsletterSource(Protocol):
    """Structural interface that all newsletter sources must satisfy.

    Any class implementing a ``fetch`` method with the right signature
    satisfies this protocol — no inheritance required.
    """

    def fetch(self, since: datetime) -> list[SourceItem]:
        """Return all items published or received since *since* (UTC)."""
        ...

    def mark_processed(self) -> None:
        """Mark all items returned by the last fetch() call as processed.

        Called by the scheduler only after the full pipeline succeeds.
        Sources that have no persistent processed-state tracking can leave
        this as a no-op.
        """
        ...
