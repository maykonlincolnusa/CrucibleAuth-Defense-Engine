from datetime import datetime, timedelta, timezone
import random

from app.core.security import hash_password
from app.db.init_db import init_db
from app.db.models import AttackSequenceEvent, LoginEvent, NetworkFlow, TimeSeriesPoint, User
from app.db.session import SessionLocal


def run() -> None:
    init_db()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "demo").first()
        if not user:
            user = User(
                username="demo",
                email="demo@security.local",
                password_hash=hash_password("Demo123!"),
                role="analyst",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        for i in range(300):
            failed = random.random() < 0.25
            db.add(
                LoginEvent(
                    user_id=user.id,
                    source_ip=f"10.0.0.{random.randint(1, 240)}",
                    user_agent=random.choice(
                        [
                            "Mozilla/5.0",
                            "python-requests/2.31",
                            "hydra/9.5 brute-force",
                            "sqlmap/1.8 tamper chain",
                        ]
                    ),
                    success=not failed,
                    latency_ms=float(random.uniform(40, 1800)),
                    risk_score=float(random.uniform(0.1, 0.95)),
                    anomaly_flag=failed,
                    context={
                        "feature_vector": [
                            random.randint(0, 20),
                            random.random(),
                            random.randint(0, 1),
                            random.random(),
                            random.random(),
                            random.random(),
                        ]
                    },
                    created_at=now - timedelta(minutes=i),
                )
            )

            db.add(
                NetworkFlow(
                    user_id=user.id,
                    source_ip=f"172.16.1.{random.randint(1, 240)}",
                    destination_ip="192.168.10.5",
                    protocol=random.choice(["tcp", "udp", "icmp"]),
                    bytes_in=random.randint(50, 40_000),
                    bytes_out=random.randint(50, 60_000),
                    packets=random.randint(1, 1200),
                    duration_ms=float(random.uniform(1, 10_000)),
                    tcp_flags={"SYN": random.randint(0, 20), "ACK": random.randint(0, 20)},
                    anomaly_score=float(random.uniform(0.0, 1.0)),
                    anomaly_flag=random.random() > 0.8,
                    created_at=now - timedelta(minutes=i),
                )
            )

            db.add(
                TimeSeriesPoint(
                    user_id=user.id,
                    metric_name="login_failures_15m",
                    metric_value=float(random.randint(0, 25)),
                    window_start=now - timedelta(minutes=i + 15),
                    window_end=now - timedelta(minutes=i),
                    created_at=now - timedelta(minutes=i),
                )
            )

            db.add(
                TimeSeriesPoint(
                    user_id=user.id,
                    metric_name="packets_rate",
                    metric_value=float(random.randint(10, 1200)),
                    window_start=now - timedelta(minutes=i + 5),
                    window_end=now - timedelta(minutes=i),
                    created_at=now - timedelta(minutes=i),
                )
            )

        sequences = [
            ["sqlmap", "tamper", "union", "select"],
            ["hydra", "ssh", "password", "spray"],
            ["botnet", "rotate-ip", "credential", "stuffing"],
            ["xss", "payload", "obfuscation", "mutation"],
        ]
        for i in range(120):
            seq = random.choice(sequences)
            db.add(
                AttackSequenceEvent(
                    attack_family=seq[0],
                    signature=" ".join(seq),
                    tokens=seq,
                    embedding_hint=[random.random() for _ in range(8)],
                    risk_score=float(random.uniform(0.2, 0.95)),
                    created_at=now - timedelta(minutes=i),
                )
            )

        db.commit()
        print("Synthetic data loaded.")


if __name__ == "__main__":
    run()
