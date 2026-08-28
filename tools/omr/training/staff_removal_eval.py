"""How much of the staff lines does removal actually clear, and what does it
cost in symbol ink?

`staff_line_removal` is judged by two numbers pulling against each other. Clear
more line ink and the image gets cleaner for every consumer of
`image_no_staff`; clear too much and you are erasing the music. Either one
alone is easy to win — erase nothing, or erase everything — so this reports
both and neither should be read without the other.

    line_ink_cleared_pct   of the ink within BAND_SPACES of a nominal line row,
                           how much removal took. Higher is better.
    off_line_removed_pct   of ALL ink in the cell, how much was removed away
                           from any line row. Lower is better; this is the
                           counter-metric, and some of it is legitimate (a line
                           that has wandered outside the band is still a line).

The band is fixed rather than derived from the measured thickness, so that two
arms of an experiment are compared on identical ground.

Usage:

    PYTHONPATH=. python3 -m tools.omr.training.staff_removal_eval
    PYTHONPATH=. python3 -m tools.omr.training.staff_removal_eval --json-out out.json

Baseline, 2026-08-28, one page per score at 600 DPI:

    score      cells   cleared%   off-line%   line thickness (staff spaces)
    WTC           28       65.9        0.00       0.134
    Boléro       203       66.4        0.14       0.148
    Mahler 5     247       78.8        1.02       0.242
    Beethoven 5  302       69.3        4.30       0.254
    La Mer        42       78.0        6.50       0.207

Re-measure after any Phase-1 change, because the cell set moves under it: the
staff-recovery and system-grouping work took Mahler from 234 cells to 247 and
La Mer from 70 to 42, and the second of those took off-line removal from 3.31%
to 6.50%. That is the largest counter-metric figure in the corpus and nothing
here caused it — it is worth a look on its own.

Those are the first line-thickness figures measured on real scans rather than
synthetically, and they sit inside the 0.06-0.31 staff-space range this
module's docstring cites — Beethoven and Mahler are printed about twice as
heavily as the Bach.

Thickness is reported in STAFF SPACES, against each cell's own spacing. It is
tempting to read the canonical-pixel figure as hundredths of a space, since a
cell is scaled to a 400px staff span and therefore a 100px spacing — but only
when the scale is set by height. A cell wide enough to hit `MAX_CELL_WIDTH_PX`
is scaled by width instead and its spacing comes out well under 100 (about 46
on the WTC page), so that shortcut understates thickness by more than a factor
of two on exactly the keyboard scores where measures are widest.

DISPROVEN HERE — do not retry without new evidence
--------------------------------------------------
Phase 1 now measures each staff's line thickness and wander off the WHOLE staff,
reading each line only where no glyph sits on it (`staff_detector.
measure_line_geometry`), and hands both to every cell. The obvious next step is
to feed those to this module in place of the two constants that stand in for
them — `MAX_LINE_THICKNESS_SPACES`, which caps a per-CELL thickness median, and
`LINE_SEARCH_RADIUS_SPACES`, a fixed guess at the wander. The reasoning was that
a per-cell median is taken over whatever columns that cell happens to have, and
on a dense one most of them carry a symbol.

Measured on this harness, it does not help. (Run against the pre-merge tree,
so the deltas below are against the older baseline in this file's history —
the conclusion does not depend on the cell set, since it rests on the two
thickness estimates agreeing, which is a property of the ink.)

  * Substituting the per-staff thickness moves cleared% by -0.7 to +0.2 across
    the five scores — slightly WORSE on three of them — while off-line removal
    falls by at most 0.09pp. A wash, and on the primary metric a small loss.
  * Narrowing the search radius to the measured wander changes nothing at all,
    on any score, to one decimal place. The constant is over-generous (25px
    canonical against ~10px needed) but the anchor never strays that far, so
    tightening it buys nothing.

The reason is that the two thickness estimates simply agree. Per-cell vs
per-staff, median disagreement is 2.4% (Beethoven), 3.1% (Mahler), 7.3% (WTC).
Only Beethoven has a meaningful tail — 32 of 302 cells differing by >25% — and
even restricted to those cells, cleared% is 55.6% with the per-cell estimate
against 55.7% with the per-staff one.

So the cap is not a weak guess in practice; it does its job, and the redundancy
between the two measurements is costing no accuracy. The per-staff figures earn
their keep as a RECORD of what erasure destroys (they reach the output JSON as
`staff_geometry.line_thickness_px` / `.line_wander_px`), not as an input here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..measure_extractor import detect_barlines, extract_measures
from ..preprocessing import render_page
from ..staff_detector import detect_staves
from ..staff_line_removal import remove_staff_lines


SCORE_DIR = Path(
    "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus"
)

# One page per score, chosen to span the printed-thickness range. Paths are the
# author's local corpus; missing scores are skipped, not an error.
CORPUS: list[tuple[str, Path, int]] = [
    ("WTC", SCORE_DIR / "PDF Scores"
     / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 5),
    ("Bolero", SCORE_DIR / "PDF Scores"
     / "IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 31),
    ("Mahler5", SCORE_DIR / "PDF Scores" / "Mahler_5_.pdf", 11),
    ("Beethoven5", SCORE_DIR
     / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 10),
    ("LaMer", SCORE_DIR / "PDF Scores"
     / "IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf", 12),
]

# Half-height of the band counted as "on a staff line", in staff spaces. Fixed
# on purpose — see the module docstring.
BAND_SPACES = 0.25


def score_page(name: str, pdf: Path, page_index: int, dpi: int = 600) -> dict:
    """Run Phase 1 + removal on one page and reduce it to the two numbers."""
    page = render_page(pdf, page_index, dpi=dpi)
    cells = extract_measures(detect_barlines(detect_staves(page)))
    remove_staff_lines(cells)

    line_ink = cleared = off_removed = total_ink = 0
    thicknesses: list[float] = []
    for cell in cells:
        before = getattr(cell, "binary", None)
        after = cell.image_no_staff
        ys = cell.staff_line_ys_canonical
        if before is None or after is None or len(ys) < 2:
            continue
        spacing = (ys[-1] - ys[0]) / 4.0
        radius = max(1, int(round(BAND_SPACES * spacing)))
        band = np.zeros(before.shape[0], dtype=bool)
        for y in ys:
            band[max(0, y - radius): y + radius + 1] = True

        ink_before = before == 0
        removed = ink_before & (after != 0)
        line_ink += int((ink_before & band[:, None]).sum())
        cleared += int((removed & band[:, None]).sum())
        off_removed += int((removed & ~band[:, None]).sum())
        total_ink += int(ink_before.sum())
        if cell.staff_line_thickness_canonical and spacing > 0:
            # Against THIS cell's spacing — see the note in the module
            # docstring on why the canonical pixel count is not divisible by a
            # constant 100.
            thicknesses.append(cell.staff_line_thickness_canonical / spacing)

    return {
        "score": name,
        "page_index": page_index,
        "cells": len(cells),
        "line_ink_cleared_pct": round(100 * cleared / max(1, line_ink), 1),
        "off_line_removed_pct": round(100 * off_removed / max(1, total_ink), 2),
        "line_thickness_spaces": (
            round(float(np.median(thicknesses)), 3) if thicknesses else None
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--only", default=None,
                    help="run one score by name (e.g. Mahler5)")
    args = ap.parse_args()

    print(f"{'score':<12}{'cells':>6}{'cleared%':>10}{'off-line%':>11}"
          f"{'thick(sp)':>11}")
    results = []
    for name, pdf, page_index in CORPUS:
        if args.only and name != args.only:
            continue
        if not pdf.exists():
            print(f"{name:<12}{'— score not present, skipped':>38}")
            continue
        r = score_page(name, pdf, page_index, dpi=args.dpi)
        results.append(r)
        print(f"{r['score']:<12}{r['cells']:>6}{r['line_ink_cleared_pct']:>10.1f}"
              f"{r['off_line_removed_pct']:>11.2f}"
              f"{r['line_thickness_spaces'] or float('nan'):>11.3f}")

    if args.json_out:
        args.json_out.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
