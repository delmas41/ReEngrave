#!/usr/bin/env python3
"""Guard 3 (cheap half): structural A/B on every scan-e2e row.

For each works.json row, run render -> staves -> systems -> barlines ->
measures with OMR_CHOIR_GROUPING off and on, at the protocol dpi (600), and
compare the complete structural fingerprint (system sizes, per-system barline
x lists, per-cell (system, staff, measure, bbox)). The two cues are the only
flag-dependent code, both upstream of everything else, so a row whose
fingerprint is identical produces a byte-identical .omr.json by construction
(demonstrated at full-pipeline strength on the Bach row: the flag-off run
hash-matches the widened-graft baseline fixture). Rows whose fingerprints
differ get a full scan_eval arm.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parents[1]
sys.path.insert(0, str(WORKTREE_ROOT))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402

LIBRARY = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
WORKS = WORKTREE_ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"
DPI = 600


def fingerprint(pdf: Path, page_idx: int) -> dict:
    pws = detect_barlines(detect_staves(render_page(pdf, page_idx, dpi=DPI)))
    cells = extract_measures(pws)
    sizes = Counter(s.system_index for s in pws.staves)
    bl: dict[int, list[int]] = {}
    for b in pws.barlines:
        bl.setdefault(b.system_index, []).append(b.x)
    return {
        "systems": [sizes[k] for k in sorted(sizes)],
        "groups": [[s.group_index for s in sorted(pws.staves, key=lambda t: (t.system_index, t.top_y)) if s.system_index == k] for k in sorted(sizes)],
        "barlines": {str(k): sorted(v) for k, v in sorted(bl.items())},
        "cells": [(c.system_index, c.staff_index, c.measure_index,
                   tuple(int(v) for v in c.bbox_page_px)) for c in cells],
    }


def main() -> int:
    rows = json.load(WORKS.open())["rows"]
    out = {}
    for r in rows:
        rid = r["row_id"]
        pdf = LIBRARY / r["edition"]["catalog_path"]
        page_idx = r["page"]["pdf_page_index"]
        if not pdf.exists():
            print(f"{rid}: MISSING {pdf}")
            continue
        fps = {}
        for flag in ("0", "1"):
            os.environ["OMR_CHOIR_GROUPING"] = flag
            fps[flag] = fingerprint(pdf, page_idx)
        os.environ.pop("OMR_CHOIR_GROUPING", None)
        identical = fps["0"] == fps["1"]
        out[rid] = {
            "identical": identical,
            "systems_off": fps["0"]["systems"],
            "systems_on": fps["1"]["systems"],
            "n_cells_off": len(fps["0"]["cells"]),
            "n_cells_on": len(fps["1"]["cells"]),
        }
        if not identical:
            b0, b1 = fps["0"]["barlines"], fps["1"]["barlines"]
            diff_sys = [k for k in set(b0) | set(b1) if b0.get(k) != b1.get(k)]
            out[rid]["barline_diff_systems"] = sorted(diff_sys)
        print(f"{rid}: {'IDENTICAL' if identical else 'DIFFERS'} "
              f"off={out[rid]['systems_off']}/{out[rid]['n_cells_off']}c "
              f"on={out[rid]['systems_on']}/{out[rid]['n_cells_on']}c", flush=True)
    (HERE / "ab_structural_rows.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
