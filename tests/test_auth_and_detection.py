from datetime import datetime, timedelta, timezone


def test_register_login_and_telemetry(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "Alice123!",
        },
    )
    assert register.status_code == 201, register.text
    user = register.json()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "alice",
            "password": "Alice123!",
            "source_ip": "10.10.1.5",
            "user_agent": "Mozilla/5.0 test",
            "latency_ms": 140.0,
        },
    )
    assert login.status_code == 200, login.text
    data = login.json()
    assert data["authenticated"] is True
    assert 0.0 <= data["risk_score"] <= 1.0
    assert isinstance(data["action"], str)

    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    end = datetime.now(timezone.utc)
    ts = client.post(
        "/api/v1/telemetry/timeseries",
        json={
            "user_id": user["id"],
            "metric_name": "login_failures_15m",
            "metric_value": 4.0,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
        },
    )
    assert ts.status_code == 202, ts.text

    net = client.post(
        "/api/v1/telemetry/network",
        json={
            "user_id": user["id"],
            "source_ip": "172.16.10.2",
            "destination_ip": "192.168.1.10",
            "protocol": "tcp",
            "bytes_in": 1900,
            "bytes_out": 1500,
            "packets": 60,
            "duration_ms": 180.0,
            "tcp_flags": {"SYN": 2, "ACK": 10},
        },
    )
    assert net.status_code == 200, net.text
    net_data = net.json()
    assert 0.0 <= net_data["anomaly_score"] <= 1.0

    stream = client.post(
        "/api/v1/telemetry/network/stream",
        json={
            "user_id": user["id"],
            "source_ip": "172.16.10.2",
            "destination_ip": "192.168.1.10",
            "protocol": "tcp",
            "bytes_in": 900,
            "bytes_out": 1800,
            "packets": 45,
            "duration_ms": 220.0,
            "tcp_flags": {"SYN": 3, "ACK": 4},
        },
    )
    assert stream.status_code == 202, stream.text
    stream_data = stream.json()
    assert stream_data["accepted"] is True

    summary = client.get(f"/api/v1/defense/risk/{user['id']}")
    assert summary.status_code == 200, summary.text
    summary_data = summary.json()
    assert 0.0 <= summary_data["aggregate_risk"] <= 1.0
