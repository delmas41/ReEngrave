import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, root, chdir_root, SCAN, ENGRAVED, CONTESTS
# ⚠️ `fixtures()` is the fail-loud one; importing it and then calling
# `glob.glob` yourself buys nothing. An unguarded glob that matches
# nothing prints a clean all-zero table and exits 0 — the failure this
# audit has now produced three ways. Fixed 2026-09-07.
chdir_root()

"""Replay _pair_ties_in_staff over committed transcriptions (read-only)."""
import json, glob, os
from collections import Counter
def replay(staff):
    ms=staff.get("measures",[])
    nh=[];ties=[]
    for m in ms:
        for d in m.get("detections",[]):
            bp=d.get("bbox_page")
            if not bp or len(bp)!=4: continue
            xc=bp[0]+bp[2]/2.0; yc=bp[1]+bp[3]/2.0
            if d.get("category")=="notehead": nh.append((xc,yc,bp[2],d))
            elif (d.get("class") or "").lower()=="tie": ties.append((bp,d))
    if not ties or len(nh)<2: return []
    avg=sum(d.get("bbox_page")[3] for _,_,_,d in nh)/len(nh)
    y_tol=max(avg*3,30); floor_binds = (avg*3) < 30
    out=[]
    for bp,_t in ties:
        tx0,ty0,tw,th=bp; tl=tx0; tr=tx0+tw; tyc=ty0+th/2.0
        bl=br=None; bld=brd=float("inf")
        for xc,yc,w,d in nh:
            if abs(yc-tyc)>y_tol: continue
            dl=tl-xc
            if 0<=dl<w*3 and dl<bld: bl=d; bld=dl
            dr=xc-tr
            if 0<=dr<w*3 and dr<brd: br=d; brd=dr
        out.append((bl,br,bld,brd,floor_binds,avg))
    return out
for fam,pat in (("scan",'benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json'),
                ("engraved",'benchmarks/omr-orchestral-e2e/fixtures/*.omr.json')):
    st=Counter(); dys=[]; pitchdiff=Counter(); floors=Counter(); avgs=[]
    for f in fixtures(pat):
        d=json.load(open(f))
        for pg in d["pages"]:
            for sy in pg["systems"]:
                for stf in sy["staves"]:
                    for bl,br,bld,brd,fb,avg in replay(stf):
                        st['ties']+=1; floors[fb]+=1; avgs.append(avg)
                        if bl is not None and br is not None and bl is not br:
                            st['paired']+=1
                            y1=bl["bbox_page"][1]+bl["bbox_page"][3]/2.0
                            y2=br["bbox_page"][1]+br["bbox_page"][3]/2.0
                            dys.append(abs(y1-y2)/max(avg,1))
                            p1,p2=bl.get("pitch"),br.get("pitch")
                            pitchdiff[(p1 is not None and p2 is not None and p1==p2)
                                      if (p1 and p2) else None]+=1
                        elif bl is None and br is None: st['no side']+=1
                        else: st['ONE side only']+=1
    print(f"=== {fam}")
    print("  ", dict(st))
    print("   y_tol 30px floor binds:", dict(floors), " median avg notehead h:",
          round(sorted(avgs)[len(avgs)//2],1) if avgs else None)
    if dys:
        dys.sort(); n=len(dys); q=lambda p: round(dys[int(p*n)],2)
        print(f"   |dy| between the two paired heads, in notehead heights: "
              f"median={q(.5)} p90={q(.9)} p99={q(.99)} max={round(dys[-1],2)}")
        print(f"   pairs whose two heads differ in y by >0.5 nh: "
              f"{sum(1 for v in dys if v>0.5)} of {n}")
    print("   paired heads with SAME resolved pitch (True/False/unknown):", dict(pitchdiff))
