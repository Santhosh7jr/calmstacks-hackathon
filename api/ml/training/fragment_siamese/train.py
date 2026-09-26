from __future__ import annotations
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
import argparse, json, random
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from ml.models.fragment_siamese.config import FragmentModelConfig
from ml.models.fragment_siamese.model import SiameseFragmentModel
from ml.training.fragment_siamese.dataset import FragmentPairDataset
from ml.training.fragment_siamese.metrics import binary_metrics

def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)

def run_eval(model, loader, device):
    model.eval(); probs=[]; labels=[]; total=0.
    with torch.no_grad():
        for a,b,y in loader:
            a,b,y=a.to(device),b.to(device),y.to(device)
            logits=model(a,b); total += nn.functional.binary_cross_entropy_with_logits(logits,y).item()*len(y)
            probs.extend(torch.sigmoid(logits).cpu().tolist()); labels.extend(y.cpu().tolist())
    return total/max(1,len(labels)), binary_metrics(labels,probs)

def main():
    p=argparse.ArgumentParser(description='Train RecoverAI Siamese 1D-CNN fragment adjacency model')
    p.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[2]/'data'/'fragment_siamese')
    p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'models'/'fragment_siamese'/'fragment_siamese.pt')
    p.add_argument('--epochs',type=int,default=30); p.add_argument('--batch-size',type=int,default=64)
    p.add_argument('--lr',type=float,default=2e-4); p.add_argument('--weight-decay',type=float,default=1e-4)
    p.add_argument('--patience',type=int,default=6); p.add_argument('--seed',type=int,default=42)
    args=p.parse_args(); seed_all(args.seed)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    cfg=FragmentModelConfig(); model=SiameseFragmentModel(cfg).to(device)
    train=FragmentPairDataset(args.data_dir/'pairs'/'train.jsonl',cfg.boundary_bytes)
    val=FragmentPairDataset(args.data_dir/'pairs'/'validation.jsonl',cfg.boundary_bytes)
    tr=DataLoader(train,batch_size=args.batch_size,shuffle=True,num_workers=0)
    va=DataLoader(val,batch_size=args.batch_size,shuffle=False,num_workers=0)
    opt=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=args.weight_decay)
    # Balance the binary loss when generated negatives outnumber positives.
    labels=torch.tensor([r['label'] for r in train.rows],dtype=torch.float32)
    pos=float(labels.sum()); neg=float(len(labels)-pos)
    pos_weight=torch.tensor([neg/max(pos,1.0)],device=device)
    loss_fn=nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    best=-1.; stale=0
    history=[]
    for epoch in range(1,args.epochs+1):
        model.train(); running=0.
        for a,b,y in tr:
            a,b,y=a.to(device),b.to(device),y.to(device); opt.zero_grad(set_to_none=True)
            loss=loss_fn(model(a,b),y); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),2.0); opt.step()
            running += loss.item()*len(y)
        val_loss,m=run_eval(model,va,device); row={'epoch':epoch,'train_loss':running/len(train),'val_loss':val_loss,**m}; history.append(row)
        print(json.dumps(row))
        if m['roc_auc'] is not None and m['roc_auc']>best:
            best=m['roc_auc']; stale=0
            torch.save({'model_state':model.state_dict(),'config':cfg.__dict__,'history':history,'seed':args.seed},args.output)
        else: stale+=1
        if stale>=args.patience: break
    print(json.dumps({'best_checkpoint':str(args.output),'best_val_roc_auc':best,'device':str(device)},indent=2))

if __name__=='__main__': main()
