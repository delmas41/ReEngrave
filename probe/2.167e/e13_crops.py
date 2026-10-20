"""2.167e probe 13: page crops (nothing of ours drawn except ONE blue box on the symbol discussed) for my own look / for out/print/2.167e/.
usage: e13_crops.py OUTDIR plate:glyphsub[:caption] ...   (bbox read from ALL.json of the plate; margin MARGIN_SP spaces)"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
SP = {"lit": 16.0, "bra": 12.5}
ZOOM = {"lit": 2.2, "bra": 2.6}
BLUE = (31, 111, 235)
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__)) + "/data/"
cache = {}
docs = {}
try:
    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
except Exception:
    fnt = ImageFont.load_default()
margin_sp = float(os.environ.get("MARGIN_SP", "7"))
for i, a in enumerate(sys.argv[2:], 1):
    parts = a.split(":")
    plate, sub = parts[0], parts[1]
    cap = parts[2] if len(parts) > 2 else sub
    if plate not in cache:
        cache[plate] = json.load(open(here + "%s_all.json" % plate))
        docs[plate] = fitz.open(PDF[plate])
    bb = cache[plate][sub]["bb"]
    page = int(sub.split("/")[1])
    m = margin_sp * SP[plate]
    r = (bb[0] - 2 * m, bb[1] - m, bb[2] + 2 * m, bb[3] + m)
    z = ZOOM[plate]
    pix = docs[plate][page].get_pixmap(matrix=fitz.Matrix(600 / 72 * z, 600 / 72 * z), clip=fitz.Rect(*[v * 72 / 600 for v in r]))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    f = im.width / (r[2] - r[0])
    d = ImageDraw.Draw(im)
    d.rectangle([(bb[0] - r[0]) * f - 2, (bb[1] - r[1]) * f - 2, (bb[2] - r[0]) * f + 2, (bb[3] - r[1]) * f + 2], outline=BLUE, width=3)
    t = Image.new("RGB", (max(im.width, 640), im.height + 24), "white")
    t.paste(im, (0, 24))
    ImageDraw.Draw(t).text((4, 4), "%d  %s" % (i, cap), fill=(0, 0, 0), font=fnt)
    t.save(os.path.join(out, "crop_%02d.png" % i))
    print(i, sub, bb)
