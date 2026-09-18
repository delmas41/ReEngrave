"""THE 26 HEADS TWO READERS DISAGREE ABOUT — reconstructed, then cropped.

⚠️ ADDED MID-PASS at the coordinator's direction, and reported APART from the
pre-registered sample. It is NOT part of `SAMPLE.json`: this is a census of a
named population, not a draw from one, so it carries none of that sample's
guarantees and must never be pooled with it.

WHAT THE STANDOFF IS. `omr-stem-attachment-2026-09` has two readers of a stem's
direction that share no METHOD:

  * the RASTER ATTACHMENT convention -- a run of ink in a hairline column
    beside the head; Sean's *right going up, left going down*;
  * the BEAM-MATE tier, already SHIPPED and default-on -- a beam joins stem
    TIPS, so every head under one beam is stem-unanimous.

Where both speak they agree on **144 of 170 Breitkopf heads (84.7%)** and on
97.0% of Litolff's. That lane refused to ship its tier on exactly this: one of
the two is wrong ~15% of the time on this plate and NEITHER instrument can say
which, because they share the notehead boxes and the plate. ⚠️ It also inverts
the published ordering, where Breitkopf is the BETTER reader (98.2% vs 95.9%).

⚠️⚠️ THE PRINT IS THE ONLY ARBITER NOT CORRELATED WITH EITHER PARTY, which is
why this belongs in a crop pass and nowhere else.

⚠️ THE 26 ARE RECONSTRUCTED, NOT COPIED: `breitkopf-marginal.json` publishes
the COUNT and not the keys. So the disagreement is re-derived by joining that
lane's own two committed outputs -- `breitkopf-rows.json`'s `says` against
`breitkopf-beammate.json`'s `fired` -- and the run ASSERTS it recovers exactly
the published 170 overlap and 26 disagreements. A reconstruction that lands on
a different number is not the population the standoff is about, and this exits
non-zero rather than cropping the wrong heads.

    python3 probe/standoff_rows.py --attach-dir ../omr-stem-attachment-2026-09 \
        --rows out/breitkopf-rows.json --json out/breitkopf-standoff.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXPECT_OVERLAP = 170
EXPECT_DISAGREE = 26


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--attach-dir", required=True)
    ap.add_argument("--rows", required=True, help="census_rows.py output, for boxes")
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    d = Path(a.attach_dir) / "out"
    att = json.loads((d / "breitkopf-rows.json").read_text())
    bm = json.loads((d / "breitkopf-beammate.json").read_text())
    marg = json.loads((d / "breitkopf-marginal.json").read_text())

    says = {r["subject"]: r for r in att["rows"] if r.get("says")}
    fired = bm["fired"]
    both = sorted(set(says) & set(fired))
    dis = [s for s in both if says[s]["says"] != fired[s]]
    print(f"{marg['label']}\nboth readers speak on {len(both)}   "
          f"they disagree on {len(dis)}")
    print(f"published:            overlap {marg['overlap']}   "
          f"disagree {marg['both_speak_agreement']['disagrees']}")
    # ⚠️ FAITHFULNESS CONTROL — the reconstruction must BE the population.
    if len(both) != EXPECT_OVERLAP or len(dis) != EXPECT_DISAGREE:
        print("DEAD: the reconstruction does not reproduce the published "
              "standoff, so these are not the heads it is about",
              file=sys.stderr)
        return 2
    print("faithfulness control: OK (reproduces both published counts)")

    rows = {r["subject"]: r for r in json.loads(Path(a.rows).read_text())["rows"]}
    out, missing = [], 0
    for s in dis:
        r = rows.get(s)
        if r is None or not r.get("bbox_page_px"):
            missing += 1
            continue
        out.append({
            "subject": s,
            "attachment_says": says[s]["says"],
            "beam_mate_says": fired[s],
            "R_up": says[s].get("R_up"), "L_down": says[s].get("L_down"),
            "illegal": says[s].get("illegal"),
            "where": r["where"], "cls": r.get("cls"),
            "bucket": r["bucket"],
            "bbox_page_px": r["bbox_page_px"],
            "staff_key": r["staff_key"], "staff_lines": r["staff_lines"],
            "staff_spacing": r["staff_spacing"],
        })
    print(f"croppable: {len(out)}   without a box in the census rows: {missing}")
    if not out:
        print("DEAD: none of the standoff heads is croppable", file=sys.stderr)
        return 2
    Path(a.json).write_text(json.dumps(
        {"label": marg["label"],
         "what": "heads the raster attachment convention and the SHIPPED "
                 "beam-mate tier disagree about; the print is the only "
                 "arbiter not correlated with either",
         "added_mid_pass": True,
         "not_part_of_the_preregistered_sample": True,
         "n": len(out), "rows": out}, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
