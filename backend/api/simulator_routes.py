"""
What-If simulator and AI remediation recipe routes.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from backend.services.simulator_service import (
    calculate_what_if_simulation,
    generate_ai_remediation_recipe,
)

router = APIRouter(tags=["Simulator, AI Recipes & CI/CD Intelligence"])


class WhatIfRequest(BaseModel):
    churn: int = Field(120, description="Code churn lines")
    complexity: float = Field(14.0, description="Cyclomatic complexity score")
    debt_minutes: float = Field(90.0, description="Technical debt minutes")
    experience: int = Field(5, description="Author experience commit count")
    refactoring_effort_pct: float = Field(40.0, ge=0.0, le=100.0, description="Refactoring effort percentage (0-100%)")
    developer_seniority: str = Field("Senior Engineer (6-8 yrs)", description="Assigned developer seniority")
    test_coverage_pct: float = Field(80.0, ge=0.0, le=100.0, description="Test coverage percentage (0-100%)")
    hourly_rate: float = Field(85.0, description="Hourly engineering rate in USD")
    refactoring_budget_hours: Optional[float] = Field(None, description="Allocated refactoring hours budget")
    refactoring_story_points: Optional[int] = Field(None, description="Allocated story points budget")
    risk_tolerance: str = Field("balanced", description="Risk tolerance strategy ('conservative' | 'balanced' | 'aggressive')")


class AiRecipeRequest(BaseModel):
    file_path: str = Field(..., description="File path (e.g. 'src/core/DataTree.java')")
    risk_score: float = Field(85.0, description="5D Priority risk score")
    debt_minutes: float = Field(120.0, description="Remediation minutes")
    complexity: float = Field(18.0, description="Cyclomatic complexity")


@router.post("/simulator/what-if", summary="Run Interactive What-If Defect & ROI Simulation")
def run_what_if_simulation(payload: WhatIfRequest):
    """
    Evaluates ML defect predictor across simulated refactoring effort,
    developer seniority transitions, and test coverage boosts, calculating
    hours saved and financial ROI with multi-sprint projection curves.
    """
    return calculate_what_if_simulation(
        current_churn=payload.churn,
        current_complexity=payload.complexity,
        current_debt_minutes=payload.debt_minutes,
        current_experience=payload.experience,
        refactoring_effort_pct=payload.refactoring_effort_pct,
        developer_seniority=payload.developer_seniority,
        test_coverage_pct=payload.test_coverage_pct,
        hourly_rate=payload.hourly_rate,
        refactoring_budget_hours=payload.refactoring_budget_hours,
        refactoring_story_points=payload.refactoring_story_points,
        risk_tolerance=payload.risk_tolerance
    )


@router.post("/recommendations/ai-recipe", summary="Generate Actionable AI Refactoring Blueprint")
def generate_recipe_endpoint(payload: AiRecipeRequest):
    """
    Analyzes code smell and generates actionable step-by-step refactoring recipe
    with before/after diffs and sprint estimates.
    """
    return generate_ai_remediation_recipe(
        file_path=payload.file_path,
        risk_score=payload.risk_score,
        debt_minutes=payload.debt_minutes,
        complexity=payload.complexity
    )
