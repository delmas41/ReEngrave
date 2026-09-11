"""Render the ink under a named arc, so a human (or this session) can LOOK.

⚠️ Every aggregate above this is compatible with two stories -- a real curve
whose notes were never detected, and ink that is not a curve -- and this repo's
own rule is that a convincing number is not evidence about its cause. One crop
settles per-arc what no amount of counting can.

The page rectangle on the record is the 600-dpi raster the gather read, which
is the same raster PyMuPDF produces at `--dpi 600`; the crop is taken there and
the arc box drawn on it, with every gathered notehead in the same bars marked.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import fitz  # PyMuPDF

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

sys.path.insert(0, "benchmarks/omr-arc-recovery-2026-09")
from arc_partition import heads_by_cell  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("pdf")
    ap.add_argument("--out-dir", default="benchmarks/omr-arc-recovery-2026-09/crops")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--bound", action="store_true",
                    help="crop arcs that DO bind two heads -- the positive control")
    a = ap.parse_args()

    rec = E.Record(json.load(open(a.record)))
    parts, *_ = E.build(rec)
    heads = heads_by_cell(rec)
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    zoom = a.dpi / 72.0
    rendered: dict = {}

    picked = 0
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments)
            want = (len(covered) >= 2) if a.bound else (len(covered) == 0)
            if not want or picked >= a.n:
                continue
            sp = spacings[segments[0][0]] or 1.0
            if sum(b[2] for _m, b in segments) / sp < 5.0:
                continue
            m_idx, (ax, ay, aw, ah) = segments[0]
            r_, c_ = cells[m_idx]
            page_i = r_.page
            if page_i not in rendered:
                pix = doc[page_i].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                p = out / f"page{page_i}.png"
                pix.save(str(p))
                rendered[page_i] = p
            picked += 1
            kind = ("tie" if "tie" in {kinds.get(id(b)) for _m, b in segments}
                    else "slur")
            pad = 6 * sp
            x0, x1 = ax - pad, ax + aw + pad
            y0, y1 = ay - 5 * sp, ay + ah + 5 * sp
            clip = fitz.Rect(max(0, x0), max(0, y0), x1, y1) / zoom
            sub = doc[page_i].get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                         clip=clip)
            name = (f"{'BOUND' if a.bound else 'REFUSED'}-{kind}-"
                    f"p{r_.page}s{r_.system}st{r_.staff}c{c_}.png")
            sub.save(str(out / name))
            pool = heads.get((r_.page, r_.system, r_.staff, c_)) or []
            print(f"{name}  arc x {ax:.0f}..{ax+aw:.0f} y {ay:.0f}..{ay+ah:.0f}"
                  f"  crop x {clip.x0}..{clip.x1} y {clip.y0}..{clip.y1}")
            for h in pool:
                pb = h["page_box"]
                if pb:
                    print(f"    head {h['subject']} x {pb[0]+pb[2]/2:.0f} "
                          f"y {pb[1]+pb[3]/2:.0f}  {h['fate']}")


if __name__ == "__main__":
    main()
