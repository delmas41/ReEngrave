"""My own look (not for Sean): crops around page boxes, tall enough for the staff, on one sheet.  args: plate out.png page:x0,y0,x1,y1 ..."""
import sys
import numpy as np
from PIL import Image, ImageDraw
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page

plate, out = sys.argv[1], sys.argv[2]
u = LR.PLATES[plate]["unit"]
cache = {}
tiles = []
for a in sys.argv[3:]:
    pg, b = a.split(":")
    pg = int(pg)
    b = [float(v) for v in b.split(",")]
    if pg not in cache:
        cache[pg] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    im = cache[pg]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    c = im.crop((int(cx - 3 * u), int(cy - 6 * u), int(cx + 3 * u), int(cy + 6 * u))).copy()
    ImageDraw.Draw(c).rectangle([b[0] - int(cx - 3 * u), b[1] - int(cy - 6 * u), b[2] - int(cx - 3 * u), b[3] - int(cy - 6 * u)],
                                outline=(255, 120, 0), width=1)
    tiles.append(c.resize((c.width * 2, c.height * 2)))
W = sum(t.width + 6 for t in tiles)
sheet = Image.new("RGB", (W, max(t.height for t in tiles) + 20), (255, 255, 255))
x = 0
d = ImageDraw.Draw(sheet)
for i, t in enumerate(tiles, 1):
    d.text((x + 4, 2), str(i), fill=(0, 0, 0))
    sheet.paste(t, (x, 18))
    x += t.width + 6
sheet.save(out)
