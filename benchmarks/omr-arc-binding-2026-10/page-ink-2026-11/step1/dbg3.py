"""2.274 r2: list the runs and rejected tracks in a page window.   R2_CACHE=.. R2_SLICES=.. python3 dbg3.py PLATE PAGE X0 Y0 X1 Y1"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402

plate, page = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1 = [int(v) for v in sys.argv[3:7]]
canvas, sp, line_ys, boxes, areas, arc_boxes = viz.load(plate, page)
res = m.read_runs(canvas, sp, line_ys, boxes, areas, keep_rejected=True)
print("sp", sp, "scale", res["scale"])
for q in res["rejected_tracks"]:
    P = np.array(q["pts"])
    if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].min() > y1 or P[:, 1].max() < y0:
        continue
    print("rej", q["why"], "x %.0f-%.0f" % (P[0, 0], P[-1, 0]), "n", len(P), "y %.0f..%.0f" % (P[:, 1].min(), P[:, 1].max()))
for r in res["runs"]:
    if r["box"][2] < x0 or r["box"][0] > x1 or r["box"][3] < y0 or r["box"][1] > y1:
        continue
    print("run", r["id"], [round(v) for v in r["box"]], r["width_sp"])
