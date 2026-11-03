"""2.255 census crops: per plate and abstention reason, up to N far heads the record reads toward NO other staff (the
true reading failures), cut from the print with one thin box, a sheet per reason.  usage: census_crops.py OUT_DIR N"""
import collections
import json
import os
import random
import sys

from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR

out, n = sys.argv[1], int(sys.argv[2])
os.makedirs(out, exist_ok=True)
for plate in ("litolff", "brahms"):
    base = LR.slice_dir(plate, "20261029-night")
    boxes = LR.glyph_boxes(json.loads(l) for l in open(base / "observations.jsonl") if '"glyph_box"' in l)
    ab = {}
    for l in open(base / "abstentions.jsonl"):
        r = json.loads(l)
        if r.get("quantity") == "far_head_ledger_position":
            w = str((r.get("detail") or {}).get("ledger_reason"))
            ab[r["subject"]] = "not_a_note" if w.startswith("not_a_note") else w.split(" ")[0]
    other = set()
    for l in open(base / "observations.jsonl"):
        if '"far_head_owner_ledger"' in l:
            r = json.loads(l)
            p = r["subject"].split("/")
            if r["subject"] in ab and r["detail"].get("candidate") != "staff/%s/%s/%s" % (p[1], p[2], p[3]):
                other.add(r["subject"])
    by = collections.defaultdict(list)
    for s, w in ab.items():
        if s not in other and s in boxes and w != "not_a_note":
            by[w].append(s)
    u = LR.PLATES[plate]["unit"]
    pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
    pages = {}
    for w, subs in by.items():
        random.Random(2255).shuffle(subs)
        tiles = []
        for s in subs[:n]:
            pg = boxes[s]["page"]
            if pg not in pages:
                pages[pg] = Image.fromarray(render_page(pdf, pg, dpi=600).rgb).convert("RGB")
            b = boxes[s]["box"]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            x0, y0 = int(cx - 3 * u), int(cy - 6 * u)
            c = pages[pg].crop((x0, y0, int(cx + 3 * u), int(cy + 6 * u))).copy()
            ImageDraw.Draw(c).rectangle([b[0] - x0 - 2, b[1] - y0 - 2, b[2] - x0 + 2, b[3] - y0 + 2], outline=(255, 140, 0), width=1)
            tiles.append(c.resize((c.width * 2, c.height * 2)))
        if not tiles:
            continue
        W, H = tiles[0].width, tiles[0].height
        sheet = Image.new("RGB", (len(tiles) * (W + 8), H), "white")
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * (W + 8), 0))
        sheet.save(os.path.join(out, "%s_%s.png" % (plate, w)))
        print(plate, w, len(subs), "->", subs[:n])
