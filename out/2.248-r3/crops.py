"""Crop look (CLAUDE rule 7: check a count before it opens a lane): far heads whose ledger count abstained, by reason, from the
20261029-night frozen-sample slices, cut from the print with ONE neutral box. usage: crops.py PLATE REASON_PREFIX N OUT.png"""
import collections
import json
import random
import sys

from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR

plate, prefix, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
base = LR.slice_dir(plate, "20261029-night")
boxes = LR.glyph_boxes(json.loads(l) for l in open(base / "observations.jsonl") if '"glyph_box"' in l)
rows = []
for line in open(base / "abstentions.jsonl"):
    r = json.loads(line)
    if r.get("quantity") != "far_head_ledger_position":
        continue
    why = str((r.get("detail") or {}).get("ledger_reason"))
    if why.startswith(prefix) and r["subject"] in boxes:
        rows.append((r["subject"], why))
random.Random(7).shuffle(rows)
rows = rows[:n]
u = LR.PLATES[plate]["unit"]
tiles = []
cache = {}
for sub, why in sorted(rows, key=lambda t: boxes[t[0]]["page"]):
    pg = boxes[sub]["page"]
    if pg not in cache:
        cache.clear()
        cache[pg] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    b = boxes[sub]["box"]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    x0, y0, x1, y1 = int(cx - 4 * u), int(cy - 4 * u), int(cx + 4 * u), int(cy + 4 * u)
    c = cache[pg].crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(c).rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
    tiles.append(c.resize((360, 360)))
    print(len(tiles), sub, why[:50])
sheet = Image.new("RGB", (3 * 368, ((len(tiles) + 2) // 3) * 368), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 3) * 368, (i // 3) * 368))
sheet.save(out)
