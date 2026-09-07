"""Left-margin crops for HAND-READING which instruments a page prints.

The impossible grade needs one work-specific fact — the page an instrument
first enters — and where that fact comes from decides what the grade means. The
cheapest wrong answer is to take it from the pipeline's own margin reader,
which is the input to the thing being scored. So it is read off the print by
eye, from these crops.

    render_margin.py PDF OUTDIR PAGE [PAGE ...] [--frac 0.28] [--dpi 200]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("outdir")
    ap.add_argument("pages", nargs="+", type=int)
    ap.add_argument("--frac", type=float, default=0.28,
                    help="fraction of the page width to keep from the left")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    for i in args.pages:
        page = doc[i]
        r = page.rect
        clip = fitz.Rect(r.x0, r.y0, r.x0 + r.width * args.frac, r.y1)
        pix = page.get_pixmap(dpi=args.dpi, clip=clip)
        dst = out / f"p{i:03d}_margin.png"
        pix.save(str(dst))
        print("wrote", dst, pix.width, pix.height)


if __name__ == "__main__":
    main()
