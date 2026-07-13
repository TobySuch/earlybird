"""Tests for UI routes."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_user
from app.config import get_db_config
from app.database import Base, get_db
from app.main import app
from app.models import Episode, Run


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: None  # bypass auth
    with patch("app.main.start_scheduler"), patch("app.main.stop_scheduler"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def episode(db_session):
    run = Run(started_at=datetime.now(timezone.utc).replace(tzinfo=None), status="success")
    db_session.add(run)
    db_session.commit()
    ep = Episode(run_id=run.id, newsletter_text="Test digest.")
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    return ep


# ── GET /episodes/{id}/audio ──────────────────────────────────────────────────


def test_audio_404_when_episode_missing(client):
    response = client.get("/episodes/9999/audio")
    assert response.status_code == 404


def test_audio_404_when_no_audio_path(client, episode):
    response = client.get(f"/episodes/{episode.id}/audio")
    assert response.status_code == 404


def test_audio_404_when_file_missing_from_disk(client, db_session, episode):
    episode.audio_path = "/nonexistent/path/episode_1.mp3"
    db_session.commit()

    response = client.get(f"/episodes/{episode.id}/audio")
    assert response.status_code == 404


def test_audio_serves_file(client, db_session, episode, tmp_path):
    audio_file = tmp_path / "episode_1.mp3"
    audio_file.write_bytes(b"FAKEMP3")
    episode.audio_path = str(audio_file)
    db_session.commit()

    response = client.get(f"/episodes/{episode.id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"FAKEMP3"


# ── DELETE /episodes/{id} ─────────────────────────────────────────────────────


def test_delete_episode_no_audio(client, db_session, episode):
    episode_id = episode.id
    response = client.delete(f"/episodes/{episode_id}")
    assert response.status_code == 204
    assert db_session.get(Episode, episode_id) is None


def test_delete_episode_with_audio(client, db_session, episode, tmp_path):
    audio_file = tmp_path / "episode_1.mp3"
    audio_file.write_bytes(b"FAKEMP3")
    episode.audio_path = str(audio_file)
    db_session.commit()

    episode_id = episode.id
    response = client.delete(f"/episodes/{episode_id}")
    assert response.status_code == 204
    assert not audio_file.exists()
    assert db_session.get(Episode, episode_id) is None


def test_delete_episode_missing_audio_file(client, db_session, episode):
    episode.audio_path = "/nonexistent/path/episode_99.mp3"
    db_session.commit()

    episode_id = episode.id
    response = client.delete(f"/episodes/{episode_id}")
    assert response.status_code == 204
    assert db_session.get(Episode, episode_id) is None


def test_delete_episode_404(client):
    response = client.delete("/episodes/9999")
    assert response.status_code == 404


# ── /settings (agent mode) ────────────────────────────────────────────────────


_SETTINGS_FORM_BASE = {
    "llm_provider": "anthropic",
    "llm_model": "claude-haiku-4-5-20251001",
    "schedule_cron": "0 7 * * 1-5",
}


def test_settings_page_shows_work_mode_options(client):
    with patch("app.gmail_auth.get_credentials", return_value=None):
        response = client.get("/settings")
    assert response.status_code == 200
    assert 'name="llm_work_mode"' in response.text
    assert "Agent mode (reporters + editor)" in response.text
    assert 'name="llm_reporter_model"' in response.text


def test_settings_post_persists_agent_config(client, db_session):
    form = {
        **_SETTINGS_FORM_BASE,
        "llm_work_mode": "agent",
        "llm_reporter_provider": "openai",
        "llm_reporter_model": "gpt-4o-mini",
        "llm_reporter_base_url": "http://localhost:11434/v1",
        "llm_agent_max_parallel": "8",
    }
    with patch("app.routers.ui._reschedule"):
        response = client.post("/settings", data=form, follow_redirects=False)

    assert response.status_code == 303
    assert get_db_config(db_session, "llm.work_mode") == "agent"
    assert get_db_config(db_session, "llm.reporter.provider") == "openai"
    assert get_db_config(db_session, "llm.reporter.model") == "gpt-4o-mini"
    assert get_db_config(db_session, "llm.reporter.openai_base_url") == "http://localhost:11434/v1"
    assert get_db_config(db_session, "llm.agent.max_parallel_reporters") == "8"


def test_settings_post_invalid_work_mode_falls_back_to_digest(client, db_session):
    form = {**_SETTINGS_FORM_BASE, "llm_work_mode": "bogus"}
    with patch("app.routers.ui._reschedule"):
        response = client.post("/settings", data=form, follow_redirects=False)

    assert response.status_code == 303
    assert get_db_config(db_session, "llm.work_mode") == "digest"
