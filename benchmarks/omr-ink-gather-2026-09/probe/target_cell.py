"""The pre-registered target: the printed `3/4` on Litolff Beethoven 5 p.62.

⚠️ THE TARGET WAS CHOSEN BEFORE ANYTHING WAS BUILT and it is the case that can
falsify the whole idea: `ASSUMPTIONS.md` A-DUR-5 justifies a raster pass with
*"the meter is printed on every staff, we classify it on 2 of 17, and the other
15 carry no unclassified detection at that column"*.

⚠️⚠️ AND THE CELL IN THAT ENTRY IS WRONG — it says cell 8 and the printed `3/4`
is at the head of CELL 6, verified by cropping the plate. See FINDINGS §6. This
probe takes the cell as an argument so the claim is not baked in.

⚠️ THE WINDOW IS READ OFF THE PRINT, NOT FITTED TO THE ROWS. The crops
(`crops/`) show a stacked `3` over `4` occupying the middle four spaces of the
staff, roughly two spaces wide, standing just past the double barline. The
window below is that description in numbers, deliberately generous, and the
probe reports what falls in it AND what the nearest row on each staff is, so a
staff that fails the window can be read rather than silently dropped.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")
os.environ["OMR_INK"] = "1"

from ink_reach import load_rows, UNNAMED_BELOW                  # noqa: E402

#: What the print shows, in staff spaces: a two-space-wide stack of digits
#: spanning the staff, standing clear of the barline at the cell's left edge.
W_MIN, W_MAX = 1.4, 2.4
H_MIN, H_MAX = 3.2, 5.0
X_MIN, X_MAX = 0.8, 2.6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cell", type=int, required=True)
    ap.add_argument("--system", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    got = load_rows(a.pdf, a.page)
    rows = [r for r in got["rows"]
            if r.subject.cell == a.cell and r.subject.system == a.system]
    if not rows:
        print("DEAD: no ink rows in that cell")
        return 2

    per_staff = {}
    for r in rows:
        per_staff.setdefault(r.subject.staff, []).append(r)

    hits, out = 0, []
    for st in sorted(per_staff):
        best = None
        for r in per_staff[st]:
            d = r.detail
            sp = d.get("cell_staff_space_px")
            if not sp:
                continue
            x = d["ink_bbox_canonical"][0] / sp
            w, h = d["width_spaces"], d["height_spaces"]
            ok = (W_MIN <= w <= W_MAX and H_MIN <= h <= H_MAX
                  and X_MIN <= x <= X_MAX)
            if ok and (best is None or d["ink_area_px"] > best[0]["ink_area_px"]):
                best = (d, x)
        if best:
            hits += 1
            d, x = best
            state = ("classified" if d["ink_detector_coverage"] >= UNNAMED_BELOW
                     else "UNCLASSIFIED")
            print(f"  staff {st:2d}  {state:12s} x={x:5.2f} w={d['width_spaces']:5.2f}"
                  f" h={d['height_spaces']:5.2f} sp  cov={d['ink_detector_coverage']:.2f}"
                  f"  page_x={d.get('x_center_page', 0):8.1f}"
                  f"  {','.join(d['ink_explained_by'][:2])}")
            out.append({"staff": st, "found": True, "x_spaces": round(x, 2),
                        "width_spaces": d["width_spaces"],
                        "height_spaces": d["height_spaces"],
                        "coverage": d["ink_detector_coverage"],
                        "x_center_page": d.get("x_center_page"),
                        "explained_by": d["ink_explained_by"]})
        else:
            print(f"  staff {st:2d}  -- nothing in the window "
                  f"({len(per_staff[st])} rows in the cell)")
            out.append({"staff": st, "found": False,
                        "n_rows_in_cell": len(per_staff[st])})

    n_un = sum(1 for o in out if o.get("found") and o["coverage"] < UNNAMED_BELOW)
    xs = [o["x_center_page"] for o in out if o.get("found")]
    print(f"\n  {hits} of {len(per_staff)} staves carry a row at the printed "
          f"meter; {n_un} of {hits} are UNCLASSIFIED")
    if xs:
        print(f"  page x spans {min(xs):.1f}..{max(xs):.1f} "
              f"({max(xs)-min(xs):.1f} px of drift down the plate)")
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(
            {"cell": a.cell, "system": a.system, "staves": len(per_staff),
             "found": hits, "unclassified": n_un,
             "page_x_min": min(xs) if xs else None,
             "page_x_max": max(xs) if xs else None,
             "window": {"w": [W_MIN, W_MAX], "h": [H_MIN, H_MAX],
                        "x": [X_MIN, X_MAX]},
             "rows": out}, indent=1))
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
