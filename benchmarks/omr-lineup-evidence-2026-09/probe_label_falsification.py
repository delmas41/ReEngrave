"""A free precision test: a hit at a position both systems NAME IDENTICALLY is wrong.

No hand-read truth is needed for this and none exists at staff granularity for
most of the corpus.  The argument is purely internal:

    if system A prints `Fl.` at position 0 and system B prints `Fl.` at
    position 0, then position 0 holds the flute in both systems, and any screen
    claiming the two systems differ THERE has produced a false positive.

That is the strongest evidence a page offers -- a name, read independently on
both systems by two OCR rungs -- and it is exactly the evidence the incumbent
`slots._pair_score` already trusts (SCORE_LABEL_MATCH = +6.0 against a clef's
+1.5).  So a screen contradicting it is not being judged against a rival
hypothesis; it is being judged against its own pipeline's best evidence.

⚠️ This measures PRECISION ONLY, and only over the labelled sub-population.  It
cannot measure recall: a position both systems leave unlabelled may or may not
have changed, and that is precisely where R1 does its work.  Reporting this as
an accuracy would overclaim.  It is here to separate "this source fires a lot"
from "this source fires a lot for a reason".

===============================================================================
RESULTS, 2026-09-05, base b02190c3.  This docstring is the primary record: the
harness refuses .md writes in this worktree, so the findings live here and in
the commit message rather than in a FINDINGS.md.
===============================================================================

PRE-REGISTERED TEST -- R1 (expected absence) PASSES ALONE.  It needs no clef,
key signature, range or score order.

    beethoven-sym5-mvt1-984073-p4   MUST fire    -> FIRE
    beethoven-sym5-mvt1-575951-p4   MUST fire    -> FIRE
    brahms-sym1-mvt1-317803-p3      MUST silent  -> silent
    brahms-sym1-mvt1-317803-p4      MUST silent  -> silent
    other 16 rows                                -> 0 fire

Reachable population: only 8 of 20 rows have two systems of equal staff count.
Four Mahler rows abstain on a structure disagreement between the fixtures and
ladder.json's re-detection (fixture [17]/[13]/[18]/[17] vs ladder
[19]/[15]/[21]/[21]); all four are single-system pages anyway.

PER-SOURCE TABLE.  Precision is measured with no hand truth: a hit at a position
where both systems independently read the SAME instrument name is false by
construction.  Cross-scan Jaccard uses the two independent scans of one 1870
Litolff plate (984073-p4 / 575951-p4) -- a sound screen must fire at the same
POSITIONS on both.

    source                       fires  prec   contra  xscanJ  FIRE  SILENT
    R1 expected absence           2/20  1.000   0/2      1.00  PASS  PASS
    R0 named conflict (incumbent) 0/20    -      -         -   FAIL  PASS
    R2 clef raw                   7/20  0.562   7/16     0.20  PASS  FAIL
    R2' clef order-conditioned    5/20  1.000   0/6      0.00  PASS  PASS
    R2' clef treble-declines      1/20  1.000   0/1      0.00  FAIL  PASS
    R3 key raw                    6/20  0.300   7/10     0.67  PASS  FAIL
    R3' key order-conditioned     0/20    -      -         -   FAIL  PASS

R0 fires 0/20: the incumbent `slots._pair_score` shape (a position named
differently by both systems) has ZERO reach here.  The gap is the whole
opportunity.

SEAN'S ORDER-CONDITIONING.  It works for clef and cannot work for transposition.
 - clef: 0.562 -> 1.000 precision, MUST-SILENT FAIL -> PASS, removing all six
   Brahms false positives.  The mechanism is exactly as argued: clef alone says
   "treble vs bass"; conditioned on position it says ['Violin'] vs ['Timpani'],
   and where both systems name the staff Cello the candidate sets intersect and
   it declines.  Order IS the frame that makes clef discriminating -- measured.
 - BUT cross-scan Jaccard 0.00: it fires at {6,8} on one scan and {9} on the
   other, agreeing only at ROW granularity.  And it can fire when the two clefs
   are IDENTICAL (bach p1 pos 0: treble->['Flute'] vs treble->['Violin']), the
   disjointness coming from the two systems getting different layout fits.  Not
   shippable.
 - transposition: SILENT AT THE DECISIVE POSITION in both scans -- the timpani
   print no key signature (KS NOT READ), which is musically correct.  R3' is not
   rejected by a strict rule; it never gets to speak.  Second starvation: the
   concert reference is a mode over a noisy reader -- Beethoven 5 mvt1 is C minor
   (-3) and the per-system modes are -4 and -1, shifting every offset by a
   different amount in each system.

WHY EACH SILENT ROW IS SILENT (three different reasons, no publisher table):
    bach p1        {1,4,7,9,10} scattered vs {}    -> not prefix, abstain
    beethoven p2   {0..6} vs {0..6}                -> equal prefixes, no disagreement
    beethoven p4   {0..5} vs {0..6}                -> FIRE, pos 6 = Timpani
    brahms p3      all 14 vs 13 with a HOLE at 5   -> k==n and a hole, abstain
    brahms p4      all 14 vs all 14                -> k==n, abstain
    dvorak p7      {} vs {}                        -> nothing printed, abstain

Brahms p3 is the informative one: its OCR hole at position 5 is exactly the
noise a naive "labelled-count differs" rule would have fired on.  The contiguity
clause and the k<n clause each block it independently.

RESIDUAL RISK.  R1's only failure shape is a label-everything edition losing
TRAILING labels to OCR at different depths in two systems.  Over all 31 systems:
13 prefix-with-k<n (EVERY ONE Litolff Beethoven), 9 all-labelled (Breitkopf,
declines), 5 scattered (declines), 4 none-labelled (declines).  The shape does
not occur here.  A Breitkopf page with two differently-truncated systems is the
case to watch, and the corpus has none -- so R1's silence on the
label-everything class is UNTESTED, not verified.  That is its ceiling.

RECOMMENDATION.  Ship R1 as a FLAG, not a join rule -- it re-joins nothing, it
marks a page where the ordinal join has positive evidence against it.  It belongs
beside `_pair_score` in slots.py as a SYSTEM-PAIR pre-check, not inside
`_pair_score`, which is a per-staff scorer with no view of the two systems' whole
label sets.  `export._stitch_slots` already refuses when systems disagree about
staff COUNT; this is the equal-count case that refusal cannot see.
Do not ship R2'.  Do not reopen R3.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from probe_order_conditioned import load

MUST_FIRE = {"beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"}
MUST_BE_SILENT = {"brahms-sym1-mvt1-317803-p3", "brahms-sym1-mvt1-317803-p4"}


def main():
    rows, labels, _ = load()
    ev = json.loads(Path(__file__).with_name("lineup-evidence.json").read_text())
    oc = json.loads(Path(__file__).with_name("order-conditioned.json").read_text())

    # Assert we have something to score before scoring it.
    n_lab = sum(len(v) for r in labels.values() for v in r.values())
    assert n_lab > 0
    print(f"=== INPUT: {len(rows)} rows, {n_lab} resolved label records ===\n")

    def agreeing_positions(row):
        """Positions where two equal-count systems carry the SAME resolved name."""
        out = {}
        sysd = rows[row]
        counts = [len(s) for s in sysd]
        for a in range(len(sysd)):
            for b in range(a + 1, len(sysd)):
                if counts[a] != counts[b]:
                    continue
                la, lb = labels[row].get(a, {}), labels[row].get(b, {})
                for p in range(counts[a]):
                    if la.get(p) and lb.get(p) and la[p] == lb[p]:
                        out[p] = la[p]
        return out

    sources = {
        "R1_expected_absence": lambda r: [
            h[0] for pr in ev["per_row"][r]["pairs"] for h in pr["R1"]
        ],
        "R2_clef": lambda r: [h[0] for h in oc["detail"][r]["R2_clef"]],
        "R3_raw_key": lambda r: [h[0] for h in oc["detail"][r]["R3_raw"]],
        "R3p_order_conditioned": lambda r: [
            h[0] for h in oc["detail"][r]["R3p_ordered"]
        ],
    }

    print("=== HITS THAT CONTRADICT AN AGREED LABEL (false by construction) ===")
    print(f"{'source':24s} {'hits':>5s} {'contradicted':>13s} {'precision':>10s}")
    summary = {}
    for name, get in sources.items():
        tot = bad = 0
        bad_detail = []
        for row in sorted(rows):
            if row not in ev["per_row"]:
                continue
            agreed = agreeing_positions(row)
            for p in get(row):
                tot += 1
                if p in agreed:
                    bad += 1
                    bad_detail.append((row, p, agreed[p]))
        prec = (tot - bad) / tot if tot else float("nan")
        summary[name] = {"hits": tot, "contradicted": bad, "precision": prec}
        print(f"{name:24s} {tot:5d} {bad:13d} {prec:10.3f}")
        for row, p, inst in bad_detail:
            print(f"        FALSE  {row:38s} pos {p:2d}  both systems read {inst}")

    print("\n=== CROSS-SCAN REPRODUCIBILITY (same 1870 Litolff plate, two scans) ===")
    a, b = "beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"
    print(f"{'source':24s} {'scan A':>16s} {'scan B':>16s} {'Jaccard':>8s}")
    for name, get in sources.items():
        sa, sb = set(get(a)), set(get(b))
        j = len(sa & sb) / len(sa | sb) if (sa | sb) else float("nan")
        summary[name]["cross_scan_jaccard"] = None if j != j else j
        print(f"{name:24s} {str(sorted(sa)):>16s} {str(sorted(sb)):>16s} {j:8.2f}")

    print("\n=== PRE-REGISTERED TEST, all four sources side by side ===")
    print(f"{'source':24s} {'fires':>6s} {'MUST-FIRE':>10s} {'MUST-SILENT':>12s} "
          f"{'other rows':>11s}")
    for name, get in sources.items():
        fires = {r for r in ev["per_row"] if get(r)}
        ff = MUST_FIRE <= fires
        ss = not (MUST_BE_SILENT & fires)
        other = sorted(fires - MUST_FIRE - MUST_BE_SILENT)
        summary[name].update(
            {"rows_fired": sorted(fires), "must_fire": ff, "must_silent": ss}
        )
        print(
            f"{name:24s} {len(fires):6d} {'PASS' if ff else 'FAIL':>10s} "
            f"{'PASS' if ss else 'FAIL':>12s} {len(other):11d}"
        )
        for r in other:
            print(f"        also fires: {r}")

    Path(__file__).with_name("falsification.json").write_text(
        json.dumps(summary, indent=2)
    )
    print("\nwrote falsification.json")


if __name__ == "__main__":
    main()
