"""ROADMAP 2.160 part 3 -- a crop sheet (NOT blind) of the left-edge arc-tail candidates `tails_2_160.py` counted, for Sean
to look at. Each crop: the head box we drew, in blue (#1F6FEB), nothing else of ours; captioned with doc, glyph id and the
arc it sits on. Writes out/print/2.160-tie-tails/crop_NN.png, sheet_N.png (up to 12 crops each) and index.json.
Only hits whose staff-erased head ink is below MAX_NET (default 0.6) are cut: above it the box nearly always holds a whole
head (a real note a tie runs into), which the count reports but does not crop.
usage: tails_sheet_2_160.py TAILS_LITOLFF.json TAILS_BRAHMS.json [MAX_NET=0.6]"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
OUT = Path("out/print/2.160-tie-tails")
OUT.mkdir(parents=True, exist_ok=True)
for old in list(OUT.glob("crop_*.png")) + list(OUT.glob("sheet_*.png")):
    old.unlink()
BLUE = (31, 111, 235)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
except OSError:
    font = ImageFont.load_default()
items = []
MAX_NET = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
for doc, path in (("litolff", sys.argv[1]), ("brahms", sys.argv[2])):
    for h in json.load(open(path))["hits"]:
        if h["ink_net"] is not None and h["ink_net"] < MAX_NET:
            items.append((doc, h))
items.sort(key=lambda t: (t[0] != "litolff", t[1]["ink_net"]))
pages, crops, index = {}, [], []
for n, (doc, h) in enumerate(items, 1):
    pg = int(h["glyph"].split("/")[1])
    if (doc, pg) not in pages:
        pages[(doc, pg)] = np.asarray(Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB"))
    a = pages[(doc, pg)]
    sp = h["sp"]
    x0b, y0b, x1b, y1b = h["box"]
    x0, y0 = int(max(x0b - 8 * sp, 0)), int(max(y0b - 5 * sp, 0))
    x1, y1 = int(min(x1b + 8 * sp, a.shape[1])), int(min(y1b + 5 * sp, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * 3 - 3, (y0b - y0) * 3 - 3, (x1b - x0) * 3 + 3, (y1b - y0) * 3 + 3],
                                   outline=BLUE, width=4)
    tile = Image.new("RGB", (max(crop.width, 520), crop.height + 80), "white")
    tile.paste(crop, (0, 80))
    d = ImageDraw.Draw(tile)
    d.text((8, 6), "%d. %s %s" % (n, doc, h["glyph"].replace("glyph/", "")), fill=(0, 0, 0), font=font)
    d.text((8, 42), "%s %s, ink %.2f" % (h["kind"], h["arc_glyph"].replace("glyph/", ""), h["ink_net"] or -1),
           fill=(80, 80, 80), font=font)
    tile.save(OUT / ("crop_%02d.png" % n))
    crops.append(tile)
    index.append(dict(n=n, doc=doc, glyph=h["glyph"], box=h["box"], arc=h["arc_glyph"], kind=h["kind"],
                      gap_sp=h["gap_sp"], left_gap_sp=h["left_gap_sp"], ink=h["ink"], ink_net=h["ink_net"],
                      conf=h["conf"]))
COLS = 4
for s in range(0, len(crops), 12):
    group = crops[s:s + 12]
    w = max(c.width for c in group)
    hgt = max(c.height for c in group)
    rows = (len(group) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * (w + 10), rows * (hgt + 10)), "white")
    for i, c in enumerate(group):
        sheet.paste(c, ((i % COLS) * (w + 10), (i // COLS) * (hgt + 10)))
    sheet.save(OUT / ("sheet_%d.png" % (s // 12 + 1)))
json.dump(dict(max_net=MAX_NET, what="ROADMAP 2.160 part 3: notehead boxes at a bar's left edge sitting on the end of a tie/slur from the "
                    "previous bar (candidates, NOT blind). Blue = our notehead box. Caption: doc, glyph id, the arc, "
                    "the head box's staff-erased ink.", crops=index), open(OUT / "index.json", "w"), indent=1)
print(len(crops), "crops")
