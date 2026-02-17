from collections import deque
from dataclasses import dataclass, field
import random

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
    class DQNet(nn.Module):
        def __init__(self, state_dim: int, action_dim: int):
            super().__init__()
            self.layers = nn.Sequential(
                nn.Linear(state_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 64),
                nn.ReLU(),
                nn.Linear(64, action_dim),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.layers(x)
else:
    class DQNet:  # pragma: no cover - no torch fallback
        def __init__(self, state_dim: int, action_dim: int):
            self.action_dim = action_dim

        def state_dict(self):
            return {}

        def load_state_dict(self, _):
            return None

        def parameters(self):
            return []

        def __call__(self, _):
            return np.zeros((1, self.action_dim), dtype=np.float32)


@dataclass
class DQNResponseAgent:
    actions: list[str] = field(
        default_factory=lambda: [
            "ALLOW",
            "MFA_CHALLENGE",
            "RATE_LIMIT",
            "TEMP_BLOCK",
            "PERM_BLOCK",
            "HONEYPOT_REDIRECT",
        ]
    )
    state_dim: int = 5
    gamma: float = 0.95
    epsilon: float = 0.20
    epsilon_min: float = 0.02
    epsilon_decay: float = 0.995
    lr: float = 1e-3
    replay_size: int = 5_000
    batch_size: int = 32
    memory: deque = field(default_factory=lambda: deque(maxlen=5_000))

    def __post_init__(self) -> None:
        self.model = DQNet(self.state_dim, len(self.actions))
        self.target_model = DQNet(self.state_dim, len(self.actions))
        self.target_model.load_state_dict(self.model.state_dict())
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.lr) if optim else None
        self.loss_fn = nn.MSELoss() if nn else None

    def choose_action(self, state: np.ndarray, deterministic: bool = False) -> str:
        if not deterministic and random.random() < self.epsilon:
            return random.choice(self.actions)
        if torch is None:
            risk = float(np.clip(np.mean(state), 0.0, 1.0))
            if risk > 0.85:
                return "PERM_BLOCK"
            if risk > 0.70:
                return "TEMP_BLOCK"
            if risk > 0.55:
                return "RATE_LIMIT"
            if risk > 0.35:
                return "MFA_CHALLENGE"
            return "ALLOW"

        with torch.no_grad():
            state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            q_vals = self.model(state_t)
            idx = int(torch.argmax(q_vals, dim=-1).item())
        return self.actions[idx]

    def remember(
        self,
        state: np.ndarray,
        action: str,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        action_idx = self.actions.index(action)
        self.memory.append((state, action_idx, reward, next_state, done))

    def train_step(self) -> None:
        if torch is None or self.optimizer is None or self.loss_fn is None:
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            return
        if len(self.memory) < self.batch_size:
            return

        batch = random.sample(self.memory, self.batch_size)
        states = torch.tensor(np.array([item[0] for item in batch]), dtype=torch.float32)
        actions = torch.tensor([item[1] for item in batch], dtype=torch.int64)
        rewards = torch.tensor([item[2] for item in batch], dtype=torch.float32)
        next_states = torch.tensor(np.array([item[3] for item in batch]), dtype=torch.float32)
        dones = torch.tensor([item[4] for item in batch], dtype=torch.float32)

        q_current = self.model(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            q_next = self.target_model(next_states).max(dim=1).values
            q_target = rewards + self.gamma * q_next * (1.0 - dones)

        loss = self.loss_fn(q_current, q_target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def update_target(self) -> None:
        self.target_model.load_state_dict(self.model.state_dict())
