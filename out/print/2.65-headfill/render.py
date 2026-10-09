"""ROADMAP 2.65 (2.23's six head-fill tiles), re-cut BLIND: Litolff pdf page 6 at 600 dpi, the head's box from the
2.23 record (`litolff-p6-2.23.record.json`, commit 7f2e7898), red corner brackets, nothing else drawn."""
import json, os
import fitz
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "../../../library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
ORDER = ["glyph/6/1/9/2/9", "glyph/6/0/3/8/19", "glyph/6/1/11/5/3", "glyph/6/0/0/9/1", "glyph/6/1/1/0/8", "glyph/6/0/8/3/4"]
boxes = json.load(open(os.path.join(HERE, "boxes-from-2.23-record.json")))
doc = fitz.open(PDF); DPI = 600; Z = 2
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
man = []
for n, k in enumerate(ORDER, 1):
    x0, y0, x1, y1 = boxes[k]["glyph_box"][1]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; W, H = 260, 190
    clip = fitz.Rect((cx - W) * 72 / DPI, (cy - H) * 72 / DPI, (cx + W) * 72 / DPI, (cy + H) * 72 / DPI)
    pix = doc[6].get_pixmap(dpi=DPI * Z, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ox, oy = clip.x0 * DPI / 72, clip.y0 * DPI / 72
    a, b, c, e = ((x0 - ox) * Z - 10, (y0 - oy) * Z - 10, (x1 - ox) * Z + 10, (y1 - oy) * Z + 10)
    d = ImageDraw.Draw(im)
    for (px, py, sx, sy) in ((a, b, 1, 1), (c, b, -1, 1), (a, e, 1, -1), (c, e, -1, -1)):
        d.line([(px, py), (px + sx * 18, py)], fill=(220, 0, 0), width=5)
        d.line([(px, py), (px, py + sy * 18)], fill=(220, 0, 0), width=5)
    out = Image.new("RGB", (im.width, im.height + 60), "white"); out.paste(im, (0, 60))
    ImageDraw.Draw(out).text((10, 12), f"Head-fill tile {n} of 6 -- Beethoven 5 (Litolff), page 7", fill="black", font=font)
    f = f"headfill_{n}.png"; out.save(os.path.join(HERE, f))
    man.append({"n": n, "subject_2_23": k, "page_box": [x0, y0, x1, y1], "detector_class": boxes[k]["glyph_box"][0][0], "file": f})
json.dump({"pdf_page_index": 6, "dpi": DPI, "question": "Is the note in the red brackets filled (black) or open (hollow) -- or is it not a note?", "tiles": man},
          open(os.path.join(HERE, "manifest.json"), "w"), indent=1)
print("ok")
