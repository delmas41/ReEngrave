"""ROADMAP 2.164 -- blind tiles for Sean: every box the flag refuses (`replay_2_164.py` `refused`, both plates) that he
has not judged (`benchmarks/acceptance/judged-tiles.json`), at most 20, plus 2 CONTROLS -- real tied-to notes at a
bar's start that the rule keeps (the lane's eye; Sean is asked the same question, so a control can fail). Shuffled
(seed 2164). One blue box (#1F6FEB) on the head box, "Tile N", nothing else of ours. Writes out/print/2.164-review/
tile_NN.png, manifest.json (question only), answers.json {}; the key goes to out/2.164/tiles-key.json, apart.
usage: tiles_2_164.py REPLAY_LITOLFF.json REPLAY_BRAHMS.json"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
CONTROLS = [("litolff", "glyph/2/1/1/14/3"), ("brahms", "glyph/16/0/11/3/7")]
QUESTION = "Is the mark in the blue box a note, or not a note?"
BLUE = (31, 111, 235)
OUT = Path("out/print/2.164-review")
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("tile_*.png"):
    old.unlink()
judged = set()
for t in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]:
    for s in [t.get("subject")] + list(t.get("subjects") or []):
        if s and t.get("doc"):
            judged.add((t["doc"], s))
boxes = {}
for doc in PDFS:
    for h in json.load(open("out/2.164/scan_%s.json" % doc))["hits"]:
        boxes[(doc, h["glyph"])] = (h["box"], h["sp"])
items = []
for doc, path in (("litolff", sys.argv[1]), ("brahms", sys.argv[2])):
    for g in json.load(open(path))["refused"]:
        if (doc, g) not in judged:
            items.append(dict(doc=doc, glyph=g, kind="refused"))
items = items[:20] + [dict(doc=d, glyph=g, kind="control") for d, g in CONTROLS]
for it in items:
    assert (it["doc"], it["glyph"]) not in judged, it
random.Random(2164).shuffle(items)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
except OSError:
    font = ImageFont.load_default()
pages = {}
key = []
for n, it in enumerate(items, 1):
    doc, g = it["doc"], it["glyph"]
    (x0b, y0b, x1b, y1b), sp = boxes[(doc, g)]
    pg = int(g.split("/")[1])
    if (doc, pg) not in pages:
        pages[(doc, pg)] = np.asarray(Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB"))
    a = pages[(doc, pg)]
    x0, y0 = int(max(x0b - 9 * sp, 0)), int(max(y0b - 6 * sp, 0))
    x1, y1 = int(min(x1b + 9 * sp, a.shape[1])), int(min(y1b + 6 * sp, a.shape[0]))
    s = 3 if doc == "litolff" else 1.6
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((int(crop.width * s), int(crop.height * s)), Image.LANCZOS)
    ImageDraw.Draw(crop).rectangle([(x0b - x0) * s - 4, (y0b - y0) * s - 4, (x1b - x0) * s + 4, (y1b - y0) * s + 4],
                                   outline=BLUE, width=4)
    tile = Image.new("RGB", (crop.width, crop.height + 60), "white")
    tile.paste(crop, (0, 60))
    ImageDraw.Draw(tile).text((10, 8), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, doc=doc, glyph=g, kind=it["kind"], page_box=[x0b, y0b, x1b, y1b]))
json.dump({"question": QUESTION, "colours": "blue box = the mark we are asking about",
           "tiles": ["tile_%02d.png" % k["n"] for k in key]}, open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))
json.dump(dict(question=QUESTION, seed=2164, tiles=key), open("out/2.164/tiles-key.json", "w"), indent=1)
print(len(key), "tiles;", sum(1 for k in key if k["kind"] == "control"), "controls")
