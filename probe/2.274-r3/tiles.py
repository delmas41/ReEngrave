"""2.274 r3: 12 blind crops for Sean, one printed arc each, nothing of ours drawn but ONE thin box on his own hand box (the printed arc as he labeled it).
Question for every crop: "Is the boxed mark one arc, and which two notes does it join?"
The crop shows the whole staff-height band the arc sits in and runs far enough left and right that BOTH ends of the printed arc (even past his box) are in view.
    python3 tiles.py   -> out/print/2.274-r3-diag/NN.png + key.json (the key is ours: which P, which bucket, what our look says; never shown with the tile)
"""
import json
import pathlib
import random
import cv2
import numpy as np
from load import *   # noqa
import page as PG

C = json.load(open("buckets.json"))
P, HEADS = printed()
OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "print" / "2.274-r3-diag"
OUT.mkdir(parents=True, exist_ok=True)
PICK = [(41, "7 ghost"), (20, "7 half label"), (27, "7 chain"), (35, "7 cross-system"),
        (88, "5 abstained"), (73, "5 abstained"), (94, "5 abstained"), (71, "5 abstained"),
        (100, "3 nested/merged run"), (53, "3 merged run"), (79, "6 bound right, not in file"), (4, "8 head not written")]
random.Random(2751).shuffle(PICK)          # seed 2751: the order Sean sees them in
img = PG.page()
rec = record("on")
runs = {o["detail"]["ordinal"]: o["detail"] for o in rec["observations"] if o["quantity"] == "page_arc" and o["value"] == "run"}
key = []
for k, (n, label) in enumerate(PICK, 1):
    c, p = C[n], P[n]
    x0, x1 = p["x0"], p["x1"]
    ex0, ex1 = x0, x1
    for r in c["runs"][:2]:                      # let the crop reach where the ink of the arc really ends (past his box when the box is one cell's half)
        ex0, ex1 = min(ex0, r["run_x0"]), max(ex1, r["run_x1"])
    ex0, ex1 = max(ex0, x0 - 22 * SP), min(ex1, x1 + 22 * SP)
    heads = [h for h in HEADS if ex0 - 2 * SP <= (h["rect"][0] + h["rect"][2]) / 2 <= ex1 + 2 * SP and abs((h["rect"][1] + h["rect"][3]) / 2 - (p["box"][1] + p["box"][3]) / 2) <= 4.5 * SP]
    ys = [p["box"][1], p["box"][3]] + [h["rect"][1] for h in heads] + [h["rect"][3] for h in heads]
    y0, y1 = min(ys) - 2.5 * SP, max(ys) + 2.5 * SP
    X0, X1, Y0, Y1 = int(ex0 - 2.5 * SP), int(ex1 + 2.5 * SP), int(y0), int(y1)
    im = cv2.cvtColor(img[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
    for r in p["rects"]:                          # his own boxes, thin
        cv2.rectangle(im, (int(r[0] - X0), int(r[1] - Y0)), (int(r[2] - X0), int(r[3] - Y0)), (0, 140, 255), 2)
    s = min(0.7, 1400.0 / im.shape[1])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    name = "%02d.png" % k
    cv2.imwrite(str(OUT / name), im)
    key.append(dict(tile=name, printed_arc=n, staff_label=p["staff"], hand_ids=p["ids"], hand_kind=p["kind"], bucket_on=c["bucket_on"], bucket_off=c["bucket_off"], why_on=c["why_on"], what_it_tests=label,
                    crop_page_px=[X0, Y0, X1, Y1], scale=round(s, 3)))
    print(name, n, label, im.shape)
json.dump(dict(question="Is the boxed mark one arc, and which two notes does it join?", seed=2751, drawn="one thin orange box per hand box of the printed arc, nothing else", tiles=key), open(OUT / "key.json", "w"), indent=1)
