"""2.274 r2: 12 BLIND crops of HOLD-OUT runs for Sean. Nothing of ours drawn but ONE thin orange box round the WHOLE run (no arrows, no colours, no labels);
one staff; both ends visible. The key (page, run, why chosen) goes in a separate json.

    python3 crops_r2.py R2DIR R1DIR OUTDIR PLATE:PAGE [PLATE:PAGE ...]

Mix (seed 2742): 6 runs that round 1's reader did NOT cover whole and this one does (the fixed buckets: named by the reason round 1 gave) and 6 NEW runs no
detector box witnesses. The question: "Is the box one whole arc, end to end?"
"""
import json
import pathlib
import random
import re
import sys

import cv2
import numpy as np

ORANGE = (0, 140, 255)       # BGR: the lane-report's neutral orange
r2d, r1d, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
pages = sys.argv[4:]
out.mkdir(parents=True, exist_ok=True)
pool = {"fixed": [], "new": []}
data = {}
for pp in pages:
    plate, page = pp.split(":")
    stem = "%s-p%s" % (plate, page)
    J2, J1 = json.load(open(r2d / (stem + ".step1.json"))), json.load(open(r1d / (stem + ".step1.json")))
    data[stem] = J2
    runs = {r["id"]: r for r in J2["runs"]}
    for k, (c2, c1) in enumerate(zip(J2["curves"], J1["curves"])):
        if c2["refused"] or c2["best"] < 0.8 or c1["best"] >= 0.8 or c2["run"] not in runs:
            continue
        r = runs[c2["run"]]
        if r["width_sp"] < 2.0:
            continue
        why = re.sub(r"\(.*", "", c1.get("why_no_run") or "?")
        pool["fixed"].append((stem, r, "round-1 miss: %s" % why))
    for r in J2["runs"]:
        if not r["witnesses"] and r["width_sp"] >= 2.5:
            pool["new"].append((stem, r, "new"))
rng = random.Random(2742)
pick = []
for kind, n in (("fixed", 6), ("new", 6)):
    items = pool[kind]
    rng.shuffle(items)
    seen, chosen = set(), []
    for stem, r, why in items:                        # one run per tile, and spread over the reasons / pages first
        if r["id"] in seen:
            continue
        chosen.append((stem, r, why))
        seen.add(r["id"])
    by = {}
    for t in chosen:
        by.setdefault(t[2], []).append(t)
    order = []
    while any(by.values()) and len(order) < n:
        for w in sorted(by):
            if by[w] and len(order) < n:
                order.append(by[w].pop())
    pick += order
rng.shuffle(pick)
key = []
for i, (stem, r, why) in enumerate(pick, 1):
    J = data[stem]
    sp = J["summary"]["sp"]
    img = cv2.imread(str(r2d / (stem + ".raw.png")), 0)
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
    key.append(dict(tile=i, plate_page=stem, run=r["id"], why=why, width_sp=r["width_sp"], witnesses=r["witnesses"][:6], box_page_px=[round(v) for v in r["box"]]))
json.dump(key, open(out / "key.json", "w"), indent=1)
print(len(key), "tiles ->", out)
