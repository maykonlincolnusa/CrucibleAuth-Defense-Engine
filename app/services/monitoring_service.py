from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import mean

import numpy as np
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.models import (
    AttackSequenceEvent,
    DefenseAction,
    LoginEvent,
    ModelArtifact,
    NetworkFlow,
    User,
)
from app.observability.metrics import DQN_EPSILON, PIPELINE_MODEL_READY
from app.services.state import get_pipeline


def _normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
        self.block_actions = {"TEMP_BLOCK", "PERM_BLOCK", "RATE_LIMIT", "HONEYPOT_REDIRECT"}

    @staticmethod
    def _percentile(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        return float(np.percentile(np.array(values, dtype=np.float32), q))

    def overview(self, hours: int = 24) -> dict:
        pipeline = get_pipeline()
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=max(1, min(hours, 168)))

        login_events = self.db.query(LoginEvent).filter(LoginEvent.created_at >= since).all()
        network_events = self.db.query(NetworkFlow).filter(NetworkFlow.created_at >= since).all()
        defense_actions = self.db.query(DefenseAction).filter(DefenseAction.created_at >= since).all()
        active_models = (
            self.db.query(ModelArtifact).filter(ModelArtifact.is_active.is_(True)).count()
        )

        total_logins = len(login_events)
        login_successes = sum(1 for e in login_events if bool(e.success))
        login_anomalies = sum(1 for e in login_events if bool(e.anomaly_flag))
        login_risks = [float(e.risk_score or 0.0) for e in login_events]
        latencies = [float(e.latency_ms or 0.0) for e in login_events]

        total_network = len(network_events)
        network_anomalies = sum(1 for e in network_events if bool(e.anomaly_flag))
        network_scores = [float(e.anomaly_score or 0.0) for e in network_events]

        action_counter = Counter(str(a.action.value) for a in defense_actions)
        blocked_actions = sum(action_counter.get(name, 0) for name in self.block_actions)

        success_rate = (login_successes / total_logins * 100.0) if total_logins else 0.0
        login_anomaly_rate = (login_anomalies / total_logins * 100.0) if total_logins else 0.0
        network_anomaly_rate = (network_anomalies / total_network * 100.0) if total_network else 0.0
        block_rate = (blocked_actions / len(defense_actions) * 100.0) if defense_actions else 0.0

        model_health = {
            "isolation_forest": pipeline.isolation_forest.fitted,
            "one_class_svm": pipeline.one_class_svm.fitted,
            "lstm_gru": pipeline.lstm_gru.fitted,
            "transformer": pipeline.transformer.fitted,
            "rnn_markov_embeddings": pipeline.hybrid_seq.fitted,
            "dqn_epsilon": float(pipeline.dqn.epsilon),
            "dqn_memory_size": int(len(pipeline.dqn.memory)),
        }
        PIPELINE_MODEL_READY.labels(model="isolation_forest").set(1 if model_health["isolation_forest"] else 0)
        PIPELINE_MODEL_READY.labels(model="one_class_svm").set(1 if model_health["one_class_svm"] else 0)
        PIPELINE_MODEL_READY.labels(model="lstm_gru").set(1 if model_health["lstm_gru"] else 0)
        PIPELINE_MODEL_READY.labels(model="transformer").set(1 if model_health["transformer"] else 0)
        PIPELINE_MODEL_READY.labels(model="rnn_markov_embeddings").set(
            1 if model_health["rnn_markov_embeddings"] else 0
        )
        DQN_EPSILON.set(model_health["dqn_epsilon"])
        trained_count = sum(
            1 for key, value in model_health.items() if key not in {"dqn_epsilon", "dqn_memory_size"} and value
        )
        model_health["status"] = "ready" if trained_count >= 4 else "learning"

        return {
            "window_hours": hours,
            "collected_at": now.isoformat(),
            "kpis": {
                "total_logins": total_logins,
                "login_success_rate": round(success_rate, 2),
                "login_anomaly_rate": round(login_anomaly_rate, 2),
                "avg_login_risk": round(mean(login_risks), 4) if login_risks else 0.0,
                "p95_login_risk": round(self._percentile(login_risks, 95), 4),
                "avg_login_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
                "p95_login_latency_ms": round(self._percentile(latencies, 95), 2),
                "total_network_flows": total_network,
                "network_anomaly_rate": round(network_anomaly_rate, 2),
                "avg_network_anomaly_score": round(mean(network_scores), 4) if network_scores else 0.0,
                "defense_block_rate": round(block_rate, 2),
                "blocked_actions": blocked_actions,
                "active_models": active_models,
            },
            "actions_distribution": dict(action_counter),
            "model_health": model_health,
        }

    def timeseries(self, hours: int = 24) -> dict:
        now = datetime.now(timezone.utc)
        hours = max(1, min(hours, 168))
        since = now - timedelta(hours=hours)

        start_hour = since.replace(minute=0, second=0, microsecond=0)
        end_hour = now.replace(minute=0, second=0, microsecond=0)
        buckets: dict[datetime, dict] = {}
        current = start_hour
        while current <= end_hour:
            buckets[current] = {
                "timestamp": current.isoformat(),
                "login_volume": 0,
                "avg_login_risk": 0.0,
                "blocked_attempts": 0,
                "network_anomalies": 0,
                "_risk_sum": 0.0,
            }
            current += timedelta(hours=1)

        login_events = self.db.query(LoginEvent).filter(LoginEvent.created_at >= since).all()
        defense_actions = self.db.query(DefenseAction).filter(DefenseAction.created_at >= since).all()
        network_events = self.db.query(NetworkFlow).filter(NetworkFlow.created_at >= since).all()

        for event in login_events:
            hour_key = _normalize_dt(event.created_at).replace(minute=0, second=0, microsecond=0)
            if hour_key not in buckets:
                continue
            buckets[hour_key]["login_volume"] += 1
            buckets[hour_key]["_risk_sum"] += float(event.risk_score or 0.0)

        for action in defense_actions:
            hour_key = _normalize_dt(action.created_at).replace(minute=0, second=0, microsecond=0)
            if hour_key not in buckets:
                continue
            if str(action.action.value) in self.block_actions:
                buckets[hour_key]["blocked_attempts"] += 1

        for flow in network_events:
            hour_key = _normalize_dt(flow.created_at).replace(minute=0, second=0, microsecond=0)
            if hour_key not in buckets:
                continue
            if bool(flow.anomaly_flag):
                buckets[hour_key]["network_anomalies"] += 1

        points = []
        for key in sorted(buckets.keys()):
            point = buckets[key]
            if point["login_volume"] > 0:
                point["avg_login_risk"] = round(point["_risk_sum"] / point["login_volume"], 4)
            del point["_risk_sum"]
            points.append(point)

        return {"window_hours": hours, "points": points}

    def drilldown(self, hours: int = 24, limit: int = 10) -> dict:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=max(1, min(hours, 168)))
        limit = max(1, min(limit, 50))

        user_rows = (
            self.db.query(
                LoginEvent.user_id,
                User.username,
                func.count(LoginEvent.id).label("attempts"),
                func.avg(LoginEvent.risk_score).label("avg_risk"),
                func.sum(case((LoginEvent.success.is_(False), 1), else_=0)).label("failed"),
            )
            .join(User, User.id == LoginEvent.user_id, isouter=True)
            .filter(LoginEvent.created_at >= since)
            .group_by(LoginEvent.user_id, User.username)
            .order_by(func.avg(LoginEvent.risk_score).desc())
            .limit(limit)
            .all()
        )
        top_users = [
            {
                "user_id": row.user_id,
                "username": row.username or "unknown",
                "attempts": int(row.attempts or 0),
                "failed": int(row.failed or 0),
                "avg_risk": round(float(row.avg_risk or 0.0), 4),
            }
            for row in user_rows
        ]

        ip_rows = (
            self.db.query(
                LoginEvent.source_ip,
                func.count(LoginEvent.id).label("events"),
                func.avg(LoginEvent.risk_score).label("avg_risk"),
                func.sum(case((LoginEvent.anomaly_flag.is_(True), 1), else_=0)).label("anomalies"),
            )
            .filter(LoginEvent.created_at >= since)
            .group_by(LoginEvent.source_ip)
            .order_by(func.count(LoginEvent.id).desc())
            .limit(limit)
            .all()
        )
        top_source_ips = [
            {
                "source_ip": row.source_ip,
                "events": int(row.events or 0),
                "anomalies": int(row.anomalies or 0),
                "avg_risk": round(float(row.avg_risk or 0.0), 4),
            }
            for row in ip_rows
        ]

        signature_rows = (
            self.db.query(
                AttackSequenceEvent.signature,
                AttackSequenceEvent.attack_family,
                func.count(AttackSequenceEvent.id).label("events"),
                func.avg(AttackSequenceEvent.risk_score).label("avg_risk"),
            )
            .filter(AttackSequenceEvent.created_at >= since)
            .group_by(AttackSequenceEvent.signature, AttackSequenceEvent.attack_family)
            .order_by(func.avg(AttackSequenceEvent.risk_score).desc())
            .limit(limit)
            .all()
        )
        top_signatures = [
            {
                "attack_family": row.attack_family,
                "signature": row.signature[:120],
                "events": int(row.events or 0),
                "avg_risk": round(float(row.avg_risk or 0.0), 4),
            }
            for row in signature_rows
        ]

        return {
            "window_hours": hours,
            "collected_at": now.isoformat(),
            "top_users_by_risk": top_users,
            "top_source_ips": top_source_ips,
            "top_attack_signatures": top_signatures,
        }
