#!/usr/bin/env python3
"""lane-ledger-template-centre (2026-10-04): the head template's CENTRE as
`head_center_y` for round 8's through-the-middle ledger test.

Shared pieces (template fit per far head) used by `score_template_centre.py`
and `template_centre_sheet.py`. Matching is exactly lane-ledger-template-fix
round 4's (`template_review_r4.py`): shape from the page's clean heads
(Litolff plain oval, Brahms mean shape), `decide="staged"` (position first),
+-0.4 sp sideways, head ink by opening, line term by coverage. Nothing here
reads the reference encoding; the fit numbers are the template's own
(IoU / offset of the oval against the head's ink blob).

THE F2 GATE (stated BEFORE any arm was scored, 2026-10-04): use the
template's centre only where its own pixel check passes round 4's own MISS
rule, unchanged -- IoU >= 0.70 AND offset <= 0.15 sp. No other number
(margin, displacement) enters the gate.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import score_head_template as sht  # noqa: E402
import combined_scorer as cs  # noqa: E402
import shape_from_page as sfp  # noqa: E402
import template_review_r4 as r4  # noqa: E402
import edge_census as ec  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

GATE_IOU_MIN = r4.IOU_MIN          # 0.70
GATE_OFFSET_MAX_SP = r4.OFFSET_MAX_SP  # 0.15

CENSUS_9 = ["glyph/3/0/7/2/4", "glyph/3/0/7/3/1", "glyph/3/0/7/3/2", "glyph/3/0/7/6/1",
            "glyph/3/0/7/7/0", "glyph/3/0/8/6/10", "glyph/3/0/7/3/4", "glyph/3/0/7/4/3",
            "glyph/3/1/0/6/0"]


def doc_context(doc_id: str) -> Dict[str, Any]:
    """Page-measured shape + templates for one document (round 4's choice
    rule: best mean IoU over 6 clean in-staff control heads)."""
    loaded = ts.load_doc(doc_id)
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    heads = sfp.in_staff_heads(doc_id, loaded, pages)
    sfp.annotate_heads(doc_id, loaded, pages, heads)
    shape_a = r4.doc_shape(doc_id, heads)
    thick = float(np.median([h["thickness"] for h in heads]))
    med_sp = float(np.median([h["spacing"] for h in heads]))
    boxes_by_page = sht._page_glyph_boxes(rec)
    nh = score._notehead_boxes_by_page(rec)
    acc = score._accidental_boxes_by_page(rec)
    cands = r4.candidate_shapes(heads, pages, shape_a)
    ctrl = r4.pick_controls(heads)
    best, best_key = None, None
    for name, shp in cands.items():
        tpl = r4.make_templates(shp, thick, med_sp)
        ious = []
        for h in ctrl:
            _t, c = r4.render_tile("control", doc_id, dict(h, thickness=h["thickness"]), rec, pages,
                                   tpl, shp, boxes_by_page, nh, acc, controls=True)
            ious.append(c["iou"])
        key = (float(np.mean(ious)), name == "A_oval")
        if best_key is None or key > best_key:
            best, best_key = name, key
    shape = cands[best]
    return dict(doc=doc_id, loaded=loaded, rec=rec, pages=pages, shape=shape, shape_name=best,
                templates=r4.make_templates(shape, thick, med_sp), thick=thick,
                boxes_by_page=boxes_by_page, nh=nh, acc=acc)


def fit_head(ctx: Dict[str, Any], h: Dict[str, Any]) -> Dict[str, Any]:
    """Template fit for one far head `h` (a `load_heads` dict)."""
    entry = {s: c for (s, c, b) in ctx["boxes_by_page"].get(h["page"], [])}
    cls = entry.get(h["subject"], "noteheadBlackOnLine")
    kind = "filled" if "Black" in cls else "hollow"
    spacing = (max(h["lines"]) - min(h["lines"])) / 4.0
    rl = dict(subject=h["subject"], page=h["page"], box=h["box"], kind=kind, lines=h["lines"],
              spacing=spacing, thickness=ctx["thick"])
    _tile, chk = r4.render_tile("far", ctx["doc"], rl, ctx["rec"], ctx["pages"], ctx["templates"],
                                ctx["shape"], ctx["boxes_by_page"], ctx["nh"], ctx["acc"])
    x0, y0, x1, y1 = h["box"]
    box_mid = (y0 + y1) / 2.0
    cy = box_mid + chk["dy_px"]
    return dict(subject=h["subject"], kind=kind, box=h["box"], box_mid_y=box_mid,
                tmpl_cx=(x0 + x1) / 2.0 + chk["dx_px"], tmpl_cy=cy,
                dy_sp=chk["dy_sp"], dx_sp=chk["dx_sp"], iou=chk["iou"], offset_sp=chk["offset_sp"],
                margin=chk["margin"], variant=chk["variant"], spacing=spacing,
                trusted=bool(chk["iou"] >= GATE_IOU_MIN and chk["offset_sp"] is not None
                             and chk["offset_sp"] <= GATE_OFFSET_MAX_SP))


def all_fits() -> Dict[str, Any]:
    out = {}
    for doc in ts.DOCS:
        ctx = doc_context(doc)
        heads = ec.load_heads(doc)
        out[doc] = dict(ctx=ctx, heads=heads, fits={h["subject"]: fit_head(ctx, h) for h in heads})
    return out


if __name__ == "__main__":
    res = all_fits()
    for doc, d in res.items():
        print(f"=== {doc} shape={d['ctx']['shape_name']} n={len(d['fits'])}")
        print("subject             kind   box_mid  tmpl_cy  dy_sp   IoU  off_sp  trusted")
        for s, f in d["fits"].items():
            print(f"{s:19} {f['kind']:6} {f['box_mid_y']:8.1f} {f['tmpl_cy']:8.1f} {f['dy_sp']:+.2f}  "
                  f"{f['iou']:.2f}  {f['offset_sp']}  {f['trusted']}")
