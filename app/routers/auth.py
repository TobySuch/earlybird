"""Authentication routes.

User auth:
GET  /auth/login    — login form
POST /auth/login    — validate credentials and set session
GET  /auth/signup   — signup form (only when no users exist)
POST /auth/signup   — create first user (requires signup code)
POST /auth/logout   — clear session

Gmail OAuth2:
GET /auth/gmail          — initiates the OAuth2 flow (redirects to Google)
GET /auth/gmail/callback — handles the redirect back from Google, saves token
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import auth as auth_utils
from app.database import get_db
from app.gmail_auth import exchange_code, get_auth_url
from app.models import User

router = APIRouter(tags=["auth"])

templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# User auth routes
# ---------------------------------------------------------------------------


@router.get("/login", name="login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Show login form. Redirect to signup if no users exist."""
    if db.query(User).count() == 0:
        return RedirectResponse(url="/auth/signup", status_code=302)
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "auth/login.html", {})


@router.post("/login", name="login_submit")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Validate credentials and set session."""
    if db.query(User).count() == 0:
        return RedirectResponse(url="/auth/signup", status_code=302)

    user = db.query(User).filter(User.username == username).first()
    if user and auth_utils.verify_password(password, user.password_hash):
        request.session["user_id"] = user.id
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"error": "Invalid username or password"},
        status_code=400,
    )


@router.get("/signup", name="signup", response_class=HTMLResponse)
async def signup_page(request: Request, db: Session = Depends(get_db)):
    """Show signup form. Only accessible when no users exist."""
    if db.query(User).count() > 0:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse(request, "auth/signup.html", {})


@router.post("/signup", name="signup_submit")
async def signup_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    signup_code: str = Form(...),
    db: Session = Depends(get_db),
):
    """Create the first user account."""
    if db.query(User).count() > 0:
        return RedirectResponse(url="/auth/login", status_code=302)

    def render_error(msg: str):
        return templates.TemplateResponse(
            request, "auth/signup.html", {"error": msg}, status_code=400
        )

    if not auth_utils.verify_pairing_code(signup_code):
        return render_error("Invalid setup code.")
    if password != confirm_password:
        return render_error("Passwords do not match.")
    if len(password) < 8:
        return render_error("Password must be at least 8 characters.")

    user = User(username=username, password_hash=auth_utils.hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    auth_utils.consume_pairing_code()
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=302)


@router.post("/logout", name="logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/change-password", name="change_password_page", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    saved: bool = False,
    error: str = "",
    _: None = Depends(auth_utils.require_user),
):
    """Show the change password form."""
    return templates.TemplateResponse(
        request, "auth/change_password.html", {"saved": saved, "error": error}
    )


@router.post("/change-password", name="change_password_submit")
async def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(auth_utils.require_user),
):
    """Validate and update the user's password."""
    user_id = request.session.get("user_id")
    user = db.get(User, user_id)

    if not auth_utils.verify_password(current_password, user.password_hash):
        return RedirectResponse(
            "/auth/change-password?error=Incorrect+current+password", status_code=303
        )
    if new_password != confirm_password:
        return RedirectResponse(
            "/auth/change-password?error=Passwords+do+not+match", status_code=303
        )
    if len(new_password) < 8:
        return RedirectResponse(
            "/auth/change-password?error=Password+must+be+at+least+8+characters",
            status_code=303,
        )

    user.password_hash = auth_utils.hash_password(new_password)
    db.commit()
    return RedirectResponse("/auth/change-password?saved=1", status_code=303)


_STATE_SESSION_KEY = "gmail_oauth_state"
_VERIFIER_SESSION_KEY = "gmail_oauth_verifier"


def _callback_uri(request: Request) -> str:
    """Build the absolute callback URL from the incoming request.

    If PUBLIC_BASE_URL is set in settings, use it to override the scheme/host
    so the URI is correct when running behind a reverse proxy.
    """
    from app.config import get_settings

    path = request.url_for("gmail_callback")
    base = get_settings().public_base_url.rstrip("/")
    if base:
        return f"{base}/auth/gmail/callback"
    return str(path)


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
