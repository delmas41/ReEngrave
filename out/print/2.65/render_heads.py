"""ROADMAP 2.65: blind re-ask of the 09-29 rhythm tiles (2.18 / 2.18b / 2.18c), one head per tile.

Each tile is cut from the PDF at 600 dpi (the gather's dpi) around the head's page box, with a red corner
bracket on the head and NOTHING else drawn -- no reading of ours is shown, so Sean's answer is evidence about
the print, compared afterwards with the current record's duration verdict.
"""
import glob, json, os, sys
import fitz
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "../../../benchmarks/omr-missing-notes-2026-09/out/print")
PDF = os.path.join(HERE, "../../../library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
DPI = 600

heads = {}
for f in sorted(glob.glob(os.path.join(B, "*2.18*manifest.json"))):
    m = json.load(open(f))
    tag = os.path.basename(f).replace("-manifest.json", "")
    for c in m["crops"]:
        h = heads.setdefault(c["subject"], {"subject": c["subject"], "page_box": c["page_box"], "from": []})
        h["from"].append(f"{tag}-{c['n']:02d}")
heads = sorted(heads.values(), key=lambda h: (int(h["subject"].split("/")[2]), int(h["subject"].split("/")[3]),
                                              h["page_box"][0]))
doc = fitz.open(PDF)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
for i, h in enumerate(heads, 1):
    page = int(h["subject"].split("/")[1])
    x0, y0, x1, y1 = h["page_box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    W, H = 520, 380  # page px each side of the head
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
    ImageDraw.Draw(top).text((10, 12), f"Tile {i} of {len(heads)} -- Brahms 1, page {page + 1}", fill="black", font=font)
    out = Image.new("RGB", (im.width, im.height + 60), "white"); out.paste(top, (0, 0)); out.paste(im, (0, 60))
    h["tile"] = f"head_{i:02d}.png"; h["n"] = i; h["pdf_page_index"] = page
    out.save(os.path.join(HERE, h["tile"]))
json.dump({"roadmap_item": "2.65", "pdf": os.path.basename(PDF), "dpi": DPI,
           "question": "What is the printed value of the note in the red brackets?",
           "heads": heads}, open(os.path.join(HERE, "heads-manifest.json"), "w"), indent=1)
print(len(heads), "tiles")
