"""Ingest coordinator: iterate sources, deduplicate, and persist news sources."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import tracing as app_tracing
from app.config import (
    GMAIL_LOOKBACK_DAYS_DEFAULT,
    GMAIL_LOOKBACK_DAYS_KEY,
    get_db_config,
)
from app.models import NewsSource, Run
from app.pipeline.sources.base import NewsletterSource, SourceItem

logger = logging.getLogger(__name__)


def run(db: Session, current_run: Run, sources: list[NewsletterSource]) -> None:
    """Fetch from every source and persist results to the DB.

    Computes the lookback window from config, calls each source, and upserts
    items — deduplicating by URL within the current run.
    """
    lookback_days = int(get_db_config(db, GMAIL_LOOKBACK_DAYS_KEY, GMAIL_LOOKBACK_DAYS_DEFAULT))
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    count = 0
    with app_tracing.span("ingest", attributes={"lookback_days": lookback_days}):
        for source in sources:
            source_name = type(source).__name__
            with app_tracing.span(
                "fetch_emails",
                attributes={"source": source_name, "since": since.isoformat()},
            ):
                items = source.fetch(since)
            logger.info("Source %r returned %d item(s)", source, len(items))
            for item in items:
                if not item.raw_content:
                    logger.info("Skipping %r — empty content", item.title)
                    continue
                _upsert(db, _item_to_news_source(item, current_run.id), current_run.id)
                count += 1

    logger.info("Ingestion complete — %d item(s) stored", count)
    current_run.newsletters_found = count
    db.commit()


def _item_to_news_source(item: SourceItem, run_id: int) -> NewsSource:
    """Convert a source-agnostic SourceItem into a NewsSource ORM object."""
    return NewsSource(
        run_id=run_id,
        title=item.title,
        url=item.url,
        raw_content=item.raw_content,
        published_at=item.published_at,
        source_type=item.source_type,
        source_name=item.source_name,
    )


def _upsert(db: Session, news_source: NewsSource, run_id: int) -> None:
    """Insert *news_source*, or increment seen_count if the same URL exists this run."""
    if news_source.url:
        existing = (
            db.query(NewsSource)
            .filter(NewsSource.run_id == run_id, NewsSource.url == news_source.url)
            .first()
        )
        if existing:
            existing.seen_count += 1
            return
    db.add(news_source)
