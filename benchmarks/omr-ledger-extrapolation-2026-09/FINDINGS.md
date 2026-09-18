# The grid extrapolates past the staff at a pitch the plate does not print

2026-09-17. **No code outside `benchmarks/`** — `git status` lists seven files,
all under this directory. Nothing was re-gathered, no flag was flipped, no
default was changed. Pre-registration: [PREREGISTRATION.md](PREREGISTRATION.md),
committed **alone and first** (`7947a5ee`), before a probe existed or a record
was opened.

## 0. THE ONE-LINE RESULT

`pitch_resolver` reads a notehead's staff position as
`(y - top_y) / half_step`, where `half_step` is half the average gap between
**this staff's own five printed lines**. Inside the staff that is a
measurement. Outside it, it is an extrapolation at exactly **1.000×** — and
measured straight off the raster on 1,061 strips, the Litolff plate prints its
ledger rungs at **1.032 / 1.079 / 1.048 / 1.111** of the staff spacing, so the
grid has fallen **half a step behind by the fourth ledger line** and every note
there is read a diatonic step wrong.

On the second publisher the same measurement over 1,354 strips reads
**1.000 / 0.992 / 0.991 / 0.969 / 1.000 / 0.973** and the grid never falls half
a step behind, out to the sixth rung.

**66 of Litolff's 2,347 heads (2.81%) against 0 of Breitkopf's 3,337.**

⚠️ **66 is a FLOOR.** A further 44 Litolff heads stand beyond the fourth rung,
where the drift is larger and only 10 strips reach; they are unscored, in the
direction that makes the number worse.

## 1. WHAT THE PRE-REGISTERED PREDICTIONS DID

| | | |
|---|---|---|
| **P1** Litolff signed residual grows outward | **FALSIFIED as written** | §2 |
| **P2** the same statistic is ~0 inside the staff | **PASSED**, twice, independently | §3 |
| **P3** Breitkopf is near zero or inward, and weaker | **PASSED in the strong form** | §4 |
| **P4** the drift accounts for the §3a stem reversal | **FALSIFIED** | §6 |

Two of four failed. The headline survives because it does not rest on either
of them — it rests on a measurement neither prediction anticipated.

## 2. ⚠️ P1 IS FALSIFIED, AND ITS REPAIR IS NOT A RESCUE — IT IS A DIFFERENT QUANTITY

P1 asked the question through the signed residual `pos - round(pos)`. Measured
on Litolff, the outward-signed residual reads **+0.114 / +0.069 / −0.100 /
−0.037** across the four ledger bands: positive and falling where P1 said
positive and rising, then changing SIGN.

**The residual is bounded to ±0.5 and therefore WRAPS.** A stretch of 0.2
half-steps per rung is indistinguishable from a stretch of 0.2 minus a whole
step once the accumulation passes half a step, which at this plate's pitch
happens around the third rung. P1 was written without that in it, which is a
fault in the prediction and not in the mechanism.

⚠️ **The temptation here is the whole trap this repo keeps paying for**: having
predicted a monotone rise and got a sign change, the cheap move is to explain
the sign change with the wrap and call P1 confirmed. It is not confirmed. What
is recorded instead is that the residual **cannot answer this question at all**
past the second rung, and the answer came from measuring the printed rung
positions directly, which has no modulus in it (§4).

## 3. P2 PASSED, AND A SECOND, SHARPER VERSION OF IT ARRIVED FOR FREE

Inside the staff the same statistic reads **−0.034 / −0.002 / +0.011 / +0.023**
across four bands out from the middle line — flat, and an order of magnitude
under the outside figures.

⚠️⚠️ **AND THE DETECTOR HANDED OVER A MUCH BETTER CONTROL WITHOUT BEING
ASKED.** Of 1,878 `ledgerLine` detections on the Litolff record, **1,107 land
INSIDE the staff — every one of them at 0/2/4/6/8, the five printed staff
lines**, whose positions are known exactly. Scored there, the class's box
carries a bias of **+0.011 staff spaces at sd 0.048**: it locates a printed
horizontal line to a twentieth of a space. That is what licenses using a rung
as truth at all, and it was measured rather than assumed.

⚠️ It is also a finding in its own right and is NOT pursued here: the detector
fires `ledgerLine` on staff lines 1,107 times on four pages, and
`transcribe`'s ledger-ladder arbitration reads `ledgerLine` detections
directly. Whether that path filters them is unchecked.

**And the alternative that would have killed everything is ruled out.** If the
record's staff SPACING were slightly too small, everything outside would
stretch for a reason that has nothing to do with the engraving. Measured in the
same strips, the printed top→bottom span over the record's span is
**1.00000 on Litolff** (n=957) and 1.00450 on Breitkopf (n=947) — the grid is
right inside the staff, to five decimal places on the plate that drifts.

