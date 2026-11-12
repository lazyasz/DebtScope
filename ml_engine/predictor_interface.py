"""Root alias for predictor interface."""
from ml_engine.src.predictor_interface import (
    DefectPredictorInterface,
    RealDefectPredictor,
    SyntheticHeuristicRiskIndex,
)

__all__ = ["DefectPredictorInterface", "RealDefectPredictor", "SyntheticHeuristicRiskIndex"]
