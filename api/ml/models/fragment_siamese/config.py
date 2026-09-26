from dataclasses import dataclass

@dataclass(frozen=True)
class FragmentModelConfig:
    boundary_bytes: int = 512
    embedding_dim: int = 256
    dropout: float = 0.15
    channels: tuple[int, int, int] = (64, 128, 192)
