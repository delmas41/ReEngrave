"""How many cells on the scan corpus carry a displaced grid, and by how much.

Phase 1 only — render, detect staves, detect barlines, extract measures — over
the five pages of `benchmarks/omr-scan-e2e-2026-09/works.json`. No YOLO, no
export, no scoring: this measures the GEOMETRY, so its numbers stand whatever
recognition then does with them, and it is the population the A/B in
RESULTS_TILT.md is drawn from.

Reports, per page and pooled: the distribution of the comb fit's offset, how
many cells sit past the quarter-space parity-flip line, how many abstain and
why, and whether `Staff.line_wander_px` predicts which staves are affected.

    python3 benchmarks/omr-cell-grid-tilt-2026-09/probe_scan_corpus_offsets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr import measure_extractor as _me  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

WORKS = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"

#: The parity-flip line: past a quarter space, the nearest half-step slot on
#: the grid is a different slot, so every note in the cell can resolve one step
#: off. FINDINGS.md §3 uses the same figure on the labeling campaign.
FLIP_SPACES = 0.25


def main() -> int:
    doc = json.loads(WORKS.read_text())
    protocol = doc["protocol"]
    lib = library_root()
    rows_out = []

    for row in doc["rows"]:
        win = row["window"]
        if win.get("first_ref_measure") is None:
            continue
        pdf = lib / row["edition"]["catalog_path"]
        if not pdf.is_file():
            print(f"{row['row_id']}: PDF missing, skipped", file=sys.stderr)
            continue
        page0 = row["page"]["pdf_page_index"]
        img = render_page(pdf, page0, dpi=protocol["dpi"])
        pws = detect_staves(img)
        _me.detect_barlines(pws)
        cells = _me.extract_measures(pws)

        by_staff = {s.staff_index: s for s in pws.staves}
        cell_recs = []
        for cell in cells:
            staff = by_staff.get(cell.staff_index)
            if staff is None or len(staff.line_ys) < 5:
                continue
            x0, _, x1, _ = cell.bbox_page_px
            spacing = float(staff.line_spacing_px)
            got = _me._cell_line_offset(pws, staff, x0, x1)
            rec = {
                "staff": cell.staff_index,
                "system": cell.system_index,
                "measure": cell.measure_index,
                "spacing_px": round(spacing, 2),
                "wander_px": staff.line_wander_px,
            }
            if got is None:
                rec["offset_spaces"] = 0.0
                rec["moved"] = False
            else:
                shift, prov = got
                rec["offset_spaces"] = prov["offset_spaces"]
                rec["min_row_coverage"] = prov["min_row_coverage"]
                rec["moved"] = True
            cell_recs.append(rec)

        offs = np.array([abs(r["offset_spaces"]) for r in cell_recs])
        moved = [r for r in cell_recs if r["moved"]]
        flip = [r for r in cell_recs if abs(r["offset_spaces"]) >= FLIP_SPACES]
        # Which staves the wander flag predicts, against which actually move.
        staff_max = {}
        for r in cell_recs:
            k = r["staff"]
            staff_max[k] = max(staff_max.get(k, 0.0), abs(r["offset_spaces"]))
        flagged = {s.staff_index for s in pws.staves
                   if len(s.line_ys) >= 5 and (s.line_wander_px or 0)
                   >= FLIP_SPACES * float(s.line_spacing_px)}
        affected = {k for k, v in staff_max.items() if v >= FLIP_SPACES}

        out = {
            "row_id": row["row_id"],
            "n_cells": len(cell_recs),
            "n_moved": len(moved),
            "n_past_flip": len(flip),
            "offset_spaces": {
                "median": round(float(np.median(offs)), 3) if offs.size else None,
                "p90": round(float(np.percentile(offs, 90)), 3) if offs.size else None,
                "max": round(float(offs.max()), 3) if offs.size else None,
            },
            "staves_affected": sorted(affected),
            "staves_wander_flagged": sorted(flagged),
            "wander_flag": {
                "true_positive": len(affected & flagged),
                "missed_by_flag": sorted(affected - flagged),
                "flagged_not_affected": sorted(flagged - affected),
            },
            "cells": cell_recs,
        }
        rows_out.append(out)
        print(f"{row['row_id']:38s} cells {out['n_cells']:>4d}  "
              f"moved {out['n_moved']:>4d}  past-flip {out['n_past_flip']:>4d}  "
              f"median {out['offset_spaces']['median']:.3f}  "
              f"p90 {out['offset_spaces']['p90']:.3f}  "
              f"max {out['offset_spaces']['max']:.3f}", flush=True)

    all_cells = [c for r in rows_out for c in r["cells"]]
    offs = np.array([abs(c["offset_spaces"]) for c in all_cells])
    pooled = {
        "n_cells": len(all_cells),
        "n_moved": sum(1 for c in all_cells if c["moved"]),
        "n_past_flip": int((offs >= FLIP_SPACES).sum()),
        "median": round(float(np.median(offs)), 3) if offs.size else None,
        "p90": round(float(np.percentile(offs, 90)), 3) if offs.size else None,
        "max": round(float(offs.max()), 3) if offs.size else None,
    }
    print(f"\npooled: {pooled['n_cells']} cells, {pooled['n_moved']} moved, "
          f"{pooled['n_past_flip']} past the {FLIP_SPACES}-space flip line "
          f"({100.0 * pooled['n_past_flip'] / max(1, pooled['n_cells']):.1f}%)")
    print(f"  |offset| median {pooled['median']}  p90 {pooled['p90']}  "
          f"max {pooled['max']} spaces")

    out = BENCH / "probe_scan_corpus_offsets.json"
    out.write_text(json.dumps({"pooled": pooled, "rows": rows_out}, indent=1) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
