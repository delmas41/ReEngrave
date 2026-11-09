"""2.274 r4: 12 BLIND crops of NEW HOLD-OUT runs for Sean. Nothing of ours drawn but ONE thin orange box round the WHOLE run (no arrows, no colours, no labels);
one staff; both ends visible. The key (page, run, why chosen) goes in a separate json.

    python3 crops_r4.py R4DIR R3DIR OUTDIR PLATE:PAGE [PLATE:PAGE ...]    (R3DIR = the round-3 behaviour (every r4 mechanism off) on the same pages)

Mix (seed 2745): 4 runs round 3 did not cover whole and round 4 does, 3 long flat slurs, 3 arcs that meet another at a note, 2 other witnessed runs. The question: "Is the box one whole arc, end to end?"
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
pool = {"gained": [], "flat": [], "pair": [], "other": []}
data = {}
for pp in pages:
    plate, page = pp.split(":")
    stem = "%s-p%s" % (plate, page)
    J2, J1 = json.load(open(r2d / (stem + ".step1.json"))), json.load(open(r1d / (stem + ".step1.json")))
    data[stem] = J2
    runs = {r["id"]: r for r in J2["runs"]}
    sp_ = J2["summary"]["sp"]

    def alone(r):
        """RECUT rule (round 3): the rectangle must hold ONE arc. A run whose padded box also holds >= 30% of another run's points (a nested or neighbouring arc) is
        not asked about: Sean would be judging two arcs in one box."""
        x0, y0, x1, y1 = r["box"]
        pad = 0.35 * sp_
        for o in J2["runs"]:
            if o["id"] == r["id"] or o["box"][2] < x0 or o["box"][0] > x1:
                continue
            P = np.array(o["pts"])
            inn = (P[:, 0] >= x0 - pad) & (P[:, 0] <= x1 + pad) & (P[:, 1] >= y0 - pad) & (P[:, 1] <= y1 + pad)
            if inn.mean() >= 0.3:
                return False
        return True
    for k, (c2, c1) in enumerate(zip(J2["curves"], J1["curves"])):
        if c2["refused"]:
            continue
        if c2["best"] >= 0.8 and c1["best"] < 0.8 and c2["run"] in runs:
            r = runs[c2["run"]]
            if r["width_sp"] >= 2.0 and alone(r):
                pool["gained"].append((stem, r, "r3 miss, whole now: %s" % re.sub(r"\(.*", "", c1.get("why_no_run") or "?")))
        if c2["best"] < 0.8 and c2["union"] >= 0.8:           # a detector curve over two arcs that meet: each arc is its own run
            for r in J2["runs"]:
                if r["box"][2] >= c2["x0"] and r["box"][0] <= c2["x1"] and r["box"][3] >= c2["box"][1] - sp_ and r["box"][1] <= c2["box"][3] + sp_ and r["width_sp"] >= 4 and alone(r):
                    pool["pair"].append((stem, r, "meeting pair"))
    for r in J2["runs"]:
        if not alone(r):
            continue
        if r["width_sp"] >= 14 and abs(r["sagitta_sp"]) / r["width_sp"] <= 0.047 and r["witnesses"]:
            pool["flat"].append((stem, r, "long flat"))
        elif r["witnesses"] and r["width_sp"] >= 3:
            pool["other"].append((stem, r, "witnessed"))
rng = random.Random(2745)
pick = []
for kind, n in (("gained", 4), ("flat", 4), ("pair", 3), ("other", 5)):
    items = pool[kind]
    rng.shuffle(items)
    seen, order = set(), []
    for stem, r, why in items:
        if (stem, r["id"]) in seen or any(o[0] == stem and o[1]["id"] == r["id"] for o in pick):
            continue
        seen.add((stem, r["id"]))
        order.append((stem, r, why))
        if len(order) >= n:
            break
    pick += order
pick = pick[:12]
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
