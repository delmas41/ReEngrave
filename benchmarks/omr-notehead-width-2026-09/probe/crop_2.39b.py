"""ROADMAP 2.39b print check (CLAUDE.md Sec.6b): a crop is a ruler, cut
from the PDF at the gather's own DPI (600), with the SUBJECT marked -- a
corner bracket on the exact head, never a margin tick.

Colours (this round's own key, extending crop_2.39.py's):
  YELLOW = the staff's own five lines (which staff the subject is filed on).
  RED    = the raw detector box -- the pre-2.39 witness, unchanged.
  GREEN  = the RE-CENTRED standard box: `geometry.standard_head_box` around
           `Q.NOTEHEAD_RECENTRE`'s own accepted offset where one exists,
           else the un-shifted detector centre (a decline or no row).
  BLUE   = the head's TRUE place as judged from the print, by hand
           (`--blue-x-page --blue-y-page`, PAGE px) -- never auto-derived;
           omit it for a first, undecorated look.

Usage: python3 crop_2.39b.py <pdf> <record.json> <glyph-subject-key> <out.png> \
    [--blue-x-page X] [--blue-y-page Y]
"""
from __future__ import annotations

import argparse
import json
import sys

import fitz
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
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("record")
    ap.add_argument("subject")
    ap.add_argument("out")
    ap.add_argument("--blue-x-page", type=float, default=None)
    ap.add_argument("--blue-y-page", type=float, default=None)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    record = _load_record(args.record)
    parts = args.subject.split("/")
    page, system, staff_idx, cell, glyph = (int(x) for x in parts[1:6])
    staff_key = f"staff/{page}/{system}/{staff_idx}"

    box_rows = _rows_for(record, "glyph_box", args.subject)
    if not box_rows:
        print(f"no glyph_box row for {args.subject}"); return 1
    box_row = box_rows[-1]
    page_box = (box_row.get("detail") or {}).get("bbox_page_px")
    if not page_box:
        print(f"no bbox_page_px on {args.subject}'s glyph_box row"); return 1
    x0, y0, x1, y1 = (float(v) for v in page_box)

    lines_rows = _rows_for(record, "staff_lines", staff_key)
    sp_rows = _rows_for(record, "staff_spacing", staff_key)
    if not lines_rows or not sp_rows:
        print(f"no staff geometry for {staff_key}"); return 1
    line_ys = [float(v) for v in lines_rows[-1]["value"]]
    spacing = float(sp_rows[-1]["value"])

    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    # The RE-CENTRED centre: `Q.NOTEHEAD_RECENTRE`'s own accepted offset
    # (an OBSERVATION, never an abstention) for this exact subject, else
    # the un-shifted detector centre.
    rc_rows = _rows_for(record, "notehead_recentre", args.subject)
    recentred = rc_rows[-1] if rc_rows else None
    rcx, rcy = cx, cy
    if recentred is not None:
        dx_sp, dy_sp = recentred["value"]
        rcx = cx + dx_sp * spacing
        rcy = cy + dy_sp * spacing
    gx0, gx1, gy0, gy1 = GEOM.standard_head_box(rcx, rcy, spacing)

    doc = fitz.open(args.pdf)
    pm = doc[page].get_pixmap(dpi=args.dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))

    pad = spacing * 3
    xs = [x0, x1, gx0, gx1]
    ys = [line_ys[0], line_ys[-1], y0, y1, gy0, gy1]
    if args.blue_x_page is not None:
        xs.append(args.blue_x_page)
    if args.blue_y_page is not None:
        ys.append(args.blue_y_page)
    fx0 = max(0, int(min(xs) - pad))
    fx1 = min(im.width, int(max(xs) + pad))
    fy0 = max(0, int(min(ys) - pad))
    fy1 = min(im.height, int(max(ys) + pad))
    crop = im.crop((fx0, fy0, fx1, fy1)).convert("RGB")
    zoom = 4
    crop = crop.resize((crop.width * zoom, crop.height * zoom), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - fx0) * zoom, (py - fy0) * zoom)

    for ly in line_ys:
        ax, ay = to_crop(fx0, ly)
        bx, by = to_crop(fx1, ly)
        draw.line([(ax, ay), (bx, by)], fill=(220, 200, 0), width=2)

    draw.rectangle([to_crop(x0, y0), to_crop(x1, y1)], outline=(230, 40, 40),
                   width=3)
    draw.rectangle([to_crop(gx0, gy0), to_crop(gx1, gy1)],
                   outline=(30, 180, 60), width=3)

    bl = 14
    bx, by = to_crop(cx, cy)
    draw.line([(bx - bl, by), (bx + bl, by)], fill=(120, 120, 120), width=1)
    draw.line([(bx, by - bl), (bx, by + bl)], fill=(120, 120, 120), width=1)

    if args.blue_x_page is not None and args.blue_y_page is not None:
        px, py = to_crop(args.blue_x_page, args.blue_y_page)
        draw.line([(px - bl, py), (px + bl, py)], fill=(30, 90, 230), width=2)
        draw.line([(px, py - bl), (px, py + bl)], fill=(30, 90, 230), width=2)

    crop.save(args.out)
    print(f"wrote {args.out}  subject={args.subject}  "
         f"raw=({x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f})  "
         f"recentred_box=({gx0:.1f},{gy0:.1f},{gx1:.1f},{gy1:.1f})  "
         f"recentre_row={'none' if recentred is None else recentred['value']}  "
         f"spacing={spacing:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
