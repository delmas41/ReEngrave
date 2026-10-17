"""ROADMAP 2.153b blind tiles: notes whose value `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` changes on the whole-record replay of
the 20261016-night records (main 1d42c4aa + 2.154 + 2.155), which Sean has not judged; plus 2 controls that can fail.

    python3 .../tiles_2_153b.py N_LITOLFF N_BRAHMS   (reads out/2.153b/whole_{doc}.json + the page slices; ONE run: tiles AND key)

Roles (NEVER drawn; the KEY only, out/2.153b/tiles-key.json, uncommitted):
  changed        -- the flag changes this note's live duration (off -> on).
  joined_control -- a beamed note the reader decided an eighth (head_and_marks) with a beam level its stem is read joined to,
                    unchanged by the flag (can fail: our eighth may be wrong).
Excluded: every glyph any judged index row, answers.json or manifest names. Head-sized boxes only (a tile asks about a VALUE).
Each tile: the note's neighbourhood, ONE blue box (#1F6FEB) on the note asked about, "Tile N". Nothing else of ours."""
import collections
import json
import random
import statistics
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
from tools.omr.preprocessing import render_page  # noqa: E402
import sean_2_153b  # noqa: E402

SD = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-start-here-go-cbd2bc/" \
     "97504ff3-7ad5-4ac2-8be1-95887e8a9382/scratchpad/slices"
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
OUT, KEY = Path("out/print/2.153b-review"), Path("out/2.153b/tiles-key.json")
NEED = {"litolff": int(sys.argv[1]), "brahms": int(sys.argv[2])}
rnd = random.Random(21532)
_, NAMED = sean_2_153b.load()


def boxes_and_joins(doc):
    bx, joined_heads = {}, set()
    for p in sorted(Path(SD, doc).glob("*.observations.jsonl")):
        for line in open(p):
            o = json.loads(line)
            d = o.get("detail") or {}
            if o["quantity"] == "glyph_box" and d.get("bbox_page_px") and d.get("category") == "notehead":
                bx[o["subject"]] = d["bbox_page_px"]
    return bx


def pick(pool, n, by):
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


def show(b):
    if b is None:
        return "none"
    if b["outcome"] == "decided":
        return "%g" % b["beats"]
    return "%s%s" % (b["outcome"][:3], b["cands"] or "")


picks = []
for doc in ("litolff", "brahms"):
    W = json.load(open("out/2.153b/whole_%s.json" % doc))
    bx = boxes_and_joins(doc)
    mh = statistics.median(b[3] - b[1] for b in bx.values())
    mw = statistics.median(b[2] - b[0] for b in bx.values())
    ok = lambda g: g in bx and 0.75 <= (bx[g][3] - bx[g][1]) / mh <= 1.6 and 0.75 <= (bx[g][2] - bx[g][0]) / mw <= 1.6
    REST = ("rest_class", "whole_rest_means_the_bar")   # whole rests resized by the meter: a meter question, not a tile
    pool = [dict(doc=doc, glyph=g, bbox=bx[g], off=d["off"], on=d["on"]) for g, d in W["changed"].items()
            if g not in NAMED and ok(g) and d["off"] and d["on"]
            and d["off"]["reason"] not in REST and d["on"]["reason"] not in REST and show(d["off"]) != show(d["on"])]
    print(doc, "changed", len(W["changed"]), "unjudged head-sized", len(pool))
    for r in pick(pool, NEED[doc], lambda r: (show(r["off"]), show(r["on"]))):
        picks.append(dict(role="changed", **r))
    # control: an eighth decided by the reader with a JOINED beam (its stem reaches the stroke), unchanged by the flag
    ctl = json.load(open("out/2.153b/controls_%s.json" % doc))
    cpool = [dict(doc=doc, glyph=g, bbox=bx[g], off=b, on=b) for g, b in ctl.items() if g not in NAMED and ok(g)
             and g not in W["changed"]]
    for r in pick(cpool, 1, lambda r: 0):
        picks.append(dict(role="joined_control", **r))
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
    pad = 4
    rect = [(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad + 70, (x1b - x0) * 2 + pad, (y1b - y0) * 2 + pad + 70]
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).rectangle(rect, outline=BLUE, width=4)
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, crop_origin=[x0, y0], rect_in_tile=rect, **p))
json.dump(dict(question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?", tiles=len(picks),
               blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))   # blank for Sean ({} adds no row to the judged index)
json.dump(key, open(KEY, "w"), indent=1)

# CHECK every tile against its key row: one PNG per row, same numbering, and the ONLY blue pixels in the PNG are the drawn
# rectangle at the key's box (bounding box of pure-blue pixels == the key's rect, +-3 px)
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
for png, r in zip(pngs, rows):
    im = np.asarray(Image.open(png).convert("RGB")).astype(int)
    blue = (abs(im[..., 0] - 31) < 4) & (abs(im[..., 1] - 111) < 4) & (abs(im[..., 2] - 235) < 4)
    ys, xs = np.nonzero(blue)
    got = [xs.min(), ys.min(), xs.max(), ys.max()]
    want = r["rect_in_tile"]
    assert all(abs(g - w) <= 3 for g, w in zip(got, want)), (png.name, got, want)
    assert r["glyph"] == picks[r["n"] - 1]["glyph"]
print(len(pngs), "tiles, key rows", len(rows), "| every tile's blue box == its key row's box",
      "| roles", dict(collections.Counter((r["doc"], r["role"]) for r in rows)))
