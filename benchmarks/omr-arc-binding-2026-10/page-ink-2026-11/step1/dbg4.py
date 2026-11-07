"""2.274 r2: print the column runs of a page window (reduced px = page px at scale 1).   python3 dbg4.py PLATE PAGE X0 X1 Y0 Y1"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402

plate, page = sys.argv[1], int(sys.argv[2])
x0, x1, y0, y1 = [int(v) for v in sys.argv[3:7]]
canvas, sp, line_ys, boxes, areas, arc_boxes = viz.load(plate, page)
ink = canvas == 0
blank = m.blank_mask(ink, boxes, areas)
ink2 = ink & ~blank
for x in range(x0, x1):
    col = np.flatnonzero(ink2[y0:y1, x]) + y0
    raw = np.flatnonzero(ink[y0:y1, x]) + y0
    print(x, "ink", (col.min(), col.max(), len(col)) if len(col) else None, "blank-only", int((ink & blank)[y0:y1, x].sum()), "raw", (raw.min(), raw.max()) if len(raw) else None)
