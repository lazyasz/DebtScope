"""
Tests for Background Analysis Worker Concurrency Controls, Heartbeats, and Timeouts.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal
from backend.database.models import AnalysisJob, Workspace, User
from backend.services.seed_service import ensure_demo_workspace
from backend.services.analysis_worker import recover_stale_jobs, run_analysis_pipeline
from backend.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_workspaces():
    db = SessionLocal()
    try:
        ensure_demo_workspace(db)
        # Ensure additional test workspace exists
        ws2 = Workspace(id="ws_worker_test2", name="Second Workspace", slug="ws-worker-test2")
        db.merge(ws2)
        # Clean up any residual test jobs
        db.query(AnalysisJob).filter(AnalysisJob.id.like("test_hb_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


class TestWorkerConcurrencyAndLimits:
    def test_per_workspace_concurrency_limit(self):
        """
        Verifies that initiating a second concurrent scan in the same workspace
        is rejected with HTTP 409 Conflict.
        """
        db = SessionLocal()
        try:
            # Create an in-flight job in ws_demo
            active_job = AnalysisJob(
                id="test_hb_ws_active",
                workspace_id="ws_demo",
                repo_url="https://github.com/active/repo",
                status="ANALYZING",
                last_heartbeat=datetime.now(timezone.utc),
            )
            db.merge(active_job)
            db.commit()

            # Attempt to start another scan in ws_demo
            response = client.post(
                "/api/v1/jobs/scan",
                json={"url": "https://github.com/another/repo"},
            )
            assert response.status_code == 409
            data = response.json()
            assert "already running for this workspace" in data["detail"]
        finally:
            db.query(AnalysisJob).filter(AnalysisJob.id == "test_hb_ws_active").delete()
            db.commit()
            db.close()

    def test_global_concurrency_limit(self):
        """
        Verifies that when global concurrency capacity is saturated across workspaces,
        new scan requests return HTTP 429 Too Many Requests.
        """
        db = SessionLocal()
        orig_global_cap = settings.WORKER_MAX_GLOBAL_CONCURRENT_JOBS
        try:
            settings.WORKER_MAX_GLOBAL_CONCURRENT_JOBS = 2
            # Create 2 active jobs in distinct workspaces
            j1 = AnalysisJob(id="test_hb_g1", workspace_id="ws_demo", repo_url="https://github.com/g/1", status="CLONING")
            j2 = AnalysisJob(id="test_hb_g2", workspace_id="ws_worker_test2", repo_url="https://github.com/g/2", status="MINING")
            db.merge(j1)
            db.merge(j2)
            db.commit()

            # Request scan in a third workspace (should hit global cap 429)
            ws3 = Workspace(id="ws_worker_test3", name="Third WS", slug="ws-3")
            db.merge(ws3)
            db.commit()

            # Query with demo client header override or test client
            from backend.database.tenant import get_current_workspace
            app.dependency_overrides[get_current_workspace] = lambda: ws3

            response = client.post(
                "/api/v1/jobs/scan",
                json={"url": "https://github.com/new/repo"},
            )
            assert response.status_code == 429
            data = response.json()
            assert "Maximum global concurrent scan capacity reached" in data["detail"]
        finally:
            app.dependency_overrides.pop(get_current_workspace, None)
            settings.WORKER_MAX_GLOBAL_CONCURRENT_JOBS = orig_global_cap
            db.query(AnalysisJob).filter(AnalysisJob.id.in_(["test_hb_g1", "test_hb_g2"])).delete(synchronize_session=False)
            db.commit()
            db.close()


class TestWorkerHeartbeatRecovery:
    def test_heartbeat_differentiates_active_vs_stale_jobs(self):
        """
        Verifies that recover_stale_jobs marks jobs with stale heartbeats as FAILED,
        while preserving jobs with fresh heartbeats intact.
        """
        db = SessionLocal()
        now = datetime.now(timezone.utc)
        try:
            # 1. Stale job (heartbeat was 300s ago > 120s threshold)
            j_stale = AnalysisJob(
                id="test_hb_stale",
                workspace_id="ws_demo",
                repo_url="https://github.com/stale/repo",
                status="ANALYZING",
                last_heartbeat=now - timedelta(seconds=300),
            )
            # 2. Fresh job (heartbeat was 15s ago <= 120s threshold)
            j_fresh = AnalysisJob(
                id="test_hb_fresh",
                workspace_id="ws_demo",
                repo_url="https://github.com/fresh/repo",
                status="MINING",
                last_heartbeat=now - timedelta(seconds=15),
            )
            db.merge(j_stale)
            db.merge(j_fresh)
            db.commit()

            recovered = recover_stale_jobs(db, stale_threshold_seconds=120)
            assert recovered >= 1

            # Assert stale job failed
            q_stale = db.query(AnalysisJob).filter(AnalysisJob.id == "test_hb_stale").first()
            assert q_stale.status == "FAILED"
            assert "stale worker heartbeat" in q_stale.error_message

            # Assert fresh job was NOT failed
            q_fresh = db.query(AnalysisJob).filter(AnalysisJob.id == "test_hb_fresh").first()
            assert q_fresh.status == "MINING"
            assert q_fresh.error_message is None
        finally:
            db.query(AnalysisJob).filter(AnalysisJob.id.in_(["test_hb_stale", "test_hb_fresh"])).delete(synchronize_session=False)
            db.commit()
            db.close()

    def test_per_job_timeout_detection(self):
        """Verifies that an analysis job whose runtime exceeds timeout_seconds is failed."""
        db = SessionLocal()
        now = datetime.now(timezone.utc)
        try:
            # Job with 5 second timeout, started 30 seconds ago
            timed_out_job = AnalysisJob(
                id="test_hb_timeout",
                workspace_id="ws_demo",
                repo_url="https://github.com/test/timeout",
                status="CLONING",
                started_at=now - timedelta(seconds=30),
                last_heartbeat=now - timedelta(seconds=30),
                timeout_seconds=5,
            )
            db.merge(timed_out_job)
            db.commit()

            # Execute pipeline (should immediately detect timeout and fail without cloning)
            run_analysis_pipeline("test_hb_timeout")

            # Check status
            q_job = db.query(AnalysisJob).filter(AnalysisJob.id == "test_hb_timeout").first()
            assert q_job.status == "FAILED"
            assert "exceeded" in q_job.error_message.lower() or "timed out" in q_job.error_message.lower()
        finally:
            db.query(AnalysisJob).filter(AnalysisJob.id == "test_hb_timeout").delete()
            db.commit()
            db.close()
