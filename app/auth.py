"""Authentication utilities: password hashing, pairing code management, and FastAPI dependencies."""

import hashlib
import hmac
import os
import random

from fastapi import HTTPException, Request

# ---------------------------------------------------------------------------
# Pairing code state
# ---------------------------------------------------------------------------

# Unambiguous alphabet: no 0/O/1/I
_PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_pairing_code: str | None = None


def generate_pairing_code() -> str:
    """Generate and store an 8-character pairing code. Returns the code."""
    global _pairing_code
    _pairing_code = "".join(random.choices(_PAIRING_ALPHABET, k=8))
    return _pairing_code


def get_pairing_code() -> str | None:
    """Return the current pairing code, or None if not set."""
    return _pairing_code


def verify_pairing_code(candidate: str) -> bool:
    """Return True if candidate matches the current pairing code (case-insensitive)."""
    if _pairing_code is None:
        return False
    return hmac.compare_digest(_pairing_code.upper(), candidate.upper())


def consume_pairing_code() -> None:
    """Clear the pairing code after successful first-time setup."""
    global _pairing_code
    _pairing_code = None


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_ITERATIONS = 260_000
_HASH_ALGO = "sha256"
_SALT_BYTES = 32


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256. Returns 'hexsalt:hexhash'."""
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(_HASH_ALGO, password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Return True if password matches the stored hash. Constant-time comparison."""
    try:
        salt_hex, hash_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        candidate = hashlib.pbkdf2_hmac(_HASH_ALGO, password.encode(), salt, _ITERATIONS)
        return hmac.compare_digest(candidate, bytes.fromhex(hash_hex))
    except (ValueError, Exception):
        return False


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
