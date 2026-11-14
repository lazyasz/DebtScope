"""
Tests for Background Analysis Worker, Job Orchestration & Tenant Isolation.
"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Optional
from unittest.mock import patch
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


@pytest.fixture(scope="session")
def local_git_fixture_repo(tmp_path_factory):
    """
    Creates a deterministic standalone local git repository with commit history,
    source files, and bug-fix commits for 100% offline worker mining tests.
    """
    repo_dir = tmp_path_factory.mktemp("worker_fixture_repo")
    str_dir = str(repo_dir)

    # Initialize repository
    subprocess.run(["git", "init", "-b", "main"], cwd=str_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Committer"], cwd=str_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "committer@example.com"], cwd=str_dir, check=True, capture_output=True)

    # Commit 1: Initial source code
    code_path = repo_dir / "service.py"
    code_path.write_text(
        "def compute_score(base: int) -> int:\n"
        "    result = 0\n"
        "    for i in range(base):\n"
        "        result += i * 2\n"
        "    return result\n",
        encoding="utf-8"
    )
    subprocess.run(["git", "add", "service.py"], cwd=str_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: initial commit for scoring service"], cwd=str_dir, check=True, capture_output=True)

    # Commit 2: Bug fix commit
    code_path.write_text(
        "def compute_score(base: int) -> int:\n"
        "    # Fix edge case for negative values\n"
        "    if base <= 0:\n"
        "        return 0\n"
        "    result = 0\n"
        "    for i in range(base):\n"
        "        result += i * 2\n"
        "    return result\n",
        encoding="utf-8"
    )
    subprocess.run(["git", "commit", "-am", "fix: resolve bug in negative base computation"], cwd=str_dir, check=True, capture_output=True)

    return str_dir


class MockSandboxedGitCloner:
    """Clones from a local fixture repo without any external network traffic."""
    def __init__(self, repo_url: str, auth_token: Optional[str] = None, fixture_path: str = ""):
        self.raw_url = repo_url
        self.validated_url = repo_url
        self.auth_token = auth_token
        self.temp_dir = None
        self.fixture_path = fixture_path

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="debtscope_fixture_clone_")
        subprocess.run(["git", "clone", self.fixture_path, self.temp_dir], check=True, capture_output=True)
        return self.temp_dir, "fixture_repo"

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and os.path.exists(self.temp_dir):
            def _handle_remove_readonly(func, path, exc):
                import stat
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(self.temp_dir, onerror=_handle_remove_readonly)


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

    def test_scan_job_creates_queued_record(self, local_git_fixture_repo):
        """
        Verifies valid URL returns 202 Accepted, queues background job,
        and completes full mining pipeline using local git fixture without network.
        """
        def cloner_factory(url, auth_token=None):
            return MockSandboxedGitCloner(url, auth_token, fixture_path=local_git_fixture_repo)

        with patch("backend.services.analysis_worker.SandboxedGitCloner", side_effect=cloner_factory):
            response = client.post(
                "/api/v1/jobs/scan",
                json={"url": "https://github.com/test-org/fixture-repo"},
            )
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            assert "job_id" in data
            assert data["job_id"].startswith("job_")
            assert data["repo_url"] == "https://github.com/test-org/fixture-repo"

            # Verify job is retrievable via polling endpoint and reached COMPLETED
            job_id = data["job_id"]
            poll_res = client.get(f"/api/v1/jobs/{job_id}")
            assert poll_res.status_code == 200
            poll_data = poll_res.json()
            assert poll_data["id"] == job_id
            assert poll_data["status"] == "COMPLETED"
            assert poll_data["files_analyzed"] >= 1
            assert poll_data["progress_pct"] == 100

    @pytest.mark.integration
    def test_scan_job_live_network_opt_in(self):
        """Live network test querying real GitHub pallets/flask repository (opt-in only)."""
        response = client.post(
            "/api/v1/jobs/scan",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"

    def test_job_polling_tenant_isolation(self):
        """User in workspace A cannot poll a job created in workspace B."""
        db = SessionLocal()
        try:
            # Create another isolated workspace and commit it before referencing in job foreign key
            ws_other = Workspace(id="ws_private_other", name="Other Workspace", slug="other-ws")
            db.merge(ws_other)
            db.commit()

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
        with stale heartbeats (> 120s) and transitions them to FAILED with a clear restart notice,
        leaving finished jobs intact.
        """
        from backend.services.analysis_worker import recover_stale_jobs
        db = SessionLocal()
        now = datetime.now(timezone.utc)
        stale_hb = now - timedelta(seconds=300)
        try:
            # Create in-flight jobs with stale heartbeats
            j_queued = AnalysisJob(id="job_stale_queued", workspace_id="ws_demo", repo_url="https://github.com/test/repo1", status="QUEUED", last_heartbeat=stale_hb)
            j_analyzing = AnalysisJob(id="job_stale_analyzing", workspace_id="ws_demo", repo_url="https://github.com/test/repo2", status="ANALYZING", last_heartbeat=stale_hb)
            j_mining = AnalysisJob(id="job_stale_mining", workspace_id="ws_demo", repo_url="https://github.com/test/repo3", status="MINING", last_heartbeat=stale_hb)
            j_completed = AnalysisJob(id="job_stale_completed", workspace_id="ws_demo", repo_url="https://github.com/test/repo4", status="COMPLETED", last_heartbeat=stale_hb)
            db.merge(j_queued)
            db.merge(j_analyzing)
            db.merge(j_mining)
            db.merge(j_completed)
            db.commit()

            recovered_count = recover_stale_jobs(db, stale_threshold_seconds=120)
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

    def test_worker_timeout_asserts_no_results_written(self, local_git_fixture_repo):
        """
        WS1 Item 8: Verifies that when a worker job times out or fails:
        1. Job status transitions to FAILED.
        2. Error message explicitly records the timeout.
        3. No source files, metrics, predictions, or priority scores are written to the database.
        """
        from backend.services.analysis_worker import run_analysis_pipeline
        from backend.database.models import SourceFile, EngineeringMetric, PriorityScore, MLPrediction
        
        db = SessionLocal()
        ws_id = "ws_timeout_test"
        try:
            ws = Workspace(id=ws_id, name="Timeout Test WS", slug="timeout-test-ws")
            db.merge(ws)
            db.commit()

            # Job configured with already-expired start timestamp
            expired_time = datetime.now(timezone.utc) - timedelta(seconds=600)
            job = AnalysisJob(
                id="job_timeout_fail_test",
                workspace_id=ws_id,
                repo_url="https://github.com/timeout/repo",
                status="QUEUED",
                timeout_seconds=5,
                started_at=expired_time,
            )
            db.merge(job)
            db.commit()

            # Execute worker pipeline
            run_analysis_pipeline(job.id, auth_token=None)

            # Refresh job and verify status
            failed_job = db.query(AnalysisJob).filter(AnalysisJob.id == "job_timeout_fail_test").first()
            assert failed_job.status == "FAILED"
            assert "exceeded execution timeout" in failed_job.error_message

            # Assert ZERO results written after job failure
            files_count = db.query(SourceFile).filter(SourceFile.workspace_id == ws_id).count()
            metrics_count = db.query(EngineeringMetric).filter(EngineeringMetric.workspace_id == ws_id).count()
            predictions_count = db.query(MLPrediction).filter(MLPrediction.workspace_id == ws_id).count()
            scores_count = db.query(PriorityScore).filter(PriorityScore.workspace_id == ws_id).count()

            assert files_count == 0, f"Expected 0 files written, found {files_count}"
            assert metrics_count == 0, f"Expected 0 metrics written, found {metrics_count}"
            assert predictions_count == 0, f"Expected 0 predictions written, found {predictions_count}"
            assert scores_count == 0, f"Expected 0 scores written, found {scores_count}"
        finally:
            db.close()

    def test_kill_process_tree_terminates_parent_and_child_processes(self):
        """
        Verifies that kill_process_tree terminates both the parent process and any
        spawned child processes (via taskkill /F /T on Windows, and start_new_session + os.killpg on POSIX).
        """
        import sys
        import time
        from backend.services.git_cloner import kill_process_tree

        parent_script = (
            "import subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "print(f'CHILD_PID:{child.pid}', flush=True)\n"
            "time.sleep(60)\n"
        )

        proc = subprocess.Popen(
            [sys.executable, "-c", parent_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        # Read child PID emitted by parent
        line = proc.stdout.readline()
        assert "CHILD_PID:" in line
        child_pid = int(line.strip().split(":")[1])

        # Execute process-tree termination
        kill_process_tree(proc)
        proc.wait(timeout=5)

        # 1. Assert parent is dead
        assert proc.poll() is not None

        # 2. Assert child process is also dead
        time.sleep(0.5)
        if os.name == "nt":
            check = subprocess.run(["tasklist", "/FI", f"PID eq {child_pid}"], capture_output=True, text=True)
            assert str(child_pid) not in check.stdout
        else:
            try:
                os.kill(child_pid, 0)
                alive = True
            except OSError:
                alive = False
            assert not alive, f"Child process {child_pid} was not terminated by kill_process_tree"
