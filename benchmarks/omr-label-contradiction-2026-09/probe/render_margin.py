"""Render the left margin strip of a PDF page, for hand adjudication.

    python3 render_margin.py <pdf> <page_index> <out.png> [frac] [dpi]

`frac` is the fraction of the page width kept (default 0.22).
"""
from __future__ import annotations

import sys

import fitz


def main(argv: list[str]) -> None:
    pdf, page_index, out = argv[0], int(argv[1]), argv[2]
    frac = float(argv[3]) if len(argv) > 3 else 0.22
    dpi = int(argv[4]) if len(argv) > 4 else 200
    doc = fitz.open(pdf)
    page = doc[page_index]
    r = page.rect
    clip = fitz.Rect(r.x0, r.y0, r.x0 + frac * r.width, r.y1)
    page.get_pixmap(dpi=dpi, clip=clip).save(out)
    print(out, clip)


if __name__ == "__main__":
    main(sys.argv[1:])
