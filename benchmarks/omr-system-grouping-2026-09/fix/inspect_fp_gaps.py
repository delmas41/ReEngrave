"""Look at the low-cueA INTERIOR gaps on single-system control pages — the ones
that would make cue A false-fire. Crop each and report structure so we can see
whether a second cue can veto them."""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import _harness as H
import system_start_detector as D

CROPS = Path(__file__).with_name("crops")
TARGETS = {  # cid -> list of gap indices to inspect
    "LaMer-p20": None,   # auto-pick the lowest-cueA interior gaps
    "lamer-p25": None,
    "B9-p50": None,
    "Bolero-p2": None,   # interior_min=4 multi-system — check the tight interior gaps
}


def dump(L, i, cid, tag):
    staves = L.staves
    up, lo = staves[i], staves[i + 1]
    sp = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    xstart = int(statistics.median([s.x_start for s in staves]))
    y0 = max(0, up.top_y - int(1.5 * sp)); y1 = min(L.rgb.shape[0], lo.bottom_y + int(1.5 * sp))
    x0 = max(0, xstart - int(6 * sp)); x1 = min(L.rgb.shape[1], xstart + int(16 * sp))
    out = L.rgb[y0:y1, x0:x1].copy()
    cv2.line(out, (0, up.bottom_y - y0), (out.shape[1], up.bottom_y - y0), (255, 0, 0), 1)
    cv2.line(out, (0, lo.top_y - y0), (out.shape[1], lo.top_y - y0), (255, 0, 0), 1)
    cv2.line(out, (xstart - x0, 0), (xstart - x0, out.shape[0]), (0, 0, 255), 1)
    p = CROPS / f"FP_{cid}_gap{i}_{tag}.png"
    cv2.imwrite(str(p), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    return p.name


def main():
    for cid in TARGETS:
        case = next(c for c in H.all_cases(include_sweep=False) if c.cid == cid)
        L = H.load(case)
        gm = D.measure_page(L, left_sp=1.5, right_sp=1.5)
        interior = [(m.i, m.left_barline, m.bracket_cross, m.wide_bridging, m.gap_px)
                    for m in gm if not m.is_gt_break]
        interior.sort(key=lambda r: r[1])
        lows = interior[:3]
        print(f"\n{cid}: lowest-cueA interior gaps (i, cueA, bracket_cross, wide, gap_px):")
        for i, lb, bc, wb, gp in lows:
            name = dump(L, i, cid, "low")
            # also x_start spread of the two staves vs page median
            xs_up, xs_lo = L.staves[i].x_start, L.staves[i + 1].x_start
            xstart = int(statistics.median([s.x_start for s in L.staves]))
            print(f"   gap {i:2d}  cueA={lb:3d} bracket_cross={bc:3d} wide={wb:4d} gap_px={gp:3d} "
                  f"| x_start up/lo/med = {xs_up}/{xs_lo}/{xstart}   crop={name}")


if __name__ == "__main__":
    main()
