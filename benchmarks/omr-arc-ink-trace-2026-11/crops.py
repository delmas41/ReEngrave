"""Trace-vs-ink crops for ROADMAP 2.272 step 1 (for LOOKING, not for Sean).

    python3 crops.py ON.record.json PDF PAGE OUTDIR [N] [--pick walked|capped|short]

Red = the part of the curve inside the detector boxes' x extent (what the OFF trace covered, +-0.5 sp); green = what the walk added; the stop
reason is printed on the crop. Page raster = the PDF rendered at 600 dpi (the pipeline's frame).
"""
import sys
import pathlib

import fitz
import numpy as np
from PIL import Image, ImageDraw

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1]); r = rec.get("record", rec)
pdf, page, out = sys.argv[2], int(sys.argv[3]), pathlib.Path(sys.argv[4])
n = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5].isdigit() else 6
pick = sys.argv[sys.argv.index("--pick") + 1] if "--pick" in sys.argv else "walked"
out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf)
pix = doc[page].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
img = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
cands = []
for o in r["observations"]:
    if o["quantity"] != "system_arc" or not o["subject"].startswith("glyph/%d/" % page):
        continue
    d = o["detail"]; sp = d["space_page_px"]
    it = d.get("ink_trace") or []
    bx0 = min(m["box_x"][0] for m in it); bx1 = max(m["box_x"][1] for m in it)
    left = min([(m.get("left") or {}).get("added_px", 0) for m in it] + [0]); right = max([(m.get("right") or {}).get("added_px", 0) for m in it] + [0])
    stops = [(m.get(s) or {}).get("stop") for m in it for s in ("left", "right")]
    score = max(
        max([(m.get("left") or {}).get("added_px", 0) for m in it]), max([(m.get("right") or {}).get("added_px", 0) for m in it])) / sp
    if pick not in ("walked", "short") and not any(s and s.startswith(pick) for s in stops):
        continue
    if pick == "short" and score >= 0.5:
        continue
    cands.append((score, o, bx0, bx1, stops))
cands.sort(key=lambda c: -c[0])
for k, (score, o, bx0, bx1, stops) in enumerate(cands[:n]):
    d = o["detail"]; sp = d["space_page_px"]; tr = d["trace"]
    xs = [t[0] for t in tr]; ys = [t[1] for t in tr] + [t[2] for t in tr]
    x0, x1 = int(min(xs) - 3 * sp), int(max(xs) + 3 * sp)
    y0, y1 = int(min(ys) - 3 * sp), int(max(ys) + 3 * sp)
    crop = img.crop((x0, y0, x1, y1)).copy()
    dr = ImageDraw.Draw(crop)
    for x, a, b in tr:
        col = (230, 0, 0) if bx0 - 0.5 * sp <= x <= bx1 + 0.5 * sp else (0, 170, 0)
        dr.line([(x - x0, a - y0 - 4), (x - x0, a - y0 - 1)], fill=col, width=1)   # a mark just above the stroke, never over it
    dr.text((4, 4), "%s score=%.1f sp stops=%s" % (o["subject"], score, stops), fill=(0, 0, 255))
    crop.save(out / ("%s_%02d.png" % (pick, k)))
    print(k, o["subject"], round(score, 1), stops, crop.size)
