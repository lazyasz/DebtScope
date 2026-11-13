"""
Tests for Background Analysis Worker, Job Orchestration & Tenant Isolation.
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal
from backend.database.models import AnalysisJob, Workspace, User
from backend.services.seed_service import ensure_demo_workspace

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_workspaces():
    db = SessionLocal()
    try:
        ensure_demo_workspace(db)
    finally:
        db.close()


class TestAnalysisJobEndpoints:
    def test_scan_job_ssrf_rejection(self):
        """Verifies SSRF URL rejection returns HTTP 400."""
        response = client.post(
            "/api/v1/jobs/scan",
            json={"url": "http://127.0.0.1:8000/internal"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Security Validation Error" in data["detail"]

    def test_scan_job_creates_queued_record(self):
        """Verifies valid URL returns 202 Accepted and queues background job."""
        response = client.post(
            "/api/v1/jobs/scan",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "job_id" in data
        assert data["job_id"].startswith("job_")
        assert data["repo_url"] == "https://github.com/pallets/flask"

        # Verify job is retrievable via polling endpoint
        job_id = data["job_id"]
        poll_res = client.get(f"/api/v1/jobs/{job_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        assert poll_data["id"] == job_id
        assert poll_data["status"] in ("QUEUED", "CLONING", "ANALYZING", "MINING", "COMPLETED")

    def test_job_polling_tenant_isolation(self):
        """User in workspace A cannot poll a job created in workspace B."""
        db = SessionLocal()
        try:
            # Create another isolated workspace and a job in it
            ws_other = Workspace(id="ws_private_other", name="Other Workspace", slug="other-ws")
            db.merge(ws_other)
            job = AnalysisJob(
                id="job_private_123",
                workspace_id="ws_private_other",
                repo_url="https://github.com/private/repo",
                status="COMPLETED",
            )
            db.merge(job)
            db.commit()
        finally:
            db.close()

        # Default client has demo workspace (ws_demo); querying ws_private_other's job must return 404
        response = client.get("/api/v1/jobs/job_private_123")
        assert response.status_code == 404

    def test_list_workspace_jobs(self):
        """Lists recent jobs for the current workspace."""
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_recover_stale_jobs_on_restart(self):
        """
        Verifies that recover_stale_jobs identifies in-flight jobs (QUEUED, CLONING, ANALYZING, MINING)
        and transitions them to FAILED with a clear restart notice, leaving finished jobs intact.
        """
        from backend.services.analysis_worker import recover_stale_jobs
        db = SessionLocal()
        try:
            # Create in-flight jobs
            j_queued = AnalysisJob(id="job_stale_queued", workspace_id="ws_demo", repo_url="https://github.com/test/repo1", status="QUEUED")
            j_analyzing = AnalysisJob(id="job_stale_analyzing", workspace_id="ws_demo", repo_url="https://github.com/test/repo2", status="ANALYZING")
            j_mining = AnalysisJob(id="job_stale_mining", workspace_id="ws_demo", repo_url="https://github.com/test/repo3", status="MINING")
            j_completed = AnalysisJob(id="job_stale_completed", workspace_id="ws_demo", repo_url="https://github.com/test/repo4", status="COMPLETED")
            db.merge(j_queued)
            db.merge(j_analyzing)
            db.merge(j_mining)
            db.merge(j_completed)
            db.commit()

            recovered_count = recover_stale_jobs(db)
            assert recovered_count >= 3

            # Check statuses
            assert db.query(AnalysisJob).filter(AnalysisJob.id == "job_stale_queued").first().status == "FAILED"
            assert db.query(AnalysisJob).filter(AnalysisJob.id == "job_stale_analyzing").first().status == "FAILED"
            assert db.query(AnalysisJob).filter(AnalysisJob.id == "job_stale_mining").first().status == "FAILED"
            # Completed job must remain COMPLETED
            assert db.query(AnalysisJob).filter(AnalysisJob.id == "job_stale_completed").first().status == "COMPLETED"

            # Check error message
            q_job = db.query(AnalysisJob).filter(AnalysisJob.id == "job_stale_queued").first()
            assert "interrupted by server restart" in q_job.error_message
        finally:
            db.close()

    def test_cookie_secure_samesite_behavior(self):
        """Verifies session cookie security behavior across environments and behind Nginx."""
        from backend.api.auth_routes import _is_cookie_secure, _set_session_cookie
        from backend.config import settings
        from fastapi import Response

        # In current test env
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

