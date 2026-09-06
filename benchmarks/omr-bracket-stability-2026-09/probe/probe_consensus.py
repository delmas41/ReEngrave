"""Hypothesis: the bridging COUNT conflates two populations, and only one of
them is evidence about brackets.

A gap's count is (crossing objects) x (each object's width in px).  The objects
are of two kinds:

  * SYSTEMIC columns — the bracket, the systemic barline, the interior barlines,
    the final barline.  These stand at the SAME x in every gap of the system
    (up to the page's warp), and their number at a gap is the structural fact
    `_assign_groups` wants: on a bracket-group-barred page the interior barlines
    stop at the group edge, so a boundary gap keeps only the left-edge complex
    and the final barline.

  * INCIDENTAL ink — a stem, a slur, a long accent, a dynamic, a number — which
    stands wherever the music put it, i.e. at no shared x.

This probe re-counts each gap using only runs standing at a systemic column,
and prints both counts side by side so the two rules can be compared on the
same page.

Usage: probe_consensus.py PDF --page=38 [--tol-spacings=0.75] [--support=0.5]
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


def gap_runs(binary, upper, lower, x0, x1):
    height = binary.shape[0]
    top = max(0, upper.bottom_y + 2)
    bot = min(height, lower.top_y - 2)
    if bot <= top or x1 <= x0:
        return None
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    spacing = max(upper.line_spacing_px, lower.line_spacing_px)
    k = max(3, int(round(spacing * sg.BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    cols = (closed.mean(axis=0) > sg.BRIDGE_INK_FRACTION)
    runs, start = [], None
    for i, v in enumerate(cols):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append(((start + i) / 2 + x0, i - start))
            start = None
    if start is not None:
        runs.append(((start + len(cols)) / 2 + x0, len(cols) - start))
    return runs


def consensus_counts(runs_per_gap, tol, support):
    """Cluster run centres across gaps; keep clusters present in >= `support`
    of the gaps; per gap return how many such clusters it stands in."""
    centres = sorted((c, g) for g, runs in enumerate(runs_per_gap) for c, _w in runs)
    clusters: list[list[tuple[float, int]]] = []
    for c, g in centres:
        if clusters and c - clusters[-1][-1][0] <= tol:
            clusters[-1].append((c, g))
        else:
            clusters.append([(c, g)])
    n_gaps = len(runs_per_gap)
    systemic = [cl for cl in clusters
                if len({g for _c, g in cl}) >= max(2, round(support * n_gaps))]
    out = [0] * n_gaps
    for cl in systemic:
        for g in {g for _c, g in cl}:
            out[g] += 1
    return out, [round(statistics.median([c for c, _g in cl])) for cl in systemic]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--tol-spacings", type=float, default=0.75)
    ap.add_argument("--support", type=float, default=0.5)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    x0, x1 = sg._robust_x_window(staves)
    x0, x1 = max(0, x0), min(pi.binary.shape[1], x1)

    by_system: dict[int, list[int]] = {}
    for i, s in enumerate(staves):
        by_system.setdefault(s.system_index, []).append(i)

    for sys_idx in sorted(by_system):
        members = by_system[sys_idx]
        if len(members) < 3:
            continue
        spacing = statistics.median([staves[i].line_spacing_px for i in members])
        tol = args.tol_spacings * spacing
        runs_per_gap = [gap_runs(pi.binary, staves[i], staves[i + 1], x0, x1) or []
                        for i in members[:-1]]
        px = [int(sum(w for _c, w in r)) for r in runs_per_gap]
        cons, cols = consensus_counts(runs_per_gap, tol, args.support)
        m_px = statistics.median(px)
        m_c = statistics.median(cons)
        print(f"\n--- system {sys_idx}: {len(members)} staves  "
              f"spacing={spacing:.1f}  tol={tol:.0f}px  "
              f"systemic columns={len(cols)} @ {cols} ---")
        print(f"  {'gap':>3} {'px':>5} {'px/med':>7} {'split?':>6} | "
              f"{'runs':>4} {'cons':>4} {'c/med':>6} {'split?':>6}")
        for g in range(len(px)):
            print(f"  {g:>3} {px[g]:>5} {px[g]/m_px:>7.3f} "
                  f"{'SPLIT' if px[g] < m_px*0.5 else '':>6} | "
                  f"{len(runs_per_gap[g]):>4} {cons[g]:>4} "
                  f"{cons[g]/m_c if m_c else 0:>6.3f} "
                  f"{'SPLIT' if m_c and cons[g] < m_c*0.5 else '':>6}")


if __name__ == "__main__":
    main()
