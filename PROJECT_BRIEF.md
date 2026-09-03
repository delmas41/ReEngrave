# ReEngrave — Project Brief

**One line:** turn a scanned PDF of a music score into correct MusicXML / LilyPond,
using an in-house YOLOv8 + classical-CV OMR pipeline, checked against reference
encodings and, where needed, a human.

**Owner:** Sean (sole user; personal-use scope re-affirmed 2026-05-24).
**Reference docs:** [CLAUDE.md](CLAUDE.md) (how everything works, the current
accuracy figure), [PROJECT_STATUS.md](PROJECT_STATUS.md) (narrative snapshot),
[NOTES.md](NOTES.md) (backlog), [version_memory.md](version_memory.md)
(running change list).

## Why it exists

Published OMR fails on real orchestral scans. The project measures that
failure with a metric other people report (OMR-NED, via musicdiff), fixes the
pipeline one evidenced fault at a time, and never lands a change without a
number on both sides.

## What is built

- **OMR pipeline** (`tools/omr/`): staff and measure segmentation, YOLO symbol
  detection, classical-CV stems and beams, header readers for clef, key and
  meter by geometry, rhythm and voicing, contextual part naming, and exporters
  to MusicXML and LilyPond. CLI: `python3 -m tools.omr.transcribe score.pdf`.
- **Ground truth and benchmarks**: an eleven-work engraved orchestral benchmark
  (`benchmarks/omr-orchestral-e2e/`), a five-page scan benchmark
  (`benchmarks/omr-scan-e2e-2026-09/`), dossiers for 97 works, and a central
  score library of 235 editions and 1745 reference encodings
  (`data/score-library/`).
- **Hand-labeling tooling** (`tools/omr/annotate/`): triage, draw-from-scratch
  and single-symbol pass modes, verdict files that convert to YOLO labels
  (`data/user-labeled/`, versions v1–v7).
- **Web app** (`backend/`, `frontend/`): upload, OMR, vision diff review,
  export; auth and Stripe wired but no longer the optimization target.

## Where the work is now (2026-09-02)

- Engraved benchmark: pooled OMR-NED **0.1306 / 2745 edits** over 11 works.
- Scan domain: hollow noteheads are the top lever; a five-batch labeling
  campaign is cut, one batch labeled.
- MXL-guided auto-labeling is **built and unit-tested, not yet measured on a
  real batch**: `tools/omr/training/mxl_verdicts.py` confirms or relabels the
  detector's boxes from the reference and queues the rest for a human. The
  first measurement (`--score` on the Mahler 5 / Peters batch) decides whether
  its `TP`s can be admitted without review. Inventory and plan:
  [docs/status-brief-2026-09-02-labeling-and-training.md](docs/status-brief-2026-09-02-labeling-and-training.md).

## Rules of the road

- Every change is measured on the benchmark before and after; refused ideas
  are recorded with their numbers.
- The accuracy figure lives in one generated place (CLAUDE.md, from
  `benchmarks/omr-ned-2026-08/current-accuracy.json`).
- Hand-labeled verdicts are irreplaceable; commit them.
- Training runs are gated on `tools/omr/training/wtc_forgetting_eval.py`.
