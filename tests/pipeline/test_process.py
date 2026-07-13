"""Tests for app/pipeline/process.py."""

from __future__ import annotations

import datetime as dt
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Episode, NewsSource, Run
from app.pipeline import process

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def current_run(db):
    run = Run(started_at=datetime.now(timezone.utc), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


# ── Stub ──────────────────────────────────────────────────────────────────────


class StubLLMProvider:
    """Minimal LLMProvider for process tests — no API calls.

    Pass a list of responses to return different values on sequential calls;
    the last entry is repeated if calls exceed the list length.
    """

    def __init__(self, responses: list[str] | str = "stub newsletter text") -> None:
        self.responses = [responses] if isinstance(responses, str) else responses
        self.calls: list[dict] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        idx = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[idx]


def _make_source(
    db,
    run_id: int,
    title: str = "Test Article",
    content: str = "Article content.",
) -> NewsSource:
    s = NewsSource(
        run_id=run_id,
        title=title,
        raw_content=content,
        source_name="Test Source",
        source_type="stub",
    )
    db.add(s)
    db.commit()
    return s


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_run_creates_episode(db, current_run):
    _make_source(db, current_run.id)
    stub = StubLLMProvider("My newsletter digest.")

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    episode = db.query(Episode).filter(Episode.run_id == current_run.id).first()
    assert episode is not None
    assert episode.newsletter_text == "My newsletter digest."


def test_run_sets_newsletters_included(db, current_run):
    _make_source(db, current_run.id, title="A")
    _make_source(db, current_run.id, title="B")
    stub = StubLLMProvider()

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    assert current_run.newsletters_included == 2


def test_run_no_sources_skips_llm_call(db, current_run):
    stub = StubLLMProvider()

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    assert stub.calls == []
    assert current_run.newsletters_included == 0
    assert db.query(Episode).filter(Episode.run_id == current_run.id).first() is None


def test_run_passes_user_prompt_in_message(db, current_run):
    _make_source(db, current_run.id)
    stub = StubLLMProvider()

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value="I love tech news"),
    ):
        process.run(db, current_run)

    assert "I love tech news" in stub.calls[0]["user"]


def test_run_includes_source_title_in_message(db, current_run):
    _make_source(db, current_run.id, title="Important Article")
    stub = StubLLMProvider()

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    assert "Important Article" in stub.calls[0]["user"]


def test_format_date_ordinals():
    assert process._format_date(dt.datetime(2026, 4, 20)) == "Monday, the 20th of April 2026"
    assert process._format_date(dt.datetime(2026, 9, 1)) == "Tuesday, the 1st of September 2026"
    assert process._format_date(dt.datetime(2026, 9, 2)) == "Wednesday, the 2nd of September 2026"
    assert process._format_date(dt.datetime(2026, 9, 3)) == "Thursday, the 3rd of September 2026"
    # teens should use "th" not "st/nd/rd"
    assert process._format_date(dt.datetime(2026, 9, 11)) == "Friday, the 11th of September 2026"
    assert process._format_date(dt.datetime(2026, 9, 12)) == "Saturday, the 12th of September 2026"
    assert process._format_date(dt.datetime(2026, 9, 13)) == "Sunday, the 13th of September 2026"
    assert process._format_date(dt.datetime(2026, 9, 21)) == "Monday, the 21st of September 2026"


def test_run_system_prompt_contains_formatted_date(db, current_run):
    _make_source(db, current_run.id)
    stub = StubLLMProvider()
    fixed_now = dt.datetime(2026, 4, 20, 8, 0, 0)

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
        patch("app.pipeline.process.datetime") as mock_dt,
    ):
        mock_dt.datetime.now.return_value = fixed_now
        process.run(db, current_run)

    assert "Monday, the 20th of April 2026" in stub.calls[0]["system"]
    assert "Disregard any dates" in stub.calls[0]["system"]


def test_run_makes_two_llm_calls(db, current_run):
    _make_source(db, current_run.id)
    stub = StubLLMProvider(["digest text", "• Headline one\n• Headline two"])

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    assert len(stub.calls) == 2


def test_run_stores_episode_headlines(db, current_run):
    _make_source(db, current_run.id)
    stub = StubLLMProvider(["My digest.", "• Topic A\n• Topic B"])

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    episode = db.query(Episode).filter(Episode.run_id == current_run.id).first()
    assert episode.episode_headlines == "• Topic A\n• Topic B"


def test_run_headlines_call_uses_newsletter_text_as_input(db, current_run):
    _make_source(db, current_run.id)
    stub = StubLLMProvider(["My digest.", "• Topic A"])

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    # Second call's user message should be the newsletter_text from the first call
    assert stub.calls[1]["user"] == "My digest."
    assert process.HEADLINES_SYSTEM_PROMPT in stub.calls[1]["system"]


def test_run_no_sources_skips_headlines_call(db, current_run):
    stub = StubLLMProvider()

    with (
        patch("app.pipeline.process.get_llm_provider", return_value=stub),
        patch("app.pipeline.process.get_llm_user_prompt", return_value=""),
    ):
        process.run(db, current_run)

    assert stub.calls == []
