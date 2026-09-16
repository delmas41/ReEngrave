"""S6 BROADENED — relax what qualifies as a STACK, keep the PAIR.

The narrow test paired two arcs of one cell that overlap in x by at least half
the narrower one AND are disjoint in y: 442 arcs, 181 disagreeing pairs,
agreement 0.740 inside 3 staff spaces.

⚠️⚠️ **THE ABSOLUTE-POSITION WIDENING IS NOT RE-TRIED, BECAUSE IT IS ALREADY
REFUTED HERE.** `s6_control.py` measured *"the arc nearer the noteheads is the
tie"* at **0.517** on the same band. S6's power is in the PAIRWISE comparison,
so every relaxation below keeps the pair and loosens only what counts as one:

  A. **x-overlap → x TOLERANCE.** Two arcs stacked on a scan need not overlap
     in x at all: the upper one is drawn wider. Allow an x GAP up to a
     multiple of the narrower arc's own width.
  B. **y-disjointness relaxed.** Allow the boxes to overlap slightly in y —
     a scan's two arcs bleed together.
  C. **`arc_owner` as the pairing**, not geometry alone.

⚠️ REACH IS REPORTED AT EVERY RELAXATION, before any agreement figure. A
relaxation that doubles the population while agreement holds is a materially
different result from one that dilutes it, and only the pair of numbers says
which.

⚠️ NOTHING IS TUNED. Every relaxation is a SWEEP printed whole.

Consumes `widen.py`'s `--out` (boxes, class, score, owner, cell).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict


def _is_tie(cls) -> bool:
    return str(cls).lower().startswith("tie")


def _binom_tail(k: int, n: int, p: float = 0.5) -> float:
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
               for i in range(k, n + 1))


def pairs_for(rows, *, x_gap_widths, y_overlap_frac, same_owner_only):
    """Every candidate stack under one relaxation, one entry per PAIR."""
    by_cell = defaultdict(list)
    for r in rows:
        by_cell[r["cell"]].append(r)
    out, seen = [], set()
    for cell_rows in by_cell.values():
        for a in cell_rows:
            ax0, ay0, ax1, ay1 = a["box"]
            for b in cell_rows:
                if a["subject"] == b["subject"]:
                    continue
                key = tuple(sorted((a["subject"], b["subject"])))
                if key in seen:
                    continue
                bx0, by0, bx1, by1 = b["box"]
                wa, wb = ax1 - ax0, bx1 - bx0
                narrow = max(1.0, min(wa, wb))
                ox = min(ax1, bx1) - max(ax0, bx0)
                # A: a NEGATIVE overlap is a gap; allow it up to the tolerance.
                if ox < -x_gap_widths * narrow:
                    continue
                oy = min(ay1, by1) - max(ay0, by0)
                ha, hb = ay1 - ay0, by1 - by0
                shallow = max(1.0, min(ha, hb))
                # B: a POSITIVE y-overlap is allowed up to the tolerance.
                if oy > y_overlap_frac * shallow:
                    continue
                if same_owner_only and not (
                        a["owner"] is not None and a["owner"] == b["owner"]):
                    continue
                seen.add(key)
                upper, lower = (a, b) if (ay0 + ay1) < (by0 + by1) else (b, a)
                out.append({
                    "upper": upper["subject"], "lower": lower["subject"],
                    "upper_cls": upper["cls"], "lower_cls": lower["cls"],
                    "y_gap": -oy, "x_overlap": ox / narrow,
                    "disagree": _is_tie(upper["cls"]) != _is_tie(lower["cls"]),
                    "s6_right": _is_tie(lower["cls"])})
    return out


def score(ps):
    d = [p for p in ps if p["disagree"]]
    k = sum(1 for p in d if p["s6_right"])
    return {"candidate_pairs": len(ps), "disagreeing": len(d),
            "lower_is_the_tie": k,
            "agreement": round(k / len(d), 4) if d else None,
            "p_binomial": round(_binom_tail(k, len(d)), 5) if d else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("widen_json")
    a = ap.parse_args(argv)
    rows = json.load(open(a.widen_json))["rows"]
    report = {"n_arcs": len(rows), "relaxations": []}

    # ⚠️ THE BASELINE ROW IS THE NARROW RULE, RE-DERIVED HERE, so a reader can
    # see the widening against it rather than against the other write-up.
    grid = [
        ("NARROW (x-overlap >= 0.5 narrower width, y-disjoint)", 0.0, 0.0, False),
        ("A: x gap up to 0.25 widths", 0.25, 0.0, False),
        ("A: x gap up to 0.5 widths", 0.5, 0.0, False),
        ("A: x gap up to 1.0 widths", 1.0, 0.0, False),
        ("B: y overlap up to 0.25 of the shallower", 0.0, 0.25, False),
        ("B: y overlap up to 0.5", 0.0, 0.5, False),
        ("A+B: x gap 0.5, y overlap 0.25", 0.5, 0.25, False),
        ("C: same arc_owner only, else NARROW", 0.0, 0.0, True),
        ("A+B+C: x 0.5, y 0.25, same owner", 0.5, 0.25, True),
    ]
    all_pairs = {}
    for name, xg, yo, so in grid:
        ps = pairs_for(rows, x_gap_widths=xg, y_overlap_frac=yo,
                       same_owner_only=so)
        all_pairs[name] = ps
        # ⚠️ The narrow rule ALSO required x-overlap >= 0.5 of the narrower
        # arc; at `x_gap_widths=0` this admits any positive overlap, which is
        # already a mild widening. Both are reported so the step is visible.
        strict = [p for p in ps if p["x_overlap"] >= 0.5]
        report["relaxations"].append({
            "relaxation": name, "x_gap_widths": xg,
            "y_overlap_frac": yo, "same_owner_only": so,
            "ALL": score(ps),
            "x_overlap_at_least_0.5": score(strict),
            # the dose-response band that carried the narrow result
            "within_3_staff_spaces": score(
                [p for p in ps if 0 < p["y_gap"] < 300]),
        })

    # ⚠️ THE DOSE-RESPONSE MUST SURVIVE THE WIDENING OR THE WIDENING IS
    # DILUTION. Recomputed on the loosest geometric relaxation.
    loose = all_pairs["A+B: x gap 0.5, y overlap 0.25"]
    report["dose_response_on_the_loosest"] = []
    for lo, hi in ((-99, 0), (0, 1), (1, 2), (2, 3), (0, 3), (3, 5), (5, 99)):
        sub = [p for p in loose if lo * 100 <= p["y_gap"] < hi * 100]
        report["dose_response_on_the_loosest"].append(
            {"gap_spaces": f"{lo}-{hi}", **score(sub)})

    json.dump(report, sys.stdout, indent=2)
    print()
    if not any(r["ALL"]["disagreeing"] for r in report["relaxations"]):
        print("DEAD: no disagreeing pair under any relaxation.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
