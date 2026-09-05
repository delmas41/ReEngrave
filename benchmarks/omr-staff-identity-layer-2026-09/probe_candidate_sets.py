#!/usr/bin/env python3
"""Is the truth in the CANDIDATE SET? — the premise a CSP identity layer rests on.

MEASUREMENT ONLY.

`fit_layouts` already votes across every layout inside `SCORE_BAND_PER_STAFF`
of the winner and keeps the full ballot in `LayoutFit.support` — then names a
staff only when one candidate holds `MIN_AGREEMENT` (0.75) of the vote, and
`contextual.py` discards the ballot entirely (line 833).

A constraint-propagation layer does not want the winner. It wants the SET, so
that clef, written range, bracket family and uniqueness can prune it. That only
works if the truth is IN the set. This probe measures exactly that, and nothing
else:

    SET_RECALL   truth ∈ support(ordinal)          -- can pruning ever find it
    SET_SIZE     |support(ordinal)|                 -- how much is left to prune
    ELIMINATION  positions whose truth is the only
                 instrument no other staff can be   -- free identity

⚠️ It measures a CEILING for pruning, not an accuracy. A set containing the
truth alongside four wrong answers is not an answer; it is a starting point.

⚠️ Same fixture discipline as `probe_heldout_identity.py`: the 20-row
`.reconciliation` gate, labels held out, no join-assigned field, no dossier.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_candidate_sets.py

── RESULTS 2026-09-05 ────────────────────────────────────────────────────────
198 positions, 20-row `.reconciliation` gate, labels hidden.

    positions with a non-empty set   198 / 198
    TRUTH IN THE SET                 178 / 198 = 0.899
    median set size                  5.0  (mean 5.30, max 8; lexicon is 28)
    already singletons               0
    set recall  Litolff 0.956 | Breitkopf 0.871 | Simrock 0.867

Then the split that decides what a CSP is FOR:

    held-out winner WRONG      20   truth still in set   4  (0.200)
    held-out ABSTAINED         41   truth still in set  37  (0.902)

⚠️⚠️ A CSP OVER SCORE-ORDER CANDIDATE SETS IS A COVERAGE MECHANISM, NOT A
CORRECTNESS ONE. Ceiling on coverage 0.793 -> up to 0.980; ceiling on the 20
current errors is -4. Eighty per cent of the errors are positions where NO
layout puts the truth there at all -- Trombone x5 (Simrock), Horn x5, Viola x3,
Contrabassoon x3, Timpani x2, Bassoon x2 -- and no constraint prunes toward an
answer that is not in the set. The residual is a score-order VOCABULARY and
ALIGNMENT problem and is not reachable by adding evidence tiers.

Read this bound before building any tier. Clef, written range, bracket family
and uniqueness all prune; pruning is worth up to +37 coverage and at most -4
errors on this corpus.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                    # noqa: E402
from tools.omr.score_layouts import LAYOUTS, align_to_layout  # noqa: E402

IDENT = HERE / "heldout-identity.json"


def main():
    if not IDENT.exists():
        raise SystemExit(f"run probe_heldout_identity.py first ({IDENT})")
    data = json.loads(IDENT.read_text())
    recs = [r for r in data["records"] if r["TRUTH"]]
    print(f"records with truth: {len(recs)}   "
          f"(from {data['meta']['n_scoreable_records']} scoreable, "
          f"tag {data['meta']['tag']!r}, "
          f"{data['meta']['n_fixture_rows']} fixture rows)")
    if not recs:
        raise SystemExit("REFUSING to report: no records.")

    # Rebuild the per-system candidate sets the same way the held-out arm ran:
    # every layout, labels hidden, clefs only where a reader read one.
    by_sys = {}
    for r in recs:
        by_sys.setdefault((r["row_id"], r["system_index"]), []).append(r)

    rows = []
    for (rid, sysi), group in sorted(by_sys.items()):
        group.sort(key=lambda r: r["ordinal"])
        n = group[0]["n_staves"]
        clefs = {r["ordinal"]: r["clef_read"] for r in group if r["clef_read"]}
        # UNION over every layout: what could stand at this position at all.
        union = [set() for _ in range(n)]
        for layout in LAYOUTS:
            _, assign = align_to_layout(layout, n, None, clefs or None)
            for i, name in enumerate(assign):
                if name:
                    union[i].add(name)
        for r in group:
            i = r["ordinal"]
            rows.append({
                **r,
                "set": sorted(union[i]),
                "set_size": len(union[i]),
                "truth_in_set": bool(set(r["TRUTH_acceptable"]) & union[i]),
            })

    spoke = [r for r in rows if r["set_size"] > 0]
    hit = [r for r in spoke if r["truth_in_set"]]
    print(f"\nSET_RECALL (truth ∈ union over all ten layouts, labels hidden)")
    print(f"  positions with a non-empty set   {len(spoke):4d} / {len(rows)}"
          f"   = {len(spoke)/len(rows):.3f}")
    print(f"  truth in the set                 {len(hit):4d} / {len(spoke)}"
          f"   = {len(hit)/len(spoke):.3f}")
    sizes = [r["set_size"] for r in spoke]
    print(f"  set size  median {statistics.median(sizes):.1f}"
          f"  mean {statistics.mean(sizes):.2f}"
          f"  max {max(sizes)}   (lexicon is {len(INST.INSTRUMENTS)})")
    print(f"  already singletons               "
          f"{sum(1 for r in spoke if r['set_size'] == 1):4d}"
          f"   of which right "
          f"{sum(1 for r in spoke if r['set_size'] == 1 and r['truth_in_set'])}")

    print(f"\nBY PUBLISHER")
    print(f"  {'publisher':12s} {'n':>4s} {'set_recall':>11s} {'med|set|':>9s}")
    for pub in sorted({r["publisher"] for r in spoke}):
        g = [r for r in spoke if r["publisher"] == pub]
        print(f"  {pub:12s} {len(g):4d} "
              f"{sum(1 for r in g if r['truth_in_set'])/len(g):11.3f} "
              f"{statistics.median([r['set_size'] for r in g]):9.1f}")

    # Where the held-out WINNER was wrong, was the truth still in the set?
    wrong = [r for r in spoke
             if r["HELDOUT"] and r["HELDOUT"] not in r["TRUTH_acceptable"]]
    rescuable = [r for r in wrong if r["truth_in_set"]]
    absent = [r for r in spoke if not r["HELDOUT"]]
    abs_hit = [r for r in absent if r["truth_in_set"]]
    print(f"\nWHAT PRUNING COULD REACH")
    print(f"  held-out winner WRONG            {len(wrong):4d}"
          f"   truth still in set {len(rescuable)}"
          f"  ({len(rescuable)/len(wrong):.3f})" if wrong else "")
    print(f"  held-out ABSTAINED               {len(absent):4d}"
          f"   truth in set {len(abs_hit)}"
          f"  ({len(abs_hit)/len(absent):.3f})" if absent else "")

    print(f"\nMISSES — truth NOT in any layout's set at that position")
    miss = Counter((r["publisher"], r["TRUTH"]) for r in spoke
                   if not r["truth_in_set"])
    for (p, t), c in miss.most_common(15):
        print(f"  {c:3d}  {p:12s} {t}")

    out = HERE / "candidate-sets.json"
    out.write_text(json.dumps({
        "meta": {**data["meta"], "n_positions": len(rows),
                 "set_recall": len(hit) / len(spoke) if spoke else 0.0},
        "rows": rows}, indent=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
