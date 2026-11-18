"""ROADMAP 2.314 -- 12 blind tiles of notes whose written value CHANGED with OMR_TWO_STEMS_TWO_NOTES (OFF refused, ON writes), seeded, both plates.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/plain-stemmed-2026-11 python3 benchmarks/plain-stemmed-2026-11/tiles.py \
        SCRATCH   OUT_DIR   KEY.json

SCRATCH holds p314/pop.json (the refused-note rows), p314/x/{lit,bra}.f{0,1}.json (the record exported flag OFF / ON), and 2311/{lit,bra}-a.extra.json.
A changed note = a head whose fate is not written OFF and written ON. Drawn from the frozen-sample pages first (the pages `lane_report` measures), then the
rest. One staff per tile, whole stem, ONE thin orange box head-to-stem-tip, nothing else drawn, same size, two per row. The key (outside the folder) says what
OFF and ON wrote; the tile does not.
"""
import json
import random
import sys
from pathlib import Path

from beam_crops import render, sheet

S, OUT, KEY = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))["plates"]
rows = {}
for plate, tag in (("litolff", "lit"), ("brahms", "bra")):
    f0 = json.load(open(f"{S}/p314/x/{tag}.f0.json"))
    f1 = json.load(open(f"{S}/p314/x/{tag}.f1.json"))
    pop = json.load(open(f"{S}/p314/pop.json"))[plate]
    extra = json.load(open(f"{S}/2311/{'lit' if tag == 'lit' else 'bra'}-a.extra.json"))
    ch = []
    for r in pop:
        k = r["it"]["key"]
        if not f0["glyphs"][k]["fate"].startswith("written") and f1["glyphs"][k]["fate"].startswith("written"):
            w = [x for x in f1["written"] if x.get("rg") == k]
            ch.append((r["it"], w[0] if w else None, f0["glyphs"][k]["fate"]))
    ch = sorted(ch, key=lambda c: c[0]["key"])
    rr = random.Random(2314003)
    bycell = {}
    for c in ch:                                   # one note per bar cell: two tiles of one pair are one question
        bycell.setdefault(tuple(c[0]["key"].split("/")[1:5]), []).append(c)
    ch = [rr.choice(v) for _, v in sorted(bycell.items())]
    rows[plate] = (ch, extra)
tiles, key = [], []
for plate in ("litolff", "brahms"):
    ch, extra = rows[plate]
    insample = [c for c in ch if c[0]["page"] in SAMPLE[plate]["pages"]]
    rest = [c for c in ch if c not in insample]
    rng = random.Random(2314001)
    pick = rng.sample(insample, min(6, len(insample)))
    if len(pick) < 6:
        pick += rng.sample(rest, min(6 - len(pick), len(rest)))
    for it, w, fate in pick:
        it = dict(it, plate=plate)
        crop, geo = render(it, extra)
        tiles.append(crop)
        key.append(dict(plate=plate, page=it["page"], key=it["key"], off=fate, on_type=(w or {}).get("type"), on_dots=len((w or {}).get("sub", {}).get("dot", []) or []),
                        on_blue=(w or {}).get("blue"), in_frozen_sample=it["page"] in SAMPLE[plate]["pages"], **geo))
random.Random(2314002).shuffle(order := list(range(len(tiles))))
tiles = [tiles[i] for i in order]
key = [dict(tile=n, **key[i]) for n, i in enumerate(order, 1)]
OUT.mkdir(parents=True, exist_ok=True)
for n, t in enumerate(tiles, 1):
    t.save(OUT / ("tile_%02d.png" % n))
sheet(tiles, OUT / "sheet.png", 2)
(OUT / "README.md").write_text("# 12 notes, one thin orange box each (head to stem tip)\n\nQuestion for every tile: what is the boxed note's value (half, quarter, dotted quarter, ...)? "
                               "Say \"cannot tell\" or \"not a note\" if so. Answer by tile number.\n")
Path(KEY).write_text(json.dumps(key, indent=1, default=str))
print("tiles", len(tiles), "in frozen sample", sum(1 for k in key if k["in_frozen_sample"]))
