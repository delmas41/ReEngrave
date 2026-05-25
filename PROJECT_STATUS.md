# ReEngrave — Project Status

**Last updated:** 2026-05-23 (post-consolidation)

This document is a snapshot. For day-to-day reference docs see
[CLAUDE.md](CLAUDE.md). For parked research ideas see [NOTES.md](NOTES.md).

---

## Scope

**Personal-use only** (re-affirmed 2026-05-24). Sean is the sole user. The Stripe payment gate and multi-user infra are already built but no longer the optimization target — design decisions should minimize complexity and ongoing cost, not maximize generality. The only acceptable interaction surface for new tooling is Claude Code itself (Claude sessions running locally, calling Bash / Python / YOLO). No new long-running services / MCP servers / HTTP proxy routes / UI surfaces unless Sean explicitly promotes them.

## TL;DR

ReEngrave has **two converged tracks** of work now living together on `main`:

1. **A web app for music-score quality control** — upload a PDF, run OMR, review diffs, export. Auth + payments wired in. Built March 2026, iterated through April–May.
2. **An in-house YOLO + classical-CV OMR pipeline** — `tools/omr/`, fine-tuned on DeepScoresV2 (F1 98.8% on the Bach WTC verdict set). Built May 2026 across 49 commits / Phase 1 → Phase 4m.

Until 2026-05-23 these lived on different branches. They have now been merged. The local YOLO pipeline is the **primary OMR engine** in the web app; Claude Vision OMR is the **secondary** engine (one query-param flip).

---

## What works today

### End-to-end OMR (CLI)

```bash
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly  # → out.pdf
```

All 5 benchmark PDFs (Bach WTC, Mozart, Beethoven, Chopin, Debussy) produce LilyPond that compiles to PDF with **zero errors** — only bar-check warnings on measures whose summed durations don't match the time signature exactly. F1 98.8% on the 25-cell Bach WTC verdict set. See [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md) for the full Phase 4 story.

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
| `export.py` | JSON → LilyPond / MusicXML |
| `yolo_detector.py` | ultralytics YOLOv8l wrapper |
| `line_detection.py` | Classical-CV stems + beams (Phase 4f) |
| `rhythm.py` | Note durations from notehead class + beam count + flag pairing + dots |
| `voicing.py` | Same-x notehead chord grouping + stem-direction voice splitting |
| `pitch_resolver.py` | Notehead y-position → diatonic pitch, with key sig + inline accidentals |
| `staff_detector.py` | 5-line staff detection via horizontal projection clustering |
| `measure_extractor.py` | Barline detection + canonical-cell extraction |
| `preprocessing.py` | PDF → PageImage (render, binarize, deskew) |
| `staff_line_removal.py` | Optional staff-removed cell variant |
| `annotate/` | FastAPI labeling UI for hand-labeled cells |
| `training/` | DSv2 prep + ultralytics training scripts |
| `tests/` | 156 unit tests |

---

## What does not yet work / known limitations

**OMR**

- **Custom YOLO classes (barlines, textDynamic) caused catastrophic forgetting.** Phase 3.4 expanded `nc` from 208 → 214; F1 collapsed to 79.3%. Currently: barlines via classical CV; textDynamic not detected. Re-introduce when there are 200+ examples per new class or seed with synthetic warm-up. See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.
- **MusicXML voice-splitting via `<backup>` is not implemented** in `tools.omr.export.to_musicxml()`. MusicXML output is single-voice-per-part. LilyPond output handles two-voice blocks via stem-direction inference.
- **OMR time-signature digit detection is unreliable** — the DSv2 model often misclassifies digit glyphs, so `time_signature` is `null` for many pages.
- **Per-measure beat sums on busy keyboard music** are close to but not exactly the time signature — LilyPond bar-check warnings typically report fractional offsets (1/32, 3/32) rather than full-beat errors.
- **Dense orchestral conductor's scores** (Mahler 5, Debussy La Mer) have more false negatives on small dynamics + grace notes. Path forward: hand-label more cells via `tools/omr/annotate`.
- **Earlier feedback (47 days ago) said Claude Vision OMR is too inaccurate for orchestral scores.** The local YOLO pipeline did not exist at that time. The current primary engine is local YOLO, which has been validated on orchestral pages.

