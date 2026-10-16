"""ROADMAP 2.151 blind tiles for Sean: the notes `OMR_DOT_BOXED_AS_A_HEAD` changes, plus controls that can fail.

    python3 .../tiles_2_151.py PICKS.json OUTDIR KEYFILE

PICKS.json: [{"doc": "brahms", "glyph": ..., "bbox": [x0,y0,x1,y1] page px, "role": ..., "base": ..., "arm": ...}, ...]
Roles (NEVER drawn; KEYFILE only, kept outside out/print):
  changed       -- the arm reads a dot boxed as a notehead on this note (dotted, or narrowed with a dotted candidate)
  declined      -- a dot-shaped refused box beside this note that the rule did NOT count (position said no / cannot tell)
  plain_control -- a note both arms write with no dot
  dotted_control-- a note both arms write dotted from a dot-class box
Each tile: the note's neighbourhood, ONE blue box (#1F6FEB) on the note asked about, a tile number. Nothing else of ours.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
picks = json.load(open(sys.argv[1]))
OUT, KEY = Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
KEY.parent.mkdir(parents=True, exist_ok=True)
random.Random(2151).shuffle(picks)
SP = 33.0
BLUE = (31, 111, 235)
pages = {}
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
except OSError:
    font = ImageFont.load_default()
key = []
for n, p in enumerate(picks, 1):
    pg = int(p["glyph"].split("/")[1])
    if (p["doc"], pg) not in pages:
        pages[(p["doc"], pg)] = np.asarray(Image.fromarray(render_page(PDFS[p["doc"]], pg, dpi=600).rgb).convert("RGB"))
    a = pages[(p["doc"], pg)]
    x0b, y0b, x1b, y1b = p["bbox"]
    x0, y0 = int(max(x0b - 6 * SP, 0)), int(max(y0b - 5 * SP, 0))
    x1, y1 = int(min(x1b + 6 * SP, a.shape[1])), int(min(y1b + 5 * SP, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    dr = ImageDraw.Draw(crop)
    pad = 4
    dr.rectangle([(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad, (x1b - x0) * 2 + pad, (y1b - y0) * 2 + pad],
                 outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, **p))
json.dump(dict(question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?",
               tiles=len(picks), blue="the note asked about", nothing_else_drawn=True),
          open(OUT / "manifest.json", "w"), indent=1)
json.dump(key, open(KEY, "w"), indent=1)
print(len(picks), "tiles ->", OUT)
