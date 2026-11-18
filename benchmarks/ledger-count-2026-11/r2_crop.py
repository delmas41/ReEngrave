"""ROADMAP 2.312 r2 -- look crops for the lane (not tiles): page ink as scanned at x8, the box in thin orange, tick marks at the left
edge for given rows (staff edge, rungs) so the lane can see what the reader saw.

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r2_crop.py PLATE PAGE "x0,y0,x1,y1" OUT.png [row,row,...]
"""
import sys

from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR

plate, page, box, out = sys.argv[1], int(sys.argv[2]), [float(v) for v in sys.argv[3].split(",")], sys.argv[4]
rows = [float(v) for v in sys.argv[5].split(",")] if len(sys.argv) > 5 and sys.argv[5] else []
pi = render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), page, dpi=600)
img = Image.fromarray(pi.rgb).convert("RGB")
cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
X0, Y0, X1, Y1 = int(cx - 45), int(cy - 75), int(cx + 45), int(cy + 75)
k = 8
c = img.crop((X0, Y0, X1, Y1)).resize(((X1 - X0) * k, (Y1 - Y0) * k), Image.NEAREST)
d = ImageDraw.Draw(c)
d.rectangle([(box[0] - X0) * k, (box[1] - Y0) * k, (box[2] - X0) * k, (box[3] - Y0) * k], outline=(255, 140, 0), width=1)
for r in rows:
    yy = (r - Y0) * k
    d.line([0, yy, 30, yy], fill=(0, 160, 255), width=3)
for y in range(Y0, Y1, 5):
    d.line([c.width - 12 if y % 10 else c.width - 24, (y - Y0) * k, c.width, (y - Y0) * k], fill=(200, 0, 0), width=1)
    if y % 10 == 0:
        d.text((c.width - 60, (y - Y0) * k - 5), str(y), fill=(200, 0, 0))
c.save(out)