## 4. THE MEASUREMENT THAT CARRIES THE RESULT — off the raster, no detector

`probe_rungs_from_raster.py` renders the page at 600 dpi and finds the rungs as
rows of ink in a strip at the head's own x-range, exactly as `staff_detector`
finds staff lines — and finds the staff's five lines in **the same strip** as
its ruler, so nothing is carried in but where to look.

⚠️ **The scale is verified, not assumed**: the record's `staff_lines` for
`staff/1/0/0` read 1148/1163/1179/1195/1210, and a 600-dpi render of pdf page 1
has its dark rows centred at 1147.5/1163/1179/1194/1210.

**Control, printed in every run**: the staff's own five lines, found by the same
rule in the same strips, sit **+1.06 px** (Litolff, sd 2.38, n=5,201) and
**−0.33 px** (Breitkopf, sd 3.03, n=6,712) from the record — against a half-step
of 7.75 px. A strip in which the rule cannot recover four of the five staff
lines is REFUSED, not measured: 138 and 266 of them were.

| gap, × the staff spacing | Litolff (n) | Breitkopf (n) |
|---|--:|--:|
| edge → rung 1 | **1.032** (379) | **1.000** (604) |
| rung 1 → 2 | **1.079** (132) | 0.992 (279) |
| rung 2 → 3 | 1.048 (50) | 0.991 (121) |
| rung 3 → 4 | 1.111 (10) | 0.969 (54) |
| rung 4 → 5 | — | 1.000 (17) |

| the grid's error, half-steps | Litolff | Breitkopf |
|---|--:|--:|
| at rung 1 | +0.065 | +0.000 |
| at rung 2 | +0.223 | −0.016 |
| at rung 3 | +0.319 | −0.034 |
| **at rung 4** | **+0.541 — FLIPS** | −0.096 |
| at rung 6 | — | −0.151 |

**P3 passes in its strong form.** Breitkopf's gaps sit at or slightly UNDER
1.000 — the direction its independently measured 0.975 predicts — and its
cumulative error never reaches a quarter step in six rungs. ⚠️ Part of even that
is the grid's own +0.45% scale error on that document rather than the plate.

⚠️ **This is what rules the alternatives out.** If the cause were the
detector's box, the crop, the notehead's shape, the page warp or my arithmetic,
Breitkopf would show it too. It does not. The cause is a property of the PLATE,
which is what "ledger pitch is publisher-dependent" means.

**It also reproduces, from a third population, a result this repo already
had.** `omr-snap-ledger-2026-09` §2 measured the same convention off the ink of
117 hand-labeled notes: pooled edge→1st **1.055**, 1st→2nd 1.020, 2nd→3rd
1.017, with **Litolff 1.102/1.135 against Breitkopf 0.975** — the first gap
systematically the widest. Three populations, two of them detector-free, one
publisher split, same direction each time.

## 5. ⚠️ THE DETECTOR-BOX MEASUREMENT DISAGREES WITH THE RASTER AND THE RASTER WINS

`probe_rung_pitch.py` asks the same question of the model's `ledgerLine` boxes
and reads Litolff's gaps as **1.130 / 1.090 / 1.080** against the raster's
1.032 / 1.079 / 1.048. Same sign, same publisher split (Breitkopf 0.990 /
0.990 / 0.995), and the first gap is 10% too wide.

**The raster is the better instrument and the reason is already on file**: the
2026-09-03 ledger audit records a printed rung print-MERGING into the same
connected component as its neighbouring notehead, pulling a centroid by up to
a full half-step. A box drawn round merged ink sits further out than the line
it is meant to name. Both numbers are kept, and **no figure in §0 or §4 comes
from the detector**.

## 6. ⚠️⚠️ P4 IS FALSIFIED, AND THIS DOES **NOT** EXPLAIN THE STEM REVERSAL

The work was ranked by `docs/handoff-2026-09-17-two-brakes-and-a-ruler.md` §3a,
which measured the stem convention's accuracy rising to 0.939 four-to-six steps
from the middle line and then REVERSING to 0.765 beyond, and concluded the
position is what fails out there.

The position **is** what fails out there. It does not produce that reversal.

* Correcting the 32 own-staff heads that have ink truth *and* a projected stem
  to their TRUE position changes the convention's agreement by **exactly
  nothing — 17 of 32 either way.** Structurally it cannot: the convention flips
  at the MIDDLE LINE, and a one-step correction to a note six steps clear of it
  leaves it on the same side.
* The other candidate is refuted too. Split by `glyph_owner`, own-staff heads
  in the `6+` band read **0.713** and relocated copies **0.806** — the reversal
  is *worse* on the staff's own heads, so it is not the cross-staff copies
  either.

