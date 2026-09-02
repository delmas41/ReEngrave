#!/usr/bin/env python3
"""Real family-broken pages: does a systemic barline physically present at the
left edge ever fall OUTSIDE the pipeline scan window? No grouping ground truth
here; this shows whether the left-edge-drop effect appears on real scans."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, cv2, fitz

HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[3]
sys.path.insert(0, str(WORKTREE))
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr import system_grouping as SG

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
PAGES = [
    ("Mahler5", MAIN/"library/editions/mahler/symphony-5/mahler--symphony-5--unidentified-scan-2016--local.pdf", [9, 10]),
    ("LaMer",   MAIN/"library/editions/debussy/la-mer-cd-111/debussy--la-mer-cd-111--durand-fils--imslp15420.pdf", [1, 2]),
]
TARGET_H = 3300

def dpi_for(pdf):
    doc = fitz.open(pdf); h_in = doc[0].rect.height/72; doc.close()
    return round(TARGET_H / h_in)

def run(name, pdf, page_idx):
    dpi = dpi_for(pdf)
    pi = render_page(pdf, page_idx, dpi=dpi)
    b = pi.binary; h, w = b.shape
    st = sorted(detect_staves(pi).staves, key=lambda s: s.top_y)
    if len(st) < 2:
        print(f"\n### {name} p{page_idx} (dpi={dpi}, {w}x{h}) -> {len(st)} staves; skip")
        return
    sp = float(np.median([s.line_spacing_px for s in st]))
    medx = int(np.median([s.x_start for s in st]))
    x0w, x1w = SG._robust_x_window(st); x0w=max(0,x0w); x1w=min(w,x1w)
    bridging = SG.gap_bridging_counts(b, st)
    systems = [s.system_index for s in st]
    print("\n" + "#"*76)
    print(f"### {name} p{page_idx}  dpi={dpi}  {w}x{h}px  ss={sp:.1f}px  n_staves={len(st)}")
    print(f"    systems -> {len(set(systems))}: {systems}")
    print(f"    median x_start={medx}  window=[{x0w}..{x1w}]  (left margin {medx-x0w}px = {(medx-x0w)/sp:.1f}sp)")
    print(f"    x_start spread: min={min(s.x_start for s in st)} med={medx} max={max(s.x_start for s in st)}")

    # For each gap, INDEPENDENT full-width scan of the physical gap.
    print(f"    {'gap':>3} {'y':>11} {'pipe':>4} {'sys':>3} | leftmost bridging cols (x-rel to med x_start); any LEFT of window?")
    for i,(u,l) in enumerate(zip(st,st[1:])):
        top=max(0,u.bottom_y+2); bot=min(h,l.top_y-2)
        if bot<=top:
            print(f"    {i:>3} {'degenerate':>11} {bridging[i]:>4} {l.system_index:>3} | -")
            continue
        spg=max(u.line_spacing_px,l.line_spacing_px)
        k=max(3,int(round(spg*SG.BRIDGE_GAP_TOLERANCE_SPACINGS))*2+1)
        band=(b[top:bot,:]<128).astype(np.uint8)
        closed=cv2.morphologyEx(band,cv2.MORPH_CLOSE,np.ones((k,1),np.uint8))
        cov=closed.mean(axis=0)
        cols=np.flatnonzero(cov>=SG.BRIDGE_INK_FRACTION)
        # bridging columns that lie LEFT of the pipeline window left edge:
        left_missed=[int(c) for c in cols if c < x0w]
        # bridging columns near the left edge (candidate systemic bar): within
        # 2 spaces either side of med x_start
        nearleft=[int(c) for c in cols if abs(c-medx)<=2*sp]
        relshow=[int(c-medx) for c in cols[:10]]
        flag=""
        if left_missed:
            flag=f"  <<< {len(left_missed)} bridging col(s) LEFT of window x<{x0w}: {left_missed[:6]}"
        print(f"    {i:>3} {u.bottom_y:>5}->{l.top_y:<5} {bridging[i]:>4} {l.system_index:>3} | "
              f"n={len(cols):>3} nearleft={len(nearleft)} x-rel={relshow}{flag}")
    return dict(name=name, page=page_idx, dpi=dpi, n_staves=len(st),
                n_systems=len(set(systems)), window=(x0w,x1w), medx=medx)

if __name__=="__main__":
    out=[]
    for name,pdf,pages in PAGES:
        for pidx in pages:
            try:
                r=run(name,pdf,pidx)
                if r: out.append(r)
            except Exception as e:
                print(f"\n### {name} p{pidx}: ERROR {type(e).__name__}: {e}")
    import json
    (HERE.parent/"real_results.json").write_text(json.dumps(out,indent=2,default=str))
    print("\nwrote real_results.json")
