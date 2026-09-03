# The shipping run — production-representative hollow fine-tune, re-gated

**Date:** 2026-09-03 · **Machine:** Apple M1 Max, 64 GB, MPS (no CUDA) ·
**Status:** COMPLETE — decision **SHIP `epoch0.pt`** (imgsz-896 hollow fine-tune),
committed path-scoped and **not pushed**; Sean's review is the final gate.

Follows `GATE_RESULTS.md`, which PASSED the labeling gate (hollow scan labels
lift half-note detection 8 → 25 and duration recall 0.388 → 0.456, cleanly and
across publishers) but found the imgsz-640 fine-tune **recipe** narrows dense
detection (0.941 → 0.818), reproduced by a pure-dense control (→ 0.841) and
scaling with epochs (control 0.973 @5ep → 0.841 @15ep). The gate's
recommendation: re-gate at **production imgsz (2048) with a higher dense ratio**
before admitting v8, and ship the weights from *that* run.

This document is that run.

---

## Step 1 — the mix (higher dense ratio than the gate)

Built in an isolated experiment root (`ship-catalog/`, symlinked version dirs)
so the committed `data/user-labeled/catalog.yaml` and `catalog-versions.txt`
stay untouched — membership remains Sean's decision after this verdict.

**Members:** v1–v4 (dense base) + v7 + v8 (hollow). **v5/v6 clef cells
EXCLUDED** (documented density-narrowing risk). **nc = 208** (custom
barline/textDynamic boxes capped into `_nc208/`) — no head reset, no
`--allow-nc-expansion`. Transferred 595/595 items from the production
checkpoint.

**Higher dense ratio via 2× oversampling of the dense base.** The gate's mix was
**48 % hollow cells / 25 % hollow boxes** — the survey design wants scan cells a
*clearer minority*. DSv2 replay is unavailable (no prepared DSv2 dataset on this
machine), so the dense base is up-weighted by duplicating its train-split lines
(verified: ultralytics `get_img_files` keeps duplicates — `sorted()`, no
`set()`, so the 136 dense train paths load exactly 2×). The honest per-version
val split is left untouched (a clean, non-oversampled monitor).

| mix (TRAIN split) | dense cells | hollow cells | dense boxes | hollow boxes |
|---|--:|--:|--:|--:|
| gate (1× dense) | 136 (53 %) | 119 (47 %) | 1057 (75 %) | 350 (25 %) |
| **ship (2× dense)** | **272 (70 %)** | **119 (30 %)** | **2114 (86 %)** | **350 (14 %)** |

Hollow drops to a clear **30 % of cells / 14 % of boxes** — the "clearer
minority" the survey design asked for — while every hollow cell is still seen
each epoch. Train images per epoch: 391 (255 base + 136 dense duplicated).

## Step 2 — imgsz feasibility on this M1 Max (the binding constraint)

The gate's recipe fix is **training imgsz** (640 → production 2048). But
YOLOv8l at high imgsz is impractical on this machine: ultralytics 8.4.50's
task-aligned assigner uses a boolean-mask `nonzero` that **falls back to CPU on
MPS/macOS 14** (`tal.py:195`), and that per-step CPU round-trip explodes with
the anchor count (∝ imgsz²). Probed each candidate (2× dense mix, from
production weights, batch chosen to fit 64 GB):

| imgsz | batch | GPU mem | steady s/it | est. epoch | 10-epoch wall-clock | verdict |
|---|--:|--:|--:|--:|--:|---|
| **2048** | 4 | 49.3 G | ~330 | ~9.0 h | ~90 h | **infeasible** (near mem ceiling → swap) |
| **1280** | 8 | ~40 G | ~196 | ~2.5 h | ~25 h | **infeasible** |
| **896** | 16 | ~38 G | ~75–99 | ~35–45 min | ~6–8 h | **feasible → chosen** |
| 640 (gate) | 16 | — | ~4–37 | ~1–10 min | ~1 h | gate baseline |

**True production-imgsz-2048 wants a cloud GPU** — exactly as the repo already
flags for the RTMDet/yolov8x escalation, and the gate anticipated. On this
machine the highest imgsz that finishes reasonably is **896** (1.96× the pixels
of the gate's 640 — a real resolution step toward production, which should
retain more small-notehead detail and hold dense recall better than 640, though
short of what 2048 would).

## Step 3 — the fine-tune (best feasible config)

    from production weights (deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt)
    --epochs 10 --imgsz 896 --batch 16 --device mps --patience 20
    --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0   (music-aware aug)
    --extra-kwargs '{"save_period": 1}'          (PER-EPOCH checkpoints)

