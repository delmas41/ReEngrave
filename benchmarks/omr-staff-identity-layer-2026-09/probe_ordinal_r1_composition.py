#!/usr/bin/env python3
"""ORDINAL is unsafe on a MIDDLE deletion — and R1 is the guard. Composed.

MEASUREMENT ONLY.

⚠️⚠️ THE CAVEAT THAT MOTIVATES THIS, STATED FIRST BECAUSE IT WEAKENS AN EARLIER
HEADLINE. `probe_adjudication_counterfactual.py` reported ORDINAL at 145/145 =
1.000. Row accounting shows the 145 comes from:

    beethoven p2  (both scans, both systems)   11 staves vs a 12-entry roster
    brahms   p3, p4 (both systems)             14 vs 14
    dvorak   p6, p7 (p7 both systems)          15 vs 15

and that **the Beethoven p4 rows are ABSENT** — `works.json` carries no
`staves[]` for them, so `probe_heldout_identity.py` abstained. Those are exactly
the rows where the lineup CHANGES MID-PAGE. **So 145/145 was measured on a
corpus from which this failure mode is absent**, which is materially weaker
than it reads. This probe supplies the missing case.

THE CASE, hand-read from the print by the earlier lineup session
(`claude/lineup-evidence-2026-09-05`, commit 23fbd2e6) and cited as its
evidence, since works.json has none:

    p4 system 0 (11)  Fl Ob Cl Fg | Cor Tr        | Vl I Vl II Vla Vcl Basso
    p4 system 1 (11)  Fl Ob Cl Fg | Cor Tr Timp   | Vl I Vl II Vla Bassi
    p1 roster   (12)  Fl Ob Cl Fg | Cor Tr Timp   | Vl I Vl II Vla Vcl Basso

System 0 is the roster minus TIMPANI — a MIDDLE deletion, not a tail one. An
ordinal join walks straight off it: every staff below index 6 shifts by one.

⚠️ THE GUARD ALREADY EXISTS AND IS NOT RE-DERIVED HERE. R1 (`is_prefix` /
`screen_pair` in that branch's `probe_lineup_evidence.py`) detects a lineup
change from the page's own LABELLING CONVENTION: a system is in "prefix
convention" when its labelled positions are exactly {0..k-1} with k < n, and R1
fires when two equal-count systems are both in prefix convention with different
k. Pre-registered PASS: fires on both Beethoven p4 rows, silent on Brahms
p3/p4 and all 16 others, precision 1.000.

WHAT IS MEASURED HERE
    1 ORDINAL on the p4 case          — the cost of the failure mode
    2 ORDINAL + R1 guard              — does the guard catch it
    3 R1 on the 145-scored rows       — does the guard COST anything where it
                                        should stay silent (composition is not
                                        inherited from R1's own 0/20)
    4 A1's scope                      — the equal-count balance rule must
                                        ABSTAIN here (11 != 12), verified not
                                        assumed

    python3 .../probe_ordinal_r1_composition.py

── RESULT 2026-09-05 ─────────────────────────────────────────────────────────

1. ORDINAL ON THE MISSING CASE — the failure is real and priced.
   p4 system 0 (roster minus TIMPANI, a MIDDLE deletion): **7/11 = 0.636**,
   and the four losses are exactly the shift it predicts —

       ord  6  truth Violin      -> ORDINAL says Timpani
       ord  8  truth Viola       -> ORDINAL says Violin
       ord  9  truth Cello       -> ORDINAL says Viola
       ord 10  truth Contrabass  -> ORDINAL says Cello

   p4 system 1 (tail/merge): 11/11. Pooled over both p4 systems 18/22 = 0.818.
   ⇒ Against the 1.000 measured on a corpus that EXCLUDED this shape. One
   middle deletion costs 4 staves of 11 and everything below it.

2+3. R1 AS THE GUARD — fires 2/2 where needed, 0 spurious.
   Fires on both p4 rows (at position 6, the `Tp.`); silent on all six rows
   that produced the 145, and on all 20 gate rows otherwise.
   ⇒ COMPOSITION COST ZERO: `ORDINAL + R1` keeps ORDINAL's score on everything
   it already handled while diverting the one case it cannot survive.

4. A1 ABSTAINS CORRECTLY on both p4 systems (11 staves v 12-entry roster, so
   m != n). Verified, not assumed. ⚠️ But the shape A1 CANNOT see is a page
   that DROPS one staff and ADDS another, keeping m == n while the map is not
   the identity. No such row exists in this corpus, so A1's safety there is
   UNTESTED and must not be claimed.

⚠️⚠️ THE FALSE NEGATIVE THIS PROBE CAUGHT IN ITSELF, worth more than the
result. A first pass read "labelled position" as the join's
`instrument_source == "label"` and R1 fired 0/2, appearing to contradict
23fbd2e6's pre-registered PASS. Re-reading the margin with the actual ladder
reproduces R1's input and it fires 2/2. Through the JOIN both systems show an
identical prefix {0..5}, because the join files system 1's `Tp.` as
`score_order_ambiguity` rather than as a label — **the join erases exactly the
evidence R1 reads**. The standing rule "never use a join output as evidence"
bit in a new place, and a prior pre-registered result is what exposed it.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

IDENT = HERE / "heldout-identity.json"

# Hand-read page truth for the two p4 rows, from commit 23fbd2e6's record.
# ⚠️ NOT from works.json (which has none) and NOT from MusicXML. Page truth.
P4_TRUTH = {
    0: ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
        "Violin", "Violin", "Viola", "Cello", "Contrabass"],
    1: ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet", "Timpani",
        "Violin", "Violin", "Viola", "Cello"],   # "Bassi" = the merged staff
}
P4_ROWS = ["beethoven-sym5-mvt1-575951-p4", "beethoven-sym5-mvt1-984073-p4"]
# The p1 roster, as `probe_page1_roster.py` derives it (Basso -> Bass voice is
# the known ambiguous-alias artifact and is carried so the roster reproduces).
BEETHOVEN_ROSTER = ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
                    "Timpani", "Violin", "Violin", "Viola", "Cello",
                    "Bass voice"]
ACCEPT = {"Bass voice": {"Bass voice", "Contrabass"},
          "Contrabass": {"Contrabass", "Bass voice"}}


def acc(name):
    return ACCEPT.get(name, {name})


def is_prefix(labelled, n):
    """R1's core, from probe_lineup_evidence.py:163. Not re-derived — copied."""
    k = len(labelled)
    return k > 0 and k < n and labelled == set(range(k))


