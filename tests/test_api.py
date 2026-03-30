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
