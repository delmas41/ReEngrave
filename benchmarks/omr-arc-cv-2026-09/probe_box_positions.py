"""Where do the adjudicated REAL and FAKE arc boxes sit relative to the staff
band? The certified fakes are described as neighbouring-staff bleed + staff
jags; this measures the position populations directly off the boxes."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
B = Path("benchmarks/omr-queue-arcs-2026-09")
mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}


def band(cid):
    ys = mans[cid].get("staff_line_ys_canonical") or []
    return (min(ys), max(ys), (max(ys) - min(ys)) / 4.0)


def rel(cid, box):
    t, b, sp = band(cid)
    x, y, w, h = box
    yc = y + h / 2.0
    if yc < t:
        return (yc - t) / sp
    if yc > b:
        return (yc - b) / sp
    return 0.0


real, fake = [], []
for vf in sorted((B / "verdicts").glob("*.verdict.json")):
    v = json.loads(vf.read_text())
    cid = v["cell_id"]
    for d in v.get("detections", []):
        cls = d.get("human_corrected_class") or d.get("model_predicted_class")
        bb = d.get("human_bbox") or d.get("model_bbox")
        if not bb:
            continue
        box = (bb["x"], bb["y"], bb["w"], bb["h"])
        if d.get("verdict") in ("TP", "WRONG_CATEGORY", "WRONG_BBOX") and cls in ("tie", "slur"):
            real.append((cid, cls, box, rel(cid, box)))
        elif d.get("verdict") == "FP" and d.get("model_predicted_class") in ("tie", "slur"):
            fake.append((cid, d["model_predicted_class"], box, rel(cid, box)))
    for a in v.get("added_detections", []):
        if a.get("human_class") in ("tie", "slur"):
            bb = a["bbox"]
            box = (bb["x"], bb["y"], bb["w"], bb["h"])
            real.append((cid, a["human_class"], box, rel(cid, box)))

for name, pop in (("REAL", real), ("FAKE", fake)):
    r = np.array([p[3] for p in pop])
    print(name, "n=", len(pop))
    for lo, hi in [(-99, -4), (-4, -2.5), (-2.5, -1), (-1, -0.01), (-0.01, 0.01),
                   (0.01, 1), (1, 2.5), (2.5, 4), (4, 99)]:
        print(f"  rel_centre in [{lo:5},{hi:5}): {int(np.sum((r >= lo) & (r < hi)))}")

for cls in ("tie", "slur"):
    ws = sorted(p[2][2] / band(p[0])[2] for p in real if p[1] == cls)
    q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))]
    print("REAL", cls, "n=", len(ws), "w_sp p5/p25/p50/p75/p95:",
          [round(q(ws, p), 2) for p in (.05, .25, .5, .75, .95)])
    hs = sorted(p[2][3] / band(p[0])[2] for p in real if p[1] == cls)
    print("REAL", cls, "h_sp p5/p25/p50/p75/p95:",
          [round(q(hs, p), 2) for p in (.05, .25, .5, .75, .95)])
