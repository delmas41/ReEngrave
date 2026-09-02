"""Step 5 — characterize WHY each of the 3 over-merges over-merged.

For each failure page and each TRUE-break gap, profile the crossing columns
(the ones the current wide-window rule counts as "bridging") and report WHERE
they sit, in staff-spaces relative to the page's median x_start. Contrast with
a within-system interior gap on the same page. Also dump a left-margin crop of
the true break so the ink can be eyeballed.

The question this answers: is the bridging ink at the true break a genuine
full-left systemic-barline column (in which case a narrow left-edge test won't
save us), or is it stray music ink far from x_start (in which case a positive
left-anchored cue is the right medicine)?
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import _harness as H
from tools.omr.system_grouping import (BRIDGE_GAP_TOLERANCE_SPACINGS,
                                        BRIDGE_INK_FRACTION)

CROPS = Path(__file__).with_name("crops")
CROPS.mkdir(exist_ok=True)


def crossing_columns(binary, up, lo, x0, x1, ink_fraction=BRIDGE_INK_FRACTION):
    """Replicate gap_bridging_counts' per-gap measurement, but RETURN the x
    indices (page px) of the crossing columns, not just the count."""
    h, w = binary.shape
    top = max(0, up.bottom_y + 2)
    bot = min(h, lo.top_y - 2)
    if bot <= top or x1 <= x0:
        return np.array([], dtype=int), (top, bot)
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    spacing = max(up.line_spacing_px, lo.line_spacing_px)
    k = max(3, int(round(spacing * BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    cols = np.flatnonzero(closed.mean(axis=0) > ink_fraction)
    return cols + x0, (top, bot)


def describe_gap(L, i, label):
    staves = L.staves
    up, lo = staves[i], staves[i + 1]
    x0, x1 = H._robust_x_window(staves)
    x0 = max(0, x0)
    x1 = min(L.binary.shape[1], x1)
    med_xstart = int(statistics.median([s.x_start for s in staves]))
    med_xend = int(statistics.median([s.x_end for s in staves]))
    spacing = statistics.median([s.line_spacing_px for s in staves]) or 1.0

    cols, (top, bot) = crossing_columns(L.binary, up, lo, x0, x1)
    n = cols.size
    # Position of crossing columns relative to median x_start, in staff-spaces.
    if n:
        rel = (cols - med_xstart) / spacing
        # How many crossing columns sit within 1.5 sp of x_start (the systemic
        # barline zone) vs out in the music (> 1.5 sp right of x_start)?
        near_left = int(np.sum(np.abs(rel) <= 1.5))
        in_music = int(np.sum(rel > 1.5))
        left_of_start = int(np.sum(rel < -1.5))
        rmin, rmax = float(rel.min()), float(rel.max())
    else:
        near_left = in_music = left_of_start = 0
        rmin = rmax = float("nan")

    print(f"    gap {i:2d} [{label}] gap_px={lo.top_y - up.bottom_y:3d} "
          f"bridging_n={n:4d}")
    print(f"        crossing-col x rel to x_start (sp): "
          f"min={rmin:6.1f} max={rmax:6.1f}  |  "
          f"near-left(|rel|<=1.5)={near_left}  left-margin(rel<-1.5)={left_of_start}  "
          f"in-music(rel>1.5)={in_music}")
    return dict(gap=i, label=label, n=int(n), near_left=near_left,
                in_music=in_music, left_of_start=left_of_start,
                med_xstart=med_xstart, med_xend=med_xend, spacing=spacing)


def dump_crop(L, i, cid):
    """Save a left-margin crop spanning [upper staff .. lower staff] around the
    break, ~10 staff-spaces wide from left of x_start."""
    staves = L.staves
    up, lo = staves[i], staves[i + 1]
    spacing = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    med_xstart = int(statistics.median([s.x_start for s in staves]))
    y0 = max(0, up.top_y - int(2 * spacing))
    y1 = min(L.rgb.shape[0], lo.bottom_y + int(2 * spacing))
    x0 = max(0, med_xstart - int(6 * spacing))
    x1 = min(L.rgb.shape[1], med_xstart + int(14 * spacing))
    crop = L.rgb[y0:y1, x0:x1]
    # annotate the gap band with a red rule at the two staff edges
    out = crop.copy()
    cv2.line(out, (0, (up.bottom_y - y0)), (out.shape[1], (up.bottom_y - y0)), (255, 0, 0), 1)
    cv2.line(out, (0, (lo.top_y - y0)), (out.shape[1], (lo.top_y - y0)), (255, 0, 0), 1)
    # blue vertical line at median x_start
    cv2.line(out, (med_xstart - x0, 0), (med_xstart - x0, out.shape[0]), (0, 0, 255), 1)
    path = CROPS / f"{cid}_break_gap{i}.png"
    cv2.imwrite(str(path), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    print(f"        crop -> {path.name}  ({out.shape[1]}x{out.shape[0]})")


def main():
    for case in H.FAILURES:
        L = H.load(case)
        staves = L.staves
        print(f"\n{'='*78}\n{case.cid}  ({len(staves)} staves)  GT breaks={sorted(L.gt_breaks)}  "
              f"bridging(all gaps)={L.bridging}")
        # True-break gaps
        for i in sorted(L.gt_breaks):
            describe_gap(L, i, "TRUE BREAK")
            dump_crop(L, i, case.cid)
        # A couple of interior (within-system) gaps for contrast: pick gaps
        # adjacent to the break and one far from it.
        interior = [i for i in range(len(staves) - 1) if i not in L.gt_breaks]
        # Sample: the gap just before the first break, the middle, and gap 0.
        sample = sorted(set([interior[0], interior[len(interior)//2], interior[-1]]))
        for i in sample:
            describe_gap(L, i, "interior")


if __name__ == "__main__":
    main()
