"""
Phase 3 Scoring, Weight Renormalization, Quadrant, and Business Rules Tests.
Verifies ADR 001, ADR 010, and single source of truth 5D formula implementation.
"""

import json
import pytest
from backend.services.priority_service import PriorityService
from backend.services.data_service import DataService
from backend.services.business_service import BusinessService
from backend.services.business_rules_service import BusinessRulesEngine
from backend.schemas.repository import RepositoryCreate, SourceFileCreate
from backend.schemas.metrics import EngineeringMetricCreate
from backend.schemas.business_context import BusinessContextCreate
from backend.database.models import SourceFile, PriorityScore, BusinessContext


def test_dynamic_weight_renormalization_missing_dimensions(db_session):
    """
    Verifies ADR 010: When dimensions are missing (e.g. no business context / integrations),
    weights renormalize dynamically over available dimensions so scores remain on a true 0-100 scale,
    and dimension coverage is recorded accurately.
    """
    repo = DataService.get_or_create_repository(
        db_session, RepositoryCreate(name="p3-test-repo", url="https://github.com/p3/repo.git")
    )
    file_obj = DataService.get_or_create_file(
        db_session,
        SourceFileCreate(
            repository_id=repo.id,
            file_path="src/service/processor.py",
            file_name="processor.py",
            language="Python",
            lines_of_code=150,
        )
    )

    # Ingest ONLY technical risk metrics; no business context, no Jira urgency
    DataService.ingest_engineering_metric(
        db_session,
        EngineeringMetricCreate(
            file_id=file_obj.id,
            cyclomatic_complexity=25.0,
            cognitive_complexity=28.0,
            code_smells_count=12,
            duplication_pct=8.0,
            test_coverage_pct=30.0,
            technical_risk_score=80.0,
        )
    )

    # Calculate priority without BusinessContext
    score = PriorityService.calculate_file_priority(db_session, file_obj.id)

    assert score is not None
    assert 0.0 <= score.baseline_score <= 100.0
    assert 0.0 <= score.final_priority_score <= 100.0

    # Dimension coverage reporting
    assert score.scored_dimensions_count < 5
    assert "of 5 dimensions" in score.dimension_coverage
    assert score.missing_dimensions_json is not None

    missing = json.loads(score.missing_dimensions_json)
    assert isinstance(missing, list)
    assert len(missing) > 0


def test_quadrant_classification_exhaustive(db_session):
    """
    Verifies single source of truth for 4 quadrants:
      - Quick Win: Base Priority >= 60, Effort <= 40
      - Strategic Refactor: Base Priority >= 60, Effort > 40
      - Opportunistic: Base Priority < 60, Effort <= 40
      - Deprioritized: Base Priority < 60, Effort > 40
    """
    repo = DataService.get_or_create_repository(
        db_session, RepositoryCreate(name="quadrant-repo", url="https://github.com/test/quad.git")
    )

    cases = [
        # (name, tech_risk, biz_crit, effort, expected_quadrant)
        ("qw.py", 90.0, 95.0, 25.0, "QUICK_WIN"),
        ("strat.py", 90.0, 95.0, 75.0, "STRATEGIC_REFACTOR"),
        ("opp.py", 20.0, 25.0, 20.0, "OPPORTUNISTIC"),
        ("dep.py", 20.0, 25.0, 80.0, "DEPRIORITIZED"),
    ]

    for fname, risk, biz, effort, expected_quad in cases:
        file_obj = DataService.get_or_create_file(
            db_session,
            SourceFileCreate(
                repository_id=repo.id,
                file_path=f"src/{fname}",
                file_name=fname,
                language="Python",
                lines_of_code=100,
            )
        )
        DataService.ingest_engineering_metric(
            db_session,
            EngineeringMetricCreate(
                file_id=file_obj.id,
                cyclomatic_complexity=15.0,
                cognitive_complexity=15.0,
                code_smells_count=5,
                duplication_pct=5.0,
                test_coverage_pct=50.0,
                technical_risk_score=risk,
            )
        )
        BusinessService.get_or_create_business_context(
            db_session,
            BusinessContextCreate(
                file_id=file_obj.id,
                business_criticality=biz,
                customer_impact=biz,
                module_criticality=biz,
                release_proximity=50.0,
                sprint_urgency=50.0,
                maintenance_cost=50.0,
                estimated_remediation_effort=effort,
                domain_tag="test",
            )
        )
        score = PriorityService.calculate_file_priority(db_session, file_obj.id)
        assert score.quadrant == expected_quad, f"File {fname} expected {expected_quad} but got {score.quadrant}"


