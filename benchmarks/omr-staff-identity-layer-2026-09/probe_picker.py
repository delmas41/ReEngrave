#!/usr/bin/env python3
"""The picker mode: top-k, and how many decisions a page actually costs.

MEASUREMENT ONLY.

Two modes need two different numbers, and precision 0.903 is the wrong one for
the second:

    whole work, batch, unattended   P(name)  must be right alone
    single page, human present      P(set)   truth in a short RANKED list

This probe measures the second. The reference is the LAYOUT arm, not the
roster arm, because the picker's case is precisely "one page, no list" — a
single page with no roster to acquire.

    TOP-K            is the truth in the top 1 / 3 / 5 of the ranked
                     suggestions for that staff?
    DECISIONS        with constraint propagation after each human choice, how
                     many picks does a page need before every staff is right?
                     Reported as a DISTRIBUTION with the worst case, not a mean.

⚠️ WHY PROPAGATION MATTERS HERE, and why the CSP result inverts from
disappointment to fit. Pruning was measured as buying COVERAGE rather than
correctness — weak for autonomous use. For an interactive picker it is exactly
right: order, family and uniqueness link the staves, so every human choice
re-ranks the others. A page should cost a couple of decisions, not fourteen.

⚠️ The simulated human is an ORACLE: asked for staff i, it answers the truth.
That is the point (it measures the INTERFACE's cost in decisions, not a
person's accuracy) but it means the decision counts are a FLOOR — a real person
mis-picking would cost more, and this probe cannot see that.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_picker.py

── RESULT 2026-09-05: BOTH PICKER NUMBERS COME IN WORSE THAN HOPED ───────────

TOP-K (198 staves, layout arm):
    top-1   167/198 = 0.843
    top-3   173/198 = 0.874
    top-5   174/198 = 0.879
      any   174/198 = 0.879
    ranked-list length: median 1.0, max 4

⚠️⚠️ THE RANKED LIST IS NOT THE CANDIDATE SET, AND THE 0.902 FIGURE IS NOT
AVAILABLE AS A PICKER. `probe_candidate_sets.py` reported "truth in the set
0.902, median set 5 of 28", and that was quoted as a usable picker needing no
further modelling. It is NOT the same object. That set is the UNION over all
ten layouts, unfiltered. What the shipped machinery ranks is
`LayoutFit.support` — the vote among layouts INSIDE the score band — and those
voters mostly agree, so its median length is **1.0**, not 5.

Consequence: top-3 buys only +0.031 over top-1 (0.843 -> 0.874) and top-5 is
already the ceiling of what any depth can reach (0.879 = "any"). **A shortlist
deep enough to carry the 0.902 does not exist in the current output**; getting
one means deliberately widening the band, which is a build, not a report.

DECISIONS TO RESOLVE (oracle human, asked about the least-certain wrong staff,
constraint propagation after every pick):

    distribution {0:2, 1:3, 3:1, 5:2, 7:4, 8:2, 11:1}
    median 5.0   mean 4.73   WORST 11 of 15 staves
    picks per staff 71/198 = 0.359

⚠️ THIS IS NOT "a couple of decisions". Brahms costs 7-8 picks of 14 staves on
every system; Dvorak p5 costs 11 of 15. Only the Beethoven systems are cheap
(0-3), and those are the ones the layout arm already nearly solves.

⚠️ IT IS ALSO EXACTLY WHAT THE PROPAGATION MEASUREMENT PREDICTED. The anchored
arm found the first oracle anchor worth +0.011 right-per-staff and six worth
+0.041; a page where pinning a staff barely moves its neighbours is a page that
needs a pick per unresolved staff. The CSP-as-interactive-picker hope rests on
choices CASCADING, and on this corpus they do not. The two results agree, and
the picker does not rescue the propagation negative — it inherits it.

⚠️ ORACLE HUMAN: asked for staff i it answers the truth. The decision counts
are therefore a FLOOR; a real person mis-picking costs more and this probe
cannot see it.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.score_layouts import fit_layouts   # noqa: E402

IDENT = HERE / "heldout-identity.json"
MAX_PICKS = 14


def ranked(fit, i):
    """Candidates at ordinal i, best first, from the layout vote."""
    if not fit or i >= len(fit.support):
        return []
    return [n for n, _ in sorted(fit.support[i].items(),
                                 key=lambda kv: -kv[1])]


def main():
    ident = json.loads(IDENT.read_text())
    by_sys = defaultdict(list)
    for r in ident["records"]:
        if r["TRUTH"]:
            by_sys[(r["row_id"], r["system_index"])].append(r)
    for g in by_sys.values():
        g.sort(key=lambda r: r["ordinal"])
    n_rec = sum(len(g) for g in by_sys.values())
    print(f"systems {len(by_sys)}   staff records {n_rec}   "
          f"tag {ident['meta']['tag']!r}")
    if not n_rec:
        raise SystemExit("REFUSING to report: no records.")

    # ── TOP-K ───────────────────────────────────────────────────────────────
    hits = Counter()
    tot = 0
    empty = 0
    sizes = []
    for (rid, sidx), g in by_sys.items():
        n = len(g)
        clefs = {i: r["clef_read"] for i, r in enumerate(g) if r["clef_read"]}
        fit = fit_layouts(n, labels=None, clefs=clefs or None)
        for i, r in enumerate(g):
            tot += 1
            cand = ranked(fit, i)
            if not cand:
                empty += 1
                continue
            sizes.append(len(cand))
            ok = set(r["TRUTH_acceptable"])
            for k in (1, 3, 5, 99):
                if ok & set(cand[:k]):
                    hits[k] += 1
    print(f"\n{'='*70}\nTOP-K — is the truth in the ranked list?\n{'='*70}")
    print(f"  staves with a non-empty list: {tot-empty}/{tot}")
    for k in (1, 3, 5, 99):
        label = "any" if k == 99 else f"top-{k}"
        print(f"  {label:>7s}  {hits[k]:4d}/{tot} = {hits[k]/tot:.3f}")
    if sizes:
        print(f"  list length: median {statistics.median(sizes):.1f}  "
              f"max {max(sizes)}   (lexicon 28)")
    print(f"\n  ⚠️ top-1 is the autonomous number; top-3/top-5 are the PICKER's."
          f"\n     A picker showing three options is a different product from"
          f" one that\n     must be right alone.")

    # ── DECISIONS TO RESOLVE ────────────────────────────────────────────────
    print(f"\n{'='*70}\nDECISIONS TO RESOLVE — picks needed per page\n{'='*70}")
    per_sys = {}
    for (rid, sidx), g in sorted(by_sys.items()):
        n = len(g)
        clefs = {i: r["clef_read"] for i, r in enumerate(g) if r["clef_read"]}
        pinned: dict[int, str] = {}
        picks = 0
        for _ in range(MAX_PICKS + 1):
            fit = fit_layouts(n, labels=pinned or None, clefs=clefs or None)
            wrong = [i for i, r in enumerate(g)
                     if i not in pinned
                     and (not fit or fit.assignment[i] not in
                          set(r["TRUTH_acceptable"]))]
            if not wrong:
                break
            # The human is asked about the staff the system is LEAST sure of —
            # lowest agreement among the still-wrong ones. That is the
            # interface a person would actually be given.
            target = min(wrong,
                         key=lambda i: (fit.agreement[i] if fit else 0.0))
            pinned[target] = g[target]["TRUTH"]
            picks += 1
        per_sys[(rid, sidx)] = (picks, n, len(wrong) if wrong else 0)
    vals = [v[0] for v in per_sys.values()]
    print(f"  {'row':34s} {'sys':>3s} {'staves':>6s} {'picks':>6s}")
    for (rid, sidx), (picks, n, left) in sorted(per_sys.items()):
        flag = "  (NOT RESOLVED)" if left else ""
        print(f"  {rid:34s} {sidx:3d} {n:6d} {picks:6d}{flag}")
    print(f"\n  DISTRIBUTION of picks per system: "
          f"{dict(sorted(Counter(vals).items()))}")
    print(f"  median {statistics.median(vals):.1f}   mean "
          f"{statistics.mean(vals):.2f}   WORST {max(vals)}")
    tot_staves = sum(v[1] for v in per_sys.values())
    print(f"  picks per staff: {sum(vals)}/{tot_staves} = "
          f"{sum(vals)/tot_staves:.3f}")
    print(f"\n  ⚠️ ORACLE HUMAN — asked for staff i it answers the truth. This"
          f" measures the\n     INTERFACE's cost in decisions and is a FLOOR;"
          f" a real person mis-picking\n     would cost more and this probe"
          f" cannot see it.")

    (HERE / "picker.json").write_text(json.dumps({
        "topk": {str(k): hits[k] / tot for k in (1, 3, 5, 99)},
        "picks": {f"{r}|{s}": v[0] for (r, s), v in per_sys.items()},
    }, indent=1))


if __name__ == "__main__":
    main()
