"""ROADMAP 2.155b blind tiles for Sean: notes the TIGHTENED `OMR_STEM_AT_BAR_EDGE` changes that he has not judged, plus controls.

Pool: every glyph on the re-gathered tile pages (Litolff p1/2/3/6/10/15/16, Brahms p1/3/9/11; `--through adjudicate`) whose
`adjudicate_duration` reading differs between base and the tightened arm, in either condition (shipped defaults; 2.153 rule ON).
Excluded: every glyph any `out/print/**/answers.json` or the judged index names (Sean already ruled on it). Controls: interior
beamed eighths both arms decide the same in both conditions (can fail). Roles and readings go in the KEY only
(out/2.155/tiles-2.155b-key.json, uncommitted). Tile = neighbourhood + ONE blue box (#1F6FEB) + a number; nothing else of ours.
answers.json is written as {} (blank: no rows enter the judged index). One run cuts tiles and key and asserts one row per PNG."""
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-beam-confirm-2026-10/probe")
from score_2_155 import load, reading  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
OUT, KEY = Path("out/print/2.155b-review"), Path("out/2.155/tiles-2.155b-key.json")
D = "out/2.155/"
N_CHANGED, N_CONTROL = 18, 2
rnd = random.Random(21552)

judged = set()
for p in Path("out/print").rglob("answers.json"):
    try:
        txt = p.read_text()
    except OSError:
        continue
    judged.update(w.strip('"') for w in txt.replace(",", " ").split() if w.strip('"').startswith("glyph/"))
for t in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]:
    for s in [t.get("subject")] + list(t.get("subjects") or []):
        if s:
            judged.add(s)
print("judged glyph ids excluded:", len(judged))

COND = {"defaults": ("tiles_{d}_base", "t2_{d}_tight_def"), "rule_2153_on": ("t2_{d}_base_r153", "t2_{d}_tight_r153")}
recs = {}
for d in PDFS:
    for c, (b, a) in COND.items():
        pb, pa = (Path(D + x.format(d=d) + ".record.json") for x in (b, a))
        if pb.exists() and pa.exists():         # Brahms under the 2.153 rule was not gathered (Sean 2026-10-16: "Cut those")
            recs[(d, c)] = (load(str(pb)), load(str(pa)))
print("conditions read:", sorted(recs))


def key_of(rd):
    return (rd["outcome"], rd.get("written"), tuple(rd.get("cands") or ()))


changed, same = {}, collections.defaultdict(int)
boxes = {}
for (d, c), (b, a) in sorted(recs.items()):
    if True:
        for o in b["observations"]:
            if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
                boxes[o["subject"]] = (d, o["detail"]["bbox_page_px"])
        heads = {o["subject"] for o in b["observations"] if o["quantity"] == "glyph_box"
                 and (o.get("detail") or {}).get("category") == "notehead"}
        for g in heads:
            rb, ra = reading(b, g), reading(a, g)
            if key_of(rb) != key_of(ra):
                changed.setdefault(g, {})[c] = dict(base=rb, arm=ra)
            elif rb["outcome"] == "decided" and rb.get("written") == 0.5:
                same[g] += 1
pool = [g for g in changed if g not in judged]
print("changed glyphs", len(changed), "unjudged", len(pool))
by_kind = collections.defaultdict(list)
for g in pool:
    c = "defaults" if "defaults" in changed[g] else "rule_2153_on"
    x = changed[g][c]
    by_kind[(c, x["base"]["outcome"], x["base"].get("written"), x["arm"]["outcome"], x["arm"].get("written"))].append(g)
for v in by_kind.values():
    rnd.shuffle(v)
picks = []
while len(picks) < N_CHANGED and any(by_kind.values()):
    for k in sorted(by_kind, key=str):
        if by_kind[k] and len(picks) < N_CHANGED:
            g = by_kind[k].pop()
            picks.append(dict(doc=boxes[g][0], role="changed", glyph=g, bbox=boxes[g][1], readings=changed[g]))
ctl = [g for g, n in same.items() if n == sum(1 for (d, _c) in recs if d == boxes.get(g, ("",))[0]) and g not in judged and g not in changed and g in boxes]
rnd.shuffle(ctl)
for g in ctl[:N_CONTROL]:
    picks.append(dict(doc=boxes[g][0], role="joined_control", glyph=g, bbox=boxes[g][1], readings="same eighth in both arms"))
rnd.shuffle(picks)

OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("tile_*.png"):
    old.unlink()
SP, BLUE = 33.0, (31, 111, 235)
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
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * 2 - 4, (y0b - y0) * 2 - 4, (x1b - x0) * 2 + 4, (y1b - y0) * 2 + 4],
                                   outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, **p))
json.dump(dict(question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?", tiles=len(picks),
               blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))
json.dump(key, open(KEY, "w"), indent=1, default=str)
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
assert all(r["glyph"] not in judged for r in rows)
print(len(pngs), "tiles, key rows", len(rows), "| roles", dict(collections.Counter(r["role"] for r in rows)),
      "| docs", dict(collections.Counter(r["doc"] for r in rows)))
