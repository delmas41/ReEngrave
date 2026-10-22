"""ROADMAP 2.69 follow-up: crops of the `augmentationDot` boxes `adjudicate_dot_role` now refuses `on_a_stroke`.

Usage: PYTHONPATH=. python3 out/print/2.69/render_dots.py <record.json> <dot subject> [...]
600 dpi cut from the PDF, a red corner bracket on the dot's own box, nothing else drawn.
"""
import json, os, sys
import fitz
from PIL import Image, ImageDraw, ImageFont

from tools.omr.staged import record_io

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
DPI = 600
rec = record_io.load_record(sys.argv[1])["record"]
boxes = {o["subject"]: o for o in rec["observations"] if o["quantity"] == "glyph_box"}
strokes = {o["subject"]: o for o in rec["observations"] if o["quantity"] == "dot_stroke_ink"}
doc = fitz.open(PDF)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
out_rows = []
for i, sub in enumerate(sys.argv[2:], 1):
    x0, y0, x1, y1 = boxes[sub]["detail"]["bbox_page_px"]
    page = int(sub.split("/")[1])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    W, H = 260, 190
    clip = fitz.Rect((cx - W) * 72 / DPI, (cy - H) * 72 / DPI, (cx + W) * 72 / DPI, (cy + H) * 72 / DPI)
    pix = doc[page].get_pixmap(dpi=DPI, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    ox, oy = clip.x0 * DPI / 72, clip.y0 * DPI / 72
    d = ImageDraw.Draw(im)
    a, b, c_, e = [(v) * 2 for v in (x0 - ox - 6, y0 - oy - 6, x1 - ox + 6, y1 - oy + 6)]
    L, w = 24, 5
    for (px, py, sx, sy) in ((a, b, 1, 1), (c_, b, -1, 1), (a, e, 1, -1), (c_, e, -1, -1)):
        d.line([(px, py), (px + sx * L, py)], fill=(220, 0, 0), width=w)
        d.line([(px, py), (px, py + sy * L)], fill=(220, 0, 0), width=w)
    top = Image.new("RGB", (im.width, 60), "white")
    ImageDraw.Draw(top).text((10, 12), f"Dot box {i} -- Brahms 1, page {page + 1}", fill="black", font=font)
    o = Image.new("RGB", (im.width, im.height + 60), "white")
    o.paste(top, (0, 0)); o.paste(im, (0, 60))
    name = f"dot_{i:02d}.png"
    o.save(os.path.join(HERE, name))
    out_rows.append({"n": i, "tile": name, "subject": sub, "page_box": [x0, y0, x1, y1],
                     "dot_stroke_fraction": strokes[sub]["value"] if sub in strokes else None})
json.dump({"roadmap_item": "2.69 follow-up", "dots": out_rows}, open(os.path.join(HERE, "dots-manifest.json"), "w"), indent=1)
print(len(out_rows), "tiles")
