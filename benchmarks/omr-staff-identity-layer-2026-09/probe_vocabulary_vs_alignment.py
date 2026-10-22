#!/usr/bin/env python3
"""Vocabulary gap or alignment slip? — the pre-registered discriminator.

MEASUREMENT ONLY. No pipeline behaviour changes.

THE SPLIT. `probe_candidate_sets.py` found that 80% of the held-out namer's
errors sit at positions where NO layout puts the truth, and warned that a
pooled count of 20 cannot separate two opposite diagnoses:

    VOCABULARY GAP   the instrument genuinely is not in the layout
    ALIGNMENT SLIP   it IS in the layout, at a different index, because a
                     suppressed or condensed staff above shifted everything

They want opposite fixes — more layouts vs better alignment — so the split has
to be measured before either is proposed.

THE DISCRIMINATOR IS A SUBSEQUENCE, AND THAT IS THE WHOLE POINT.
**Score order is RELATIVE, not absolute.** The trombone is below the horns and
above the timpani; which index it lands on is not a fact about music, it is an
artifact of who else is printed. Suppress the flute and every remaining
instrument keeps its relative order — only the indices move.

So: take the system's TRUTH lineup and a layout's part list, and compute their
longest common subsequence BY NAME. LCS ignores indices entirely and preserves
only order. Then for a staff the namer got wrong:

    truth ∈ LCS(truth_lineup, layout.parts)   -> ALIGNMENT SLIP. The instrument
        is in the layout AND in the right relative order, so a purely
        relational matcher had everything it needed and the index cost it.
    truth ∈ layout.parts but ∉ LCS           -> ORDER CONFLICT. Present, but
        out of order relative to its neighbours — a real ordering disagreement.
    truth ∉ layout.parts                     -> VOCABULARY GAP. Genuine.

⚠️ THE MECHANISM THIS TESTS IS VISIBLE IN THE CODE, and it is why the
hypothesis is alignment. `score_layouts._pair_score` (line 344) scores every
pairing with

    SCORE_POSITION_WEIGHT * (1.0 - abs(staff_position - part_position))

on top of a DP that is ALREADY a monotone subsequence matcher with gaps. So the
machine is built to handle deletion and then CHARGED for it a second time: a
skipped layout part costs `GAP_LAYOUT` (-0.8, legitimate — the instrument is
not on this page) AND shifts every position below it, costing the drift term
again. Worked example, Brahms 1: 14 staves against `late-romantic-large`'s 20
parts means skipping 6, so `6 * -0.8 = -4.8` of explicit gap penalty plus up to
`(6/19) * 14 ≈ 4.4` of positional drift — **suppression is charged roughly
twice.** That is a quantitative account of why this workstream measured the
near-size template match as "load-bearing": the template is carrying weight the
relational term should carry, because the relational term is being cancelled by
a positional penalty.

⚠️ NOT A PRIOR. "Trombone below Horn" is a relation read off THIS page's staff
order, not a population tendency about which instruments a page usually holds.
Era and genre priors were considered and RETRACTED for exactly that reason:
they are a template the page is matched against, and templates are what has
been failing.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_vocabulary_vs_alignment.py

── RESULT 2026-09-05: IT IS ALIGNMENT. VOCABULARY IS ZERO. ───────────────────
198 records, 20-row `.reconciliation` gate. Of the 61 staves the held-out namer
does not get right:

    ALIGNMENT SLIP  59  0.967   in the layout AND in the right relative order
    ORDER CONFLICT   0  0.000
    VOCABULARY GAP   2  0.033

⚠️⚠️ CORRECTED — THE FIRST RUN REPORTED 9 ORDER CONFLICTS AND THEY WERE MY
PROBE'S ARTIFACT, NOT THE PIPELINE'S. I read Horn x5 + Trombone x4, all brass,
as brass ordering differing between engraving traditions, and recommended
exempting brass from any order relation. All nine are DUPLICATES — 9 of 9, no
exceptions: Brahms prints Horn on two staves at ordinal 6, Dvorak Trombone on
two at ordinal 8, and a bare LCS can match only one occurrence of a repeated
name. The PIPELINE models this and my probe did not: `align_to_layout` carries
an `ext` lane with `EXTEND_PENALTY` (score_layouts.py:444) exactly for "two
horns on two staves". Collapsing consecutive repeats before the LCS — the
probe's analogue of that lane — takes order conflicts to ZERO.

Two independent measurements falsified the tradition story before it could be
built on: `probe_order_consensus.py` finds the ten layouts UNANIMOUS on all 6
brass-internal pairs (only Flute/Piccolo is contested, across all 191 pairs),
and the admitted relation matches this corpus's pages 1177/1177. **THE BRASS
EXEMPTION IS WITHDRAWN — it rested entirely on this artifact.**

Multiplicity is the real phenomenon it was hiding: 56 of 198 staves (0.283) sit
where an instrument appears more than once in its own lineup.

⚠️ AND THE TWO "VOCABULARY GAPS" ARE NOT REAL. Both are `Basso` -> `Bass
voice`, the ambiguous-alias scorer artifact this workstream already documented
and fixed for scoring. **The genuine vocabulary gap on this corpus is ZERO.**
Adding layouts would fix nothing.

By instrument, the slips are led by Contrabass x9, Contrabassoon x5, Cello x4,
Oboe x4, Clarinet x4, Trumpet x4, Trombone x4 — i.e. the bottom of the string
section and the instruments that sit below a suppressible neighbour.

THE 9 ORDER CONFLICTS ARE A REAL AND SEPARATE FINDING: Horn x5 and Trombone x4,
entirely within the brass. Brass section ordering genuinely differs between
engraving traditions (horns above trumpets, or trumpets above horns), so a
strict global order over brass is the one place a pairwise relation should NOT
be asserted without evidence. Every other family is order-stable here.

By arm: Simrock/Dvorak align 32 / order 4 / vocab 0; Breitkopf/Brahms 15 / 5 /
0; Litolff/Beethoven 3 / 0 / 2 (both artifacts).

⚠️ THIS CORRECTS THIS WORKSTREAM'S OWN EARLIER READING. `probe_candidate_sets.py`
reported that 80% of errors sit where "NO layout puts the truth there at all"
and left vocabulary live as a diagnosis. That probe asks an INDEX-BOUND
question; this one ignores indices and keeps only order. Both are true — the
instrument is in the layout, in order, and not at that index — and what the
0.200 measured was index sensitivity, which is the positional penalty itself.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.score_layouts import LAYOUTS  # noqa: E402

IDENT = HERE / "heldout-identity.json"
SETS = HERE / "candidate-sets.json"


def lcs_members(a, b):
    """Indices of `a` that lie on a longest common subsequence with `b`."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = (dp[i + 1][j + 1] + 1 if a[i] == b[j]
                        else max(dp[i + 1][j], dp[i][j + 1]))
    out, i, j = set(), 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            out.add(i); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


