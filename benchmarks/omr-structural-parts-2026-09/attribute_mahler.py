"""Where does the Mahler regression actually land? Attribution before a build.

Phase 2 proved something OTHER than the count is costing on
`mahler-sym5-mvt1-local-p2/p3/p4/p5`: on p2, the one Mahler row with a
hand-verified map, the dossier assigns 26 players where the map assigns 34, so
we UNDER-count — and under-counting forgoes a gain, it cannot cause a
regression. Yet all four rows regress (+35 / +233 / +660 / +238).

This diffs the per-category musicdiff ops between `base` and `dossier_stitch`
on those four rows, from arms already scored. No new scoring, no build.

  If the cost is concentrated where DUPLICATION would put it — extra notes,
  wrong-note / note-head churn inside bars that now pair — Phase 3 (divisi by
  stem direction) has a target and Sean's hand-verified maps are worth asking
  for.

  If it lands somewhere else — whole-measure or whole-staff operations, or a
  category duplication does not touch — Phase 3 dies cheaply and the defect is
  a different one.

⚠️ THE MAHLER CONFOUND, for anyone who compares assigned parts to a dossier's
`n_parts` on this work. 38 is UNREACHABLE on these pages by construction:
Mahler 5 prints one-line percussion staves the five-line detector cannot find,
and a page suppresses tacet staves. `works.json`'s own map for p2 says **34,
not 38**. A sum against `n_parts` will always look short here and that is not
evidence about the counts.

⚠️ CEILING / REAL-USE. Every figure derives from dossier-fed arms, and dossiers
are generated from the same Gradus MusicXML that scores the run. Never a
benchmark figure.

    python3 benchmarks/omr-structural-parts-2026-09/attribute_mahler.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=str(HERE / "arms20-gates.json"))
    ap.add_argument("--baseline", default="base")
    ap.add_argument("--arm", default="dossier_stitch")
    ap.add_argument("--prefix", default="mahler")
    args = ap.parse_args()

    data = json.loads(Path(args.arms).read_text())
    base = {r["row"]: r for r in data[args.baseline]["rows"]}
    arm = {r["row"]: r for r in data[args.arm]["rows"]}
    rows = [r for r in base if r.startswith(args.prefix)]
    rows.sort()

    cats = set()
    for r in rows:
        cats |= set(base[r]["categories"]) | set(arm[r]["categories"])

    short = [r.split("local-")[-1] for r in rows]
    print(f"{args.arm} vs {args.baseline}, per category\n")
    print(f"{'category':<34} " + " ".join(f"{s:>8}" for s in short)
          + f"{'TOTAL':>9}")
    totals = {}
    for c in sorted(cats):
        deltas = [arm[r]["categories"].get(c, 0) - base[r]["categories"].get(c, 0)
                  for r in rows]
        totals[c] = sum(deltas)
        if any(deltas):
            print(f"{c:<34} " + " ".join(f"{d:>+8}" for d in deltas)
                  + f"{sum(deltas):>+9}")

    ned = [arm[r]["omr_ed"] - base[r]["omr_ed"] for r in rows]
    pred = [arm[r]["pred_symbols"] - base[r]["pred_symbols"] for r in rows]
    print(f"\n{'net edits':<34} " + " ".join(f"{d:>+8}" for d in ned)
          + f"{sum(ned):>+9}")
    print(f"{'predicted symbols':<34} " + " ".join(f"{d:>+8}" for d in pred)
          + f"{sum(pred):>+9}")

    print("\nlargest movers")
    for c, v in sorted(totals.items(), key=lambda kv: -abs(kv[1]))[:6]:
        if v:
            print(f"  {c:<32} {v:>+8}")

    struct = sum(v for c, v in totals.items() if "entire" in c)
    content = sum(v for c, v in totals.items() if "entire" not in c)
    print(f"\nstructural (entire measure/staff): {struct:+}")
    print(f"content (everything else):         {content:+}")
    print("\nDuplication would show as CONTENT — extra notes in bars that now "
          "pair.\nA structural residue means the parts still are not pairing, "
          "which divisi\ncannot fix.")


if __name__ == "__main__":
    main()
