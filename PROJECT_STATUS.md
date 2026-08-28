# ReEngrave — Project Status

**Last updated:** 2026-08-28 (cross-session reconciliation)

This document is a snapshot. For day-to-day reference docs see
[CLAUDE.md](CLAUDE.md). For parked research ideas see [NOTES.md](NOTES.md).

---

## Scope

**Personal-use only** (re-affirmed 2026-05-24). Sean is the sole user. The Stripe payment gate and multi-user infra are already built but no longer the optimization target — design decisions should minimize complexity and ongoing cost, not maximize generality. The only acceptable interaction surface for new tooling is Claude Code itself (Claude sessions running locally, calling Bash / Python / YOLO). No new long-running services / MCP servers / HTTP proxy routes / UI surfaces unless Sean explicitly promotes them.

## TL;DR

ReEngrave has **two converged tracks** living together on `main`, plus an optional theory layer:

1. **A web app for music-score quality control** — upload a PDF, run OMR, review diffs, export. Auth + payments wired in. Built March 2026, iterated through April–May.
2. **An in-house YOLO + classical-CV OMR pipeline** — `tools/omr/`, fine-tuned on DeepScoresV2 (F1 98.8% on the Bach WTC verdict set). Built May 2026 across 49 commits / Phase 1 → Phase 4m.
3. **Maestro theory layer** (shipped 2026-05-24) — `tools/maestro_bridge/` (TypeScript, runs host-side via node/tsx) + `backend/modules/theory_layer.py`. Env-gated: harmony/rhythm validation, scholarly cross-check against 5 seed works, and in-pipeline pitch re-ranking with auto-correction (M4, local-YOLO pipeline only). See [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md).

**Current activity (July–August 2026): stopped trying to make the detector see more, and started making the pipeline *reason* about what it sees.** Three things drove this:

1. **The orchestral wall is a synthetic→real domain gap, not a threshold problem.** A July confidence probe found that at conf 0.10 the detector recovers *zero* real time-signature digits on Boléro/Mahler first pages and only partial, mostly-treble clefs. Lowering confidence floods noteheads with false positives instead.
2. **Training your way out of it does not work.** Three separate fine-tuning campaigns failed — catalog training (May), ScoreAug/Augraphy domain augmentation (July), and a clef-targeted fine-tune (July) that fixed all-treble but collapsed dense-page noteheads 2506 → 114.
3. **So the leverage is in deterministic layers that reason over the detections** — verification that abstains where detection is blind, and geometry that measures rather than classifies.

That produced the July **internal-consistency layer** (five cross-staff checks) and the August **geometry layer** (clef and key signature read by position, not by shape).

---

## What works today

### End-to-end OMR (CLI)

```bash
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly  # → out.pdf
```

All 5 benchmark PDFs (Bach WTC, Mozart, Beethoven, Chopin, Debussy) produce LilyPond that compiles to PDF with **zero errors** — only bar-check warnings on measures whose summed durations don't match the time signature exactly. F1 98.8% on the 25-cell Bach WTC verdict set. See [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md) for the full Phase 4 story.

### Clef + key signature by geometry (2026-08-27/28, on main)

Clef reading stopped being a classification problem. Alto, tenor, soprano, mezzo and
baritone clefs are **the same glyph on different staff lines**, so no classifier — and
no ensemble of classifiers — can separate them; measuring which line the glyph names
does, exactly.

- `clef_geometry.py` — resolve a clef by the staff line it names.
- `clef_locator.py` — a classical-CV C-clef locator for pages where no model sees a clef
  at all. Rejects an F clef by its two dots rather than by proportions.
- `staff_header.py` + `header_ink.py` — a *measured* header window. This fixes a real
  and previously silent failure: `Staff.x_start` is the longest unbroken ink run on the
  middle staff line, so on a degraded print it lands **past** the clef and the key
  signature, and every header reader then sees nothing.
