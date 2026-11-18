"""
Repository API endpoints.
Provides CRUD and health summary operations for tracked code repositories.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import Repository, SourceFile, PriorityScore, Workspace, User, IntegrationConnection
from backend.database.tenant import get_current_workspace, get_current_user
from backend.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    RepositorySummary,
    SourceFileResponse,
    SourceFileCreate,
)
from backend.services.data_service import DataService

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get("", response_model=List[RepositorySummary])
def list_repositories(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Lists all tracked repositories in workspace with debt and health summaries."""
    repos = DataService.get_all_repositories(db, workspace_id=workspace.id)
    results = []
    for r in repos:
        files = r.files
        file_count = len(files)
        critical_count = 0
        total_health = 0.0

        for f in files:
            score = f.priority_score
            if score:
                if score.priority_level == "CRITICAL":
                    critical_count += 1
                total_health += (100.0 - score.final_priority_score)
            else:
                total_health += 100.0

        avg_health = round(total_health / max(1, file_count), 1)
        results.append(
            RepositorySummary(
                id=r.id,
                name=r.name,
                url=r.url,
                default_branch=r.default_branch,
                created_at=r.created_at,
                file_count=file_count,
                critical_files_count=critical_count,
                average_health_score=avg_health,
            )
        )
    return results


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def create_repository(
    repo_in: RepositoryCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Registers a new code repository for technical debt analysis."""
    return DataService.get_or_create_repository(db, repo_in, workspace_id=workspace.id)


@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(
    repo_id: int,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Fetches details for a single repository."""
    repo = DataService.get_repository_by_id(db, repo_id, workspace_id=workspace.id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository with id {repo_id} not found in current workspace")
    return repo


@router.delete("/{repo_id}", summary="Remove a scanned repository and all its results")
def delete_repository(
    repo_id: int,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    repo = DataService.get_repository_by_id(db, repo_id, workspace_id=workspace.id)
    if not repo or getattr(workspace, "is_demo", False):
        # Only your own workspace's repos; the shared sample workspace is read-only
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found in your workspace")
    db.delete(repo)  # files, metrics, predictions and scores cascade
    db.commit()
    return {"status": "deleted", "id": repo_id}


@router.get("/{repo_id}/files", response_model=List[SourceFileResponse])
def get_repository_files(
    repo_id: int,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Lists all source files registered in a repository."""
    repo = DataService.get_repository_by_id(db, repo_id, workspace_id=workspace.id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository with id {repo_id} not found in current workspace")
    return DataService.get_files_by_repository(db, repo_id, workspace_id=workspace.id)


@router.post("/{repo_id}/files", response_model=SourceFileResponse, status_code=status.HTTP_201_CREATED)
def add_file_to_repository(
    repo_id: int,
    file_in: SourceFileCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Registers a new source file to a repository."""
    repo = DataService.get_repository_by_id(db, repo_id, workspace_id=workspace.id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository with id {repo_id} not found in current workspace")
    file_in.repository_id = repo_id
    return DataService.get_or_create_file(db, file_in, workspace_id=workspace.id)


from pydantic import BaseModel, Field

class RepoScanRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL or Apache project key (e.g., https://github.com/apache/zookeeper)")
    background: bool = Field(default=False, description="Whether to execute analysis asynchronously in background worker")


@router.post("/scan", summary="Scan GitHub Repository or Ingest Apache Lakehouse Project")
def scan_repository(
    payload: RepoScanRequest,
    background_tasks: BackgroundTasks,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Scans a GitHub repository (private ones too when the user connected their GitHub).
    If background=True, queues a sandboxed background analysis job and returns 202.
    Otherwise executes synchronously for backward-compatible demonstration.
    """
    if payload.background:
        from backend.api.jobs_routes import trigger_repository_scan, ScanRepoRequest
        import uuid
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        from backend.database.models import AnalysisJob
        job = AnalysisJob(
            id=job_id,
            workspace_id=workspace.id,
            repo_url=payload.url,
            status="QUEUED",
            stage="Queued for analysis...",
            progress_pct=0,
        )
        db.add(job)
        db.commit()
        from backend.services.analysis_worker import run_analysis_pipeline
        background_tasks.add_task(run_analysis_pipeline, job_id, None)
        return {
            "status": "accepted",
            "job_id": job_id,
            "repo_url": payload.url,
            "message": "Repository analysis queued in background worker.",
        }

    from backend.services.repo_scanner_service import RepoScannerService
    try:
        conn = db.query(IntegrationConnection).filter(
            IntegrationConnection.user_id == user.id,
            IntegrationConnection.provider == "github",
            IntegrationConnection.status == "CONNECTED",
        ).first()
        from backend.integrations.token_security import TokenSecurity
        user_token = TokenSecurity.decrypt(conn.access_token_enc) if conn and conn.access_token_enc else None
        result = RepoScannerService.scan_github_repository(db, payload.url, workspace.id, user_token)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


