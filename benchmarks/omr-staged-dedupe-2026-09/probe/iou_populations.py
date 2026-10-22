"""Is a SAME-CELL overlapping pair one glyph twice, or two glyphs touching?

⚠️⚠️ THE 0.3 THRESHOLD IS NOT VALID HERE AND THE FIRST LOOK PROVED IT.
`_CROSS_STAFF_DUPLICATE_IOU = 0.3` was swept on CROSS-STAFF NOTEHEADS
(`benchmarks/omr-orchestral-e2e/DEDUPE_THRESHOLD.md`) and its own comment says
0.25 "starts to merge genuinely distinct neighbours". Inside one cell the
neighbours are not merely genuine, they are the POINT: a printed `ff` is two
`f` glyphs standing side by side, their boxes are wider than the gap between
them, and the first same-cell pair this probe found is exactly that —
two `dynamicF` at IoU 0.317, 21 px apart, both real.

So a flat 0.3 rule applied within a cell would DELETE one `f` of every `ff` on
the page. This probe asks whether the two populations separate, and on what.
It reports the DISTRIBUTION and the widest empty interval; it does not pick a
number for you.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from reach import duplicate_pairs  # noqa: E402

BINS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.01]


def centre_offset(p):
    """How far apart the two centres are, as a fraction of the mean box size.

    A glyph detected twice sits on ITSELF; two adjacent letters sit a letter
    apart. This is the quantity a human uses and it needs no threshold to be
    reported.
    """
    ax, ay, aw, ah = p["box_a"]
    bx, by, bw, bh = p["box_b"]
    dx = abs((ax + aw / 2) - (bx + bw / 2))
    dy = abs((ay + ah / 2) - (by + bh / 2))
    scale = (aw + bw) / 2.0
    return (dx / scale if scale else 0.0), (dy / ((ah + bh) / 2.0)
                                            if (ah + bh) else 0.0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--scope", default="same_cell")
    args = ap.parse_args(argv)

    obs = json.load(open(args.record))["record"]["observations"]
    _subjects, _family, pairs = duplicate_pairs(obs, iou=0.0)
    pairs = [p for p in pairs if p["scope"] == args.scope]

    print(f"scope={args.scope}  pairs with ANY overlap: {len(pairs)}")
    fams = sorted({p["family"] for p in pairs})

    print("\nIoU histogram (any overlap > 0):")
    hdr = "  ".join(f"{lo:.2f}-{hi:.2f}" for lo, hi in zip(BINS, BINS[1:]))
    print(f"{'family':<20} {hdr}")
    for f in fams:
        fp = [p for p in pairs if p["family"] == f]
        row = []
        for lo, hi in zip(BINS, BINS[1:]):
            row.append(sum(1 for p in fp if lo <= p["iou"] < hi))
        print(f"{f:<20} " + "  ".join(f"{v:>10}" for v in row))

    print("\nCENTRE OFFSET in x, as a fraction of mean box WIDTH:")
    print(f"{'family':<20} {'n':>5} {'<0.25':>7} {'0.25-0.5':>9} "
          f"{'0.5-0.75':>9} {'>=0.75':>8}")
    for f in fams:
        fp = [p for p in pairs if p["family"] == f]
        b = [0, 0, 0, 0]
        for p in fp:
            dx, _dy = centre_offset(p)
            b[0 if dx < 0.25 else 1 if dx < 0.5 else 2 if dx < 0.75 else 3] += 1
        print(f"{f:<20} {len(fp):>5} {b[0]:>7} {b[1]:>9} {b[2]:>9} {b[3]:>8}")

    # The widest empty interval in the pooled x-offset, which is what a
    # constant would have to sit in if one is ever justified.
    for f in fams:
        fp = [p for p in pairs if p["family"] == f]
        xs = sorted(centre_offset(p)[0] for p in fp)
        if len(xs) < 3:
            continue
        gaps = [(xs[i + 1] - xs[i], xs[i], xs[i + 1])
                for i in range(len(xs) - 1)]
        g, lo, hi = max(gaps)
        print(f"\n{f}: widest empty x-offset interval {lo:.3f} .. {hi:.3f} "
              f"(width {g:.3f}), n={len(xs)}")

    # Do near-identical boxes disagree about CLASS? That is the difference
    # between "which copy" and "which reading".
    print("\nclass agreement by x-offset band:")
    for f in fams:
        fp = [p for p in pairs if p["family"] == f]
        near = [p for p in fp if centre_offset(p)[0] < 0.25]
        far = [p for p in fp if centre_offset(p)[0] >= 0.25]
        def frac(lst):
            return (f"{sum(1 for p in lst if p['same_class'])}/{len(lst)}"
                    if lst else "-")
        print(f"  {f:<20} near(<0.25w) same-class {frac(near):<10} "
              f"far same-class {frac(far)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