- `key_signature_geometry.py` / `key_signature_locator.py` / `key_signature_vote.py` —
  positional key-signature reading plus a cross-page vote.
- **`clef_source`** on each staff dict names which reader supplied the clef
  (`detector` / `specialist` / `cv_locator`); **absent means defaulted**. This is the
  single most useful field for judging a page's pitches, because a defaulted clef
  transposes every note on the staff without any other visible sign.

Ground truth in `benchmarks/omr-clef-geometry/` and `benchmarks/omr-key-signature/`.

### Internal-consistency checks (2026-07, on main)

A zero-input, no-model safety net that verifies the `transcribe()` JSON **against
itself** and flags where it is internally contradictory. Works on any score with no hand
input. Five checks, all additive post-passes that write nothing on clean output:

| id | flag | invariant |
|----|------|-----------|
| (d) | `measure_count_warning` | barlines run through a system → every staff shares one measure count |
| (c) | `rhythm_sum_warning` | each measure-column sums to its meter |
| (b) | `key_signature_warning` | one concert key explains all staves, via transposition |
| (a) | `clef_register_warning` | staves run high→low; a lower staff should not resolve above an upper one |
| (e) | `time_signature_disagreement` | all staves of a system share one meter |

Design rule throughout: **abstain rather than guess.** With no external anchor a check
can say "these disagree, at most one is right" but usually not which, so each requires a
strict majority before pointing at a minority. Reference and lessons learned:
[docs/internal-consistency-checks.md](docs/internal-consistency-checks.md).

### Theory layer (optional, env-gated)

With `MAESTRO_BRIDGE_ENABLED=true`, OMR output is enriched with key detection, rhythm/beat-mapping validation, and a scholarly cross-check against curated reference analyses (5 seed works). With `MAESTRO_PITCH_RERANK_ENABLED=true`, ambiguous noteheads are re-ranked against the detected key during local-YOLO OMR and auto-corrected above a confidence threshold. Runs host-side (node/tsx + the `gradus` submodule) — **not available inside the Docker container by design** (personal-use scope; the container has no Node).

### Web app pipeline

```
Upload PDF → ReEngrave (pick: local YOLO or Claude Vision) → Review
  ├── Vision diff (paid)            — Claude Vision flags per-measure differences
  └── Theory check (free)           — music21 rhythm/range/enharmonic sanity
→ Export (musicxml | lilypond | pdf)

Parallel: Gradus Library
  ├── Upload master reference XMLs
  └── Multi-source comparison (2-6 XMLs, music21 measure agreement matrix)
```

Auth: JWT + httpOnly refresh cookie, 8-hr access tokens.
Payments: Stripe webhook, $5/score for Vision diff, admin-email bypass.

### Local YOLO pipeline modules (`tools/omr/`)

| Module | Function |
|---|---|
| `transcribe.py` | Entry point — PDF → structured JSON |
| `export.py` | JSON → LilyPond / MusicXML (incl. voice splitting via `<backup>`) |
| `yolo_detector.py` | ultralytics YOLOv8l wrapper |
| `line_detection.py` | Classical-CV stems + beams (Phase 4f) |
| `rhythm.py` | Note durations from notehead class + beam count + flag pairing + dots |
| `voicing.py` | Same-x notehead chord grouping + stem-direction voice splitting |
| `pitch_resolver.py` | Notehead y-position → diatonic pitch, with key sig + inline accidentals |
| `staff_detector.py` | 5-line staff detection via horizontal projection clustering |
| `measure_extractor.py` | Barline detection + canonical-cell extraction |
| `preprocessing.py` | PDF → PageImage (render, binarize, deskew) |
| `staff_line_removal.py` | Optional staff-removed cell variant |
| `clef_geometry.py` | Resolve a clef by which staff line it names (2026-08) |
| `clef_locator.py` | Classical-CV C-clef locator for pages no model reads (2026-08) |
| `staff_header.py` / `header_ink.py` | Measured header window — fixes the `x_start` failure (2026-08) |
| `key_signature_geometry.py` / `_locator.py` / `_vote.py` | Positional key signature + cross-page vote (2026-08) |
| `annotate/` | FastAPI labeling UI — triage mode + draw-from-scratch mode (2026-06-09) |
| `training/` | DSv2 prep + ultralytics training scripts |
| `tests/` | **670 unit tests** (main, 2026-08-28) |

