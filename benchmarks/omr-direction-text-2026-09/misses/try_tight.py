import json, os, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
import cv2, numpy as np
from tools.omr import direction_text as DT
from tools.omr import staff_labels_surya as SU
from tools.omr.direction_lexicon import lookup
def tight(pws, c, sp, padx=0.25, pady=0.2, margin=1.0):
    x0,y0,x1,y1=c.bbox_page
    px,py=int(padx*sp),int(pady*sp)
    H,W=pws.page.rgb.shape[:2]
    a,b,c2,d=max(0,x0-px),max(0,y0-py),min(W,x1+px),min(H,y1+py)
    cr=pws.page.rgb[b:d,a:c2]
    m=int(margin*sp)
    cr=cv2.copyMakeBorder(cr,m,m,m,m,cv2.BORDER_CONSTANT,value=(255,255,255))
    scale=min(DT.MAX_CROP_UPSCALE, DT.MIN_CROP_SPACING_PX/max(1.0,sp))
    if scale>1: cr=cv2.resize(cr,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
    return cr
cm=SU.worker_session(); cm.__enter__()
try:
  for tag in sys.argv[1:]:
    raw=json.load(open(f"/private/tmp/dtmiss/raw_{tag}.json"))["cands"]
    pws,pd=pickle.load(open(f"/private/tmp/dtmiss/{tag}.pkl","rb"))
    cands=DT.find_candidates(pws,pd)
    sp=float(np.median([DT._spacing(s) for s in pws.staves]))
    rd=dict(DT.default_readers(pws.page))
    todo=[i for i,r in enumerate(raw) if not (lookup(r["surya"]) or lookup(r["tesseract"]))]
    crops=[tight(pws,cands[i],sp) for i in todo]
    res={n:fn(crops) for n,fn in rd.items()}
    print("==",tag)
    for k,i in enumerate(todo):
        s,t=res["surya"][k],res["tesseract"][k]
        flag="NEW" if (lookup(s) or lookup(t)) else "   "
        print(flag,i,raw[i]["staff"],raw[i]["measure"],repr(s),repr(t),"| was",repr(raw[i]["surya"]),repr(raw[i]["tesseract"]))
finally: cm.__exit__(None,None,None)
