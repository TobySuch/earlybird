"""OAuth2 authentication routes for Gmail.

GET /auth/gmail          — initiates the OAuth2 flow (redirects to Google)
GET /auth/gmail/callback — handles the redirect back from Google, saves token
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.gmail_auth import exchange_code, get_auth_url

router = APIRouter(tags=["auth"])

_STATE_SESSION_KEY = "gmail_oauth_state"
_VERIFIER_SESSION_KEY = "gmail_oauth_verifier"


def _callback_uri(request: Request) -> str:
    """Build the absolute callback URL from the incoming request."""
    return str(request.url_for("gmail_callback"))


@router.get("/gmail", name="gmail_auth")
async def gmail_auth(request: Request):
    """Redirect the user to Google's OAuth2 consent screen."""
    auth_url, state, code_verifier = get_auth_url(redirect_uri=_callback_uri(request))
    request.session[_STATE_SESSION_KEY] = state
    request.session[_VERIFIER_SESSION_KEY] = code_verifier
    return RedirectResponse(auth_url)


@router.get("/gmail/callback", name="gmail_callback")
async def gmail_callback(request: Request, code: str, state: str):
    """Handle the OAuth2 callback, exchange code for token, then redirect home."""
    expected_state = request.session.pop(_STATE_SESSION_KEY, None)
    code_verifier = request.session.pop(_VERIFIER_SESSION_KEY, None)
    if expected_state is None or state != expected_state or code_verifier is None:
        return RedirectResponse("/?error=oauth_state_mismatch")

    exchange_code(
        code=code, state=state, redirect_uri=_callback_uri(request), code_verifier=code_verifier
    )
    return RedirectResponse("/?gmail_auth=success")
