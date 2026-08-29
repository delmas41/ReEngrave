#!/usr/bin/env python3
"""Where does staff grouping have no boundary to work with?

`_group_into_staves` slides a 5-peak window and takes the first one whose gaps
are uniform. That is correct when staves are separated by a visible gap. When
several staves are set so tightly that the space BETWEEN them equals the line
spacing WITHIN them, the page presents one long uniform ladder, every phase
through it is equally uniform, and the grouper's choice is arbitrary — it takes
whichever phase the ladder happens to start on.

On Mahler 5 that guess is wrong by one line, which shifts every staff band by a
line spacing and drops the trumpet's notes into two neighbours' padding. See
STAFF_LADDER_PHASING.md.

This reports, per page, the maximal uniform ladders and whether each holds a
whole number of staves. A ladder whose length is not a multiple of five spans a
staff boundary the detector cannot see.

    python3 benchmarks/omr-orchestral-e2e/probe_staff_ladders.py
    python3 benchmarks/omr-orchestral-e2e/probe_staff_ladders.py --pdf X.pdf --page 0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2                                                  # noqa: E402
import numpy as np                                           # noqa: E402

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import (                    # noqa: E402
    _candidate_staff_rows,
    _group_into_staves,
    _ink_profile,
    detect_staves,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DEFAULTS = [
    (FIXTURES / "mahler-sym5-mvt1.pdf", 0),
    (FIXTURES / "brahms-sym1-mvt1.pdf", 0),
    (FIXTURES / "beethoven-sym5-mvt1.pdf", 0),
]


def ladders(peaks: list[int], tol: float = 0.25, max_gap: int = 70):
    """Split the line-rows into maximal runs of near-uniform spacing."""
    if not peaks:
        return []
    runs = [[peaks[0]]]
    for i in range(1, len(peaks)):
        d = peaks[i] - peaks[i - 1]
        prev = (runs[-1][-1] - runs[-1][-2]) if len(runs[-1]) >= 2 else d
        if d < max_gap and abs(d - prev) <= tol * max(prev, 1):
            runs[-1].append(peaks[i])
        else:
            runs.append([peaks[i]])
    return runs


def barline_groups(page) -> list[tuple[int, int, int]]:
    """(top, bottom, times_seen) for each repeated long vertical stroke.

    A barline is drawn once per bracket GROUP, not once per staff, and it is
    drawn identically at every measure — so the spans that recur across the page
    are the group extents. That makes them the most reliable structural signal
    available before staves are grouped, and nothing currently uses it.
    """
    from collections import Counter
    ink = (page.binary < 128).astype(np.uint8)
    vert = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 120))
    )
    n, _lab, stats, _c = cv2.connectedComponentsWithStats(vert, 8)
    spans = Counter()
    for i in range(1, n):
        x, y, w, h, _a = stats[i]
        if h < 120 or w > 25:
            continue
        spans[(int(y), int(y + h))] += 1
    return [(t, b, c) for (t, b), c in spans.most_common() if c >= 3]


def true_lines(page, y0: int, y1: int) -> list[int]:
    """Full-width staff lines between y0 and y1, over the best column found.

    Scanning several narrow columns and keeping the richest guards against a
    column that happens to sit under a beam or a thick rest, which merges rows
    and undercounts.
    """
    b = page.binary
    best: list[int] = []
    for x0 in range(700, max(701, page.width - 300), 100):
        x1 = x0 + 60
        col = (b[y0:y1, x0:x1] < 128).sum(axis=1)
        rows = [y + y0 for y, v in enumerate(col) if v > 0.9 * (x1 - x0)]
        groups: list[list[int]] = []
        for y in rows:
            if groups and y - groups[-1][-1] <= 3:
                groups[-1].append(y)
            else:
                groups.append([y])
        cents = [int(np.mean(g)) for g in groups if len(g) <= 7]
        if len(cents) > len(best):
            best = cents
    return best


def report(pdf: Path, page_index: int, dpi: int) -> None:
    page = render_page(pdf, page_index, dpi=dpi)
    peaks = [int(p) for p in _candidate_staff_rows(_ink_profile(page.binary),
                                                   page.width)]
    groups = _group_into_staves(peaks)
    staves = detect_staves(page).staves

    print(f"\n{pdf.name} p{page_index}: {len(peaks)} line-rows, "
          f"{len(groups)} staves grouped, "
          f"{len(peaks) - 5 * len(groups)} rows left over")
    ambiguous = 0
    for run in ladders(peaks):
        if len(run) < 6:
            continue  # a single staff, or too short to span a boundary
        spacing = (run[-1] - run[0]) // max(1, len(run) - 1)
        flag = "" if len(run) % 5 == 0 else "   <-- spans a boundary nothing can see"
        if len(run) % 5:
            ambiguous += 1
        print(f"   ladder {len(run):>3d} lines  {run[0]:>5d}..{run[-1]:<5d} "
              f"spacing~{spacing}  len%5={len(run) % 5}{flag}")
    print(f"   {ambiguous} ambiguous ladder(s); "
          f"{len(staves)} staves reported by detect_staves")

    groups = barline_groups(page)
    if groups:
        print("   barline groups (a barline spans a BRACKET GROUP, not a staff):")
        for top, bot, seen in sorted(groups)[:12]:
            lines = true_lines(page, top - 6, bot + 6)
            inside = [ln for ln in lines if top - 4 <= ln <= bot + 4]
            fits = "" if len(inside) % 5 == 0 else "   <-- not a whole number of 5-line staves"
            print(f"     {top:>5d}..{bot:<5d} seen {seen:>2d}x  "
                  f"{len(inside):>3d} full-width lines{fits}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=None)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args(argv)

    targets = [(args.pdf, args.page)] if args.pdf else DEFAULTS
    for pdf, page_index in targets:
        if not Path(pdf).is_file():
            print(f"missing: {pdf} — run orchestral_eval once to render it",
                  file=sys.stderr)
            continue
        report(Path(pdf), page_index, args.dpi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
