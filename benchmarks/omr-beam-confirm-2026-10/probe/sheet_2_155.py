"""ROADMAP 2.155 -- PROBE: a contact sheet (OURS drawn: rescued run red, the head(s) it ends in blue) of rescued stems from
reach_2_155.py's json, for the lane's own review -- NOT a blind tile. usage: sheet_2_155.py REACH.json DOC FILTER N SEED OUT.png
FILTER: all | had_stem | no_stem"""
import json
import random
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402

sys.path.insert(0, "benchmarks/omr-beam-confirm-2026-10/probe")
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
REACH, DOC, FILT, N, SEED, OUT = sys.argv[1:7]
R = json.load(open(REACH))["rescued"]
if FILT == "had_stem":
    R = [r for r in R if any(h and h.startswith("decided") for h in r["head_stem"])]
elif FILT == "no_stem":
    R = [r for r in R if all(h and h.startswith("abstained") for h in r["head_stem"])]
random.Random(int(SEED)).shuffle(R)
R = R[:int(N)]
pages, tiles = {}, []
for i, r in enumerate(R):
    pg = int(r["cell"].split("/")[1])
    if pg not in pages:
        pages[pg] = render_page(PDFS[DOC], pg, dpi=600).binary
    bb, up = r["page_bbox"], r["upscale"]
    x, y, w, h = r["stem"]
    sx0, sy0, sx1, sy1 = bb[0] + x / up, bb[1] + y / up, bb[0] + (x + w) / up, bb[1] + (y + h) / up
    m = 70
    X0, Y0 = int(sx0 - m), int(min(sy0, bb[1]) - 20)
    X1, Y1 = int(sx1 + m), int(max(sy1, bb[3]) + 20)
    im = Image.fromarray(pages[pg][max(0, Y0):Y1, max(0, X0):X1]).convert("RGB")
    d = ImageDraw.Draw(im)
    ox, oy = max(0, X0), max(0, Y0)
    d.rectangle((sx0 - ox - 2, sy0 - oy, sx1 - ox + 2, sy1 - oy), outline=(220, 0, 0))
    im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
    ImageDraw.Draw(im).text((4, 4), "%d %s %s" % (i + 1, r["join"], r["head_stem"]), fill=(0, 0, 255))
    tiles.append(im)
    print(i + 1, r["cell"], r["stem"], r["side"], r["join"], r["heads"], r["head_stem"])
W = sum(t.width for t in tiles[:6]) + 10 * 6
rows = [tiles[k:k + 6] for k in range(0, len(tiles), 6)]
H = sum(max(t.height for t in row) + 10 for row in rows)
sheet = Image.new("RGB", (max(W, 10), H), "white")
yy = 0
for row in rows:
    xx = 0
    for t in row:
        sheet.paste(t, (xx, yy))
        xx += t.width + 10
    yy += max(t.height for t in row) + 10
sheet.save(OUT)
