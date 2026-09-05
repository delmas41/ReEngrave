# Round 5, step 1 — the fine-tune does not suppress detection, it DELETES CLASSES

**Date:** 2026-09-04 · **Measured on:** the 5 verified rows of
`benchmarks/omr-scan-e2e-2026-09/works.json`, from the raw transcription JSONs
the round-3/4 session already produced — so this costs nothing to reproduce and
re-uses that session's exact arms.

    python3 benchmarks/omr-labeling-survey-2026-09/probe_confidence_shift.py \
        --arms prodbase e3 e5 e10 r4e5 i512e1 i512e5

## The question it was built to ask, and the answer that was not it

The round-4 handoff records every fine-tune predicting far fewer symbols than
production (3172-3364 against 4350) and treats that as *suppression*. There is a
cheaper explanation that nobody had ruled out: the pipeline thresholds at a
fixed `conf_threshold = 0.25`, and a fine-tune on a corpus whose unlabeled ink is
background pushes confidences **down**. If the ranking survived and only the
calibration moved, the fix would be one number per checkpoint, not a different
training method.

**It is not calibration.** Every fine-tuned checkpoint's median confidence is
HIGHER than production's, not lower:

| arm | raw detections | median conf | mean conf |
|---|--:|--:|--:|
| **production** | **3204** | 0.604 | 0.586 |
| round3 e3 | 806 | 0.669 | 0.615 |
| round3 e5 | 876 | 0.698 | 0.645 |
| round3 e10 | 910 | 0.692 | 0.636 |
| round4 e5 | 967 | 0.693 | 0.632 |
| imgsz512 e1 | 1365 | 0.642 | 0.587 |
| imgsz512 e5 | 806 | 0.492 | 0.484 |

The detections are gone, and what is left is held more confidently.

## What is actually gone: whole class families, at exactly zero

| class | production | e3 | e5 | e10 | r4 e5 | i512 e1 | i512 e5 |
|---|--:|--:|--:|--:|--:|--:|--:|
| noteheadBlackInSpace | 367 | 269 | 282 | 305 | 304 | 378 | 249 |
| noteheadBlackOnLine | 351 | 292 | 311 | 331 | 320 | 329 | 238 |
| noteheadHalfInSpace | 93 | 72 | 66 | 54 | 55 | 107 | 65 |
| dynamicF | 63 | 61 | 80 | 61 | 60 | 63 | 50 |
| **tie** | **249** | 0 | 0 | 0 | 0 | 0 | 0 |
| **slur** | **184** | 0 | 0 | 0 | 0 | 0 | 0 |
| **augmentationDot** | **150** | 0 | 0 | 0 | 0 | 0 | 0 |
| **accidentalFlat** | **80** | 0 | 0 | 0 | 0 | 0 | 0 |
| **restWhole** | **396** | 0 | 0 | 0 | 0 | 0 | 0 |
| **beam** | **188** | 0 | 0 | 0 | 0 | 0 | 0 |
| **ledgerLine** | **288** | 5 | 0 | 0 | 14 | 149 | 0 |
| staff | 89 | 0 | 0 | 0 | 0 | 0 | 0 |
| timeSig4 | 51 | 5 | 7 | 5 | 9 | 30 | 0 |

Noteheads and dynamics — the two families the labeling campaign actually
covered — survive at 80-100 %. Everything else is **zero**, not reduced. This is
catastrophic forgetting of class families, and it is the same wall the clef
fine-tune hit (dense noteheads 2506 -> 114) and the reason v5/v6 are parked.

It also explains why round 4's data work could not move the number: the campaign
stamps say what a pass ever LOOKED for — 603 cells swept for hollow noteheads,
409 for rests+accidentals, 255 for grace, 46 for clefs, and only 109 + 55 under
a rich or full palette. On most cells a slur, a tie, a beam or a ledger line is
**background**, and the loss teaches exactly that. Completing the labels within
the classes a pass covers cannot reach it.

⚠️ **Not all of the 3204 is signal — but less of it is noise than the first
reading of this table assumed.** `staff` (89) is a class project policy
deliberately leaves to classical CV, so a checkpoint reading fewer is not worse
for it. `restWhole` at 396 looked like the same case — the round-2 audit names
`restWhole` on slur arcs as a production false-positive mode, and 396 whole
rests over five pages reads as absurd — and it was **exempted from the gate on
that reasoning before anyone counted**. Counted, it is wrong in the other
direction. The five truth files carry **801 resting bars** (194 / 194 / 18 / 99
/ 296) and production reads **108 / 88 / 11 / 96 / 93** — under the printed
count on every page, never over. Whole rests are a real loss here and the
exemption is gone; `staff` is the only one left.

The rows the handoff's own element-count table already pinned against truth
carry the rest: **tie (truth 227, production 58, fine-tune 0), slur (202 / 147 /
0), accidental (85 / 79 / 0)**.

## ⚠️ Two of the dead classes are CONSUMED by the pipeline, against the
## labeling policy's assumption

`CLAUDE.md` tells a labeler to skip staff lines, stems and beams because
classical CV finds them and a human cannot bbox a thin line. Both halves are
true. What the instruction does not say, and what is false, is that they may
therefore train as background:

* `rhythm.resolve_rhythms_for_cell` keeps a **YOLO `beam`** wherever no CV beam
  overlaps its x-range — the "kept" rule measured at pooled 0.1917 -> 0.1861,
  chosen over replace-outright precisely because CV misses strokes.
* `transcribe`'s ledger-ladder arbitration reads **`ledgerLine` detections**
  directly (`det.get("class") != "ledgerLine"`) — the completeness rule worth
  pooled 0.1506 -> 0.1431 and Beethoven notes 81/81.

Production reads 188 beams and 288 ledger lines on these pages; the round-4
checkpoint reads 0 and 14. **On every candidate checkpoint measured so far, both
of those rules are dead** — silently, because neither has a test that fails when
its input vanishes. A human cannot draw them; the teacher can, which is what
`build_rehearsal_versions.py` is for.

## What this makes the next experiment

Not more labels. The lever is a training method that keeps the base's class
space alive — freezing, a much lower learning rate, or rehearsal — and rehearsal
is the one this corpus can actually supply, because the teacher can label every
class on the images we already have. See `build_rehearsal_versions.py` and
`run_method_sweep.sh`.
