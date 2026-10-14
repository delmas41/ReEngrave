"""Closest calls of `interior_variants.json`: per page, the 4 lowest-reading BLACK heads and the 4 highest-reading HOLLOW heads under variant (c)
(line rows left out, re-centred). usage: interior_crops.py interior_variants.json OUT_DIR"""
import json, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-second-detector-2026-10")
import interior_variants as V
d = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
imgs = {"brahms": V.raster(V.BRA, 0), "litolff": V.raster(V.LIT, 1)}
SP = {"brahms": 0, "litolff": 15.75}
rows = []
for pg in ("brahms", "litolff"):
    its = [i for i in d["items"] if i["page"] == pg and i["c"] is not None]
    bl = sorted([i for i in its if i["label"] == "black"], key=lambda i: i["c"])[:4]
    ho = sorted([i for i in its if i["label"] == "hollow"], key=lambda i: -i["c"])[:4]
    for lab, grp in (("black", bl), ("hollow", ho)):
        for i in grp:
            img = imgs[pg]; x0, y0, x1, y1 = i["box"]; sp = 15.75 if pg == "litolff" else (x1 - x0) / 1.4
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; hw, hh = 2.2 * sp, 2.2 * sp
            ax0, ay0, ax1, ay1 = int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh)
            crop = cv2.cvtColor(img[ay0:ay1, ax0:ax1], cv2.COLOR_GRAY2BGR)
            Z = 192.0 / crop.shape[1]; crop = cv2.resize(crop, None, fx=Z, fy=Z, interpolation=cv2.INTER_NEAREST)
            T = lambda x, y: (int((x - ax0) * Z), int((y - ay0) * Z))
            bx = i["bbox"]
            if bx:
                cv2.rectangle(crop, T(bx[0], bx[1]), T(bx[0] + bx[2], bx[1] + bx[3]), (0, 170, 0), 1)
                dx, dy = int(round(.3 * bx[2])), int(round(.3 * bx[3]))
                cv2.rectangle(crop, T(bx[0] + dx, bx[1] + dy), T(bx[0] + bx[2] - dx, bx[1] + bx[3] - dy), (200, 0, 200), 1)
            tag = np.full((22, crop.shape[1], 3), 255, np.uint8)
            cv2.putText(tag, f"{pg[:3]} {lab} a{i['a']} b{i['b']} c{i['c']}", (2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            rows.append((pg, lab, np.vstack([tag, crop])))
for pg in ("brahms", "litolff"):
    for lab in ("black", "hollow"):
        tiles = [r[2] for r in rows if r[0] == pg and r[1] == lab]
        if tiles:
            h = max(t.shape[0] for t in tiles); tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
            cv2.imwrite(str(out / f"interior-{pg}-{lab}-closest.png"), np.hstack(tiles))
print("ok")
