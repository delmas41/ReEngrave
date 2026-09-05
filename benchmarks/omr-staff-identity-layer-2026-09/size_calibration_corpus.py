#!/usr/bin/env python3
"""How big must the derived-tier corpus be? — sized from the BINS, not the library.

MEASUREMENT DESIGN, no pipeline behaviour. Run this BEFORE spending transcription
time, and report its target; run the calibration after and report the achieved
count against it.

WHY A TARGET AT ALL. `probe_calibration.py` failed for two reasons and only one
of them is about sample size:

  (a) the `derived` tier has n=0 records, so the tier whose calibration would
      decide an admission is not represented at all; and
  (b) the top bin has n=13, so even where there ARE records the curve cannot
      place its most decision-relevant point.

Neither is fixed by a better estimator, and (a) is not fixed by more of the
SAME data -- the shipped join names 175 of 197 truth-bearing staves from
labels, so derived records only exist where labels are WITHHELD. That is the
held-out-label design, and this is the calculation of how much of it is needed.

THE BIN ARITHMETIC. A reliability bin is a binomial estimate. To claim a bin is
calibrated we must be able to DETECT the miscalibration we would care about --
and we know its size, because we measured it: P(name)'s top bin promised 0.989
and delivered 0.692, and the smallest gap worth catching is around 0.08 (the
difference between "safe for a clef override" and "not"). At 95% confidence:

    n  >  p(1-p) * (1.96 / half_width)^2

    python3 benchmarks/omr-staff-identity-layer-2026-09/size_calibration_corpus.py
"""
from __future__ import annotations

import math

# Publisher labelling conventions, measured in
# benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md and reproduced on
# the 20-row gate by probe_heldout_identity.py.
#   staves_per_page is the mean over that publisher's gate rows;
#   truth_fraction is the share of staves whose identity the PAGE prints, which
#   is what a held-out-label run can score.
PUBLISHERS = [
    # name,        staves/page, truth fraction, note
    ("Breitkopf",  24.3, 1.00, "labels every staff — full held-out truth"),
    ("Litolff",    19.0, 0.64, "winds+brass only; strings unscoreable"),
    ("Simrock",    20.0, 0.33, "movement's first page only"),
]


def n_for(p, half_width, conf_z=1.96):
    return p * (1 - p) * (conf_z / half_width) ** 2


def main():
    print("BIN SIZING — how many records must a reliability bin hold?\n")
    print(f"  {'bin centre':>10s} {'gap to detect':>14s} {'n needed':>9s}")
    targets = {}
    for p in (0.95, 0.90, 0.80):
        for hw in (0.10, 0.08, 0.05):
            n = n_for(p, hw)
            print(f"  {p:10.2f} {hw:14.2f} {math.ceil(n):9d}")
            targets[(p, hw)] = math.ceil(n)
    print()

    # The decision-relevant bin is the TOP one: a consumer sets a high bar, so
    # that is where miscalibration costs something. Size on it.
    top_n = targets[(0.95, 0.08)]
    print(f"DECISION-RELEVANT BIN: centre 0.95, detect a 0.08 gap "
          f"-> n >= {top_n}")

    # Empirically the top bin held 13 of 197 records = 6.6%; but that curve was
    # label-dominated. For the derived tier assume the top bin is a larger
    # share, because a derived answer is either well-supported by position or
    # not; take a deliberately OPTIMISTIC 30% and flag it as an assumption.
    for share in (0.15, 0.30):
        need = math.ceil(top_n / share)
        print(f"  if the top bin is {share:.0%} of derived records "
              f"-> {need} derived records needed")
    print()

    print("PAGES REQUIRED (a held-out-label page yields one derived record per\n"
          "SCOREABLE staff, because every label is withheld from the predictor)\n")
    print(f"  {'publisher':11s} {'staves/pg':>9s} {'truth':>6s} "
          f"{'scoreable/pg':>13s}  note")
    for name, spp, frac, note in PUBLISHERS:
        print(f"  {name:11s} {spp:9.1f} {frac:6.2f} {spp*frac:13.1f}  {note}")
    print()

    for share, label in ((0.30, "optimistic"), (0.15, "conservative")):
        need = top_n / share
        bk = math.ceil(need / (24.3 * 1.00))
        print(f"  {label:12s} ({need:.0f} records): "
              f"{bk:2d} Breitkopf-equivalent pages")

    print("""
⚠️ A PUBLISHER HOLDOUT IS REQUIRED AND BREITKOPF ALONE CANNOT PROVIDE IT.
Calibrating on one house and testing on the same house is the publisher-shaped
trap this corpus has sprung before (document roster transfer: Simrock 45/45,
Litolff 2/50). But Breitkopf is the only publisher measured that labels EVERY
staff, so a second source must be either another Breitkopf work (different
plate, same house — a weak holdout) or Litolff at 0.64 truth coverage (a real
holdout, at 1.6x the pages for the same scoreable count).

⚠️ TWO SCANS OF ONE PLATE ARE ONE ENGRAVING and count once. Pages must come
from DISTINCT works/plates, not from re-scans.

RECOMMENDED TARGET, stated before any CPU is spent:
    ~200 derived records minimum for a 3-bin curve at n>=50/bin
    ~500 derived records for a top bin that resolves a 0.08 gap
    => 8 Breitkopf pages minimum, 21 for the full curve,
       PLUS ~10 Litolff pages as a genuine cross-publisher holdout.
    Call it 20-30 pages across >=2 houses and >=3 distinct plates.

⚠️ IF THAT PROVES IMPRACTICAL, SAY SO RATHER THAN HALF-FILLING THE CURVE. A
3-bin curve at n>=50 (8 pages) is an honest partial result and would answer
whether the derived tier calibrates AT ALL; it would NOT license a
high-threshold consumer, because the top bin is exactly what it lacks.""")


if __name__ == "__main__":
    main()
