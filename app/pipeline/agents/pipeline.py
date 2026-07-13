"""Agent mode orchestrator: parallel reporters, then the two-stage editor."""

from __future__ import annotations

import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app import tracing as app_tracing
from app.config import get_db_config
from app.llm.factory import get_llm_provider, get_llm_user_prompt
from app.models import Episode, NewsSource, Run
from app.pipeline.agents.editor import assemble_episode, build_rundown
from app.pipeline.agents.reporter import run_reporter
from app.pipeline.agents.types import SourceInput

logger = logging.getLogger(__name__)

DEFAULT_MAX_PARALLEL_REPORTERS = 4


def _max_parallel_reporters(db: Session) -> int:
    raw = get_db_config(db, "llm.agent.max_parallel_reporters")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_PARALLEL_REPORTERS
    return value if value >= 1 else DEFAULT_MAX_PARALLEL_REPORTERS


def run(db: Session, current_run: Run) -> None:
    """Produce an Episode for this run via reporter and editor agents.

    Note: in agent mode current_run.newsletters_included counts the stories
    the editor put in the episode, not the sources fetched.
    """
    from app.pipeline.process import HEADLINES_SYSTEM_PROMPT, format_date

    sources = db.query(NewsSource).filter(NewsSource.run_id == current_run.id).all()

    if not sources:
        logger.warning("No NewsSource rows found for run %d — skipping LLM calls", current_run.id)
        current_run.newsletters_included = 0
        db.commit()
        return

    logger.info("Agent mode: processing %d source(s) for run %d", len(sources), current_run.id)

    # Snapshot before threading — ORM objects must not cross threads.
    inputs = [
        SourceInput(
            id=s.id,
            title=s.title or "(untitled)",
            source_name=s.source_name or "unknown",
            content=(s.raw_content or "").strip(),
        )
        for s in sources
    ]

    reporter_provider = get_llm_provider(db, role="reporter")
    editor_provider = get_llm_provider(db, role="editor")
    user_prompt = get_llm_user_prompt(db)
    current_date = format_date(datetime.datetime.now())

    # Reporter spans run in worker threads, so MLflow's contextvar-based
    # tracing records them as separate root traces rather than children of
    # this span. Acceptable for now.
    with app_tracing.span(
        "agent_process",
        attributes={"sources_count": len(inputs)},
    ):
        max_workers = min(_max_parallel_reporters(db), len(inputs))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(run_reporter, reporter_provider, s, user_prompt, current_date)
                for s in inputs
            ]
            # Collect in submission order so downstream ordering is deterministic.
            reports = [r for r in (f.result() for f in futures) if r is not None]

        if not reports:
            raise RuntimeError("All reporter agents failed — no reports to edit")

        logger.info("Reporters filed %d/%d report(s)", len(reports), len(inputs))

        rundown = build_rundown(editor_provider, reports, user_prompt, current_date)
        reports_by_id = {r.source_id: r for r in reports}
        newsletter_text = assemble_episode(
            editor_provider, rundown, reports_by_id, user_prompt, current_date
        )

        if rundown.headlines:
            episode_headlines = "\n".join(f"• {h}" for h in rundown.headlines)
        else:
            with app_tracing.span(
                "process_headlines",
                inputs={"digest": newsletter_text},
            ) as hl_span:
                episode_headlines = editor_provider.complete(
                    system=HEADLINES_SYSTEM_PROMPT, user=newsletter_text
                )
                if hl_span is not None:
                    hl_span.set_outputs({"result": episode_headlines})

    episode = Episode(
        run_id=current_run.id,
        newsletter_text=newsletter_text,
        episode_headlines=episode_headlines,
    )
    db.add(episode)

    included_count = sum(len(section.story_ids) for section in rundown.sections)
    current_run.newsletters_included = included_count
    db.commit()
    logger.info(
        "Episode created for run %d (%d of %d stories included)",
        current_run.id,
        included_count,
        len(inputs),
    )
