"""ROADMAP 2.166 -- a cell's staff-erased raster before | after the arc erase, side by side (debug).
usage: cell_dump.py DOC PAGE SYSTEM STAFF CELL OUT.png [R0 R1]"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-arcs-system-2026-10/probe")
import cv2  # noqa: E402
import numpy as np  # noqa: E402

import arc_debug  # noqa: E402

doc, pg, sy, st, m, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
pws, cells, local, dets, log, summary, traces = arc_debug.run(doc, pg)
c = [c for c in cells if local.get(c.staff_index) == (sy, st) and c.measure_index == m][0]
a = c.image_no_staff_with_arcs if getattr(c, "image_no_staff_with_arcs", None) is not None else c.image_no_staff
b = c.image_no_staff
r0, r1 = (int(sys.argv[7]), int(sys.argv[8])) if len(sys.argv) > 8 else (0, a.shape[0])
img = np.concatenate([a[r0:r1], np.full((a[r0:r1].shape[0], 10), 128, np.uint8), b[r0:r1]], axis=1)
cv2.imwrite(out, cv2.resize(img, None, fx=0.5, fy=0.5))
print(c.bbox_page_px, c.upscale_factor, a.shape)
