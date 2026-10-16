"""ROADMAP 2.150 -- a contact sheet of rest boxes (for the lane's own look; NOT a blind tile).
usage: sheet_2_150.py DOC ROWS.json OUT.png glyph [glyph ...]     DOC = brahms | litolff
Each cell: the print around the box (+-3 spaces across, +-4.5 down), the box drawn BLUE, an index number."""
import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {"brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
        "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
doc, rows_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
glyphs = sys.argv[4:]
d = json.load(open(rows_path))
pages = {}
tiles = []
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
except Exception:
    font = ImageFont.load_default()
for i, g in enumerate(glyphs):
    b = d["boxes"].get(g)
    if not b or not b[3]:
        continue
    p = int(g.split("/")[1])
    staff = "staff/" + "/".join(g.split("/")[1:4])
    sp = float((d["staff"].get(staff) or {}).get("space") or 30)
    if p not in pages:
        pages[p] = np.asarray(Image.fromarray(render_page(PDFS[doc], p, dpi=600).rgb).convert("RGB"))
    img = pages[p]
    x0, y0, x1, y1 = b[3]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    wx0, wx1 = int(cx - 3 * sp), int(cx + 3 * sp)
    lines = (d["staff"].get(staff) or {}).get("lines")
    if lines:
        wy0, wy1 = int(min(lines) - 3 * sp), int(max(lines) + 3 * sp)
    else:
        wy0, wy1 = int(cy - 5 * sp), int(cy + 5 * sp)
    crop = Image.fromarray(img[max(0, wy0):wy1, max(0, wx0):wx1].copy())
    dr = ImageDraw.Draw(crop)
    dr.rectangle([x0 - wx0 - 3, y0 - wy0 - 3, x1 - wx0 + 3, y1 - wy0 + 3], outline=(0, 70, 230), width=3)
    crop = crop.resize((240, int(crop.height * 240 / max(1, crop.width))))
    t = Image.new("RGB", (240, crop.height + 30), (255, 255, 255))
    ImageDraw.Draw(t).text((4, 2), str(i), fill=(200, 0, 0), font=font)
    t.paste(crop, (0, 30))
    tiles.append(t)
cols = 8
H = max(t.height for t in tiles)
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 245, rows * (H + 5)), (180, 180, 180))
for k, t in enumerate(tiles):
    sheet.paste(t, ((k % cols) * 245, (k // cols) * (H + 5)))
sheet.save(out)
print("sheet", out, len(tiles))
