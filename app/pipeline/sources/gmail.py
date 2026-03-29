"""Gmail newsletter source — wraps the Gmail API behind NewsletterSource."""

from __future__ import annotations

import base64
import email
import html
import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.gmail_auth import build_gmail_service
from app.pipeline.sources.base import SourceItem

logger = logging.getLogger(__name__)


class GmailSource:
    """Fetches newsletters from Gmail using the configured label."""

    def __init__(self, db: Session, cfg: dict) -> None:
        """
        Args:
            db:  SQLAlchemy session (available for future per-source state).
            cfg: The ``gmail`` sub-dict from app_config, e.g.
                 {"label": "Newsletters",
                  "processed_label": "earlybird-processed",
                  "lookback_days": 7}
        """
        self._db = db
        self._cfg = cfg
        self._service = None  # built lazily on first fetch()

    # ── Public interface ──────────────────────────────────────────────────

    def fetch(self, since: datetime) -> list[SourceItem]:
        """Return all unprocessed newsletter items since *since*.

        Also applies the processed label to each message so it is skipped
        on future runs.
        """
        service = self._get_service()

        label_name: str = self._cfg["label"]
        processed_label_name: str = self._cfg["processed_label"]

        query = (
            f"label:{label_name} -label:{processed_label_name} after:{since.strftime('%Y/%m/%d')}"
        )
        logger.info("Gmail query: %s", query)

        message_ids = self._list_messages(service, query)
        logger.info("Found %d message(s) matching query", len(message_ids))

        processed_label_id = self._get_or_create_label(service, processed_label_name)

        items: list[SourceItem] = []
        for msg_id in message_ids:
            raw = self._fetch_message(service, msg_id)
            item = self._parse_to_source_item(raw)
            items.append(item)
            self._apply_label(service, msg_id, processed_label_id)
            logger.info("Fetched item: %s", item.title)

        return items

    # ── Private helpers ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"GmailSource(label={self._cfg['label']!r})"

    def _get_service(self):
        if self._service is None:
            self._service = build_gmail_service()
        return self._service

    def _list_messages(self, service, query: str) -> list[str]:
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

    def _fetch_message(self, service, msg_id: str) -> dict:
        """Fetch a single message in full format."""
        return service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    def _parse_to_source_item(self, raw: dict) -> SourceItem:
        """Extract a SourceItem from a raw Gmail API message payload."""
        headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "(no subject)")
        body = _extract_body(raw.get("payload", {}))
        url = _extract_first_url(body)
        published_at = _parse_date_header(headers.get("date"))

        return SourceItem(
            title=subject,
            raw_content=body,
            source_type="gmail",
            url=url,
            published_at=published_at,
        )

    def _get_or_create_label(self, service, label_name: str) -> str:
        """Return the label ID for *label_name*, creating it if necessary."""
        response = service.users().labels().list(userId="me").execute()
        for label in response.get("labels", []):
            if label["name"] == label_name:
                return label["id"]

        created = service.users().labels().create(userId="me", body={"name": label_name}).execute()
        return created["id"]

    def _apply_label(self, service, msg_id: str, label_id: str) -> None:
        """Add *label_id* to the message."""
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": [label_id]},
        ).execute()


# ── Module-level pure functions (no Gmail coupling; directly testable) ────────


def _extract_body(payload: dict) -> str:
    """Decode and return the plain-text (or HTML-stripped) body of a message."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        return _decode_b64(payload.get("body", {}).get("data", ""))

    if mime_type == "text/html":
        return _strip_html(_decode_b64(payload.get("body", {}).get("data", "")))

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
