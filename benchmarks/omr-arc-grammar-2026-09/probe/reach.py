"""REACH FIRST: how many arcs can S4 and S6 even SPEAK ABOUT?

Sean's rules S4 (*"connected to the stem's edge away from the notehead ⇒
SLUR"*) and S6 (*"two arcs stacked: the lower is a tie, the upper a slur"*)
are claims about ENGRAVING. Before either can be scored, this asks the prior
question this repo has been bitten by three times: **is the arbiter even
present?**

⚠️ THE RECORDED HAZARD IS EXACTLY THIS FAMILY. `ARC_KIND.md` measured the
position grammar available on 81 of 199 arcs, and the arcs it CANNOT speak
about are the WEAKER readings (median detector confidence 0.408 against
0.563). *Wherever the first reader is worst, the second is most often
absent.* So availability is reported **split by confidence**, never as one
number — a pooled rate averages two populations that behave differently.

⚠️ S4'S PRECONDITION IS NARROWER THAN "THERE IS A STEM", and getting that
wrong is the difference between a measurement and a story. Sean's rule is
about an arc **CONNECTED TO** a stem: *near the notehead ⇒ either; at the
edge away from the notehead ⇒ slur*. An arc drawn on the side of the head
AWAY from its stem touches no stem at all and S4 addresses it not at all —
so the population is arcs whose endpoint lands ON the stem, which is a
three-part test (the arc is on the stem's side of the head, its endpoint is
x-proximate to the stem, and its endpoint lies within the stem's span).
Reported in stages so a reader can see what each condition costs.

⚠️ THIS IS A REACH PROBE. It reports no agreement rate; `separate.py` does
that over what this writes. It exits NON-ZERO when a rule can speak about
nothing, because a dead instrument and a clean negative are the same number.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict

from tools.omr.staged import export as E
from tools.omr.staged.record import Kind, Q, Subject


def _cell_of(subject_key: str) -> str:
    return Subject.from_key(subject_key).at(Kind.CELL).to_key()


def _arc_rows(rec):
    """Every arc, with its canonical box, cell, class and score."""
    out = []
    for o in rec.obs_of(Q.ARC_BOX):
        d = o.get("detail") or {}
        try:
            box = (float(d["x0"]), float(d["y0"]),
                   float(d["x1"]), float(d["y1"]))
        except (KeyError, TypeError, ValueError):
            continue
        owner = rec.value(Q.ARC_OWNER, o["subject"])
        out.append(dict(subject=o["subject"], cell=_cell_of(o["subject"]),
                        cls=str(o["value"]), score=o.get("score"), box=box,
                        owner=owner))
    return out


def _heads_by_cell(rec):
    """Notehead boxes with their staff STEP, keyed by cell.

    ⚠️ STEPS, NEVER SPELLED PITCHES — the same input `adjudicate_arc_kind`
    takes, and for the same recorded reason (a cross-barline tie's far head
    does not restate its accidental).
    """
    step = {}
    for o in rec.obs_of(Q.NOTEHEAD_STAFF_POSITION):
        step[o["subject"]] = (o.get("detail") or {}).get("rounded")
    by_cell = defaultdict(list)
    for o in rec.obs_of(Q.GLYPH_BOX):
        if (o.get("detail") or {}).get("category") != "notehead":
            continue
        v = o["value"]
        if not isinstance(v, (list, tuple)) or len(v) < 5:
            continue
        x, y, w, h = float(v[1]), float(v[2]), float(v[3]), float(v[4])
        by_cell[_cell_of(o["subject"])].append(dict(
            subject=o["subject"], box=(x, y, w, h), w=w,
            xc=x + w / 2.0, yc=y + h / 2.0, step=step.get(o["subject"])))
    return by_cell


def _stems_by_cell(rec):
    by_cell = defaultdict(list)
    for o in rec.obs_of(Q.STEM):
        v = o["value"]
        if not isinstance(v, (list, tuple)) or len(v) < 4:
            continue
        by_cell[o["subject"]].append(tuple(float(t) for t in v[:4]))
    return by_cell


def _overlap(a, b) -> bool:
    """`rhythm._boxes_overlap`, transcribed — box overlap, NO tolerance.

    Measured rather than chosen: 819 heads take exactly one stem and where
    none overlaps the nearest is 94 px away but for three pairs at 1-2 px.
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax <= bx + bw and ax + aw >= bx
            and ay <= by + bh and ay + ah >= by)


