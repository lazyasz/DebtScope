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
