"""REACH of Sean's six tie-vs-slur rules, before any of them is built.

⚠️ REACH BEFORE ACCURACY. A rule whose precondition is never met on this
document cannot be scored here at all, and *that* is the finding -- the same
discipline `direction_arm.py` and `wedge_arm.py` already carry (print the
reach, exit non-zero at zero, never let a clean zero read as a clean result).

The unit is the MERGED ARC GROUP -- what `_pair_arcs` actually decides about,
after `_merge_arcs_across_barlines` has rejoined the halves a barline cut --
not the raw `Q.ARC_BOX` row, because a rule about "the notes this arc
connects" is a question about the whole curve.

⚠️ EVERY FIGURE HERE IS AN EXPORT-STAGE FIGURE. It replays a saved record, so
it is blind by construction to a GATHER or an ADJUDICATE change.

The rules, from `SEAN_ARC_RULES.md`:

  S1  connected to NOTEHEADS                 -> ambiguous
  S2  spans MORE THAN TWO notes              -> SLUR
  S3  at the stem NEAR the notehead          -> ambiguous
  S4  at the stem's edge AWAY from the head  -> SLUR
  S5  the connected notes differ in PITCH    -> SLUR
  S6  two arcs STACKED: lower / upper        -> TIE / SLUR
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09")
from arc_frames import cell_maps  # noqa: E402

#: x-overlap two arcs must share before they are a candidate STACK. A pair
#: sharing less than half of the shorter arc is two different curves that
#: happen to be near each other, not one drawn over the other.
STACK_MIN_X_OVERLAP = 0.5

#: IoU at or above which a "stack" is really the SAME curve detected twice --
#: the duplicate population the arc-recovery work measured (48 pairs in one
#: cell at IoU >= 0.7, 19 of them on two different staves). Two arcs a reader
#: sees stacked are separated in y and cannot overlap this much.
DUPLICATE_IOU = 0.7


def _steps_by_subject(rec) -> Dict[str, Any]:
    out = {}
    for o in rec.obs_of(Q.NOTEHEAD_STAFF_POSITION):
        r = (o.get("detail") or {}).get("rounded")
        if r is not None:
            out[o["subject"]] = r
    return out


def _stems_page(rec, maps) -> Dict[str, List[Tuple[float, float, float, float]]]:
    """`cell key -> [(x0, y0, x1, y1)]` in PAGE pixels, or absent."""
    out: Dict[str, List[Tuple[float, float, float, float]]] = \
        collections.defaultdict(list)
    for o in rec.obs_of(Q.STEM):
        v = o["value"]
        m = maps.get(o["subject"])
        if m is None or not isinstance(v, (list, tuple)) or len(v) < 4:
            continue
        ax, bx = m["x"]
        ay, by = m["y"]
        x0 = ax * float(v[0]) + bx
        x1 = ax * (float(v[0]) + float(v[2])) + bx
        y0 = ay * float(v[1]) + by
        y1 = ay * (float(v[1]) + float(v[3])) + by
        out[o["subject"]].append((x0, y0, x1, y1))
    return dict(out)


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def collect(path: str) -> Dict[str, Any]:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)
    maps, frame_report = cell_maps(rec)
    stems = _stems_page(rec, maps)
    steps = _steps_by_subject(rec)
    dirs: Dict[str, Any] = {}
    for v in rec.verdicts_of(Q.STEM_DIRECTION):
        if v.get("outcome") == "decided":
            dirs[v["subject"]] = v["value"]

    groups: List[Dict[str, Any]] = []
    for part in parts:
        measures, per_measure_arcs, kinds, spacings, tops, breaks = \
            E._flatten_part(part)
        if not measures or not any(per_measure_arcs):
            continue
        cells = E._part_cells_in_order(part)
        order = _legacy._event_order_of_noteheads(measures)
        x_probes = _stem_probes_for(rec, part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, per_measure_arcs, spacings, tops, breaks):
            seen = {kinds.get(id(b)) for _m, b in segments}
            kind = "tie" if "tie" in seen else "slur"
            covered = _legacy._noteheads_under(measures, segments,
                                               x_probes=x_probes)
            m0 = segments[0][0]
            run, _ci = cells[m0]
            sp = spacings[m0] or 0.0
            xs = [b[0] for _m, b in segments] + [b[0] + b[2] for _m, b in segments]
            ys = [b[1] for _m, b in segments] + [b[1] + b[3] for _m, b in segments]
            ev: Dict[int, set] = collections.defaultdict(set)
            for _m, _x, det in covered:
                vo = order.get(id(det))
                if vo is not None:
                    ev[vo[0]].add(vo[1])
            n_events = max((len(s) for s in ev.values()), default=0)
            heads = [det for _m, _x, det in covered]
            # flanked steps: the outermost covered heads, by x
            step_pair = None
            if len(covered) >= 2:
                sorted_c = sorted(covered, key=lambda t: t[1])
                sa = steps.get(sorted_c[0][2].get("glyph"))
                sb = steps.get(sorted_c[-1][2].get("glyph"))
                if sa is not None and sb is not None:
                    step_pair = (sa, sb)
            groups.append({
                "part": id(part),
                "staff": (run.page, run.system, run.staff),
                "kind": kind,
                "segments": [(m, list(b)) for m, b in segments],
                "x0": min(xs), "x1": max(xs),
                "y0": min(ys), "y1": max(ys),
                "spacing": sp,
                "bound_heads": len(covered),
                "head_ys": [d["bbox_page"][1] + d["bbox_page"][3] / 2.0
                            for _m, _x, d in covered
                            if d.get("bbox_page")],
                "bound_events": n_events,
                "step_pair": step_pair,
                "ends": _end_attachments(segments, measures, cells, stems,
                                         dirs, spacings),
                "where": f"p{run.page}/s{run.system}/st{run.staff}",
            })
    return {"groups": groups, "frames": frame_report,
            "stem_cells_with_page_boxes": len(stems),
            "stem_direction_decided": len(dirs)}


def _stem_probes_for(rec, part):
    from tools.omr.staged.export import _stem_boxes_by_cell, _stem_probes
    return _stem_probes(rec, part, _stem_boxes_by_cell(rec))


#: How near an arc's END must come to a stem's x before that stem is the one
#: it is drawn to. NOT a tuned constant -- it is the same "is this the stem of
#: THIS note" question `_stem_joined` answers by box overlap, expressed in the
#: staff's own unit because an arc end carries no box of its own. A wider
#: window lets the nearest stem anywhere in the bar stand in for the right
#: one, which is how `along` acquires values outside [0, 1].
STEM_END_WINDOW_SPACES = 1.0


def _end_attachments(segments, measures, cells, stems, dirs, spacings):
    """For each END of the merged arc: what it is drawn to, and where on it.

    Returns two dicts (left end, right end) carrying:
      `to`        "stem" | "head" | None -- whichever is nearer in x, and a
                  stem only within `STEM_END_WINDOW_SPACES`
      `dx_head`   page px from the end to the nearest head centre
      `dx_stem`   page px from the end to the nearest stem centre
      `along`     0.0 at the NOTEHEAD end of that stem, 1.0 at the far edge,
                  or None where the stem's DIRECTION was never decided

    ⚠️⚠️ AN ARC'S END IS A CORNER OF ITS BOX, NOT ITS MIDDLE. A curve arching
    UP has its apex at the box top and BOTH ENDS at the bottom; one arching
    down is the mirror. The first cut of this probe measured the box's
    vertical CENTRE and produced `along` values from -3.3 to +5.4 -- a
    quantity defined on [0, 1] running eight units wide, which is the tell
    that the number was not measuring what its name says. The side is READ
    from the arc's position against the head it is nearest, never assumed.

    ⚠️ `along` ABSTAINS without a direction. A stem's two ends are only "near
    the head" and "away from the head" once you know which way it points, and
    `Q.STEM_DIRECTION` abstains `no_stem` / `stems_disagree` on a large share
    of heads. Where it abstained S3/S4 cannot be asked, and the probe says so
    rather than picking an end.

    ⚠️ THE DIRECTION IS TAKEN FROM A HEAD THAT STEM ACTUALLY CARRIES, found by
    box overlap -- `_stem_joined`'s own relation -- never from whichever head
    happens to be nearest the arc. A direction is a fact about the stem and
    the heads ON it, which is `adjudicate_stem_direction`'s own rule.
    """
    out = []
    for which, (m_idx, box) in ((0, segments[0]), (1, segments[-1])):
        ax, ay, aw, ah = box
        ex = ax if which == 0 else ax + aw
        sp = spacings[m_idx] or 0.0
        run, cidx = cells[m_idx]
        key = f"cell/{run.page}/{run.system}/{run.staff}/{cidx}"
        pool = stems.get(key) or []
        heads_here = [d for d in measures[m_idx].get("detections", [])
                      if d.get("category") == "notehead"
                      and d.get("bbox_page") and len(d["bbox_page"]) == 4]

        dx_head, best_head = None, None
        for det in heads_here:
            bp = det["bbox_page"]
            d = abs(bp[0] + bp[2] / 2.0 - ex)
            if dx_head is None or d < dx_head:
                dx_head, best_head = d, det

        # WHICH CORNER is the arc's end: the one nearer the notes.
        ey = None
        if best_head is not None:
            hb = best_head["bbox_page"]
            head_yc = hb[1] + hb[3] / 2.0
            arc_yc = ay + ah / 2.0
            ey = (ay + ah) if arc_yc < head_yc else ay

        dx_stem, best_stem = None, None
        for st in pool:
            cx = (st[0] + st[2]) / 2.0
            d = abs(cx - ex)
            if dx_stem is None or d < dx_stem:
                dx_stem, best_stem = d, st
        in_window = (dx_stem is not None and sp > 0
                     and dx_stem <= STEM_END_WINDOW_SPACES * sp)

        to = None
        if in_window and dx_head is not None:
            to = "stem" if dx_stem < dx_head else "head"
        elif in_window:
            to = "stem"
        elif dx_head is not None:
            to = "head"

        along = None
        direction = None
        if in_window and best_stem is not None and ey is not None:
            sx0, sy0, sx1, sy1 = best_stem
            on_stem = [d for d in heads_here
                       if not (d["bbox_page"][0] > sx1
                               or d["bbox_page"][0] + d["bbox_page"][2] < sx0
                               or d["bbox_page"][1] > sy1
                               or d["bbox_page"][1] + d["bbox_page"][3] < sy0)]
            answers = {dirs.get(d.get("glyph")) for d in on_stem}
            answers.discard(None)
            if len(answers) == 1:
                direction = answers.pop()
            if direction in ("up", "down") and sy1 > sy0:
                head_end = sy1 if direction == "up" else sy0
                far_end = sy0 if direction == "up" else sy1
                along = (ey - head_end) / (far_end - head_end)
        out.append({"to": to, "dx_head": dx_head, "dx_stem": dx_stem,
                    "along": along, "direction": direction,
                    "stem_len": (best_stem[3] - best_stem[1])
                    if best_stem else None})
    return out


def _pct(n: int, d: int) -> str:
    return f"{n:5d}  ({100.0 * n / d:5.1f}%)" if d else f"{n:5d}"


def report(r: Dict[str, Any]) -> int:
    gs = r["groups"]
    n = len(gs)
    print(f"merged arc groups                     {n}")
    print(f"  the exporter WRITES (binds 2+ heads) {sum(1 for g in gs if g['bound_heads'] >= 2)}")
    print("\nframe control (canonical -> page, per cell, per axis):")
    for k, v in r["frames"].items():
        print(f"    {k:32s} {v}")
    print(f"    stem cells with a page map       {r['stem_cells_with_page_boxes']}")
    print(f"    stem directions DECIDED          {r['stem_direction_decided']}")

    print("\n=== REACH, per rule ===")
    ends = [e for g in gs for e in g["ends"]]
    to = collections.Counter(e["to"] for e in ends)
    print(f"\nS1 arc END drawn to a NOTEHEAD (nearer than any stem)")
    print(f"    of {len(ends)} ends: head {to['head']}  stem {to['stem']}  "
          f"neither {to[None]}")
    s1 = sum(1 for g in gs if all(e["to"] == "head" for e in g["ends"]))
    print(f"    groups with BOTH ends at a head:  {_pct(s1, n)}")

    s2 = sum(1 for g in gs if g["bound_events"] > 2)
    print(f"\nS2 spans MORE THAN TWO note events:   {_pct(s2, n)}")
    print("    (of the groups that bind 2+ heads at all: "
          f"{sum(1 for g in gs if g['bound_events'] > 2)}"
          f" of {sum(1 for g in gs if g['bound_heads'] >= 2)})")

    s34 = [e for e in ends if e["to"] == "stem" and e["along"] is not None]
    s34_nodir = [e for e in ends if e["to"] == "stem" and e["along"] is None]
    print(f"\nS3/S4 arc END at a STEM with a DECIDED direction: {len(s34)}")
    print(f"      at a stem, direction NOT decided -> ABSTAIN: {len(s34_nodir)}")
    s4g = sum(1 for g in gs
              if any(e["to"] == "stem" and e["along"] is not None
                     for e in g["ends"]))
    print(f"      groups S4 could speak about:      {_pct(s4g, n)}")

    s5 = sum(1 for g in gs if g["step_pair"] is not None)
    s5d = sum(1 for g in gs
              if g["step_pair"] and g["step_pair"][0] != g["step_pair"][1])
    print(f"\nS5 groups with two flanked STEPS read: {_pct(s5, n)}")
    print(f"    ...of which the steps DIFFER:        {_pct(s5d, n)}")

    stacks, dup = _stacks(gs)
    print(f"\nS6 candidate STACKS (x-overlap >= {STACK_MIN_X_OVERLAP}, "
          f"y disjoint):   {len(stacks)}")
    print(f"    same-staff pairs at IoU >= {DUPLICATE_IOU} "
          f"(DUPLICATES, not stacks): {dup}")
    if stacks:
        kinds = collections.Counter(
            (a["kind"], b["kind"]) for a, b in stacks)
        for k, v in kinds.most_common():
            print(f"      lower={k[0]:5s} upper={k[1]:5s}  {v}")
    return 0 if n else 1


def _stacks(gs) -> Tuple[List[Tuple[dict, dict]], int]:
    by_staff: Dict[Any, List[dict]] = collections.defaultdict(list)
    for g in gs:
        by_staff[g["staff"]].append(g)
    out: List[Tuple[dict, dict]] = []
    dup = 0
    for pool in by_staff.values():
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                a, b = pool[i], pool[j]
                ox = _overlap(a["x0"], a["x1"], b["x0"], b["x1"])
                shorter = min(a["x1"] - a["x0"], b["x1"] - b["x0"])
                if shorter <= 0 or ox / shorter < STACK_MIN_X_OVERLAP:
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
                out.append((lower, upper))
    return out, dup


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = collect(a.record)
    code = report(r)
    if a.out:
        json.dump(r, open(a.out, "w"), indent=1, default=str)
    sys.exit(code)


if __name__ == "__main__":
    main()
