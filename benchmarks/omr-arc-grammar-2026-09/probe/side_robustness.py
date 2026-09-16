"""Is S4's SIDE determination robust, or is the refutation the probe's fault?

`s4_axis` decides whether the arc lies above or below its heads from the
MEDIAN y-centre of all flanked heads, then takes the arc's near edge as the
bbox edge on that side. **If an arc spans heads at very different heights, that
one decision can be wrong for one of the two endpoints** — and since SIDE is
`sign(t_axis)`, a wrong side flips the sign and would make the SIDE rule look
flat for a reason that has nothing to do with Sean's convention.

⚠️ THIS IS A CHECK ON THE REFUTATION, NOT ON THE RULE. A refutation produced by
a probe defect is worth nothing, and this repo's record is that the expensive
mistakes are instruments that were answering a different question confidently.
So the disagreement is measured before the refutation is reported.

Two determinations per arc, compared:
  * **MEDIAN** — what `widen.py` uses: above/below the median flanked head.
  * **PER-ENDPOINT** — above/below THAT endpoint's own outer head.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[2]))
_spec = importlib.util.spec_from_file_location("_reach", _HERE / "reach.py")
_reach = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reach)

from tools.omr.staged import export as E                        # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record")
    a = ap.parse_args(argv)
    rec = E.Record(json.load(open(a.record)))
    heads_by_cell = _reach._heads_by_cell(rec)
    stems_by_cell = _reach._stems_by_cell(rec)

    agree = disagree = 0
    flips = Counter()
    head_spread = []
    for arc in _reach._arc_rows(rec):
        heads = _reach._flanked(arc["box"], heads_by_cell.get(arc["cell"], []))
        stems = stems_by_cell.get(arc["cell"], [])
        if not heads:
            continue
        ax0, ay0, ax1, ay1 = arc["box"]
        arc_yc = (ay0 + ay1) / 2.0
        med_above = arc_yc < statistics.median(h["yc"] for h in heads)
        outer = [heads[0], heads[-1]]
        if len(heads) > 1:
            head_spread.append(abs(heads[0]["yc"] - heads[-1]["yc"]))
        for h in outer:
            if not [s for s in stems if _reach._overlap(s, h["box"])]:
                continue
            own_above = arc_yc < h["yc"]
            if own_above == med_above:
                agree += 1
            else:
                disagree += 1
                flips["median says above, its own head says below"
                      if med_above else
                      "median says below, its own head says above"] += 1

    total = agree + disagree
    out = {
        "stemmed_outer_endpoints": total,
        "the_two_determinations_AGREE": agree,
        "they_DISAGREE": disagree,
        "disagreement_rate": round(disagree / total, 4) if total else None,
        "flips": dict(flips),
        "vertical_spread_of_the_outer_flanked_heads_canonical_px":
            {"n": len(head_spread),
             "median": round(statistics.median(head_spread), 1)
             if head_spread else None,
             "p90": round(sorted(head_spread)[int(0.9 * (len(head_spread) - 1))], 1)
             if head_spread else None,
             "max": round(max(head_spread), 1) if head_spread else None},
    }
    json.dump(out, sys.stdout, indent=2)
    print()
    if total == 0:
        print("DEAD: no stemmed outer endpoint to check.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
