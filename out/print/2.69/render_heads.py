"""ROADMAP 2.69: crops of the heads whose duration the hook count DECIDED and Sean has not judged.

Usage: PYTHONPATH=. python3 out/print/2.69/render_heads.py <record.json> <subject> [<subject> ...]

Each tile is cut from the PDF at 600 dpi (the gather's dpi) around the head's page box, a red corner bracket on
the head and NOTHING else drawn (our reading is only in heads-manifest.json, never on the tile), staff lines
visible. The frame control: the bracket is drawn from the record's own page box, so a bracket not on a notehead
means the box is wrong, not the print.
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
obs = {o["id"]: o for o in rec["observations"]}
verd = {}
for v in rec["verdicts"]:
    if v["quantity"] == "duration":
        verd[v["subject"]] = v
doc = fitz.open(PDF)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
heads = []
for i, sub in enumerate(sys.argv[2:], 1):
    v = verd[sub]
    gb = [obs[o] for o in v["used"] if o in obs and obs[o]["quantity"] == "glyph_box" and obs[o]["subject"] == sub][-1]
    x0, y0, x1, y1 = gb["detail"]["bbox_page_px"]
    page = int(sub.split("/")[1])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    W, H = 520, 380
    clip = fitz.Rect((cx - W) * 72 / DPI, (cy - H) * 72 / DPI, (cx + W) * 72 / DPI, (cy + H) * 72 / DPI)
    pix = doc[page].get_pixmap(dpi=DPI, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ox, oy = clip.x0 * DPI / 72, clip.y0 * DPI / 72
    d = ImageDraw.Draw(im)
    a, b, c_, e = x0 - ox - 8, y0 - oy - 8, x1 - ox + 8, y1 - oy + 8
    L, w = 18, 5
    for (px, py, sx, sy) in ((a, b, 1, 1), (c_, b, -1, 1), (a, e, 1, -1), (c_, e, -1, -1)):
        d.line([(px, py), (px + sx * L, py)], fill=(220, 0, 0), width=w)
        d.line([(px, py), (px, py + sy * L)], fill=(220, 0, 0), width=w)
    top = Image.new("RGB", (im.width, 60), "white")
    ImageDraw.Draw(top).text((10, 12), f"Head {i} of {len(sys.argv) - 2} -- Brahms 1, page {page + 1}", fill="black", font=font)
    out = Image.new("RGB", (im.width, im.height + 60), "white")
    out.paste(top, (0, 0))
    out.paste(im, (0, 60))
    name = f"head_{i:02d}.png"
    out.save(os.path.join(HERE, name))
    heads.append({"n": i, "tile": name, "subject": sub, "page_box": [x0, y0, x1, y1], "pdf_page_index": page,
                  "ours": {"outcome": v["outcome"], "reason": v["reason"], "value": v["value"]}})
json.dump({"roadmap_item": "2.69", "pdf": os.path.basename(PDF), "dpi": DPI,
           "question": "What is the printed value of the note in the red brackets?",
           "note": "ours is for the manager only; the tile shows nothing of ours", "heads": heads},
          open(os.path.join(HERE, "heads-manifest.json"), "w"), indent=1)
print(len(heads), "tiles")
