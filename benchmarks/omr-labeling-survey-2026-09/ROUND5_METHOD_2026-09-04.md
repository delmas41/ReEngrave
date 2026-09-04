# Round 5 — the fine-tune deletes classes, and no hyper-parameter fixes it

**Date:** 2026-09-04 · **Box:** vast.ai RTX 4090 48 GB (US), destroyed ·
**Status:** production scan weights UNTOUCHED, nothing shipped.

Follows `docs/handoff-2026-09-04-scan-weights-round4.md`, which ended with
"every fine-tune degrades the base's breadth" and named four method levers.
This round measured what "degrades" means, ran the levers, and found the fix is
not a lever at all.

---

## 1. It is not suppression and it is not calibration — it is class deletion

The handoff reads the failure as fine-tunes *suppressing detection*. There was a
cheaper explanation nobody had ruled out: the pipeline thresholds at a fixed
`conf 0.25`, and a fine-tune whose unlabeled ink is background pushes
confidences down, so a detection that merely lost confidence looks deleted. That
would have been one number per checkpoint.

**It is not calibration.** Every fine-tune's median confidence is HIGHER than
production's (0.669-0.698 vs 0.604) while raw detections fall 3204 -> 806-1365
(`probe_confidence_shift.py`). What is gone is whole class families, at exactly
zero rather than reduced:

| class | production | e3 | e5 | e10 | r4 e5 | i512 e1 |
|---|--:|--:|--:|--:|--:|--:|
| noteheadBlack (both) | 718 | 561 | 593 | 636 | 624 | 707 |
| **tie** | 249 | 0 | 0 | 0 | 0 | 0 |
| **slur** | 184 | 0 | 0 | 0 | 0 | 0 |
| **beam** | 188 | 0 | 0 | 0 | 0 | 0 |
| **augmentationDot** | 150 | 0 | 0 | 0 | 0 | 0 |
| **accidentalFlat** | 80 | 0 | 0 | 0 | 0 | 0 |
| **restWhole** | 396 | 0 | 0 | 0 | 0 | 0 |
| **ledgerLine** | 288 | 5 | 0 | 0 | 14 | 149 |

Noteheads and dynamics — the two families the campaign swept — survive at
80-100%. The mechanism is in the corpus: 3871 human boxes contain **0 `beam`
and 5 `ledgerLine`**, and the campaign's own stamps say what a pass ever looked
for (603 cells hollow noteheads, 409 rests+accidentals, 255 grace, 46 clefs,
only 109 + 55 under a rich palette). On most cells a slur, a tie, a beam or a
ledger line is background, and the loss teaches exactly that.

**Two of the dead classes are consumed by the pipeline.** `CLAUDE.md` tells a
labeler to skip stems, beams and staff lines because classical CV finds them and
a human cannot bbox a thin line — both true — but that silently became "they may
train as background", and they may not:
`rhythm.resolve_rhythms_for_cell` keeps a YOLO `beam` wherever no CV beam
overlaps (worth pooled 0.1917 -> 0.1861) and the ledger-ladder arbitration reads
`ledgerLine` detections directly (0.1506 -> 0.1431). On every candidate measured
in rounds 3-5, **both rules are dead**, silently, because neither has a test
that fails when its input vanishes. That is now gate axis 3.

⚠️ `restWhole` was nearly exempted from that gate on the reasoning that 396 over
five pages must be the documented slur-arc false-positive mode. Counted against
the truth files it is wrong the other way: those pages carry **801 resting bars**
(194/194/18/99/296) and production reads 108/88/11/96/93 — under the printed
count on every page. The exemption is gone; `staff` is the only one left, and
that one is policy.

## 2. Eleven method arms, all identical

Rented a 4090 and ran the levers, at the 896 ship's 69/31 dense ratio (⚠️ 2x
oversampling now gives 43/57 because there are 359 hollow cells against v7/v8's
119 — the ratio is the ship's parameter, not the factor).

