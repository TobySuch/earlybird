"""Tests for the change-password page and route."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.auth as auth_utils
from app.database import Base, get_db
from app.main import app
from app.models import User

# ---------------------------------------------------------------------------
# Fixtures (mirrors test_auth.py)
# ---------------------------------------------------------------------------


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
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    with patch("app.main.start_scheduler"), patch("app.main.stop_scheduler"):
        with TestClient(app, follow_redirects=False) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def existing_user(db_session):
    user = User(username="alice", password_hash=auth_utils.hash_password("password123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authenticated_client(client, existing_user):
    resp = client.post("/auth/login", data={"username": "alice", "password": "password123"})
    assert resp.status_code == 302
    return client


# ---------------------------------------------------------------------------
# GET /auth/change-password
# ---------------------------------------------------------------------------


def test_change_password_page_requires_auth(client, existing_user):
    resp = client.get("/auth/change-password")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


def test_change_password_page_accessible_when_authenticated(authenticated_client):
    resp = authenticated_client.get("/auth/change-password")
    assert resp.status_code == 200
    assert b"Change password" in resp.content


def test_change_password_page_shows_success_banner(authenticated_client):
    resp = authenticated_client.get("/auth/change-password?saved=1")
    assert resp.status_code == 200
    assert b"Password changed successfully" in resp.content


def test_change_password_page_shows_error_banner(authenticated_client):
    resp = authenticated_client.get("/auth/change-password?error=Incorrect+current+password")
    assert resp.status_code == 200
    assert b"Incorrect current password" in resp.content


# ---------------------------------------------------------------------------
# POST /auth/change-password
# ---------------------------------------------------------------------------


def test_change_password_success(authenticated_client, db_session, existing_user):
    resp = authenticated_client.post(
        "/auth/change-password",
        data={
            "current_password": "password123",
            "new_password": "newpassword99",
            "confirm_password": "newpassword99",
        },
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/auth/change-password?saved=1"

    db_session.refresh(existing_user)
    assert auth_utils.verify_password("newpassword99", existing_user.password_hash)
    assert not auth_utils.verify_password("password123", existing_user.password_hash)


def test_change_password_wrong_current_password(authenticated_client, db_session, existing_user):
    resp = authenticated_client.post(
        "/auth/change-password",
        data={
            "current_password": "wrongpassword",
            "new_password": "newpassword99",
            "confirm_password": "newpassword99",
        },
    )
    assert resp.status_code == 303
    assert "error=Incorrect" in resp.headers["location"]

    db_session.refresh(existing_user)
    assert auth_utils.verify_password("password123", existing_user.password_hash)


def test_change_password_mismatched_new_passwords(authenticated_client, db_session, existing_user):
    resp = authenticated_client.post(
        "/auth/change-password",
        data={
            "current_password": "password123",
            "new_password": "newpassword99",
            "confirm_password": "different99",
        },
    )
    assert resp.status_code == 303
    assert "error=Passwords" in resp.headers["location"]

    db_session.refresh(existing_user)
    assert auth_utils.verify_password("password123", existing_user.password_hash)


def test_change_password_too_short(authenticated_client, db_session, existing_user):
    resp = authenticated_client.post(
        "/auth/change-password",
        data={
            "current_password": "password123",
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert resp.status_code == 303
    assert "error=Password" in resp.headers["location"]

    db_session.refresh(existing_user)
    assert auth_utils.verify_password("password123", existing_user.password_hash)


def test_change_password_requires_auth(client, existing_user):
    resp = client.post(
        "/auth/change-password",
        data={
            "current_password": "password123",
            "new_password": "newpassword99",
            "confirm_password": "newpassword99",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"
