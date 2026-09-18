"""ISSUES 1 AND 2, RE-SCORED OVER A DENOMINATOR THAT IS NOT CONTAMINATED.

Sean picked this job because *"I feel like the previous issues (1 and 2) will
be affected by this."* This is that answer, and both halves of it are
arithmetic over figures the lanes committed -- nothing is re-adjudicated and
no reader is re-run.

⚠️ NEITHER ANSWER IS THE ONE THE BRIEF EXPECTED, and both are reported the way
they came out:

  * ISSUE 1 -- the beam-mate tier. Its 16-0 loss is over the 16 heads the
    PRINT SETTLED, and **not one of those 16 is under the width floor**. The
    contamination in that population (3 of 26) sits entirely in the rows the
    print already declined or already called `not_a_notehead`. **The 16-0
    stands, unchanged, and the width test neither rescues nor worsens it.**

  * ISSUE 2 -- `OMR_STEM_STROKE`. The cleaning is real and it is LARGE on
    Breitkopf (+21 points). But the boxes it removes were **never in the
    bucket the stroke reader works on**: `too WIDE` is 0.84% / 2.53% thin,
    while `too TALL` is 96.4% / 40.4% thin. So the raw rate was DILUTED by a
    population the reader never touches, which is a different claim from
    "the reader was reading barlines" -- it never was.

⚠️ `stroke_arm.py` ALREADY COMPUTED THIS and named it `plausible_heads` /
`thin_boxes`. This reproduces 44 / 576 and 749 / 953 from the record. ⚠️ It is
a reproduction of the COMPUTATION, not an independent ruler: that lane divides
the page box by the mean of the four printed staff-line gaps and this one by
`Q.STAFF_SPACING`, and those turn out to be the SAME NUMBER to the float
(max |diff| 0.0 over 5,684 boxes) -- so the agreement confirms the threshold,
the box convention and the population, and says nothing about the ruler.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
BENCH = HERE.parent
STROKE = BENCH.parent / "omr-stem-stroke-2026-09" / "out"
from floor import FLOOR  # ⚠️ ONE place; see probe/floor.py
# the variant the stroke lane reports as the shipped one; `+legal` is marked
# CIRCULAR in its own output and is deliberately not used here.
VARIANT = "side+end"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    out = {"floor": FLOOR, "variant": VARIANT}
    for pub in ("litolff", "breitkopf"):
        rows = json.loads(
            (BENCH / "out" / f"{pub}-widths.json").read_text())["rows"]
        sc = json.loads((BENCH / "out" / f"score-{pub}.json").read_text())
        arm = json.loads((STROKE / f"{pub}-arm.json").read_text())

        no_stem = [r for r in rows if r["reason"] == "no_stem"]
        thin = sum(1 for r in no_stem if r["w_page"] < FLOOR)
        plaus = len(no_stem) - thin

        rec = arm["restricted"][VARIANT]["recovered"]
        out[pub] = {
            "reproduced_from_the_record": {
                "no_stem": len(no_stem),
                "thin_boxes": thin, "thin_boxes_published": arm["thin_boxes"],
                "plausible_heads": plaus,
                "plausible_heads_published": arm["plausible_heads"],
                "agree": (thin == arm["thin_boxes"]
                          and plaus == arm["plausible_heads"]),
            },
            "issue2_reach": {
                "recovered": rec,
                "over_raw_no_stem": round(rec / len(no_stem), 4),
                "over_plausible": round(rec / plaus, 4),
                "points_gained_by_cleaning": round(
                    100 * (rec / plaus - rec / len(no_stem)), 1),
            },
            # ⚠️ AND THE POINT THAT MATTERS: the cleaning does not touch the
            # bucket the reader reads.
            "issue2_where_the_thin_boxes_live": {
                k: {"n": v["n"], "under_floor": v["under_floor"],
                    "share": v["share_under_floor"]}
                for k, v in sc["populations"].items()
                if k.startswith("no_stem / ")
            },
            "issue2_quality_bar": {
                "agreement_rate_over_plausible":
                    arm["restricted"][VARIANT]["agreement_rate"],
                "reference_bar_same_restriction":
                    arm["reference_restricted_rate"],
            },
        }

    # ---- ISSUE 1 ----
    con = json.loads((BENCH / "out" / "contamination.json").read_text())
    i1 = con["issue1_standoff"]
    out["issue1"] = {
        "standoff_heads": i1["n"],
        "print_verdicts": i1["verdicts"],
        "under_floor_overall": i1["under_floor"],
        "settled_by_the_print": i1["settled_n"],
        "settled_and_under_floor": i1["settled_under_floor"],
        "attachment_wins_among_settled": i1["attachment_wins_among_settled"],
        "beam_mate_wins_among_settled": i1["beam_mate_wins_among_settled"],
        "verdict": ("the 16-0 is UNCHANGED by the width test: 0 of the 16 "
                    "settled heads is under the floor"),
    }

    bad = [p for p in ("litolff", "breitkopf")
           if not out[p]["reproduced_from_the_record"]["agree"]]
    Path(a.json).write_text(json.dumps(out, indent=1))

    for pub in ("litolff", "breitkopf"):
        d = out[pub]
        r = d["reproduced_from_the_record"]
        print(f"== {pub}")
        print(f"   {'ok  ' if r['agree'] else 'FAIL'} reproduced thin "
              f"{r['thin_boxes']} (published {r['thin_boxes_published']}) / "
              f"plausible {r['plausible_heads']} "
              f"(published {r['plausible_heads_published']})")
        i = d["issue2_reach"]
        print(f"   issue 2 reach: {i['recovered']} of {r['no_stem']} raw = "
              f"{i['over_raw_no_stem']:.1%}   of {r['plausible_heads']} "
              f"plausible = {i['over_plausible']:.1%}   "
              f"(+{i['points_gained_by_cleaning']} pts)")
        print("   where the thin boxes live:")
        for k, v in sorted(d["issue2_where_the_thin_boxes_live"].items(),
                           key=lambda z: -z[1]["under_floor"]):
            print(f"      {k[10:]:<46} {v['under_floor']:>4} of "
                  f"{v['n']:<5} {v['share']:>7.1%}")
    print(f"\n== issue 1: {out['issue1']['verdict']}")
    print(f"   {out['issue1']['print_verdicts']}")
    print(f"\nwrote {a.json}")
    if bad:
        print(f"DEAD: {bad} did not reproduce the stroke lane's own figures")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
