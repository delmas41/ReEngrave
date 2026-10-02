#!/usr/bin/env python3
"""lane-brahms-frame (2026-10-01) -- redraw the 4 Brahms review crops the
manager flagged (`out/print/ledgers/r5/brahms1-breitkopf-glyph-1-1-8-{4-4,
5-0,6-0,7-4}.png`) with the CORRECTED frame (`score_truth_set_rungs.
frame_lines_for_head`, same module `review_crops5.py` now calls), so the
drawn green staff lines sit ON the ink instead of ~10-13 page px below it.

Does NOT re-run `review_crops5.main()` -- that script's own population
(every truth-set head still wrong/abstaining/changed) is now 113 heads on
this fresh re-gather (the 11-head population in FINDINGS' round-5 table
came from a since-regenerated, no-longer-reproducible small record -- see
FINDINGS entry for this lane), and redrawing the WHOLE round-5 sheet is
out of scope for a frame fix. This redraws exactly the 4 flagged crops,
reusing `review_crops5.render_crop` UNCHANGED (same style, same pixel-row
check), with BEFORE/AFTER meaning the FRAME fix itself (global
`Q.STAFF_LINES` vs `frame_lines_for_head`'s local re-measurement) rather
than round 5's own ledger_grid-vs-round-3 comparison.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_truth_set_rungs as score  # noqa: E402
import review_crops5 as rc  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

TARGET_SUBJECTS = [
    "glyph/1/1/8/4/4",
    "glyph/1/1/8/5/0",
    "glyph/1/1/8/6/0",
    "glyph/1/1/8/7/4",
]

OUT_DIR = REPO / "out" / "print" / "ledgers" / "r5"


def main() -> int:
    doc_id = "brahms1-breitkopf"
    loaded = ts.load_doc(doc_id)
    rec = loaded["rec"]
    rows_by_sub = {row["subject"]: row
                  for row in score._far_head_rows(doc_id, loaded)}
    pages = score.PageCache(loaded["cfg"])
    boxes_by_page = score._notehead_boxes_by_page(rec)

    for sub in TARGET_SUBJECTS:
        row = rows_by_sub.get(sub)
        if row is None:
            print(f"{sub}: NOT in the far-head population on this record -- skipped")
            continue
        staff_key = row["staff_key"]
        clef_v = rec.value(Q.CLEF, staff_key)
        truth_pos = sorted(score.truth_positions(row["truth_pitches"], str(clef_v))) \
            if clef_v is not None else []
        box = row["page_box"]
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        global_lines = [float(v) for v in line_rows[-1]["value"]]
        gray = pages.get(row["page"])
        local_lines = score.frame_lines_for_head(gray, global_lines, box)
        page_boxes = boxes_by_page.get(row["page"], [])
        others = [b for (s, b) in page_boxes if s != sub]

        geom_pos = int(round(row["raw_pos"]))

        before_pos, before_reason = score.reader_absolute_position(
            gray, global_lines, box, sub, page_boxes
        )
        after_pos, after_reason = score.reader_absolute_position(
            gray, local_lines, box, sub, page_boxes
        )

        offsets = [g - l for g, l in zip(sorted(global_lines), sorted(local_lines))]
        cause = (
            f"lane-brahms-frame: GLOBAL Q.STAFF_LINES sits "
            f"{sum(offsets) / len(offsets):+.1f}px (mean over 5 lines) off "
            f"this head's own local ink -- frame_lines_for_head re-measures "
            f"at the head's x (ts.local_staff_lines), matching the ink"
        )

        safe = f"{doc_id}-{sub.replace('/', '-')}.png"
        out_path = OUT_DIR / safe
        pix_report = rc.render_crop(
            gray, box, local_lines, sub, out_path,
            truth_pos, geom_pos, after_pos, after_reason,
            cause, others, before_pos, before_reason,
        )
        print(f"{sub} -> {out_path}")
        print(f"  global_lines={[round(v, 1) for v in sorted(global_lines)]}")
        print(f"  local_lines ={[round(v, 1) for v in sorted(local_lines)]}")
        print(f"  before(global)={before_pos} ({before_reason})  "
             f"after(local)={after_pos} ({after_reason})  truth={truth_pos}")
        for line in pix_report:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
