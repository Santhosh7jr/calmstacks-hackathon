import sys
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ml.models.fragment_siamese.model import SiameseFragmentModel

def test_forward_shape():
    m=SiameseFragmentModel(); a=torch.rand(4,1,512); b=torch.rand(4,1,512)
    y=m(a,b); assert y.shape==(4,)

def test_probability_range():
    m=SiameseFragmentModel(); a=torch.rand(2,1,512); b=torch.rand(2,1,512)
    p=m.probability(m(a,b)); assert torch.all((p>=0)&(p<=1))
