"""2.274 r3: why two fragments in a window did / did not join.   R2_CACHE=.. R2_SLICES=.. python3 dbglink3.py PLATE PAGE X0 Y0 X1 Y1
Prints every pre-judge track with >= 3 points in the window (page px) and, for each ordered pair, the joint-fit numbers the linker uses."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz3  # noqa: E402
from tools.omr.staged import page_arcs as m  # noqa: E402

plate, page = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1 = [int(v) for v in sys.argv[3:7]]
canvas, raw, sp, line_ys, boxes, areas, arc_boxes = viz3.load(plate, page)
res = m.read_runs(canvas, sp, line_ys, boxes, areas, keep_rejected=True, raw=raw)
sc = res["scale"]
spr = res["sp"]
T = []
for t in res["all_tracks"]:
    P = np.array(t["pts"], float)
    if len(P) < 3:
        continue
    Q = P[:, :2] / sc
    if Q[:, 0].max() < x0 or Q[:, 0].min() > x1 or Q[:, 1].min() > y1 or Q[:, 1].max() < y0:
        continue
    T.append(t)
    print(len(T) - 1, "n", len(P), "x %.0f-%.0f" % (Q[0, 0], Q[-1, 0]), "y %.0f..%.0f" % (Q[:, 1].min(), Q[:, 1].max()), "linked" if t.get("linked") else "", "thick" if t.get("thick") else "")
for i, a in enumerate(T):
    for j, b in enumerate(T):
        if i == j:
            continue
        pa, pb = np.array(a["pts"], float), np.array(b["pts"], float)
        gx = pb[0, 0] - pa[-1, 0]
        if gx < -2 or gx > m.LINK_GAP_SP * spr:
            continue
        x = np.r_[pa[:, 0], pb[:, 0]]
        y = np.r_[pa[:, 1], pb[:, 1]]
        deg = 2 if (x.max() - x.min()) <= 8 * spr else 4
        c = np.polyfit(x, y, deg)
        r = y - np.polyval(c, x)
        print("pair", i, "->", j, "gap %.1f sp" % (gx / spr), "ydiff %.2f sp" % (abs(pb[0, 1] - pa[-1, 1]) / spr), "rms %.3f sp (max %.3f)" % (np.sqrt((r ** 2).mean()) / spr, np.abs(r).max() / spr))

# JUDGE=i,j : the verdict the judge gives the pair joined (gap counted as explained)
import os
if os.environ.get("JUDGE"):
    i, j = [int(v) for v in os.environ["JUDGE"].split(",")]
    a, b = T[i], T[j]
    pa, pb = a["pts"], b["pts"]
    gaps = list(a.get("gaps", [])) + list(b.get("gaps", [])) + [(pa[-1][0], pb[0][0])]
    lines = np.array(sorted(y * sc for y in line_ys))
    print("judge joined:", m._judge(dict(pts=list(pa) + list(pb), gaps=gaps), spr, lines))
    print("judge a:", m._judge(a, spr, lines)[0], "judge b:", m._judge(b, spr, lines)[0])
