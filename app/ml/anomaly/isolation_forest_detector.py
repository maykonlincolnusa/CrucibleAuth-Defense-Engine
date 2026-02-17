from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


@dataclass
class IsolationForestDetector:
    contamination: float = 0.05
    random_state: int = 42
    threshold: float = 0.65
    scaler: StandardScaler = field(default_factory=StandardScaler)
    model: IsolationForest = field(init=False)
    fitted: bool = False

    def __post_init__(self) -> None:
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=300,
        )

    def fit(self, x: np.ndarray) -> None:
        if len(x) < 20:
            return
        x_scaled = self.scaler.fit_transform(x)
        self.model.fit(x_scaled)
        self.fitted = True

    def score(self, row: np.ndarray) -> tuple[float, bool]:
        row_2d = row.reshape(1, -1)
        if not self.fitted:
            # Fallback while model is warming up.
            heuristic = float(np.clip(np.mean(np.abs(row)) / 10.0, 0.0, 1.0))
            return heuristic, heuristic >= self.threshold

        row_scaled = self.scaler.transform(row_2d)
        raw = float(self.model.score_samples(row_scaled)[0])
        risk = float(1.0 / (1.0 + np.exp(4.0 * raw)))
        return risk, risk >= self.threshold
