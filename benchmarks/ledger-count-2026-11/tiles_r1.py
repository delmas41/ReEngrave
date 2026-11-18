"""ROADMAP 2.312 job 1 -- 12 blind tiles: "which staff does the boxed note belong to, and how many ledger lines are printed between it and that staff?"

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/ledger-count-2026-11 python3 benchmarks/ledger-count-2026-11/tiles_r1.py HEADS_ALL.json HEADS_P.json OUTDIR KEY.json [SEED=2312]

Pool: Litolff real heads (not refused as a head) on pages 4, 8, 10 where the ledger finder saw no line (`no_rungs`, `no_line_at_the_note_box`), not moved by the ledger lines.
12 drawn at random (seeded), NOT by cause. Tile: the page as scanned (grey), the staff above and the staff below the head in full, 30 spaces wide, one thin orange box, only the tile number.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from checksheet import page_image
from ledger_heights import load
from rung_why import real_refused
from tools.omr.annotate import ledger_grid as lg

allh = json.load(open(sys.argv[1]))
ph = {h["key"]: h for h in json.load(open(sys.argv[2]))}
out = Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 2312
rows, _ = load("litolff")
sl = rows["staff_lines"]
PX, W, H = 26.0, 800, 900
pool = sorted((h for h in allh if real_refused(h) and int(h["key"].split("/")[1]) in (4, 8, 10)), key=lambda h: h["key"])
print("pool", len(pool))
random.Random(seed).shuffle(pool)


def geometry(h):
    p, s, st = (int(x) for x in h["key"].split("/")[1:4])
    own = sl["staff/%d/%d/%d" % (p, s, st)]["value"]
    sp = (own[4] - own[0]) / 4.0
    b = h["box"]
    cy = (b[1] + b[3]) / 2
    staves = [(k, r["value"]) for k, r in sl.items() if int(k.split("/")[1]) == p]
    above = max([(v[4], k, v) for k, v in staves if v[4] < cy], default=None)
    below = min([(v[0], k, v) for k, v in staves if v[0] > cy], default=None)
    return p, own, sp, b, cy, above, below


chosen = []
for h in pool:
    p, own, sp, b, cy, above, below = geometry(h)
    if above is None or below is None:
        continue
    top, bot = above[2][0] - 2.0 * sp, below[2][4] + 2.0 * sp
    if (bot - top) / sp * PX > 1400:
        continue
    chosen.append(h)
    if len(chosen) == 12:
        break
H = 600
for h in chosen:
    p, own, sp, b, cy, above, below = geometry(h)
    H = max(H, int((below[2][4] + 2.0 * sp - (above[2][0] - 2.0 * sp)) / sp * PX) + 2)
print("tile height", H)
tiles, key = [], []
for i, h in enumerate(chosen, 1):
    p, own, sp, b, cy, above, below = geometry(h)
    img = page_image("litolff", p)
    cx = (b[0] + b[2]) / 2
    k = PX / sp
    half = (W / k) / 2
    top, bot = above[2][0] - 2.0 * sp, below[2][4] + 2.0 * sp
    x0, y0 = int(cx - half), int(top)
    crop = img.crop((x0, y0, int(cx + half), int(bot))).convert("L").convert("RGB")
    d = ImageDraw.Draw(crop)
    d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
    crop = crop.resize((W, int(crop.height * k)))
    t = Image.new("RGB", (W, H), "white")
    t.paste(crop, (0, 0))
    ImageDraw.Draw(t).text((6, 4), str(i), fill=(0, 0, 0))
    t.save(out / ("tile_%02d.png" % i))
    tiles.append(t)
    gray = np.array(img.convert("L"))
    above_side = cy < own[0]
    found = lg.measure_ledger_rungs(gray, [float(v) for v in own], cx, head_y=cy, head_box_x=(b[0], b[2]),
                                    collapse_edges_box=tuple(b)).get("above" if above_side else "below", [])
    other = min(abs(cy - v) for k2, r2 in sl.items() if int(k2.split("/")[1]) == p and r2["value"] != own for v in (r2["value"][0], r2["value"][4])) / sp
    reason = h["ledger_refusal"]["detail"].get("ledger_reason", "?").split(" (")[0]
    group = ("head touches or sits in the first space of another staff (nearest other staff edge %.1f sp)" % other) if other < 1.3 else reason
    w = (ph.get(h["key"]) or {}).get("written")
    key.append(dict(tile=i, glyph=h["key"], cause_group=group, reason_word=reason,
                    owner_staff_as_we_have_it="staff/" + "/".join(h["key"].split("/")[1:4]),
                    position_half_steps_from_geometry=round(h["geom"], 2), pitch_verdict=(h["pitch"] or {}).get("value"),
                    pitch_written="dropped (verdict, not in the exported file)" if w is None else "written %s%s" % (w["pitch"], " blue" if w["blue"] else " plain"),
                    finder_line_count_raw_ink=len(found), box=[round(v, 1) for v in b]))
cols = 2
sheet = Image.new("RGB", (cols * (W + 8) + 8, ((len(tiles) + 1) // 2) * (H + 8) + 8), (200, 200, 200))
for j, t in enumerate(tiles):
    sheet.paste(t, (8 + (j % cols) * (W + 8), 8 + (j // cols) * (H + 8)))
sheet.save(out / "sheet.png")
json.dump(key, open(sys.argv[4], "w"), indent=1)
print(len(tiles), "tiles")
