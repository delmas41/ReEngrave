#!/usr/bin/env python3
"""Does removing the double charge actually reduce alignment slips?

MEASUREMENT ONLY. No pipeline file is modified: each arm monkeypatches
`score_layouts` inside this process, runs the same held-out identity arm, and
reports coverage, precision and the alignment-slip share.

⚠️⚠️ THE "DOUBLE CHARGE" AS I FIRST STATED IT IS WRONG, AND READING THE CODE IS
WHAT FALSIFIED IT. I reported that `staff_position` and `part_position` are
normalised over different denominators so that any skip accrues drift, and gave
a worked figure for Brahms (6 skips = -4.8 of gap plus ~4.4 of drift).
`score_layouts.py:413-415` computes

    staff_positions = [i / (m - 1) for i in range(m)]     # over STAVES
    part_positions  = [j / (n - 1) for j in range(n)]     # over PARTS

— **both already normalised to [0,1] over their own axis.** So a UNIFORMLY
skipped layout is already free: under uniform skipping j ~ i(n-1)/(m-1), hence
part_position ~ staff_position and the term contributes its full 1.0. The
positional term is deletion-invariant in exactly the case I claimed it was not,
and my arithmetic double-counted nothing that the code does.

WHAT THE TERM ACTUALLY PENALISES IS **WHERE** THE SKIPS FALL, NOT THAT THERE
ARE SKIPS. Clustered skips break the proportionality: a 14-staff page against a
20-part layout that omits six CONSECUTIVE parts at one end maps staff i to part
i, so the last staff scores 13/13 = 1.000 against 13/19 = 0.684 — a 0.316
penalty on that pairing, growing along the run. And clustered omission is the
normal case: a Classical orchestra against a late-Romantic template drops a
contiguous block of extras.

So the mechanism is narrower and more specific than "suppression is charged
twice", and the fix cannot be the one I implied. That matters for what is
measurable here: a genuinely skip-position-invariant term needs a FREE AFFINE
FIT between the two axes, which the current DP cannot express — each cell sees
one (i, j) pair and no global offset. That is a design question, not a
one-line change, and nothing is proposed on the strength of a mechanism I
already got wrong once.

WHAT IS THE POSITIONAL TERM FOR? Not nothing — that is the honest answer and it
rules out simply deleting it. For a staff with no label and no read clef the
position term is the ONLY discriminating term, so it is what decides WHICH
parts get skipped when no evidence speaks. Deleting it leaves the DP
indifferent among all monotone assignments. The `FLOOR` arm (position alone, no
clef, no label) scoring precision 0.742 on 62 staves is that term working.

So the fix is not removal and not a smaller weight — it is making the term
DELETION-INVARIANT:

    arm A  current    |staff_position - part_position|, as shipped
    arm B  weight 0   DIAGNOSTIC ONLY — how much of the residual does the
                      positional term account for at all? Not a proposal: it
                      removes the only term that orders an unlabelled,
                      clefless staff, which is the `FLOOR` arm's 0.742.
    arm C  prefix     part_position renormalised over the STAVES axis
                      (j/(m-1), clipped) — free for a CONTIGUOUS PREFIX
                      alignment, which is the clustered-omission case above.
                      Deliberately NOT symmetric: it trades a penalty on
                      skip-at-the-start for none on skip-at-the-end, so it is
                      a probe of the direction, not a candidate to ship.

⚠️ NO WEIGHT IS TUNED. `SCORE_POSITION_WEIGHT` stays 1.0 in every arm; only the
FORM of the comparison changes. A weight search on three engravings is exactly
what this corpus punishes.

⚠️ PRE-REGISTERED. The alignment-slip share is 0.967 before (59 of 61 staves
the namer gets wrong). It must FALL, and by how much is the result. If it does
not fall materially the mechanism is not what we think, and that is the report
— not a weight search.

⚠️ The two `Basso`->`Bass voice` VOCABULARY GAPs are scorer artifacts and are
excluded from every figure below, so they can neither flatter nor muddy it.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_alignment_fix.py

── RESULT 2026-09-05: KILL CRITERION MET. THE MECHANISM IS NOT WHAT WE THOUGHT.
196 records (the 2 `Basso` artifacts excluded, pre-registered).

    arm                        cov    prec   wrong   slips  slip share
    A current (baseline)     0.801   0.873      59      59       1.000
    B weight 0 (diagnostic)  0.832   0.853      57      57       1.000
    C prefix-invariant       0.745   0.856      71      71       1.000

⚠️ THE SLIP SHARE CANNOT FALL, AND THAT IS A FLAW IN THE PRE-REGISTERED METRIC
RATHER THAN A RESULT. Once the vocabulary gap is zero, every wrong staff is an
alignment slip BY DEFINITION, so the share is pinned at 1.000 in every arm.
The outcome measure that actually moves is the WRONG COUNT, and it does not
move: 59 -> 57 with the positional term deleted OUTRIGHT. Two staves out of 196
on three engravings is noise. **The positional term is not the cause of the
slips**, and arm C — a form change in the direction the mechanism predicted —
makes things WORSE (59 -> 71).

⚠️⚠️ AND THE PROPOSED FIX IS VACUOUS, WHICH IS THE FINDING WORTH KEEPING.
Pairwise ordering constraints would add nothing, because ORDER IS ALREADY A
HARD CONSTRAINT of the alignment: `align_to_layout`'s DP is monotone, so its
output cannot violate layout order. Measured, not assumed —

    systems whose PREDICTION violates layout order:  0 of 15
    truth pairs an admitted relation speaks about:   1177, page AGREES 1177

Both the predictions and the pages already satisfy the relation everywhere. A
constraint that is never violated can never fire. Building it would have cost
the effort and changed not one staff.

SO WHAT IS THE LIMIT? EVIDENCE, not scoring form and not ordering. With labels
hidden the only real signal is the clef, and it is present on 132/137 = 0.96 of
the staves the namer gets RIGHT against 46/59 = 0.78 of the ones it gets wrong.

⚠️ THE STRUCTURAL CONSEQUENCE, and it closes the loop on this workstream's
original motivation in the opposite direction from the one intended: IDENTITY
AND CLEF ARE MUTUALLY DEPENDENT. Identity was pitched as the way past the
documented clef ceiling, but with labels hidden identity is itself mostly
downstream of the clef. Neither bootstraps the other. **The margin label is
what breaks the circle** — which is exactly why label-sourced identity reaches
precision 0.914 and derived identity is stuck at 0.873 with no scoring change
able to move it.
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

from tools.omr import instruments as INST          # noqa: E402
from tools.omr import score_layouts as SL          # noqa: E402

IDENT = HERE / "heldout-identity.json"
FIXTURES = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
            "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures")
TAG = ".reconciliation"
RAW_CLEF_SOURCES = {"detector", "detector_header", "specialist", "cv_locator"}

_ORIG_PAIR = SL._pair_score
_ORIG_ALIGN = SL.align_to_layout


def make_pair_score(mode):
    """Return a `_pair_score` replacement for the given arm.

    Arm C needs the two axis LENGTHS, which `_pair_score` is not given, so
    `align_to_layout` is wrapped to stamp them onto the scorer before each
    call. The wrapper changes no behaviour of its own.
    """
    def scorer(label, clef, staff_position, part, part_position, part_clef):
        if mode == "A":
            score = SL.SCORE_POSITION_WEIGHT * (
                1.0 - abs(staff_position - part_position))
        elif mode == "B":
            score = 0.0
        else:  # C — prefix-invariant
            # Re-express the part's rank on the STAVES axis, so a contiguous
            # PREFIX alignment (page uses parts 0..m-1 of n, the
            # clustered-omission case) scores 1.0 at every pairing instead of
            # drifting to 0.684 by the last staff.
            n_parts = scorer.n_parts
            m = scorer.m_staves
            if n_parts > 1 and m > 1:
                j = round(part_position * (n_parts - 1))
                pp = min(1.0, j / (m - 1))
            else:
                pp = part_position
            score = SL.SCORE_POSITION_WEIGHT * (1.0 - abs(staff_position - pp))
        if label is not None:
            score += (SL.SCORE_LABEL_MATCH if label == part
                      else SL.SCORE_LABEL_CONFLICT)
        if clef is not None and part_clef is not None:
            if clef == part_clef:
                score += SL.SCORE_CLEF_MATCH
            else:
                score += (SL.SCORE_TREBLE_CONFLICT if clef == "treble"
                          else SL.SCORE_CLEF_CONFLICT)
        return score
    scorer.n_parts = 0
    scorer.m_staves = 0
    return scorer


def install(mode):
    sc = make_pair_score(mode)
    SL._pair_score = sc

    def wrapped(layout, n_staves, labels=None, clefs=None, **kw):
        sc.n_parts = len(layout.parts)
        sc.m_staves = n_staves
        return _ORIG_ALIGN(layout, n_staves, labels, clefs, **kw)
    SL.align_to_layout = wrapped


def lcs_members(a, b):
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


def systems():
    """(row_id, system_index, [staff dicts]) over the 20-row gate."""
    import glob
    for p in sorted(glob.glob(f"{FIXTURES}/*{TAG}.omr.json")):
        rid = Path(p).name[: -len(f"{TAG}.omr.json")].rstrip(".")
        for page in json.loads(Path(p).read_text()).get("pages", []):
            for sysd in page.get("systems", []):
                yield rid, sysd.get("system_index"), sorted(
                    sysd.get("staves", []),
                    key=lambda s: (s.get("staff_geometry") or {})
                    .get("line_ys_page", [0])[0])


def main():
    ident = json.loads(IDENT.read_text())
    truth = {(r["row_id"], r["system_index"], r["ordinal"]): r
             for r in ident["records"] if r["TRUTH"]}
    print(f"truth records: {len(truth)}   tag {ident['meta']['tag']!r}")
    if not truth:
        raise SystemExit("REFUSING to report: no truth records.")

    # Exclude the Basso artifact from every arm, pre-registered.
    artifact = {k for k, r in truth.items()
                if r["TRUTH"] == "Bass voice"}
    print(f"excluded `Basso`->`Bass voice` scorer artifacts: {len(artifact)}")

    results = {}
    for mode in ("A", "B", "C"):
        install(mode)
        named = right = scoreable = slips = 0
        for rid, sidx, staves in systems():
            n = len(staves)
            clefs = {i: s["clef"] for i, s in enumerate(staves)
                     if s.get("clef_source") in RAW_CLEF_SOURCES and s.get("clef")}
            fit = SL.fit_layouts(n, labels=None, clefs=clefs or None)
            # LCS membership for the slip classification, continuation-aware
            group = [truth.get((rid, sidx, i)) for i in range(n)]
            lineup_raw = [g["TRUTH"] if g else None for g in group]
            collapsed, keep = [], []
            for i, nm in enumerate(lineup_raw):
                if nm and (not collapsed or collapsed[-1] != nm):
                    collapsed.append(nm); keep.append(i)
            best_mem, best_len = set(), -1
            for layout in SL.LAYOUTS:
                mem = lcs_members(collapsed, list(layout.parts))
                if len(mem) > best_len:
                    best_len, best_mem = len(mem), mem
            member_raw = set()
            for c_i in best_mem:
                lo = keep[c_i]
                hi = keep[c_i + 1] if c_i + 1 < len(keep) else n
                member_raw.update(range(lo, hi))
            for i in range(n):
                key = (rid, sidx, i)
                r = truth.get(key)
                if not r or key in artifact:
                    continue
                scoreable += 1
                got = fit.assignment[i] if fit else None
                if got:
                    named += 1
                    if got in r["TRUTH_acceptable"]:
                        right += 1
                    elif i in member_raw:
                        slips += 1
                elif i in member_raw:
                    slips += 1
        wrong = scoreable - right
        results[mode] = dict(
            scoreable=scoreable, named=named, right=right, slips=slips,
            coverage=named / scoreable, precision=right / named if named else 0,
            slip_share=slips / wrong if wrong else 0, wrong=wrong)
    SL._pair_score = _ORIG_PAIR
    SL.align_to_layout = _ORIG_ALIGN

    print(f"\n  {'arm':26s} {'cov':>6s} {'prec':>7s} {'wrong':>6s} "
          f"{'slips':>6s} {'slip share':>11s}")
    names = {"A": "A current (baseline)", "B": "B weight 0 (diagnostic)",
             "C": "C stretch-invariant"}
    for mode in ("A", "B", "C"):
        r = results[mode]
        print(f"  {names[mode]:26s} {r['coverage']:6.3f} {r['precision']:7.3f} "
              f"{r['wrong']:6d} {r['slips']:6d} {r['slip_share']:11.3f}")
    (HERE / "alignment-fix.json").write_text(json.dumps(results, indent=1))
    print("\n⚠️ Arm B is a DIAGNOSTIC, not a proposal: it removes the only term"
          "\n   that orders an unlabelled, clefless staff.")


if __name__ == "__main__":
    main()
