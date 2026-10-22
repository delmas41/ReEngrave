#!/usr/bin/env python3
"""Every claim the roster rule would make, over every roster the catalog holds.

⚠️ **The reference corpus fires ZERO times in `probe_roster_reach.py` and that
is a VACUOUS result.** Those 1271 part names carry no work, so the layer cannot
touch them by construction; reporting "no regression" from it would be reporting
that a switched-off thing is off. This is the same corpora crossed with all 219
rosters instead: for every distinct string either corpus produces, ask what the
rule would do under EACH work in the store.

That is a strictly harder test than production faces — a Ravel margin string is
scored against Bach's roster — and it is the only way to see the rule's
false-positive surface rather than the handful of works two corpora happen to
name.

    python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_false_positives.py

Output is one row per DISTINCT claim (string, before, after), with how many
rosters make it. Every one is meant to be adjudicated by hand — see FINDINGS.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import instruments                            # noqa: E402
from tools.omr import work_roster as wr                      # noqa: E402

LEXICON = ROOT / "benchmarks" / "omr-lexicon-2026-09"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=BENCH / "false-positives.json")
    ap.add_argument("--max-rows", type=int, default=60)
    args = ap.parse_args(argv)

    strings = {rec["text"] for rec in
               json.loads((LEXICON / "labels.json").read_text())}
    strings |= set(json.loads((LEXICON / "part-names.json").read_text()))
    strings = sorted(s for s in strings if s and s.strip())

    catalog = json.loads((ROOT / "data" / "score-library" / "catalog.json").read_text())
    rosters = [r for r in (wr.work_roster(wid) for wid in sorted(catalog["works"]))
               if r is not None]
    print(f"{len(strings)} distinct strings x {len(rosters)} rosters "
          f"= {len(strings) * len(rosters)} decisions")

    hits = {s: instruments.lookup(s) for s in strings}
    claims: collections.Counter = collections.Counter()
    kinds: collections.Counter = collections.Counter()
    for roster in rosters:
        for s in strings:
            d = wr.decide(s, roster, hit=hits[s])
            if d.kind == "unchanged":
                continue
            kinds[d.kind] += 1
            claims[(d.kind, s,
                    hits[s].instrument.name if hits[s] else None,
                    d.match.instrument.name if d.match else None)] += 1

    print(f"\nfirings: {dict(kinds)}")
    print(f"{len(claims)} distinct claims\n")
    print(f"{'rosters':>7}  {'kind':13} {'string':34} "
          f"{'lexicon':>15} -> {'roster'}")
    for (kind, s, before, after), n in claims.most_common(args.max_rows):
        print(f"{n:7d}  {kind:13} {s!r:34} {str(before):>15} -> {after}")
    if len(claims) > args.max_rows:
        print(f"  … {len(claims) - args.max_rows} more, see {args.out}")

    args.out.write_text(json.dumps(
        {"n_strings": len(strings), "n_rosters": len(rosters),
         "kinds": dict(kinds),
         "claims": [{"kind": k, "text": s, "before": b, "after": a, "rosters": n}
                    for (k, s, b, a), n in claims.most_common()]},
        indent=1) + "\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
