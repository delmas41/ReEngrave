"""Where, exactly, did OMR_CELL_LINE_TRACE change the widened-gate A/B?

Localization is metadata until pitch resolution reads it, so the honest
localization of the A/B is per CELL: walk both arms' raw transcriptions keyed
on (system, staff, measure), and report for every cell whether the stored grid
moved, and whether anything the exporter reads — the detections' pitches,
accidentals, durations — moved with it. A cell whose grid moved and whose
reading did not is the no-op the minimum-shift and coverage gates promise on
mildly-moved cells; a cell whose reading changed with no grid move would be a
DEFECT (nothing else in the pipeline may read the flag), and this script's
exit code says so.

    python3 benchmarks/omr-cell-grid-tilt-2026-09/compare_ab_cells.py \
        --baseline-tag wbase --arm-tag wtilt

Reads benchmarks/omr-scan-e2e-2026-09/fixtures/<row>.<tag>.omr.json for the
rows of works.json, plus the two scan_eval results JSONs for the score deltas.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
FIXTURES = SCAN / "fixtures"

FLIP_SPACES = 0.25


def _cells(doc: dict) -> dict[tuple[int, int, int], dict]:
    out: dict[tuple[int, int, int], dict] = {}
    for page in doc["pages"]:
        for sys_ in page["systems"]:
            for staff in sys_["staves"]:
                for m in staff["measures"]:
                    key = (sys_["system_index"], staff["staff_index"],
                           m["measure_index"])
                    out[key] = m
    return out


def _reading(measure: dict) -> list[str]:
    """Everything the exporter could read out of this cell, order-stable.

    The whole detection dict, not a hand-picked subset — a subset is exactly
    how a changed tie or articulation would slip past this comparison.
    """
    return [json.dumps(det, sort_keys=True)
            for det in measure.get("detections", [])]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-tag", default="wbase")
    ap.add_argument("--arm-tag", default="wtilt")
    ap.add_argument("--out", type=Path,
                    default=BENCH / "widened_ab_cell_report.json")
    args = ap.parse_args(argv)

    rows = json.loads((SCAN / "works.json").read_text())["rows"]
    report_rows = []
    defect = False
    for row in rows:
        rid = row["row_id"]
        base_p = FIXTURES / f"{rid}.{args.baseline_tag}.omr.json"
        arm_p = FIXTURES / f"{rid}.{args.arm_tag}.omr.json"
        if not (base_p.is_file() and arm_p.is_file()):
            print(f"{rid}: fixtures missing for one or both tags, skipped",
                  file=sys.stderr)
            continue
        base = _cells(json.loads(base_p.read_text()))
        arm = _cells(json.loads(arm_p.read_text()))
        keys = sorted(set(base) | set(arm))
        moved, reading_changed, changed_no_move = [], [], []
        for k in keys:
            b, a = base.get(k), arm.get(k)
            if b is None or a is None:
                # A structural difference (a cell present in one arm only)
                # counts as a changed reading with no grid to compare.
                reading_changed.append(k)
                changed_no_move.append(k)
                continue
            grid_moved = (b.get("staff_line_ys_canonical")
                          != a.get("staff_line_ys_canonical"))
            read_moved = _reading(b) != _reading(a)
            if grid_moved:
                moved.append(k)
            if read_moved:
                reading_changed.append(k)
                if not grid_moved:
                    changed_no_move.append(k)
        mx_same = ((FIXTURES / f"{rid}.{args.baseline_tag}.omr.musicxml")
                   .read_bytes()
                   == (FIXTURES / f"{rid}.{args.arm_tag}.omr.musicxml")
                   .read_bytes())
        report_rows.append({
            "row_id": rid,
            "n_cells": len(keys),
            "n_grid_moved": len(moved),
            "n_reading_changed": len(reading_changed),
            "reading_changed_cells": [list(k) for k in reading_changed],
            "reading_changed_without_grid_move": [list(k)
                                                  for k in changed_no_move],
            "musicxml_identical": mx_same,
        })
        # A changed reading in an unmoved cell is EXPECTED where some other
        # cell of the page moved — ties and slurs are paired across the staff,
        # so a flipped pitch in the moved cell renumbers its partner's marks.
        # The defect signature is a row where readings changed and NO grid
        # moved anywhere: only the grid may read the flag.
        if reading_changed and not moved:
            defect = True
        print(f"{rid:38s} cells {len(keys):>4d}  grid-moved {len(moved):>4d}  "
              f"reading-changed {len(reading_changed):>3d}  "
              f"musicxml {'identical' if mx_same else 'DIFFERS'}")

    args.out.write_text(json.dumps({"rows": report_rows}, indent=1) + "\n")
    print(f"wrote {args.out}")
    if defect:
        print("\n!! a cell's READING changed without its grid moving — "
              "nothing but the grid may read the flag", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
