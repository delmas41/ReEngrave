#!/usr/bin/env python3
"""Quantify the safety headroom of the left window edge.

The task's explicit concern: can median(x_start) sit RIGHT of the systemic
barline by enough that the barline leaves the scan window (dropped -> family
boundary reads 0 -> false over-split)?

We hold the RENDERED IMAGE fixed (the systemic barline stays where it is) and
artificially drift every staff's x_start rightward by `delta` px, then re-run
gap_bridging_counts. The window is median(x_start) - 4*spacing, so a rightward
x_start drift pushes the window's left edge right. We report the delta at which
the two family-boundary gaps (bridged ONLY by the systemic barline) collapse to
0 -- that delta is the headroom before the documented failure would occur.
"""
from __future__ import annotations
import sys, copy
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve(); WORKTREE = HERE.parents[3]
sys.path.insert(0, str(WORKTREE))
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr import system_grouping as SG

d = HERE.parent
for dpi, tag in [(186, "ss~12.8"), (107, "ss~7.5")]:
    pi = render_page(d/"one_system.pdf", 0, dpi=dpi)
    b = pi.binary; h, w = b.shape
    st0 = sorted(detect_staves(pi).staves, key=lambda s: s.top_y)
    sp = float(np.median([s.line_spacing_px for s in st0]))
    medx0 = int(np.median([s.x_start for s in st0]))
    # independently locate the systemic bar (family-boundary bridging column)
    u, l = st0[2], st0[3]                       # gap 2 = family boundary
    top, bot = u.bottom_y+2, l.top_y-2
    raw = ((b[top:bot, :] < 128).astype(np.uint8)).mean(axis=0)
    bar_cols = [x for x in np.flatnonzero(raw >= 0.8) if abs(x-medx0) < 3*sp]
    bar_x = bar_cols[0] if bar_cols else None
    print(f"\n{tag}  dpi={dpi}  ss={sp:.1f}px  median x_start={medx0}  "
          f"systemic bar x={bar_x} (x-rel {bar_x-medx0:+d})")
    print(f"  {'delta_px':>8} {'delta_sp':>8} {'win_left':>8} {'bar_in_win':>10} "
          f"{'gap2':>5} {'gap4':>5} {'n_systems':>9}")
    headroom = None
    for delta in range(0, int(round(9*sp))+1, max(1, int(round(sp/4)))):
        st = copy.deepcopy(st0)
        for s in st:
            s.x_start += delta
        x0w, x1w = SG._robust_x_window(st); x0w = max(0, x0w); x1w = min(w, x1w)
        cnt = SG.gap_bridging_counts(b, st)
        # replicate assign_systems break logic to get system count
        staves2 = copy.deepcopy(st)
        system = 0; staves2[0].system_index = 0
        for i, (uu, ll) in enumerate(zip(staves2, staves2[1:])):
            if SG._x_overlap_frac(uu, ll) <= SG.MIN_X_OVERLAP_FRAC:
                system += 1
            elif cnt[i] == 0:
                system += 1
            ll.system_index = system
        nsys = len(set(s.system_index for s in staves2))
        in_win = (x0w <= bar_x < x1w) if bar_x is not None else False
        if headroom is None and (cnt[2] == 0 or cnt[4] == 0):
            headroom = delta
        mark = "  <-- family boundary drops to 0 here" if (cnt[2]==0 or cnt[4]==0) and delta==headroom else ""
        print(f"  {delta:>8} {delta/sp:>8.1f} {x0w:>8} {str(in_win):>10} "
              f"{cnt[2]:>5} {cnt[4]:>5} {nsys:>9}{mark}")
    if headroom is not None:
        print(f"  HEADROOM: x_start must drift >= {headroom}px ({headroom/sp:.1f} staff-spaces) "
              f"RIGHT of its true position before the systemic barline is dropped.")
    else:
        print(f"  HEADROOM: family boundaries never dropped within tested range (>9 staff-spaces).")
