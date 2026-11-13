"""
Authentication & RBAC API Routes.

Endpoints:
  GET  /auth/google/login     → redirect to Google consent (or sandbox auto-login)
  GET  /auth/google/callback  → exchange code, set httpOnly cookie, redirect to frontend
  GET  /auth/me               → current user + sandbox_mode flag
  POST /auth/logout           → clear session cookie
  GET  /auth/profiles         → list demo profiles (viva)
  POST /auth/switch-profile   → set cookie for a demo profile (viva)

Legacy viva-compat endpoints kept:
  POST /auth/google           → verify ID token directly
  POST /auth/google/inspect   → diagnostic token audit
  POST /auth/verify-jwt       → decode app JWT
"""

import secrets
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status, Query, Depends
from fastapi.responses import RedirectResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.tenant import get_current_user, get_current_workspace
from backend.database.models import User, Workspace
from backend.services.auth_service import (
    DEMO_PROFILES,
    mint_user_jwt,
    verify_user_jwt,
    get_google_login_url,
    exchange_google_code,
    get_sandbox_demo_user,
    verify_google_credential,
    inspect_google_token,
    set_active_profile,
    logout_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])

# ---------------------------------------------------------------------------
# Cookie helper
# ---------------------------------------------------------------------------

def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,       # set True in production (HTTPS)
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        samesite="lax",
    )


# ---------------------------------------------------------------------------
# Primary OAuth flow
# ---------------------------------------------------------------------------

@router.get("/google/login", summary="Initiate Google OAuth 2.0 Authorization Code Flow")
def google_oauth_login(db: Session = Depends(get_db)):
    """
    Redirects to Google consent screen.
    - DEV_SANDBOX_AUTH=True → auto-login with demo user, set cookie, redirect to frontend.
    - No GOOGLE_CLIENT_ID → 503.
    - Normal → redirect to Google with CSRF state cookie.
    """
    if settings.DEV_SANDBOX_AUTH:
        user, app_jwt = get_sandbox_demo_user(db)
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        response = RedirectResponse(url=f"{frontend_url}/", status_code=302)
        _set_session_cookie(response, app_jwt)
        return response

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in .env (see docs/MANUAL_STEPS.md).",
        )

    state = secrets.token_urlsafe(24)
    auth_url = get_google_login_url(state)
    response = RedirectResponse(url=auth_url, status_code=302)
    # Store state for CSRF check; short-lived, httpOnly
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600,  # 10 minutes
        path="/",
    )
    return response


@router.get("/google/callback", summary="Google OAuth 2.0 Callback Handler")
async def google_oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Receives the authorization code from Google, exchanges it for tokens,
    verifies the id_token, upserts the user, sets the session cookie,
    then redirects to the frontend.
    """
    frontend_url = settings.FRONTEND_URL.rstrip("/")

    if error:
        logger.warning("Google OAuth error: %s", error)
        return RedirectResponse(url=f"{frontend_url}/login?error=google_denied", status_code=302)

    # CSRF check
    stored_state = request.cookies.get("oauth_state")
    if stored_state and state and stored_state != state:
        logger.warning("OAuth state mismatch: stored=%s received=%s", stored_state, state)
        return RedirectResponse(url=f"{frontend_url}/login?error=state_mismatch", status_code=302)

    try:
        user, app_jwt = await exchange_google_code(code, db)
    except ValueError as e:
        logger.error("OAuth code exchange failed: %s", e)
        return RedirectResponse(url=f"{frontend_url}/login?error=auth_failed", status_code=302)
    except Exception as e:
        logger.exception("Unexpected OAuth error: %s", e)
        return RedirectResponse(url=f"{frontend_url}/login?error=server_error", status_code=302)

    response = RedirectResponse(url=f"{frontend_url}/", status_code=302)
    _set_session_cookie(response, app_jwt)
    # Clear state cookie
    response.delete_cookie("oauth_state", path="/")
    return response


# ---------------------------------------------------------------------------
# /me — session introspection
# ---------------------------------------------------------------------------

@router.get("/me", summary="Get Current Authenticated User")
def get_me(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Returns the current session user and sandbox_mode flag.
    If DEV_SANDBOX_AUTH is on, ensures sandbox user exists and returns sandbox_mode=true.
    """
    sandbox_mode = settings.DEV_SANDBOX_AUTH

    # Try reading from cookie/header
    from backend.database.tenant import extract_token_from_request
    token = extract_token_from_request(request)

    if token:
        payload = verify_user_jwt(token)
        if payload and "sub" in payload:
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if user:
                ws = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
                return {
                    "status": "authenticated",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "name": user.full_name,       # alias for compat
                        "full_name": user.full_name,
                        "avatar_url": user.avatar_url,
                        "role": payload.get("role", "Lead Architect"),
                        "permissions": payload.get("permissions", ["prioritize", "export_jira", "sync_notion", "override_weights", "manage_integrations"]),
                    },
                    "sandbox_mode": payload.get("sandbox", sandbox_mode),
                    "active_simulations": {
                        "auth": settings.DEV_SANDBOX_AUTH,
                        "jira": settings.JIRA_SIMULATION_MODE,
                        "notion": settings.NOTION_SIMULATION_MODE,
                    },
                    "workspace_id": ws.id if ws else "ws_demo",
                }

    # No valid token — return sandbox profile if DEV_SANDBOX_AUTH, else unauthenticated
    if sandbox_mode:
        user, app_jwt = get_sandbox_demo_user(db)
        demo = DEMO_PROFILES.get("dhruv", {})
        ws = db.query(Workspace).filter(Workspace.id == "ws_demo").first()
        return JSONResponse(
            content={
                "status": "authenticated",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.full_name,       # alias for compat
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url,
                    "role": demo.get("role", "Lead Architect"),
                    "permissions": demo.get("permissions", ["prioritize", "export_jira", "sync_notion", "override_weights", "manage_integrations"]),
                },
                "sandbox_mode": True,
                "active_simulations": {
                    "auth": settings.DEV_SANDBOX_AUTH,
                    "jira": settings.JIRA_SIMULATION_MODE,
                    "notion": settings.NOTION_SIMULATION_MODE,
                },
                "workspace_id": ws.id if ws else "ws_demo",
            },
            headers={"Set-Cookie": (
                f"{settings.SESSION_COOKIE_NAME}={app_jwt}; "
                f"HttpOnly; SameSite=Lax; Max-Age={settings.SESSION_MAX_AGE_SECONDS}; Path=/"
            )},
        )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"status": "unauthenticated", "sandbox_mode": False},
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.post("/logout", summary="Log Out — Clear Session Cookie")
def logout(response: Response):
    """Clears the session cookie. Stateless — no server-side session to invalidate."""
    _clear_session_cookie(response)
    return {"status": "logged_out"}


