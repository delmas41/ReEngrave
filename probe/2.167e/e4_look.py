"""2.167e probe 4: my own look. Page raster around a bar with every detector box drawn and numbered (class, conf). NOT for Sean.
usage: e4_look.py CELLS.json CELLKEY plate(lit|bra) OUT.png [minconf]"""
import json
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
cells, key, plate, out = sys.argv[1:5]
d = json.load(open(cells))[key]
p = int(key.split("/")[0])
cell = [o for o in d["obs"] if o["subject"].startswith("cell/") and o["quantity"] == "cell_box"][0]["value"]
boxes = {}
for o in d["obs"]:
    if o["quantity"] == "glyph_box":
        boxes[o["subject"]] = dict(cls=o["value"][0], bb=o["detail"]["bbox_page_px"])
    if o["quantity"] == "glyph_conf":
        boxes.setdefault(o["subject"], {})["conf"] = o["value"]
sp = [o for o in d["obs"] if o["quantity"] == "cell_staff_space"][0]["value"]
spg = 16.0
x0, y0, x1, y1 = cell
r = (x0 - 30, y0 - 30, x1 + 30, y1 + 30)
doc = fitz.open(PDF[plate])
z = 2.0 if plate == "lit" else 1.6
pix = doc[p].get_pixmap(matrix=fitz.Matrix(600 / 72 * z, 600 / 72 * z), clip=fitz.Rect(*[v * 72 / 600 for v in r]))
im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
f = im.width / (r[2] - r[0])
dr = ImageDraw.Draw(im)
fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11)
minc = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
for sub, b in boxes.items():
    if "bb" not in b or b.get("conf", 0) < minc:
        continue
    bb = b["bb"]
    col = (220, 0, 0) if b["cls"].startswith("rest") else (0, 120, 0) if b["cls"].startswith("notehead") else (200, 100, 0) if b["cls"].startswith(("flag", "augm", "dot")) else (120, 120, 120)
    dr.rectangle([(bb[0] - r[0]) * f, (bb[1] - r[1]) * f, (bb[2] - r[0]) * f, (bb[3] - r[1]) * f], outline=col, width=1)
    dr.text(((bb[0] - r[0]) * f, (bb[1] - r[1]) * f - 11), "%s %s %.2f" % (sub.split("/")[-1], b["cls"][:14], b.get("conf", 0)), fill=col, font=fnt)
im.save(out)
print(im.size, "cell", cell)
