from __future__ import annotations
import torch
from torch import nn
from .config import FragmentModelConfig
from .encoder import FragmentEncoder
from .scorer import PairScorer

class SiameseFragmentModel(nn.Module):
    """Predicts whether fragment B immediately follows fragment A."""
    def __init__(self, config: FragmentModelConfig | None = None):
        super().__init__()
        self.config = config or FragmentModelConfig()
        self.encoder = FragmentEncoder(self.config.embedding_dim, self.config.dropout)
        self.scorer = PairScorer(self.config.embedding_dim, self.config.dropout)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def forward(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return self.scorer(self.encoder(a), self.encoder(b))

    @staticmethod
    def probability(logits: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(logits)
