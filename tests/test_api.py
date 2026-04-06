"""Tests for API routes: /api/run/trigger and /api/run/status."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_user_api
from app.database import Base, get_db
from app.main import app
from app.models import Run


@pytest.fixture
def db_session():
    # StaticPool keeps a single connection so the in-memory DB persists across requests.
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
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[require_user_api] = lambda: None  # bypass auth
    # Suppress scheduler start/stop so tests don't spin up APScheduler
    with patch("app.main.start_scheduler"), patch("app.main.stop_scheduler"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# ── /api/run/trigger ──────────────────────────────────────────────────────────


def test_trigger_creates_run_record(client, db_session):
    with patch("app.scheduler.execute_pipeline"):
        response = client.post("/api/run/trigger")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "run_id" in data

    run = db_session.get(Run, data["run_id"])
    assert run is not None
    assert run.status == "running"


def test_trigger_queues_background_task(client, db_session):
    with patch("app.scheduler.execute_pipeline") as mock_exec:
        response = client.post("/api/run/trigger")
        # TestClient runs background tasks synchronously before returning
        mock_exec.assert_called_once_with(response.json()["run_id"])


# ── /api/run/status ───────────────────────────────────────────────────────────


def test_status_idle_when_no_runs(client):
    response = client.get("/api/run/status")
    assert response.status_code == 200
    assert response.json()["status"] == "idle"


def test_status_returns_latest_run(client, db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = Run(started_at=now, status="success", newsletters_found=5)
    db_session.add(run)
    db_session.commit()

    response = client.get("/api/run/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["newsletters_found"] == 5
    assert data["run_id"] == run.id


# ── execute_pipeline ──────────────────────────────────────────────────────────


def test_execute_pipeline_sets_success(db_session):
    from app.scheduler import execute_pipeline

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = Run(started_at=now, status="running")
    db_session.add(run)
    db_session.commit()
    run_id = run.id

    with (
        patch("app.pipeline.ingest.run"),
        patch("app.pipeline.process.run"),
        patch("app.scheduler.SessionLocal", return_value=db_session),
    ):
        execute_pipeline(run_id)

    # Session was closed by execute_pipeline; re-fetch the run by ID
    refreshed = db_session.get(Run, run_id)
    assert refreshed.status == "success"
    assert refreshed.finished_at is not None


# ── /api/unprocessed-count ────────────────────────────────────────────────────


def test_unprocessed_count_returns_count(client):
    with patch("app.pipeline.sources.gmail.GmailSource") as MockSource:
        MockSource.return_value.count_unprocessed.return_value = 7
        response = client.get("/api/unprocessed-count")
    assert response.status_code == 200
    assert response.json() == {"count": 7}


def test_unprocessed_count_handles_error(client):
    with patch("app.pipeline.sources.gmail.GmailSource") as MockSource:
        MockSource.return_value.count_unprocessed.side_effect = RuntimeError(
            "Gmail not authenticated."
        )
        response = client.get("/api/unprocessed-count")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] is None
    assert "Gmail not authenticated" in data["error"]


# ── /api/feed/{token}/feed.xml ────────────────────────────────────────────────


def _set_feed_config(db_session, enabled: bool, token: str = "secret-token-abc"):
    from app.config import FEED_ENABLED_KEY, FEED_TOKEN_KEY, set_db_config

    set_db_config(db_session, FEED_ENABLED_KEY, "true" if enabled else "false")
    set_db_config(db_session, FEED_TOKEN_KEY, token)


def test_feed_disabled_returns_503(client, db_session):
    _set_feed_config(db_session, enabled=False)
    response = client.get("/api/feed/secret-token-abc/feed.xml")
    assert response.status_code == 503


def test_feed_wrong_token_returns_404(client, db_session):
    _set_feed_config(db_session, enabled=True, token="correct-token")
    response = client.get("/api/feed/wrong-token/feed.xml")
    assert response.status_code == 404


def test_feed_no_audio_episodes_returns_empty_feed(client, db_session):
    _set_feed_config(db_session, enabled=True)
    response = client.get("/api/feed/secret-token-abc/feed.xml")
    assert response.status_code == 200
    assert "application/rss+xml" in response.headers["content-type"]
    assert b"<channel>" in response.content
    assert b"<item>" not in response.content


def test_feed_returns_rss_with_episodes(client, db_session, tmp_path):
    from app.models import Episode

    audio_file = tmp_path / "ep1.mp3"
    audio_file.write_bytes(b"\x00" * 1024)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = Run(started_at=now, status="success")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    episode = Episode(run_id=run.id, audio_path=str(audio_file), newsletter_text="Today's digest.")
    db_session.add(episode)
    db_session.commit()

    _set_feed_config(db_session, enabled=True)
    response = client.get("/api/feed/secret-token-abc/feed.xml")
    assert response.status_code == 200
    body = response.content.decode()
    assert "<enclosure" in body
    assert "audio/mpeg" in body
    assert "Earlybird" in body


def test_feed_audio_streams_file(client, db_session, tmp_path):
    from app.models import Episode

    audio_file = tmp_path / "ep.mp3"
    audio_file.write_bytes(b"ID3" + b"\x00" * 100)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = Run(started_at=now, status="success")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    episode = Episode(run_id=run.id, audio_path=str(audio_file))
    db_session.add(episode)
    db_session.commit()
    db_session.refresh(episode)

    _set_feed_config(db_session, enabled=True)
    response = client.get(f"/api/feed/secret-token-abc/audio/{episode.id}.mp3")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"


# ── execute_pipeline ──────────────────────────────────────────────────────────


def test_execute_pipeline_sets_error_on_exception(db_session):
    from app.scheduler import execute_pipeline

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = Run(started_at=now, status="running")
    db_session.add(run)
    db_session.commit()
    run_id = run.id

    with (
        patch("app.pipeline.ingest.run", side_effect=RuntimeError("boom")),
        patch("app.scheduler.SessionLocal", return_value=db_session),
    ):
        with pytest.raises(RuntimeError):
            execute_pipeline(run_id)

    refreshed = db_session.get(Run, run_id)
    assert refreshed.status == "error"
    assert refreshed.finished_at is not None
