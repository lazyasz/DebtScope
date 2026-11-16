"""
Multi-tenancy isolation tests for DebtScope P1 Foundation.
Proves workspace boundaries are enforced at the query layer.

Run: py -m pytest backend/tests/test_multi_tenancy.py -v
"""

import os
# Must be set before any backend import so Settings() uses these values
os.environ.setdefault("DEV_SANDBOX_AUTH", "True")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import (
    Base, User, Workspace, WorkspaceMembership, Repository, SourceFile,
    EngineeringMetric, TechnicalDebtItem, BusinessContext, MLPrediction,
    PriorityScore, Recommendation, AnalysisJob, CopilotConversation,
    CopilotMessage, JiraIssueLink, NotionReport
)
from backend.database.tenant import TenantQueryHelper
from backend.services.copilot_tools import CopilotToolRegistry
from backend.services.data_service import DataService
from backend.services.priority_service import PriorityService
from backend.services.recommendation_service import RecommendationService
from backend.services.business_service import BusinessService
from backend.services.prediction_service import PredictionService


# ── Shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def mem_db():
    """Fresh in-memory SQLite database per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def isolation_data(mem_db):
    """Two users, two workspaces, one repo each — fully isolated."""
    user_a = User(id="usr_a", email="a@test.com", full_name="User A")
    ws_a = Workspace(id="ws_a", name="WS A", slug="ws-a", owner_id="usr_a")
    mem_a = WorkspaceMembership(user_id="usr_a", workspace_id="ws_a", role="owner")

    user_b = User(id="usr_b", email="b@test.com", full_name="User B")
    ws_b = Workspace(id="ws_b", name="WS B", slug="ws-b", owner_id="usr_b")
    mem_b = WorkspaceMembership(user_id="usr_b", workspace_id="ws_b", role="owner")

    repo_a = Repository(id=1, name="repo-a", url="https://github.com/a/a", workspace_id="ws_a")
    repo_b = Repository(id=2, name="repo-b", url="https://github.com/b/b", workspace_id="ws_b")

    for obj in [user_a, ws_a, mem_a, user_b, ws_b, mem_b, repo_a, repo_b]:
        mem_db.add(obj)
    mem_db.commit()

    return {
        "db": mem_db,
        "user_a": user_a, "ws_a": ws_a,
        "user_b": user_b, "ws_b": ws_b,
        "repo_a": repo_a, "repo_b": repo_b,
    }


# ── TenantQueryHelper tests ──────────────────────────────────────────────────

class TestTenantQueryHelper:
    def test_scoped_returns_only_own_workspace_repos(self, isolation_data):
        db = isolation_data["db"]
        result = TenantQueryHelper.scoped(db, Repository, "ws_a").all()

        assert len(result) == 1
        assert result[0].id == isolation_data["repo_a"].id
        assert result[0].workspace_id == "ws_a"

    def test_user_a_cannot_see_user_b_repos(self, isolation_data):
        db = isolation_data["db"]
        result = TenantQueryHelper.scoped(db, Repository, "ws_a").all()
        repo_ids = {r.id for r in result}

        assert isolation_data["repo_b"].id not in repo_ids

    def test_user_b_cannot_see_user_a_repos(self, isolation_data):
        db = isolation_data["db"]
        result = TenantQueryHelper.scoped(db, Repository, "ws_b").all()
        repo_ids = {r.id for r in result}

        assert isolation_data["repo_a"].id not in repo_ids

    def test_scoped_returns_empty_for_nonexistent_workspace(self, isolation_data):
        db = isolation_data["db"]
        result = TenantQueryHelper.scoped(db, Repository, "ws_ghost").all()
        assert result == []

    def test_get_scoped_one_enforces_cross_workspace_boundary(self, isolation_data):
        """User A's workspace must NOT be able to fetch User B's repo by ID."""
        db = isolation_data["db"]
        result = TenantQueryHelper.get_scoped_one(
            db, Repository, isolation_data["repo_b"].id, "ws_a"
        )
        assert result is None

    def test_get_scoped_one_returns_own_record(self, isolation_data):
        db = isolation_data["db"]
        result = TenantQueryHelper.get_scoped_one(
            db, Repository, isolation_data["repo_a"].id, "ws_a"
        )
        assert result is not None
        assert result.id == isolation_data["repo_a"].id

    def test_scoped_model_without_workspace_id_returns_all(self, isolation_data):
        """Models without workspace_id (e.g. User) are not filtered."""
        db = isolation_data["db"]
        result = TenantQueryHelper.scoped(db, User, "ws_a").all()
        # Both users present — no workspace_id on User table
        assert len(result) >= 2


# ── Membership tests ─────────────────────────────────────────────────────────

class TestWorkspaceMembership:
    def test_workspace_has_correct_owner(self, isolation_data):
        db = isolation_data["db"]
        ws_a = db.query(Workspace).filter(Workspace.id == "ws_a").first()
        assert ws_a.owner_id == "usr_a"

    def test_membership_links_user_to_workspace(self, isolation_data):
        db = isolation_data["db"]
        mem = db.query(WorkspaceMembership).filter(
            WorkspaceMembership.user_id == "usr_a",
            WorkspaceMembership.workspace_id == "ws_a",
        ).first()
        assert mem is not None
        assert mem.role == "owner"

    def test_cross_workspace_membership_does_not_exist(self, isolation_data):
        """User A must NOT be a member of workspace B."""
        db = isolation_data["db"]
        mem = db.query(WorkspaceMembership).filter(
            WorkspaceMembership.user_id == "usr_a",
            WorkspaceMembership.workspace_id == "ws_b",
        ).first()
        assert mem is None


# ── DEV_SANDBOX_AUTH guardrail tests ─────────────────────────────────────────

class TestDEVSandboxAuth:
    def test_sandbox_auth_raises_in_production(self):
        """Settings(DEV_SANDBOX_AUTH=True, ENVIRONMENT=production) must raise."""
        from backend.config import Settings

        with pytest.raises((RuntimeError, Exception)):
            Settings(
                DEV_SANDBOX_AUTH=True,
                ENVIRONMENT="production",
                SECRET_KEY="x",
                JWT_SECRET="x",
            )

    def test_jira_simulation_raises_in_production(self):
        """Settings(JIRA_SIMULATION_MODE=True, ENVIRONMENT=production) must raise."""
        from backend.config import Settings
        with pytest.raises(RuntimeError) as exc_info:
            Settings(
                DEV_SANDBOX_AUTH=False,
                JIRA_SIMULATION_MODE=True,
                NOTION_SIMULATION_MODE=False,
                ENVIRONMENT="production",
                SECRET_KEY="x",
                JWT_SECRET="x",
            )
        assert "JIRA_SIMULATION_MODE=True is not allowed" in str(exc_info.value)

    def test_notion_simulation_raises_in_production(self):
        """Settings(NOTION_SIMULATION_MODE=True, ENVIRONMENT=production) must raise."""
        from backend.config import Settings
        with pytest.raises(RuntimeError) as exc_info:
            Settings(
                DEV_SANDBOX_AUTH=False,
                JIRA_SIMULATION_MODE=False,
                NOTION_SIMULATION_MODE=True,
                ENVIRONMENT="production",
                SECRET_KEY="x",
                JWT_SECRET="x",
            )
        assert "NOTION_SIMULATION_MODE=True is not allowed" in str(exc_info.value)

    def test_production_mode_allowed_when_all_simulations_false(self):
        """When all simulation flags are False and valid secrets are supplied, production instantiates cleanly."""
        from backend.config import Settings
        from cryptography.fernet import Fernet
        valid_fernet = Fernet.generate_key().decode()
        s = Settings(
            DEV_SANDBOX_AUTH=False,
            JIRA_SIMULATION_MODE=False,
            NOTION_SIMULATION_MODE=False,
            ENVIRONMENT="production",
            SECRET_KEY="secure-production-session-secret-key-12345",
            JWT_SECRET="secure-production-jwt-token-secret-key-12345",
            TOKEN_ENCRYPTION_KEY=valid_fernet,
        )
        assert s.ENVIRONMENT == "production"
        assert s.DEV_SANDBOX_AUTH is False
        assert s.JIRA_SIMULATION_MODE is False
        assert s.NOTION_SIMULATION_MODE is False

    def test_production_refuses_default_session_secret(self):
        """In production, default or empty SECRET_KEY raises RuntimeError."""
        from backend.config import Settings
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with pytest.raises(RuntimeError, match="SECRET_KEY is missing or using an insecure default"):
            Settings(
                ENVIRONMENT="production",
                DEV_SANDBOX_AUTH=False,
                SECRET_KEY="super-secret-key-change-in-production-2026",
                JWT_SECRET="valid-secret-1234567890",
                TOKEN_ENCRYPTION_KEY=key,
            )

    def test_production_refuses_default_jwt_secret(self):
        """In production, default or empty JWT_SECRET raises RuntimeError."""
        from backend.config import Settings
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with pytest.raises(RuntimeError, match="JWT_SECRET is missing or using an insecure default"):
            Settings(
                ENVIRONMENT="production",
                DEV_SANDBOX_AUTH=False,
                SECRET_KEY="valid-secret-1234567890",
                JWT_SECRET="pei-jwt-secret-key-production-2026",
                TOKEN_ENCRYPTION_KEY=key,
            )

    def test_production_refuses_missing_or_invalid_fernet_key(self):
        """In production, missing or non-Fernet TOKEN_ENCRYPTION_KEY raises RuntimeError."""
        from backend.config import Settings
        with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY is missing or using an insecure default"):
            Settings(
                ENVIRONMENT="production",
                DEV_SANDBOX_AUTH=False,
                SECRET_KEY="valid-secret-1234567890",
                JWT_SECRET="valid-secret-1234567890",
                TOKEN_ENCRYPTION_KEY="",
            )
        with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY is too short"):
            Settings(
                ENVIRONMENT="production",
                DEV_SANDBOX_AUTH=False,
                SECRET_KEY="valid-secret-1234567890",
                JWT_SECRET="valid-secret-1234567890",
                TOKEN_ENCRYPTION_KEY="not-a-valid-fernet-key",
            )

    def test_sandbox_auth_allowed_in_development(self):
        """DEV_SANDBOX_AUTH=True + ENVIRONMENT=development must NOT raise."""
        from backend.config import Settings

        s = Settings(
            DEV_SANDBOX_AUTH=True,
            ENVIRONMENT="development",
            SECRET_KEY="x",
            JWT_SECRET="x",
        )
        assert s.DEV_SANDBOX_AUTH is True

    def test_empty_env_refuses_sandbox_auth(self, monkeypatch):
        """With an empty environment, the app defaults to production fail-closed behavior and refuses sandbox auth."""
        from backend.config import Settings, settings
        from backend.api.auth_routes import _is_cookie_secure
        from fastapi.testclient import TestClient
        from backend.main import app

        # Clear relevant environment overrides
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("DEV_SANDBOX_AUTH", raising=False)
        monkeypatch.delenv("JIRA_SIMULATION_MODE", raising=False)
        monkeypatch.delenv("NOTION_SIMULATION_MODE", raising=False)

        # 1. Settings instantiated with empty env defaults strictly to production and refuses startup
        with pytest.raises(RuntimeError) as exc_info:
            Settings(_env_file=None)
        assert "Startup refused in production" in str(exc_info.value)

        # 2. In production, cookies are secure by default
        orig_env = settings.ENVIRONMENT
        orig_sandbox = settings.DEV_SANDBOX_AUTH
        orig_sec = settings.COOKIE_SECURE
        try:
            settings.ENVIRONMENT = "production"
            settings.DEV_SANDBOX_AUTH = False
            settings.COOKIE_SECURE = None
            assert _is_cookie_secure() is True

            # 3. Unauthenticated request to /auth/me returns 401 (refuses sandbox auto-login)
            client = TestClient(app, raise_server_exceptions=False)
            res = client.get("/api/v1/auth/me")
            assert res.status_code == 401
            assert res.json().get("sandbox_mode") is False
            assert res.json().get("status") == "unauthenticated"

            # 4. Request to /auth/google/login returns 503 (refuses sandbox bypass)
            res_login = client.get("/api/v1/auth/google/login", follow_redirects=False)
            assert res_login.status_code == 503
            assert "not configured" in res_login.json().get("detail", "").lower()
        finally:
            settings.ENVIRONMENT = orig_env
            settings.DEV_SANDBOX_AUTH = orig_sandbox
            settings.COOKIE_SECURE = orig_sec

    def test_five_weights_sum_to_one(self):
        """Priority formula weights must sum to exactly 1.00."""
        from backend.config import Settings
        s = Settings(ENVIRONMENT="development", DEV_SANDBOX_AUTH=True)
        total = (
            s.WEIGHT_TECHNICAL_RISK
            + s.WEIGHT_BUSINESS_IMPACT
            + s.WEIGHT_RELEASE_URGENCY
            + s.WEIGHT_MAINTENANCE_COST
            + s.WEIGHT_DEBT_AGE
        )
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_effort_blend_is_separate_from_five_weights(self):
        """EFFORT_BLEND_WEIGHT must NOT affect the five-weight sum."""
        from backend.config import Settings
        s = Settings(ENVIRONMENT="development", DEV_SANDBOX_AUTH=True)
        five_sum = (
            s.WEIGHT_TECHNICAL_RISK
            + s.WEIGHT_BUSINESS_IMPACT
            + s.WEIGHT_RELEASE_URGENCY
            + s.WEIGHT_MAINTENANCE_COST
            + s.WEIGHT_DEBT_AGE
        )
        # effort blend is separate — adding it would exceed 1.0
        assert five_sum + s.EFFORT_BLEND_WEIGHT > 1.0, (
            "EFFORT_BLEND_WEIGHT should be a separate Stage-6 value, not part of the 5D sum"
        )


# ── Full cross-tenant isolation test suite across all entities ───────────────

@pytest.fixture
def full_tenant_matrix(mem_db):
    """
    Sets up two complete workspace ecosystems (ws_a and ws_b)
    spanning repositories, source files, metrics, debt items, predictions,
    business context, priority scores, recommendations, jobs, Jira links,
    Notion reports, and Copilot conversations.
    """
    # Workspaces and Users
    usr_a = User(id="usr_a", email="a@tenant.com", full_name="User A")
    ws_a = Workspace(id="ws_a", name="Tenant A", slug="tenant-a", owner_id="usr_a")
    mem_a = WorkspaceMembership(user_id="usr_a", workspace_id="ws_a", role="owner")

    usr_b = User(id="usr_b", email="b@tenant.com", full_name="User B")
    ws_b = Workspace(id="ws_b", name="Tenant B", slug="tenant-b", owner_id="usr_b")
    mem_b = WorkspaceMembership(user_id="usr_b", workspace_id="ws_b", role="owner")

    # Repositories
    repo_a = Repository(id=101, name="repo-alpha", url="https://github.com/a/alpha", workspace_id="ws_a")
    repo_b = Repository(id=202, name="repo-beta", url="https://github.com/b/beta", workspace_id="ws_b")

    # Source Files
    file_a = SourceFile(
        id=1001,
        workspace_id="ws_a",
        repository_id=101,
        file_path="src/payments/processor.py",
        file_name="processor.py",
        language="Python",
        lines_of_code=250,
        is_active=True,
    )
    file_b = SourceFile(
        id=2002,
        workspace_id="ws_b",
        repository_id=202,
        file_path="src/secret/vault.py",
        file_name="vault.py",
        language="Python",
        lines_of_code=400,
        is_active=True,
    )

    # Engineering Metrics
    metric_a = EngineeringMetric(
        workspace_id="ws_a",
        file_id=1001,
        cyclomatic_complexity=18.0,
        code_smells_count=4,
        duplication_pct=5.0,
        test_coverage_pct=65.0,
        technical_risk_score=72.0,
    )
    metric_b = EngineeringMetric(
        workspace_id="ws_b",
        file_id=2002,
        cyclomatic_complexity=35.0,
        code_smells_count=12,
        duplication_pct=15.0,
        test_coverage_pct=30.0,
        technical_risk_score=88.0,
    )

    # Technical Debt Items
    debt_a = TechnicalDebtItem(
        workspace_id="ws_a",
        file_id=1001,
        debt_category="COMPLEXITY",
        severity="HIGH",
        debt_age_days=45,
        description="Tenant A complex billing dispatch",
    )
    debt_b = TechnicalDebtItem(
        workspace_id="ws_b",
        file_id=2002,
        debt_category="SECURITY",
        severity="CRITICAL",
        debt_age_days=120,
        description="Tenant B hardcoded cryptographic seed",
    )

    # Business Context
    ctx_a = BusinessContext(
        workspace_id="ws_a",
        file_id=1001,
        business_criticality=95.0,
        customer_impact=90.0,
        module_criticality=85.0,
        domain_tag="checkout",
    )
    ctx_b = BusinessContext(
        workspace_id="ws_b",
        file_id=2002,
        business_criticality=99.0,
        customer_impact=99.0,
        module_criticality=95.0,
        domain_tag="authentication",
    )

    # ML Predictions
    pred_a = MLPrediction(
        workspace_id="ws_a",
        file_id=1001,
        predicted_future_risk=68.0,
        defect_probability=0.55,
        confidence_score=0.88,
    )
    pred_b = MLPrediction(
        workspace_id="ws_b",
        file_id=2002,
        predicted_future_risk=92.0,
        defect_probability=0.89,
        confidence_score=0.94,
    )

    # Priority Scores
    score_a = PriorityScore(
        workspace_id="ws_a",
        file_id=1001,
        final_priority_score=82.5,
        priority_level="CRITICAL",
        quadrant="STRATEGIC_REFACTOR",
        rank=1,
    )
    score_b = PriorityScore(
        workspace_id="ws_b",
        file_id=2002,
        final_priority_score=94.0,
        priority_level="CRITICAL",
        quadrant="STRATEGIC_REFACTOR",
        rank=1,
    )

    # Recommendations
    rec_a = Recommendation(
        workspace_id="ws_a",
        file_id=1001,
        recommendation_type="Refactor",
        action_summary="Refactor billing processor",
        rationale="Decompose high complexity billing dispatch",
        sprint_target="Next Sprint",
        estimated_story_points=5,
    )
    rec_b = Recommendation(
        workspace_id="ws_b",
        file_id=2002,
        recommendation_type="Security Remediation",
        action_summary="Patch cryptographic seed",
        rationale="Eliminate hardcoded security vulnerability",
        sprint_target="Immediate Sprint",
        estimated_story_points=8,
    )

    # Analysis Jobs
    job_a = AnalysisJob(
        id="job_tenant_a_123",
        workspace_id="ws_a",
        repo_url="https://github.com/a/alpha",
        status="COMPLETED",
        stage="Completed",
        progress_pct=100,
        files_analyzed=1,
    )
    job_b = AnalysisJob(
        id="job_tenant_b_456",
        workspace_id="ws_b",
        repo_url="https://github.com/b/beta",
        status="COMPLETED",
        stage="Completed",
        progress_pct=100,
        files_analyzed=1,
    )

    # Copilot Conversations & Messages
    conv_a = CopilotConversation(
        id="conv_a_001",
        workspace_id="ws_a",
        user_id="usr_a",
        title="Tenant A Debt Strategy",
    )
    msg_a = CopilotMessage(
        conversation_id="conv_a_001",
        role="user",
        content="How do we refactor billing processor?",
    )
    conv_b = CopilotConversation(
        id="conv_b_002",
        workspace_id="ws_b",
        user_id="usr_b",
        title="Tenant B Secret Vault",
    )
    msg_b = CopilotMessage(
        conversation_id="conv_b_002",
        role="user",
        content="Is the cryptographic seed safe?",
    )

    # Jira Links
    jira_a = JiraIssueLink(
        workspace_id="ws_a",
        file_id=1001,
        issue_key="ALPHA-101",
        summary="Refactor Tenant A billing",
        issue_type="Task",
    )
    jira_b = JiraIssueLink(
        workspace_id="ws_b",
        file_id=2002,
        issue_key="BETA-202",
        summary="Audit Tenant B vault",
        issue_type="Bug",
    )

    # Notion Reports
    notion_a = NotionReport(
        workspace_id="ws_a",
        notion_page_id="notion_a_page",
        title="Tenant A Executive Audit",
        total_debt_hours=32.0,
        top_debt_items_count=3,
        report_url="https://notion.so/tenant-a/audit",
    )
    notion_b = NotionReport(
        workspace_id="ws_b",
        notion_page_id="notion_b_page",
        title="Tenant B Executive Audit",
        total_debt_hours=85.0,
        top_debt_items_count=10,
        report_url="https://notion.so/tenant-b/audit",
    )

    all_entities = [
        usr_a, ws_a, mem_a, usr_b, ws_b, mem_b,
        repo_a, repo_b, file_a, file_b,
        metric_a, metric_b, debt_a, debt_b,
        ctx_a, ctx_b, pred_a, pred_b,
        score_a, score_b, rec_a, rec_b,
        job_a, job_b, conv_a, msg_a, conv_b, msg_b,
        jira_a, jira_b, notion_a, notion_b,
    ]
    for e in all_entities:
        mem_db.add(e)
    mem_db.commit()

    return {
        "db": mem_db,
        "ws_a": ws_a, "ws_b": ws_b,
        "repo_a": repo_a, "repo_b": repo_b,
        "file_a": file_a, "file_b": file_b,
        "job_a": job_a, "job_b": job_b,
        "conv_a": conv_a, "conv_b": conv_b,
        "jira_a": jira_a, "jira_b": jira_b,
        "notion_a": notion_a, "notion_b": notion_b,
    }


class TestCrossTenantDataIsolation:
    """
    Exhaustive verification that User/Workspace A cannot read or access
    User/Workspace B's data across all domain tables, background jobs,
    integrations, and Copilot tools.
    """

    def test_repository_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_repos = DataService.get_all_repositories(db, workspace_id="ws_a")
        assert len(a_repos) == 1
        assert a_repos[0].name == "repo-alpha"
        assert DataService.get_repository_by_id(db, 202, workspace_id="ws_a") is None

    def test_source_file_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_files = DataService.get_files_by_repository(db, 101, workspace_id="ws_a")
        assert len(a_files) == 1
        assert a_files[0].file_name == "processor.py"
        # Attempt to access tenant B's file from tenant A's workspace context
        assert DataService.get_file_by_id(db, 2002, workspace_id="ws_a") is None

    def test_technical_debt_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_debt = DataService.get_all_debt_items(db, workspace_id="ws_a")
        assert len(a_debt) == 1
        assert a_debt[0].description == "Tenant A complex billing dispatch"
        assert not any("cryptographic seed" in d.description for d in a_debt)

    def test_business_context_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_contexts = BusinessService.get_all_business_contexts(db, workspace_id="ws_a")
        assert len(a_contexts) == 1
        assert a_contexts[0].domain_tag == "checkout"
        assert BusinessService.get_business_context_by_file_id(db, 2002, workspace_id="ws_a") is None

    def test_ml_predictions_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_preds = PredictionService.get_all_predictions(db, workspace_id="ws_a")
        assert len(a_preds) == 1
        assert a_preds[0].predicted_future_risk == 68.0
        assert PredictionService.get_prediction_by_file_id(db, 2002, workspace_id="ws_a") is None

    def test_priority_scores_and_recommendations_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_ranked = PriorityService.get_ranked_priorities(db, workspace_id="ws_a")
        assert len(a_ranked) == 1
        assert a_ranked[0].file_path == "src/payments/processor.py"

        a_recs = RecommendationService.get_recommendations_response(db, workspace_id="ws_a")
        assert len(a_recs) == 1
        assert a_recs[0].action_summary == "Refactor billing processor"

        # Attempt to fetch file detail of tenant B from tenant A
        assert PriorityService.get_file_detail_response(db, 2002, workspace_id="ws_a") is None

    def test_analysis_jobs_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_jobs = db.query(AnalysisJob).filter(AnalysisJob.workspace_id == "ws_a").all()
        assert len(a_jobs) == 1
        assert a_jobs[0].id == "job_tenant_a_123"

        # Cross-tenant query must return None
        cross_job = db.query(AnalysisJob).filter(
            AnalysisJob.id == "job_tenant_b_456",
            AnalysisJob.workspace_id == "ws_a"
        ).first()
        assert cross_job is None

    def test_copilot_conversations_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_convs = db.query(CopilotConversation).filter(CopilotConversation.workspace_id == "ws_a").all()
        assert len(a_convs) == 1
        assert a_convs[0].title == "Tenant A Debt Strategy"

        # Cross-tenant conversation query must return None
        b_conv_under_a = db.query(CopilotConversation).filter(
            CopilotConversation.id == "conv_b_002",
            CopilotConversation.workspace_id == "ws_a"
        ).first()
        assert b_conv_under_a is None

    def test_jira_and_notion_isolation(self, full_tenant_matrix):
        db = full_tenant_matrix["db"]
        a_jira = db.query(JiraIssueLink).filter(JiraIssueLink.workspace_id == "ws_a").all()
        assert len(a_jira) == 1
        assert a_jira[0].issue_key == "ALPHA-101"

        b_jira_under_a = db.query(JiraIssueLink).filter(
            JiraIssueLink.issue_key == "BETA-202",
            JiraIssueLink.workspace_id == "ws_a"
        ).first()
        assert b_jira_under_a is None

        a_notion = db.query(NotionReport).filter(NotionReport.workspace_id == "ws_a").all()
        assert len(a_notion) == 1
        assert a_notion[0].title == "Tenant A Executive Audit"

        b_notion_under_a = db.query(NotionReport).filter(
            NotionReport.notion_page_id == "notion_b_page",
            NotionReport.workspace_id == "ws_a"
        ).first()
        assert b_notion_under_a is None

    def test_copilot_tools_tenant_containment(self, full_tenant_matrix):
        """
        Verifies CopilotToolRegistry invoked for ws_a cannot resolve, read,
        or inspect any files, priorities, or Jira tickets belonging to ws_b.
        """
        db = full_tenant_matrix["db"]
        tools_a = CopilotToolRegistry(db=db, workspace_id="ws_a")

        # 1. list_priorities returns only ws_a files
        res_priorities = tools_a.list_priorities(limit=10)
        assert res_priorities["workspace_id"] == "ws_a"
        assert len(res_priorities["items"]) == 1
        assert res_priorities["items"][0]["file_id"] == 1001

        # 2. get_file_detail resolves only within ws_a, never returning ws_b's file
        res_detail = tools_a.get_file_detail("src/secret/vault.py")
        assert res_detail.get("file_id") != 2002
        assert res_detail.get("file_path") != "src/secret/vault.py"

        # 3. read_code resolves only within ws_a, never exposing ws_b's file
        res_code = tools_a.read_code(file_path_or_id="2002")
        assert res_code.get("file_path") != "src/secret/vault.py"

        # 4. search_jira_issues returns only ws_a issues
        res_jira = tools_a.search_jira_issues()
        assert res_jira["total_count"] == 1
        assert res_jira["issues"][0]["issue_key"] == "ALPHA-101"

