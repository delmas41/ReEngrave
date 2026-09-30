"""ROADMAP 2.39b, manager review item 4: print-check the staff-position
swing claim. For one glyph subject whose ACCEPTED `Q.NOTEHEAD_RECENTRE`
row would move its rounded `Q.NOTEHEAD_STAFF_POSITION`, this draws the
staff's own five lines (yellow), the raw detector box (grey), and two
horizontal ticks -- OLD position (ORANGE) and NEW position (PURPLE), each
spanning the box's own x-range -- and prints the ink fraction measured in
a notehead-height band at each tick BEFORE any visual judgement is made.

`position * half_step` is a frame-agnostic ratio (`(y - top) / half_step`
at GATHER), so the same arithmetic, redone with the PAGE frame's own top
line and spacing, lands the tick at the same physical row the canonical-
frame position names -- no canonical/page conversion needed.

Usage: python3 crop_2.39b_position_swing.py <pdf> <record.json> <subject> <out.png>
"""
from __future__ import annotations

import argparse
import json
import sys

import fitz
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")


def _load_record(path):
    with open(path) as f:
        return json.load(f)["record"]


def _rows_for(record, quantity, subject, kind="observations"):
    return [r for r in record[kind]
           if r["quantity"] == quantity and r["subject"] == subject]


def _ink_fraction(im, x0, x1, y_center, band_px):
    """Ink (dark) fraction in a band `band_px` tall, `[x0, x1]` wide,
    centred on `y_center`, on the RGB crop `im` (a PIL Image) -- a plain
    grey threshold, independent of the pipeline's own binarisation, so
    this measurement is not circular with the reader it is checking."""
    arr = np.asarray(im.convert("L"))
    H, W = arr.shape
    ix0, ix1 = max(0, int(x0)), min(W, int(x1))
    iy0 = max(0, int(y_center - band_px / 2.0))
    iy1 = min(H, int(y_center + band_px / 2.0))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    region = arr[iy0:iy1, ix0:ix1]
    if region.size == 0:
        return None
    return float((region < 128).sum()) / float(region.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("record")
    ap.add_argument("subject")
    ap.add_argument("out")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--zoom", type=int, default=6)
    args = ap.parse_args()

    record = _load_record(args.record)
    parts = args.subject.split("/")
    page, system, staff_idx, cell, glyph = (int(x) for x in parts[1:6])
    staff_key = f"staff/{page}/{system}/{staff_idx}"

    box_row = _rows_for(record, "glyph_box", args.subject)[-1]
    x0, y0, x1, y1 = (float(v) for v in box_row["detail"]["bbox_page_px"])

    line_ys = [float(v) for v in
              _rows_for(record, "staff_lines", staff_key)[-1]["value"]]
    spacing = float(_rows_for(record, "staff_spacing", staff_key)[-1]["value"])
    half_step = spacing / 2.0
    top_y = line_ys[0]

    pos_row = _rows_for(record, "notehead_staff_position", args.subject)[-1]
    rec_row = _rows_for(record, "notehead_recentre", args.subject)[-1]
    old_pos = round(pos_row["value"])
    dy_sp = rec_row["value"][1]
    new_pos = round(pos_row["value"] + 2 * dy_sp)

    old_y = top_y + old_pos * half_step
    new_y = top_y + new_pos * half_step

    doc = fitz.open(args.pdf)
    pm = doc[page].get_pixmap(dpi=args.dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))

    band = spacing * 1.1   # a notehead-height band, same as the standard box
    old_fill = _ink_fraction(im, x0 - spacing * 0.2, x1 + spacing * 0.2,
                             old_y, band)
    new_fill = _ink_fraction(im, x0 - spacing * 0.2, x1 + spacing * 0.2,
                             new_y, band)

    pad = spacing * 3
    fx0 = max(0, int(min(x0, x1) - pad))
    fx1 = min(im.width, int(max(x0, x1) + pad))
    fy0 = max(0, int(min(line_ys[0], y0, y1, old_y, new_y) - pad))
    fy1 = min(im.height, int(max(line_ys[-1], y0, y1, old_y, new_y) + pad))
    crop = im.crop((fx0, fy0, fx1, fy1)).convert("RGB")
    zoom = args.zoom
    crop = crop.resize((crop.width * zoom, crop.height * zoom), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)
    head_w_px = (x1 - x0) * zoom

    def to_crop(px, py):
        return ((px - fx0) * zoom, (py - fy0) * zoom)

    for ly in line_ys:
        ax, ay = to_crop(fx0, ly)
        bx, by = to_crop(fx1, ly)
        draw.line([(ax, ay), (bx, by)], fill=(220, 200, 0), width=2)

    draw.rectangle([to_crop(x0, y0), to_crop(x1, y1)], outline=(140, 140, 140),
                   width=2)

    ax, ay = to_crop(x0 - spacing * 0.2, old_y)
    bx, by = to_crop(x1 + spacing * 0.2, old_y)
    draw.line([(ax, ay), (bx, by)], fill=(235, 140, 0), width=4)   # OLD, orange
    ax, ay = to_crop(x0 - spacing * 0.2, new_y)
    bx, by = to_crop(x1 + spacing * 0.2, new_y)
    draw.line([(ax, ay), (bx, by)], fill=(150, 30, 200), width=4)  # NEW, purple

    crop.save(args.out)
    print(f"wrote {args.out}  subject={args.subject}  "
         f"head_width_px_at_zoom={head_w_px:.0f}  "
         f"old_pos={old_pos} new_pos={new_pos}  "
         f"old_ink_fraction={old_fill}  new_ink_fraction={new_fill}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