def test_business_rules_matching():
    """
    Verifies path pattern matching in BusinessRulesEngine.
    """
    rule = BusinessRulesEngine.match_path_rule("src/payments/stripe_gateway.py")
    assert rule is not None
    assert rule["business_criticality"] >= 90.0
    assert rule["domain_tag"] == "payment"

    rule = BusinessRulesEngine.match_path_rule("src/auth/jwt_provider.py")
    assert rule is not None
    assert rule["customer_impact"] >= 90.0
    assert rule["domain_tag"] == "auth"

    rule = BusinessRulesEngine.match_path_rule("src/tests/unit/test_calc.py")
    assert rule is not None
    assert rule["business_criticality"] <= 25.0
    assert rule["domain_tag"] == "testing"

    # Unmatched fallback
    rule = BusinessRulesEngine.match_path_rule("src/other/misc_worker.py")
    assert rule is None


def test_business_rules_application_to_repo(db_session):
    """
    Verifies applying path-pattern rules to all files in a repository.
    """
    repo = DataService.get_or_create_repository(
        db_session, RepositoryCreate(name="rules-repo", url="https://github.com/rules/test.git")
    )
    f1 = DataService.get_or_create_file(
        db_session,
        SourceFileCreate(repository_id=repo.id, file_path="src/payments/billing.py", file_name="billing.py", language="Python", lines_of_code=200)
    )
    f2 = DataService.get_or_create_file(
        db_session,
        SourceFileCreate(repository_id=repo.id, file_path="tests/test_billing.py", file_name="test_billing.py", language="Python", lines_of_code=50)
    )

    updated_count = BusinessRulesEngine.apply_rules_to_repository(db_session, repo.id)
    assert updated_count == 2

    # Verify f1 was updated with payment domain
    ctx1 = db_session.query(BusinessContext).filter(BusinessContext.file_id == f1.id).first()
    assert ctx1 is not None
    assert ctx1.business_criticality >= 90.0
    assert ctx1.domain_tag == "payment"

    # Verify f2 was updated with testing domain
    ctx2 = db_session.query(BusinessContext).filter(BusinessContext.file_id == f2.id).first()
    assert ctx2 is not None
    assert ctx2.business_criticality <= 25.0
    assert ctx2.domain_tag == "testing"


def test_provenance_honesty_and_technical_only_labeling(db_session):
    """
    Verifies Item 3 provenance rules:
    1. DEFAULT / DEFAULT_RULE business inputs enter score but are labeled:
       'technical-only (business context not configured)'
    2. Simulated data is tagged SIMULATED and excluded from confidence boost.
    3. User-defined rules or live integrations show genuine coverage without disclaimer.
    """
    repo = DataService.get_or_create_repository(
        db_session, RepositoryCreate(name="prov-repo", url="https://github.com/prov/test.git")
    )
    f_default = DataService.get_or_create_file(
        db_session,
        SourceFileCreate(repository_id=repo.id, file_path="src/utils/calc.py", file_name="calc.py", language="Python", lines_of_code=100)
    )
    DataService.ingest_engineering_metric(
        db_session,
        EngineeringMetricCreate(file_id=f_default.id, cyclomatic_complexity=10.0, technical_risk_score=50.0)
    )
    # 1. Default provenance
    BusinessService.get_or_create_business_context(
        db_session,
        BusinessContextCreate(file_id=f_default.id, business_criticality=50.0)
    )
    score_def = PriorityService.calculate_file_priority(db_session, f_default.id)
    assert "technical-only (business context not configured)" in score_def.dimension_coverage

    # 2. DEFAULT_RULE provenance
    ctx = db_session.query(BusinessContext).filter(BusinessContext.file_id == f_default.id).first()
    ctx.provenance = "DEFAULT_RULE"
    db_session.commit()
    score_rule = PriorityService.calculate_file_priority(db_session, f_default.id)
    assert "technical-only (business context not configured)" in score_rule.dimension_coverage

    # 3. Genuine INTEGRATION provenance
    ctx.provenance = "INTEGRATION"
    db_session.commit()
    score_integ = PriorityService.calculate_file_priority(db_session, f_default.id)
    assert "technical-only" not in score_integ.dimension_coverage
    assert "of 5 dimensions" in score_integ.dimension_coverage

    # 4. SIMULATED provenance
    ctx.provenance = "SIMULATED"
    db_session.commit()
    score_sim = PriorityService.calculate_file_priority(db_session, f_default.id)
    assert "simulated data, excluded from confidence" in score_sim.dimension_coverage

