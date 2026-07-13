"""Reporter agent: summarise one source and pitch it to the editor."""

from __future__ import annotations

import logging

from app import tracing as app_tracing
from app.llm.base import LLMProvider
from app.pipeline.agents.parsing import extract_json_object
from app.pipeline.agents.types import Report, SourceInput

logger = logging.getLogger(__name__)

_EDITOR_NOTE_FALLBACK_CHARS = 200

REPORTER_SYSTEM_PROMPT_TEMPLATE = """\
You are a reporter on a podcast production team. You receive exactly one \
newsletter article and must file a report for the editor.

Return ONLY a JSON object with these keys, nothing else:
- "summary": the article's key insight or story in 2-4 sentences, written in \
plain English, ready to be read out in the episode.
- "editor_note": a 1-2 sentence pitch telling the editor what this story is \
and why it does or does not deserve airtime.
- "include": true if you recommend including this story in the episode, \
false otherwise.
- "importance": an integer from 1 (skippable) to 5 (must-run).

Today's date is {current_date}. Disregard any dates mentioned in the source \
content — they belong to the original articles and are not today's date.

The reader's personal preferences follow after these instructions. Base your \
include recommendation and importance rating on them.\
"""


def _build_user_message(source: SourceInput, user_prompt: str) -> str:
    parts: list[str] = []
    if user_prompt.strip():
        parts.append(f"## Reader's interests and preferences\n\n{user_prompt.strip()}\n")
    parts.append(
        f"## Article\n\nTitle: {source.title}\nSource: {source.source_name}\n---\n{source.content}"
    )
    return "\n".join(parts)


def _parse_reporter_response(raw: str, source: SourceInput) -> Report:
    """Parse the reporter's JSON; fail open to a degraded report on garbage.

    A mangled summary in the episode beats silently dropping a story, so an
    unparseable response yields the raw text as the summary with include=True.
    """
    data = extract_json_object(raw)
    if data is not None:
        summary = data.get("summary")
        editor_note = data.get("editor_note")
        if isinstance(summary, str) and summary.strip() and isinstance(editor_note, str):
            importance = data.get("importance")
            if not isinstance(importance, int) or isinstance(importance, bool):
                importance = 3
            return Report(
                source_id=source.id,
                source_title=source.title,
                source_name=source.source_name,
                summary=summary.strip(),
                editor_note=editor_note.strip(),
                recommend_include=bool(data.get("include", True)),
                importance=min(max(importance, 1), 5),
            )

    logger.warning("Reporter response for source %d was not valid JSON — degrading", source.id)
    text = raw.strip()
    return Report(
        source_id=source.id,
        source_title=source.title,
        source_name=source.source_name,
        summary=text,
        editor_note=text[:_EDITOR_NOTE_FALLBACK_CHARS],
        recommend_include=True,
        importance=3,
        degraded=True,
    )


def run_reporter(
    provider: LLMProvider, source: SourceInput, user_prompt: str, current_date: str
) -> Report | None:
    """File a report for one source. Returns None if the LLM call fails."""
    system_prompt = REPORTER_SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date)
    user_message = _build_user_message(source, user_prompt)

    try:
        with app_tracing.span(
            "reporter",
            attributes={"source_id": source.id, "source_title": source.title},
            inputs={"system": system_prompt, "user": user_message},
        ) as active_span:
            raw = provider.complete(system=system_prompt, user=user_message)
            if active_span is not None:
                active_span.set_outputs({"result": raw})
    except Exception:
        logger.warning("Reporter failed for source %d (%s)", source.id, source.title, exc_info=True)
        return None

    return _parse_reporter_response(raw, source)
