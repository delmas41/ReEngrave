"""Does S6 add anything to "the arc that HUGS its noteheads is the tie"?

S6 says *of two stacked arcs the LOWER is the tie*. On a page whose arcs sit
ABOVE the staff the lower arc is also the one nearer the noteheads — so S6
may be nothing more than the hugging rule `arc_owner` already runs, restated
in vertical order. That is the question this asks, and it is asked BEFORE the
dose-response is believed.

⚠️⚠️ THE FIRST CONTROL WRITTEN FOR THIS WAS DEGENERATE AND IS RECORDED HERE
RATHER THAN QUIETLY REPLACED. It classified each arc alone as above or below
its CELL's median arc height. For a pair drawn in one cell, "the median lies
between them" is exactly when that arm answers — and there it makes the SAME
prediction as S6 by construction, so its apparently better rate (0.702
against 0.630) was S6's own rate on the easier subset, not a second opinion.
**An arm that is the arm under test, restricted, cannot control it.** This
file's own subject matter arriving against its author.

The three arms below are genuinely different questions:

  * **S6**      — of the pair, the LOWER arc is the tie.  (vertical order)
  * **HUGS**    — of the pair, the arc nearer the cell's noteheads is the
                  tie.  (distance, not order — and on an arc drawn BELOW the
                  staff it points the opposite way from S6, which is what
                  makes it a control rather than a synonym)
  * **COIN**    — 0.5, the base rate for a pair whose readings disagree.

`agree_with_each_other` is the number that decides whether S6 is a new fact:
where HUGS and S6 always coincide, S6 has told us nothing `arc_owner` does
not already read off the same ink.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def _is_tie(cls) -> bool:
    return str(cls).lower().startswith("tie")


def _binom_tail(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k) for X ~ Binom(n, p). Exact, stdlib only."""
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
               for i in range(k, n + 1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reach_json")
    ap.add_argument("--heads", required=True,
                    help="JSON from head_y.py: cell -> median notehead y")
    args = ap.parse_args(argv)
    data = json.load(open(args.reach_json))
    rows = {r["subject"]: r for r in data["rows"]}
    head_y = json.load(open(args.heads))

    ymid = {s: (r["box"][1] + r["box"][3]) / 2.0 for s, r in rows.items()}

    pairs, seen = [], set()
    for r in rows.values():
        for c in r["s6"]:
            key = tuple(sorted((r["subject"], c["other"])))
            if key in seen or c["y_gap"] <= 0 or c["x_overlap_frac"] < 0.5:
                continue
            seen.add(key)
            upper, lower = ((r["subject"], c["other"]) if c["arc_is_upper"]
                            else (c["other"], r["subject"]))
            if _is_tie(rows[upper]["cls"]) == _is_tie(rows[lower]["cls"]):
                continue                      # S6 addresses disagreement only
            hy = head_y.get(rows[lower]["cell"])
            hugs = None
            if hy is not None:
                du = abs(ymid[upper] - hy)
                dl = abs(ymid[lower] - hy)
                if du != dl:
                    # HUGS predicts: the NEARER arc is the tie.
                    nearer = lower if dl < du else upper
                    hugs = _is_tie(rows[nearer]["cls"])
            pairs.append(dict(
                y_gap=c["y_gap"],
                same_owner=(r["owner"] == c["other_owner"]
                            and r["owner"] is not None),
                s6_right=_is_tie(rows[lower]["cls"]),
                hugs_right=hugs,
                # Do the two arms make the SAME prediction on this pair?
                same_prediction=(hy is not None
                                 and (abs(ymid[lower] - hy)
                                      < abs(ymid[upper] - hy)))))

    def table(sub):
        n = len(sub)
        s6 = sum(1 for p in sub if p["s6_right"])
        hn = [p for p in sub if p["hugs_right"] is not None]
        hk = sum(1 for p in hn if p["hugs_right"])
        coincide = sum(1 for p in sub if p["same_prediction"])
        return {
            "disagreeing_pairs": n,
            "S6_agreement": round(s6 / n, 4) if n else None,
            "S6_p_binomial": round(_binom_tail(s6, n), 5) if n else None,
            "HUGS_answers": len(hn),
            "HUGS_agreement": round(hk / len(hn), 4) if hn else None,
            "arms_make_the_SAME_prediction": coincide,
            "arms_coincide_rate": round(coincide / n, 4) if n else None,
            "COIN": 0.5,
        }

    report = {"all_disagreeing_stack_pairs": table(pairs),
              "by_y_gap_staff_spaces": [],
              "same_owner": table([p for p in pairs if p["same_owner"]]),
              "different_owner": table([p for p in pairs
                                        if not p["same_owner"]])}
    for lo_b, hi_b in ((0, 1), (1, 2), (2, 3), (0, 3), (3, 5), (5, 99)):
        sub = [p for p in pairs if lo_b * 100 <= p["y_gap"] < hi_b * 100]
        report["by_y_gap_staff_spaces"].append(
            {"gap_spaces": f"{lo_b}-{hi_b}", **table(sub)})

    json.dump(report, sys.stdout, indent=2)
    print()
    if not pairs:
        print("DEAD: no disagreeing stack pair on this record.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
