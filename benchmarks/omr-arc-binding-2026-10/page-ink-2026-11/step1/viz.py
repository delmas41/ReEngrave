"""2.274 r2: my own debugging picture of the reader on a cached canvas (not a tile for Sean).

    R2_CACHE=... R2_SLICES=... python3 viz.py PLATE PAGE OUT.png  X0 Y0 X1 Y1 [X0 Y0 X1 Y1 ...]    (page px windows; one panel each, stacked)
Ink black, ink the reader blanks red, runs green, every rejected track blue with its reason printed.
"""
import json
import os
import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import measure as M  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402


def load(plate, page):
    z = np.load(os.environ["R2_CACHE"] + "/%s-p%d.canvas.npz" % (plate, page), allow_pickle=True)
    canvas, sp, staves = z["canvas"], float(z["sp"]), json.loads(str(z["staves"]))
    rows, curves, refused = M.slice_rows(plate, page, os.environ["R2_SLICES"])
    boxes, areas, arc_boxes = m.inputs_from_rows(rows)
    line_ys = [y for s in staves for y in s["lines"]]
    return canvas, sp, line_ys, boxes, areas, arc_boxes


def main():
    plate, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    wins = [tuple(int(v) for v in sys.argv[i:i + 4]) for i in range(4, len(sys.argv), 4)]
    canvas, sp, line_ys, boxes, areas, arc_boxes = load(plate, page)
    res = m.read_runs(canvas, sp, line_ys, boxes, areas, keep_rejected=True)
    ink = canvas == 0
    blank = res.get("blank_mask")
    if blank is None:
        blank = m.blank_mask(ink, boxes, areas)
    panels = []
    for (x0, y0, x1, y1) in wins:
        crop = np.full((y1 - y0, x1 - x0, 3), 255, np.uint8)
        sub = ink[y0:y1, x0:x1]
        bl = blank[y0:y1, x0:x1]
        crop[sub & ~bl] = (0, 0, 0)
        crop[sub & bl] = (90, 90, 230)
        sc = min(5.0, 1100.0 / (x1 - x0))
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
        for r in res["runs"]:
            P = (np.array(r["pts"]) - [x0, y0]) * sc
            cv2.polylines(crop, [P.astype(np.int32).reshape(-1, 1, 2)], False, (0, 170, 0), 2)
        for q in res.get("rejected_tracks", []):
            P = (np.array(q["pts"]) - [x0, y0]) * sc
            if P[:, 0].max() < 0 or P[:, 0].min() > crop.shape[1]:
                continue
            cv2.polylines(crop, [P.astype(np.int32).reshape(-1, 1, 2)], False, (255, 120, 0), 1)
            cv2.putText(crop, "%s" % q["why"], (int(P[0, 0]), int(P[0, 1]) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        panels.append(crop)
    w = max(p.shape[1] for p in panels)
    panels = [np.pad(p, ((0, 6), (0, w - p.shape[1]), (0, 0)), constant_values=200) for p in panels]
    cv2.imwrite(out, np.vstack(panels))


if __name__ == "__main__":
    main()
