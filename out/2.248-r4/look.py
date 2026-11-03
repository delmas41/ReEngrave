"""Crop a page region big (for my own look) + print a row ink profile across the head's columns. args: plate page x0 y0 x1 y1 name"""
import sys
import numpy as np
from PIL import Image
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page

plate, pg = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1 = [float(v) for v in sys.argv[3:7]]
name = sys.argv[7]
im = render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600)
g = np.asarray(Image.fromarray(im.rgb).convert("L"))
u = LR.PLATES[plate]["unit"]
cx = (x0 + x1) / 2
X0, X1 = int(cx - 4 * u), int(cx + 4 * u)
Y0, Y1 = int(y0 - 6 * u), int(y1 + 6 * u)
crop = Image.fromarray(g[Y0:Y1, X0:X1]).convert("RGB")
from PIL import ImageDraw
ImageDraw.Draw(crop).rectangle([x0 - X0, y0 - Y0, x1 - X0, y1 - Y0], outline=(255, 120, 0), width=1)
crop = crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST)
crop.save("out/2.248-r4/look_%s.png" % name)
thr = 128
ha, hb = int(x0), int(x1)
la, lb = int(x0 - 0.6 * u), int(x1 + 0.6 * u)
print("unit", u, "box", x0, y0, x1, y1)
for y in range(int(y0 - 3 * u), int(y1 + 3 * u)):
    inside = (g[y, ha:hb] < thr).mean()
    left = (g[y, la:ha] < thr).mean()
    right = (g[y, hb:lb] < thr).mean()
    print(y, "in %.2f  left %.2f  right %.2f" % (inside, left, right), "#" * int(inside * 20), "<" if left > 0.6 else "", ">" if right > 0.6 else "")
