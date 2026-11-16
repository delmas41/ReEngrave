"""2.311 print-check of the red-bar sample, for OUR look: each sampled bar cropped from the un-erased page, the bar's
cell outlined orange, every head/rest box the export did NOT write outlined red, the record's cause under it.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/redcheck.py FACTS RED.json PLATE OUT_PREFIX
"""
import json
import sys

from PIL import Image, ImageDraw

from checksheet import page_image
from tools.omr.staged.lane_report import PLATES

facts, red, plate, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3], sys.argv[4]
u = PLATES[plate]["unit"]
W = int(sys.argv[5]) if len(sys.argv) > 5 else 560
PER = int(sys.argv[6]) if len(sys.argv) > 6 else 10
COLS = int(sys.argv[7]) if len(sys.argv) > 7 else 2
tiles = []
for n, b in enumerate(red["sample"], 1):
    key = "cell/%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"])
    r = facts["cells"].get(key)
    if r is None:
        continue
    im = page_image(plate, b["page"])
    x0, y0, x1, y1 = int(r[0] - u), int(r[1] - u), int(r[2] + u), int(r[3] + u)
    crop = im.crop((max(0, x0), max(0, y0), x1, y1)).copy()
    d = ImageDraw.Draw(crop)
    d.rectangle([r[0] - x0, r[1] - y0, r[2] - x0, r[3] - y0], outline=(255, 140, 0), width=2)
    pre = "glyph/%d/%d/%d/%d/" % (b["page"], b["system"], b["staff"], b["cell"])
    for k, g in facts["glyphs"].items():
        if k.startswith(pre) and (g["head"] or g["rest"]) and g["fate"] not in ("written", "written_relocated"):
            bx = g["box"]
            d.rectangle([bx[0] - x0, bx[1] - y0, bx[2] - x0, bx[3] - y0], outline=(220, 0, 0), width=2)
    s = W / crop.width
    crop = crop.resize((W, max(1, int(crop.height * s))))
    lab = "%d p%d s%d st%d c%d %s | %s | %s" % (n, b["page"], b["system"], b["staff"], b["cell"], b["kind"], b["cause"], b["why"][:60])
    tiles.append((lab, crop))
for part in range(0, len(tiles), PER):
    chunk = tiles[part:part + PER]
    h = max(t.height for _, t in chunk)
    sh = Image.new("RGB", (COLS * (W + 8) + 8, ((len(chunk) + COLS - 1) // COLS) * (h + 30) + 8), (255, 255, 255))
    dd = ImageDraw.Draw(sh)
    for i, (lab, t) in enumerate(chunk):
        x, y = 8 + (i % COLS) * (W + 8), 8 + (i // COLS) * (h + 30)
        sh.paste(t, (x, y))
        dd.text((x, y + t.height + 2), lab, fill=(0, 0, 0))
    sh.save("%s-%d.png" % (out, part // PER + 1))
print(len(tiles))
