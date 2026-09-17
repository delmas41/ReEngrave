"""Dump the three pixel sets at the meter window, so the ink can be LOOKED AT.

⚠️ THIS IS THE "SEND SEAN THE CROP" DISCIPLINE, APPLIED TO MY OWN CONCLUSION.
`diagnose.py` reports that the printed `3/4` is ALREADY one erased component on
every staff — 1.7-2.1 spaces wide, 3.8-4.5 tall. A count cannot say WHY. Two
readings fit that number and they have opposite consequences:

  (a) the two digits physically touch on the plate — the scanner's own
      threshold merged them, and the ceiling is the plate (K2);
  (b) they are separate glyphs bridged by a MIDDLE STAFF LINE that
      `remove_staff_lines` did not take — in which case the component is a
      MERGE and the representation problem runs the other way.

Only pixels separate those, so this writes them out: `intact`, `erased`,
`removed`, and a colour overlay where red = removed (staff line AND possibly
glyph), black = ink that survives erasure.

Usage:
    python3 probe/crops.py <pdf> <page> --cell 6 --staves 0,2,7,16
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")

from bridge import load_page, pixel_sets, components, cell_units   # noqa: E402

X_MIN, X_MAX = 0.6, 3.0        # the meter window, widened a little to show context


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cell", type=int, default=6)
    ap.add_argument("--staves", default="0,2,7,16")
    ap.add_argument("--out", default="out/crops")
    a = ap.parse_args()

    import cv2
    want = [int(s) for s in a.staves.split(",")]
    _pws, cells = load_page(a.pdf, a.page)
    here = {c.staff_index: c for c in cells if c.measure_index == a.cell}
    print(f"REACH  cells at measure_index={a.cell}: {len(here)}; "
          f"asked for {want}")
    if not here:
        print("DEAD: no cells at that index")
        return 2

    outdir = pathlib.Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    n_written = 0
    for st in want:
        c = here.get(st)
        if c is None:
            print(f"  staff {st}: absent")
            continue
        sets = pixel_sets(c)
        sp, thick = cell_units(c)
        if sets is None or not sp:
            print(f"  staff {st}: no mask/unit")
            continue
        intact, erased, removed = sets
        h, w = intact.shape
        xa, xb = int(X_MIN * sp), min(int(X_MAX * sp), w)
        if xb <= xa:
            print(f"  staff {st}: empty window")
            continue

        cut = (slice(0, h), slice(xa, xb))
        ci, ce, cr = intact[cut], erased[cut], removed[cut]

        def png(mask):
            return np.where(mask, 0, 255).astype(np.uint8)

        cv2.imwrite(str(outdir / f"s{st:02d}-1-intact.png"), png(ci))
        cv2.imwrite(str(outdir / f"s{st:02d}-2-erased.png"), png(ce))
        cv2.imwrite(str(outdir / f"s{st:02d}-3-removed.png"), png(cr))

        # Overlay: black = survives erasure, red = removed (the multi-membership
        # pixels), white = paper.
        rgb = np.full(ci.shape + (3,), 255, np.uint8)
        rgb[cr] = (0, 0, 255)          # BGR red
        rgb[ce] = (0, 0, 0)
        cv2.imwrite(str(outdir / f"s{st:02d}-4-overlay.png"), rgb)

        n, labels, stats = components(ce)
        big = [(int(stats[i, 4]), i) for i in range(1, n)]
        big.sort(reverse=True)
        print(f"  staff {st:2d}  sp={sp:.1f} thick={thick}  window={xb - xa}px "
              f"erased_components={n - 1}  largest_areas="
              f"{[b[0] for b in big[:4]]}")
        n_written += 1

    if not n_written:
        print("DEAD: nothing written")
        return 2
    print(f"wrote {n_written * 4} images to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
