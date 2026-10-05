#!/usr/bin/env python3
"""lane-standard-head-box (2026-10-04): score round 8 (fix 1 + far-side rule)
with a STANDARD-SIZE head box (size from the page's measured head, centre from
the template's free position search) instead of the detector's box.

Arms (reader = `four_causes_cd` + near_edge_ledgers + restore_masked_near_edge
+ far_side_ledger, i.e. score_far_side's `fix1_far`):
  S0  detector box on every far head   (CONTROL: Litolff 32/10/2, Brahms 11/0/0)
  S1  standard box on every far head
  S2  standard box only where the template fit passes its own PRE-SET gate
      (IoU >= 0.70 and offset <= 0.15 sp, on the opened ink -- ledger-free so
      the gate is not a consequence of the ledger read; set before scoring)

The BOX and the CENTRE both change (`head_center_y` is left None: the reader
takes the centre from the box). Other heads' boxes (exclusion) stay detector
boxes. Two reference exclusions as in score_far_side: `glyph/1/0/10/14/1`
(dropped by the loader) and `glyph/3/0/0/6/2` (n=43 tallies; its reference -4
is wrong, Sean says -6 -- reported separately).

    python3 benchmarks/omr-local-staff-2026-09/score_standard_box.py [--json f]
"""
from __future__ import annotations

import json
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
import shape_from_page as sfp  # noqa: E402
_argv, sys.argv = sys.argv, sys.argv[:1]   # r7 parses argv at import
import template_review_r7 as r7  # noqa: E402  (oval_vs_ink, make_templates)
sys.argv = _argv
import edge_census as ec  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402
from tools.omr.annotate import standard_head_box as shb  # noqa: E402

WRONG_REFERENCE = {"glyph/3/0/0/6/2"}          # Sean 2026-10-04
READER = dict(near_edge_ledgers=True, restore_masked_near_edge=True,
              far_side_ledger=True)
MIN_PAGE_SHAPE_HEADS = 8


def page_shapes(doc_id, heads_in):
    """Per-page measured shape (clean isolated ON-LINE filled heads), falling
    back to the document's where a page has fewer than 8 -- said out loud."""
    ok = [h for h in heads_in if h["kind"] == "filled" and h["isolated"] and h["meas"]["ok"]]
    on = [h for h in ok if h["pos"] % 2 == 0 and h["meas"]["angle_defined"]]
    med = lambda hs, k: float(np.median([h["meas"][k] for h in hs]))
    doc = dict(width_sp=med(on, "long_sp"), height_sp=med(on, "short_sp"),
               tilt_deg=med(on, "tilt"), n=len(on), source="document")
    out = {}
    for pg in sorted({h["page"] for h in heads_in}):
        sub = [h for h in on if h["page"] == pg]
        if len(sub) >= MIN_PAGE_SHAPE_HEADS:
            out[pg] = dict(width_sp=med(sub, "long_sp"), height_sp=med(sub, "short_sp"),
                           tilt_deg=med(sub, "tilt"), n=len(sub), source="page")
        else:
            out[pg] = dict(doc, source=f"document (page has {len(sub)} on-line heads)")
    return out, doc


def build(doc_id) -> Dict[str, Any]:
    loaded = ts.load_doc(doc_id)
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    heads_in = sfp.in_staff_heads(doc_id, loaded, pages)
    sfp.annotate_heads(doc_id, loaded, pages, heads_in)
    shapes, doc_shape = page_shapes(doc_id, heads_in)
    glyphs = sht._page_glyph_boxes(rec)
    nh = score._notehead_boxes_by_page(rec)
    acc = score._accidental_boxes_by_page(rec)
    tmpl, thick_by_page = {}, {}
    for pg, shp in shapes.items():
        ph = [h for h in heads_in if h["page"] == pg]
        thick = float(np.median([h["thickness"] for h in ph]))
        sp = float(np.median([h["spacing"] for h in ph]))
        tmpl[pg] = r7.make_templates(shp, thick, sp)
        thick_by_page[pg] = thick
    # far heads: ec.load_heads's population, reproduced
    rows = score._far_head_rows(doc_id, loaded)
    far = []
    for row in rows:
        if row["subject"] == "glyph/1/0/10/14/1" or not row["truth_pitches"] or not row["page_box"]:
            continue
        clef_v = rec.value(Q.CLEF, row["staff_key"])
        if clef_v is None:
            continue
        truth_pos = set(score.truth_positions(row["truth_pitches"], str(clef_v)))
        lr = rec.obs(Q.STAFF_LINES, row["staff_key"])
        if not truth_pos or not lr:
            continue
        gl = [float(y) for y in lr[-1]["value"]]
        gray = pages.get(row["page"])
        lines = score.frame_lines_for_head(gray, gl, row["page_box"])
        entry = {s: c for (s, c, b) in glyphs.get(row["page"], [])}
        cls = entry.get(row["subject"], "noteheadBlackOnLine")
        far.append(dict(doc=doc_id, subject=row["subject"], page=row["page"],
                        box=tuple(row["page_box"]), gray=gray, lines=lines,
                        boxes=nh.get(row["page"], []), acc=acc.get(row["page"], []),
                        truth=sorted(truth_pos), cls=cls,
                        kind="hollow" if sfp._kind(cls) == "hollow" else "filled",
                        spacing=(max(lines) - min(lines)) / 4.0))
    return dict(doc=doc_id, rec=rec, pages=pages, heads_in=heads_in, shapes=shapes,
                doc_shape=doc_shape, tmpl=tmpl, thick=thick_by_page, far=far, nh=nh, acc=acc)


