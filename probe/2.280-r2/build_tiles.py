"""2.280 r2: 8 blind tiles for Sean. One staff-height window, ONE thin ORANGE box on the head, nothing else drawn.
Question: "Does this head have a stem, and which way does it go?"  Picks fixed by subject (the micro test's own heads), order seeded.
usage: build_tiles.py OUTDIR   (reads out/2.280-r2/f1/proto_*.json for page_box / sp)"""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
R = {}
for p in PDFS:
    for s, r in json.load(open("out/2.280-r2/f1/proto_%s.json" % p))["results"].items():
        r["plate"] = p
        R[p + ":" + s] = r
PICKS = [("brahms:glyph/5/0/12/7/26", "micro false stem (a sharp boxed as a head), 2.277 does not refuse it"),
         ("brahms:glyph/14/1/2/4/9", "micro false stem (a sharp boxed as a head)"),
         ("brahms:glyph/14/1/3/4/10", "micro false stem (a sharp boxed as a head)"),
         ("brahms:glyph/14/1/1/0/7", "real head of a second, arm B abstained"),
         ("brahms:glyph/14/0/2/0/32", "real head of a second, arm B abstained"),
         ("litolff:glyph/1/0/7/11/3", "real head, arm B abstained: ruler_none"),
         ("brahms:glyph/0/0/0/5/4", "control: real head, single stem, arm B filed"),
         ("litolff:glyph/16/0/9/16/1", "control: real head, single stem, arm B filed")]
rng = random.Random(2802)
order = list(range(len(PICKS)))
rng.shuffle(order)
docs, key = {}, {}
ORANGE = (255, 110, 0)
for n, i in enumerate(order, 1):
    k, why = PICKS[i]
    r = R[k]
    SP = r["sp"]
    doc = docs.setdefault(r["plate"], fitz.open(PDFS[r["plate"]]))
    x0, y0, x1, y1 = r["page_box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    HW, HH = 10.0, 7.0
    clip = (cx - HW * SP, cy - HH * SP, cx + HW * SP, cy + HH * SP)
    Z = 900 / (2 * HW * SP)
    pix = doc[r["page"]].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
    ImageDraw.Draw(im).rectangle([(x0 - clip[0]) * sx, (y0 - clip[1]) * sy, (x1 - clip[0]) * sx, (y1 - clip[1]) * sy], outline=ORANGE, width=1)
    fn = "tile_%02d.png" % n
    im.save(os.path.join(OUT, fn))
    key[str(n)] = dict(file=fn, subject=k, page=r["page"], why_picked=why, my_label=r["label"], armB=r["B"], head_page_box=r["page_box"], sp=SP)
json.dump(key, open(os.path.join(OUT, "key.json"), "w"), indent=1)
open(os.path.join(OUT, "README.md"), "w").write(
    "# 2.280 r2 blind tiles\n\nOne staff, one thin ORANGE box on a head, nothing else drawn. Question for each: **Does this head have a stem, and which way does it go?** "
    "(or: is the boxed ink not a head at all). What the prototype said and why each was picked: key.json only.\n")
print("tiles ->", OUT)
