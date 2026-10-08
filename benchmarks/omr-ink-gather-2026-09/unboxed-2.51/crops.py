"""Contact sheet of the largest head-sized and digit-sized UNCOVERED ink
components, per page -- ROADMAP 2.51. Renders the real PDF page at the
gather's own DPI (never a re-derived raster), crops >=3x around each
component, tints the uncovered box, draws nearby detector boxes thin.
NOT a judgement -- a one-word eyeball guess per tile only.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

from tools.omr.staged import record_io


def cell_key_of(subj):
    parts = subj.split("/")
    return "/".join(["cell"] + parts[1:5])


def make_sheet(record_path, pdf_path, page_index, dpi, out_png, label, top_n=20):
    d = record_io.load_record(record_path)
    obs = d["record"]["observations"]
    ink = [r for r in obs if r.get("quantity") == "ink" and isinstance(r.get("detail"), dict)
           and "ink_bbox_canonical" in r["detail"]]
    gb_by_cell = {}
    for r in obs:
        if r.get("quantity") == "glyph_box":
            gb_by_cell.setdefault(cell_key_of(r["subject"]), []).append(r)

    cands = []
    for r in ink:
        dd = r["detail"]
        cov = dd.get("ink_detector_coverage", 0.0)
        area = dd["ink_area_px"]
        if cov > 0.3:
            continue
        w, h = dd.get("width_spaces"), dd.get("height_spaces")
        if w is None or h is None:
            continue
        head = 1.0 <= w <= 1.4 and 0.8 <= h <= 1.2
        digit = 0.3 <= w <= 1.0 and 0.5 <= h <= 1.6 and h >= w
        if not (head or digit):
            continue
        pb = dd.get("bbox_page_px")
        if not pb:
            continue
        # only this page
        sub_parts = r["subject"].split("/")
        if int(sub_parts[1]) != page_index:
            continue
        cands.append((area, r, "head_sized" if head else "digit_letter_sized"))

    cands.sort(key=lambda t: -t[0])
    cands = cands[:top_n]
    if not cands:
        print(f"[{label}] no candidates found for page {page_index}")
        return

    page = fitz.open(pdf_path)[page_index]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    page_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    tiles = []
    for area, r, group in cands:
        dd = r["detail"]
        pb = dd["bbox_page_px"]
        x0, y0, x1, y1 = pb
        margin = max(40, (x1 - x0) * 1.5, (y1 - y0) * 1.5)
        cx0, cy0 = max(0, x0 - margin), max(0, y0 - margin)
        cx1, cy1 = min(page_img.width, x1 + margin), min(page_img.height, y1 + margin)
        crop = page_img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
        scale = 3
        crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
        draw = ImageDraw.Draw(crop, "RGBA")
        # tint the uncovered box red
        rx0, ry0 = (x0 - cx0) * scale, (y0 - cy0) * scale
        rx1, ry1 = (x1 - cx0) * scale, (y1 - cy0) * scale
        draw.rectangle([rx0, ry0, rx1, ry1], outline=(255, 0, 0, 255), width=3,
                        fill=(255, 0, 0, 60))
        # nearby detector boxes, thin blue
        cell_key = cell_key_of(r["subject"])
        for gr in gb_by_cell.get(cell_key, []):
            gb = (gr.get("detail") or {}).get("bbox_page_px")
            if not gb:
                continue
            gx0, gy0, gx1, gy1 = gb
            if gx1 < cx0 or gx0 > cx1 or gy1 < cy0 or gy0 > cy1:
                continue
            bx0, by0 = (gx0 - cx0) * scale, (gy0 - cy0) * scale
            bx1, by1 = (gx1 - cx0) * scale, (gy1 - cy0) * scale
            draw.rectangle([bx0, by0, bx1, by1], outline=(0, 100, 255, 255), width=1)
        caption = f"{group} area={int(area)} {r['subject']}"
        draw.rectangle([0, 0, crop.width, 18], fill=(0, 0, 0, 180))
        draw.text((2, 2), caption, fill=(255, 255, 0))
        tiles.append(crop)

    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (tw * cols, th * rows), (30, 30, 30))
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet.paste(t, (c * tw, r * th))
    sheet.save(out_png)
    print(f"[{label}] wrote {out_png} ({len(tiles)} tiles)")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("dpi", type=int)
    ap.add_argument("out")
    ap.add_argument("label")
    args = ap.parse_args()
    make_sheet(args.record, args.pdf, args.page, args.dpi, args.out, args.label)
