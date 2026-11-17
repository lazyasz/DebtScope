"""
Unified Integrations API Router.
Exposes standard endpoints for Google OAuth, GitHub App, Atlassian Jira Cloud, and Notion Workspace.
Manages connections, credential encryption, resource browsing, synchronization, and webhooks.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import secrets
from datetime import datetime

from backend.database.connection import get_db
from backend.database.models import IntegrationConnection, JiraIssueLink, NotionReport, Workspace, User
from backend.database.tenant import get_current_workspace, get_current_user as session_user
from backend.integrations.github_provider import GitHubProvider
from backend.integrations.jira_provider import JiraProvider
from backend.integrations.notion_provider import NotionProvider
from backend.integrations.token_security import TokenSecurity
from backend.services.auth_service import get_current_user
from backend.services.business_rules_service import BusinessRulesEngine
from backend.config import settings


router = APIRouter(prefix="/integrations", tags=["Unified Integrations Hub"])

# Initialize singleton providers
PROVIDERS = {
    "github": GitHubProvider(),
    "jira": JiraProvider(),
    "notion": NotionProvider(),
}


def get_provider(provider_name: str):
    p = PROVIDERS.get(provider_name.lower())
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration provider '{provider_name}' not supported. Valid providers: github, jira, notion."
        )
    return p


# Request / Response Schemas
class CallbackRequest(BaseModel):
    code: str = Field(..., description="OAuth 2.0 authorization code from vendor")
    state: Optional[str] = Field(default=None, description="CSRF state parameter")
    redirect_uri: Optional[str] = None


class SyncRequest(BaseModel):
    resource_ids: List[str] = Field(default_factory=list, description="IDs of repositories, projects, or databases to synchronize")


class ConfigUpdateRequest(BaseModel):
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    github_app_id: Optional[str] = None
    jira_domain: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_project_key: Optional[str] = None
    notion_api_key: Optional[str] = None
    notion_database_id: Optional[str] = None
    google_client_id: Optional[str] = None


@router.get("/status", summary="Get Unified Ecosystem Integration Status")
async def get_ecosystem_status(db: Session = Depends(get_db), user: User = Depends(session_user)):
    """Returns the comprehensive operational status of all external providers."""
    current_user = {"id": user.id, "name": user.full_name, "email": user.email, "role": None, "avatar": user.avatar_url}
    user_id = user.id

    # Fetch connections for this user
    connections = db.query(IntegrationConnection).filter(IntegrationConnection.user_id == user_id).all()
    conn_map = {c.provider: c for c in connections}

    gh_status = await PROVIDERS["github"].get_status(conn_map.get("github"))
    jira_status = await PROVIDERS["jira"].get_status(conn_map.get("jira"))
    notion_status = await PROVIDERS["notion"].get_status(conn_map.get("notion"))

    return {
        "status": "healthy",
        "user_id": user_id,
        "active_persona": current_user.get("name"),
        "google_auth": {
            "service": "Google Identity Services (OAuth2)",
            "configured": bool(settings.GOOGLE_CLIENT_ID),
            "client_id": settings.GOOGLE_CLIENT_ID or "SANDBOX_MOCK_CLIENT_ID",
            "mode": "live" if settings.GOOGLE_CLIENT_ID else "sandbox_mock",
            "connected": True,
            "account": {
                "name": current_user.get("name"),
                "email": current_user.get("email"),
                "role": current_user.get("role"),
                "avatar": current_user.get("avatar")
            }
        },
        "github": gh_status,
        "github_token_configured": bool(settings.GITHUB_TOKEN),
        "jira": jira_status,
        "notion": notion_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/{provider}/auth-url", summary="Get Provider OAuth Authorization URL")
def get_provider_auth_url(
    provider: str,
    user: User = Depends(session_user),
    redirect_uri: Optional[str] = None,
    state: Optional[str] = None
):
    """Generates the vendor OAuth 2.0 authorization URL with CSRF protection."""
    prov = get_provider(provider)
    if not getattr(prov, "client_id", None) or not getattr(prov, "client_secret", None):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider.capitalize()} sign-in isn't set up on this server yet (missing OAuth app).",
        )
    csrf_state = state or secrets.token_urlsafe(16)
    auth_url = prov.get_authorization_url(csrf_state, redirect_uri)
    return {
        "provider": provider,
        "auth_url": auth_url,
        "state": csrf_state
    }


@router.post("/{provider}/callback", summary="Handle OAuth 2.0 Callback and Store Encrypted Connection")
async def handle_provider_callback(
    provider: str,
    payload: CallbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(session_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Exchanges vendor authorization code for tokens, encrypts tokens,
    and creates or updates the user's IntegrationConnection record.
    """
    prov = get_provider(provider)
    user_id = user.id

    try:
        token_res = await prov.exchange_code(payload.code, payload.state, payload.redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authenticate with {provider}: {str(e)}"
        )

    # Encrypt tokens before saving
    access_token_enc = TokenSecurity.encrypt(token_res.get("access_token"))
    refresh_token_enc = TokenSecurity.encrypt(token_res.get("refresh_token"))
    user_data = token_res.get("user", {})

    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.user_id == user_id,
        IntegrationConnection.provider == provider
    ).first()

    if not conn:
        conn = IntegrationConnection(
            workspace_id=workspace.id,
            user_id=user_id,
            provider=provider,
            provider_account_id=str(user_data.get("id", user_data.get("login", "unknown"))),
            provider_account_name=user_data.get("name") or user_data.get("login") or user_data.get("site_name") or user_data.get("workspace_name"),
            avatar_url=user_data.get("avatar_url") or user_data.get("workspace_icon"),
            access_token_enc=access_token_enc,
            refresh_token_enc=refresh_token_enc,
            scopes=token_res.get("scopes"),
            status="CONNECTED",
            metadata_json=json.dumps({"connected_at": datetime.utcnow().isoformat()}),
            last_sync_at=datetime.utcnow()
        )
        db.add(conn)
    else:
        conn.provider_account_id = str(user_data.get("id", user_data.get("login", conn.provider_account_id)))
        conn.provider_account_name = user_data.get("name") or user_data.get("login") or user_data.get("site_name") or user_data.get("workspace_name") or conn.provider_account_name
        conn.avatar_url = user_data.get("avatar_url") or user_data.get("workspace_icon") or conn.avatar_url
        conn.access_token_enc = access_token_enc
        conn.refresh_token_enc = refresh_token_enc or conn.refresh_token_enc
        conn.status = "CONNECTED"
        conn.error_message = None
        conn.last_sync_at = datetime.utcnow()

    db.commit()
    db.refresh(conn)

    status_data = await prov.get_status(conn)
    return {
        "status": "success",
        "message": f"Successfully connected to {provider.upper()}!",
        "connection": status_data
    }


