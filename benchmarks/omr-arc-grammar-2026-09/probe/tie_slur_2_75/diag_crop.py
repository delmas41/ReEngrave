"""NOT BLIND. Diagnostic crop: the arc in a red bracket, the two heads the rule
read in green boxes, with the steps it read.
usage: diag_crop.py record.json rows.json out.png sub"""
import json
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

from tools.omr.staged import readout

rec, rows_p, out, sub = sys.argv[1:5]
run = readout.load_run(rec)
dpi = run.dpi or 600
r = {x["sub"]: x for x in json.load(open(rows_p))}[sub]
tn = r["rule"]["two_note"]
doc = fitz.open(run.pdf)
boxes = [tuple(r["box"])]
heads = []
for k in (tn.get("start"), tn.get("stop")):
    if k in run.glyphs:
        b = tuple(run.glyphs[k].box_page)
        heads.append(b)
        boxes.append(b)
x0 = min(b[0] for b in boxes) - 160
y0 = min(b[1] for b in boxes) - 120
x1 = max(b[2] for b in boxes) + 160
y1 = max(b[3] for b in boxes) + 120
page = int(sub.split("/")[1])
clip = fitz.Rect(x0 * 72 / dpi, y0 * 72 / dpi, x1 * 72 / dpi, y1 * 72 / dpi)
pix = doc[page].get_pixmap(dpi=dpi, clip=clip)
im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
ox, oy = clip.x0 * dpi / 72, clip.y0 * dpi / 72
d = ImageDraw.Draw(im)
for b in heads:
    d.rectangle([b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy], outline=(0, 150, 0), width=3)
a = (r["box"][0] - ox - 6, r["box"][1] - oy - 6, r["box"][2] - ox + 6, r["box"][3] - oy + 6)
for (px, py, sx, sy) in ((a[0], a[1], 1, 1), (a[2], a[1], -1, 1), (a[0], a[3], 1, -1), (a[2], a[3], -1, -1)):
    d.line([(px, py), (px + sx * 16, py)], fill=(220, 0, 0), width=4)
    d.line([(px, py), (px, py + sy * 16)], fill=(220, 0, 0), width=4)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
top = Image.new("RGB", (max(im.width, 700), 70), "white")
ImageDraw.Draw(top).text((6, 4), "%s  detector=%s ours=%s  side=%s  start_step=%s (%s) stop_step=%s (%s) rel=%s dy=%s" % (
    sub, r["det"], r["kind"], tn.get("arc_side"), tn.get("start_step"), tn.get("start_step_source"),
    tn.get("stop_step"), tn.get("stop_step_source"), tn.get("relation"), tn.get("dy_spaces")), fill="black", font=font)
ImageDraw.Draw(top).text((6, 36), "red = the arc; green = the two heads the rule paired", fill="black", font=font)
o = Image.new("RGB", (top.width, top.height + im.height), "white")
o.paste(top, (0, 0))
o.paste(im, (0, top.height))
o.save(out)
print(out)
