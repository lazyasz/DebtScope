"""
Fail-Closed Configuration & Production-Mode Security Verification Tests.
Verifies that when running in production or with empty environment variables,
all sandbox auth, simulation fallbacks, and dummy bypasses are strictly disabled.
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import Settings


def test_empty_env_defaults_to_production(monkeypatch):
    """Empty env vars must default to production fail-closed behavior."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DEV_SANDBOX_AUTH", raising=False)
    monkeypatch.delenv("JIRA_SIMULATION_MODE", raising=False)
    monkeypatch.delenv("NOTION_SIMULATION_MODE", raising=False)

    s = Settings(
        _env_file=None,
        SECRET_KEY="test-key-32-chars-minimum-length!",
        JWT_SECRET="test-jwt-secret-key-32-chars-min!",
        TOKEN_ENCRYPTION_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
    )
    assert s.ENVIRONMENT == "production"
    assert s.DEV_SANDBOX_AUTH is False
    assert s.JIRA_SIMULATION_MODE is False
    assert s.NOTION_SIMULATION_MODE is False


def test_production_refuses_sandbox_auth(monkeypatch):
    """Attempting to activate DEV_SANDBOX_AUTH in production must raise RuntimeError."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    with pytest.raises(RuntimeError, match="DEV_SANDBOX_AUTH.*production"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEV_SANDBOX_AUTH=True,
            SECRET_KEY="test-key-32-chars-minimum-length!",
            JWT_SECRET="test-jwt-secret-key-32-chars-min!",
            TOKEN_ENCRYPTION_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        )


def test_production_refuses_simulation_flags(monkeypatch):
    """Attempting to activate simulation flags in production must raise RuntimeError."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DEV_SANDBOX_AUTH", raising=False)

    with pytest.raises(RuntimeError, match="JIRA_SIMULATION_MODE.*production"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEV_SANDBOX_AUTH=False,
            JIRA_SIMULATION_MODE=True,
            SECRET_KEY="test-key-32-chars-minimum-length!",
            JWT_SECRET="test-jwt-secret-key-32-chars-min!",
            TOKEN_ENCRYPTION_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        )

    with pytest.raises(RuntimeError, match="NOTION_SIMULATION_MODE.*production"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEV_SANDBOX_AUTH=False,
            NOTION_SIMULATION_MODE=True,
            SECRET_KEY="test-key-32-chars-minimum-length!",
            JWT_SECRET="test-jwt-secret-key-32-chars-min!",
            TOKEN_ENCRYPTION_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        )


def test_unauthenticated_auth_me_rejects_in_production(monkeypatch):
    """Unauthenticated /auth/me in production must return 401, not demo user."""
    from backend.config import settings
    monkeypatch.setattr(settings, "DEV_SANDBOX_AUTH", False)

    client = TestClient(app)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["sandbox_mode"] is False


def test_switch_profile_forbidden_in_production(monkeypatch):
    """POST /auth/switch-profile must return 403 when DEV_SANDBOX_AUTH is False."""
    from backend.config import settings
    monkeypatch.setattr(settings, "DEV_SANDBOX_AUTH", False)

    client = TestClient(app)
    response = client.post("/api/v1/auth/switch-profile", json={"profile_key": "dhruv"})
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_google_login_unconfigured_returns_503(monkeypatch):
    """GET /auth/google/login must return 503 when credentials missing, no silent sandbox fallback."""
    from backend.config import settings
    monkeypatch.setattr(settings, "DEV_SANDBOX_AUTH", False)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")

    client = TestClient(app)
    response = client.get("/api/v1/auth/google/login")
    assert response.status_code == 503


def test_cookie_secure_samesite_behavior():
    """Verifies session cookie security behavior across environments and in production."""
    from backend.api.auth_routes import _is_cookie_secure, _set_session_cookie
    from backend.config import settings
    from fastapi import Response

    orig_secure = settings.COOKIE_SECURE
    orig_env = settings.ENVIRONMENT
    try:
        # 1. Dev default: secure is False
        settings.COOKIE_SECURE = None
        settings.ENVIRONMENT = "development"
        assert _is_cookie_secure() is False

        # 2. Production default: secure is True
        settings.COOKIE_SECURE = None
        settings.ENVIRONMENT = "production"
        assert _is_cookie_secure() is True

        # 3. Explicit override
        settings.COOKIE_SECURE = True
        assert _is_cookie_secure() is True
        settings.COOKIE_SECURE = False
        assert _is_cookie_secure() is False

        # 4. Check Set-Cookie headers in Response
        res = Response()
        settings.COOKIE_SECURE = True
        _set_session_cookie(res, "test_jwt_value")
        cookie_header = res.headers.get("set-cookie", "")
        assert "Secure" in cookie_header
        assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header
        assert "HttpOnly" in cookie_header or "httponly" in cookie_header
    finally:
        settings.COOKIE_SECURE = orig_secure
        settings.ENVIRONMENT = orig_env

