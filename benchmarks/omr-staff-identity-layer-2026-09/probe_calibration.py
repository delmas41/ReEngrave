#!/usr/bin/env python3
"""P(name) and P(set): are they CALIBRATED, or only plausible?

MEASUREMENT ONLY.

A probability is not a confidence, and this workstream already measured the
difference: `LayoutFit.agreement` sits at 1.000 for 70% of WRONG answers, which
is why `contextual.py:833` discards it. A probability has a testable property a
score does not -- **things assigned 0.8 must be right about 80% of the time**.

⚠️ AN UNCALIBRATED PROBABILITY IS WORSE THAN NONE. It launders a guess into
something that reads as evidence. If either quantity does not calibrate, this
probe says so and the record emits nothing for it.

TWO QUANTITIES, NEVER COLLAPSED
    P(name)  this specific instrument is correct -- for consumers that COMMIT
             (part naming, an identity-driven clef override, the roster carry)
    P(set)   the truth is somewhere in this candidate set -- for consumers that
             only RULE OUT (the written-range veto, a pitch prior,
             `_dedupe_cross_staff_detections` arbitration)

They are calibrated against different targets: P(name) against "was this name
right", P(set) against "was the truth in the set". They may not be derived from
one another by any fixed factor -- a WRONG name holds the truth in its set
0.200 of the time and an ABSTENTION 0.902, and one blended number destroys
exactly that distinction.

WHERE THE NUMBER COMES FROM -- a frequency, not a fitted opacity. The estimate
is the empirical correctness rate of a FEATURE CELL, with hierarchical backoff
(cell -> tier -> global) and Laplace smoothing, so every emitted probability is
auditable back to "staves that looked like this were right N of M times".
Features are page-derived and none is a join output:

    tier       label (a margin label was read) / roster (carried from another
               page of the same edition, label-sourced only) / derived (the
               score-order prior alone)
    clef_read  did any reader actually read this staff's clef
    set_bucket |candidate set| <= 4, or >= 5

⚠️ CALIBRATED HELD OUT FROM RULE DEVELOPMENT, by LEAVE-ONE-ENGRAVING-OUT. The
split is by engraving and not by row because two scans of one plate are ONE
engraving, and because a rule calibrated on one house's conventions is the
publisher-shaped trap this corpus has sprung repeatedly (Simrock 45/45 against
Litolff 2/50 on document roster transfer).

⚠️ n IS SMALL AND THE BINS SAY SO. 198 records over 3 engravings leaves ~60-70
per fold. This probe reports the WIDEST bins the data supports and prints the
count in every bin; it deliberately does not draw a smooth curve through noise.
A bin with fewer than MIN_BIN observations is reported as thin and excluded
from ECE rather than quietly averaged in.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_calibration.py

── RESULTS 2026-09-05: NEITHER CALIBRATES. EMIT NOTHING. ─────────────────────
197 records, 3 engravings, leave-one-engraving-out.

    P(name)  POOLED  Brier 0.0887   ECE 0.1277
      [0.70,0.90)  n=88  predicted 0.823  observed 1.000   +0.177
      [0.90,0.98)  n=96  predicted 0.945  observed 0.885   -0.060
      [0.98,1.01)  n=13  predicted 0.989  observed 0.692   -0.297

    P(set)   POOLED  Brier 0.1036   ECE 0.1301
      [0.70,0.90)  n=75  predicted 0.856  observed 1.000   +0.144
      [0.90,0.98)  n=55  predicted 0.925  observed 0.855   -0.070
      [0.98,1.01)  n=67  predicted 0.985  observed 0.821   -0.164

⚠️⚠️ THE MISCALIBRATION IS SYSTEMATIC AND WORST WHERE IT MATTERS MOST. In both
quantities the LOW bin is under-confident (observes 1.000) and the TOP bin is
badly over-confident -- P(name) promises 0.989 and delivers 0.692. A consumer
setting a high bar, which is exactly what a clef override would do, would be
buying the least trustworthy part of the curve. Per the pre-registered standard
that an uncalibrated probability is worse than none, NOTHING IS EMITTED.

Per publisher, P(name) ECE: Litolff 0.178, Breitkopf 0.137, Simrock 0.113 --
so it is not one house's conventions, it fails everywhere.

⚠️ AND THE TIER THAT MOST NEEDS CALIBRATING HAS NO RECORDS. Tier counts are
label 175 / roster 22 / **derived 0**: on the truth-bearing records the shipped
join already names all but 22, so the `derived` tier -- the 0.550-precision one
whose calibration would actually decide an admission -- never gets exercised by
this construction. The 197 records CANNOT calibrate the tier the design most
needs, and that is a property of the corpus, not of the estimator.

WHY IT FAILS, and what would be needed. 175 of 197 records are tier `label` at
~0.90 correctness, and none of the three features separates the ~15 wrong ones
from the right ones inside that tier -- so the estimator returns a base rate
with noise, which is what a flat reliability curve with a collapsing tail looks
like. Getting an honest probability needs a feature that discriminates WITHIN a
tier, and this corpus does not contain one. The route is the held-out-label
design at scale: Breitkopf pages with the labels hidden give effectively
unlimited labelled examples, and each such page yields ~28 `derived` records --
the tier that is empty here. That is a transcription cost (Surya label reads
per page), not a modelling problem, and it is the honest next step before any
probability ships.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDENT = HERE / "heldout-identity.json"
SETS = HERE / "candidate-sets.json"

MIN_BIN = 10          # below this a bin is reported but excluded from ECE
BINS = [(0.0, 0.7), (0.7, 0.9), (0.9, 0.98), (0.98, 1.01)]
PRIOR_STRENGTH = 2.0  # Laplace pseudo-counts, toward the parent level


def edition_of(rid):
    return rid.rsplit("-p", 1)[0]


def build_records():
    """One record per staff: the layer's ACTUAL output, its tier, and truth."""
    ident = json.loads(IDENT.read_text())
    sets = {(r["row_id"], r["system_index"], r["ordinal"]): r
            for r in json.loads(SETS.read_text())["rows"]}

    # Roster of label-sourced identity, per edition, keyed (n_staves, ordinal).
    roster = defaultdict(lambda: defaultdict(set))
    for r in ident["records"]:
        if r["SHIPPED"]:
            roster[edition_of(r["row_id"])][(r["n_staves"], r["ordinal"])].add(
                r["SHIPPED"])

    out = []
    for r in ident["records"]:
        if not r["TRUTH"]:
            continue
        key = (r["row_id"], r["system_index"], r["ordinal"])
        s = sets.get(key, {})
        # The layer's output: best tier available, in order of trust.
        if r["SHIPPED"]:
            tier, name = "label", r["SHIPPED"]
        else:
            carried = roster[edition_of(r["row_id"])].get(
                (r["n_staves"], r["ordinal"]), set())
            if len(carried) == 1:
                tier, name = "roster", next(iter(carried))
            elif r["HELDOUT"]:
                tier, name = "derived", r["HELDOUT"]
            else:
                tier, name = "none", None
        if name is None:
            continue
        size = s.get("set_size", 0)
        out.append({
            "engraving": r["engraving"], "publisher": r["publisher"],
            "tier": tier, "clef_read": bool(r["clef_read"]),
            "set_bucket": "<=4" if size <= 4 else ">=5",
            "name_correct": name in r["TRUTH_acceptable"],
            "truth_in_set": bool(s.get("truth_in_set")),
            "set_size": size,
        })
    return out


