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
