"""What S4 and S6 SAY, over the populations `reach.py` established.

⚠️ NEITHER WITNESS IS TRUTH. The detector's class is not truth and neither is
a geometric rule; every number below is an AGREEMENT RATE between two
readings of the same ink, and it is named as one. An agreement rate cannot
say which reading is right, and this document is the *low-res bitonal*
pessimistic end of the corpus.

⚠️ NOTHING HERE IS TUNED. S4's quantity `t` is unit-free by construction (the
fraction along the stem from the head end to the far end), so the question
asked is whether the two detector classes SEPARATE on it — and if they do
not, that is the result. `_SLUR_ARC_PAD_NOTEHEADS` is the recorded precedent:
a constant read off a smooth slope is fitted to a wish, so the sweep below is
printed whole and no row of it is promoted.

⚠️ S6 IS SCORED AS A DOSE-RESPONSE, NOT AT A CHOSEN GAP. If *the lower of two
stacked arcs is the tie* is a fact about engraving, agreement must be highest
where the two arcs are genuinely stacked — close together, near-total
x-overlap — and decay as the pair gets further apart. A single rate at one
threshold cannot tell a real rule from a threshold fitted to it.

Consumes `reach.py`'s `--out` JSON.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter


def _is_tie(cls) -> bool:
    return str(cls).lower().startswith("tie")


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
    """The gap between two populations, by this repo's own standard.

    `TIE_SAME_POSITION_MAX_SPACES` sits in a MEASURED empty interval (0.168
    against 0.435); the slur pad was REFUSED because the same distribution is
    a smooth slope with no gap anywhere. Reported so a reader can apply that
    standard instead of taking a rate on trust.
    """
    if not a or not b:
        return None
    lo, hi = (a, b) if statistics.median(a) < statistics.median(b) else (b, a)
    gap = min(hi) - max(lo)
    return {"lower_max": round(max(lo), 4), "upper_min": round(min(hi), 4),
            "gap": round(gap, 4), "empty": gap > 0}


def _s4_on_stem(r):
    return [e for e in r["s4"] if e["same_side"] and -0.05 <= e["t"] <= 1.05]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reach_json")
    args = ap.parse_args(argv)
    data = json.load(open(args.reach_json))
    rows = data["rows"]
    med = data["summary"]["confidence_median"]
    report = {"n_arcs": len(rows)}

    # ── the availability gradient, the way ARC_KIND.md reports it ───────────
    report["confidence_gradients"] = {}
    for name, avail in (("s4_on_stem", lambda r: bool(_s4_on_stem(r))),
                        ("s4_any_stemmed_head", lambda r: bool(r["s4"])),
                        ("grammar_two_heads", lambda r: r["flanked"] >= 2),
                        ("s6_candidate", lambda r: any(
                            c["y_gap"] > 0 and c["x_overlap_frac"] >= 0.5
                            for c in r["s6"]))):
        yes = [r["score"] for r in rows if avail(r) and r["score"] is not None]
        no = [r["score"] for r in rows
              if not avail(r) and r["score"] is not None]
        report["confidence_gradients"][name] = {
            "available_n": len(yes), "unavailable_n": len(no),
            "available_median_conf": round(statistics.median(yes), 4) if yes else None,
            "unavailable_median_conf": round(statistics.median(no), 4) if no else None}

    # ── S4 ──────────────────────────────────────────────────────────────────
    # ⚠️ TWO POPULATIONS, REPORTED APART. The WIDE one is every arc with a
    # stemmed flanked head — where `t` is a position and may be anywhere. The
    # NARROW one is Sean's own precondition: the endpoint is ON the stem.
    s4 = {}
    wide = [(r, statistics.median([e["t"] for e in r["s4"]]))
            for r in rows if r["s4"]]
    s4["wide_population"] = {
        "n": len(wide),
        "reading_tie": _dist([t for r, t in wide if _is_tie(r["cls"])]),
        "reading_slur": _dist([t for r, t in wide if not _is_tie(r["cls"])]),
        "widest_empty_interval": _empty_interval(
            [t for r, t in wide if _is_tie(r["cls"])],
            [t for r, t in wide if not _is_tie(r["cls"])])}

    narrow = [(r, statistics.median([e["t"] for e in _s4_on_stem(r)]))
              for r in rows if _s4_on_stem(r)]
    n_tie = [t for r, t in narrow if _is_tie(r["cls"])]
    n_slur = [t for r, t in narrow if not _is_tie(r["cls"])]
    s4["narrow_population_endpoint_on_the_stem"] = {
        "n": len(narrow),
        "reading_tie": _dist(n_tie), "reading_slur": _dist(n_slur),
        "widest_empty_interval": _empty_interval(n_tie, n_slur),
        "base_rate_slur": round(len(n_slur) / len(narrow), 4) if narrow else None}

    # ⚠️ S4 IS ONE-SIDED — *far edge ⇒ slur*, silent about the near end — so it
    # is scored at a SWEEP and no row is promoted. `lift` is agreement minus
    # the base rate: a rule that only reproduces the population's own mix
    # has lift 0 and has told us nothing.
    base = (len(n_slur) / len(narrow)) if narrow else 0.0
    s4["one_sided_sweep_on_the_narrow_population"] = []
    for thr in (0.25, 0.4, 0.5, 0.6, 0.75, 0.9):
        fires = [(r, t) for r, t in narrow if t >= thr]
        ns = sum(1 for r, _t in fires if not _is_tie(r["cls"]))
        s4["one_sided_sweep_on_the_narrow_population"].append({
            "t_at_least": thr, "fires": len(fires),
            "reading_says_slur": ns, "reading_says_tie": len(fires) - ns,
            "agreement": round(ns / len(fires), 4) if fires else None,
            "lift_over_base": round(ns / len(fires) - base, 4) if fires else None})
    # The mirror arm: does the NEAR half prefer ties, as S3 would imply?
    near = [(r, t) for r, t in narrow if t < 0.5]
    s4["near_half_t_below_0_5"] = {
        "fires": len(near),
        "reading_says_tie": sum(1 for r, _ in near if _is_tie(r["cls"])),
        "reading_says_slur": sum(1 for r, _ in near if not _is_tie(r["cls"]))}
    # ⚠️ SPLIT BY CONFIDENCE, never pooled.
    s4["by_confidence"] = {}
    for bname, keep in (("low_conf", lambda s: s < med),
                        ("high_conf", lambda s: s >= med)):
        sub = [(r, t) for r, t in narrow
               if r["score"] is not None and keep(r["score"])]
        s4["by_confidence"][bname] = {
            "n": len(sub),
            "reading_tie": _dist([t for r, t in sub if _is_tie(r["cls"])]),
            "reading_slur": _dist([t for r, t in sub if not _is_tie(r["cls"])])}
    report["s4"] = s4

    # ── S6 ──────────────────────────────────────────────────────────────────
    pairs, seen = [], set()
    for r in rows:
        for c in r["s6"]:
            key = tuple(sorted((r["subject"], c["other"])))
            if key in seen:
                continue
            seen.add(key)
            upper_cls = r["cls"] if c["arc_is_upper"] else c["other_cls"]
            lower_cls = c["other_cls"] if c["arc_is_upper"] else r["cls"]
            pairs.append(dict(y_gap=c["y_gap"], iou=c["iou"],
                              xfrac=c["x_overlap_frac"],
                              upper=upper_cls, lower=lower_cls,
                              same_owner=(r["owner"] == c["other_owner"]
                                          and r["owner"] is not None)))
    s6 = {"n_pairs_overlapping_in_x": len(pairs),
          "y_gap_all_pairs": _dist([p["y_gap"] for p in pairs]),
          "iou_all_pairs": _dist([p["iou"] for p in pairs])}

    stacks = [p for p in pairs if p["y_gap"] > 0 and p["xfrac"] >= 0.5]
    s6["n_stack_candidates"] = len(stacks)
    s6["stack_y_gap"] = _dist([p["y_gap"] for p in stacks])
    s6["stack_class_table"] = {
        f"upper={p_u}|lower={p_l}": n for (p_u, p_l), n in
        Counter((p["upper"], p["lower"]) for p in stacks).most_common()}

    # ⚠️ S6 IS ONLY ADDRESSED TO PAIRS WHOSE READINGS DISAGREE. A slur/slur
    # pair is a pair S6 has nothing to say about, and counting it as a miss
    # would score the rule against a population it does not address.
    def score(ps):
        d = [p for p in ps if _is_tie(p["upper"]) != _is_tie(p["lower"])]
        hit = sum(1 for p in d if _is_tie(p["lower"]))
        return {"disagreeing_pairs": len(d), "lower_is_the_tie": hit,
                "agreement": round(hit / len(d), 4) if d else None}

    s6["overall"] = score(stacks)
    # ⚠️ THE DOSE-RESPONSE. A staff space is 100 canonical px by construction
    # (`CANONICAL_STAFF_SPAN_PX / 4`), so these bands are stated in spaces and
    # are a DESCRIPTION of the distribution, not a threshold.
    s6["by_y_gap_staff_spaces"] = []
    bands = [(0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 99)]
    for lo, hi in bands:
        sub = [p for p in stacks if lo * 100 <= p["y_gap"] < hi * 100]
        s6["by_y_gap_staff_spaces"].append(
            {"gap_spaces": f"{lo}-{hi}", "n_pairs": len(sub), **score(sub)})
    # And by how completely the two arcs overlap in x — a real stack is drawn
    # over the same notes.
    s6["by_x_overlap"] = []
    for lo, hi in ((0.5, 0.7), (0.7, 0.9), (0.9, 1.01)):
        sub = [p for p in stacks if lo <= p["xfrac"] < hi]
        s6["by_x_overlap"].append(
            {"x_overlap": f"{lo}-{hi}", "n_pairs": len(sub), **score(sub)})
    # ⚠️ AND THE CONTROL THE OWNERSHIP WORK DEMANDS: a pair whose two arcs
    # `arc_owner` gives to DIFFERENT staves is not a stack at all — it is the
    # measure-cell padding reaching into the neighbour, the signature that
    # work already measured (every one of its 12 moves went to an ADJACENT
    # staff).
    s6["same_owner_only"] = score([p for p in stacks if p["same_owner"]])
    s6["different_owner"] = score([p for p in stacks if not p["same_owner"]])
    report["s6"] = s6

    json.dump(report, sys.stdout, indent=2)
    print()
    if not narrow and not stacks:
        print("DEAD: no population for either rule.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
