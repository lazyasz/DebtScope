"""
Unit & Integration Tests for Atlassian Jira Cloud Integration (Phase 4).
Tests OAuth 2.0 (3LO) lifecycle, commit regex parsing, 5D business signal calculation,
ticket write-back, and Copilot Jira tools.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from backend.config import settings
from backend.integrations.jira_provider import JiraProvider
from backend.services.jira_service import (
    parse_jira_keys_from_commit,
    derive_jira_business_signals,
    create_jira_issue,
    bulk_export_to_jira,
)
from backend.services.copilot_tools import CopilotToolRegistry
from backend.database.models import (
    Workspace,
    Repository,
    SourceFile,
    BusinessContext,
    PriorityScore,
    EngineeringMetric,
    MLPrediction,
    JiraIssueLink,
)


@pytest.fixture
def jira_provider():
    return JiraProvider()


def test_jira_auth_url_generation(jira_provider):
    """Verifies OAuth 2.0 (3LO) authorization URL generation."""
    url = jira_provider.get_authorization_url(state="test_state_123")
    assert "state=test_state_123" in url
    assert "jira" in url


def test_jira_exchange_code_sandbox(jira_provider, monkeypatch):
    """Tests exchanging code in sandbox mode returns simulated access and refresh tokens."""
    monkeypatch.setattr(settings, "JIRA_SIMULATION_MODE", True)
    res = asyncio.run(jira_provider.exchange_code("jira_mock_auth_code_2026"))
    assert "access_token" in res
    assert "refresh_token" in res
    assert res["expires_in"] == 3600
    assert "user" in res
    assert res["user"]["name"] == "Dhruv Patel"


def test_jira_token_refresh(jira_provider):
    """Tests token refresh lifecycle."""
    res = asyncio.run(jira_provider.refresh_token("jira_mock_refresh_token_99182371"))
    assert "access_token" in res
    assert "refresh_token" in res
    assert res["expires_in"] == 3600


def test_parse_jira_keys_from_commit():
    """Tests extracting Jira issue keys from git commit messages."""
    msg1 = "feat(auth): add PKCE challenge verification [DEBT-101]"
    assert parse_jira_keys_from_commit(msg1) == ["DEBT-101"]

    msg2 = "fix(pay): resolve concurrency deadlock PAY-42 and CORE-88"
    assert parse_jira_keys_from_commit(msg2) == ["PAY-42", "CORE-88"]

    msg3 = "chore: bump dependencies"
    assert parse_jira_keys_from_commit(msg3) == []


def test_derive_jira_business_signals_empty():
    """Empty issue list returns safe defaults."""
    signals = derive_jira_business_signals([])
    assert signals["customer_impact"] == 50.0
    assert signals["sprint_urgency"] == 25.0
    assert signals["provenance"] == "DEFAULT"
    assert signals["open_bugs_count"] == 0


def test_derive_jira_business_signals_critical_bug():
    """Active sprint bug with highest severity produces high urgency and customer impact."""
    issues = [
        {
            "key": "PAY-42",
            "issue_type": "Bug",
            "priority": "Highest",
            "status": "In Progress",
            "is_bug": True,
            "sprint_state": "ACTIVE",
            "fix_version": "v2.3.9",
            "fix_version_date": datetime.now(timezone.utc) + timedelta(days=5),
        }
    ]
    signals = derive_jira_business_signals(issues)
    assert signals["customer_impact"] >= 95.0
    assert signals["sprint_urgency"] == 90.0
    assert signals["release_proximity"] == 95.0
    assert signals["provenance"] == "INTEGRATION"
    assert signals["has_active_sprint"] is True


def test_derive_jira_business_signals_future_task():
    """Future sprint task yields lower urgency and medium customer impact."""
    issues = [
        {
            "key": "CORE-88",
            "issue_type": "Task",
            "priority": "Medium",
            "status": "Open",
            "is_bug": False,
            "sprint_state": "FUTURE",
            "fix_version": "v2.5.0",
        }
    ]
    signals = derive_jira_business_signals(issues)
    assert signals["customer_impact"] < 60.0
    assert signals["sprint_urgency"] == 55.0
    assert signals["provenance"] == "INTEGRATION"
    assert signals["has_active_sprint"] is False


def test_create_jira_issue_sandbox(monkeypatch):
    """Tests creating a single refactoring ticket."""
    monkeypatch.setattr(settings, "JIRA_SIMULATION_MODE", True)
    data = {
        "component_name": "backend/services/payment.py",
        "priority_score": 88.5,
        "remediation_effort_hours": 16.0,
        "technical_risk": 90.0,
        "business_impact": 85.0,
        "roi_quadrant": "Strategic Refactor",
        "summary": "Refactor Payment Router",
        "issue_type": "Task"
    }
    res = asyncio.run(create_jira_issue(data))
    assert res["status"] == "success"
    assert "issue_key" in res
    assert "issue_url" in res
    assert res["priority"] == "Highest"
    assert res["story_points"] == 3


def test_bulk_export_to_jira_sandbox(monkeypatch):
    """Tests bulk exporting components to a sprint backlog."""
    monkeypatch.setattr(settings, "JIRA_SIMULATION_MODE", True)
    components = [
        {"component_name": "file_a.py", "priority_score": 92.0, "remediation_effort_hours": 8.0},
        {"component_name": "file_b.py", "priority_score": 65.0, "remediation_effort_hours": 4.0},
    ]
    res = asyncio.run(bulk_export_to_jira(components, sprint_name="Sprint 25"))
    assert res["status"] == "success"
    assert res["total_tickets_created"] == 2
    assert res["total_story_points"] == 3  # 2 + 1


def test_sync_mined_jira_links(db_session, jira_provider, monkeypatch):
    """Tests syncing mined commit links updates BusinessContext and priority scores."""
    monkeypatch.setattr(settings, "JIRA_SIMULATION_MODE", True)
    ws = Workspace(id="ws_jira_test", name="Jira Workspace", slug="jira-test")
    db_session.add(ws)
    repo = Repository(workspace_id="ws_jira_test", name="jira-repo")
    db_session.add(repo)
    db_session.commit()

    f = SourceFile(
        workspace_id="ws_jira_test",
        repository_id=repo.id,
        file_path="src/billing.py",
        file_name="billing.py",
        language="Python",
    )
    db_session.add(f)
    db_session.commit()

    bctx = BusinessContext(
        workspace_id="ws_jira_test",
        file_id=f.id,
        business_criticality=50.0,
        customer_impact=50.0,
        sprint_urgency=20.0,
        release_proximity=40.0,
        provenance="DEFAULT",
    )
    metric = EngineeringMetric(
        workspace_id="ws_jira_test",
        file_id=f.id,
        cyclomatic_complexity=15.0,
        test_coverage_pct=60.0,
        technical_risk_score=75.0,
    )
    pred = MLPrediction(
        workspace_id="ws_jira_test",
        file_id=f.id,
        predicted_future_risk=70.0,
        defect_probability=0.55,
    )
    db_session.add_all([bctx, metric, pred])
    db_session.commit()

    mined_commits = [
        {
            "commit_hash": "c101",
            "jira_keys": ["DEBT-101"],
            "files": ["src/billing.py"],
        }
    ]

    res = asyncio.run(jira_provider.sync_mined_jira_links(
        db=db_session,
        workspace_id="ws_jira_test",
        repo_id=repo.id,
        commit_links=mined_commits,
    ))
    assert res["status"] == "success"
    assert res["linked_records_created"] >= 1
    assert res["files_with_jira_signals"] == 1

    # Verify BusinessContext updated
    db_session.refresh(bctx)
    assert bctx.provenance == "INTEGRATION"
    assert bctx.sprint_urgency == 90.0
    assert bctx.customer_impact >= 95.0


def test_copilot_jira_tools(db_session, monkeypatch):
    """Tests create_jira_issue and search_jira_issues inside CopilotToolRegistry."""
    monkeypatch.setattr(settings, "JIRA_SIMULATION_MODE", True)
    ws = Workspace(id="ws_copilot_jira", name="Copilot Jira WS", slug="copilot-jira")
    db_session.add(ws)
    repo = Repository(workspace_id="ws_copilot_jira", name="copilot-repo")
    db_session.add(repo)
    db_session.commit()

    f = SourceFile(
        workspace_id="ws_copilot_jira",
        repository_id=repo.id,
        file_path="src/gateway.py",
        file_name="gateway.py",
        language="Python",
    )
    db_session.add(f)
    db_session.commit()

    registry = CopilotToolRegistry(db=db_session, workspace_id="ws_copilot_jira", repository_id=repo.id, user_id="usr_copilot")

    # 1. Create Jira issue via Copilot tool returns single-use staged action
    create_res = registry.create_jira_issue(
        file_path_or_id="src/gateway.py",
        summary="Refactor gateway timeout handler",
        issue_type="Task"
    )
    assert create_res.get("action_required") == "CONFIRMATION_REQUIRED"
    action_id = create_res["action_id"]

    # 2. Confirm and execute staged action via server endpoint helper
    exec_res = CopilotToolRegistry.execute_confirmed_action(
        db=db_session,
        action_id=action_id,
        user_id="usr_copilot",
        workspace_id="ws_copilot_jira"
    )
    assert exec_res["status"] == "success"
    assert "issue_key" in exec_res["result"]

    # 3. Search Jira issues via Copilot tool
    search_res = registry.search_jira_issues(file_path_or_id="src/gateway.py")
    assert search_res["total_count"] >= 1
    assert search_res["issues"][0]["issue_key"] == exec_res["result"]["issue_key"]


def test_parse_jira_keys_rejects_cve_sha_utf8_rfc():
    """
    Verifies that parse_jira_keys_from_commit strictly rejects false positive patterns:
    CVE-2023-1234, SHA-256, UTF-8, RFC-2616, ISO-8601, and non-ASCII spoofing.
    """
    from backend.services.jira_service import parse_jira_keys_from_commit

    commit_msg = (
        "fix: resolve vulnerability CVE-2023-9999 and update hashing to SHA-256\n\n"
        "Encode payload in UTF-8 according to RFC-2616 and ISO-8601 spec.\n"
        "Resolves ticket DEBT-404 and PAY-12 successfully."
    )
    keys = parse_jira_keys_from_commit(commit_msg)

    # Valid Jira issue keys MUST be extracted
    assert "DEBT-404" in keys
    assert "PAY-12" in keys

    # False positive technical standards MUST be excluded
    assert "CVE-2023" not in keys
    assert "SHA-256" not in keys
    assert "UTF-8" not in keys
    assert "RFC-2616" not in keys
    assert "ISO-8601" not in keys


def test_parse_jira_keys_validates_connected_site_project_keys():
    """Verifies that extracted keys are filtered against connected site project keys."""
    from backend.services.jira_service import parse_jira_keys_from_commit

    commit_msg = "feat: add webhook integration for DEBT-101 and external UNKNOWN-42"
    connected_site_keys = {"DEBT", "CORE", "PAY"}

    # With connected site whitelist:
    validated_keys = parse_jira_keys_from_commit(commit_msg, allowed_project_keys=connected_site_keys)
    assert validated_keys == ["DEBT-101"]
    assert "UNKNOWN-42" not in validated_keys


def test_derive_jira_business_signals_dynamic_release_proximity():
    """
    Verifies release proximity is dynamically computed from fix_version target dates,
    not hardcoded assumptions.
    """
    from datetime import datetime, timezone, timedelta
    from backend.services.jira_service import derive_jira_business_signals

    now = datetime.now(timezone.utc)

    # 1. Imminent release (within 5 days) -> 95.0
    signals_urgent = derive_jira_business_signals([
        {
            "fix_version": "v1.0-gold",
            "fix_version_date": now + timedelta(days=5),
            "status": "In Progress",
            "sprint_state": "ACTIVE",
            "priority": "Highest",
            "is_bug": True,
        }
    ])
    assert signals_urgent["release_proximity"] == 95.0
    assert signals_urgent["sprint_urgency"] == 90.0

    # 2. Distant release (within 45 days) -> 50.0
    signals_distant = derive_jira_business_signals([
        {
            "fix_version": "v2.0-roadmap",
            "fix_version_date": now + timedelta(days=45),
            "status": "Open",
            "sprint_state": "FUTURE",
            "priority": "Medium",
        }
    ])
    assert signals_distant["release_proximity"] == 50.0
    assert signals_distant["sprint_urgency"] == 55.0


def test_simulation_isolation_refuses_fixtures_outside_simulation_mode(monkeypatch):
    """
    Amendment A: With Jira not connected and JIRA_SIMULATION_MODE=False:
    1. Direct call to fetch_or_simulate_issue MUST raise RuntimeError.
    2. Git commit parsing skips key extraction (zero Jira keys extracted).
    3. No fixture data can reach business context or priority score.
    """
    from backend.config import settings
    from backend.integrations.jira_provider import JiraProvider
    from backend.services.git_miner import GitMiner

    monkeypatch.setattr(settings, "JIRA_SIMULATION_MODE", False)
    provider = JiraProvider()
    monkeypatch.setattr(provider, "is_live_configured", lambda: False)

    # 1. Direct call to fetch_or_simulate_issue raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        provider.fetch_or_simulate_issue("DEBT-101")
    assert "JIRA_SIMULATION_MODE is False" in str(exc_info.value)

    # 2. GitMiner skips commit-key extraction when Jira is disabled
    miner = GitMiner(repo_dir=".")
    assert miner._is_jira_enabled() is False

    # 3. Simulate parsing commits - even if commit message has [DEBT-999], zero keys extracted
    sample_log = "COMMIT_SEP|abc1234|Dev|1700000000|feat(core): fix login crash [DEBT-999]\n10\t2\tsrc/core/login.py"
    monkeypatch.setattr(miner, "_run_git", lambda *a, **kw: sample_log)
    stats = miner.mine_file_history()
    assert "src/core/login.py" in stats
    assert stats["src/core/login.py"]["jira_keys"] == []

    # 4. mine_jira_commit_links returns empty list immediately
    assert miner.mine_jira_commit_links() == []