# ---------------------------------------------------------
# Direct Action Endpoints (Preserving compatibility with existing modals)
# Must be defined BEFORE /{provider}/... parameterized routes
# ---------------------------------------------------------

class JiraIssueRequest(BaseModel):
    component_name: str = Field(..., description="Target software component / file path")
    priority_score: float = Field(..., ge=0.0, le=100.0, description="5D Mathematical Priority Score")
    remediation_effort_hours: float = Field(default=8.0, description="Estimated remediation effort in hours")
    defect_probability: Optional[float] = Field(default=0.45, description="ML Predicted Defect Probability (0-1.0)")
    technical_risk: Optional[float] = Field(default=65.0, description="Technical Risk score (0-100)")
    business_impact: Optional[float] = Field(default=70.0, description="Business Impact score (0-100)")
    roi_quadrant: Optional[str] = Field(default="Quick Wins", description="ROI Matrix Quadrant")
    summary: Optional[str] = None
    issue_type: Optional[str] = "Task"
    explanation: Optional[str] = None
    project_key: Optional[str] = None


class JiraBulkExportRequest(BaseModel):
    sprint_name: Optional[str] = "Sprint 24 — Technical Debt Remediation"
    project_key: Optional[str] = None
    components: List[JiraIssueRequest]


def _user_jira(db: Session, user: User) -> Optional[IntegrationConnection]:
    return db.query(IntegrationConnection).filter(
        IntegrationConnection.user_id == user.id,
        IntegrationConnection.provider == "jira",
        IntegrationConnection.status == "CONNECTED",
        IntegrationConnection.access_token_enc.isnot(None),
    ).first()


async def _create_in_user_jira(conn, db, project_key, items):
    try:
        return await PROVIDERS["jira"].create_issues(conn, db, project_key, items)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Jira refused the ticket: {e}")


class NotionSyncRequest(BaseModel):
    database_id: Optional[str] = None
    components: List[JiraIssueRequest]


class NotionAuditReportRequest(BaseModel):
    title: Optional[str] = "Executive Technical Debt Audit — Q3 2026"
    total_components: Optional[int] = 100
    avg_priority_score: Optional[float] = 64.2
    quick_wins_count: Optional[int] = 24
    critical_hotspots_count: Optional[int] = 12


