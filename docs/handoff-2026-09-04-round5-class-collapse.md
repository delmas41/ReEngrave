# Handoff — round 5: the fine-tune deletes classes, and the fix is surgery

**Branch:** `claude/scan-weights-round4-continue-074940` (has the round-3/4
branch merged into it). **Production scan weights are UNTOUCHED and nothing has
shipped.** GPU spend **$0.37**; the rented box is destroyed.

Full account: [`benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md`](../benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md).

## 1. The one-line state

There is a checkpoint that beats production on **all three gate axes** for the
first time in three rounds — `omr-weights/round5-merged/d25e0_graftprod_shift0.9.pt`
— and it was produced by **head surgery on a failed fine-tune**, not by
training. Sean's call whether it ships.

| | half | with-dur R | exact R | dense R | axis 2 | classes |
|---|--:|--:|--:|--:|--:|--:|
| production | 27 | 0.4354 | 0.5646 | 0.941 | 0.7517 | 28 |
| **candidate** | **31** | **0.5102** | **0.5782** | **1.000** | **0.7493** | **28, 0 collapsed** |

## 2. What round 4's "degrades the base" actually meant

Not suppression and not calibration — every fine-tune's median confidence is
HIGHER than production's. **Whole class families go to exactly zero**: tie
249→0, slur 184→0, beam 188→0, augmentationDot 150→0, accidentalFlat 80→0,
restWhole 396→0, ledgerLine 288→14, while noteheads hold at 80-100%.

The corpus is the mechanism: 3871 human boxes contain **0 `beam` and 5
`ledgerLine`**, and the pass stamps say only 164 of 591 cells ever saw a rich
palette. Everything unboxed is background.

⚠️ **`beam` and `ledgerLine` are consumed by the pipeline** — `rhythm` keeps a
YOLO beam where no CV beam overlaps (0.1917→0.1861), the ledger-ladder
arbitration reads `ledgerLine` directly (0.1506→0.1431). Both rules were dead on
every candidate of rounds 3-5, silently. That is now **gate axis 3**
(`probe_confidence_shift.py --gate`, and `probe_class_inventory.py` for a
40-second screen on 30 held-out cells).

## 3. ELEVEN METHOD ARMS, ALL DEAD — do not re-run

`prod896` (the 896 ship's recipe on the new labels — the control round 4 never
ran), `nowarmup`, `gentle`, `lowlr`, `plain2`, `dense6`, `freeze`, and teacher
rehearsal in both scopes at conf 0.50 and 0.25. All collapse the same eight
classes. The **pre-hollow base loses nothing**, so it is caused by the fine-tune
and not inherited. Class ids verified against the checkpoints' own `model.names`
— not an index bug.

**Two hypotheses died here that were worth testing:** the warmup theory (one
epoch is ~31 steps, but `warmup_bias_lr` is 0.1 for the first three epochs, so a
short fine-tune is entirely warmup — turning it off changes nothing), and
teacher rehearsal (3417 teacher boxes including 450 beams still leaves the
classes at zero; 0.76 beams per cell cannot hold a class open against DSv2).

**More labeling will not fix this.** Round 4 tested it by hand (3%); round 5
tested the perfect version of it with the teacher (nothing).

## 4. The fix

A YOLOv8 head is per-class in exactly one place: `model.22.cv3.{0,1,2}.2`, a 1×1
conv with one weight row and one bias per class. `merge_class_head.py` restores
the base's rows for classes the corpus does not teach, and `--bias-shift` bakes
a per-class confidence floor into the rows that stay (the pipeline has one
global `conf_threshold`). Seconds on the Mac, no GPU.

    python3 benchmarks/omr-labeling-survey-2026-09/merge_class_head.py \
      --ft omr-weights/round5-sweep/distill25/epoch0.pt \
      --base omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt \
      --labels-root data/user-labeled --bias-shift 0.9 \
      --keep noteheadHalfOnLine noteheadHalfInSpace noteheadWholeOnLine \
             noteheadWholeInSpace noteheadHalfOnLineSmall \
             noteheadHalfInSpaceSmall noteheadWhole \
      --out omr-weights/round5-merged/d25e0_graftprod_shift0.9.pt

⚠️ **Shift 1.5 has the best axis-2 number in the table and is the worst
checkpoint in it** — 17 half-noteheads against production's 27, exact recall
below production's. Read alone, axis 2 would have shipped it.

## 5. What to do next

1. **Decide on the candidate.** It clears all three axes. Shipping means
   repointing `DEFAULT_WEIGHTS` in `tools/omr/transcribe.py` (the router's scan
   slot only — engraved input is unaffected), backing up the old file, and
   verifying nc=208 loads and routes. Sean's explicit OK first, per the
   NEXT_ITERATION discipline.
2. **Sweep the shift.** Only 0.9 and 1.5 were measured and 0.9 is better on
   every axis; the optimum is somewhere at or below it. 0.5 and 0.7 are two more
   local runs (~15 min each, no GPU).
3. **Try grafting a better donor.** `distill25 epoch0` was the arm grafted
   because it was to hand. Fifteen other arms' epoch-0 checkpoints sit in
   `omr-weights/round5-sweep/` and any of them can donate its seven notehead
   rows; the screen costs 40 seconds each.
4. **Widen the scan benchmark.** Still 5 verified rows, all German publishers.
   The three drafted non-German rows in `works-draft-nongerman.json` still need a
   human to confirm each page's first bar and bar count. Every conclusion here
   rests on five pages.
5. **Do NOT run more training arms on this corpus.** Eleven is enough. A real
   training fix needs DeepScoresV2 back (`download_dataset.py` +
   `prepare_yolo_data.py`, tens of GB, straight onto a rented box — never onto
   the Mac), and that is a separate decision.

## 6. Rig faults, so nobody loses an hour to them again

* **v2/v3/v4 store cell images as SYMLINKS** into `benchmarks/omr-labeling-*/cells/`;
  only v1 and the round-3 versions are copies. A plain `cp -R` into a cloud
  tarball ships 101 of the 136 dense-base cells as dangling links, and
  ultralytics skips them as "corrupt image/label" inside a warning stream
  thousands of lines long. `build_cloud_tarball.sh` now uses `cp -RL`.
* **Never overwrite a running bash script** — bash re-reads by byte offset, so
  editing an arm list mid-sweep shifts every offset after the edit.
* **The 208-class space has 40 DUPLICATED NAMES.** `merge_class_head.py --keep`
  handles it; `build_rehearsal_versions.py`'s `name_to_id` does not and silently
  resolves a duplicate to its LAST index.
* **2× dense oversampling is no longer the ship's ratio.** The 896 ship got
  70/30 from 2× because it had 119 hollow cells; there are now 359, so 2× is
  43/57 hollow-MAJORITY. **6× restores 69/31.**
* `omr-weights/round4-sweep/e1_768.pt` will not load at all (truncated transfer).
