from sqlalchemy.exc import OperationalError

from app.services.monitoring_service import MonitoringService


def test_monitoring_returns_503_when_db_unavailable(client, monkeypatch):
    def crash(*_, **__):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(MonitoringService, "overview", crash)
    response = client.get("/api/v1/monitoring/overview?hours=24")
    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"