### Hand-labeled training data (`data/user-labeled/`)

| Version | Cells | Content |
|---|---|---|
| `v1-2026-05-18-orchestral` | 60 | Beet 5 + Mahler 5 orchestral cells; cleaned 2026-06 to remove structural-element boxes (staff/stem/beam → background) |
| `v2-2026-06-08-beet5` | 37 | Beethoven 5 pp. 45–75; heavy FP-drop batch (480 FPs dropped, 37 FNs added) |
| `v3-2026-06-09-mahler5` | 35 | Mahler 5 batch |
| `v4-2026-06-10-la-mer` | 29 | Debussy La Mer batch (336 boxes) |
| `v5-2026-07-12-clef` | 151 | Clef-diversity batch across 4 scores |

---

## The catalog-training experiment (2026-05-23 → 05-25) — concluded, not merged

The headline NOTES.md idea — *train YOLO from symphony MusicXML × IMSLP editions instead of hand-labeling* — **was executed** across Phases A–L on branch `claude/interesting-curran-3ca1b7` (43 commits, never merged to main). Outcome:

- **The catalog itself worked.** 65/65 IMSLP editions aligned to MusicXML (Phase D); per-cell YOLO label generation shipped (Phase E); 154k labels emitted across 26 movements (Phase G).
- **Training on it failed, repeatedly.** Phase H (catalog-augmented fine-tune): collapsed. Phase I (fixed a ~50px x-offset in catalog labels): still collapsed. Phase J (mix-mode, briefly promoted): Phase K diagnosed a class-ID collision with DSv2 and the collapse stood. Phase L (slot remap to DSv2-free slots): **still collapsed** on Beethoven 5.
- **Verdict:** catalog-augmented YOLO training is a dead end with the current recipe. Structural elements (stems/beams/barlines) stay with classical CV; symbol-class improvement comes from **hand-labeling via the annotate UI** (the current June work).

**Loose end:** `omr-weights/deepscoresv2-yolov8l-phase-j-mix-30ep.pt` (84 MB, from the collapsed Phase J run) still sits next to the production weights. **Do not use it.** Production remains `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`.

The branch also carries **post-experiment OMR improvements that may still be valuable** (see "Unmerged work" below).

---

## Unmerged work on branches

Audit **2026-08-28**. Five ReEngrave sessions ran in parallel that day; three were still
running at the time of this audit, so treat this as a snapshot. Full cross-session
reconciliation: [docs/state-of-play-2026-08-28.md](docs/state-of-play-2026-08-28.md).

