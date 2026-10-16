"""ROADMAP 2.151 diagnosis sheet (for the lane, not for Sean): crops round the heads `held_dots_heads_2_151.py` names,
a thin green box on the head only.  usage: diag_sheet_2_151.py HELD_DOTS.json KIND N OUT.png
KIND: as_head | wedge | stroke"""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
rows = json.load(open(sys.argv[1]))
KIND, N, OUT = sys.argv[2], int(sys.argv[3]), sys.argv[4]
want = {"as_head": None, "wedge": "abstained:wedge_without_a_head", "stroke": "abstained:on_a_stroke"}[KIND]
SP = 33.0
picks = []
for r in rows:
    heads = {h["glyph"]: h for h in r["heads"]}
    for d in r["dots"]:
        if KIND == "as_head" and d.get("as_head"):
            picks.append((heads[d["head"]]["bbox"], d["head"]))
        elif want and d.get("role") == want and d.get("bbox"):
            db = d["bbox"]
            cy = (db[1] + db[3]) / 2
            for h in r["heads"]:
                hb = h["bbox"]
                if hb and -0.1 <= (db[0] - hb[2]) / SP <= 1.5 and abs(cy - (hb[1] + hb[3]) / 2) / SP <= 0.8:
                    picks.append((hb, h["glyph"]))
                    break
seen, uniq = set(), []
for p in picks:
    if p[1] not in seen:
        seen.add(p[1]); uniq.append(p)
uniq = uniq[:N]
pages = {}
tiles = []
for hb, g in uniq:
    pg = int(g.split("/")[1])
    if pg not in pages:
        pages[pg] = np.asarray(Image.fromarray(render_page(PDF, pg, dpi=600).rgb).convert("RGB"))
    a = pages[pg]
    x0, y0 = int(hb[0] - 3 * SP), int(hb[1] - 3 * SP)
    x1, y1 = int(hb[2] + 4 * SP), int(hb[3] + 3 * SP)
    im = Image.fromarray(a[max(y0, 0):y1, max(x0, 0):x1].copy())
    dr = ImageDraw.Draw(im)
    dr.rectangle([hb[0] - x0 - 2, hb[1] - y0 - 2, hb[2] - x0 + 2, hb[3] - y0 + 2], outline=(0, 160, 0), width=2)
    dr.text((3, 3), g, fill=(200, 0, 0))
    tiles.append(im.resize((im.width, im.height)))
W = 4
cw = max(t.width for t in tiles); ch = max(t.height for t in tiles)
sheet = Image.new("RGB", (cw * W, ch * ((len(tiles) + W - 1) // W)), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % W) * cw, (i // W) * ch))
sheet.save(OUT)
print(len(tiles), "tiles ->", OUT)
