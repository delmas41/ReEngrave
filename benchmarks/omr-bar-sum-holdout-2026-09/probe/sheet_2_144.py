"""ROADMAP 2.144 -- MY OWN contact sheet (RED = head box under test, BLUE = clef box / second box). NOT for Sean.
usage: sheet_2_144.py ROWS.json PDF OUT.png  SUBJECT[:OTHER[:OTHER2]] ...   (OTHER boxes drawn blue; crop 220 px square)"""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
rows = json.load(open(sys.argv[1])); B = rows["boxes"]; V = rows["verdicts"]
pdf, out, items = sys.argv[2], sys.argv[3], sys.argv[4:]
pages = {}; W = 330; H = 110; tiles = []
for i, it in enumerate(items):
    parts = it.split(":"); s = parts[0]
    pg = int(s.split("/")[1])
    if pg not in pages:
        pages = {pg: np.asarray(Image.fromarray(render_page(pdf, pg, dpi=600).rgb).convert("RGB"))}
    img = pages[pg]
    b = B[s][2]; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    x0, y0 = max(int(cx - H), 0), max(int(cy - H), 0)
    crop = Image.fromarray(img[y0:y0 + 2 * H, x0:x0 + 2 * H]).convert("RGB")
    d = ImageDraw.Draw(crop)
    def rect(bb, col): d.rectangle([bb[0] - x0, bb[1] - y0, bb[2] - x0, bb[3] - y0], outline=col, width=1)
    rect(b, (230, 0, 0))
    for t in parts[1:]: rect(B[t][2], (0, 80, 255))
    crop = crop.resize((W, W), Image.LANCZOS); d = ImageDraw.Draw(crop)
    v = V.get(s, {}); nn = v.get("notehead_is_not_a_notehead")
    d.text((3, 3), "%d %s %s" % (i, s.replace("glyph/", ""), B[s][0][:16]), fill=(200, 0, 0))
    d.text((3, 15), "dur=%s nn=%s" % ((v.get("duration") or ["-", None])[1], nn and nn[1:3]), fill=(0, 0, 200))
    tiles.append(crop)
cols = 4; rws = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rws * W), "white")
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * W, (i // cols) * W))
sheet.save(out); print(out, len(tiles))
