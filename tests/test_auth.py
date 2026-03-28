"""Tests for authentication: utilities, routes, and route protection."""

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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_signup_code():
    """Ensure the module-level signup code is reset between tests."""
    yield
    auth_utils._pairing_code = None


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
    """Create a pre-existing user in the DB."""
    user = User(username="alice", password_hash=auth_utils.hash_password("password123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authenticated_client(client, existing_user):
    """A client with a valid session (logged in as existing_user)."""
    resp = client.post("/auth/login", data={"username": "alice", "password": "password123"})
    assert resp.status_code == 302
    return client


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_hash_password_produces_verifiable_hash():
    hashed = auth_utils.hash_password("secret")
    assert auth_utils.verify_password("secret", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = auth_utils.hash_password("secret")
    assert not auth_utils.verify_password("wrong", hashed)


def test_verify_password_handles_malformed_stored_hash():
    assert not auth_utils.verify_password("secret", "not:valid")
    assert not auth_utils.verify_password("secret", "")


def test_hash_password_different_hashes_for_same_input():
    # Each call uses a new random salt
    h1 = auth_utils.hash_password("same")
    h2 = auth_utils.hash_password("same")
    assert h1 != h2


# ---------------------------------------------------------------------------
# Signup code
# ---------------------------------------------------------------------------


def test_generate_signup_code_sets_module_var():
    code = auth_utils.generate_pairing_code()
    assert auth_utils.get_pairing_code() == code
    assert len(code) > 0


def test_consume_signup_code_clears_module_var():
    auth_utils.generate_pairing_code()
    auth_utils.consume_pairing_code()
    assert auth_utils.get_pairing_code() is None


# ---------------------------------------------------------------------------
# GET /auth/signup
# ---------------------------------------------------------------------------


def test_signup_page_shown_when_no_users(client):
    resp = client.get("/auth/signup")
    assert resp.status_code == 200
    assert b"Create your account" in resp.content


def test_signup_page_redirects_to_login_when_user_exists(client, existing_user):
    resp = client.get("/auth/signup")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------


def test_signup_creates_user_and_sets_session(client, db_session):
    code = auth_utils.generate_pairing_code()
    resp = client.post(
        "/auth/signup",
        data={
            "username": "bob",
            "password": "password123",
            "confirm_password": "password123",
            "signup_code": code,
        },
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"

    user = db_session.query(User).filter_by(username="bob").first()
    assert user is not None
    assert auth_utils.verify_password("password123", user.password_hash)


def test_signup_code_consumed_after_success(client):
    code = auth_utils.generate_pairing_code()
    client.post(
        "/auth/signup",
        data={
            "username": "bob",
            "password": "password123",
            "confirm_password": "password123",
            "signup_code": code,
        },
    )
    assert auth_utils.get_pairing_code() is None


def test_signup_rejects_wrong_code(client):
    auth_utils.generate_pairing_code()
    resp = client.post(
        "/auth/signup",
        data={
            "username": "bob",
            "password": "password123",
            "confirm_password": "password123",
            "signup_code": "wrongcode",
        },
    )
    assert resp.status_code == 400
    assert b"Invalid setup code" in resp.content


def test_signup_rejects_mismatched_passwords(client):
    code = auth_utils.generate_pairing_code()
    resp = client.post(
        "/auth/signup",
        data={
            "username": "bob",
            "password": "password123",
            "confirm_password": "different",
            "signup_code": code,
        },
    )
    assert resp.status_code == 400
    assert b"do not match" in resp.content


def test_signup_rejects_short_password(client):
    code = auth_utils.generate_pairing_code()
    resp = client.post(
        "/auth/signup",
        data={
            "username": "bob",
            "password": "short",
            "confirm_password": "short",
            "signup_code": code,
        },
    )
    assert resp.status_code == 400
    assert b"8 characters" in resp.content


def test_signup_redirects_to_login_when_user_already_exists(client, existing_user):
    resp = client.post(
        "/auth/signup",
        data={
            "username": "bob",
            "password": "password123",
            "confirm_password": "password123",
            "signup_code": "any",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# GET /auth/login
# ---------------------------------------------------------------------------


def test_login_page_shown_when_user_exists(client, existing_user):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"Log in" in resp.content


def test_login_page_redirects_to_signup_when_no_users(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/signup"


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


def test_login_success_redirects_to_dashboard(client, existing_user):
    resp = client.post("/auth/login", data={"username": "alice", "password": "password123"})
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


def test_login_wrong_password_returns_error(client, existing_user):
    resp = client.post("/auth/login", data={"username": "alice", "password": "wrong"})
    assert resp.status_code == 400
    assert b"Invalid username or password" in resp.content


def test_login_unknown_username_returns_generic_error(client, existing_user):
    resp = client.post("/auth/login", data={"username": "nobody", "password": "password123"})
    assert resp.status_code == 400
    assert b"Invalid username or password" in resp.content


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


def test_logout_redirects_to_login(authenticated_client):
    resp = authenticated_client.post("/auth/logout")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


def test_logout_clears_session(authenticated_client):
    authenticated_client.post("/auth/logout")
    # After logout, dashboard should redirect to login
    resp = authenticated_client.get("/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


# ---------------------------------------------------------------------------
# Route protection
# ---------------------------------------------------------------------------


def test_unauthenticated_ui_route_redirects_to_login(client, existing_user):
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


def test_authenticated_ui_route_is_accessible(authenticated_client):
    resp = authenticated_client.get("/")
    assert resp.status_code == 200


def test_unauthenticated_api_trigger_returns_401(client, existing_user):
    resp = client.post("/api/run/trigger")
    assert resp.status_code == 401


def test_unauthenticated_api_status_returns_401(client, existing_user):
    resp = client.get("/api/run/status")
    assert resp.status_code == 401


def test_feed_route_is_public(client):
    # Feed route is intentionally unauthenticated (token-based)
    resp = client.get("/api/feed/sometoken/feed.xml")
    # It returns a JSON error (not implemented), but not a 401 or 302
    assert resp.status_code not in (401, 302)
