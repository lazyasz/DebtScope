"""
Tenant Scoping & Multi-Tenancy Middleware Helpers.
Guarantees strict workspace isolation across all database queries.
"""

from typing import Optional, Type, TypeVar, List, Any
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User, Workspace, WorkspaceMembership

T = TypeVar("T")


class TenantQueryHelper:
    """Helper to enforce workspace boundary isolation across all data queries."""

    @staticmethod
    def scoped(db: Session, model: Type[T], workspace_id: str):
        """Returns a SQLAlchemy query filtered strictly by workspace_id."""
        if hasattr(model, "workspace_id"):
            return db.query(model).filter(model.workspace_id == workspace_id)
        return db.query(model)

    @staticmethod
    def get_scoped_one(db: Session, model: Type[T], record_id: Any, workspace_id: str) -> Optional[T]:
        """Finds a single record by primary key inside the tenant workspace boundary."""
        if hasattr(model, "workspace_id"):
            return db.query(model).filter(model.id == record_id, model.workspace_id == workspace_id).first()
        return db.query(model).filter(model.id == record_id).first()


def extract_token_from_request(request: Request) -> Optional[str]:
    """Extracts session token from httpOnly cookie or Authorization header."""
    # 1. Check httpOnly cookie
    cookie_token = request.cookies.get("debtscope_session")
    if cookie_token:
        return cookie_token

    # 2. Check Authorization Bearer header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()

    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    FastAPI dependency that returns the authenticated User.

    Resolution order:
    1. DEV_SANDBOX_AUTH=True → always return demo user (no JWT needed).
    2. Valid JWT cookie/header → return or provision that user.
    3. No token → return demo user (graceful fallback for existing viva routes).
    """
    from backend.config import settings
    from backend.services.auth_service import verify_user_jwt, DEMO_PROFILES, get_sandbox_demo_user

    # 1. Sandbox fast-path
    if settings.DEV_SANDBOX_AUTH:
        user, _ = get_sandbox_demo_user(db)
        return user

    token = extract_token_from_request(request)
    if token:
        payload = verify_user_jwt(token)
        if payload and "sub" in payload:
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if user:
                return user
            # Auto-provision user if verified by valid token
            new_user = User(
                id=payload["sub"],
                email=payload.get("email", "user@debtscope.local"),
                full_name=payload.get("name", "DebtScope User"),
                avatar_url=payload.get("avatar")
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user

    # Production: no session means no access (the demo fallback let anonymous
    # visitors read and write the demo workspace as the demo user)
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")

    # Default fallback (development/tests): Lead Architect demo user
    from backend.services.auth_service import DEMO_PROFILES
    demo_data = DEMO_PROFILES.get("dhruv", {})
    demo_user = db.query(User).filter(User.id == demo_data.get("id", "usr_lead_01")).first()
    if not demo_user:
        demo_user = User(
            id=demo_data.get("id", "usr_lead_01"),
            email=demo_data.get("email", "dhruv.lead@engineering.org"),
            full_name=demo_data.get("name", "Dhruv Patel"),
            avatar_url=demo_data.get("avatar")
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

    return demo_user


def get_current_workspace(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Workspace:
    """
    FastAPI dependency that resolves the active Workspace.
    Checks:
      1. X-Workspace-Id header or query param
      2. Session token payload
      3. User's owned workspace
      4. System Demo Workspace (ws_demo)
    """
    # 1. Explicit Header or Query Parameter
    header_ws = request.headers.get("X-Workspace-Id") or request.query_params.get("workspace_id")
    if header_ws:
        ws = db.query(Workspace).filter(Workspace.id == header_ws).first()
        if ws:
            # Check membership or demo access
            if ws.is_demo:
                return ws
            membership = db.query(WorkspaceMembership).filter(
                WorkspaceMembership.workspace_id == ws.id,
                WorkspaceMembership.user_id == user.id
            ).first()
            if membership:
                return ws

    # 2. Check token claims for active workspace
    token = extract_token_from_request(request)
    if token:
        from backend.services.auth_service import verify_user_jwt
        payload = verify_user_jwt(token)
        if payload and "workspace_id" in payload:
            ws = db.query(Workspace).filter(Workspace.id == payload["workspace_id"]).first()
            if ws:
                return ws

    # 3. Find user's active or primary workspace
    membership = db.query(WorkspaceMembership).filter(
        WorkspaceMembership.user_id == user.id
    ).first()
    if membership:
        ws = db.query(Workspace).filter(Workspace.id == membership.workspace_id).first()
        if ws:
            return ws

    # 4. Fallback: Demo Workspace
    demo_ws = db.query(Workspace).filter(Workspace.id == "ws_demo").first()
    if not demo_ws:
        demo_ws = Workspace(
            id="ws_demo",
            name="Demo Workspace",
            slug="demo",
            owner_id=user.id,
            is_demo=True
        )
        db.add(demo_ws)
        db.commit()
        db.refresh(demo_ws)

    return demo_ws
