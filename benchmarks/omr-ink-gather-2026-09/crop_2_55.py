"""ROADMAP 2.55 crops: every rescued-and-KEPT notehead box (up to 30 per
page), at >=x3, the rescued box in its own colour (red) with its score and
matched witness kind; one contact sheet per page under out/print/2.55/.

Record read ONLY through `record_io.load_record`. Reuses the record's own
provenance for the PDF path and DPI, so the crop coordinates (`bbox_page_px`,
already filed at GATHER time by `gather_lowconf_rescue`) need no second
conversion -- CLAUDE.md 2026-10-01: measure/draw at the SAME frame the
reader itself measured in.

    python3 benchmarks/omr-ink-gather-2026-09/crop_2_55.py \
        --record /tmp/lane255-arm-out/out/beethoven5-litolff/beethoven5-litolff-p3.record.json \
        --tag litolff-p3 --out-root out/print/2.55
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tools.omr.staged.record_io import load_record  # noqa: E402

MARGIN_PX = 90       # how much raster around the box each crop shows
SCALE = 3            # >= x3 per CLAUDE.md §6b's own print-check convention
COLS = 6


def _crop_one(page, box, witness, score, smufl, dpi):
    """`box` is in RENDER PIXELS at `dpi` (`bbox_page_px`'s own frame,
    `gather._page_box`'s own derivation) -- fitz clip rects are in PDF
    POINTS (72/inch), so the pixel box is converted down to points first and
    the page is then rendered at `dpi * SCALE` for the magnified crop."""
    import fitz
    from PIL import Image, ImageDraw

    base_zoom = dpi / 72.0
    x0, y0, x1, y1 = (v / base_zoom for v in box)
    margin_pt = MARGIN_PX / base_zoom
    cx0, cy0 = max(0, x0 - margin_pt), max(0, y0 - margin_pt)
    cx1, cy1 = x1 + margin_pt, y1 + margin_pt
    clip = fitz.Rect(cx0, cy0, cx1, cy1)
    zoom = base_zoom * SCALE
    pix = page.get_pixmap(clip=clip, matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(img)
    # the rescued box itself, in its own colour -- a corner bracket on the
    # exact box, per CLAUDE.md's "a crop is a crop with a ruler" convention.
    bx0 = (x0 - cx0) * zoom
    by0 = (y0 - cy0) * zoom
    bx1 = (x1 - cx0) * zoom
    by1 = (y1 - cy0) * zoom
    draw.rectangle([bx0, by0, bx1, by1], outline=(220, 20, 20), width=3)
    label = f"{smufl} {score:.2f} [{witness}]"
    draw.rectangle([0, 0, 9 + 7 * len(label), 16], fill=(255, 255, 0))
    draw.text((2, 1), label, fill=(0, 0, 0))
    return img


def main(argv=None) -> int:
    from PIL import Image

    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out-root", default="out/print/2.55")
    ap.add_argument("--max-kept", type=int, default=30)
    a = ap.parse_args(argv)

    rec = load_record(a.record)
    obs = rec["record"]["observations"]
    args = rec["provenance"]["settings"]["args"]
    pdf_path = args["pdf"]
    dpi = args["dpi"]

    kept = [o for o in obs
           if o.get("reader") == "yolo_rescue_lowconf"
           and o.get("quantity") == "glyph_box"]
    kept = kept[: a.max_kept]
    if not kept:
        print(f"{a.tag}: no rescued-and-kept glyphs -- no sheet written")
        return 0

    import fitz
    doc = fitz.open(pdf_path)
    tiles = []
    for o in kept:
        subj = o["subject"]
        page_idx = int(subj.split("/")[1])
        page = doc[page_idx]
        box = o["detail"]["bbox_page_px"]
        smufl = o["value"][0]
        img = _crop_one(page, box, o["detail"].get("witness"), o["score"],
                        smufl, dpi)
        tiles.append((subj, img))

    cols = COLS
    rows = (len(tiles) + cols - 1) // cols
    tw = max(im.width for _, im in tiles)
    th = max(im.height for _, im in tiles)
    sheet = Image.new("RGB", (cols * tw, rows * th), (255, 255, 255))
    for i, (subj, im) in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet.paste(im, (c * tw, r * th))

    out_dir = Path(a.out_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{a.tag}-rescued-kept-contact-sheet.png"
    sheet.save(out_path)
    print(f"{a.tag}: {len(tiles)} kept rescue(s) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
