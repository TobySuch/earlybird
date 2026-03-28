"""Authentication utilities: password hashing, signup code, and FastAPI dependencies."""

import base64
import hashlib
import os
import secrets

from fastapi import HTTPException, Request

_ITERATIONS = 600_000
_signup_code: str | None = None


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256. Returns a self-describing string."""
    salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    b64_salt = base64.b64encode(salt).decode()
    b64_hash = base64.b64encode(dk).decode()
    return f"sha256:{_ITERATIONS}:{b64_salt}:{b64_hash}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash. Constant-time comparison."""
    try:
        alg, iters, b64_salt, b64_hash = stored.split(":")
        salt = base64.b64decode(b64_salt)
        expected = base64.b64decode(b64_hash)
        dk = hashlib.pbkdf2_hmac(alg, password.encode(), salt, int(iters))
        return secrets.compare_digest(dk, expected)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Signup code (in-memory, consumed after first use)
# ---------------------------------------------------------------------------


def generate_signup_code() -> str:
    """Generate and store a one-time signup code. Returns the code."""
    global _signup_code
    _signup_code = secrets.token_urlsafe(16)
    return _signup_code


def get_signup_code() -> str | None:
    return _signup_code


def consume_signup_code() -> None:
    global _signup_code
    _signup_code = None


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------


class NotAuthenticatedError(Exception):
    """Raised by require_user when no valid session is present."""


def require_user(request: Request) -> None:
    """FastAPI dependency for HTML routes — raises NotAuthenticatedError if not logged in."""
    if not request.session.get("user_id"):
        raise NotAuthenticatedError()


def require_user_api(request: Request) -> None:
    """FastAPI dependency for API routes — returns 401 if not logged in."""
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Not authenticated")
