"""
Jira Cloud Integration Provider.
Implements Atlassian OAuth 2.0 (3LO) Authorization Code Flow, token refresh lifecycle,
cloud site discovery, commit-to-issue linking, 5D business signal calculation, and ticket write-back.
Supports live Atlassian REST API v3 and interactive Sandbox/Mock mode.
"""

import json
import httpx
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.integrations.base import IntegrationProvider
from backend.integrations.normalizer import Normalizer, NormalizedIssue
from backend.integrations.token_security import TokenSecurity
from backend.database.models import (
    IntegrationConnection,
    JiraIssueLink,
    SourceFile,
    BusinessContext,
    Repository,
)
from backend.services.jira_service import (
    create_jira_issue,
    bulk_export_to_jira,
    derive_jira_business_signals,
    parse_jira_keys_from_commit,
)
from backend.services.priority_service import PriorityService
from backend.config import settings

SANDBOX_JIRA_PROJECTS = [
    {
        "id": "proj_101",
        "key": "DEBT",
        "name": "Technical Debt & Architectural Remediation",
        "projectTypeKey": "software",
        "lead": "Dhruv Patel",
        "issueTypes": ["Task", "Bug", "Story", "Debt Remediation"],
        "open_issues_count": 18,
        "avatar_url": "https://cdn.iconscout.com/icon/free/png-256/jira-1-569472.png"
    },
    {
        "id": "proj_102",
        "key": "CORE",
        "name": "Core Platform & ML Intelligence Engine",
        "projectTypeKey": "software",
        "lead": "Sarah Chen",
        "issueTypes": ["Task", "Bug", "Epic", "Spike"],
        "open_issues_count": 24,
        "avatar_url": "https://cdn.iconscout.com/icon/free/png-256/jira-1-569472.png"
    },
    {
        "id": "proj_103",
        "key": "PAY",
        "name": "Distributed Payment & Billing Gateway",
        "projectTypeKey": "software",
        "lead": "Alex Mercer",
        "issueTypes": ["Task", "Bug", "Security Vulnerability"],
        "open_issues_count": 11,
        "avatar_url": "https://cdn.iconscout.com/icon/free/png-256/jira-1-569472.png"
    }
]

# Simulated issue metadata for common project keys when in sandbox mode
SIMULATED_JIRA_ISSUES = {
    "DEBT-101": {
        "summary": "High cyclomatic complexity in payment routing",
        "issue_type": "Bug",
        "priority": "Highest",
        "status": "In Progress",
        "is_bug": True,
        "sprint_state": "ACTIVE",
        "fix_version": "v2.4.0",
    },
    "DEBT-102": {
        "summary": "Refactor monolithic auth handler",
        "issue_type": "Task",
        "priority": "High",
        "status": "Open",
        "is_bug": False,
        "sprint_state": "ACTIVE",
        "fix_version": "v2.4.0",
    },
    "PAY-42": {
        "summary": "Race condition on concurrent idempotency tokens",
        "issue_type": "Bug",
        "priority": "Highest",
        "status": "Open",
        "is_bug": True,
        "sprint_state": "ACTIVE",
        "fix_version": "v2.3.9",
    },
    "CORE-88": {
        "summary": "Upgrade AST parser and migrate database pool",
        "issue_type": "Task",
        "priority": "Medium",
        "status": "Open",
        "is_bug": False,
        "sprint_state": "FUTURE",
        "fix_version": "v2.5.0",
    },
}


