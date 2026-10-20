"""2.167e probe 16: a contact sheet of crops (one BLUE box = the symbol) for my own look. usage: e16_sheet.py LIST.json OUT.png [cols]
LIST.json = [[plate, glyph subject, caption], ...]"""
import json
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
SP = {"lit": 16.0, "bra": 12.5}
BLUE = (31, 111, 235)
items = json.load(open(sys.argv[1]))
out = sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 3
here = "probe/2.167e/data/"
cache, docs = {}, {}
fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
import os
W, H = int(os.environ.get("TW", "520")), int(os.environ.get("TH", "300"))
tiles = []
for i, (plate, sub, cap) in enumerate(items, 1):
    if plate not in cache:
        cache[plate] = json.load(open(here + "%s_all.json" % plate))
        docs[plate] = fitz.open(PDF[plate])
    bb = cache[plate][sub]["bb"]
    page = int(sub.split("/")[1])
    sp = SP[plate]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    hw, hh = 8 * sp, 4.5 * sp
    r = (cx - hw, cy - hh, cx + hw, cy + hh)
    z = W / (2 * hw) * 600 / 72
    pix = docs[plate][page].get_pixmap(matrix=fitz.Matrix(z, z), clip=fitz.Rect(*[v * 72 / 600 for v in r]))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).resize((W, H))
    d = ImageDraw.Draw(im)
    f = W / (r[2] - r[0])
    d.rectangle([(bb[0] - r[0]) * f - 2, (bb[1] - r[1]) * f - 2, (bb[2] - r[0]) * f + 2, (bb[3] - r[1]) * f + 2], outline=BLUE, width=2)
    t = Image.new("RGB", (W, H + 18), "white")
    t.paste(im, (0, 18))
    ImageDraw.Draw(t).text((2, 2), "%d %s" % (i, cap[:70]), fill=(0, 0, 0), font=fnt)
    tiles.append(t)
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (W + 6), rows * (H + 24)), "white")
for k, t in enumerate(tiles):
    sheet.paste(t, ((k % cols) * (W + 6), (k // cols) * (H + 24)))
sheet.save(out)
print(sheet.size)
