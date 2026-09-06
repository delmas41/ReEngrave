"""Renders for hand-reading the second work's refusals.

Full pages at 200 dpi (enough to read a Breitkopf margin and count staves) for
the pages the residual refusals sit on, plus the pages either side of the
Trombone attestation edge (45), which is where a boundary error would show.
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
       "symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
PAGES = [int(a) for a in sys.argv[1:]] or [6, 22, 42, 43, 44, 45]


def main() -> None:
    doc = fitz.open(PDF)
    out = ROOT / "out" / "brahms1"
    out.mkdir(parents=True, exist_ok=True)
    for i in PAGES:
        pix = doc[i].get_pixmap(dpi=200)
        pix.save(str(out / f"page{i:03d}_full.png"))
        print("wrote", out / f"page{i:03d}_full.png", pix.width, pix.height)


if __name__ == "__main__":
    main()
