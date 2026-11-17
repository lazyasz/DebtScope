"""
What-If simulation (runs the trained defect model) and AI remediation recipes.
"""

from typing import Dict, Any, List, Optional
import os
import math
import time

_predictor_instance = None

def _predict_faults(churn: float, complexity: float, debt_minutes: float, experience: float, refactorings: float) -> Optional[float]:
    """Runs the trained defect model (the one scans use) on what-if inputs; None if it isn't available."""
    from backend.services.repo_scanner_service import RepoScannerService
    import numpy as np
    bundle = RepoScannerService.get_defect_model()
    if not bundle or "model" not in bundle:
        return None
    smells = debt_minutes / 25.0
    # Same feature layout the repository scanner feeds the model
    vec = np.array([[churn * 18, churn * 4, churn * 22, 300, 0, 0, smells, debt_minutes,
                     1 if complexity > 18 else 0, 1 if complexity > 14 else 0, smells // 2, smells,
                     refactorings, experience]])
    try:
        return max(0.0, float(bundle["model"].predict(vec)[0]))
    except Exception:
        return None


def calculate_what_if_simulation(
    current_churn: int,
    current_complexity: float,
    current_debt_minutes: float,
    current_experience: int,
    refactoring_effort_pct: float,
    developer_seniority: str,
    test_coverage_pct: float,
    hourly_rate: float = 85.0,
    refactoring_budget_hours: Optional[float] = None,
    refactoring_story_points: Optional[int] = None,
    risk_tolerance: str = "balanced"  # "conservative" | "balanced" | "aggressive"
) -> Dict[str, Any]:
    """
    Simulates defect risk, technical debt remediation, and dollar ROI:
    1. Adjusts structural complexity and code churn based on refactoring effort and budget.
    2. Applies risk tolerance modifier (conservative, balanced, aggressive).
    3. Adjusts author experience metric based on developer seniority.
    4. Adjusts residual defect risk based on automated test coverage boost.
    5. Calculates engineering hours saved and dollar ROI.
    6. Generates multi-sprint projection curves (Sprints 1 through 6).
    """
    # Seniority multiplier for experience
    seniority_map = {
        "Junior Developer (1-2 yrs)": 3,
        "Junior Engineer (1-2 yrs)": 3,
        "Mid-Level Engineer (3-5 yrs)": 15,
        "Senior Engineer (6-8 yrs)": 45,
        "Staff / Principal Architect (9+ yrs)": 90,
        "Lead Architect": 90
    }
    simulated_experience = seniority_map.get(developer_seniority, max(current_experience, 20))

    # Risk tolerance modifier
    risk_multiplier = {
        "conservative": 0.85,  # Focus on safety, strict defect dampening
        "balanced": 1.0,       # Standard balanced triage
        "aggressive": 1.25     # High speed, maximum debt burn-down
    }.get(risk_tolerance.lower(), 1.0)

    model_faults = _predict_faults(current_churn, current_complexity, current_debt_minutes, current_experience, 1.0)
    model_used = "random_forest" if model_faults is not None else "formula"
    if model_faults is not None:
        baseline_faults = round(model_faults, 2)
    else:
        # Mathematical fallback
        baseline_faults = round((current_churn * 0.02) + (current_complexity * 0.25) + (current_debt_minutes * 0.015) / max(1, current_experience * 0.1), 2)

    # Simulated post-refactoring features
    effort_effective = min(100.0, refactoring_effort_pct * (1.1 if risk_tolerance == "aggressive" else (0.9 if risk_tolerance == "conservative" else 1.0)))
    reduction_factor = 1.0 - (effort_effective / 100.0)
    simulated_churn = max(5, int(current_churn * (1.0 - 0.4 * (effort_effective / 100.0))))
    simulated_complexity = max(1.0, current_complexity * (1.0 - 0.5 * (effort_effective / 100.0)))
    simulated_debt_minutes = max(0.0, current_debt_minutes * reduction_factor)

    sim_model = _predict_faults(simulated_churn, simulated_complexity, simulated_debt_minutes, simulated_experience, 1.0 + (effort_effective / 20.0)) if model_used == "random_forest" else None
    if sim_model is not None:
        raw_sim_faults = sim_model
    else:
        raw_sim_faults = (simulated_churn * 0.02) + (simulated_complexity * 0.25) + (simulated_debt_minutes * 0.015) / max(1, simulated_experience * 0.1)
    
    # Apply test coverage dampening factor on residual defects
    coverage_dampening = 1.0 - (min(100.0, max(0.0, test_coverage_pct)) / 100.0 * 0.45)
    simulated_faults = round(max(0.0, raw_sim_faults * coverage_dampening), 2)

    # Calculate reductions & ROI
    faults_prevented = round(max(0.0, baseline_faults - simulated_faults), 2)
    fault_reduction_pct = round((faults_prevented / max(0.01, baseline_faults)) * 100.0, 1)
    
    # Industry benchmark: 1 software defect takes ~16.5 hours of debugging/QA/hotfix
    hours_saved_from_bugs = faults_prevented * 16.5
    hours_saved_from_debt = (current_debt_minutes - simulated_debt_minutes) / 60.0
    total_hours_saved = round(hours_saved_from_bugs + hours_saved_from_debt, 1)
    
    dollar_savings = round(total_hours_saved * hourly_rate, 2)

    # Budget & Story Points calculation
    budget_hours = refactoring_budget_hours or round(current_debt_minutes / 60.0 * (refactoring_effort_pct / 100.0) * 1.2, 1)
    story_points = refactoring_story_points or max(1, math.ceil(budget_hours / 6.0))

    # Multi-Sprint Projections (Sprint 1 to Sprint 6)
    projection_curves = []
    base_debt_hrs = current_debt_minutes / 60.0
    base_defect_prob = min(95.0, baseline_faults * 15.0)
    base_velocity = 60.0  # Baseline team velocity in SP / sprint

    for sprint_idx in range(1, 7):
        # Gradual realization over sprints based on effort and risk tolerance
        decay_progress = min(1.0, (sprint_idx / 4.0) * (effort_effective / 100.0))
        sprint_debt_hrs = max(0.0, round(base_debt_hrs * (1.0 - decay_progress), 1))
        sprint_defect_prob = max(5.0, round(base_defect_prob * (1.0 - (fault_reduction_pct / 100.0) * decay_progress), 1))
        # Velocity recovery: recovering up to +35% sprint capacity
        velocity_gain_pct = round(35.0 * (effort_effective / 100.0) * (sprint_idx / 6.0) * risk_multiplier, 1)
        sprint_velocity = round(base_velocity * (1.0 + (velocity_gain_pct / 100.0)), 1)
        sprint_cumulative_savings = round((total_hours_saved * (sprint_idx / 6.0)) * hourly_rate, 2)

        projection_curves.append({
            "sprint": f"Sprint {sprint_idx}",
            "debt_hours": sprint_debt_hrs,
            "defect_probability_pct": sprint_defect_prob,
            "team_velocity_sp": sprint_velocity,
            "velocity_gain_pct": velocity_gain_pct,
            "cumulative_savings_usd": sprint_cumulative_savings
        })

    # Risk level transition
    def get_risk_label(val: float) -> str:
        if val >= 5.0: return "CRITICAL"
        if val >= 2.5: return "HIGH"
        if val >= 1.0: return "MEDIUM"
        return "LOW"

    # Jira Package Generation Payload
    jira_package = {
        "sprint_name": f"Sprint 49 — Debt Remediation Initiative ({risk_tolerance.capitalize()})",
        "total_story_points": story_points,
        "estimated_budget_hours": budget_hours,
        "projected_roi_usd": dollar_savings,
        "risk_reduction_pct": fault_reduction_pct,
        "suggested_tickets": [
            {
                "issue_key": "DEBT-101",
                "summary": f"Refactor high-cyclomatic hotspot ({current_complexity:.1f} complexity)",
                "story_points": max(1, math.ceil(story_points * 0.5)),
                "priority": "High",
                "component": "Core Architecture"
            },
            {
                "issue_key": "DEBT-102",
                "summary": f"Increase unit & regression test harness to {testCoverage if 'testCoverage' in locals() else test_coverage_pct}%",
                "story_points": max(1, math.ceil(story_points * 0.3)),
                "priority": "Medium",
                "component": "Test Infrastructure"
            },
            {
                "issue_key": "DEBT-103",
                "summary": "Decouple God Class dependencies and extract domain handlers",
                "story_points": max(1, math.ceil(story_points * 0.2)),
                "priority": "High",
                "component": "Domain Service"
            }
        ]
    }

    return {
        "model_used": model_used,
        "baseline": {
            "predicted_faults": baseline_faults,
            "risk_level": get_risk_label(baseline_faults),
            "debt_minutes": current_debt_minutes,
            "debt_hours": round(current_debt_minutes / 60.0, 1),
            "complexity": current_complexity,
            "defect_probability_pct": base_defect_prob
        },
        "simulated": {
            "predicted_faults": simulated_faults,
            "risk_level": get_risk_label(simulated_faults),
            "debt_minutes": round(simulated_debt_minutes, 1),
            "debt_hours": round(simulated_debt_minutes / 60.0, 1),
            "complexity": round(simulated_complexity, 1),
            "defect_probability_pct": max(5.0, round(base_defect_prob * (1.0 - (fault_reduction_pct / 100.0)), 1)),
            "payback_velocity": "1.8 Sprints" if fault_reduction_pct > 50 else "3.2 Sprints",
            "recommendation": f"Allocating {budget_hours}h ({story_points} SP) under a {risk_tolerance} strategy averts {faults_prevented} projected defects and saves ${dollar_savings:,.2f}."
        },
        "impact": {
            "faults_prevented": faults_prevented,
            "fault_reduction_pct": fault_reduction_pct,
            "total_hours_saved": total_hours_saved,
            "dollar_savings": dollar_savings,
            "hourly_rate_used": hourly_rate,
            "budget_hours": budget_hours,
            "story_points": story_points,
            "risk_tolerance": risk_tolerance,
            "return_on_investment_multiple": round(max(1.0, (dollar_savings / max(100.0, (budget_hours * hourly_rate * 0.4)))), 1)
        },
        "projection_curves": projection_curves,
        "jira_package": jira_package
    }


