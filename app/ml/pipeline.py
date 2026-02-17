from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.ml.anomaly.isolation_forest_detector import IsolationForestDetector
from app.ml.hybrid.rnn_markov_embeddings import RNNMarkovEmbeddings
from app.ml.network.one_class_svm_detector import OneClassSVMDetector
from app.ml.rl.dqn_response_agent import DQNResponseAgent
from app.ml.timeseries.lstm_gru_predictor import LSTMGRUPredictor
from app.ml.transformers.attack_mutation_transformer import AttackMutationTransformer


@dataclass
class DefenseMLPipeline:
    isolation_forest: IsolationForestDetector = field(default_factory=IsolationForestDetector)
    one_class_svm: OneClassSVMDetector = field(default_factory=OneClassSVMDetector)
    lstm_gru: LSTMGRUPredictor = field(default_factory=LSTMGRUPredictor)
    transformer: AttackMutationTransformer = field(default_factory=AttackMutationTransformer)
    hybrid_seq: RNNMarkovEmbeddings = field(default_factory=RNNMarkovEmbeddings)
    dqn: DQNResponseAgent = field(default_factory=DQNResponseAgent)

    def __post_init__(self) -> None:
        self.settings = get_settings()
        self.model_dir = Path(self.settings.model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def login_features(
        failed_attempts_15m: int,
        hour_of_day: int,
        is_new_ip: int,
        latency_ms: float,
        user_success_rate: float,
        user_agent_entropy: float,
    ) -> np.ndarray:
        return np.array(
            [
                failed_attempts_15m,
                hour_of_day / 24.0,
                is_new_ip,
                latency_ms / 5000.0,
                1.0 - user_success_rate,
                user_agent_entropy,
            ],
            dtype=np.float32,
        )

    @staticmethod
    def network_features(
        bytes_in: int,
        bytes_out: int,
        packets: int,
        duration_ms: float,
        syn_flag_ratio: float,
    ) -> np.ndarray:
        return np.array(
            [
                np.log1p(bytes_in),
                np.log1p(bytes_out),
                np.log1p(packets),
                np.log1p(duration_ms + 1.0),
                syn_flag_ratio,
            ],
            dtype=np.float32,
        )

    def score_login(self, row: np.ndarray) -> tuple[float, bool]:
        return self.isolation_forest.score(row)

    def score_network(self, row: np.ndarray) -> tuple[float, bool]:
        return self.one_class_svm.score(row)

    def score_temporal(self, observed: float, recent: list[float]) -> float:
        return self.lstm_gru.anomaly_score(observed=observed, recent=recent)

    def score_mutation(self, tokens: list[str]) -> tuple[str, float]:
        tf_token, tf_risk = self.transformer.predict_next(tokens)
        hy_token, hy_risk = self.hybrid_seq.predict(tokens)

        if tf_risk >= hy_risk:
            return tf_token, float((tf_risk * 0.7) + (hy_risk * 0.3))
        return hy_token, float((hy_risk * 0.7) + (tf_risk * 0.3))

    @staticmethod
    def aggregate_risk(
        login_risk: float,
        network_risk: float,
        temporal_risk: float,
        mutation_risk: float,
    ) -> float:
        weights = np.array([0.35, 0.30, 0.20, 0.15], dtype=np.float32)
        values = np.array([login_risk, network_risk, temporal_risk, mutation_risk], dtype=np.float32)
        return float(np.clip(np.dot(weights, values), 0.0, 1.0))

    def choose_action(
        self,
        login_risk: float,
        network_risk: float,
        temporal_risk: float,
        mutation_risk: float,
        aggregate_risk: float,
        deterministic: bool = False,
    ) -> str:
        state = np.array(
            [login_risk, network_risk, temporal_risk, mutation_risk, aggregate_risk],
            dtype=np.float32,
        )
        return self.dqn.choose_action(state, deterministic=deterministic)

    def reinforce(
        self,
        state: np.ndarray,
        action: str,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.dqn.remember(state, action, reward, next_state, done)
        self.dqn.train_step()

    def bootstrap_train(
        self,
        login_matrix: np.ndarray,
        network_matrix: np.ndarray,
        time_series: list[float],
        attack_sequences: list[list[str]],
    ) -> None:
        self.isolation_forest.fit(login_matrix)
        self.one_class_svm.fit(network_matrix)
        self.lstm_gru.fit(time_series)
        self.transformer.fit(attack_sequences)
        self.hybrid_seq.fit(attack_sequences)
        self.dqn.update_target()
