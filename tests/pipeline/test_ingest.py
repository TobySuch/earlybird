"""Tests for app/pipeline/ingest.py — coordinator logic with stub sources."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import NewsSource, Run
from app.pipeline import ingest
from app.pipeline.sources.base import SourceItem

_BASE_CFG = {
    "gmail": {"label": "Newsletters", "processed_label": "earlybird-processed", "lookback_days": 7}
}

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    """In-memory SQLite session, isolated per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def current_run(db):
    run = Run(started_at=datetime.utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_item(title="Newsletter A", url="https://a.example.com") -> SourceItem:
    return SourceItem(
        title=title,
        raw_content=f"Visit {url}",
        source_type="stub",
        url=url,
        published_at=datetime(2024, 1, 1),
    )


class StubSource:
    """Minimal NewsletterSource for coordinator tests."""

    def __init__(self, items: list[SourceItem]) -> None:
        self.items = items
        self.fetch_calls: list[datetime] = []

    def fetch(self, since: datetime) -> list[SourceItem]:
        self.fetch_calls.append(since)
        return self.items


# ── Tests ─────────────────────────────────────────────────────────────────────


@patch("app.pipeline.ingest.get_app_config")
def test_run_stores_items(mock_cfg, db, current_run):
    mock_cfg.return_value = _BASE_CFG

    sources = [
        StubSource(
            [_make_item("A", "https://a.example.com"), _make_item("B", "https://b.example.com")]
        )
    ]
    ingest.run(db, current_run, sources)

    rows = db.query(NewsSource).filter(NewsSource.run_id == current_run.id).all()
    assert len(rows) == 2
    assert current_run.newsletters_found == 2


@patch("app.pipeline.ingest.get_app_config")
def test_run_deduplicates_by_url(mock_cfg, db, current_run):
    mock_cfg.return_value = _BASE_CFG

    shared_url = "https://shared.example.com"
    sources = [StubSource([_make_item("A", shared_url), _make_item("B", shared_url)])]
    ingest.run(db, current_run, sources)

    rows = db.query(NewsSource).filter(NewsSource.run_id == current_run.id).all()
    assert len(rows) == 1
    assert rows[0].seen_count == 2


@patch("app.pipeline.ingest.get_app_config")
def test_run_no_items_sets_count_zero(mock_cfg, db, current_run):
    mock_cfg.return_value = _BASE_CFG

    ingest.run(db, current_run, [StubSource([])])

    assert current_run.newsletters_found == 0


@patch("app.pipeline.ingest.get_app_config")
def test_run_iterates_multiple_sources(mock_cfg, db, current_run):
    mock_cfg.return_value = _BASE_CFG

    sources = [
        StubSource([_make_item("A", "https://a.example.com")]),
        StubSource([_make_item("B", "https://b.example.com")]),
    ]
    ingest.run(db, current_run, sources)

    rows = db.query(NewsSource).filter(NewsSource.run_id == current_run.id).all()
    assert len(rows) == 2
    assert current_run.newsletters_found == 2


@patch("app.pipeline.ingest.get_app_config")
def test_run_passes_since_to_source(mock_cfg, db, current_run):
    mock_cfg.return_value = _BASE_CFG

    stub = StubSource([])
    ingest.run(db, current_run, [stub])

    assert len(stub.fetch_calls) == 1
    since = stub.fetch_calls[0]
    # since should be roughly 7 days ago
    now = datetime.now(timezone.utc)
    assert (now - since).days == 7


@patch("app.pipeline.ingest.get_app_config")
def test_run_persists_source_type(mock_cfg, db, current_run):
    mock_cfg.return_value = _BASE_CFG

    sources = [StubSource([_make_item()])]
    ingest.run(db, current_run, sources)

    row = db.query(NewsSource).filter(NewsSource.run_id == current_run.id).first()
    assert row.source_type == "stub"
