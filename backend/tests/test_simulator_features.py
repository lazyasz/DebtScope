"""
Tests for Simulator, AI Remediation Recipe, CI/CD PR Gate, and Executive Audit Features.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_what_if_simulation_endpoint():
    """Tests the interactive What-If ML defect and financial ROI calculator."""
    payload = {
        "churn": 150,
        "complexity": 18.0,
        "debt_minutes": 180.0,
        "experience": 4,
        "refactoring_effort_pct": 50.0,
        "developer_seniority": "Senior Engineer (6-8 yrs)",
        "test_coverage_pct": 85.0,
        "hourly_rate": 90.0
    }
    response = client.post("/api/simulator/what-if", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "baseline" in data
    assert "simulated" in data
    assert "impact" in data
    assert data["impact"]["faults_prevented"] >= 0
    assert data["impact"]["dollar_savings"] >= 0
    assert data["impact"]["total_hours_saved"] >= 0


def test_ai_remediation_recipe_endpoint():
    """Tests generation of actionable AI refactoring recipe and code diffs."""
    payload = {
        "file_path": "src/core/OrderManager.java",
        "risk_score": 88.0,
        "debt_minutes": 150.0,
        "complexity": 22.0
    }
    response = client.post("/api/recommendations/ai-recipe", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "identified_smell" in data
    assert "recipe_steps" in data
    assert len(data["recipe_steps"]) > 0
    assert "code_diff" in data
    assert "before" in data["code_diff"]
    assert "after" in data["code_diff"]
