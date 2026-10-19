"""ROADMAP 2.166 -- where is a glyph on the page, and what did the system-arc reader do near it (debug).
usage: glyph_debug.py DOC PAGE GLYPH [OUT.png]"""
import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-arcs-system-2026-10/probe")
import arc_debug  # noqa: E402
from tools.omr.staged import arcs_system as AS  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402

doc, pg, glyph = sys.argv[1], int(sys.argv[2]), sys.argv[3]
pws, cells, local, dets, log, summary, traces = arc_debug.run(doc, pg)
_, _, sy, st, m, gi = glyph.split("/")
c = [c for c in cells if local.get(c.staff_index) == (int(sy), int(st)) and c.measure_index == int(m)][0]
d = dets[R.cell(pg, int(sy), int(st), int(m)).to_key()][int(gi)]
b = AS._page_box(c, d)
print(glyph, d.smufl_name, [int(v) for v in b], "cell", c.bbox_page_px)
for a in summary["arcs_detail"]:
    if a["x_right_page"] >= b[0] - 60 and a["x_left_page"] <= b[2] + 60 and abs(a["y_left_page"] - b[1]) < 60:
        print(" arc", a["subject"], a["shape"], a["x_left_page"], a["x_right_page"], a["y_left_page"],
              [(t["glyph"], t["class"], t["residual_spaces2"], t["stroke_only"]) for t in a["through_boxes"]])
for t in traces:
    tb = t["box"]
    if tb[2] >= b[0] - 80 and tb[0] <= b[2] + 20 and abs(tb[1] - b[1]) < 40:
        print(" trace box", [int(v) for v in tb], t["coverage"], t["x0"], t["x1"])
if len(sys.argv) > 4:
    os.environ.setdefault("DBG_SCALE", "4")
    arc_debug.draw(pws, cells, local, dets, summary, traces,
                   [int(b[0]) - 120, int(b[1]) - 50, int(b[2]) + 60, int(b[3]) + 50], sys.argv[4])
