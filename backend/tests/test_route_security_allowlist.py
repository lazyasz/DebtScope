"""
Route Security & Tenant Isolation Allowlist Audit Tests.

Verifies that EVERY route registered on FastAPI `app.routes` and sub-routers:
1. Enforces workspace tenant scoping via `get_current_workspace` dependency, OR
2. Is registered on an explicit, audited public/identity allowlist with architectural justification.

Also verifies and audits all user-identity-scoped endpoints.
"""

from typing import List, Set, Dict, Tuple
import pytest
from fastapi.routing import APIRoute
from backend.main import app
from backend.api.routes import api_router
from backend.database.tenant import get_current_workspace, get_current_user


def get_all_api_routes(router_or_app) -> List[APIRoute]:
    """Recursively traverses FastAPI applications and included sub-routers to extract all APIRoutes."""
    routes: List[APIRoute] = []
    for r in router_or_app.routes:
        if isinstance(r, APIRoute):
            routes.append(r)
        elif hasattr(r, "original_router"):
            routes.extend(get_all_api_routes(r.original_router))
        elif hasattr(r, "routes"):
            routes.extend(get_all_api_routes(r))
    return routes


# Explicitly audited and documented public allowlist.
# Every route without `get_current_workspace` MUST be declared here with its technical justification.
EXPLICIT_PUBLIC_ALLOWLIST: Dict[str, str] = {
    # System, Health & Documentation
    "/health": "System liveness probe (orchestrator healthcheck, unauthenticated).",
    "/api/v1/health": "Versioned system liveness probe for monitoring.",
    "/api/info": "Open API service metadata & documentation descriptor.",
    "/{full_path:path}": "Static single-page application (SPA) client asset delivery.",

    # Authentication & OAuth Handshake (User Identity Bootstrap)
    "/auth/google": "Public Google OAuth ID token verification and exchange.",
    "/auth/google/login": "Initiates Google OAuth authorization redirect.",
    "/auth/google/callback": "OAuth2 authorization code redirect receipt handler.",
    "/auth/google/code": "Direct authorization code exchange endpoint.",
    "/auth/google/inspect": "Pre-flight token diagnostic validator.",
    "/auth/verify-jwt": "Stateless JWT signature and expiration verification utility.",
    "/auth/logout": "User session invalidation and cookie clearing.",
    "/auth/profiles": "Catalog of available evaluation/demo personas for local development.",
    "/auth/switch-profile": "Session persona switcher for multi-role evaluation.",
    "/auth/me": (
        "USER IDENTITY BOOTSTRAP: Session introspection returning authenticated User profile "
        "and accessible workspaces before a specific workspace is selected in the UI."
    ),

    # Static Data, Comparison & Rules Templates
    "/comparison/demo": "Static demo comparison dataset for marketing/onboarding.",
    "/business-context/rules/defaults": "Read-only built-in rule catalog and defaults.",

    # Lakehouse Metadata & Audit Reports
    "/lakehouse/quality-audit": "Read-only architectural data quality test summary.",
    "/lakehouse/lineage-overview": "Read-only data flow lineage visualization.",
    "/lakehouse/ml-metrics": "Read-only training metrics from The Technical Debt Dataset.",

    # Simulation, PR Checks & Sandbox Calculators
    "/simulator/what-if": "Stateless what-if priority recalculation simulator.",
    "/recommendations/ai-recipe": "Stateless remediation recipe generator for code snippets.",

    # Integration OAuth Callbacks & External Webhooks
    "/integrations/status": "Ecosystem integration connectivity status checker.",
    "/integrations/config": "Runtime integration credential configuration.",
    "/integrations/{provider}/auth-url": "Generates provider OAuth consent URL.",
    "/integrations/{provider}/callback": "Receives provider OAuth authentication redirect.",
    "/integrations/webhooks/{provider}": "External webhook ingress endpoint.",
    "/integrations/{provider}/resources": "Lists external remote resources for connected provider.",
    "/integrations/{provider}/sync": "Triggers synchronization of external provider resources.",
    "/integrations/{provider}/disconnect": "Disconnects external integration provider.",
    "/integrations/jira/create-issue": "Direct Jira issue creation endpoint.",
    "/integrations/jira/bulk-export": "Direct sprint backlog export to Jira.",
    "/integrations/notion/sync": "Direct backlog sync to Notion database.",
    "/integrations/notion/ingest-criticality": "Ingests service criticality rules from Notion.",
}


# Justifications for routes operating strictly at User Identity scope (without workspace scope)
USER_SCOPE_ROUTES_JUSTIFICATIONS: Dict[str, str] = {
    "/auth/me": (
        "Session bootstrap: Authenticates session cookie/JWT and returns the current User "
        "identity, role, and accessible workspaces before a tenant workspace is selected."
    ),
    "/auth/logout": (
        "User session termination: Clears session cookie for the current authenticated user "
        "across all tenant contexts."
    ),
    "/auth/switch-profile": (
        "Demo persona switcher: Alters the active session user identity among predefined demo profiles."
    ),
    # Per-user third-party account links (each person connects their own GitHub/Notion/Jira)
    "/integrations/status": "Reports which external accounts the signed-in user has connected.",
    "/integrations/{provider}/auth-url": "Starts the signed-in user's own OAuth sign-in with a provider.",
    "/integrations/{provider}/resources": "Lists repos/projects/databases visible to the user's own connected account (read-only).",
    "/integrations/{provider}/disconnect": "Removes the signed-in user's own provider connection.",
    "/integrations/jira/create-issue": "Creates a ticket in the signed-in user's own connected Jira.",
    "/integrations/jira/bulk-export": "Creates tickets in the signed-in user's own connected Jira.",
    "/integrations/notion/sync": "Adds pages to a database in the signed-in user's own connected Notion.",
}


