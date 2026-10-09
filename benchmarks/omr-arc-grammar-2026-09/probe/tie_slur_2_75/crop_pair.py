"""Blind crop of a STACKED pair: the PDF around two arcs, each bracketed and
lettered A (upper) / B (lower); nothing else drawn.  The question: which arc
is the tie?

usage: crop_pair.py record.json rows.json outdir tag [--blind] subUpper subLower [subUpper subLower ...]
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
big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
manifest = []


def ink(im, box):
    a = np.asarray(im.convert("L"))
    x0, y0, x1, y1 = [int(v) for v in box]
    sub = a[max(0, y0):y1, max(0, x0):x1]
    return float((sub < 128).mean()) if sub.size else 0.0


for n in range(0, len(subs), 2):
    sa, sb = subs[n], subs[n + 1]
    ra, rb = rows[sa], rows[sb]
    if (ra["box"][1] + ra["box"][3]) > (rb["box"][1] + rb["box"][3]):
        sa, sb, ra, rb = sb, sa, rb, ra
    ux0 = min(ra["box"][0], rb["box"][0]); uy0 = min(ra["box"][1], rb["box"][1])
    ux1 = max(ra["box"][2], rb["box"][2]); uy1 = max(ra["box"][3], rb["box"][3])
    page = int(sa.split("/")[1])
    clip = fitz.Rect((ux0 - 130) * 72 / dpi, (uy0 - 130) * 72 / dpi,
                     (ux1 + 130) * 72 / dpi, (uy1 + 130) * 72 / dpi)
    pix = doc[page].get_pixmap(dpi=dpi, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ox, oy = clip.x0 * dpi / 72, clip.y0 * dpi / 72
    d = ImageDraw.Draw(im)
    frames = {}
    for letter, r in (("A", ra), ("B", rb)):
        x0, y0, x1, y1 = r["box"]
        fb = (x0 - ox, y0 - oy, x1 - ox, y1 - oy)
        frames[letter] = (round(ink(im, fb), 3), round(ink(im, (fb[0] + 300, fb[1], fb[2] + 300, fb[3])), 3))
        a, b, c_, e = fb[0] - 8, fb[1] - 8, fb[2] + 8, fb[3] + 8
        L, w = 16, 4
        for (px, py, sx, sy) in ((a, b, 1, 1), (c_, b, -1, 1), (a, e, 1, -1), (c_, e, -1, -1)):
            d.line([(px, py), (px + sx * L, py)], fill=(220, 0, 0), width=w)
            d.line([(px, py), (px, py + sy * L)], fill=(220, 0, 0), width=w)
        d.text((a - 34, (b + e) / 2 - 20), letter, fill=(220, 0, 0), font=big)
    top = Image.new("RGB", (im.width, 46), "white")
    k = n // 2 + 1
    label = f"{tag} {k}: which arc is the tie, A or B?" if blind else \
        f"{tag} {k} A={sa} det={ra['det']}/{ra['kind']}  B={sb} det={rb['det']}/{rb['kind']}"
    ImageDraw.Draw(top).text((10, 8), label, fill="black", font=font)
    out = Image.new("RGB", (im.width, im.height + 46), "white")
    out.paste(top, (0, 0)); out.paste(im, (0, 46))
    name = f"{tag}_{k:02d}.png"
    out.save(os.path.join(outdir, name))
    manifest.append({"n": k, "tile": name, "A_upper": sa, "B_lower": sb, "pdf_page_index": page,
                     "A_box_page_px": [round(v, 1) for v in ra["box"]],
                     "B_box_page_px": [round(v, 1) for v in rb["box"]], "dpi": dpi,
                     "frame_ink_vs_shifted_control": frames,
                     "question": "Which arc is the tie, A or B? (or both / neither)",
                     "VERDICT_none_yet": None})
    print(name, sa, sb, frames)
json.dump({"roadmap_item": "2.75", "pdf": os.path.basename(pdf), "dpi": dpi, "pairs": manifest},
          open(os.path.join(outdir, f"{tag}-manifest.json"), "w"), indent=1)
