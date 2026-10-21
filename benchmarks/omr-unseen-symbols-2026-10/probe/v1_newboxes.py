"""ROADMAP 2.179 -- a contact sheet of every new stem-end head box (e1_export.py's .new_glyphs.json) for MY look (ours, not evidence).
usage: python3 .../v1_newboxes.py PDF NEW_GLYPHS.json OUTDIR TAG
Each tile: +-3 staff spaces around the box, the box in blue, label = index, placed (W = written) or not (-), detector class read from,
score. Writes OUTDIR/TAG_newNN.png sheets of 30 tiles."""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

pdf, path, outdir, tag = sys.argv[1:5]
os.makedirs(outdir, exist_ok=True)
fates = json.load(open(path))
pages = {}
tiles = []
for i, f in enumerate(fates):
    p = int(f["glyph"].split("/")[1])
    if p not in pages:
        pages[p] = cv2.cvtColor(render_page(pdf, p).rgb, cv2.COLOR_RGB2BGR)
    img = pages[p]
    b = f["detail"]["bbox_page_px"]
    sp = max(b[3] - b[1], 8) * 1.1
    X0, Y0 = int(max(0, b[0] - 3 * sp)), int(max(0, b[1] - 3 * sp))
    X1, Y1 = int(min(img.shape[1], b[2] + 3 * sp)), int(min(img.shape[0], b[3] + 3 * sp))
    crop = img[Y0:Y1, X0:X1].copy()
    k = 220.0 / max(crop.shape[0], 1)
    crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    cv2.rectangle(crop, (int((b[0] - X0) * k) - 2, int((b[1] - Y0) * k) - 2), (int((b[2] - X0) * k) + 2, int((b[3] - Y0) * k) + 2),
                  (235, 110, 30), 2)
    lab = "%d %s %s %.2f" % (i, "W" if f["placed"] else "-", f["detail"]["read_from"].replace("notehead", "h")[:9], f["score"])
    t = np.full((240, max(crop.shape[1], 200), 3), 255, np.uint8)
    t[20:20 + crop.shape[0], :crop.shape[1]] = crop
    cv2.putText(t, lab, (2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    tiles.append(t)
W = 1800
for s in range(0, len(tiles), 30):
    rows, row = [], []
    for t in tiles[s:s + 30]:
        if sum(x.shape[1] for x in row) + t.shape[1] > W:
            rows.append(np.hstack(row + [np.full((240, W - sum(x.shape[1] for x in row), 3), 255, np.uint8)]))
            row = []
        row.append(t)
    if row:
        rows.append(np.hstack(row + [np.full((240, W - sum(x.shape[1] for x in row), 3), 255, np.uint8)]))
    cv2.imwrite(os.path.join(outdir, "%s_new%02d.png" % (tag, s // 30)), np.vstack(rows))
print(len(tiles), "tiles")
