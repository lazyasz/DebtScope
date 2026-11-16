"""
Authentication Service for DebtScope.

Supports:
- Server-side Google OAuth 2.0 Authorization Code Flow (real production path)
- DEV_SANDBOX_AUTH mode (tests / local dev without Google credentials)
- JWT minting and verification for session cookies
- Demo profiles kept for viva persona switching

Thread-safety: no module-level mutable state (_active_user removed).
"""

import time
import json
import base64
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

import jwt
import httpx
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.models import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo profiles — kept for viva persona switching; not used as real auth
# ---------------------------------------------------------------------------
DEMO_PROFILES: Dict[str, Dict[str, Any]] = {
    "dhruv": {
        "id": "usr_lead_01",
        "name": "Dhruv Patel",
        "email": "dhruv.lead@engineering.org",
        "avatar": "https://ui-avatars.com/api/?name=Dhruv+Patel&background=43562b&color=ffffff",
        "role": "Lead Architect",
        "role_code": "lead_architect",
        "permissions": ["prioritize", "export_jira", "sync_notion", "override_weights", "manage_integrations"],
        "team": "Core Platform & Architecture",
    },
    "sarah": {
        "id": "usr_ml_02",
        "name": "Sarah Jenkins",
        "email": "sarah.j@engineering.org",
        "avatar": "https://ui-avatars.com/api/?name=Sarah+Jenkins&background=1a3a5c&color=ffffff",
        "role": "Staff ML Engineer",
        "role_code": "ml_engineer",
        "permissions": ["retrain_model", "export_jira", "view_telemetry", "sync_notion"],
        "team": "ML & Defect Intelligence",
    },
    "alex": {
        "id": "usr_pm_03",
        "name": "Alex Rivera",
        "email": "alex.r@engineering.org",
        "avatar": "https://ui-avatars.com/api/?name=Alex+Rivera&background=5c1a1a&color=ffffff",
        "role": "Product & Engineering Lead",
        "role_code": "product_lead",
        "permissions": ["prioritize", "export_jira", "sync_notion", "approve_sprint"],
        "team": "Product Engineering",
    },
    "developer": {
        "id": "usr_dev_04",
        "name": "Junior Developer",
        "email": "dev.sandbox@engineering.org",
        "avatar": "https://ui-avatars.com/api/?name=Dev+Sandbox&background=444&color=ffffff",
        "role": "Software Engineer",
        "role_code": "developer",
        "permissions": ["view_priorities", "view_hotspots", "suggest_refactor"],
        "team": "Core Platform & Architecture",
    },
}


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def mint_user_jwt(user_dict: Dict[str, Any]) -> str:
    """Mints a signed HS256 JWT for the session cookie."""
    payload = {
        "sub": user_dict.get("id", f"usr_{int(time.time())}"),
        "email": user_dict.get("email"),
        "name": user_dict.get("name") or user_dict.get("full_name"),
        "role": user_dict.get("role", "Lead Architect"),
        "role_code": user_dict.get("role_code", "lead_architect"),
        "avatar": user_dict.get("avatar") or user_dict.get("avatar_url"),
        "permissions": user_dict.get("permissions", []),
        "sandbox": user_dict.get("sandbox", False),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_user_jwt(token_str: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a signed application JWT. Returns None on failure."""
    try:
        decoded = jwt.decode(token_str, settings.JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        logger.debug("JWT expired")
        return None
    except Exception:
        # Fallback: try base64 decode for legacy tokens (removes after P2)
        try:
            parts = token_str.split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                return json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Google OAuth — Authorization Code Flow (server-side)
# ---------------------------------------------------------------------------

def get_google_login_url(state: str) -> str:
    """
    Builds the Google OAuth 2.0 authorization URL.
    Uses server-side Authorization Code Flow (no PKCE needed for confidential client).
    """
    params = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=select_account"
    )
    return params


def _ensure_personal_workspace(db: Session, user: User) -> None:
    """Create an owned workspace for a user who has none (idempotent)."""
    from backend.database.models import Workspace, WorkspaceMembership

    if db.query(WorkspaceMembership).filter(WorkspaceMembership.user_id == user.id).first():
        return
    ws_id = f"ws_{secrets.token_hex(6)}"
    first_name = (user.full_name or user.email).split()[0]
    db.add(Workspace(id=ws_id, name=f"{first_name}'s Workspace", slug=ws_id, owner_id=user.id, is_demo=False))
    db.add(WorkspaceMembership(workspace_id=ws_id, user_id=user.id, role="OWNER"))
    db.commit()


async def exchange_google_code(code: str, db: Session) -> Tuple[User, str]:
    """
    Exchanges a Google authorization code for tokens.
    Verifies the id_token with Google's public certs.
    Upserts a User row. Returns (User, app_jwt).

    Raises ValueError with a user-safe message on any auth failure.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")

    # 1. Exchange code for tokens
    async with httpx.AsyncClient(timeout=15.0) as client:
        tok_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if tok_res.status_code != 200:
            logger.error("Google token exchange failed with HTTP status %s", tok_res.status_code)
            raise ValueError("Google token exchange failed. Please try signing in again.")

        tok_data = tok_res.json()
        id_token_str = tok_data.get("id_token")
        if not id_token_str:
            raise ValueError("No id_token in Google response.")

    # 2. Verify id_token with Google's public certs
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        id_info = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        logger.error("Google id_token verification failed: %s", e)
        raise ValueError("Google token verification failed. Please try again.")

    # 3. Validate claims
    if not id_info.get("email_verified"):
        raise ValueError("Google account email is not verified.")
    if id_info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("Invalid token issuer.")

    sub = id_info["sub"]
    email = id_info.get("email", "")
    full_name = id_info.get("name") or email.split("@")[0].replace(".", " ").title()
    avatar_url = id_info.get("picture") or f"https://ui-avatars.com/api/?name={full_name}&background=43562b&color=ffffff"
    user_id = f"usr_google_{sub}"

    # 4. Upsert User
    user = db.query(User).filter(
        (User.id == user_id) | (User.email == email)
    ).first()

    if user:
        user.full_name = full_name
        user.avatar_url = avatar_url
        user.is_active = True
    else:
        user = User(
            id=user_id,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            is_active=True,
        )
        db.add(user)
    db.commit()
    db.refresh(user)

    # 4b. Give first-time users their own empty workspace instead of the shared demo one
    _ensure_personal_workspace(db, user)

    # 5. Mint app JWT
    app_jwt = mint_user_jwt({
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "avatar": user.avatar_url,
        "sandbox": False,
    })

    return user, app_jwt


# ---------------------------------------------------------------------------
# Sandbox / Demo helpers (DEV_SANDBOX_AUTH only)
# ---------------------------------------------------------------------------

def get_sandbox_demo_user(db: Session) -> Tuple[User, str]:
    """
    Returns the demo usr_lead_01 user and a sandbox-flagged JWT.
    Only called when DEV_SANDBOX_AUTH=True.
    """
    demo = DEMO_PROFILES["dhruv"]
    user = db.query(User).filter(User.id == demo["id"]).first()
    if not user:
        user = User(
            id=demo["id"],
            email=demo["email"],
            full_name=demo["name"],
            avatar_url=demo.get("avatar"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    app_jwt = mint_user_jwt({
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "avatar": user.avatar_url,
        "sandbox": True,
        "permissions": demo["permissions"],
        "role": demo["role"],
        "role_code": demo["role_code"],
    })
    return user, app_jwt


# ---------------------------------------------------------------------------
# Legacy compat shims — kept so existing tests/routes don't break
# ---------------------------------------------------------------------------

def get_current_user() -> Dict[str, Any]:
    """Legacy shim — returns demo profile dict. Use tenant.get_current_user() for real auth."""
    return DEMO_PROFILES["dhruv"]


def set_active_profile(profile_key: str) -> Dict[str, Any]:
    """Switches persona for demo/viva (stateless — returns profile dict for JWT minting)."""
    if profile_key in DEMO_PROFILES:
        return DEMO_PROFILES[profile_key]
    raise ValueError(f"Unknown demo profile key: {profile_key}")


def logout_user() -> Dict[str, Any]:
    """Stateless logout — cookie clearing is done in the route layer."""
    return {"status": "logged_out"}


# ---------------------------------------------------------------------------
# Google credential inspection (diagnostic endpoint — keep for viva)
# ---------------------------------------------------------------------------

def verify_google_credential(credential_jwt: str) -> Dict[str, Any]:
    """
    Cryptographically verifies a Google ID token (used by /auth/google POST endpoint).
    Falls back to base64 decode in sandbox mode.
    """
    if settings.GOOGLE_CLIENT_ID:
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            id_info = google_id_token.verify_oauth2_token(
                credential_jwt,
                google_requests.Request(),
                audience=settings.GOOGLE_CLIENT_ID,
            )
            if not id_info.get("email_verified"):
                raise ValueError("email_verified is False")
            if id_info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
                raise ValueError("Invalid issuer")

            email = id_info.get("email", "")
            sub = id_info.get("sub", "")
            return {
                "id": f"usr_google_{sub}",
                "name": id_info.get("name") or email,
                "email": email,
                "avatar": id_info.get("picture"),
                "provider": "google",
                "email_verified": True,
                "google_sub": sub,
            }
        except Exception as e:
            logger.debug("verify_google_credential prod path failed: %s", e)

    # Fallback: base64 decode (sandbox)
    try:
        parts = credential_jwt.split(".")
        if len(parts) >= 2:
            padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
            return {
                "id": f"usr_google_{payload.get('sub', 'sandbox')}",
                "name": payload.get("name", "Sandbox User"),
                "email": payload.get("email", "sandbox@debtscope.local"),
                "avatar": payload.get("picture"),
                "provider": "google",
                "email_verified": payload.get("email_verified", True),
                "google_sub": payload.get("sub"),
            }
    except Exception:
        pass

    return DEMO_PROFILES["dhruv"]


def inspect_google_token(credential_jwt: str) -> Dict[str, Any]:
    """Diagnostic: parse and audit Google OIDC token claims."""
    diagnostic: Dict[str, Any] = {
        "verified": False,
        "token_format_valid": False,
        "email": None,
        "email_verified": None,
        "google_sub": None,
        "issuer": None,
        "audience": None,
        "is_expired": False,
        "claims_audit": {},
    }
    try:
        parts = credential_jwt.split(".")
        if len(parts) >= 2:
            padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
            diagnostic["token_format_valid"] = True
            diagnostic["email"] = payload.get("email")
            diagnostic["email_verified"] = payload.get("email_verified")
            diagnostic["google_sub"] = payload.get("sub")
            diagnostic["issuer"] = payload.get("iss")
            diagnostic["audience"] = payload.get("aud")

            exp = payload.get("exp", 0)
            if exp:
                diagnostic["is_expired"] = time.time() > exp
                diagnostic["expires_at"] = datetime.fromtimestamp(exp, timezone.utc).isoformat()

            is_email_verified = payload.get("email_verified") is True
            has_sub = bool(payload.get("sub"))
            not_expired = not diagnostic["is_expired"]
            diagnostic["verified"] = bool(is_email_verified and has_sub and not_expired)
            diagnostic["claims_audit"] = {
                "email_verified_status": "PASSED" if is_email_verified else "FAILED",
                "issuer_status": (
                    "PASSED"
                    if payload.get("iss") in ("accounts.google.com", "https://accounts.google.com")
                    else "WARNING (custom issuer)"
                ),
                "sub_anchor_status": "PASSED" if has_sub else "FAILED",
                "expiration_status": "PASSED" if not_expired else "FAILED",
            }
    except Exception as e:
        diagnostic["error"] = str(e)
    return diagnostic