def estimate(train, feats, target):
    """Hierarchical frequency: cell -> tier -> global, Laplace smoothed."""
    glob = [0, 0]
    tier = defaultdict(lambda: [0, 0])
    cell = defaultdict(lambda: [0, 0])
    for r in train:
        k = tuple(r[f] for f in feats)
        for acc in (glob, tier[r["tier"]], cell[k]):
            acc[0] += bool(r[target])
            acc[1] += 1
    g = (glob[0] + 1) / (glob[1] + 2) if glob[1] else 0.5

    def p(r):
        k = tuple(r[f] for f in feats)
        t_hit, t_n = tier[r["tier"]]
        t = ((t_hit + PRIOR_STRENGTH * g) / (t_n + PRIOR_STRENGTH)
             if t_n else g)
        c_hit, c_n = cell[k]
        return ((c_hit + PRIOR_STRENGTH * t) / (c_n + PRIOR_STRENGTH)
                if c_n else t)
    return p


def reliability(pairs, label):
    """pairs = [(predicted, actual_bool)]. Prints bins, returns (ECE, Brier)."""
    brier = sum((p - a) ** 2 for p, a in pairs) / len(pairs)
    print(f"\n  {label}   n={len(pairs)}   Brier={brier:.4f}")
    print(f"    {'bin':>12s} {'n':>4s} {'predicted':>10s} {'observed':>9s} "
          f"{'gap':>7s}")
    ece_num = ece_den = 0.0
    for lo, hi in BINS:
        g = [(p, a) for p, a in pairs if lo <= p < hi]
        if not g:
            continue
        pm = sum(p for p, _ in g) / len(g)
        om = sum(a for _, a in g) / len(g)
        thin = " THIN" if len(g) < MIN_BIN else ""
        print(f"    [{lo:.2f},{hi:.2f}) {len(g):4d} {pm:10.3f} {om:9.3f} "
              f"{om-pm:+7.3f}{thin}")
        if len(g) >= MIN_BIN:
            ece_num += len(g) * abs(om - pm)
            ece_den += len(g)
    ece = ece_num / ece_den if ece_den else float("nan")
    print(f"    ECE (bins with n>={MIN_BIN}) = {ece:.4f}"
          f"   [{ece_den:.0f} of {len(pairs)} records in scored bins]")
    return ece, brier


def main():
    for p in (IDENT, SETS):
        if not p.exists():
            raise SystemExit(f"run the earlier probes first ({p})")
    recs = build_records()
    print(f"records: {len(recs)}")
    if not recs:
        raise SystemExit("REFUSING to report: no records.")
    eng = sorted({r["engraving"] for r in recs})
    print(f"engravings: {eng}")
    print(f"tier counts: "
          f"{ {t: sum(1 for r in recs if r['tier'] == t) for t in ('label','roster','derived')} }")

    for target, feats, name in (
            ("name_correct", ("tier", "clef_read", "set_bucket"), "P(name)"),
            ("truth_in_set", ("tier", "clef_read", "set_bucket"), "P(set)")):
        print(f"\n{'='*68}\n{name}  — LEAVE-ONE-ENGRAVING-OUT\n{'='*68}")
        pooled = []
        for held in eng:
            train = [r for r in recs if r["engraving"] != held]
            test = [r for r in recs if r["engraving"] == held]
            if not train or not test:
                continue
            f = estimate(train, feats, target)
            pairs = [(f(r), bool(r[target])) for r in test]
            reliability(pairs, f"fold held-out = {held}")
            pooled += pairs
        print(f"\n  {'-'*60}")
        reliability(pooled, f"{name} POOLED over folds")
        by_pub = defaultdict(list)
        for held in eng:
            train = [r for r in recs if r["engraving"] != held]
            f = estimate(train, feats, target)
            for r in recs:
                if r["engraving"] == held:
                    by_pub[r["publisher"]].append((f(r), bool(r[target])))
        for pub in sorted(by_pub):
            reliability(by_pub[pub], f"{name} publisher={pub}")


if __name__ == "__main__":
    main()
