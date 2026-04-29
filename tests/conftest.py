"""Shared test fixtures and autouse patches."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_init_db():
    """Prevent init_db() and the lifespan SessionLocal() call from hitting the
    real DB during tests.

    Each test that needs a DB creates its own in-memory SQLite engine and
    overrides get_db via app.dependency_overrides. The real init_db call and
    the direct SessionLocal() usage in the lifespan (first-run pairing code
    check) are irrelevant and would fail on CI where no DB file exists yet.
    """
    with patch("app.main.init_db"), patch("app.main.SessionLocal"):
        yield
    # Reset tracing global so a test that triggered setup_tracing (via the
    # TestClient lifespan when MLFLOW_TRACKING_URI is set in .env) doesn't
    # leave _tracing_enabled=True for subsequent tests.
    import app.tracing as _tracing

    _tracing._tracing_enabled = False
