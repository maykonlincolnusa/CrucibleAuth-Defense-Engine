from datetime import datetime, timedelta, timezone
import random

from locust import HttpUser, between, task


class SecurityLabUser(HttpUser):
    wait_time = between(0.2, 1.2)

    def on_start(self):
        username = f"loaduser_{random.randint(10_000, 99_999)}"
        self.username = username
        self.password = "LoadUser123!"
        self.client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": f"{username}@load.local",
                "password": self.password,
            },
        )

    @task(4)
    def login(self):
        self.client.post(
            "/api/v1/auth/login",
            json={
                "username": self.username,
                "password": self.password,
                "source_ip": f"10.10.{random.randint(1, 30)}.{random.randint(1, 240)}",
                "user_agent": "locust load test",
                "latency_ms": random.uniform(20, 900),
            },
        )

    @task(2)
    def send_network(self):
        self.client.post(
            "/api/v1/telemetry/network/stream",
            json={
                "source_ip": f"172.16.{random.randint(1, 30)}.{random.randint(1, 240)}",
                "destination_ip": "192.168.1.20",
                "protocol": random.choice(["tcp", "udp"]),
                "bytes_in": random.randint(100, 9000),
                "bytes_out": random.randint(100, 9000),
                "packets": random.randint(5, 200),
                "duration_ms": random.uniform(1.0, 1500.0),
                "tcp_flags": {"SYN": random.randint(0, 5), "ACK": random.randint(1, 10)},
            },
        )

    @task(1)
    def send_timeseries(self):
        now = datetime.now(timezone.utc)
        self.client.post(
            "/api/v1/telemetry/timeseries",
            json={
                "metric_name": "login_failures_15m",
                "metric_value": random.randint(0, 10),
                "window_start": (now - timedelta(minutes=15)).isoformat(),
                "window_end": now.isoformat(),
            },
        )

    @task(1)
    def monitoring(self):
        self.client.get("/api/v1/monitoring/overview?hours=24")
        self.client.get("/api/v1/monitoring/timeseries?hours=24")
