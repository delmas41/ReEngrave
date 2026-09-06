"""Render the left margin of a Brahms 1 / Breitkopf page for HAND READING.

The truth this benchmark produces must come off the PRINTED PAGE.  Not from
the reference MusicXML (that is `source_kind: encoding`, and the benchmarks
score against it), and not from an OMR output (`source_kind: page`, which is
what is being graded).  So: render at 600 dpi, crop the left band where
Breitkopf sets the instrument names, and read it.

Usage:  margins.py PAGE [PAGE ...]  [--frac 0.22] [--half top|bottom|all]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
       "symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+", type=int)
    ap.add_argument("--frac", type=float, default=0.22,
                    help="fraction of the page width to keep")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--half", default="all", choices=["all", "top", "bottom"])
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--y0", type=float, default=None,
                    help="top of the crop, as a fraction of page height")
    ap.add_argument("--y1", type=float, default=None)
    ap.add_argument("--suffix", default="")
    args = ap.parse_args()

    out = ROOT / "out" / "crops"
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    for i in args.pages:
        pix = doc[i].get_pixmap(dpi=args.dpi)
        w, h = pix.width, pix.height
        y0, y1 = 0, h
        if args.half == "top":
            y1 = h // 2
        elif args.half == "bottom":
            y0 = h // 2
        if args.y0 is not None:
            y0 = int(args.y0 * h)
        if args.y1 is not None:
            y1 = int(args.y1 * h)
        clip = fitz.Rect(0, y0 * 72 / args.dpi, w * args.frac * 72 / args.dpi,
                         y1 * 72 / args.dpi)
        pix2 = doc[i].get_pixmap(dpi=int(args.dpi * args.scale), clip=clip)
        dest = out / f"p{i:03d}-margin-{args.half}{args.suffix}.png"
        pix2.save(str(dest))
        print("wrote", dest, pix2.width, "x", pix2.height,
              f"(page {w}x{h} at {args.dpi} dpi)")


if __name__ == "__main__":
    main()
