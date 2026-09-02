"""Where, exactly, does the crossing ink sit in the left region? Plot per-column
gap coverage over [x_start-6sp .. x_start+6sp] for a break gap vs interior gaps,
across editions, to fix the systemic-barline anchoring."""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import _harness as H


def profile(L, i, span_sp=6.0):
    staves = L.staves
    up, lo = staves[i], staves[i + 1]
    sp = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    xstart = int(statistics.median([s.x_start for s in staves]))
    x0 = max(0, int(xstart - span_sp * sp))
    x1 = min(L.binary.shape[1], int(xstart + span_sp * sp))
    top = up.bottom_y + 2
    bot = lo.top_y - 2
    band = (L.binary[top:bot, x0:x1] < 128).astype(np.uint8)
    k = max(3, int(round(sp * 0.6)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    cov = closed.mean(axis=0)
    # columns (rel to x_start, in sp) that clear 0.8
    hot = np.flatnonzero(cov > 0.8)
    rel_hot = sorted(set(round((c + x0 - xstart) / sp, 1) for c in hot))
    return sp, xstart, x0, rel_hot


def show(cid, gaps):
    case = next(c for c in H.all_cases(include_sweep=False) if c.cid == cid)
    L = H.load(case)
    print(f"\n{cid}: (x rel to median x_start, in staff-spaces, where a column is >0.8 inked over the gap)")
    for i, lbl in gaps:
        sp, xstart, x0, rel_hot = profile(L, i)
        # bucket the hot columns
        print(f"  gap {i:2d} [{lbl:10s}] hot cols (sp from x_start): {rel_hot}")


if __name__ == "__main__":
    show("B9-p60", [(11, "BREAK"), (0, "interior"), (5, "interior")])
    show("B5-p40", [(6, "BREAK"), (13, "BREAK"), (0, "interior"), (10, "interior")])
    show("lamer-p25", [(1, "interior"), (3, "interior"), (10, "interior")])
    show("LaMer-p20", [(8, "interior"), (10, "interior"), (0, "interior")])
    show("LaMer-p2", [(10, "BREAK"), (0, "interior"), (5, "interior")])
    show("Bolero-p2", [(6, "BREAK"), (1, "interior"), (9, "interior")])
