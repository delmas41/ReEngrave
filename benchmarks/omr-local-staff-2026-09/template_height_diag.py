#!/usr/bin/env python3
"""lane-ledger-template-fix (2026-10-04), item 4: WHY did the matcher put the
oval at that height on the three heads the manager named? Diagnostic only,
reads the sheet's own check json + the print; scores nothing.

Prints, per head: the matcher's score over every vertical shift (best,
chosen, flatness = best - worst), whether the head region the matcher sees
has any contrast (an all-ink window correlates to exactly 0.0), and the
vertical ink run through the box centre column versus the box (a merged
blob taller than the box means the BOX, not the matcher, is off the head).

    python3 benchmarks/omr-local-staff-2026-09/template_height_diag.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import score_head_template as sht  # noqa: E402
import measure_head_tilt as mht  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

HEADS = {
    "beethoven5-litolff": ["glyph/1/0/9/14/8", "glyph/1/0/11/2/3"],
    "brahms1-breitkopf": ["glyph/0/0/0/6/20"],
}


def main() -> int:
    for doc_id, subs in HEADS.items():
        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        rows = {r["subject"]: r for r in score._far_head_rows(doc_id, loaded)}
        summary = mht.summarize(doc_id, mht.collect_doc_measurements(doc_id))
        tby, _info = sht.build_geometry_templates_for_doc(doc_id)
        boxes = sht._page_glyph_boxes(rec)
        for sub in subs:
            r = rows[sub]
            box = r["page_box"]
            gl = [float(y) for y in rec.obs(Q.STAFF_LINES, r["staff_key"])[-1]["value"]]
            gray = pages.get(r["page"])
            lines = score.frame_lines_for_head(gray, gl, box)
            sp = (max(lines) - min(lines)) / 4.0
            nh = score._notehead_boxes_by_page(rec).get(r["page"], [])
            acc = score._accidental_boxes_by_page(rec).get(r["page"], [])
            r8set = [b for (s, b) in nh if s != sub] + [b for (_s, b) in acc]
            sets = {
                "ALL other detections (old sheet)":
                    [b for (s, c, b) in boxes[r["page"]] if s != sub],
                "other noteheads + accidentals (round 8's set)": r8set,
            }
            for label, others in sets.items():
                mm = ht.match_head_template(gray, box, sp, sht.templates_for_page(tby, r["page"]),
                                            exclude_boxes=others, kind="filled")
                print(f"   exclusion = {label}: variant {mm['best_variant']} "
                      f"margin {mm['margin']:.3f} "
                      f"centre shift {mm['center_y'] - (box[1] + box[3]) / 2:+.1f}px")
            m = ht.match_head_template(gray, box, sp, sht.templates_for_page(tby, r["page"]),
                                       exclude_boxes=r8set, kind="filled")
            x0, y0, x1, y1 = box
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            print(f"== {doc_id} {sub}  spacing {sp:.1f}px  box h={y1 - y0:.0f}px "
                  f"({(y1 - y0) / sp:.2f} sp)  variant={m['best_variant']} margin={m['margin']:.3f}")
            for v, ss in m["shift_scores"].items():
                if not ss:
                    continue
                best = max(ss, key=ss.get)
                print(f"   {v:9} best shift {best:+d}px score {ss[best]:+.3f}  at 0: {ss.get(0, float('nan')):+.3f}  "
                      f"range {min(ss.values()):+.3f}..{max(ss.values()):+.3f}  (flat if range < 0.1)")
            # contrast the matcher sees in the head region at shift 0
            half_w = int(ht.WINDOW_HALF_WIDTH_HEAD_WIDTHS * 1.4 * sp)
            win = gray[int(cy - sp):int(cy + sp), int(cx - half_w):int(cx + half_w)]
            thr = ht._otsu_threshold(win)
            ink_frac = float((win <= thr).mean())
            print(f"   ink fraction in +-1 sp window at box centre: {ink_frac:.2f}")
            # vertical ink run through the box centre column
            col = gray[:, int(round(cx))] <= ht._otsu_threshold(gray[int(cy - 3 * sp):int(cy + 3 * sp), int(cx - 2 * sp):int(cx + 2 * sp)])
            yc = int(round(cy))
            top = yc
            while top - 1 >= 0 and col[top - 1]:
                top -= 1
            bot = yc
            while bot + 1 < len(col) and col[bot + 1]:
                bot += 1
            print(f"   ink run through box-centre column: y {top}..{bot} "
                  f"({(bot - top + 1) / sp:.2f} sp) vs box y {y0:.0f}..{y1:.0f}; "
                  f"run extends {(y0 - top) / sp:+.2f} sp above box, {(bot - y1) / sp:+.2f} sp below")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
