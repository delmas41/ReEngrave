"""2.305 r10 -- crops of the page-ink reader's run mask where an arc crosses a barline: grey = the page raster, black = the canvas the reader reads
(staff lines erased, barline columns carved -- white gaps), red = ink blanked as claimed by another mark, green = the run's points.

    python3 crossing_crops.py CANVAS_DIR PLATE PAGE RECORD.json OUT.png X0 Y0 X1 Y1 [--header-claim 0|1]
"""
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2  # noqa: E402
import numpy as np  # noqa: E402

import dbg_runs as D  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402


def main():
    cdir, plate, page, rec, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[6:10])
    if "--header-claim" in sys.argv:
        m.HEADER_BOX_NEEDS_CLAIM = int(sys.argv[sys.argv.index("--header-claim") + 1])
    canvas, raw, sp, line_ys, boxes, areas, ab = D.load(cdir, plate, page, rec)
    res = m.read_runs(canvas, sp, line_ys, boxes, areas, raw=raw, arc_boxes=ab)
    bx = m.unclaimed_header_boxes_dropped(boxes, areas)
    ink = canvas == 0
    bl = m.blank_mask(ink, bx, areas, sp)
    img = np.full((y1 - y0, x1 - x0, 3), 255, np.uint8)
    r = raw[y0:y1, x0:x1] == 0
    c = ink[y0:y1, x0:x1]
    b = bl[y0:y1, x0:x1]
    img[r] = (200, 200, 200)
    img[c] = (0, 0, 0)
    img[c & b] = (0, 0, 255)
    k = max(1, int(round(600.0 / (x1 - x0))))
    img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
    for rr in res["runs"]:
        P = [(int((p[0] - x0) * k), int((p[1] - y0) * k)) for p in rr["pts"] if x0 <= p[0] < x1 and y0 <= p[1] < y1]
        for a, z in zip(P, P[1:]):
            cv2.line(img, a, z, (0, 180, 0), max(1, k // 2))
    cv2.imwrite(out, img)
    print(out, img.shape)


if __name__ == "__main__":
    main()
