"""
Background Analysis Jobs & Scan Orchestration API Routes.

Endpoints:
  POST /api/v1/jobs/scan      → initiate background repo clone & analysis
  GET  /api/v1/jobs/{job_id}  → poll job status, stage, progress, and results
  GET  /api/v1/jobs           → list recent analysis jobs for active workspace
"""

import uuid
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.tenant import get_current_workspace, get_current_user
from backend.database.models import AnalysisJob, Workspace, User, utc_now
from backend.services.git_cloner import validate_repo_url, SSRFValidationError
from backend.services.analysis_worker import run_analysis_pipeline
from backend.config import settings

router = APIRouter(prefix="/jobs", tags=["Background Analysis Jobs"])


class ScanRepoRequest(BaseModel):
    url: str = Field(..., description="Git repository URL (e.g. 'https://github.com/pallets/flask')")
    auth_token: Optional[str] = Field(None, description="Optional GitHub Personal Access Token for private repos")


class JobStatusResponse(BaseModel):
    id: str
    workspace_id: str
    repository_id: Optional[int]
    repo_url: str
    status: str
    stage: str
    progress_pct: int
    files_analyzed: int
    error_message: Optional[str]
    result_summary: Optional[Dict[str, Any]]
    created_at: Optional[str]
    completed_at: Optional[str]
    last_heartbeat: Optional[str] = None
    timeout_seconds: Optional[int] = 600


@router.post("/scan", status_code=status.HTTP_202_ACCEPTED, summary="Trigger Background Repository Scan")
def trigger_repository_scan(
    payload: ScanRepoRequest,
    background_tasks: BackgroundTasks,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validates repository URL against SSRF boundaries, queues an analysis job,
    and launches background clone, AST complexity analysis, and git mining.
    """
    # 1. SSRF Validation
    try:
        validated_url = validate_repo_url(payload.url)
    except SSRFValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Validation Error: {str(e)}",
        )

    # 2. Concurrency checks
    ACTIVE_STATUSES = ["QUEUED", "CLONING", "ANALYZING", "MINING"]

    # 2a. Per-workspace concurrency check
    ws_active_count = db.query(AnalysisJob).filter(
        AnalysisJob.workspace_id == workspace.id,
        AnalysisJob.status.in_(ACTIVE_STATUSES),
    ).count()
    max_ws = getattr(settings, "WORKER_MAX_WORKSPACE_CONCURRENT_JOBS", 1)
    if ws_active_count >= max_ws:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An analysis job is already running for this workspace (limit: {max_ws}). Please wait for it to complete.",
        )

    # 2b. Global concurrency check
    global_active_count = db.query(AnalysisJob).filter(
        AnalysisJob.status.in_(ACTIVE_STATUSES),
    ).count()
    max_global = getattr(settings, "WORKER_MAX_GLOBAL_CONCURRENT_JOBS", 2)
    if global_active_count >= max_global:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum global concurrent scan capacity reached ({max_global} active jobs). Please retry shortly.",
        )

    # 3. Create Job in DB
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job_timeout = getattr(settings, "WORKER_JOB_TIMEOUT_SECONDS", 600)
    job = AnalysisJob(
        id=job_id,
        workspace_id=workspace.id,
        repo_url=validated_url,
        status="QUEUED",
        stage="Queued for analysis...",
        progress_pct=0,
        last_heartbeat=utc_now(),
        timeout_seconds=job_timeout,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 4. Queue Background Pipeline
    background_tasks.add_task(run_analysis_pipeline, job_id, payload.auth_token)

    return {
        "status": "accepted",
        "job_id": job_id,
        "repo_url": validated_url,
        "message": "Repository analysis queued in background worker.",
    }


@router.get("/{job_id}", response_model=JobStatusResponse, summary="Poll Background Job Status")
def get_job_status(
    job_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """
    Returns real-time status, stage, progress %, and completed metrics for a job.
    Strictly tenant-scoped to the active workspace.
    """
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.workspace_id == workspace.id,
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found in current workspace.",
        )

    summary_dict = None
    if job.result_summary:
        try:
            summary_dict = json.loads(job.result_summary)
        except Exception:
            summary_dict = {"raw": job.result_summary}

    return JobStatusResponse(
        id=job.id,
        workspace_id=job.workspace_id,
        repository_id=job.repository_id,
        repo_url=job.repo_url,
        status=job.status,
        stage=job.stage,
        progress_pct=job.progress_pct,
        files_analyzed=job.files_analyzed or 0,
        error_message=job.error_message,
        result_summary=summary_dict,
        created_at=job.created_at.isoformat() if job.created_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.get("", summary="List Recent Analysis Jobs")
def list_workspace_jobs(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Lists the 20 most recent analysis jobs within the user's active workspace."""
    jobs = db.query(AnalysisJob).filter(
        AnalysisJob.workspace_id == workspace.id,
    ).order_by(AnalysisJob.created_at.desc()).limit(20).all()

    return [
        {
            "id": j.id,
            "repo_url": j.repo_url,
            "status": j.status,
            "stage": j.stage,
            "progress_pct": j.progress_pct,
            "files_analyzed": j.files_analyzed,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]
