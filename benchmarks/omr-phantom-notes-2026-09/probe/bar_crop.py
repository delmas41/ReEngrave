"""Cut ONE printed bar of ONE printed staff out of an extracted system crop.

⚠️ This is how the print gets adjudicated in a container with no weights and no
`library/`. The system crops embedded in the committed side-by-side artefact
are the only copy of the Litolff plate that reaches this session.

Staves come from `staff_rows` (a five-line group of ink rows). Barlines come
from ink COLUMNS that run the full height of the system -- the same fact
`measure_extractor` uses, and the reason a note stem does not qualify.

⚠️ The bar index it cuts is the PRINTED one, counted left to right from the
system's opening barline. Whether that equals the exporter's cell index is the
thing being checked, so the probe prints how many bars it found and refuses to
guess when that disagrees with what was asked for.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from staff_rows import groups, line_rows, staves_from_rows  # noqa: E402


def staves_of(im, frac=0.40):
    _, rows = line_rows(im, frac)
    return staves_from_rows(groups(rows))


def barlines(im, top, bottom, frac=0.80, min_gap=25):
    """Columns inked through the WHOLE staff band -- a barline, not a stem.

    A stem is at most ~3.5 spaces tall inside a 4-space staff, so demanding
    ink over `frac` of the band's height already excludes most of them; the
    residue is thinned by keeping one column per run.
    """
    a = np.asarray(im.convert("L"))[int(top):int(bottom) + 1]
    col = (a < 128).mean(axis=0)
    cand = np.where(col > frac)[0]
    out = []
    for c in cand:
        if not out or c - out[-1][-1] > 3:
            out.append([c])
        else:
            out[-1].append(c)
    xs = [float(np.mean(r)) for r in out]
    keep = []
    for x in xs:
        if not keep or x - keep[-1] > min_gap:
            keep.append(x)
    return keep


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--img", required=True)
    ap.add_argument("--staff", type=int, required=True)
    ap.add_argument("--bar", type=int, action="append", default=[])
    ap.add_argument("--pad-spaces", type=float, default=5.0)
    ap.add_argument("--scale", type=float, default=3.0)
    ap.add_argument("--frac", type=float, default=0.40)
    ap.add_argument("--bl-frac", type=float, default=0.80,
                    help="ink share of the system band a barline column must have")
    ap.add_argument("--expect", type=int, default=None,
                    help="bars the system map says this staff has; refuses on a mismatch")
    ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args()

    im = Image.open(a.img)
    sts = staves_of(im, a.frac)
    print(f"REACH  {a.img}: {len(sts)} five-line staves detected")
    if a.staff >= len(sts):
        print(f"DEAD: asked for staff {a.staff}", file=sys.stderr)
        return 2
    five = sts[a.staff]
    sp = (five[4] - five[0]) / 4.0
    # Barlines are looked for over the WHOLE system, so a staff that happens to
    # print no full-height ink of its own still gets the system's bar grid.
    top, bottom = sts[0][0], sts[-1][4]
    bl = barlines(im, top, bottom, frac=a.bl_frac)
    print(f"REACH  system band y={top:.0f}..{bottom:.0f}; "
          f"{len(bl)} full-height columns -> {max(0, len(bl) - 1)} bars")
    print(f"       columns: {[round(x) for x in bl]}")
    print(f"       staff {a.staff}: lines {[round(v,1) for v in five]} spacing {sp:.2f}")

    if a.expect is not None and len(bl) - 1 != a.expect:
        print(f"REFUSED: found {len(bl)-1} bars, the system map says {a.expect}. "
              f"A bar index read off a grid that disagrees with the map names "
              f"the wrong bar, which is worse than no crop.", file=sys.stderr)
        return 3

    for b in a.bar:
        if b + 1 >= len(bl):
            print(f"  bar {b}: NOT PRESENT (only {len(bl)-1} bars)")
            continue
        x0, x1 = bl[b], bl[b + 1]
        y0 = five[0] - a.pad_spaces * sp
        y1 = five[4] + a.pad_spaces * sp
        cut = im.crop((int(x0), int(max(0, y0)), int(x1), int(min(im.size[1], y1))))
        cut = cut.resize((int(cut.width * a.scale), int(cut.height * a.scale)),
                         Image.LANCZOS)
        p = f"{a.out_prefix}_s{a.staff}_b{b}.png"
        cut.save(p)
        print(f"  bar {b}: x {x0:.0f}..{x1:.0f} -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
