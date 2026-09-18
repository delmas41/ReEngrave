# PRE-REGISTRATION — the grid extrapolates past the staff at the wrong pitch

**Committed ALONE and BEFORE the probe was written or any record was opened.**
The precedent is `omr-cleanup-count-2026-09/CATEGORIES.md`: a prediction fixed
after looking is not a prediction, and commit order is the only form of that
claim a later reader can check.

## The convention

An engraver prints ledger lines at **their own pitch, and it is not the staff
spacing.** Measured in this repo already, off the ink of 117 hand-labeled
ledger notes (`benchmarks/omr-snap-ledger-2026-09/FINDINGS.md` §2, 185 rung
gaps):

| gap | n | median, × staff spacing |
|---|--:|--:|
| edge line → 1st ledger | 105 | **1.055** |
| 1st → 2nd | 49 | 1.020 |
| 2nd → 3rd | 26 | 1.017 |

and it is **publisher-dependent in BOTH directions**: Litolff hi-res
**1.102**, hollow-08 Litolff 1.135, Eulenburg 1.050 — against Breitkopf
**0.975**, Peters 0.977, Simrock 0.975.

## The mechanism this predicts

`pitch_resolver.pitch_for_notehead` (and `gather_notehead_positions`, which
restates the same arithmetic) computes

    pos_float = (y_center - top_y) / half_step

where `half_step` is **half the average gap between this staff's own five
printed lines**. Inside the staff that is a measurement. Outside it, it is an
EXTRAPOLATION at exactly 1.000× — a number the plate does not print.

Let the true rung pitch be `k` × the staff spacing. A head on the `m`-th
ledger line below the staff stands at `y = bottom_y + m·k·s`, so we read

    pos = 8 + 2·m·k     where the truth is 8 + 2·m

an error of **`2m(k−1)` half-steps, signed, growing linearly with `m`**, and
pointing AWAY from the staff when `k > 1`.

At Litolff's k ≈ 1.10 that is +0.2 per ledger line: the 3rd ledger line is
0.6 half-steps out and **rounds to the wrong staff position**. At Breitkopf's
k ≈ 0.975 it is −0.05 per ledger line, pointing TOWARD the staff, and an
order of magnitude weaker.

## What this would explain

`docs/handoff-2026-09-17-two-brakes-and-a-ruler.md` §3a measured the stem
convention's accuracy against distance from the middle line and found it
**rises steeply and then REVERSES**: 0.537 / 0.776 / 0.860 / **0.939** /
**0.765** across 0-1 / 1-2 / 2-4 / 4-6 / 6+ steps. A note three spaces clear
of the middle line is the least ambiguous case the stem convention has, so
the reversal cannot be the stem convention failing. Its own author's
conclusion was that the position is wrong there and named this as the
biggest lever available, because **position is PITCH**.

The `6+` band is exactly `pos < −2` or `pos > 10` — the second ledger line
and beyond, which is where `2m(k−1)` first exceeds a quarter step.

## THE PREDICTIONS, fixed before any record is opened

Recomputed from the record's own `Q.NOTEHEAD_STAFF_POSITION` **value**
(`pos_float`, kept unrounded), never from the stored `residual`, which is an
ABSOLUTE value and cannot carry a sign.

Signed residual `r = pos_float − round(pos_float)`.
Distance beyond the staff `m̂ = (pos − 8)/2` below, `(0 − pos)/2` above.

**P1 (LITOLFF, the headline).** Over Litolff Beethoven 5 pp.1-4, the signed
residual OUTSIDE the staff is biased AWAY from the staff, and the bias GROWS
with distance. Concretely: mean signed-outward residual is positive in every
outside band, and strictly larger in the further band than the nearer one.
*Falsified by:* a mean within noise of zero, or no growth with distance.

**P2 (the INSIDE control).** Inside the staff the same statistic is ~0 —
there the grid reads printed lines and there is nothing to extrapolate. If
the inside bands show the same bias, the effect is warp, clipping or box
centroid and NOT extrapolation, and P1 means nothing.
*This control can fail, and if it fails the headline is withdrawn.*

**P3 (BREITKOPF, the opposite-sign test).** The same statistic on
Breitkopf Brahms 1 pp.0-3 is **near zero or slightly NEGATIVE (inward)**, and
in any case **weaker than Litolff's**. This is the prediction that cannot be
got by fitting: it says a second publisher goes the OTHER WAY.
*Falsified by:* Breitkopf showing the same positive outward bias at similar
strength — which would make the cause something both plates share (the
detector's box, the crop, the warp) rather than the engraving.

**P4 (the reversal is accounted for).** Among `6+` heads, the ones the stem
convention calls WRONG carry a larger outward signed residual than the ones
it calls right.
*Falsified by:* no separation — which would leave §3a's reversal unexplained
and this whole line of work not the lever it was ranked as.

## What this pre-registration does NOT claim

- Nothing here is checked against the PRINT. Every figure is our own reading
  against our own grid, which is what §6 of that handoff already says of the
  whole stem thread. **Crops are a separate step and come after.**
- It claims nothing about what a FIX would be worth. `measure_ledger_rungs`
  exists in `tools/omr/annotate/ledger_grid.py` and is read by the annotate
  server and by nothing else, but "the fix exists" is not "the fix ports":
  that module reads a labeled cell image and the reader would need the same
  ink at gather time, which is a GATHER change and therefore unpriceable by
  any re-adjudication arm.
- A corrected CONSTANT is already refuted (§3 there: no single factor serves
  1.10 and 0.975) and is not proposed.
