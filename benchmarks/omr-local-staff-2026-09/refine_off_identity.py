#!/usr/bin/env python3
"""lane-ledger-template-fix round 6: prove `refine_centre` is OFF by default and that
the matcher's output is then bit-identical to the commit before it existed
(56f8c66c). Needs that commit's head_template.py copied to
tools/omr/annotate/_ht_old_tmp.py (delete afterwards; it is not committed):

    git show 56f8c66c:tools/omr/annotate/head_template.py > tools/omr/annotate/_ht_old_tmp.py
    python3 benchmarks/omr-local-staff-2026-09/refine_off_identity.py
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
import template_review_r6 as r6  # noqa: E402
from tools.omr.annotate import head_template as new  # noqa: E402
from tools.omr.annotate import _ht_old_tmp as old  # noqa: E402


def same(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float):
        return a == b or (np.isnan(a) and np.isnan(b))
    return a == b


def main() -> int:
    n = bad = 0
    configs = [dict(), dict(dx_range_spaces=0.4, head_ink_mode="opening"),
               dict(dx_range_spaces=0.4, head_ink_mode="opening", decide="staged", line_term="coverage")]
    for doc in ts.DOCS:
        loaded = ts.load_doc(doc)
        pages = score.PageCache(loaded["cfg"])
        heads = sfp.in_staff_heads(doc, loaded, pages)
        sfp.annotate_heads(doc, loaded, pages, heads)
        shape = r6.doc_shape(doc, heads)
        thick = float(np.median([h["thickness"] for h in heads]))
        med = float(np.median([h["spacing"] for h in heads]))
        tm_new = new.build_geometry_templates({"filled": shape["tilt_deg"], "hollow": shape["tilt_deg"]}, {},
                                              thick * 30.0 / med,
                                              width_spaces={"filled": shape["width_sp"], "hollow": shape["width_sp"]},
                                              height_spaces={"filled": shape["height_sp"], "hollow": shape["height_sp"]})
        tm_old = old.build_geometry_templates({"filled": shape["tilt_deg"], "hollow": shape["tilt_deg"]}, {},
                                              thick * 30.0 / med,
                                              width_spaces={"filled": shape["width_sp"], "hollow": shape["width_sp"]},
                                              height_spaces={"filled": shape["height_sp"], "hollow": shape["height_sp"]})
        nh = score._notehead_boxes_by_page(loaded["rec"])
        for h in r6.pick_controls(heads, n_each=3) + [x for x in heads if x["isolated"]][:6]:
            gray = pages.get(h["page"])
            others = [b for (s, b) in nh.get(h["page"], []) if s != h["subject"]]
            for cfg in configs:
                a = new.match_head_template(gray, h["box"], h["spacing"], tm_new, exclude_boxes=others, kind=h["kind"], **cfg)
                b = old.match_head_template(gray, h["box"], h["spacing"], tm_old, exclude_boxes=others, kind=h["kind"], **cfg)
                n += 1
                if not same(a, b):
                    bad += 1
                    print("DIFFERENT", doc, h["subject"], cfg)
    print(f"match_head_template, refine_centre off (default): {n - bad} of {n} calls bit-identical to 56f8c66c")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
