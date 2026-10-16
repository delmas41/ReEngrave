"""ROADMAP 2.142 -- MY OWN contact sheet (boxes drawn: RED = head box under test, BLUE = its twin box). NOT for Sean.
usage: sheet_2_142.py ROWS.json PDF OUT.png  SUBJECT[:TWIN] ..."""
import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
rows = json.load(open(sys.argv[1])); B = rows["boxes"]; V = rows["verdicts"]
pdf, out, items = sys.argv[2], sys.argv[3], sys.argv[4:]
pages = {}
W = 360; tiles = []
for i, it in enumerate(items):
    s, _, t = it.partition(":")
    pg = int(s.split("/")[1])
    if pg not in pages:
        pages = {pg: np.asarray(Image.fromarray(render_page(pdf, pg, dpi=600).rgb).convert("RGB"))}
    img = pages[pg]
    b = B[s][2]; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    x0, y0 = int(cx - 70), int(cy - 70)
    crop = Image.fromarray(img[max(y0, 0):y0 + 140, max(x0, 0):x0 + 140]).convert("RGB")
    d = ImageDraw.Draw(crop)
    def rect(bb, col):
        d.rectangle([bb[0] - max(x0, 0), bb[1] - max(y0, 0), bb[2] - max(x0, 0), bb[3] - max(y0, 0)], outline=col, width=1)
    rect(b, (230, 0, 0))
    if t: rect(B[t][2], (0, 80, 255))
    crop = crop.resize((W, W), Image.NEAREST)
    d = ImageDraw.Draw(crop)
    v = V.get(s, {})
    lab = "%d %s %s" % (i, s.replace("glyph/", ""), B[s][0][:14])
    d.text((3, 3), lab, fill=(200, 0, 0))
    nn = v.get("notehead_is_not_a_notehead")
    d.text((3, 16), "dur=%s nn=%s" % ((v.get("duration") or ["-", None])[1], nn and nn[2]), fill=(0, 0, 200))
    tiles.append(crop)
cols = 4; rws = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rws * W), "white")
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * W, (i // cols) * W))
sheet.save(out); print(out, len(tiles))
