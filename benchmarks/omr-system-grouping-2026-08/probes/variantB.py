"""Reach measured against the two staves' OWN right end, not a page-wide window."""
import sys, glob
import numpy as np, cv2
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave')
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.system_grouping import (_robust_x_window, BRIDGE_INK_FRACTION,
                                       BRIDGE_GAP_TOLERANCE_SPACINGS)
def reaches(binary, staves):
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
        cols=np.flatnonzero(closed.mean(axis=0)>BRIDGE_INK_FRACTION)
        rightmost_px = (x0 + int(cols.max())) if cols.size else None
        # reference: the right end shared by THESE two staves
        own_end = min(up.x_end, lo.x_end)
        out.append({
            "win": float(cols.max())/(x1-x0) if cols.size else 0.0,
            # how far short of the staves' own right end the ink stops, in spacings
            "short_spacings": (own_end - rightmost_px)/sp if rightmost_px is not None else None,
        })
    return out
B9="tools/omr/training/data/imslp/beethoven-symphony-9/pdfs/imslp-516488/score.pdf"
B5=("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
    "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf")
L="/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores"
GT=[(B9,20,[11]),(B9,25,[11]),(B9,30,[]),(B9,55,[7]),(B9,60,[11]),(B9,70,[10]),
    (B5,10,[10]),(B5,40,[6,13]),(B5,47,[])]
OTHER=[(f"{L}/Mahler_5_.pdf",10,"1 system per LEGATO"),
       (f"{L}/IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf",20,"1 system"),
       (f"{L}/Haendel_Messiah_lead-sheet.pdf",20,"2 systems")]
brk,non=[],[]
for pdf,page,breaks in GT:
    pi=render_page(pdf,page,dpi=300); st=sorted(detect_staves(pi).staves,key=lambda s:s.top_y)
    for i,r in enumerate(reaches(pi.binary,st)):
        if r is None or r["short_spacings"] is None: continue
        (brk if i in breaks else non).append(r["short_spacings"])
print("GT pages — 'how many staff-spacings short of the staves own right end':")
print(f"  TRUE BREAKS n={len(brk):3d} min={min(brk):7.2f} max={max(brk):7.2f}")
print(f"  NON-BREAKS  n={len(non):3d} min={min(non):7.2f} max={max(non):7.2f}")
print()
print("the regressed corpora (all boundaries are WITHIN a system on these pages):")
for pdf,page,note in OTHER:
    pi=render_page(pdf,page,dpi=300); st=sorted(detect_staves(pi).staves,key=lambda s:s.top_y)
    vals=[r["short_spacings"] for r in reaches(pi.binary,st) if r and r["short_spacings"] is not None]
    wins=[r["win"] for r in reaches(pi.binary,st) if r]
    print(f"  {pdf.split('/')[-1][:34]:34s} p{page} ({note}): short min={min(vals):6.2f} max={max(vals):6.2f} | win-frac min={min(wins):.3f}")
