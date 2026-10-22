# Follow-up session prompts — deterministic double-check & training-side domain augmentation

Two paste-ready handoff prompts for tracks NOT yet built (the shipped work is
the time-sig/clef inference layer + the dossier *plan*). Produced 2026-07-11 via
a grounded workflow; every file/line reference verified against the repo.

- **Prompt A** — a deterministic, zero-input, no-model *internal-consistency*
  double-check (works on any score; complements the dossier plan which needs
  hand-input facts).
- **Prompt B** — training-side *domain augmentation* (ScoreAug/Augraphy) to close
  the synthetic→real detection gap at the source. **Guardrailed away from the
  proven dead ends** (hand-label fine-tuning, catalog training).

---

## PROMPT A — Deterministic internal-consistency double-check

> You are picking up an OMR verification task in the ReEngrave repo
> (`/Users/seanjohnson/Desktop/ReEngrave`).
>
> **Goal.** Build a **deterministic, zero-hand-input, no-model internal-consistency
> double-check** for the local OMR pipeline — a "does this OMR output even make
> sense?" safety net that verifies the `transcribe()` JSON **against itself** and
> flags where it is internally contradictory. It must work on **any** score with
> **zero** external input.
>
> **Why, and why it's complementary (not duplicative).** Already on `main`: the
> deterministic time-sig/clef layer (`tools/omr/`) and `docs/dossier-verification-plan.md`
> (a planned layer that anchors checks to Sean's **hand-input** truth and can
> therefore *resolve* which staff is right). `benchmarks/omr-detection-probe-2026-07/findings.md`
> established the core problem: the orchestral wall is a **synthetic→real domain
> gap** — the detector is often blind on dense pages, so the shipped layer
> abstains. **Your layer is the always-on free tier beneath the dossier layer.**
> With no external anchor you can only test *internal consistency*: you can flag
> "these staves disagree, at most one is right" but usually **cannot say which** —
> a real ceiling, not a tuning gap. The dossier layer resolves what you surface.
> Do **not** read hand-input or re-implement the dossier plan.
>
> **Read first:** `docs/dossier-verification-plan.md` (the sibling external-truth
> layer — understand the boundary; §2 table + §6 Phase-1 reshape),
> `benchmarks/omr-detection-probe-2026-07/findings.md`, and in `tools/omr/transcribe.py`
> the `transcribe()` page loop: systems grouping (~1213–1218), per-staff
> `n_measures` (~1271), `phase1_warning` emission (~1330–1344), `rhythm_sum_warning`
> post-pass (~1387–1394), `_measure_rhythm_sum_warning` (~1078, meter-None skip
> ~1094–1096), `_ClefContinuity` (~449–488), `_detect_key_sig_from_cell` (~525).
>
> **The checks, ranked (build in order):**
>
> **(d) Measure-count consistency across staves of a system — STRONGEST, build first.**
> Barlines run vertically through the whole system, so every staff in a system
> must have the same measure count (`measure_index` is even renumbered within a
> system — `resegment_fused_measures` docstring, `measure_extractor.py:694–696`).
> A staff whose `n_measures` deviates from the system mode localizes a missed
> barline (too low → fused cell) or spurious barline (too high). Pure integer
> invariant the pipeline already computed — **zero** meter/register/transposition
> reasoning. Not redundant with `resegment_fused_measures` (`:680`), which only
> *splits* when it finds a confident internal barline (else counts stay mismatched
> and nothing is emitted — you surface exactly that). Cross-reference the shipped
> `phase1_warning`: a staff short on count whose wide cell also carries it =
> confirmed missed barline → high confidence.
>
> **(c) Rhythm-sum notation-math, column-aggregated — USEFUL, partially shipped.**
> `_measure_rhythm_sum_warning` compares per-voice sums to `expected_beats` but is
> **skipped when `time_signature is None`** (most orchestral measures) and runs
> per-staff-per-measure, so it over-fires (empty resting staff → `[[]]` at
> `voicing.py:230` → actual=0; `rhythm.py:274–283` documents sparse bars
> legitimately under-summing). Upgrade: (1) meter target from the pipeline's OWN
> inference — C/cut-C are the only reliably-detected meter (`rhythm.py:411`), and
> `_dominant_detected_meter` (`:429`) / `infer_page_time_signature` (`:385`,
> per-column MAX via `_page_column_lengths:356`) already yield a page meter; (2)
> **aggregate to the measure COLUMN across the system**; (3) treat **over-sum** as
> HIGH-confidence (extra beats → fused barline, corroborate `phase1_warning`),
> **under-sum** as LOW. A fully-internal variant: the column MAX fullest-voice
> length IS the bar-length estimate; any staff-measure exceeding it flags over-full.
> **Build this column verifier once, parameterized by meter-source (internal OR
> dossier)** so this track and the dossier plan don't implement it twice.
>
> **(b) Cross-staff key-sig consistency within a system — MODERATE, scope-limited.**
> `staff_dict['key_signature']` from `_detect_key_sig_from_cell` (`:525`, just
> counts keySharp/keyFlat glyphs). Non-transposing staves share one key sig — on
> piano/quartet/choral/concert scores an outlier flags a mis-detected key. But on
> full orchestra, transposing instruments legitimately differ, and you can't know
> the transposition. Gate high confidence to ≤~4-staff systems and/or a large
> majority agreeing with one staff off by a single accidental; else advisory/abstain.
>
> **(a) Clef from notehead-pitch distribution — WEAKEST, advisory only.** Clef is a
> constant diatonic offset (`pitch_resolver.py:49,74`) — one staff in isolation
> gives zero evidence. Two soft anchors: cross-system self-stability of a role's
> register, and neighbor register ordering (a nominally-bass staff resolving above
> the treble above it). Gross errors only, real FPs (voice-crossing, piccolo).
> **Advisory only** — this is the check that most needs the dossier's register anchor.
>
> **(e) Clef-continuity verification** — `_ClefContinuity` already *prevents* drift;
> add only a flag when a *detected* clef for a role contradicts other systems.
> **Bonus:** cross-staff time-signature agreement within a system (`_dominant_detected_meter`
> aggregates but picks silently — flag the disagreement itself).
>
> **First vertical slice (do only this, then stop for review): check (d) only**, as
> a pure additive post-pass over the built `page_dict`, mirroring exactly where
> `rhythm_sum_warning` is added (`transcribe.py:1387–1394`). Per system collect
> `staff_dict['n_measures']`, take the mode; on a deviating staff set
> `staff_dict['measure_count_warning'] = {staff_measures, system_mode, agreement:'k/total'}`.
> Confidence = consensus_strength × deviation; promote to high when the short staff
> also carries `phase1_warning`; **abstain on near-even splits** (never assert which
> staff is wrong — the message is "internally inconsistent, needs review").
>
> **Runtime setup (a worktree has NO weights).** `transcribe()` loads weights from
> `DEFAULT_WEIGHTS`, a *relative* path empty in a worktree. Run from the main
> checkout, or pass the file explicitly:
> `--weights /Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`.
> **Concrete test PDFs (in the repo):** clean = `benchmarks/omr-phase4-extension/output/bach-wtc.pdf`;
> dense/orchestral (the likely `phase1_warning` carrier) =
> `benchmarks/omr-phase4-extension/output/ravel-bolero.pdf`.
>
> **Verification discipline:** (1) clean-case **byte-identical** — add a dict key
> only on a real anomaly; prove the bach-wtc JSON is byte-identical before/after.
> (2) Prove the metric on ravel-bolero (a short staff on a fused cell now flags and
> points at it). (3) Baseline first. (4) Touch **no** detection/pitch/rhythm code —
> pure additive post-pass. (5) Run `python3 -m pytest tools/omr/tests`. (6) **No
> merge/push/deploy without my explicit go-ahead** — report the diff, the two
> before/after demos, and the test run, then wait. Check (d) is the **zero-anchor
> sibling** of the dossier plan's `total_measures`/`structure_warning` row — share
> the `n_measures` reader, don't fork it. Known FP class (down-weight, don't
> hard-error): independently-barred systems / condensed multi-measure-rest staves.

