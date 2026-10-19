"""2.169 my-eye contact sheet (ours drawn, NOT a tile, NOT evidence): N random strokes the NEW arm adds, red box = the added stroke.
usage: sheet_2_169.py DOC REACH.json OUT.png [N=12] [SEED=1]"""
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
import json  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
DOC, REACH, OUT = sys.argv[1:4]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 12
SEED = int(sys.argv[5]) if len(sys.argv) > 5 else 1
d = json.load(open(REACH))
adds = [a for a in d["added"] if a["arm"] == "NEW"]
random.Random(SEED).shuffle(adds)
pages, tiles = {}, []
for a in adds[:N]:
    pg = int(a["cell"].split("/")[1])
    if pg not in pages:
        pages[pg] = np.asarray(Image.fromarray(render_page(PDFS[DOC], pg, dpi=600).rgb).convert("RGB"))
    img = pages[pg]
    bb, up = a["page_bbox"], a["upscale"]
    x, y, w, h = a["stem"]
    px0, py0, px1, py1 = bb[0] + x / up, bb[1] + y / up, bb[0] + (x + w) / up, bb[1] + (y + h) / up
    cx0, cy0 = int(max(px0 - 150, 0)), int(max(py0 - 60, 0))
    cx1, cy1 = int(min(px1 + 150, img.shape[1])), int(min(py1 + 60, img.shape[0]))
    t = Image.fromarray(img[cy0:cy1, cx0:cx1].copy())
    ImageDraw.Draw(t).rectangle([px0 - cx0 - 2, py0 - cy0 - 2, px1 - cx0 + 2, py1 - cy0 + 2], outline=(255, 0, 0), width=1)
    tiles.append(t)
W = max(t.width for t in tiles)
cols = 3
rows = (len(tiles) + cols - 1) // cols
H = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * (W + 6), rows * (H + 6)), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * (W + 6), (i // cols) * (H + 6)))
sheet.save(OUT)
print("wrote", OUT, len(tiles))
