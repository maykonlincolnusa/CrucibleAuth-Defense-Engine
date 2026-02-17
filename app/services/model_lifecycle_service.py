from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AttackSequenceEvent, LoginEvent, NetworkFlow, TimeSeriesPoint
from app.ml.pipeline import DefenseMLPipeline
from app.services.mlflow_tracking import training_run
from app.services.state import get_pipeline, replace_pipeline


@dataclass
class TrainingPayload:
    login_matrix: np.ndarray
    network_matrix: np.ndarray
    time_series: list[float]
    attack_sequences: list[list[str]]


class ModelLifecycleService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _build_payload(self) -> TrainingPayload:
        base_pipeline = get_pipeline()

        login_rows = self.db.query(LoginEvent.context).filter(LoginEvent.context.is_not(None)).all()
        login_matrix: list[list[float]] = []
        for (ctx,) in login_rows:
            if not isinstance(ctx, dict):
                continue
            vec = ctx.get("feature_vector")
            if isinstance(vec, list) and len(vec) == 6:
                login_matrix.append([float(v) for v in vec])

        flow_rows = self.db.query(NetworkFlow).all()
        network_matrix = [
            base_pipeline.network_features(
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

        return TrainingPayload(
            login_matrix=np.array(login_matrix, dtype=np.float32),
            network_matrix=np.array(network_matrix, dtype=np.float32),
            time_series=time_series,
            attack_sequences=sequences,
        )

    def _evaluate_pipeline_quality(self, candidate: DefenseMLPipeline) -> float:
        login_rows = self.db.query(LoginEvent.context, LoginEvent.success).all()
        success_scores: list[float] = []
        failed_scores: list[float] = []
        for ctx, success in login_rows:
            if not isinstance(ctx, dict):
                continue
            vec = ctx.get("feature_vector")
            if not isinstance(vec, list) or len(vec) != 6:
                continue
            risk, _ = candidate.score_login(np.array(vec, dtype=np.float32))
            if bool(success):
                success_scores.append(risk)
            else:
                failed_scores.append(risk)

        login_delta = (float(np.mean(failed_scores)) - float(np.mean(success_scores))) if success_scores and failed_scores else 0.0
        login_quality = float(np.clip((login_delta + 1.0) / 2.0, 0.0, 1.0))

        flow_rows = self.db.query(NetworkFlow).all()
        anomaly_scores: list[float] = []
        normal_scores: list[float] = []
        for flow in flow_rows:
            row = candidate.network_features(
                flow.bytes_in,
                flow.bytes_out,
                flow.packets,
                flow.duration_ms,
                float(flow.tcp_flags.get("SYN", 0)) / max(float(flow.packets), 1.0),
            )
            risk, _ = candidate.score_network(row)
            if bool(flow.anomaly_flag):
                anomaly_scores.append(risk)
            else:
                normal_scores.append(risk)

        network_delta = (float(np.mean(anomaly_scores)) - float(np.mean(normal_scores))) if anomaly_scores and normal_scores else 0.0
        network_quality = float(np.clip((network_delta + 1.0) / 2.0, 0.0, 1.0))

        return float(np.clip((0.6 * login_quality) + (0.4 * network_quality), 0.0, 1.0))

    def _snapshot(self, pipeline: DefenseMLPipeline, name: str) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        path = Path(self.settings.model_dir) / f"{name}_{timestamp}.joblib"
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, path)
        return path

    def train_with_validation_and_rollback(self) -> dict:
        payload = self._build_payload()
        current = get_pipeline()
        baseline_quality = self._evaluate_pipeline_quality(current)
        previous_snapshot = self._snapshot(current, "pipeline_previous")

        candidate = copy.deepcopy(current)
        candidate.bootstrap_train(
            login_matrix=payload.login_matrix,
            network_matrix=payload.network_matrix,
            time_series=payload.time_series,
            attack_sequences=payload.attack_sequences,
        )
        candidate_quality = self._evaluate_pipeline_quality(candidate)

        acceptance_floor = max(
            float(self.settings.retrain_acceptance_threshold),
            float(baseline_quality * 0.95),
        )
        accepted = candidate_quality >= acceptance_floor
        artifact_path = previous_snapshot

        if accepted:
            replace_pipeline(candidate)
            artifact_path = self._snapshot(candidate, "pipeline_candidate")
        else:
            replace_pipeline(current)

        with training_run(
            run_name="pipeline_retrain",
            params={
                "login_samples": len(payload.login_matrix),
                "network_samples": len(payload.network_matrix),
                "timeseries_points": len(payload.time_series),
                "attack_sequences": len(payload.attack_sequences),
                "acceptance_floor": acceptance_floor,
                "auto_retrain_enabled": self.settings.auto_retrain_enabled,
            },
            metrics={
                "baseline_quality": baseline_quality,
                "candidate_quality": candidate_quality,
                "accepted": 1.0 if accepted else 0.0,
            },
        ) as run_id:
            mlflow_run_id = run_id

        return {
            "status": "accepted" if accepted else "rolled_back",
            "accepted": accepted,
            "baseline_quality": round(baseline_quality, 5),
            "candidate_quality": round(candidate_quality, 5),
            "acceptance_floor": round(acceptance_floor, 5),
            "artifact_path": str(artifact_path),
            "previous_snapshot": str(previous_snapshot),
            "mlflow_run_id": mlflow_run_id,
            "samples": {
                "login_samples": len(payload.login_matrix),
                "network_samples": len(payload.network_matrix),
                "timeseries_points": len(payload.time_series),
                "attack_sequences": len(payload.attack_sequences),
            },
        }
