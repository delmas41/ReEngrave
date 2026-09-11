"""Are S6's candidate stacks TWO PRINTED ARCS, or ONE curve detected twice?

The arc-recovery work left a named, unrepaired defect: `_place_arcs` sends
every arc to the cell its OWNER names, so where ONE printed curve is detected
on two staves BOTH detections name the same owner and BOTH are placed — 48
pairs in one cell at IoU >= 0.7, 19 of them across two staves. **An arc is
thin, so two boxes of one curve a few pixels apart in y overlap by NOTHING and
score IoU 0.0** — an IoU filter cannot see that half of the population, and
what it leaves behind looks exactly like a stack.

This asks the question IoU cannot. For each candidate pair it joins the two
arcs back to their `Q.ARC_BOX` rows by exact page box and reports:

  * were they DETECTED ON DIFFERENT STAVES?  One printed curve seen twice.
  * do they carry the SAME detector class?   An engraver does not print a tie
    over a tie.
  * do their spans coincide?                 A tie under a phrase slur is
                                             SHORTER than the slur; two boxes
                                             of one curve are the same length.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from typing import Any, Dict, List, Tuple

from tools.omr.staged import export as E
from tools.omr.staged.record import Q

sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09")
sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09/probe")
from s6_stacks import run as stacks_run  # noqa: E402


def arc_rows(path: str) -> Dict[Tuple[float, ...], List[Dict[str, Any]]]:
    rec = E.Record(json.load(open(path)))
    out: Dict[Tuple[float, ...], List[Dict[str, Any]]] = \
        collections.defaultdict(list)
    for o in rec.obs_of(Q.ARC_BOX):
        box = E._corners_to_wh(E._page_box_of(o))
        if box is None:
            continue
        s = E._parse_subject(o["subject"])
        out[tuple(round(v, 2) for v in box)].append({
            "subject": o["subject"], "staff": s["staff"],
            "system": s["system"], "page": s["page"],
            "cls": str(o["value"]), "score": o.get("score"),
        })
    return dict(out)


def _rows_for(boxes: List[List[float]], rows) -> List[Dict[str, Any]]:
    out = []
    for b in boxes:
        out.extend(rows.get(tuple(round(float(v), 2) for v in b), ()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--max-gap", type=float, default=1.0)
    a = ap.parse_args()
    rows = arc_rows(a.record)
    r = stacks_run(a.record)
    close = [p for p in r["pairs"] if (p["gap_spaces"] or 99) <= a.max_gap]

    diff_staff = same_staff = unjoinable = 0
    same_class = 0
    same_length = 0
    for p in close:
        lo = _rows_for(p["lower_boxes"], rows)
        up = _rows_for(p["upper_boxes"], rows)
        if not lo or not up:
            unjoinable += 1
            continue
        ls = {(x["page"], x["system"], x["staff"]) for x in lo}
        us = {(x["page"], x["system"], x["staff"]) for x in up}
        if ls & us:
            same_staff += 1
        else:
            diff_staff += 1
        if {x["cls"] for x in lo} == {x["cls"] for x in up}:
            same_class += 1
        llen = sum(b[2] for b in p["lower_boxes"])
        ulen = sum(b[2] for b in p["upper_boxes"])
        if llen and ulen and 0.9 <= llen / ulen <= 1.111:
            same_length += 1

    n = len(close)
    print(f"candidate stacked pairs within {a.max_gap} staff space: {n}")
    print(f"  DETECTED ON DIFFERENT STAVES (one curve, twice): {diff_staff}")
    print(f"  detected on the SAME staff:                      {same_staff}")
    print(f"  could not be joined back to a row:               {unjoinable}")
    print(f"  SAME detector class on both arcs:                {same_class}")
    print(f"  spans within 10% of the same LENGTH:             {same_length}")
    print("\n⚠️ A tie drawn under a phrase slur is SHORTER than the slur and")
    print("   carries a different class. A pair that is the same class, the")
    print("   same length and detected on two different staves is ONE curve.")


if __name__ == "__main__":
    main()
