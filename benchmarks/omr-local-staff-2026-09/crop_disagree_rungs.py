#!/usr/bin/env python3
"""lane-ledger-rungs (2026-10-01) -- crops of every truth-set head where
`measure_ledger_rungs` AFTER the wide-gap/first-space/stub fixes
disagrees with the current geometry read (CLAUDE.md rule: "send Sean the
crop", never judge it ourselves). Same drawing style as `rungs_sheet.py`
(red detector box, green real 5 staff lines, orange measured rungs).

Writes `out/print/ledgers/disagree/<subject-with-slashes-as-dashes>.png`,
up to 10 heads. States only what the reference says for each head --
never which reading is "right".
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import rungs_sheet as rs  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers" / "disagree"


def crop_one(doc_id: str, loaded, row: dict, out_path: Path) -> None:
    rec = loaded["rec"]
    gray = loaded["gray"]
    sub = row["subject"]
    staff_key = row["staff_key"]
    box = row["page_box"]
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    lines = sorted(float(v) for v in line_rows[-1]["value"])
    spacing_px = (lines[-1] - lines[0]) / 4.0

    fake_row = dict(
        box_page=(x0, y0, x1, y1),
        spacing_px=spacing_px,
        nominal_ys=lines,
        orange_shift=0.0,
        x_center=cx, y_center=cy,
        today_pos=row["raw_pos"],
        staff=staff_key,
        sub=sub,
    )
    side, rung_items, rungs_step, read_kind, crashed = rs.classify_far_head(
        fake_row, gray
    )
    # draw_tile_far expects a BGR page and the SAME binary page the rung
    # reader was run against; this script's own `gray` (uint8 grayscale,
    # the same `_render_page_gray` the reader itself was scored against)
    # stands in for both -- a 3-channel view of it is enough to draw on.
    rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    tile = rs.draw_tile_far(rgb, gray, fake_row, None, rung_items, rungs_step,
                            read_kind, side)
    cv2.imwrite(str(out_path), tile)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        result = score.score_doc(doc_id, score._load_before_module(), score.lg_after)
        disagree = [h for h in result["per_head"] if h["v_after"] != h["v_before"]]
        rows_by_sub = {r["subject"]: r for r in score._far_head_rows(doc_id, loaded)}
        for h in disagree:
            if written >= 10:
                break
            row = rows_by_sub.get(h["subject"])
            if row is None:
                continue
            safe = h["subject"].replace("/", "-")
            out_path = OUT_DIR / f"{doc_id}-{safe}.png"
            crop_one(doc_id, loaded, row, out_path)
            print(f"wrote {out_path}  truth={h['truth_pos']} "
                 f"before={h['before_pos']}({h['v_before']}) "
                 f"after={h['after_pos']}({h['v_after']})")
            written += 1
    print(f"\n{written} disagreement crops written to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
