"""2.274 r3: the ink component at a page point and why it is / is not an arc component.   R2_CACHE=.. R2_SLICES=.. python3 dbgcomp3.py PLATE PAGE X Y"""
import pathlib
import sys

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz3  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402

plate, page, X, Y = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
canvas, raw, sp, line_ys, boxes, areas, arc_boxes = viz3.load(plate, page)
ink = canvas == 0
n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
i = int(lab[Y, X])
print("component", i, "bbox", st[i][:4].tolist(), "w/sp %.1f" % (st[i][2] / sp))
x0, y0, w, h = [int(v) for v in st[i][:4]]
mm = lab[y0:y0 + h, x0:x0 + w] == i
multi = sum(1 for x in range(w) if 1 + np.count_nonzero(np.diff(np.flatnonzero(mm[:, x])) > 1) > 1 and mm[:, x].any())
th = [int(mm[:, x].sum()) for x in range(w) if mm[:, x].any()]
print("cols", w, "multi", multi, "median th %.1f (max run %.1f)" % (np.median(th), m.RUN_MAX_SP * sp), "max th", max(th))
print("is arc component:", m._is_arc_component(lab, i, x0, y0, w, h, sp))
