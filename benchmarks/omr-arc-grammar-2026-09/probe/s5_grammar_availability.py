"""S5 on the STAGED path: how often can the recorded grammar speak, and does
it agree with the reading?

`adjudicate_arc_kind` lets the DETECTOR'S CLASS decide and RECORDS the position
grammar beside it in `detail["grammar"]`, deliberately — the tie->slur veto is
measured and refused, so turning the grammar into a gate would enable half a
refused flag by the back door. CLAUDE.md records the resulting figure from ONE
page: *available on 81 of 199 arcs, agreeing 42 / disagreeing 39 — a coin
flip*, with 28 of the 39 in the expensive tie->slur direction.

This reads the same field over FOUR pages, which is the first time that number
has been taken on more than one.

⚠️ It also asks the question behind the availability: `adjudicate_arc_kind`
finds its flanked heads by padding the arc's span by the ARC'S OWN HEIGHT and
taking head CENTRES inside it — the very test the arc-recovery work measured
missing by *half a notehead width, because an arc is drawn to a STEM and a
stem stands at the SIDE of its head*. `Q.STEM` is filed on the CELL in the
SAME canonical frame this decision reads, so the repair needs no frame
conversion. How much more often could the grammar speak? That is measured
here, at EXPORT stage, before any ADJUDICATE arm is spent.
"""
from __future__ import annotations

import argparse
import collections
import json
from typing import Any, Dict, List, Tuple

from tools.omr.staged import export as E
from tools.omr.staged.record import Q


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    a = ap.parse_args()
    rec = E.Record(json.load(open(a.record)))

    n = avail = agree = disagree = 0
    direction: "collections.Counter[str]" = collections.Counter()
    why: "collections.Counter[str]" = collections.Counter()
    for v in rec.verdicts_of(Q.ARC_KIND):
        if v.get("outcome") != "decided":
            why["not_decided_" + str(v.get("reason"))] += 1
            continue
        n += 1
        g = (v.get("detail") or {}).get("grammar") or {}
        if g.get("says") is None:
            why["fewer_than_two_flanked_heads"] += 1
            continue
        avail += 1
        if g.get("agrees_with_reading"):
            agree += 1
        else:
            disagree += 1
            direction[f"{v['value']} -> {g['says']}"] += 1
    print(f"decided arc_kind verdicts            {n}")
    print(f"  grammar AVAILABLE                  {avail}"
          f"  ({100.0 * avail / n:.1f}%)" if n else "")
    print(f"    agrees with the reading          {agree}")
    print(f"    disagrees                        {disagree}")
    for k, c in direction.most_common():
        print(f"      {k:20s} {c}")
    print("\nwhy the grammar could not speak:")
    for k, c in why.most_common():
        print(f"    {k:34s} {c}")

    # --- the stem question, measured in the SAME canonical frame ---
    stems: Dict[str, List[Tuple[float, ...]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.STEM):
        v = o["value"]
        if isinstance(v, (list, tuple)) and len(v) >= 4:
            stems[o["subject"]].append(tuple(float(x) for x in v[:4]))
    boxes: Dict[str, Dict[str, Any]] = {}
    for o in rec.obs_of(Q.GLYPH_BOX):
        boxes[o["subject"]] = o
    steps = {o["subject"]: (o.get("detail") or {}).get("rounded")
             for o in rec.obs_of(Q.NOTEHEAD_STAFF_POSITION)}
    by_cell: Dict[str, List[str]] = collections.defaultdict(list)
    for sub in steps:
        s = E._parse_subject(sub)
        by_cell[f"cell/{s['page']}/{s['system']}/{s['staff']}/"
                f"{s['cell'] or 0}"].append(sub)

    from tools.omr.staged.adjudicators.rhythm import _boxes_overlap
    gained = 0
    for o in rec.obs_of(Q.ARC_BOX):
        v = rec.verdict(Q.ARC_KIND, o["subject"])
        if not v or v.get("outcome") != "decided":
            continue
        g = (v.get("detail") or {}).get("grammar") or {}
        if g.get("says") is not None:
            continue
        d = o.get("detail") or {}
        pad = max(float(d.get("y1", 0)) - float(d.get("y0", 0)), 1.0)
        x0 = float(d.get("x0", 0)) - pad
        x1 = float(d.get("x1", 0)) + pad
        s = E._parse_subject(o["subject"])
        key = (f"cell/{s['page']}/{s['system']}/{s['staff']}/"
               f"{s['cell'] or 0}")
        pool = stems.get(key) or []
        hit = 0
        for sub in by_cell.get(key, ()):
            bo = boxes.get(sub)
            if bo is None:
                continue
            val = bo["value"]
            if not isinstance(val, (list, tuple)) or len(val) < 5:
                continue
            hb = (float(val[1]), float(val[2]), float(val[3]), float(val[4]))
            xs = [hb[0] + hb[2] / 2.0]
            for st in pool:
                if _boxes_overlap(st, hb):
                    xs.append(st[0] + st[2] / 2.0)
            if any(x0 <= x <= x1 for x in xs):
                hit += 1
        if hit >= 2:
            gained += 1
    print(f"\narcs the grammar could ALSO speak about if a head were "
          f"reachable AT ITS STEM: {gained}")
    print(f"  availability {avail} -> {avail + gained} of {n}")


if __name__ == "__main__":
    main()
