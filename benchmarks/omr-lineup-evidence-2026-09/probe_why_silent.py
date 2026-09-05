"""Why the order-conditioned transposition source is silent, and a cross-scan control.

Two questions the headline numbers cannot answer on their own.

(1) WHY does `R3p_ordered` fire 0/20 -- is the intersection rule rejecting real
    evidence, or does the source never get to speak?  Answered by walking the
    decisive position (Beethoven 5 p.4, position 6, where one system prints
    Timpani and the other a violin) and printing every gate it passes or fails.
    "The rule was too strict" and "the page prints nothing there" are different
    findings and must not be reported as one.

(2) A CROSS-SCAN CONTROL that costs nothing and is available only here.
    `beethoven-sym5-mvt1-984073-p4` and `-575951-p4` are two independent scans
    of the SAME 1870 Litolff plate.  Whatever the true lineup evidence is, it is
    a property of the plate, so a sound screen must produce the SAME hits on
    both and a screen whose hits differ between them is reading scan noise.
    This is a reproducibility test no other row in the corpus can supply.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave")
from tools.omr import score_layouts as sl
from tools.omr.instruments import lookup

sys.path.insert(0, str(Path(__file__).parent))
from probe_order_conditioned import RECON, LADDER, fifths, offset_of, load


def main():
    rows, labels, meta = load()
    assert len(rows) == 20 and len(labels) == 20

    print("=== (1) THE DECISIVE POSITION, GATE BY GATE ===")
    print("Beethoven 5 p.4: system 0 pos 6 is a violin (unlabelled, Litolff")
    print("prints no string names); system 1 pos 6 prints `Tp.` = Timpani.\n")
    for row in ("beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"):
        print(f"-- {row}")
        sysd = rows[row]
        fits = {}
        for i, staves in enumerate(sysd):
            labs = labels[row].get(i, {})
            clefs = {j: st["clef"] for j, st in enumerate(staves) if st["clef"]}
            fits[i] = sl.fit_layouts(len(staves), labels=labs or None, clefs=clefs or None)
        for p in range(len(sysd[0])):
            line = [f"   pos {p:2d}"]
            for i in (0, 1):
                st = sysd[i][p]
                lab = labels[row].get(i, {}).get(p)
                cA = Counter(
                    x["fifths"] for x in sysd[i] if x["ks_read"]
                ).most_common(1)
                concert = cA[0][0] if cA else None
                sup = []
                f = fits[i]
                if f is not None and p < len(f.support):
                    sup = [n for n in (f.support[p] or {}) if n]
                if st["ks_read"] and concert is not None:
                    off = st["fifths"] - concert
                    cand = sorted(n for n in sup if offset_of(n) == off)
                    ks = f"fifths={st['fifths']:+d} off={off:+d} cand={cand}"
                else:
                    ks = "KS NOT READ"
                line.append(
                    f"sys{i}[label={str(lab):8s} clef={str(st['clef']):11s} {ks}]"
                )
            print("  ".join(line))
        print()

    print("=== (1b) JOINT KEY-SIGNATURE COVERAGE ON EQUAL-COUNT PAIRS ===")
    print("A pair position can only speak when BOTH systems read a signature.")
    tot = both = neither = one = 0
    for row in sorted(rows):
        sysd = rows[row]
        counts = [len(s) for s in sysd]
        for a in range(len(sysd)):
            for b in range(a + 1, len(sysd)):
                if counts[a] != counts[b]:
                    continue
                for p in range(counts[a]):
                    tot += 1
                    ra, rb = sysd[a][p]["ks_read"], sysd[b][p]["ks_read"]
                    both += ra and rb
                    one += ra ^ rb
                    neither += not ra and not rb
    print(f"  pair positions on equal-count systems : {tot}")
    print(f"    both systems read a signature       : {both}  ({both/tot:.3f})")
    print(f"    exactly one did                     : {one}  ({one/tot:.3f})")
    print(f"    neither did                         : {neither}  ({neither/tot:.3f})")

    print("\n=== (2) CROSS-SCAN CONTROL: two scans of one 1870 Litolff plate ===")
    ev = json.loads((Path(__file__).with_name("lineup-evidence.json")).read_text())
    oc = json.loads((Path(__file__).with_name("order-conditioned.json")).read_text())
    a, b = "beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"
    pa = ev["per_row"][a]["pairs"][0]
    pb = ev["per_row"][b]["pairs"][0]
    print(f"  R1 expected-absence  {a[-11:]}: {pa['R1']}")
    print(f"  R1 expected-absence  {b[-11:]}: {pb['R1']}")
    same = [tuple(x[:2]) for x in pa["R1"]] == [tuple(x[:2]) for x in pb["R1"]]
    print(f"  -> identical hits across the two scans: {same}")
    ca = {x[0] for x in oc["detail"][a]["R2_clef"]}
    cb = {x[0] for x in oc["detail"][b]["R2_clef"]}
    print(f"\n  R2 clef positions {a[-11:]}: {sorted(ca)}")
    print(f"  R2 clef positions {b[-11:]}: {sorted(cb)}")
    print(f"  -> shared {sorted(ca & cb)}, scan-only {sorted(ca ^ cb)}; "
          f"Jaccard {len(ca & cb)/len(ca | cb):.2f}")
    ka = {x[0] for x in oc["detail"][a]["R3_raw"]}
    kb = {x[0] for x in oc["detail"][b]["R3_raw"]}
    print(f"\n  R3raw key positions {a[-11:]}: {sorted(ka)}")
    print(f"  R3raw key positions {b[-11:]}: {sorted(kb)}")
    j = len(ka & kb) / len(ka | kb) if (ka | kb) else float("nan")
    print(f"  -> shared {sorted(ka & kb)}, scan-only {sorted(ka ^ kb)}; Jaccard {j:.2f}")


if __name__ == "__main__":
    main()
