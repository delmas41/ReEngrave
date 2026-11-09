"""2.280 probe 4: MY LOOK (ours, not evidence). Contact sheet of the heads in one cause bucket: page raster crop (head +-6 sp wide, +-5.5 sp tall),
thin blue box on the detector head box, label = index. usage: p4_sheet.py plate RERUN.json BUCKETS.json "cause prefix" OUT.png [N=12] [stratum=A]"""
import json
import random
import sys
import fitz
from PIL import Image, ImageDraw

plate, rr, bk, prefix, out = sys.argv[1:6]
N = int(sys.argv[6]) if len(sys.argv) > 6 else 12
STRAT = sys.argv[7] if len(sys.argv) > 7 else "A"
PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
pdf, SP = PDFS[plate]
doc = fitz.open(pdf)
R = json.load(open(rr))
B = json.load(open(bk))
subs = [s for s, b in B.items() if b["stratum"] == STRAT and b["cause"].startswith(prefix)]
import os
OFF = os.environ.get("OFFSET")
if OFF is None:
    random.Random(280).shuffle(subs)
    subs = subs[:N]
else:
    subs = sorted(subs)[int(OFF):int(OFF) + N]
tiles = []
for i, s in enumerate(subs):
    r = R[s]
    x0, y0, x1, y1 = r["page_box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    HW, HH = 6.0 * SP, 5.5 * SP
    clip = (cx - HW, cy - HH, cx + HW, cy + HH)
    Z = 330 / (2 * HW)
    k = 72 / 600
    pix = doc[r["page"]].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * k for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx = im.width / (2 * HW)
    sy = im.height / (2 * HH)
    ImageDraw.Draw(im).rectangle([(x0 - clip[0]) * sx, (y0 - clip[1]) * sy, (x1 - clip[0]) * sx, (y1 - clip[1]) * sy], outline=(31, 111, 235), width=1)
    ImageDraw.Draw(im).text((3, 3), "%d %s p%d" % (i, s.split("/", 2)[2], r["page"]), fill=(200, 0, 0))
    tiles.append(im)
cols = 4
w, h = tiles[0].size
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(len(tiles), out, [s for s in subs])