def generate_ai_remediation_recipe(file_path: str, risk_score: float, debt_minutes: float, complexity: float) -> Dict[str, Any]:
    """
    Generates tailored, actionable AI refactoring recipes and before/after code transformations.
    """
    file_lower = file_path.lower()
    
    # Determine dominant architectural code smell
    if complexity > 18 or "manager" in file_lower or "service" in file_lower:
        smell = "God Class / Excessive Architectural Coupling"
        impact_analysis = "High cyclomatic complexity and dense method coupling create severe blast radius during refactorings."
        steps = [
            "1. Extract cohesive sub-methods into dedicated Single Responsibility domain handlers.",
            "2. Replace inline state mutation with immutable domain events or Strategy pattern.",
            "3. Decouple database I/O from core business logic via repository interfaces.",
            "4. Add unit test harnesses targeting edge branches before decomposing private helpers."
        ]
        before_code = (
            "class OrderProcessor {\n"
            "    public void process(Order o) {\n"
            "        // 200+ lines of monolithic logic:\n"
            "        // DB queries, Stripe validation, inventory locks,\n"
            "        // PDF generation, email dispatch...\n"
            "    }\n"
            "}"
        )
        after_code = (
            "class OrderProcessor {\n"
            "    private final PaymentGateway payment;\n"
            "    private final InventoryService inventory;\n"
            "    private final NotificationEmitter notifier;\n"
            "\n"
            "    public OrderResult process(Order o) {\n"
            "        inventory.reserve(o.items());\n"
            "        PaymentResult pay = payment.charge(o.total());\n"
            "        notifier.emitOrderPlaced(o.id());\n"
            "        return OrderResult.success(pay.txId());\n"
            "    }\n"
            "}"
        )
    elif debt_minutes > 120 or "util" in file_lower or "helper" in file_lower:
        smell = "Bloated Utility / Feature Envy Anti-Pattern"
        impact_analysis = "Unstructured utility methods accumulate spurious churn across sprints without clear domain boundaries."
        steps = [
            "1. Move static helper functions directly into the domain models they operate on.",
            "2. Deprecate global mutable helper state in favor of stateless dependency injection.",
            "3. Enforce contract boundaries with strict type hints and input sanitization.",
            "4. Eliminate dead helper branches and unreferenced fallback overloads."
        ]
        before_code = (
            "// Global helper module with uncontrolled dependencies\n"
            "def format_and_save_data(raw_payload, target_db, send_mail=False):\n"
            "    # Feature envy: operates on internal fields of 4 different classes\n"
            "    ..."
        )
        after_code = (
            "class DataPipelineService:\n"
            "    def __init__(self, repository: LakehouseRepository, notifier: EventBus):\n"
            "        self.repository = repository\n"
            "        self.notifier = notifier\n"
            "\n"
            "    def ingest_payload(self, payload: CleanDataContract) -> IngestionResult:\n"
            "        return self.repository.store(payload)"
        )
    else:
        smell = "High Cyclomatic Branch Density"
        impact_analysis = "Nested conditional trees (cyclomatic complexity > 12) increase cognitive load and fault induction risk."
        steps = [
            "1. Replace deep if/else staircases with Polymorphic Dispatch or Command pattern.",
            "2. Introduce early-return guard clauses to flatten execution flow.",
            "3. Extract complex Boolean predicates into self-documenting predicate functions.",
            "4. Isolate error-handling routines into localized exception handlers."
        ]
        before_code = (
            "if user.is_active:\n"
            "    if user.subscription:\n"
            "        if not user.is_banned:\n"
            "            if resource.is_available:\n"
            "                # Deeply nested critical section\n"
            "                execute_action()"
        )
        after_code = (
            "# Guard clauses flatten execution to O(1) cognitive depth\n"
            "if not user.can_execute_action(resource):\n"
            "    raise PermissionDenied('User or resource ineligible')\n"
            "\n"
            "return execute_action()"
        )

    estimated_hours_reduction = round(debt_minutes / 60.0 * 0.75, 1)
    return {
        "file_path": file_path,
        "identified_smell": smell,
        "impact_analysis": impact_analysis,
        "recipe_steps": steps,
        "code_diff": {
            "before": before_code,
            "after": after_code
        },
        "target_metrics": {
            "projected_complexity_reduction_pct": 55.0,
            "projected_defect_risk_reduction_pct": 68.0,
            "estimated_hours_saved": estimated_hours_reduction,
            "recommended_sprint_points": max(1, math.ceil(debt_minutes / 60.0 * 1.5))
        }
    }
