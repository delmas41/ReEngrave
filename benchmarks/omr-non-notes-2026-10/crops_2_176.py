"""2.176: LOOKING aid (mine, not evidence, not for Sean). Per glyph: a plain crop and the same crop with the glyph box in blue, montaged.
usage: crops_2_176.py DOC LIST.json OUTDIR PER_SHEET [HALF_W_SPACES HALF_H_SPACES]   LIST = [subject, ...]; slices in scratch/slices/DOC."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

DOC, LST, OUT, PER = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4])
HW = float(sys.argv[5]) if len(sys.argv) > 5 else 4.0
HH = float(sys.argv[6]) if len(sys.argv) > 6 else 3.5
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
subs = json.load(open(LST))
if isinstance(subs, dict):
    subs = subs["list"]
OUT.mkdir(parents=True, exist_ok=True)
by_page = {}
for s in subs:
    by_page.setdefault(int(s.split("/")[1]), []).append(s)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
except OSError:
    font = ImageFont.load_default()
tiles = {}
for pg, ss in sorted(by_page.items()):
    want = set(ss)
    gb_of = {}
    hb_of = {}
    for line in open("scratch/slices/%s/p%02d.observations.jsonl" % (DOC, pg)):
        o = json.loads(line)
        if o["subject"] in want and o["quantity"] == "glyph_box" and o["subject"] not in gb_of:
            gb_of[o["subject"]] = o["detail"]["bbox_page_px"]
            hb_of[o["subject"]] = o["value"]
    a = np.asarray(Image.fromarray(render_page(PDFS[DOC], pg, dpi=600).rgb).convert("RGB"))
    for s in ss:
        if s not in gb_of:
            continue
        gb, hb = gb_of[s], hb_of[s]
        k = (gb[2] - gb[0]) / float(hb[3])      # page px per canonical px
        unit = 100.0 * k                          # one staff space in page px
        cx, cy = (gb[0] + gb[2]) / 2, (gb[1] + gb[3]) / 2
        x0, y0 = int(max(cx - HW * unit, 0)), int(max(cy - HH * unit, 0))
        x1, y1 = int(min(cx + HW * unit, a.shape[1])), int(min(cy + HH * unit, a.shape[0]))
        plain = Image.fromarray(a[y0:y1, x0:x1].copy())
        z = max(1, int(round(260.0 / plain.size[1])))
        plain = plain.resize((plain.size[0] * z, plain.size[1] * z), Image.LANCZOS)
        ann = plain.copy()
        d = ImageDraw.Draw(ann)
        d.rectangle([(gb[0] - x0) * z, (gb[1] - y0) * z, (gb[2] - x0) * z, (gb[3] - y0) * z], outline=(31, 111, 235), width=2)
        w, h = plain.size
        tile = Image.new("RGB", (2 * w + 10, h + 28), "white")
        tile.paste(plain, (0, 28))
        tile.paste(ann, (w + 10, 28))
        ImageDraw.Draw(tile).text((6, 3), "%d  %s" % (subs.index(s), s), fill=(0, 0, 0), font=font)
        tiles[s] = tile
order = [s for s in subs if s in tiles]
for i in range(0, len(order), PER):
    chunk = order[i:i + PER]
    W = max(tiles[s].width for s in chunk)
    H = max(tiles[s].height for s in chunk)
    cols = 2
    rowsn = (len(chunk) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rowsn * H), "white")
    for j, s in enumerate(chunk):
        sheet.paste(tiles[s], ((j % cols) * W, (j // cols) * H))
    sheet.save(OUT / ("sheet%02d.png" % (i // PER)))
print("sheets", (len(order) + PER - 1) // PER, "tiles", len(order))
