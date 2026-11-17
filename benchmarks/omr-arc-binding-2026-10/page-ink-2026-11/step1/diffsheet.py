"""2.274 r2: curves covered whole in run A but not in run B (my own look; orange = the detector curve, green = B's runs).
    python3 diffsheet.py DIR_A DIR_B PLATE PAGE OUT.png
"""
import json
import pathlib
import sys

import cv2
import numpy as np

A, B, plate, page, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5]
stem = "%s-p%d" % (plate, page)
JA, JB = json.load(open(A / (stem + ".step1.json"))), json.load(open(B / (stem + ".step1.json")))
img = cv2.imread(str(B / (stem + ".raw.png")), 0)
sp = JB["summary"]["sp"]
H, W = img.shape
tiles = []
labels = []
for k, (ca, cb) in enumerate(zip(JA["curves"], JB["curves"])):
    if ca["refused"] or not (ca["best"] >= 0.8 and cb["best"] < 0.8):
        continue
    x0, y0, x1, y1 = cb["box"]
    m = 2.0 * sp
    a, b, c, d = int(max(0, x0 - m)), int(max(0, y0 - m)), int(min(W, x1 + m)), int(min(H, y1 + m))
    crop = cv2.cvtColor(img[b:d, a:c], cv2.COLOR_GRAY2BGR)
    sc = min(3.0, 380.0 / max(1, c - a), 165.0 / max(1, d - b))
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
    for r in JB["runs"]:
        if r["box"][2] < a or r["box"][0] > c or r["box"][3] < b or r["box"][1] > d:
            continue
        P = (np.array(r["pts"]) - [a, b]) * sc
        cv2.polylines(crop, [P.astype(np.int32).reshape(-1, 1, 2)], False, (0, 160, 0), 1)
    cv2.rectangle(crop, (int((x0 - a) * sc), int((y0 - b) * sc)), (int((x1 - a) * sc), int((y1 - b) * sc)), (0, 140, 255), 1)
    cv2.putText(crop, "c%d %s" % (k, cb["why_no_run"]), (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    t = np.full((170, 390, 3), 255, np.uint8)
    t[:min(170, crop.shape[0]), :min(390, crop.shape[1])] = crop[:170, :390]
    tiles.append(t)
    labels.append(k)
while len(tiles) % 3:
    tiles.append(np.full((170, 390, 3), 255, np.uint8))
rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
cv2.imwrite(out, np.vstack(rows[:9]))
print(labels)
