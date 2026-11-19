"""ROADMAP 2.321 -- the blind tiles for Sean (research doc §7 questions 1 and 3), from the pool bars OUR look kept (look_pool.py's sheet).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/voice-line-of-time-2026-11 python3 benchmarks/voice-line-of-time-2026-11/tiles_final.py \
        DIR POOL.json TILE_DIR KEY.json

The code's pool (cuts.py: a split -- an up stem and a down stem at one place -- followed by single-stem notes, no "a 2" read) held 19 bars; by our
look (pool_sheet.png) most were not the case (one voice, chords, a part holding a long note under the other, another staff's marks). Kept by our look:
Q1 (split stems, then single stems, no "a 2"): pool numbers 3, 4, 5, 7. Q3 (after the split only the upper part goes on, nothing printed for the lower):
13, 14, 15. Drawn: up to 4 each, random.Random(2321001) / (2321003) from the kept list. Tile: one staff, the bar and its neighbours, one thin orange box
the bar's size, nothing else drawn; tiles 1-4 ask question 1, 5-8 question 3 (the README says which).
"""
import json
import random
import sys
from pathlib import Path

import cuts as C

D, POOL, TILES, KEY = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
KEEP = {1: [3, 4, 5, 7], 3: [13, 14, 15]}
SEEDS = {1: 2321001, 3: 2321003}
pool = {k["n"]: tuple(k["place"]) for k in json.load(open(POOL))}
rows = {C.place(r): r for r in C.load(D)}
TILES.mkdir(parents=True, exist_ok=True)
tiles, key = [], []
for q in (1, 3):
    picks = random.Random(SEEDS[q]).sample(KEEP[q], min(4, len(KEEP[q])))
    for n in picks:
        r = rows[pool[n]]
        cb = r["cell_box"]
        w = cb[2] - cb[0]
        x0 = (r["prev_box"] or [cb[0] - 0.8 * w])[0]
        x1 = (r["next_box"] or [0, 0, cb[2] + 0.8 * w])[2]
        top, bot, sp = C.staff_geo(r)
        heads = C.ubox([b for e in r["events"] for b in C.ev_boxes(e)])
        v = (max(top - 4 * sp, min(top, heads[1])) if heads else top, min(bot + 4 * sp, max(bot, heads[3])) if heads else bot)
        box = [cb[0], v[0] - 1.0 * sp, cb[2], v[1] + 1.0 * sp]
        crop, geo = C.cut(r, box, x0 - 0.3 * sp, x1 + 0.3 * sp, v)
        tiles.append(crop)
        key.append(dict(tile=len(tiles), question=q, plate=r["plate"], page=r["page"], system=r["system"], staff=r["staff"], cell=r["cell"],
                        staff_name_read=r["name"], pool_number=n, code_verdict=r["verdict"], written_red=r["red"], n_streams_written=r["n_streams"], **geo))
for n, t in enumerate(tiles, 1):
    t.save(TILES / ("tile_%02d.png" % n))
C.sheet(tiles, TILES / "sheet.png")
n1 = sum(1 for k in key if k["question"] == 1)
(TILES / "README.md").write_text(
    "# 2.321 -- two players on one staff, %d bars, one thin orange box each (the bar)\n\n" % len(tiles)
    + "Tiles 1-%d: the bar goes from split stems (one up, one down) back to single stems, with no \"a 2\" printed. "
    "After the split, are BOTH players playing the single-stem notes, or only ONE?\n\n" % n1
    + "Tiles %d-%d: after the split only the upper part's notes go on, and no rest is printed for the lower part. "
    "Is the lower player silent for the rest of the bar, and is that normal in this edition?\n\n" % (n1 + 1, len(tiles))
    + "Say \"cannot tell\" if so. Answer by tile number.\n")
KEY.write_text(json.dumps(dict(seeds=SEEDS, kept_by_our_look=KEEP, code_pool=len(pool), tiles=key), indent=1))
print("tiles", len(tiles))
