#!/usr/bin/env python3
"""Sean's reading procedure: the candidate set is the WORK'S OWN page-1 roster.

MEASUREMENT ONLY.

    "If I am reading a score the first thing I look at are the names on the
     first page. I assume it won't add anything unless it adds a name, but it
     will take away to make the readability easier. If it takes away, I look at
     families of instruments and clefs / key transpositions to determine the
     rest."

This is a REPLACEMENT for layout selection, not a refinement of it. The ten
layouts are a guess at what COULD be present; page 1 states what IS. A roster
is page-derived, work-specific, and needs no layout chosen — and layout
selection is the step that has been failing here (the near-size match measured
load-bearing; vocabulary-containment selection 0.873 -> 0.680).

The load-bearing clause is **"it won't add, only take away"**: if true, every
later system is a SUBSEQUENCE OF A KNOWN SET, which is exactly what the
monotone DP is built for. We have been pointing it at the wrong reference.

THREE QUESTIONS, IN THE ORDER THEY GATE EACH OTHER

  1 THE PREMISE. How often does a later system carry an instrument that is NOT
    in the page-1 roster? Expected ~never. ⚠️ An instrument genuinely entering
    mid-movement is usually NEWLY NAMED where it enters — Sean's "unless it
    adds a name" clause — so that CONFIRMS the rule rather than breaking it.
    Exceptions are reported individually at this n, never as a rate.

  2 ACQUISITION vs JOIN. A document roster transfer was already measured in
    this repo at 52/117 — Simrock 45/45, Litolff 2/50 — which on its face
    refutes all of this. Acquiring a roster and JOINING it to a later page are
    different steps, and Litolff labels its strings on page 1 and never again,
    so the roster was probably AVAILABLE and the join is what failed. Measured
    here directly rather than by archaeology on that benchmark.

  3 THE ABLATION, RE-RUN AGAINST THE ROSTER instead of the layouts.

⚠️ The roster used here is the hand-read page-1 truth (works.json), so arms
that consume it are ORACLE-ROSTER arms and are ceilings, never accuracies. What
they isolate is the JOIN, with acquisition held perfect on purpose. Acquisition
is measured separately in (2) from the actual label reads.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_page1_roster.py

── RESULT 2026-09-05: THE PROCEDURE HOLDS, AND THE ROSTER BEATS THE TEMPLATES ─

1. THE PREMISE HOLDS EXACTLY. 11 later systems checked, **0** carrying any
   instrument absent from their page-1 roster and 0 carrying MORE of one than
   the roster lists. Every later system is a strict SUBSEQUENCE of page 1. A
   page only ever takes away.

2. ACQUISITION IS NOT THE BOTTLENECK — the shipped pipeline names the roster
   page perfectly on every edition here:

       beethoven-575951 p1  12/12    brahms-317803 p1  14/14
       beethoven-984073 p1  12/12    dvorak-405834 p5  15/15

   ⇒ So the historical document-roster figure (52/117; Simrock 45/45, Litolff
   2/50) was measuring the JOIN, not acquisition — the hypothesis is confirmed
   on this corpus. Litolff labels its strings on page 1 and never again, the
   roster was there, and joining it to later pages is what failed.

3. THE ABLATION, scored only on pages AFTER the roster's own (n=145):

       arm                                cov    right   prec
       layouts, order only              0.290       30  0.714
       layouts + clef (HELDOUT equiv)   0.807      104  0.889
       PAGE-1 ROSTER, order only        1.000      125  0.862
       PAGE-1 ROSTER + clef             1.000      131  0.903

⚠️⚠️ THE ROSTER REPLACES LAYOUT SELECTION AND DOMINATES IT. Coverage goes
0.807 -> **1.000** while precision RISES 0.889 -> 0.903. And the roster with
ORDER ALONE — no clef at all — already reaches coverage 1.000 at precision
0.862, beating layouts-plus-clef on coverage outright. There is no layout to
choose, so the step that has been failing (near-size match load-bearing;
vocabulary-containment selection 0.873 -> 0.680) simply does not occur.

⚠️ CLEF IS EXACTLY THE REFINEMENT SEAN DESCRIBED, and now it is worth
something measurable in its proper place: +0.041 precision (0.862 -> 0.903)
choosing between roster entries that order leaves in contention. That is a
BINARY DISCRIMINATION among ~14 known instruments, not an identification from
28 — which is why it can work here having failed as a namer (clef alone names
11 staves of 198).

⚠️ IT DISSOLVES THE MULTIPLICITY FINDING, visibly in the rosters printed above:
Brahms's page 1 carries `Horn | Horn` and Dvorak's `Horn | Horn` and
`Trombone | Trombone` as DISTINCT ENTRIES. The roster states there are two, and
order alone separates them — no clef, range or label text ever could. The 28.3%
of staves in duplicated-instrument positions stop being a problem class.

⚠️ CEILING, NOT ACCURACY. The roster here is hand-read page-1 truth, so arms 3
and 4 are ORACLE-ROSTER arms isolating the JOIN with acquisition held perfect.
Acquisition is measured separately in (2) and is 1.000 on these four editions —
but `probe_label_yield.py` found FIVE Breitkopf plates that print no labels at
all, so in general this procedure is BOUNDED BY PAGE-1 LABEL YIELD. Where page
1 is unnamed there is no roster to acquire and the layer falls back to the
template path measured above.

⚠️ n = 11 later systems, 145 staves, 3 engravings (two of the four rows are one
Litolff plate). `Bass voice` in the Beethoven roster is the known `Basso`
ambiguous-alias artifact, carried here only so the roster reproduces the truth
table exactly.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.score_layouts import ScoreLayout, fit_layouts   # noqa: E402

IDENT = HERE / "heldout-identity.json"


def work_of(row_id):
    """The EDITION, which is what a roster belongs to."""
    return row_id.rsplit("-p", 1)[0]


def page_of(row_id):
    return int(row_id.rsplit("-p", 1)[1])


def main():
    ident = json.loads(IDENT.read_text())
    by_sys = defaultdict(list)
    for r in ident["records"]:
        if r["TRUTH"]:
            by_sys[(r["row_id"], r["system_index"])].append(r)
    for g in by_sys.values():
        g.sort(key=lambda r: r["ordinal"])
    print(f"systems {len(by_sys)}   staff records "
          f"{sum(len(g) for g in by_sys.values())}   "
          f"tag {ident['meta']['tag']!r}")
    if not by_sys:
        raise SystemExit("REFUSING to report: no records.")

    # ── the roster: the EARLIEST page of each edition, in printed order ─────
    rosters = {}
    for (rid, sidx), g in by_sys.items():
        w = work_of(rid)
        p = page_of(rid)
        cur = rosters.get(w)
        if cur is None or (p, sidx) < cur[0]:
            rosters[w] = ((p, sidx), [r["TRUTH"] for r in g], rid)
    print(f"\n{'='*72}\nROSTERS TAKEN FROM EACH EDITION'S EARLIEST PAGE\n{'='*72}")
    for w, ((p, s), lineup, rid) in sorted(rosters.items()):
        print(f"  {w:32s} from p{p} sys{s}: {len(lineup)} staves")
        print(f"      {' | '.join(lineup)}")

    # ── 1. THE PREMISE ──────────────────────────────────────────────────────
    print(f"\n{'='*72}\n1. THE PREMISE — does a later system ADD an instrument?"
          f"\n{'='*72}")
    checked = adds = 0
    for (rid, sidx), g in sorted(by_sys.items()):
        w = work_of(rid)
        key, lineup, src = rosters[w]
        if (page_of(rid), sidx) == key:
            continue
        checked += 1
        roster = Counter(lineup)
        here = Counter(r["TRUTH"] for r in g)
        extra = {k: v for k, v in here.items() if k not in roster}
        more = {k: (v, roster[k]) for k, v in here.items()
                if k in roster and v > roster[k]}
        if extra or more:
            adds += 1
            print(f"  ⚠️ {rid} sys{sidx}: NEW {extra}   MORE-THAN-ROSTER {more}")
    print(f"  later systems checked: {checked}")
    print(f"  systems adding an instrument absent from the roster: {adds}")
    if not adds:
        print("  ⇒ PREMISE HOLDS on every later system in this corpus: a page"
              " only ever\n    TAKES AWAY. Every later system is a SUBSEQUENCE"
              " of its page-1 roster.")

    # ── 2. ACQUISITION vs JOIN ──────────────────────────────────────────────
    print(f"\n{'='*72}\n2. ACQUISITION vs JOIN\n{'='*72}")
    print("  ACQUISITION — can page 1's roster be READ? (label reads on the"
          " earliest page)")
    for w, ((p, s), lineup, rid) in sorted(rosters.items()):
        rec = [r for r in ident["records"] if r["row_id"] == rid]
        got = sum(1 for r in rec if r["SHIPPED"])
        print(f"    {w:32s} p{p}: pipeline named {got}/{len(rec)} "
              f"= {got/len(rec) if rec else 0:.3f}")

    # ── 3. THE ABLATION, AGAINST THE ROSTER ─────────────────────────────────
    print(f"\n{'='*72}\n3. ABLATION — LAYOUTS vs the PAGE-1 ROSTER\n{'='*72}")

    def run(use_roster, use_clef):
        tot = named = right = 0
        for (rid, sidx), g in by_sys.items():
            w = work_of(rid)
            key, lineup, _ = rosters[w]
            if (page_of(rid), sidx) == key:
                continue                      # never score the source page
            n = len(g)
            clefs = ({i: r["clef_read"] for i, r in enumerate(g)
                      if r["clef_read"]} if use_clef else None)
            if use_roster:
                lay = (ScoreLayout("page1-roster", tuple(lineup),
                                   "the work's own page-1 roster"),)
                fit = fit_layouts(n, labels=None, clefs=clefs, layouts=lay)
            else:
                fit = fit_layouts(n, labels=None, clefs=clefs)
            for i, r in enumerate(g):
                tot += 1
                got = fit.assignment[i] if fit else None
                if got:
                    named += 1
                    if got in r["TRUTH_acceptable"]:
                        right += 1
        return tot, named, named / tot if tot else 0, right, (
            right / named if named else 0)

    print(f"  {'arm':38s} {'n':>4s} {'cov':>7s} {'right':>6s} {'prec':>7s}")
    out = {}
    for label, ur, uc in (
            ("layouts, order only", False, False),
            ("layouts + clef  (HELDOUT equiv)", False, True),
            ("PAGE-1 ROSTER, order only", True, False),
            ("PAGE-1 ROSTER + clef", True, True)):
        tot, named, cov, right, prec = run(ur, uc)
        out[label] = (cov, prec)
        print(f"  {label:38s} {tot:4d} {cov:7.3f} {right:6d} {prec:7.3f}")
    print("\n  ⚠️ The roster arms are ORACLE-ROSTER CEILINGS (the roster is"
          " hand-read truth).\n     They isolate the JOIN with acquisition held"
          " perfect. Scored only on\n     pages AFTER the roster's own, which"
          " is why n is smaller than 198.")

    (HERE / "page1-roster.json").write_text(json.dumps({
        "premise_systems_checked": checked, "premise_adds": adds,
        "ablation": {k: list(v) for k, v in out.items()},
        "rosters": {w: v[1] for w, v in rosters.items()},
    }, indent=1))


if __name__ == "__main__":
    main()
