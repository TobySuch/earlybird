"""Tests for UI routes."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_user
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
