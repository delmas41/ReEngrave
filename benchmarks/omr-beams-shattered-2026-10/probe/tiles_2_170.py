"""ROADMAP 2.170 blind tiles for Sean: notes `OMR_BEAM_REFUSED_OFF_THE_TIP` changes, plus 2 controls that can fail.

    python3 .../tiles_2_170.py REPLAYDIR      (ONE run writes tiles AND key; asserts one key row per PNG, same numbering)

Question on every tile: "What is the written value of the note in the blue box?"
Roles (KEY only, out/2.170/tiles-key.json; never drawn): changed -- narrowed OFF, decided by the rule ON (seeded, both plates, none
already judged); control -- a decided note the rule never touched (unchanged both arms). Each tile: the note's neighbourhood at 600
dpi, ONE blue box (#1F6FEB) on the note, a tile number. Nothing else of ours."""
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
RD = Path(sys.argv[1])
OUT, KEY = Path("out/print/2.170-review"), Path("out/2.170/tiles-key.json")
Q = "What is the written value of the note in the blue box?"
N_CHANGED = {"brahms": 5, "litolff": 5}
rnd = random.Random(2170)
J = json.load(open("benchmarks/acceptance/judged-tiles.json"))
judged = set()
for it in J["tiles"] if "tiles" in J else list(J.values())[0]:
    for s in (it.get("subjects") or [it.get("subject")]):
        if s:
            judged.add(s)
picks = []
boxes = {}
for doc in ("brahms", "litolff"):
    off = json.load(open(RD / ("%s.off.json" % doc)))["glyphs"]
    on = json.load(open(RD / ("%s.on.json" % doc)))["glyphs"]
    for o in json.load(open(RD / ("%s.on.record.json" % doc)))["observations"]:
        boxes[(doc, o["subject"])] = o["detail"]["bbox_page_px"]
    changed, ctl = [], []
    for g in sorted(on):
        a, b = off.get(g), on[g]
        if a is None or g in judged or (doc, g) not in boxes:
            continue
        if b["off_tip"] and a["outcome"] == "narrowed" and b["outcome"] == "decided":
            changed.append(g)
        elif (not b["off_tip"] and a == b and b["outcome"] == "decided" and not b["rest"]
              and b["written"] in (0.5, 1.0) and b["origin_reason"] in ("head_and_marks", "stem_tip_reads_no_beam")):
            ctl.append(g)
    rnd.shuffle(changed)
    rnd.shuffle(ctl)
    picks += [(doc, "changed", g, off[g], on[g]) for g in changed[:N_CHANGED[doc]]]
    picks += [(doc, "control", g, off[g], on[g]) for g in ctl[:1]]
    print(doc, "changed", len(changed), "controls", len(ctl))
rnd.shuffle(picks)
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("tile_*.png"):
    old.unlink()
KEY.parent.mkdir(parents=True, exist_ok=True)
BLUE = (31, 111, 235)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
pages, key = {}, []
for n, (doc, role, g, a, b) in enumerate(picks, 1):
    pg = int(g.split("/")[1])
    if (doc, pg) not in pages:
        pages[(doc, pg)] = np.asarray(Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB"))
    im = pages[(doc, pg)]
    x0b, y0b, x1b, y1b = boxes[(doc, g)]
    sp = 32.0 if doc == "brahms" else 18.0
    x0, y0 = int(max(x0b - 8 * sp, 0)), int(max(y0b - 7 * sp, 0))
    x1, y1 = int(min(x1b + 8 * sp, im.shape[1])), int(min(y1b + 7 * sp, im.shape[0]))
    k = 2 if doc == "brahms" else 3
    crop = Image.fromarray(im[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * k, crop.height * k), Image.LANCZOS)
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * k - 5, (y0b - y0) * k - 5, (x1b - x0) * k + 5, (y1b - y0) * k + 5],
                                   outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, doc=doc, role=role, glyph=g, bbox=boxes[(doc, g)], off=a, on=b))
json.dump(dict(question=Q, tiles=len(picks), blue="the note asked about", nothing_else_drawn=True,
               subjects={str(r["n"]): {"doc": r["doc"], "glyph": r["glyph"], "page_box": r["bbox"]} for r in key}),
          open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))
(OUT / "README.md").write_text(
    "# 2.170 tiles: %d blind tiles (Brahms 1 Breitkopf and Beethoven 5 Litolff, mvt 1)\n\nQuestion on every tile: %s\n\n"
    "Colours: BLUE = the one note asked about. Nothing else is drawn; the page is the scan as printed.\n"
    "Some tiles are ordinary notes we did not change (controls). Key (kept apart): out/2.170/tiles-key.json. "
    "answers.json is empty until Sean answers.\n" % (len(picks), Q))
json.dump(key, open(KEY, "w"), indent=1)
pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks), (len(pngs), len(rows), len(picks))
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
print(len(pngs), "tiles, key rows", len(rows), dict(collections.Counter((r["doc"], r["role"]) for r in rows)))