| arm | classes | beam | tie | accidSharp | ledgerLine |
|---|--:|--:|--:|--:|--:|
| production | 28 | 126 | 19 | 15 | 31 |
| pre-hollow base (control) | 29 | 127 | 24 | 15 | 57 |
| prod896 e0 — the ship's recipe, new data | 11 | 0 | 0 | 0 | 2 |
| nowarmup e0 | 10 | 0 | 0 | 0 | 0 |
| gentle (nowarmup + lr 1e-5) | 11 | 0 | 0 | 0 | 3 |
| plain2 (matched control) | 12 | 0 | 0 | 0 | 7 |
| rehearsal (teacher, pass scope) | 12 | 0 | 0 | 0 | 7 |
| distill (teacher, all scope, conf .50) | 12 | 0 | 0 | 0 | 7 |
| distill25 (all scope, conf .25) | 12 | 0 | 0 | 0 | 11 |

* **The warmup hypothesis is dead.** One epoch is ~31 steps at 4.7e-05, which
  cannot zero a class, but ultralytics runs bias params at `warmup_bias_lr` 0.1
  for the first 3 epochs — so a short fine-tune is *entirely* warmup. Turning it
  off changes nothing. The arithmetic still stands; it is not the mechanism.
* **The ship's recipe on the new data is dead** — the control the last session
  never ran. So the 896 ship survived because of what v7/v8 CONTAINED, not how
  it was trained.
* **Teacher rehearsal is dead as a training fix.** Even at conf 0.25 (3417
  teacher boxes, `beam` 450, `ledgerLine` 350, `tie` 336) the classes still go
  to zero. 450 beam boxes over 591 cells is 0.76/cell against a base trained on
  DSv2; it is not enough to hold a class open.
* **The pre-hollow base loses NOTHING** (29 classes, 0 collapsed), so the
  collapse is caused by this fine-tune and not inherited.

The class-id mapping was checked against the checkpoints' own `model.names`
rather than assumed — 0 mismatches at every index — so none of this is an index
bug.

## 3. The fix is surgery, and it works on two axes of three

A YOLOv8 detect head is per-class in exactly one place: `model.22.cv3.{0,1,2}.2`
is a 1x1 convolution with one weight row and one bias per class. So take the
fine-tune and put the base's rows back for every class the corpus does not
teach (`merge_class_head.py`, seconds on a Mac, no GPU).

| checkpoint | detections | classes | collapsed |
|---|--:|--:|--:|
| production | 594 | 28 | — |
| distill25 e0 raw | 303 | 12 | 7 |
| restore-if-never-labelled | 460 | 14 | 5 |
| **hollow graft** (keep 7 notehead classes, restore 201) | **574** | **28** | **0** |

**Axis 1 (beet5 p.1 scan + 18 dense cells):**

| | production | hollow graft | raw fine-tune |
|---|--:|--:|--:|
| half-noteheads | 27 | **44** | 44 |
| dense notehead recall | 0.941 | **1.000** | 1.000 |
| pitch recall (step) | 0.646 | **0.742** | 0.714 |
| pitch+duration recall | 0.435 | **0.558** | 0.599 |
| classes held | 28 | **28** | 12 |

⚠️ **The raw fine-tune beats the graft here and is not the better checkpoint** —
a model that has forgotten twenty classes emits almost nothing to be wrong
about. Its axis-3 column is the same sentence from the other side.

**Axis 2 (5-page scan-e2e) — DOES NOT HOLD:**

| | OMR-NED | edits | predicted |
|---|--:|--:|--:|
| production | **0.7517** | 7894 | 4350 |
| hollow graft | 0.7572 | 8036 | 4462 |

So **nothing ships.** But the ratio is not the reading: element counts move
toward truth on note (1478 -> 1490 of 1894), tie (60 -> **106** of 271), slur
(160 -> 170 of 204), beam (358 -> 368 of 563) and time (56 -> 69 of 110), away
on accidental (79 -> 67 of 85) and clef (77 -> 74 of 112). And the pooled rise
is not spread — the graft **improves three of five rows** (Mahler -0.0139,
Dvorak -0.0114, Brahms -0.0016) and loses on both Beethoven rows (+0.0428,
+0.0163).

