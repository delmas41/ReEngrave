"""2.274 r3: the detector boxes and claimed areas that touch a page window.   R2_CACHE=.. R2_SLICES=.. python3 boxes3.py PLATE PAGE X0 Y0 X1 Y1"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz3  # noqa: E402

plate, page = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1 = [int(v) for v in sys.argv[3:7]]
canvas, raw, sp, line_ys, boxes, areas, arc_boxes = viz3.load(plate, page)


def hit(b):
    return not (b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1)


for c, b in boxes:
    if hit(b):
        print("box ", c, [round(v) for v in b])
for o, b in areas:
    if hit(b):
        print("area", o, [round(v) for v in b])
