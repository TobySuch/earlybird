"""Tests for app/pipeline/agents/reporter.py."""

from __future__ import annotations

import json

from app.pipeline.agents.reporter import run_reporter
from app.pipeline.agents.types import SourceInput

SOURCE = SourceInput(id=7, title="Big News", source_name="Tech Weekly", content="Stuff happened.")

GOOD_RESPONSE = json.dumps(
    {
        "summary": "Stuff happened and it matters.",
        "editor_note": "Solid story about stuff.",
        "include": True,
        "importance": 4,
    }
)


class StubProvider:
    def __init__(self, response: str = GOOD_RESPONSE, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        if self.error:
            raise self.error
        return self.response


def test_parses_clean_json():
    report = run_reporter(StubProvider(), SOURCE, "", "Monday, the 1st of June 2026")
    assert report is not None
    assert report.source_id == 7
    assert report.source_title == "Big News"
    assert report.summary == "Stuff happened and it matters."
    assert report.editor_note == "Solid story about stuff."
    assert report.recommend_include is True
    assert report.importance == 4
    assert report.degraded is False


def test_parses_fenced_json():
    fenced = f"```json\n{GOOD_RESPONSE}\n```"
    report = run_reporter(StubProvider(fenced), SOURCE, "", "date")
    assert report.summary == "Stuff happened and it matters."
    assert report.degraded is False


def test_parses_json_embedded_in_chatter():
    chatty = f"Sure! Here is my report:\n{GOOD_RESPONSE}\nLet me know if you need more."
    report = run_reporter(StubProvider(chatty), SOURCE, "", "date")
    assert report.summary == "Stuff happened and it matters."
    assert report.degraded is False


def test_garbage_response_degrades_fail_open():
    report = run_reporter(StubProvider("Total nonsense, no JSON here."), SOURCE, "", "date")
    assert report is not None
    assert report.degraded is True
    assert report.summary == "Total nonsense, no JSON here."
    assert report.editor_note == "Total nonsense, no JSON here."
    assert report.recommend_include is True
    assert report.importance == 3


def test_long_garbage_truncates_editor_note():
    raw = "x" * 500
    report = run_reporter(StubProvider(raw), SOURCE, "", "date")
    assert report.degraded is True
    assert report.summary == raw
    assert report.editor_note == "x" * 200


def test_provider_exception_returns_none():
    report = run_reporter(StubProvider(error=RuntimeError("boom")), SOURCE, "", "date")
    assert report is None


def test_importance_clamped_to_range():
    high = json.dumps({"summary": "s", "editor_note": "n", "include": False, "importance": 99})
    report = run_reporter(StubProvider(high), SOURCE, "", "date")
    assert report.importance == 5
    assert report.recommend_include is False

    low = json.dumps({"summary": "s", "editor_note": "n", "include": True, "importance": -3})
    report = run_reporter(StubProvider(low), SOURCE, "", "date")
    assert report.importance == 1


def test_non_integer_importance_defaults_to_three():
    weird = json.dumps({"summary": "s", "editor_note": "n", "include": True, "importance": "high"})
    report = run_reporter(StubProvider(weird), SOURCE, "", "date")
    assert report.importance == 3
    assert report.degraded is False


def test_prompt_contains_preferences_and_date():
    stub = StubProvider()
    run_reporter(stub, SOURCE, "I love rockets", "Monday, the 1st of June 2026")
    assert "I love rockets" in stub.calls[0]["user"]
    assert "Monday, the 1st of June 2026" in stub.calls[0]["system"]
    assert "Big News" in stub.calls[0]["user"]
    assert "Stuff happened." in stub.calls[0]["user"]
