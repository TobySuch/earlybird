"""LLM processing: filter newsletters by interest profile, summarise, write podcast script."""

from app.models import Run


def run(db, current_run: Run) -> None:
    """Call Claude Haiku to filter and summarise newsletters for this run.

    Steps:
    1. Load interest profile from config table.
    2. Fetch all newsletters for current_run from DB.
    3. Send batch to Claude Haiku with filter + summarise prompt.
    4. Write newsletter_text and podcast_script to a new Episode row.
    5. Update current_run.newsletters_included.
    """
    # TODO: implement Claude Haiku summarisation
    raise NotImplementedError
