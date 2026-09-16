"""Find the STAFF LINES in an extracted system crop, by ink row profile.

⚠️ Eyeballing which staff a notehead sits on is exactly the mistake this repo
has paid for twice (`_refit_misaligned_group`, and the hairpin attribution).
The crops are bitonal scans of a 19th-century plate, so a staff line is a row
of ink running most of the width -- countable, not a matter of opinion.

Prints one line per detected five-line group, so a note's y can be turned into
a staff and a STEP by hand afterwards with `--y`.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
from PIL import Image


def line_rows(img, frac=0.55):
    a = np.asarray(img.convert("L"))
    ink = (a < 128).mean(axis=1)
    return ink, np.where(ink > frac)[0]


def groups(rows, gap=4):
    out, cur = [], []
    for r in rows:
        if cur and r - cur[-1] > gap:
            out.append(cur)
            cur = []
        cur.append(r)
    if cur:
        out.append(cur)
    return [float(np.mean(g)) for g in out]


def staves_from_rows(ys, min_rows=4):
    """Group detected line rows into five-line staves by the GAP between them.

    ⚠️ A greedy "take the next five rows whose gaps agree" scan fails the moment
    ONE line of a staff is faint -- it then eats a row from the staff below and
    every staff after it is off by one. Measured on the committed crops it found
    9 staves of 11 and silently renumbered the rest, which would have named the
    wrong instrument for every bar adjudicated after it.

    A staff's own lines sit one SPACING apart; the gap to the next staff is
    several times that, so the split is a cliff and not a threshold. A group of
    four rows is a staff with one faint line: the missing row is RECONSTRUCTED
    from the group's own regular spacing rather than dropped, because dropping
    it is what renumbers everything below.
    """
    if len(ys) < min_rows:
        return []
    gaps = sorted(np.diff(ys))
    intra = float(np.median(gaps[:max(1, int(0.6 * len(gaps)))]))
    groups, cur = [], [ys[0]]
    for a, b in zip(ys, ys[1:]):
        if b - a > 2.0 * intra:
            groups.append(cur)
            cur = []
        cur.append(b)
    groups.append(cur)

    out = []
    for g in groups:
        if len(g) == 5:
            out.append(g)
        elif len(g) == 4:
            sp = (g[-1] - g[0]) / 3.0
            # Which of the five rows is missing: the one whose slot has no row.
            d = np.diff(g)
            k = int(np.argmax(d))
            if d[k] > 1.5 * sp * 3 / 4:          # a doubled gap inside the group
                g = g[:k + 1] + [g[k] + d[k] / 2.0] + g[k + 1:]
            else:                                 # an END line is missing
                g = g + [g[-1] + sp] if True else g
            out.append(g[:5] if len(g) >= 5 else g)
    return [g for g in out if len(g) == 5]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--img", required=True)
    ap.add_argument("--frac", type=float, default=0.55)
    ap.add_argument("--y", type=float, action="append", default=[],
                    help="a notehead centre y in crop pixels; reported as a step")
    a = ap.parse_args()

    im = Image.open(a.img)
    ink, rows = line_rows(im, a.frac)
    ys = groups(rows)
    if len(ys) < 5:
        print(f"DEAD: only {len(ys)} line-like rows at frac={a.frac}",
              file=sys.stderr)
        return 2

    staves = staves_from_rows(ys)
    print(f"REACH  {im.size[0]}x{im.size[1]}  line-rows={len(ys)}  "
          f"five-line staves={len(staves)}")
    for k, s in enumerate(staves):
        sp = (s[4] - s[0]) / 4.0
        print(f"  staff {k}: top={s[0]:.1f} bottom={s[4]:.1f} spacing={sp:.2f} "
              f"lines={[round(v, 1) for v in s]}")

    for y in a.y:
        print(f"\n  y={y}")
        for k, s in enumerate(staves):
            sp = (s[4] - s[0]) / 4.0
            step = (s[4] - y) / (sp / 2.0)
            if -14 <= step <= 22:
                print(f"     on staff {k}: step {step:+.2f} "
                      f"({'inside' if 0 <= step <= 8 else 'outside'} the staff)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
