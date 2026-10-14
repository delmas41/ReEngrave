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

---

# The re-assembly (Sean 2026-10-13: "yes, try the reassembly") -- REVERSE graft: KILLED, and it shows where the damage lives

STAGED detector only, `--through adjudicate`; production weights NOT switched. Same two pages, same truth, same controls (self-match 59/59,
shifted 0/59). Built with the unchanged `merge_class_head.py` (`--export-rows` from PRODUCTION, `--import-rows` onto the FINE-TUNE as `--base`;
self-check PASSED on all six builds = every other tensor bit-identical to the fine-tune). `build_reverse_graft.py`, `build_bn_arm.py`,
`class_counts.py`, `run_reverse_ab*.sh`; counts in `ab/class-counts-*.json`, scores `ab/score-reverse*.json`.

**Arms** (each built on the v24 fine-tune AND on the CONTROL fine-tune, `last.pt` of `runs/2.4b/hollow4-{withv24,control}`):
* **A** = fine-tune + production's `cv3.*.2` rows for the measured-damaged classes (>10% box drop vs production on either page, base >= 3: 23
  names) + the named set (beam, ledgerLine, augmentationDot, flag*, stem*, timeSig*) = 42 class names. Hollow heads (idx 28-39) stay the fine-tune's.
* **B** = fine-tune + production's rows for EVERY class except the taught hollow heads (156 names; includes the filled noteheads).
* **C** (not in the brief; found by the tensor diff below) = B + production's BatchNorm running statistics put back.

**Hollow heads** (Litolff TEST, 59 heads; Brahms pdf 0, 27 hollow):

| arm | Litolff recall | precision | Brahms found | Brahms extra hollow boxes (on timeSig 8/9 eyes) | filled called half |
|---|--:|--:|--:|--:|--:|
| production | 43/59 = 72.9% | 88.9% | 27/27 | 32 (14) | 0 |
| raw fine-tune (diagnostic, v24) | 54/59 = 91.5% | 88.1% | 25/27 | 48 (28) | 0 |
| **A, v24** | 54/59 = 91.5% | 88.1% | **25/27** | 48 (28) | 0 |
| **B, v24** | 54/59 = 91.5% | 88.1% | **25/27** | 48 (28) | 0 |
| C, v24 | 50/59 = 84.7% | 83.6% | 25/27 | 52 (29) | 0 |
| A / B, control (no v24) | 51/59 = 86.4% | 87.5% | 25/27 | 43 (22) | 0 |
| C, control | 48/59 = 81.4% | 85.7% | 24/27 | 49 (29) | 0 |

**Damaged classes** (detector boxes on the whole page, production -> arm; Litolff p1 / Brahms p0):

| class | production | raw ft | A = B (v24) | C (v24) |
|---|--:|--:|--:|--:|
| beam | 63 / 178 | 11 / 47 | 13 / 50 | 21 / 71 |
| ledgerLine | 103 / 231 | 27 / 190 | 26 / 184 | 128 / 236 |
| augmentationDot | 2 / 139 | 0 / 142 | (Litolff not listed, < 5) / 141 | 141 on Brahms |
| timeSig4 (Lit) ; 6, 8, 9 (Bra) | 7 ; 20, 33, 10 | 2 ; 12, 19, 5 | 2 ; 12, 19, 5 | 4 ; 11, 25, 6 |
| keyFlat | 19 / 28 | 9 / 25 | 9 / 25 | 10 / 21 |
| tie | 18 / 193 | 14 / 73 | 15 / 77 | 14 / 74 |
| restWhole | 113 / 11 | 86 / 5 | 86 / 6 | 109 / 10 |
| flag8thDown (Bra) | 40 | 27 | 27 | 34 |
| timeSig-digit hollow boxes (Bra) | 14 | 28 | 28 | 29 |

## Verdict: KILL (all three arms, both fine-tunes)
* **A and B restore nothing.** Putting production's class rows back for every damaged class changes the box counts by 0-2 (beam 11 -> 13, ledger 27
  -> 26, timeSig4 stays 2; A and B are the same to the box even though B restores 114 more classes). The raw fine-tune and A/B differ only in
  the tiny row-level effects. **The damage this round is NOT in the last-layer class rows** -- the opposite of the 2026-09-29 finding
  (docs/detector.md) that the six `cv3.*.2` tensors carry class deletion. That finding was for fine-tunes of the BASE on a corpus with 41-61% unboxed ink;
  this 1-epoch fine-tune started FROM production, so the rows barely moved (max |diff| 2.6e-4 on beam/ledger rows) and what moved is upstream.
