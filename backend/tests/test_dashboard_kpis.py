"""Dashboard summary returns real KPIs computed from the workspace, and no invented trend."""


def test_dashboard_kpis_from_real_data(seeded_client):
    res = seeded_client.get("/api/v1/metrics/dashboard")
    assert res.status_code == 200
    body = res.json()

    kpis = body["kpis"]
    assert kpis["files_analyzed"] > 0
    assert 0 <= kpis["quick_wins"] <= kpis["files_analyzed"]
    assert 0.0 <= kpis["avg_defect_risk_pct"] <= 100.0
    assert 0 <= kpis["complex_files"] <= kpis["files_analyzed"]
    assert body["risk_trend"] == []
    assert all(c["value"] > 0 for c in body["debt_categories"])
