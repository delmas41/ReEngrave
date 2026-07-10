# ReEngrave — Project Status

**Last updated:** 2026-06-10 (process audit)

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

**Current activity (June 2026): hand-labeling round to improve the model on dense orchestral scores.** Labeling sessions ran 2026-06-08 → 06-10 (Beethoven 5); a draw-from-scratch labeling mode landed 2026-06-09; label set `v2-2026-06-08-beet5` (37 cells) was produced, and v1 labels were cleaned to the current doctrine (structural elements — staff lines / stems / beams — are no longer boxed; they're classical-CV's job).

---

## What works today

### End-to-end OMR (CLI)

```bash
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly  # → out.pdf
```

All 5 benchmark PDFs (Bach WTC, Mozart, Beethoven, Chopin, Debussy) produce LilyPond that compiles to PDF with **zero errors** — only bar-check warnings on measures whose summed durations don't match the time signature exactly. F1 98.8% on the 25-cell Bach WTC verdict set. See [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md) for the full Phase 4 story.

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
| `annotate/` | FastAPI labeling UI — triage mode + draw-from-scratch mode (2026-06-09) |
| `training/` | DSv2 prep + ultralytics training scripts |
| `tests/` | 156 unit tests |

### Hand-labeled training data (`data/user-labeled/`)

| Version | Cells | Content |
|---|---|---|
| `v1-2026-05-18-orchestral` | 60 | Beet 5 + Mahler 5 orchestral cells; cleaned 2026-06 to remove structural-element boxes (staff/stem/beam → background) |
| `v2-2026-06-08-beet5` | 37 | Beethoven 5 pp. 45–75; heavy FP-drop batch (480 FPs dropped, 37 FNs added) |

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

Audit 2026-06-10. Five branches hold commits absent from main:

| Branch | Commits | What it has | Disposition |
|---|---|---|---|
| `claude/interesting-curran-3ca1b7` | 43 | Catalog experiment Phases A–L (above) **plus** 2026-05-25 `line_detection` improvements (beam fragment-merge + NMS dedup, cell-width filter, notehead-anchored stems, clef masking) and a stem-precision benchmark UI | Evaluate the line_detection + benchmark commits for cherry-pick; keep branch as the experiment's archive |
| `claude/gallant-hellman-29ffdd` | 3 | Per-class OMR improvements: grammar verification, phantom-rest corrector, imgsz ensemble `[1280, 2048]` in hand-labeling pre-label runs | Evaluate for cherry-pick (overlaps with curran's ensemble commit) |
| `claude/magical-bhabha` | 1 (March) | **Real MusicXML measure-level patching in `export_module`** — an implementation of what docs list as the #1 web-app TODO | Pre-consolidation code; evaluate against current export_module before deciding |
| `claude/peaceful-kapitsa` | 1 (March) | SQLite-backed persistent job queue replacing FastAPI BackgroundTasks — another listed limitation | Same: pre-consolidation; evaluate or discard |
| `claude/quizzical-bell` | 1 (April) | The parked `/engrave` skill (Claude Vision-only OMR) | Superseded by local YOLO; backed up on origin; safe to delete |

---

## What does not yet work / known limitations

**OMR**

- **Custom YOLO classes (barlines, textDynamic) caused catastrophic forgetting.** Phase 3.4 expanded `nc` from 208 → 214; F1 collapsed to 79.3%. Currently: barlines via classical CV; textDynamic not detected. Re-introduce when there are 200+ examples per new class or seed with synthetic warm-up. See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.
- **OMR time-signature digit detection is unreliable** — the DSv2 model often misclassifies digit glyphs, so `time_signature` is `null` for many pages.
- **Per-measure beat sums on busy keyboard music** are close to but not exactly the time signature — LilyPond bar-check warnings typically report fractional offsets (1/32, 3/32) rather than full-beat errors.
- **Dense orchestral conductor's scores** (Mahler 5, Debussy La Mer) have more false negatives on small dynamics + grace notes. Path forward: the active hand-labeling rounds via `tools/omr/annotate`.

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

---

## What's parked / next up

Immediate (from the current labeling round):

1. **Finish the 2026-06-10 labeling batch** (21/36 verdicts done), then convert the finished 06-09 + 06-10 batches → `v3` via `verdicts_to_yolo_labels` + rebuild the catalog.
2. **Retrain / fine-tune on v1+v2(+v3)** and re-evaluate on the verdict sets. (2026-07-10: the committed `catalog.yaml` is now capped at nc=208 — custom-class boxes filtered via `_nc208/` — and `train_yolo.py` fails fast on an nc mismatch with the checkpoint, so this retrain can no longer silently re-trigger the Phase 3.4 head-reset collapse.)
3. **Decide the fate of the unmerged branches** (table above) — especially the `line_detection` improvements and the two March web-app implementations.

Parked (carried from NOTES.md — see there for full context):

- **GKB access for OMR context** — natural follow-on now that the maestro bridge exists.
- **DoReMi + MUSCIMA++ training data** — expand beyond DSv2.
- **RTMDet / yolov8x@200ep escalation** — Sean already approved the full run.
- **Multi-type barline classification** — single / double / final / repeat (classical-CV post-processing is the likely route).
- **MusicXML repeat signs** — currently dropped on export.
- **"Just ink" label class** — verified 2026-06-10: the annotate UI does **not** expose a noise/ink class. Add one if hard-negative-by-omission proves insufficient.
- ~~YOLO training via symphony MusicXML × IMSLP editions~~ — **executed and concluded** (see catalog-experiment section).
- ~~Maestro Analyzer as theory-constraint layer~~ — **shipped M0–M4** (2026-05-24).

---

## Repository layout (where to find things)

- **Web app entry:** [`backend/main.py`](backend/main.py) (all routes), [`frontend/src/App.tsx`](frontend/src/App.tsx) (all pages).
- **OMR pipeline:** [`tools/omr/`](tools/omr/) with [`tools/omr/README.md`](tools/omr/README.md) as the deep-dive.
- **Theory layer:** [`tools/maestro_bridge/`](tools/maestro_bridge/) (TypeScript CLI + `gradus` submodule), [`backend/modules/theory_layer.py`](backend/modules/theory_layer.py), [`backend/modules/maestro_bridge.py`](backend/modules/maestro_bridge.py), plan + results in [`docs/maestro-integration-plan.md`](docs/maestro-integration-plan.md).
- **Training:** [`tools/omr/training/`](tools/omr/training/). Cloud-GPU notes in `HANDOFF_PREMIUM_TRAINING.md` + `VAST_AI_SETUP.md`. Hand-labeled data: [`data/user-labeled/`](data/user-labeled/).
- **Benchmarks:** [`benchmarks/`](benchmarks/). The headline write-up is [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md).
- **Setup & operational reference:** [`CLAUDE.md`](CLAUDE.md).
- **Open ideas:** [`NOTES.md`](NOTES.md).

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
