#!/usr/bin/env python3
"""l281_tipprobe: could a POSITIVE reading of "this stem's tip is bare" be made from the page raster, and
does it tell the page-0 members the quarter rule gets right from the ones it gets wrong? ROADMAP 2.81
Phase 1, the question behind "tip SEEN clean". A PROBE, not a reader: no product code, no threshold
adopted; it answers whether the reading exists to be built.

For each judged page-0 member that stands on one of Sean's stem boxes it measures, on the 600 dpi page
raster, the ink hugging the stem's far end:

  zone  = a band `ZONE_X_SPACES` wide on EACH side of the stem box, from `ZONE_OUT` spaces BEYOND the
          stem's tip to `ZONE_IN` spaces back along it (a flag hangs from the tip, a beam lies across it,
          a second beam level stands about a space in)
  ink   = dark pixels (gray < 128) in the zone, leaving out the rows a STAFF LINE stands on (from his
          staff-line checks) and every pixel inside one of his boxes that is NOT a beam, flag, stem or
          tremolo (ledger lines, ties, slurs, heads, accidentals, dots, dynamics)
  value = the larger of the two sides' ink fraction

It is NOT independent of Sean's boxes (the stem and the excluded classes are his), so it cannot say how a
reader that had to find the stem would do; it says whether the tip's INK separates bare from beamed/flagged.

    python3 l281_tipprobe.py --scored scored.json [--cache p0.npy]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from l281_truth import Truth  # noqa: E402
from l281_view import PDF, page_rgb  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402

ZONE_X_SPACES = 1.3
ZONE_OUT = 0.45
ZONE_IN = 1.5
LINE_HALF = 0.14


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    T = Truth()
    sp = T.space
    img = page_rgb(PDF, a.cache)
    gray = img.mean(axis=2)
    H, W = gray.shape
    bands = S.staff_bands(T.page)
    keep_cls = ("beam", "flag", "tremolo")
    rows = json.loads(Path(a.scored).read_text())
    judged = [r for r in rows if r["judge"] in ("right", "wrong_beam") and r.get("truth_stem_rect")]
    res = []
    for r in judged:
        x0, y0, x1, y1 = r["truth_stem_rect"]
        tip_end = r["truth_tip_end"]
        tip = y0 if tip_end == "top" else y1
        # y-range of the zone: from OUT beyond the tip to IN along the stem
        if tip_end == "top":
            za, zb = tip - ZONE_OUT * sp, tip + ZONE_IN * sp
        else:
            za, zb = tip - ZONE_IN * sp, tip + ZONE_OUT * sp
        za, zb = int(round(max(0, za))), int(round(min(H, zb)))
        mask = np.ones((zb - za, W), bool)
        # staff-line rows of the bands that contain this x
        for b in bands:
            if b.rect[0] <= (x0 + x1) / 2 <= b.rect[2]:
                for ly in b.lines:
                    lo = int(round(ly - LINE_HALF * sp)) - za
                    hi = int(round(ly + LINE_HALF * sp)) - za
                    mask[max(0, lo):max(0, hi + 1), :] = False
        # his non-beam/flag boxes
        for it in T.items:
            if it.family in keep_cls or it.cls == "stem":
                continue
            bx0, by0, bx1, by1 = [int(round(v)) for v in it.rect]
            if by1 < za or by0 > zb or bx1 < x0 - 3 * sp or bx0 > x1 + 3 * sp:
                continue
            mask[max(0, by0 - za):max(0, by1 - za), max(0, bx0):bx1] = False
        sides = []
        for side in ("right", "left"):
            if side == "right":
                xa, xb = int(round(x1)), int(round(x1 + ZONE_X_SPACES * sp))
            else:
                xa, xb = int(round(x0 - ZONE_X_SPACES * sp)), int(round(x0))
            reg = (gray[za:zb, xa:xb] < 128) & mask[:, xa:xb]
            denom = max(1, int(mask[:, xa:xb].sum()))
            sides.append(float(reg.sum()) / denom)
        res.append({"key": r["key"], "judge": r["judge"], "tip": r["tip"], "right": sides[0],
                    "left": sides[1], "value": max(sides)})
    for jd in ("right", "wrong_beam"):
        xs = sorted(round(x["value"], 3) for x in res if x["judge"] == jd)
        print(f"{jd:11s} n={len(xs)} tip-ink value: min {xs[0]} p25 {xs[len(xs)//4]} median {xs[len(xs)//2]} "
              f"p75 {xs[3*len(xs)//4]} max {xs[-1]}")
        print("   ", xs)
    # the best single cut and what it does
    vals = sorted({x["value"] for x in res})
    best = None
    for c in vals:
        tp = sum(1 for x in res if x["judge"] == "right" and x["value"] <= c)
        fp = sum(1 for x in res if x["judge"] == "wrong_beam" and x["value"] <= c)
        if best is None or (tp - 5 * fp, -c) > best[0]:
            best = ((tp - 5 * fp, -c), c, tp, fp)
    _s, c, tp, fp = best
    n_r = sum(1 for x in res if x["judge"] == "right")
    n_w = sum(1 for x in res if x["judge"] == "wrong_beam")
    print(f"\ncut (error-weighted x5, chosen ON THIS PAGE -- an upper bound on what it would do elsewhere): "
          f"value <= {c:.3f}: keeps {tp} of {n_r} right heads, lets through {fp} of {n_w} wrong")
    print("\nper tip status:")
    for tip in ("clean_nostroke", "clean_stroke", "occupied", "no_stem"):
        sub = [x for x in res if x["tip"] == tip]
        if sub:
            print(f"  {tip:15s} right={sum(1 for x in sub if x['judge'] == 'right'):2d} wrong={sum(1 for x in sub if x['judge'] == 'wrong_beam'):2d}"
                  f"  median value right={np.median([x['value'] for x in sub if x['judge'] == 'right'] or [float('nan')]):.3f}"
                  f" wrong={np.median([x['value'] for x in sub if x['judge'] == 'wrong_beam'] or [float('nan')]):.3f}")
    print("\nwrong heads' values:", sorted((round(x["value"], 3), x["key"]) for x in res if x["judge"] == "wrong_beam"))
    print("highest right heads:", sorted(((round(x["value"], 3), x["key"]) for x in res if x["judge"] == "right"), reverse=True)[:6])


if __name__ == "__main__":
    main()