| Branch | Commits | What it has | Disposition |
|---|---|---|---|
| `claude/reengraver-contextual-analysis-29cdd5` | 9 | **Contextual analysis**: system grouping by vertical connectivity (43%→86%), instrument identity from the PDF text layer, stable part slots across systems/pages (92% label purity), clef proposal from an instrument's written range. Plus a disproven clef-from-key-fit benchmark. | Merge after `recognition-improvement-next`, then re-run its benchmarks |
| `claude/recognition-improvement-next-2f1709` | 4 | Staff recovery ("comb" pass for lightly printed staves) + spacing-outlier rejection; staff-line removal was a no-op on most orchestral scores; stem/beam ground truth and the stem bug it found; beams redefined as horizontal ink that stems run into | **Merge first** — it is upstream of everything else |
| `clef-phase0-eval` | 15 | Time-signature labeling batch; clef fine-tune Phase-0 conclusion. Carries **hand-drawn label verdicts** (irreplaceable) | Merge for the labels; the fine-tuned weights stay unused |
| `claude/clef-time-signature-weights-6d6e38` | 9 | `oemer` / LEGATO bridge for a host-side orchestral second opinion; clef pseudo-label training scoping | Evaluate — the second-opinion idea is live, the pseudo-label plan is not scoped |
| `claude/omr-dossier-verification-layer-eaf6d0` | 4 | Dossier-guided verification slice 1 (meter back-fill + column notation-math) | Active WIP; see the design brief in `docs/` |
| `claude/interesting-curran-3ca1b7` | 43 | Catalog experiment Phases A–L (below) **plus** 2026-05-25 `line_detection` improvements | Archive of the experiment; evaluate the line_detection commits for cherry-pick |
| `claude/yolo-score-labeling-automation-1276ee` | 8 | MXL-guided auto-labeling (resurrected phase_e label emitter → triage UI pre-labels) | Evaluate |
| `claude/training-domain-augmentation-a29baf` / `claude/scoreaug-fair-test-a2928e` | 3 / 2 | ScoreAug + Augraphy domain augmentation — **DISPROVEN** by a fair 3-way fine-tune test | Keep as the negative-result archive; do not revive the recipe |
| `claude/gallant-hellman-29ffdd` | 3 | Per-class OMR improvements: grammar verification, phantom-rest corrector, imgsz ensemble | Evaluate for cherry-pick |
| `claude/magical-bhabha` | 1 (March) | Real MusicXML measure-level patching in `export_module` — the #1 web-app TODO | Pre-consolidation; evaluate against current `export_module` |
| `claude/peaceful-kapitsa` | 1 (March) | SQLite-backed persistent job queue replacing FastAPI BackgroundTasks | Same: evaluate or discard |
| `claude/quizzical-bell` | 1 (April) | The parked `/engrave` skill (Claude Vision-only OMR) | Superseded; safe to delete |

**Housekeeping noted 2026-08-28:** four older worktrees (`blissful-payne`, `silly-bose`,
`distracted-bartik`, `adoring-kare-52c6`) hold uncommitted frontend/backend edits from
earlier sessions — nothing modified on 08-28, but they have been sitting there. The
`omr-clef-detector-demo-d51278` worktree is parked mid-merge; its content is a duplicate
of work already on main (checked file by file), so nothing is at risk.

---

## What does not yet work / known limitations

**OMR**

- **The orchestral wall is a domain gap, not a threshold.** On dense conductor's scores
  the detector is often blind: a July confidence probe at conf 0.10 recovered **zero**
  real time-signature digits on Boléro/Mahler first pages and only partial, mostly-treble
  clefs, while flooding noteheads with 2.4–3.5× false positives. The deterministic layers
  correctly **abstain** there. `benchmarks/omr-detection-probe-2026-07/findings.md`.
- **Three fine-tuning campaigns have failed; do not assume a fourth will work.**
  Catalog training (May, Phases A–L), ScoreAug/Augraphy domain augmentation (July — the
  augmented arm came out *worse than the clean control* on real dense cells), and a
  clef-targeted fine-tune (July — fixed all-treble but collapsed dense-page noteheads
  2506 → 114). **Do not deploy `clef-ft` or `phase-j-mix` weights.** Production remains
  `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`.
- **Custom YOLO classes (barlines, textDynamic) caused catastrophic forgetting.** Phase
  3.4 expanded `nc` 208 → 214; F1 collapsed to 79.3%. Barlines now via classical CV;
  textDynamic not detected. `catalog.yaml` is capped at nc=208 and `train_yolo.py` fails
  fast on a mismatch, so this can no longer re-trigger silently.
- **Time-signature detection is still unreliable**, though a deterministic inference
  layer now back-fills conservatively (beat-sum inference, C/cut-C propagation,
  left-edge instrument-number misread filter) and abstains rather than guessing.
