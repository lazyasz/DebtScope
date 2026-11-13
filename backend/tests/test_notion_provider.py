"""
Unit & Integration Tests for Notion Workspace Integration (Phase 5).
Tests OAuth 2.0 flow, Service Criticality Database ingestion,
Executive Audit Report publishing, and Copilot Notion tools.
"""

import pytest
import asyncio
from backend.integrations.notion_provider import NotionProvider
from backend.services.notion_service import (
    sync_backlog_to_notion,
    create_notion_audit_report,
    ingest_service_criticality_from_notion,
)
from backend.services.business_rules_service import BusinessRulesEngine
from backend.services.copilot_tools import CopilotToolRegistry
from backend.database.models import (
    Workspace,
    Repository,
    SourceFile,
    BusinessContext,
    PriorityScore,
    EngineeringMetric,
    MLPrediction,
    NotionReport,
)


@pytest.fixture
def notion_provider():
    return NotionProvider()


def test_notion_auth_url_generation(notion_provider):
    """Verifies Notion OAuth 2.0 authorization URL generation."""
    url = notion_provider.get_authorization_url(state="notion_state_456")
    assert "state=notion_state_456" in url
    assert "notion" in url


def test_notion_exchange_code_sandbox(notion_provider):
    """Tests code exchange in sandbox mode returns mock access token and workspace info."""
    res = asyncio.run(notion_provider.exchange_code("notion_mock_auth_code_2026"))
    assert "access_token" in res
    assert "workspace_name" in res
    assert res["workspace_name"] == "DebtScope Engineering Workspace"


def test_notion_sync_backlog_sandbox():
    """Tests synchronizing debt components to Notion database."""
    components = [
        {
            "component_name": "services/auth/token.go",
            "priority_score": 85.0,
            "remediation_effort_hours": 10.0,
            "roi_quadrant": "Quick Wins",
            "technical_risk": 88.0,
        }
    ]
    res = asyncio.run(sync_backlog_to_notion(components))
    assert res["status"] == "success"
    assert res["synced_count"] == 1
    assert "notion_url" in res


def test_notion_create_audit_report_sandbox():
    """Tests creating an executive audit report."""
    summary = {
        "title": "Boardroom Technical Debt Briefing — Q4",
        "total_components": 85,
        "avg_priority_score": 62.4,
        "quick_wins_count": 18,
        "critical_hotspots_count": 9,
    }
    res = asyncio.run(create_notion_audit_report(summary))
    assert res["status"] == "success"
    assert "report_id" in res
    assert "notion_url" in res
    assert res["title"] == "Boardroom Technical Debt Briefing — Q4"


def test_notion_ingest_service_criticality_sandbox(notion_provider):
    """Tests ingesting service criticality tiers from Notion."""
    res = asyncio.run(notion_provider.ingest_criticality())
    assert res["status"] == "success"
    assert res["rules_count"] >= 3
    rules = res["rules"]
    payment_rule = next(r for r in rules if "payment" in r["service_name"].lower())
    assert payment_rule["business_criticality"] >= 95.0
    assert "Tier 1" in payment_rule["tier"]


def test_notion_service_criticality_applied_to_repository(db_session, notion_provider):
    """Tests applying ingested Notion service criticality rules to repository files."""
    ws = Workspace(id="ws_notion_test", name="Notion Test WS", slug="notion-test")
    db_session.add(ws)
    repo = Repository(workspace_id="ws_notion_test", name="notion-repo")
    db_session.add(repo)
    db_session.commit()

    f = SourceFile(
        workspace_id="ws_notion_test",
        repository_id=repo.id,
        file_path="src/payment_gateway/checkout.py",
        file_name="checkout.py",
        language="Python",
    )
    db_session.add(f)
    db_session.commit()

    bctx = BusinessContext(
        workspace_id="ws_notion_test",
        file_id=f.id,
        business_criticality=50.0,
        customer_impact=50.0,
        provenance="DEFAULT",
    )
    db_session.add(bctx)
    db_session.commit()

    # Ingest rules from Notion
    crit_data = asyncio.run(notion_provider.ingest_criticality())
    rules = crit_data["rules"]

    updated_count = BusinessRulesEngine.apply_rules_to_repository(
        db_session, repository_id=repo.id, custom_rules=rules
    )
    assert updated_count == 1

    db_session.refresh(bctx)
    assert bctx.business_criticality >= 95.0
    assert bctx.domain_tag == "payment"
    assert bctx.provenance == "USER_RULE"


def test_copilot_notion_tool(db_session):
    """Tests export_notion_report inside CopilotToolRegistry."""
    ws = Workspace(id="ws_copilot_notion", name="Copilot Notion WS", slug="copilot-notion")
    db_session.add(ws)
    repo = Repository(workspace_id="ws_copilot_notion", name="copilot-repo-notion")
    db_session.add(repo)
    db_session.commit()

    registry = CopilotToolRegistry(db=db_session, workspace_id="ws_copilot_notion", repository_id=repo.id)

    res = registry.export_notion_report(title="Sprint 24 Executive Audit")
    assert res["status"] == "success"
    assert "report_id" in res

    # Verify NotionReport record created
    report = db_session.query(NotionReport).filter(NotionReport.workspace_id == "ws_copilot_notion").first()
    assert report is not None
    assert report.title == "Sprint 24 Executive Audit"
    assert report.export_status == "COMPLETED"
