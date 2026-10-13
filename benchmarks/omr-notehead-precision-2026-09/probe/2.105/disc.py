"""ROADMAP 2.105 (a): widest filled disc (staff spaces, RAW ink, threshold 180 as
GATHER's `head_letter_ink`) inside every filled-class notehead box of a page,
kept ones only, ascending. usage: disc.py RECORD MOVEMENT PAGE [PAGE...]"""
import sys

import cv2
import numpy as np

from lib105 import page_rgb, staff_spacing
from tools.omr.staged.readout import load_run, adjudicate_status

run = load_run(sys.argv[1])
mv = sys.argv[2]
sps = staff_spacing(run)
rows = []
for page in [int(p) for p in sys.argv[3:]]:
    rgb = page_rgb(mv, page)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) if rgb.ndim == 3 else rgb
    _, ink = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    dist = cv2.distanceTransform((ink > 0).astype(np.uint8), cv2.DIST_L2, 5)
    for g in run.glyphs.values():
        if g.page != page or not (g.cls or "").startswith("noteheadBlack") or g.box_page is None:
            continue
        if adjudicate_status(run, g)[0] == "refused":
            continue
        x0, y0, x1, y1 = (int(round(v)) for v in g.box_page)
        win = dist[y0:y1, x0:x1]
        if win.size == 0:
            continue
        sp = sps[g.staff_key]
        hs = run.standing(g.key, "head_stem", "ADJUDICATE")
        stem = "stem" if hs and hs.get("outcome") == "decided" else "nostem"
        rows.append((round(2 * float(win.max()) / sp, 2), g.key, round((x1 - x0) / sp, 2), round((y1 - y0) / sp, 2),
                     round(g.score or 0, 2), stem))
rows.sort()
print("n", len(rows))
low = [r for r in rows if r[0] < 0.9]
print("disc<0.9:", len(low), "of which no decided head_stem:", sum(1 for r in low if r[5] == "nostem"),
      "| all kept with no head_stem:", sum(1 for r in rows if r[5] == "nostem"))
for r in [r for r in low if r[5] == "nostem"][:40]:
    print(r)
for r in rows:
    if r[1] in ("glyph/2/1/0/6/6", "glyph/2/1/0/6/1"):
        print("SUBJECT", r)
print("quantiles", [rows[int(len(rows) * q)][0] for q in (0.05, 0.25, 0.5, 0.75)])