@router.post("/jira/create-issue", summary="Create Single Jira Refactoring Issue")
async def create_single_jira_issue(
    payload: JiraIssueRequest,
    user: User = Depends(session_user),
    db: Session = Depends(get_db),
):
    """Creates the issue in the user's own Jira when connected; otherwise a clearly simulated result."""
    conn = _user_jira(db, user)
    if conn:
        return await _create_in_user_jira(conn, db, payload.project_key, [payload.model_dump()])
    from backend.services.jira_service import create_jira_issue
    res = await create_jira_issue(payload.model_dump())
    return res


@router.post("/jira/bulk-export", summary="Bulk Export Prioritized Components to Jira Sprint")
async def bulk_export_sprint_to_jira(
    payload: JiraBulkExportRequest,
    user: User = Depends(session_user),
    db: Session = Depends(get_db),
):
    """Creates one issue per component in the user's own Jira when connected; otherwise simulated."""
    components_dict = [c.model_dump() for c in payload.components]
    conn = _user_jira(db, user)
    if conn:
        return await _create_in_user_jira(conn, db, payload.project_key, components_dict)
    from backend.services.jira_service import bulk_export_to_jira
    res = await bulk_export_to_jira(components_dict, payload.sprint_name)
    return res


@router.post("/notion/sync", summary="Sync Components to Notion Database")
async def sync_to_notion_database(
    payload: NotionSyncRequest,
    user: User = Depends(session_user),
    db: Session = Depends(get_db),
):
    """Adds the files to a database in the user's own Notion when connected; otherwise a clearly simulated result."""
    components_dict = [c.model_dump() for c in payload.components]
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.user_id == user.id,
        IntegrationConnection.provider == "notion",
        IntegrationConnection.status == "CONNECTED",
        IntegrationConnection.access_token_enc.isnot(None),
    ).first()
    if conn:
        if not payload.database_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pick one of your Notion databases.")
        try:
            return await PROVIDERS["notion"].create_backlog_pages(conn, payload.database_id, components_dict)
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    from backend.services.notion_service import sync_backlog_to_notion
    return await sync_backlog_to_notion(components_dict, payload.database_id)


