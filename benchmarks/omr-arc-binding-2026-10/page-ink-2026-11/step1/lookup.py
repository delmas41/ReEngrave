"""2.274 step 1: contact sheets for MY OWN look (not Sean's tiles; the curve is drawn, so they are not blind).

    python3 lookup.py PLATE PAGE WORKDIR KIND [--per 24]
KIND = missed   detector curves a run does not cover whole (orange = the detector curve's centre line, green = runs)
       new      runs no detector box witnesses (green = the run)
       seeded   boxes the seeded local read answered
Writes WORKDIR/PLATE-pPAGE.KIND.N.png and prints the id order (left to right, top to bottom).
"""
import json
import pathlib
import sys

import cv2
import numpy as np


def main():
    argv = sys.argv[1:]
    per = 18
    if "--per" in argv:
        i = argv.index("--per")
        per = int(argv[i + 1])
        del argv[i:i + 2]
    plate, page, wd, kind = argv[0], int(argv[1]), pathlib.Path(argv[2]), argv[3]
    stem = "%s-p%d" % (plate, page)
    J = json.load(open(wd / (stem + ".step1.json")))
    sp = J["summary"]["sp"]
    img = cv2.imread(str(wd / (stem + ".raw.png")), 0)
    H, W = img.shape
    items = []
    if kind == "missed":
        for k, c in enumerate(J["curves"]):
            if not c["refused"] and c["best"] < 0.8:
                items.append(dict(label="c%d %.2f/%.2f" % (k, c["best"], c["seeded_best"]), box=c["box"], curve=c))
    elif kind == "new":
        for r in J["runs"]:
            if not r["witnesses"]:
                items.append(dict(label="r%d" % r["id"], box=r["box"], run=r))
    elif kind == "seeded":
        for k, s in enumerate(J["seeded"]):
            items.append(dict(label="s%d" % k, box=s["run"]["box"], run=s["run"]))
    elif kind == "sample":
        import random
        rs = [r for r in J["runs"] if r["witnesses"]]
        random.Random(274).shuffle(rs)
        for r in rs[:20]:
            items.append(dict(label="w%d" % r["id"], box=r["box"], run=r))
    tiles = []
    for it in items:
        x0, y0, x1, y1 = it["box"]
        m = 2.0 * sp
        a, b, c, d = int(max(0, x0 - m)), int(max(0, y0 - m)), int(min(W, x1 + m)), int(min(H, y1 + m))
        crop = cv2.cvtColor(img[b:d, a:c], cv2.COLOR_GRAY2BGR)
        sc = min(3.0, 380.0 / max(1, (c - a)), 165.0 / max(1, (d - b)))
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
        ov = crop.copy()
        for r in J["runs"]:
            if r["box"][2] < a or r["box"][0] > c or r["box"][3] < b or r["box"][1] > d:
                continue
            P = (np.array(r["pts"]) - [a, b]) * sc
            cv2.polylines(ov, [P.astype(np.int32).reshape(-1, 1, 2)], False, (0, 160, 0), 1)
        if "curve" in it:
            bx0, by0, bx1, by1 = it["box"]
            cv2.rectangle(ov, (int((bx0 - a) * sc), int((by0 - b) * sc)), (int((bx1 - a) * sc), int((by1 - b) * sc)), (0, 140, 255), 1)
        cv2.putText(ov, it["label"], (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        tiles.append(ov)
    cols = 3
    for n in range(0, len(tiles), per):
        chunk = tiles[n:n + per]
        w = 390
        rows = []
        for i in range(0, len(chunk), cols):
            row = []
            for t in chunk[i:i + cols]:
                h = 170
                canvas = np.full((h, w, 3), 255, np.uint8)
                tt = t[:h, :w]
                canvas[:tt.shape[0], :tt.shape[1]] = tt
                row.append(canvas)
            while len(row) < cols:
                row.append(np.full((170, w, 3), 255, np.uint8))
            rows.append(np.hstack(row))
        sheet = np.vstack(rows)
        out = wd / ("%s.%s.%d.png" % (stem, kind, n // per))
        cv2.imwrite(str(out), sheet)
        print(out, [it["label"] for it in items[n:n + per]])


if __name__ == "__main__":
    main()
