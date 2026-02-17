from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    AttackSequenceEvent,
    DefenseAction,
    DefenseActionType,
    LoginEvent,
    NetworkFlow,
    TimeSeriesPoint,
    User,
)
from app.observability.metrics import LOGIN_EVENTS_TOTAL, NETWORK_ANOMALIES_TOTAL
from app.schemas.telemetry import AttackSequenceIn, NetworkFlowIn, TimeSeriesPointIn
from app.services.state import get_pipeline


def _to_action_type(action: str) -> DefenseActionType:
    try:
        return DefenseActionType(action)
    except ValueError:
        return DefenseActionType.allow


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    freq = {ch: text.count(ch) for ch in set(text)}
    probs = np.array([v / len(text) for v in freq.values()], dtype=np.float32)
    value = -np.sum(probs * np.log2(probs + 1e-9))
    return float(np.clip(value / 5.0, 0.0, 1.0))


class DefenseOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.pipeline = get_pipeline()

    def _recent_failed_attempts(self, user_id: str | None, minutes: int = 15) -> int:
        if not user_id:
            return 0
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return (
            self.db.query(LoginEvent)
            .filter(
                LoginEvent.user_id == user_id,
                LoginEvent.success.is_(False),
                LoginEvent.created_at >= since,
            )
            .count()
        )

    def _is_new_ip(self, user_id: str | None, source_ip: str) -> int:
        if not user_id:
            return 1
        exists = (
            self.db.query(LoginEvent)
            .filter(LoginEvent.user_id == user_id, LoginEvent.source_ip == source_ip)
            .first()
        )
        return 0 if exists else 1

    def _user_success_rate(self, user_id: str | None) -> float:
        if not user_id:
            return 0.5
        total = self.db.query(LoginEvent).filter(LoginEvent.user_id == user_id).count()
        if total == 0:
            return 0.8
        successes = (
            self.db.query(LoginEvent)
            .filter(LoginEvent.user_id == user_id, LoginEvent.success.is_(True))
            .count()
        )
        return float(successes / total)

    def _recent_metric(self, user_id: str | None, metric_name: str, limit: int = 50) -> list[float]:
        query = self.db.query(TimeSeriesPoint).filter(TimeSeriesPoint.metric_name == metric_name)
        if user_id:
            query = query.filter(TimeSeriesPoint.user_id == user_id)
        points = query.order_by(TimeSeriesPoint.window_end.desc()).limit(limit).all()
        values = [float(p.metric_value) for p in points]
        values.reverse()
        return values

    def evaluate_login(
        self,
        username: str,
        source_ip: str,
        user_agent: str,
        latency_ms: float,
        authenticated: bool,
        user: User | None,
    ) -> dict:
        user_id = user.id if user else None
        now = datetime.now(timezone.utc)

        failed_attempts = self._recent_failed_attempts(user_id)
        new_ip_flag = self._is_new_ip(user_id, source_ip)
        success_rate = self._user_success_rate(user_id)
        hour = now.hour
        ua_entropy = _entropy(user_agent)

        row = self.pipeline.login_features(
            failed_attempts_15m=failed_attempts,
            hour_of_day=hour,
            is_new_ip=new_ip_flag,
            latency_ms=latency_ms,
            user_success_rate=success_rate,
            user_agent_entropy=ua_entropy,
        )

        login_risk, anomaly_flag = self.pipeline.score_login(row)

        observed_fail_rate = float(failed_attempts + (0 if authenticated else 1))
        recent_series = self._recent_metric(user_id, "login_failures_15m")
        temporal_risk = self.pipeline.score_temporal(observed_fail_rate, recent_series)

        mutation_tokens = [token for token in user_agent.lower().split() if token][:10]
        pred_mutation, mutation_risk = self.pipeline.score_mutation(
            mutation_tokens or ["unknown-agent"]
        )

        network_risk = 0.0
        aggregate = self.pipeline.aggregate_risk(
            login_risk=login_risk,
            network_risk=network_risk,
            temporal_risk=temporal_risk,
            mutation_risk=mutation_risk,
        )
        action = self.pipeline.choose_action(
            login_risk=login_risk,
            network_risk=network_risk,
            temporal_risk=temporal_risk,
            mutation_risk=mutation_risk,
            aggregate_risk=aggregate,
        )

        event = LoginEvent(
            user_id=user_id,
            source_ip=source_ip,
            user_agent=user_agent,
            success=authenticated,
            latency_ms=latency_ms,
            risk_score=aggregate,
            anomaly_flag=anomaly_flag,
            context={
                "username": username,
                "login_risk": login_risk,
                "temporal_risk": temporal_risk,
                "mutation_risk": mutation_risk,
                "predicted_mutation": pred_mutation,
                "feature_vector": row.tolist(),
                "recommended_action": action,
            },
        )
        self.db.add(event)
        self.db.flush()

        defense_action = DefenseAction(
            user_id=user_id,
            event_type="LOGIN",
            event_id=str(event.id),
            action=_to_action_type(action),
            reward=0.0,
            decision_context={
                "aggregate_risk": aggregate,
                "authenticated": authenticated,
                "username": username,
            },
        )
        self.db.add(defense_action)
        self.db.commit()

        state = np.array(
            [login_risk, network_risk, temporal_risk, mutation_risk, aggregate], dtype=np.float32
        )
        reward = 0.0
        if authenticated and action in {"ALLOW", "MFA_CHALLENGE"}:
            reward = 1.0 if aggregate < 0.6 else 0.4
        if not authenticated and action in {"TEMP_BLOCK", "PERM_BLOCK", "RATE_LIMIT"}:
            reward = 1.0
        if authenticated and action in {"PERM_BLOCK", "HONEYPOT_REDIRECT"}:
            reward = -0.7
        next_state = np.clip(state + (0.02 if reward > 0 else -0.01), 0.0, 1.0)
        self.pipeline.reinforce(state, action, reward, next_state, done=True)
        LOGIN_EVENTS_TOTAL.labels(result="success" if authenticated else "failed").inc()

        return {
            "risk_score": aggregate,
            "action": action,
            "authenticated": authenticated,
            "event_id": event.id,
        }

    def evaluate_network_flow(self, payload: NetworkFlowIn) -> dict:
        syn = float(payload.tcp_flags.get("SYN", 0))
        syn_ratio = syn / max(float(payload.packets), 1.0)

        row = self.pipeline.network_features(
            bytes_in=payload.bytes_in,
            bytes_out=payload.bytes_out,
            packets=payload.packets,
            duration_ms=payload.duration_ms,
            syn_flag_ratio=syn_ratio,
        )
        network_risk, network_anomaly = self.pipeline.score_network(row)

        recent_packets = self._recent_metric(payload.user_id, "packets_rate")
        temporal_risk = self.pipeline.score_temporal(float(payload.packets), recent_packets)

        seq_tokens = [payload.protocol.lower()] + [k.lower() for k in payload.tcp_flags.keys()]
        pred_mutation, mutation_risk = self.pipeline.score_mutation(seq_tokens)

        latest_login_risk = (
            self.db.query(LoginEvent.risk_score)
            .filter(LoginEvent.user_id == payload.user_id)
            .order_by(LoginEvent.created_at.desc())
            .limit(1)
            .scalar()
        )
        login_risk = float(latest_login_risk or 0.0)

        aggregate = self.pipeline.aggregate_risk(
            login_risk=login_risk,
            network_risk=network_risk,
            temporal_risk=temporal_risk,
            mutation_risk=mutation_risk,
        )
        action = self.pipeline.choose_action(
            login_risk=login_risk,
            network_risk=network_risk,
            temporal_risk=temporal_risk,
            mutation_risk=mutation_risk,
            aggregate_risk=aggregate,
        )

        flow = NetworkFlow(
            user_id=payload.user_id,
            source_ip=payload.source_ip,
            destination_ip=payload.destination_ip,
            protocol=payload.protocol,
            bytes_in=payload.bytes_in,
            bytes_out=payload.bytes_out,
            packets=payload.packets,
            duration_ms=payload.duration_ms,
            tcp_flags=payload.tcp_flags,
            anomaly_score=network_risk,
            anomaly_flag=network_anomaly,
            label=pred_mutation,
        )
        self.db.add(flow)
        self.db.flush()

        defense_action = DefenseAction(
            user_id=payload.user_id,
            event_type="NETWORK_FLOW",
            event_id=str(flow.id),
            action=_to_action_type(action),
            reward=0.0,
            decision_context={"aggregate_risk": aggregate, "network_risk": network_risk},
        )
        self.db.add(defense_action)
        self.db.commit()
        if network_anomaly:
            NETWORK_ANOMALIES_TOTAL.inc()

        return {"anomaly_score": aggregate, "anomaly_flag": network_anomaly, "action": action}

    def ingest_timeseries(self, payload: TimeSeriesPointIn) -> None:
        point = TimeSeriesPoint(
            user_id=payload.user_id,
            metric_name=payload.metric_name,
            metric_value=payload.metric_value,
            window_start=payload.window_start,
            window_end=payload.window_end,
        )
        self.db.add(point)
        self.db.commit()

    def ingest_attack_sequence(self, payload: AttackSequenceIn) -> dict:
        predicted_mutation, mutation_risk = self.pipeline.score_mutation(payload.tokens)

        event = AttackSequenceEvent(
            attack_family=payload.attack_family,
            signature=payload.signature,
            tokens=payload.tokens,
            embedding_hint=payload.embedding_hint,
            predicted_mutation=predicted_mutation,
            risk_score=mutation_risk,
        )
        self.db.add(event)
        self.db.commit()
        return {"predicted_mutation": predicted_mutation, "mutation_risk": mutation_risk}

    def train_bootstrap(self) -> dict:
        login_rows = (
            self.db.query(LoginEvent.context)
            .filter(LoginEvent.context.is_not(None))
            .all()
        )
        login_matrix: list[list[float]] = []
        for (ctx,) in login_rows:
            if not isinstance(ctx, dict):
                continue
            vec = ctx.get("feature_vector")
            if isinstance(vec, list) and len(vec) == 6:
                login_matrix.append([float(v) for v in vec])

        flow_rows = self.db.query(NetworkFlow).all()
        network_matrix = [
            self.pipeline.network_features(
                row.bytes_in,
                row.bytes_out,
                row.packets,
                row.duration_ms,
                float(row.tcp_flags.get("SYN", 0)) / max(float(row.packets), 1.0),
            ).tolist()
            for row in flow_rows
        ]

        ts_points = (
            self.db.query(TimeSeriesPoint.metric_value)
            .order_by(TimeSeriesPoint.created_at.asc())
            .all()
        )
        time_series = [float(v[0]) for v in ts_points]

        seq_rows = self.db.query(AttackSequenceEvent.tokens).all()
        sequences = [row[0] for row in seq_rows if isinstance(row[0], list) and row[0]]

        # Bootstrap synthetic samples when history is still small.
        if len(login_matrix) < 50:
            login_synth = np.random.normal(loc=0.3, scale=0.2, size=(250, 6)).clip(0.0, 1.0)
            login_matrix.extend(login_synth.tolist())
        if len(network_matrix) < 50:
            net_synth = np.random.normal(loc=1.0, scale=0.8, size=(300, 5)).clip(0.0, 5.0)
            network_matrix.extend(net_synth.tolist())
        if len(time_series) < 80:
            base = np.abs(np.random.normal(loc=12, scale=4, size=220))
            time_series.extend(base.astype(float).tolist())
        if len(sequences) < 20:
            sequences.extend(
                [
                    ["sqlmap", "tamper", "union", "select"],
                    ["bruteforce", "rotate-ip", "credential-stuffing"],
                    ["hydra", "ssh", "parallel", "password-spray"],
                    ["botnet", "burst", "login", "replay"],
                ]
                * 8
            )

        self.pipeline.bootstrap_train(
            login_matrix=np.array(login_matrix, dtype=np.float32),
            network_matrix=np.array(network_matrix, dtype=np.float32),
            time_series=time_series,
            attack_sequences=sequences,
        )

        return {
            "login_samples": len(login_matrix),
            "network_samples": len(network_matrix),
            "timeseries_points": len(time_series),
            "attack_sequences": len(sequences),
            "status": "trained",
        }

    def user_risk_summary(self, user_id: str) -> dict:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        login_avg = (
            self.db.query(func.avg(LoginEvent.risk_score))
            .filter(LoginEvent.user_id == user_id, LoginEvent.created_at >= since)
            .scalar()
        )
        network_avg = (
            self.db.query(func.avg(NetworkFlow.anomaly_score))
            .filter(NetworkFlow.user_id == user_id, NetworkFlow.created_at >= since)
            .scalar()
        )

        recent_ts = self._recent_metric(user_id, "login_failures_15m")
        temporal_risk = self.pipeline.score_temporal(float(recent_ts[-1] if recent_ts else 0.0), recent_ts)

        seq_events = (
            self.db.query(AttackSequenceEvent.risk_score)
            .order_by(AttackSequenceEvent.created_at.desc())
            .limit(20)
            .all()
        )
        mutation_risk = float(np.mean([float(v[0]) for v in seq_events])) if seq_events else 0.0

        login_risk = float(login_avg or 0.0)
        network_risk = float(network_avg or 0.0)
        aggregate = self.pipeline.aggregate_risk(
            login_risk=login_risk,
            network_risk=network_risk,
            temporal_risk=temporal_risk,
            mutation_risk=mutation_risk,
        )
        action = self.pipeline.choose_action(
            login_risk=login_risk,
            network_risk=network_risk,
            temporal_risk=temporal_risk,
            mutation_risk=mutation_risk,
            aggregate_risk=aggregate,
            deterministic=True,
        )

        return {
            "user_id": user_id,
            "login_risk": login_risk,
            "network_risk": network_risk,
            "temporal_risk": temporal_risk,
            "mutation_risk": mutation_risk,
            "aggregate_risk": aggregate,
            "recommended_action": action,
        }