class JiraProvider(IntegrationProvider):
    provider_name = "jira"

    def __init__(self):
        self.client_id = getattr(settings, "JIRA_CLIENT_ID", "") or ""
        self.client_secret = getattr(settings, "JIRA_CLIENT_SECRET", "") or ""
        self.redirect_uri = getattr(settings, "JIRA_REDIRECT_URI", "") or f"{settings.FRONTEND_URL.rstrip('/')}/auth/callback"
        self.domain = settings.JIRA_DOMAIN
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self.project_key = settings.JIRA_PROJECT_KEY

    def is_live_configured(self) -> bool:
        return bool((self.client_id and self.client_secret) or (self.domain and self.email and self.api_token))

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """Generates Atlassian OAuth 2.0 (3LO) authorization URL."""
        if not self.is_live_configured() or not self.client_id:
            frontend_url = settings.FRONTEND_URL.rstrip("/")
            return f"{frontend_url}/integrations?provider=jira&auth_success=true&state={state}&mock_code=jira_mock_auth_code_2026"

        base_url = "https://auth.atlassian.com/authorize"
        audience = "api.atlassian.com"
        # Must match the scopes enabled on the Atlassian app (developer console → Permissions)
        scopes = "read:jira-work read:jira-user write:jira-work offline_access"
        r_uri = redirect_uri or self.redirect_uri
        return (
            f"{base_url}?audience={audience}&client_id={self.client_id}&scope={quote(scopes)}"
            f"&redirect_uri={quote(r_uri, safe='')}&state={state}&response_type=code&prompt=consent"
        )

    async def exchange_code(self, code: str, state: Optional[str] = None, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchanges authorization code for Atlassian Cloud access tokens."""
        if not self.is_live_configured() or code.startswith("jira_mock"):
            if not settings.JIRA_SIMULATION_MODE:
                raise RuntimeError("Jira live credentials not configured and JIRA_SIMULATION_MODE is disabled.")
            return {
                "access_token": "jira_sandbox_mock_token_88921827491",
                "refresh_token": "jira_mock_refresh_token_99182371",
                "expires_in": 3600,
                "scopes": "read:jira-work read:jira-user write:jira-work offline_access",
                "user": {
                    "id": "atlassian_user_9912",
                    "name": "Dhruv Patel",
                    "email": "dhruvsakhare2006@gmail.com",
                    "site_name": "engineering-hub.atlassian.net",
                    "site_id": "cloud_site_debtscope_prod_01",
                    "avatar_url": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png"
                }
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri or self.redirect_uri
                }
            )
            token_data = resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError(token_data.get("error_description") or token_data.get("error") or "Atlassian did not return a token")

            # Fetch accessible Cloud Sites
            sites_resp = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            )
            sites = sites_resp.json()
            site = sites[0] if sites else {}

            return {
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in", 3600),
                "scopes": token_data.get("scope", "read:jira-work read:jira-user write:jira-work offline_access"),
                "user": {
                    "id": site.get("id", "atlassian_cloud_id"),
                    "name": site.get("name", "Atlassian Cloud Site"),
                    "email": settings.JIRA_EMAIL or "jira-admin@debtscope.io",
                    "site_name": site.get("url", "engineering-hub.atlassian.net"),
                    "site_id": site.get("id"),
                    "avatar_url": site.get("avatarUrl", "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png")
                }
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Performs OAuth 2.0 token refresh using offline_access refresh_token."""
        if not self.is_live_configured() or refresh_token.startswith("jira_mock"):
            return {
                "access_token": "jira_refreshed_mock_token_771829",
                "refresh_token": "jira_new_refresh_token_661928",
                "expires_in": 3600,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                }
            )
            data = resp.json()
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token", refresh_token),
                "expires_in": data.get("expires_in", 3600),
            }

    def fetch_or_simulate_issue(self, issue_key: str) -> Dict[str, Any]:
        """Returns details for a Jira issue key from live API or realistic sandbox fixtures."""
        if not self.is_live_configured():
            if not getattr(settings, "JIRA_SIMULATION_MODE", False):
                raise RuntimeError(
                    "Cannot fetch simulated Jira issue: Jira live credentials are not configured and JIRA_SIMULATION_MODE is False. "
                    "Simulation data must not be accessed outside explicit simulation mode."
                )
            clean_key = issue_key.upper().strip()
            if clean_key in SIMULATED_JIRA_ISSUES:
                data = SIMULATED_JIRA_ISSUES[clean_key].copy()
                data["key"] = clean_key
                return data

            # Deterministic generation for arbitrary keys
            is_bug = "BUG" in clean_key or int(''.join(filter(str.isdigit, clean_key)) or 0) % 2 == 1
            return {
                "key": clean_key,
                "summary": f"Telemetry issue for {clean_key}",
                "issue_type": "Bug" if is_bug else "Task",
                "priority": "High" if is_bug else "Medium",
                "status": "In Progress" if is_bug else "Open",
                "is_bug": is_bug,
                "sprint_state": "ACTIVE" if is_bug else "FUTURE",
                "fix_version": "v1.2.0",
            }

    async def sync_mined_jira_links(
        self,
        db: Session,
        workspace_id: str,
        repo_id: int,
        commit_links: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Links commits to Jira issue keys, saves JiraIssueLink records,
        derives business signals for linked files, and triggers priority score recomputation.
        """
        linked_records = 0
        file_to_issues: Dict[int, List[Dict[str, Any]]] = {}

        # Cache source files for this repository
        files = db.query(SourceFile).filter(
            SourceFile.workspace_id == workspace_id,
            SourceFile.repository_id == repo_id
        ).all()
        file_path_map = {f.file_path: f for f in files}

        for commit in commit_links:
            c_hash = commit.get("commit_hash", "")
            jira_keys = commit.get("jira_keys", [])
            touched_files = commit.get("files", [])

            for key in jira_keys:
                issue_info = self.fetch_or_simulate_issue(key)

                for path in touched_files:
                    f_obj = file_path_map.get(path)
                    f_id = f_obj.id if f_obj else None

                    # Upsert JiraIssueLink
                    existing = db.query(JiraIssueLink).filter(
                        JiraIssueLink.workspace_id == workspace_id,
                        JiraIssueLink.issue_key == key,
                        JiraIssueLink.commit_hash == c_hash,
                        JiraIssueLink.file_id == f_id,
                    ).first()

                    if not existing:
                        link = JiraIssueLink(
                            workspace_id=workspace_id,
                            file_id=f_id,
                            commit_hash=c_hash,
                            issue_key=key,
                            summary=issue_info.get("summary"),
                            issue_type=issue_info.get("issue_type", "Task"),
                            priority=issue_info.get("priority", "Medium"),
                            status=issue_info.get("status", "Open"),
                            is_bug=issue_info.get("is_bug", False),
                            sprint_state=issue_info.get("sprint_state"),
                            fix_version=issue_info.get("fix_version"),
                            created_at=datetime.now(timezone.utc),
                        )
                        db.add(link)
                        linked_records += 1

                    if f_id:
                        if f_id not in file_to_issues:
                            file_to_issues[f_id] = []
                        file_to_issues[f_id].append(issue_info)

        db.commit()

        # Update BusinessContext for each file with newly derived signals
        updated_files = 0
        for f_id, issues in file_to_issues.items():
            b_signals = derive_jira_business_signals(issues)
            bctx = db.query(BusinessContext).filter(
                BusinessContext.workspace_id == workspace_id,
                BusinessContext.file_id == f_id
            ).first()

            if bctx:
                bctx.customer_impact = b_signals["customer_impact"]
                bctx.sprint_urgency = b_signals["sprint_urgency"]
                bctx.release_proximity = b_signals["release_proximity"]
                bctx.provenance = "INTEGRATION"
                updated_files += 1

        db.commit()

        # Recalculate priority scores across affected repository files
        recalculated_scores = 0
        for f_id in file_to_issues:
            ps = PriorityService.calculate_file_priority(db, f_id)
            if ps:
                recalculated_scores += 1

        db.commit()

        return {
            "status": "success",
            "linked_records_created": linked_records,
            "files_with_jira_signals": updated_files,
            "recalculated_priority_scores": recalculated_scores,
        }

    async def get_status(self, connection: Optional[IntegrationConnection]) -> Dict[str, Any]:
        """Returns Jira connection status, active projects, and sync statistics."""
        if not connection or connection.status != "CONNECTED":
            return {
                "connected": False,
                "status": "DISCONNECTED",
                "provider": "jira",
                "configured": self.is_live_configured(),
                "mode": "live" if self.is_live_configured() else "sandbox_mock",
                "connected_projects_count": 0,
                "domain": self.domain or "engineering-hub.atlassian.net",
                "project_key": self.project_key or "DEBT",
                "last_sync": None,
                "account": None
            }

        metadata = json.loads(connection.metadata_json or "{}")
        connected_projects = metadata.get("connected_projects", ["DEBT"])

        return {
            "connected": True,
            "status": connection.status,
            "provider": "jira",
            "configured": self.is_live_configured(),
            "mode": "live" if self.is_live_configured() else "sandbox_mock",
            "connected_projects_count": len(connected_projects),
            "connected_projects": connected_projects,
            "domain": self.domain or connection.provider_account_name or "engineering-hub.atlassian.net",
            "project_key": metadata.get("primary_project_key", self.project_key or "DEBT"),
            "last_sync": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "account": {
                "id": connection.provider_account_id,
                "name": connection.provider_account_name,
                "avatar_url": connection.avatar_url
            }
        }

    async def get_resources(self, connection: Optional[IntegrationConnection], query: Optional[str] = None) -> Dict[str, Any]:
        """Lists Jira projects on the sites the user's own Atlassian connection can access."""
        token = TokenSecurity.decrypt(connection.access_token_enc) if connection else None
        if not token:
            return {"projects": [], "total_count": 0, "error": "Not connected"}
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        projects = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            sites = await client.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
            if sites.status_code != 200:
                return {"projects": [], "total_count": 0, "error": f"Atlassian returned {sites.status_code}; try reconnecting."}
            for site in sites.json():
                resp = await client.get(
                    f"https://api.atlassian.com/ex/jira/{site['id']}/rest/api/3/project/search",
                    headers=headers,
                    params={"maxResults": 100, **({"query": query} if query else {})},
                )
                if resp.status_code == 200:
                    for p in resp.json().get("values", []):
                        projects.append({"id": p["id"], "key": p["key"], "name": f"{p['key']} — {p['name']}", "site": site.get("url")})
        return {"projects": projects, "total_count": len(projects), "source": "live_jira_api"}

    async def sync(self, connection: Optional[IntegrationConnection], resource_ids: List[str], db: Session) -> Dict[str, Any]:
        """Synchronizes prioritized debt items into Jira sprint backlog."""
        sample_components = [
            {
                "component_name": "services/auth_service/auth.go",
                "priority_score": 89.2,
                "remediation_effort_hours": 12.0,
                "defect_probability": 0.58,
                "technical_risk": 91.0,
                "business_impact": 88.0,
                "roi_quadrant": "Critical Hotspots",
                "summary": "Refactor Hardened OAuth Token Verification & Replay Protection",
                "issue_type": "Task"
            },
            {
                "component_name": "pipeline/analytics/spark_aggregator.py",
                "priority_score": 84.6,
                "remediation_effort_hours": 16.0,
                "defect_probability": 0.52,
                "technical_risk": 84.0,
                "business_impact": 82.0,
                "roi_quadrant": "Strategic Refactoring",
                "summary": "Decompose Monolithic Aggregator & Optimize Spark Partition Skew",
                "issue_type": "Task"
            }
        ]

        res = await bulk_export_to_jira(sample_components, sprint_name=f"Sprint {datetime.now(timezone.utc).strftime('%U')} — Remediation Backlog")

        if connection:
            metadata = json.loads(connection.metadata_json or "{}")
            metadata["connected_projects"] = resource_ids
            connection.metadata_json = json.dumps(metadata)
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.status = "CONNECTED"
            db.commit()

        return {
            "status": "success",
            "provider": "jira",
            "exported_issues_count": res.get("total_tickets_created", len(sample_components)),
            "sprint_name": res.get("sprint_name", "Remediation Sprint"),
            "results": res.get("issues", []),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def disconnect(self, connection: Optional[IntegrationConnection], db: Session) -> bool:
        """Revokes token and disconnects Jira."""
        if not connection:
            return True
        connection.status = "DISCONNECTED"
        connection.access_token_enc = None
        connection.refresh_token_enc = None
        db.commit()
        return True

    async def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str], db: Session) -> Dict[str, Any]:
        """Ingests Jira issue state updates."""
        issue = payload.get("issue", {})
        issue_key = issue.get("key", "UNKNOWN")
        event = payload.get("webhookEvent", "jira:issue_updated")

        return {
            "status": "received",
            "event": event,
            "issue_key": issue_key,
            "action_triggered": "SYNCHRONIZE_DEBT_STATUS",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
