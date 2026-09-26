import torch
from torch import nn

class PairScorer(nn.Module):
    def __init__(self, embedding_dim: int = 256, dropout: float = 0.15):
        super().__init__()
        features = embedding_dim * 4
        self.net = nn.Sequential(
            nn.Linear(features, 256), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(256, 64), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(64, 1),
        )

    def forward(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        z = torch.cat((a, b, torch.abs(a - b), a * b), dim=1)
        return self.net(z).squeeze(1)
