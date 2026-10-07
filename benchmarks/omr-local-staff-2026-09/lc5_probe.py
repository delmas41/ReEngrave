"""lane-lines-combined: for one far head, swap the ONE input at a time (staff lines old/new, box old/new) and show which of the
walk's rungs and which answer each gives. Which input moves the answer is the step to look at.

  python3 lc5_probe.py <litolff|brahms> <scan.json> <subject> [<subject> ...]      (read-only; the record only for the exclusion boxes)"""
import collections, json, sys
sys.path.insert(0, '.')
import cv2
import farhead_note_first_oos as O
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

which, js, subjects = sys.argv[1], sys.argv[2], [a for a in sys.argv[3:] if a != '--trace']
fname = {"litolff": "beethoven5-litolff-mvt1-whole-20261006-night-combined.record.json",
         "brahms": "brahms1-breitkopf-mvt1-whole-20261006-night-combined.record.json"}[which]
doc = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}[which]
rec = EXP.Record(load_record(O.SHARED / fname))
glyphs = collections.defaultdict(list)
pages = {int(s.split("/")[1]) for s in subjects}
for o in rec.observations:
    if o["quantity"] == Q.GLYPH_BOX and o.get("value"):
        p = int(o["subject"].split("/")[1])
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb and p in pages:
            glyphs[p].append((o["subject"], o["value"][0], tuple(float(v) for v in pb),
                              float(o.get("score") if o.get("score") is not None else 1.0)))
heads_json = json.load(open(js))["heads"]
_w, _c, _v = lg._walk_ladder, lg.collapse_head_edge_rungs_to_middle, lg._rung_row_clears_box
def _walk(edge_y, sign, bands, spacing, target_y=None):
    r = _w(edge_y, sign, bands, spacing, target_y)
    print("      walk: edge", round(edge_y, 1), "sp", round(spacing, 2), "bands", [round(b, 1) for b in bands], "->", [round(v, 1) for v in r])
    return r
def _col(rungs, sign, box, *a, **k):
    r = _c(rungs, sign, box, *a, **k)
    if list(r) != list(rungs):
        print("      collapse dropped", [round(v, 1) for v in rungs], "->", [round(v, 1) for v in r], "box y", round(box[1], 1), round(box[3], 1))
    return r
def _clr(img, y, x, hb, sp, ex=None):
    r = _v(img, y, x, hb, sp, ex)
    if not r:
        print("      clears_box REFUSED rung", round(y, 1))
    return r
if "--trace" in sys.argv:
    lg._walk_ladder, lg.collapse_head_edge_rungs_to_middle, lg._rung_row_clears_box = _walk, _col, _clr
FH.EXCLUSION_RULES["jut_from_ink"] = True
for page in sorted(pages):
    pi = render_page_matching_gather(ts.DOCS[doc]["pdf"], page, 600)
    gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
    heads, staff_lines, page_boxes = O.page_inputs(rec, page, glyphs[page])
    ctx = FH.FarHeadPage(gray, heads, page_boxes, staff_lines)
    for s in [x for x in subjects if int(x.split("/")[1]) == page]:
        r = heads_json[s]
        o, n = r["old"]["read"], r["new"]["read"]
        print("==", s, "old", o["pos"], o["box_source"], "| new", n["pos"], n["reason"][:60], n["box_source"])
        for ln_name, ln in (("old lines", o["lines"]), ("new lines", n["lines"])):
            for bx_name, bx in (("old box", o["box_used"]), ("new box", n["box_used"])):
                x0, y0, x1, y1 = bx
                others = lg.exclusion_boxes_for(s, bx, ctx.nh, ctx.acc,
                                                drop_same_ink_other_staff=FH.READER_KEYWORDS["drop_same_ink_other_staff"])
                ys = sorted(ln)
                cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                side = "above" if cy < ys[0] else "below"
                sign = -1.0 if side == "above" else 1.0
                edge = ys[0] if side == "above" else ys[-1]
                sp = (ys[-1] - ys[0]) / 4.0
                rungs = lg.measure_ledger_rungs(
                    gray, ys, cx, head_y=cy, exclude_boxes=others, head_box_x=(x0, x1),
                    collapse_edges_box=(x0, y0, x1, y1), head_center_y=None,
                    restore_masked_staff_side_rungs=FH.READER_KEYWORDS["restore_masked_near_edge"]).get(side, [])
                nf = lg.derive_note_first_step(gray, (x0, y0, x1, y1), edge, sign, sp, rungs, exclude_boxes=others,
                                               far_side_partner_boxes=[b for (s_, b) in ctx.nh if s_ != s],
                                               ledger_not_text=True, text_boxes=ctx.text_boxes, edge_vs_through=True)
                pos = None if nf["offset"] is None else (0 if side == "above" else 8) + int(sign * nf["offset"])
                print(f"   {ln_name:9s} {bx_name:7s} rungs {[round(v, 1) for v in rungs]}  -> {pos} {nf['reason'][:70]}")
