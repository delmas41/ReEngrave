"""Would a UNION roster trip the guards `build_reference` already carries?

MEASUREMENT ONLY. Reads the 20-row scan gate read-only; writes nothing;
changes no pipeline behaviour.

⚠️ FIXTURE PROVENANCE. The 20-row gate lives ONLY in the reconciliation
worktree, suffix `.reconciliation.omr.json`. The main checkout's `fixtures/`
holds the 11-row `..graft09` set — a script pointed there measures the old gate.

## The question, and why it comes first

H1' proposes building the reference roster as the UNION over a page's systems,
because different systems suppress different staves (Beethoven 5 p.4: system 1
prints no Timpani, system 2 merges Violoncello and Basso into `Bassi`; both
count 11, so the union is 12). A union is by construction LARGER than any
system observed — which is exactly the shape `build_reference`'s two guards
were written to reject:

* `REFERENCE_MAX_SIZE_RATIO = 2.0` — drops a candidate system larger than
  2x the median, because a MERGED system (two concatenated) is ~2x its
  neighbours;
* `_looks_merged` — drops a candidate whose label sequence repeats an
  instrument after an intervening different one.

A guard written for one reason and firing for another is how the tenor symmetry
floor and the cap-at-2 both went wrong. So: measure the sizes, and read what
each guard is actually quantified over.

## What this probe can and cannot answer

CAN: the size distributions the guards act on, per row, and therefore whether a
union could ever approach the 2x cap.

⚠️ CANNOT: whether `_looks_merged` fires. It reads the RAW per-system label
dict, and the transcription retains only the resolved, post-join `instrument`
field — which is assigned BY the slot join and is therefore circular for this
purpose (the class-6 result). Any `_looks_merged` arm here would be measuring
the join, not the labels. Reported as an abstention, not imputed.
"""

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures"
)
SUFFIX = ".reconciliation.omr.json"
REFERENCE_MAX_SIZE_RATIO = 2.0   # mirrored from tools/omr/slots.py, not imported


def main() -> int:
    paths = sorted(FIXTURES.glob(f"*{SUFFIX}"))
    assert paths, f"EMPTY INPUT — no fixtures under {FIXTURES}"
    assert len(paths) == 20, f"expected the 20-row gate, found {len(paths)}"

    rows = []
    for path in paths:
        row = os.path.basename(path).split(".reconciliation")[0]
        doc = json.loads(path.read_text())
        systems = [s for pg in doc.get("pages", []) for s in pg.get("systems", [])
                   if s.get("staves")]
        sizes = [len(s["staves"]) for s in systems]
        assert sizes, f"no systems on {row}"
        median = statistics.median_low(sorted(sizes))
        rows.append({
            "row": row,
            "n_systems": len(systems),
            "sizes": sizes,
            "max": max(sizes),
            "median": median,
            "cap": median * REFERENCE_MAX_SIZE_RATIO,
            # The union can be no smaller than the largest system, and no larger
            # than the sum (every system disjoint — impossible in practice, but
            # it is the only bound derivable without a correspondence).
            "union_lower_bound": max(sizes),
            "union_upper_bound": sum(sizes),
        })

    n_staves = sum(sum(r["sizes"]) for r in rows)
    assert n_staves == 396, f"expected 396 staves, counted {n_staves}"

    print(f"fixtures: {len(paths)}   staves: {n_staves}   "
          f"(provenance: {FIXTURES})\n")
    hdr = (f"{'row':46s} {'sys':>3} {'sizes':>16} {'med':>4} {'cap':>5} "
           f"{'u_lo':>5} {'u_hi':>5} {'lo>cap?':>8}")
    print(hdr)
    print("-" * len(hdr))
    trips = 0
    multi = 0
    for r in rows:
        if r["n_systems"] > 1:
            multi += 1
        over = r["union_lower_bound"] > r["cap"]
        trips += bool(over)
        print(f"{r['row']:46s} {r['n_systems']:>3} {str(r['sizes']):>16} "
              f"{r['median']:>4} {r['cap']:>5.1f} {r['union_lower_bound']:>5} "
              f"{r['union_upper_bound']:>5} {'YES' if over else 'no':>8}")

    print()
    print("=== census (the corrected one — see HYPOTHESES.md) ===")
    single = sum(1 for r in rows if r["n_systems"] == 1)
    refuse = sum(1 for r in rows
                 if r["n_systems"] > 1 and len(set(r["sizes"])) != 1)
    succeed = sum(1 for r in rows
                  if r["n_systems"] > 1 and len(set(r["sizes"])) == 1)
    print(f"  rows                        : {len(rows)}")
    print(f"  multi-system                : {multi}")
    print(f"  ordinal join SUCCEEDS       : {succeed}")
    print(f"  ordinal join REFUSES        : {refuse}")
    print(f"  single-system               : {single}")
    assert single + refuse + succeed == len(rows)

    print()
    print("=== guard interaction ===")
    print(f"  rows where the union's LOWER bound already exceeds the "
          f"2x-median cap: {trips}")
    print("  ⚠️ _looks_merged: NOT MEASURED — it reads the raw per-system label")
    print("     dict, which the transcription does not retain. The resolved")
    print("     `instrument` field is assigned BY the join and is circular here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
