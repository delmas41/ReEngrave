"""2.306 strings-mixed (OMR_STRING_STOPS_OWN_VALUE): the control sheet -- one staff per tile, a thin red box on the chord's heads, nothing
else drawn; the key (outside the tile folder) holds what the written file writes for each head.

Usage: strings_mixed_sheet.py OUTDIR KEY.json SPEC.json
SPEC.json: [{"label", "pdf", "page", "dpi", "staff_box": [x0,y0,x1,y1] page px, "heads": [[x0,y0,x1,y1] page px ...], "written": [...]}]"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw

outd, keyp, specp = sys.argv[1], sys.argv[2], sys.argv[3]
spec = json.load(open(specp))
os.makedirs(os.path.join(outd, "tiles"), exist_ok=True)
tiles, key = [], []
for n, s in enumerate(spec, 1):
    doc = fitz.open(s["pdf"])
    pix = doc[s["page"]].get_pixmap(dpi=s["dpi"], colorspace=fitz.csGRAY)
    im = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
    hx0 = min(h[0] for h in s["heads"]); hy0 = min(h[1] for h in s["heads"])
    hx1 = max(h[2] for h in s["heads"]); hy1 = max(h[3] for h in s["heads"])
    sx0, sy0, sx1, sy1 = s["staff_box"]
    X0, X1 = int(max(0, hx0 - s.get("pad_x", 600))), int(min(im.width, hx1 + s.get("pad_x", 600)))
    Y0, Y1 = int(max(0, min(sy0, hy0) - 20)), int(min(im.height, max(sy1, hy1) + 20))
    t = im.crop((X0, Y0, X1, Y1))
    ImageDraw.Draw(t).rectangle([hx0 - X0 - 6, hy0 - Y0 - 6, hx1 - X0 + 6, hy1 - Y0 + 6], outline=(230, 0, 0), width=3)
    t = t.resize((t.width // 2, t.height // 2), Image.LANCZOS)
    t.save(os.path.join(outd, "tiles", "tile%02d.png" % n))
    tiles.append(t)
    key.append(dict(tile=n, label=s["label"], written=s["written"]))
W = max(t.width for t in tiles); H = sum(t.height + 34 for t in tiles)
sheet = Image.new("RGB", (W + 20, H + 10), "white")
d = ImageDraw.Draw(sheet)
y = 6
for i, t in enumerate(tiles):
    d.text((8, y), "tile %d" % (i + 1), fill=(0, 0, 0))
    sheet.paste(t, (10, y + 22))
    y += t.height + 34
sheet.save(os.path.join(outd, "sheet.png"))
json.dump(key, open(keyp, "w"), indent=1)
print(len(tiles), "tiles")
