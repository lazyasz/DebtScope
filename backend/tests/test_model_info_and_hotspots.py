"""Real model facts and measured hotspot metrics are exposed (the UI used to invent them)."""


def test_model_info_reports_the_scanning_model(seeded_client):
    res = seeded_client.get("/api/v1/predictions/model-info")
    assert res.status_code == 200
    info = res.json()
    assert info["algorithm"] == "RandomForestRegressor"
    assert info["n_estimators"] > 0
    assert 0 < info["r2"] < 1
    imps = [f["importance"] for f in info["features"]]
    assert imps == sorted(imps, reverse=True)
    assert abs(sum(imps) - 1.0) < 0.01


def test_hotspots_include_measured_metrics(seeded_client):
    hotspots = seeded_client.get("/api/v1/hotspots").json()
    assert hotspots, "seeded demo data should produce hotspots"
    for key in ("lines_of_code", "cyclomatic_complexity", "duplication_pct", "churn_commits"):
        assert key in hotspots[0]


def test_production_requires_sign_in_for_data(client, monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DEV_SANDBOX_AUTH", False)
    assert client.get("/api/v1/repositories").status_code == 401
    assert client.get("/health").status_code == 200


def test_file_detail_includes_measured_metrics(seeded_client):
    file_id = seeded_client.get("/api/v1/priorities").json()[0]["file_id"]
    detail = seeded_client.get(f"/api/v1/files/{file_id}").json()
    assert detail["lines_of_code"] > 0
    assert detail["cyclomatic_complexity"] is not None
