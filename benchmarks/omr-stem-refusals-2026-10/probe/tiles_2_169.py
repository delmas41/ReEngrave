"""ROADMAP 2.169 blind tiles for Sean: notes whose stem `OMR_STEM_PAIR_AT_HEAD` newly finds, plus controls that can fail.

    python3 .../tiles_2_169.py REPLAY_LITOLFF.json     (writes ONE set, tiles AND key, in this run; asserts one key row per PNG)

Question on every tile: "What is the written value of the note in the blue box (4, dotted 4, 8, 16 ...)?" (the OUTCOME, not our stem).
Roles (the KEY only, out/2.169/tiles-key.json; never drawn):
  changed_value    -- a head the arm connects (head_stem no_stem -> one_stem) whose standing duration verdict changes
  changed_same     -- connected, verdict the same decided value either way
  untouched_ctl    -- a decided note in a changed cell whose head_stem is the same both arms (can fail: our reading may be wrong)
  interior_ctl     -- a decided note in an UNchanged cell
Each tile: the note's neighbourhood at 600 dpi, ONE blue box (#1F6FEB) on the note asked about, a tile number. Nothing else of ours."""
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec as RC  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
REC = RC.LIB + "beethoven5-litolff-mvt1-whole-20261016-night.record.json"
OUT, KEY = Path("out/print/2.169-review"), Path("out/2.169/tiles-key.json")
Q = "What is the written value of the note in the blue box (4, dotted 4, 8, 16 ...)?"
rnd = random.Random(2169)
res = json.load(open(sys.argv[1]))["readings"]
# Sean's 2.167 stem tiles (answered): not asked again
ANSWERED = {"glyph/4/0/2/0/7", "glyph/6/0/1/8/6", "glyph/16/1/8/11/1", "glyph/1/0/8/0/7", "glyph/13/1/2/0/10", "glyph/13/1/6/10/11",
            "glyph/16/1/7/5/7", "glyph/6/0/0/9/1", "glyph/6/0/3/3/7", "glyph/4/1/7/7/8", "glyph/7/0/10/0/9"}


def kind(r):
    c, a = r["control"], r["arm"]
    if not c or not a or not r["in_changed_cell"]:
        return None
    if r["hs_control"] and r["hs_control"][1] == "no_stem" and r["hs_arm"] and r["hs_arm"][0] == "decided":
        if (c["outcome"], c["written"]) != (a["outcome"], a["written"]):
            return "changed_value"
        return "changed_same"
    return None


groups = collections.defaultdict(list)
for g, r in res.items():
    if g in ANSWERED or int(g.split("/")[-1]) >= 100000 or not r.get("control") or not r.get("arm"):
        continue
    k = kind(r)
    if k:
        groups[k].append(g)
    elif r["in_changed_cell"] and r["control"]["outcome"] == "decided" and r["hs_control"] == r["hs_arm"] and r["hs_arm"] and r["hs_arm"][0] == "decided":
        groups["untouched_ctl"].append(g)
    elif not r["in_changed_cell"] and r["control"]["outcome"] == "decided" and r["control"]["written"] in (0.5, 1.0, 0.25):
        groups["interior_ctl"].append(g)
for v in groups.values():
    v.sort()
    rnd.shuffle(v)
print({k: len(v) for k, v in groups.items()})
picks = ([("changed_value", g) for g in groups["changed_value"][:5]] + [("changed_same", g) for g in groups["changed_same"][:3]]
         + [("untouched_ctl", g) for g in groups["untouched_ctl"][:2]] + [("interior_ctl", g) for g in groups["interior_ctl"][:1]])
picks = picks[:12]
rnd.shuffle(picks)
want = {g for _r, g in picks}
bbox = {}
with RC.lock():
    for o in RC.items(REC, "observations"):
        if o["quantity"] == "glyph_box" and o["subject"] in want:
            bbox[o["subject"]] = o["detail"]["bbox_page_px"]
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("tile_*.png"):
    old.unlink()
KEY.parent.mkdir(parents=True, exist_ok=True)
SP, BLUE = 33.0, (31, 111, 235)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
except OSError:
    font = ImageFont.load_default()
pages, key = {}, []
for n, (role, g) in enumerate(picks, 1):
    pg = int(g.split("/")[1])
    if pg not in pages:
        pages[pg] = np.asarray(Image.fromarray(render_page(PDF, pg, dpi=600).rgb).convert("RGB"))
    a = pages[pg]
    x0b, y0b, x1b, y1b = bbox[g]
    x0, y0 = int(max(x0b - 6 * SP, 0)), int(max(y0b - 5 * SP, 0))
    x1, y1 = int(min(x1b + 6 * SP, a.shape[1])), int(min(y1b + 5 * SP, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * 2 - 4, (y0b - y0) * 2 - 4, (x1b - x0) * 2 + 4, (y1b - y0) * 2 + 4], outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    r = res[g]
    key.append(dict(n=n, role=role, glyph=g, bbox=bbox[g], control=r["control"], arm=r["arm"], hs_control=r["hs_control"], hs_arm=r["hs_arm"]))
json.dump(dict(question=Q, tiles=len(picks), blue="the note asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))
(OUT / "README.md").write_text(
    "# 2.169 stem tiles: %d blind tiles (Litolff Beethoven 5, mvt 1)\n\nQuestion on every tile: %s\n\n"
    "Colours: BLUE = the one note asked about. Nothing else is drawn; the page is the scan as printed.\n"
    "Some tiles are ordinary notes we did not change (controls). Key (kept apart): out/2.169/tiles-key.json. answers.json is empty until Sean answers.\n"
    % (len(picks), Q))
json.dump(key, open(KEY, "w"), indent=1)
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
print(len(pngs), "tiles, key rows", len(rows), dict(collections.Counter(r["role"] for r in rows)))
