# Stem and beam ground truth — and the bug it found in its first hour

**2026-08-28.** Fixing staff-line removal moved Mahler 5 p.11's stem count from
178 to 145, and nothing in the repo could say whether that was 33 artefacts
removed or 33 stems lost. `line_detection` (Phase 4f) had no ground truth of any
kind. This is that ground truth, and the answer.

## Where the truth comes from

Not from counting a scan by eye. A dense orchestral cell is genuinely ambiguous
to a human at canonical resolution, and a number nobody can reproduce is not a
baseline. Instead LilyPond engraves a sheet whose counts follow from the
notation itself — `reference-lines.ly`, 6 measures × 2 staves, 48 stems and 14
beam bars, exact and reproducible on any machine with LilyPond.

The same music is engraved at four staff-line **thicknesses** (0.09, 0.20, 0.29
and 0.39 staff spaces), because thickness is the axis the corpus actually varies
along — WTC 0.06, Boléro 0.09, Mahler 0.23, Beethoven 5 0.25 — and it is where
staff-line removal used to fail outright.

    python3 -m tools.omr.training.line_detection_eval

Two design points, both learned the hard way. The staves carry **different**
music: with identical music the stems align vertically across both staves and
barline detection, which votes on exactly that alignment, read them as barlines
— the sheet segmented into 19 measures instead of 6. And counts are compared per
**staff over the whole page**, not per cell, because segmentation is not stable
across thicknesses (at thickness 1 the barline before the chord measure is
missed and two measures fuse), and a per-cell comparison would score that
segmentation difference as a stem error.

## What it found: the notehead was taking its stem down with it

`detect_stems` isolates stems with a vertical opening whose kernel was **one
staff space** — which is exactly a notehead's height. So a notehead survived the
opening, remained joined to its own stem, and the component came out as wide as
the notehead; the width filter then threw the stem away with it. The same note,
before and after removal was fixed:

    staff-lines left in place:   w=32  h=282   accepted
    staff-lines removed:         w=85  h=309   rejected, too wide

This had been invisible because an un-removed staff line broke the notehead up
as a side effect. Removal working is what exposed it — the Mahler drop was the
symptom, not the disease.

The fix is not a tuned number. A component shorter than `min_height_lines` is
rejected a few lines later regardless, so erasing it in the opening costs
nothing, and the taller the kernel the more non-stem ink it clears first. So the
kernel goes just under that floor (0.8 × it). Stems against ground truth:

| line thickness | before | after | truth |
|---|---|---|---|
| 0.09 sp | 41 / 15 | 40 / 15 | 34 / 14 |
| 0.20 sp | 41 / 16 | 40 / 16 | 34 / 14 |
| 0.29 sp | **24 / 11** | **37 / 16** | 34 / 14 |
| 0.39 sp | **6 / 5** | **35 / 15** | 34 / 14 |

The collapse on thick lines is gone. On real pages, with staff-line removal
fixed and this kernel: **Mahler 5 p.11 145 → 212 stems** (above the 178 it read
before either change), Beethoven 5 p.10 20 → 34, Boléro 255 → 260, WTC unchanged
at 497.

### So the Mahler question is answered

The 178 → 145 fall was not lost stems. It was staff-line removal starting to
work and exposing a latent flaw in `detect_stems`, which is now fixed and
measured against known truth. There is still a residual over-count of about 6 on
the reference sheet (40 against 34), unexplained and worth a look.

## What it also found: beams were counting slurs, ties and ledger lines

Beams came back at **41 where 12 exist**, on clean engraving with thin lines.
Three separate defects, each measured:

**1. Everything horizontal was a beam.** The only checks were shape ones —
width, height, aspect — and a slur, a tie, a ledger line and a fragment of
un-removed staff line all pass them. On Mahler 5 p.11 those were essentially
the entire beam count: one cell of half notes under slurs reported **27 beams**,
another reported 26, boxing a staff-line fragment and the ledger lines beneath
some low notes.

**2. Sloped beams were counted several times each.** The stacked-bar count came
from the component's bounding box HEIGHT divided by a beam's thickness. A
sloped bar has a box far taller than the bar — measured, sloped beams fill only
43-46% of their box against 95% for a level one — so a single sloped bar was
reported as two, three, and in one cell eight.

**3. Stacked beams were rejected outright.** `max_height_lines` was 1.0, and two
bars plus the gap between them is about 1.2 staff spaces. An entire measure of
sixteenths scored **0 against a known 8**.

### What replaced it

The fix for (1) is one rule rather than one rule per false-positive class: **a
beam is horizontal ink that stems run into.** Nothing else in the notation is —
a slur or tie runs between noteheads, a ledger line sits at a notehead's middle
with at most one stem beside it, and staff-line residue has no stem at all.
Requiring two removes all four classes at once.

Two details earned their place by failing first:

* The stem must be allowed to **pass through** the component, not only end at
  it. With a double beam the stems stop at the outer bar and cross the inner
  one, so requiring an end found every primary bar and discarded every
  secondary. The stem's end still has to be within reach, which is what stops a
  long residue *inside* the staff from being adopted by every stem crossing it.
* The comparison is against the component's ink **in the stem's own column**,
  not against its bounding box. A sloped beam's box reaches well above and
  below the bar, which put the far stem out of range.

For (2), bars are counted as **vertical ink runs in a column**. A column crosses
each bar exactly once whatever the slope, so counting runs counts bars; the
median over sampled columns keeps a stem or notehead crossing the beam from
swaying it. This replaces `typical_single_beam_lines` entirely — no constant is
needed, which matters because no single value fits the corpus (real beams
measure a median 0.31 staff spaces on Mahler against 0.45-0.46 on WTC and
Boléro).

### Result

| line thickness | beams before | after | truth |
|---|---|---|---|
| 0.09 sp | 41 / 10 | 13 / 2 | 12 / 2 |
| 0.20 sp | 36 / 11 | 13 / 2 | 12 / 2 |
| 0.29 sp | 21 / 17 | 13 / 2 | 12 / 2 |
| 0.39 sp | 17 / 16 | 12 / 2 | 12 / 2 |

Summed absolute error over the four thicknesses falls from **157 to 3**. It
holds under degradation: re-rendering the sheet at 300 and 200 DPI keeps the
error at +1, and only at 150 DPI does recall start to go (10 of 14).

On real pages, beams fall to **Mahler 249 → 19, WTC 566 → 182, Boléro 308 → 79**.
Those are large drops, and they are precision, not recall: the removed
detections on Mahler were inspected and are slurs, ties, ledger lines and
staff-line residue, while on the beam-rich WTC page the surviving detections sit
squarely on real beams with the slurs and ties correctly ignored.

### Still open

No page-level ground truth exists for beams on a *real* score, only on the
reference sheet, so the real-page numbers above are supported by inspection
rather than by counting. The residual +1 on the reference sheet, and the
residual ~6-stem over-count (40 against 34), are both unexplained.

## Tests

15 units on synthetic cells (`test_line_detection_stems.py`) pinning the
notehead-vs-stem behaviour without needing LilyPond: one note yields one stem,
the component stays stem-wide rather than notehead-wide, a stemless notehead
yields nothing, and a stem at exactly the accepted height floor survives the
opening.
