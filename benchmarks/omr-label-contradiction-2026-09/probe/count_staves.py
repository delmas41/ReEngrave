"""How many five-line staves does a page actually print?

Adjudication needs the printed staff count, and eyeballing a 200-dpi margin
strip cannot settle 16 against 17. Renders the page, takes the row ink profile
over the NOTATION band (the right of the page, past the margin labels), and
reports the runs of inked rows — a staff is five of them close together.

    python3 count_staves.py <pdf> <page_index> [dpi]
"""
from __future__ import annotations

import sys

import fitz
import numpy as np


def main(argv: list[str]) -> None:
    pdf, page_index = argv[0], int(argv[1])
    dpi = int(argv[2]) if len(argv) > 2 else 150
    doc = fitz.open(pdf)
    page = doc[page_index]
    r = page.rect
    clip = fitz.Rect(r.x0 + 0.25 * r.width, r.y0, r.x1, r.y1)
    pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=fitz.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height,
                                                             pix.width)
    ink = (img < 128).sum(axis=1) / img.shape[1]
    on = ink > 0.35                       # a staff LINE spans the system
    runs = []
    start = None
    for y, v in enumerate(on):
        if v and start is None:
            start = y
        elif not v and start is not None:
            runs.append((start, y - 1))
            start = None
    if start is not None:
        runs.append((start, len(on) - 1))
    gaps = [b[0] - a[1] for a, b in zip(runs, runs[1:])]
    med = sorted(gaps)[len(gaps) // 2] if gaps else 0
    staves, cur = [], []
    for i, run in enumerate(runs):
        if cur and (run[0] - cur[-1][1]) > 2.5 * med:
            staves.append(cur)
            cur = []
        cur.append(run)
    if cur:
        staves.append(cur)
    print(f"{len(runs)} staff-line runs, median gap {med}, "
          f"grouped into {len(staves)} staves")
    for s in staves:
        print(f"   y {s[0][0]:5d}-{s[-1][1]:5d}  lines={len(s)}")


if __name__ == "__main__":
    main(sys.argv[1:])
