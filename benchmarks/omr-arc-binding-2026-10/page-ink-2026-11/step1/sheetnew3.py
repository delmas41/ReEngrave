"""2.274 r3: my own contact sheet of the NEW runs (no witnessing detector box) of a measure output; debugging, not tiles for Sean.

    R2_CACHE=... python3 sheetnew3.py RESDIR OUTDIR STEM [STEM ...] [--base BASEDIR]   (--base: only the runs BASEDIR's reader did not already file, matched by box)
Each cell: raw ink grey, the erased canvas black, the run's polyline green; caption stem + run id.
"""
import json
import os
import pathlib
import sys

import cv2
import numpy as np

argv = sys.argv[1:]
base = None
if "--base" in argv:
    i = argv.index("--base")
    base = pathlib.Path(argv[i + 1])
    del argv[i:i + 2]
src = None
if "--src" in argv:
    i = argv.index("--src")
    src = argv[i + 1]
    del argv[i:i + 2]
resd, out = pathlib.Path(argv[0]), pathlib.Path(argv[1])
out.mkdir(parents=True, exist_ok=True)
cells, index = [], []
for stem in argv[2:]:
    J = json.load(open(resd / (stem + ".step1.json")))
    old = json.load(open(base / (stem + ".step1.json")))["runs"] if base else []
    z = np.load(os.environ["R2_CACHE"] + "/%s.canvas.npz" % stem, allow_pickle=True)
    canvas, raw, sp = z["canvas"], z["raw"], float(z["sp"])
    for r in J["runs"]:
        if os.environ.get("WITNESSED"):
            if not r["witnesses"]:
                continue
        elif (r["witnesses"] and not src) or (src and r.get("src") != src):
            continue
        if any(abs(o["box"][0] - r["box"][0]) < 0.5 * sp and abs(o["box"][2] - r["box"][2]) < 0.5 * sp and abs(o["box"][1] - r["box"][1]) < sp for o in old):
            continue
        x0, y0, x1, y1 = r["box"]
        a, b, cc, d = int(max(0, x0 - 2 * sp)), int(max(0, y0 - 2.5 * sp)), int(min(raw.shape[1], x1 + 2 * sp)), int(min(raw.shape[0], y1 + 2.5 * sp))
        img = np.full((d - b, cc - a, 3), 255, np.uint8)
        img[(raw[b:d, a:cc] == 0)] = (200, 200, 200)
        img[(canvas[b:d, a:cc] == 0)] = (0, 0, 0)
        sc = min(3.0, 420.0 / max(1, cc - a))
        img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
        P = ((np.array(r["pts"]) - [a, b]) * sc).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [P], False, (0, 170, 0), 1)
        cell = np.full((max(img.shape[0], 40) + 18, 430, 3), 255, np.uint8)
        cell[18:18 + min(img.shape[0], 300), :min(430, img.shape[1])] = img[:300, :430]
        cv2.putText(cell, "%s run %d w%.1f" % (stem, r["id"], r["width_sp"]), (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
        cells.append(cell)
        index.append(dict(stem=stem, run=r["id"], box=[round(v) for v in r["box"]], width=r["width_sp"]))
if os.environ.get("SAMPLE"):
    import random
    k = int(os.environ["SAMPLE"])
    order = list(range(len(cells)))
    random.Random(int(os.environ.get("SEED", "2743"))).shuffle(order)
    order = sorted(order[:k])
    cells = [cells[i] for i in order]
    index = [index[i] for i in order]
per = 6
for i in range(0, len(cells), per):
    chunk = cells[i:i + per]
    rows = []
    for j in range(0, len(chunk), 2):
        pair = chunk[j:j + 2]
        h = max(p.shape[0] for p in pair)
        pair = [np.pad(p, ((0, h - p.shape[0]), (0, 0), (0, 0)), constant_values=255) for p in pair]
        if len(pair) == 1:
            pair.append(np.full_like(pair[0], 255))
        rows.append(np.hstack(pair))
    cv2.imwrite(str(out / ("new-%02d.png" % (i // per))), np.vstack(rows))
json.dump(index, open(out / "index.json", "w"))
print(len(cells), "cells")