- **Key-signature *detection* is weak.** Beethoven 5 p15 reads `0 sharps / 0 flats` on
  all 18 staves of a C-minor movement, with one `keySharp` detection on the whole page.
  The positional reader and cross-page vote help where the glyphs are visible at all.
- **One-line percussion staves are invisible.** `_group_into_staves` accepts only
  five-peak evenly-spaced windows, so a single-line staff produces no `Staff` at all —
  and every staff below it then carries a `staff_index` one lower than its true slot.
  Proven in `tools/omr/tests/test_system_grouping.py` (contextual branch).
- **Per-measure beat sums on busy keyboard music** are close to but not exactly the time
  signature — LilyPond bar-check warnings report fractional offsets (1/32, 3/32).
- **Dense orchestral scores** still have more false negatives on small dynamics and grace
  notes.

**Web app**

- **MusicXML correction patching is a stub** on main. Accepted diffs are written as XML comments, not actual measure replacements. (An unmerged March implementation exists on `claude/magical-bhabha` — unevaluated.)
- **PDF.js crop region in `DiffCard` is incomplete** — full crop viewport implementation has a TODO.
- **No database migrations.** Schema changes require dropping the DB.
- **Background tasks use FastAPI `BackgroundTasks` (no queue).** Server restart during a long OMR job loses the job. (Unmerged March job-queue implementation on `claude/peaceful-kapitsa` — unevaluated.)
- **Frontend type field names still say "audiveris"** (`audiveris_confidence`, `min_audiveris_confidence`, `pattern_type: 'audiveris_failure'`). They now refer to the primary OMR engine; rename when there's a migration story.

**Theory layer**

- Host-side only (needs node/tsx + the `gradus` submodule); the Docker backend container cannot run it. By design under the personal-use scope, but worth remembering when a web-app OMR run shows no theory enrichment.
- M4 pitch re-ranking applies to the **local YOLO pipeline only** (Vision OMR emits no pitch candidates).

---

## How we got here — major milestones

