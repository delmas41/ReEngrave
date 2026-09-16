"""WHERE THIS DOCUMENT'S `restWhole` DETECTIONS ACTUALLY STAND — the population
the NEIGHBOUR witness is built out of.

⚠️ THE WITNESS IS ONLY AS GOOD AS ITS POPULATION, and that is the thing a cut
sweep cannot see. `WHOLE_REST_NEIGHBOUR_*` lets a detected `restWhole` in a
nearby bar of the SAME STAFF vouch for a suspect at nearly the same height. Its
whole justification is that *a tacet part prints a whole rest in every bar*, so
a real one always has a neighbour — a claim about rests that stand INSIDE their
own staff, at the slot.

A measure cell is padded several staff spaces above and below so ledger notes
are not sliced off, so on a conductor's page the NEIGHBOURING staff's ink lands
in this cell too. If a document's `restWhole` rows include a large population
standing outside their own staff, the neighbour witness is corroborating
cross-staff contamination with more cross-staff contamination — two copies of
the same mistake, which is this repo's recorded *correlated witnesses* hazard
with the correlation running through the CROP rather than through the ink.

This just counts them, by staff step. It decides nothing.

    python3 rest_population.py --cache cache.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators import rhythm as R  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from whole_rest_reach import load, _k  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--label", default="this document")
    ap.add_argument("--json")
    a = ap.parse_args()

    _c, box, cls, rest, _conf, lines, spacing = load(a.cache)
    wr = [s for s in rest if s in box
          and str(rest[s]).lower().startswith("restwhole")]
    if not wr:
        print("NO `restWhole` ROWS — dead instrument.", file=sys.stderr)
        return 2

    steps, out_of_staff = [], []
    for s in wr:
        k = _k(s, 3)
        ly, sp = lines.get(k), spacing.get(k)
        if not ly or not sp:
            continue
        st = R._staff_step(box[s], ly, sp)
        if st is None:
            continue
        steps.append(st)
        # THE STAFF ITSELF spans step 0 (bottom line) to 8 (top line). A whole
        # rest hangs at 5.5. Anything below 0 or above 8 is not in this staff.
        if st < 0.0 or st > 8.0:
            out_of_staff.append((s, st))

    # ── DOES THE SHIPPED BAND DESCRIBE THIS DOCUMENT'S WHOLE RESTS? ─────────
    # ⚠️ THE FALSE-NEGATIVE SIDE, ASKED WITHOUT A SINGLE CROP. The cuts claim
    # to be the SHAPE OF A WHOLE REST. Run them over the rests this document's
    # own detector got RIGHT — a population the rule never judges, and the same
    # population the cuts were derived from on the other document — and the
    # miss rate is how badly the description travels. A band fitted to one
    # plate that excludes a fifth of another plate's whole rests is a band
    # describing that plate, not the glyph.
    shape_miss = collections.Counter()
    for s in wr:
        k = _k(s, 3)
        ly, sp = lines.get(k), spacing.get(k)
        if not ly or not sp:
            continue
        pb = box[s]
        h = (pb[3] - pb[1]) / sp
        w = (pb[2] - pb[0]) / sp
        if h <= 0:
            continue
        asp = w / h
        if R._rest_shaped(h, asp):
            shape_miss["inside the SHIPPED shape band"] += 1
        else:
            if h > R.WHOLE_REST_INK_MAX_HEIGHT_SPACES:
                shape_miss["refused: TALLER than the shipped max height"] += 1
            elif asp < R.WHOLE_REST_INK_MIN_ASPECT:
                shape_miss["refused: NARROWER than the shipped min aspect"] += 1
            else:
                shape_miss["refused: WIDER than the shipped max aspect"] += 1

    n = len(steps)
    print(f"=== {a.label}: {n} `restWhole` detections with staff geometry ===")
    print()
    print("  THE SHIPPED SHAPE BAND, run over this document's OWN whole rests")
    tot = sum(shape_miss.values())
    for k in ("inside the SHIPPED shape band",
              "refused: TALLER than the shipped max height",
              "refused: NARROWER than the shipped min aspect",
              "refused: WIDER than the shipped max aspect"):
        v = shape_miss.get(k, 0)
        print(f"  {k:<48} {v:>5}  ({100.0*v/max(1, tot):5.1f}%)")
    print()
    bands = collections.Counter()
    for st in steps:
        if st < -2:
            bands["below the staff by more than a space (< -2)"] += 1
        elif st < 0:
            bands["just below the bottom line (-2..0)"] += 1
        elif st <= 8:
            bands["INSIDE the staff (0..8)"] += 1
        elif st <= 10:
            bands["just above the top line (8..10)"] += 1
        else:
            bands["above the staff by more than a space (> 10)"] += 1
    for k in ("below the staff by more than a space (< -2)",
              "just below the bottom line (-2..0)",
              "INSIDE the staff (0..8)",
              "just above the top line (8..10)",
              "above the staff by more than a space (> 10)"):
        v = bands.get(k, 0)
        print(f"  {k:<48} {v:>5}  ({100.0*v/n:5.1f}%)")

    at_slot = sum(1 for st in steps
                  if abs(st - R.WHOLE_REST_STEP) <= R.WHOLE_REST_STEP_TOLERANCE)
    print()
    print(f"  at the SLOT (|step - {R.WHOLE_REST_STEP}| <= "
          f"{R.WHOLE_REST_STEP_TOLERANCE})              {at_slot:>5}  "
          f"({100.0*at_slot/n:5.1f}%)")
    print(f"  OUTSIDE their own staff entirely                 "
          f"{len(out_of_staff):>5}  ({100.0*len(out_of_staff)/n:5.1f}%)")
    print()
    print("  ⚠️ Every row outside its own staff is a rest the neighbour witness "
          "can use to vouch for a suspect ALSO outside the staff — which is "
          "the population a whole-rest rule has no business speaking about.")

    if a.json:
        json.dump({"n": n, "bands": dict(bands), "at_slot": at_slot,
                   "out_of_staff": len(out_of_staff),
                   "shape_band_over_own_rests": dict(shape_miss),
                   "steps": [round(s, 3) for s in sorted(steps)]},
                  open(a.json, "w"), indent=1)
        print(f"\nwrote -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