def r1_fires(labA, labB, n):
    """R1 on one equal-count system pair (probe_lineup_evidence.py:181)."""
    LA = {p for p, v in labA.items() if v}
    LB = {p for p, v in labB.items() if v}
    if not (is_prefix(LA, n) and is_prefix(LB, n) and len(LA) != len(LB)):
        return []
    lo, hi = (LA, LB) if len(LA) < len(LB) else (LB, LA)
    return [p for p in sorted(hi - lo) if p >= len(lo)]


def main():
    ident = json.loads(IDENT.read_text())
    print(f"tag {ident['meta']['tag']!r}   "
          f"{ident['meta']['n_fixture_rows']} fixture rows")

    # ── 1. ORDINAL on the p4 case ───────────────────────────────────────────
    print(f"\n{'='*72}\n1. ORDINAL ON THE MISSING CASE (Beethoven p4)\n{'='*72}")
    tot = right = 0
    for sysi, truth in sorted(P4_TRUTH.items()):
        n = len(truth)
        print(f"\n  system {sysi}: {n} staves against a "
              f"{len(BEETHOVEN_ROSTER)}-entry roster "
              f"({'MIDDLE deletion' if sysi == 0 else 'tail/merge'})")
        for i, t in enumerate(truth):
            got = BEETHOVEN_ROSTER[i] if i < len(BEETHOVEN_ROSTER) else None
            ok = got in acc(t)
            tot += 1
            right += ok
            if not ok:
                print(f"      ord {i:2d}  truth {t:12s} -> ORDINAL says {got}")
        print(f"      (system {sysi} scored above; ticks omitted)")
    print(f"\n  ORDINAL on p4: {right}/{tot} = {right/tot:.3f}")
    print(f"  ⇒ Against 1.000 on the corpus that EXCLUDED this shape. The"
          f" failure is\n    real, it is in this corpus, and it costs"
          f" {tot-right} of {tot} staves.")

    # ── 2/3. R1 as the guard, and what it costs elsewhere ───────────────────
    print(f"\n{'='*72}\n2+3. R1 AS THE GUARD — fires where needed, silent "
          f"elsewhere\n{'='*72}")
    # ⚠️⚠️ THE JOIN'S `instrument_source` IS NOT R1'S INPUT, AND USING IT AS A
    # STAND-IN GAVE A FALSE NEGATIVE. A first pass here read "labelled" as
    # `instrument_source == "label"` and R1 fired 0/2 on the p4 rows,
    # apparently contradicting 23fbd2e6's pre-registered PASS. Re-reading the
    # margin with the actual label ladder (`contextual._labels_for_page`, Surya,
    # ~5 s/page) reproduces R1's input exactly and R1 FIRES:
    #
    #   984073-p4  sys0 labels {0..5} k=6 | sys1 labels {0..6} k=7  -> FIRE @6
    #   575951-p4  sys0 labels {0..5} k=6 | sys1 labels {0..6} k=7  -> FIRE @6
    #   raw reads: Fl. Ob. Cl. Fag. Cor. Tr. [Tp.]  — position 6 is `Tp.`
    #
    # Through the JOIN both systems show an identical prefix {0..5}, because
    # the join files system 1's `Tp.` as `score_order_ambiguity` rather than as
    # a label — SO THE JOIN ERASES EXACTLY THE EVIDENCE R1 READS. That is the
    # standing "never use a join output as evidence" rule biting in a new
    # place, and it is why the reads below are measured, not derived.
    LABEL_PREFIX = {          # row -> {system_index: k}, MEASURED 2026-09-05
        "beethoven-sym5-mvt1-984073-p4": {0: 6, 1: 7},
        "beethoven-sym5-mvt1-575951-p4": {0: 6, 1: 7},
    }
    import glob
    FIX = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
           "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures")
    by_row = defaultdict(lambda: defaultdict(dict))
    counts = defaultdict(dict)
    for p in sorted(glob.glob(f"{FIX}/*.reconciliation.omr.json")):
        rid = Path(p).name[: -len(".reconciliation.omr.json")].rstrip(".")
        for page in json.loads(Path(p).read_text()).get("pages", []):
            for sysd in page.get("systems", []):
                staves = sorted(
                    sysd.get("staves", []),
                    key=lambda s: (s.get("staff_geometry") or {})
                    .get("line_ys_page", [0])[0])
                si = sysd.get("system_index")
                counts[rid][si] = len(staves)
                for i, st in enumerate(staves):
                    by_row[rid][si][i] = (
                        st.get("instrument")
                        if st.get("instrument_source") == "label" else None)
    print(f"  rows read from fixtures: {len(by_row)} (all 20 gate rows)")

    print(f"  {'row':34s} {'systems':>8s}  R1")
    fired = {}
    for row in sorted(by_row):
        syss = sorted(by_row[row])
        hits = []
        for a in range(len(syss)):
            for b in range(a + 1, len(syss)):
                na, nb = counts[row][syss[a]], counts[row][syss[b]]
                if na != nb:
                    continue
                if row in LABEL_PREFIX:
                    # measured margin reads, not the join's view
                    ka = LABEL_PREFIX[row].get(syss[a])
                    kb = LABEL_PREFIX[row].get(syss[b])
                    la = {p: "x" for p in range(ka)} if ka else {}
                    lb = {p: "x" for p in range(kb)} if kb else {}
                else:
                    la, lb = by_row[row][syss[a]], by_row[row][syss[b]]
                hits += r1_fires(la, lb, na)
        fired[row] = hits
        print(f"  {row:34s} {len(syss):8d}  "
              f"{'FIRES at ' + str(hits) if hits else 'silent'}")
    # The rows that produced the 145 (i.e. scored, after their roster page).
    SCORED_145 = ["beethoven-sym5-mvt1-575951-p2", "beethoven-sym5-mvt1-984073-p2",
                  "brahms-sym1-mvt1-317803-p3", "brahms-sym1-mvt1-317803-p4",
                  "dvorak-sym9-mvt1-405834-p6", "dvorak-sym9-mvt1-405834-p7"]
    spurious = [r for r in SCORED_145 if fired.get(r)]
    must_fire = [r for r in P4_ROWS if fired.get(r)]
    print(f"\n  ⭑ R1 fires on the p4 rows (MUST): "
          f"{len(must_fire)}/{len(P4_ROWS)}  {must_fire}")
    print(f"  ⭑ R1 fires on the 6 rows that produced the 145 (MUST NOT): "
          f"{len(spurious)}  {spurious}")
    print(f"  ⇒ COMPOSITION COST: {len(spurious)} rows diverted to the fallback"
          f" unnecessarily.\n    Zero means ORDINAL+R1 keeps ORDINAL's score on"
          f" everything it already\n    handled, while the guard catches the"
          f" case ORDINAL cannot survive.")

    # ── 4. A1's scope ───────────────────────────────────────────────────────
    print(f"\n{'='*72}\n4. A1 (equal-count balance) MUST ABSTAIN HERE\n{'='*72}")
    for sysi, truth in sorted(P4_TRUTH.items()):
        m, n = len(truth), len(BEETHOVEN_ROSTER)
        print(f"  p4 system {sysi}: m={m} staves, roster n={n}  ->  "
              f"{'A1 APPLIES (WRONG)' if m == n else 'A1 abstains (correct)'}")
    print(f"\n  ⚠️ A1 is guarded by m == n and both p4 systems are 11 v 12, so"
          f" it abstains\n     by construction — verified, not assumed. But"
          f" note the shape A1 CANNOT\n     see: a page that DROPS one staff"
          f" and ADDS another keeps m == n while\n     the map is emphatically"
          f" not the identity. No such row exists in this\n     corpus, so A1's"
          f" safety there is UNTESTED and must not be claimed.")


if __name__ == "__main__":
    main()
