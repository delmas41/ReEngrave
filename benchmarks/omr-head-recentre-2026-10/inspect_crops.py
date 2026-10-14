"""2.115 manager-side check (NOT Sean's tiles): crops of every re-centred head on the truth pages, drawn box = orange (as detected), green = the standard head box at the
re-centred position. usage: inspect_crops.py truth_rows.json OUT.png"""
import json, sys
import numpy as np, cv2
sys.path.insert(0, "."); sys.path.insert(0, "benchmarks/omr-head-recentre-2026-10")
import explore as X
from tools.omr.staged import gather as G
rows = [r for r in json.load(open(sys.argv[1])) if r["moved"] and (r["page"] == "litolff" or r["label"] == "hollow")]
rast = {"brahms": X.raster(X.BRA, 0), "litolff": X.raster(X.LIT, 1)}
Z = 6; tiles = []
for r in rows:
    raw = rast[r["page"]]; x0, y0, x1, y1 = r["box"]; sp = 15.75 if r["page"] == "litolff" else None
    sp = sp or 15.9
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = int(2.2 * sp); ox, oy = int(cx - R), int(cy - R)
    crop = cv2.cvtColor(raw[oy:oy + 2 * R, ox:ox + 2 * R], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=Z, fy=Z, interpolation=cv2.INTER_NEAREST)
    T = lambda x, y: (int((x - ox) * Z), int((y - oy) * Z))
    cv2.rectangle(crop, T(x0, y0), T(x1, y1), (0, 140, 255), 2)
    bx0, bx1, by0, by1 = G._standard_head_box(cx, cy + r["dy"] * sp, sp)
    cv2.rectangle(crop, T(bx0, by0), T(bx1, by1), (0, 170, 0), 2)
    cv2.putText(crop, f'{r["page"][:3]} {r["label"][:4]} {r["key"][6:]} {r["before"][1]}->{r["after"][1]}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 0, 0), 1)
    tiles.append(crop)
cols = 4
h, w = tiles[0].shape[:2]
sheet = np.full(((len(tiles) + cols - 1) // cols * h, cols * w, 3), 255, np.uint8)
for i, t in enumerate(tiles):
    sheet[(i // cols) * h:(i // cols + 1) * h, (i % cols) * w:(i % cols + 1) * w] = t
cv2.imwrite(sys.argv[2], sheet); print(len(tiles), sheet.shape)
