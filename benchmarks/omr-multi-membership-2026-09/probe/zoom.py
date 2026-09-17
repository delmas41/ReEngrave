"""The meter component, cropped to its own box, in BOTH frames.

⚠️ THE CANONICAL FRAME IS AN UPSCALE AND IT FLATTERS THE PICTURE.
`_upscale_to_canonical` rescales a cell so the staff span is constant (100 px
per space), so a crop shown there is a magnification of however many pixels the
plate actually carried. A judgement about whether two digits TOUCH has to be
made on the pixels that exist, not on the interpolation — so this reports the
native staff space and native glyph size beside every crop, and writes the
canonical view only as a magnifier.

Usage:
    python3 probe/zoom.py <pdf> <page> --cell 6 --staves 0,2,7,16
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

X_MIN, X_MAX = 0.8, 2.6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cell", type=int, default=6)
    ap.add_argument("--staves", default="0,2,7,16")
    ap.add_argument("--out", default="out/zoom")
    a = ap.parse_args()

    import cv2
    want = [int(s) for s in a.staves.split(",")]
    _pws, cells = load_page(a.pdf, a.page)
    here = {c.staff_index: c for c in cells if c.measure_index == a.cell}
    print(f"REACH  cells at measure_index={a.cell}: {len(here)}")
    if not here:
        print("DEAD")
        return 2
    outdir = pathlib.Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    wrote = 0
    for st in want:
        c = here.get(st)
        if c is None:
            continue
        sets = pixel_sets(c)
        sp, thick = cell_units(c)
        if sets is None or not sp:
            continue
        intact, erased, removed = sets
        up = float(getattr(c, "upscale_factor", 0) or 0)
        n, labels, stats = components(erased)

        # The meter is the tallest component standing in the meter x-window.
        best = None
        for lab in range(1, n):
            x, y, w, h, area = (int(stats[lab, k]) for k in range(5))
            if not (X_MIN <= x / sp <= X_MAX):
                continue
            if h / sp < 3.0:
                continue
            if best is None or area > best[4]:
                best = (x, y, w, h, area, lab)
        if best is None:
            print(f"  staff {st}: no tall component in the window")
            continue
        x, y, w, h, area, lab = best
        pad = int(0.3 * sp)
        ya, yb = max(0, y - pad), min(intact.shape[0], y + h + pad)
        xa, xb = max(0, x - pad), min(intact.shape[1], x + w + pad)
        cut = (slice(ya, yb), slice(xa, xb))
        ci, ce, cr = intact[cut], erased[cut], removed[cut]

        native_sp = sp / up if up else float("nan")
        print(f"  staff {st:2d}  upscale={up:.3f}  canonical_sp={sp:.1f}px  "
              f"NATIVE_sp={native_sp:.1f}px  glyph={w}x{h} canonical = "
              f"{w / up:.0f}x{h / up:.0f} NATIVE px  "
              f"({w / sp:.2f}x{h / sp:.2f} spaces)")

        rgb = np.full(ci.shape + (3,), 255, np.uint8)
        rgb[cr] = (0, 0, 255)
        rgb[ce] = (0, 0, 0)
        big = cv2.resize(rgb, None, fx=3, fy=3,
                         interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(str(outdir / f"s{st:02d}-meter-overlay.png"), big)
        cv2.imwrite(str(outdir / f"s{st:02d}-meter-erased.png"),
                    cv2.resize(np.where(ce, 0, 255).astype(np.uint8), None,
                               fx=3, fy=3, interpolation=cv2.INTER_NEAREST))
        wrote += 1

    if not wrote:
        print("DEAD: nothing written")
        return 2
    print(f"wrote {wrote * 2} images to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
