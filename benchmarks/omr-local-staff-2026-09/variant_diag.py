#!/usr/bin/env python3
"""lane-ledger-template-fix round 4 (2026-10-04), item 2: WHY does the matcher's
on_line / in_space answer disagree with the staff position on easy in-staff
heads? For each control head, print the best HEAD term and best LINE term of
each variant (and each in_space band separately) at the shift the matcher
settled on, plus what the page actually has at the two candidate line rows
(+-0.5 sp: the lines that bound a space) and (+-1.0 sp: an on-line head's
neighbouring staff lines).

    python3 benchmarks/omr-local-staff-2026-09/variant_diag.py
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
import shape_from_page as sfp  # noqa: E402
import template_review_r4 as r3  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

DECIDE = sys.argv[1] if len(sys.argv) > 1 else "joint"   # "joint" = the pre-fix joint search
TOL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
LINE_TERM = sys.argv[3] if len(sys.argv) > 3 else "ncc"   # "ncc" (old) or "coverage"
LOG = []
_orig = ht._template_score


def _logged(tmpl, candidate, line_candidate=None, line_term="ncc"):
    head = ht._masked_ncc(tmpl.head_img if tmpl.head_img is not None else tmpl.img,
                          candidate, ht.HEAD_MASK)
    lc = candidate if line_candidate is None else line_candidate
    if line_term == "coverage":
        comps = [float(lc[m & (tmpl.img > 0.5)].mean()) if (m & (tmpl.img > 0.5)).any() else None
                 for m in tmpl.line_mask_components]
    else:
        comps = [ht._masked_ncc(tmpl.img, lc, m) for m in tmpl.line_mask_components]
    total = _orig(tmpl, candidate, line_candidate, line_term)
    LOG.append((tmpl.variant, total, head, comps))
    return total


def main() -> int:
    ht._template_score = _logged
    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        heads = sfp.in_staff_heads(doc_id, loaded, pages)
        sfp.annotate_heads(doc_id, loaded, pages, heads)
        shape = r3.doc_shape(doc_id, heads)
        thick = float(np.median([h["thickness"] for h in heads]))
        med_sp = float(np.median([h["spacing"] for h in heads]))
        tm = ht.build_geometry_templates(
            {"filled": shape["tilt_deg"], "hollow": shape["tilt_deg"]}, {},
            thick * ht.CANONICAL_PX_PER_SPACE / med_sp,
            width_spaces={"filled": shape["width_sp"], "hollow": shape["width_sp"]},
            height_spaces={"filled": shape["height_sp"], "hollow": shape["height_sp"]})
        nh = score._notehead_boxes_by_page(rec)
        acc = score._accidental_boxes_by_page(rec)
        print(f"=== {doc_id}: measured line thickness {thick:.1f} px, spacing {med_sp:.1f} px "
              f"({thick / med_sp:.2f} sp)")
        for h in r3.pick_controls(heads):
            gray = pages.get(h["page"])
            others = [b for (s, b) in nh.get(h["page"], []) if s != h["subject"]] + \
                     [b for (_s, b) in acc.get(h["page"], [])]
            LOG.clear()
            m = ht.match_head_template(gray, h["box"], h["spacing"], tm, exclude_boxes=others,
                                       kind="filled", dx_range_spaces=0.4, head_ink_mode="opening",
                                       decide=DECIDE, line_tolerance_spaces=TOL,
                                       line_term=LINE_TERM)
            best = {}
            for v, tot, head, comps in LOG:
                if v not in best or tot > best[v][0]:
                    best[v] = (tot, head, comps)
            par = "on-line" if h["pos"] % 2 == 0 else "in-space"
            fmt = lambda c: "[" + ",".join("n/a" if x is None else f"{x:+.2f}" for x in c) + "]"
            print(f"  {h['subject']:<18} pos {h['pos']} ({par:8}) -> {m['best_variant']:<8} margin {m['margin']:.3f}"
                  f" | on: head {best['on_line'][1]:+.2f} line {fmt(best['on_line'][2])}"
                  f" | space: head {best['in_space'][1]:+.2f} bands {fmt(best['in_space'][2])}")
            # what the page has at the line rows, at the head's own x-side zones
            x0, y0, x1, y1 = h["box"]
            cy = (y0 + y1) / 2.0
            sp = h["spacing"]
            ys = [(round(((ly - cy) / sp), 2)) for ly in h["lines"]]
            print(f"      staff lines at y - head centre (spaces): {ys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
