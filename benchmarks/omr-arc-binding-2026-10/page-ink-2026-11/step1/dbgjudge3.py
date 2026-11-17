"""2.274 r3: what a window's tracks would measure if the roughness gate were off.   R2_CACHE=.. R2_SLICES=.. python3 dbgjudge3.py PLATE PAGE X0 Y0 X1 Y1 [NAME=VALUE ...]"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz3  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402

plate, page = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1 = [int(v) for v in sys.argv[3:7]]
for kv in sys.argv[7:]:
    k, v = kv.split("=")
    setattr(m, k, type(getattr(m, k))(v))
canvas, raw, sp, line_ys, boxes, areas, arc_boxes = viz3.load(plate, page)
res = m.read_runs(canvas, sp, line_ys, boxes, areas, keep_rejected=True, raw=raw)
for r in res["runs"]:
    if r["box"][2] < x0 or r["box"][0] > x1 or r["box"][3] < y0 or r["box"][1] > y1:
        continue
    print("RUN", [round(v) for v in r["box"]], "width %.1f sag %.3f thick %.2f resid %.3f inked %.2f" % (r["width_sp"], r["sagitta_sp"], r["thick_sp"], r["resid_sp"], r["inked"]))
for q in res["rejected_tracks"]:
    P = np.array(q["pts"])
    if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].min() > y1 or P[:, 1].max() < y0:
        continue
    print("rej", q["why"], "x %.0f-%.0f y %.0f..%.0f n %d" % (P[0, 0], P[-1, 0], P[:, 1].min(), P[:, 1].max(), len(P)))