def standard_for(h, D):
    shp, tm = D["shapes"][h["page"]], D["tmpl"][h["page"]]
    others = [b for (s, b) in D["nh"].get(h["page"], []) if s != h["subject"]] \
        + [b for (_s, b) in D["acc"].get(h["page"], [])]
    st = shb.standard_head_box(h["gray"], h["box"], h["spacing"], tm, shp, h["kind"], others)
    # fit on the OPENED ink, staff lines only (ledger-free)
    poly = ht.geometry_outline_poly(st["centre"][0], st["centre"][1], h["spacing"],
                                    shp["tilt_deg"], shp["width_sp"], shp["height_sp"])
    chk = r7.oval_vs_ink(h["gray"], h["box"], h["spacing"], D["thick"][h["page"]],
                         list(h["lines"]), poly, st["centre"][0], st["centre"][1])
    iou, off = chk["iou_open"], chk["offset_open_sp"]
    st["fit"] = dict(iou_open=iou, offset_open_sp=off,
                     iou_raw=chk["iou"], offset_raw_sp=chk["offset_sp"])
    st["pass"] = bool(st["placed"] and off is not None and iou >= shb.FIT_IOU_MIN
                      and off <= shb.FIT_OFFSET_MAX_SPACES)
    x0, y0, x1, y1 = h["box"]
    dcx, dcy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    sp = h["spacing"]
    st["shift_sp"] = (round((st["centre"][0] - dcx) / sp, 3), round((st["centre"][1] - dcy) / sp, 3))
    st["det_size_sp"] = (round((x1 - x0) / sp, 3), round((y1 - y0) / sp, 3))
    st["size_ratio"] = (round(st["size_sp"][0] / st["det_size_sp"][0], 3),
                        round(st["size_sp"][1] / st["det_size_sp"][1], 3))
    return st


def read(h, box, **kw):
    return score.reader_absolute_position(
        h["gray"], h["lines"], tuple(box), h["subject"], h["boxes"],
        page_accidental_boxes=h["acc"], four_causes_cd=True, **kw)


def run_arms(D):
    out = {}
    for h in D["far"]:
        st = standard_for(h, D)
        row = dict(st=st, truth=h["truth"], reads={})
        for arm, box in (("S0", h["box"]), ("S1", st["box"]),
                         ("S2", st["box"] if st["pass"] else h["box"])):
            pos, reason = read(h, box, **READER)
            row["reads"][arm] = dict(pos=pos, reason=reason, v=ec.verdict(pos, h["truth"]),
                                     box=[round(float(v), 2) for v in box])
        out[h["subject"]] = row
    return out


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if k != "match"}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def main():
    res, shape_out, Ds = {}, {}, {}
    for d in ts.DOCS:
        D = build(d)
        Ds[d] = D
        res[d] = run_arms(D)
        shape_out[d] = dict(doc=D["doc_shape"], pages=D["shapes"])
    print("== SHAPES (measured, per page) ==")
    for d in ts.DOCS:
        for pg, s in shape_out[d]["pages"].items():
            w, hh = shb.oval_extents_spaces(s["width_sp"], s["height_sp"], s["tilt_deg"])
            print(f"{d[:8]} p{pg}: oval {s['width_sp']:.2f}x{s['height_sp']:.2f} sp tilt {s['tilt_deg']:.1f}"
                  f" n={s['n']} [{s['source']}]  -> box extent {w:.2f}x{hh:.2f} sp")
    for excl, label in ((set(), "n=44/11"), (WRONG_REFERENCE, "n=43/11 (3/0/0/6/2 excluded)")):
        print(f"== {label}")
        for arm in ("S0", "S1", "S2"):
            for d in ts.DOCS:
                vs = [r["reads"][arm]["v"] for s, r in res[d].items() if s not in excl]
                print(f"{arm} {d:20} {ec.tally(vs)} n={len(vs)}")
    for a, b in (("S0", "S1"), ("S0", "S2")):
        print(f"\n--- {b} vs {a}: every changed head ---")
        for d in ts.DOCS:
            for s, r in res[d].items():
                o, n = r["reads"][a], r["reads"][b]
                if (o["pos"], o["v"]) != (n["pos"], n["v"]):
                    st = r["st"]
                    print(f"{d[:8]} {s:18} {o['pos']!s:>5} {o['v']:7} -> {n['pos']!s:>5} {n['v']:7} "
                          f"ref={r['truth']} shift={st['shift_sp']} size_ratio={st['size_ratio']} "
                          f"fit={st['fit']['iou_open']}/{st['fit']['offset_open_sp']} pass={st['pass']} | {n['reason'][:110]}")
        print("right heads broken:", [s for d in ts.DOCS for s, r in res[d].items()
                                        if r["reads"][a]["v"] == "right" and r["reads"][b]["v"] != "right"])
    n_pass = {d: (sum(r["st"]["pass"] for r in res[d].values()), len(res[d])) for d in ts.DOCS}
    print("\ngate pass (pass, total):", n_pass)
    for d in ts.DOCS:
        sh = np.array([r["st"]["shift_sp"] for r in res[d].values()])
        mag = np.hypot(sh[:, 0], sh[:, 1])
        sr = np.array([r["st"]["size_ratio"] for r in res[d].values()])
        print(f"{d[:8]} centre shift detector->standard (sp): median {np.median(mag):.2f} p90 {np.percentile(mag,90):.2f} max {mag.max():.2f};"
              f" size ratio w median {np.median(sr[:,0]):.2f} [{sr[:,0].min():.2f},{sr[:,0].max():.2f}] h median {np.median(sr[:,1]):.2f} [{sr[:,1].min():.2f},{sr[:,1].max():.2f}]")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(dict(shapes=_clean(shape_out), results=_clean(res)), indent=1, default=str))
    return Ds, res


if __name__ == "__main__":
    main()
