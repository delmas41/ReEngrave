"""ROADMAP 2.314 r2 -- 12 blind tiles of notes whose written VALUE CHANGED, flag OFF vs ON (same tree), 6 per plate, seeded; and our own look sheets.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/plain-stemmed-2026-11 python3 benchmarks/plain-stemmed-2026-11/tiles_r2.py WORK OUT_DIR KEY.json [--look LOOK_DIR]

A changed note = a note host of the ON file whose glyph key is not written OFF, or is written with another type. One note per bar cell. One staff per tile, ONE thin orange box
from the head to the stem tip, nothing else drawn, every tile padded to one size, two per row. The stem tip is not in the slice rows (stems live in the cell frame), so the box
runs 3.5 staff spaces from the head the way the page says (page-facts: where two voices share a column the UPPER head takes the up stem, the LOWER the down stem; else the head's
place on the staff); the key says `stem_direction_from_*`. The key (outside the folder) says what OFF and ON wrote; the tile does not.
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image

from beam_crops import render, sheet

WORK, OUT, KEY = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
LOOK = Path(sys.argv[sys.argv.index("--look") + 1]) if "--look" in sys.argv else None
SLICE = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/%s/observations.jsonl"
SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))["plates"]


def hosts(plate, arm):
    return {h["rg"]: h for h in json.load(open("%s/%s.%s.symbols.json" % (WORK, plate, arm)))["hosts"] if h.get("rg") and h["kind"] == "note"}


def geometry(plate, keys):
    boxes, lines = {}, {}
    for l in open(SLICE % plate):
        if '"glyph_box"' in l or '"staff_lines"' in l:
            o = json.loads(l)
            if o["quantity"] == "glyph_box" and o["subject"] in keys:
                boxes[o["subject"]] = o["detail"]["bbox_page_px"]
            elif o["quantity"] == "staff_lines":
                p, s, st = o["subject"].split("/")[1:4]
                lines["%s/%s/%s" % (p, s, st)] = o["value"]
    return boxes, lines


def changed(plate):
    off, on = hosts(plate, "off"), hosts(plate, "on")
    out = []
    for k, h in on.items():
        if k not in off or off[k]["type"] != h["type"]:
            out.append((k, h, off.get(k)))
    return sorted(out, key=lambda c: c[0])


def item(plate, k, h, boxes, lines):
    p, s, st = k.split("/")[1:4]
    sl = lines["%s/%s/%s" % (p, s, st)]
    cy = (boxes[k][1] + boxes[k][3]) / 2
    # two voices: voice 1 = upper head = up stem, voice 2 = lower = down stem (page-facts 2026-11-14); a single voice: by the head's place
    if h.get("voice") == "2":
        d, how = "down", "stem_direction_from_voice_2"
    else:
        d = "up" if cy > (sl[0] + sl[4]) / 2 else "down"
        how = "stem_direction_from_head_place"
    return dict(plate=plate, page=int(p), system=int(s), staff=int(st), key=k, head_box=boxes[k], stem_box=None, stem_dir=[None, d]), how


def pad(im, size):
    c = Image.new("RGB", size, (255, 255, 255))
    c.paste(im, (0, 0))
    return c


rng = random.Random(2314201)
tiles, key, looks = [], [], []
for plate in ("litolff", "brahms"):
    ch = changed(plate)
    keys = {c[0] for c in ch}
    boxes, lines = geometry(plate, keys)
    ch = [c for c in ch if c[0] in boxes]
    bycell = {}
    for c in ch:
        bycell.setdefault(tuple(c[0].split("/")[1:5]), []).append(c)
    one = [rng.choice(v) for _, v in sorted(bycell.items())]
    one = sorted(one, key=lambda c: c[0])
    print(plate, "changed notes", len(ch), "cells", len(one))
    insample = [c for c in one if int(c[0].split("/")[1]) in SAMPLE[plate]["pages"]]
    pick = random.Random(2314202).sample(insample, min(6, len(insample)))
    if LOOK is not None:                       # our own look: 24 seeded changed notes (the first 24 of a seeded order), numbered
        lk = random.Random(2314203).sample(one, min(24, len(one)))
        for n, (k, h, o) in enumerate(lk, 1):
            it, how = item(plate, k, h, boxes, lines)
            im, _ = render(it, dict(staff_lines=lines), 560)
            looks.append((plate, n, k, h["type"], (o or {}).get("type"), im))
    for k, h, o in pick:
        it, how = item(plate, k, h, boxes, lines)
        crop, geo = render(it, dict(staff_lines=lines), 1400)
        tiles.append(crop)
        key.append(dict(plate=plate, page=it["page"], key=k, off=(o or {}).get("type") or "not written", on=h["type"], on_blue=h.get("blue"), voice=h.get("voice"), stem_how=how, **geo))
order = list(range(len(tiles)))
random.Random(2314204).shuffle(order)
size = (max(t.width for t in tiles), max(t.height for t in tiles))
tiles = [pad(tiles[i], size) for i in order]
key = [dict(tile=n, **key[i]) for n, i in enumerate(order, 1)]
OUT.mkdir(parents=True, exist_ok=True)
for n, t in enumerate(tiles, 1):
    t.save(OUT / ("tile_%02d.png" % n))
sheet(tiles, OUT / "sheet.png", 2)
json.dump(key, open(KEY, "w"), indent=1)
print("tiles", len(tiles), "size", size)
if LOOK is not None:
    LOOK.mkdir(parents=True, exist_ok=True)
    json.dump([l[:5] for l in looks], open(LOOK / "look_key.json", "w"))
    for plate in ("litolff", "brahms"):
        ls = [l for l in looks if l[0] == plate]
        for s in range(0, len(ls), 6):
            sheet([l[5] for l in ls[s:s + 6]], LOOK / ("%s_%d.png" % (plate, s // 6 + 1)), 2, ["%d %s -> %s" % (l[1], l[4] or "-", l[3]) for l in ls[s:s + 6]])
