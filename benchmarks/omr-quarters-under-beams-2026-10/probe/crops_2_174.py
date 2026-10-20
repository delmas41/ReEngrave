"""2.174 step 2b: LOOKING aid (mine, not evidence, not for Sean). For a list of glyph subjects: a plain crop and the same crop with the
cell's geometry drawn (head blue, CV stems green, CV beam strokes orange, detector beam boxes red), montaged into sheets.
usage: crops_2_174.py DOC LIST.json OUTDIR PER_SHEET     LIST = [subject, ...]; slices read from scratch/slices/DOC."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

DOC, LST, OUT, PER = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4])
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
subs = json.load(open(LST))
OUT.mkdir(parents=True, exist_ok=True)
by_page = {}
for s in subs:
    by_page.setdefault(int(s.split("/")[1]), []).append(s)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
except OSError:
    font = ImageFont.load_default()
tiles = {}
for pg, ss in sorted(by_page.items()):
    cells = {"cell/" + "/".join(s.split("/")[1:5]) for s in ss}
    rows = {}
    for l in open("scratch/slices/%s/p%02d.observations.jsonl" % (DOC, pg)):
        o = json.loads(l)
        if o["subject"] in cells or o["subject"] in ss:
            if o["quantity"] in ("cell_box", "stem", "beam_stroke", "cell_staff_space", "glyph_box"):
                rows.setdefault(o["subject"], []).append(o)
    a = np.asarray(Image.fromarray(render_page(PDFS[DOC], pg, dpi=600).rgb).convert("RGB"))
    for s in ss:
        cell = "cell/" + "/".join(s.split("/")[1:5])
        cr = rows[cell]
        cb = [o for o in cr if o["quantity"] == "cell_box"][0]["value"]
        sp_c = [o for o in cr if o["quantity"] == "cell_staff_space"][0]["value"]
        gb = [o for o in rows[s] if o["quantity"] == "glyph_box"][0]["detail"]["bbox_page_px"]
        sp = 15.5 * (gb[3] - gb[1]) / 19.0 if False else None
        # canonical -> page: page = origin + c * (page_space / canonical_space). Page space from the head box: use the cell's own ratio.
        hb = [o for o in rows[s] if o["quantity"] == "glyph_box"][0]["value"]
        k = (gb[2] - gb[0]) / float(hb[3])      # page px per canonical px (head width ratio)
        ox, oy = cb[0], cb[1]
        cx, cy = (gb[0] + gb[2]) / 2, (gb[1] + gb[3]) / 2
        unit = 100.0 * k                          # one staff space in page px
        x0, y0 = int(max(cx - 7 * unit, 0)), int(max(cy - 6 * unit, 0))
        x1, y1 = int(min(cx + 7 * unit, a.shape[1])), int(min(cy + 6 * unit, a.shape[0]))
        plain = Image.fromarray(a[y0:y1, x0:x1].copy())
        ann = plain.copy()
        d = ImageDraw.Draw(ann)
        for o in cr:
            if o["quantity"] == "stem":
                v = o["value"]
                d.rectangle([ox + v[0] * k - x0, oy + v[1] * k - y0, ox + (v[0] + v[2]) * k - x0, oy + (v[1] + v[3]) * k - y0], outline=(0, 160, 0), width=2)
            elif o["quantity"] == "beam_stroke":
                v = o["value"]
                col = (255, 140, 0) if o["reader"] == "cv_lines" else (220, 0, 0)
                d.rectangle([ox + v[0] * k - x0, oy + v[1] * k - y0, ox + (v[0] + v[2]) * k - x0, oy + (v[1] + v[3]) * k - y0], outline=col, width=2)
        d.rectangle([gb[0] - x0, gb[1] - y0, gb[2] - x0, gb[3] - y0], outline=(31, 111, 235), width=3)
        w, h = plain.size
        tile = Image.new("RGB", (2 * w + 10, h + 40), "white")
        tile.paste(plain, (0, 40))
        tile.paste(ann, (w + 10, 40))
        ImageDraw.Draw(tile).text((6, 4), s, fill=(0, 0, 0), font=font)
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
    sheet = sheet.resize((int(sheet.width * 1.0), int(sheet.height * 1.0)), Image.LANCZOS)
    sheet.save(OUT / ("sheet_%02d.png" % (i // PER + 1)))
    print("sheet", i // PER + 1, [c[6:] for c in chunk])
