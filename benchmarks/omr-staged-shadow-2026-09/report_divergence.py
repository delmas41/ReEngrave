"""Read a staged `--against` result as Step 2 asks for it.

  "A divergence list ranked by how many staves each disagreement touches,
   each traceable to the decision that caused it."

⚠️ NOT A SCORE, and the counts are not a scoreboard. `new_abstention` is a
FEATURE THAT SCORES AS A LOSS -- a decision that declines to guess makes a
symbol-counting metric worse -- so the abstention column is read BEFORE the
agreement column, never after. The precedent is in the tree: `OMR_SLOT_STITCH`
is structurally right, doubles its named bucket, and ships default-off with
the reason recorded.

⚠️ READ `staged_only` AND `coverage` FIRST. They say what fraction of the
staged path's decisions the table can see at all. A table that compares 9 of
15 quantities and reports 96% agreement has said almost nothing, and until
2026-09-08 it did not say which 9.

Usage:
    python3 benchmarks/omr-staged-shadow-2026-09/report_divergence.py staged.json
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("staged_json")
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()

    d = json.load(open(a.staged_json))
    div = d.get("divergence")
    if div is None:
        print("no divergence block -- was this run with --against?")
        return 1

    print("== COVERAGE: what the table can see at all " + "=" * 30)
    cov = div.get("coverage", {})
    comp = cov.get("compared", [])
    stg = cov.get("staged_quantities", [])
    print(f"  staged decides {len(stg)} quantities; the table compares "
          f"{len(comp)}")
    print(f"  compared            : {', '.join(comp)}")
    if cov.get("staged_not_extracted"):
        print(f"  ⚠️ NOT extracted     : {', '.join(cov['staged_not_extracted'])}")
    if cov.get("extractable_but_legacy_silent"):
        print("  extractable, legacy silent HERE: "
              + ", ".join(cov["extractable_but_legacy_silent"])
              + "   (not missing code)")
    if cov.get("legacy_not_decided"):
        print(f"  legacy-only quantity: {', '.join(cov['legacy_not_decided'])}")

    so = div.get("staged_only", {})
    if so:
        print("\n== STAGED-ONLY: decided, but compared against nothing " + "=" * 14)
        for q, e in sorted(so.items(), key=lambda kv: -sum(
                v for k, v in kv[1].items() if k != "kinds")):
            print(f"  {q:<20} decided {e['decided']:>4}  "
                  f"abstained {e['abstained']:>4}  narrowed {e['narrowed']:>3}"
                  f"   {e['kinds']}")

    print("\n== OUTCOMES " + "=" * 62)
    counts = div.get("counts", {})
    order = ["new_abstention", "new_narrowing", "differ", "not_comparable",
             "agree", "new_decision", "legacy_only", "staged_only"]
    for k in order:
        if k in counts:
            flag = "   <- a feature that scores as a loss" \
                if k == "new_abstention" else ""
            print(f"  {k:<18} {counts[k]:>6}{flag}")

    ranked = div.get("ranked", [])
    print(f"\n== RANKED DISAGREEMENTS ({len(ranked)}), widest first " + "=" * 22)
    if not ranked:
        print("  none -- the two paths agree wherever both decided")
    for r in ranked[: a.top]:
        b = r.get("basis") or {}
        rests = b.get("rests_on") or {}
        print(f"\n  [{r['staves_touched']:>3} staves] {r['quantity']}  "
              f"@ {r['subject']}   ({r['outcome']})")
        print(f"      legacy={r['legacy']!r}")
        print(f"      staged={r['staged']!r}   reason={r.get('reason')!r}")
        if rests:
            print("      rests on: " + ", ".join(
                f"{q}x{n}" for q, n in sorted(rests.items())))
        elif b:
            print(f"      rests on: (basis of {b.get('n_rows')} rows)")
    if len(ranked) > a.top:
        print(f"\n  ... {len(ranked) - a.top} more")

    ag = d.get("agreement")
    if ag:
        print("\n== GROUPS: did any redundancy actually CORROBORATE " + "=" * 16)
        for name, g in sorted(ag.items()) if isinstance(ag, dict) else []:
            if not isinstance(g, dict):
                continue
            v = g.get("verdicts") or g.get("counts") or {}
            print(f"  {name:<34} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