def main():
    if not IDENT.exists():
        raise SystemExit(f"run probe_heldout_identity.py first ({IDENT})")
    ident = json.loads(IDENT.read_text())
    sets = {(r["row_id"], r["system_index"], r["ordinal"]): r
            for r in json.loads(SETS.read_text())["rows"]} if SETS.exists() else {}
    recs = [r for r in ident["records"] if r["TRUTH"]]
    print(f"records with truth: {len(recs)}  "
          f"(tag {ident['meta']['tag']!r}, {ident['meta']['n_fixture_rows']} rows)")
    if not recs:
        raise SystemExit("REFUSING to report: no records.")

    by_sys = defaultdict(list)
    for r in recs:
        by_sys[(r["row_id"], r["system_index"])].append(r)

    verdict = Counter()
    detail = Counter()
    per_layout_best = Counter()
    rows_out = []
    for key, group in sorted(by_sys.items()):
        group.sort(key=lambda r: r["ordinal"])
        lineup_raw = [r["TRUTH"] for r in group]
        # ⚠️ CONSECUTIVE REPEATS ARE COLLAPSED, because the PIPELINE models
        # them and a plain LCS does not. `align_to_layout`'s DP carries an
        # `ext` lane with `EXTEND_PENALTY` (score_layouts.py:444) precisely so
        # one part can CONTINUE onto several staves -- two horns on two staves,
        # first violins divided over three. A bare LCS has no such lane, so it
        # can match only ONE of a page's two Horn staves and reports the other
        # as an ordering failure that does not exist.
        #
        # This was not hypothetical: the first run of this probe reported 9
        # ORDER CONFLICTS (Horn x5, Trombone x4) and I read them as brass
        # ordering differing between engraving traditions. They are 9 of 9
        # DUPLICATES -- Brahms prints Horn on two staves at ordinal 6, Dvorak
        # Trombone on two at ordinal 8 -- and `probe_order_consensus.py`
        # falsified the tradition story independently: the ten layouts are
        # UNANIMOUS on all 6 brass-internal pairs, and the admitted relation
        # matches this corpus's pages 1177/1177.
        collapsed, keep_idx = [], []
        for i, name in enumerate(lineup_raw):
            if not collapsed or collapsed[-1] != name:
                collapsed.append(name)
                keep_idx.append(i)
        lineup = collapsed
        # Best layout BY SUBSEQUENCE, not by size or by score: the question is
        # whether the page's order is expressible in the layout at all.
        best, best_lcs, best_members = None, -1, set()
        for layout in LAYOUTS:
            mem = lcs_members(lineup, list(layout.parts))
            if len(mem) > best_lcs:
                best, best_lcs, best_members = layout, len(mem), mem
        per_layout_best[best.name] += 1
        parts = set(best.parts)
        # Map collapsed-run membership back onto every staff of the run: if a
        # run of Horn staves lies on the LCS, every staff in it does.
        member_raw = set()
        for c_i in best_members:
            lo = keep_idx[c_i]
            hi = keep_idx[c_i + 1] if c_i + 1 < len(keep_idx) else len(lineup_raw)
            member_raw.update(range(lo, hi))
        best_members = member_raw
        for r in group:
            i = r["ordinal"]
            wrong = (not r["HELDOUT"]) or (r["HELDOUT"] not in r["TRUTH_acceptable"])
            if not wrong:
                verdict["namer was right"] += 1
                continue
            if i in best_members:
                v = "ALIGNMENT SLIP"
            elif r["TRUTH"] in parts:
                v = "ORDER CONFLICT"
            else:
                v = "VOCABULARY GAP"
            verdict[v] += 1
            detail[(v, r["TRUTH"])] += 1
            rows_out.append({**{k: r[k] for k in
                                ("row_id", "publisher", "system_index",
                                 "ordinal", "TRUTH", "HELDOUT", "clef_read")},
                             "verdict": v, "best_layout": best.name,
                             "lcs_len": best_lcs, "lineup_len": len(lineup)})

    total_wrong = sum(v for k, v in verdict.items() if k != "namer was right")
    print(f"\n{'='*66}\nEVERY STAFF THE HELD-OUT NAMER DID NOT GET RIGHT\n{'='*66}")
    print(f"  {'verdict':18s} {'n':>5s} {'share of wrong':>15s}")
    for v in ("ALIGNMENT SLIP", "ORDER CONFLICT", "VOCABULARY GAP"):
        n = verdict[v]
        print(f"  {v:18s} {n:5d} {n/total_wrong if total_wrong else 0:15.3f}")
    print(f"  {'(right)':18s} {verdict['namer was right']:5d}")
    print(f"\n  total wrong-or-abstained: {total_wrong} of {len(recs)}")

    print(f"\nBY INSTRUMENT")
    for (v, t), c in detail.most_common(18):
        print(f"  {c:3d}  {v:16s} {t}")

    print(f"\nBEST LAYOUT BY SUBSEQUENCE (not by score): "
          f"{dict(per_layout_best)}")

    print(f"\nBY ARM (publisher label = its composer; see probe_heldout_identity)")
    for pub in sorted({r["publisher"] for r in rows_out}):
        g = [r for r in rows_out if r["publisher"] == pub]
        c = Counter(r["verdict"] for r in g)
        print(f"  {pub:11s} n={len(g):3d}  "
              f"align {c['ALIGNMENT SLIP']:3d}  order {c['ORDER CONFLICT']:3d}"
              f"  vocab {c['VOCABULARY GAP']:3d}")

    (HERE / "vocabulary-vs-alignment.json").write_text(json.dumps({
        "verdict": dict(verdict), "detail": {f"{v}|{t}": c
                                             for (v, t), c in detail.items()},
        "rows": rows_out}, indent=1))
    print(f"\nwrote {HERE / 'vocabulary-vs-alignment.json'}")


if __name__ == "__main__":
    main()
