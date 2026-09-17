"""Is the merged `3/4` separable at a STAFF LINE, or do the digits touch?

⚠️ THIS IS THE FORK THE WHOLE EXPERIMENT TURNS ON, and it is not the one the
brief expected. The brief's mechanism is a JOIN — reunite fragments erasure
broke. `diagnose.py` measured that erasure broke nothing here: the printed
`3/4` is already ONE erased component on 17 of 17 staves. So the live question
inverts to a SPLIT: the two digits are one blob, and the only reading of
multi-membership that could help is *"this pixel is staff line AND glyph, so
attribute it to the line and cut there"*.

Two outcomes, and they are different results:

  (a) the blob falls into exactly two pieces when the pixels at a STAFF LINE's
      own y are cut -> the merge is INCOMPLETE ERASURE, and multi-membership in
      the SPLIT direction is the repair;
  (b) it does not -> the digits touch in ink that erasure correctly judged not
      to be a line, i.e. the PLATE's own 1-bit threshold merged them. K2. The
      ceiling is the plate.

⚠️ THE TEST DOES NOT ASSUME WHERE THE LINES ARE — it reads them off the cell's
own `staff_line_ys_canonical`, the same field `remove_staff_lines_from_cell`
uses, so a disagreement cannot be mine.

⚠️ AND IT REPORTS THE MINIMUM CUT WHEREVER IT FALLS, not only at the lines. A
merge that separates cleanly at a row which is NOT a staff line is neither (a)
nor (b), and would be a third answer this probe must be able to give.

Usage:
    python3 probe/separability.py <pdf> <page> --cell 6 [--out out/sep.json]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")

from bridge import load_page, pixel_sets, components, cell_units   # noqa: E402

X_MIN, X_MAX = 0.8, 2.6
MIN_H_SPACES = 3.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cell", type=int, default=6)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    import cv2
    _pws, cells = load_page(a.pdf, a.page)
    here = sorted([c for c in cells if c.measure_index == a.cell],
                  key=lambda c: c.staff_index)
    print(f"REACH  staves={len({c.staff_index for c in cells})}  "
          f"cells={len(cells)}  at measure_index={a.cell}: {len(here)}")
    if not here:
        print("DEAD: no cells at that index")
        return 2

    out = []
    for c in here:
        sets = pixel_sets(c)
        sp, thick = cell_units(c)
        if sets is None or not sp:
            continue
        intact, erased, removed = sets
        n, labels, stats = components(erased)
        best = None
        for lab in range(1, n):
            x, y, w, h, area = (int(stats[lab, k]) for k in range(5))
            if not (X_MIN <= x / sp <= X_MAX):
                continue
            if h / sp < MIN_H_SPACES:
                continue
            if best is None or area > best[4]:
                best = (x, y, w, h, area, lab)
        if best is None:
            out.append({"staff": c.staff_index, "meter_component": None})
            print(f"  staff {c.staff_index:2d}  no tall component in window")
            continue
        x, y, w, h, area, lab = best
        blob = (labels[y:y + h, x:x + w] == lab)
        rows = blob.sum(axis=1)                     # ink per row of the blob

        # ── (a) cut at the staff lines ───────────────────────────────────────
        line_ys = list(getattr(c, "staff_line_ys_canonical", None) or [])
        half = max(1, int(round((thick or 0) / 2.0)))
        cut = blob.copy()
        n_line_rows = 0
        for ly in line_ys:
            lo, hi = int(round(ly)) - half - y, int(round(ly)) + half + 1 - y
            lo, hi = max(0, lo), min(h, hi)
            if hi > lo:
                cut[lo:hi, :] = False
                n_line_rows += hi - lo
        nc, _cl, cs = components(cut)
        # only pieces worth calling a digit (>= 1/2 space each way)
        floor = int(0.5 * sp)
        pieces = [i for i in range(1, nc)
                  if cs[i, 2] >= floor * 0.6 and cs[i, 3] >= floor * 0.6]

        # ── the minimum horizontal cut, wherever it falls ────────────────────
        interior = rows[int(0.25 * h):int(0.75 * h)]
        if interior.size:
            k = int(interior.argmin()) + int(0.25 * h)
            min_row, min_val = k, int(rows[k])
        else:
            min_row, min_val = -1, -1
        at_line = any(abs((y + min_row) - ly) <= half + 1 for ly in line_ys)

        print(f"  staff {c.staff_index:2d}  blob {w}x{h}px "
              f"({w / sp:.2f}x{h / sp:.2f} sp)  "
              f"cut-at-lines -> {len(pieces)} piece(s)  "
              f"min-row ink={min_val}/{w} at y_off={min_row} "
              f"({'AT a staff line' if at_line else 'not at a line'})")
        out.append({
            "staff": c.staff_index,
            "blob_px": [w, h], "blob_spaces": [round(w / sp, 2),
                                               round(h / sp, 2)],
            "pieces_after_line_cut": len(pieces),
            "min_row_ink": min_val, "blob_width": int(w),
            "min_row_at_staff_line": bool(at_line),
        })

    got = [o for o in out if o.get("blob_px")]
    if not got:
        print("DEAD: no meter component on any staff")
        return 2
    two = sum(1 for o in got if o["pieces_after_line_cut"] == 2)
    one = sum(1 for o in got if o["pieces_after_line_cut"] <= 1)
    print(f"\n(a) cutting at the staff lines splits the blob into exactly TWO "
          f"on {two} of {len(got)} staves")
    print(f"    it does NOT separate (<=1 piece) on {one} of {len(got)}")
    print(f"(b) the narrowest interior row still carries a median "
          f"{int(np.median([o['min_row_ink'] for o in got]))} ink px "
          f"of a median {int(np.median([o['blob_width'] for o in got]))}-px "
          f"blob width")
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"cell": a.cell, "staves": out}, indent=1))
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
