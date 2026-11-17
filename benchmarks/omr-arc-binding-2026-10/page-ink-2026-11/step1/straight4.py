"""2.274 r4: what the tracks refused "straight" look like, by whether they lie under a kept detector curve (a real arc, taken as such) or under no detector arc box (lines, legs, beams).

    R2_CACHE=.. R2_SLICES=.. python3 straight4.py DIR PLATE:PAGE [...]      DIR = a measure output dir (for the detector curves)
Prints per straight track: width (sp), bow/width, mid thickness (sp), end/mid taper, the share of its columns thicker than 1.25x the track's own median, and the group.
"""
import json
import os
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz3 as V  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402

seen = []
_orig = m._judge


def _wrap(t, sp, lines, **kw):
    v, info = _orig(t, sp, lines, **kw)
    if v == "straight":
        seen.append((t, sp))
    return v, info


m._judge = _wrap


def metrics(t, sp, scale):
    p = np.array(t["pts"], float)
    x, y, th = p[:, 0], p[:, 1], p[:, 2]
    width = x[-1] - x[0] + 1
    deg = 4 if width > 8 * sp else 2
    c = np.polyfit(x, y, deg)
    fit = np.polyval(c, x)
    line_y = fit[0] + (fit[-1] - fit[0]) * (x - x[0]) / max(1.0, x[-1] - x[0])
    dev = fit - line_y
    sag = float(dev[np.argmax(np.abs(dev))])
    f = (x - x[0]) / max(1.0, x[-1] - x[0])

    def med(sel):
        return float(np.median(th[sel])) if sel.any() else float("nan")
    mid = med((f >= 0.3) & (f <= 0.7))
    el, er = med(f <= 0.15), med(f >= 0.85)
    def mean(sel):
        return float(np.mean(th[sel])) if sel.any() else float("nan")
    mm = mean((f >= 0.35) & (f <= 0.65))
    me = 0.5 * (mean(f <= 0.12) + mean(f >= 0.88))
    return dict(mt=round(me / max(mm, 1e-6), 2), mm=round(mm / sp, 2), w=round(width / sp, 1), bow=round(abs(sag) / width, 4), mid=round(mid / sp, 2), taper=round(min(el, er) / max(mid, 1e-6), 2),
                el=round(el / sp, 2), er=round(er / sp, 2), x0=float(x[0] / scale), x1=float(x[-1] / scale), y=float(np.median(y) / scale))


def main():
    resd = pathlib.Path(sys.argv[1])
    for pp in sys.argv[2:]:
        plate, page = pp.split(":")
        page = int(page)
        canvas, raw, sp, line_ys, boxes, areas, arc_boxes = V.load(plate, page)
        seen.clear()
        res = m.read_runs(canvas, sp, line_ys, boxes, areas, keep_rejected=True, raw=raw)
        J = json.load(open(resd / ("%s-p%d.step1.json" % (plate, page))))
        kept = [c for c in J["curves"] if not c["refused"] and c["best"] < 0.8]
        scale = res["scale"]
        for t, s in seen:
            if len(t["pts"]) < 5:
                continue
            q = metrics(t, s, scale)
            grp = "B"
            for c in kept:
                if min(q["x1"], c["x1"]) - max(q["x0"], c["x0"]) > 0.5 * (q["x1"] - q["x0"]) and c["box"][1] - sp <= q["y"] <= c["box"][3] + sp:
                    grp = "A"
                    break
            if any(abs(q["x0"] - b["box"][0]) < 3 * sp and q["x1"] - q["x0"] > 0 and b["box"][1] - sp <= q["y"] <= b["box"][3] + sp and min(q["x1"], b["box"][2]) - max(q["x0"], b["box"][0]) > 0.5 * (q["x1"] - q["x0"]) for b in arc_boxes) and grp == "B":
                grp = "b"       # under a detector arc box (witness) but not under a kept missed curve
            print(pp, grp, json.dumps(q))


if __name__ == "__main__":
    main()
