"""lane-farhead-per-bar-grid: WHY does the page head-shape sample shrink (Litolff pool 50 -> 25 clean on-line heads)?
For the clean-head candidates `FarHeadPage.__init__` offers `measure_clean_head` (filled, on a line, isolated, symbol gate), the
reason word under OLD lines and NEW lines, per page.

  python3 farhead_per_bar_grid_shape_probe.py litolff 8
"""
import collections, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import farhead_note_first_oos as O
import farhead_per_bar_grid_lib as GL
import farhead_per_bar_grid_oos as S
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

which, page = sys.argv[1], int(sys.argv[2])
doc, fname, _ = S.DOCS[which]
rec = EXP.Record(load_record(O.SHARED / fname))
import collections as C
glyphs = C.defaultdict(list)
for o in rec.observations:
    if o["quantity"] == Q.GLYPH_BOX and o.get("value") and o["subject"].startswith(f"glyph/{page}/"):
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb:
            glyphs[page].append((o["subject"], o["value"][0], tuple(float(v) for v in pb), float(o.get("score") or 1.0)))
pi = render_page_matching_gather(ts.DOCS[doc]["pdf"], page, 600)
gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
heads, staff_lines, page_boxes = O.page_inputs(rec, page, glyphs[page])
grid_of = GL.bar_grids(rec, page, pi)[0]
fp = FH.FarHeadPage(gray, heads, page_boxes, staff_lines)
th = fp.thickness
res = {False: collections.Counter(), True: collections.Counter()}
detail = []
for h in heads:
    if not (0 <= h["pos"] <= 8 and FH.head_kind(h.get("cls"))):
        continue
    if FH.head_kind(h["cls"]) != "filled" or h["pos"] % 2 != 0:
        continue
    out = {}
    for new in (False, True):
        FH.READER_KEYWORDS["per_bar_grid"] = new
        g = (grid_of.get(GL.head_cell(h["subject"])) if new else None) or h["global_lines"]
        lines = FH.frame_lines_for_head(gray, g, h["box"])
        sp = (max(lines) - min(lines)) / 4.0
        hh = dict(h, spacing=sp)
        if not fp._isolated(hh) or not FH._symbol_gate(gray, hh, page_boxes):
            out[new] = "gated_out"
        else:
            m = FH.measure_clean_head(gray, h["box"], lines, sp, th)
            out[new] = (m["reason"] or "?") if not m["ok"] else ("OK" if m["angle_defined"] else "not_angle_defined")
        res[new][out[new]] += 1
    detail.append((h["subject"], out[False], out[True]))
FH.READER_KEYWORDS["per_bar_grid"] = True
print(which, page, "thickness", th, "\n OLD", dict(res[False]), "\n NEW", dict(res[True]))
for d in detail:
    if d[1] != d[2]:
        print("  differs", d)
