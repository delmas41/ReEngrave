"""ROADMAP 2.39 print check (CLAUDE.md Sec.6b): a crop is a ruler, cut from
the PDF at the gather's own DPI (600), with the SUBJECT marked -- a corner
bracket on the exact head, never a margin tick.

Colours: RED = the raw detector box (what every consumer used before
2.39). GREEN = the standard box (geometry.standard_head_box) -- what a
REGULAR notehead's ink-reading consumers use now. YELLOW = the staff's own
five lines, so the crop names which staff the subject is filed on
(feedback_send_sean_the_crop's own rule).

Usage: python3 crop_2.39.py <pdf> <record.json> <glyph-subject-key> <out.png>
"""
from __future__ import annotations

import json
import sys

import fitz
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
from tools.omr.staged import geometry as GEOM  # noqa: E402


def _load_record(path):
    with open(path) as f:
        return json.load(f)["record"]


def _rows_for(record, quantity, subject, kind="observations"):
    return [r for r in record[kind]
           if r["quantity"] == quantity and r["subject"] == subject]


def main():
    pdf_path, record_path, subject, out_path = sys.argv[1:5]
    record = _load_record(record_path)
    parts = subject.split("/")
    page, system, staff_idx, cell, glyph = (int(x) for x in parts[1:6])
    staff_key = f"staff/{page}/{system}/{staff_idx}"

    box_rows = _rows_for(record, "glyph_box", subject)
    if not box_rows:
        print(f"no glyph_box row for {subject}"); return 1
    box_row = box_rows[-1]
    page_box = (box_row.get("detail") or {}).get("bbox_page_px")
    if not page_box:
        print(f"no bbox_page_px on {subject}'s glyph_box row"); return 1
    x0, y0, x1, y1 = (float(v) for v in page_box)

    lines_rows = _rows_for(record, "staff_lines", staff_key)
    sp_rows = _rows_for(record, "staff_spacing", staff_key)
    if not lines_rows or not sp_rows:
        print(f"no staff geometry for {staff_key}"); return 1
    line_ys = [float(v) for v in lines_rows[-1]["value"]]
    spacing = float(sp_rows[-1]["value"])

    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    sx0, sx1, sy0, sy1 = GEOM.standard_head_box(cx, cy, spacing)

    doc = fitz.open(pdf_path)
    pm = doc[page].get_pixmap(dpi=600)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))

    pad = spacing * 3
    fx0 = max(0, int(min(x0, sx0) - pad))
    fx1 = min(im.width, int(max(x1, sx1) + pad))
    fy0 = max(0, int(min(line_ys[0], y0, sy0) - pad))
    fy1 = min(im.height, int(max(line_ys[-1], y1, sy1) + pad))
    crop = im.crop((fx0, fy0, fx1, fy1)).convert("RGB")
    zoom = 4
    crop = crop.resize((crop.width * zoom, crop.height * zoom), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - fx0) * zoom, (py - fy0) * zoom)

    # staff lines, yellow
    for ly in line_ys:
        ax, ay = to_crop(fx0, ly)
        bx, by = to_crop(fx1, ly)
        draw.line([(ax, ay), (bx, by)], fill=(220, 200, 0), width=2)

    # raw detector box, red
    draw.rectangle([to_crop(x0, y0), to_crop(x1, y1)], outline=(230, 40, 40),
                   width=3)
    # standard box, green
    draw.rectangle([to_crop(sx0, sy0), to_crop(sx1, sy1)],
                   outline=(30, 180, 60), width=3)
    # corner bracket on the exact head (the subject), blue, at its centre
    bl = 14
    bx, by = to_crop(cx, cy)
    draw.line([(bx - bl, by), (bx + bl, by)], fill=(30, 90, 230), width=2)
    draw.line([(bx, by - bl), (bx, by + bl)], fill=(30, 90, 230), width=2)

    crop.save(out_path)
    print(f"wrote {out_path}  subject={subject}  "
         f"raw=({x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f})  "
         f"standard=({sx0:.1f},{sy0:.1f},{sx1:.1f},{sy1:.1f})  "
         f"spacing={spacing:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
