# DSv2 rehearsal — the last training-side lever, priced, and it fails on every axis

**Date:** 2026-09-04 · **Branch:** `claude/dsv2-rehearsal` (worktree pinned at
`b8b10514`) · **Box:** vast.ai RTX 4090 24 GB (Hungary, machine 14205),
destroyed and destruction verified (Instances page reads 0) · **GPU spend:
$0.49** ($57.76 → $57.27 credit after bandwidth settled, both instances) · **Production
weights UNTOUCHED, weight routing untouched, nothing shipped.**

`ROUND5_METHOD_2026-09-04.md` §4 named this experiment: eleven method arms all
collapse the same class families — teacher rehearsal at conf 0.25 included —
and the one untried training-side fix was REAL rehearsal, DeepScoresV2 itself
mixed back into the fine-tune, "tens of GB, best done straight onto a rented
box". This round ran it, from both donors.

## The answer

**No. DSv2 rehearsal does not hold the class space open, and it does not keep
the scan gains either — it loses both at once, from either donor, within one
epoch, and more epochs make it worse.**

- **Axis 3 (class space): FAIL, every epoch, both arms.** The same families
  the scan-only fine-tunes delete — `beam`, `tie`, `staff`,
  `accidentalSharp`, `clefG`, `rest8th`, `augmentationDot` — are at exactly
  zero after ONE epoch, joined by `ledgerLine` from epoch 1, while the model
  is being trained on 69,016 labeled beams. No epoch recovers anything.
- **Axis 1 (hollow payoff): the scan gain is actively traded away.**
  Production reads 27 half-noteheads on beet5-p1; one epoch of rehearsal FROM
  production reads **14**; from the pre-hollow base, **8** — the base's own
  recorded number, i.e. the entire hollow campaign undone. DSv2-dense is
  engraved black-notehead music, and rehearsing on it pulls the detector back
  toward the base prior.
- The one thing rehearsal protects is the thing the rehearsal data is made
  of: dense-page black-notehead recall rises 0.941 → 0.955/0.964, and both
  arms "win" overall F1 on the dense cells (0.857/0.869 vs production's
  0.625) — the round-5 reading again: a model that has stopped emitting
  twenty classes has very little left to be imprecise about.

A clean negative was the closing condition for the training-side question, and
this is one. **The fix for the class collapse is not more data, not method
knobs (round 5), and not rehearsal (this round). What works remains head
surgery** (`merge_class_head.py` + per-class bias floors), whose candidate
`d25e0_graftprod_shift0.9.pt` is still the only checkpoint to clear all three
axes.

## Design

Two arms, one mix, the round-5 ship recipe:

