# Why does a rest specialist delete rests? — the experiment

**Date:** 2026-09-29 · **Branch:** `claude/rest-specialist-experiment` ·
**Sean's instruction (verbatim):** *"set it up the experiment. I want to know
for certain why these are not working. If I need to relabel I will. If we
need to double check the process let's do it. The whole point is to get as
accurate as we can. We have spent months on this and I don't want to miss
out on ways of improving because the tests we were basing our decisions off
of were bad."*

Round 6 (`ROUND6_SPECIALISTS_2026-09-04.md`) trained a rest specialist on
`data/specialist-rests` (round 6's own corpus, 424 cells, 226 boxes, built by
`build_specialist_versions.py`) and it deleted its own class
(`rest8th 12 -> 0, restQuarter 7 -> 0`). Round 6 blamed unboxed labels: the
teacher sees 41% more rest instances in that corpus than the humans boxed.
Today's audit (`UNBOXED-AUDIT.md`) found that 41% is inflated ~2x by a bulk
arithmetic bug and by the teacher's own documented false-positive mode
(`restWhole`/`restHBar` on staff-line/slur/beam ink) — the TRUE unboxed rate
is closer to 19%. Sean's question follows directly: if the corpus is only
~19% incomplete, not 41%, is "the labels" still the right explanation for
the collapse — and can we relabel our way out, or is something else (the
`dsv2-rehearsal` FINDINGS.md's "optimization dynamics delete minority
classes even when they ARE labeled, at volume") the real cause?

## The arms

All five train from `deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`
(production), `freeze=22` (head-only — round 6's OWN rests-family table was
measured this way: "rests (e0, frz) | rest8th 12 -> 0, restQuarter 7 -> 0"),
5 epochs, imgsz 896, batch 16, `--device mps`, `save_period=1`, exactly
`run_specialist_sweep.sh`'s `specialist()` recipe. A fixed, seeded 35-cell
held-out split (`held_out_rests.json`, drawn from round 6's own 152
rest-positive cells) is excluded from every training corpus below and used
only for scoring (`held_out_truth.json`, `eval_rest_arm.py`).

| arm | corpus | question it answers |
|---|---|---|
| **A baseline** | round 6's own corpus minus the held-out cells | control — must collapse, or this rig differs from round 6's |
| **B completed** | A + every high-confidence (conf≥0.5), non-FP-mode (not restWhole/restHBar) unmatched teacher rest, added as a label | if completing the labels fixes it, the cause WAS the labels |
| **C painted** | A's cells/labels unchanged; every unmatched teacher rest region (any class, any confidence) painted to paper color | isolates "ambiguous ink as a forced negative" from "ambiguous ink as a forced positive" — if C ALSO survives, the mere presence of unresolved ink was enough to cause the collapse, independent of which label a human would give it |
| **D hollow** | `data/specialist-hollow`, unmodified (round 5/6's own positive control) | rig-validity control — must survive, or the rig itself is broken |
| **E oversampled** | B, rest-positive train cells duplicated x4 | tests the rehearsal FINDINGS.md's own reading directly: if B still collapses but E doesn't, the cause was classes starved relative to background volume, not missing labels |

**Why B/C/E and not A gets a `--min-labels`-style curation, and why C paints
rather than deletes the cell:** deleting an ambiguous cell would shrink the
corpus and confound "fewer cells" with "cleaner cells." Painting keeps every
cell and every OTHER label in it identical to A; only the disputed pixels
change.

## Readout (per arm, on the 35 held-out cells)

1. **Rest detections at conf 0.25**, precision/recall/F1 against two truth
   sets (`eval_rest_arm.py`, `rest_experiment_results.json`):
   - `vs_sean_*`: exactly Sean's own boxes.
   - `vs_corrected_*`: Sean's boxes + the same high-confidence/non-FP-mode
     teacher additions arm B uses (an AUTOMATED proxy for "genuine", not a
     re-adjudication by Sean — see `HOW-THE-TESTS-JUDGE.md` and the module
     docstring in `rest_experiment_lib.py`).
   - Both broken out by `{restWhole, restHBar}` vs the other four classes,
     because the audit found those two behave nothing like the rest of the
     family.
   - Every 5 epochs (0-4), so a monotone-collapse trajectory (like the
     rehearsal FINDINGS.md's) is visible, not just the endpoint.
2. **Composability**: epoch0 of each arm's rest rows grafted onto production
   (`compose_specialists.sh`, bias-shift 0.9 — round 5's convention), scored
   two ways: the composite's rest detections on the same held-out cells
   (would this actually ship better than production), and
   `probe_class_inventory.py` confirming every NON-rest class is unchanged
   from production on the 30-cell screen (`benchmarks/omr-phase2.5/cells`) —
   the mechanism only matters if grafting doesn't break something else.
3. **Visual check (Sean, 2026-09-29):** two contact sheets under
   `out/rest-experiment/` — see "Visual-check sheets" below.

## Decision table

| A | B | C | D | E | reading |
|---|---|---|---|---|---|
| collapses | survives | — | survives | — | labels were the cause; relabeling (completing) is worth Sean's time |
| collapses | collapses | collapses | survives | survives | labels are NOT the cause; the dynamics fix (oversampling/rehearsal-style) is the lever |
| collapses | collapses | survives | survives | — | the mere presence of unresolved ink drove the collapse, independent of the correct label — points at a different fix (remove ambiguity, not add labels) |
| survives | — | — | — | — | **rig is broken** — this experiment differs from round 6's somehow; stop and find out why before trusting anything else here |
| — | — | — | collapses | — | **rig is broken** — the positive control failed; nothing else here is trustworthy until this is understood |

## Visual-check sheets (Sean, 2026-09-29: "I will want to visual check some
of these also to verify")

- `out/rest-experiment/crop-b-additions/` — ~16 crops of the teacher rest
  boxes arm B is about to add as labels, stratified by class and confidence,
  orange box drawn, staff shaded. Question: real rest, or teacher FP?
- `out/rest-experiment/crop-c-painted/` — ~8 before/after pairs of regions
  arm C erases. Question: correctly-erased noise, or did painting eat
  something real?
- `out/rest-experiment/crop-preds-rest-exp-<arm>-epoch0/` (one per arm,
  A/B/C/E) — ~12 held-out cells, that arm's epoch0 detections vs Sean's
  boxes: GREEN matched, RED detection with no nearby box, BLUE box with no
  nearby detection.

Every sheet ships a `manifest.json` with `VERDICT_none_yet: null` per crop —
nothing here has been adjudicated yet.

## Running it

```
nohup benchmarks/omr-labeling-survey-2026-09/run_rest_experiment.sh \
    > benchmarks/omr-labeling-survey-2026-09/out/rest-experiment/run.log 2>&1 &
```

Reads: `rest_experiment_results.json` (per-arm, per-epoch precision/recall),
`out/rest-experiment/composability_screen.txt` (non-rest classes unchanged?),
`out/rest-experiment/composite-<arm>-composite` rows inside
`rest_experiment_results.json` (the deployable-graft number), and the crop
sheets above.

## Known rig quirk (observed during the actual run, 2026-09-29)

Every arm's training crashes on the LAST batch of the 5th (last) epoch with
`RuntimeError: Trying to create tensor with negative dimension -1: [5, -1, 5]`
inside `ultralytics/utils/loss.py`'s target-preprocessing (`get_assigned_targets_and_loss`
-> `preprocess`), triggered by the final PARTIAL batch (batch size 5, not 16 --
none of these corpora's train-image counts divide evenly by 16). This is an
ultralytics/MPS library issue, not a property of any specific corpus arm --
arm A hit it first and reproduced identically on arm B. The driver's
`|| log "!! TRAINING FAILED"` guard (added after this was first hit) catches
it and moves on to the next arm rather than aborting the whole run.

**Effect: every arm ends up with epoch0.pt through epoch3.pt (4 of the
planned 5 checkpoints), missing only the LAST one (epoch4.pt).** This does
NOT block the experiment's decision table -- `epoch0` is round 6's own
primary reference point (least-collapsed, what its "e0" columns report) and
is what gets grafted for the composability check. The per-epoch trajectory
in `rest_experiment_results.json` will simply have 4 points instead of 5 for
every arm, which is still enough to see whether a collapse is monotone.

## What this does NOT do

- Does not touch `omr-weights/` or `data/user-labeled/` — every corpus is
  built fresh under `data/rest-exp-*` (gitignored, not committed; only the
  building SCRIPTS and small manifests are).
- Does not re-run the converter on any existing labeled version.
- Does not run a whole-work export (Sean, 2026-09-28: no whole-work runs
  without asking first) — every eval here is on cell PNGs already cut.
