"""ROADMAP 2.321 -- OUR look (rule 7) at the "divisi" pairs that are ONE head written as an up-stem event and a down-stem event (no stem id):
does the page show a stem each way on that head (two players on one note) or one stem?

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/voice-line-of-time-2026-11 python3 benchmarks/voice-line-of-time-2026-11/look_twins.py DIR OUT_DIR

Up to 16 heads per plate, random.Random(2321007) from the twins sorted by place; one thin orange box on the head; 7 staff spaces up and down.
"""
import json
import random
import sys
from pathlib import Path

import cuts as C

D, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
for plate in ("litolff", "brahms"):
    p = D / ("%s.json" % plate)
    if not p.exists():
        continue
    rows = sorted(json.load(open(p))["rows"], key=C.place)
    twins = []
    for r in rows:
        for i, j in r.get("divisi_idx") or ():
            a = {h["glyph"] for h in r["events"][i]["heads"]}
            b = {h["glyph"] for h in r["events"][j]["heads"]}
            for g in sorted(a & b):
                h = next(h for h in r["events"][i]["heads"] if h["glyph"] == g)
                if h.get("page_box"):
                    twins.append((r, g, h["page_box"]))
    pick = random.Random(2321007).sample(twins, min(16, len(twins)))
    crops, labels, key = [], [], []
    for n, (r, g, b) in enumerate(pick, 1):
        _, _, sp = C.staff_geo(r)
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        crop, geo = C.cut(r, [b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2], cx - 6 * sp, cx + 6 * sp, (cy - 6 * sp, cy + 6 * sp), width=420)
        crops.append(crop)
        labels.append("%d %s" % (n, g))
        key.append(dict(n=n, glyph=g, place=C.place(r), verdict=r["verdict"], red=r["red"]))
    if crops:
        C.sheet(crops, OUT / ("twins_%s.png" % plate), labels, cols=4)
    (OUT / ("twins_%s.json" % plate)).write_text(json.dumps(dict(twins=len(twins), drawn=len(key), items=key), indent=1))
    print(plate, "twin heads", len(twins), "drawn", len(key))
