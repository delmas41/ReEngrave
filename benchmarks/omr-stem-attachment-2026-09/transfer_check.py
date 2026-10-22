"""DOES 95.9% TRANSFER TO THE POPULATION THE CONVENTION IS FOR?

⚠️⚠️ THE CONTROL AND THE TARGET ARE NOT THE SAME POPULATION, AND THE
DIFFERENCE RUNS THE WRONG WAY. The convention's headline agreement (95.9%
Litolff, 98.2% Breitkopf) is measured on heads where `stem_direction` is
DECIDED -- which is to say, on heads whose stem ink was clean enough for the CV
rung to find a component in it. The heads it would be USED on are the ones
where that rung found nothing. **The control is the easy half and the target is
the hard half**, which is this repo's own *the bars are not an independent
umpire over a bad reading* arriving from a new direction: wherever the first
reader is worst, the validation set is thinnest.

TWO TRUTH-FREE TESTS, because no note in any stem arm has ever been checked
against the print:

1. **A run longer than a stem can be is not a stem.** `line_detection`'s
   `STEM_MAX_HEIGHT_LINES = 8.0` is IMPORTED, not restated, and its own
   comment says what a longer component is: *"That is a barline, and it is
   what the cap is for."* An arm over 8.0 staff spaces from the head's centre
   is therefore a self-refuting answer -- the convention has found a run, and
   the run cannot be a stem. On a plate this file's siblings measure as FUSING
   its ink, that is the expected failure.

2. **Stratify the control by arm length, then RE-WEIGHT it to the target's arm
   distribution.** If agreement falls with arm length, and the target has more
   long arms, the headline overstates what the convention would deliver.
   ⚠️ This assumes agreement-given-arm-length is the same in both populations.
   It is an ESTIMATE and is labelled one; it is not a measurement of accuracy
   on the target, which needs crops.

    python3 transfer_check.py --rows out/L-rows.json --label L
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

# ⚠️ IMPORTED. The bound is `line_detection`'s and it is measured there.
from tools.omr.line_detection import STEM_MAX_HEIGHT_LINES      # noqa: E402

#: `detect_stems(min_height_lines=2.0)` -- the shortest component that module
#: will call a stem. ⚠️ Read from its SIGNATURE rather than retyped, so a
#: change there is loud here.
MIN_COMPONENT = float(
    __import__("inspect").signature(
        __import__("tools.omr.line_detection", fromlist=["detect_stems"])
        .detect_stems).parameters["min_height_lines"].default)

#: Arm-length strata, in staff spaces. The last is open-ended and is the one
#: the cap already calls a barline.
BANDS = ((1.25, 2.5), (2.5, 4.0), (4.0, 6.0), (6.0, STEM_MAX_HEIGHT_LINES),
         (STEM_MAX_HEIGHT_LINES, 1e9))


def band_of(x: float) -> str:
    for lo, hi in BANDS:
        if lo <= x < hi:
            return (f">{lo:g}" if hi > 1e8 else f"{lo:g}-{hi:g}")
    return "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    rows = json.loads(Path(a.rows).read_text())["rows"]
    speaks = [r for r in rows if r["says"]]
    if not speaks:
        print("DEAD: the convention speaks for no head at all",
              file=sys.stderr)
        return 2
    for r in speaks:
        r["arm"] = max(r["R_up"], r["L_down"])
        r["band"] = band_of(r["arm"])

    ctrl = [r for r in speaks if r["reason"] == "DECIDED" and r["read"]]
    targ = [r for r in speaks if r["reason"] == "no_stem"]
    if not ctrl or not targ:
        print("DEAD: one of the two populations is empty", file=sys.stderr)
        return 2

    print(f"{a.label}\n")
    print("== 1. IS THE RUN EVEN A POSSIBLE STEM? "
          f"(line_detection.STEM_MAX_HEIGHT_LINES = {STEM_MAX_HEIGHT_LINES})")
    for name, pop in (("DECIDED  (the control)", ctrl),
                      ("no_stem  (the target)", targ)):
        over = sum(1 for r in pop if r["arm"] > STEM_MAX_HEIGHT_LINES)
        print(f"   {name:<24} n={len(pop):>5}  median {statistics.median(r['arm'] for r in pop):>5.2f}"
              f"  over {STEM_MAX_HEIGHT_LINES:g}: {over:>4} ({over/len(pop):>5.1%})")
    o_c = sum(1 for r in ctrl if r["arm"] > STEM_MAX_HEIGHT_LINES) / len(ctrl)
    o_t = sum(1 for r in targ if r["arm"] > STEM_MAX_HEIGHT_LINES) / len(targ)
    if o_c:
        print(f"   -> the target is {o_t / o_c:.1f}x more likely to answer "
              f"with a run that cannot be a stem")

    print("\n== 2. AGREEMENT BY ARM LENGTH, on the control ==")
    bands = [band_of(lo + 1e-9) for lo, _ in BANDS]
    hit: collections.Counter = collections.Counter()
    tot: collections.Counter = collections.Counter()
    for r in ctrl:
        tot[r["band"]] += 1
        if r["says"] == r["read"]:
            hit[r["band"]] += 1
    share_t = collections.Counter(r["band"] for r in targ)
    print(f"{'band (spaces)':<16}{'n':>7}{'agrees':>9}{'rate':>8}"
          f"{'target share':>14}")
    for b in bands:
        if not tot[b]:
            print(f"{b:<16}{0:>7}{'-':>9}{'-':>8}"
                  f"{share_t[b] / len(targ):>13.1%}")
            continue
        print(f"{b:<16}{tot[b]:>7}{hit[b]:>9}{hit[b]/tot[b]:>8.3f}"
              f"{share_t[b] / len(targ):>13.1%}")
    raw = sum(hit.values()) / sum(tot.values())
    print(f"{'ALL':<16}{sum(tot.values()):>7}{sum(hit.values()):>9}"
          f"{raw:>8.3f}")

    # Re-weight the control's per-band rates onto the target's band mix.
    num = den = 0.0
    missing = 0
    for b in bands:
        w = share_t[b]
        if not w:
            continue
        if not tot[b]:
            missing += w
            continue
        num += w * (hit[b] / tot[b])
        den += w
    print(f"\n== 3. RE-WEIGHTED ESTIMATE for the target population ==")
    print(f"   control, as measured                        {raw:.3f}")
    if den:
        print(f"   re-weighted onto the target's arm mix       {num/den:.3f}"
              f"   <- AN ESTIMATE, not a measurement")
    if missing:
        print(f"   ⚠️ {missing/1:.1%} of the target sits in a band the control "
              f"cannot speak for")
    print(f"\n⚠️ ASSUMES agreement-given-arm-length transfers between the two "
          f"populations. The honest statement remains that the convention has "
          f"NEVER been checked against the print.")

    # ── 4. would a PHYSICAL gate on the run length rescue it? ─────────────
    #
    # ⚠️ THE TWO EDGES ARE `line_detection`'s OWN AND ARE IMPORTED. A stem
    # component is between `min_height_lines` (2.0) and `STEM_MAX_HEIGHT_LINES`
    # (8.0) spaces tall, and an ARM is measured from the head's CENTRE, so it
    # is shorter than its component by roughly the half-head it starts inside.
    # That makes ~1.5 the derived floor for a 2.0-space stem, not 2.5.
    #
    # ⚠️⚠️ AND THE SWEEP IS RUN ON THE CONTROL, SO ITS OPTIMUM IS NOT
    # CLAIMABLE. A constant read off the population it is about to judge is a
    # constant fitted to it. The sweep is here to show whether the DERIVED
    # edge sits on a plateau or on a cliff -- nothing more.
    print(f"\n== 4. A PHYSICAL GATE, swept. The derived floor is ~1.5 "
          f"(a {MIN_COMPONENT} space component read from the head's centre).")
    print(f"{'floor':>7}{'ceiling':>9}{'ctrl n':>8}{'ctrl rate':>11}"
          f"{'target n':>10}{'est.':>8}")
    swept = []
    for floor in (1.25, 1.5, 1.75, 2.0, 2.5, 3.0):
        for ceil in (STEM_MAX_HEIGHT_LINES, 1e9):
            c = [r for r in ctrl if floor <= r["arm"] <= ceil]
            t = [r for r in targ if floor <= r["arm"] <= ceil]
            if not c or not t:
                continue
            # re-weight the gated control onto the gated target's arm mix
            ch: collections.Counter = collections.Counter()
            ct: collections.Counter = collections.Counter()
            for r in c:
                ct[r["band"]] += 1
                if r["says"] == r["read"]:
                    ch[r["band"]] += 1
            st = collections.Counter(r["band"] for r in t)
            n = d = 0.0
            for b, w in st.items():
                if ct[b]:
                    n += (w / len(t)) * (ch[b] / ct[b])
                    d += w / len(t)
            est = (n / d) if d else None
            rate = sum(ch.values()) / len(c)
            swept.append({"floor": floor,
                          "ceiling": None if ceil > 1e8 else ceil,
                          "control_n": len(c), "control_rate": round(rate, 4),
                          "target_n": len(t),
                          "estimate": round(est, 4) if est else None})
            print(f"{floor:>7.2f}{('none' if ceil > 1e8 else f'{ceil:g}'):>9}"
                  f"{len(c):>8}{rate:>11.3f}{len(t):>10}"
                  f"{(f'{est:.3f}' if est else '-'):>8}")
    print(f"\n⚠️ Compare against the SHIPPED tier on this quantity: beam-mate "
          f"UNANIMOUS decides at 0.984, and beam-mate MAJORITY was REFUSED at "
          f"0.938 for accuracy. That is the bar this convention has to clear.")

    if a.out:
        Path(a.out).write_text(json.dumps(
            {"label": a.label,
             "control_n": len(ctrl), "target_n": len(targ),
             "control_over_cap": o_c, "target_over_cap": o_t,
             "control_rate": round(raw, 4),
             "reweighted_estimate": round(num / den, 4) if den else None,
             "min_component_spaces": MIN_COMPONENT,
             "max_component_spaces": STEM_MAX_HEIGHT_LINES,
             "gate_sweep": swept,
             "by_band": {b: {"n": tot[b], "agrees": hit[b],
                             "target_share": round(share_t[b] / len(targ), 4)}
                         for b in bands}}, indent=1))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
