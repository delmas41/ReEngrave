#!/usr/bin/env python3
"""lud_sample: a RANDOM sample of the notes that went kept -> narrowed, as crops.

The three Brahms systems on the side-by-side images were chosen for having the
MOST such notes, which selects for one kind of passage. This sheet is the
check on that selection: notes drawn at random (fixed seed) from all of them,
each one cut from the print around its head (the subject marked by the box),
labelled with what it was last night, what it is tonight, and why.

Nothing here says which reading is right. The print is the evidence; the
person reading the sheet is the umpire.
"""
import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lud_render import font, name  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402


def lab(s):
    return "|".join(name(x) for x in s.split(" | "))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--extract", required=True)
    ap.add_argument("--notes-csv", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ex = json.load(open(a.extract))
    rows = [r for r in csv.DictReader(open(a.notes_csv)) if r["kind"] == "kept_to_narrowed"]
    random.Random(a.seed).shuffle(rows)
    rows = rows[:a.n]
    rows.sort(key=lambda r: (int(r["page"]), int(r["system"]), int(r["staff"])))
    pages = {}
    tiles = []
    for r in rows:
        page = int(r["page"])
        if page not in pages:
            pages = {page: render_page(ex["prov"]["pdf"], page, dpi=ex["prov"]["dpi"]).rgb}
        img = pages[page]
        box = ex["boxes"][r["subject"]][1:5]
        st = ex["staves"][f"staff/{page}/{r['system']}/{r['staff']}"]
        sp = (st["ys"][-1] - st["ys"][0]) / 4
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        x0, x1 = int(cx - 4.5 * sp), int(cx + 4.5 * sp)
        y0, y1 = int(cy - 7 * sp), int(cy + 7 * sp)
        sc = 3 if sp < 20 else 2
        crop = Image.fromarray(img[max(0, y0):y1, max(0, x0):x1]).resize(
            ((x1 - max(0, x0)) * sc, (y1 - max(0, y0)) * sc), Image.BICUBIC)
        d = ImageDraw.Draw(crop)
        bx = [(box[0] - max(0, x0)) * sc, (box[1] - max(0, y0)) * sc, (box[2] - max(0, x0)) * sc, (box[3] - max(0, y0)) * sc]
        d.rectangle(bx, outline=(235, 90, 0), width=3)
        f = font(sp * sc * 0.55)
        why = r["ink_refusal_why"] or "none"
        txt = [f"{a.doc.split('-')[0][:6]} p{page} s{r['system']} st{r['staff']} bar {r['export_bar']}",
               f"LAST NIGHT: {lab(r['last_night_value_beats'])}",
               f"TONIGHT: {lab(r['tonight_candidates_beats'])}",
               f"{r['tonight_reason'].replace('_', ' ')}",
               f"ink refused: {why}"]
        y = 2
        for t in txt:
            d.text((3, y), t, fill=(0, 0, 0), font=f, stroke_width=2, stroke_fill=(255, 255, 255))
            y += sp * sc * 0.72
        tiles.append(crop)
    w, h = max(t.width for t in tiles), max(t.height for t in tiles)
    cols = a.cols
    rws = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 8), rws * (h + 8)), (200, 200, 200))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (w + 8), (i // cols) * (h + 8)))
    sheet.save(a.out, optimize=True)
    print(a.out, sheet.size, len(tiles))


if __name__ == "__main__":
    main()
