#!/usr/bin/env python3
"""Render a probe page with the flag-off and flag-on partitions painted, for
hand adjudication of every page the cue changed. Also dumps the per-gap
evidence at the changed gaps (bridging, pair-left count, band anchor)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parents[1]
sys.path.insert(0, str(WORKTREE_ROOT))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr import system_grouping as sg  # noqa: E402

LIBRARY_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_rel")
    ap.add_argument("page", type=int)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    page = render_page(LIBRARY_ROOT / args.pdf_rel, args.page, dpi=args.dpi)
    pws = detect_staves(page)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    off, _ = sg.assign_systems(page.binary, list(staves),
                               left_edge_split=True, choir_grouping=False)
    part_off = [s.system_index for s in off]
    on, _ = sg.assign_systems(page.binary, list(staves),
                              left_edge_split=True, choir_grouping=True)
    part_on = [s.system_index for s in on]

    bridging = sg.gap_bridging_counts(page.binary, staves)
    print(f"{len(staves)} staves; off={part_off}\n on={part_on}")
    for i, (u, l) in enumerate(zip(staves, staves[1:])):
        note = ""
        if part_off[i + 1] - part_off[i] != part_on[i + 1] - part_on[i]:
            note = "  <== CHANGED by cue B"
        pl = (sg.pair_left_edge_count(page.binary, u, l)
              if bridging[i] == 0 else None)
        print(f"gap[{i:2d}] s{u.staff_index}->s{l.staff_index} "
              f"y {u.bottom_y}-{l.top_y} bridging={bridging[i]} "
              f"overlap={sg._x_overlap_frac(u, l):.2f} "
              f"x_starts=({u.x_start},{l.x_start}) pair_left={pl}{note}")

    img = cv2.cvtColor(page.binary, cv2.COLOR_GRAY2BGR)
    for s, po, pn in zip(staves, part_off, part_on):
        color = (200, 200, 0)
        cv2.rectangle(img, (s.x_start, s.top_y), (s.x_end, s.bottom_y), color, 2)
        cv2.putText(img, f"off:{po} on:{pn}", (10, s.top_y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    scale = 1600 / img.shape[0]
    img = cv2.resize(img, (int(img.shape[1] * scale), 1600))
    cv2.imwrite(str(args.out), img)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
