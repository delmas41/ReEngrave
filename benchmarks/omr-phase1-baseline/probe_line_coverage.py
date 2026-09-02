"""Does row COVERAGE separate a misfitted staff window from a healthy one?

`staff_detector` step 3d already slides a five-line window back onto the staff
it missed, and it decides using LINE THICKNESS: an end line far thicker than the
group's median is a beam, not a staff line. That caught Brahms's contrabass
(18px against 5px, ratio 3.6) and does NOT catch its Violin 1, whose window sits
TWO spaces high with thicknesses [9, 8, 5, 4, 5] — a ratio of 1.8, inside the
normal range for a clean staff on the same page.

The signal that does separate them is how far the row's ink RUNS. A printed
staff line spans the staff; the two rows Violin 1 locked onto are ledger lines
under a high violin line and cover 44% and 49% of it. `_longest_row_run` already
computes exactly that, one line below in the same function, as the rule's
CONFIRMATION gate — it is not consulted as a detection signal.

Before changing the rule, this asks the corpus whether that is generally true:
per staff, the coverage of each of its five lines against the staff's own
x-extent, and whether END-line coverage being an outlier is rare on staves that
are placed correctly. A signal that fires on healthy staves is not a signal, and
the repository's history is mostly thresholds that looked clean on one corpus.

    python3 benchmarks/omr-phase1-baseline/probe_line_coverage.py
    python3 benchmarks/omr-phase1-baseline/probe_line_coverage.py --json out.json

Corpus is `phase1_layout_eval.CORPUS` (12 pages, 5 editions) plus the three
engraved orchestral fixtures, so the one known misfit is in the sample and the
scanned pages that must not regress are too.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import (  # noqa: E402
    _longest_row_run,
    _staff_x_extent,
    detect_staves,
    measure_line_geometry,
)
from tools.omr.training.phase1_layout_eval import CORPUS  # noqa: E402

FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
EXTRA = [
    ("brahms-e2e", FIXTURES / "brahms-sym1-mvt1.pdf", 0, 600),
    ("beethoven-e2e", FIXTURES / "beethoven-sym5-mvt1.pdf", 0, 600),
    ("mahler-e2e", FIXTURES / "mahler-sym5-mvt1.pdf", 0, 600),
]


def probe_page(key: str, pdf: Path, page_index: int, dpi: int) -> list[dict[str, Any]]:
    page = render_page(pdf, page_index, dpi=dpi)
    staved = detect_staves(page)
    spacing = statistics.median(
        [(s.line_ys[-1] - s.line_ys[0]) / 4.0 for s in staved.staves
         if len(s.line_ys) == 5] or [0.0])
    rows = []
    for staff in staved.staves:
        if len(staff.line_ys) != 5:
            continue
        x0, x1 = _staff_x_extent(page.binary, staff.line_ys, spacing)
        width = max(1, x1 - x0)
        coverage = [
            _longest_row_run(page.binary, y, spacing, x0, x1 + 1)[2] / width
            for y in staff.line_ys
        ]
        measured = measure_line_geometry(page.binary, staff.line_ys, x0, x1)
        thickness = measured[0] if measured else None
        rows.append({
            "page": key,
            "staff_index": staff.staff_index,
            "line_ys": list(staff.line_ys),
            "coverage": [round(c, 3) for c in coverage],
            "min_coverage": round(min(coverage), 3),
            "median_coverage": round(statistics.median(coverage), 3),
            # The two candidate signals, side by side, for the same staves.
            "end_coverage_deficit": round(
                statistics.median(coverage) - min(coverage[0], coverage[-1]), 3),
            "thickness": thickness,
            "thickness_ratio": (
                round(max(thickness) / statistics.median(thickness), 2)
                if thickness and statistics.median(thickness) > 0 else None),
            "wander": measured[1] if measured else None,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--only", default=None, help="substring of the page key")
    args = ap.parse_args(argv)

    rows: list[dict[str, Any]] = []
    for key, pdf, page_index, dpi in list(CORPUS) + EXTRA:
        if args.only and args.only not in key:
            continue
        if not Path(pdf).exists():
            print(f"{key:15s} SKIP (missing {Path(pdf).name})", file=sys.stderr)
            continue
        page_rows = probe_page(key, Path(pdf), page_index, dpi)
        rows.extend(page_rows)
        worst = max(page_rows, key=lambda r: r["end_coverage_deficit"],
                    default=None)
        print(f"{key:15s} staves={len(page_rows):3d}  "
              f"worst end-coverage deficit "
              f"{worst['end_coverage_deficit'] if worst else 0:.3f} "
              f"(staff {worst['staff_index'] if worst else '-'}, "
              f"thickness ratio {worst['thickness_ratio'] if worst else '-'})")

    if rows:
        deficits = sorted(r["end_coverage_deficit"] for r in rows)
        print(f"\n{len(rows)} staves. end-coverage deficit "
              f"(median coverage minus the worse END line):")
        for q in (0.5, 0.9, 0.95, 0.99, 1.0):
            i = min(len(deficits) - 1, int(q * len(deficits)))
            print(f"  p{int(q * 100):>3d}  {deficits[i]:.3f}")
        print("\n  the ten worst:")
        for r in sorted(rows, key=lambda r: -r["end_coverage_deficit"])[:10]:
            print(f"    {r['page']:15s} staff {r['staff_index']:>2d}  "
                  f"deficit {r['end_coverage_deficit']:.3f}  "
                  f"coverage {r['coverage']}  "
                  f"thickness_ratio {r['thickness_ratio']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
