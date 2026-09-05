"""Crop a page-pixel region of a fixture PDF to a PNG, for looking at the ink."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import fitz  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("json")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--box", nargs=4, type=int, required=True,
                    help="x0 y0 x1 y1 in PAGE PIXELS")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    res = json.loads(Path(args.json).read_text())
    pg = res["pages"][args.page]
    doc = fitz.open(args.pdf)
    page = doc[pg.get("pdf_page_index", pg.get("page_index", 0))]
    # Derive the raster scale from the recorded page size rather than guessing
    # a dpi: the CLI default and the container default differ.
    scale = pg["page_size_px"][0] / page.rect.width
    dpi = round(scale * 72)
    x0, y0, x1, y1 = args.box
    clip = fitz.Rect(x0 / scale, y0 / scale, x1 / scale, y1 / scale)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip)
    pix.save(args.out)
    print(f"dpi={dpi} clip={clip} -> {args.out} {pix.width}x{pix.height}")


if __name__ == "__main__":
    main()