**§3a's reversal is still unexplained, and it is not this.** What this finding
is instead is a PITCH fault, which is the larger thing anyway.

## 7. ⚠️⚠️ THE CROP REFUTED MY OWN CLASSIFIER, WHICH IS WHY IT WAS CUT

The handoff's §5 ranked "crops, not code" first, because everything on the
thread was one of our readings agreeing with another. The first crop cut paid
for itself immediately and against its author.

An earlier cut of `probe_head_on_rung.py` scored **38.6%** of own-staff ledger
heads as wrongly placed. Cropping the worst of them showed `glyph/1/0/3/9/3`
sitting in the SPACE above the first rung, not on it: a notehead box on this
record is a median **2.62 half-steps tall**, taller than the step it sits on,
so "the rung is inside the box" also admits the neighbouring space, and a head
misclassified that way is scored WRONG **by construction**.

**The bias is vicious in exactly the direction that flatters the finding**: the
population one would naturally crop first — sorted by error — is the population
the classifier is wrong about.

Repaired by measuring the discriminator instead of assuming it, on the 836
heads INSIDE the staff whose line-or-space is not in doubt, in units of the
head's OWN height:

| | n | p5 | median | p95 | max |
|---|--:|--:|--:|--:|--:|
| head ON a line | 430 | 0.000 | 0.022 | 0.062 | 0.143 |
| head IN a space | 406 | 0.292 | 0.374 | 0.450 | — |

so the probe now answers ON below 0.15 and IN-A-SPACE above 0.29 and
**ABSTAINS between**, the empty-interval discipline this repo already applies
to dot windows, tie flanks and bracket columns.

⚠️ **The per-head figure that survives is still the weaker one and is not the
headline.** It reads 32.7% on Litolff against 0.9% on Breitkopf, over 52 and
222 heads, and it remains exposed to duplicate notehead detections (the crop
`glyph/4/0/0/9` shows two overlapping notehead detections at one position).
**§0's number comes from the raster and the measured pitch, not from it.**

⚠️ **And the crop's real payoff is that the drift is visible.** In
`out/print/zoom_glyph_4_0_0_9_2.png`, rung 1 sits on the grid's −2 tick and
rungs 2 and 3 stand progressively above the −4 and −6 ticks. The record agrees
to the detection: that cell prints its four rungs at −2.37 / −4.49 / −6.46 /
−8.80 where the grid says −2 / −4 / −6 / −8.

## 8. THE FIX IS NOT PROPOSED HERE, AND TWO ROUTES ARE ALREADY REFUTED

* **A corrected CONSTANT cannot work** and is refuted on file: no single factor
  serves Litolff's 1.03–1.11 and Breitkopf's 0.97–1.00 at once
  (`omr-snap-ledger-2026-09` §3 swept it and it lost).
* **`measure_ledger_rungs` already exists** — `tools/omr/annotate/ledger_grid.py`
  — and does exactly this against a cell image, for the LABELING UI. Its only
  consumers are `annotate/server.py` and its own test. ⚠️ But "the fix exists"
  is not "the fix ports": it reads a raster, so a reader-side version is a
  **GATHER change**, which `readjudicate` and `reexport_arm` are both
  structurally blind to and which only two full re-gathers can price.
* ⚠️ Its own findings record the guard that any port must keep: a click beyond
  an incomplete ladder's reach **falls back to the grid**, because
  extrapolating a whole ladder from one distant rung measured WORSE than the
  constant. This probe reproduced that failure from scratch before adopting the
  rule — counting a lone 4th rung as the 1st invented a −6.02 half-step error.

## 9. WHAT IS NOT ESTABLISHED

* **n = 2 documents, 2 publishers, 8 pages.** The hand-labeled study covers
  nine publishers and agrees; this one does not widen that.
* **Nothing was re-gathered, re-exported or scored.** No MusicXML moved, and
  **no OMR-NED figure is claimed** — the metric is symmetric and a wrong pitch
  inside a bar it has already failed to pair costs it nothing.
* **The 66 heads are identified but not individually adjudicated against the
  print.** Ten crops were cut and looked at; the mechanism was confirmed and
  one classifier fault was found. The remaining heads are a population estimate
  from the measured pitch, not 66 hand-checked notes.
* **The consequence in the FILE is unmeasured.** A wrong staff position is a
  wrong pitch through any clef, but how many of the 66 reach an exported
  `<note>` depends on the exporter's own refusals and was not checked.
* **`+1`, `+9` and beyond are unscored** on Litolff (173 and 44 heads) — the
  interpolation needs both bracketing rungs, and past rung 4 only 10 strips
  reach.
* The Litolff record was gathered on a **dirty tree** (`9d4ccc85`, `dirty:
  true`); the Breitkopf one is the committed shared record.