def _flanked(arc_box, heads):
    """`adjudicate_arc_kind`'s own flanking rule, transcribed."""
    x0, y0, x1, y1 = arc_box
    pad = max(y1 - y0, 1.0)
    lo, hi = x0 - pad, x1 + pad
    return sorted([h for h in heads if lo <= h["xc"] <= hi],
                  key=lambda h: h["xc"])


def s4_endpoints(arc, heads, stems):
    """One record per (endpoint, stem) — the raw material S4 is scored on.

    ⚠️ AN ARC BOX DOES NOT SAY WHICH EDGE ITS ENDPOINTS ARE ON, and that has
    to be settled rather than assumed. A slur drawn OVER its notes is a `∩`
    whose endpoints sit at the bbox's LOWER edge; one drawn under is a `∪`
    whose endpoints sit at the UPPER edge. The side is read off the flanked
    heads — the arc's near edge is the bbox edge closer to their y-centres.

    ⚠️ `t` IS UNIT-FREE AND THEREFORE NOT A CONSTANT: the fraction along the
    stem from the HEAD end (0.0) to the FAR end (1.0). An endpoint with
    `0 <= t <= 1` is ON the stem; `t < 0` is on the head's far side, where
    Sean's rule is silent, and `t > 1` is past the stem's tip.

    ⚠️ `dx_widths` is in NOTEHEAD WIDTHS, the unit the arc work already uses
    (an arc's edge sits a median 0.52 notehead widths inside the outer head
    centre), so nothing here introduces a pixel constant.
    """
    if not heads:
        return []
    ax0, ay0, ax1, ay1 = arc["box"]
    head_yc = statistics.median(h["yc"] for h in heads)
    arc_yc = (ay0 + ay1) / 2.0
    above = arc_yc < head_yc
    near_edge = ay1 if above else ay0

    out = []
    for h, ex in ((heads[0], ax0), (heads[-1], ax1)):
        for sx, sy, sw, sh in [s for s in stems if _overlap(s, h["box"])]:
            sy1 = sy + sh
            head_end, far_end = ((sy, sy1)
                                 if abs(sy - h["yc"]) < abs(sy1 - h["yc"])
                                 else (sy1, sy))
            span = far_end - head_end
            if abs(span) < 1e-6:
                continue
            # Does the stem point the way the arc lies? `far_end < head_end`
            # in canonical (y-down) coordinates means the stem points UP.
            stem_up = far_end < head_end
            out.append(dict(
                t=(near_edge - head_end) / span,
                arc_above=above, stem_up=stem_up,
                # ⚠️ THE TEST SEAN'S WORDS ACTUALLY NAME. "Connected to the
                # stem" needs the arc and the stem on the SAME side of the
                # head; an arc on the other side touches no stem.
                same_side=(above == stem_up),
                dx_widths=abs(ex - (sx + sw / 2.0)) / max(h["w"], 1.0),
                head=h["subject"]))
    return out