**Two density-hold levers, both feasible here, are exercised at once:** the
higher dense ratio (Step 1) and **early stopping by checkpoint** — the gate
showed the narrowing scales with epochs (control 0.973 @5 → 0.841 @15), so
`save_period=1` lets the re-gate pick the epoch where dense recall still holds
*and* hollow has risen, instead of guessing. Weights are gitignored experiment
artifacts under `runs/ship-896-run/weights/`; production weights are never
touched.

**Run stopped after epoch 3** once the re-gate (below) showed the clear-win
checkpoint is **epoch 1** and that dense recall falls monotonically after it —
so no later checkpoint can be a clear win, and the ~4 remaining hours were
better spent on the required engraved-benchmark and generalization checks.
Per-epoch pace ~25–30 min (mild throttle, not the 10× the gate saw at 640).
The internal val (catalog's own 52-cell / 208-class split) is a noisy proxy —
`val/box_loss` fell steadily (2.86 → 2.47) while `val_mAP50` stayed ~0.005–0.01
(tiny multi-class val during LR warmup); the real signal is the two re-gate
axes below, on external ground truth.

Checkpoints saved (`save_period=1`): `epoch0.pt` (after epoch 1) …
`epoch2.pt` (after epoch 3). **`epoch0.pt` is the ship candidate.**

## Step 4a — density-collapse re-gate (forgetting)

`wtc_forgetting_eval.py`, 18 dense Beethoven orchestral cells, imgsz 1280,
center-match, **--device cpu**. Production baseline reproduced on this machine.

| model | epoch | notehead recall | overall recall | precision | F1 |
|---|--:|--:|--:|--:|--:|
| **production** | — | **207/220 = 0.941** | 0.935 | 0.443 | 0.601 |
| **epoch0.pt (SHIP)** | 1 | **207/220 = 0.941** | 0.931 | 0.470 | 0.625 |
| epoch1.pt | 2 | 196/220 = 0.891 | 0.874 | 0.582 | 0.699 |
| epoch2.pt | 3 | 193/220 = 0.877 | 0.861 | 0.659 | 0.747 |

**Epoch 1 holds dense notehead recall at exactly 0.941 — zero forgetting**
(Δ 0.000 vs production, far inside the ~2–3 pt ship threshold), while precision
rises (0.443 → 0.470). Recall then narrows with epochs (0.941 → 0.891 → 0.877),
the same epoch-scaling the gate's control showed — which is precisely why the
`save_period=1` early checkpoint is the shipping lever. Compare the gate's
imgsz-640 **treatment@12 at 0.818**: the higher imgsz (896) + higher dense ratio
+ early stop hold **0.941 vs 0.818** — the density collapse the gate diagnosed
as recipe-level is *avoided*.

## Step 4b — hollow payoff re-gate

Beethoven 5 p.1 scan (held-out page/movement), plain `transcribe` (no dossier),
scored vs the Gradus reference (`eval_first_run.py`), **OMR_DEVICE=cpu**.

| model | epoch | half-notes | hollow_total | black | with_duration R | exact R | step R |
|---|--:|--:|--:|--:|--:|--:|--:|
| **production** | — | 8 | 14 | 120 | 0.388 | 0.599 | 0.701 |
| **epoch0.pt (SHIP)** | 1 | **27** | **30** | 79 | **0.435** | 0.565 | 0.646 |
| epoch1.pt | 2 | 36 | 38 | 72 | **0.483** | 0.524 | — |
| epoch2.pt | 3 | 30 | 31 | 69 | 0.408 | 0.429 | — |

**Epoch 1: half-note detections 8 → 27, hollow_total 14 → 30, with_duration
recall 0.388 → 0.435 (+12 % rel)** — the strongest-evidenced gap in the project
(68 printed half notes read as 8) moves, and moves as much as the gate's
treatment@12 (half 25, with_dur 0.456) but **without** the dense collapse.
production's ~40 phantom black-notehead over-detections are also stripped
(120 → 79). Exact recall dips slightly (0.599 → 0.565) — the same
black-notehead-stripping trade the gate recorded, milder here. clefs 11/12,
measures 16/16 unchanged.

**The Pareto frontier across checkpoints** (dense recall vs hollow with_duration):
epoch 1 is the **maximum dense-hold** point (0.941, with_dur 0.435); epoch 2 is
the **maximum hollow** point (with_dur 0.483, half 36) but costs 5 dense points
(0.891) → a *tradeoff*, not a clear win; epoch 3 is dominated. So **epoch 1 is
the unique clear-win checkpoint.** (epoch 2 is noted as an alternative for a
deliberate hollow-for-dense trade, should Sean want it — but it is not a clear
win and is not shipped from this run.)

### Held-out publisher — Mahler 5 (Peters scan, p.172), UNSCORED

| model | half-notes | whole-notes | hollow_total | black |
|---|--:|--:|--:|--:|
| production | 36 | 13 | 49 | 214 |
| epoch0.pt | 31 | 1 | 32 | 189 |

⚠️ **Reported honestly, not spun.** On this dense Peters page epoch0 detects
*fewer* hollow than production — the opposite direction from beet5-p1. There is
no reference to score against here, so which reading is right is unknown. It is
consistent with the **over-detection-stripping** epoch0 shows on the *scored*
pages (beet5-p1 black 120→79 with duration recall UP; forgetting-set FP dropped
with notehead recall HELD at 0.941 — i.e. epoch0 drops false detections, not
real ones), rather than with missing real notes — but unscored, this is a
caveat, not evidence of gain. The reliable held-out evidence is the **scored**
beet5-p1 (§4b) plus the **scored** engraved mahler-sym5-mvt1, which *improved*
(−0.0042, §4c).

## Step 4c — engraved-benchmark check

`orchestral_eval --omr-ned`, 11 works, `--no-direction-text` (isolates the YOLO
weights and skips the slow Surya rung; recorded no-direction-text baseline
**0.13988 / 2915 edits**). The direction-text reader is OCR on word crops and is
only **second-order** dependent on the detector (the crops it reads are what's
left after note/symbol detections are subtracted), so the no-direction-text
comparison captures essentially all of the weights' effect; the direction-text
headline (0.1306) was **not** directly re-measured here — see the follow-up note
in §5. Run on **MPS** (GPU free after training stopped;
matches the recorded baseline's device — `transcribe` uses device=auto=MPS; the
CPU protocol was for training-contention avoidance, now moot). Production
re-run on THIS setup to remove any device/harness offset from the comparison.

| model | pooled OMR-NED | edits |
|---|--:|--:|
| recorded baseline (main) | 0.13988 | 2915 |
| **production (this setup)** | **0.1399** | 2915 |
| **epoch0.pt (SHIP)** | **0.1421** | 2960 |

Production reproduces the recorded figure **exactly** (0.1399 ≈ 0.13988) — the
harness/device is validated, so the epoch0 delta is the *weights*, not the
setup: **+0.0022 pooled (+1.6 % rel, +45 edits)**. epoch0 note recall per work
is intact (beethoven-sym5 **81/81 = 1.000**, brahms-sym1 0.956, mahler 0.917).

**The regression is net-neutral and concentrated, not a uniform clean-page
collapse.** Per-work Δ (epoch0 − prod):

| better with epoch0 | Δ | | worse with epoch0 | Δ |
|---|--:|---|---|--:|
| mahler-sym5 | −0.0042 | | **mozart-sym41** | **+0.0146** |
| beethoven-sym5 | −0.0028 | | tchaikovsky-sym6 | +0.0056 |
| dvorak-sym9 | −0.0019 | | brahms-sym4 | +0.0054 |
| mozart-sym40 | −0.0016 | | tchaikovsky-sym4 | +0.0018 |
| brahms-sym1 | −0.0005 | | bruckner-sym5 | +0.0006 |
| beethoven-sym3 | −0.0005 | | | |

**6 of 11 works IMPROVE**; the net +0.0022 is dominated by a single work,
**mozart-sym41 (+0.0146**, "wrong note" — the hollow-learning shifted a few
note reads on that sparse classical engraving). Not a material uniform
regression of the headline — but the mozart-sym41 single-work wobble is a real
side-effect and is flagged for review.

## Step 5 — decision: **SHIP `epoch0.pt`** (as a reviewable proposal, not pushed)

**epoch0.pt meets the clear-win criteria on both re-gate axes, and the engraved
benchmark did not materially regress:**

| axis | production | epoch0.pt | verdict |
|---|--:|--:|---|
| dense notehead recall (forgetting) | 0.941 | **0.941** | HELD (Δ 0.000, ≪ 2–3 pt threshold) |
| scanned half-note detection (beet5-p1) | 8 | **27** | UP |
| scanned duration recall (beet5-p1) | 0.388 | **0.435** | UP (+12 % rel) |
| engraved OMR-NED, 11 works (this setup) | 0.1399 | 0.1421 | +0.0022 net (6/11 works improve; not material) |

This is the outcome the gate asked for but its imgsz-640 recipe could not
deliver: the density collapse (gate treatment@12 = 0.818) is **avoided** —
dense recall is held at production's 0.941 — while the #1 project gap (68
printed half notes read as 8) moves (8 → 27, duration recall +12 %). The lever
that made it possible on this hardware was **not** the unreachable imgsz-2048,
but **imgsz-896 (feasible ceiling) + a higher dense ratio + the early-epoch
checkpoint** — the epoch-scaling of the narrowing that the gate's control
exposed, turned into the shipping knob via `save_period=1`.

