"""Tests for GmailSource — mocked Gmail API, no live calls."""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.pipeline.sources.gmail import (
    GmailSource,
    _clean_content,
    _decode_b64,
    _extract_body,
    _extract_first_url,
    _parse_date_header,
    _strip_html,
)

_GMAIL_CFG = {
    "label": "Newsletters",
    "processed_label": "earlybird-processed",
    "lookback_days": 7,
}

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    """In-memory SQLite session, isolated per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _b64(text: str) -> str:
    """URL-safe base64 encode *text* (mimics Gmail encoding)."""
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _make_message(
    subject="Test Newsletter",
    body_text="Hello world https://example.com",
    date="Mon, 1 Jan 2024 09:00:00 +0000",
    msg_id="msg001",
):
    """Build a minimal Gmail API message payload."""
    return {
        "id": msg_id,
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": "newsletter@example.com"},
                {"name": "Date", "value": date},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _b64(body_text)},
                }
            ],
        },
    }


def _build_mock_service(messages, label_id="label_processed"):
    """Build a mock Gmail service that returns *messages* from list()."""
    service = MagicMock()

    list_response = {"messages": [{"id": m["id"]} for m in messages]}
    service.users().messages().list().execute.return_value = list_response

    msg_map = {m["id"]: m for m in messages}
    service.users().messages().get().execute.side_effect = lambda: msg_map[
        service.users().messages().get.call_args[1]["id"]
    ]

    service.users().labels().list().execute.return_value = {
        "labels": [{"id": label_id, "name": "earlybird-processed"}]
    }
    service.users().messages().modify().execute.return_value = {}

    return service


# ── Unit tests for module-level helpers ───────────────────────────────────────


def test_decode_b64_roundtrip():
    original = "Hello, world! 🎉"
    assert _decode_b64(_b64(original)) == original


def test_decode_b64_empty():
    assert _decode_b64("") == ""


def test_strip_html_removes_tags():
    result = _strip_html("<p>Hello <b>world</b></p>")
    assert "<" not in result
    assert "Hello" in result
    assert "world" in result


def test_strip_html_decodes_entities():
    result = _strip_html("&amp; &lt; &gt;")
    assert "&" in result
    assert "<" in result
    assert ">" in result
    assert "&amp;" not in result
    assert "&lt;" not in result


def test_extract_first_url_found():
    text = "Check this out: https://example.com/article and more"
    assert _extract_first_url(text) == "https://example.com/article"


def test_extract_first_url_none():
    assert _extract_first_url("no links here") is None


def test_parse_date_header_valid():
    dt = _parse_date_header("Mon, 1 Jan 2024 09:00:00 +0000")
    assert dt is not None
    assert dt.year == 2024
    assert dt.tzinfo is None  # stored without tzinfo


def test_parse_date_header_none():
    assert _parse_date_header(None) is None


def test_parse_date_header_invalid():
    assert _parse_date_header("not a date") is None


def test_extract_body_plain_text():
    payload = {
        "mimeType": "text/plain",
        "body": {"data": _b64("Plain text content")},
    }
    assert _extract_body(payload) == "Plain text content"


def test_extract_body_html():
    payload = {
        "mimeType": "text/html",
        "body": {"data": _b64("<p>HTML content</p>")},
    }
    result = _extract_body(payload)
    assert "HTML content" in result
    assert "<" not in result


def test_extract_body_multipart_prefers_plain():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("Plain part")}},
            {"mimeType": "text/html", "body": {"data": _b64("<p>HTML part</p>")}},
        ],
    }
    assert _extract_body(payload) == "Plain part"


# ── _strip_html improvements ──────────────────────────────────────────────────


def test_strip_html_excludes_style_content():
    html_input = (
        "<html><head>"
        "<style>body { font-family: Arial; color: #333; }</style>"
        "</head><body><p>Real content here.</p></body></html>"
    )
    result = _strip_html(html_input)
    assert "Real content here" in result
    assert "font-family" not in result
    assert "Arial" not in result
    assert "#333" not in result


def test_strip_html_excludes_script_content():
    html_input = (
        "<html><body>"
        "<script>var tracker = 'abc123'; window.onload = function() {};</script>"
        "<p>Newsletter body.</p>"
        "</body></html>"
    )
    result = _strip_html(html_input)
    assert "Newsletter body" in result
    assert "tracker" not in result
    assert "window.onload" not in result


# ── _clean_content ────────────────────────────────────────────────────────────


def test_clean_content_removes_utm_params():
    text = (
        "Read more at https://example.com/article?utm_source=newsletter"
        "&utm_medium=email&utm_campaign=spring2024 for details."
    )
    result = _clean_content(text)
    assert "https://example.com/article" in result
    assert "utm_source" not in result
    assert "utm_medium" not in result
    assert "utm_campaign" not in result


def test_clean_content_preserves_meaningful_query_params():
    text = "Visit https://example.com/search?q=python&page=2 for results."
    result = _clean_content(text)
    assert "https://example.com/search?q=python&page=2" in result


def test_clean_content_removes_tracking_urls():
    text = (
        "Read here: https://click.mailchimp.com/track/click/123456/example.com?p=xyz "
        "and here: https://click.e.economist.com/?qs=ABB7InYiOjE "
        "and here: https://links.tldrnewsletter.com/9jLT5n extra text."
    )
    result = _clean_content(text)
    assert "click.mailchimp.com" not in result
    assert "click.e.economist.com" not in result
    assert "links.tldrnewsletter.com" not in result
    assert result.count("[link]") == 3


def test_clean_content_truncates_at_footer():
    text = (
        "Today's top stories:\n\n"
        "Item 1: AI makes progress.\n\n"
        "You received this email because you subscribed at example.com.\n"
        "To unsubscribe visit https://example.com/unsub\n"
        "Copyright © 2024 Example Inc."
    )
    result = _clean_content(text)
    assert "AI makes progress" in result
    assert "You received this email because" not in result
    assert "Copyright" not in result


def test_clean_content_truncates_at_footer_case_insensitive():
    text = "Real content.\n\nIF YOU NO LONGER WISH TO RECEIVE these emails, click here."
    result = _clean_content(text)
    assert "Real content" in result
    assert "IF YOU NO LONGER WISH" not in result


def test_clean_content_truncates_tldr_footer():
    text = (
        "Great article about Python.\n\n"
        "Love TLDR? Tell your friends and get rewards!\n\n"
        "Share your referral link: https://refer.tldr.tech/abc123"
    )
    result = _clean_content(text)
    assert "Great article about Python" in result
    assert "Tell your friends" not in result
    assert "refer.tldr.tech" not in result


def test_clean_content_truncates_links_section():
    text = (
        "OpenAI introduced workspace agents.\n\n"
        "Links:\n"
        "------\n"
        "[1] https://example.com/article\n"
        "[2] https://example.com/other\n"
    )
    result = _clean_content(text)
    assert "OpenAI introduced workspace agents" in result
    assert "[1] https://example.com/article" not in result


def test_clean_content_removes_boilerplate_lines():
    text = (
        "Great article about Python.\n"
        "View this email in your browser\n"
        "More article content here.\n"
        "Unsubscribe\n"
        "Follow us on Twitter\n"
        "All rights reserved\n"
        "Final sentence of real content."
    )
    result = _clean_content(text)
    assert "Great article about Python" in result
    assert "More article content here" in result
    assert "Final sentence of real content" in result
    assert "View this email in your browser" not in result
    assert "All rights reserved" not in result
    lines = [ln.strip() for ln in result.splitlines() if ln.strip()]
    assert "Unsubscribe" not in lines
    assert "Follow us on Twitter" not in lines


def test_clean_content_removes_decorative_separators():
    text = "Section heading\n---\nBody text.\n=====\nMore body text.\n***\n"
    result = _clean_content(text)
    assert "Section heading" in result
    assert "Body text" in result
    assert "More body text" in result
    for line in result.splitlines():
        stripped = line.strip()
        if stripped:
            assert not all(c in "-=*_~" for c in stripped), f"Separator leaked: {line!r}"


def test_clean_content_removes_zero_width_chars():
    text = "OpenAI introduced workspace agents‌ ‌ ‌ for complex tasks."
    result = _clean_content(text)
    assert "‌" not in result
    assert "OpenAI introduced workspace agents" in result
    assert "for complex tasks" in result


def test_clean_content_decodes_html_entities():
    text = "Britain&rsquo;s alliance with America &mdash; it&rsquo;s complicated."
    result = _clean_content(text)
    assert "’" in result  # right single quotation mark
    assert "&rsquo;" not in result
    assert "&mdash;" not in result


def test_clean_content_strips_residual_html_tags():
    text = (
        "<link rel=stylesheet href=https://example.com/font.css>\n"
        "The Economist\n\n"
        "Real article content here."
    )
    result = _clean_content(text)
    assert "Real article content here" in result
    assert "<link" not in result
    assert "rel=stylesheet" not in result


def test_clean_content_removes_tldr_footnote_numbers():
    text = (
        "OpenAI introduced workspace agents [8] in ChatGPT, "
        "allowing teams to create shared AI agents [9] for complex tasks."
    )
    result = _clean_content(text)
    assert "[8]" not in result
    assert "[9]" not in result
    assert "OpenAI introduced workspace agents" in result
    assert "allowing teams to create shared AI agents" in result


def test_clean_content_normalises_whitespace():
    text = "Para one.\n\n\n\n\nPara two."
    result = _clean_content(text)
    assert "Para one" in result
    assert "Para two" in result
    assert "\n\n\n" not in result


def test_clean_content_empty_string():
    assert _clean_content("") == ""


def test_clean_content_plain_text_passthrough():
    text = "Hello, world. This is a plain newsletter with no junk."
    assert _clean_content(text) == text


# ── GmailSource.fetch() tests ─────────────────────────────────────────────────


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_parse_to_source_item_extracts_fields(mock_build, db):
    raw = _make_message(
        subject="My Newsletter", body_text="Visit https://news.example.com for details"
    )
    service = _build_mock_service([raw])
    mock_build.return_value = service

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    since = datetime(2024, 1, 1, tzinfo=timezone.utc)
    items = source.fetch(since)

    assert len(items) == 1
    item = items[0]
    assert item.title == "My Newsletter"
    assert item.url == "https://news.example.com"
    assert item.source_type == "gmail"
    assert "Visit" in item.raw_content


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_fetch_query_excludes_processed_and_respects_since(mock_build, db):
    service = MagicMock()
    service.users().messages().list().execute.return_value = {"messages": []}
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "lbl1", "name": "earlybird-processed"}]
    }
    mock_build.return_value = service

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    source.fetch(since)

    call_kwargs = service.users().messages().list.call_args[1]
    query: str = call_kwargs["q"]

    assert "label:Newsletters" in query
    assert "-label:earlybird-processed" in query
    assert f"after:{since.strftime('%Y/%m/%d')}" in query


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_fetch_returns_source_items(mock_build, db):
    messages = [
        _make_message(subject="Newsletter A", body_text="https://a.example.com", msg_id="msg001"),
        _make_message(subject="Newsletter B", body_text="https://b.example.com", msg_id="msg002"),
    ]
    service = _build_mock_service(messages)
    mock_build.return_value = service

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    items = source.fetch(datetime(2024, 1, 1, tzinfo=timezone.utc))

    assert len(items) == 2
    assert {i.title for i in items} == {"Newsletter A", "Newsletter B"}
    assert all(i.source_type == "gmail" for i in items)


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_fetch_does_not_apply_label(mock_build, db):
    """fetch() must NOT apply the processed label — that is deferred to mark_processed()."""
    messages = [_make_message()]
    service = _build_mock_service(messages, label_id="lbl_processed")
    mock_build.return_value = service
    service.users().messages().modify.reset_mock()

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    source.fetch(datetime(2024, 1, 1, tzinfo=timezone.utc))

    service.users().messages().modify.assert_not_called()


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_mark_processed_applies_label_after_fetch(mock_build, db):
    """mark_processed() applies the label to all messages from the last fetch()."""
    messages = [_make_message()]
    service = _build_mock_service(messages, label_id="lbl_processed")
    mock_build.return_value = service
    service.users().messages().modify.reset_mock()

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    source.fetch(datetime(2024, 1, 1, tzinfo=timezone.utc))
    source.mark_processed()

    service.users().messages().modify.assert_called_once_with(
        userId="me",
        id="msg001",
        body={"addLabelIds": ["lbl_processed"]},
    )


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_mark_processed_is_idempotent(mock_build, db):
    """Calling mark_processed() twice does not apply the label a second time."""
    messages = [_make_message()]
    service = _build_mock_service(messages, label_id="lbl_processed")
    mock_build.return_value = service
    service.users().messages().modify.reset_mock()

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    source.fetch(datetime(2024, 1, 1, tzinfo=timezone.utc))
    source.mark_processed()
    source.mark_processed()

    assert service.users().messages().modify.call_count == 1


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_fetch_creates_processed_label_if_absent(mock_build, db):
    service = MagicMock()
    service.users().messages().list().execute.return_value = {"messages": []}
    service.users().labels().list().execute.return_value = {"labels": []}
    service.users().labels().create.return_value.execute.return_value = {"id": "new_lbl"}
    mock_build.return_value = service

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    source.fetch(datetime(2024, 1, 1, tzinfo=timezone.utc))

    service.users().labels().create.assert_called_once_with(
        userId="me", body={"name": "earlybird-processed"}
    )


@patch("app.pipeline.sources.gmail.build_gmail_service")
def test_fetch_empty_returns_empty_list(mock_build, db):
    service = MagicMock()
    service.users().messages().list().execute.return_value = {"messages": []}
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "lbl1", "name": "earlybird-processed"}]
    }
    mock_build.return_value = service

    source = GmailSource(db=db, cfg=_GMAIL_CFG)
    items = source.fetch(datetime(2024, 1, 1, tzinfo=timezone.utc))

    assert items == []
