"""2.274 r4: the RAW (unerased, unblanked) vertical ink thickness along each run: a beam's edge piece sits on ink much thicker than the piece itself; a slur's run IS the ink.

    R2_CACHE=.. python3 rawth4.py RESDIR STEM [STEM ...]     RESDIR = a measure output dir (runs as filed)
Prints per run: id, NEW|wit, width (sp), mid raw thickness (sp), end/mid raw ratio, own thickness, share of the run's points whose raw ink column is taller than 0.45 sp.
"""
import json
import os
import pathlib
import sys

import numpy as np

resd = pathlib.Path(sys.argv[1])
for stem in sys.argv[2:]:
    J = json.load(open(resd / (stem + ".step1.json")))
    z = np.load(os.environ["R2_CACHE"] + "/%s.canvas.npz" % stem, allow_pickle=True)
    raw, sp = z["raw"] == 0, float(z["sp"])
    H, W = raw.shape
    for r in J["runs"]:
        P = np.array(r["pts"], float)
        th = []
        for x, y in P:
            xi, yi = int(round(x)), int(round(y))
            if not (0 <= xi < W and 0 <= yi < H) or not raw[yi, xi]:
                # nearest ink within 2 px vertically
                for d in (1, -1, 2, -2, 3, -3):
                    if 0 <= yi + d < H and raw[yi + d, xi]:
                        yi += d
                        break
                else:
                    th.append(np.nan)
                    continue
            a = yi
            while a > 0 and raw[a - 1, xi]:
                a -= 1
            b = yi
            while b < H - 1 and raw[b + 1, xi]:
                b += 1
            th.append(b - a + 1)
        th = np.array(th, float)
        f = (P[:, 0] - P[0, 0]) / max(1.0, P[-1, 0] - P[0, 0])
        mid = th[(f >= 0.3) & (f <= 0.7)]
        ends = th[(f <= 0.12) | (f >= 0.88)]
        mm = float(np.nanmedian(mid)) if np.isfinite(mid).any() else float("nan")
        me = float(np.nanmedian(ends)) if np.isfinite(ends).any() else float("nan")
        print("%s run %d %s w%.1f mid %.2f endratio %.2f own %.2f tall %.2f" % (stem, r["id"], "wit" if r["witnesses"] else "NEW", r["width_sp"], mm / sp, me / max(mm, 1e-6), r["thick_sp"], float(np.nanmean(th > 0.45 * sp))))
