"""2.167d probe 8: list every NEW notehead/rest/flag/dot box >= 0.25 a re-cut variant adds inside the 45 sampled bars (not matching any base >= 0.25 box
of the same family), and render a contact sheet of them for MY OWN judgement (real symbol or not: ours, not evidence).
Tile: page crop around the box (2.5 sp margin, grey frame = the bar crop the detector was given), BLUE box = the new box.
usage: d8_newboxes.py VARIANT lit|bra  -> sheets/new_<variant>_<plate>_K.png and data/new_<variant>_<plate>.json"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/"
var, plate = sys.argv[1], sys.argv[2]
PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
FAM = ("notehead", "rest", "flag", "augmentationDot")


def fam(c):
    for f in FAM:
        if c.startswith(f):
            return f
    if c[:3] in ("F8t", "F16", "F32"):
        return "flag"
    if c == "dot":
        return "augmentationDot"
    return "other"


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


rr = json.load(open(D + "data/%s_rerun.json" % plate))
sample = json.load(open(D + "data/%s_sample.json" % plate))
new = []
for idx, (p, s, st, c) in enumerate(sample):
    key = "%d/%d/%d/%d" % (p, s, st, c)
    R = rr[key]
    sp = R["spacing"]
    x0, y0, x1, y1 = R["cell"]
    top, bot = R["lines"][0], R["lines"][4]
    base = [b for b in R["variants"]["base"]["boxes"] if b[1] >= 0.25]
    low = [b for b in R["variants"]["base"]["boxes"] if 0.05 <= b[1] < 0.25]
    for b in R["variants"][var]["boxes"]:
        if b[1] < 0.25 or fam(b[0]) == "other":
            continue
        cx, cy = (b[2] + b[4]) / 2, (b[3] + b[5]) / 2
        if not (x0 <= cx <= x1 and top - 3 * sp <= cy <= bot + 3 * sp):
            continue
        if any(fam(a[0]) == fam(b[0]) and iou(a[2:6], b[2:6]) > 0.4 for a in base):
            continue
        near_low = any(fam(a[0]) == fam(b[0]) and iou(a[2:6], b[2:6]) > 0.3 for a in low)
        new.append(dict(bar=idx, key=key, cls=b[0], conf=b[1], bbox=b[2:6], cell=R["cell"], sp=sp, top=top, near_low_box=near_low))
json.dump(new, open(D + "data/new_%s_%s.json" % (var, plate), "w"))
print(var, plate, "new boxes", len(new), "of which a sub-floor box (0.05-0.25) already sat there:", sum(n["near_low_box"] for n in new))
doc = fitz.open(PDF[plate])
try:
    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
except Exception:
    fnt = ImageFont.load_default()
tiles = []
for k, n in enumerate(new):
    sp = n["sp"]
    x0, y0, x1, y1 = n["cell"]
    b = n["bbox"]
    r = (b[0] - 3.5 * sp, n["top"] - 3 * sp, b[2] + 3.5 * sp, n["top"] + 7 * sp)
    p = int(n["key"].split("/")[0])
    z = 2.0 if plate == "lit" else 1.2
    pix = doc[p].get_pixmap(matrix=fitz.Matrix(600 / 72 * z, 600 / 72 * z), clip=fitz.Rect(*[v * 72 / 600 for v in r]))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    f = im.width / (r[2] - r[0])
    d = ImageDraw.Draw(im)
    d.rectangle([(x0 - r[0]) * f, (y0 - r[1]) * f, (x1 - r[0]) * f, (y1 - r[1]) * f], outline=(130, 130, 130))
    d.rectangle([(b[0] - r[0]) * f, (b[1] - r[1]) * f, (b[2] - r[0]) * f, (b[3] - r[1]) * f], outline=(31, 111, 235), width=2)
    t = Image.new("RGB", (im.width, im.height + 16), "white")
    t.paste(im, (0, 16))
    ImageDraw.Draw(t).text((2, 1), "%d bar#%d %s %.2f%s" % (k, n["bar"], n["cls"][:16], n["conf"], " (was low box)" if n["near_low_box"] else ""), fill=(0, 0, 0), font=fnt)
    tiles.append(t)
per = 8
for s0 in range(0, len(tiles), per):
    ch = tiles[s0:s0 + per]
    W = max(t.width for t in ch) * 2 + 6
    rows = (len(ch) + 1) // 2
    Hs = []
    for i in range(rows):
        Hs.append(max(t.height for t in ch[2 * i:2 * i + 2]))
    sheet = Image.new("RGB", (W, sum(Hs) + 6 * rows), (235, 235, 235))
    y = 0
    for i in range(rows):
        for j, t in enumerate(ch[2 * i:2 * i + 2]):
            sheet.paste(t, (j * (W // 2 + 3), y))
        y += Hs[i] + 6
    sheet.save(D + "sheets/new_%s_%s_%d.png" % (var, plate, s0 // per))
print("sheets", (len(tiles) + per - 1) // per)
