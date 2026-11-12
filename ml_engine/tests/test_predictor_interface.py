"""
Unit tests for the Versioned Machine Learning Predictor Interface.
Verifies Phase 3 ML decisions:
- RealDefectPredictor runs on 14 empirical SZZ features
- Domain shift marking for non-training languages (Python/JS/TS)
- SyntheticHeuristicRiskIndex strictly relabeled as legacy heuristic risk index, not defect prediction
"""

import pytest
from ml_engine.predictor_interface import RealDefectPredictor, SyntheticHeuristicRiskIndex


def test_real_defect_predictor_inference():
    """Verifies that RealDefectPredictor loads and produces calibrated predictions."""
    predictor = RealDefectPredictor()
    
    features = {
        "loc": 250,
        "churn": 85,
        "lines_added": 50,
        "lines_removed": 35,
        "code_smells_count": 8,
        "code_churn_commits": 12,
        "author_experience_commits": 45,
        "language": "Java",
        "coverage_provenance": "MEASURED",
    }
    
    result = predictor.predict_file(features)
    
    assert "predicted_risk_score" in result
    assert 0.0 <= result["predicted_risk_score"] <= 100.0
    assert 0.0 <= result["defect_probability"] <= 1.0
    assert result["model_version"] == "real-szz-rf-v2.1"
    assert "SZZ Fault Counts" in result["model_type"]
    
    # Java is native training domain
    assert result["experimental_language"] is False
    assert result["confidence_score"] >= 0.90
    
    # Empirical drivers present
    assert len(result["top_drivers"]) >= 3
    assert result["top_drivers"][0]["feature"] == "author_experience_commits"


def test_real_defect_predictor_domain_shift():
    """Verifies that non-Java languages are flagged as experimental with confidence adjustment."""
    predictor = RealDefectPredictor()
    
    python_features = {
        "loc": 180,
        "churn": 40,
        "language": "Python",
        "code_smells_count": 3,
    }
    py_result = predictor.predict_file(python_features)
    assert py_result["experimental_language"] is True
    assert "experimental domain extrapolation" in py_result["language_note"]
    assert py_result["confidence_score"] <= 0.85

    ts_features = {
        "loc": 320,
        "churn": 90,
        "language": "TypeScript",
        "code_smells_count": 6,
    }
    ts_result = predictor.predict_file(ts_features)
    assert ts_result["experimental_language"] is True


def test_synthetic_heuristic_risk_index_labeling():
    """Verifies that rf_defect_model is isolated, labeled as legacy heuristic, and never as defect prediction."""
    legacy = SyntheticHeuristicRiskIndex()
    
    meta = legacy.get_model_metadata()
    assert meta["model_name"] == "rf_defect_model.pkl"
    assert meta["status"] == "RETIRED_FOR_LIVE_DEFECT_PREDICTION"
    assert "synthetic" in meta["target"].lower()
    assert "feature overlap" in meta["warning"].lower()
    
    pred = legacy.predict_file({
        "cyclomatic_complexity": 18.0,
        "cognitive_complexity": 22.0,
        "code_smells_count": 14,
        "duplication_pct": 5.0,
        "test_coverage_pct": 45.0,
        "code_churn_commits": 10,
        "bug_frequency": 4,
        "lines_of_code": 350,
        "language": "Python",
    })
    
    assert "heuristic_risk_score" in pred
    assert "NOT Defect Prediction" in pred["model_type"]
    assert "retired" in pred["notice"].lower()
