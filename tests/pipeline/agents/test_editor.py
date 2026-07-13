"""Tests for app/pipeline/agents/editor.py."""

from __future__ import annotations

import json

from app.pipeline.agents.editor import assemble_episode, build_rundown
from app.pipeline.agents.types import Report, Rundown, RundownSection


def _report(source_id: int, include: bool = True, importance: int = 3) -> Report:
    return Report(
        source_id=source_id,
        source_title=f"Story {source_id}",
        source_name=f"Source {source_id}",
        summary=f"Full summary of story {source_id}.",
        editor_note=f"Pitch for story {source_id}.",
        recommend_include=include,
        importance=importance,
    )


class StubProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        return self.response


def _rundown_json(sections, headlines=("Headline one here now", "Headline two here now")) -> str:
    return json.dumps({"sections": sections, "headlines": list(headlines)})


# ── build_rundown ─────────────────────────────────────────────────────────────


def test_rundown_parses_sections_and_headlines():
    reports = [_report(1), _report(2), _report(3)]
    stub = StubProvider(
        _rundown_json(
            [
                {"title": "Tech", "story_ids": [3, 1]},
                {"title": "Science", "story_ids": [2]},
            ]
        )
    )
    rundown = build_rundown(stub, reports, "", "date")
    assert rundown.fallback is False
    assert [s.title for s in rundown.sections] == ["Tech", "Science"]
    assert rundown.sections[0].story_ids == [3, 1]
    assert rundown.sections[1].story_ids == [2]
    assert rundown.headlines == ["Headline one here now", "Headline two here now"]


def test_rundown_drops_hallucinated_ids():
    reports = [_report(1), _report(2)]
    stub = StubProvider(_rundown_json([{"title": "News", "story_ids": [1, 99, 2]}]))
    rundown = build_rundown(stub, reports, "", "date")
    assert rundown.sections[0].story_ids == [1, 2]


def test_rundown_dedupes_repeated_ids_first_wins():
    reports = [_report(1), _report(2)]
    stub = StubProvider(
        _rundown_json(
            [
                {"title": "A", "story_ids": [2, 1]},
                {"title": "B", "story_ids": [1, 2]},
            ]
        )
    )
    rundown = build_rundown(stub, reports, "", "date")
    assert rundown.sections[0].story_ids == [2, 1]
    assert len(rundown.sections) == 1  # section B emptied out and was dropped


def test_rundown_unparseable_uses_fallback():
    reports = [_report(1, include=True), _report(2, include=False), _report(3, include=True)]
    rundown = build_rundown(StubProvider("no json at all"), reports, "", "date")
    assert rundown.fallback is True
    assert len(rundown.sections) == 1
    assert rundown.sections[0].story_ids == [1, 3]  # recommended only, source order
    assert rundown.headlines == []


def test_rundown_fallback_uses_all_when_none_recommended():
    reports = [_report(1, include=False), _report(2, include=False)]
    rundown = build_rundown(StubProvider("garbage"), reports, "", "date")
    assert rundown.fallback is True
    assert rundown.sections[0].story_ids == [1, 2]


def test_rundown_all_ids_hallucinated_uses_fallback():
    reports = [_report(1)]
    stub = StubProvider(_rundown_json([{"title": "News", "story_ids": [42, 43]}]))
    rundown = build_rundown(stub, reports, "", "date")
    assert rundown.fallback is True
    assert rundown.sections[0].story_ids == [1]


def test_rundown_prompt_contains_pitches_and_preferences():
    reports = [_report(1), _report(2, include=False)]
    stub = StubProvider(_rundown_json([{"title": "News", "story_ids": [1]}]))
    build_rundown(stub, reports, "I love space news", "date")
    user = stub.calls[0]["user"]
    assert "I love space news" in user
    assert "Pitch for story 1." in user
    assert "Pitch for story 2." in user
    assert "Full summary of story 1." not in user  # rundown sees pitches, not summaries
    assert "Reporter recommends: skip" in user


# ── assemble_episode ──────────────────────────────────────────────────────────


def test_assembly_contains_only_included_summaries_in_order():
    reports = {r.source_id: r for r in [_report(1), _report(2), _report(3)]}
    rundown = Rundown(
        sections=[
            RundownSection(title="Tech", story_ids=[3, 1]),
        ],
        headlines=["h"],
    )
    stub = StubProvider("The episode text.")
    text = assemble_episode(stub, rundown, reports, "", "date")
    assert text == "The episode text."

    user = stub.calls[0]["user"]
    assert "Full summary of story 3." in user
    assert "Full summary of story 1." in user
    assert "Full summary of story 2." not in user
    assert user.index("Full summary of story 3.") < user.index("Full summary of story 1.")
    assert "### Tech" in user


def test_assembly_prompt_contains_preferences_and_date():
    reports = {1: _report(1)}
    rundown = Rundown(sections=[RundownSection(title="News", story_ids=[1])])
    stub = StubProvider("text")
    assemble_episode(stub, rundown, reports, "I love rockets", "Monday, the 1st of June 2026")
    assert "I love rockets" in stub.calls[0]["user"]
    assert "Monday, the 1st of June 2026" in stub.calls[0]["system"]
