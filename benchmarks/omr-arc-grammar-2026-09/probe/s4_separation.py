"""S4: does WHERE ALONG THE STEM an arc attaches separate slurs from ties?

Sean: *"If it connects to the stem near the note it could be either but if it
is connected to the stems edge away from the note head then it is a slur."*

⚠️ **THE STANDARD IS AN EMPTY INTERVAL, NOT A TREND.** This repo ships a
constant only where the two populations leave a gap — the tie-pairing work
found same-position links at max 0.168 against step-apart links at min 0.435
and shipped on that; `_SLUR_ARC_PAD_NOTEHEADS` was REFUSED three hours earlier
because the same distribution on this document is *"a smooth slope with no
gap, so a pad read off it is fitted to a wish"*. If S4's populations do not
separate here, it does not ship here.

⚠️ **THE LABEL MUST NOT BE THE DETECTOR'S CLASS.** Scoring a proposed
tie/slur rule against the detector's own tie/slur call measures agreement with
the thing the rule exists to arbitrate, and the record already says that
comparison is a coin flip (grammar available on 81 of 199 arcs, agreeing 42 /
disagreeing 39). So the axis here is the ONE label that is PROVABLE without
the print and without the detector:

    the two flanked heads sit at DIFFERENT STAFF STEPS  -> CERTAINLY A SLUR
    the two flanked heads sit at ONE step               -> tie-CAPABLE

`record.Checkable`'s own rule — a tie's two ends are the same pitch — read as
a one-sided label. It is one-sided and stated as such: same-step does not
prove tie, so the test can show S4 SEPARATES or fails to, never that it is
accurate.

⚠️ The label is read from `Q.NOTEHEAD_STAFF_POSITION`, a STEP measured off the
staff lines, never from a spelled pitch — the key `_pitch_step` and the
pre-fill alignment both moved to, for the reason CLAUDE.md records.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09")
from reach import collect  # noqa: E402


def along_of(g: Dict[str, Any]) -> Optional[float]:
    """The arc's attachment position, 0 at the notehead end of the stem and 1
    at the far edge. An arc has two ends; Sean's rule fires if EITHER is at
    the far edge, so the group takes the larger. A group with no end on a
    direction-decided stem has NO value and is excluded, never defaulted."""
    vals = [e["along"] for e in g["ends"]
            if e["to"] == "stem" and e["along"] is not None]
    return max(vals) if vals else None


def label_of(g: Dict[str, Any]) -> Optional[str]:
    sp = g.get("step_pair")
    if not sp:
        return None
    return "certainly_slur" if sp[0] != sp[1] else "tie_capable"


def quant(xs: List[float]) -> Dict[str, float]:
    xs = sorted(xs)
    out = {}
    for q in (0, 5, 10, 25, 50, 75, 90, 95, 100):
        i = min(len(xs) - 1, int(round(q / 100.0 * (len(xs) - 1))))
        out[f"p{q}"] = round(xs[i], 3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = collect(a.record)
    gs = r["groups"]

    pops: Dict[str, List[float]] = collections.defaultdict(list)
    both = 0
    for g in gs:
        al = along_of(g)
        lb = label_of(g)
        if al is None:
            continue
        if lb is None:
            pops["no_step_label"].append(al)
            continue
        both += 1
        pops[lb].append(al)

    print(f"merged arc groups                          {len(gs)}")
    print(f"groups with an `along` (stem + direction)   "
          f"{sum(1 for g in gs if along_of(g) is not None)}")
    print(f"  ...AND a provable step label              {both}")
    if both == 0:
        print("\nS4 CANNOT BE SCORED: no group has both a stem attachment "
              "and a provable label.")
        return
    for k in ("certainly_slur", "tie_capable", "no_step_label"):
        xs = pops.get(k) or []
        if not xs:
            continue
        print(f"\n{k}  (n={len(xs)})  mean {statistics.mean(xs):.3f}")
        print("   ", quant(xs))

    # ⚠️ HOW MANY ENDS ARE ON THE STEM AT ALL. `along` is defined on [0, 1];
    # a value outside it means the arc's end does not lie between the stem's
    # two ends, so the "near the head / away from the head" question Sean's
    # rule asks does not arise. Reported as its own reach figure, because a
    # separation measured over values the quantity is not defined at would be
    # a separation of noise.
    allv = [v for k, vs in pops.items() for v in vs]
    inr = [v for v in allv if 0.0 <= v <= 1.0]
    print(f"\n`along` values in [0, 1] (the end is ON the stem): "
          f"{len(inr)} of {len(allv)}")

    cs = sorted(v for v in (pops.get("certainly_slur") or [])
                if 0.0 <= v <= 1.0)
    tc = sorted(v for v in (pops.get("tie_capable") or [])
                if 0.0 <= v <= 1.0)
    print(f"  ...labelled, in range: certainly_slur {len(cs)}, "
          f"tie_capable {len(tc)}")
    if cs and tc:
        print("\n--- SEPARATION ---")
        print(f"certainly_slur  min {cs[0]:.3f}  max {cs[-1]:.3f}")
        print(f"tie_capable     min {tc[0]:.3f}  max {tc[-1]:.3f}")
        gap = cs[0] - tc[-1]
        print(f"empty interval between the populations: "
              f"{gap:.3f}  ({'PRESENT' if gap > 0 else 'NONE — they overlap'})")
        # How well could ANY threshold do?  The best achievable split, stated
        # so a null result cannot be read as "the threshold was badly chosen".
        best = (0.0, None)
        for t in [i / 100.0 for i in range(0, 201)]:
            tp = sum(1 for x in cs if x >= t)
            fp = sum(1 for x in tc if x >= t)
            acc = (tp + (len(tc) - fp)) / (len(cs) + len(tc))
            if acc > best[0]:
                best = (acc, t)
        base = max(len(cs), len(tc)) / (len(cs) + len(tc))
        print(f"best achievable accuracy at ANY threshold: {best[0]:.3f} "
              f"at along >= {best[1]}")
        print(f"  ...against the majority-class baseline:  {base:.3f}")
    if a.out:
        json.dump({k: v for k, v in pops.items()}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
