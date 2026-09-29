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

## Known rig quirk (observed during the actual run, 2026-09-29) -- INTERMITTENT, corrected below

Arm A's training crashed on the LAST batch of the 5th (last) epoch with
`RuntimeError: Trying to create tensor with negative dimension -1: [5, -1, 5]`
inside `ultralytics/utils/loss.py`'s target-preprocessing (`get_assigned_targets_and_loss`
-> `preprocess`), plausibly triggered by the final PARTIAL batch (batch size
5, not 16 -- none of these corpora's train-image counts divide evenly by 16).
**Correction: this is NOT systematic.** An earlier version of this note
claimed it "reproduced identically on arm B" -- that was written before arm
B's run had actually finished and was wrong. Arm B in fact completed all 5
epochs cleanly (`epoch0.pt` through `epoch4.pt` all present, no crash). So
the failure mode is real but intermittent (an MPS/ultralytics race or
memory-pressure issue, not a deterministic property of a partial last
batch), and whether a given arm loses its epoch4 checkpoint has to be
checked per arm rather than assumed. The driver's
`|| log "!! TRAINING FAILED"` guard (added after arm A first hit this)
catches it either way and moves on to the next arm rather than aborting the
whole run -- an arm that DOES hit it ends up with epoch0.pt-epoch3.pt (4 of
5), which still includes `epoch0`, round 6's own primary reference point and
what gets grafted for the composability check, so the decision table is not
blocked either way. Check `find runs -path "*<arm>*/weights/epoch4.pt"` per
arm before trusting a 5-point trajectory for it.

## What this does NOT do

- Does not touch `omr-weights/` or `data/user-labeled/` — every corpus is
  built fresh under `data/rest-exp-*` (gitignored, not committed; only the
  building SCRIPTS and small manifests are).
- Does not re-run the converter on any existing labeled version.
- Does not run a whole-work export (Sean, 2026-09-28: no whole-work runs
  without asking first) — every eval here is on cell PNGs already cut.

## Verification (2026-09-29, before anyone trusts the results table)

Three things were checked, per the coordinator's request, before reading
`rest_experiment_results.json` as evidence of anything. **No new arm was
retrained; two small, targeted diagnostic checks were run** (both read-only
probes on already-trained checkpoints, plus one short retrain used only to
rule out a specific hypothesis in Q2 — see below).

### 1. A and B are identical to 2+ decimals at every epoch — is it a wiring bug?

**No.** Checked three independent ways:

- **Each checkpoint's own embedded `train_args`** records the catalog it was
  actually trained on: `torch.load(...)['train_args']['data']` reads
  `cat-rest-exp-A/catalog.yaml` for A's checkpoints and
  `cat-rest-exp-B/catalog.yaml` for B's — two different files, and
  `cat-rest-exp-B/*` symlinks resolve to `data/rest-exp-B-completed/`, not
  `data/rest-exp-A-baseline/` (confirmed by `readlink`).
- **The label files on disk genuinely differ.** `diff -rq
  data/rest-exp-A-baseline data/rest-exp-B-completed` shows exactly 18
  label files differing (covering the 22 logged additions — some cells
  received more than one), each containing precisely the extra line
  `additions.json` says it should.
- **The checkpoint weights genuinely differ.** `epoch0.pt` for A and B have
  different md5s, different file sizes are equal (88,043,444 bytes, expected
  — same architecture), and a direct `state_dict` tensor comparison shows 42
  of 595 tensors differ, by up to 0.0156 absolute. **Raw per-cell inference
  also differs**: re-running both checkpoints on all 35 held-out cells and
  diffing the raw detection lists (class, confidence to 6 decimals, center
  position) shows 30 of 35 cells differ at the confidence/sub-pixel level —
  it is simply that none of those differences (typically 0.001–0.003
  confidence, <1px position) are large enough to cross the 0.25 threshold or
  move a box outside the 0.6-diagonal match radius on THIS specific 35-cell
  set, so the discretized precision/recall/detection-count come out
  bit-identical by coincidence of scale, not by a wiring fault.

**A genuinely more interesting and more concerning finding fell out of this
check**: **D's checkpoint (trained on `data/specialist-hollow`, which
contains ZERO rest-class labels at all) also scores identically to A/B on
rests** (61 detections, P=0.721, R=0.800 — see the table in §3). Worse,
**`D-composite`'s rest numbers also match D/A/B, not production's** — but
`D-composite` is supposed to have its rest-class rows RESTORED FROM
PRODUCTION UNCHANGED (`compose_specialists.sh`'s `--base` = production
for every graft), so its rest detections should be indistinguishable from
raw production (78 preds), not from A/D's trained checkpoints (61 preds).
They are not. The explanation: **`merge_class_head.py`'s `CLS_LAYERS`
restores only the per-class 1×1 classification convolutions
(`model.22.cv3.*.2`) — it never restores the SHARED box-regression head
(`model.22.cv2.*`) or the DFL layer**, which are common to every class.
Since `freeze=22` leaves the WHOLE of `model.22` trainable (not just the
classification rows), a specialist's own training perturbs box-regression
for every class, including ones its corpus never mentions — and grafting
"restores" that class's confidence scoring but not its box geometry. This
is a pre-existing limitation of the shared graft tooling (used unmodified
by rounds 5/6 too, not something new here) that has not been measured
before; it means every composability check in this whole benchmark line
likely understates a restored class's true fidelity to its pre-graft
behavior. Flagging as a follow-up, not fixing here (no roadmap item for it
yet, and fixing `merge_class_head.py` is out of this experiment's scope).

### 2. Arm A did not collapse — why not, versus round 6's "12 → 0"?

**Recipe match, checked line for line against `run_specialist_sweep.sh`'s
`specialist()`:** same base checkpoint
(`deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`), `freeze=22`, 5 epochs,
imgsz 896, batch 16, `save_period=1`, `fliplr=flipud=hsv_h=hsv_s=0`. The
auto-optimizer picked `AdamW(lr=4.7e-05, momentum=0.9)` — the SAME lr
`ROUND5_METHOD_2026-09-04.md` itself records for this exact recipe shape,
confirming the lr formula (which depends only on nc=208 and batch) is not a
variable here. **Corpus population matches bit-for-bit**: rebuilding
`data/specialist-rests` fresh in this worktree gives 424 cells / 226 boxes,
identical to round 6's own reported numbers and to `UNBOXED-AUDIT.md`'s
independent reproduction.

**Reproduced round 6's OWN measurement method exactly** (`probe_class_inventory.py`
on the 30 fixed dense cells at `benchmarks/omr-phase2.5/cells.json`, raw
detection counts, no ground truth — this is the actual instrument behind
round 6's "12 → 0" table, not a re-interpretation): production reads
rest8th=12, restQuarter=7. **Arm A's raw epoch0 and epoch3 checkpoints both
read rest8th=12, restQuarter=7 — completely unchanged.** The GRAFTED
composite (matching round 6's literal "graft onto production, before →
after" comparison) reads the same: 12, 7. **Ruled out held-out-cell removal
as the cause**: retrained round 6's recipe on the FULL, un-reduced 424-cell
corpus (no held-out split at all — this is the one short retrain run for
this verification, killed by the same intermittent MPS crash at epoch 3 but
not before saving `epoch0.pt`/`epoch1.pt`) and measured it the same way:
rest8th=12, restQuarter=7, unchanged, at both epochs. **The held-out split
is not the explanation — full round-6 corpus, full round-6 recipe, round
6's own instrument, and rest8th/restQuarter do not move.**

What differs and could not be controlled for: **device**. Round 6 ran on a
rented vast.ai RTX 4090 (CUDA); every run in this experiment ran on this
Mac (Apple M1 Max, MPS). No CUDA box was rented for this check. It is also
worth stating plainly: round 6's own raw probe JSON for this exact number
was never committed — `ROUND6_SPECIALISTS_2026-09-04.md` §6 says the box
was destroyed the same day — so "12 → 0" rests on that document's prose
alone and cannot be independently re-derived from anything on disk.
`UNBOXED-AUDIT.md` already found a measurement artifact (a ~2x inflation)
in the ADJACENT claim from the same round; a further one in the headline
collapse number itself cannot be ruled out from here, only flagged as
unverifiable rather than confirmed.

### 3. Production baseline and D's numbers, same 35 held-out cells, same eval

| arm | n_pred | tp (vs Sean) | precision | recall | F1 |
|---|--:|--:|--:|--:|--:|
| **production** | 78 | 50 | 0.641 | **0.909** | 0.752 |
| A (epoch0) | 61 | 44 | 0.721 | 0.800 | 0.759 |
| B (epoch0) | 61 | 44 | 0.721 | 0.800 | 0.759 |
| C (epoch0) | 62 | 45 | 0.726 | 0.818 | 0.769 |
| D (epoch0, hollow control) | 61 | 44 | 0.721 | 0.800 | 0.759 |
| E (epoch0, oversampled) | 57 | 44 | 0.772 | 0.800 | **0.786** |
| A-composite | 50 | 40 | 0.800 | 0.727 | 0.762 |
| D-composite | 61 | 44 | 0.721 | 0.800 | 0.759 |

**No arm beats production on recall** — every specialist (including D,
which never saw a rest label) reads fewer rests than production on this
held-out set. **E has the best F1 of any raw checkpoint** (0.786, precision
up without recall cost relative to A/B), a small positive signal for the
oversampling lever, but still below production's recall. **D matches A/B/D-composite
essentially exactly** — the same finding as §1: whatever moves the
rest-class rows away from production's behavior under this recipe does not
appear to depend on whether the corpus contains rest labels at all.

Full per-epoch numbers for every arm: `rest_experiment_results.json`
(tags `production`, `D-epoch0`, `D-composite` added by this verification
pass — everything else was already there from the main run).
