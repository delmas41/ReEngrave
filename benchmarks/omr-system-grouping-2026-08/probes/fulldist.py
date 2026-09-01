import sys, json
import numpy as np, cv2
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave')
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.system_grouping import (_robust_x_window, BRIDGE_INK_FRACTION,
                                       BRIDGE_GAP_TOLERANCE_SPACINGS)
def profile(binary, staves):
    h, w = binary.shape
    x0, x1 = _robust_x_window(staves); x0=max(0,x0); x1=min(w,x1)
    out=[]
    for up, lo in zip(staves, staves[1:]):
        top=max(0,up.bottom_y+2); bot=min(h,lo.top_y-2)
        if bot<=top or x1<=x0: out.append(None); continue
        band=(binary[top:bot, x0:x1]<128).astype(np.uint8)
        sp=max(up.line_spacing_px, lo.line_spacing_px)
        k=max(3,int(round(sp*BRIDGE_GAP_TOLERANCE_SPACINGS))*2+1)
        closed=cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k,1),np.uint8))
        cols=np.flatnonzero(closed.mean(axis=0)>BRIDGE_INK_FRACTION); W=x1-x0
        out.append({"n":int(cols.size),
                    "rightmost": float(cols.max())/W if cols.size else 0.0,
                    "span": float(cols.max()-cols.min())/W if cols.size else 0.0})
    return out
B9="tools/omr/training/data/imslp/beethoven-symphony-9/pdfs/imslp-516488/score.pdf"
B5=("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
    "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf")
CASES=[(B9,20,[11]),(B9,25,[11]),(B9,30,[]),(B9,35,[]),(B9,40,[]),(B9,45,[]),
       (B9,50,[]),(B9,55,[7]),(B9,60,[11]),(B9,65,[7]),(B9,70,[10]),(B9,75,[9]),
       (B5,10,[10]),(B5,40,[6,13]),(B5,47,[])]
brk, non = [], []
for pdf,page,breaks in CASES:
    pi=render_page(pdf,page,dpi=300); st=sorted(detect_staves(pi).staves,key=lambda s:s.top_y)
    for i,p in enumerate(profile(pi.binary, st)):
        if p is None: continue
        (brk if i in breaks else non).append({**p,"page":page,"i":i,
                                              "pdf":"B9" if pdf==B9 else "B5"})
def stats(rows, key):
    v=sorted(r[key] for r in rows); n=len(v)
    return f"n={n:3d} min={v[0]:.3f} p5={v[max(0,n//20)]:.3f} med={v[n//2]:.3f} max={v[-1]:.3f}"
print("TRUE BREAKS      rightmost:", stats(brk,"rightmost"))
print("NON-BREAKS       rightmost:", stats(non,"rightmost"))
print()
nz=[r for r in brk if r["n"]>0]
print("true breaks WITH bridging (the hard ones):")
for r in sorted(nz,key=lambda r:-r["rightmost"]):
    print(f"   {r['pdf']} p{r['page']} i={r['i']:2d}  n={r['n']:4d} rightmost={r['rightmost']:.3f} span={r['span']:.3f}")
print()
low=sorted(non,key=lambda r:r["rightmost"])[:6]
print("non-breaks with the LOWEST rightmost (closest false positives):")
for r in low:
    print(f"   {r['pdf']} p{r['page']} i={r['i']:2d}  n={r['n']:4d} rightmost={r['rightmost']:.3f} span={r['span']:.3f}")
json.dump({"brk":brk,"non":non}, open('/tmp/dist.json','w'))
