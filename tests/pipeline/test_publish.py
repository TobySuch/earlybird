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


def _mock_settings(api_key="test-key"):
    s = MagicMock()
    s.elevenlabs_api_key = api_key
    return s


def _db_config(overrides: dict):
    """Return a get_db_config-compatible function with given key overrides."""
    defaults = {
        "tts.enabled": "true",
        "tts.voice_id": "voice123",
        "tts.model_id": "eleven_monolingual_v1",
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


def test_run_skips_when_no_api_key(db, episode):
    with (
        patch("app.pipeline.publish.get_db_config", side_effect=_db_config({})),
        patch("app.pipeline.publish.get_settings", return_value=_mock_settings(api_key="")),
    ):
        publish.run(db, episode)

    assert episode.audio_path is None


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

    with (
        patch("app.pipeline.publish.get_db_config", side_effect=_db_config({})),
        patch("app.pipeline.publish.get_settings", return_value=_mock_settings()),
        patch("app.pipeline.publish._generate_audio", return_value=expected_path) as mock_gen,
    ):
        publish.run(db, episode)

    assert episode.audio_path == str(expected_path)
    mock_gen.assert_called_once_with(
        "test-key", "voice123", "eleven_monolingual_v1", episode.newsletter_text, episode.id
    )


# ── _generate_audio() tests ───────────────────────────────────────────────────


def test_generate_audio_writes_mp3(tmp_path):
    fake_audio = b"FAKEMP3DATA"
    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = iter([fake_audio])

    with patch("app.pipeline.publish.ElevenLabs", return_value=mock_client):
        result = publish._generate_audio(
            api_key="key",
            voice_id="v1",
            model_id="eleven_monolingual_v1",
            text="Hello world",
            episode_id=42,
            audio_dir=tmp_path,
        )

    assert result == tmp_path / "episode_42.mp3"
    assert result.read_bytes() == fake_audio


def test_generate_audio_calls_elevenlabs_with_correct_args(tmp_path):
    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = iter([b"audio"])

    with patch("app.pipeline.publish.ElevenLabs", return_value=mock_client):
        publish._generate_audio(
            api_key="mykey",
            voice_id="myvoice",
            model_id="eleven_turbo_v2",
            text="Test text",
            episode_id=1,
            audio_dir=tmp_path,
        )

    mock_client.text_to_speech.convert.assert_called_once_with(
        voice_id="myvoice",
        text="Test text",
        model_id="eleven_turbo_v2",
        output_format="mp3_44100_128",
    )


# ── _maybe_upload_to_abs() tests ──────────────────────────────────────────────
