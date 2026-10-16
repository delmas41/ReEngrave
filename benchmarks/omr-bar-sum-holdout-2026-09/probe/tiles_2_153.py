"""ROADMAP 2.153 blind tiles for Sean: the notes `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` changes, plus controls that can fail.

    python3 .../tiles_2_153.py            (reads out/2.153/picks_{litolff,brahms}.json; writes ONE set, tiles AND key, in this run)

Roles (NEVER drawn; the KEY only, out/2.153/tiles-key.json, kept uncommitted):
  changed         -- the arm turns a decided beam level into a narrowing (or a bar-picked value)
  joined_control  -- a note whose beam a stem reaches; both arms write the same value (can fail: our reading may be wrong)
  plain_control   -- a note with no beam, written a quarter by both arms (can fail)
Each tile: the note's neighbourhood, ONE blue box (#1F6FEB) on the note asked about, a tile number. Nothing else of ours.
Cutting the tiles and writing the key happen in this ONE run, in ONE loop, so the numbering cannot drift; the run ends by
asserting one key row per PNG, in the same order."""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
OUT, KEY = Path("out/print/2.153-review"), Path("out/2.153/tiles-key.json")
rnd = random.Random(2153)
P = {d: json.load(open("out/2.153/picks_%s.json" % d)) for d in PDFS}


def pick(pool, n, by):
    """n picks, as different as possible by `by` (round-robin over the groups)."""
    groups = {}
    for x in pool:
        groups.setdefault(by(x), []).append(x)
    for g in groups.values():
        rnd.shuffle(g)
    out = []
    while len(out) < n and any(groups.values()):
        for k in sorted(groups, key=str):
            if groups[k] and len(out) < n:
                out.append(groups[k].pop())
    return out


def kind(c):
    a = c["arm"]
    return (c["base"]["written"], "narrowed" if a["outcome"] == "narrowed" else "bar/other")


import statistics  # noqa: E402


def head_sized(doc):
    """A box one head's size (0.75-1.6x the median joined-beam head box of the document): a tile is about a VALUE, so a box that
    is a barline sliver, a stack or a clef is not asked."""
    bx = [c["bbox"] for c in P[doc]["joined"]]
    mh = statistics.median(b[3] - b[1] for b in bx)
    mw = statistics.median(b[2] - b[0] for b in bx)
    return lambda c: 0.75 <= (c["bbox"][3] - c["bbox"][1]) / mh <= 1.6 and 0.75 <= (c["bbox"][2] - c["bbox"][0]) / mw <= 1.6


picks = []
for doc, nch, nj, npl in (("litolff", 6, 2, 1), ("brahms", 6, 2, 1)):
    ok = head_sized(doc)
    a_set = {r["glyph"] for r in json.load(open("out/2.153/a_%s.json" % doc))["a"]}
    changed = [c for c in P[doc]["changed"] if ok(c) and c["glyph"] in a_set and c["base"]["reason"] == "head_and_marks"
               and c["base"]["written"] < 1.0
               and (c["arm"]["outcome"] == "narrowed" or c["arm"]["written"] != c["base"]["written"])]
    joined = [c for c in P[doc]["joined"] if ok(c)]
    plain = [c for c in P[doc]["plain"] if ok(c) and c["base"]["written"] == 1.0 and c["base"]["reason"] == "head_and_marks"]
    print(doc, "pools: changed", len(changed), "joined", len(joined), "plain", len(plain))
    for role, pool, n, by in (("changed", changed, nch, kind), ("joined_control", joined, nj, lambda c: c["base"]["written"]),
                              ("plain_control", plain, npl, lambda c: c["base"]["written"])):
        for c in pick(pool, n, by):
            picks.append(dict(doc=doc, role=role, glyph=c["glyph"], bbox=c["bbox"], base=c["base"], arm=c["arm"]))
rnd.shuffle(picks)

OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("tile_*.png"):
    old.unlink()
KEY.parent.mkdir(parents=True, exist_ok=True)
SP = 33.0
BLUE = (31, 111, 235)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
except OSError:
    font = ImageFont.load_default()
pages, key = {}, []
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
    dr.rectangle([(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad, (x1b - x0) * 2 + pad, (y1b - y0) * 2 + pad], outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, **p))
json.dump(dict(question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?", tiles=len(picks),
               blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump(key, open(KEY, "w"), indent=1)
# the check the report quotes: one key row per PNG, same numbering
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
import collections  # noqa: E402

print(len(pngs), "tiles, key rows", len(rows), "| roles", dict(collections.Counter(r["role"] for r in rows)),
      "| docs", dict(collections.Counter(r["doc"] for r in rows)))
