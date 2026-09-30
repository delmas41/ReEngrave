"""ROADMAP 2.41 print check (CLAUDE.md Sec.6b) -- crop a notehead at 600
dpi with its staff lines drawn and each reading's centre marked in its own
colour.

Colours: YELLOW = the staff's own five lines. RED = reading A (detector
box centre, rounded). BLUE = reading B (continuous template fit). GREEN =
reading C (best discrete grid position). A cross, not a box -- the
question is CENTRE, not extent.

Usage: python3 crop_2.41.py <pdf> <measure.json> <subject> <out.png>
"""
from __future__ import annotations

import argparse
import json
import sys

import fitz
from PIL import Image, ImageDraw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("measure_json")
    ap.add_argument("subject")
    ap.add_argument("out")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--pad-spaces", type=float, default=3.0)
    args = ap.parse_args()

    data = json.load(open(args.measure_json))
    row = next((r for r in data["rows"] if r["subject"] == args.subject), None)
    if row is None:
        print(f"no row for {args.subject}"); return 1

    page = data["page"]
    bbox = row["bbox_page_px"]
    spacing = row["spacing"]
    x0, y0, x1, y1 = bbox
    a_cx, a_cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    top = a_cy - (row["a_pos_float"]) * (spacing / 2.0)  # line_ys[0] recovered

    doc = fitz.open(args.pdf)
    pm = doc[page].get_pixmap(dpi=args.dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))
    doc.close()

    half_step = spacing / 2.0
    a_y = top + row["a_pos"] * half_step
    b_y = top + row["b_pos"] * half_step if row["b_ok"] else None
    c_y = top + row["c_pos"] * half_step if row["c_ok"] else None
    b_cx = a_cx + (row["b_dx_sp"] * spacing if row.get("b_dx_sp") else 0.0)

    pad = spacing * args.pad_spaces
    ys_all = [top, top + 8 * half_step, y0, y1]
    if b_y is not None:
        ys_all.append(b_y)
    if c_y is not None:
        ys_all.append(c_y)
    fx0 = max(0, int(x0 - pad))
    fx1 = min(im.width, int(x1 + pad))
    fy0 = max(0, int(min(ys_all) - pad))
    fy1 = min(im.height, int(max(ys_all) + pad))
    crop = im.crop((fx0, fy0, fx1, fy1)).convert("RGB")
    zoom = 6
    crop = crop.resize((crop.width * zoom, crop.height * zoom), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - fx0) * zoom, (py - fy0) * zoom)

    for k in range(9):
        ly = top + k * half_step
        ax, ay = to_crop(fx0, ly)
        bx, by = to_crop(fx1, ly)
        colour = (220, 200, 0) if 0 <= k <= 8 and k % 2 == 0 else (150, 140, 90)
        w = 2 if k % 2 == 0 else 1
        draw.line([(ax, ay), (bx, by)], fill=colour, width=w)

    def cross(px, py, colour, size=20, width=4):
        cx, cy = to_crop(px, py)
        draw.line([(cx - size, cy), (cx + size, cy)], fill=colour, width=width)
        draw.line([(cx, cy - size), (cx, cy + size)], fill=colour, width=width)

    cross(a_cx, a_y, (230, 30, 30), size=22, width=3)  # A red
    if b_y is not None:
        cross(b_cx, b_y, (30, 80, 230), size=16, width=3)  # B blue
    if c_y is not None:
        cross(a_cx, c_y, (20, 160, 60), size=11, width=3)  # C green

    draw.rectangle([to_crop(x0, y0), to_crop(x1, y1)], outline=(120, 120, 120),
                   width=2)

    crop.save(args.out)
    print(f"wrote {args.out}  subject={args.subject}  name={row['name']}  "
         f"A_pos={row['a_pos']}  B_pos={row.get('b_pos')} fill={row.get('b_fill')}  "
         f"C_pos={row.get('c_pos')} fill={row.get('c_fill')} ambiguous={row.get('c_ambiguous')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
