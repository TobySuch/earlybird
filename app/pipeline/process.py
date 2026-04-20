"""LLM processing: summarise newsletters into a daily digest."""

from __future__ import annotations

import datetime
import logging

from sqlalchemy.orm import Session

from app import tracing as app_tracing
from app.llm.factory import get_llm_provider, get_llm_user_prompt
from app.models import Episode, NewsSource, Run

logger = logging.getLogger(__name__)

_ORDINAL_SUFFIX = {1: "st", 2: "nd", 3: "rd"}

SYSTEM_PROMPT_TEMPLATE = """\
You are an expert newsletter editor. Your job is to read a batch of newsletter \
content and produce a concise, well-structured daily digest for the reader.

For each source, extract the key insight or story in 2-4 sentences. \
Group related topics together. Use clear section headings. \
Write in plain English - no bullet-point spam, no filler phrases like \
"In today's edition". Aim for a digest the reader can finish in under 5 minutes.

Today's date is {current_date}. Disregard any dates mentioned in the source \
content — they belong to the original articles and are not today's date.

The reader's personal preferences follow after these instructions. \
Tailor the selection and emphasis accordingly.\
"""


def _ordinal(n: int) -> str:
    suffix = _ORDINAL_SUFFIX.get(n % 10 if not (11 <= n % 100 <= 13) else 0, "th")
    return f"{n}{suffix}"


def _format_date(dt: datetime.datetime) -> str:
    return f"{dt.strftime('%A')}, the {_ordinal(dt.day)} of {dt.strftime('%B %Y')}"


def _build_user_message(sources: list[NewsSource], user_prompt: str) -> str:
    """Concatenate all NewsSource content into a single prompt string."""
    parts: list[str] = []

    if user_prompt.strip():
        parts.append(f"## My interests and preferences\n\n{user_prompt.strip()}\n")

    parts.append("## Newsletter content\n")

    for i, source in enumerate(sources, start=1):
        title = source.title or "(untitled)"
        source_name = source.source_name or "unknown"
        content = (source.raw_content or "").strip()

        parts.append(f"=== SOURCE {i} ===\nTitle: {title}\nSource: {source_name}\n---\n{content}\n")

    return "\n".join(parts)


def run(db: Session, current_run: Run) -> None:
    """Call the configured LLM to summarise newsletters for this run.

    Steps:
    1. Fetch all NewsSource rows for current_run from DB.
    2. If none, skip the LLM call entirely.
    3. Build the user message (formatted content + user preferences).
    4. Make a single LLM call with the baked-in system prompt.
    5. Write the result to a new Episode row (newsletter_text).
    6. Update current_run.newsletters_included.
    """
    sources = db.query(NewsSource).filter(NewsSource.run_id == current_run.id).all()

    if not sources:
        logger.warning("No NewsSource rows found for run %d — skipping LLM call", current_run.id)
        current_run.newsletters_included = 0
        db.commit()
        return

    logger.info("Processing %d source(s) for run %d", len(sources), current_run.id)

    provider = get_llm_provider(db)
    user_prompt = get_llm_user_prompt(db)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        current_date=_format_date(datetime.datetime.now())
    )
    user_message = _build_user_message(sources, user_prompt)
    logger.debug("User message length: %d chars", len(user_message))

    with app_tracing.span("process", attributes={"sources_count": len(sources)}):
        newsletter_text = provider.complete(system=system_prompt, user=user_message)

    episode = Episode(
        run_id=current_run.id,
        newsletter_text=newsletter_text,
        podcast_script=None,  # TODO: populate in publish.py
    )
    db.add(episode)

    current_run.newsletters_included = len(sources)
    db.commit()
    logger.info("Episode created for run %d (%d sources)", current_run.id, len(sources))
