from __future__ import annotations
import json
from pathlib import Path
import torch
from torch.utils.data import Dataset

class FragmentPairDataset(Dataset):
    def __init__(self, jsonl_path: str | Path, boundary_bytes: int = 512):
        self.path = Path(jsonl_path)
        self.boundary_bytes = boundary_bytes
        self.rows = [json.loads(line) for line in self.path.read_text(encoding='utf-8').splitlines() if line.strip()]
        if not self.rows:
            raise ValueError(f'No pairs found in {self.path}')

    def __len__(self):
        return len(self.rows)

    def _read(self, path: str, take_tail: bool) -> torch.Tensor:
        data = Path(path).read_bytes()
        data = data[-self.boundary_bytes:] if take_tail else data[:self.boundary_bytes]
        if len(data) < self.boundary_bytes:
            data = data + b'\x00' * (self.boundary_bytes - len(data))
        # Keep byte identity while putting values in a stable numeric range.
        return torch.tensor(list(data), dtype=torch.float32).div_(255.0).unsqueeze(0)

    def __getitem__(self, index: int):
        row = self.rows[index]
        a = self._read(row['fragment_a'], True)
        b = self._read(row['fragment_b'], False)
        return a, b, torch.tensor(float(row['label']), dtype=torch.float32)
