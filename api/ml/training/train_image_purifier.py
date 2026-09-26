from pathlib import Path
import json, joblib
import numpy as np
from PIL import Image, ImageDraw
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
BASE_DIR=Path(__file__).resolve().parents[1]; ROOT=BASE_DIR.parent.parent; MODEL_DIR=BASE_DIR/'models'/'image_purification'; MODEL_DIR.mkdir(parents=True,exist_ok=True); METRIC=BASE_DIR/'data'/'processed'/'metrics'/'image_purification.json'
rng=np.random.default_rng(42)
bases=[]
real=Image.open(BASE_DIR/'data'/'raw'/'images'/'file_example_JPG_100kB.jpg').convert('RGB').resize((512,342),Image.Resampling.BILINEAR); bases.append(np.asarray(real,np.uint8))
for k in range(12):
 h=w=256; y,x=np.mgrid[0:h,0:w]; a=np.zeros((h,w,3),np.float32); a[:,:,0]=x/w*255+25*np.sin(y/(9+k%5)); a[:,:,1]=y/h*255+30*np.sin(x/(13+k%7)); a[:,:,2]=(x+y)/(w+h)*255+20*np.cos((x+y)/(11+k%4)); a+=rng.normal(0,10,(h,w,1)); a=np.clip(a,0,255).astype(np.uint8); im=Image.fromarray(a); d=ImageDraw.Draw(im)
 for j in range(10):
  x0=int(rng.integers(0,220)); y0=int(rng.integers(0,220)); x1=x0+int(rng.integers(10,50)); y1=y0+int(rng.integers(10,50)); d.rectangle((x0,y0,x1,y1),fill=tuple(int(v) for v in rng.integers(0,256,3)))
 bases.append(np.asarray(im,np.uint8))
X=[]; y=[]
for bi,base in enumerate(bases):
 h,w=base.shape[:2]; n=30000 if bi==0 else 900
 for _ in range(n):
  cy=int(rng.integers(6,h-6)); cx=int(rng.integers(6,w-6)); patch=base[cy-5:cy+6,cx-5:cx+6].astype(np.float32)/255.; clean=patch[5,5].copy(); corrupted=patch.copy()
  mode=int(rng.integers(0,6)); size=int(rng.choice([1,3,5,7])); half=size//2
  if mode in (0,1,2,3):
   if mode==0: val=0.0
   elif mode==1: val=1.0
   elif mode==2: val=float(rng.random())
   else: val=None
   if val is None: corrupted[5-half:6+half,5-half:6+half]=rng.random((2*half+1,2*half+1,1))*0.15
   else: corrupted[5-half:6+half,5-half:6+half]=val
  elif mode==4:
   corrupted[5,5]=np.clip(clean+rng.normal(0,0.4,3),0,1)
  else:
   corrupted[5-half:6+half,5-half:6+half]=corrupted[5-half:6+half,5-half:6+half]*0.2
  X.append(corrupted.reshape(-1)); y.append(clean)
X=np.asarray(X,np.float32); y=np.asarray(y,np.float32); Xtr,Xv,ytr,yv=train_test_split(X,y,test_size=.15,random_state=42)
model=MLPRegressor(hidden_layer_sizes=(128,64),activation='relu',solver='adam',batch_size=1024,learning_rate_init=.001,max_iter=100,early_stopping=True,validation_fraction=.1,n_iter_no_change=10,random_state=42)
model.fit(Xtr,ytr); pred=np.clip(model.predict(Xv),0,1); rmse=float(np.sqrt(mean_squared_error(yv,pred))); base=Xv.reshape(-1,11,11,3)[:,5,5]; base_rmse=float(np.sqrt(mean_squared_error(yv,base)))
joblib.dump({'model':model,'patch_size':11,'channels':3,'input_scale':'0_1','version':'3.0','purpose':'masked-region RGB purification','training_samples':int(len(X))},MODEL_DIR/'image_purifier.joblib',compress=3)
metrics={'validation_rmse':rmse,'baseline_corrupted_center_rmse':base_rmse,'improvement_percent':max(0,(1-rmse/base_rmse)*100),'samples':int(len(X)),'bases':len(bases),'iterations':int(getattr(model,'n_iter_',0)),'patch_size':11,'real_image_samples':30000}
METRIC.write_text(json.dumps(metrics,indent=2)); print(json.dumps(metrics,indent=2))
