"""Do the interior barlines really STOP at the gap the fix calls a boundary?

The fix's whole premise. Rather than eyeball a crop, this measures the ink
coverage of the system's own barline columns in each gap band: at an interior
gap a barline column is near-solid; at a group boundary, if the premise holds,
those same columns are near-empty and whatever crossing ink the gap does carry
stands somewhere else.

Barline columns are taken from a reference gap (the system's median-crossing
gap), so the boundary gap is judged against columns it did not help choose.

Usage: probe_barlines_stop.py PDF --page=38 --system=0
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


def band_cover(binary, upper, lower, x0, x1):
    top = max(0, upper.bottom_y + 2)
    bot = min(binary.shape[0], lower.top_y - 2)
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    spacing = max(upper.line_spacing_px, lower.line_spacing_px)
    k = max(3, int(round(spacing * sg.BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    return closed.mean(axis=0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--system", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    x0, x1 = sg._robust_x_window(staves)
    x0, x1 = max(0, x0), min(pi.binary.shape[1], x1)
    members = [i for i, s in enumerate(staves) if s.system_index == args.system]
    gaps = members[:-1]
    covers = [band_cover(pi.binary, staves[i], staves[i + 1], x0, x1) for i in gaps]
    spacing = statistics.median([staves[i].line_spacing_px for i in members])

    # reference gap = the one whose crossing count is the system's median
    counts = [int((c > sg.BRIDGE_INK_FRACTION).sum()) for c in covers]
    med = statistics.median(counts)
    ref = min(range(len(counts)), key=lambda g: abs(counts[g] - med))
    cols = (covers[ref] > sg.BRIDGE_INK_FRACTION)
    refs, start = [], None
    for i, v in enumerate(cols):
        if v and start is None:
            start = i
        elif not v and start is not None:
            refs.append((start + i) // 2)
            start = None
    print(f"reference gap {ref} contributes {len(refs)} columns at "
          f"x={[c + x0 for c in refs]}")
    print(f"\n{'gap':>3}  " + "  ".join(f"{c + x0:>5}" for c in refs)
          + "   | max coverage at those columns")
    for g in range(len(gaps)):
        vals = [covers[g][max(0, c - 3):c + 4].max() for c in refs]
        print(f"{g:>3}  " + "  ".join(f"{v:5.2f}" for v in vals)
              + f"   | {max(vals):.2f}  group "
              f"{staves[gaps[g]].group_index}->{staves[gaps[g] + 1].group_index}")


if __name__ == "__main__":
    main()
