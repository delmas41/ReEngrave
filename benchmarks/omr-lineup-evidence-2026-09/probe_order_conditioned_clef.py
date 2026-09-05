"""Does score order rescue the CLEF source the way it was asked to rescue transposition?

Sean's general point is not about key signatures specifically: *what sits above
and below a staff leaves only a few options for what it can be*, so order is the
frame that makes clef, range and transposition discriminating -- each is asked
to choose within a short candidate list rather than across the whole lexicon.
Transposition could not be tested properly because it is silent at the decisive
position (the timpani print no key signature).  The clef source has hits, so it
CAN be tested, and it is the fairest available test of the general claim.

The rule.  At position p, take the admissible instruments from the same
`score_layouts.fit_layouts` ballot used for transposition, and intersect with
the clef actually read:

    C_p(sys) = { n in support[p] : default_clef(n) == clef_read(sys, p) }

Fire when both sides are non-empty and DISJOINT -- the two systems' clefs point
at candidate sets with no instrument in common at that position.  Compared
against the raw rule (fire whenever the two clefs differ).

Two arms, because `score_layouts` itself records that they are not equivalent:
`SCORE_TREBLE_CONFLICT = -0.3` against `SCORE_CLEF_CONFLICT = -1.5`, with the
comment that reading everything as treble is the documented failure mode of clef
detection on degraded orchestral prints -- so "this staff reads treble" is weak
evidence about a part while "this staff reads alto" is strong.  Arm B therefore
declines to fire when EITHER side reads treble.  Both arms are pre-registered
here and both are reported; picking the better one after the fact would be the
tuned-on-one-corpus mistake this repo has recorded twice.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(Path(__file__).parent))

from tools.omr import score_layouts as sl
from tools.omr.instruments import lookup
from probe_order_conditioned import load

MUST_FIRE = {"beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"}
MUST_BE_SILENT = {"brahms-sym1-mvt1-317803-p3", "brahms-sym1-mvt1-317803-p4"}
TREBLEISH = {"treble", "treble_8vb"}


def default_clef(name):
    m = lookup(name)
    if m is None:
        return None
    return getattr(getattr(m, "instrument", m), "default_clef", None)


def main():
    rows, labels, _ = load()
    assert len(rows) == 20

    fits = {}
    for row in sorted(rows):
        for i, staves in enumerate(rows[row]):
            labs = labels.get(row, {}).get(i, {})
            clefs = {j: st["clef"] for j, st in enumerate(staves) if st["clef"]}
            fits[(row, i)] = sl.fit_layouts(
                len(staves), labels=labs or None, clefs=clefs or None
            )
    assert sum(1 for f in fits.values() if f is not None) > 0

    def agreed(row):
        out = {}
        sysd = rows[row]
        c = [len(s) for s in sysd]
        for a in range(len(sysd)):
            for b in range(a + 1, len(sysd)):
                if c[a] != c[b]:
                    continue
                la, lb = labels[row].get(a, {}), labels[row].get(b, {})
                for p in range(c[a]):
                    if la.get(p) and lb.get(p) and la[p] == lb[p]:
                        out[p] = la[p]
        return out

    results = {}
    for arm in ("A_all_clefs", "B_treble_declines"):
        hits_rows, tot, bad, cov = set(), 0, 0, 0
        per = {}
        for row in sorted(rows):
            sysd = rows[row]
            c = [len(s) for s in sysd]
            ag = agreed(row)
            rh = []
            for a in range(len(sysd)):
                for b in range(a + 1, len(sysd)):
                    if c[a] != c[b]:
                        continue
                    fA, fB = fits[(row, a)], fits[(row, b)]
                    if fA is None or fB is None:
                        continue
                    for p in range(c[a]):
                        ca, cb = sysd[a][p]["clef"], sysd[b][p]["clef"]
                        if not ca or not cb:
                            continue
                        if p >= len(fA.support) or p >= len(fB.support):
                            continue
                        supA = [n for n in (fA.support[p] or {}) if n]
                        supB = [n for n in (fB.support[p] or {}) if n]
                        if not supA or not supB:
                            continue
                        if arm == "B_treble_declines" and (
                            ca in TREBLEISH or cb in TREBLEISH
                        ):
                            continue
                        CA = {n for n in supA if default_clef(n) == ca}
                        CB = {n for n in supB if default_clef(n) == cb}
                        if not CA or not CB:
                            continue
                        cov += 1
                        if not (CA & CB):
                            rh.append([p, ca, sorted(CA), cb, sorted(CB)])
                            tot += 1
                            if p in ag:
                                bad += 1
            if rh:
                hits_rows.add(row)
            per[row] = rh
        prec = (tot - bad) / tot if tot else float("nan")
        results[arm] = {
            "rows_fired": sorted(hits_rows),
            "hits": tot,
            "contradicted": bad,
            "precision": prec,
            "cells_covered": cov,
            "must_fire": MUST_FIRE <= hits_rows,
            "must_silent": not (MUST_BE_SILENT & hits_rows),
            "per_row": per,
        }
        a_, b_ = "beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"
        sa = {h[0] for h in per[a_]}
        sb = {h[0] for h in per[b_]}
        results[arm]["cross_scan_jaccard"] = (
            len(sa & sb) / len(sa | sb) if (sa | sb) else None
        )

    print("=== ORDER-CONDITIONED CLEF vs RAW CLEF ===")
    print(
        f"{'arm':22s} {'cells':>6s} {'hits':>5s} {'contra':>7s} {'prec':>6s} "
        f"{'rows':>5s} {'MUSTFIRE':>9s} {'MUSTSIL':>8s} {'xscanJ':>7s}"
    )
    print(
        f"{'raw (R2, reference)':22s} {'99':>6s} {'16':>5s} {'7':>7s} "
        f"{'0.562':>6s} {'7':>5s} {'PASS':>9s} {'FAIL':>8s} {'0.20':>7s}"
    )
    for arm, r in results.items():
        j = r["cross_scan_jaccard"]
        print(
            f"{arm:22s} {r['cells_covered']:6d} {r['hits']:5d} {r['contradicted']:7d} "
            f"{r['precision']:6.3f} {len(r['rows_fired']):5d} "
            f"{'PASS' if r['must_fire'] else 'FAIL':>9s} "
            f"{'PASS' if r['must_silent'] else 'FAIL':>8s} "
            f"{'n/a' if j is None else f'{j:.2f}':>7s}"
        )
        for row in r["rows_fired"]:
            tag = (
                "TRUE"
                if row in MUST_FIRE
                else ("FALSE-POS(prereg)" if row in MUST_BE_SILENT else "?")
            )
            print(f"      {row:38s} {tag}  {r['per_row'][row]}")

    Path(__file__).with_name("order-conditioned-clef.json").write_text(
        json.dumps(results, indent=2)
    )
    print("\nwrote order-conditioned-clef.json")


if __name__ == "__main__":
    main()
