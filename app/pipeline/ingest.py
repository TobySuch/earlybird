"""Gmail ingestion: fetch newsletters since last run, label as processed, store stories."""

from app.models import Run


def run(db, current_run: Run) -> None:
    """Fetch emails from Gmail and persist stories to the DB.

    Steps:
    1. Build Gmail query from active Sources (gmail_filter fields) + date window
       (since last successful run.started_at).
    2. Authenticate with OAuth2 (token.json / refresh flow).
    3. For each message: parse sender, subject, body; extract story links.
    4. Deduplicate against existing stories (increment seen_count on duplicates).
    5. Apply 'earlybird-processed' label so the message is skipped next run.
    6. Update current_run.stories_found.
    """
    # TODO: implement Gmail OAuth2 fetch
    raise NotImplementedError