def s6_view(arc, siblings):
    """Is there a SECOND arc stacked over or under this one?

    ⚠️ A STACK IS NOT A DUPLICATE, and this document is already recorded as
    full of the second: `_place_arcs` has no dedupe and 48 pairs sit in one
    cell at IoU >= 0.7, several disagreeing about their own kind. So a
    candidate pair must OVERLAP IN X and be DISJOINT IN Y — two curves at the
    same height are one curve detected twice, whatever their IoU.

    The pair's own IoU, x-overlap fraction and y-gap travel with it so the
    duplicate population can be separated downstream by MEASUREMENT rather
    than assumed away here with a threshold.
    """
    ax0, ay0, ax1, ay1 = arc["box"]
    out = []
    for other in siblings:
        if other["subject"] == arc["subject"]:
            continue
        bx0, by0, bx1, by1 = other["box"]
        ox = min(ax1, bx1) - max(ax0, bx0)
        if ox <= 0:
            continue
        frac = ox / max(1.0, min(ax1 - ax0, bx1 - bx0))
        oy = min(ay1, by1) - max(ay0, by0)
        inter = max(0.0, ox) * max(0.0, oy)
        union = ((ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter)
        out.append(dict(other=other["subject"], other_cls=other["cls"],
                        other_score=other["score"],
                        other_owner=other["owner"],
                        x_overlap_frac=frac, y_gap=-oy,
                        iou=inter / union if union > 0 else 0.0,
                        arc_is_upper=(ay0 + ay1) < (by0 + by1)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record")
    ap.add_argument("--out")
    args = ap.parse_args(argv)

    rec = E.Record(json.load(open(args.record)))
    arcs = _arc_rows(rec)
    heads_by_cell = _heads_by_cell(rec)
    stems_by_cell = _stems_by_cell(rec)

    by_cell = defaultdict(list)
    for a in arcs:
        by_cell[a["cell"]].append(a)

    rows = []
    for a in arcs:
        heads = _flanked(a["box"], heads_by_cell.get(a["cell"], []))
        stems = stems_by_cell.get(a["cell"], [])
        rows.append(dict(
            subject=a["subject"], cell=a["cell"], cls=a["cls"],
            score=a["score"], box=list(a["box"]), owner=a["owner"],
            flanked=len(heads),
            first_step=heads[0]["step"] if heads else None,
            last_step=heads[-1]["step"] if heads else None,
            cell_stems=len(stems),
            s4=s4_endpoints(a, heads, stems),
            s6=s6_view(a, by_cell[a["cell"]])))

    scores = [r["score"] for r in rows if r["score"] is not None]
    med = statistics.median(scores) if scores else None

    def s4_on_stem(r):
        """The arcs S4 can speak about: an endpoint ON a stem, same side."""
        return [e for e in r["s4"]
                if e["same_side"] and -0.05 <= e["t"] <= 1.05]

    stages = {
        "arcs_total": len(rows),
        "with_any_flanked_head": sum(1 for r in rows if r["flanked"] >= 1),
        "grammar_available_two_heads": sum(1 for r in rows if r["flanked"] >= 2),
        "with_a_stemmed_flanked_head": sum(1 for r in rows if r["s4"]),
        "arc_on_the_stems_side": sum(
            1 for r in rows if any(e["same_side"] for e in r["s4"])),
        "endpoint_lands_ON_the_stem": sum(1 for r in rows if s4_on_stem(r)),
    }

    def band(r):
        if r["score"] is None or med is None:
            return "unknown"
        return "high_conf" if r["score"] >= med else "low_conf"

    by_conf = {}
    for name in ("low_conf", "high_conf", "unknown"):
        sub = [r for r in rows if band(r) == name]
        if not sub:
            continue
        stack = [r for r in sub
                 if any(c["y_gap"] > 0 and c["x_overlap_frac"] >= 0.5
                        for c in r["s6"])]
        by_conf[name] = {
            "n": len(sub),
            "median_score": round(statistics.median(
                [r["score"] for r in sub if r["score"] is not None]), 4),
            "grammar_available": sum(1 for r in sub if r["flanked"] >= 2),
            "s4_available": sum(1 for r in sub if s4_on_stem(r)),
            "s4_rate": round(sum(1 for r in sub if s4_on_stem(r)) / len(sub), 4),
            "s6_candidate": len(stack),
            "s6_rate": round(len(stack) / len(sub), 4),
        }

    tot4 = stages["endpoint_lands_ON_the_stem"]
    tot6 = sum(1 for r in rows
               if any(c["y_gap"] > 0 and c["x_overlap_frac"] >= 0.5
                      for c in r["s6"]))
    summary = {"n_arcs": len(rows), "confidence_median": med,
               "reach_stages": stages, "by_confidence": by_conf,
               "s4_available_total": tot4, "s6_candidate_total": tot6}

    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"summary": summary, "rows": rows}, fh)
    print(json.dumps(summary, indent=2))

    # ⚠️ A DEAD INSTRUMENT MUST NOT READ AS A CLEAN RESULT.
    if tot4 == 0 and tot6 == 0:
        print("DEAD: neither rule can speak about a single arc on this "
              "record.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
