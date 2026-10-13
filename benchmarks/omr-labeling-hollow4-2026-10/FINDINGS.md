# ROADMAP 2.4b -- hollow-head detector round: the graft carries nothing (KILL by the plan's own bar)

2026-10-13, branch `lane-2.4b-hollow`, not merged. Detector only (GATHER+ADJUDICATE records, `--through adjudicate`);
no GATHER/ADJUDICATE/EVALUATE/INFER code changed. Production weights NOT switched.

## What was built
* **v24-2026-10-13-hollow4-train** (`data/user-labeled/`, NOT in `catalog-versions.txt` -- same precedent as v23): the 100-cell
  TRAIN batch, 90 hollow heads (64 half + 26 whole), 52 cells are real EMPTY labels. Converter run once, on a new version.
* **OnLine/InSpace recomputed** (DECISIONS 2026-10-13), not merged into one class: `recompute_line_space.py` fits the
  five staff lines in strips beside each head (the head's own x), puts the head's centre on that grid (integer = line,
  half-integer = space), and cross-checks with ink (a line through the head's centre row, or lines half a space above/below).
  On the staff the measured grid decides; off the staff (a ledger zone or a neighbour staff, where the grid is extrapolated
  across a gap that is not a whole number of spaces) the ink decides -- Sean's rule, ledger lines name the head. Result: the
  tool's tag was right on 87 of 90; the 3 changes are all tool InSpace -> OnLine (off-staff); 24 of 31 off-staff labels
  decided by ink, 8 off-staff labels had no ink evidence either way and keep the grid (UNCLEAR, listed in
  `hollow-class-recomputed.json`). The OnLine/InSpace pair stays two classes because the graft copies per-class rows;
  merging would change the class space.
* Other classes: the production teacher at conf 0.25, every box no human box overlaps (distill25 form), **except every
  hollow-class teacher box (71 dropped: unboxed hollow = background, Sean's rule)**. 1,748 teacher boxes (ledgerLine 292,
  black heads 418, beam 183, tie 128, slur 116, ...).

## The run (`train_2.4b.sh`, lock file + trap, `nice -n 10`, batch 8 / 2 workers)
From PRODUCTION (`hollow-graft-shift09`), the SHIP_RESULTS recipe: imgsz 896, 1 epoch, mix = v1-v4 (2x dense) + v13-v22
(distill25 form) + v24 -> 720 images/epoch, **~5 min training + ~3 min validation on the M1 Max**. A CONTROL arm (same,
without v24) was trained the same way, because "1 epoch from production on the old mix" is itself a change.
Grafts (`merge_class_head.py`, fixed direction, self-check PASSED): only the 7 notehead classes' rows onto a copy of
production, `--bias-shift` 0 and 0.9, for both arms.

## The A/B (`run_2.4b_ab.sh` = run_ab.sh's gather command; `score_ab.py`)
Litolff 984073 idx 1: Sean's 104 TEST cells (never trained on), 59 hollow heads, matched in the cell's canonical frame
against the record's own `box_canon` (no page mapping invented). Brahms 317803 idx 0: Sean's hand truth, 27 hollow heads.
Controls that can fail: truth self-match 59/59, truth shifted 3 head-widths 0/59 (both arms' numbers withheld otherwise);
**production reads 54 hollow boxes / 44 surviving ADJUDICATE on this page, exactly the earlier 2026-10-11 sizing** (independent
check that the frame is right).

| arm (weights) | Litolff TEST hollow recall | precision (boxes on a truth head) | Brahms hollow found | Brahms extra hollow boxes (on 8s / tremolo) | filled heads called half |
|---|--:|--:|--:|--:|--:|
| **production** | 43/59 = 72.9% | 48/54 = 88.9% | 27/27 | 32 (14 / 3) | 0 |
| graft, shift 0 (v24 mix) | 43/59 = 72.9% | 48/54 = 88.9% | 27/27 | 33 (14 / 3) | 0 |
| graft, shift 0.9 (v24 mix) | 36/59 = 61.0% | 37/38 = 97.4% | **18/27** | 19 (9 / 0) | 0 |
| graft, shift 0 (CONTROL, no v24) | 43/59 = 72.9% | 48/54 = 88.9% | 27/27 | 33 (14 / 3) | 0 |
| graft, shift 0.9 (CONTROL) | 36/59 = 61.0% | 37/38 = 97.4% | 18/27 | 19 (9 / 0) | 0 |
| *raw 1-epoch fine-tune, v24 mix (diagnostic, NOT a ship candidate)* | **54/59 = 91.5%** | 59/67 = 88.1% | 25/27 | 48 (**28** / 2) | 0 |
| *raw 1-epoch fine-tune, CONTROL (no v24)* | 51/59 = 86.4% | 56/64 = 87.5% | 25/27 | 43 (22 / 2) | 0 |

## Verdict against the plan's bars
* **Both grafts: KILL.** Shift 0 gains **0 points** (43/59 before and after, 54 hollow boxes before and after; the scores move
  by <= 0.03 so the rows are live, they just do not change a box); shift 0.9 LOSES 12 points of recall (and Brahms drops to
  18/27, failing "must stay 27/27") for +8.5 points of precision. The kill bar was "gain < 5 points".
* **v24 contributes nothing at the graft level**: the v24-mix graft and the control graft are identical to the box on Litolff
  (and 66 vs 67 hollow boxes on Brahms). The 90 hand labels do not move the head rows against 700 other images.
* **Where the gain actually is: the features, not the head rows.** The raw fine-tune reads 91.5% (>= the 90% bar) at 88.1%
  precision -- but 86.4% of that is the control (one more epoch from production on the OLD mix; v24 adds +3 heads = +5 points),
  and it costs 5 more time-signature-digit boxes on Brahms (28 vs 14 -- the plan's "8 eyes" kill criterion is exactly what
  rises) and 2 of 27 Brahms heads. And the raw model deletes classes: Litolff page, production -> raw fine-tune, beams 63 -> 11,
  ledger lines 103 -> 27, augmentation dots 2 -> 0 (despite 1,748 teacher boxes in the corpus) -- the known class deletion;
  that is why the product path only ever grafts rows, and grafted rows trained against drifted features do not land on
  production's features.
* The 16 truth heads production misses: 10 have NO box at all (reach), 6 sit under a black-head box (class). The raw
  fine-tune closes the reach ones (4 left) -- reach, not floor.

## Not claimed / caveats
* One epoch, one seed, one test page (59 heads): a 5-point difference is 3 heads. The graft result is an exact zero, which is the
  robust finding; the raw-ft numbers are a diagnostic of where the signal lives.
* Tempo-mark notes are deliberately unboxed, so a few true boxes count against precision on every arm alike.
* imgsz 896 (the feasible one here); 2048 would need a cloud GPU.
* Untested and NOT recommended without Sean: keeping the fine-tune's features (it deletes beams/ledgers), a freeze or
  rehearsal variant at 2048, grafting a larger slice of rows (the box-regression rows are shared and would move everything).

Artefacts: `ab/score.json` (the records, 417 MB, stay in the ignored `runs/2.4b/ab-records/`; re-gather with `run_2.4b_ab.sh`), `hollow-class-recomputed.json`,
`verdicts-recomputed/`, weights under `omr-weights/candidates/hollow4-2.4b-*` (gitignored).
