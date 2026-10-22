#!/usr/bin/env python3
"""PRE-REGISTER the strips, before any of them is looked at.

⚠️⚠️ THE SAMPLE IS FIXED BEFORE THE CROPS EXIST, and the reason is this repo's
own record: a sibling lane sampled its barlines FROM the `too TALL` bucket and
then measured *"19 of 19 are too TALL"*, which is true by construction. Here
the hazard is sharper, because the question is **which of two populations a
pair belongs to** — so choosing the pairs after seeing them would decide the
answer.

## WHAT IS BEING ASKED OF THE PRINT

`probe_where_along_the_stem.py` measured that the two populations **overlap
with no empty interval**: the gap between consecutive heads claiming one
stroke runs 0.0 to 4.0 notehead heights on Litolff and 0.0 to 5.0 on
Breitkopf, continuously, on both plates. So geometry cannot say whether three
heads on one stroke are **a chord** (legitimate, all attached at one end) or
**one note's stem crossing two strangers** (the attribution fault). The print
can.

**THE QUESTION PER STRIP, and it is one question:** *is the vertical stroke
under the marked head THIS head's stem, or does it belong to another note?*

## WHY A STRIP AND NOT A TILE

`docs/handoff-2026-09-18-three-lanes-and-the-print.md` §3: *"at tile
magnification the adjudicator read two heads WRONG and a wide strip corrected
both — a numeral and a dotted half note each read as a hollow head with no
stem. A crop centred on a head cannot tell you the head is a NUMERAL. Any
future crop pass here uses a full-width strip."* That is an instruction from a
paid-for mistake, and it is obeyed: every crop here is the full width of the
staff at the marked bar.

## THE STRATA

Both are defined off `end_gap_heads` and `interior_chord_member`, which are
the probe's own columns and are computed from the RECORD, never from a crop:

* **`far_with_a_better_claimant`** — the head is more than 1.0 notehead height
  from either end of the stroke AND another head claims the same stroke from
  within 0.5. This is the presumed FAULT; 153 such pairs on Litolff and 231 on
  Breitkopf.
* **`chord_interior`** — the head has a claiming mate both above and below on
  the same stroke. This is the presumed LEGITIMATE case; 115 and 36.

⚠️ **The two strata are the two answers the probe cannot separate, and they are
sampled EQUALLY** — not in proportion — because the question is whether the
labels are right, not how common each is. A proportional sample would spend
the human's attention on whichever stratum happens to be larger.

⚠️ **The seed and the counts are in this file and in the artefact**, so the
sample can be reproduced and a later reader can check that what was
adjudicated is what was drawn.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

#: ⚠️ Fixed here, never on the command line: a seed passed in is a seed that
#: can be retried until the sample looks convenient.
SEED = 20260920

#: Per stratum, per document. 20 is what one sitting can hold at strip size,
#: and the strata are equal by the argument above.
PER_STRATUM = 20

FAR_HEADS = 1.0          # the probe's own band edge, restated nowhere else
AT_AN_END_HEADS = 0.5


def strata(rows: list) -> dict:
    """The two populations, by the probe's own columns."""
    per: dict = {}
    for r in rows:
        per.setdefault(r["stem"], []).append(r)
    far, chord = [], []
    for r in rows:
        mates = [o for o in per[r["stem"]] if o["subject"] != r["subject"]]
        if (r["end_gap_heads"] > FAR_HEADS
                and not r["interior_chord_member"]
                and any(o["end_gap_heads"] <= AT_AN_END_HEADS for o in mates)):
            far.append(r)
        if r["interior_chord_member"]:
            chord.append(r)
    return {"far_with_a_better_claimant": far, "chord_interior": chord}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, help="the probe's json")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = json.load(open(a.probe))["rows"]
    pops = strata(rows)
    rng = random.Random(SEED)
    picked = []
    for name, pop in sorted(pops.items()):
        # ⚠️ SORTED BEFORE SAMPLING. `rows` arrives in record order, which is
        # stable, but a dict iteration or a set anywhere upstream would make
        # the "seeded" sample unreproducible — the silent kind of
        # irreproducibility, because it still prints a seed.
        pop = sorted(pop, key=lambda r: (r["subject"], r["stem"]))
        take = pop if len(pop) <= PER_STRATUM else rng.sample(pop, PER_STRATUM)
        for r in sorted(take, key=lambda r: (r["subject"], r["stem"])):
            picked.append({"stratum": name, **r})
        print(f"  {name:<28} {len(pop):>5} available -> {len(take)} drawn")

    if not picked:
        print("⚠️ DEAD: neither stratum is populated in this probe output.",
              file=sys.stderr)
        return 2

    out = {"label": a.label, "seed": SEED, "per_stratum": PER_STRATUM,
           "probe": a.probe,
           "available": {k: len(v) for k, v in pops.items()},
           "question": "is the vertical stroke under the marked head THIS "
                       "head's stem, or does it belong to another note?",
           "verdicts_allowed": ["this_heads_stem", "another_notes_stem",
                                "cannot_tell", "not_a_notehead"],
           "rows": picked}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"{a.label}: {len(picked)} strips pre-registered -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
