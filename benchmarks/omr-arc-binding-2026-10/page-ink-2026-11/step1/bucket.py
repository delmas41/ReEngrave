"""2.274 step 1: a contact sheet of detector curves with no whole run, one reason at a time, across pages (my own look; orange box = detector curve,
green = ink runs).   python3 bucket.py WORKDIR WHY N [--blank] [--seed 1]  -> WORKDIR/bucket.WHY.png and the labels."""
import json
import pathlib
import random
import re
import sys

import cv2
import numpy as np

wd = pathlib.Path(sys.argv[1])
why, n = sys.argv[2], int(sys.argv[3])
want_blank = "--blank" in sys.argv
seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
items = []
for p in sorted(wd.glob("*.step1.json")):
    stem = p.name.replace(".step1.json", "")
    J = json.load(open(p))
    for k, c in enumerate(J["curves"]):
        if c["refused"] or c["best"] >= 0.8:
            continue
        if why != "all" and re.sub(r"\(.*", "", c["why_no_run"] or "?") != why:
            continue
        if why != "all" and (c["blank_share"] >= 0.3) != want_blank:
            continue
        items.append((stem, k, c))
random.Random(seed).shuffle(items)
items = items[:n]
imgs = {}
tiles = []
for stem, k, c in items:
    if stem not in imgs:
        imgs[stem] = (cv2.imread(str(wd / (stem + ".raw.png")), 0), json.load(open(wd / (stem + ".step1.json"))))
    img, J = imgs[stem]
    sp = J["summary"]["sp"]
    H, W = img.shape
    x0, y0, x1, y1 = c["box"]
    m = 1.5 * sp
    a, b, cc, d = int(max(0, x0 - m)), int(max(0, y0 - m)), int(min(W, x1 + m)), int(min(H, y1 + m))
    crop = cv2.cvtColor(img[b:d, a:cc], cv2.COLOR_GRAY2BGR)
    sc = min(3.0, 280.0 / max(1, cc - a), 150.0 / max(1, d - b))
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
    ov = crop.copy()
    for r in J["runs"]:
        if r["box"][2] < a or r["box"][0] > cc or r["box"][3] < b or r["box"][1] > d:
            continue
        P = (np.array(r["pts"]) - [a, b]) * sc
        cv2.polylines(ov, [P.astype(np.int32).reshape(-1, 1, 2)], False, (0, 160, 0), 1)
    cv2.rectangle(ov, (int((x0 - a) * sc), int((y0 - b) * sc)), (int((x1 - x0) * sc + (x0 - a) * sc), int((y1 - b) * sc)), (0, 140, 255), 1)
    cv2.putText(ov, "%s c%d %s" % (stem.replace("brahms", "B").replace("litolff", "L"), k, c["why_no_run"]), (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    canvas = np.full((160, 300, 3), 255, np.uint8)
    t = ov[:160, :300]
    canvas[:t.shape[0], :t.shape[1]] = t
    tiles.append(canvas)
while len(tiles) % 4:
    tiles.append(np.full((160, 300, 3), 255, np.uint8))
rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
for part in range(0, len(rows), 6):
    out = wd / ("bucket.%s%s.%d.png" % (why, ".blank" if want_blank else "", part // 6))
    cv2.imwrite(str(out), np.vstack(rows[part:part + 6]))
    print(out)
print(len(items))
