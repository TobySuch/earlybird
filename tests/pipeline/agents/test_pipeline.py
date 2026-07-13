"""Tests for app/pipeline/agents/pipeline.py."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import set_db_config
from app.database import Base
from app.models import Episode, NewsSource, Run
from app.pipeline.agents import pipeline as agent_pipeline
from app.pipeline.process import HEADLINES_SYSTEM_PROMPT

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


def _make_source(db, run_id: int, title: str = "Article") -> NewsSource:
    s = NewsSource(
        run_id=run_id,
        title=title,
        raw_content=f"Content of {title}.",
        source_name="Test Source",
        source_type="stub",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ── Stubs ─────────────────────────────────────────────────────────────────────


def _reporter_json(summary: str, include: bool = True) -> str:
    return json.dumps(
        {
            "summary": summary,
            "editor_note": f"Pitch: {summary}",
            "include": include,
            "importance": 3,
        }
    )


class StubReporterProvider:
    """Thread-safe stub returning one reporter JSON per call."""

    def __init__(self, fail_titles: set[str] | None = None, delay_by_title=None) -> None:
        self.fail_titles = fail_titles or set()
        self.delay_by_title = delay_by_title or {}
        self._lock = threading.Lock()
        self.calls: list[dict] = []
        self.concurrent = 0
        self.max_concurrent = 0

    def complete(self, system: str, user: str) -> str:
        with self._lock:
            self.calls.append({"system": system, "user": user})
            self.concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent)
        try:
            title = next((t for t in self.fail_titles if t in user), None)
            if title:
                raise RuntimeError(f"boom for {title}")
            for t, delay in self.delay_by_title.items():
                if t in user:
                    time.sleep(delay)
            # Echo the article title back as the summary so tests can trace it.
            first = next(
                line for line in user.splitlines() if line.startswith("Title: ")
            ).removeprefix("Title: ")
            return _reporter_json(f"Summary of {first}")
        finally:
            with self._lock:
                self.concurrent -= 1


class StubEditorProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        idx = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[idx]


def _patch_providers(reporter, editor):
    def fake_get_llm_provider(db, role=None):
        return {"reporter": reporter, "editor": editor}[role]

    return patch("app.pipeline.agents.pipeline.get_llm_provider", side_effect=fake_get_llm_provider)


def _rundown_json(story_ids: list[int], headlines: list[str] | None = None) -> str:
    return json.dumps(
        {
            "sections": [{"title": "News", "story_ids": story_ids}],
            "headlines": headlines if headlines is not None else ["Big day for tests"],
        }
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_happy_path_creates_episode(db, current_run):
    s1 = _make_source(db, current_run.id, "Alpha")
    s2 = _make_source(db, current_run.id, "Beta")
    reporter = StubReporterProvider()
    editor = StubEditorProvider([_rundown_json([s2.id, s1.id]), "Final episode text."])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    episode = db.query(Episode).filter(Episode.run_id == current_run.id).first()
    assert episode is not None
    assert episode.newsletter_text == "Final episode text."
    assert episode.episode_headlines == "• Big day for tests"
    assert current_run.newsletters_included == 2
    # One reporter call per source, rundown + assembly on the editor.
    assert len(reporter.calls) == 2
    assert len(editor.calls) == 2


def test_included_count_reflects_editor_selection(db, current_run):
    s1 = _make_source(db, current_run.id, "Alpha")
    _make_source(db, current_run.id, "Beta")
    _make_source(db, current_run.id, "Gamma")
    reporter = StubReporterProvider()
    editor = StubEditorProvider([_rundown_json([s1.id]), "Episode."])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    assert current_run.newsletters_included == 1


def test_assembly_receives_only_included_summaries(db, current_run):
    s1 = _make_source(db, current_run.id, "Alpha")
    _make_source(db, current_run.id, "Beta")
    reporter = StubReporterProvider()
    editor = StubEditorProvider([_rundown_json([s1.id]), "Episode."])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    assembly_user = editor.calls[1]["user"]
    assert "Summary of Alpha" in assembly_user
    assert "Summary of Beta" not in assembly_user


def test_failed_reporter_skips_story_run_succeeds(db, current_run):
    s1 = _make_source(db, current_run.id, "Alpha")
    _make_source(db, current_run.id, "Beta")
    reporter = StubReporterProvider(fail_titles={"Beta"})
    editor = StubEditorProvider([_rundown_json([s1.id]), "Episode."])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    episode = db.query(Episode).filter(Episode.run_id == current_run.id).first()
    assert episode is not None
    # Only Alpha's pitch reached the editor.
    assert "Alpha" in editor.calls[0]["user"]
    assert "Beta" not in editor.calls[0]["user"]


def test_all_reporters_failing_raises(db, current_run):
    _make_source(db, current_run.id, "Alpha")
    _make_source(db, current_run.id, "Beta")
    reporter = StubReporterProvider(fail_titles={"Alpha", "Beta"})
    editor = StubEditorProvider(["unused"])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
        pytest.raises(RuntimeError, match="reporter"),
    ):
        agent_pipeline.run(db, current_run)

    assert db.query(Episode).filter(Episode.run_id == current_run.id).first() is None


def test_no_sources_skips_llm_calls(db, current_run):
    reporter = StubReporterProvider()
    editor = StubEditorProvider(["unused"])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    assert reporter.calls == []
    assert editor.calls == []
    assert current_run.newsletters_included == 0
    assert db.query(Episode).filter(Episode.run_id == current_run.id).first() is None


def test_concurrency_limit_respected(db, current_run):
    for i in range(6):
        _make_source(db, current_run.id, f"Story{i}")
    set_db_config(db, "llm.agent.max_parallel_reporters", "2")
    delays = {f"Story{i}": 0.02 for i in range(6)}
    reporter = StubReporterProvider(delay_by_title=delays)
    editor = StubEditorProvider([_rundown_json([]), "Episode."])
    # Empty rundown → fallback → headlines call; give the editor stub a third response.
    editor.responses = [json.dumps({"sections": [], "headlines": []}), "Episode.", "• H"]

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    assert reporter.max_concurrent <= 2


def test_report_order_is_deterministic_under_staggered_completion(db, current_run):
    _make_source(db, current_run.id, "Slow")
    _make_source(db, current_run.id, "Fast")
    reporter = StubReporterProvider(delay_by_title={"Slow": 0.05})
    s_ids = [s.id for s in db.query(NewsSource).order_by(NewsSource.id).all()]
    editor = StubEditorProvider([_rundown_json(s_ids), "Episode."])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    # Pitches appear in source order even though Slow finished last.
    rundown_user = editor.calls[0]["user"]
    assert rundown_user.index("Slow") < rundown_user.index("Fast")


def test_fallback_rundown_triggers_legacy_headlines_call(db, current_run):
    _make_source(db, current_run.id, "Alpha")
    reporter = StubReporterProvider()
    editor = StubEditorProvider(["not json at all", "Episode text.", "• Legacy headline"])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    episode = db.query(Episode).filter(Episode.run_id == current_run.id).first()
    assert episode.episode_headlines == "• Legacy headline"
    assert len(editor.calls) == 3
    assert HEADLINES_SYSTEM_PROMPT in editor.calls[2]["system"]
    assert editor.calls[2]["user"] == "Episode text."


def test_roles_use_their_own_providers(db, current_run):
    _make_source(db, current_run.id, "Alpha")
    reporter = StubReporterProvider()
    editor = StubEditorProvider([_rundown_json([1]), "Episode."])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    # Reporter prompts mention filing a report; editor prompts mention the rundown.
    assert all("reporter" in c["system"] for c in reporter.calls)
    assert all("editor-in-chief" in c["system"] for c in editor.calls[:2])


def test_invalid_max_parallel_config_falls_back(db, current_run):
    _make_source(db, current_run.id, "Alpha")
    set_db_config(db, "llm.agent.max_parallel_reporters", "banana")
    reporter = StubReporterProvider()
    editor = StubEditorProvider([_rundown_json([1]), "Episode."])

    with (
        _patch_providers(reporter, editor),
        patch("app.pipeline.agents.pipeline.get_llm_user_prompt", return_value=""),
    ):
        agent_pipeline.run(db, current_run)

    assert db.query(Episode).filter(Episode.run_id == current_run.id).first() is not None
