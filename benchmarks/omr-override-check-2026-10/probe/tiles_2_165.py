"""ROADMAP 2.165 blind tiles for Sean: notes the one shared override check (`OMR_ONE_OVERRIDE_CHECK`) changes.

    python3 .../tiles_2_165.py OUTDIR [N_CHANGED=23]   (reads OUTDIR/<doc>.changed.json from compare_2_165.py and the
                                                      mini records OUTDIR/<doc>.on.record.json; ONE run: tiles AND key)

Picks: changed notes Sean has not judged (judged index), both plates, spread across the causes (guard rows and the
shared-stem rule) round-robin, biggest cause first, one per bar; plus 2 controls -- a note the reader decided that the
flag does not touch (one per plate; can fail: our reading may be wrong). The roles and both arms' readings are in the
KEY only (out/2.165/tiles-key.json, uncommitted). Each tile: the note's neighbourhood, ONE blue box (#1F6FEB) on the
note asked about, "Tile N". Nothing else of ours."""
import collections
import json
import random
import sys
from pathlib import Path

import ijson
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
SRC = Path(sys.argv[1])
N_CHANGED = int(sys.argv[2]) if len(sys.argv) > 2 else 23
OUT, KEY = Path("out/print/2.165-review"), Path("out/2.165/tiles-key.json")
rnd = random.Random(2165)
JUDGED = {s for r in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
          for s in (r["subjects"] or [r["subject"]] if r["subject_kind"] == "glyph" else []) if s}

bx, by_cause, plain = {}, collections.defaultdict(list), []
for doc in ("litolff", "brahms"):
    with open(SRC / ("%s.on.record.json" % doc), "rb") as f:
        for o in ijson.items(f, "observations.item", use_float=True):
            d = o.get("detail") or {}
            if d.get("bbox_page_px") and d.get("category") == "notehead":
                bx[(doc, o["subject"])] = d["bbox_page_px"]
    ch = json.load(open(SRC / ("%s.changed.json" % doc)))
    seen_bar = set()
    for g in sorted(ch):
        d = ch[g]
        b = "/".join(g.split("/")[1:5])
        if g in JUDGED or (doc, g) not in bx or (doc, b) in seen_bar or (d["on"] or {}).get("rest"):
            continue
        seen_bar.add((doc, b))
        by_cause[d["cause"]].append(dict(doc=doc, glyph=g, base=d["base"], on=d["on"], cause=d["cause"]))
    B = json.load(open(SRC / ("%s.base.json" % doc)))
    cands = [g for g, v in B["glyphs"].items() if g not in ch and g not in JUDGED and (doc, g) in bx
             and v and v["cls"] == "READ" and v["reason"] == "head_and_marks" and not v["rest"]]
    cands.sort()
    rnd.shuffle(cands)
    if cands:
        plain.append(dict(doc=doc, glyph=cands[0], base=B["glyphs"][cands[0]], on=B["glyphs"][cands[0]],
                          cause="plain_control"))

for c in by_cause.values():
    c.sort(key=lambda p: (p["doc"], p["glyph"]))
    rnd.shuffle(c)
order = sorted(by_cause, key=lambda c: -len(by_cause[c]))
print("pool by cause:", {c: len(by_cause[c]) for c in order})
picks = []
while len(picks) < N_CHANGED and any(by_cause[c] for c in order):
    for c in order:
        if by_cause[c] and len(picks) < N_CHANGED:
            # alternate plates within a cause where both have one
            docs = {p["doc"] for p in by_cause[c]}
            want = "litolff" if sum(p["doc"] == "litolff" for p in picks) <= sum(p["doc"] == "brahms" for p in picks) \
                else "brahms"
            i = next((j for j, p in enumerate(by_cause[c]) if p["doc"] == want), 0) if len(docs) > 1 else 0
            picks.append(dict(role="changed", **by_cause[c].pop(i)))
picks += [dict(role="plain_control", **p) for p in plain]
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
    x0b, y0b, x1b, y1b = bx[(p["doc"], p["glyph"])]
    x0, y0 = int(max(x0b - 7 * SP, 0)), int(max(y0b - 5 * SP, 0))
    x1, y1 = int(min(x1b + 7 * SP, a.shape[1])), int(min(y1b + 5 * SP, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    pad = 4
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad, (x1b - x0) * 2 + pad,
                                    (y1b - y0) * 2 + pad], outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, bbox=bx[(p["doc"], p["glyph"])], **p))
json.dump(dict(question="What is the written value of the note in the blue box (quarter, eighth, half, dotted half ...)? "
                        "Say 'not a note' if it is not one.", tiles=len(picks),
               blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))
json.dump(key, open(KEY, "w"), indent=1)
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
assert not any(r["glyph"] in JUDGED for r in rows)
print(len(pngs), "tiles | roles", dict(collections.Counter((r["doc"], r["role"], r["cause"]) for r in rows)))
