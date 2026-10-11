"""ROADMAP 2.87 round 2 (head_contact / one_stem_per_head): print crops WITH A RULER for the lane's own check. NOT product code.

For each subject (a glyph key in a re-adjudicated record) cut the print at 600 dpi around the head's page box, corner brackets on
the SUBJECT head only, a 100 px scale bar, and the base -> arm verdict in the caption. Frame control (it can fail): the bracket
must lie on ink or the crop is refused.

    python3 make_crops.py <pdf> <record.json> <name>=<glyph key> ... [--outdir DIR]
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tools.omr.hand_truth.session import _render
from tools.omr.staged.record_io import load_record

args = [a for a in sys.argv[1:]]
outdir = Path(__file__).resolve().parent / "crops"
if "--outdir" in args:
    i = args.index("--outdir"); outdir = Path(args[i + 1]); del args[i:i + 2]
pdf, rec = args[0], args[1]
subs = [a.split("=", 1) for a in args[2:]]
R = load_record(rec)["record"]
box_of = {}
for o in R["observations"]:
    if o["quantity"] == "glyph_box":
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b: box_of[o["subject"]] = b
pages = {}
for name, key in subs:
    pg = int(key.split("/")[1])
    if pg not in pages:
        im = _render(pdf, pg, 600)
        b = im.binary
        pages[pg] = np.where(b < 128 if b.dtype != bool else b, 0, 255).astype(np.uint8)
    pix = pages[pg]
    x0, y0, x1, y1 = box_of[key]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    W, H = 150, 230
    cx0, cy0 = int(cx - W), int(cy - H)
    crop = pix[max(0, cy0):int(cy + H), max(0, cx0):int(cx + W)]
    ink = (pix[int(y0):int(y1), int(x0):int(x1)] == 0).mean()
    if ink < 0.1:
        print("REFUSED (bracket not on ink)", name, key, round(float(ink), 3)); continue
    S = 3
    img = Image.fromarray(crop).convert("RGB").resize((crop.shape[1] * S, crop.shape[0] * S), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    ox, oy = max(0, cx0), max(0, cy0)
    bx0, by0, bx1, by1 = [(v - o) * S for v, o in ((x0 - 5, ox), (y0 - 5, oy), (x1 + 5, ox), (y1 + 5, oy))]
    L = 22
    for (px, py, sx, sy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        d.line([(px, py), (px + sx * L, py)], fill=(215, 0, 0), width=4)
        d.line([(px, py), (px, py + sy * L)], fill=(215, 0, 0), width=4)
    d.line([(10, img.height - 14), (10 + 100 * S, img.height - 14)], fill=(0, 0, 0), width=4)
    d.text((14, img.height - 34), "100 px (page, 600 dpi)", fill=(0, 0, 0))
    img.save(outdir / f"{name}.png"); print("wrote", name, key)
