from __future__ import annotations
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
import torch
from ml.models.fragment_siamese.config import FragmentModelConfig
from ml.models.fragment_siamese.model import SiameseFragmentModel

class FragmentPairPredictor:
    def __init__(self, checkpoint: str | Path, device: str | None = None):
        self.device=torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
        ckpt=torch.load(checkpoint,map_location=self.device,weights_only=False)
        cfg=FragmentModelConfig(**ckpt.get('config',{}))
        self.model=SiameseFragmentModel(cfg).to(self.device)
        self.model.load_state_dict(ckpt['model_state']); self.model.eval()

    def _tensor(self,data: bytes, tail: bool):
        n=self.model.config.boundary_bytes
        data=data[-n:] if tail else data[:n]
        data=data+b'\x00'*max(0,n-len(data))
        return torch.tensor(list(data),dtype=torch.float32,device=self.device).div(255).view(1,1,n)

    @torch.inference_mode()
    def predict_bytes(self,a: bytes,b: bytes):
        p=float(torch.sigmoid(self.model(self._tensor(a,True),self._tensor(b,False))).item())
        return {'probability':p,'is_adjacent':p>=0.5}
