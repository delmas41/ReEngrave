"""Can the document's slot space SAY what each span's lineup is?

The span machinery moves a staff to a different SLOT. It cannot change what a
slot is CALLED: `build_reference` picks ONE printed system as the document
reference and `slot_instruments` gives each slot one name for the whole
document. So a span's lineup can only be named correctly if it is a
SUBSEQUENCE of that reference's names.

The count axiom guarantees exactly that, and this probe is how one sees it: a
boundary taken only where the lineup GREW means the last span's lineup is a
superset of every earlier one, so the largest printed system holds them all.
**A swap boundary carries no such guarantee** — two lineups that each contain a
name the other lacks cannot both be subsequences of any single printed system,
because no printed system of that document contains both.

    expressibility.py LINEUPS.json [LINEUPS.json ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _scs(a, b):
    """Shortest common supersequence of two lineups, via their LCS.

    The union of two lineups is not their concatenation and it is not their
    set: `Horn Horn` is two staves and `Violin Violin` is two different parts,
    so the merge has to keep multiplicity while sharing what the two agree on
    IN SCORE ORDER. That is exactly the SCS.
    """
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = (1 + dp[i + 1][j + 1] if a[i] == b[j]
                        else max(dp[i + 1][j], dp[i][j + 1]))
    out, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    return out + a[i:] + b[j:]


def is_subsequence(small, big) -> bool:
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def main() -> int:
    for path in sys.argv[1:]:
        lineups = json.load(open(path))
        print(f"\n=== {Path(path).stem}")
        biggest = max(lineups, key=lambda r: len(r["lineup"]))
        print(f"  largest printed lineup: {len(biggest['lineup'])} staves "
              f"(pages {biggest['first']}-{biggest['last']})")
        union: list[str] = []
        for row in lineups:                      # shortest common supersequence
            union = _scs(union, row["lineup"])
        print(f"  union over spans      : {len(union)} staves  {union}")
        ok = True
        for row in lineups:
            good = is_subsequence(row["lineup"], biggest["lineup"])
            ok &= good
            missing = [n for n in row["lineup"]
                       if row["lineup"].count(n)
                       > biggest["lineup"].count(n)]
            print(f"  pages {row['first']:3d}-{row['last']:3d} "
                  f"({len(row['lineup']):2d}): expressible in the largest "
                  f"printed lineup? {'YES' if good else 'NO '}"
                  + (f"   short of: {sorted(set(missing))}" if missing else ""))
        verdict = ("EVERY span is expressible — the document reference can "
                   "name them all" if ok else
                   "AT LEAST ONE span is NOT expressible — no choice of span "
                   "boundaries can name it")
        print(f"  => {verdict}")
        print(f"  => union {len(union)} vs largest printed "
              f"{len(biggest['lineup'])}: "
              + ("equal, growth-only" if len(union) == len(biggest["lineup"])
                 else f"a swap, {len(union) - len(biggest['lineup'])} names "
                      "with nowhere to live"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
