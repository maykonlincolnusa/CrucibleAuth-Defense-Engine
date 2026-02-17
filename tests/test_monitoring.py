def test_monitoring_endpoints(client):
    overview = client.get("/api/v1/monitoring/overview?hours=24")
    assert overview.status_code == 200, overview.text
    payload = overview.json()
    assert "kpis" in payload
    assert "actions_distribution" in payload
    assert "model_health" in payload

    series = client.get("/api/v1/monitoring/timeseries?hours=24")
    assert series.status_code == 200, series.text
    ts = series.json()
    assert "points" in ts
    assert isinstance(ts["points"], list)

    drilldown = client.get("/api/v1/monitoring/drilldown?hours=24&limit=5")
    assert drilldown.status_code == 200, drilldown.text
    dd = drilldown.json()
    assert "top_users_by_risk" in dd
    assert "top_source_ips" in dd
    assert "top_attack_signatures" in dd
