"""Tests for app/pipeline/publish.py."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Episode, Run
from app.pipeline import publish

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def episode(db):
    run = Run(started_at=datetime.now(timezone.utc), status="running")
    db.add(run)
    db.commit()
    ep = Episode(run_id=run.id, newsletter_text="Today's top stories: AI advances.")
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_settings(elevenlabs_api_key="test-key", openai_api_key="", openai_tts_api_key=""):
    s = MagicMock()
    s.elevenlabs_api_key = elevenlabs_api_key
    s.openai_api_key = openai_api_key
    s.openai_tts_api_key = openai_tts_api_key
    return s


def _db_config(overrides: dict):
    """Return a get_db_config-compatible function with given key overrides."""
    defaults = {
        "tts.enabled": "true",
        "tts.provider": "elevenlabs",
        "tts.voice_id": "voice123",
        "tts.model_id": "eleven_monolingual_v1",
        "tts.instructions": "",
        "abs.library_id": "",
        "abs.folder_id": "",
    }

    def _get(db, key, default=""):
        return {**defaults, **overrides}.get(key, default)

    return _get


# ── run() guard tests ─────────────────────────────────────────────────────────


def test_run_skips_when_tts_disabled(db, episode):
    with (
        patch(
            "app.pipeline.publish.get_db_config",
            side_effect=_db_config({"tts.enabled": "false"}),
        ),
        patch("app.pipeline.publish.get_settings", return_value=_mock_settings()),
    ):
        publish.run(db, episode)

    assert episode.audio_path is None


def test_run_skips_when_no_elevenlabs_api_key(db, episode):
    with (
        patch("app.pipeline.publish.get_db_config", side_effect=_db_config({})),
        patch(
            "app.pipeline.publish.get_settings",
            return_value=_mock_settings(elevenlabs_api_key=""),
        ),
    ):
        publish.run(db, episode)

    assert episode.audio_path is None


def test_run_skips_when_no_openai_api_key(db, episode):
    with (
        patch(
            "app.pipeline.publish.get_db_config",
            side_effect=_db_config({"tts.provider": "openai"}),
        ),
        patch(
            "app.pipeline.publish.get_settings",
            return_value=_mock_settings(openai_api_key="", openai_tts_api_key=""),
        ),
    ):
        publish.run(db, episode)

    assert episode.audio_path is None


def test_run_openai_tts_key_takes_precedence(db, episode, tmp_path):
    """OPENAI_TTS_API_KEY is used when set, even if OPENAI_API_KEY differs."""
    expected_path = tmp_path / f"episode_{episode.id}.mp3"
    mock_provider = MagicMock()
    mock_provider.generate.return_value = expected_path

    with (
        patch(
            "app.pipeline.publish.get_db_config",
            side_effect=_db_config({"tts.provider": "openai"}),
        ),
        patch(
            "app.pipeline.publish.get_settings",
            return_value=_mock_settings(openai_api_key="general-key", openai_tts_api_key="tts-key"),
        ),
        patch("app.pipeline.publish.get_tts_provider", return_value=mock_provider),
    ):
        publish.run(db, episode)

    assert episode.audio_path == str(expected_path)


def test_run_openai_falls_back_to_openai_api_key(db, episode, tmp_path):
    """Falls back to OPENAI_API_KEY when OPENAI_TTS_API_KEY is not set."""
    expected_path = tmp_path / f"episode_{episode.id}.mp3"
    mock_provider = MagicMock()
    mock_provider.generate.return_value = expected_path

    with (
        patch(
            "app.pipeline.publish.get_db_config",
            side_effect=_db_config({"tts.provider": "openai"}),
        ),
        patch(
            "app.pipeline.publish.get_settings",
            return_value=_mock_settings(openai_api_key="general-key", openai_tts_api_key=""),
        ),
        patch("app.pipeline.publish.get_tts_provider", return_value=mock_provider),
    ):
        publish.run(db, episode)

    assert episode.audio_path == str(expected_path)


def test_run_skips_when_no_voice_id(db, episode):
    with (
        patch("app.pipeline.publish.get_db_config", side_effect=_db_config({"tts.voice_id": ""})),
        patch("app.pipeline.publish.get_settings", return_value=_mock_settings()),
    ):
        publish.run(db, episode)

    assert episode.audio_path is None


def test_run_skips_when_no_newsletter_text(db, episode):
    episode.newsletter_text = None
    db.commit()

    with (
        patch("app.pipeline.publish.get_db_config", side_effect=_db_config({})),
        patch("app.pipeline.publish.get_settings", return_value=_mock_settings()),
    ):
        publish.run(db, episode)

    assert episode.audio_path is None


def test_run_sets_audio_path(db, episode, tmp_path):
    expected_path = tmp_path / f"episode_{episode.id}.mp3"
    mock_provider = MagicMock()
    mock_provider.generate.return_value = expected_path

    with (
        patch("app.pipeline.publish.get_db_config", side_effect=_db_config({})),
        patch("app.pipeline.publish.get_settings", return_value=_mock_settings()),
        patch("app.pipeline.publish.get_tts_provider", return_value=mock_provider),
    ):
        publish.run(db, episode)

    assert episode.audio_path == str(expected_path)
    mock_provider.generate.assert_called_once_with(
        "voice123",
        "eleven_monolingual_v1",
        episode.newsletter_text,
        episode.id,
        publish.AUDIO_DIR,
        instructions="",
    )


# ── _maybe_upload_to_abs() tests ──────────────────────────────────────────────
