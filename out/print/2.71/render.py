"""ROADMAP 2.71 -- BLIND crops of the boxes the tremolo-slash reader changed, one tile each.

Each tile is the printed page at 600 dpi (the gather's own DPI), x2, red corner brackets on the subject box and
NOTHING else drawn (rule: crops of ours show the print, not our reading). `manifest.json` holds what the tree read
before and after; it is NOT shown to the judge.

Usage (from the repo root): python3 out/print/2.71/render.py <items.json>
`items.json`: [{"pdf": "<path>", "page": <pdf page index>, "box": [x0, y0, x1, y1], "subject": "...",
                "base": "...", "arm": "..."}, ...]
"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DPI, Z = 600, 2
W, H = 260, 190

items = json.load(open(sys.argv[1]))
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
man = []
docs = {}
for n, it in enumerate(items, 1):
    doc = docs.setdefault(it["pdf"], fitz.open(it["pdf"]))
    x0, y0, x1, y1 = it["box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    clip = fitz.Rect((cx - W) * 72 / DPI, (cy - H) * 72 / DPI, (cx + W) * 72 / DPI, (cy + H) * 72 / DPI)
    pix = doc[it["page"]].get_pixmap(dpi=DPI * Z, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ox, oy = clip.x0 * DPI / 72, clip.y0 * DPI / 72
    a, b, c, e = ((x0 - ox) * Z - 10, (y0 - oy) * Z - 10, (x1 - ox) * Z + 10, (y1 - oy) * Z + 10)
    d = ImageDraw.Draw(im)
    for (px, py, sx, sy) in ((a, b, 1, 1), (c, b, -1, 1), (a, e, 1, -1), (c, e, -1, -1)):
        d.line([(px, py), (px + sx * 18, py)], fill=(220, 0, 0), width=5)
        d.line([(px, py), (px, py + sy * 18)], fill=(220, 0, 0), width=5)
    out = Image.new("RGB", (im.width, im.height + 60), "white")
    out.paste(im, (0, 60))
    ImageDraw.Draw(out).text((10, 12), f"Tile {n} of {len(items)} -- {it.get('title', '')}", fill="black", font=font)
    f = f"tile_{n:02d}.png"
    out.save(os.path.join(HERE, f))
    man.append({"n": n, "file": f, "pdf_page_index": it["page"], "page_box_600dpi": it["box"],
                "subject": it["subject"], "question": it.get("question"),
                "read_before": it["base"], "read_after": it["arm"]})
json.dump({"dpi": DPI, "tiles": man}, open(os.path.join(HERE, "manifest.json"), "w"), indent=1)
print("ok", len(man))
