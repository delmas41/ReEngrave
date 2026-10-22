#!/usr/bin/env python3
"""Does a per-DOCUMENT roster pay? — pricing the carry tier.

MEASUREMENT ONLY.

The architecture proposes three storage tiers, and the value is claimed for the
middle one: identity accumulated across the pages of ONE PDF, so that Litolff
naming its winds on p.1 and nothing on p.40 still yields p.40's winds. It is
structurally `transcribe`'s meter carry — including the tagging, so a carried
fact can never be read as an observed one.

This prices it on the 20-row gate, against hand-read page truth.

    OBSERVED   what the page itself resolved (the pipeline's own answer)
    CARRIED    OBSERVED, plus — for a position the page did not resolve — the
               instrument another page of the SAME EDITION resolved at the
               same (system-size, ordinal). Never across editions.

The carry key is `(n_staves_in_system, ordinal)`, not `slot_index`: a slot is
the output of an alignment, and the whole point is to need no alignment. Two
systems that print the same number of staves print the same lineup — the
assumption is stated here because it is the one the carry rests on, and it is
exactly what fails on a page with tacet staves suppressed, which is why the
key includes the size.

⚠️ A wrong carried identity poisons every later page, so this reports carried
PRECISION separately from observed precision. A carry that raises coverage
while lowering precision below the observed rate is refused.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_roster_carry.py

── RESULTS 2026-09-05 ────────────────────────────────────────────────────────
198 records with truth, 20-row `.reconciliation` gate.

    carried over   carried  right  carryP   coverage        pooled precision
    SHIPPED             22     22   1.000   0.884 -> 0.995  0.914 -> 0.924
    HELDOUT             20     11   0.550   0.793 -> 0.894  0.873 -> 0.836

ALL 22 correct carries are SIMROCK -- the publisher that labels the movement's
first page and nothing after. Its coverage goes 0.617 -> 1.000 at precision
1.000, recovering 22 staves on pages that print no label at all. That is the
per-document roster's central claim, measured, and it is perfect here.

⚠️⚠️ THE SAME MECHANISM OVER DERIVED IDENTITY IS ACTIVELY HARMFUL: 0.550, and
it drags pooled precision BELOW the observed rate (0.873 -> 0.836) by
propagating the score-order prior's errors onto every later page.

DESIGN RULE, with a number behind it: THE ROSTER CARRIES OBSERVED
(LABEL-SOURCED) IDENTITY ONLY. Derived identity is recomputed per page, never
carried. This is why provenance must be per-FACT rather than per-file -- the
carry cannot be implemented at all without knowing, for each fact, whether it
was observed or derived. The abstain-on-conflict rule fired once, correctly.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDENT = HERE / "heldout-identity.json"


def edition_of(row_id):
    """`brahms-sym1-mvt1-317803-p3` -> `brahms-sym1-mvt1-317803`.

    ⚠️ The two Beethoven scans are deliberately NOT merged here even though
    they are one engraving: a roster is a property of a PDF, and the carry has
    to be measured as it would actually run.
    """
    return row_id.rsplit("-p", 1)[0]


def main():
    if not IDENT.exists():
        raise SystemExit(f"run probe_heldout_identity.py first ({IDENT})")
    data = json.loads(IDENT.read_text())
    recs = [r for r in data["records"] if r["TRUTH"]]
    print(f"records with truth: {len(recs)}  tag {data['meta']['tag']!r}  "
          f"{data['meta']['n_fixture_rows']} fixture rows")
    if not recs:
        raise SystemExit("REFUSING to report: no records.")

    for base in ("SHIPPED", "HELDOUT"):
        print(f"\n{'='*66}\nCARRY OVER  {base}\n{'='*66}")

        # Build each edition's roster from what its pages observed.
        roster = defaultdict(lambda: defaultdict(Counter))
        for r in recs:
            if r[base]:
                roster[edition_of(r["row_id"])][
                    (r["n_staves"], r["ordinal"])][r[base]] += 1

        n_obs = n_obs_right = 0
        n_carry = n_carry_right = 0
        n_none = 0
        per_pub = defaultdict(lambda: [0, 0, 0, 0])   # obs, obsR, car, carR
        conflicted = 0
        for r in recs:
            pub = r["publisher"]
            ok = set(r["TRUTH_acceptable"])
            if r[base]:
                n_obs += 1
                per_pub[pub][0] += 1
                if r[base] in ok:
                    n_obs_right += 1
                    per_pub[pub][1] += 1
                continue
            tally = roster[edition_of(r["row_id"])].get(
                (r["n_staves"], r["ordinal"]))
            if not tally:
                n_none += 1
                continue
            if len(tally) > 1:
                # The edition's own pages disagree about this position. A
                # roster that cannot agree with itself must ABSTAIN, not
                # majority-vote: the disagreement is the diagnostic.
                conflicted += 1
                n_none += 1
                continue
            got = next(iter(tally))
            n_carry += 1
            per_pub[pub][2] += 1
            if got in ok:
                n_carry_right += 1
                per_pub[pub][3] += 1

        tot = len(recs)
        print(f"  observed   {n_obs:4d}  right {n_obs_right:4d}  "
              f"precision {n_obs_right/n_obs:.3f}" if n_obs else "")
        print(f"  CARRIED    {n_carry:4d}  right {n_carry_right:4d}  "
              f"precision {n_carry_right/n_carry:.3f}" if n_carry
              else "  CARRIED      0  — the carry never fires")
        print(f"  still unresolved {n_none:4d}   "
              f"(of which roster CONFLICTED {conflicted})")
        print(f"  coverage   {n_obs/tot:.3f} -> {(n_obs+n_carry)/tot:.3f}"
              f"   ({n_obs} -> {n_obs+n_carry} of {tot})")
        if n_obs + n_carry:
            print(f"  precision  {n_obs_right/n_obs:.3f} -> "
                  f"{(n_obs_right+n_carry_right)/(n_obs+n_carry):.3f}")
        print(f"  {'publisher':12s} {'obs':>5s} {'obsP':>6s} "
              f"{'carry':>6s} {'carryP':>7s}")
        for pub in sorted(per_pub):
            o, orr, c, cr = per_pub[pub]
            print(f"  {pub:12s} {o:5d} {orr/o if o else 0:6.3f} "
                  f"{c:6d} {cr/c if c else 0:7.3f}")


if __name__ == "__main__":
    main()
