"""2.274 r3: my own contact sheets of the uncovered kept detector curves (debugging, not tiles for Sean).

    R2_CACHE=... python3 sheet3.py RESDIR OUTDIR STEM [STEM ...]     -> OUTDIR/sheet-NN.png, OUTDIR/index.json
Each cell: the RAW page ink (grey), the erased canvas ink (black), the curve's box (orange), the reader's best partial run (green); caption = stem, curve index, reason.
"""
import json
import os
import pathlib
import sys

import cv2
import numpy as np

resd, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
cells, index = [], []
for stem in sys.argv[3:]:
    J = json.load(open(resd / (stem + ".step1.json")))
    z = np.load(os.environ["R2_CACHE"] + "/%s.canvas.npz" % stem.replace("-p", "-p"), allow_pickle=True)
    canvas, raw, sp = z["canvas"], z["raw"], float(z["sp"])
    runs = {r["id"]: r for r in J["runs"]}
    for k, c in enumerate(J["curves"]):
        if c["refused"] or c["best"] >= 0.8:
            continue
        x0, y0, x1, y1 = c["box"]
        a, b, cc, d = int(max(0, x0 - 2 * sp)), int(max(0, y0 - 2 * sp)), int(min(raw.shape[1], x1 + 2 * sp)), int(min(raw.shape[0], y1 + 2 * sp))
        img = np.full((d - b, cc - a, 3), 255, np.uint8)
        img[(raw[b:d, a:cc] == 0)] = (200, 200, 200)
        img[(canvas[b:d, a:cc] == 0)] = (0, 0, 0)
        sc = min(3.0, 420.0 / max(1, cc - a))
        img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
        cv2.rectangle(img, (int((x0 - a) * sc), int((y0 - b) * sc)), (int((x1 - a) * sc), int((y1 - b) * sc)), (0, 140, 255), 1)
        r = runs.get(c.get("run"))
        if r is not None and c["best"] > 0.1:
            P = ((np.array(r["pts"]) - [a, b]) * sc).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(img, [P], False, (0, 170, 0), 1)
        cap = "%s #%d %s %.2f" % (stem, k, c.get("why_no_run"), c["best"])
        cell = np.full((max(img.shape[0], 40) + 18, 430, 3), 255, np.uint8)
        cell[18:18 + img.shape[0], :min(430, img.shape[1])] = img[:, :430]
        cv2.putText(cell, cap, (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
        cells.append(cell)
        index.append(dict(stem=stem, curve=k, why=c.get("why_no_run"), best=c["best"], box=[round(v) for v in c["box"]]))
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
    w = max(r.shape[0] for r in rows)
    cv2.imwrite(str(out / ("sheet-%02d.png" % (i // per))), np.vstack(rows))
json.dump(index, open(out / "index.json", "w"))
print(len(cells), "cells")
