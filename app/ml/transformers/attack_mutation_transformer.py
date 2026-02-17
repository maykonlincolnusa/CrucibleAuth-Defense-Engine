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
    class MutationTransformer(nn.Module):
        def __init__(self, vocab_size: int, embed_dim: int = 48, heads: int = 4, layers: int = 2):
            super().__init__()
            self.embedding = nn.Embedding(vocab_size, embed_dim)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=embed_dim,
                nhead=heads,
                dim_feedforward=128,
                batch_first=True,
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=layers)
            self.out = nn.Linear(embed_dim, vocab_size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            emb = self.embedding(x)
            enc = self.encoder(emb)
            return self.out(enc[:, -1, :])
else:
    class MutationTransformer:  # pragma: no cover - no torch fallback
        def parameters(self):
            return []

        def train(self):
            return None

        def eval(self):
            return None


@dataclass
class AttackMutationTransformer:
    epochs: int = 12
    lr: float = 1e-3
    vocab: dict[str, int] = field(default_factory=lambda: {"<pad>": 0, "<unk>": 1})
    inverse_vocab: dict[int, str] = field(default_factory=lambda: {0: "<pad>", 1: "<unk>"})
    model: MutationTransformer | None = None
    fitted: bool = False
    max_len: int = 12

    def _encode(self, token: str) -> int:
        if token not in self.vocab:
            idx = len(self.vocab)
            self.vocab[token] = idx
            self.inverse_vocab[idx] = token
        return self.vocab[token]

    def fit(self, sequences: list[list[str]]) -> None:
        if len(sequences) < 10:
            return

        encoded_sequences: list[list[int]] = []
        for seq in sequences:
            encoded_sequences.append([self._encode(tok) for tok in seq][: self.max_len + 1])

        x_batch, y_batch = [], []
        for seq in encoded_sequences:
            if len(seq) < 2:
                continue
            x = seq[:-1]
            y = seq[-1]
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

        vocab_size = len(self.vocab)
        self.model = MutationTransformer(vocab_size=vocab_size)
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

    def predict_next(self, tokens: list[str], top_k: int = 3) -> tuple[str, float]:
        if not tokens:
            return "<unk>", 0.0
        if not self.fitted or not self.model or torch is None:
            return tokens[-1], 0.3

        encoded = [self.vocab.get(tok, 1) for tok in tokens][-self.max_len :]
        pad_len = self.max_len - len(encoded)
        if pad_len > 0:
            encoded = [0] * pad_len + encoded

        x_t = torch.tensor([encoded], dtype=torch.long)
        self.model.eval()
        with torch.no_grad():
            logits = self.model(x_t)
            probs = torch.softmax(logits, dim=-1)
            values, idxs = torch.topk(probs, k=min(top_k, probs.shape[-1]), dim=-1)

        token = self.inverse_vocab.get(int(idxs[0][0].item()), "<unk>")
        confidence = float(values[0][0].item())
        risk = float(np.clip(1.0 - confidence, 0.0, 1.0))
        return token, risk
