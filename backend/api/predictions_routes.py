"""
Machine Learning Predictions API endpoints.
Provides model risk ingestion interfaces for Member 2 ML Engine.
"""

import os
from functools import lru_cache
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import MLPrediction, SourceFile, Workspace
from backend.database.tenant import get_current_workspace
from backend.schemas.prediction import (
    MLPredictionResponse,
    MLPredictionCreate,
    MLPredictionBatchIngest,
)
from backend.services.prediction_service import PredictionService
from backend.services.data_service import DataService

router = APIRouter(prefix="/predictions", tags=["ML Predictions (Member 2 Engine)"])


@lru_cache(maxsize=1)
def _model_info() -> dict:
    """Facts about the defect model scans actually use, read from its saved bundle."""
    from backend.services.repo_scanner_service import RepoScannerService

    # Reuse the scanner's cached copy: loading the 100-tree model twice doubles memory on a small server
    bundle = RepoScannerService.get_defect_model()
    if not bundle or "model" not in bundle:
        raise RuntimeError("defect model file not available")
    model = bundle["model"]
    importances = getattr(model, "feature_importances_", [])
    features = sorted(
        ({"feature": n, "importance": round(float(w), 4)} for n, w in zip(bundle["feature_names"], importances)),
        key=lambda f: -f["importance"],
    )
    m = bundle.get("metrics", {})
    return {
        "algorithm": type(model).__name__,
        "n_estimators": getattr(model, "n_estimators", None),
        "target": bundle.get("target_name"),
        "trained_at": bundle.get("trained_at"),
        "r2": m.get("rf_r2"),
        "cv_r2_mean": m.get("cv_r2_mean"),
        "mae": m.get("rf_mae"),
        "rmse": m.get("rf_rmse"),
        "baseline_mae": m.get("dummy_mae"),
        "mae_improvement_pct": m.get("mae_improvement_pct"),
        "features": features,
    }


@router.get("/model-info", summary="Defect model details (algorithm, accuracy, feature importances)")
def get_model_info(workspace: Workspace = Depends(get_current_workspace)):
    try:
        return _model_info()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Model unavailable: {e}")


@router.get("", response_model=List[MLPredictionResponse])
def list_predictions(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Lists ML defect and risk predictions across all files in workspace."""
    return PredictionService.get_all_predictions(db, workspace_id=workspace.id)


@router.post("/ingest", response_model=MLPredictionResponse, status_code=status.HTTP_201_CREATED)
def ingest_prediction(
    pred_in: MLPredictionCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Ingests a single file's risk prediction from Member 2 ML model."""
    file_obj = DataService.get_file_by_id(db, pred_in.file_id, workspace_id=workspace.id)
    if not file_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source file with id {pred_in.file_id} not found in current workspace"
        )
    return PredictionService.ingest_prediction(db, pred_in)


@router.post("/batch-ingest", response_model=List[MLPredictionResponse], status_code=status.HTTP_201_CREATED)
def batch_ingest_predictions(
    batch_data: MLPredictionBatchIngest,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Batch ingests predictions for multiple files directly from ML pipeline."""
    return PredictionService.batch_ingest_predictions(db, batch_data)


@router.get("/{file_id}", response_model=MLPredictionResponse)
def get_prediction_by_file(
    file_id: int,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Fetches ML prediction for a specific file in workspace."""
    file_obj = DataService.get_file_by_id(db, file_id, workspace_id=workspace.id)
    if not file_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source file with id {file_id} not found in current workspace"
        )
    prediction = PredictionService.get_prediction_by_file_id(db, file_id, workspace_id=workspace.id)
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ML prediction found for file id {file_id}"
        )
    return prediction
