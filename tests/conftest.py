"""Shared test fixtures and autouse patches."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_init_db():
    """Prevent init_db() from running alembic against the real DB during tests.

    Each test that needs a DB creates its own in-memory SQLite engine and
    overrides get_db via app.dependency_overrides. The real init_db call in
    the FastAPI lifespan is irrelevant and would fail on CI where no DB file
    exists yet.
    """
    with patch("app.main.init_db"):
        yield
