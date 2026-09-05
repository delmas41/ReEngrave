# Round 7 — the arc specialists, trained properly, and why the path closes

2026-09-04. Follows the arcs adjudication (21779507): Sean judged all 268
teacher arc candidates over 126 cells — 260 fake (staff-above/below bleed at
cell edges, jagged scanned staff lines), 5 real, plus 2 drawn. The corpora
were nearly honest all along; the round-6 "residue" measured the teacher's
hallucinations, not missing labels.

## What was trained

Tie and slur single-class specialists on the adjudicated corpora
(`data/specialist-{ties,slurs}-v2`: 107 / 69 positives, 164 cells each, every
negative human-certified), from production `hollow-graft-shift09` with
`freeze: 22` — so the rows drop into production bit-exactly
(`transplant_class_rows.py`, the conservative direction; the standard
`merge_class_head` direction was REJECTED by the inventory probe: it carries
the specialist's drifted shared head convs and costs the ledgerLine canary
11 -> 4).

Two training regimes, because the first was a silent null:

| regime | tie-row |dW|/|W| | outcome |
|---|--:|---|
| 5 ep, auto-LR (~5e-5), warmup 3 | 0.002-0.004 | rows did not move; composite == production on every probe count |
| 60 ep, SGD, no warmup, RTX 4090 | 0.88-1.00 | rows moved — see below |

⚠️ **A frozen specialist at ultralytics defaults does not collapse — and does
not learn.** Warmup ate the ~90 steps and auto-LR is sized for full
fine-tunes. Check |dW| on the target rows before believing any head-only run
did anything.

## The probe that decides (in-sample, which is the damning part)

Tie/slur detections scored against the adjudicated human boxes on the 126
training cells themselves (`probe_arcs_vs_human.py`, IoU 0.3, conf 0.25):

| checkpoint | dets | recall | precision | kind acc |
|---|--:|--:|--:|--:|
| production | 625 | 0.824 | 0.232 | 0.717 |
| composite lr0.01 | 4184 | 0.875 | **0.037** | 0.747 |
| composite lr0.001 | 442 | **0.494** | 0.197 | 0.759 |

lr0.01 buys +9 TP with 3550 extra false arcs; lr0.001 halves recall for no
precision. **On their own training data.** No gate run is justified — there
is no winner, and the 11-row scan gate on production would re-measure the
widened baseline (0.8535 / 35817, WIDENED_BASELINE_2026-09-04.md).

## Why this closes the path (the pincer)

A frozen-head specialist is a linear readout of production's features. If a
linear readout trained on human-certified positives and negatives cannot
separate real arcs from edge-bleed and staff-line jags, **the features do not
separate them**. Fixing features means training the trunk — which rounds 3-6
measured deleting whole classes under every method tried. Head-only cannot
learn it; full training destroys the rest. With 176 positives, both jaws are
measured.

## What stands after the round

- 260 human-certified hard negatives (v23-2026-09-04-arcs-reconcile) — usable
  by any future training that solves deletion, and by any non-YOLO arc reader
  as a test set.
- The residue-table correction: `build_family_queue` residues are TEACHER
  measurements. Adjudicate before believing one.
- `transplant_class_rows.py` — the conservative graft direction, canary-clean.
- **The likeliest live lever for arcs is classical CV, not the detector.**
  Production's arc precision is 0.232 on scan cells; the project's repeated
  win is geometry over learning exactly where YOLO is structurally weak
  (stems/beams in Phase 4f — "YOLO bounding boxes are structurally bad at
  thin lines" — and a slur IS a thin curved line; clefs, key and time
  signatures all went geometric). An arc tracer + the 260 adjudicated fakes
  as its false-positive gauntlet is the experiment this round hands to the
  next one.
