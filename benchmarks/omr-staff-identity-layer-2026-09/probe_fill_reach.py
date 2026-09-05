#!/usr/bin/env python3
"""Why did the FILL path move so little? — the reach diagnostic, no scoring.

MEASUREMENT ONLY, and deliberately CHEAP: it runs the same identity supplies as
`price_clef_consumer.py` but never exports or scores, so it answers "how many
staves could this consumer even touch" in seconds.

`clef_correction`'s FILL path is `do_apply = apply and not detected` (:597): a
staff takes its instrument's default clef only where NO reader read one. So the
consumer's reach is the INTERSECTION of two populations:

    staves an identity layer newly names   x   staves with no clef read

and either one being large tells you nothing. This prints both and their
overlap, per arm and per row, which is what turns an edit delta into an
explanation.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_fill_reach.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

import price_clef_consumer as P  # noqa: E402
sys.path.insert(0, str(HERE))
from price_clef_consumer import (  # noqa: E402
    FIXTURES, TAG, RAW_CLEF_SOURCES, systems_of, tier_a, tier_b, tier_c,
    build_roster, edition_of, rows, apply_arm)


def main():
    paths = rows()
    print(f"FIXTURES {FIXTURES}\nTAG {TAG!r}   rows {len(paths)}")
    if len(paths) != 20:
        raise SystemExit(f"expected the 20-row gate, found {len(paths)}")
    roster = build_roster(paths)

    print(f"\n{'row':34s} {'staves':>6s} {'noclef':>7s} "
          f"{'B_sup':>6s} {'B_app':>6s} {'C_sup':>6s} {'C_app':>6s}")
    tot = Counter()
    for p in paths:
        rid = p.name[: -len(f"{TAG}.omr.json")].rstrip(".")
        fx = json.loads(p.read_text())
        n_st = n_noclef = 0
        for _, _, _, staves in systems_of(fx):
            n_st += len(staves)
            n_noclef += sum(
                1 for s in staves
                if s.get("clef_source") not in RAW_CLEF_SOURCES)
        _, b_sup, b_app = apply_arm(json.loads(p.read_text()), roster, rid,
                                    use_b=True, use_c=False)
        _, c_sup, c_app = apply_arm(json.loads(p.read_text()), roster, rid,
                                    use_b=False, use_c=True)
        tot["staves"] += n_st; tot["noclef"] += n_noclef
        tot["B_sup"] += b_sup; tot["B_app"] += b_app
        tot["C_sup"] += c_sup; tot["C_app"] += c_app
        print(f"{rid:34s} {n_st:6d} {n_noclef:7d} "
              f"{b_sup:6d} {b_app:6d} {c_sup:6d} {c_app:6d}")
    print(f"\n{'TOTAL':34s} {tot['staves']:6d} {tot['noclef']:7d} "
          f"{tot['B_sup']:6d} {tot['B_app']:6d} "
          f"{tot['C_sup']:6d} {tot['C_app']:6d}")
    print("\n  sup = staves this tier newly supplies an identity for")
    print("  app = of those, staves where the FILL path actually applied a clef")


if __name__ == "__main__":
    main()
