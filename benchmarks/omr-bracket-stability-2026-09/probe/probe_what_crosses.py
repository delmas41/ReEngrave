"""What IS the bridging count made of?

`_assign_groups` compares a gap's crossing-COLUMN COUNT to the system median.
A count is not a thing on the page: it is (number of crossing objects) x (each
object's width in px).  This dumps the crossing columns as RUNS — contiguous
stretches of crossing x — so the two factors come apart, per gap.

Usage: probe_what_crosses.py PDF --page=38 [--system=0] [--dpi=600]
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402
from tools.omr import system_grouping as sg              # noqa: E402


def crossing_runs(binary, upper, lower, x0, x1):
    height = binary.shape[0]
    top = max(0, upper.bottom_y + 2)
    bot = min(height, lower.top_y - 2)
    if bot <= top or x1 <= x0:
        return None, None
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    spacing = max(upper.line_spacing_px, lower.line_spacing_px)
    k = max(3, int(round(spacing * sg.BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    cols = (closed.mean(axis=0) > sg.BRIDGE_INK_FRACTION)
    runs = []
    start = None
    for i, v in enumerate(cols):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start + x0, i + x0))
            start = None
    if start is not None:
        runs.append((start + x0, len(cols) + x0))
    return int(cols.sum()), runs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    x0, x1 = sg._robust_x_window(staves)
    x0 = max(0, x0)
    x1 = min(pi.binary.shape[1], x1)
    print(f"page {args.page}: {len(staves)} staves, window x={x0}..{x1}")

    by_system: dict[int, list[int]] = {}
    for i, s in enumerate(staves):
        by_system.setdefault(s.system_index, []).append(i)

    for sys_idx in sorted(by_system):
        members = by_system[sys_idx]
        print(f"\n--- system {sys_idx}: {len(members)} staves ---")
        counts = []
        for pos, i in enumerate(members[:-1]):
            up, lo = staves[i], staves[i + 1]
            n, runs = crossing_runs(pi.binary, up, lo, x0, x1)
            counts.append(n)
            gapy = lo.top_y - up.bottom_y
            widths = [b - a for a, b in runs] if runs else []
            print(f"  gap {pos:2d} (staff {i}->{i+1})  count={n:4d}  "
                  f"runs={len(runs):3d}  gap_px={gapy:4d}  band_px={lo.bottom_y-up.top_y:5d}  "
                  f"median_w={statistics.median(widths) if widths else 0:.0f}  "
                  f"group {staves[i].group_index}->{staves[i+1].group_index}")
            if runs and len(runs) <= 40:
                print("       x:", " ".join(f"{a}" for a, _b in runs))
        med = statistics.median([c for c in counts if c and c >= 0]) if counts else 0
        print(f"  median={med}  threshold={med * sg.GROUP_BOUNDARY_RATIO}")


if __name__ == "__main__":
    main()
