"""Tests for app/pipeline/ingest.py — mocked Gmail API, no live calls."""

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Run, Story
from app.pipeline import ingest
from app.pipeline.ingest import (
    _decode_b64,
    _extract_body,
    _extract_first_url,
    _parse_date_header,
    _parse_to_story,
    _strip_html,
)

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


@pytest.fixture
def current_run(db):
    run = Run(started_at=datetime.utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _b64(text: str) -> str:
    """URL-safe base64 encode *text* (mimics Gmail encoding)."""
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _make_message(
    subject="Test Newsletter",
    body_text="Hello world https://example.com",
    date="Mon, 1 Jan 2024 09:00:00 +0000",
):
    """Build a minimal Gmail API message payload."""
    return {
        "id": "msg001",
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


# ── Unit tests for helpers ────────────────────────────────────────────────────


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
    # html.unescape converts entities to their characters — & < > should appear
    assert "&" in result
    assert "<" in result
    assert ">" in result
    # Original entities should be gone
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


def test_parse_to_story_extracts_fields():
    raw = _make_message(
        subject="My Newsletter", body_text="Visit https://news.example.com for details"
    )
    story = _parse_to_story(raw, run_id=1)

    assert story.title == "My Newsletter"
    assert story.url == "https://news.example.com"
    assert story.run_id == 1
    assert "Visit" in story.raw_content


# ── Integration-style tests for ingest.run ───────────────────────────────────


def _build_mock_service(messages, label_id="label_processed"):
    """Build a mock Gmail service that returns *messages* from list()."""
    service = MagicMock()

    # messages().list().execute() returns a single page
    list_response = {"messages": [{"id": m["id"]} for m in messages]}
    service.users().messages().list().execute.return_value = list_response

    # messages().get().execute() returns the full message by id
    msg_map = {m["id"]: m for m in messages}
    service.users().messages().get().execute.side_effect = lambda: msg_map[
        service.users().messages().get.call_args[1]["id"]
    ]

    # labels().list().execute() returns existing labels
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": label_id, "name": "earlybird-processed"}]
    }

    # messages().modify().execute() — no-op
    service.users().messages().modify().execute.return_value = {}

    return service


@patch("app.pipeline.ingest.build_gmail_service")
@patch("app.pipeline.ingest.get_app_config")
def test_run_stores_stories(mock_cfg, mock_build, db, current_run):
    mock_cfg.return_value = {
        "gmail": {"label": "Newsletters", "processed_label": "earlybird-processed"}
    }

    messages = [
        _make_message(subject="Newsletter A", body_text="https://a.example.com"),
        _make_message(subject="Newsletter B", body_text="https://b.example.com"),
    ]
    messages[1]["id"] = "msg002"

    service = MagicMock()
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": m["id"]} for m in messages]
    }
    msg_map = {m["id"]: m for m in messages}

    def get_execute():
        call = service.users().messages().get.call_args
        return msg_map[call[1]["id"]]

    service.users().messages().get().execute.side_effect = get_execute
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "lbl1", "name": "earlybird-processed"}]
    }
    service.users().messages().modify().execute.return_value = {}
    mock_build.return_value = service

    ingest.run(db, current_run)

    stories = db.query(Story).filter(Story.run_id == current_run.id).all()
    assert len(stories) == 2
    assert current_run.stories_found == 2


@patch("app.pipeline.ingest.build_gmail_service")
@patch("app.pipeline.ingest.get_app_config")
def test_run_deduplicates_by_url(mock_cfg, mock_build, db, current_run):
    mock_cfg.return_value = {
        "gmail": {"label": "Newsletters", "processed_label": "earlybird-processed"}
    }

    shared_url = "https://shared.example.com"
    messages = [
        {**_make_message(subject="A", body_text=shared_url), "id": "msg001"},
        {**_make_message(subject="B", body_text=shared_url), "id": "msg002"},
    ]

    service = MagicMock()
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": m["id"]} for m in messages]
    }
    msg_map = {m["id"]: m for m in messages}

    def get_execute():
        call = service.users().messages().get.call_args
        return msg_map[call[1]["id"]]

    service.users().messages().get().execute.side_effect = get_execute
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "lbl1", "name": "earlybird-processed"}]
    }
    service.users().messages().modify().execute.return_value = {}
    mock_build.return_value = service

    ingest.run(db, current_run)

    stories = db.query(Story).filter(Story.run_id == current_run.id).all()
    assert len(stories) == 1
    assert stories[0].seen_count == 2


@patch("app.pipeline.ingest.build_gmail_service")
@patch("app.pipeline.ingest.get_app_config")
def test_run_creates_processed_label_if_absent(mock_cfg, mock_build, db, current_run):
    mock_cfg.return_value = {
        "gmail": {"label": "Newsletters", "processed_label": "earlybird-processed"}
    }

    service = MagicMock()
    service.users().messages().list().execute.return_value = {"messages": []}
    # No existing labels → create() should be called
    service.users().labels().list().execute.return_value = {"labels": []}
    service.users().labels().create.return_value.execute.return_value = {"id": "new_lbl"}
    mock_build.return_value = service

    ingest.run(db, current_run)

    service.users().labels().create.assert_called_once_with(
        userId="me", body={"name": "earlybird-processed"}
    )


@patch("app.pipeline.ingest.build_gmail_service")
@patch("app.pipeline.ingest.get_app_config")
def test_run_no_messages_sets_stories_found_zero(mock_cfg, mock_build, db, current_run):
    mock_cfg.return_value = {
        "gmail": {"label": "Newsletters", "processed_label": "earlybird-processed"}
    }

    service = MagicMock()
    service.users().messages().list().execute.return_value = {"messages": []}
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "lbl1", "name": "earlybird-processed"}]
    }
    mock_build.return_value = service

    ingest.run(db, current_run)

    assert current_run.stories_found == 0
