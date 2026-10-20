"""2.172 (d): a contact sheet of random new view boxes for MY look (ours, not blind, not evidence). Green frame = the view box; caption = class, view, median conf.
usage: c2_sheet.py lit|bra FAMILY N SEED OUT.png"""
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page   # noqa: E402

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate, fam, n, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
d = json.load(open(str(ROOT) + "/probe/2.172/data/compare_%s.json" % plate))["new"]
items = sorted(k for k, v in d.items() if v["fam"] == fam)
random.Random(seed).shuffle(items)
items = items[:n]
pages = {}
tiles = []
sp = 15.5 if plate == "lit" else 16.0
for k in items:
    v = d[k]
    pg = int(k.split("/")[1])
    if pg not in pages:
        pages[pg] = render_page(PDF[plate], pg, dpi=600).rgb
    img = pages[pg]
    x0, y0, x1, y1 = v["pg"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = int(5 * sp), int(4 * sp)
    X0, Y0 = int(max(0, cx - hw)), int(max(0, cy - hh))
    crop = img[Y0:int(cy + hh), X0:int(cx + hw)].copy()
    crop = cv2.resize(crop, (2 * hw * 2 // 2, 2 * hh * 2 // 2))
    cv2.rectangle(crop, (int(x0 - X0), int(y0 - Y0)), (int(x1 - X0), int(y1 - Y0)), (0, 160, 0), 1)
    canvas = np.full((crop.shape[0] + 18, crop.shape[1], 3), 255, np.uint8)
    canvas[18:, :crop.shape[1]] = crop[:, :canvas.shape[1]]
    cv2.putText(canvas, "%s %s %.2f" % (k[6:], v["cls"][:18], v["conf"]), (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    tiles.append(canvas)
cols = 3
H = max(t.shape[0] for t in tiles)
W = max(t.shape[1] for t in tiles)
rows = []
for i in range(0, len(tiles), cols):
    row = tiles[i:i + cols]
    row = [np.pad(t, ((0, H - t.shape[0]), (0, W - t.shape[1]), (0, 0)), constant_values=255) for t in row]
    while len(row) < cols:
        row.append(np.full((H, W, 3), 255, np.uint8))
    rows.append(np.concatenate(row, axis=1))
cv2.imwrite(out, cv2.cvtColor(np.concatenate(rows, axis=0), cv2.COLOR_RGB2BGR))
print("wrote", out, len(tiles))
