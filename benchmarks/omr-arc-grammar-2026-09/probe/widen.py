"""S4 and S6 BROADENED — Sean, 2026-09-15: the convention is not the operationalisation.

The narrow test (`reach.py` + `separate.py`, same directory) scored S4 only
where the arc's endpoint lands ON stem ink — 143 of 779 arcs — and refuted it
there. Sean's objection is that this measures our reading, not his engraving:
*"connected to the stem's edge away from the notehead"* is a claim about WHERE
THE ARC ENDS, and **a scan breaks ink constantly**, so demanding pixel contact
is our limitation. Three widenings, cheapest first:

  1. **SIDE, not contact.** A tie is drawn on the side of the notehead AWAY
     from its stem — it hugs the head — while a slur over stemmed notes runs
     stem-tip to stem-tip (the arc work measured its edge a median 0.52
     notehead widths inside the outer head centre). So which SIDE the arc lies
     on is a cleaner, binary reading of Sean's sentence than distance along.
     ⚠️ This was already computed in `reach.py` and used only as a FILTER on
     the way to the narrow test. It has never been scored.
  2. **DROP THE CONTACT REQUIREMENT.** `t_axis` projects the arc's near edge
     onto the axis from the NOTEHEAD CENTRE (0.0) to the STEM TIP (1.0),
     whether or not the endpoint touches stem ink. Negative is the head's far
     side, so SIDE is just `sign(t_axis)` — the two widenings are one
     quantity, which is why they are computed together rather than as two
     rules that could drift.
  3. **THE ABSTAIN POPULATION IS COUNTED**, not dropped, so reach stays
     honest.

⚠️⚠️ **S4 IS ONE-SIDED BY SEAN'S OWN CONSTRUCTION AND IS SCORED THAT WAY.**
Near the head is S3, which he states is AMBIGUOUS, so the rule is *far end ⇒
SLUR, near end ⇒ ABSTAIN* — never a two-sided classifier. The narrow pass
reported "only the direction survives", which is a two-sided reading of a
one-sided rule.

⚠️ **AN ARC HAS TWO ENDS AND "CONNECTED TO A STEM'S FAR EDGE" IS EXISTENTIAL.**
Both aggregations are scored and neither is chosen here: `max` (either end
reaches the tip — the natural reading) and `median` (what the narrow pass
used). Picking one silently would be the modelling choice doing the work.

⚠️ **NO CONSTANT IS TUNED.** `t_axis` is unit-free; every threshold below is a
SWEEP printed whole, and the empty-interval test is reported so this repo's own
standard can be applied (`_SLUR_ARC_PAD_NOTEHEADS` was refused for sitting on a
smooth slope).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[2]))

# ⚠️ THE FLANKING RULE IS IMPORTED FROM `reach.py`, never restated — it is a
# transcription of `adjudicate_arc_kind`'s own rule and a third spelling is how
# the three drift.
_spec = importlib.util.spec_from_file_location("_reach", _HERE / "reach.py")
_reach = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reach)

from tools.omr.staged import export as E                        # noqa: E402
from tools.omr.staged.record import Q                           # noqa: E402,F401


def _is_tie(cls) -> bool:
    return str(cls).lower().startswith("tie")


def _binom_tail(k: int, n: int, p: float = 0.5) -> float:
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
               for i in range(k, n + 1))


def _q(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))], 4)


def _dist(xs):
    if not xs:
        return None
    return {"n": len(xs), "min": round(min(xs), 4), "p10": _q(xs, 0.10),
            "p25": _q(xs, 0.25), "median": _q(xs, 0.50), "p75": _q(xs, 0.75),
            "p90": _q(xs, 0.90), "max": round(max(xs), 4)}


def _empty_interval(a, b):
    if not a or not b:
        return None
    lo, hi = (a, b) if statistics.median(a) < statistics.median(b) else (b, a)
    gap = min(hi) - max(lo)
    return {"lower_max": round(max(lo), 4), "upper_min": round(min(hi), 4),
            "gap": round(gap, 4), "empty": gap > 0}


def s4_axis(arc_box, heads, stems):
    """`t_axis` per endpoint: NOTEHEAD CENTRE (0.0) → STEM TIP (1.0).

    ⚠️ NO CONTACT REQUIREMENT. The stem still has to be THIS head's — that
    attachment is `_stem_joined`'s measured box overlap and stays — but the
    ARC's endpoint may sit anywhere along or past the axis, which is the
    widening. Negative means the head's far side, where a tie is drawn.
    """
    if not heads:
        return []
    ax0, ay0, ax1, ay1 = arc_box
    head_yc = statistics.median(h["yc"] for h in heads)
    above = (ay0 + ay1) / 2.0 < head_yc
    near_edge = ay1 if above else ay0

    out = []
    for h, ex in ((heads[0], ax0), (heads[-1], ax1)):
        h_yc = h["yc"]
        for sx, sy, sw, sh in [s for s in stems
                               if _reach._overlap(s, h["box"])]:
            sy1 = sy + sh
            tip = sy if abs(sy - h_yc) > abs(sy1 - h_yc) else sy1
            span = tip - h_yc
            if abs(span) < 1e-6:
                continue
            out.append({"t_axis": (near_edge - h_yc) / span,
                        "stem_up": bool(tip < h_yc),
                        "arc_above": bool(above)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    rec = E.Record(json.load(open(a.record)))
    arcs = _reach._arc_rows(rec)
    heads_by_cell = _reach._heads_by_cell(rec)
    stems_by_cell = _reach._stems_by_cell(rec)

    # ⚠️⚠️ PAIRING BY VOICE WAS SCOPED AND IS NOT AVAILABLE, and the reason
    # is a number rather than a story: an ARC has no voice on the record.
    # `Q.VOICES` partitions a cell's EVENTS, so an arc's voice would have to
    # be derived from the noteheads it binds — and only 345 of 779 arcs bind
    # two. A voice-keyed pairing would therefore REACH LESS than the geometry
    # it was meant to widen, which is the opposite of a relaxation.

    by_cell = defaultdict(list)
    for arc in arcs:
        by_cell[arc["cell"]].append(arc)

    rows = []
    for arc in arcs:
        heads = _reach._flanked(arc["box"], heads_by_cell.get(arc["cell"], []))
        stems = stems_by_cell.get(arc["cell"], [])
        eps = s4_axis(arc["box"], heads, stems)
        rows.append({
            "subject": arc["subject"], "cell": arc["cell"], "cls": arc["cls"],
            "score": arc["score"], "box": list(arc["box"]),
            "owner": arc["owner"], "flanked": len(heads),
            "first_step": heads[0]["step"] if heads else None,
            "last_step": heads[-1]["step"] if heads else None,
            "eps": eps,
        })

    report = {"n_arcs": len(rows)}
    med = statistics.median([r["score"] for r in rows
                             if r["score"] is not None])

    # ── REACH, restated for the widened rule ────────────────────────────────
    with_axis = [r for r in rows if r["eps"]]
    # ⚠️ THE NARROW FIGURE IS NOT RECOMPUTED HERE. It belongs to `reach.py`,
    # and a second computation of one number is how two numbers for one thing
    # appear in two write-ups. This reports only what the WIDENING reaches.
    report["reach"] = {
        "arcs_total": len(rows),
        "S4_NARROW_endpoint_on_stem_ink": "see probe/reach.py: 143 of 779",
        "S4_WIDE_any_stemmed_flanked_head": len(with_axis),
        "S4_abstains_no_stemmed_flanked_head": len(rows) - len(with_axis),
    }

    for agg_name, agg in (("max", max), ("median", statistics.median)):
        pop = [(r, agg([e["t_axis"] for e in r["eps"]])) for r in with_axis]
        ties = [t for r, t in pop if _is_tie(r["cls"])]
        slurs = [t for r, t in pop if not _is_tie(r["cls"])]
        base = len(slurs) / len(pop) if pop else 0.0

        blk = {
            "n": len(pop), "base_rate_slur": round(base, 4),
            "reading_tie": _dist(ties), "reading_slur": _dist(slurs),
            "widest_empty_interval": _empty_interval(ties, slurs),
        }

        # ── WIDENING 1: SIDE ALONE, the binary reading ───────────────────────
        # ⚠️ SIDE IS `sign(t_axis)`, so this is the same quantity thresholded
        # at zero — reported separately because it is the rule Sean's sentence
        # most directly names and it needs no number at all.
        stem_side = [(r, t) for r, t in pop if t > 0]
        head_side = [(r, t) for r, t in pop if t <= 0]
        k = sum(1 for r, _ in stem_side if not _is_tie(r["cls"]))
        blk["SIDE"] = {
            "arc_on_the_STEM_side": len(stem_side),
            "...reads_slur": k,
            "...slur_share": round(k / len(stem_side), 4) if stem_side else None,
            "arc_on_the_HEAD_side": len(head_side),
            "...reads_tie": sum(1 for r, _ in head_side if _is_tie(r["cls"])),
            "...tie_share": round(
                sum(1 for r, _ in head_side if _is_tie(r["cls"]))
                / len(head_side), 4) if head_side else None,
            "lift_of_stem_side_over_base": round(
                k / len(stem_side) - base, 4) if stem_side else None,
            "p_binomial_stem_side": round(
                _binom_tail(k, len(stem_side), base), 5) if stem_side else None,
        }

        # ── WIDENING 2: the ONE-SIDED sweep on the widened population ────────
        # ⚠️ FAR END ⇒ SLUR, NEAR END ⇒ ABSTAIN. Never a two-sided classifier:
        # near the head is S3, which Sean states is AMBIGUOUS.
        blk["one_sided_sweep_ABSTAINING"] = []
        for thr in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
            fires = [(r, t) for r, t in pop if t >= thr]
            ns = sum(1 for r, _ in fires if not _is_tie(r["cls"]))
            blk["one_sided_sweep_ABSTAINING"].append({
                "t_axis_at_least": thr, "fires": len(fires),
                "abstains": len(rows) - len(fires),
                "reading_says_slur": ns,
                "reading_says_tie": len(fires) - ns,
                "agreement": round(ns / len(fires), 4) if fires else None,
                "lift_over_base": round(ns / len(fires) - base, 4) if fires else None,
                "p_binomial": round(_binom_tail(ns, len(fires), base), 5)
                if fires else None})

        # ⚠️⚠️ SPLIT BY CONFIDENCE, AND THE SWEEP TOO — NOT ONLY `SIDE`.
        # The detector's own class MIX differs enormously between the bands on
        # this document (base slur rate 0.25 low against 0.82 high), so a
        # POOLED lift can be pure Simpson: if far-`t_axis` arcs are mostly
        # high-confidence arcs and high-confidence arcs are mostly slurs, a
        # rule that knows nothing at all still shows lift. The within-band
        # sweep is the arm that cannot be fooled that way, and it is the one
        # to read.
        blk["by_confidence"] = {}
        for bn, keep in (("low_conf", lambda s: s < med),
                         ("high_conf", lambda s: s >= med)):
            sub = [(r, t) for r, t in pop
                   if r["score"] is not None and keep(r["score"])]
            ss = [(r, t) for r, t in sub if t > 0]
            kk = sum(1 for r, _ in ss if not _is_tie(r["cls"]))
            bb = (sum(1 for r, _ in sub if not _is_tie(r["cls"])) / len(sub)
                  if sub else 0.0)
            sweep = []
            for thr in (0.0, 0.5, 1.0, 1.5, 2.0):
                f = [(r, t) for r, t in sub if t >= thr]
                ns = sum(1 for r, _ in f if not _is_tie(r["cls"]))
                sweep.append({
                    "t_axis_at_least": thr, "fires": len(f),
                    "agreement": round(ns / len(f), 4) if f else None,
                    "lift_over_band_base": round(ns / len(f) - bb, 4)
                    if f else None,
                    "p_binomial": round(_binom_tail(ns, len(f), bb), 5)
                    if f else None})
            blk["by_confidence"][bn] = {
                "n": len(sub), "base_rate_slur": round(bb, 4),
                "stem_side_n": len(ss),
                "stem_side_slur_share": round(kk / len(ss), 4) if ss else None,
                "SIDE_lift": round(kk / len(ss) - bb, 4) if ss else None,
                "sweep_within_band": sweep}
        report[f"S4_WIDE_agg_{agg_name}"] = blk

    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"report": report, "rows": rows}, fh)
    json.dump(report, sys.stdout, indent=2)
    print()
    if not with_axis:
        print("DEAD: no arc has a stemmed flanked head.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
