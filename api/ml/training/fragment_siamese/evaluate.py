from __future__ import annotations
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
import argparse, json
import torch
from torch.utils.data import DataLoader
from ml.models.fragment_siamese.model import SiameseFragmentModel
from ml.training.fragment_siamese.dataset import FragmentPairDataset
from ml.training.fragment_siamese.metrics import binary_metrics

def evaluate(model, loader, device):
    model.eval(); probs=[]; labels=[]
    with torch.no_grad():
        for a,b,y in loader:
            logits=model(a.to(device), b.to(device))
            probs.extend(torch.sigmoid(logits).cpu().tolist())
            labels.extend(y.tolist())
    return binary_metrics(labels, probs)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parents[2]/'data'/'fragment_siamese')
    p.add_argument('--batch-size', type=int, default=64)
    args=p.parse_args()
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    ckpt=torch.load(args.checkpoint, map_location=device, weights_only=False)
    from ml.models.fragment_siamese.config import FragmentModelConfig
    cfg = FragmentModelConfig(**ckpt['config']) if isinstance(ckpt.get('config'), dict) else FragmentModelConfig()
    model=SiameseFragmentModel(cfg).to(device)
    model.load_state_dict(ckpt['model_state'])
    ds=FragmentPairDataset(args.data_dir/'pairs'/'test.jsonl', model.config.boundary_bytes)
    metrics=evaluate(model, DataLoader(ds,batch_size=args.batch_size),device)
    print(json.dumps(metrics, indent=2))

if __name__=='__main__': main()
