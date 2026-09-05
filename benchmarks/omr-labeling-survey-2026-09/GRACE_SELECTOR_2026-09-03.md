# The grace-note selector — built, and what the first measurement says (2026-09-03)

`grace_score.py` is survey Row 2's cell selector (SURVEY_DESIGN.md §4 named
the signal: a small notehead near a full-sized one). Status: **built and
runnable; NOT yet validated, because the available cell pool cannot validate
it** — and that second half is the finding worth recording.

## What it does

Staff-line-removed crop → morphological opening (an ellipse 0.25 staff
spaces across snaps 0.06–0.12-space stems off head mass) → connected
components filtered to head-shaped ink (fill ≥ 0.55, aspect 0.95–2.4) →
two height bands in the cell's own staff spaces:

| band | height (spaces) | basis |
|---|---|---|
| full head | 0.85 – 1.30 | conventional 1.0-space head ± scan erosion/bleed |
| grace head | 0.45 – 0.78 | SMuFL/DSv2 grace ≈ 0.6×; floor clears the dot mass |

A grace candidate must stand within 3.0 spaces of a full head (grace notes
attach to a host). Score = candidate count; `--measure` prints the height
histogram; `--annotate-top` renders audit crops. Like `hollow_score.py`, a
RANKER — one plausible candidate makes a cell worth a human's minute.

⚠️ **Every constant above is a PROVISIONAL convention, not a measured gap.**
The hollow selector's bands were read off empty measured gaps; these cannot
be yet, because zero labeled grace notes exist anywhere in
`data/user-labeled` (the class is a total blind spot — that is *why* it is
Row 2). The floor at 0.45 sits under a real, measured mass — 834 of 1772
head-shaped blobs in the pool measure below 0.45 spaces (dots, staccati,
fragments) — but it is a smear that decays through the band
(456→205→173→142→70 per 0.05-space bin), not a gap. Calibrate all four
numbers against the first real labeled graces, not before.

## The measurement, and why this pool can't validate the selector

Run over the **280 cells on disk** (Breitkopf/Brahms 1 round-2 batch + the
four Phase-2 batches: Universal/Mahler 1, Novello/Elgar 1,
Jurgenson/Tchaikovsky 1, Durand/La mer):

- 1772 head-shaped blobs; **no empty gap anywhere in 0.30–1.40 spaces** —
  scan ink is a continuum, and the full-head mode actually centers nearer
  1.2 than 1.0 on these editions (bleed, dot-merges).
- 61/280 cells carry ≥1 grace candidate.
- **Visual audit of the top-ranked cells: false positives.** The top cell
  (elgar1-p99-s3-m8, 4 candidates) boxes fragments of a broken glyph and two
  small blobs; the next (brahms1-p4-s15-m0, 3) boxes a natural-adjacent
  fragment and two dot-like blobs. No audited candidate is a grace note.

**The pool is the wrong corpus by construction, and that is the finding.**
These cells were selected FOR the hollow campaign — short-bar, sparse,
sustained music ranked by enclosed-white counters — and ornamental
figuration anti-correlates with sustained sparse bars. A selector for a
blind-spot class cannot be validated on cells selected for a different
class; this is the corpus-coverage lesson again (*a corpus that cannot
express a fault cannot regression-test its repair*), met at the selection
stage instead of the benchmark stage.

## Next step (bounded, named)

Cut a fresh candidate pool from movements that PRINT grace notes, on
editions already in the library: Mahler 1 inner movements (Universal,
imslp17070 — the Phase-2 batch used only mvt 1's opening page), Scheherazade
(Eulenburg 2957 — the round-2 batch dir exists with its manifest), and a
Tchaikovsky movement. `select_cells_orchestral.py` cuts, `grace_score.py`
re-ranks, the annotate crops get an eyes-on audit, and the first sitting's
verdicts become the calibration set the bands are waiting for. Only then
does R2 earn a publisher-diverse sweep.

```bash
python3 benchmarks/omr-labeling-survey-2026-09/grace_score.py --measure \
    --repo /Users/seanjohnson/Desktop/ReEngrave <batch>/cells.json ...
python3 benchmarks/omr-labeling-survey-2026-09/grace_score.py \
    --repo /Users/seanjohnson/Desktop/ReEngrave \
    --annotate-top 8 --out-dir /tmp/grace-audit <batch>/cells.json
```

## CALIBRATED (2026-09-03, same day): the first 30 labeled graces re-cut the bands

Sean's sitting on `omr-labeling-grace2-2026-09` (eye-verified cells) produced
**30 grace boxes in 15 cells, 152/153 cells inspected** — the project's first
grace ground truth, exactly where the eyes and the reference said (the ★
figures at printed mm.39–40; the mm.28–30 bassoon + divisi-bass run). All 30
boxes are click-placed at the derived size; variants split 15
`OnLineSmall` / 15 `InSpaceSmall`.

Measuring the ink components under those boxes with the scorer's own
pipeline: **h 0.56–1.34 spaces, aspect 0.54–1.44, fill 0.53–0.85.** Two of
the provisional convention bands were wrong, for one mechanism: the opening
cannot detach a small head from its thin grace stem/beam, so grace ink
arrives taller than wide (aspect < 1) and beamed runs arrive as single
components above 1.0 space. The original bands passed **2 of 30**.

Cell-level confusion of three re-cut variants against the labels:

| bands | TP | FP | FN | TN | P | R |
|---|--:|--:|--:|--:|--:|--:|
| original (0.45–0.78, aspect ≥ 0.95) | 8 | 17 | 7 | 120 | 0.32 | 0.53 |
| **A: 0.50–0.95, aspect ≥ 0.50 (SHIPPED)** | **15** | 62 | **0** | 75 | 0.19 | **1.00** |
| B: 0.50–1.40, aspect ≥ 0.50 | 15 | 88 | 0 | 49 | 0.15 | 1.00 |
| C: B minus full-shaped components | 15 | 74 | 0 | 63 | 0.17 | 1.00 |

Variant A ships: for a cell RANKER, recall 1.00 is the property that
matters, and widening past 0.95 only adds false positives — a cell holding a
merged run always also holds a ≤ 0.95 component. Calibration set: one
edition (Peters), 30 boxes — re-measure when a second publisher's graces are
labeled.
