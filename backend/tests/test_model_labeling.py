"""
Tests for Item 5: Model Labeling, Target Identification, Calibration Status,
and Non-Training Language 'Experimental' Flagging.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database.models import Base, Workspace, Repository, SourceFile, EngineeringMetric, BusinessContext, MLPrediction, PriorityScore
from backend.services.priority_service import PriorityService
from backend.schemas.priority import RankedFilePriority, FileDetailResponse


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    ws = Workspace(id="ws_model_test", name="Model Test Workspace", slug="model-test")
    session.add(ws)
    repo = Repository(id=1, workspace_id=ws.id, name="TestRepo", url="https://github.com/org/TestRepo")
    session.add(repo)
    session.commit()

    yield session
    session.close()


def test_model_labeling_experimental_flag_for_languages(db_session):
    """
    Verifies that files written in languages outside the training corpus (Java, C, C++)
    are marked as is_experimental=True and confidence is capped at <= 0.70.
    """
    # 1. Java file (In training corpus)
    java_file = SourceFile(
        id=1, workspace_id="ws_model_test", repository_id=1,
        file_path="src/main/Engine.java", file_name="Engine.java",
        language="Java", lines_of_code=200, file_category="source"
    )
    # 2. Python file (Non-training language -> Experimental)
    py_file = SourceFile(
        id=2, workspace_id="ws_model_test", repository_id=1,
        file_path="src/app.py", file_name="app.py",
        language="Python", lines_of_code=200, file_category="source"
    )
    # 3. JavaScript file (Non-training language -> Experimental)
    js_file = SourceFile(
        id=3, workspace_id="ws_model_test", repository_id=1,
        file_path="src/index.js", file_name="index.js",
        language="JavaScript", lines_of_code=200, file_category="source"
    )
    db_session.add_all([java_file, py_file, js_file])
    db_session.commit()

    for fid, conf in [(1, 0.90), (2, 0.90), (3, 0.90)]:
        pred = MLPrediction(
            workspace_id="ws_model_test", file_id=fid,
            predicted_future_risk=65.0, defect_probability=0.55,
            churn_risk_score=40.0, confidence_score=conf,
            model_version="real-szz-rf-v2.1"
        )
        metric = EngineeringMetric(
            workspace_id="ws_model_test", file_id=fid,
            cyclomatic_complexity=12.0, cognitive_complexity=10.0,
            code_smells_count=2, technical_risk_score=50.0
        )
        bctx = BusinessContext(
            workspace_id="ws_model_test", file_id=fid,
            business_criticality=60.0, customer_impact=50.0,
            module_criticality=55.0, maintenance_cost=40.0,
            estimated_remediation_effort=40.0, provenance="DEFAULT"
        )
        db_session.add_all([pred, metric, bctx])
    db_session.commit()

    PriorityService.analyze_all_files(db_session, 1)

    priorities = PriorityService.get_ranked_priorities(db_session, repo_id=1, category="all")
    p_map = {p.file_id: p for p in priorities}

    # Java: Trained language
    assert p_map[1].is_experimental is False
    assert p_map[1].confidence_score == 0.90
    assert p_map[1].model_calibration_status == "uncalibrated_heuristic"

    # Python: Experimental non-training language
    assert p_map[2].is_experimental is True
    assert p_map[2].confidence_score <= 0.70
    assert p_map[2].model_calibration_status == "uncalibrated_heuristic"

    # JavaScript: Experimental non-training language
    assert p_map[3].is_experimental is True
    assert p_map[3].confidence_score <= 0.70
    assert p_map[3].model_calibration_status == "uncalibrated_heuristic"


def test_file_detail_response_includes_model_labels(db_session):
    """Verifies that the FileDetailResponse API contract exposes model labeling and experimental fields."""
    file_obj = SourceFile(
        id=10, workspace_id="ws_model_test", repository_id=1,
        file_path="lib/server.ts", file_name="server.ts",
        language="TypeScript", lines_of_code=150, file_category="source"
    )
    pred = MLPrediction(
        workspace_id="ws_model_test", file_id=10,
        predicted_future_risk=72.0, defect_probability=0.68,
        churn_risk_score=50.0, confidence_score=0.85,
        model_version="real-szz-rf-v2.1"
    )
    metric = EngineeringMetric(
        workspace_id="ws_model_test", file_id=10,
        cyclomatic_complexity=15.0, cognitive_complexity=12.0,
        code_smells_count=4, technical_risk_score=60.0
    )
    bctx = BusinessContext(
        workspace_id="ws_model_test", file_id=10,
        business_criticality=70.0, customer_impact=65.0,
        module_criticality=70.0, maintenance_cost=50.0,
        estimated_remediation_effort=45.0, provenance="DEFAULT"
    )
    db_session.add_all([file_obj, pred, metric, bctx])
    db_session.commit()

    PriorityService.analyze_all_files(db_session, 1)

    detail = PriorityService.get_file_detail_response(db_session, file_id=10)
    assert detail is not None
    assert detail.is_experimental is True
    assert detail.confidence_score <= 0.70
    assert detail.model_calibration_status == "uncalibrated_heuristic"
    assert detail.defect_probability_label == "relative defect risk (uncalibrated)"
