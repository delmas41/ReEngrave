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

## What it also found, and what is NOT fixed: beams

Beams are heavily over-detected — **41 where 12 exist**, on clean engraving with
thin lines. Two separate causes, both measured, neither fixed here:

1. **Every beam is split in two.** `typical_single_beam_lines` is 0.22 staff
   spaces and its docstring says that "matches a single engraved beam". It does
   not. The reference sheet's beams measure 0.47 spaces — LilyPond's default
   beam thickness is 0.48, and half a staff space is the engraving convention —
   so `round(h / typical)` splits each single bar into two. Disabling the split
   alone takes staff 0 from 47 to 19 at thickness 1, and to exactly 12 at
   thickness 3.

2. **Something else is contributing false positives.** Even with splitting off,
   the lower staff reads 9-10 beams where it has 2. That staff is mostly half
   and whole notes below the staff, which points at **ledger lines**: they clear
   the width floor (1.5 spaces), are thin, and are horizontal.

The constant is deliberately left alone. Real beam candidates measure a median
of 0.31 spaces on Mahler but 0.45-0.46 on WTC and Boléro, so no single constant
fits the corpus, and raising it to suit the reference sheet would trade one
mis-tuning for another. The right shape is the one that worked twice for
staff-line removal and staff detection: **measure the typical beam thickness
from the page** and compare against that. Doing it properly also needs a ledger
line discriminator, which is a separate piece of work.

Beams therefore still have no trustworthy count. What they now have is a
harness that says so, with numbers.

## Tests

7 units on synthetic cells (`test_line_detection_stems.py`) pinning the
notehead-vs-stem behaviour without needing LilyPond: one note yields one stem,
the component stays stem-wide rather than notehead-wide, a stemless notehead
yields nothing, and a stem at exactly the accepted height floor survives the
opening.
