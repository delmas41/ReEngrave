"""2.274 step 1: 12 BLIND crops of out-of-sample runs for Sean. Nothing of ours drawn but ONE thin orange box round the WHOLE run (no arrows, no colours,
no labels); one staff; both ends visible. The key (which page, which run, why chosen) goes in a separate json.

    python3 crops12.py WORKDIR OUTDIR PLATE:PAGE [PLATE:PAGE ...]      (WORKDIR holds PLATE-pPAGE.step1.json and .raw.png; fresh pages only)

Mix: 4 runs no detector box witnesses (NEW), 4 that cross a barline (their witnessing boxes come from two or more cells), 4 other witnessed runs; random, seed 274.
The question: "Is the box one whole arc, end to end?"
"""
import json
import pathlib
import random
import sys

import cv2
import numpy as np

ORANGE = (0, 140, 255)       # BGR: the lane-report's neutral orange
wd, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
pages = sys.argv[3:]
out.mkdir(parents=True, exist_ok=True)
pool = {"new": [], "cross": [], "other": []}
data = {}
for pp in pages:
    plate, page = pp.split(":")
    stem = "%s-p%s" % (plate, page)
    J = json.load(open(wd / (stem + ".step1.json")))
    data[stem] = J
    for r in J["runs"]:
        if r["width_sp"] < 2.0:
            continue
        cells = {tuple(w.split("/")[1:5]) for w in r["witnesses"]}
        kind = "new" if not r["witnesses"] else "cross" if len(cells) >= 2 else "other"
        pool[kind].append((stem, r))
rng = random.Random(274)
pick = []
for kind, n in (("new", 4), ("cross", 4), ("other", 4)):
    rng.shuffle(pool[kind])
    pick += [(kind,) + t for t in pool[kind][:n]]
rng.shuffle(pick)
key = []
for i, (kind, stem, r) in enumerate(pick, 1):
    J = data[stem]
    sp = J["summary"]["sp"]
    img = cv2.imread(str(wd / (stem + ".raw.png")), 0)
    H, W = img.shape
    x0, y0, x1, y1 = r["box"]
    ym = (y0 + y1) / 2.0
    st = min(J["staves"], key=lambda s: abs((s["lines"][0] + s["lines"][-1]) / 2.0 - ym))
    top, bot = min(st["lines"][0], y0), max(st["lines"][-1], y1)
    a, b, c, d = int(max(0, x0 - 3 * sp)), int(max(0, top - 2.5 * sp)), int(min(W, x1 + 3 * sp)), int(min(H, bot + 2.5 * sp))
    crop = cv2.cvtColor(img[b:d, a:c], cv2.COLOR_GRAY2BGR)
    sc = min(3.0, 1000.0 / (c - a))
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC if sc > 1 else cv2.INTER_AREA)
    pad = 0.35 * sp
    cv2.rectangle(crop, (int((x0 - pad - a) * sc), int((y0 - pad - b) * sc)), (int((x1 + pad - a) * sc), int((y1 + pad - b) * sc)), ORANGE, 2)
    cv2.imwrite(str(out / ("tile-%02d.png" % i)), crop)
    key.append(dict(tile=i, plate_page=stem, run=r["id"], kind=kind, width_sp=r["width_sp"], witnesses=r["witnesses"][:6], box_page_px=[round(v) for v in r["box"]]))
json.dump(key, open(out / "key.json", "w"), indent=1)
print(len(key), "tiles ->", out)
