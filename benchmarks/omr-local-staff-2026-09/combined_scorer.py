#!/usr/bin/env python3
"""ROADMAP 2.54 (Sean, 2026-10-01, "combine that way") -- score
`ledger_grid.combine_farhead_position` as a PURE FUNCTION against the
2.44c reference-backed truth set, at STAFF POSITION (CLAUDE.md sec6b).

Reuses `score_truth_set_rungs.py`'s own per-head data (geometry position +
`derive_far_head_step`'s own rung reading, "as shipped" -- ROUND7_CLEANUP_
ENABLED stays False, CLAUDE.md rule 6: never re-derive what already
exists) UNCHANGED; this script only adds the combine step and the report.

MEASUREMENT ONLY -- writes nothing back into the pipeline.

    python3 benchmarks/omr-local-staff-2026-09/combined_scorer.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402


def _rungs_y_for_head(gray, lines: Sequence[float], box, subject: str,
                      page_boxes: Sequence[Tuple[str, tuple]]
                      ) -> Tuple[List[float], float, str]:
    """The SAME rung ladder `score.reader_absolute_position` derives its
    own answer from -- recomputed here (not re-exported by that function,
    which returns only the final offset) so the evenness measure and the
    final offset are provably reading the SAME ladder, never a second,
    independently-walked one."""
    ys = sorted(float(v) for v in lines)
    spacing = (ys[-1] - ys[0]) / 4.0
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    side = "above" if cy < ys[0] else "below"
    others = [b for (s, b) in page_boxes if s != subject]
    items = lg.measure_ledger_rungs(
        gray, ys, cx, head_y=cy, exclude_boxes=others, head_box_x=(x0, x1),
    ).get(side, [])
    return items, spacing, side


def score_doc(doc_id: str) -> Dict[str, Any]:
    loaded = ts.load_doc(doc_id)
    rows = score._far_head_rows(doc_id, loaded)
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    boxes_by_page = score._notehead_boxes_by_page(rec)

    tally: "collections.Counter[str]" = collections.Counter()
    branch_tally: Dict[str, "collections.Counter[str]"] = collections.defaultdict(
        collections.Counter
    )
    half_step_tally: "collections.Counter[str]" = collections.Counter()
    per_head: List[Dict[str, Any]] = []

    for row in rows:
        if row["subject"] == "glyph/1/0/10/14/1":
            continue  # Sean: this head's own reference pairing is wrong
        truth_p = row["truth_pitches"]
        if not truth_p:
            continue
        staff_key = row["staff_key"]
        clef_v = rec.value(Q.CLEF, staff_key)
        if clef_v is None:
            continue
        truth_pos = set(score.truth_positions(truth_p, str(clef_v)))
        if not truth_pos:
            continue
        box = row["page_box"]
        if not box:
            continue
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        if not line_rows:
            continue
        global_lines = [float(y) for y in line_rows[-1]["value"]]
        gray = pages.get(row["page"])
        lines = score.frame_lines_for_head(gray, global_lines, box)

        geom_pos = int(round(row["raw_pos"]))
        geom_residual = abs(row["raw_pos"] - round(row["raw_pos"]))
        page_boxes = boxes_by_page.get(row["page"], [])
        rungs_pos, _reason = score.reader_absolute_position(
            gray, lines, box, row["subject"], page_boxes
        )
        rungs_y, spacing, _side = _rungs_y_for_head(
            gray, lines, box, row["subject"], page_boxes
        )

        combined = lg.combine_farhead_position(
            geom_pos=geom_pos, geom_residual=geom_residual,
            rungs_pos=rungs_pos, rungs_y=rungs_y, spacing=spacing,
        )

        def verdict(pos: Optional[int]) -> str:
            if pos is None:
                return "unread"
            return "right" if pos in truth_pos else "wrong"

        v_geom = "right" if geom_pos in truth_pos else "wrong"
        v_rungs = verdict(rungs_pos)
        v_combined = verdict(combined["position"])

        tally[v_combined] += 1
        branch_tally[combined["branch"]][v_combined] += 1

        # half-step control -- reusing the broken box the same way
        # score_truth_set_rungs's own control does.
        bx0, by0, bx1, by1 = box
        broken_box = (bx0, by0 + spacing / 2.0, bx1, by1 + spacing / 2.0)
        broken_rungs_pos, _ = score.reader_absolute_position(
            gray, lines, broken_box, row["subject"], page_boxes
        )
        broken_rungs_y, broken_spacing, _ = _rungs_y_for_head(
            gray, lines, broken_box, row["subject"], page_boxes
        )
        broken_geom_pos = geom_pos  # geometry box unchanged by the control
        # (score_truth_set_rungs's own control only perturbs the rungs
        # reader's input box, not the stored raw geometric position --
        # matched here for the SAME reason, see that script's control.)
        broken_combined = lg.combine_farhead_position(
            geom_pos=broken_geom_pos, geom_residual=geom_residual,
            rungs_pos=broken_rungs_pos, rungs_y=broken_rungs_y,
            spacing=broken_spacing,
        )
        half_step_tally[verdict(broken_combined["position"])] += 1

        per_head.append(dict(
            subject=row["subject"], truth_pos=sorted(truth_pos),
            geom_pos=geom_pos, v_geom=v_geom,
            rungs_pos=rungs_pos, v_rungs=v_rungs,
            combined_pos=combined["position"], branch=combined["branch"],
            v_combined=v_combined,
            max_gap_deviation=combined["max_gap_deviation"],
        ))

    return dict(tally=dict(tally), branch_tally={k: dict(v) for k, v in branch_tally.items()},
               half_step_tally=dict(half_step_tally), per_head=per_head)


def main() -> int:
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        r = score_doc(doc_id)
        n = len(r["per_head"])
        t = r["tally"]
        print(f"  combined   right={t.get('right',0):>3} wrong={t.get('wrong',0):>3} "
             f"unread={t.get('unread',0):>3}  (n={n})")
        geom_right = sum(1 for h in r["per_head"] if h["v_geom"] == "right")
        rungs_right = sum(1 for h in r["per_head"] if h["v_rungs"] == "right")
        rungs_undec = sum(1 for h in r["per_head"] if h["v_rungs"] == "unread")
        print(f"  geometry   right={geom_right:>3} wrong={n-geom_right:>3} (n={n})")
        print(f"  rungs      right={rungs_right:>3} wrong={n-rungs_right-rungs_undec:>3} "
             f"undecided={rungs_undec:>3} (n={n})")
        print(f"  half-step control (combined, must score worse): {r['half_step_tally']}")
        print("  branch breakdown:")
        for branch in ("agree", "disagree_rungs", "disagree_geometry", "unread"):
            bt = r["branch_tally"].get(branch, {})
            bn = sum(bt.values())
            print(f"    {branch:<20} n={bn:<4} right={bt.get('right',0):<4} "
                 f"wrong={bt.get('wrong',0):<4} unread={bt.get('unread',0):<4}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
