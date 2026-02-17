from dataclasses import dataclass, field

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM


@dataclass
class OneClassSVMDetector:
    nu: float = 0.08
    gamma: str = "scale"
    threshold: float = 0.7
    scaler: StandardScaler = field(default_factory=StandardScaler)
    model: OneClassSVM = field(init=False)
    fitted: bool = False

    def __post_init__(self) -> None:
        self.model = OneClassSVM(nu=self.nu, kernel="rbf", gamma=self.gamma)

    def fit(self, x: np.ndarray) -> None:
        if len(x) < 30:
            return
        x_scaled = self.scaler.fit_transform(x)
        self.model.fit(x_scaled)
        self.fitted = True

    def score(self, row: np.ndarray) -> tuple[float, bool]:
        row_2d = row.reshape(1, -1)
        if not self.fitted:
            heuristic = float(np.clip(np.log1p(np.sum(np.abs(row))) / 10.0, 0.0, 1.0))
            return heuristic, heuristic >= self.threshold

        row_scaled = self.scaler.transform(row_2d)
        raw = float(self.model.decision_function(row_scaled)[0])
        risk = float(1.0 / (1.0 + np.exp(3.5 * raw)))
        return risk, risk >= self.threshold
