#!/usr/bin/env python3
"""Two follow-up probes the headline scorecards raised.

1. S3's PERMISSIVE arm. A natural-horn or trumpet staff in this repertoire
   prints NO key signature at all — accidentals are written inline. The
   pipeline records that as `key_signature_read: False` with `sharps=0,
   flats=0`, which is byte-identical to "the reader found nothing". So the
   strict arm abstains on exactly the staves S3 exists for. This arm asks what
   S3 is worth if an unread signature is taken at face value as an EMPTY one.

2. The multiplicity per-row table — specifically whether any page-side rule
   avoids the Dvořák over-count that cost the condensed-parts session +2,181.

    python3 benchmarks/omr-staff-identity-2026-09/probe_s3_and_multiplicity.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from tools.omr import instruments as INST                     # noqa: E402


def truth_instrument(r):
    n = r.get("CEILING_hand_label")
    m = INST.lookup(n) if n else None
    return m.instrument.name if m else None


def truth_offset(r):
    n = r.get("CEILING_hand_label")
    m = INST.lookup(n) if n else None
    return m.fifths_offset if m else None


def family(name):
    for x in INST.INSTRUMENTS:
        if x.name == name:
            return x.family
    return None


def main():
    E = json.loads((HERE / "evidence.json").read_text())["evidence"]
    S = json.loads((HERE / "scorecards.json").read_text())
    T = [r for r in E if truth_instrument(r)]
    out = {}

    print("=== 1. S3 STRICT vs PERMISSIVE ===")
    arms = {}
    for arm, gate in [
        ("strict (key_signature_read only)", lambda r: r["s3_read"]),
        ("permissive (unread == an empty printed signature)",
         lambda r: r["s3_page_modal_fifths"] is not None),
    ]:
        sp = [r for r in T if gate(r) and r["s3_implied_offset"] is not None
              and truth_offset(r) is not None]
        ok = [r for r in sp if r["s3_implied_offset"] == truth_offset(r)]
        tr = [r for r in sp if truth_offset(r) != 0]
        trok = [r for r in tr if r["s3_implied_offset"] == truth_offset(r)]
        arms[arm] = {"spoke": len(sp), "of": len(T), "exact": len(ok),
                     "precision": round(len(ok) / max(len(sp), 1), 4),
                     "transposing_spoke": len(tr), "transposing_exact": len(trok),
                     "transposing_precision": round(len(trok) / max(len(tr), 1), 4)}
        a = arms[arm]
        print(f"  {arm:52s} spoke {a['spoke']:3d}/{a['of']}  exact {a['exact']:3d}  "
              f"prec {a['precision']:.4f}  | transposing staves only "
              f"{a['transposing_exact']}/{a['transposing_spoke']} "
              f"({a['transposing_precision']:.4f})")
    out["s3_arms"] = arms

    print("\n=== 2. S3 coverage by instrument family (strict arm) ===")
    fam = {}
    for f in ("woodwind", "brass", "string", "percussion"):
        sub = [r for r in T if family(truth_instrument(r)) == f]
        sp = [r for r in sub if r["s3_read"] and r["s3_implied_offset"] is not None]
        ok = [r for r in sp if r["s3_implied_offset"] == truth_offset(r)]
        fam[f] = {"n": len(sub), "spoke": len(sp),
                  "coverage": round(len(sp) / max(len(sub), 1), 4),
                  "exact": len(ok),
                  "precision": round(len(ok) / max(len(sp), 1), 4) if sp else None}
        print(f"  {f:11s} n={len(sub):3d} spoke={len(sp):3d} "
              f"cov={fam[f]['coverage']:.3f} prec={fam[f]['precision']}")
    out["s3_by_family"] = fam

    print("\n  truth offsets, all truth rows:      ",
          dict(Counter(truth_offset(r) for r in T)))
    print("  truth offsets where S3 (strict) spoke:",
          dict(Counter(truth_offset(r) for r in T
                       if r["s3_read"] and r["s3_implied_offset"] is not None)))

    print("\n=== 3. MULTIPLICITY per row ===")
    rows = sorted({r["row_id"] for r in E if r["TRUTH_n_parts"]})
    names = ["always 1", "S1 label plurality", "S7 texture, stricter",
             "S7 AND S1-plurality", "S7+S8+S9+S1-plurality combined",
             "S9 placement"]
    hdr = f"{'row':32s}" + "".join(f"{n[:20]:>20s}" for n in names)
    print(hdr)
    table = {}
    for rid in rows:
        line = f"{rid[:32]:32s}"
        table[rid] = {}
        for n in names:
            rr = [x for x in S["multiplicity"]["rules"] if x["rule"].startswith(n)][0]
            e, o, u = rr["per_row_exact_over_under"].get(rid, [0, 0, 0])
            table[rid][n] = {"exact": e, "over": o, "under": u}
            line += f"{f'{e}/{e + o + u} +{o}-{u}':>20s}"
        print(line)
    out["multiplicity_per_row"] = table

    (HERE / "probe-s3-multiplicity.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