@router.post("/notion/create-report", summary="Create Executive Audit Report in Notion")
async def create_audit_report_in_notion(
    payload: NotionAuditReportRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Publishes a comprehensive Tech Debt Executive Audit Report to Notion."""
    from backend.services.notion_service import create_notion_audit_report

    res = await create_notion_audit_report(payload.model_dump())

    # Save NotionReport record
    report = NotionReport(
        workspace_id=workspace.id,
        notion_page_id=res.get("report_id", "adr_mock"),
        title=payload.title or "Executive Technical Debt Audit",
        total_debt_hours=float(res.get("summary", {}).get("total_components", 100)) * 2.5,
        top_debt_items_count=int(res.get("summary", {}).get("critical_hotspots", 12)),
        report_url=res.get("notion_url"),
        export_status="COMPLETED"
    )
    db.add(report)
    db.commit()

    return res


@router.get("/notion/reports", summary="Get Workspace Notion Reports")
def get_notion_reports(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Returns executive Notion audit reports published within current workspace."""
    reports = db.query(NotionReport).filter(NotionReport.workspace_id == workspace.id).all()
    return {
        "status": "success",
        "workspace_id": workspace.id,
        "count": len(reports),
        "reports": [
            {
                "id": r.id,
                "workspace_id": r.workspace_id,
                "notion_page_id": r.notion_page_id,
                "title": r.title,
                "total_debt_hours": r.total_debt_hours,
                "top_debt_items_count": r.top_debt_items_count,
                "report_url": r.report_url,
                "export_status": r.export_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]
    }


@router.get("/jira/issues", summary="Get Workspace Linked Jira Issues")
def get_linked_jira_issues(
    file_id: Optional[int] = None,
    limit: int = 50,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Returns Jira issue links mapped to codebase files."""
    query = db.query(JiraIssueLink).filter(JiraIssueLink.workspace_id == workspace.id)
    if file_id:
        query = query.filter(JiraIssueLink.file_id == file_id)

    issues = query.limit(limit).all()
    return {
        "status": "success",
        "workspace_id": workspace.id,
        "count": len(issues),
        "issues": [
            {
                "id": i.id,
                "issue_key": i.issue_key,
                "summary": i.summary,
                "issue_type": i.issue_type,
                "priority": i.priority,
                "status": i.status,
                "is_bug": i.is_bug,
                "sprint_state": i.sprint_state,
                "fix_version": i.fix_version,
                "file_id": i.file_id,
                "commit_hash": i.commit_hash,
            }
            for i in issues
        ]
    }


class IngestCriticalityRequest(BaseModel):
    database_id: Optional[str] = None
    repository_id: Optional[int] = None


@router.post("/notion/ingest-criticality", summary="Ingest Service Criticality Rules from Notion")
async def ingest_notion_criticality(
    payload: IngestCriticalityRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests Service Criticality rules from Notion and automatically applies them
    to matching repository source files via BusinessRulesEngine.
    """
    prov = PROVIDERS["notion"]
    rules_data = await prov.ingest_criticality(payload.database_id)
    rules = rules_data.get("rules", [])

    updated_files = 0
    if payload.repository_id and rules:
        updated_files = BusinessRulesEngine.apply_rules_to_repository(
            db, payload.repository_id, custom_rules=rules
        )

    return {
        "status": "success",
        "database_id": rules_data.get("database_id"),
        "rules_ingested_count": len(rules),
        "rules": rules,
        "repository_files_updated": updated_files,
    }



@router.post("/config", summary="Update Live Integration Credentials")
def update_credentials_config(payload: ConfigUpdateRequest, workspace: Workspace = Depends(get_current_workspace)):
    """Dynamically updates integration credentials at runtime (development only)."""
    # These are server-wide keys shared by every user; in production they come
    # only from the host's environment, never from a browser request.
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Integration keys are managed in the server environment.")
    if payload.github_client_id is not None:
        settings.GITHUB_CLIENT_ID = payload.github_client_id
    if payload.github_client_secret is not None:
        settings.GITHUB_CLIENT_SECRET = payload.github_client_secret
    if payload.github_app_id is not None:
        settings.GITHUB_APP_ID = payload.github_app_id
    if payload.jira_domain is not None:
        settings.JIRA_DOMAIN = payload.jira_domain
    if payload.jira_email is not None:
        settings.JIRA_EMAIL = payload.jira_email
    if payload.jira_api_token is not None:
        settings.JIRA_API_TOKEN = payload.jira_api_token
    if payload.jira_project_key is not None:
        settings.JIRA_PROJECT_KEY = payload.jira_project_key
    if payload.notion_api_key is not None:
        settings.NOTION_API_KEY = payload.notion_api_key
    if payload.notion_database_id is not None:
        settings.NOTION_DATABASE_ID = payload.notion_database_id
    if payload.google_client_id is not None:
        settings.GOOGLE_CLIENT_ID = payload.google_client_id

    return {
        "status": "success",
        "message": "Integration configurations successfully updated."
    }


# ---------------------------------------------------------
# Dynamic Generic Provider Endpoints
# ---------------------------------------------------------

@router.get("/{provider}/resources", summary="List Accessible Repositories, Projects, or Databases")
async def get_provider_resources(
    provider: str,
    q: Optional[str] = Query(default=None, description="Search keyword query"),
    db: Session = Depends(get_db),
    user: User = Depends(session_user),
):
    """Fetches accessible repositories (GitHub), projects (Jira), or databases (Notion)."""
    prov = get_provider(provider)
    user_id = user.id

    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.user_id == user_id,
        IntegrationConnection.provider == provider
    ).first()

    if not conn or conn.status != "CONNECTED":
        return {"connected": False, "items": [], "message": f"Connect your {provider.capitalize()} account first."}
    resources = await prov.get_resources(conn, query=q)
    return {"connected": True, **resources}


@router.post("/{provider}/sync", summary="Synchronize Selected Provider Resources")
async def sync_provider_resources(
    provider: str,
    payload: SyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(session_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Triggers deep AST scanning and technical-debt metric synchronization for selected resources."""
    prov = get_provider(provider)
    user_id = user.id

    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.user_id == user_id,
        IntegrationConnection.provider == provider
    ).first()

    result = await prov.sync(conn, payload.resource_ids, db)
    return result


@router.post("/{provider}/disconnect", summary="Disconnect Integration and Revoke Token")
async def disconnect_provider(
    provider: str,
    db: Session = Depends(get_db),
    user: User = Depends(session_user),
):
    """Safely disconnects provider integration."""
    prov = get_provider(provider)
    user_id = user.id

    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.user_id == user_id,
        IntegrationConnection.provider == provider
    ).first()

    await prov.disconnect(conn, db)
    return {
        "status": "success",
        "message": f"{provider.capitalize()} integration has been successfully disconnected."
    }


@router.post("/webhooks/{provider}", summary="Receive Inbound Webhook Events")
async def receive_provider_webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Processes incoming vendor webhooks (GitHub push/PR, Jira issue update)."""
    prov = get_provider(provider)
    headers = dict(request.headers)
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    result = await prov.handle_webhook(payload, headers, db)
    return result

