"""One head: its box (page px), its Q.PAGE_STEM, every Q.STEM row of its cell in page px with reader, tip ink and beam levels. Usage: cell_stems.py REC glyph"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "benchmarks/page-ledger-2026-11")
import m4a_controls as M
from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])
g = sys.argv[2]
cell = "cell/" + "/".join(g.split("/")[1:5])
Q = M.rows_by_quantity(rec)
geo = M.cell_geometry(Q)
(rx0, ry0, rx1, ry1), up = geo[cell]
hb = [o for o in Q["glyph_box"] if o["subject"] == g][0]
print("head", hb["value"][:1], [round(v) for v in hb["detail"]["bbox_page_px"]])
for o in Q["page_stem"]:
    if o["subject"] == g:
        print("page stem ->", o["value"], json.dumps(o["detail"], default=str)[:400])
tip = collections.defaultdict(list)
for o in Q["stem_tip_ink"] + Q["beam_stem_levels"]:
    d = o.get("detail") or {}
    sid = d.get("stem_row_id") or d.get("stem_row")
    tip[sid].append((o["quantity"], o["value"], d.get("end")))
for o in Q["stem"]:
    if o["subject"] != cell:
        continue
    x, y, w, h = o["value"][:4]
    pb = [rx0 + x / up, ry0 + y / up, rx0 + (x + w) / up, ry0 + (y + h) / up]
    print(" STEM", o["id"], o["reader"], [round(v) for v in pb], tip.get(o["id"]))