| | arm 1 (`rehbase`) | arm 2 (`rehprod`) |
|---|---|---|
| donor | `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (pre-hollow base) | `deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt` (production) |
| data | identical mix (below) | identical mix |
| recipe | imgsz 896, batch 16, `optimizer=auto` (AdamW, auto lr ≈1.2e-4), patience 99, `fliplr=flipud=hsv_h=hsv_s=0`, `save_period=1`, 5 epochs, nc=208 | same |

**The mix.** Scan side = the round-5 corpus exactly: the 14 admitted versions
of `data/user-labeled/catalog-versions.txt` at `b8b10514` — **591 cells /
3,871 human boxes** (v1–v4 dense + v13–v21 completed + v22), split 495 train /
96 val by the repo's own `build_catalog_yaml`, no dense oversample (the ratio
is the knob this round varies, and 73% of images being dense engraved pages
already carries the density prior the 6x oversample proxied). ⚠️ The round-4
handoff's "752 cells / 5211 boxes" is a different accounting; the tree and
`ROUND5_METHOD` §1 both say 3871 boxes / 591 cells, which is what is on disk.

DSv2 side = the **dense subset, whole**: 1,362 train / 352 test pages,
889,833 train instances (`ds2_dense.tar.gz` is 707 MB from Zenodo — the
download script's "~6.5 GB" docstring estimate is 9x high). The assignment
asked for ~3:1 DSv2:scan by image count = 1,485 pages; dense-train only HAS
1,362, so all of them went in: **actual ratio 2.75:1** — the whole population,
nothing to document about sampling (the coverage-first sampler in
`build_mix.py` never triggered). Val monitor = 96 scan cells + 150 DSv2 test
pages, monitor only; checkpoints were gated on the Mac, never picked by val
fitness. `mix_report.json` beside this file records all of it.

**Class-space integrity** (the recorded round-5 index trap): the prepared DSv2
`data.yaml` names were verified equal to `deepscoresv2_208_classes.json` **at
every index**, and that JSON was verified equal to both donors' own
`model.names` index-by-index before anything trained — one 208-class space
shared by DSv2 labels, scan labels and model rows, checked per-INDEX, never
remapped by name (40 names are duplicated). DSv2-dense populates ids 0–135
(the deepscores naming family), 115 classes with instances — the family the
donors' knowledge lives in.

## Axis 3 — class-space survival (30 held-out dense cells, conf 0.25)

`probe_class_inventory.py`; production emits 594 detections / 28 classes.
Full table in `class_inventory_full.json`; the top rows:

| class | prod | prehollow | r5cand | rb_e0 | rb_e1 | rb_e2 | rb_e3 | rb_e4 | rp_e0 | rp_e1 | rp_e2 | rp_e3 | rp_e4 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| noteheadBlackInSpace | 142 | 142 | 140 | 144 | 137 | 140 | 143 | 145 | 144 | 137 | 138 | 143 | 145 |
| noteheadBlackOnLine | 125 | 127 | 126 | 127 | 130 | 133 | 131 | 131 | 127 | 131 | 131 | 129 | 130 |
| beam | 126 | 127 | 127 | **0** | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 |
| ledgerLine | 31 | 57 | 11 | 35 | 1 | 0 | 0 | 0 | 29 | 0 | 0 | 0 | 0 |
| staff | 27 | 30 | 30 | **0** | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 |
| tie | 19 | 24 | 19 | **0** | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 |
| accidentalSharp | 15 | 15 | 15 | **0** | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 |
| clefG | 12 | 10 | 11 | **0** | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 |
| rest8th | 12 | 12 | 12 | **0** | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 |
| augmentationDot | 12 | 12 | 13 | **0** | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 |
| **classes emitted** | **28** | 29 | 28 | 17 | 13 | 11 | 10 | 10 | 18 | 12 | 11 | 10 | 10 |
| **collapsed vs prod** | — | 0 | 0 | **7** | 8 | 8 | 8 | 8 | **7** | 8 | 8 | 8 | 8 |

Identical family lists at every epoch of both arms, monotone through epoch 2,
flat thereafter. Rehearsal changed nothing about which classes die or how
fast — the trajectory is round 5's, with 2.75x more data flowing past it.

## The control that makes it damning: the model deletes classes it is being trained on

Two per-class `yolo val` runs on the box, same mixed val (150 DSv2 pages + 96
scan cells, 95,318 instances), imgsz 896, mAP50:

| class (val instances) | pre-hollow base | rehprod e1 |
|---|--:|--:|
| noteheadBlackOnLine (13,213) | 0.972 | 0.981 |
| staff (1,587) | 0.961 | 0.648 |
| rest8th (991) | **0.965** | **0.000** |
| accidentalSharp (699) | **0.959** | **~0.000** |
| tie (1,246) | **0.806** | **0.001** |
| beam (6,862) | **0.752** | **0.022** |
| augmentationDot (2,425) | 0.231 | 0.000 |
| ledgerLine (9,355) | 0.000 | 0.000 |
| **all** | **0.689** | **0.413** |

Read the base column first: at imgsz 896 the rehearsal data is perfectly
legible to the donor for every collapsing class except `ledgerLine` (a native
~2 px rung letterboxed below a pixel — the one class whose signal plausibly
never reaches the assigner at this scale). `beam` 0.752, `tie` 0.806,
`rest8th` 0.965 — the base reads them ON THESE PAGES at THIS imgsz. One epoch
of fine-tuning later they are near zero **on the training distribution
itself**, not merely on the cell-frame probe. So this is not "rehearsal signal
absent", not "wrong scale", not "cell-frame domain shift": the optimization
destroys minority classes while their positive gradient is present at ~6,800
beam instances per epoch. The train log agrees — `cls_loss` rises 1.52
(epoch 1) → 2.60 (epoch 2) before drifting back, the shape of a class head
being torn up and resettled.

That also retires the last innocent explanation from round 5 (corpus silence:
"everything unboxed trains as background"). Here the classes WERE boxed, at
volume, on three quarters of the images — and died on the same schedule.
Whatever deletes them operates through the optimization dynamics of a
208-class fine-tune at this LR scale, not through the labels.

## Axis 1 — dense-recall forgetting + hollow payoff (beet5-p1 scan)

`gate_all.py` on both arms' epoch 0 (their least-collapsed checkpoints),
production re-measured in the same run on the same device — its numbers
reproduce the recorded baselines exactly (nh 207/220 = 0.941, half = 27), so
the comparison is fair:

| | nh recall (dense) | overall F1 | half | hollow total | black | with-dur R | exact R | step R |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| production | 0.941 | 0.625 | **27** | 30 | 79 | **0.4354** | **0.5646** | 0.6463 |
| round-5 candidate | 1.000 | — | 31 | 31 | — | 0.5102 | 0.5782 | 0.6939 |
| rehbase e0 | 0.955 | 0.857 | **8** | 8 | 55 | 0.3129 | 0.3946 | 0.3946 |
| rehprod e0 | 0.964 | 0.869 | **14** | 15 | 59 | 0.3741 | 0.4354 | 0.4422 |

*(candidate row from ROUND5_METHOD §3b, measured on the same harness; raw
numbers for both e0 rows in `gate_all_summary.json`.)*

The pre-hollow base reads 8 half-noteheads on this page — the hollow
campaign's whole point was 8 → 27. Rehearsal from that base lands on
**exactly 8**: the 359 hollow-campaign cells in the mix taught it nothing
that survived the DSv2 gravity. Rehearsal from production gives back **13 of
the 19** halves the ship bought, in one epoch. Every pitch/duration recall
lands at or under production. The F1 column is the round-5 trap in new
clothes.

## Axis 2 — 5-page scan-e2e, one representative run, for the record

Axis 3 already disqualifies every checkpoint, so one run (rehprod e0, the
least-collapsed) documents how the collapse prices out end-to-end rather than
auditioning a candidate. `results-rehprod-e0.json` beside this file:

| | pooled OMR-NED | edits | predicted symbols |
|---|--:|--:|--:|
| production | 0.7517 | 7894 | 4350 |
| round-5 candidate (shift 0.9) | 0.7493 | 7872 | 4355 |
| **rehprod e0** | **0.7329** | **7001** | **3402** |

⚠️ **The rehearsal checkpoint posts the best pooled number in the repo's
history and is the worst checkpoint ever gated on this benchmark.** OMR-NED
divides by `truth + predicted` and flatters under-prediction (the recorded
round-4 lesson; shift-1.5 was the round-5 rehearsal of the same trap). The
element counts against truth are the honest columns:

| element | truth | production | rehprod e0 |
|---|--:|--:|--:|
| note | 1894 | 1478 | 1276 |
| tie | 271 | 60 | **0** |
| slur | 204 | 160 | **0** |
| accidental | 85 | 79 | **0** |
| beam | 563 | 358 | 373 |

Zero ties, zero slurs, zero printed accidentals reach the file. `<beam>`
elements survive only because classical CV supplies them — the deleted YOLO
`beam` class costs the kept-where-no-CV-overlap rule (worth 0.1917 → 0.1861
on the engraved benchmark), silently, which is gate axis 3's entire reason to
exist. Had axis 2 been read alone, this checkpoint ships.

## What this closes, and what it doesn't

Round 4 named the training-side levers; round 5 killed the method knobs
(eleven arms) and teacher rehearsal; this round killed real rehearsal, from
both donors, with the rehearsal signal verified legible (base reads it at
0.75–0.97 on the very val it then dies on) and verified index-aligned.
**Closed: on this corpus at this model size, short fine-tunes delete minority
classes no matter what data is mixed in.** The working path remains head
surgery + per-class bias floors (round 5 §3/3b), and the standing candidate is
`omr-weights/round5-merged/d25e0_graftprod_shift0.9.pt`.

Deliberately not run (two-arm budget, and nothing measured here motivates
them):

1. **Rehearsal at imgsz 2048** (the donors' native scale). The control table
   is the reason for skepticism — beam/tie/rest8th/accidentalSharp are
   legible at 896 and died anyway; 2048 would only re-admit `ledgerLine`'s
   signal. If ever priced, the cheap discriminator is the same two `yolo val`
   runs before any Mac gating.
2. **`freeze=22` + this mix** — the one arm this round's control MOTIVATES.
   The deletion survives the presence of positive gradient, so the suspect is
   the magnitude of early fine-tune updates outside the head (auto-AdamW
   lr ≈1.2e-4; `warmup_bias_lr` 0.1 — round 5 tested those knobs only where
   there was no rehearsal signal to save). Everything-but-the-head frozen,
   with this mix on disk, is a ~5-minute arm on the next rented box if the
   surgery path ever needs a trained-not-grafted competitor.

## Run record

- **Spend $0.49 total** ($57.76 → $57.27 after bandwidth settled). Instance 1: Sweden m:11230,
  $0.335/hr — **broken host**: CUDA error 803 on every init with matching
  kernel/userspace driver 555.52.04, nvidia-smi fine, torch dead 5/5 (the
  round-4 Delaware lesson repeating). Destroyed after ~10 min, ~$0.06.
  Instance 2: Hungary m:14205 (instance 49902152), $0.423/hr, RTX 4090 24 GB,
  150 GB disk, ↓6.5 Gbps — healthy (CUDA matmul 3/3); everything ran in
  ~63 min, ~$0.40 incl. bandwidth. Destroyed; **Instances page verified (0)**.
- **Each arm trained in 5 minutes** (0.083 h, 117 iters/epoch, 22.5 GB VRAM;
  TaskAlignedAssigner OOM warnings auto-degraded to per-image assignment,
  forward batch unchanged). The DSv2-dense download is 707 MB, ~2 min on that
  pipe; the whole "tens of GB" fear was misplaced for the dense subset.
- Checkpoints: `omr-weights/dsv2-rehearsal/{rehbase,rehprod}_epoch{0..4}.pt`
  in the MAIN checkout (sibling of `round5-merged/`), all 10 **md5-verified
  against the box's manifest** (`CHECKSUMS.md5` here, with both arms'
  `results.csv`, `mix_report.json`, and the on-box logs pulled alongside).
- Reproduction: `build_tarball_rehearsal.sh` (pack, from this directory) →
  `run_rehearsal.sh data` → `run_rehearsal.sh train` on the box;
  `build_mix.py` holds the verification and mix logic.

## Rig faults burned this round (so nobody repeats them)

1. **`Path.resolve()` on dataset image lists dereferences symlinks and breaks
   ultralytics' images→labels derivation.** `prepare_yolo_data` symlinks
   images into `deepscoresv2-yolo/images/`; the first `build_mix.py` wrote
   `str(p.resolve())` train lines, which pointed at the symlink TARGETS under
   `ds2_dense/images/` — ultralytics then derived labels under
   `ds2_dense/labels/` (nonexistent) and trained all 1,362 DSv2 pages as
   BACKGROUND, silently. The tells: the loader cache read `(found 96,
   missing 150)`, and per-batch `Instances` sat at ~2–6 where dense pages
   read hundreds (5,336 in the first fixed batch). One full training pass
   wasted (~$0.08). **Check the loader's found/missing line before believing
   any mixed-source run.**
2. `ultralytics 8.4.139` nests `project=runs name=X` under
   `runs/detect/runs/X` — round 5's strip/checksum glob
   (`runs/*/weights/*.pt`) matches nothing there. Strip by `find`.
3. The `pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel` image lacks libxcb, so
   `opencv-python` (an ultralytics dep) fails to import. Install
   `opencv-python-headless` over it.
4. This Mac's downlink from the box ran ~250 KB/s single-stream; four
   parallel `scp -C` streams moved ~4x that. A save_period=1 sweep is ~880 MB
   — budget ~25 min even parallelized, or strip more aggressively.
5. `scan_eval.py` hardcodes `ROOT/.venv-omrned/bin/python` and ignores
   `OMRNED_PYTHON` — in a fresh worktree, symlink the venv the same way as
   `.venv-surya`:
   `ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned`.