⚠️ **Beethoven 5 p.1 is the page the hollow campaign is ABOUT** — 68 printed
half notes — so the arm built for it is the arm that loses there. `wrong note
head` 30 -> 72 and `wrong note` 151 -> 178: it reads 44 half-noteheads against
production's 27 (truth 68) and `hollow_eval` scores that page's pitch+duration
recall 0.435 -> 0.558, so many of the new heads are right and musicdiff charges
the ones that are not. **Recall bought with precision — axis 1's metric rewards
it and axis 2's charges it, on the same change.**

## 3b. A per-class confidence floor clears axis 2

Grafting onto PRODUCTION instead of onto the base measures **0.7577** against
the base graft's 0.7572 — no difference — which locates the cost exactly: it is
not the 201 restored classes, it is the seven grafted ones over-firing. The
pipeline has one global `conf_threshold`, so the floor goes into the weights:
subtracting `logit(p1) - logit(p0)` from a kept class's bias IS raising that
class's threshold from p0 to p1 (`merge_class_head.py --bias-shift`; 0.25 ->
0.45 is 0.90).

| | OMR-NED | edits | predicted |
|---|--:|--:|--:|
| production | 0.7517 | 7894 | 4350 |
| graft, no floor | 0.7577 | 8038 | 4457 |
| **graft + shift 0.9** | **0.7493** | **7872** | 4355 |

Four of five rows improve — Mahler -0.0240, Dvorak -0.0076, Beethoven/575951
-0.0034, Brahms -0.0018 — and Beethoven/984073's regression halves (+0.0428 ->
+0.0228).

⚠️ **Axis 2 alone does not make this a ship candidate.** The floor gives back
some of the half-noteheads axis 1 rewards, by construction. A checkpoint that
clears axis 2 by discarding the gain it exists to deliver is production with
extra steps, so axis 1 and axis 3 must be re-run ON THE SHIFTED CHECKPOINT
before any of this counts.

## 4. What the next session should do

1. **Graft onto PRODUCTION, not onto the pre-hollow base.** Production is the
   checkpoint that scores 0.7517; the current graft replaces its head with the
   base's on all 201 restored classes, which is a different model. Built as
   `d25e0_graft_onto_prod.pt`; measured in `RESULTS` below when it lands.
2. **Price the precision.** The graft's extra half-noteheads are the whole
   trade. A confidence floor applied to the grafted hollow classes only — they
   are seven rows and can carry their own threshold — is the obvious knob and
   costs no training.
3. **Do not run more training arms on this corpus.** Eleven is enough. If a
   training fix is wanted, it needs DeepScoresV2 back for real rehearsal
   (`download_dataset.py` + `prepare_yolo_data.py`, tens of GB, best done
   straight onto a rented box), and that is a separate decision.

## 5. Rig faults worth not repeating

* **v2/v3/v4 store their cell images as SYMLINKS** into the labeling batch dirs;
  only v1 and the round-3 versions are copies. A plain `cp -R` into a cloud
  tarball shipped 101 of the 136 dense-base cells as dangling links, and
  ultralytics skipped them as "corrupt image/label" inside a warning stream
  thousands of lines long. The dense base is what carries the class breadth.
  `build_cloud_tarball.sh` now uses `cp -RL`.
* **Do not overwrite a running bash script** — bash re-reads it by byte offset,
  so editing the arm list mid-sweep shifts every offset after the edit.
* **The 208-class space has 40 DUPLICATED NAMES** (`augmentationDot` at 40 and
  159, `clefG` at 5 and 141, `slur` twice) because DSv2 carries two naming
  families. `merge_class_head.py --keep` keeps every index of a name. But
  `build_rehearsal_versions.py`'s `name_to_id` resolves a duplicate to its LAST
  index, so teacher boxes for those 40 names went to the model's other class of
  the same name. It changed no conclusion here — the distill arms lose on their
  own terms — and it is a defect.
* **`e1_768.pt` from the round-4 sweep will not load at all** (truncated
  transfer). The screen skips an unloadable checkpoint loudly rather than dying.
