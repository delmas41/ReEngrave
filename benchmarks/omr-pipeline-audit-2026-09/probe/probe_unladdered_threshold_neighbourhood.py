import json, glob, os
from collections import Counter
ROOT="/Users/seanjohnson/Desktop/ReEngrave"
def bands(st):
    g=st.get("staff_geometry") or {}
    ys=g.get("line_ys_page")
    if not ys or len(ys)<2: return None
    return min(ys), max(ys), (max(ys)-min(ys))/(len(ys)-1)
for fam,pat in (("scan",f"{ROOT}/benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json"),
                ("engraved",f"{ROOT}/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json")):
    hist=Counter(); inside=Counter(); tot_out=0; tot_in=0
    for f in sorted(glob.glob(pat)):
        d=json.load(open(f))
        for pg in d.get("pages",[]):
            for sy in pg.get("systems",[]):
                for st in sy.get("staves",[]):
                    b=bands(st)
                    if not b: continue
                    top,bot,sp=b
                    if sp<=0: continue
                    for m in st.get("measures",[]):
                        for det in m.get("detections",[]):
                            if det.get("category")!="notehead": continue
                            bb=det.get("bbox_page")
                            if not bb or len(bb)!=4: continue
                            yc=bb[1]+bb[3]/2.0
                            dist = top-yc if yc<top else (yc-bot if yc>bot else 0.0)
                            n_exp = int(dist/sp + 0.25)
                            c=det.get("confidence") or 0
                            bucket=round(min(0.999,c)*20)/20
                            if n_exp>=1:
                                tot_out+=1; hist[bucket]+=1
                            else:
                                tot_in+=1; inside[bucket]+=1
    print(f"=== {fam}: kept noteheads inside-ladder-zone={tot_in} OUTSIDE (n_expected>=1)={tot_out}")
    print("  OUTSIDE-staff kept noteheads, confidence histogram (0.05 buckets):")
    for k in sorted(hist): print(f"    {k:.2f}: {hist[k]}")
    print(f"  of these, in [0.65,0.75): {sum(v for k,v in hist.items() if 0.65<=k<0.75)}"
          f"   in [0.75,0.85): {sum(v for k,v in hist.items() if 0.75<=k<0.85)}")
