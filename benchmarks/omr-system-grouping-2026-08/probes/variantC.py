"""The band the docstring SPECIFIES: top line of upper staff -> bottom line of lower."""
import sys
import numpy as np, cv2
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave')
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.system_grouping import (_robust_x_window, BRIDGE_INK_FRACTION,
                                       BRIDGE_GAP_TOLERANCE_SPACINGS)
def counts(binary, staves, through_staves):
    h, w = binary.shape
    x0, x1 = _robust_x_window(staves); x0=max(0,x0); x1=min(w,x1)
    out=[]
    for up, lo in zip(staves, staves[1:]):
        if through_staves:
            top, bot = max(0, up.top_y), min(h, lo.bottom_y)      # as documented
        else:
            top, bot = max(0, up.bottom_y+2), min(h, lo.top_y-2)  # as implemented
        if bot<=top or x1<=x0: out.append(-1); continue
        band=(binary[top:bot, x0:x1]<128).astype(np.uint8)
        sp=max(up.line_spacing_px, lo.line_spacing_px)
        k=max(3,int(round(sp*BRIDGE_GAP_TOLERANCE_SPACINGS))*2+1)
        closed=cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k,1),np.uint8))
        out.append(int((closed.mean(axis=0)>BRIDGE_INK_FRACTION).sum()))
    return out
B9="tools/omr/training/data/imslp/beethoven-symphony-9/pdfs/imslp-516488/score.pdf"
B5=("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
    "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf")
L="/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores"
GT=[(B9,20,[11]),(B9,25,[11]),(B9,30,[]),(B9,35,[]),(B9,40,[]),(B9,45,[]),(B9,50,[]),
    (B9,55,[7]),(B9,60,[11]),(B9,65,[7]),(B9,70,[10]),(B9,75,[9]),
    (B5,10,[10]),(B5,40,[6,13]),(B5,47,[])]
brk,non=[],[]
for pdf,page,breaks in GT:
    pi=render_page(pdf,page,dpi=300); st=sorted(detect_staves(pi).staves,key=lambda s:s.top_y)
    for i,c in enumerate(counts(pi.binary,st,True)):
        if c<0: continue
        (brk if i in breaks else non).append((c,page,i))
bv=sorted(x[0] for x in brk); nv=sorted(x[0] for x in non)
print("BAND THROUGH BOTH STAVES (as documented):")
print(f"  TRUE BREAKS n={len(bv):3d} values={bv}")
print(f"  NON-BREAKS  n={len(nv):3d} min={nv[0]} p5={nv[max(0,len(nv)//20)]} med={nv[len(nv)//2]} max={nv[-1]}")
print(f"  separation: max(break)={max(bv)}  vs  min(non-break)={nv[0]}")
print()
print("same measurement on the corpora the last attempt broke (all within-system):")
for name,page in ((f"{L}/Mahler_5_.pdf",10),(f"{L}/IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf",20),
                  (f"{L}/Haendel_Messiah_lead-sheet.pdf",20),(f"{L}/IMSLP421137-PMLP03667-Ravel_Bolero.pdf",2)):
    pi=render_page(name,page,dpi=300); st=sorted(detect_staves(pi).staves,key=lambda s:s.top_y)
    c=[x for x in counts(pi.binary,st,True) if x>=0]
    z=sum(1 for x in c if x==0)
    print(f"  {name.split('/')[-1][:34]:34s} p{page}: n={len(c):2d} min={min(c):4d} zeros={z}  values={sorted(c)[:8]}...")
