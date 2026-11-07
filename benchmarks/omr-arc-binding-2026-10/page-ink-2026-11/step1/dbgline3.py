"""2.274 r3: the line model at a page point.   R2_CACHE=.. R2_SLICES=.. python3 dbgline3.py PLATE PAGE X Y"""
import pathlib
import sys

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz3  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402

plate, page, X, Y = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
canvas, raw, sp, line_ys, boxes, areas, arc_boxes = viz3.load(plate, page)
scale = min(1.0, m.TARGET_SP_PX / sp)
rf = cv2.resize((raw == 0).astype(np.float32), None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else (raw == 0).astype(np.float32)
model = m.line_model(rf, line_ys, sp * scale, scale)
x = int(X * scale)
y = Y * scale
print("sp", sp, "scale", scale, "n lines", len(line_ys), "model", len(model))
for k, md in enumerate(model):
    if abs(md["c"][x] - y) < 3 * sp * scale:
        print(k, "c %.1f t %.1f tmed %.1f have %s top %d bot %d" % (md["c"][x], md["t"][x], md["tmed"], md["have"][x], md["top"][x], md["bot"][x]))
col = (canvas[:, X] == 0)
rc = (raw[:, X] == 0)
ys = np.arange(Y - 12, Y + 12)
print("canvas", "".join("#" if col[v] else "." for v in ys))
print("raw   ", "".join("#" if rc[v] else "." for v in ys))
print("y from", Y - 12)
print([round(v, 1) for v in line_ys if abs(v - Y) < 40])
