import torch
from torch import nn

class FragmentEncoder(nn.Module):
    """Shared 1D-CNN encoder for a fragment boundary byte sequence."""
    def __init__(self, embedding_dim: int = 256, dropout: float = 0.15):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(1, 64, 9, padding=4),
            nn.BatchNorm1d(64), nn.GELU(), nn.MaxPool1d(2),
            nn.Conv1d(64, 128, 7, padding=3),
            nn.BatchNorm1d(128), nn.GELU(), nn.MaxPool1d(2),
            nn.Conv1d(128, 192, 5, padding=2),
            nn.BatchNorm1d(192), nn.GELU(),
            nn.Conv1d(192, 192, 3, padding=1),
            nn.BatchNorm1d(192), nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.projection = nn.Sequential(
            nn.Flatten(),
            nn.Linear(192, 256), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(256, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.projection(self.features(x))