**Caveats, flagged for review (not hidden):**
1. **1-epoch fine-tune.** epoch0.pt is the model after a single (warmup-phase)
   epoch. Unusual as a shipping artifact, but it is the Pareto-optimal
   checkpoint (dense falls and duration recall peaks-then-falls after it), and
   every number above is measured on external ground truth, not the noisy
   internal val.
2. **Engraved +0.0022 net, driven by one work.** mozart-sym41 regresses +0.0146
   ("wrong note"); the other ten are flat-or-better and 6/11 improve. Not a
   material headline regression, but a real single-work wobble.
3. **Mahler p.172 unscored** shows fewer hollow (§4b) — likely over-detection
   stripping, but unproven.

**Why ship despite the caveats:** ReEngrave's product is *scanned* scores. The
trade is large, measured scan gains (duration recall +12 %, half-notes 8→27)
and held scanned dense recall, for a net-neutral engraved benchmark. For the
scanned use case this is a net improvement. **Sean's review is the final gate**
— the change is committed (path-scoped) but **not pushed**; production weights
are backed up (`…imgsz2048-ft-30ep.PRE-HOLLOW-2026-09-03.pt`) and the repoint is
a clean one-line revert.

**Alternative for Sean — `epoch1.pt` (after epoch 2), a deliberate trade, NOT
shipped:** duration recall **0.483** (vs 0.435) and half-notes 36, but dense
recall 0.891 (−0.050) — a hollow-for-dense tradeoff. It is *not* a clear win
(dense down 5 pts) so it is not shipped from this run; offered if a bigger
scanned-duration gain is worth the dense cost.

