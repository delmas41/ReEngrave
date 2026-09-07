"""Are the one-line percussion staves DETECTED, and where are they lost?

The works.json Mahler rows carry a `condensation` block instead of a `staves`
map, and the recorded reason is that the printed one-line percussion staves
"a five-line staff detector cannot find by construction" break a positional
part->staff join. That premise is asked of the CURRENT tree here, stage by
stage, on the four Mahler pages.

Nothing is inferred from the stored fixture: the page is rendered and each
phase-1 stage is run, so the answer is about the tree, not about an artefact.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page                    # noqa: E402
from tools.omr.staff_detector import detect_staves                 # noqa: E402
from tools.omr.measure_extractor import (                          # noqa: E402
    detect_barlines, extract_measures)
from tools.library.score_library import library_root               # noqa: E402

PDF = ("editions/mahler/symphony-5/"
       "mahler--symphony-5--unidentified-scan-2016--local.pdf")
PAGES = {1: "p2", 2: "p3", 3: "p4", 4: "p5"}


def main() -> int:
    pdf = library_root() / PDF
    out = []
    for pidx, tag in PAGES.items():
        page = render_page(str(pdf), pidx, dpi=600)
        pws = detect_staves(page)
        staves = pws.staves
        one_line = [s for s in staves if len(s.line_ys) < 5]
        pws2 = detect_barlines(pws)
        cells = extract_measures(pws2)
        with_cells = {c.staff_index for c in cells}
        rec = {
            "row": "mahler-sym5-mvt1-local-" + tag,
            "pdf_page_index": pidx,
            "detect_staves_total": len(staves),
            "detect_staves_five_line": len(staves) - len(one_line),
            "detect_staves_one_line": len(one_line),
            "one_line": [
                {"staff_index": s.staff_index, "line_ys": list(s.line_ys),
                 "span_px": s.span_px, "x_start": s.x_start, "x_end": s.x_end,
                 "system_index": s.system_index}
                for s in one_line],
            "staves_with_cells": len(with_cells),
            "one_line_with_cells": sorted(
                {s.staff_index for s in one_line} & with_cells),
            "staff_indices_with_cells": sorted(with_cells),
        }
        out.append(rec)
        print(json.dumps(rec, indent=1))
    dst = Path(__file__).with_name("one-line-staves.json")
    dst.write_text(json.dumps({"rows": out}, indent=1) + "\n")
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