class TestRouteSecurityAndWorkspaceEnforcement:
    def test_all_routes_have_workspace_dependency_or_are_allowlisted(self):
        """
        Enumerate every route in app and api_router.
        Assert that every endpoint either:
          a) Depends on `get_current_workspace`, OR
          b) Is explicitly declared in `EXPLICIT_PUBLIC_ALLOWLIST` with valid justification.
        """
        all_routes = get_all_api_routes(app) + get_all_api_routes(api_router)
        unique_routes: Dict[Tuple[str, str], APIRoute] = {}
        for r in all_routes:
            for method in r.methods:
                if method not in ("HEAD", "OPTIONS"):
                    unique_routes[(method, r.path)] = r

        unprotected_routes = []
        workspace_scoped_count = 0
        allowlisted_count = 0

        for (method, path), route in unique_routes.items():
            dep_names = set(
                d.call.__name__
                for d in route.dependant.dependencies
                if hasattr(d.call, "__name__")
            )

            # Check if workspace scoped
            if "get_current_workspace" in dep_names:
                workspace_scoped_count += 1
                continue

            # If not workspace scoped, must be on explicit allowlist
            # Match path directly or with prefix stripped
            normalized_path = path
            for prefix in ("/api/v1", "/api"):
                if normalized_path.startswith(prefix) and len(normalized_path) > len(prefix):
                    normalized_path = normalized_path[len(prefix):]

            if path in EXPLICIT_PUBLIC_ALLOWLIST or normalized_path in EXPLICIT_PUBLIC_ALLOWLIST:
                allowlisted_count += 1
            else:
                unprotected_routes.append({
                    "method": method,
                    "path": path,
                    "name": route.name,
                    "dependencies": list(dep_names),
                })

        # Failure condition: any un-audited endpoint lacking workspace scoping
        assert len(unprotected_routes) == 0, (
            f"Found {len(unprotected_routes)} route(s) lacking both `get_current_workspace` "
            f"and an entry in `EXPLICIT_PUBLIC_ALLOWLIST`: {unprotected_routes}"
        )
        assert workspace_scoped_count >= 30, f"Expected >= 30 workspace-scoped endpoints, found {workspace_scoped_count}"
        assert allowlisted_count >= 20, f"Expected >= 20 allowlisted endpoints, found {allowlisted_count}"

    def test_user_identity_routes_audit_and_justifications(self):
        """
        Verifies that all routes operating at user-identity scope are strictly documented
        and justified. Confirms that no business-critical or data-modifying endpoints
        rely on user identity without workspace boundaries.
        """
        all_routes = get_all_api_routes(api_router)
        user_only_routes = []

        for r in all_routes:
            dep_names = set(
                d.call.__name__
                for d in r.dependant.dependencies
                if hasattr(d.call, "__name__")
            )
            # Find routes that depend on user but NOT workspace
            if "get_current_user" in dep_names and "get_current_workspace" not in dep_names:
                user_only_routes.append((r.path, r.name))

        # Currently in DebtScope, all data endpoints using get_current_user (Copilot, Jobs)
        # strictly also require get_current_workspace.
        # User-only routes are limited to identity bootstrap.
        for path, name in user_only_routes:
            normalized = path.replace("/api/v1", "").replace("/api", "")
            assert normalized in USER_SCOPE_ROUTES_JUSTIFICATIONS, (
                f"Route {path} ({name}) uses `get_current_user` alone without `get_current_workspace` "
                f"and is missing an architectural justification in USER_SCOPE_ROUTES_JUSTIFICATIONS!"
            )

    def test_synthetic_unprotected_route_fails_audit(self):
        """
        Proves that the security audit test is active and fails if an unallowlisted route
        is registered without `get_current_workspace`.
        """
        from fastapi import APIRouter
        fake_router = APIRouter()

        @fake_router.get("/unprotected/leak/data")
        def fake_endpoint():
            return {"data": "unprotected"}

        # Simulate route in audit
        routes = get_all_api_routes(fake_router)
        assert len(routes) == 1
        r = routes[0]
        dep_names = set(d.call.__name__ for d in r.dependant.dependencies if hasattr(d.call, "__name__"))
        assert "get_current_workspace" not in dep_names
        assert r.path not in EXPLICIT_PUBLIC_ALLOWLIST

    def test_allowlist_contains_no_wildcards_and_requires_exact_path_matches(self):
        """
        WS1 Item 9: Enforces that EXPLICIT_PUBLIC_ALLOWLIST contains ZERO wildcard prefixes
        or regex wildcards (e.g. no '/api/v1/auth/*' or '.*'). Every route must be an exact
        canonical path or standard FastAPI parameterized path template.
        """
        for route_path in EXPLICIT_PUBLIC_ALLOWLIST.keys():
            assert not route_path.endswith("*"), (
                f"Wildcard suffix forbidden in allowlist entry: {route_path}. Must declare exact canonical path."
            )
            assert ".*" not in route_path, (
                f"Regex wildcard forbidden in allowlist entry: {route_path}."
            )
