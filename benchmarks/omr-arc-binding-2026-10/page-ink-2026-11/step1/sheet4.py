"""2.274 r4: my own contact sheet of detector curves by class (debugging, never a tile for Sean).

    R2_CACHE=.. python3 sheet4.py RESDIR OUT.png CLASS N SEED [STEM ...]
CLASS: pair (union >= .8, no single run whole) | miss (kept, best < .8, union < .8) | straight | no_track | sparse (the reader's why_no_run) | any
Each cell: raw ink grey, erased canvas black, each run of the page a different colour, detector curve trace in blue; caption stem, curve index, best / union, why.
"""
import json
import os
import pathlib
import random
import sys

import cv2
import numpy as np

resd, out, cls, n, seed = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
stems = sys.argv[6:] or sorted(p.name.replace(".step1.json", "") for p in resd.glob("*.step1.json"))
COL = [(0, 170, 0), (200, 0, 200), (0, 140, 255), (200, 120, 0), (0, 0, 200)]
items = []
for stem in stems:
    J = json.load(open(resd / (stem + ".step1.json")))
    for i, c in enumerate(J["curves"]):
        if c["refused"] or c["best"] >= 0.8:
            continue
        why = (c.get("why_no_run") or "?").split("(")[0]
        k = "pair" if c["union"] >= 0.8 else "miss"
        if cls in ("pair", "miss") and k != cls:
            continue
        if cls not in ("pair", "miss", "any") and why != cls:
            continue
        if cls != "pair" and k == "pair" and cls != "any":
            continue
        items.append((stem, i, c, J))
random.Random(seed).shuffle(items)
items = items[:n]
cells = []
cache = {}
for stem, i, c, J in items:
    if stem not in cache:
        z = np.load(os.environ["R2_CACHE"] + "/%s.canvas.npz" % stem, allow_pickle=True)
        cache[stem] = (z["canvas"], z["raw"], float(z["sp"]))
    canvas, raw, sp = cache[stem]
    x0, y0, x1, y1 = c["box"]
    a, b, e, d = int(max(0, x0 - 1.5 * sp)), int(max(0, y0 - 2 * sp)), int(min(raw.shape[1], x1 + 1.5 * sp)), int(min(raw.shape[0], y1 + 2 * sp))
    img = np.full((d - b, e - a, 3), 255, np.uint8)
    img[(raw[b:d, a:e] == 0)] = (200, 200, 200)
    img[(canvas[b:d, a:e] == 0)] = (0, 0, 0)
    sc = min(3.0, 640.0 / max(1, e - a))
    img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    for k, r in enumerate(J["runs"]):
        if r["box"][2] < a or r["box"][0] > e or r["box"][3] < b or r["box"][1] > d:
            continue
        P = ((np.array(r["pts"]) - [a, b]) * sc).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [P], False, COL[k % len(COL)], 2)
    cell = np.full((min(img.shape[0], 260) + 16, 650, 3), 255, np.uint8)
    cell[16:16 + min(img.shape[0], 260), :min(650, img.shape[1])] = img[:260, :650]
    cv2.putText(cell, "%s c%d best %.2f un %.2f %s w%.0f" % (stem, i, c["best"], c["union"], c.get("why_no_run"), (c["x1"] - c["x0"]) / sp), (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
    cells.append(cell)
per = 8
rows = []
for j in range(0, len(cells), 2):
    pair = cells[j:j + 2]
    h = max(p.shape[0] for p in pair)
    pair = [np.pad(p, ((0, h - p.shape[0]), (0, 0), (0, 0)), constant_values=255) for p in pair]
    if len(pair) == 1:
        pair.append(np.full_like(pair[0], 255))
    rows.append(np.hstack(pair))
for p in range(0, len(rows), per // 2):
    cv2.imwrite(out.replace(".png", "-%d.png" % (p // (per // 2))), np.vstack(rows[p:p + per // 2]))
print(len(cells), "cells")
