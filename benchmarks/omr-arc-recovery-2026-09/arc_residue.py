"""What the 550 REFUSED arcs actually are -- opened rather than counted.

`arc_partition.py` says 550 of 721 merged groups bind fewer than two heads and
that **331 of them have no gathered notehead under them at all**. That number
is compatible with two very different stories, and this project's own rule is
that a convincing aggregate is not evidence about its cause:

* the notes under a real printed arc were never DETECTED -- a reading ceiling;
* the arc is not a printed arc -- a duplicate of one already placed, or ink
  the detector called `tie` that is not one.

So this asks, per refused group: how much gathered ink is in its bar AT ALL,
and is there another placed arc at essentially the same page rectangle?

⚠️ THE DUPLICATE TEST IS THE ONE THE DEDUPE REPAIR DID NOT REACH.
`_place_arcs` sends every arc to the cell its OWNER names -- and where one
printed curve is detected on two staves, BOTH detections name the same owner,
so both are placed. That is exactly the shape `_place_notes` was repaired for
on 2026-09-11 (`A.is_relocated_copy`), one family over, and the repair's own
report records that `arc_owner` was left holding each contested arc twice.

⚠️ Overlap is measured in PAGE pixels on the record's own CORNER boxes, and
IoU is used rather than centre distance because two halves of a cross-barline
arc are genuinely different ink at nearby centres.
"""
from __future__ import annotations

import argparse
import collections
import json
from typing import Any, Dict, List, Tuple

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

#: Two arc boxes this alike are one piece of ink seen twice. Deliberately
#: HIGH: the question here is whether a duplicate population EXISTS, and a
#: loose threshold would answer it by manufacturing one. The distribution it
#: measures is printed, so the reader can see whether the number is on a cliff
#: or on a slope -- it is not used to decide anything.
IOU_SAME_INK = 0.7


def _iou(a: List[float], b: List[float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    iy = max(0.0, min(ay1, by1) - max(ay0, by0))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


def run(path: str) -> Dict[str, Any]:
    result = json.load(open(path))
    rec = E.Record(result)
    parts, *_ = E.build(rec)
    cells_with_heads: "collections.Counter[Tuple[Any, ...]]" = collections.Counter()
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None or not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue
        cells_with_heads[(s["page"], s["system"], s["staff"], s["cell"] or 0)] += 1

    # Every arc row, with its own page box and where it was PLACED.
    arcs: List[Dict[str, Any]] = []
    for o in rec.obs_of(Q.ARC_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None:
            continue
        kv = rec.verdict(Q.ARC_KIND, sub)
        box = E._page_box_of(o)
        if not kv or kv["outcome"] != "decided" or box is None:
            continue
        owner = rec.value(Q.ARC_OWNER, sub)
        home = owner if isinstance(owner, str) else E._staff_key(
            s["page"] or 0, s["system"] or 0, s["staff"] or 0)
        arcs.append({"subject": sub, "kind": str(kv["value"]), "box": box,
                     "home": home, "cell": s["cell"] or 0,
                     "from_staff": E._staff_key(s["page"] or 0, s["system"] or 0,
                                                s["staff"] or 0)})

    # Duplicates: two arcs PLACED IN ONE CELL whose page boxes are the same
    # ink. Grouped by (home, cell) because that is the pool the merge and the
    # pairing see -- two copies elsewhere on the page are not this fault.
    by_slot: Dict[Tuple[str, int], List[Dict[str, Any]]] = collections.defaultdict(list)
    for a in arcs:
        by_slot[(a["home"], a["cell"])].append(a)
    dup_pairs = 0
    dup_cross_staff = 0
    ious: List[float] = []
    dup_examples: List[Dict[str, Any]] = []
    for (home, cell), pool in by_slot.items():
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                v = _iou(pool[i]["box"], pool[j]["box"])
                if v > 0.1:
                    ious.append(round(v, 3))
                if v >= IOU_SAME_INK:
                    dup_pairs += 1
                    if pool[i]["from_staff"] != pool[j]["from_staff"]:
                        dup_cross_staff += 1
                    if len(dup_examples) < 8:
                        dup_examples.append({
                            "home": home, "cell": cell, "iou": round(v, 3),
                            "a": pool[i]["subject"], "b": pool[j]["subject"],
                            "a_kind": pool[i]["kind"], "b_kind": pool[j]["kind"],
                        })

    # Per refused group: is its bar EMPTY of gathered heads?
    groups: List[Dict[str, Any]] = []
    for part in parts:
        measures, per_measure_arcs, kinds, spacings, tops, breaks = \
            E._flatten_part(part)
        if not measures or not any(per_measure_arcs):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, per_measure_arcs, spacings, tops, breaks):
            seen = {kinds.get(id(b)) for _m, b in segments}
            covered = _legacy._noteheads_under(measures, segments)
            in_bars = 0
            where = []
            widths = []
            for m_idx, box in segments:
                r_, c_ = cells[m_idx]
                in_bars += cells_with_heads.get((r_.page, r_.system, r_.staff, c_), 0)
                where.append(f"p{r_.page}/s{r_.system}/st{r_.staff}/c{c_}")
                widths.append(round(box[2], 1))
            groups.append({
                "kind": "tie" if "tie" in seen else "slur",
                "bound": len(covered),
                "heads_gathered_in_its_bars": in_bars,
                "where": where, "widths": widths,
                "n_segments": len(segments),
            })
    return {"groups": groups, "n_arcs": len(arcs),
            "duplicate_pairs_in_one_cell": dup_pairs,
            "of_which_from_two_different_staves": dup_cross_staff,
            "overlap_iou_distribution": sorted(ious, reverse=True),
            "duplicate_examples": dup_examples}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = run(a.record)
    refused = [g for g in r["groups"] if g["bound"] < 2]
    empty = [g for g in refused if g["heads_gathered_in_its_bars"] == 0]
    print(f"arcs with a kind and a page box   {r['n_arcs']}")
    print(f"refused groups                    {len(refused)}")
    print(f"  in bars with ZERO gathered heads {len(empty)}")
    print(f"  in bars that DO hold heads       {len(refused) - len(empty)}")
    print(f"\nduplicate arc pairs in one cell (IoU >= {IOU_SAME_INK}): "
          f"{r['duplicate_pairs_in_one_cell']}")
    print(f"  of which detected on two different staves: "
          f"{r['of_which_from_two_different_staves']}")
    d = r["overlap_iou_distribution"]
    print(f"  overlapping pairs (IoU > 0.1): {len(d)}; "
          f"top {d[:10]}")
    for e in r["duplicate_examples"]:
        print(f"    {e['home']} c{e['cell']} IoU {e['iou']}  "
              f"{e['a']} ({e['a_kind']}) == {e['b']} ({e['b_kind']})")
    w = collections.Counter()
    for g in refused:
        w[min(g["widths"]) // 50 * 50] += 1
    print("\nrefused-arc widths (page px, 50px buckets):")
    for k in sorted(w):
        print(f"    {int(k):5d}+ {w[k]}")
    if a.out:
        json.dump(r, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
