def test_auto_retrain_disabled_by_default_in_tests(client):
    response = client.post("/api/v1/models/auto-retrain")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "disabled"
