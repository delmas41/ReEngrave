#!/usr/bin/env python3
"""Which pairwise order relations are TRADITION-INDEPENDENT? — the source audit.

MEASUREMENT ONLY.

⚠️ A RELATION IS ONLY AS GOOD AS ITS SOURCE, AND MINE IS THE SAME TEN LAYOUTS.
"Trombone below Horn" is page-independent only if it holds in EVERY tradition —
and `probe_vocabulary_vs_alignment.py` measured that brass is exactly where it
does not (Horn x5 + Trombone x4 ORDER CONFLICTS, entirely within that family,
against every other family order-stable across all three arms). A pair asserted
from a single layout is a template in disguise, which is the trap one level up.

So a pair (A before B) is admitted only where EVERY layout that contains both
agrees on the direction. Pairs the layouts disagree about are not "resolved by
majority" — they are DROPPED, and the drop is the finding: it is where the page
must speak for itself.

This probe reports:
    how many ordered pairs are expressible at all,
    how many survive unanimity,
    which families the casualties fall in,
    and how much of the corpus's own truth the survivors actually cover.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_order_consensus.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST         # noqa: E402
from tools.omr.score_layouts import LAYOUTS       # noqa: E402

IDENT = HERE / "heldout-identity.json"


def family(name):
    m = INST.lookup(name)
    return m.instrument.family if m else "?"


def build_consensus():
    """(unanimous pairs, contested pairs, per-layout pair counts)."""
    seen = defaultdict(Counter)      # (A,B) sorted -> Counter of direction
    for layout in LAYOUTS:
        parts = list(layout.parts)
        idx = {p: i for i, p in enumerate(parts)}
        for a, b in combinations(sorted(set(parts)), 2):
            if a in idx and b in idx:
                key = (a, b)
                seen[key]["a_first" if idx[a] < idx[b] else "b_first"] += 1
    unanimous, contested = {}, {}
    for key, tally in seen.items():
        if len(tally) == 1:
            direction = next(iter(tally))
            a, b = key
            unanimous[key] = (a, b) if direction == "a_first" else (b, a)
        else:
            contested[key] = dict(tally)
    return unanimous, contested


def main():
    unanimous, contested = build_consensus()
    total = len(unanimous) + len(contested)
    print(f"ORDERED PAIRS EXPRESSIBLE BY THE TEN LAYOUTS: {total}")
    print(f"  unanimous (admitted)  {len(unanimous):4d}  "
          f"{len(unanimous)/total:.3f}")
    print(f"  contested (DROPPED)   {len(contested):4d}  "
          f"{len(contested)/total:.3f}")

    print(f"\nCONTESTED PAIRS — where the layouts disagree, so the page must "
          f"speak")
    fam = Counter()
    for (a, b), tally in sorted(contested.items()):
        fa, fb = family(a), family(b)
        fam[tuple(sorted((fa, fb)))] += 1
        print(f"   {a:16s} vs {b:16s}  {fa:10s}/{fb:10s}  {tally}")
    print(f"\n  contested pairs by family pair: {dict(fam)}")

    within_brass = sum(1 for (a, b) in contested
                       if family(a) == "brass" == family(b))
    all_brass_pairs = sum(1 for (a, b) in list(unanimous) + list(contested)
                          if family(a) == "brass" == family(b))
    print(f"\n  ⭑ brass-internal pairs contested: {within_brass} of "
          f"{all_brass_pairs}"
          f"   ({within_brass/all_brass_pairs if all_brass_pairs else 0:.3f})")
    other = len(contested) - within_brass
    print(f"    all other contested pairs:      {other}")

    # ── does the admitted relation actually reach this corpus's truth? ──────
    if not IDENT.exists():
        print("\n(no heldout-identity.json; skipping corpus coverage)")
        return
    recs = [r for r in json.loads(IDENT.read_text())["records"] if r["TRUTH"]]
    by_sys = defaultdict(list)
    for r in recs:
        by_sys[(r["row_id"], r["system_index"])].append(r)
    constrained = agree = 0
    for key, group in by_sys.items():
        group.sort(key=lambda r: r["ordinal"])
        lineup = [r["TRUTH"] for r in group]
        for i, j in combinations(range(len(lineup)), 2):
            a, b = lineup[i], lineup[j]
            if a == b:
                continue
            rel = unanimous.get((a, b)) or unanimous.get((b, a))
            if not rel:
                continue
            constrained += 1
            if rel == (a, b):        # relation says a before b; page has a above
                agree += 1
    print(f"\nDOES THE ADMITTED RELATION MATCH THIS CORPUS'S PAGES?")
    print(f"  truth pairs an admitted relation speaks about: {constrained}")
    print(f"  ...where the page AGREES with the relation:    {agree}"
          f"   ({agree/constrained if constrained else 0:.3f})")
    print(f"\n  ⚠️ This is the relation's OWN accuracy against hand-read page"
          f" truth.\n     A relation that the pages themselves contradict is"
          f" not usable however\n     unanimous the layouts were.")

    (HERE / "order-consensus.json").write_text(json.dumps({
        "n_pairs": total, "n_unanimous": len(unanimous),
        "n_contested": len(contested),
        "unanimous": [list(v) for v in unanimous.values()],
        "contested": {f"{a}|{b}": t for (a, b), t in contested.items()},
        "corpus_pairs_constrained": constrained, "corpus_pairs_agree": agree,
    }, indent=1))


if __name__ == "__main__":
    main()
