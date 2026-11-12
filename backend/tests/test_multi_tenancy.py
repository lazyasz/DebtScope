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

from backend.database.models import Base, User, Workspace, WorkspaceMembership, Repository
from backend.database.tenant import TenantQueryHelper


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
