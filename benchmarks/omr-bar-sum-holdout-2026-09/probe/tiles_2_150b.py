"""ROADMAP 2.150b blind print tiles for Sean: rest boxes the INK TEST refuses that the width floor kept, near-margin
controls, clear controls, and a re-ask of 2.150 tile 11. usage: tiles_2_150b.py OUTDIR KEYFILE
Inputs: out/2.150/{brahms,litolff}-rows.json (cache_2_150.py) + the page rasters; boxes the width floor keeps
(restQuarter >= 0.7 spaces, any rest8th), sampled, measured by rest_ink.measure with family_precision's cuts.
Roles (KEYFILE only, never on the image):
  refused  -- the ink test refuses it (signed margin >= 0); the width floor kept it
  near     -- kept, margin within 0.45 below the cut
  clear    -- kept, margin below -0.45
  re_ask_2_150_tile_11 -- Sean said "quarter rest"; the ink reads a stem running into a head
Each tile: the bar's staff with context, 900 px wide, a tile number, BLUE corners on the box. Nothing else of ours is
drawn."""
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
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import ink_2_150b as INK  # noqa: E402
from tools.omr.staged.adjudicators import family_precision as FP  # noqa: E402

rng = random.Random(21501)


def margin_of(m):
    ms = m["thin_run_sp"] / FP.REST_STROKE_MIN_SP - 1
    mh = max(m["blob_sp"] / FP.REST_HEAD_BLOB_MIN_SP - 1, m["head_ink_sp2"] / FP.REST_HEAD_INK_MIN_SP2 - 1)
    return min(ms, mh)


# Population: rest boxes the width floor KEEPS (restQuarter >= 0.7 spaces wide, or any rest8th), sampled, measured.
pool = {"refused": [], "near": [], "clear": []}
rows = {}
for doc, n_sample in (("brahms", 450), ("litolff", 350)):
    rows[doc] = INK.rows(doc)
    d = rows[doc]
    cand = []
    for g, cls in d["rest_rows"].items():
        if cls not in ("restQuarter", "rest8th") or g not in d["boxes"]:
            continue
        cell = "cell/" + "/".join(g.split("/")[1:5])
        sp = float(d["cells"][cell]["space"])
        w = float(d["boxes"][g][2][2]) / sp
        if cls == "restQuarter" and w < 0.7:
            continue
        cand.append((g, cls, w))
    cand.sort()
    for g, cls, w in rng.sample(cand, min(n_sample, len(cand))):
        m = INK.measure_glyph(doc, g)
        if m is None:
            continue
        mg = margin_of(m)
        bucket = "refused" if mg >= 0 else ("near" if mg >= -0.45 else "clear")
        pool[bucket].append((doc, g, cls, round(w, 3), round(mg, 3)))
    print(doc, {k: len(v) for k, v in pool.items()}, flush=True)
chosen = []
# refused: 11, both documents, both classes as the pool gives them; near: the 3 restQuarter + 2 rest8th kept boxes
# CLOSEST below the cut; clear: 2 restQuarter + 1 rest8th at random.
for bucket, plan in (("refused", (("restQuarter", 11), ("rest8th", 11))), ("near", (("restQuarter", 3), ("rest8th", 2))),
                     ("clear", (("restQuarter", 2), ("rest8th", 1)))):
    items = list(pool[bucket])
    rng.shuffle(items)
    if bucket == "near":
        items.sort(key=lambda t: -t[4])
    got = 0
    total = sum(n for _c, n in plan) if bucket != "refused" else 11
    for cls, n in plan:
        for t in [t for t in items if t[2] == cls][:n]:
            if got >= total:
                break
            chosen.append((t[0], bucket, t[1], t[2], t[3], t[4]))
            got += 1
rng.shuffle(chosen)
# the re-ask: tile 11 of 2.150 (Sean: "quarter rest"; the ink reads a stem running into a head)
chosen.append(("brahms", "re_ask_2_150_tile_11", "glyph/15/1/9/2/5", "restQuarter", 0.47, None))
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
for n, (doc, role, g, cls, wsp, mg) in enumerate(chosen, 1):
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
    key.append({"n": n, "role": role, "document": doc, "glyph": g, "class": cls, "width_spaces": wsp,
                "margin": mg})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
KEY.parent.mkdir(parents=True, exist_ok=True)
KEY.write_text(json.dumps(key, indent=1))
print("wrote", len(key), "tiles to", OUT, "key", KEY)
