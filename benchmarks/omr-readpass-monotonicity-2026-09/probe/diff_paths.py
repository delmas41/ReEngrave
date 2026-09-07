#!/usr/bin/env python3
"""`diff_arms.py` for two artefact PATHS instead of two registered arm names.

Same scorer, same key-set refusal.  Exists only because the arms here are made
by this benchmark and are not in `arms.py`.

    diff_paths.py WORK A.json B.json [--all]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HARNESS = (Path(__file__).resolve().parents[2]
           / "omr-identity-harness-2026-09" / "probe")
sys.path.insert(0, str(HARNESS))

import load as load_mod          # noqa: E402
import score as score_mod        # noqa: E402


def graded(work: str, path: str):
    r = score_mod.score(load_mod.load(Path(path).resolve(), work,
                                      Path(path).stem), "whole work 0-87")
    return {(x["page"], x["system"], x["ordinal"]): x for x in r.records}, r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    A, ra = graded(args.work, args.a)
    B, rb = graded(args.work, args.b)
    if set(A) != set(B):
        print(f"REFUSING: key sets differ by {len(set(A) ^ set(B))}")
        return 1
    print(f"A = {Path(args.a).stem}  {ra.correct}/{ra.n_judgeable} = "
          f"{ra.rate:.4f}  impossible {ra.impossible}  human {ra.human}")
    print(f"B = {Path(args.b).stem}  {rb.correct}/{rb.n_judgeable} = "
          f"{rb.rate:.4f}  impossible {rb.impossible}  human {rb.human}")
    print(f"shared judgeable key set: {len(A)} records\n")

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
          f"both wrong the same way {same_wrong}\n")
    print(f"{'verdict':24s} {'page':>4s} {'sys':>3s} {'ord':>3s} {'n':>3s} "
          f"{'truth':16s} {'A emits':16s} {'B emits':16s} "
          f"{'A src':22s} {'B src'}")
    shown = rows if not args.limit else rows[:args.limit]
    for verdict, (pg, sy, o), a, b in shown:
        print(f"{verdict:24s} {pg:4d} {sy:3d} {o:3d} {a['n_staves']:3d} "
              f"{str(a['truth']):16s} {str(a['emitted']):16s} "
              f"{str(b['emitted']):16s} {str(a['source']):22s} {b['source']}")
    if args.limit and len(rows) > args.limit:
        print(f"... {len(rows) - args.limit} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
