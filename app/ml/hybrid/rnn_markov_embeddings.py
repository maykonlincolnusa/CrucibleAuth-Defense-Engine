from collections import defaultdict
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
    class TokenRNN(nn.Module):
        def __init__(self, vocab_size: int, embedding_dim: int = 24, hidden_dim: int = 32):
            super().__init__()
            self.embedding = nn.Embedding(vocab_size, embedding_dim)
            self.gru = nn.GRU(embedding_dim, hidden_dim, batch_first=True)
            self.head = nn.Linear(hidden_dim, vocab_size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            emb = self.embedding(x)
            out, _ = self.gru(emb)
            return self.head(out[:, -1, :])
else:
    class TokenRNN:  # pragma: no cover - no torch fallback
        def parameters(self):
            return []

        def train(self):
            return None

        def eval(self):
            return None


@dataclass
class RNNMarkovEmbeddings:
    max_len: int = 10
    epochs: int = 10
    lr: float = 1e-3
    vocab: dict[str, int] = field(default_factory=lambda: {"<pad>": 0, "<unk>": 1})
    inv_vocab: dict[int, str] = field(default_factory=lambda: {0: "<pad>", 1: "<unk>"})
    markov: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    model: TokenRNN | None = None
    fitted: bool = False

    def _id(self, token: str) -> int:
        if token not in self.vocab:
            idx = len(self.vocab)
            self.vocab[token] = idx
            self.inv_vocab[idx] = token
        return self.vocab[token]

    def fit(self, sequences: list[list[str]]) -> None:
        if len(sequences) < 10:
            return

        x_batch, y_batch = [], []
        for seq in sequences:
            for i in range(len(seq) - 1):
                a, b = seq[i], seq[i + 1]
                self.markov[a][b] += 1

            ids = [self._id(tok) for tok in seq]
            if len(ids) < 2:
                continue
            x = ids[:-1]
            y = ids[-1]
            pad_len = self.max_len - len(x)
            if pad_len > 0:
                x = [0] * pad_len + x
            else:
                x = x[-self.max_len :]
            x_batch.append(x)
            y_batch.append(y)

        if not x_batch:
            return
        if torch is None or nn is None or optim is None:
            self.fitted = True
            return

        self.model = TokenRNN(vocab_size=len(self.vocab))
        x_t = torch.tensor(np.array(x_batch), dtype=torch.long)
        y_t = torch.tensor(np.array(y_batch), dtype=torch.long)

        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        criterion = nn.CrossEntropyLoss()

        self.model.train()
        for _ in range(self.epochs):
            optimizer.zero_grad()
            logits = self.model(x_t)
            loss = criterion(logits, y_t)
            loss.backward()
            optimizer.step()

        self.fitted = True

    def predict(self, tokens: list[str]) -> tuple[str, float]:
        if not tokens:
            return "<unk>", 0.0

        last = tokens[-1]
        markov_probs = self.markov.get(last, {})
        markov_choice = None
        markov_conf = 0.0
        if markov_probs:
            total = float(sum(markov_probs.values()))
            markov_choice = max(markov_probs, key=markov_probs.get)
            markov_conf = markov_probs[markov_choice] / total

        rnn_choice = None
        rnn_conf = 0.0
        if self.fitted and self.model is not None and torch is not None:
            ids = [self.vocab.get(tok, 1) for tok in tokens][-self.max_len :]
            pad_len = self.max_len - len(ids)
            if pad_len > 0:
                ids = [0] * pad_len + ids
            x_t = torch.tensor([ids], dtype=torch.long)
            self.model.eval()
            with torch.no_grad():
                logits = self.model(x_t)
                probs = torch.softmax(logits, dim=-1)
                idx = int(torch.argmax(probs, dim=-1).item())
                rnn_choice = self.inv_vocab.get(idx, "<unk>")
                rnn_conf = float(probs[0][idx].item())

        if markov_conf >= rnn_conf and markov_choice:
            return markov_choice, float(np.clip(1.0 - markov_conf, 0.0, 1.0))
        if rnn_choice:
            return rnn_choice, float(np.clip(1.0 - rnn_conf, 0.0, 1.0))
        return tokens[-1], 0.5
