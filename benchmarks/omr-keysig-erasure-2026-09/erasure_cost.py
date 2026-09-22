#!/usr/bin/env python3
"""Does `erase_staff_lines` cost the key-signature flats their height?

⚠️⚠️ THE QUESTION, and it is the 2026-09-22 handoff's ranked #1. On an ENGRAVED
render `adjudicate_key_signature`'s locator drops two of every three flats at
`min_height_spaces = 1.10`, because they measure ~0.94 spaces after
`header_ink_mask` where the page truth measures them at 2.57. Lane A could not
say whether that was **Verovio's key-signature spacing** or **the erasure** --
and if it is the erasure, it is everywhere.

THIS ASKS IT DIRECTLY: the same crop, clustered twice, differing ONLY in
whether `erase_staff_lines` ran. `header_ink_mask` is called UNCHANGED for the
erased arm; the un-erased arm reproduces its body with that one line dropped,
and a CONTROL asserts the two agree wherever no staff line is involved.

⚠️ ONE-SIDED. It measures what the erasure costs THIS glyph on THIS render. It
does not establish what a real plate does, where staff lines and ink are not
separable by construction.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# the sibling lane's own shim, so this runs from anywhere
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--staff", type=int, default=0)
    ap.add_argument("--x", type=int, nargs=2, default=(400, 800))
    ap.add_argument("--label", default="")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    import cv2
    import numpy as np  # noqa: F401
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staff_header import header_cells_for_page
    from tools.omr.key_signature_locator import (
        DEFAULT_LOCATOR_CONFIG as C, DEFAULT_INK_CONFIG as IC)
    from tools.omr import header_ink as HI

    pages = prepare_pages(str(args.pdf), [args.page], dpi=args.dpi)
    pws, _ = pages[0]
    crops = header_cells_for_page(pws)
    crop = crops.get(args.staff)
    if crop is None:
        print(f"DEAD: staff {args.staff} has no header crop")
        return 2
    metrics = HI.staff_metrics(crop)
    if metrics is None:
        print("DEAD: no staff metrics")
        return 2
    spacing, _top, _bot = metrics

    def clusters(erase: bool):
        # ⚠️ The ERASED arm calls the SHIPPED function. The un-erased arm hands
        # it an EMPTY line list, which is how `erase_staff_lines` is made a
        # no-op without reimplementing the mask -- so the two arms differ in
        # exactly one thing and nothing is restated.
        mask = HI.header_ink_mask(
            crop, spacing,
            crop.staff_line_ys_canonical if erase else [], IC)
        if mask is None:
            return []
        n, _l, stats, _c = cv2.connectedComponentsWithStats(mask, connectivity=8)
        min_area = C.min_component_area_spaces * spacing * spacing
        comps = [tuple(stats[i][:4]) for i in range(1, n)
                 if stats[i][4] >= min_area]
        return HI.cluster_components_2d(
            comps, max_gap=C.cluster_gap_spaces * spacing)

    lo, hi = args.x
    out = {}
    for name, erase in (("erased", True), ("intact", False)):
        rows = []
        for b in sorted(clusters(erase)):
            x, y, w, h = b[0], b[1], b[2], b[3]
            if not (lo <= x <= hi):
                continue
            rows.append({"x": int(x), "y": int(y),
                         "w_sp": round(w / spacing, 2),
                         "h_sp": round(h / spacing, 2),
                         "kept": bool(C.min_height_spaces <= h / spacing
                                      <= C.max_height_spaces
                                      and w / spacing >= C.min_width_spaces)})
        out[name] = rows

    print(f"{args.label or args.pdf.name}  staff {args.staff}  "
          f"spacing {spacing:.1f} px  window x in [{lo}, {hi}]")
    print(f"  staff lines (canonical y): "
          f"{[round(float(v)) for v in crop.staff_line_ys_canonical]}")
    print(f"  `min_height_spaces` = {C.min_height_spaces}\n")
    for name in ("intact", "erased"):
        print(f"  staff lines {name.upper()}:")
        if not out[name]:
            print("     (nothing in the window)")
        for r in out[name]:
            print(f"     x={r['x']:5d} y={r['y']:5d}  "
                  f"w {r['w_sp']:.2f}  h {r['h_sp']:.2f}  "
                  f"{'KEPT' if r['kept'] else 'DROPPED'}")
        print()

    # ⚠️ THE HEADLINE IS A COUNT, NOT A PAIRING. Erasure SPLITS and reshapes
    # components, so a cluster's bounding box MOVES -- matching on x alone
    # pairs a flat with whatever else is near that column, which the first
    # draft of this probe did and which produced a nonsense "-431%". What the
    # locator's pre-fit actually consumes is *how many accidental-sized
    # clusters survive*, so that is what is reported.
    n_intact = sum(1 for r in out["intact"] if r["kept"])
    n_erased = sum(1 for r in out["erased"] if r["kept"])
    print(f"  ACCIDENTAL-SIZED CLUSTERS THE LOCATOR WOULD KEEP:")
    print(f"     staff lines INTACT : {n_intact}")
    print(f"     staff lines ERASED : {n_erased}")
    if n_intact > n_erased:
        print(f"     ⚠️⚠️ THE ERASURE COSTS {n_intact - n_erased} OF "
              f"{n_intact}.")
    elif n_intact == n_erased:
        print("     the erasure costs NOTHING here.")

    # And the heights, side by side, as two sorted lists -- no pairing claimed.
    print("\n  accidental-sized heights (staff spaces), sorted:")
    print(f"     INTACT : {sorted(r['h_sp'] for r in out['intact'] if r['kept'])}")
    print(f"     ERASED : {sorted(r['h_sp'] for r in out['erased'] if r['kept'])}")
    print(f"     ⚠️ the ones the erasure pushed under {C.min_height_spaces}: "
          f"{sorted(r['h_sp'] for r in out['erased'] if not r['kept'] and 0.6 <= r['h_sp'] < C.min_height_spaces)}")

    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
