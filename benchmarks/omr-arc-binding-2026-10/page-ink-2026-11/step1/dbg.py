"""2.274 step 1: why does a detector curve have no run? Lists, for each curve id, the blanked ink under it, the boxes/areas that blank it,
and every track in its place with the reason `_judge` gave.   python3 dbg.py PLATE PAGE WORKDIR ID [ID ...]"""
import json
import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import measure as M  # noqa: E402
from tools.omr.staged import page_arcs as m, lane_report as L, pipeline as P, page_strokes as PS, barline_columns as BC  # noqa: E402

plate, page, wd = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3])
ids = [int(x) for x in sys.argv[4:]]
J = json.load(open(wd / ("%s-p%d.step1.json" % (plate, page))))
import os
z = np.load(os.environ["R2_CACHE"] + "/%s-p%d.canvas.npz" % (plate, page), allow_pickle=True)
canvas, sp, staves = z["canvas"], float(z["sp"]), json.loads(str(z["staves"]))
rows, curves, refused = M.slice_rows(plate, page, os.environ["R2_SLICES"])
boxes, areas, arc_boxes = m.inputs_from_rows(rows)
ink = canvas == 0
blank = m.blank_mask(ink, boxes, areas)
line_ys = [y for s in staves for y in s['lines']]
scale = min(1.0, 16 / sp)
sp_s = sp * scale
ink2 = ink & ~blank
small = cv2.resize(ink2.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96
cols = m._column_runs(small.astype(np.int8), int(round(m.RUN_MAX_SP * sp_s)))
tr = [q for t in m._track(cols, sp_s, small.shape[1]) for q in m._split_at_cusps(t, sp_s)]
lines = np.array(sorted(y * scale for y in line_ys))
for i in ids:
    c = J["curves"][i]
    x0, y0, x1, y1 = [int(v) for v in c["box"]]
    print("curve", i, c["box"], "sp", round(sp, 1))
    reg = (slice(max(0, y0 - 8), y1 + 8), slice(x0, x1))
    print("  ink px", int(ink[reg].sum()), "blanked ink px", int((ink & blank)[reg].sum()))
    for cls, b in boxes:
        if b[2] > x0 and b[0] < x1 and b[3] > y0 and b[1] < y1:
            print("  blank box", cls, [round(v) for v in b])
    for cls, b in areas:
        if b[2] > x0 and b[0] < x1 and b[3] > y0 and b[1] < y1:
            print("  area", cls, [round(v) for v in b])
    for t in tr:
        p = np.array(t["pts"])
        if len(p) < 3:
            continue
        px0, px1 = p[0, 0] / scale, p[-1, 0] / scale
        py = np.median(p[:, 1]) / scale
        if px1 < x0 or px0 > x1 or py < y0 - 12 or py > y1 + 12:
            continue
        v, info = m._judge(t, sp_s, lines)
        print("  track x %.0f-%.0f y %.0f n %d -> %s thick %.2f" % (px0, px1, py, len(p), v, np.median(p[:, 2]) / sp_s))
