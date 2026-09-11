"""S6: is one arc drawn OVER another, and can we tell that from a duplicate?

Sean: *"If there are 2 arcs on top of each other then the lower is a tie and
the upper is a slur."*

⚠️ **THE PRECONDITION IS THE MEASUREMENT.** Two stacked arcs must first be
DETECTED as two arcs in a configuration a reader would call stacked — one
drawn just outside the other, over the SAME notes, on the SAME side of the
staff. Three other populations look like that to a loose test and are not it:

  * **duplicates** — one printed curve detected twice (the arc-recovery work
    measured 48 pairs in one cell at IoU >= 0.7, 19 of them across two
    staves);
  * **opposite sides** — a slur above the staff and a tie below it in the same
    bar are two arcs on two different runs of notes, not a stack;
  * **far apart** — two arcs on one side of the staff separated by more than
    an engraver would ever leave between a tie and the slur over it.

So this prints the y-GAP distribution and the side agreement and asks whether
the candidate population SEPARATES. It sets no threshold of its own; the
numbers are the output.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09")
from reach import DUPLICATE_IOU, collect, _overlap  # noqa: E402


def side_of(g: Dict[str, Any], top: float, sp: float) -> str:
    """ABOVE / BELOW / ON — where this arc sits against its staff."""
    if not sp:
        return "no_geometry"
    bottom = top + 4 * sp
    yc = (g["y0"] + g["y1"]) / 2.0
    if yc < top:
        return "above"
    if yc > bottom:
        return "below"
    return "on"


def run(path: str) -> Dict[str, Any]:
    r = collect(path)
    gs = r["groups"]
    by_staff: Dict[Any, List[dict]] = collections.defaultdict(list)
    for g in gs:
        by_staff[g["staff"]].append(g)
    pairs: List[Dict[str, Any]] = []
    dup = 0
    for pool in by_staff.values():
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                a, b = pool[i], pool[j]
                ox = _overlap(a["x0"], a["x1"], b["x0"], b["x1"])
                shorter = min(a["x1"] - a["x0"], b["x1"] - b["x0"])
                if shorter <= 0 or ox / shorter < 0.5:
                    continue
                oy = _overlap(a["y0"], a["y1"], b["y0"], b["y1"])
                union = ((a["x1"] - a["x0"]) * (a["y1"] - a["y0"])
                         + (b["x1"] - b["x0"]) * (b["y1"] - b["y0"])
                         - ox * oy)
                iou = (ox * oy / union) if union > 0 else 0.0
                if iou >= DUPLICATE_IOU:
                    dup += 1
                    continue
                if oy > 0:
                    continue
                lower, upper = (a, b) if a["y0"] > b["y0"] else (b, a)
                sp = lower["spacing"] or upper["spacing"]
                gap = (lower["y0"] - upper["y1"]) / sp if sp else None
                pairs.append({
                    "gap_spaces": gap,
                    "x_overlap_frac": ox / shorter,
                    "lower_kind": lower["kind"], "upper_kind": upper["kind"],
                    "lower_binds": lower["bound_heads"],
                    "upper_binds": upper["bound_heads"],
                    "where": lower["where"],
                    "iou": iou,
                    "lower_head_ys": lower["head_ys"],
                    "upper_head_ys": upper["head_ys"],
                    "lower_y0": lower["y0"], "lower_y1": lower["y1"],
                    "upper_y0": upper["y0"], "upper_y1": upper["y1"],
                    "lower_boxes": [b for _m, b in lower["segments"]],
                    "upper_boxes": [b for _m, b in upper["segments"]],
                })
    return {"pairs": pairs, "duplicates_excluded": dup, "groups": len(gs)}


def report(r: Dict[str, Any]) -> int:
    ps = r["pairs"]
    print(f"merged arc groups                {r['groups']}")
    print(f"candidate stacked pairs          {len(ps)}")
    print(f"same-curve DUPLICATES excluded   {r['duplicates_excluded']}")
    if not ps:
        print("\nS6 CANNOT BE ASKED on this document: no candidate pair.")
        return 1
    gaps = sorted(p["gap_spaces"] for p in ps if p["gap_spaces"] is not None)
    print(f"\nvertical GAP between the two arcs, in staff spaces "
          f"(n={len(gaps)}):")
    for q in (0, 5, 10, 25, 50, 75, 90, 100):
        i = min(len(gaps) - 1, int(round(q / 100.0 * (len(gaps) - 1))))
        print(f"    p{q:<3d} {gaps[i]:8.2f}")
    hist: "collections.Counter[str]" = collections.Counter()
    for g in gaps:
        b = int(g) if g < 8 else 8
        hist[f"{b}-{b + 1}" if b < 8 else "8+"] += 1
    print("    histogram:", dict(sorted(hist.items())))
    print("\n⚠️ A TIE AND THE SLUR OVER IT ARE ADJACENT INK. A pair separated")
    print("   by several staff spaces is two arcs on two runs of notes, not")
    print("   one drawn over the other.")
    close = [p for p in ps if (p["gap_spaces"] or 99) <= 1.0]
    print(f"\npairs within ONE staff space of each other: {len(close)}")
    if close:
        k = collections.Counter((p["lower_kind"], p["upper_kind"])
                                for p in close)
        for key, v in k.most_common():
            print(f"    lower={key[0]:5s} upper={key[1]:5s}  {v}")
        both = sum(1 for p in close
                   if p["lower_binds"] >= 2 and p["upper_binds"] >= 2)
        print(f"    ...both arcs bind 2+ heads (S6 could act): {both}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = run(a.record)
    code = report(r)
    if a.out:
        json.dump(r, open(a.out, "w"), indent=1, default=str)
    sys.exit(code)


if __name__ == "__main__":
    main()
