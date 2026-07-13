"""In-memory data passed between agent-mode stages. Nothing here is persisted."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceInput:
    """Plain-data snapshot of a NewsSource — ORM objects never cross threads."""

    id: int
    title: str
    source_name: str
    content: str


@dataclass(frozen=True)
class Report:
    """A reporter's output for one source."""

    source_id: int
    source_title: str
    source_name: str
    summary: str
    editor_note: str
    recommend_include: bool
    importance: int
    degraded: bool = False  # JSON parse failed; summary is the raw LLM response


@dataclass(frozen=True)
class RundownSection:
    title: str
    story_ids: list[int]


@dataclass(frozen=True)
class Rundown:
    sections: list[RundownSection]
    headlines: list[str] = field(default_factory=list)
    fallback: bool = False  # built by the parse-failure fallback, not the editor
