# ReEngrave — Project Brief

**Owner:** Sean Johnson (sole user — see "Scope" in [PROJECT_STATUS.md](PROJECT_STATUS.md))
**Status:** Active development, personal-use scope

## What it is

ReEngrave takes a scanned PDF of a music score, runs optical music
recognition (OMR) to produce MusicXML, then checks the result — either
against itself (theory rules), against a known-good reference score, or
against the original PDF page-by-page with Claude Vision — and lets a human
accept, reject, or edit each flagged difference. The corrected score exports
as MusicXML, LilyPond, or an engraved PDF.

Full technical reference, architecture, and the day-to-day working notes
live in [CLAUDE.md](CLAUDE.md). This brief is the short version: what the
project is for and where it stands, not how the code works.

## The two things being built

1. **A web app** (FastAPI + React, Docker Compose) — upload a PDF, run OMR,
   review diffs, export. Auth and a Stripe payment gate are wired in but not
   the optimization target: Sean is the only user, so new work should
   minimize complexity and cost rather than build for a wider audience.
2. **An in-house OMR pipeline** (`tools/omr/`) — YOLOv8l + classical CV,
   fine-tuned on DeepScoresV2. This is where most of the recent engineering
   effort has gone: reading orchestral conductor's scores accurately is
   hard, and the project has been steadily closing the gap between "reads
   an engraved page" and "reads a real 19th-century scan."

A third, optional piece — the **Maestro theory layer**
(`tools/maestro_bridge/`) — adds harmony/rhythm validation and pitch
re-ranking against music-theory rules. Host-side only, off by default.

## How progress is measured

The project adopted **OMR-NED** (the metric used in published OMR research)
in August 2026 so its accuracy numbers are comparable to outside work, not
just to its own history. The current figure and the benchmark it's measured
on are documented in one place — the OMR-NED section of CLAUDE.md — and a
test fails if that figure drifts out of sync with the recorded JSON. Don't
requote it elsewhere; link to that section instead.

## Where things stand

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current snapshot (updated
most recently 2026-09-02) and [NOTES.md](NOTES.md) for the backlog of
research ideas not yet scheduled. Both are living documents — check them at
the start of a session rather than trusting this brief for anything that
changes week to week.

## Where the work is now (2026-09-03)

- Engraved benchmark: pooled OMR-NED **0.1306 / 2745 edits** over 11 works
  (the figure lives in CLAUDE.md's OMR-NED section; do not requote it).
- Scan domain: hollow noteheads are the top lever. All five round-2
  hollow-notehead batches are labeled, and the gated training run (Sean,
  2026-09-02) says the labels **work** — half-note detection 8 → 25 — while
  the dense-page narrowing is the fine-tune recipe's, not the labels'. v8
  stays out of the catalog until an imgsz-matched fine-tune re-gates it
  (`benchmarks/omr-labeling-survey-2026-09/GATE_RESULTS.md`).
- MXL-guided auto-labeling (`tools/omr/training/mxl_verdicts.py`) is built,
  unit-tested, and measured once on the Brahms 1 / Breitkopf batch: 51 of 56
  cells pre-filled. Its hollow-notehead signal on that print is weak because
  the reference spells out tremolo abbreviations as repeated eighths where
  the page prints one hollow head; see `version_memory.md` for the numbers.
  Inventory and plan: [docs/status-brief-2026-09-02-labeling-and-training.md](docs/status-brief-2026-09-02-labeling-and-training.md).
- Tremolo and tremolando abbreviations are reconciled by the reading (one
  head for a repeated pitch, two for an alternating pair) and a hollow-vs-black
  disagreement is routed to the human as a `CONFLICT` — the committed Brahms
  hints carry both (5 conflicts on 4 cells). Measured against a complete
  human pass on six cells: **precision 0.84**, so the pre-fill is a queue
  rather than labels for now — six of its eight errors are detection box
  placement, which means its accuracy rises as recognition does. A follow-up
  measurement (`benchmarks/omr-prefill-admission-2026-09/`) showed the eight
  errors are separable by three cheap signals (cell parity consistency, a
  small-head veto, the reference's own line/space variant) — in-sample the
  clean subset reaches 37/37 at 74% coverage, pending an unbiased re-test. A batch checked out on a machine
  that did not cut it has no cell images (they are gitignored) and shows a
  blank canvas; `tools/omr/annotate/recut_cells.py` re-renders them from the
  manifest, refusing anything whose frame does not match. Where the work stands and
  Sean's checklist: [docs/handoff-2026-09-03-prefill-session.md](docs/handoff-2026-09-03-prefill-session.md).

## Running it

- **Web app:** `docker compose up -d` → http://localhost
- **CLI:** `python3 -m tools.omr.transcribe score.pdf` — no Docker needed
- **Production:** a self-hosted VPS via `scripts/deploy.sh` +
  `docker-compose.prod.yml` (Traefik, Let's Encrypt). This is the deploy
  path actually in use — see the note in `version_memory.md` about the
  unused/disabled GitHub Actions Vercel+Railway workflow.

Full setup and environment variables: CLAUDE.md → "Running locally" and
"Environment variables".
