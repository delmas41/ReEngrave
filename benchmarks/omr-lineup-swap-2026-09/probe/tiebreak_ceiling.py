"""Which system wins the reference contest, and what each winner's ceiling is —
computed from a committed label dump, with no run.

`reference_candidates` picks `max(recurring, key=(size, len(labels)))`, and
`max` returns the FIRST maximum, so a tie on both keys is broken by document
order. The tail of the same function is ordered by `(-size, -labels, -shapes)`
— how many systems SHARE the lineup — and the head does not use that term.

This reproduces both contests off a label dump and prints, for each winner, the
best each hand-read region could then score: for a region of the reference's
own size the placement is the identity, so the ceiling is a fixed property of
the reference's vocabulary (see `ceiling.py`).

    tiebreak_ceiling.py LABELS.json --lineups LINEUPS.json
"""
from __future__ import annotations

import argparse
import collections
import json


def systems(rows):
    """`[(page, sysidx, size, (label tuple))]` for every system."""
    out = []
    for r in sorted(rows, key=lambda r: r["page"]):
        by_staff = {l["staff_index"]: l["instrument"] for l in r["labels"]}
        offset = 0
        for si, n in enumerate(r["systems"]):
            out.append((r["page"], si, n,
                        tuple(by_staff.get(offset + k) for k in range(n))))
            offset += n
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels")
    ap.add_argument("--lineups", required=True)
    args = ap.parse_args()

    views = systems(json.load(open(args.labels)))
    sizes = sorted(v[2] for v in views)
    cap = sizes[len(sizes) // 2] * 2.0
    cands = [v for v in views if v[2] <= cap]
    counts = collections.Counter(v[2] for v in cands)
    recurring = [v for v in cands if counts[v[2]] > 1] or cands
    shapes = collections.Counter((v[2], v[3]) for v in recurring)

    def nlab(v):
        return sum(1 for x in v[3] if x)

    top = max((v[2], nlab(v)) for v in recurring)
    tied = [v for v in recurring if (v[2], nlab(v)) == top]
    by_order = tied[0]
    by_shape = max(tied, key=lambda v: shapes[(v[2], v[3])])

    print(f"reference contest: top key = size {top[0]}, labels {top[1]}; "
          f"{len(tied)} system(s) tied")
    for tag, v in (("document order (shipped)", by_order),
                   ("shape frequency", by_shape)):
        print(f"  {tag:26s} p{v[0]} s{v[1]}  shared by "
              f"{shapes[(v[2], v[3])]} system(s)")
        print(f"      {[x or '-' for x in v[3]]}")

    lineups = json.load(open(args.lineups))
    print(f"\n{'region':14s}{'size':>5s}{'systems':>9s}"
          f"{'ceiling(order)':>16s}{'ceiling(shape)':>16s}")
    tot = [0, 0]
    for row in lineups:
        n = sum(1 for v in views
                if row["first"] <= v[0] <= row["last"] and v[2] == row["size"])
        cells = []
        for v in (by_order, by_shape):
            cells.append(sum(1 for a, b in zip(row["lineup"], v[3]) if a == b)
                         if v[2] == row["size"] else None)
        for i, c in enumerate(cells):
            if c is not None:
                tot[i] += c * n
        fmt = [f"{c}/{row['size']}" if c is not None else "n/a" for c in cells]
        print(f"{str(row['first']) + '-' + str(row['last']):14s}"
              f"{row['size']:5d}{n:9d}{fmt[0]:>16s}{fmt[1]:>16s}")
    print(f"{'TOTAL (same-size regions only)':47s}{tot[0]:>10d}{tot[1]:>16d}")
    print("\n⚠️ The ceiling is over the regions whose size equals the "
          "reference's; a region of a DIFFERENT size is aligned by "
          "subsequence and is not fixed by this arithmetic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
