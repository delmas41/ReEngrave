import pickle, sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
import cv2, numpy as np
from tools.omr import direction_text as DT
tag = sys.argv[1]; sysi = int(sys.argv[2]) if len(sys.argv) > 2 else None
pws, pd = pickle.load(open(f"/private/tmp/dtmiss/{tag}.pkl", "rb"))
cands = DT.find_candidates(pws, pd)
print(len(cands), "candidates")
img = pws.page.rgb.copy()
for c in cands:
    a,b,c2,d = c.bbox_page
    cv2.rectangle(img,(a-2,b-2),(c2+2,d+2),(0,0,255),2)
for s in pws.staves:
    pass
sts=[s for s in pws.staves if sysi is None or s.system_index==sysi]
y0=int(min(s.top_y for s in sts))-150; y1=int(max(s.bottom_y for s in sts))+150
x0=int(min(s.x_start for s in sts))-50; x1=int(max(s.x_end for s in sts))+50
crop=img[max(0,y0):y1,max(0,x0):x1]
k=1400/crop.shape[1]; crop=cv2.resize(crop,None,fx=k,fy=k,interpolation=cv2.INTER_AREA)
cv2.imwrite(f"/private/tmp/dtmiss/cands_{tag}_{sysi}.png", crop)
