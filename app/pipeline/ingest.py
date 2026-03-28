"""Gmail ingestion: fetch newsletters since last run, label as processed, store newsletters."""

import base64
import email
import html
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.app_config import get_app_config
from app.gmail_auth import build_gmail_service
from app.models import Newsletter, Run

logger = logging.getLogger(__name__)


def run(db: Session, current_run: Run) -> None:
    """Fetch emails from Gmail and persist newsletters to the DB.

    Steps:
    1. Build the Gmail query using the configured label + date window since the
       last successful run.
    2. Fetch all matching message IDs (paginated).
    3. For each message: parse sender, subject, body; store as a Newsletter row.
    4. Deduplicate within the current run by URL (increment seen_count).
    5. Apply the 'processed' label so the message is skipped next run.
    6. Update current_run.newsletters_found.
    """
    service = build_gmail_service()
    cfg = get_app_config()["gmail"]
    label_name: str = cfg["label"]
    processed_label_name: str = cfg["processed_label"]
    lookback_days: int = int(cfg.get("lookback_days", 7))

    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    query = f"label:{label_name} -label:{processed_label_name} after:{since.strftime('%Y/%m/%d')}"

    logger.info("Gmail query: %s", query)

    message_ids = _list_messages(service, query)
    logger.info("Found %d message(s) matching query", len(message_ids))

    processed_label_id = _get_or_create_label(service, processed_label_name)
    count = 0

    for msg_id in message_ids:
        raw = _fetch_message(service, msg_id)
        newsletter = _parse_to_newsletter(raw, current_run.id)
        _upsert_newsletter(db, newsletter, current_run.id)
        _apply_label(service, msg_id, processed_label_id)
        logger.info("Stored newsletter: %s", newsletter.title)
        count += 1

    logger.info("Ingestion complete — %d newsletter(s) stored", count)
    current_run.newsletters_found = count
    db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _list_messages(service, query: str) -> list[str]:
    """Return all message IDs matching *query*, following pagination."""
    ids: list[str] = []
    page_token = None

    while True:
        kwargs: dict = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().messages().list(**kwargs).execute()
        ids.extend(m["id"] for m in response.get("messages", []))

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return ids


def _fetch_message(service, msg_id: str) -> dict:
    """Fetch a single message in full format."""
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()


def _parse_to_newsletter(raw: dict, run_id: int) -> Newsletter:
    """Extract a Newsletter from a raw Gmail API message payload."""
    headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}

    subject = headers.get("subject", "(no subject)")
    body = _extract_body(raw.get("payload", {}))
    url = _extract_first_url(body)
    published_at = _parse_date_header(headers.get("date"))

    return Newsletter(
        run_id=run_id,
        title=subject,
        url=url,
        raw_content=body,
        published_at=published_at,
    )


def _extract_body(payload: dict) -> str:
    """Decode and return the plain-text (or HTML-stripped) body of a message."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return _decode_b64(data)

    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        return _strip_html(_decode_b64(data))

    # multipart — prefer text/plain, fall back to text/html
    parts = payload.get("parts", [])
    plain = next((p for p in parts if p.get("mimeType") == "text/plain"), None)
    if plain:
        return _decode_b64(plain.get("body", {}).get("data", ""))

    html_part = next((p for p in parts if p.get("mimeType") == "text/html"), None)
    if html_part:
        return _strip_html(_decode_b64(html_part.get("body", {}).get("data", "")))

    # recurse into nested multipart parts
    for part in parts:
        if part.get("mimeType", "").startswith("multipart/"):
            result = _extract_body(part)
            if result:
                return result

    return ""


def _decode_b64(data: str) -> str:
    if not data:
        return ""
    # Gmail uses URL-safe base64
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _strip_html(text: str) -> str:
    """Very lightweight HTML → plain text (strips tags, decodes entities)."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_first_url(text: str) -> str | None:
    """Return the first http(s) URL found in *text*, or None."""
    match = re.search(r"https?://[^\s\"'<>]+", text)
    return match.group(0) if match else None


def _parse_date_header(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        # Normalise to UTC, strip tzinfo for storage
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def _upsert_newsletter(db: Session, newsletter: Newsletter, run_id: int) -> None:
    """Insert *newsletter*, or increment seen_count if the same URL already exists this run."""
    if newsletter.url:
        existing = (
            db.query(Newsletter)
            .filter(Newsletter.run_id == run_id, Newsletter.url == newsletter.url)
            .first()
        )
        if existing:
            existing.seen_count += 1
            return
    db.add(newsletter)


def _get_or_create_label(service, label_name: str) -> str:
    """Return the label ID for *label_name*, creating it if necessary."""
    response = service.users().labels().list(userId="me").execute()
    for label in response.get("labels", []):
        if label["name"] == label_name:
            return label["id"]

    created = service.users().labels().create(userId="me", body={"name": label_name}).execute()
    return created["id"]


def _apply_label(service, msg_id: str, label_id: str) -> None:
    """Add *label_id* to the message."""
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": [label_id]},
    ).execute()