* **Tensor diff, production vs the fine-tune: 422 of 595 tensors differ, but the conv weights moved < 2% (relative norm) while the BatchNorm
  running statistics moved 3-23%** (running_var up to 0.23 in `model.22.cv3.2.*`, i.e. the class branch's own input statistics). Arm C tests
  that suspect: it restores 291 BN buffers to production's and nothing else. **Result: BN statistics carry a large part of the damage -- ledger
  lines 27 -> 128 on Litolff (production 103), whole rests 86 -> 109, dynamics, fermatas, arpeggiato, 8th rests all back to within ~10% -- and a
  large part of the hollow gain: recall falls 91.5 -> 84.7 (v24) / 86.4 -> 81.4 (control), precision 88.1 -> 83.6.** Still not restored by C:
  beams (63 -> 21 / 178 -> 71), ties (193 -> 74), key flats, 3 of 4 time-signature digits; Brahms 25/27 and the `8`-eye boxes stay doubled (29).
  Those live in conv weights (cv3.* convs moved 1-2%, `model.19` 1.3%), not in anything that can be put back separately.
* **No arm meets the bar.** Needed: hollow recall +10 points or >= 90% with precision -3 at most, AND damaged classes within ~10%, AND Brahms 27/27,
  timeSig not doubled. A/B: recall 91.5% / precision -0.8 pts pass, but beams -79%, ledger -75%, timeSig4 -71%, Brahms 25/27, timeSig eyes x2 fail.
  C: recall +11.8 pts but precision -5.3, beams -67%, Brahms 25/27 fail. Same for the control.
* **Attribution.** v24 contributes +5 points at A/B (54 vs 51 heads = 3 heads) and +3 at C (50 vs 48 = 2 heads): ~one third of the gain over
  production at most, and 2-3 heads of 59 is inside noise for a one-seed run. Two thirds is "one more epoch from production on the old mix" (the
  control). The re-assembly therefore does not rescue the labeling round: the hollow gain and the class deletion are the same weight movement
  (A/B/C show no setting that keeps one without the other), which is exactly why the head-row graft got 0.

## Caveats
* One epoch, one seed, 59 + 27 heads. imgsz 896. `last.pt` used (best.pt differs by md5 but the raw numbers reproduce 54/59 exactly).
* Box counts are detector boxes after GATHER+ADJUDICATE on one Litolff page and one Brahms page; `staff`/`stem` classes are CV-side and not read
  as damage. A BN-stat restore in a trained model without recalibration is a diagnostic, not a candidate.
* Not tried (needs Sean's go; each is a new training run): freezing backbone + BN (`freeze` family was retired 2026-09-29 for the head, but BN-in-eval
  with frozen conv layers was never run), fine-tuning with BN statistics frozen (`model.eval()`-style BN) so the stats cannot move, 2048 on a cloud GPU.

---

# BN-statistics-FROZEN fine-tune (Sean 2026-10-13: "try it") -- is it the retired freeze family?

History read first (`git log --all -S "freeze=22"`, `ROUND7_FREEZE22_2026-09-05.md`, round 4/5, DSv2 rehearsal): the retired family is ultralytics `freeze=N`
(requires_grad off for layers 0..N-1; freeze=22 left only `model.22` trainable, where class deletion lives) plus rehearsal and label/imgsz/density arms.
A search of the benchmarks, docs and training code finds **no BatchNorm-statistics freeze ever run** (`freeze` leaves BN running stats updating in train mode).
1. **Different:** here every conv/head weight trains (incl. `model.22`); only the BN running mean/var are pinned (eval mode, momentum 0), so the
   features keep their production activation statistics while the weights learn the hollow heads.
2. **Same failure would look like:** beams/ledger lines/time-sig digits still collapse (beam < ~half of production) with the hollow gain intact -- then the
   deletion is in the trained conv weights themselves (the same optimisation dynamics as rounds 4-7), and the stats were a symptom.
3. **Different outcome would be:** damaged classes within ~10% of production with hollow recall >= 90% (or +10 pts) at precision -3 pts.

## Result: BN-frozen fine-tune -- SAME FAILURE (worse). 2.4b CLOSED AS KILLED (labels stay as test truth)
Trained from production, same mix, 1 epoch, imgsz 896 (`train_bnfrozen.py`, `train_2.4b_bn.sh`; checked after: BN running stats 194/194 tensors
bit-identical to production, conv weights moved 1.6-1.9%). Raw `last.pt`, same A/B and controls (`ab/score-bn.json`, `ab/class-counts-bn.json`).

| arm | Litolff recall | precision | Brahms found | Brahms extra boxes on timeSig digits |
|---|--:|--:|--:|--:|
| production | 72.9% | 88.9% | 27/27 | 14 |
| BN-frozen, v24 | 93.2% (55/59) | 89.2% | **24/27** | 34 |
| BN-frozen, control | 86.4% (51/59) | 92.1% | 23/27 | 20 |

| class (Litolff / Brahms) | production | BN-frozen v24 | BN-frozen control |
|---|--:|--:|--:|
| beam | 63 / 178 | **0** / 13 | **0** / 14 |
| ledgerLine | 103 / 231 | 8 / 143 | 0 / 87 |
| tie | 18 / 193 | 5 / 33 | 7 / 45 |
| timeSig4 (Lit) ; 6, 8, 9 (Bra) | 7 ; 20, 33, 10 | 0 ; 8, 14, 3 | 0 ; 11, 26, 4 |
| augmentationDot (Bra) | 139 | 139 | 140 |

Hollow recall and precision pass the bar (v24: +20 pts, precision +0.3) but beams are 0, ledger lines -92%/-38%, ties -72%/-83%, time signatures down by
half or more and doubled-plus `8`-eye boxes, Brahms 24/27 -- the damaged classes are NOT restored; they are deleted harder than in the unfrozen
fine-tune. This is the "same failure" outcome (point 2 above): the deletion lives in the trained conv weights, not the BN statistics (which in arm C
only masked part of the symptom). v24 vs control: +4 heads (55 vs 51), so ~1/5 of the gain over production. No graft arms built: the 2.4b
re-assembly showed restoring class rows changes nothing, and deletion is now deeper than before. **Kill** by the plan's bar; production unchanged.
