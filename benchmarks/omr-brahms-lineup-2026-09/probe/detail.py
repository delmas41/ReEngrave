"""Every wrong judgeable record, per arm — and the whole-document Tuba count.

Two things the summary table cannot show:

* WHICH staves each arm gets wrong, so the `refuse`-vs-`search` difference can
  be read as music rather than as a delta of one;
* how many staves are called `Tuba` ANYWHERE in the document.  Brahms 1 has no
  tuba (IMSLP `InstrDetail` "3, 0"), so every one is certainly wrong — but the
  `impossible` counter that scored this fix only looks at pages BEFORE the
  finale, so the finale's own Tubas were never counted.

Usage:  detail.py TAG=BLOB.json ...
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_brahms_lineups import LINEUPS, arm, blob_of  # noqa: E402


def main() -> int:
    for a in sys.argv[1:]:
        tag, path = a.split("=", 1)
        blob = blob_of(path)
        slot, name, _vet = arm(blob)
        size = collections.Counter()
        sysstaves = collections.defaultdict(list)
        for (p, sy, st) in slot:
            size[(p, sy)] += 1
            sysstaves[(p, sy)].append(st)
        for v in sysstaves.values():
            v.sort()

        print(f"===== {tag}   ({path})")
        tuba = [(p, sy, st) for (p, sy, st), s in slot.items()
                if name.get(s) == "Tuba"]
        pre = sum(1 for p, _, _ in tuba if p < 45)
        print(f"  `Tuba` staff-records document-wide: {len(tuba)} "
              f"({pre} before page 45, {len(tuba) - pre} in the finale) "
              "— Brahms 1 has no tuba, so all of them are wrong")

        seen = collections.Counter()
        for (p, sy), stx in sorted(sysstaves.items()):
            names = None
            for lo, hi, k, nm in LINEUPS["brahms1"]:
                if lo <= p <= hi and len(stx) == k:
                    names = nm
                    break
            if names is None:
                continue
            bad = []
            for i, st in enumerate(stx):
                got = name.get(slot[(p, sy, st)])
                if got != names[i]:
                    bad.append(f"#{i} {names[i]}->{got}")
            if bad:
                seen[" | ".join(bad)] += 1
        print("  wrong-record PATTERNS over the judgeable systems:")
        for k, n in seen.most_common():
            print(f"    {n:3d} systems:  {k}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
