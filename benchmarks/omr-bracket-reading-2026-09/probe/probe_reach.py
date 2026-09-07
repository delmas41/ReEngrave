"""REACH: on how many systems does the left edge STATE a family partition?

Reads `probe_strokes.py`'s dump and asks, per system, three questions in order:

  1. Is there a vertical RULE at the left edge at all?  (shape gate below)
  2. Do the rules that cover only PART of the system tile it into >= 2
     contiguous blocks that between them account for every staff?
  3. If so, what partition do they state?

Question 2 is the one that matters: a rule spanning the whole system is a
bracket over the whole orchestra or the systemic barline, and either way it
distinguishes no gap from any other — the same object `systemic_column_counts`
already drops.  A family bracket is a rule that stops.

    probe_reach.py out/scan-strokes.json --out out/reach.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

# ── Shape gate ───────────────────────────────────────────────────────────────
# A bracket and a systemic barline are both THIN STRAIGHT vertical rules.  The
# band also contains music: a beam reaching left of the staff, a bass clef's
# body, a slur.  Measured on the dump, those come in at 2.2-3.5 staff spacings
# thick with straightness 0.0, against 0.3-1.6 and ~1.0 for the rules.
MAX_THICKNESS_SPACINGS = 1.75
MIN_STRAIGHTNESS = 0.85


def is_rule(st: dict) -> bool:
    return (st["thickness_spacings"] <= MAX_THICKNESS_SPACINGS
            and st["straightness"] >= MIN_STRAIGHTNESS)


def classify(system: dict) -> dict:
    n = system["n_staves"]
    rules = [s for s in system["strokes"] if is_rule(s)]
    spanning = [s for s in rules if len(s["covers"]) == n]
    partial = [s for s in rules if 0 < len(s["covers"]) < n]

    # A partition is stated when the partial rules are disjoint, contiguous,
    # and between them account for every staff.
    blocks = sorted(
        ({tuple(s["covers"]) for s in partial}),
        key=lambda c: c[0]) if partial else []
    covered: list[int] = []
    for b in blocks:
        covered.extend(b)
    contiguous = all(b == tuple(range(b[0], b[-1] + 1)) for b in blocks)
    complete = sorted(covered) == list(range(n)) and len(covered) == n
    states = bool(blocks) and len(blocks) >= 2 and contiguous and complete

    return {
        "n_staves": n,
        "n_rules": len(rules),
        "n_spanning": len(spanning),
        "n_partial": len(partial),
        "blocks": [list(b) for b in blocks],
        "sizes": [len(b) for b in blocks],
        "contiguous": contiguous,
        "complete": complete,
        "states_partition": states,
        "any_rule": bool(rules),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--min-staves", type=int, default=4,
                    help="ignore trivially small systems")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    report = json.loads(Path(args.dump).read_text())
    per_pub: dict[str, list[dict]] = defaultdict(list)
    rows = []
    for page in report:
        for sy in page["systems"]:
            if sy["n_staves"] < args.min_staves:
                continue
            c = classify(sy)
            c.update(tag=page["tag"], page=page["page"],
                     system=sy["system_index"])
            per_pub[page["tag"]].append(c)
            rows.append(c)

    print(f"{'publisher':<12} {'systems':>8} {'any rule':>9} {'spanning':>9} "
          f"{'partial>0':>10} {'STATES':>8}")
    for pub in sorted(per_pub):
        rs = per_pub[pub]
        print(f"{pub:<12} {len(rs):>8} "
              f"{sum(r['any_rule'] for r in rs):>9} "
              f"{sum(r['n_spanning'] > 0 for r in rs):>9} "
              f"{sum(r['n_partial'] > 0 for r in rs):>10} "
              f"{sum(r['states_partition'] for r in rs):>8}")
    print(f"{'TOTAL':<12} {len(rows):>8} "
          f"{sum(r['any_rule'] for r in rows):>9} "
          f"{sum(r['n_spanning'] > 0 for r in rows):>9} "
          f"{sum(r['n_partial'] > 0 for r in rows):>10} "
          f"{sum(r['states_partition'] for r in rows):>8}")

    print("\nStated partitions, by publisher and staff count:")
    for pub in sorted(per_pub):
        by_n: dict[int, Counter] = defaultdict(Counter)
        for r in per_pub[pub]:
            if r["states_partition"]:
                by_n[r["n_staves"]][tuple(r["sizes"])] += 1
        for n in sorted(by_n):
            print(f"  {pub:<11} {n:>3} staves: "
                  + ", ".join(f"{list(k)}x{v}" for k, v
                              in by_n[n].most_common()))

    Path(args.out).write_text(json.dumps(rows, indent=1))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
