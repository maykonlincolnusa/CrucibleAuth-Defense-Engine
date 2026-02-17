from dataclasses import dataclass, field

import numpy as np
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
except Exception:  # pragma: no cover - optional runtime fallback
    torch = None
    nn = None
    optim = None


if nn is not None:
    class LSTMGRUNet(nn.Module):
        def __init__(self, input_dim: int = 1, hidden_dim: int = 32):
            super().__init__()
            self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
            self.gru = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
            self.out = nn.Linear(hidden_dim, 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out, _ = self.lstm(x)
            out, _ = self.gru(out)
            out = self.out(out[:, -1, :])
            return out
else:
    class LSTMGRUNet:  # pragma: no cover - no torch fallback
        def parameters(self):
            return []

        def train(self):
            return None

        def eval(self):
            return None


@dataclass
class LSTMGRUPredictor:
    seq_len: int = 12
    lr: float = 1e-3
    epochs: int = 15
    threshold: float = 0.65
    model: LSTMGRUNet = field(default_factory=LSTMGRUNet)
    fitted: bool = False
    mean_: float = 0.0
    std_: float = 1.0

    def _build_dataset(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x, y = [], []
        for i in range(len(values) - self.seq_len):
            x.append(values[i : i + self.seq_len])
            y.append(values[i + self.seq_len])
        return np.array(x), np.array(y)

    def fit(self, series: list[float]) -> None:
        values = np.array(series, dtype=np.float32)
        if len(values) <= self.seq_len + 5:
            return

        self.mean_ = float(values.mean())
        self.std_ = float(values.std() + 1e-6)
        values = (values - self.mean_) / self.std_
        x, y = self._build_dataset(values)
        if len(x) == 0:
            return
        if torch is None or nn is None or optim is None:
            self.fitted = True
            return

        x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(-1)
        y_t = torch.tensor(y, dtype=torch.float32).unsqueeze(-1)

        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        criterion = nn.MSELoss()

        self.model.train()
        for _ in range(self.epochs):
            optimizer.zero_grad()
            pred = self.model(x_t)
            loss = criterion(pred, y_t)
            loss.backward()
            optimizer.step()

        self.fitted = True

    def predict_next(self, recent: list[float]) -> float:
        if len(recent) < self.seq_len:
            return float(recent[-1] if recent else 0.0)

        if not self.fitted:
            return float(np.mean(recent[-self.seq_len :]))
        if torch is None:
            return float(np.mean(recent[-self.seq_len :]))

        window = np.array(recent[-self.seq_len :], dtype=np.float32)
        window = (window - self.mean_) / self.std_
        x_t = torch.tensor(window, dtype=torch.float32).unsqueeze(0).unsqueeze(-1)

        self.model.eval()
        with torch.no_grad():
            pred = self.model(x_t).item()
        return float(pred * self.std_ + self.mean_)

    def anomaly_score(self, observed: float, recent: list[float]) -> float:
        expected = self.predict_next(recent)
        delta = abs(observed - expected)
        scale = max(abs(expected), 1.0)
        risk = float(np.clip(delta / (2.5 * scale), 0.0, 1.0))
        return risk
