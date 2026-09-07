#!/usr/bin/env python3
"""Which STAFF RECORDS differ between two arms — the forensics half.

An aggregate tells you a change moved 6 records; it does not tell you which 6,
and every identity fault fixed on 2026-09-06 was found by looking at named
staves on named pages.  This prints them.

    python3 probe/diff_arms.py ARM_A ARM_B [--all]

Refuses unless the two arms share a staff-record key set — otherwise the rows
it prints are not a comparison.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import arms as arms_mod          # noqa: E402
import load as load_mod          # noqa: E402
import score as score_mod        # noqa: E402


def graded(arm: str):
    work, path, regime, _ = arms_mod.ARMS[arm]
    r = score_mod.score(load_mod.load(path, work, arm), regime)
    return {(x["page"], x["system"], x["ordinal"]): x for x in r.records}, r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--all", action="store_true",
                    help="also print records both arms get wrong")
    ap.add_argument("--intersect", action="store_true",
                    help="compare only the records both arms hold — for "
                         "comparing two PAGE-SET REGIMES, where the key sets "
                         "cannot be equal by construction")
    args = ap.parse_args()

    A, ra = graded(args.a)
    B, rb = graded(args.b)
    if set(A) != set(B):
        if not args.intersect:
            print(f"REFUSING: the arms do not share a judgeable key set "
                  f"({len(set(A) ^ set(B))} keys differ).  Pass --intersect "
                  "if this is deliberately a cross-REGIME comparison.")
            return 1
        shared = set(A) & set(B)
        print(f"CROSS-REGIME: comparing the {len(shared)} judgeable records "
              f"both page sets contain (A has {len(A)}, B has {len(B)}).\n"
              "⚠️ These are the SAME PRINTED SYSTEMS.  A difference is the "
              "page set and nothing about the page.")
        A = {k: A[k] for k in shared}
        B = {k: B[k] for k in shared}

    print(f"A = {args.a}   {ra.correct}/{ra.n_judgeable} = {ra.rate:.4f}   "
          f"impossible {ra.impossible}  human {ra.human}")
    print(f"B = {args.b}   {rb.correct}/{rb.n_judgeable} = {rb.rate:.4f}   "
          f"impossible {rb.impossible}  human {rb.human}")
    print(f"shared judgeable key set: {len(A)} records")
    print()
    fixed = broke = same_wrong = 0
    rows = []
    for k in sorted(A):
        a, b = A[k], B[k]
        if a["emitted"] == b["emitted"]:
            if not a["correct"]:
                same_wrong += 1
                if args.all:
                    rows.append(("BOTH-WRONG", k, a, b))
            continue
        if b["correct"] and not a["correct"]:
            fixed += 1
            rows.append(("B-FIXES", k, a, b))
        elif a["correct"] and not b["correct"]:
            broke += 1
            rows.append(("B-BREAKS", k, a, b))
        else:
            rows.append(("BOTH-WRONG-DIFFERENTLY", k, a, b))
    print(f"B fixes {fixed}, B breaks {broke}, "
          f"both wrong the same way {same_wrong}")
    print()
    print(f"{'verdict':24s} {'page':>4s} {'sys':>3s} {'ord':>3s} {'n':>3s} "
          f"{'truth':16s} {'A emits':16s} {'B emits':16s} "
          f"{'A src':22s} {'B src'}")
    for verdict, (pg, sy, o), a, b in rows:
        print(f"{verdict:24s} {pg:4d} {sy:3d} {o:3d} {a['n_staves']:3d} "
              f"{str(a['truth']):16s} {str(a['emitted']):16s} "
              f"{str(b['emitted']):16s} {str(a['source']):22s} {b['source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