**Web app**

- **MusicXML correction patching is a stub.** Accepted diffs are written as XML comments, not actual measure replacements. Real patching is the biggest remaining web-app TODO.
- **PDF.js crop region in `DiffCard` is incomplete** — full crop viewport implementation has a TODO.
- **No database migrations.** Schema changes require dropping the DB.
- **Background tasks use FastAPI `BackgroundTasks` (no queue).** Server restart during a long OMR job loses the job. For production scale → Celery + Redis.
- **Frontend type field names still say "audiveris"** (`audiveris_confidence`, `min_audiveris_confidence`, `pattern_type: 'audiveris_failure'`). They now refer to the primary OMR engine; rename when there's a migration story.

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
| 2026-05-23 | **Consolidation.** Pruned 460MB of stale benchmark overlay dumps, merged YOLO pipeline into main. Local YOLO becomes primary OMR engine, Claude Vision OMR becomes secondary, Audiveris removed entirely. Gradus library + multi-source XML comparison + theory checks landed in the same merge. |

---

## What's parked / next up (from NOTES.md)

- **YOLO training via symphony MusicXML × multiple IMSLP editions.** Avoid hand-labeling ~500 cells for measure-line detection by using symphony MusicXML as ground truth (authoritative for measure boundaries, stem direction, rhythm), then pulling every available IMSLP edition of the same symphonies and training YOLO by comparing detections against the XML. Includes a publisher/era axis as a transfer-learning hypothesis (Breitkopf & Härtel 1862–1890 etc.).
  - Limit: MusicXML lacks dynamics, expression, articulation — this is **only useful for structural classes**.
  - Status: parked. Surface at the start of the next ReEngrave session.

### Plans recovered 2026-05-24 from past sessions

Seven items Sean had proposed across earlier YOLO sessions that hadn't carried into the active plan. Full quotes + scoping notes in [NOTES.md](NOTES.md).

1. **Maestro Analyzer as a theory-constraint layer over OMR** — wire `gradus-vercel/lib/maestroAnalyst/` in to verify harmony, beat mapping, and scholarly cross-check. Scoped 2026-05-24 → see [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md). Personal-use constraint locks the shape to a Bun CLI + thin Python wrapper; no HTTP server, no MCP, no UI changes. Next action: M0 (Bun script + submodule + harmony capability, ~1 day).
2. **GKB access for OMR context** — composer/period/harmonic-vocabulary knowledge. Bounded by item 1.
3. **DoReMi + MUSCIMA++ training data** — expand beyond DSv2.
4. **RTMDet / yolov8x@200ep escalation** — current weights stop at yolov8l@30ep; Sean already approved the full run.
5. **Multi-type barline classification** — single / double / final / repeat instead of one class.
6. **MusicXML repeat signs** — currently dropped on export.
7. **"Just ink" as a label class** — needs 5-minute verification in the annotate UI.

See [NOTES.md](NOTES.md) for the full note.

---

## Repository layout (where to find things)

- **Web app entry:** [`backend/main.py`](backend/main.py) (all routes), [`frontend/src/App.tsx`](frontend/src/App.tsx) (all pages).
- **OMR pipeline:** [`tools/omr/`](tools/omr/) with [`tools/omr/README.md`](tools/omr/README.md) as the deep-dive.
- **Training:** [`tools/omr/training/`](tools/omr/training/). Cloud-GPU notes in `HANDOFF_PREMIUM_TRAINING.md` + `VAST_AI_SETUP.md`.
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

# Hand-label more cells (open-loop labeling UI)
python3 -m tools.omr.annotate.select_cells path/to/score.pdf
python3 -m tools.omr.annotate.server
# → http://localhost:8001

# Train a new YOLO checkpoint
python3 tools/omr/training/train_yolo.py
```

See [CLAUDE.md](CLAUDE.md) for the full operational reference.
