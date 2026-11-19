"""ROADMAP 2.321 -- OUR look (rule 7) at every population bar kept as flag OFF that is written RED: what does the page show?

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/voice-line-of-time-2026-11 python3 benchmarks/voice-line-of-time-2026-11/look_red.py DIR OUT_DIR

Bar crop (thin orange box the bar's size, neighbours either side), labelled with the code's reason; one sheet for both plates.
"""
import json
import sys
from pathlib import Path

import cuts as C

D, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
crops, labels = [], []
for plate in ("litolff", "brahms"):
    p = D / ("%s.json" % plate)
    if not p.exists():
        continue
    for r in sorted(json.load(open(p))["rows"], key=C.place):
        if not r["red"] or not r["cell_box"]:
            continue
        cb = r["cell_box"]
        w = cb[2] - cb[0]
        x0 = (r["prev_box"] or [cb[0] - 0.8 * w])[0]
        x1 = (r["next_box"] or [0, 0, cb[2] + 0.8 * w])[2]
        top, bot, sp = C.staff_geo(r)
        crop, _ = C.cut(r, [cb[0], top - 1.0 * sp, cb[2], bot + 1.0 * sp], x0, x1, None, width=700)
        crops.append(crop)
        labels.append("%d %s p%d s%d st%d c%d %s" % (len(crops), plate[:3], r["page"], r["system"], r["staff"], r["cell"], (r["verdict"] or "split")[-30:]))
C.sheet(crops, OUT / "red_sheet.png", labels, cols=3)
print(len(crops))
