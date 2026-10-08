import pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
import cv2, numpy as np
from tools.omr import direction_text as DT
tag=sys.argv[1]; idx=[int(i) for i in sys.argv[2:]]
pws,pd=pickle.load(open(f"/private/tmp/dtmiss/{tag}.pkl","rb"))
c=DT.find_candidates(pws,pd)
sp=float(np.median([DT._spacing(s) for s in pws.staves]))
raw=DT._page_ink(pws.page)
erase=((raw>0)&(DT._blank_detections(raw,pd,sp,DT.DEFAULT_BAND_CONFIG)==0)).astype(np.uint8)*255
rows=[]
for i in idx:
    cr=DT.crop_for(pws.page,c[i],sp,erase=erase)
    cr=cv2.resize(cr,(600,int(cr.shape[0]*600/cr.shape[1])))
    rows.append(cr if cr.ndim==3 else cv2.cvtColor(cr,cv2.COLOR_GRAY2BGR)); rows.append(np.full((6,600,3),128,np.uint8))
cv2.imwrite("/private/tmp/dtmiss/crops.png",np.vstack(rows))