**Follow-ups (deferred to Sean, not done here):**
- The **OMR-NED accuracy headline** (`accuracy_record.py` / CLAUDE.md, currently
  0.1306 direction-text for the prior weights) is **not** updated — a headline
  change must go through `orchestral_eval --record` with the direction-text
  configuration, which this run did not measure. Re-record if the weights are
  adopted.
- **imgsz-2048 on a cloud GPU** remains the gate's ideal recipe; this run is the
  best *feasible* approximation on the M1 Max (§2). A 2048 run may hold dense
  recall even further out and let more epochs (more hollow) ship.

### What was committed (path-scoped, NOT pushed)
- `data/user-labeled/catalog-versions.txt` (+ regenerated catalog files):
  v7 + v8 admitted.
- `tools/omr/transcribe.py`, `backend/modules/local_omr.py`,
  `docker-compose.yml`, `CLAUDE.md`, `PROJECT_STATUS.md`, `tools/omr/README.md`:
  DEFAULT_WEIGHTS / OMR_WEIGHTS_PATH / docs repointed to
  `deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`.
- `tools/omr/tests/test_training_pipeline.py`: membership pin updated (v7+v8).
- this `SHIP_RESULTS.md`.

Weights are gitignored and never committed. The stripped 88 MB inference file
(`strip_optimizer`-verified to give byte-identical detections to `epoch0.pt`) is
installed in `omr-weights/` (docker mount) and
`tools/omr/training/data/weights/` (host CLI).

### Reproduce

```bash
# mix (isolated root, committed catalog untouched)
python3 -m tools.omr.training.build_catalog_yaml --root benchmarks/omr-labeling-survey-2026-09/ship-catalog \
    --versions v1-2026-05-18-orchestral v2-2026-06-08-beet5 v3-2026-06-09-mahler5 v4-2026-06-10-la-mer \
               v7-2026-09-02-hollow v8-2026-09-02-hollow2-5pub \
    --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
# (then 2x-dense oversample of the train list -> catalog-2xdense.yaml)
# fine-tune (serial, ALONE on MPS)
python3 -m tools.omr.training.train_yolo --data .../ship-catalog/catalog-2xdense.yaml \
    --weights omr-weights/...ft-30ep.pt --epochs 10 --imgsz 896 --batch 16 --device mps \
    --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 --extra-kwargs '{"save_period": 1}' --name ship-896-run
# re-gate (all CPU)
python3 benchmarks/omr-labeling-survey-2026-09/gate_all.py --prod omr-weights/...ft-30ep.pt \
    --ckpt e4=.../weights/epoch3.pt e6=.../weights/epoch5.pt e8=.../weights/epoch7.pt e10=.../weights/epoch9.pt \
    --beet5-pdf <IMSLP984073 p1 pdf> --page 1
```
