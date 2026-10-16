"""ROADMAP 2.150 blind print tiles for Sean: restQuarter boxes the width floor refuses, plus controls that can fail.
usage: tiles_2_150.py OUTDIR KEYFILE
Inputs: out/2.150/{brahms,litolff}-rows.json + -census.json (cache_2_150.py / census_2_150.py).
Roles (KEYFILE only, never on the image):
  refused       -- kept restQuarter today, box under 0.7 spaces: the arm refuses it (must NOT be a rest)
  near_control  -- kept restQuarter, box 0.7-0.95 spaces: the arm keeps it (the band just above the floor)
  wide_control  -- kept restQuarter, box >= 1.0 spaces: the arm keeps it
Each tile: the bar's staff with 2.5 spaces of context, 900 px wide, a tile number, BLUE corners on the box. Nothing
else of ours is drawn."""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {"brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
        "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
OUT, KEY = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
NAMED = {"glyph/21/0/6/8/11", "glyph/11/1/1/9/8", "glyph/9/1/3/8/9"}
rng = random.Random(2150)
chosen = []
rows = {}
for doc, k_ref, k_near, k_wide in (("brahms", 7, 3, 2), ("litolff", 5, 2, 1)):
    rows[doc] = json.load(open(f"out/2.150/{doc}-rows.json"))
    c = [r for r in json.load(open(f"out/2.150/{doc}-census.json")) if r["cls"] == "restQuarter"]
    ref = sorted(r["glyph"] for r in c if r["w"] < 0.7)
    named = [g for g in ref if g in NAMED]
    rest = [g for g in ref if g not in NAMED]
    pick = named + rng.sample(rest, k_ref - len(named))
    chosen += [(doc, "refused", g) for g in pick]
    near = sorted(r["glyph"] for r in c if 0.7 <= r["w"] < 0.95)
    chosen += [(doc, "near_control", g) for g in rng.sample(near, k_near)]
    wide = sorted(r["glyph"] for r in c if r["w"] >= 1.0)
    chosen += [(doc, "wide_control", g) for g in rng.sample(wide, k_wide)]
rng.shuffle(chosen)
# The one box the arm refuses that Sean's hand-truth page labels `restQuarter` (q-box in cell s0-st8-m1, 8 px wide at
# the cell's left edge; the lane's look reads a barline there): asked, not assumed.
chosen.append(("brahms", "hand_truth_conflict", "glyph/0/0/8/1/7"))
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
except Exception:
    font = ImageFont.load_default()


def bracket(arr, x0, y0, x1, y1, colour, arm=18, thick=5):
    h, w = arr.shape[:2]
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        xa, xb = sorted((cx, cx + dx * arm))
        ya, yb = sorted((cy, cy + dy * arm))
        arr[max(cy - thick // 2, 0):cy + thick // 2 + 1, max(xa, 0):min(xb, w)] = colour
        arr[max(ya, 0):min(yb, h), max(cx - thick // 2, 0):cx + thick // 2 + 1] = colour


pages = {}
manifest = {"dpi": 600, "question": "What is the mark in the blue box?", "tiles": []}
key = []
for n, (doc, role, g) in enumerate(chosen, 1):
    d = rows[doc]
    b = d["boxes"][g]
    page = int(g.split("/")[1])
    staff = "staff/" + "/".join(g.split("/")[1:4])
    cell = "cell/" + "/".join(g.split("/")[1:5])
    ln = d["staff"][staff]["lines"]
    sp = float(d["staff"][staff]["space"])
    cb = d["cells"][cell]["box"]
    if (doc, page) not in pages:
        pages[(doc, page)] = np.asarray(Image.fromarray(render_page(PDFS[doc], page, dpi=600).rgb).convert("RGB"))
    img = pages[(doc, page)].copy()
    x0, y0, x1, y1 = b[3]
    pad = int(max(2.5 * sp, (14 * sp - (cb[2] - cb[0])) / 2))
    wx0, wx1 = max(0, int(cb[0]) - pad), int(cb[2]) + pad
    wy0, wy1 = int(min(ln) - 4.5 * sp), int(max(ln) + 4.5 * sp)
    bracket(img, int(x0) - 6, int(y0) - 6, int(x1) + 6, int(y1) + 6, (0, 70, 230))
    crop = Image.fromarray(img[max(0, wy0):wy1, wx0:wx1])
    crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
    tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile.paste(crop, (0, 130))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    manifest["tiles"].append({"n": n, "file": name, "document": doc, "page_box_600dpi": [wx0, wy0, wx1, wy1]})
    key.append({"n": n, "role": role, "document": doc, "glyph": g,
                "width_spaces": round(float(b[2][2]) / float(d["cells"][cell]["space"]), 3)})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
KEY.parent.mkdir(parents=True, exist_ok=True)
KEY.write_text(json.dumps(key, indent=1))
print("wrote", len(key), "tiles to", OUT, "key", KEY)