---

## PROMPT B — Training-side domain augmentation

> You are picking up an OMR **training** task in the ReEngrave repo
> (`/Users/seanjohnson/Desktop/ReEngrave`, run from the repo root). Read the whole
> prompt first — the first half is guardrails that keep you off three proven dead
> ends.
>
> **STOP — dead ends, do NOT go here (settled, with evidence):**
> 1. **Detector fine-tuning on the sparse hand-labels is a PROVEN DEAD END.**
>    Multiple vast.ai runs made the model strictly worse (it forgot/suppressed
>    detections). Even the *correct* anti-forgetting recipe (DSv2 replay + BN-eval
>    lock + two-stage freeze) dropped WTC F1 **97.8% → 90.5%** (recall −13pt,
>    density halved). Sparse hand-labels teach the model to **suppress**. **The
>    hand-labels are EVAL data, not fine-tune data.**
> 2. **The catalog IMSLP×MusicXML training direction is ALSO dead** (Phases A–L).
>    Never load `omr-weights/deepscoresv2-yolov8l-phase-j-mix-30ep.pt`.
> 3. **Keep the nc=208 cap** — an nc mismatch silently re-inits the head (Phase-3.4
>    collapse). `train_yolo.py:_check_nc_consistency()` guards it; don't pass
>    `--allow-nc-expansion`.
>
> **Goal (the ONLY promising direction):** close the synthetic→real domain gap at
> the source via **domain augmentation of the DSv2 TRAINING SET**, then **retrain
> from the DSv2 base** (not a hand-label fine-tune). Fundamentally different
> mechanism: it teaches real-scan *appearance* (paper texture, ink bleed,
> show-through) **without** teaching suppression, because labels stay byte-identical
> and only pixels change. The TISMIR ScoreAug paper reports AP 36 → 56.5 on real
> scans (from memory — treat as motivation, not a promise).
>
> **Why:** `benchmarks/omr-detection-probe-2026-07/findings.md` — a conf-0.10 probe
> recovered zero real time-sig digits and only partial, mostly-treble clefs on real
> orchestral scans. The shipped deterministic + dossier verification layers can only
> *abstain* when detection is blind; fixing detection at the source is the
> complementary attack.
>
> **What already exists (wire it, don't rebuild):** `tools/omr/training/augment_scoreaug.py`
> — `run()` / `apply_blank_composite()` (darker-min `np.minimum` merge of a real
> blank scanned IMSLP page — paper texture lands, every ink pixel survives) /
> `apply_show_through()` / `apply_augraphy()` (ONLY photometric-safe effects:
> `AUGRAPHY_SAFE_EFFECTS`; geometric/warping augs forbidden so labels stay valid).
> Labels copied byte-identical. `tools/omr/tests/test_augment_scoreaug.py` — **16
> passing tests** proving darker-min never lightens ink, labels byte-identical, no
> spatial augs. **Critical wiring gap:** `augment_scoreaug.py` is a standalone
> drop-in-dir generator, **NOT** referenced by `prepare_yolo_data.py` or
> `train_yolo.py` — the glue (run it over the DSv2 train split, merge into the
> training dirs, point `data.yaml` at the union) is the work you write once.
> **Not yet on disk:** real TISMIR blank scans via `--download-blanks` (~186 MB,
> sha-pinned); `augraphy` not in `requirements-training.txt` (lazy-imported —
> without it, degrades to a weaker fallback). Fetch both before any run claiming a
> domain-gap result.
>
> **Existing DSv2 pipeline** (`tools/omr/training/`): `download_dataset.py`
> (`ds2_dense.tar.gz` ~6.5 GB default, `ds2_complete.tar.gz` ~80 GB `--full`) →
> `prepare_yolo_data.py:convert_dataset()` (extended-COCO OBB → YOLO, `data.yaml`
> nc=208) → [`merge_shards.py` for the full multi-shard layout] →
> `train_yolo.py:train()`. Production weights `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`
> were trained at **imgsz 2048** (F1 98.8% on the WTC verdict set — **the baseline
> to beat**).
>
> **First vertical slice — offline augmentation preview, BEFORE any GPU spend.**
> 1. `python3 -m tools.omr.training.augment_scoreaug --download-blanks --blanks-dir tools/omr/training/data/blanks` (~186 MB) and `pip install augraphy`.
> 2. **Skip the 6.5 GB DSv2 download for the preview** — `augment_scoreaug.run()`
>    only needs an `images/` + `labels/` dir, and real YOLO pairs already exist at
>    `data/user-labeled/v1-2026-05-18-orchestral/{images,labels}`. Point the preview
>    there. (Caveat: those are *real-scan* hand-labeled cells, whereas ScoreAug is
>    designed to composite blanks onto *clean synthetic* DSv2 — fine for verifying
>    alignment/ink/augraphy-ran, not for judging final realism. Defer the DSv2 pull
>    to the GPU stage.)
> 3. Run `augment_scoreaug` over those images (`--src-images … --src-labels … --out-root <scratch> --blanks-dir … --fraction 1.0`).
> 4. **Eyeball + confirm labels still align:** render each augmented image with its
>    (unchanged) YOLO boxes overlaid — symbols must still sit under their boxes,
>    ink preserved (darker-min never lightens), paper texture/bleed visible, and
>    `augraphy` actually ran (not the synth fallback).
> 5. **Slice success = boxes visibly still align, ink intact, real paper texture
>    applied** — report a couple of overlay images, then **stop and report** before
>    proposing the GPU A/B.
>
> **Full plan (only after I approve the preview),** on a vast.ai RTX 4090
> (SSH-driven — `VAST_AI_SETUP.md` + `HANDOFF_PREMIUM_TRAINING.md`):
> - Run `augment_scoreaug` over the DSv2 **train split only** (`--fraction 0.5`);
>   the **val split stays CLEAN** (degrade it and you can't measure the lift).
> - Merge degraded + originals; point `data.yaml` at the union.
> - **Retrain from COCO-pretrained `yolov8l.pt`** — pass `--weights yolov8l.pt`
>   (this matches production's provenance). **NOT** the production ft checkpoint
>   (that would be a fine-tune) and **NOT** the `train_yolo.py` default `yolov8m.pt`
>   (that yields a non-comparable `m` model). Train at **imgsz=2048**, nc=208,
>   music-aware aug flags (`fliplr`/`flipud`/`hsv_*` = 0).
> - **Cost caveat:** imgsz=2048 roughly doubles per-iter time vs 1280; a full
>   30-epoch imgsz=2048 DSv2 retrain is several GPU-hours (not the ~$0.15–0.42 of a
>   smoke run) — start with a `--smoke` run to confirm the pipeline before the real
>   A/B, and budget accordingly.
> - **Evaluate `best.pt`** on (a) the 25-cell WTC verdict set and (b) the
>   Boléro/Mahler probe pages that currently recover zero real time-sig digits.
> - **Success = clef/time-sig/notehead recall on the real orchestral pages goes UP
>   while WTC F1 does NOT regress below the 98.8% production baseline.** Only then
>   scale to `ds2_complete` via `merge_shards`.
>
> **Verification discipline:** baseline the production model on the WTC verdicts +
> probe pages FIRST (measure against a captured number, not memory); prove
> label-preservation before GPU spend; keep production weights as the baseline to
> beat; hand-labels are EVAL data only; run `python3 -m pytest tools/omr/tests`
> (incl. `test_augment_scoreaug.py`). **No merge/push/deploy/GPU-spend without my
> explicit go-ahead** — report the preview overlays and wait.
