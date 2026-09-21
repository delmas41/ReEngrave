"""REACH, and the DISTRIBUTION, for the stem-attribution end rule.

⚠️ REACH BEFORE ACCURACY. The question this answers first is not *"is the end
rule right"* but *"is there anything for it to act on"*: how many noteheads
does the shipped overlap test attach to a stem at all, how many to MORE than
one, and -- the rule's whole population -- how many sit part-way ALONG a
stroke rather than at one of its ends.

⚠️ IT READS THE RECORD AND NOTHING ELSE. No weights, no cell cutting, no
re-gather: every number here is a property of committed observations, so it
can be reproduced on either publisher in minutes and cannot be contaminated by
detector jitter.

⚠️ THE FRACTION IS THE HEAD CENTRE ALONG THE STROKE'S Y-EXTENT, 0.0 at the
stroke's top end and 1.0 at its bottom. The engraving convention says a head
sits at ONE END, so the claim under test is that this distribution is
BIMODAL -- mass at both ends, a gap in the middle. If it is not, there is no
rule here and the honest result is a refusal.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from omr_ledger_extrapolation_shim import stream_array  # noqa: E402


def cell_of(subject: str) -> str:
    """`glyph/p/s/st/c/g` -> `cell/p/s/st/c`. Returns '' when there is none."""
    parts = subject.split("/")
    if parts[0] == "glyph" and len(parts) >= 6:
        return "cell/" + "/".join(parts[1:5])
    if parts[0] == "cell":
        return subject
    return ""


def overlap(a, b) -> bool:
    """The shipped `_boxes_overlap`, restated here ONLY because this probe
    must be runnable against a record with no import of the module under
    test.

    ⚠️ IT IS ASSERTED EQUAL TO THE SHIPPED ONE, not assumed
    (`test_probes.TestTheOverlapPredicateIsTheShippedOne`), including at the
    TOUCHING boundary, which the shipped predicate counts and a strict one
    does not -- one pair of this corpus turns on exactly that.
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax <= bx + bw and ax + aw >= bx
            and ay <= by + bh and ay + ah >= by)


def end_gap(head, stroke) -> float:
    """Distance from the head's CENTRE to the NEARER end of the stroke, in
    units of the head's OWN HEIGHT.

    ⚠️⚠️ THIS REPLACED `frac`, THE POSITION ALONG THE STROKE AS A FRACTION OF
    ITS LENGTH, WHICH THE CROPS REFUTED. `frac` conflates *a head part-way
    along a LONG stroke* (the fault) with *a head at the end of a SHORT stroke*
    (harmless): when a stroke is barely longer than the head, a head at its end
    scores mid-`frac` by arithmetic alone. Measured on 24 crops, every `MID`
    pair had a stroke of 1.39-2.20 head heights and every `END` pair 2.42-4.63,
    while this statistic read 0.45-0.64 and 0.14-0.32 -- i.e. all of them were
    at an end and `frac` had invented a population out of stroke length.

    ⚠️ SPELLED ONCE AND IMPORTED. Four probes need it, and four copies of a
    statistic this lane's whole conclusion rests on would be free to drift.
    A head at an end scores about 0.5, because a stem leaves the head at its
    top or bottom edge and the centre is half a height away.
    """
    hh = max(head[3], 1e-6)
    hcy = head[1] + head[3] / 2.0
    return min(abs(hcy - stroke[1]),
               abs(hcy - (stroke[1] + stroke[3]))) / hh


def collect(record):
    """cell -> stems, cell -> heads. One pass, streamed."""
    stems = defaultdict(list)
    heads = defaultdict(list)
    n_obs = 0
    for o in stream_array(record, "observations"):
        n_obs += 1
        q = o.get("quantity")
        if q == "stem":
            v = o.get("value")
            if isinstance(v, (list, tuple)) and len(v) >= 4:
                c = cell_of(o.get("subject", ""))
                if c:
                    stems[c].append((o["id"], tuple(float(x) for x in v[:4])))
        elif q == "glyph_box":
            if (o.get("detail") or {}).get("category") != "notehead":
                continue
            v = o.get("value")
            # `Q.GLYPH_BOX` is (smufl_name, x, y, w, h) -- the NAME comes first.
            if isinstance(v, (list, tuple)) and len(v) >= 5:
                c = cell_of(o.get("subject", ""))
                if c:
                    heads[c].append((o.get("subject", ""), o["id"],
                                     tuple(float(x) for x in v[1:5])))
    return stems, heads, n_obs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    stems, heads, n_obs = collect(args.record)
    n_heads = sum(len(v) for v in heads.values())
    n_stems = sum(len(v) for v in stems.values())

    counts = Counter()
    fracs = []
    per_head = {}
    for c, hs in heads.items():
        ss = stems.get(c, [])
        for subj, _hid, hb in hs:
            mine = [(sid, sb) for sid, sb in ss if overlap(sb, hb)]
            counts["heads"] += 1
            if not mine:
                counts["no_stem"] += 1
                per_head[subj] = {"n": 0, "fracs": []}
                continue
            counts["has_stem"] += 1
            if len(mine) > 1:
                counts["multi_stem"] += 1
            hcy = hb[1] + hb[3] / 2.0
            fs = []
            for _sid, sb in mine:
                sy, sh = sb[1], sb[3]
                f = (hcy - sy) / sh if sh > 0 else 0.5
                fs.append(f)
                fracs.append(f)
            per_head[subj] = {"n": len(mine), "fracs": fs}

    vals = sorted(fracs)

    def pct(p):
        return vals[min(len(vals) - 1, int(p * len(vals)))] if vals else None

    band = {f"{m:.2f}": sum(1 for f in vals if m < f < 1.0 - m)
            for m in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45)}

    out = {
        "label": args.label or Path(args.record).name,
        "record": args.record,
        "observations_streamed": n_obs,
        "cells_with_heads": len(heads),
        "noteheads": n_heads,
        "stem_rows": n_stems,
        "counts": dict(counts),
        "head_stem_pairs": len(vals),
        "frac_along_percentiles": {
            f"p{int(p * 100):02d}": pct(p)
            for p in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)},
        "frac_min": vals[0] if vals else None,
        "frac_max": vals[-1] if vals else None,
        "pairs_strictly_inside_band": band,
        "histogram_20": _hist(vals, 20),
    }
    print(json.dumps(out, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(
            {**out, "per_head": per_head}, indent=1))
    if not vals:
        print("DEAD: no (head, stem) pair on this record", file=sys.stderr)
        return 2
    return 0


def _hist(vals, nbins):
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return [[lo, hi, len(vals)]]
    out = [0] * nbins
    for v in vals:
        out[min(nbins - 1, int((v - lo) / (hi - lo) * nbins))] += 1
    return [[round(lo + (hi - lo) * i / nbins, 3),
             round(lo + (hi - lo) * (i + 1) / nbins, 3), out[i]]
            for i in range(nbins)]


if __name__ == "__main__":
    raise SystemExit(main())
