"""ROADMAP 2.321 -- OUR look (rule 7, not truth) at the population itself: does the bar show two players at one moment at all?

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/voice-line-of-time-2026-11 python3 benchmarks/voice-line-of-time-2026-11/look_pop.py DIR OUT_DIR

Per plate: 8 bars the flag writes split and 8 it keeps as flag OFF, random.Random(2321005) from the population sorted by place. Bar crop, one thin
box the bar's size, the neighbours either side; orange boxes also round the heads the code paired at one place (the split columns), so we can say
whether the pair is two players at one moment. Labels under each crop; a sheet per plate.
"""
import json
import random
import sys
from pathlib import Path

from PIL import ImageDraw

import cuts as C

D, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
BLUE = (30, 110, 235)
for plate in ("litolff", "brahms"):
    p = D / ("%s.json" % plate)
    if not p.exists():
        continue
    rows = sorted(json.load(open(p))["rows"], key=C.place)
    rng = random.Random(2321005)
    split = [r for r in rows if r["verdict"] is None and r["cell_box"]]
    off = [r for r in rows if r["verdict"] is not None and r["cell_box"]]
    pick = rng.sample(split, min(8, len(split))) + rng.sample(off, min(8, len(off)))
    crops, labels, key = [], [], []
    for n, r in enumerate(pick, 1):
        cb = r["cell_box"]
        w = cb[2] - cb[0]
        x0 = (r["prev_box"] or [cb[0] - 0.8 * w])[0]
        x1 = (r["next_box"] or [0, 0, cb[2] + 0.8 * w])[2]
        top, bot, sp = C.staff_geo(r)
        box = [cb[0], top - 1.0 * sp, cb[2], bot + 1.0 * sp]
        crop, geo = C.cut(r, box, x0, x1, None, width=900)
        d = ImageDraw.Draw(crop)
        X0, Y0 = geo["crop_origin"]
        s = geo["scale"]
        pairs = [(c["i"], c["j"]) for c in r["stem_pair_columns"]] + [tuple(x) for x in r.get("divisi_idx") or ()]
        for i, j in pairs:
            b = C.ubox(C.ev_boxes(r["events"][i]) + C.ev_boxes(r["events"][j]))
            if b:
                d.rectangle([(b[0] - X0) * s - 3, (b[1] - Y0) * s - 3, (b[2] - X0) * s + 3, (b[3] - Y0) * s + 3], outline=BLUE, width=2)
        crops.append(crop)
        labels.append("%d p%d s%d st%d c%d %s%s" % (n, r["page"], r["system"], r["staff"], r["cell"], r["verdict"] or "SPLIT", " RED" if r["red"] else ""))
        key.append(dict(n=n, place=C.place(r), verdict=r["verdict"], red=r["red"], n_pairs=len(pairs)))
    C.sheet(crops, OUT / ("pop_%s.png" % plate), labels, cols=2)
    (OUT / ("pop_%s.json" % plate)).write_text(json.dumps(key, indent=1))
    print(plate, len(crops))
