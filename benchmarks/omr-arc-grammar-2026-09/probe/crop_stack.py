"""Render the ink under a candidate STACKED PAIR, so somebody can LOOK.

Every S6 aggregate is compatible with two stories — two arcs an engraver
printed one over the other, and one curve the detector boxed twice — and this
repo's own rule is that *a convincing number is not evidence about its cause*.
One crop settles per-pair what no amount of counting can.

⚠️ Crops are BUILD PRODUCTS and `benchmarks/**/crops/` is gitignored; this
regenerates every one of them deterministically from the committed record and
the edition PDF, and prints each pair's coordinates beside its file so a
reader can re-cut one by hand.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import fitz  # PyMuPDF

sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09")
sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09/probe")
from s6_stacks import run as stacks_run  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("pdf")
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-arc-grammar-2026-09/crops")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--max-gap", type=float, default=1.0)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--both-bind", action="store_true",
                    help="only pairs where BOTH arcs bind two heads")
    a = ap.parse_args()

    r = stacks_run(a.record)
    close = [p for p in r["pairs"] if (p["gap_spaces"] or 99) <= a.max_gap]
    if a.both_bind:
        close = [p for p in close
                 if p["lower_binds"] >= 2 and p["upper_binds"] >= 2]
    close.sort(key=lambda p: p["gap_spaces"])
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    zoom = a.dpi / 72.0
    for i, p in enumerate(close[:a.n]):
        page_i = int(p["where"].split("/")[0][1:])
        boxes = p["lower_boxes"] + p["upper_boxes"]
        x0 = min(b[0] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes)
        y0 = min(b[1] for b in boxes)
        y1 = max(b[1] + b[3] for b in boxes)
        pad = 240.0
        clip = fitz.Rect(max(0, x0 - pad), max(0, y0 - pad),
                         x1 + pad, y1 + pad) / zoom
        pix = doc[page_i].get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        name = (f"STACK{i:02d}-{p['where'].replace('/', '')}-"
                f"{p['lower_kind']}{p['lower_binds']}-over-"
                f"{p['upper_kind']}{p['upper_binds']}.png")
        pix.save(str(out / name))
        print(f"{name}\n    gap {p['gap_spaces']:.2f} spaces, x-overlap "
              f"{p['x_overlap_frac']:.2f}\n"
              f"    lower {p['lower_boxes']}\n    upper {p['upper_boxes']}\n"
              f"    crop x {clip.x0:.0f}..{clip.x1:.0f} "
              f"y {clip.y0:.0f}..{clip.y1:.0f} (pdf pts)")


if __name__ == "__main__":
    main()