| Date | Milestone |
|---|---|
| 2026-03-25 | Initial ReEngrave scaffold — FastAPI + React + Audiveris OMR + Claude Vision diff |
| 2026-03-26 | Auth (JWT + httpOnly refresh) + Stripe payments + Docker stack + 79 backend tests |
| 2026-03-26 | Production deployment stack (Traefik + Let's Encrypt) + restructured 3-step UI |
| 2026-04-06 | Spiked a `/engrave` Claude Code skill (Claude Vision OMR only) — parked when Vision OMR proved too inaccurate on orchestral scores |
| 2026-05-22 | Phase 4 session — built full `tools/omr` pipeline: pitch / rhythm / voicing / line detection / LilyPond + MusicXML exporters / 156 tests / real-world validation on 5 PDFs. F1 98.8% on Bach WTC verdicts. |
| 2026-05-23 | Phase 1 connectivity-aware barline acceptance for orchestral pages + cross-cell tie pairing + voice splitting via `<backup>` + octave-clef pitch support |
| 2026-05-23 | **Consolidation.** Pruned 460MB of stale benchmark overlay dumps, merged YOLO pipeline into main. Local YOLO becomes primary OMR engine, Claude Vision OMR secondary, Audiveris removed entirely. Gradus library + multi-source XML comparison + theory checks landed in the same merge. |
| 2026-05-23 → 05-25 | **Catalog-training experiment** (Phases A–L, branch `claude/interesting-curran-3ca1b7`): IMSLP × MusicXML label generation worked (65/65 editions, 154k labels); every training attempt collapsed (H, I, J, K, L). Conclusion: stick with classical CV for structure + hand-labeling for symbols. Never merged. |
| 2026-05-24 | **Maestro theory layer shipped** (M0–M4 + follow-ups A/B, on main): bridge CLI, harmony/rhythm validation, scholarly cross-check (5 seed works), in-pipeline pitch re-ranking with auto-correction, wired into both OMR engines behind env flags. |
| 2026-06-08 → 06-10 | **Hand-labeling round on Beethoven 5.** Draw-from-scratch labeling mode + box delete (commit 1fe5484). Label set `v2-2026-06-08-beet5` (37 cells) created; v1 cleaned of structural-element boxes. Batches: 05-24 ✅ (became v2), 06-09 ✅ (35/36, not yet converted), 06-10 in progress (21/36), 06-08 abandoned. |
| 2026-06-10 | **Process audit** — docs refreshed, stale worktrees/branches pruned, orphaned label data committed. |
| 2026-07-10 | **Research round + reality check.** VLM narrow-VQA pilot NO-GO on all 6 question types (best 89.7% vs a 95% bar, on real degraded scans). nc=214 catalog footgun defused. Dead pipeline signals wired up. Anthropic SDK 0.28 → 0.116 with structured outputs. |
| 2026-07-10/11 | **Time-signature + clef inference layer.** Beat-sum meter inference, dominant C/cut-C propagation, clef continuity by staff role across systems, left-edge misread filter. The detection-confidence probe establishes the orchestral wall as a **domain gap**, not a threshold problem. |
| 2026-07-11/12 | **Internal-consistency layer** — five deterministic cross-staff checks (a–e), zero hand input, abstain-by-design. Capstone: `docs/internal-consistency-checks.md`. Dossier-guided verification design brief written. |
| 2026-07-13 | **Domain augmentation disproven.** A fair 3-way fine-tune test (ScoreAug/Augraphy vs clean control vs production) put dense real-cell notehead recall at 0.652 production → 0.384 clean → **0.122 augmented**. The augmented arm scored *best* on synthetic validation and *worst* on real pages — synthetic validation is misleading here. |
| 2026-08-27/28 | **Geometry layer.** Clef read by which staff line it names rather than by glyph class (alto/tenor are the same glyph); CV C-clef locator; measured staff-header window fixing the silent `x_start` failure; positional key-signature reader + cross-page vote; `clef_source` provenance; body-text paragraphs no longer detected as staves. **Phase-1 test expectations corrected against the pages themselves**, retiring the "no regression baseline" objection that had deferred Phase-1 fixes for months. |
| 2026-08-28 | **Contextual analysis** (branch, unmerged): systems by connectivity, instrument identity from the PDF text layer, stable part slots, clef from instrument range. Clef-from-key-fit measured and **disproven** — a staff's note geometry is clef-invariant. |

---

## What's parked / next up

**Immediate (2026-08-28):**

1. **Merge in dependency order** — `recognition-improvement-next` (better staff
   detection, upstream of everything), then re-run the contextual branch's benchmarks,
   then merge it. Then `clef-phase0-eval` for its hand-drawn labels.
2. **Finish instrument identity for scans.** Instrument names currently come free from a
   PDF text layer, which only 18 of 65 corpus PDFs have. An OCR or VLM reader on the
   margin crop takes that from ~28% of scores to most of them, and it multiplies the
   value of the whole slot/clef/range chain.
3. **Fix the one-line percussion staff.** It shifts every slot below it. The old reason
   for deferring it (no Phase-1 regression baseline) no longer applies.
4. **Infer the key signature from the music.** Beethoven 5 p15 reads no accidentals for a
   C-minor movement. Likely a *detection* not a *reading* failure, so it probably belongs
   with the positional key-signature reader rather than as a new layer.

**Live research directions:**

- **Dossier-guided verification** — hand-input known facts (instrumentation, key plan,
  meter, measure counts) to cross-check OMR as it runs. Slice 1 built on a branch; the
  design brief is `docs/dossier-verification-plan.md`. Contextual analysis makes the
  dossier partly **self-populating**, which removes its main cost.
- **End-to-end models as a host-side second opinion** (LEGATO, oemer, homr) — they read
  clef and meter contextually by construction. Bridge started on
  `claude/clef-time-signature-weights-6d6e38`.
- **MXL-guided auto-labeling** — resurrect the validated phase_e label emitter to
  pre-label the triage UI.
- **GKB access for OMR context**; **DoReMi + MUSCIMA++** training data; **multi-type
  barline classification**; **MusicXML repeat signs** (currently dropped on export).

**Closed with evidence — do not revive:**

- ~~Catalog-augmented YOLO training~~ — executed Phases A–L, collapsed every time.
- ~~ScoreAug/Augraphy domain augmentation~~ — fair 3-way test, augmented arm worst on real pages.
- ~~Clef-targeted YOLO fine-tune~~ — fixes clefs, collapses dense-page noteheads.
- ~~VLM as a symbol verifier~~ — 89.7% best case on real scans against a 95% bar.
- ~~Clef from tonal/key context~~ — four mechanisms, none beating an always-treble
  baseline; a staff's note geometry is clef-invariant.
- ~~Ensemble clef recognition~~ — *partly* overtaken: the clef half is solved by geometry.
  The time-signature half and cross-page state resets remain open.
- ~~YOLO training via symphony MusicXML × IMSLP editions~~ — executed and concluded.
- ~~Maestro Analyzer as theory-constraint layer~~ — shipped M0–M4 (2026-05-24).

---

## Repository layout (where to find things)

- **Web app entry:** [`backend/main.py`](backend/main.py) (all routes), [`frontend/src/App.tsx`](frontend/src/App.tsx) (all pages).
- **OMR pipeline:** [`tools/omr/`](tools/omr/) with [`tools/omr/README.md`](tools/omr/README.md) as the deep-dive.
- **Theory layer:** [`tools/maestro_bridge/`](tools/maestro_bridge/) (TypeScript CLI + `gradus` submodule), [`backend/modules/theory_layer.py`](backend/modules/theory_layer.py), [`backend/modules/maestro_bridge.py`](backend/modules/maestro_bridge.py), plan + results in [`docs/maestro-integration-plan.md`](docs/maestro-integration-plan.md).
- **Training:** [`tools/omr/training/`](tools/omr/training/). Cloud-GPU notes in `HANDOFF_PREMIUM_TRAINING.md` + `VAST_AI_SETUP.md`. Hand-labeled data: [`data/user-labeled/`](data/user-labeled/).
- **Benchmarks:** [`benchmarks/`](benchmarks/). The headline write-up is [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md).
- **Setup & operational reference:** [`CLAUDE.md`](CLAUDE.md).
- **Open ideas:** [`NOTES.md`](NOTES.md) — including the active **contextual analysis roadmap**.
- **Verification layers:** [`docs/internal-consistency-checks.md`](docs/internal-consistency-checks.md) (shipped) and [`docs/dossier-verification-plan.md`](docs/dossier-verification-plan.md) (planned).
- **Today's cross-session picture:** [`docs/state-of-play-2026-08-28.md`](docs/state-of-play-2026-08-28.md).

---

## How to run things (quick reference)

```bash
# Full web stack (requires omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt)
docker compose up -d
# → http://localhost

# Standalone OMR CLI (no Docker)
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly

# Theory layer (host-side; one-time setup)
git submodule update --init && (cd tools/maestro_bridge && npm install)
MAESTRO_BRIDGE_ENABLED=true MAESTRO_PITCH_RERANK_ENABLED=true python3 ... # see CLAUDE.md

# Hand-label more cells (full flow: CLAUDE.md → "Hand-label cells for OMR training")
python3 -m tools.omr.annotate.select_cells_orchestral --out-dir benchmarks/omr-labeling-NEW --plan "tag=/path/to/score.pdf:12:6"
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-NEW
# → http://127.0.0.1:5050

# Train a new YOLO checkpoint
python3 tools/omr/training/train_yolo.py
```

See [CLAUDE.md](CLAUDE.md) for the full operational reference.
