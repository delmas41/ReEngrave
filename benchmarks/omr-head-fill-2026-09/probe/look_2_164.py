"""ROADMAP 2.164 -- a contact sheet (for the lane's own eye, NOT evidence, NOT blind) of named glyph boxes: blue = the head
box, orange = the arc box it sits on (when given). Captions: n, doc, glyph.
usage: look_2_164.py OUT.png DOC:GLYPH[:ARCGLYPH] ...   (boxes read from out/2.164/why_<doc>.json + ext_<doc>.json)"""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
BLUE, ORANGE = (31, 111, 235), (240, 130, 0)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
except OSError:
    font = ImageFont.load_default()
OUT = sys.argv[1]
boxes = {}
for doc in PDFS:
    try:
        ext = json.load(open("out/2.164/ext_%s.json" % doc))
    except OSError:
        continue
    for o in ext["observations"]:
        if o["quantity"] in ("glyph_box", "arc_box") and (o.get("detail") or {}).get("bbox_page_px"):
            boxes[(doc, o["subject"])] = o["detail"]["bbox_page_px"]
pages, tiles = {}, []
specs = []
for s_ in sys.argv[2:]:
    specs += open(s_[1:]).read().split() if s_.startswith("@") else [s_]
for n, spec in enumerate(specs, 1):
    parts = spec.split(":")
    doc, g = parts[0], parts[1]
    arc = parts[2] if len(parts) > 2 else None
    pg = int(g.split("/")[1])
    if (doc, pg) not in pages:
        pages[(doc, pg)] = np.asarray(Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB"))
    a = pages[(doc, pg)]
    b = boxes[(doc, g)]
    sp = 16.0 if doc == "litolff" else 32.0
    x0, y0 = int(max(b[0] - 7 * sp, 0)), int(max(b[1] - 5 * sp, 0))
    x1, y1 = int(min(b[2] + 7 * sp, a.shape[1])), int(min(b[3] + 5 * sp, a.shape[0]))
    s = 3 if doc == "litolff" else 1.5
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((int(crop.width * s), int(crop.height * s)), Image.LANCZOS)
    dr = ImageDraw.Draw(crop)
    if arc and (doc, arc) in boxes:
        ab = boxes[(doc, arc)]
        dr.rectangle([(ab[0] - x0) * s, (ab[1] - y0) * s, (ab[2] - x0) * s, (ab[3] - y0) * s], outline=ORANGE, width=3)
    dr.rectangle([(b[0] - x0) * s - 2, (b[1] - y0) * s - 2, (b[2] - x0) * s + 2, (b[3] - y0) * s + 2], outline=BLUE,
                 width=3)
    t = Image.new("RGB", (max(crop.width, 420), crop.height + 40), "white")
    t.paste(crop, (0, 40))
    ImageDraw.Draw(t).text((6, 6), "%d. %s %s" % (n, doc[:3], g[6:]), fill=(0, 0, 0), font=font)
    tiles.append(t)
COLS = min(5, len(tiles))
w = max(t.width for t in tiles)
h = max(t.height for t in tiles)
rows = (len(tiles) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * (w + 8), rows * (h + 8)), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % COLS) * (w + 8), (i // COLS) * (h + 8)))
sheet.save(OUT)
print(len(tiles), OUT)
