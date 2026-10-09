"""Blind crops of arcs: the PDF cut at the gather's dpi around an arc and its two
end notes, a red corner bracket on the ARC's box, nothing else drawn.

usage: crop_arcs.py record.json rows.json outdir tag [--blind] sub [sub ...]
 - record.json gives pdf + dpi (readout.load_run)
 - rows.json (replay rows) gives each arc's page box and the two end heads
   (rule.two_note.start / stop glyph keys) -> the crop window.
Control: the fraction of dark pixels inside the bracketed box is printed; a
box shifted 300 px must read far lower or the frame is not the arc.
"""
import json
import os
import sys

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tools.omr.staged import readout

args = [a for a in sys.argv[1:] if not a.startswith("--")]
rec_path, rows_path, outdir, tag = args[:4]
subs = args[4:]
blind = "--blind" in sys.argv
run = readout.load_run(rec_path)
pdf, dpi = run.pdf, run.dpi or 600
doc = fitz.open(pdf)
rows = {r["sub"]: r for r in json.load(open(rows_path))}
os.makedirs(outdir, exist_ok=True)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
manifest = []


def dark_fraction(im, box):
    a = np.asarray(im.convert("L"))
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    sub = a[y0:y1, x0:x1]
    return float((sub < 128).mean()) if sub.size else 0.0


for i, s in enumerate(subs, 1):
    r = rows[s]
    x0, y0, x1, y1 = r["box"]
    boxes = [(x0, y0, x1, y1)]
    tn = (r.get("rule") or {}).get("two_note") or {}
    for key in (tn.get("start"), tn.get("stop")):
        if key and key in run.glyphs:
            boxes.append(tuple(run.glyphs[key].box_page))
    ux0 = min(b[0] for b in boxes); uy0 = min(b[1] for b in boxes)
    ux1 = max(b[2] for b in boxes); uy1 = max(b[3] for b in boxes)
    padx, pady = 120, 110
    page = int(s.split("/")[1])
    clip = fitz.Rect((ux0 - padx) * 72 / dpi, (uy0 - pady) * 72 / dpi,
                     (ux1 + padx) * 72 / dpi, (uy1 + pady) * 72 / dpi)
    pix = doc[page].get_pixmap(dpi=dpi, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ox, oy = clip.x0 * dpi / 72, clip.y0 * dpi / 72
    fb = (x0 - ox, y0 - oy, x1 - ox, y1 - oy)
    ctrl = (x0 - ox + 300, y0 - oy, x1 - ox + 300, y1 - oy)
    frac, cfrac = dark_fraction(im, fb), dark_fraction(im, ctrl)
    d = ImageDraw.Draw(im)
    a, b, c_, e = fb[0] - 8, fb[1] - 8, fb[2] + 8, fb[3] + 8
    L, w = 18, 5
    for (px, py, sx, sy) in ((a, b, 1, 1), (c_, b, -1, 1), (a, e, 1, -1), (c_, e, -1, -1)):
        d.line([(px, py), (px + sx * L, py)], fill=(220, 0, 0), width=w)
        d.line([(px, py), (px, py + sy * L)], fill=(220, 0, 0), width=w)
    top = Image.new("RGB", (im.width, 46), "white")
    label = f"{tag} {i}" if blind else f"{tag} {i}  {s}  det={r['det']} ours={r['kind']} {r['reason']}"
    ImageDraw.Draw(top).text((10, 8), label, fill="black", font=font)
    out = Image.new("RGB", (im.width, im.height + 46), "white")
    out.paste(top, (0, 0)); out.paste(im, (0, 46))
    name = f"{tag}_{i:02d}.png"
    out.save(os.path.join(outdir, name))
    manifest.append({"n": i, "tile": name, "subject": s, "pdf_page_index": page,
                     "arc_box_page_px": [round(v, 1) for v in r["box"]], "dpi": dpi,
                     "frame_ink_fraction": round(frac, 3),
                     "control_shifted_300px_ink_fraction": round(cfrac, 3),
                     "question": "Is the bracketed arc a tie or a slur?",
                     "VERDICT_none_yet": None})
    print(name, s, "ink in frame %.3f vs shifted control %.3f" % (frac, cfrac))
json.dump({"roadmap_item": "2.75", "pdf": os.path.basename(pdf), "dpi": dpi, "arcs": manifest},
          open(os.path.join(outdir, f"{tag}-manifest.json"), "w"), indent=1)
