"""Gmail OAuth2 authentication helpers.

Client ID and secret come from environment variables (GMAIL_CLIENT_ID,
GMAIL_CLIENT_SECRET). The OAuth token is persisted to data/token.json so it
survives restarts and Docker container recreations.
"""

import base64
import hashlib
import secrets
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import get_settings

TOKEN_PATH = Path("data/token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _client_config() -> dict:
    """Build the client config dict that google-auth-oauthlib expects."""
    settings = get_settings()
    return {
        "web": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def get_credentials() -> Credentials | None:
    """Load the stored token, refreshing it if expired.

    Returns None if no token file exists (i.e. the OAuth flow hasn't been
    completed yet).
    """
    if not TOKEN_PATH.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)

    return creds


def _save_credentials(creds: Credentials) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())


def build_gmail_service():
    """Return an authenticated Gmail API resource.

    Raises RuntimeError if the OAuth flow hasn't been completed yet.
    """
    creds = get_credentials()
    if creds is None or not creds.valid:
        raise RuntimeError(
            "Gmail is not authenticated. Visit /auth/gmail to complete the OAuth flow."
        )
    return build("gmail", "v1", credentials=creds)


def _pkce_pair() -> tuple[str, str]:
    """Return a (code_verifier, code_challenge) PKCE pair (S256 method)."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def get_auth_url(redirect_uri: str) -> tuple[str, str, str]:
    """Build the Google OAuth2 authorisation URL with PKCE.

    Returns (auth_url, state, code_verifier). Both state and code_verifier
    must be stored in the session so the callback can validate and use them.
    """
    code_verifier, code_challenge = _pkce_pair()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # always return a refresh_token
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return auth_url, state, code_verifier


def exchange_code(code: str, state: str, redirect_uri: str, code_verifier: str) -> None:
    """Exchange an authorisation code for a token and persist it to TOKEN_PATH."""
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code, code_verifier=code_verifier)
    _save_credentials(flow.credentials)
