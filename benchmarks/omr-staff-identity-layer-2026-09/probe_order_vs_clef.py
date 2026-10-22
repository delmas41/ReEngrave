#!/usr/bin/env python3
"""Order or clef — which carries the weight? And what does ONE anchor buy?

MEASUREMENT ONLY.

⚠️ THIS PROBE EXISTS BECAUSE I CONFLATED TWO CLAIMS. I measured that an added
pairwise ordering constraint fires zero times and wrote that up in a way a
reader would take as "order does not matter". Those are different sentences and
only the first is supported:

    "an ADDED order constraint would fire zero times"   TRUE, and measured
    "order does not matter"                             DOES NOT FOLLOW

`align_to_layout`'s DP is MONOTONE, so it already exploits order exhaustively.
That is precisely WHY a re-assertion of order cannot fire. My "0 of 15 systems
violate layout order" test therefore demonstrates that the aligner is monotone
— close to a tautology — and says nothing about whether order is informative.
**Order is not unused; it is already load-bearing.** The correct finding is
"order is already fully exploited, so re-asserting it is vacuous."

THE NUMBER THAT MAKES THE POINT: the FLOOR arm — position alone, no clef, no
label — scores precision 0.742. Order by itself gets three-quarters of the way;
with clef it is 0.873.

THE MISSING CELL. Clef WITHOUT order has never been measured, and the whole
attribution rests on it:

    order only (FLOOR)               0.742 @ coverage 0.313   measured
    clef only, ORDER DESTROYED       <- this probe
    order + clef (HELDOUT)           0.873 @ coverage 0.793   measured

⚠️ PRE-REGISTERED, both directions:
    clef-only far BELOW 0.742  -> order dominates, and my "the limit is
                                  evidence (the clef)" conclusion is
                                  mis-attributed;
    clef-only ~ 0.742          -> the two are largely redundant;
    clef-only far ABOVE 0.742  -> clef dominates after all and the FLOOR number
                                  was flattering order. Say so.

⚠️ COVERAGE IS REPORTED BESIDE PRECISION IN EVERY CELL. FLOOR's 0.742 comes at
coverage 0.313 and the two arms are not comparable without it.

SECOND QUESTION — ANCHORED PROPAGATION. The circularity I found (clef needs
identity, identity needs clef) is broken by ANY anchor, because order is
independent of both. One observed margin label plus order plus uniqueness
constrains its neighbours, and those constrain theirs. This measures the curve:
given k observed labels, how many of the REMAINING staves does the alignment
get right? Reported with the marginal value of the FIRST anchor, and by anchor
POSITION (a mid-page anchor constrains in both directions and should be worth
more than an edge one).

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_order_vs_clef.py

── RESULT 2026-09-05: ORDER DOMINATES. MY ATTRIBUTION WAS WRONG. ─────────────
198 records, 15 systems, 20-row `.reconciliation` gate.

    arm                            named  coverage  right  precision
    order only (FLOOR)                62     0.313     46      0.742
    clef only, ORDER DESTROYED        11     0.056      9      0.818
    order + clef (HELDOUT)           157     0.793    137      0.873

⚠️⚠️ CLEF ALONE NAMES ELEVEN STAVES OF 198. Its coverage is 0.056 against
order's 0.313 — a factor of 5.6 — and the reason is structural, not
circumstantial: of the 25 instruments the layouts know, the clef partition is
`alto: 1, bass: 8, treble: 16`. Only the alto clef is unique to one instrument
(Viola), so a clef can NAME a staff almost nowhere. Its 0.818 precision is
computed on those eleven trivially-identifiable staves and is not comparable to
the others.

PRE-REGISTERED READING, first branch: clef-only is far BELOW the FLOOR arm, so
ORDER CARRIES THE WEIGHT and my earlier conclusion — "the limit is evidence,
i.e. the clef" — IS MIS-ATTRIBUTED. The honest relation is that order is the
dominant signal and clef is a REFINEMENT that multiplies its reach: order alone
covers 0.313, and adding clef takes it to 0.793 while raising precision
0.742 -> 0.873. Neither is a substitute for the other, but only one of them can
stand alone.

MULTIPLICITY — 18 of the 61 wrong-or-abstained staves (0.295) sit in a
duplicated-instrument position. Horn 1 versus Horn 2 is indistinguishable by
clef, range or label TEXT; only vertical position separates them. Nearly a
third of the residual is therefore reachable by order and by nothing else, and
no scoring change could ever touch it.

── ANCHORED PROPAGATION: WEAK. THE "ONE LABEL" ARCHITECTURE IS NOT SUPPORTED. ─
Oracle anchors, mean over 24 random anchor sets, scored only on the UNREVEALED
staves:

    k anchors  coverage  precision  right-per-staff
            0     0.793      0.873            0.692
            1     0.819      0.858            0.703
            2     0.846      0.851            0.720
            3     0.877      0.816            0.716
            6     0.938      0.781            0.733

⚠️ THE FIRST ANCHOR IS WORTH +0.011 right-per-staff, and six anchors +0.041.
Anchors buy COVERAGE (0.793 -> 0.938) and SPEND PRECISION (0.873 -> 0.781),
leaving the number of staves actually named correctly close to flat. So
identity does NOT propagate along the system the way the hypothesis needed: the
alignment is already near its ceiling without anchors, and forcing it to
accommodate one drags its neighbours.

⇒ "Find one good label per page and let order do the rest" is NOT supported by
this corpus. The label ladder should not be re-motivated as anchor acquisition
on the strength of it.

⚠️ THIS DOES NOT CONTRADICT THE ROSTER CARRY (22/22 at precision 1.000). That
is a different mechanism: carrying an observed label to the SAME position on
ANOTHER page, not propagating it to NEIGHBOURS on this one. Same-slot transfer
works; along-system propagation does not.

ANCHOR POSITION behaves as predicted, but weakly: middle 0.754, bottom 0.710,
top 0.699. A mid-page anchor does constrain in both directions and is worth
more — by 0.055 over a top anchor, on n=15 systems.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                    # noqa: E402
from tools.omr.score_layouts import LAYOUTS, fit_layouts     # noqa: E402

IDENT = HERE / "heldout-identity.json"
SEED = 20260905
N_SAMPLES = 24


def load():
    ident = json.loads(IDENT.read_text())
    by_sys = defaultdict(list)
    for r in ident["records"]:
        if r["TRUTH"]:
            by_sys[(r["row_id"], r["system_index"])].append(r)
    for g in by_sys.values():
        g.sort(key=lambda r: r["ordinal"])
    return ident, by_sys


def default_clef(name):
    m = INST.lookup(name)
    return m.instrument.default_clef if m else None


def main():
    ident, by_sys = load()
    n_rec = sum(len(g) for g in by_sys.values())
    print(f"systems {len(by_sys)}   staff records with truth {n_rec}   "
          f"tag {ident['meta']['tag']!r}")
    if not n_rec:
        raise SystemExit("REFUSING to report: no records.")

    # every instrument any layout knows — the pool an unordered matcher draws on
    pool = sorted({p for l in LAYOUTS for p in l.parts})
    clef_of = {p: default_clef(p) for p in pool}
    by_clef = defaultdict(list)
    for p, c in clef_of.items():
        if c:
            by_clef[c].append(p)
    print(f"instrument pool {len(pool)}   "
          f"instruments per clef: "
          f"{ {c: len(v) for c, v in sorted(by_clef.items())} }")

    # ── THE ABLATION ────────────────────────────────────────────────────────
    def score(named_fn):
        tot = named = right = 0
        for key, group in by_sys.items():
            n = len(group)
            clefs = {i: r["clef_read"] for i, r in enumerate(group)
                     if r["clef_read"]}
            got = named_fn(n, clefs, group)
            for i, r in enumerate(group):
                tot += 1
                g = got.get(i)
                if g:
                    named += 1
                    if g in r["TRUTH_acceptable"]:
                        right += 1
        return tot, named, named / tot, right, (right / named if named else 0.0)

    def arm_floor(n, clefs, group):
        fit = fit_layouts(n, labels=None, clefs=None)
        return {i: fit.assignment[i] for i in range(n)
                if fit and fit.assignment[i]} if fit else {}

    def arm_heldout(n, clefs, group):
        fit = fit_layouts(n, labels=None, clefs=clefs or None)
        return {i: fit.assignment[i] for i in range(n)
                if fit and fit.assignment[i]} if fit else {}

    def arm_clef_only(n, clefs, group):
        """UNORDERED best match per staff on the clef alone.

        Order is destroyed by construction: each staff is resolved
        INDEPENDENTLY, with no monotonicity and no reference to its
        neighbours. A staff is named only where its read clef admits exactly
        ONE instrument in the pool — anything else is an abstention, which is
        the honest answer for a signal that cannot discriminate.
        """
        out = {}
        for i in range(n):
            c = clefs.get(i)
            if not c:
                continue
            cands = by_clef.get(c, [])
            if len(cands) == 1:
                out[i] = cands[0]
        return out

    print(f"\n{'='*72}\nTHE ABLATION\n{'='*72}")
    print(f"  {'arm':30s} {'n':>4s} {'named':>6s} {'coverage':>9s} "
          f"{'right':>6s} {'precision':>10s}")
    rows = [("order only (FLOOR)", arm_floor),
            ("clef only, ORDER DESTROYED", arm_clef_only),
            ("order + clef (HELDOUT)", arm_heldout)]
    results = {}
    for label, fn in rows:
        tot, named, cov, right, prec = score(fn)
        results[label] = (cov, prec, named)
        print(f"  {label:30s} {tot:4d} {named:6d} {cov:9.3f} {right:6d} "
              f"{prec:10.3f}")

    print(f"\n  Instruments sharing each clef is why the unordered arm cannot"
          f" speak:\n  a clef names an instrument only where it is unique to"
          f" it.")

    # ── MULTIPLICITY: only order can resolve it ─────────────────────────────
    wrong_mult = wrong_tot = 0
    for key, group in by_sys.items():
        c = Counter(r["TRUTH"] for r in group)
        for r in group:
            if (not r["HELDOUT"]) or r["HELDOUT"] not in r["TRUTH_acceptable"]:
                wrong_tot += 1
                if c[r["TRUTH"]] > 1:
                    wrong_mult += 1
    print(f"\n{'='*72}\nMULTIPLICITY — the cases ONLY order can resolve\n{'='*72}")
    print(f"  wrong-or-abstained staves: {wrong_tot}")
    print(f"  ...in a DUPLICATED-instrument position: {wrong_mult}"
          f"  ({wrong_mult/wrong_tot if wrong_tot else 0:.3f})")
    print("  Horn 1 vs Horn 2 is indistinguishable by clef, range or label"
          " text.\n  Only vertical position separates them, so no scoring"
          " change could.")

    # ── ANCHORED PROPAGATION ────────────────────────────────────────────────
    print(f"\n{'='*72}\nANCHORED PROPAGATION — what does ONE label buy?\n{'='*72}")
    rng = random.Random(SEED)
    print(f"  {'k anchors':>9s} {'coverage':>9s} {'precision':>10s} "
          f"{'right/rest':>12s}   (mean over {N_SAMPLES} random anchor sets)")
    curve = {}
    for k in range(0, 7):
        tot = named = right = 0
        for key, group in by_sys.items():
            n = len(group)
            if k > n:
                continue
            clefs = {i: r["clef_read"] for i, r in enumerate(group)
                     if r["clef_read"]}
            for _ in range(N_SAMPLES if k else 1):
                anchors = rng.sample(range(n), k) if k else []
                labels = {i: group[i]["TRUTH"] for i in anchors}
                fit = fit_layouts(n, labels=labels or None, clefs=clefs or None)
                for i in range(n):
                    if i in anchors:
                        continue          # score only the UNREVEALED staves
                    tot += 1
                    g = fit.assignment[i] if fit else None
                    if g:
                        named += 1
                        if g in group[i]["TRUTH_acceptable"]:
                            right += 1
        cov = named / tot if tot else 0
        prec = right / named if named else 0
        curve[k] = (cov, prec, right / tot if tot else 0)
        print(f"  {k:9d} {cov:9.3f} {prec:10.3f} {right/tot if tot else 0:12.3f}")
    d0 = curve[1][2] - curve[0][2]
    print(f"\n  ⭑ MARGINAL VALUE OF THE FIRST ANCHOR: "
          f"right-per-staff {curve[0][2]:.3f} -> {curve[1][2]:.3f}  ({d0:+.3f})")

    # anchor POSITION
    print(f"\n  ANCHOR POSITION (k=1), right-per-unrevealed-staff:")
    for name, pick in (("top staff", lambda n: 0),
                       ("middle staff", lambda n: n // 2),
                       ("bottom staff", lambda n: n - 1)):
        tot = right = 0
        for key, group in by_sys.items():
            n = len(group)
            a = pick(n)
            clefs = {i: r["clef_read"] for i, r in enumerate(group)
                     if r["clef_read"]}
            fit = fit_layouts(n, labels={a: group[a]["TRUTH"]},
                              clefs=clefs or None)
            for i in range(n):
                if i == a:
                    continue
                tot += 1
                g = fit.assignment[i] if fit else None
                if g and g in group[i]["TRUTH_acceptable"]:
                    right += 1
        print(f"    {name:14s} {right}/{tot} = {right/tot if tot else 0:.3f}")

    (HERE / "order-vs-clef.json").write_text(json.dumps({
        "ablation": {k: list(v) for k, v in results.items()},
        "curve": {str(k): list(v) for k, v in curve.items()},
        "multiplicity_share_of_wrong": wrong_mult / wrong_tot if wrong_tot else 0,
    }, indent=1))


if __name__ == "__main__":
    main()
