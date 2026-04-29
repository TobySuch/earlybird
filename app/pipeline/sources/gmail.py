"""Gmail newsletter source — wraps the Gmail API behind NewsletterSource."""

from __future__ import annotations

import base64
import email
import html
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

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
        self._pending_label_id: str | None = None
        self._pending_msg_ids: list[str] = []

    # ── Public interface ──────────────────────────────────────────────────

    def fetch(self, since: datetime) -> list[SourceItem]:
        """Return all unprocessed newsletter items since *since*.

        Labels are NOT applied here — call mark_processed() after the full
        pipeline succeeds so that a mid-run error does not consume emails.
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

        self._pending_label_id = self._get_or_create_label(service, processed_label_name)
        self._pending_msg_ids = list(message_ids)

        items: list[SourceItem] = []
        for msg_id in message_ids:
            raw = self._fetch_message(service, msg_id)
            item = self._parse_to_source_item(raw)
            items.append(item)
            logger.info("Fetched item: %s", item.title)

        return items

    def count_unprocessed(self, since: datetime) -> int:
        """Return the number of unprocessed messages without fetching bodies."""
        service = self._get_service()
        label_name: str = self._cfg["label"]
        processed_label_name: str = self._cfg["processed_label"]
        query = (
            f"label:{label_name} -label:{processed_label_name} after:{since.strftime('%Y/%m/%d')}"
        )
        logger.info("Gmail count query: %s", query)
        return len(self._list_messages(service, query))

    def mark_processed(self) -> None:
        """Apply the processed label to all messages fetched in the last fetch() call."""
        if not self._pending_msg_ids or not self._pending_label_id:
            return
        service = self._get_service()
        for msg_id in self._pending_msg_ids:
            self._apply_label(service, msg_id, self._pending_label_id)
            logger.info("Marked message %s as processed", msg_id)
        self._pending_msg_ids = []
        self._pending_label_id = None

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
        body = _clean_content(_extract_body(raw.get("payload", {})))
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


class _HTMLTextExtractor(HTMLParser):
    """Extract visible text from HTML, suppressing style/script/head content."""

    _SKIP_TAGS = frozenset({"style", "script", "head"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def handle_comment(self, data: str) -> None:  # noqa: ANN001
        pass

    def get_text(self) -> str:
        return "".join(self._parts)


def _strip_html(text: str) -> str:
    """Extract visible plain text from HTML, skipping style/script/head blocks."""
    extractor = _HTMLTextExtractor()
    extractor.feed(text)
    raw = extractor.get_text()
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


_TRACKING_DOMAINS = re.compile(
    r"https?://(?:"
    r"click\.mailchimp\.com"
    r"|click\.e\.economist\.com"
    r"|links\.substack\.com"
    r"|links\.tldrnewsletter\.com"
    r"|a\.tldrnewsletter\.com"
    r"|tracking\.tldrnewsletter\.com"
    r"|link\.mail\.beehiiv\.com"
    r"|email\.mg\.[^/]+"
    r"|r\.email\.[^/]+"
    r"|t\.co"
    r")/[^\s\"'<>]*",
    re.IGNORECASE,
)

_FOOTER_TRIGGERS = re.compile(
    r"^(?:"
    r"if you no longer wish to receive"
    r"|you received this email because"
    r"|you're receiving this because"
    r"|you are receiving this"
    r"|to unsubscribe from this list"
    r"|to stop receiving"
    r"|this email (?:was|has been) sent to"
    r"|love tldr\?"
    r"|want to advertise in tldr"
    r"|links:\s*$"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

_BOILERPLATE_LINE = re.compile(
    r"^[ \t]*(?:"
    r"view (?:this )?email in (?:your )?browser"
    r"|view in browser"
    r"|unsubscribe(?: here)?"
    r"|manage (?:your )?(?:preferences|subscriptions?)"
    r"|update (?:your )?(?:email )?preferences"
    r"|copyright\s+(?:©\s*)?\d{4}"
    r"|©\s*\d{4}"
    r"|all rights reserved"
    r"|follow us on (?:twitter|facebook|linkedin|instagram|youtube)"
    r"|privacy policy"
    r"|terms of (?:use|service)"
    r"|read online"
    r")[ \t]*[.|,]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

_SEPARATOR_LINE = re.compile(r"^[ \t]*[-=*_~]{3,}[ \t]*$", re.MULTILINE)

_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "utm_reader",
        "utm_referrer",
        "mc_cid",
        "mc_eid",
        "fbclid",
        "gclid",
        "gclsrc",
        "msclkid",
    }
)


def _strip_utm_params(match: re.Match) -> str:
    base = match.group(1)
    query = match.group(2) or ""
    fragment = match.group(3) or ""
    if not query:
        return base + fragment
    pairs = query.lstrip("?").split("&")
    cleaned = [p for p in pairs if p.split("=")[0].lower() not in _TRACKING_PARAMS]
    if not cleaned:
        return base + fragment
    return base + "?" + "&".join(cleaned) + fragment


def _clean_content(text: str) -> str:
    """Remove noise from extracted email body before LLM ingestion."""
    if not text:
        return text

    # Strip zero-width chars used as email preview padding (e.g. TLDR ‌ sequences)
    text = re.sub(r"[​‌‍⁠﻿­]", "", text)

    # Decode HTML entities in plain-text emails (e.g. Economist text/plain has &rsquo;)
    text = html.unescape(text)

    # Strip residual HTML tags from hybrid plain-text/HTML emails
    text = re.sub(r"<[^>]+>", " ", text)

    # Strip UTM/tracking query params; preserve meaningful params
    text = re.sub(
        r"(\bhttps?://[^\s\"'<>?#]+)(\?[^\s\"'<>]*)(\#[^\s\"'<>]*)?",
        _strip_utm_params,
        text,
    )

    # Replace known tracking redirect URLs
    text = _TRACKING_DOMAINS.sub("[link]", text)

    # Truncate at footer boilerplate
    m = _FOOTER_TRIGGERS.search(text)
    if m:
        text = text[: m.start()].rstrip()

    # Remove standalone boilerplate lines
    text = _BOILERPLATE_LINE.sub("", text)

    # Remove decorative separators
    text = _SEPARATOR_LINE.sub("", text)

    # Remove TLDR-style inline footnote numbers: "read more [8]" → "read more"
    text = re.sub(r"\s*\[\d+\]", "", text)

    # Normalise blank lines
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
