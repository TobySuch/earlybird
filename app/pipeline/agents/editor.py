"""Editor agent: pick and order stories, then assemble the episode text."""

from __future__ import annotations

import logging

from app import tracing as app_tracing
from app.llm.base import LLMProvider
from app.pipeline.agents.parsing import extract_json_object
from app.pipeline.agents.types import Report, Rundown, RundownSection

logger = logging.getLogger(__name__)

FALLBACK_SECTION_TITLE = "Today's stories"

EDITOR_RUNDOWN_SYSTEM_PROMPT_TEMPLATE = """\
You are the editor-in-chief of a daily news podcast. Your reporters have each \
filed a pitch for one story. Decide which stories make today's episode and in \
what order, grouping related stories into sections.

Selection rules: drop stories the reader won't care about, drop duplicates \
(keep the strongest pitch), and order sections from most to least important \
to the reader. It is fine to cut aggressively — a tight episode beats a \
bloated one.

Return ONLY a JSON object with these keys, nothing else:
- "sections": an ordered list of objects, each with "title" (a short section \
heading) and "story_ids" (an ordered list of the story ids to include).
- "headlines": 3-5 episode headlines, each 5-8 words, as a list of strings.

Today's date is {current_date}.

The reader's personal preferences follow after these instructions. Base your \
selection and ordering on them.\
"""

EDITOR_ASSEMBLY_SYSTEM_PROMPT_TEMPLATE = """\
You are the editor-in-chief of a daily news podcast, writing the final \
episode text from your rundown. The stories below are already selected, \
ordered, and grouped into sections — keep that structure.

Write in plain English with clear section headings — no bullet-point spam, \
no filler phrases like "In today's edition". Weave each section's stories \
into flowing prose the reader can finish in under 5 minutes. Output the \
episode text only.

Today's date is {current_date}. Disregard any dates mentioned in the story \
summaries — they belong to the original articles and are not today's date.

The reader's personal preferences follow after these instructions. Tailor \
the tone and emphasis accordingly.\
"""


def _build_rundown_user_message(reports: list[Report], user_prompt: str) -> str:
    parts: list[str] = []
    if user_prompt.strip():
        parts.append(f"## Reader's interests and preferences\n\n{user_prompt.strip()}\n")
    parts.append("## Pitches\n")
    for report in reports:
        recommendation = "include" if report.recommend_include else "skip"
        parts.append(
            f"Story {report.source_id}: {report.source_title} ({report.source_name})\n"
            f"Pitch: {report.editor_note}\n"
            f"Reporter recommends: {recommendation} | Importance: {report.importance}/5\n"
        )
    return "\n".join(parts)


def _fallback_rundown(reports: list[Report]) -> Rundown:
    """All recommended stories (or all stories) in source order, one section."""
    included = [r for r in reports if r.recommend_include] or reports
    return Rundown(
        sections=[
            RundownSection(title=FALLBACK_SECTION_TITLE, story_ids=[r.source_id for r in included])
        ],
        headlines=[],
        fallback=True,
    )


def _parse_rundown_response(raw: str, reports: list[Report]) -> Rundown:
    data = extract_json_object(raw)
    if data is None:
        logger.warning("Editor rundown was not valid JSON — using fallback rundown")
        return _fallback_rundown(reports)

    valid_ids = {r.source_id for r in reports}
    seen: set[int] = set()
    sections: list[RundownSection] = []
    for entry in data.get("sections") or []:
        if not isinstance(entry, dict):
            continue
        story_ids = []
        for story_id in entry.get("story_ids") or []:
            if isinstance(story_id, int) and story_id in valid_ids and story_id not in seen:
                seen.add(story_id)
                story_ids.append(story_id)
        if story_ids:
            sections.append(
                RundownSection(title=str(entry.get("title") or "Stories"), story_ids=story_ids)
            )

    if not sections:
        logger.warning("Editor rundown contained no valid story ids — using fallback rundown")
        return _fallback_rundown(reports)

    headlines = [h.strip() for h in data.get("headlines") or [] if isinstance(h, str) and h.strip()]
    return Rundown(sections=sections, headlines=headlines)


def build_rundown(
    provider: LLMProvider, reports: list[Report], user_prompt: str, current_date: str
) -> Rundown:
    """Ask the editor to select and order stories. LLM errors propagate."""
    system_prompt = EDITOR_RUNDOWN_SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date)
    user_message = _build_rundown_user_message(reports, user_prompt)

    with app_tracing.span(
        "editor_rundown",
        attributes={"pitch_count": len(reports)},
        inputs={"system": system_prompt, "user": user_message},
    ) as active_span:
        raw = provider.complete(system=system_prompt, user=user_message)
        if active_span is not None:
            active_span.set_outputs({"result": raw})

    return _parse_rundown_response(raw, reports)


def _build_assembly_user_message(
    rundown: Rundown, reports_by_id: dict[int, Report], user_prompt: str
) -> str:
    parts: list[str] = []
    if user_prompt.strip():
        parts.append(f"## Reader's interests and preferences\n\n{user_prompt.strip()}\n")
    parts.append("## Rundown\n")
    for section in rundown.sections:
        parts.append(f"### {section.title}\n")
        for story_id in section.story_ids:
            report = reports_by_id[story_id]
            parts.append(f"Story: {report.source_title} ({report.source_name})\n{report.summary}\n")
    return "\n".join(parts)


def assemble_episode(
    provider: LLMProvider,
    rundown: Rundown,
    reports_by_id: dict[int, Report],
    user_prompt: str,
    current_date: str,
) -> str:
    """Write the final episode text from the rundown. LLM errors propagate."""
    system_prompt = EDITOR_ASSEMBLY_SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date)
    user_message = _build_assembly_user_message(rundown, reports_by_id, user_prompt)

    with app_tracing.span(
        "editor_assembly",
        attributes={"section_count": len(rundown.sections)},
        inputs={"system": system_prompt, "user": user_message},
    ) as active_span:
        episode_text = provider.complete(system=system_prompt, user=user_message)
        if active_span is not None:
            active_span.set_outputs({"result": episode_text})

    return episode_text
