# Durations: not a rhythm bug (2026-08-31)

**Not fixed.** What follows is the diagnosis, a control that pins the cause, and
four attempts that did not work — recorded so the next attempt starts here
rather than at the beginning.

Duration recall on Beethoven 5 p.1 is **0.381** against a step recall of 0.714:
half the notes that are correctly located carry the wrong value. That looked
like the rhythm layer's problem — beam counting, flags, dots — and it is not.

## What the errors actually are

Pairing truth against output by step-and-octave over the page's 12 staves, 75
notes pair up and 49 have the right duration. Every substantial error is one
shape:

```
truth -> omr     count
  2.0 -> 0.5       15
  2.0 -> 1.0        5
  0.5 -> 1.0        3
  0.5 -> 2.0        2
```

Twenty of the twenty-six errors are a **half note read as something shorter**.
The duration histogram says the same thing from the other side:

| quarterLength | truth | OMR |
|---|---|---|
| 0.5 (eighth) | 77 | 99 |
| 1.0 (quarter) | 2 | 45 |
| 2.0 (half) | 68 | **8** |
| 4.0 (whole) | 0 | 7 |

The page prints 68 half notes and the output contains 8.

## The cause: hollow noteheads are not detected

Not misclassified — **not detected at all**. Drawing the detector's notehead
boxes over the Violino I staff shows the three opening eighths boxed and the two
fermata half notes carrying no box of any kind. Over the whole page the detector
reports 142 black noteheads and 17 hollow ones (9 half + 8 whole), where the
page prints 68 halves.

The reason is visible at 7× on the scan: at this print quality and 600 dpi
bitonal, **the half notehead's counter has closed**. What should be a white
ellipse is a thin diagonal sliver inside an otherwise solid head. A detector
trained on clean engraving has no reason to call that hollow, and does not.

## The control that pins it

The same music, the same weights, engraved by LilyPond instead of scanned
(`benchmarks/omr-orchestral-e2e/fixtures/beethoven-sym5-mvt1.pdf`):

| | scan | engraved |
|---|---|---|
| hollow noteheads detected | 17 | **31** |
| half notes on the page | 68 | 30 |
| pitch recall | 0.714 | 0.926 |
| pitch **and** duration recall | 0.381 | **0.926** |

On the engraved page every note whose pitch is right also has the right
duration — the two numbers are identical to three decimals. **The rhythm layer
is not the problem.** Durations fail on scans, and they fail because the
notehead they depend on is invisible.

This also means the meter work was worth what it was worth and no more: giving
`_reconcile_measure_to_meter` the right meter can only re-read a beam level, and
a bar missing its half note is not short by a beam level.

## Four attempts, none good enough to ship

**Reclassify by fill.** Measure the ink fraction inside each detected notehead
and flip filled/hollow. Useless here: there is nothing to reclassify, because
the heads are not detected. (Of the 159 boxes that do exist, 129 measure above
0.9 fill and the most hollow-looking is 0.63 — consistent with the closed
counter.)

**Find the counters as holes.** Connected components of white enclosed by ink,
filtered to notehead size. Returns **662 candidates for 68 half notes** — on a
scan this broken, enclosed white of roughly that size is everywhere.

**Template matching**, the technique that worked for the meter and for
key-signature accidentals. The Bravura `noteheadHalf` outline finds 15 of 68 at
a threshold of 0.50 and **none at all** above it. The printed head is too solid
to correlate with a drawn hollow one.

**Thin the ink and re-detect.** Dilate the paper by 2–4 px to reopen the counter,
then run the detector again. On three string staves holding 26 half notes it
goes from 4 hollow detections to 9 — and inflates `noteheadWhole` from 1 to 5,
which is a different wrong duration. Not a fix.

## What would actually work

This is a detection gap on degraded print, and this project's own history says
what closes those: **real labeled data**, through `tools/omr/annotate/`. The
specific ask is narrow and unusually well defined — hollow noteheads on scans
whose counters have closed — which makes it a good labeling batch rather than a
vague "more data" wish. The cells are easy to select: any staff whose bar sums
short against a known meter is a candidate, and the meter is now read
(`benchmarks/omr-timesig-2026-08/`).

Worth noting what NOT to do, from `[[project_domain_augmentation]]`: synthetic
augmentation of DSv2 was measured on exactly this kind of gap and made dense
real-cell recall *worse* (0.652 → 0.122). Ink-degradation augmentation is the
obvious idea here and it is the one that has already been disproven.

## Reproducing

```bash
python3 benchmarks/omr-first-run-2026-08/eval_first_run.py --stem beet5-p1-keyfix
```

The scan-versus-engraved control is two `transcribe` calls, one on
`IMSLP984073` page 1 and one on the orchestral-e2e Beethoven fixture, compared
against the same reference.
