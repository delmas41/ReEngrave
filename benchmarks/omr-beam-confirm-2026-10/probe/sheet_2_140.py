"""Contact sheet for MY eyes (not Sean's): crops around the stem tip of chosen glyphs, a small red tick at the stem x on the left margin.
    python3 sheet_2_140.py lit|brah COUNT.json OUT.png g1,g2,..."""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
PDF = {"brah": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
       "lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
mov, cp, out, gl = sys.argv[1:5]
d = json.load(open(cp))
tiles, cache = [], {}
for g in gl.split(","):
    m = d[g]; p = int(g.split("/")[1])
    if p not in cache:
        cache = {p: Image.fromarray(render_page(PDF[mov], p, dpi=600).rgb).convert("RGB")}
    sp = m["sp"]; x = m["stem_x"]; y = m["tip_y"]
    box = (int(x - 4 * sp), int(y - 4 * sp), int(x + 4 * sp), int(y + 2 * sp))
    c = cache[p].crop(box).resize((450, 337))
    dr = ImageDraw.Draw(c)
    f = 450 / (box[2] - box[0])
    dr.line([((x - box[0]) * f, 0), ((x - box[0]) * f, 12)], fill=(255, 0, 0), width=2)
    for nm, col in (("left", (255, 0, 0)), ("right", (0, 160, 0))):
        xx = x + (-1 if nm == "left" else 1) * 0.45 * sp
        for a, b, _t in m["cols"][nm]:
            dr.line([((xx - box[0]) * f, (a - box[1]) * f), ((xx - box[0]) * f, (b - box[1]) * f)], fill=col, width=2)
    dr.text((3, 3), g.replace("glyph/", "") + " " + str(m["dur"][1:3] if m.get("dur") else ""), fill=(200, 0, 0))
    tiles.append(c)
cols = 3
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (450 * cols, 337 * rows), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * 450, (i // cols) * 337))
sheet.save(out)
