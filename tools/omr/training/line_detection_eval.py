"""Phase 4f ground truth — stems and beams against a known-by-construction sheet.

`line_detection` (stems, beams) had no ground truth at all. That gap became
concrete when staff-line removal was fixed: Mahler's stem count moved 178 -> 145
and there was no way to say whether that was 33 artefacts removed or 33 stems
lost. This module removes the excuse.

The truth comes from LilyPond rather than from a human counting a scan. A
reference sheet (`benchmarks/omr-phase4-lines/reference-lines.ly`) is engraved
with a known number of stems and beam bars in every measure, so the expected
counts are exact, free, and reproducible on any machine with LilyPond.

The same music is engraved at several staff-line THICKNESSES, which is the point:
thick lines are the regime where staff-line removal used to be a no-op, and
where any future change to it will show up first. Line thickness is reported in
staff spaces, so the sheets can be compared with real scores (measured across
the corpus: WTC 0.06, Boléro 0.09, Mahler 0.23, Beethoven 5 0.25 spaces).

    python3 -m tools.omr.training.line_detection_eval
    python3 -m tools.omr.training.line_detection_eval --keep-dir /tmp/refsheets

Counts are compared per STAFF over the whole page, not per cell. Measure
segmentation is not perfectly stable across thicknesses — at thickness 1 the
barline before the chord measure is missed, fusing two measures into one cell —
and a per-cell comparison would report that segmentation difference as a
stem/beam error, which it is not.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tools.omr.preprocessing import render_page, binarize
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import detect_barlines, extract_measures
from tools.omr.staff_line_removal import remove_staff_lines
from tools.omr.line_detection import detect_lines


BENCH_DIR = Path("benchmarks/omr-phase4-lines")
TEMPLATE = BENCH_DIR / "reference-lines.ly"
GROUND_TRUTH_PATH = BENCH_DIR / "ground-truth.json"
THICKNESSES = (1, 2, 3, 4)


def engrave(thickness: int, out_dir: Path) -> Path:
    """Render the reference sheet at one staff-line thickness."""
    src = TEMPLATE.read_text().replace("#THICKNESS", f"#{thickness}")
    ly = out_dir / f"ref_t{thickness}.ly"
    ly.write_text(src)
    subprocess.run(
        ["lilypond", "-s", "-o", ly.stem, ly.name],
        cwd=out_dir, check=True, capture_output=True,
    )
    return out_dir / f"ref_t{thickness}.pdf"


def measured_line_thickness(cell) -> float:
    """The printed thickness of a staff line in the cell, in staff spaces."""
    img = cell.image
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.ndim == 3 else img
    binary = binarize(gray)
    h, w = binary.shape
    ys = cell.staff_line_ys_canonical
    spacing = (ys[-1] - ys[0]) / 4.0
    y = int(ys[len(ys) // 2])
    runs = []
    for x in range(0, w, 7):
        if binary[y, x] != 0:
            continue
        top = y
        while top > 0 and binary[top - 1, x] == 0:
            top -= 1
        bot = y
        while bot < h - 1 and binary[bot + 1, x] == 0:
            bot += 1
        runs.append(bot - top + 1)
    if not runs or spacing <= 0:
        return 0.0
    return float(np.median(runs)) / spacing


def score_pdf(pdf: Path, dpi: int = 600) -> dict[str, Any]:
    page = render_page(pdf, 0, dpi=dpi)
    pws = detect_barlines(detect_staves(page))
    cells = extract_measures(pws)
    remove_staff_lines(cells)

    per_staff: dict[int, dict[str, int]] = {}
    for c in cells:
        d = detect_lines(c)
        s = per_staff.setdefault(c.staff_index, {"stems": 0, "beams": 0, "cells": 0})
        s["stems"] += len(d["stems"])
        s["beams"] += len(d["beams"])
        s["cells"] += 1
    return {
        "n_staves": len(pws.staves),
        "n_cells": len(cells),
        "line_thickness_spaces": round(measured_line_thickness(cells[0]), 2) if cells else 0.0,
        "per_staff": {str(k): v for k, v in sorted(per_staff.items())},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-dir", type=Path, help="write the engraved sheets here")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    if shutil.which("lilypond") is None:
        raise SystemExit("lilypond not on PATH — needed to engrave the reference sheet")

    gt = json.loads(GROUND_TRUTH_PATH.read_text())
    expected = gt["per_staff_totals"]

    tmp = args.keep_dir or Path(tempfile.mkdtemp(prefix="refsheets-"))
    tmp.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    print(f"{'thick':>5} {'lines(sp)':>9} {'cells':>5}  "
          f"{'staff0 stems':>13} {'staff0 beams':>13} {'staff1 stems':>13} {'staff1 beams':>13}")
    for t in THICKNESSES:
        pdf = engrave(t, tmp)
        r = score_pdf(pdf, dpi=args.dpi)
        results[str(t)] = r
        row = f"{t:>5} {r['line_thickness_spaces']:>9.2f} {r['n_cells']:>5}  "
        for staff in ("0", "1"):
            got = r["per_staff"].get(staff, {"stems": 0, "beams": 0})
            for kind in ("stems", "beams"):
                exp = expected[staff][kind]
                mark = "OK" if got[kind] == exp else f"{got[kind] - exp:+d}"
                row += f"{got[kind]:>4}/{exp:<3}{mark:>6}"
        print(row)

    if args.json_out:
        args.json_out.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.json_out}")
    if not args.keep_dir:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
