"""Every suspect's own ink, on ONE contact sheet, so all of them are looked at.

⚠️ Cropping the first few and generalising is how the last four briefs got
their mechanism wrong. This tiles EVERY row it is given, in one image, each
with the detector's own box drawn on it -- so "I looked at them" is a claim
about the whole population rather than about a convenient prefix.

    python3 .../suspect_sheet.py --record R --pdf P --rows S.json --out X.png
"""
from __future__ import annotations

import argparse
import io
import json
import math

GATHER_DPI = 600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=int, default=55)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--cols", type=int, default=5)
    a = ap.parse_args()

    import fitz
    from PIL import Image, ImageDraw

    rows = json.load(open(a.rows))
    print(f"suspects to tile   {len(rows)}")
    if not rows:
        raise SystemExit("nothing to draw")

    rec = json.load(open(a.record))["record"]
    pagebox = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            pg = (o.get("detail") or {}).get("bbox_page_px")
            if pg:
                pagebox[o["subject"]] = pg

    doc = fitz.open(a.pdf)
    zoom = GATHER_DPI / 72.0
    rendered = {}
    tiles = []
    for r in rows:
        bb = pagebox[r["subject"]]
        pg = r["page"]
        if pg not in rendered:
            pm = doc[pg].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            rendered[pg] = Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")
        img = rendered[pg]
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        p = a.pad
        clip = (max(0, int(cx) - p), max(0, int(cy) - p),
                min(img.width, int(cx) + p), min(img.height, int(cy) + p))
        t = img.crop(clip).resize(((clip[2] - clip[0]) * a.scale,
                                   (clip[3] - clip[1]) * a.scale), Image.LANCZOS)
        d = ImageDraw.Draw(t)
        d.rectangle([(bb[0] - clip[0]) * a.scale, (bb[1] - clip[1]) * a.scale,
                     (bb[2] - clip[0]) * a.scale, (bb[3] - clip[1]) * a.scale],
                    outline=(220, 0, 0), width=2)
        tiles.append((t, f"p{r['page']}s{r['system']}st{r['staff']}c{r['cell']} "
                         f"{r['cls'][8:]} {r['conf']:.2f} a={r['a']:.1f}"))

    w = max(t.width for t, _ in tiles)
    h = max(t.height for t, _ in tiles) + 16
    cols = a.cols
    n_rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * w, n_rows * h), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, (t, cap) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(t, (x, y))
        d.text((x + 2, y + t.height + 2), cap, fill=(0, 0, 0))
    sheet.save(a.out)
    print(f"wrote {len(tiles)} tiles -> {a.out}")


if __name__ == "__main__":
    main()
