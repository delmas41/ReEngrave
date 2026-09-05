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
  hints carry both (5 conflicts on 4 cells; all five reviewed 2026-09-03 and
  none is live — three are the reference's tie-split fragments of one printed
  note, two are accidental glyphs misdetected as heads, and the existing
  human verdicts were already right on every cell). Measured against a complete
  human pass on six cells: **precision 0.84**, so the pre-fill is a queue
  rather than labels for now — six of its eight errors are detection box
  placement, which means its accuracy rises as recognition does. A follow-up
  measurement (`benchmarks/omr-prefill-admission-2026-09/`) showed the eight
  errors are separable by three cheap signals (cell parity consistency, a
  small-head veto, the reference's own line/space variant) — in-sample the
  clean subset reaches 37/37 at 74% coverage, pending an unbiased re-test.
  The first half of that plan now lives in the pre-fill itself: the variant
  follows the reference on exact pairs, tie-split encodings collapse to the
  one printed head, and every pre-filled box carries a labels/queue
  admission tier that `--score` prices (six-cell precision 0.84 → 0.88,
  labels tier 22/22; still metadata until a random pass re-tests it). Better
  weights then lifted the same measurement to **0.96 exact with no pre-fill
  change** — the clearest evidence yet that this approach improves for free
  as recognition does, which is the reason to keep investing in it. All of
  those figures come from the same six cells, chosen as the ones the pre-fill
  decided most. ⚠️ **That measurement has now been made and it came back
  negative: on a pre-registered random sample labeled blind, precision falls
  to 0.84 (0.92 pooled over 141 boxes), under the 0.97 bar set in advance —
  so pre-filled boxes stay a review queue and are not admitted as labels.**
  The rest of this paragraph describes how that measurement was set up: a
  **pre-registered random
  sample of 25 cells labeled blind** (the UI can now withhold its own hints,
  since a human shown them cannot measure them). That sample is registered
  and waiting on labeling time; it is the step that would turn pre-filled
  boxes from a review queue into labels. A batch checked out on a machine
  that did not cut it has no cell images (they are gitignored) and shows a
  blank canvas; `tools/omr/annotate/recut_cells.py` re-renders them from the
  manifest, refusing anything whose frame does not match. Where the work stands and
  Sean's checklist: [docs/handoff-2026-09-03-prefill-session.md](docs/handoff-2026-09-03-prefill-session.md).

## Decisions made without a probability (2026-09-05)

Work on clef assignment found that a lot was being lost because a staff's clef
was either *selected* or *discarded* — no middle ground, and no way to combine
the several things the page already knew. A scan of the rest of the recognition
pipeline found the same shape in five distinct forms, written up in
[docs/handoff-probability-gates-2026-09-05.md](docs/handoff-probability-gates-2026-09-05.md).

The two largest findings are both "the number exists and nothing reads it". The
exporter never consults a detection's confidence at all — a symbol recognised
with 26% certainty and one recognised with 98% certainty are written out as
equally true. And the five self-consistency checks, which already grade how
strongly a page contradicts itself, are read by nothing: on one real scanned
score, 85 such signals fire and every one is inert.

The practical payoff is a ranked shortlist of seven places where a graded answer
would replace a yes/no one, each with an estimate of how much it touches and
which existing measurement could prove it helped. The first item goes straight
back to the clef work: a register-inversion check already fires on the same page
and is never consulted, and unlike the range test it needs no instrument name —
which matters, because on real scans the names usually are not printed.

⚠️ Nothing in that document is a measured result; it is a survey that says what
to measure next.

## Beyond the current scope (captured 2026-09-05)

One long-range idea is recorded at the top of [NOTES.md](NOTES.md) rather than
here, because it is far off and unscheduled: pairing **recordings** with the
notes on the page, so that a score written from scratch could be rendered as an
emulated orchestral performance. The distinction that makes it worth keeping is
that the composer supplies the music and the model supplies only the
performance — a rendering problem, not a generative one, and therefore
measurable in the same way OMR is.

It is noted here for one reason: the thing that would make ReEngrave uniquely
able to attempt it is not audio work at all, but the **expressive layer of the
page** — slurs, hairpins, articulations, printed directions — which the project
has already spent a month learning to read because those marks were costing
accuracy. Nothing is scheduled, and nothing in the entry is a measured result.

## Running it

- **Web app:** `docker compose up -d` → http://localhost
- **CLI:** `python3 -m tools.omr.transcribe score.pdf` — no Docker needed
- **Production:** a self-hosted VPS via `scripts/deploy.sh` +
  `docker-compose.prod.yml` (Traefik, Let's Encrypt). This is the deploy
  path actually in use — see the note in `version_memory.md` about the
  unused/disabled GitHub Actions Vercel+Railway workflow.

Full setup and environment variables: CLAUDE.md → "Running locally" and
"Environment variables".
