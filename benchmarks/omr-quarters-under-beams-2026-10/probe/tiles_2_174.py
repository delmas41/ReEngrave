"""ROADMAP 2.174 blind tiles: decided quarters (`head_and_marks`) the flag `OMR_STROKE_AT_STEM_TIP_NARROWS` turned NARROWED (replay_2_174.py OFF vs ON)
that Sean has not judged, plus 2 controls (a decided quarter the flag did NOT touch; one per plate; each can fail).

    python3 .../tiles_2_174.py REPLAYOUT SLICEDIR MAX       (ONE run: tiles AND key)

Roles (never drawn; the KEY only, out/2.174/tiles-key.json): narrowed -- the flag stopped writing a quarter here; control -- a decided quarter left
alone. Excluded: every glyph the judged index, any out/print answers/manifest, the 2.162 Set B key or the 2.153b key names; non-head-sized boxes.
Each tile: the note's neighbourhood, ONE blue box (#1F6FEB) on the note asked about, "Tile N". Nothing else of ours."""
import collections
import glob
import json
import random
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

W, SD, MAX = sys.argv[1], sys.argv[2], int(sys.argv[3])
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
OUT, KEY = Path("out/print/2.174-review"), Path("out/2.174/tiles-key.json")
rnd = random.Random(21740)

named = set()
for r in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]:
    named |= {s for s in (r["subjects"] or [r["subject"]]) if s and s.startswith("glyph/")}
for path in glob.glob("out/print/**/*.json", recursive=True):
    try:
        d = json.load(open(path))
    except (OSError, ValueError):
        continue
    for t in (d.get("tiles") if isinstance(d, dict) and isinstance(d.get("tiles"), list) else []):
        if isinstance(t, dict) and str(t.get("glyph", "")).startswith("glyph/"):
            named.add(t["glyph"])
named |= {r["glyph"] for r in json.load(open("out/2.162/tiles-key-b.json"))}
named |= {r["glyph"] for r in json.loads(subprocess.check_output(
    ["git", "show", "origin/lane-2.153-retile:out/2.153b/tiles-key.json"], text=True))}


def boxes(doc):
    bx = {}
    for p in sorted(Path(SD, doc).glob("*.observations.jsonl")):
        for line in open(p):
            o = json.loads(line)
            d = o.get("detail") or {}
            if o["quantity"] == "glyph_box" and d.get("bbox_page_px") and d.get("category") == "notehead":
                bx[o["subject"]] = d["bbox_page_px"]
    return bx


picks = []
pools = {}
for doc in ("litolff", "brahms"):
    on = json.load(open("%s/%s.on.json" % (W, doc)))
    off = json.load(open("%s/%s.off.json" % (W, doc)))
    bx = boxes(doc)
    mh = statistics.median(b[3] - b[1] for b in bx.values())
    mw = statistics.median(b[2] - b[0] for b in bx.values())
    ok = lambda g: g in bx and 0.75 <= (bx[g][3] - bx[g][1]) / mh <= 1.6 and 0.75 <= (bx[g][2] - bx[g][0]) / mw <= 1.6
    marked = {}
    for g, a in off["glyphs"].items():
        b = on["glyphs"].get(g)
        if a and b and a["outcome"] == "decided" and a["beats"] == 1.0 and a["reason"] == "head_and_marks" and b["outcome"] == "narrowed" \
                and (b.get("ev") or {}).get("origin_reason") == "beams_ambiguous":
            marked[g] = dict(kept=a["beats"], alternative=b["cands"])
    pool = sorted(g for g in marked if g not in named and ok(g))
    print(doc, "narrowed by the flag", len(marked), "unjudged head-sized", len(pool), "named excluded", len(set(marked) & named))
    pools[doc] = [dict(doc=doc, glyph=g, bbox=bx[g], role="narrowed", kept=marked[g]["kept"], alternative=marked[g]["alternative"]) for g in pool]
    ctl = [g for g, v in sorted(off["glyphs"].items()) if g not in named and g not in marked and ok(g) and v
           and v["outcome"] == "decided" and v["reason"] == "head_and_marks" and not v["rest"] and v["beats"] == 1.0
           and (on["glyphs"].get(g) or {}).get("outcome") == "decided"]
    c = rnd.choice(ctl)
    picks.append(dict(doc=doc, glyph=c, bbox=bx[c], role="control", kept=off["glyphs"][c]["beats"]))
chosen = []
for doc in ("litolff", "brahms"):
    p = pools[doc]
    rnd.shuffle(p)
    chosen += p[:(MAX - 2) // 2]
picks = chosen + picks
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
json.dump({}, open(OUT / "answers.json", "w"))
json.dump(key, open(KEY, "w"), indent=1)

pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks)
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
for png, r in zip(pngs, rows):
    im = np.asarray(Image.open(png).convert("RGB")).astype(int)
    blue = (abs(im[..., 0] - 31) < 4) & (abs(im[..., 1] - 111) < 4) & (abs(im[..., 2] - 235) < 4)
    ys, xs = np.nonzero(blue)
    got = [xs.min(), ys.min(), xs.max(), ys.max()]
    assert all(abs(g - w) <= 3 for g, w in zip(got, r["rect_in_tile"])), (png.name, got, r["rect_in_tile"])
print(len(pngs), "tiles | every tile's blue box == its key row's box | roles",
      dict(collections.Counter((r["doc"], r["role"]) for r in rows)))