# ---------------------------------------------------------------------------
# Demo / viva profile switching
# ---------------------------------------------------------------------------

@router.get("/profiles", summary="List Available Demo Profiles")
def list_demo_profiles():
    """Returns the set of available role-based demo profiles (viva evaluation)."""
    return {"profiles": DEMO_PROFILES}


class SwitchProfileRequest(BaseModel):
    profile_key: str = Field(..., description="Demo profile key: 'dhruv', 'sarah', 'alex', 'developer'")


@router.post("/switch-profile", summary="Switch Demo Identity Profile")
def switch_profile(payload: SwitchProfileRequest, response: Response):
    """
    Switches the active persona for viva demos.
    Sets a session cookie with that profile's JWT.
    """
    try:
        profile = set_active_profile(payload.profile_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    token = mint_user_jwt({
        "id": profile["id"],
        "name": profile["name"],
        "email": profile["email"],
        "avatar": profile.get("avatar"),
        "role": profile["role"],
        "role_code": profile["role_code"],
        "permissions": profile["permissions"],
        "sandbox": True,
    })
    _set_session_cookie(response, token)
    return {
        "status": "success",
        "message": f"Switched to {profile['name']} ({profile['role']})",
        "user": profile,
        "token": token,
    }


# ---------------------------------------------------------------------------
# Legacy viva-compat endpoints
# ---------------------------------------------------------------------------

class GoogleLoginRequest(BaseModel):
    credential: str = Field(..., description="Google OAuth 2.0 ID Token JWT string")


class VerifyJwtRequest(BaseModel):
    token: str = Field(..., description="Application JWT token string")


@router.post("/google", summary="Authenticate via Direct Google ID Token")
def login_with_google_id_token(payload: GoogleLoginRequest, response: Response):
    """Direct ID token verification (legacy/viva endpoint)."""
    if not payload.credential:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credential.")
    user = verify_google_credential(payload.credential)
    token = mint_user_jwt(user)
    _set_session_cookie(response, token)
    return {"status": "success", "user": user, "token": token}


@router.post("/google/inspect", summary="Inspect and Audit Google ID Token Claims")
def inspect_google_token_endpoint(payload: GoogleLoginRequest):
    """Diagnostic: audit OIDC token claims (viva endpoint)."""
    if not payload.credential:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing token.")
    return inspect_google_token(payload.credential)


@router.post("/verify-jwt", summary="Verify and Decode Application JWT")
def verify_jwt_endpoint(payload: VerifyJwtRequest):
    """Verifies and decodes an app JWT."""
    result = verify_user_jwt(payload.token)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return {"status": "valid", "user": result}


@router.post("/google/code", summary="Exchange Google OAuth Code (popup flow)")
async def exchange_google_code_endpoint(
    payload: "GoogleCodeExchangeRequest",
    response: Response,
    db: Session = Depends(get_db),
):
    """Legacy popup-flow code exchange endpoint."""
    if not payload.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code.")
    try:
        user, app_jwt = await exchange_google_code(payload.code, db)
        _set_session_cookie(response, app_jwt)
        return {"status": "success", "user": {"id": user.id, "email": user.email, "full_name": user.full_name}, "token": app_jwt}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


class GoogleCodeExchangeRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Google")
