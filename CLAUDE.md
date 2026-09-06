# ReEngrave — CLAUDE.md

## What this project is

ReEngrave is a system for music score quality control. It takes a scanned PDF of a music score, runs optical music recognition (OMR) to produce MusicXML, then either:

1. **Auto-checks** the MusicXML against itself (theory checks) or against a known-good reference in the Gradus Library (multi-source XML comparison), **or**
2. **Vision-checks** each measure of the original PDF against the re-engraved output with Claude Vision and flags differences for a human to accept / reject / edit.

The corrected MusicXML is then exported as `.musicxml`, LilyPond `.ly`, or an engraved PDF.

Over time the analytics layer learns from human decisions, building auto-accept rules for patterns it has seen before.

**Two ways to use the project:**

| Use it from | Entry point | Best for |
|---|---|---|
| **Web app** | `docker compose up -d` → http://localhost | Reviewing scores, comparison sessions, payment-gated multi-user setup |
| **CLI** | `python3 -m tools.omr.transcribe score.pdf` | Batch transcription, scripting, anyone who just wants `PDF → MusicXML / LilyPond` without spinning up Docker |

**Stack:**
- **OMR (primary):** In-house YOLOv8l + classical CV pipeline (`tools/omr/`) — fine-tuned on DeepScoresV2, **F1 98.8%** on the Bach WTC verdict set.
- **OMR (secondary):** Claude Vision API (Opus 4.6) — reads pages visually, slower, costs API credits, useful when the YOLO model is wrong.
- **Backend:** FastAPI + SQLAlchemy 2.0 async + SQLite (aiosqlite) + Claude Vision API + Verovio + LilyPond + music21 + ultralytics
- **Frontend:** React + Vite + React Query + TypeScript
- **Container:** Docker Compose (local) + Traefik (production, SSL via Let's Encrypt)

**Backlog / research notes:** see [NOTES.md](NOTES.md) — surface these at the start of a ReEngrave session.

**Where the work stands today:** see [PROJECT_STATUS.md](PROJECT_STATUS.md).

**Short project overview (non-technical):** see [PROJECT_BRIEF.md](PROJECT_BRIEF.md).

**Running changelog of changes made:** see [version_memory.md](version_memory.md) — update alongside this file and PROJECT_BRIEF.md after every commit. Labeling / training-system status as of 2026-09-02: [docs/status-brief-2026-09-02-labeling-and-training.md](docs/status-brief-2026-09-02-labeling-and-training.md). Session handoff for the pre-fill work, 2026-09-03: [docs/handoff-2026-09-03-prefill-session.md](docs/handoff-2026-09-03-prefill-session.md) — read it first in a fresh session.

---

## Running locally

```bash
cd /Users/seanjohnson/Desktop/ReEngrave

# Start everything (backend + frontend)
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild after code changes
docker compose build backend   # or frontend
docker compose up -d backend   # or frontend
```

Site runs at **http://localhost**. Backend API at **http://localhost:8000**.

**Important:** `docker compose restart` does NOT pick up `.env` changes. Use `docker compose up -d` (which recreates the container) instead.

### OMR weights (required before first run)

The local OMR pipeline needs a YOLOv8l weights file (`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, ~88 MB). It's gitignored.

```bash
# docker-compose mounts /Users/seanjohnson/Desktop/ReEngrave/omr-weights/ → /app/tools/omr/training/data/weights/
ls /Users/seanjohnson/Desktop/ReEngrave/omr-weights/
# Should contain: deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt  (current
#   production, scans + routing default; the prior deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt
#   and deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt are kept alongside — weight
#   routing serves the imgsz2048 file for digitally engraved input, see OMR_WEIGHT_ROUTING)
```

If the file is missing, OMR jobs fail fast with a clear error in `Score.metadata_json['omr_error']`. The web app still works for direct MusicXML uploads and the Gradus / comparison flows.

### Theory layer (optional, host-side)

The Maestro theory layer needs the `gradus` submodule + node deps — only required if you set `MAESTRO_BRIDGE_ENABLED` / `MAESTRO_PITCH_RERANK_ENABLED`:

```bash
git submodule update --init
cd tools/maestro_bridge && npm install
```

### Hot-patching without a full rebuild

For quick backend iteration, copy files directly into the running container and restart uvicorn:

```bash
docker cp backend/modules/some_module.py reengrave-backend-1:/app/modules/some_module.py
docker cp tools/omr/transcribe.py reengrave-backend-1:/app/tools/omr/transcribe.py
docker restart reengrave-backend-1
```

For frontend changes, a full `docker compose build frontend && docker compose up -d frontend` is required (Vite bakes env vars at build time).

### Default login

Register at http://localhost/register. To give yourself admin access (bypasses the Stripe payment gate), add your email to `backend/.env`:

```
ADMIN_EMAILS=you@example.com
```

Then `docker compose up -d backend` to reload.

---

## Project structure

```
ReEngrave/
├── backend/
│   ├── main.py                  # FastAPI app, all routes
│   ├── dependencies.py          # get_current_user() Depends
│   ├── requirements.txt         # FastAPI + ultralytics + opencv + PyMuPDF + music21 …
│   ├── Dockerfile               # python:3.11-slim + LilyPond + opencv runtime
│   ├── .env                     # local secrets (never commit)
│   ├── .env.production.example  # template for prod deployment
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (reads .env)
│   │   ├── security.py          # JWT + bcrypt helpers
│   │   └── limiter.py           # slowapi rate limiter
│   ├── database/
│   │   ├── models.py            # SQLAlchemy ORM + Pydantic response schemas
│   │   └── connection.py        # async engine, get_db() dependency
│   ├── modules/
│   │   ├── local_omr.py         # Primary OMR: thin wrapper around tools.omr
│   │   ├── claude_vision_omr.py # Secondary OMR: Claude Vision → JSON → MusicXML
│   │   ├── musicxml_builder.py  # JSON → MusicXML serializer (used by Vision OMR)
│   │   ├── score_comparison.py  # music21-backed comparison + theory checks
│   │   ├── claude_vision.py     # Diff-flagging: PDF vs re-engraved → JSON diffs
│   │   ├── export_module.py     # MusicXML / LilyPond / PDF export dispatcher
│   │   ├── lilypond_engrave.py  # MusicXML → LilyPond → engraved PDF (fallback path)
│   │   ├── file_import.py       # save uploads, detect file type
│   │   ├── analytics.py         # self-improving pattern learning
│   │   ├── theory_layer.py      # env-gated Maestro enrichment + M4 pitch re-rank hooks
│   │   └── maestro_bridge.py    # subprocess bridge → tools/maestro_bridge (node/tsx, host-side)
│   └── routers/
│       ├── auth.py              # register, login, refresh, logout, /me
│       └── payments.py          # Stripe checkout + webhook
├── tools/
│   ├── maestro_bridge/          # Theory layer CLI (TypeScript) — see docs/maestro-integration-plan.md
│   │   ├── analyze.ts           # entry point: harmony / rhythm / cross-check / re-rank capabilities
│   │   ├── re-rank.ts           # M4 pitch re-ranking against detected key
│   │   ├── scholarly/           # curated reference analyses (5 seed works)
│   │   └── gradus/              # git submodule → github.com/delmas41/gradus (maestroAnalyst lives here)
│   └── omr/                     # In-house OMR pipeline (49-commit Phase 1 → 4m history)
│       ├── README.md            # Full pipeline + class space + CLI reference
│       ├── transcribe.py        # ENTRY POINT — PDF → structured JSON
│       ├── export.py            # JSON → LilyPond / MusicXML
│       ├── yolo_detector.py     # ultralytics YOLOv8l wrapper
│       ├── line_detection.py    # classical-CV stems + beams (Phase 4f)
│       ├── staff_header.py      # measures each staff's clef/key/time window
│       ├── header_ink.py        # shared header CV: traces staff lines off, clusters glyphs
│       ├── clef_geometry.py     # which line a clef names (measured, not classified)
│       ├── clef_locator.py      # CV C-clef finder for scores no model reads
│       ├── key_signature_geometry.py  # slot-table fit: read the positions, don't count
│       ├── key_signature_locator.py   # CV finder for the accidental run
│       ├── key_signature_vote.py      # reconcile readings across staves + systems
│       ├── dossier.py           # known facts per work + checks against them
│       ├── rhythm.py            # duration parsing (Phase 4c)
│       ├── voicing.py           # chord grouping, voice splitting
│       ├── pitch_resolver.py    # notehead y → pitch + accidental
│       ├── staff_detector.py    # 5-line staff detection
│       ├── measure_extractor.py # barline detection + cell extraction
│       ├── preprocessing.py     # PDF → PageImage (render, binarize, deskew)
│       ├── staff_line_removal.py # optional staff-line-removed cell variant
│       ├── visualize.py         # debug overlay PNGs
│       ├── types.py             # PageImage, Staff, MeasureCell, SymbolDetection
│       ├── annotate/            # FastAPI labeling UI for hand-labeled cells
│       ├── symbol_library/      # Bravura SMuFL archetype PNGs
│       ├── training/            # DSv2 prep + ultralytics training scripts
│       │   ├── train_yolo.py
│       │   ├── prepare_yolo_data.py
│       │   ├── build_catalog_yaml.py
│       │   ├── verdicts_to_yolo_labels.py
│       │   ├── build_dossiers.py       # MusicXML -> data/dossiers/*.json
│       │   ├── orchestral_eval.py      # Gradus MXL -> PDF -> OMR -> accuracy
│       │   ├── end_to_end_eval.py      # authored fixtures -> note accuracy
│       │   ├── eval_on_score_cells.py
│       │   ├── download_dataset.py
│       │   ├── merge_shards.py
│       │   ├── deepscores_classes.py
│       │   ├── HANDOFF_PREMIUM_TRAINING.md
│       │   ├── VAST_AI_SETUP.md
│       │   └── data/            # gitignored — DSv2 dataset, fine-tuning shards, weights
│       └── tests/               # 156 unit tests across Phase 4 modules
├── omr-weights/                 # gitignored, mounted into the container
│   ├── deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt  # ~88 MB — PRODUCTION (scans + routing default; head-graft + bias floor, shipped 2026-09-04)
│   ├── deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt      # ~88 MB — prior scan production (graft source's base; in-flight benchmarks pin it by path)
│   ├── deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt         # ~88 MB — engraved-routing target (prior production)
│   └── deepscoresv2-yolov8l-phase-j-mix-30ep.pt    # from the collapsed catalog run — DO NOT USE
├── data/
│   ├── user-labeled/            # hand-labeled YOLO training data (v1, v2, …) + catalog.yaml
│   └── dossiers/                # 97 generated per-work fact files (see "Dossiers")
├── docs/
│   └── maestro-integration-plan.md  # theory-layer plan + M0–M4 results
├── benchmarks/
│   ├── omr-phase1/              # staff/measure extraction
│   ├── omr-phase2.5/            # classical-CV vs YOLO bake-off
│   ├── omr-phase3/              # initial YOLO runs
│   ├── omr-phase3.1 .. 3.4b/    # iterative training rounds (F1 91.5% → 98.8%)
│   ├── omr-phase-realft/        # real-orchestral hand-labeled set (Phase 3.4)
│   ├── omr-phase4-extension/    # validate Phase 4 features on 5 PDFs
│   ├── omr-phase4-session/      # retrospective.md — full Phase 4 story
│   └── omr-real-world/          # 5 diverse PDFs end-to-end
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # routes + AuthProvider wrapper
│   │   ├── main.tsx             # React entry, QueryClient, BrowserRouter
│   │   ├── api/client.ts        # typed Axios client, JWT injection, auto-refresh
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   ├── types/index.ts       # TypeScript interfaces mirroring backend schemas
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # score library + analytics
│   │   │   ├── FileUpload.tsx   # upload PDF or MusicXML
│   │   │   ├── ScoreProcess.tsx # Step 1: ReEngrave (OMR — pick engine)
│   │   │   ├── ReviewUI.tsx     # Step 2: Vision comparison + diff review + theory checks
│   │   │   ├── Export.tsx       # Step 3: export score
│   │   │   ├── GradusLibrary.tsx # Reference XML library + multi-source comparison
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   └── PaymentSuccess.tsx
│   │   └── components/
│   │       ├── Navigation.tsx
│   │       ├── DiffCard.tsx     # single flagged diff with accept/reject/edit
│   │       ├── PDFjsRenderer.tsx
│   │       ├── VerovioRenderer.tsx
│   │       └── VisionComparisonPaywall.tsx
│   ├── nginx.conf               # serves SPA, proxies /api/ and /uploads/ to backend
│   └── Dockerfile
├── scripts/
│   ├── setup-vps.sh             # first-time Ubuntu server bootstrap
│   └── deploy.sh                # git pull → build → up -d
├── docker-compose.yml           # local dev
├── docker-compose.prod.yml      # production (Traefik + SSL)
├── NOTES.md                     # parked research / backlog
└── PROJECT_STATUS.md            # where we are right now
```

---

## The pipeline

```
[User] → Upload PDF (or open Gradus Library to upload reference MusicXML)
    ↓
[ScoreProcess page] → Pick engine → "ReEngrave" button
    → POST /api/scores/{id}/process/omr?omr_engine=local|claude_vision
    ┌──────────────────────────┐    ┌──────────────────────────────────┐
    │ local (default)           │    │ claude_vision                     │
    │ local_omr.run_local_omr() │    │ claude_vision_omr.run_…()         │
    │  → tools.omr.transcribe   │    │  → per-page Vision API calls      │
    │  → tools.omr.export       │    │  → musicxml_builder.write_…       │
    │     to_musicxml()         │    │                                   │
    │ Writes:                   │    │ Writes:                           │
    │  - {stem}.omr.json        │    │  - {stem}.musicxml                │
    │  - {stem}.musicxml        │    │ Supports per-page progress in UI  │
    └──────────────────────────┘    └──────────────────────────────────┘
    → Optional theory layer (host-side only, env-gated — see "Maestro theory layer"):
        MAESTRO_BRIDGE_ENABLED=true       → enrich result with key detection, rhythm
                                            validation, scholarly cross-check
        MAESTRO_PITCH_RERANK_ENABLED=true → M4: re-rank ambiguous pitches against the
                                            detected key + auto-correct (local engine only)
    → Score.musicxml_path set, Score.status = "review"
    ↓
[ReviewUI page] options:
    A. "Run Vision Comparison" (paid / admin)
       → POST /api/scores/{id}/process/compare
       → claude_vision.py:
            1. Verovio renders MusicXML pages → PNG
            2. pdf2image renders PDF pages → PNG
            3. Each page pair → Claude Vision (opus-4-6) → JSON diffs
            4. FlaggedDifference rows + snippet PNGs saved
       → Human reviews each diff: PATCH /api/diffs/{id}/decision

    B. "Run Theory Checks" (free)
       → POST /api/scores/{id}/theory-check
       → score_comparison.run_theory_checks(): rhythm, range, enharmonic
       → Returns issues list (no DB writes — informational)
    ↓
[Export page] → Choose format
    → GET /api/scores/{id}/export?format=lilypond|pdf|musicxml
    → export_module.py:
        - musicxml: copy + comment-stub corrections (TODO: real patching)
        - lilypond: if Score.metadata_json["omr_json_path"] exists →
                    tools.omr.export.to_lilypond() directly (skip musicxml2ly)
                    else MusicXML → musicxml2ly → .ly
        - pdf:      lilypond .ly → lilypond CLI → .pdf

[Gradus Library page] — parallel workflow
    Tab 1 (Library):  upload/view/delete master reference MusicXML
    Tab 2 (Compare):  upload 2–6 XMLs, optionally pin a Gradus master,
                       music21 measure-by-measure comparison → similarity
                       matrix + per-measure agreement report
    → POST /api/gradus/ (master upload)
    → POST /api/compare/ (session create, runs synchronously, 10–30s)
```

### OMR knobs (env-overridable on the backend container)

| Env var               | Default | What it tunes |
|-----------------------|--------:|---|
| `OMR_WEIGHTS_PATH`    | _(unset)_ | Pin ONE weights file for every input — this disables scan/engraved weight routing. Unset (the default) lets each run pick weights by input domain; see `OMR_WEIGHT_ROUTING`. |
| `OMR_WEIGHT_ROUTING`  | `1` (on)  | **On by default since 2026-09-03.** With no pinned weights, each run classifies its input by where the ink comes from — a scanned page is one full-page raster image (total coverage ≥ 0.95 on every scan measured, incl. one tiled into 8 strips), an engraved page is vector drawings (428–2058 paths vs 0–4 on scans, the gap empty over 147 probed pages) — and picks the weights that measured best for that domain: **scans → the hollow graft** (since 2026-09-04 the head-graft + bias-floor checkpoint; half-notes 8→27 under the 09-03 hollow-ft, →31 under the graft on beet5-p1), **digitally engraved PDFs → the prior production weights** (11-work OMR-NED 0.1399 vs 0.1421 no-direction-text). Blank/ambiguous inputs abstain to the default (scan) weights, and a missing engraved-weights file falls back soft with one stderr line — routing can never fail a run that used to work. Verdict + per-page evidence are recorded in the result JSON as `weight_routing`. Set `0` to disable. Costs ≤ 77 ms per document. Implementation record: `benchmarks/omr-weight-routing-2026-09/FINDINGS.md`; strategy + the vetted process for any future specialist weights (publisher/era forks deferred behind measured triggers): `docs/weight-routing-and-specialization-2026-09-03.md`. |
| `OMR_ENGRAVED_WEIGHTS`| `tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` | Override the engraved-side weights file that routing targets. |
| `OMR_CLEF_WEIGHTS`    | _(unset)_ | Optional **clef-specialist** weights — a checkpoint fine-tuned to read clefs, **not** general-purpose detection weights. You don't need it: header reading (clef + key signature) is on by default and needs no extra files. When set, a 2nd detector reads each staff's clef from its header and overrides the main clef, which helps on some orchestral scans (decoupled; the main detector still does all symbols). **Pointing this at ordinary weights makes clefs worse.** See `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`. CLI: `--clef-weights`. |
| `OMR_MAX_PAGES`       | `5`     | Hard cap on pages per OMR job |
| `OMR_CONF_THRESHOLD`  | `0.25`  | Min YOLO detection confidence |
| `OMR_IMGSZ`           | `512`   | YOLO inference image size. **Larger is NOT better** — ultralytics letterboxes to `imgsz²` regardless of cell size, so a big value buys anchors and false noteheads, not recall. Measured: `benchmarks/omr-imgsz-sweep-2026-08/findings.md` |
| `OMR_DPI`             | `300`   | PDF rasterization DPI (CLI default is **600** — they differ on purpose). **Coupled to `OMR_IMGSZ`, and the best pair depends on the music:** 300 wins on sparse authored fixtures (ensemble precision 0.684 → 0.915), 600 wins on dense orchestral pages (Mahler recall 0.042 → 0.208, duration 0.000 → 0.200). Unifying them in either direction regresses the other family. **Do not 'fix' the inconsistency without measuring both.** See `benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md` |
| `OMR_LEFT_EDGE_SPLIT`  | `1` (on) | **On by default.** A second, narrow barline scan at each system's shared left edge that *adds* a system break where that left column is empty even though the wide connectivity window found staff-body ink — recovering two stacked systems that the wide window MERGED because a measure number, stem, or `a 2.` marking faked a connection. Union-only (never merges) and gated so it never creates a size-1 system. Measured across 964 library pages: fixed 27 over-merged symphony pages vs 1 mild residual (Mozart K22), 0 size-1 created; ground-truth eval 20/23 → 22/23. Guarded **end-to-end** by `tools/omr/tests/test_left_edge_split_e2e.py` — 4 scanned pages, 3 publishers, hand-read staff/measure truth, asserting both that the split reads the true structure and that flag-off still merges (merged, Eroica p36 reads 10 measures where the page prints 16). Set `0` to disable. See `benchmarks/omr-system-grouping-2026-09/FIX_PLAN.md`. |
| `OMR_DIRECTION_TEXT`  | `1` (on) | **On by default since 2026-09-02.** Reads the words printed inside a system — `legato`, `Allegro con brio` — by subtracting every detection from the page's ink, refusing the curves by fill ratio, OCRing what is left with Surya and Tesseract, and gating on a lexicon of musical terms. Emitted as MusicXML `<words>`. **Worth 144 edits** on the engraved orchestral benchmark, 18.8% of the pooled figure, and `wrong direction` is the third-largest bucket. **Additive** — every word placed reaches the file and the export is identical outside its `<direction>` blocks, checked per page on engravings and on a scan. Costs 0.5-0.8 s per candidate crop; the ~70 s model load it used to be blamed for belongs to the margin-label reader, which is on by default and loads Surya first on any page without a text layer. Self-disables where neither `.venv-surya` nor Tesseract exists. CLI: `--no-direction-text`. See `benchmarks/omr-direction-text-2026-09/DEFAULT_2026-09-02.md`. |
| `OMR_CELL_LINE_TRACE` | `1` (on) | **On by default since 2026-09-04.** `Staff.line_ys` models a staff as five ideal horizontal rows and every measure cell copies those constants — but a SCANNED staff tilts/bows 8-17 page px across its width, so an end-of-staff cell's grid can be half a space off the print and `pitch_resolver` reads exactly those rows. This slides the cell's five rows as ONE RIGID COMB onto the ink beneath it (recovers all seven hand-traced displacements within 0.04 spaces; per-line tracing ALIASES and was refused). **Priced on the widened scan gate the day widening made it possible**: pooled 0.8387 → 0.8345 (−233 edits), −217 of them on exactly the three tilted rows (the widened pool holds 8.6% of cells past the 0.25-space parity-flip line vs the old corpus's 0.4% — the old '4 edits of 7894' null was the corpus, not the fix), exact-pitch recall/precision +4.8/+5.9pts on the most-exposed edition, zero-exposure row unchanged to the edit; the engraved side is a no-op by construction (byte-identical A/B). Known blast radius, priced: the grid feeds the key-sig slot fit (net keysig −15, but two-directional per staff) and +2..+7 edit noise on three low-exposure rows. Labeling batches survive re-cuts: `recut_cells.frame_mismatch` compares the frame's own UNLOCALIZED grid and `_nostaff.png` is re-erased on the manifest's authority, pinned by e2e tests. Set `0` to disable. See [benchmarks/omr-cell-grid-tilt-2026-09/WIDENED_PRICING_2026-09-04.md](benchmarks/omr-cell-grid-tilt-2026-09/WIDENED_PRICING_2026-09-04.md) |
| `OMR_ARC_ATTRIBUTION` | `move` (on) | **On by default since 2026-09-04.** Gives SLURS AND TIES the cross-staff arbitration noteheads have had since `_dedupe_cross_staff_detections`. A measure cell is padded above and below, so on a conductor's page a neighbouring staff's arc lands in this staff's cell — and unlike a notehead it need not be detected twice for that to matter: where the staves are far apart the upper cell reaches ink the lower cell does not, so the arc exists ONLY in the wrong staff and no duplicate-resolution rule can see it. On `brahms-sym1-mvt1` the Timpani exported 4 slurs and 1 tie against a truth of ZERO — they are Violin 1's, drawn over ITS four-ledger-line notes in the 7.7-space gap between the two staves. **The evidence is the arc's own job: an arc binds a run of noteheads and is drawn just clear of them, so it belongs to the staff whose NOTEHEADS IT HUGS** — asked of every staff in the system, including ones that never detected it. ⚠️ Distance to the staff LINES is the same trap it was for notes: an engraver opens the gap above a staff precisely so its ledger notes and their slurs can live there. The rule is COMPARATIVE (an arc leaves only where another staff explains it better) and both constants sit on measured plateaus. Worth **pooled 2,473 → 2,371 edits**, Brahms 1 490 → 390, no work worse, `wrong note` untouched; the scan gate's two Brahms rows are identical to the edit. ⚠️ `drop` (delete instead of regift) scores 2,388 — better arm-for-arm — and is REFUSED: it gets there by emitting 20 fewer slurs, 12 of them real, the metric's under-prediction reward. `off` disables. See [benchmarks/omr-arc-attribution-2026-09/FINDINGS.md](benchmarks/omr-arc-attribution-2026-09/FINDINGS.md). |
| `OMR_SLOT_STITCH` | `0` (off) | **Measured, deliberately dormant.** `export._stitch_slots` joins staves into continuous parts by ORDINAL and REFUSES when systems disagree about staff count — correct, because a printed score suppresses tacet staves and joining by position would graft one instrument's music onto another. Its fallback is per-system FRAGMENT parts, each pairing with nothing in the truth. On this, the contextual pass's SLOTS supply the join instead, and only where the ordinal join refused. Structurally it works — Brahms 1 p.2 recovers 14 continuous parts from 27 fragments and correctly leaves the suppressed Trompeten slot short. ⚠️ It is OFF because it still costs OMR-NED: the fragments are charged as `entire measure`, the recovered parts as `entire staff`, and musicdiff charges an unpaired truth PART more than that part's unpaired MEASURES — so the named bucket DOUBLES (715 → 1,632) while `entire measure` falls further. **A corollary worth carrying: attributing structural work by the `entire staff` bucket alone systematically under-counts fragmentation.** Priced on n=1 page. See [benchmarks/omr-staff-structure-2026-09/FINDINGS.md](benchmarks/omr-staff-structure-2026-09/FINDINGS.md). |
| `OMR_CONDENSED_PARTS` | `0` (off) | **Measured, dormant, and blocked on a count source.** A condensed staff (`Flauti`, `Corni`, `Violoncello e Basso`) carries several reference parts; we emit one, and every unmatched truth part is charged a whole staff. On this, a staff carrying `condensed_parts: N>1` emits N parts. The convention is MEASURED, not assumed: over every condensed staff-measure in the truths, silent 51.5% + unison 18.3% = **69.8% is exact duplication** (divisi 27.6% is approximated by duplication, so the figures are a floor). Ceiling with oracle counts: scan pool **−4,195 edits alone, −4,557 with `OMR_SLOT_STITCH`** (they compose, and the split cancels stitch's `entire staff` penalty); `entire staff` 8,453 → 2,060. ⚠️ **The page cannot supply the count.** Staves carrying the SAME printed label are encoded as 1 part in some editions and >1 in others (Litolff/Simrock/Breitkopf `Viola` = 1, Peters `Violen` = 2), so whether a reference splits is a property of the ENCODING, not the engraving; a label-derived rule is 74/74 on Beethoven/Brahms and **+2,181 edits on Dvořák**, and eleven page-side signals separate the two populations no better than chance (best ensemble 0.526 vs the `always 1` baseline's 0.538). `=all` splits fragments too (measured +904, for reproduction only). Flag-off is byte-identical (22/22 fixtures). See [benchmarks/omr-condensed-parts-2026-09/FINDINGS.md](benchmarks/omr-condensed-parts-2026-09/FINDINGS.md). |
| `OMR_SLOT_STITCH` | `0` off (default) → join staves into parts by contextual SLOT where the ordinal join refuses. Measured; dormant because the trade is priced on one page. See the knobs table. |
| `OMR_CONDENSED_PARTS` | `0` off (default) → emit one part per player on a condensed staff; `all` splits fragments too. Ceiling −4,557 scan edits with slot stitch, but the COUNT cannot come from the page. See the knobs table. |
| `OMR_ARC_RECLASS` | `0` (off) | **Measured, deliberately NOT shipped.** Export-time tie/slur grammar veto (`docs/position-grammar-confusables-2026-09-04.md` §2 ARC, R3 shape): a slur-classed arc covering exactly two adjacent same-pitch heads of one voice becomes a tie; a tie-classed arc whose flanked pair sits on different STAFF STEPS, or with a third event of its voice under its span, becomes a slur — the vetoed arc widened to the flanked centres and split at cell boundaries so the ordinary barline merge rejoins it. Compares steps, never spelled pitches: the far head of a cross-barline tie does not restate its accidental and the resolver spells it plain, so the naive spelled-pitch key broke truth-matched ties (+21 engraved edits, every loss a same-step `F#4→F4` pair). Priced on both families: engraved **0.1306 → 0.1306, +2 edits, 24 firings**; scan **0.8387 → 0.8391, +130 edits — REFUSED**, because a scan's resolved pitch at an arc's ends is downstream of exactly what scans get wrong (`wrong note` = 26% of that pool), and per-direction attribution puts ALL +130 in the tie→slur half while slur→tie alone is edit-free and moves the tie inventory toward truth (420 → 462 of 805 elements). If any half ever defaults on it is slur→tie; tie→slur is blocked on ANCHORS, not grammar (R4). Flag-off is byte-identical, asserted per work and per row. See [benchmarks/omr-export-gaps-2026-09/FINDINGS.md](benchmarks/omr-export-gaps-2026-09/FINDINGS.md). |
| `OMR_CHOIR_GROUPING`  | `1` (on) | **On by default since 2026-09-05** (Sean's call, coupled with the Bach row's pool re-admission; the re-stamped 11-row baseline is recorded beside WIDENED_BASELINE_2026-09-04.md). Two cues for choir-grouped / differently-indented pages, both riding this one flag. The Bach Brandenburg 3 stress row shatters (6 "systems", 122 measure-cells vs 10) because the wide connectivity window and cue A's band are both anchored on the page-MEDIAN `x_start`, and on a page whose systems are indented differently (792–836 vs 178–200) the median lands between the modes and cuts the full-width system's bracket + systemic barline out of the scan — while the page is also choir-barred (interior barlines stop at choir edges), so nothing else crosses its choir gaps. **Cue B** (merge-only mirror of cue A, `system_grouping.py`): a break the wide rule made for lack of evidence is re-examined in the cue-A band anchored at the PAIR's own left edge; a crossing column there cancels the break. A cue-B merge is exempt from cue A's re-split (the cues act on disjoint gap sets — bridging > 0 vs == 0). **Cue C** (`measure_extractor.py`): a system whose staves form ≥2 bracket-groups (≥ half in multi-staff groups) AND that holds a **window-blind internal gap** — a gap nothing in-window crosses, the choir-barred signature, impossible for a true open score — is never flipped into open-score mode, so a merged rhythm-unison tutti's aligned stems stop out-voting its barlines. ⚠️ Bracket-groups ALONE was falsified on the engraved benchmark (LilyPond open scores manufacture "groups" from bridging jitter; pooled 0.1306 → 0.8560, nine works' barlines deleted) and repaired before shipping — do not loosen the second condition. Flag ON: Bach row 0.9241 → **0.8152** OMR-NED, 6735 → 6236 edits, 122 → 11 cells vs true 10; all ten pooled scan rows byte-identical (pooled 0.8387 untouched); the 11-work engraved benchmark **edit-for-edit identical** (0.1306 / 2745) and the `boulanger` structure canary byte-identical; 969-page library probe: 757 examined break-gaps read 0 ×735 / ≥4 ×22 with nothing at 1–3, and the 10 pages that change were each hand-adjudicated toward the truth (7 exact heals incl. both operas' vocal systems; zero false merges). Flag OFF: byte-identical by construction (Bach flag-off hash-matches the widened-graft baseline fixture). Re-admitting the Bach row to the scan pool is coupled to a default-ON decision and a re-stamped pool. See `benchmarks/omr-choir-grouping-2026-09/FINDINGS.md`. |

---

## The central score library

Every score the project uses lives in one place with its provenance attached:
`library/` (machine-local, gitignored) plus a **committed** catalog at
[`data/score-library/catalog.json`](data/score-library/catalog.json). Full
conventions: [`data/score-library/README.md`](data/score-library/README.md).

**235 editions and 1745 reference encodings**, 6.4 GB, 27 works pairing a PDF
with ground truth. Before this, the same score existed under four names in four
trees — `tools/omr/training/data/imslp/`,
`~/Desktop/gradus-vercel/public/scores/`, and two copies of
`~/Documents/Gradus-Assets/Scores/`. Importing all of them yielded **1745 unique
reference files out of 4167+ candidates**; the rest were recorded as extra
origins on files already held.

The edition half was built from a ranked wantlist
([`data/score-library/wishlist.md`](data/score-library/wishlist.md)) that scores
every full score on a work's IMSLP page **for OMR rather than for playing**: a
real engraving beats a modern typeset, a named publisher beats an anonymous
upload, and an edition series already held beats one that is not. That last
bonus picked the Litolff 1870 series for the whole Beethoven cycle unprompted —
consecutive plates 2765-2773.

```
library/editions/<composer>/<work>/<composer>--<work>--<edition>--<source>.pdf
library/reference/<composer>/<work>/<composer>--<work>--<movement>--<source>.mxl
```

`editions/` is what a reader sees (OMR input); `reference/` is what the notes are
(ground truth). They join on `work_id`, which is keyed on **genre + number**, not
the full title — an IMSLP page says "Symphony No.5, Op.67" and a MusicXML header
says "Symphony No.5", and keying on the title split Beethoven's fifth into two
works with no edition and no ground truth respectively.

```bash
python3 -m tools.library.ingest imslp ~/Downloads/IMSLP*.pdf   # provenance from the wiki API
python3 -m tools.library.ingest musicxml <dir> --source gradus
python3 -m tools.library.ingest catalog | verify | reorganize | refresh | relink
python3 -m tools.library.ingest instrumentation                # work rosters, backfill
python3 -m tools.library.build_wishlist --out data/score-library/wishlist.json
```

**What each work is SCORED FOR is captured too**, keyed on the same `work_id`,
in a top-level `works` map in the catalog (schema version 2). The IMSLP work
page states it (`InstrDetail`, or `Instrumentation` on works that have no
detail line), so it is one more read of the open MediaWiki API the provenance
already comes from — never the download gate — and it costs one query per
WORK, not per page. It exists because roster acquisition off the printed page
fails on a minority of documents and this is an **independent** work-level
escalation. The raw string is stored verbatim and a parsed roster beside it
(instrument + count, named through `tools/omr/instruments.py` so the rest of
the pipeline recognises the words); a fragment the lexicon does not know is
recorded `unparsed`, never forced to a nearest match.

⚠️ **`source_kind` is the load-bearing field.** Every fact carries
`source: "imslp"` / `source_kind: "catalog"`, and `"catalog"` is what makes it
legitimate production evidence: it is independent of the MusicXML the
benchmarks score against. A roster derived from an encoding would be
`source_kind: "encoding"` and a measurement path may not read it. The
distinction is enforced (`validate_fact` refuses a fact without it) rather than
conventional, because it cannot be added to facts already written.

⚠️ **N instruments is not N staves** — a printed score condenses and splits, and
the condensed count is a property of the encoding. ⚠️ Two IMSLP pages can share
one `work_id` (Clara Op.7 and Robert Op.54 are both `schumann--piano-concerto`);
the key is not forked, the second roster is kept as a recorded conflict and
neither is trusted. **Measured 2026-09-05 over all 223 held IMSLP works: 2419 of
2518 roster fragments parse (96.1%), 171 works (76.7%) parse completely, 4 parse
nothing** (their page states no roster — `keyboard`, `orchestra`). The
work-complete figure is the one a staff join cares about: a roster missing a
part joins *wrong*, not *not at all*. The residual is lexicon gaps rather than
parser failures — `2 cornets` alone is 14 of the 99, and `instruments.py` has no
cornet. Backfill cost 224 requests at 6 s = **25.4 min, 0 failures**. Regenerate
the figures with
`python3 benchmarks/omr-instrumentation-capture-2026-09/measure_parse_rate.py`
(writes `parse-rate.json`, which carries the per-work table and the unparsed
tail). ⚠️ Three fault shapes are pinned by tests because each produced a
*confident wrong answer*: one field holding both dialects (Bach's B minor Mass,
0 of 18), an opera's field opening with its CAST list (Tannhäuser, 0 of 54), and
a prose roster ending in desk counts `strings (16, 16, 12, 12, 8)` being read as
the numeric dialect. Fixing them took the pooled rate 0.9015 → 0.9432 → 0.9607
**with no new IMSLP requests** — the raw string is stored verbatim, so
`--reparse` re-derives every roster offline.

⚠️ **AND A FOURTH, WORSE THAN THOSE THREE, FOUND 2026-09-05: a doubling
parenthetical DELETED THE CHAIR.** `2 flutes (2nd also piccolo)` was resolved
whole, the lexicon matched `piccolo` *inside* the fragment, and the chair came
back as **Piccolo, count 2** — the flutes gone, the auxiliary standing in their
place with the flutes' own count, at `parse_rate 1.0`. **58 of 223 works write
"also"**, and Berlioz's *Symphonie fantastique* had no flute and no oboe.
Underneath it, fragments split on commas at *any* bracket depth, so
`4 oboes (3rd, 4th also English horn)` was cut in half and the split lost the
**chair**, not the aside (10 works). The head is the chair; a parenthetical is a
`qualifier`, or a `doubles` entry when it says *also*/*doubling* — never a
roster entry of its own, because a doubling player is ONE chair holding two
instruments. `or` is not a doubling marker (`harp (or piano)` is a
substitution). Measured offline over the raw strings, **0 requests**: **61
rosters changed**, unparsed 99 → 75, fully-parsed works 171 → 178; recovered
Flute ×39, Oboe ×18, Continuo ×6; removed the fakes Piccolo ×37, English horn
×17, Piano ×6 (`continuo (harpsichord)` had been inventing a keyboard chair out
of a figured-bass line). Pinned by `TestDoubling`.

**And what ONE PRINTING is scored for is captured too** (2026-09-05), in a
second top-level `editions` map keyed on the file's own `path` (schema 2 → 3),
read from that edition's own pages: `tools.library.edition_instrumentation`.
The work tier is generic and right about the piece; an edition tier is
authoritative for **this PDF**, which matters because Bruckner exists in
versions with different orchestration, publishers add and absorb parts, and one
`work_id` can hold a full score *and* a piano reduction. ⚠️ **A page-derived
fact is a THIRD `source_kind`, `"page"`** — not `catalog` — because a roster read
off a raster is an **OMR output**, so a measurement path that scores OMR must
refuse it for a different reason than it refuses `encoding`. ⚠️ The roster is
**one SYSTEM's, not one page's** (Brahms 1 / Breitkopf p.1 is 27 staves in two
systems and would report the roster twice), and `staves` (observed) is kept
apart from `count_printed` (quoted), so neither tier implies a staff count.
**Measured over all 234 held editions: roster acquired 189 (0.808), 68 min, 0
failures, 18 of them only on a page past p.2.** The **disagreement between the
tiers is the output**, and its mix is the finding, not its rate: of 181
comparable rows, 0.442 are partial reads, 0.210 agree, **0.210 are one lexicon
word** (`Basso.` → Bass *voice* — the bottom string staff of every orchestral
score, 35 rows, the only disagreement on 30), 0.017 doubling, and **0 are a
genuine editorial variant** — all 9 `variant_suspected` rows opened by hand are
movement scope (Beethoven 5's trombones enter in the finale), condensation
(`Violoncello e Contrabasso` on one staff), a bracketed optional part, or an
opera's cast list. So **`variant_suspected` means "worth a human", never "a
variant"**. Full reading in the docstring of
`benchmarks/omr-edition-instrumentation-2026-09/probe_tier_disagreement.py`.

**The legacy paths still work.** ~20 benchmark scripts hard-code
`tools/omr/training/data/imslp/<work>/pdfs/imslp-<id>/score.pdf` and NOTES.md
quotes measured numbers from them; those are now symlinks into the store,
recreated by `relink`. `library_root()` also resolves to the MAIN checkout from
inside a git worktree, so one machine keeps one store.

**Downloading from IMSLP.** File downloads sit behind a JavaScript redirect gate
that `curl` cannot pass, so a logged-in browser has to resolve
`Special:ImagefromIndex/<id>` to its direct file URL; the wiki pages and the
MediaWiki API are open, which is where all provenance comes from. **Do not try to
defeat the gate** — pace the requests instead. Practical recipe: drive 3-5 Chrome
tabs, read the resolved URLs out of the tab list, then fetch them with a delay
(`FETCH_DELAY`, 12s used for the bulk runs). Nothing tripped a rate limit across
~230 downloads.

⚠️ **Five ways this silently installed the WRONG file** — case-sensitive
filenames, redirect stubs blanking all provenance, slashes in titles, regional
mirrors (`imslp.eu`, `petruccimusiclibrary.ca`) serving HTML, and non-atomic
writes. Each is described with its symptom in
[`data/score-library/README.md`](data/score-library/README.md); read that before
changing the provenance path.

⚠️ **Never trust an embedded composer or movement field.** The Mahler 5 export
repeats "I. Trauermarsch" as the movement title of *every* movement; one
collection wrote `Desktop` as the composer of 70 Bach chorales; life dates arrive
glued to the name (`Bach(1685 - 1750)`) and once made the store grow a composer
called `1750`. `reorganize` re-derives from the strongest evidence available and
is idempotent — a hand-supplied name outranks the file's own metadata, which
outranks a folder name, and a folder name is accepted only if some *other* file's
metadata independently vouches for it.

---

## Dossiers — checking a reading against what the work actually is

The five internal-consistency checks can only ask whether a page agrees with
ITSELF, which is why a page where every staff reads treble passes all of them.
A **dossier** supplies external truth: the meter, the measure count, and the
written clef and key signature of every part.

They are **generated from MusicXML**, not hand-typed — the Gradus score library
(`~/Desktop/gradus-vercel/public/scores/`) holds ~97 orchestral movements, so
the facts are exact rather than remembered.

```bash
# Build them (97 works, a few minutes) — writes data/dossiers/<work_id>.json
python3 -m tools.omr.training.build_dossiers
python3 -m tools.omr.training.build_dossiers --list

# Use one during transcription
python3 -m tools.omr.transcribe score.pdf --dossier beethoven-sym5-mvt1 --out out.json
```

**Everything is stored as WRITTEN pitch** — what is printed on the page, which
is what the reader sees. A B-flat clarinet in a 3-flat movement is stored as
`fifths: -1`. `docs/dossier-verification-plan.md` warned that a concert-pitch
dossier makes every transposing staff false-flag; storing written facts removes
the trap instead of compensating for it.

**Two tiers of check, and the difference matters** (`tools/omr/dossier.py`):

- *Alignment-free* — clef vocabulary, key vocabulary, clef distribution, meter.
  These compare sets and distributions and need no part→staff join. Trustworthy.
- *Slot-level* — per-staff clef and key. These need to know which staff is
  which, and a printed score condenses (Fl 1+2 share a staff) and splits
  (divisi), so Beethoven 5 has 18 parts and 22-staff pages. Forcing that join
  measured **F1 0.064** (`benchmarks/omr-mxl-autolabel/FINDINGS.md`). So they
  run ONLY when staff count equals part count, and abstain otherwise.

**The meter is applied, not just checked.** On a constant-meter work the dossier
meter is what the meter IS, so a detected meter that disagrees is a misread and
is replaced — every override is still reported. Measured on an engraved
Beethoven 5 excerpt the detector read 4/4, 4/24 and 7/24 across a 2/4 movement.

**The dossier also SEEDS, not just checks.** With `--dossier` the pipeline takes
each staff's written clef and key signature from the work, where the parts join
1:1 to the staves (`--no-dossier-seeding` turns this off). Clef detection is the
documented ceiling — 2% coverage on orchestral scans, and a fine-tune, ensemble
voting and a CV locator have all failed to move it — so knowing the clef beats
reading it. Measured on the orchestral benchmark: Beethoven recall .642 → .691,
Brahms .206 → .253 (matched notes 136 → 167). Mahler is untouched because it
detects 31 staves against 38 parts and the join correctly abstains.

**System grouping is decided by CONNECTIVITY, not gap distance**
(`staff_detector._gap_is_bridged`). Within one Brahms system the inter-staff
gaps run 17–237 px and within one Beethoven system 130–345 px — both wider than
the gaps BETWEEN systems on a piano page — and x-overlap is 1.00 for every pair,
so no distance threshold can separate them. It used to report one 21-staff
Brahms system as *twelve*. A barline runs a system's full height and the bracket
encloses exactly it, so a column inked through the whole gap VETOES a gap-based
break (veto only — it can merge an over-split page, never split a correct one).
Brahms 12 → 1 system, Beethoven 4 → 1, and Beethoven's measure count went 14/8 →
**8/8 exact**. The dossier join still falls back to page level
(`slot_facts_for_page`) for pages where grouping is still imperfect.

**Do not use dossiers to generate training labels.** The MXL→bounding-box path
is closed: F1 0.064 on 76 hand-mapped cells, x-drift diagnosed as the cause.
Measure-level alignment works; per-symbol placement does not.

---

## Meter → rhythm feedback

Until 2026-08-28 the meter was derived FROM the durations and then used only to
complain about them. `resolve_rhythms_for_cell` took no time signature,
`backfill_page_time_signatures` voted a meter out of durations already
committed to, and a 4/4 bar summing to 4.53 beats was flagged and shipped.

`transcribe._reconcile_measure_to_meter` closes that loop for the one duration
input fragile enough to be worth arbitrating: the **beam level**. Durations come
from clustering beam y-positions, so one extra or missing cluster halves or
doubles a note. Deliberately narrow:

- only ever re-reads a beam level by ±1 — never adds, deletes or re-pitches a
  note, so it cannot paper over the over-detection thread;
- the corrected bar must land EXACTLY on the meter;
- the answer must be UNIQUE, else nothing changes and the warning stands;
- single-voice measures only.

Every change is recorded as `rhythm_reconciliation` on the measure. On the
Beethoven 5 opening it re-read three notes from sixteenths to eighths, taking
the bar from 1.25 to the 2.0 that 2/4 requires — the right answer on the most
famous bar in the repertoire.

---

## Durations: two units, and both of them were wrong

The rhythm bucket was the largest remaining after the metric's first eight
fixes, and neither half of it needed the meter, better detection, or a wider
`_reconcile_measure_to_meter`. Both were signals already on the page, thrown
away by a threshold expressed in the wrong unit.

**A dot does not sit at its note's height.** A note in a space takes its dot in
the same space; a note ON A LINE takes it in the space ABOVE, half a staff space
up. The gate was `max(dot.height, 12) * 1.2` — a length derived from the dot's
own bounding box, which is small and mostly detector noise — so the on-a-line
case landed within a few pixels of the threshold and went either way. C Horn 1's
dotted half was read as a half in bars 1 and 5 and as a dotted half in bars 2,
3, 4 and 6. Measured over the 116 dots of the three works, the signed offsets
are bimodal and nothing else: 52 at 0.00 spaces, 52 at +0.50, nothing between
+0.57 and +3.75.

⚠️ **The window is ASYMMETRIC, and it has to be.** A dot goes above its note or
level with it, never under. Brahms's Viola plays double stops — two noteheads a
space apart, each with its own dot — so the lower dot is equidistant from both
noteheads, a symmetric window ties, and the upper note comes out double-dotted
while the lower loses its dot. `DOT_ABOVE_NOTE_MAX_SPACES` is 0.75 and
`DOT_BELOW_NOTE_MAX_SPACES` is 0.25.

**A YOLO beam box bounds the STACK, not a stroke.** `resolve_rhythms_for_cell`'s
docstring always said the classical-CV beams replace the YOLO ones; the code
unioned them, for the Phase-4f reason that CV was the more conservative detector
and missed strokes. What the union costs is the one thing beams are read for —
how many are stacked. A YOLO box spanning two strokes contributes a centre in
the GAP between them, and the run then has no gap wider than the clustering
tolerance anywhere in it: on Brahms's Violin 2, CV reads the strokes at
canonical y 1112 and 1172 (60 px apart against a 35 px tolerance, two levels)
and the YOLO box adds 1142 between them, so three sixteenths read as three
eighths. A YOLO beam is now kept only where **no CV beam overlaps its x-range**.

All three arrangements were measured, because the Phase-4f reason is still half
true — replacing outright throws real beams away:

| | pooled | edits | brahms dur | melody dur |
|---|--:|--:|--:|--:|
| union (Phase 4f) | 0.1917 | 1355 | 0.916 | 0.778 |
| replace outright | **0.1855** | **1310** | 0.929 | **0.722** |
| **kept** | 0.1861 | 1315 | **0.931** | 0.778 |

Replace scores best, by five edits out of 1315, and gets there by throwing real
beams away: it is the only arm that regresses an authored fixture, and the
`×4` family — notes that lost every beam they had, read four times too long —
goes from 4 under the kept rule to **7** under it. Five edits is less than one
measure's amplification is worth; the beams are the thing.

Together the two: **pooled 0.2209 → 0.1861**, Brahms 0.3185 → 0.2563 and its
duration rate 0.889 → 0.931, Beethoven and Mahler unchanged to the edit.

### Then the two beneath them, in the classical CV

Fixing the above left 36 wrong durations and a handoff saying the next step was
detector work. It was — `line_detection`, not the model — and it was two more
constants that did not mean what they said. Together: **pooled 0.1861 → 0.1506**,
Brahms 0.2563 → **0.1922**, its duration rate 0.931 → 0.968 and `exact` measures
67% → **76%**; Beethoven and Mahler unchanged to the edit both times.

**A stem is as long as the music needs it to be** (`STEM_MAX_HEIGHT_LINES`). The
cap was 6.0 staff spaces, and a note two ledger lines above the staff beamed to
notes inside it carries a stem longer than that — so the notes furthest from
their beam were silently un-stemmed, and the same distance then put the beam out
of reach of the notehead-to-beam fallback (which gives up at 5.5 spaces). The
note lost every level it had. Over 8746 candidates on 13 pages of 8 editions the
population decays smoothly to 8 spaces and stops, with a second population from
10 up to the height of the cell itself — barlines and brackets crossing the crop.
The constant sits on the 11× cliff between them, and the benchmark agrees:
6.0 → 0.1861, 7.0 → 0.1601, **8.0 → 0.1601**, 9.0 → 0.1610.

**A beam bar was counted from its neighbour's ink.** `_stacked_bar_count` counts
vertical ink runs in a column, which is right, but it sampled the OPENED IMAGE
inside the component's bounding box instead of the component's own label mask.
A sloped bar's box is exactly the shape that reaches over its neighbours: where
the slope exceeds the pitch between bars (61 px against 53 on the Brahms page),
the secondary bar sits inside the primary's box, 26 of 51 columns show two runs,
and the primary is cut into two bands — giving every note under it a level too
many. `_attached_stem_count` right below it already reads the label mask and says
why. The LilyPond beam ground truth went 9 → **8** summed error, which is the
corroboration worth having: it counts bars exactly, and it had been one over.

⚠️ **A green ground truth is not evidence when the case is outside what it
engraves.** `benchmarks/omr-phase4-lines` is unchanged at every stem cap tried
(6, 7, 8, 9, 12) because its music has no long stems. It could not have caught
this and does not pretend to.

---

## Tuplets

A triplet's noteheads are ORDINARY eighths on the page. The printed value is
right; the bracket says three of them occupy two's worth of time. So
`rhythm.resolve_rhythms_for_cell` does not re-read anything — it multiplies
`duration_beats` by 2/3 and leaves `duration_type` as the written value, which
is what MusicXML's `<type>` and LilyPond's `8` both want inside a tuplet.

**The signal was already in the JSON and nothing consumed it.** Before
2026-09-01 `grep -ci tuplet` returned 0 in `export.py`, `rhythm.py` and
`transcribe.py`, while the Mahler page carried `tuplet3` and `tupletBracket`
detections and ALL 15 of that work's wrong durations were one triplet figure
read straight — 87 of its 154 OMR-NED edits. Pooled 0.2595 → **0.2489**,
Mahler 0.0826 → **0.0455**, duration rate 0.318 → 0.864, with Beethoven and
Brahms byte-identical.

**Two markers, read differently, because they sit differently on the page.**
The DIGIT is printed over the middle of its group, so its centre must fall
inside the group's span. The BRACKET encloses the group, so the group must fall
inside the BRACKET's span — detected brackets are far wider than the notes they
cover (one measured at 1846px over a 478px group) and testing a bracket's centre
rejects every one of them.

**Which notes are in the group is the BEAM box, not the marker.** Same split
`export.annotate_beams` documents: the marker says a tuplet is there, the beam
box says how far it reaches. The box is padded by a notehead width because it
bounds beam INK, which starts at the first stem — unpadded, every stem-up group
loses its first note.

Deliberately narrow, and it abstains rather than guesses:

- only `tuplet3` → 3:2. `tuplet5`/`6`/`7` are in the DSv2 class space but each
  needs its own normal-count convention and none of them occurs in anything
  measured here;
- the group must have exactly as many notes as the digit claims, so a triplet
  written quarter-plus-eighth is left alone rather than guessed at;
- an unnumbered bracket is read as a triplet only over a group of exactly
  three, and only when it covers exactly one group in the cell;
- rests inside a group are NOT scaled — pairing a rest to a beam group needs a
  signal the beam box does not carry;
- tuplet notes are excluded from `_reconcile_measure_to_meter`'s candidates,
  because `_duration_for_level` re-derives a duration from beams and dots alone
  and would silently drop the ratio.

⚠️ **`export._compute_divisions` is an LCM, not a max, and that is load-bearing.**
A triplet eighth is 1/3 of a quarter; the old power-of-two ladder returned 16 and
16 thirds is not a whole number, so every triplet would get a rounded
`<duration>` and a short bar. The LCM of powers of two IS their maximum, so
scores without tuplets get exactly the old number — verified byte-identical on
Brahms (8) and the authored fixtures.

**A triplet digit arrives under two class names, and the class is not evidence
about which.** DSv2 labels a `3` over a beamed group `tuplet3` and a `3` beside a
notehead `fingering3` — a POSITIONAL distinction, made by where the digit
stands, and the detector reproduces it badly on orchestral pages. Measured over
twelve engraved works (`benchmarks/omr-corpus-widening-2026-09/`): **33
`fingering3` against 16 `tuplet3`, and all 33 sit in a cell that holds a real
triplet**; the single detection that does not is a `tuplet3`. So both classes
are read, and the positional gate above is what keeps that safe — a real
fingering centred over a beamed group of exactly three would still be misread,
and no conductor's score in the corpus prints one to price that against.

⚠️ **This corrected a claim that stood here for a day.** The line this replaces
said Mahler's fifth triplet group "carries no marker at all, at any
confidence". It carries a `fingering3` at **0.72** — the highest-confidence
tuplet marker on that page. Nothing was wrong with the reasoning; the three-work
benchmark simply could not falsify a story about one of its own pages. Mahler
went 0.0455 → **0.0331** and its duration rate 0.864 → **1.000** when the class
was admitted, and `tchaikovsky-sym6-mvt2` 0.2321 → 0.1958.

⚠️ **A GROUP IS A SET OF NOTES, NOT A BEAM STROKE.** A sixteenth carries two
beam strokes, the CV detector finds both, and `_beamed_groups` returned one
group per box — so the ratio was applied once per stroke and a triplet
sixteenth came out `(1/4) × (2/3) × (2/3) = 1/9`. Every triplet in the three
works this benchmark used to consist of is an EIGHTH triplet, one stroke and one
group, so the fault could not appear there; `mozart-sym41-mvt1` prints 40 groups
of triplet sixteenths and cost 464 edits for it. Identical member sets are
collapsed.

---

## Slurs — paired over the STAFF, because the barline cuts the arc

A slur crossing a barline is **detected as two arcs**, because cells are cut per
measure — 120 arcs on the Brahms fixture against 82 slurs in the truth. That is
why `annotate_slurs` sat implemented, tested and unwired from `89277a2` until
2026-09-01: emitting per measure wrote two slurs where the music has one.

**The event model needed nothing.** A MusicXML slur may already open in one
measure and close in another, and LilyPond's `(` `)` never cared about barlines;
both need only a number that means the same thing at both ends. What was
per-measure was the PAIRING. So `export.annotate_slurs_in_staff` runs once per
staff in **page pixels** — the only frame shared across cells, the same move
`transcribe._pair_ties_in_staff` makes to catch ties across a barline — and
marks the notehead detections, which `group_chords_in_measure` already carries
into events the way it carries the tie flags.

**Three constants, none of them tuned — each sits in a gap the measurement
found** (`benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`):

| what it decides | the two clusters | constant |
|---|---|--:|
| an arc was CUT by the boundary | 0.00–0.10 spaces vs 1.58 | 0.5 spaces |
| the two halves are ONE slur | 0.02–1.14 spaces vs 8.04 | 2.0 spaces |
| a notehead is UNDER the arc | 0.00–0.19 widths vs 0.32 | 0.25 nh widths |

Each is a PLATEAU rather than a peak — the exported score is identical for the
continuation tolerance anywhere in 1.0–6.0, and for the pad at 0.25 or 0.5 —
which is what a constant read off a gap should look like. **Re-check them when
the geometry beneath them moves:** the continuation cluster's top went 0.53 →
1.14 across the system-grouping change, still inside the gap and changing no
note, but it moved.

⚠️ **The arc is NARROWER than the run it binds, and that half is what made the
change real rather than cosmetic.** A slur is drawn *between* its noteheads, so
its ink stops inside both outer centres; unpadded, the Contrabass read
`n1 -> n4` in every bar whose truth is `n0 -> n5`. The box is padded exactly as
`rhythm._beamed_groups` pads a beam box. Merging *without* the pad lowered
pooled OMR-NED (0.2449 → 0.2436) while **raising** the edit count and the
`wrong slur` category — the metric's symmetry rewarding extra symbols. With the
pad, on top of the ledger fix: **0.2263 → 0.2209**, edits 1584 → 1563,
`wrong slur` 81 → 61, Contrabass 7/7 exact. (The pre-ledger reading of the same
work was 0.2449 → 0.2394; the step size barely moved.)

**Both ends must land in the same voice**, because MusicXML pairs `<slur>`
within a `<voice>` stream: 3 of 75 straddled two voices and left both halves
unpaired, which is malformed rather than merely wrong.

Beethoven and Mahler export **byte-identically** — neither page carries a slur
the detector reads. A slur-stripped truth scores 0.2171, so this takes ~38% of
what slurs are worth here; the residue has the right note INDICES and the wrong
pitches, which is note recognition, not slur work.

**A slur can also cross a SYSTEM BREAK**, since stitching made a part the same
staff on every system (`annotate_slurs_in_slot`). That junction is NOT the
barline's: the resuming half begins ~5.3 staff spaces inside its cell, because
the cell opens with a clef and a key signature, so it is anchored on the FIRST
NOTE instead — a resuming fragment runs in from the margin and ENDS on that
note, where a slur merely beginning there runs the other way. Heights are
compared RELATIVE to each staff's own top line; absolute page y is meaningless
across a break. Measured on `e2e_fixtures.build_systems`, the only multi-system
fixture in the repo: 0.2416 → **0.2381**, `wrong slur` 7 → 6, with the
orchestral benchmark byte-identical. LilyPond deliberately never receives one —
it emits one `\new Staff` per system-staff and a LilyPond slur cannot span two
Staff contexts. See
[SYSTEM_BREAK_SLURS_2026-09-01.md](benchmarks/omr-ned-2026-08/SYSTEM_BREAK_SLURS_2026-09-01.md),
which is mostly about how the FIXTURE had to be built before the fix could be
measured at all.

---

## Hairpins — a slur is drawn OVER its notes, a hairpin BETWEEN them

The **ninth** recognised-then-dropped element (2026-09-03), and the first that
is not purely an export fix. `dynamicCrescendoHairpin` and
`dynamicDiminuendoHairpin` fired freely and nothing downstream mentioned either
class, so `<wedge>` was absent from every file the exporter had ever written.

**The pairing is the slur pairing with one part replaced.** A hairpin is cut in
two by the same per-measure cell crop, so it reuses
`_merge_arcs_across_barlines`, `_voice_of_notehead` and the `number=` allocator
unchanged. ⚠️ **What it cannot reuse is `_noteheads_under`, and that is the
finding.** A slur is drawn over its notes; a hairpin is drawn in the space
BETWEEN them. On the Mahler 5 fixture the Trumpet's diminuendo spans page x
5922-6068 in a bar whose only notehead spans 5817-5897 — not one pixel of
overlap — and an overlap test scores **0 of 4**. So `_wedge_anchors` reads the
edges as pointers instead, and the start rule was **measured against the truth's
own spans**, because the obvious one is wrong: the ink begins slightly BEFORE
the note it starts on (26 px left of it, 105 px right of the previous note, on
Tchaikovsky 6), so "the last note at or before the edge" reaches back past the
answer. Nearest-either-side pairs **4 of 8** truth hairpins and gets all 4
exactly right; before-the-edge pairs 1.

**Emitting it is not reading it, and the gap between those is where the rest
went.** Nine boxes detected over the eleven works, five exported, four correct:

- **3 of Mahler's 4 land on the staff BELOW the one that prints them**, which
  has zero detected noteheads. A hairpin is drawn in the gap under its staff and
  `_dedupe_cross_staff_detections` awards a contested glyph to the nearer
  five-line band — the same failure this file already records for ledger
  noteheads, in the same function, and a hairpin has no ledger ladder to
  arbitrate with; **fixed the same day**, below;
- Brahms 4's one confident detection (0.91) abstains because the note the truth
  starts it on was never detected; the one hairpin we get WRONG there is a
  679×24 px box at confidence **0.28**, which is a line.

Measured, export-only A/B over the same stored transcriptions: engraved pooled
**0.1306 → 0.1304**, 2745 → 2742 edits (Mahler −1, Tchaikovsky 6 −3, Brahms 4
+1, the other eight byte-identical), `wrong crescendo` 3 → 1 and `wrong
diminuendo` 5 → 4.

⚠️ **THE STAFF-ATTRIBUTION FAULT WAS FIXED THE SAME DAY, and it was distance's
fault specifically, not the ladder rule's.** A hairpin prints in the gap under
its own staff, so a contested copy's centre sits roughly midway between the two
staves bracketing that gap — measured, the three misattributed detections were
only 5-62 px nearer staff 18's top than staff 17's bottom, against 25 px the
other way for the one correctly kept, close enough that distance is nearly a
coin flip. What actually separates them is that staff 17 carries a notehead in
every one of those bars and staff 18 carries none anywhere on the page — the
same shape as the pitch-range veto, keyed on presence rather than pitch, and it
has to be a SEPARATE tier because a hairpin has no ledger ladder for the
existing note-vs-note evidence to run on. `_WEDGE_HAIRPIN_CLASSES` names the
two wedge classes so the veto cannot leak into `dynamicF`-style point dynamics,
which are not anchored to a notehead the way a wedge is. Where both contested
staves carry a note — the case a "prefer the staff above" convention would be
for — nothing in this corpus exercises it, so distance is still the whole rule
there, exactly as before. Effect: Mahler's four hairpins all land on the
Trumpet staff that prints them, taking the **eleven-work total from 5 of 8
truth hairpins exported to 7**, controlled A/B pooled **0.1304 → 0.1299**,
2742 → 2733 edits, all nine of them Mahler's. ⚠️ **A from-scratch full rebuild
reproduces the categorical result** — same staff, same measures, `wrong
crescendo`/`wrong diminuendo` land at the identical 1/3 — **but not the same
pooled edit count** (Mahler 42 → 50 there): the same four boxes' confidences
moved between runs on byte-identical code (0.83 → 0.69 on the widest one),
detector-level jitter unrelated to this fix that touches other symbols on the
page too. The controlled A/B isolates the fix from that noise on purpose;
FINDINGS.md §6 has both figures and why they disagree.
`TestHairpinDedupePrefersTheStaffWithNotes`
(`tools/omr/tests/test_transcribe_helpers.py`) pins the veto and its two
fall-through cases. Full reading, including why "prefer above" did not ship:
[benchmarks/omr-hairpins-2026-09/FINDINGS.md](benchmarks/omr-hairpins-2026-09/FINDINGS.md)
§6.

⚠️ **THE SCAN BENCHMARK CANNOT PRICE THIS.** Its truth carries **20 hairpins**
across the five verified rows and the detector fires on **none** — zero
detections of either class on any of the five pages — so the scan arm is
byte-identical by construction, verified rather than assumed. On scans this is a
DETECTION problem and the export change is not addressed to it; the lever is the
labeling pipeline, and both classes are already in the DSv2 class space.

**LilyPond gets less than MusicXML, deliberately.** `\<` … `\!` are post-events
on notes, so the anchors serve — but a hairpin under ONE long note (`c4\<\!`),
a second hairpin opened before the first closes (there is no `number=` level),
and one whose ends fall in different LilyPond lanes are each dropped by
`_lily_wedge_plan` rather than approximated, because an unterminated `\<` is a
compile warning and a wrongly drawn hairpin. The lane case is not the
transcription's voices: `_lone_voice_is_the_second` routes a lone voice to
`\voiceTwo` PER MEASURE, so `_lily_staff_block` now fixes the lanes ONCE, before
rendering, and the planner sees the lanes the renderer will use. Touching is not
overlapping — `e'4\!\>` is ordinary and is kept.

Full reading:
[benchmarks/omr-hairpins-2026-09/FINDINGS.md](benchmarks/omr-hairpins-2026-09/FINDINGS.md),
including why the stop-rule constant is weaker than the ones around it (its
plateau is real and nothing in the corpus exercises it).

---

## Articulations, and the time signature's own glyph

Both shipped 2026-09-01 out of the corpus widening
(`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`), and both are the shape
this project has now paid for eight times: **the signal was detected and
something downstream threw it away.** Neither needed the detector touched.

**A time signature carries a GLYPH as well as numbers.** `4/4` and a common-time
`C` are one bar length and two engravings; MusicXML says so with `symbol=`, and
musicdiff charges the difference at a flat **3 edits per staff** — 25 staves of
Bruckner 5 is 75 of them. `parse_time_signature` sets `symbol` ("common" /
"cut") only where a `timeSigCommon` / `timeSigCutCommon` glyph was detected, at
confidence 0.89-0.96 on the works measured. Worth **273 edits over five works**,
each delta exactly three times that work's staff count.

⚠️ **`symbol` is not `raw`, and exporting off `raw` would be wrong.**
`_propagated_meter` SYNTHESISES `raw` from the winning numbers (`"C"` for any
4/4), so a `raw` of `"C"` is not evidence that a C was printed. Only `symbol`,
set at the one place the glyph is read, reaches the export.

**The numbers come from the work; the glyph comes from the page.**
`dossier.apply_meter` used to replace the whole dict — including on the branch
where the detector AGREED — so the reading was discarded. A dossier is built
from one MusicXML file and can say a movement is in 2/2; it cannot say whether
THIS edition set that as a stroked C or as two digits, because that is a fact
about the engraving. The override now keeps the detected `symbol` where the
numbers agree, and drops it where they do not: a `timeSigCommon` read on a 3/4
movement is a misread, and its glyph is as wrong as its numbers.

**Articulations reach both exporters.** `export.py` contained the string
"articulation" once, in a docstring, while the detector maps all ten DSv2
`artic*` classes to category `ornament` and fires them freely — Mozart 40
detects **exactly 102** staccati and was charged **exactly 102**
`insarticulation` edits. The three works the benchmark used to consist of print
0, 2 and 6 of them, which is the only reason it survived sixteen fixes.

`transcribe._attach_articulations_in_cell` gives each mark to the notehead
nearest it in x on the side its own class names, within **0.75 notehead
widths** — the unit, not the mark's own bounding box, which is the mistake the
augmentation-dot gate made. Not a tuned constant: swept over eight works and
scored against the truth, **0.50 through 2.50 are identical** (197 placed, 193
correct, precision 0.980) with a cliff below at 0.30 (placement 0.486). A mark
with no notehead on the correct side is left unattached — 21 of 218.

⚠️ **This one makes pooled OMR-NED WORSE by 97 edits and shipped anyway**, which
is worth stating plainly. It is −122 across the eight works whose pages segment
correctly and **+219 on `boulanger-printemps-mvt1` alone** — a 46-part score
that emits 43 parts and spends 76% of its budget on whole-measure and
whole-staff operations. Its marks are not wrong there: 263 of the 271 printed
articulations are exported, with the right kinds. What is wrong is that its bars
do not pair, so every correct symbol added to one raises a charge already being
levied whole. Same call as `b8ccc89` (chords written bottom-up, +2 edits, still
right), at a larger number and with the counter-argument recorded beside it.

---

## The cell's own edge is not a notehead

A measure cell is the staff plus four staff spaces of air
(`measure_extractor.PAD_ABOVE_STAFF_LINES`), and on a conductor's page four
spaces reaches into whatever the staff next door printed. The crop slices it,
and **a wide flat sliver of ink is exactly the shape of a hollow notehead.**

On the engraved Brahms 1 benchmark page, whose truth contains no whole note at
all, that produced seven `noteheadWholeInSpace` — two of them the bowl of the
**g** in the word *legato*, one the lower bowl of the **8** of a 6/8 printed on
the staff above, and four real noteheads belonging to the staff above or below.
`transcribe._drop_clipped_notehead_fragments` takes them out at detection time,
worth pooled 0.2209 → **0.2137** (Brahms 1256 → 1201 edits) — ten detections and
55 edits, because a bar that differs by one spurious note is charged as a whole
bar inserted plus a whole bar deleted. (It was worth 99 edits when first
measured, before the ledger-attribution fix landed and took some of the same
damage a different way.)

**The discriminator is the one dimension a notehead cannot vary in:** it is a
staff space tall, because that is what a notehead is. Measured over the three
benchmark works (`benchmarks/omr-ned-2026-08/probe_edge_fragments.py`), interior
noteheads run 0.61–1.12 spaces with none below 0.60, the fragments 0.29–0.56,
and the notes a crop merely grazes 0.77–0.99 — a note the boundary barely
reaches is still almost all there. Restricted to detections that TOUCH an edge,
which is the mechanism; a short notehead in the middle of a cell is a different
problem and this has no opinion on it.

⚠️ **Do not fix a clipped note by growing the pad.** Measured at
`PAD_*_STAFF_LINES = 5`: Brahms 0.3420 → **0.3732** (+128 edits), cross-staff
duplicates removed 135 → 390. A taller crop makes more contested glyphs, and
`_dedupe_cross_staff_detections` resolves a contest by distance to the nearer
five-line band — which for a note in a gap the engraver opened *for* it is the
wrong staff. Brahms's C Horn 2 is the worked example: its `C3` sits 4.5 spaces
below a treble staff, four pixels past its own cell, and at pad 5 the note goes
to Eb Horn 3 by 19 px while C Horn 2 stays empty. See the DIAGNOSED section of
`benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md`.

---

## Orchestral end-to-end benchmark

`benchmarks/omr-orchestral-e2e/` — renders an excerpt of a Gradus MXL back to
PDF through LilyPond, so every note is known by construction, at eleven to
twenty-five staves. The first measurement of note accuracy on a conductor's page.

```bash
python3 -m tools.omr.training.orchestral_eval
python3 -m tools.omr.training.orchestral_eval --works mahler-sym5-mvt1 --no-dossier
```

The input is engraved, not scanned, so a failure is a failure of recognition on
dense music and cannot be blamed on print quality. It says nothing about scan
robustness.

**ELEVEN WORKS SINCE 2026-09-02** (`accuracy_record.BENCHMARK_WORKS`, which is
where the set and the per-work reasons live). It was three —
`beethoven-sym5-mvt1`, `brahms-sym1-mvt1`, `mahler-sym5-mvt1` — and sixteen
fixes were landed against those three and measured on nothing else. The corpus
widening ran eight more engraved orchestral pages of the same kind and they
scored roughly **twice** the incumbents' error rate, so the three-work figure
was hiding a distribution rather than summarising one. Three of the faults that
surfaced were invisible to the incumbents by accident of what those pages print:
a cut-common glyph read at 0.92 and dropped on export (all three incumbents
print digit meters), triplet digits filed under `fingering3` (two incumbents
have none), articulations never exported at all (0, 2 and 6 detections across
the three). It also falsified a documented claim about the incumbent Mahler —
"its fifth triplet group carries no marker at any confidence" — which was the
**highest-confidence** marker on the page, under the other class name.
*A benchmark of three pages cannot falsify a story about one of them.*
Full reading: [benchmarks/omr-corpus-widening-2026-09/FINDINGS.md](benchmarks/omr-corpus-widening-2026-09/FINDINGS.md).

The eight added: `mozart-sym40-mvt1`, `mozart-sym41-mvt1`,
`beethoven-sym3-mvt1`, `brahms-sym4-mvt1`, `dvorak-sym9-mvt4`,
`tchaikovsky-sym4-mvt2`, `tchaikovsky-sym6-mvt2`, `bruckner-sym5-mvt1` — chosen
on the three axes a fix tuned on three pages could break (era, part count,
texture/meter), with `beethoven-sym3-mvt1` and `brahms-sym4-mvt1` as deliberate
**near-neighbour controls** for two incumbents: a distant composer failing is
ambiguous, a near neighbour failing is not.

⚠️ **`boulanger-printemps-mvt1` is deliberately NOT pooled**, and stays runnable
with `--works boulanger-printemps-mvt1`. At 46 parts it is the one work whose
*structure* fails — 43 parts against 46, with 76% of its budget in `entire
measure` and `entire staff` operations — so it measures page segmentation on a2
paper rather than note recognition, and it dominates any pool it enters (alone,
it moved the widening pool 0.2057 → 0.3846). It is also where a correct fix
looked like a regression: the articulation work read 263 of its 271 printed
marks and its OMR-NED still **rose**, because a symbol added to a bar already
charged delete-whole-plus-insert-whole costs more. Its row is kept and honest in
FINDINGS.md §2 and §4; what it must not do is set the headline.

**Fixtures are build products, not artifacts to move.** `excerpt()` regenerates
every truth XML and rendered PDF from the score library on each run, into
`--work-dir` (default `benchmarks/omr-orchestral-e2e/fixtures/`, gitignored), so
a default run is self-contained with no flags and nothing on disk. The widening
ran with its own `--work-dir` so a parallel canonical run could not collide;
that directory's committed provenance (`FINDINGS.md`, `out/*.json`) is
unchanged by the widening of the default.

### What eleven works still cannot see

⚠️ **A corpus that cannot express a fault cannot regression-test its repair**,
and a benchmark that says what it cannot see is worth more than one that implies
coverage it lacks. Measured on the widened set with
`benchmarks/omr-direction-text-2026-09/probe_empty_measure_marks.py`, which asks
the question in both directions:

| side | what it asks | 3 works | **11 works** |
|---|---|--:|--:|
| truth | a bar carrying a mark and no note — the SHAPE | 1 | **6** |
| pred (`--direction-text`) | our export having one — the same shape | ~1 | **20** |
| either | a bar carrying a mark and **nothing at all** — the TRIGGER | 0 | **0** |

The bug it is about: a measure with no detected events takes the
whole-measure-rest path, which never calls `_mxl_voice_events` — the only
`<direction>` emitter — so placed directions AND dynamics are computed and then
discarded. **The trigger is the DETECTOR finding nothing**, which is why the
shape is not the trigger: a rest IS an event, so a bar of rests takes the normal
path and its marks survive. Widening multiplied the near-misses sixfold (the
`P1 m1` tempo mark over a resting first part, in Beethoven 5, Brahms 4, Bruckner
5, Dvorak 9, Mozart 40 and Tchaikovsky 6) and added **not one** triggering bar.

⚠️ **AND THE FIX WAS NOT IN THE TREE UNTIL 2026-09-03, though this paragraph
said it was.** Commit `a907e41` (and its duplicate `46e42a4`) describes it in
full — "Both export sites had it", "Both are covered by tests now" — and its
diff is ONE FILE, a Surya determinism probe; `git log --all -S 'directions=_dyn'
-- tools/omr/export.py` finds the hunk on no branch, and
`test_direction_text.py` had no test for the case. It was found by reading the
branch rather than the log, while wiring hairpins into the same two export
sites, and closed in `export._mxl_empty_measure` with the unit tests the message
had promised. **THE TREE OUTRANKS THE LEDGER**, including a ledger written as a
commit message inside it. Measured on the scan benchmark, where the trigger
actually occurs: **2 bars** carry marks and no events, both dynamics, and
recovering them costs **+10 edits** (0.7517 → 0.7525) — every one of them
`entire measure insert/delete`, because both bars were already charged whole.
Same call as the articulation ship.

So: **the eleven-work benchmark does not guard that fix.** Its unit tests in
`test_export.py` (`TestEmptyMeasureDirections`) are the only thing that does.
The pred row is measured
under `--direction-text`, which emits strictly more marks than a default run and
therefore has strictly more chances to trigger — a zero there is a zero for the
default configuration too. The likeliest future source of a real triggering bar
is a **scanned** work, where a staff genuinely rests through a marked bar and
the detector finds nothing in it; every work here is engraved, and engraved
pages put an event in every bar.

⚠️ **THAT PREDICTION WAS CORRECT, AND THE BUG IS LIVE — measured 2026-09-04.**
Over 11 scanned pages with hand-verified windows, the eventless-measure branch
computes `measure_directions()`, assigns it to `_dyn`, and never uses it:
**14 dynamics are read and discarded**, against **0** on the engraved eleven —
the benchmark's blindness and the scan's exposure, both confirmed on the same
run. The attribution is exact rather than inferred: `words formed − words in an
eventless measure == words exported` on **all eleven pages, to the mark**. Both
of `export.py`'s two measure emitters carried it identically. **FIXED
2026-09-04** (`_mxl_directions_only`, called from both): the marks are emitted
in x order at the head of the bar, ahead of the whole-measure rest, because a
`<direction>` carries no duration and applies where it sits.

**CONTROL: the eleven engraved works export BYTE-IDENTICALLY** — the fix cannot
move the pooled figure, which is the same fact as the benchmark not being able
to see the bug. On the scans it recovers the 14, on 5 pages of 11. ⚠️ **The
benchmark therefore does not guard the repair either**, so
`TestEventlessMeasureKeepsItsMarks` does, including a source-level anti-drift
test asserting BOTH MusicXML emitters call it — verified to fail when either
call site is removed. (The LilyPond exporter is deliberately excluded: it never
calls `measure_directions` at all, so it drops dynamics on *every* measure —
a wider gap, not this one, and not on `KNOWN_GAPS` because
`export_coverage` compares MusicXML.) Measured by
`benchmarks/omr-dynamics-band-2026-09/probe_dynamic_band.py --funnel`.

---

## Contextual analysis — part identity, in the pipeline

`transcribe()` runs a **contextual post-pass** by default (`--no-contextual` to
skip). It names each staff's part, assigns stable slots across systems, fills in
clefs the detector never read, and writes a `contextual` block into the result.

Until 2026-08-31 `apply_contextual_analysis` was reachable only from benchmarks,
so the clef figures quoted below (48/52 → 49/52 → 50/52) described a path no
transcription ever took. Wiring it in is what makes them true of the output.

It is a **post-pass over the built page dicts** — a clef hypothesis is arithmetic
on already-resolved pitches — so nothing about detection, rhythm or segmentation
changes, and a score where it finds nothing serialises unchanged. A failure is
recorded in `contextual.reason` rather than raised: a transcription that
succeeded is never lost to an optional enrichment.

**The exporter now names parts by instrument.** A Beethoven 5 page with no text
layer exports as `Flute / Oboe / Clarinet / Bassoon / Horn / Trumpet / Timpani /
Violin / Viola / Cello` instead of `Staff p47-s0-N`. Staves it cannot name keep
the old coordinate form, so `--no-contextual` output is unchanged.

⏱️ **Cost, and how to remove most of it.** The pass re-uses `transcribe`'s own
staves rather than re-running phase 1, so it is cheap in itself — but the Surya
rung spawns llama.cpp and loads a 650M model, and by default kills it again on
exit, paying that on *every* run.

**Surya implements the persistence itself** (sentinel file + health probe), so
this is a flag rather than a server anyone has to write:

```bash
python3 -m tools.omr.staff_labels_surya --serve    # start it, model loaded
export OMR_SURYA_KEEP_ALIVE=1                      # runs attach instead of spawning
python3 -m tools.omr.staff_labels_surya --check    # is one up?
python3 -m tools.omr.staff_labels_surya --stop     # give the 1.7 GB back
```

Measured on a 17-staff page, identical output either way (9 labels):

| | contextual_s | whole transcribe |
|---|--:|--:|
| spawn-and-kill (default) | 21.4 s | 44.0 s |
| **resident server** | **6.9 s** | **30.6 s** |

**Off by default** — the resident process holds ~1.7 GB, and that should not
appear on someone's machine because a default said so. The 6.9 s residue is the
worker's own `torch` import; only a long-lived *Python* process would remove it,
which is a much bigger lift for the remaining few seconds.

Absent entirely where `.venv-surya` is not installed, including the container.

⚠️⚠️ **THE KEEP-ALIVE SERVER IS SHARED, AND `pkill -f llama-server` DESTROYS
ANOTHER SESSION'S RUN.** Learned the hard way 2026-09-06: an agent tidying up
after itself ran `pkill -f llama-server` and killed the resident server a
*sibling* agent was reading through, costing that agent a multi-hour
transcription (`395e2193`, committed against itself). One machine has one
server; `--serve` detaches to **ppid 1 by design**, so a stray worker cannot be
told from the legitimate daemon by parent pid. **Never blanket-kill by name.**
Use `--stop`, and only when you know nothing else is reading.

⚠️ **And an orphan you cannot identify is safer left alive.** The same session
declined to clean up several suspected orphans for exactly that reason, which
was the right call: a second guess-driven `pkill` while another agent is mid-run
is worse than an unmeasured number.

✅ **The escape for an UNATTENDED run: `OMR_SURYA_KEEP_ALIVE=0`.** A worker per
page costs ~15 s/page and owns its own process, so the run can repair itself by
killing its own PID. The principle, from the session that hit the stall while
forbidden to touch the shared server: **an unattended run should not depend on
shared state it is not allowed to repair.** Use the resident server for
interactive work, where you can see who else is reading.

⚠️ **The wedge itself is UNDIAGNOSED, and three plausible causes were each
falsified**: CPU starvation (the machine went quiet and it still stalled),
retained page rasters (~3 GB, dropped, still stalled at the same count), and
"one specific page" (that page reads in 2 s from another window). Recorded as
unknown rather than as any of the three. The known symptom stands: a worker at
0.0% CPU against long elapsed while `--check` reports healthy, recovered with
`--stop && --serve`, hidden by piping (use `python3 -u`) — and a parent at 0% is
NOT a wedge if a child is burning CPU.

---

## An optional pass may abstain quietly — it may not fail like a defect quietly

`transcribe` runs two optional enrichments behind `except Exception`, because a
transcription that succeeded must not be lost to an enrichment that could not
run. **Not raising is not the same as not telling anyone**, and the gap between
those is how a documented on-by-default pass went dark:
`apply_contextual_analysis` renamed a parameter (`e518679`, 2026-08-31), the
caller kept the old name, and the TypeError was filed as an ordinary
"unavailable" — indistinguishable from the honest abstentions that pass makes
constantly (no text layer, no five-line geometry, no Surya venv).

**It was live on main for hours, not weeks** — it arrived with the five-branch
integration merge on 2026-09-01 and was fixed the same day. The duration is not
the lesson and an earlier draft of this section invented one; what matters is
that in those hours it cleared a five-branch merge queue, a full benchmark run
and a green suite without a single check noticing.

**Nothing caught it.** The suite was green. The OMR-NED number did not move —
contextual's two channels into the export (part names, clef fill) provably do
not reach the metric on dossier-seeded fixtures, part naming shown by experiment
to change the score by exactly nothing. The only trace was one stderr line gated
on `progress`, and `orchestral_eval` runs `progress=False`.

`_optional_pass_failure` now classifies the two:

| | what it means | how loud |
|---|---|---|
| abstention (`ImportError`, `FileNotFoundError`, …) | had nothing to work with | quiet unless `progress` |
| bug (`TypeError`, `AttributeError`, `NameError`, `KeyError`, `IndexError`, `ValueError`) | the code is wrong | **stderr always** |

`error_class` and `looks_like_a_bug` are recorded either way so a benchmark can
assert on them, and `orchestral_eval` **exits non-zero** when a pass failed like
a defect. Both swallows route through it, and a test asserts they still do.

⚠️ **The benchmark cannot regress-test contextual by its SCORE.** If that pass
dies again the pooled number will not move. The seam tests
(`test_transcribe_helpers.py`) and this guard stand in its place — do not
assume a stable OMR-NED means the pipeline is intact.

---

## Decisions made without a probability — the scan

The clef work found a lot being lost because a staff's clef was either SELECTED
or DISCARDED, with nothing between and no way to combine what the page already
knew. [docs/handoff-probability-gates-2026-09-05.md](docs/handoff-probability-gates-2026-09-05.md)
asks where else that shape occurs, and answers it by taxonomy — the sibling of
[docs/discussion-detector-right-output-wrong-2026-09-04.md](docs/discussion-detector-right-output-wrong-2026-09-04.md),
which asks the same question about signals that were read and then lost.

Five classes: **A** the probability is never formed (a boolean veto — the
`clef_locator` dot veto's "8 false positives removed for 20 declined C clefs" is
a hand-set threshold on a score that does not exist); **B** formed then quantised
(`instruments.Match.coverage`, a float, becomes `high`/`medium`/`low` and then a
flat `SCORE_LABEL_MATCH = 6.0` — `slots.py` and `score_layouts.py` are ALREADY
additive-evidence models and the evidence is binarised twice on the way in);
**C** formed, kept, consumed by nobody; **D** used only as an exclusive tier or a
raw argmax; **E** all-or-nothing structural refusals.

⚠️ **Two Class-C findings are the headline.** `grep -c '\bconfidence\b'
tools/omr/export.py` returns **1, and that one occurrence is a comment** — the
exporter treats a notehead detected at 0.26 and one at 0.98 as equally true, and
across the whole pipeline detection confidence reaches a decision at only four
places (three argmax, one threshold). And the five internal-consistency checks
compute a graded confidence that **nothing reads**: of the five warning keys,
only `rhythm_sum_warning` is consumed anywhere, by `backend/modules/local_omr.py`,
as a boolean presence count for a UI percentage. Measured on one real scanned
document (Breitkopf Brahms 1, 3 pages, 83 staves): **85 warnings fire and every
one is inert.** ⚠️ Volume is uneven and the honest reading matters —
`measure_count_warning` fired ZERO times across all 29 stored transcriptions,
corroborated by `benchmarks/omr-majority-steering-2026-08/findings.md` finding 0
disagreeing staves over 27 systems; the high-volume check (`rhythm_sum_warning`,
78 on that document) is the one with no confidence field at all.

**The best-evidenced combination is the one the clef session can use now.**
`clef_correction` decides on range fit alone behind two hard `return None`
cutoffs, and `grep -c clef_register_warning tools/omr/clef_correction.py` is
**0** — the register-inversion check fires on the same page dict (Brahms staff 3
vs 4: median MIDI 53 against 71, a 12-semitone inversion, labelled `advisory`)
and asks the same question from an independent direction. It needs NO instrument
label, which is what makes it worth having: 29 of 29 unresolved non-treble staves
on the scan corpus have no label printed at all, so it is the evidence that
survives exactly where label evidence is structurally unavailable.

⚠️ **The scan gate's biggest unarbitrated population is Class D.** With the
written-range veto never firing on a scan, all 4,256 cross-staff duplicates
across the 20-row gate are resolved by ledger ladder or by DISTANCE — a quantity
already caught being a coin flip (5-62 px) — and `_dedupe_cross_staff_detections`
has both detections' confidences in hand at the moment it decides and uses
neither.

⚠️ **AND THE CALIBRATION EXPERIMENT IT ASSUMES HAD ALREADY FAILED.** Reconciled
2026-09-05 against `claude/staff-identity-layer-2026-09-05`, which was asked for
calibrated identity probabilities and measured that NEITHER calibrates (P(name)
ECE 0.1277, P(set) 0.1301, n=197) — failing worst where a consumer would set its
bar, the top bin promising 0.989 and delivering 0.692. Its pre-registered
standard, adopted by the scan: **an uncalibrated probability is WORSE than none,
because it launders a guess into something that reads as evidence.** The failure
is the CORPUS (the `derived` tier that would decide an admission is EMPTY), not
the estimator. So the scan's `coverage`-into-`slots` item is DEMOTED, and its
clef item is re-framed — KC-3 showed `clef_correction`'s FILL reaches only 34 of
396 staves (8.6%) because it fires only where no clef was read, while the
documented ceiling is clefs read WRONG. The reachable question is the OVERRIDE
gate (`clef_correction.py:594-601`), whose `sources.get(slot) == "label"`
conjunct is unsatisfiable on scans — and `clef_register_warning` needs no label.
⚠️ **That last step is a REACH question, not a scoring one, and the framing
"just swap the conjunct" was withdrawn on 2026-09-05**: the label conjunct has
held-out evidence behind it (the p2 violas read as Violin ×3), so it is not
arbitrary. What survives is narrower — `clef_register_warning` names no
instrument, so that hazard does not apply to it, and it fires on staves that
HAVE a clef, the population the ungated path cannot see. Measure the reach
before the accuracy. Cross-session note, written for another agent to
open: [docs/handoff-probability-gates-2026-09-05.md](docs/handoff-probability-gates-2026-09-05.md).

⚠️ **Nothing in that document is a benchmark result.** The weights were absent
from the container, so no arm was run; the shortlist names which harness would
price each item and whether that harness can SEE it, which is the part this repo
has been bitten by before.

---

## Instrument identity — three readers, cheapest first

`contextual._labels_for_page` runs them in order and only pays when the free
ones come back empty:

| reader | cost | needs |
|---|---|---|
| `staff_labels.read_staff_labels` — PDF text layer | free | a text layer (18 of 65 IMSLP PDFs) |
| `staff_labels_surya.read_staff_labels_surya` — Surya 2, local | **free** | `.venv-surya` + `brew install llama.cpp` |
| `staff_labels_vision.read_staff_labels_vision` — Claude | ~1¢/system | `ANTHROPIC_API_KEY`; **off by default** |

```bash
python3 -m tools.omr.staff_labels_surya --bootstrap   # once
brew install llama.cpp
python3 -m tools.omr.staff_labels_surya --check
```

`surya_fallback=True` is the default and **self-disables when the venv is
absent**, so a machine that never bootstrapped it behaves exactly as before.
Surya spends no `vision_system_budget` — it costs nothing. Measured on the same
crops and the same free ground truth: Surya and Claude both score **zero
disagreements** against the text layer, and Surya resolves 89% of the staves
Claude does. It is not a worse reader; what it gives up is reach, because Claude
repairs a damaged label from the running order and an OCR engine transcribes what
is printed. See
[SURYA_BAKEOFF_2026-08-31.md](benchmarks/omr-margin-labels-2026-08/SURYA_BAKEOFF_2026-08-31.md).

⚠️ **A newly-readable page can surface lexicon bugs that were dormant, and the
lexicon is reader-independent.** Beethoven 5 p.48 went 0 → 12 labels and three
resolved to the wrong instrument — `Tr. Alt.` → *Alto*, a singer, at high
confidence — because `instruments.lookup` said so, which means the paid reader
returned the same answer for the same printed string.

Fixed 2026-08-31 (`instruments.py`). `Tr.` is Trombe **and** Tromboni, and
Beethoven 5 p.47 prints both — `Tr.` over the trumpets, `Tr. Alt. / Tr. Ten. /
Tr. Bas.` over the trombones four staves below. What separates them is the part
name beside the abbreviation: **a trombone section is scored by REGISTER and a
trumpet section by number and key** (`Tr. I`, `Trombe in C`), so Trombone gains
`tr alt` / `tr ten` / `tr bas` (and spellings), which outrank the bare `tr`.
`Tr. B.` is deliberately NOT among them — that is a trumpet in B-flat, the same
trap as `Cl. B.`.

The other half was a mechanism gap: `VOICE_QUALIFIERS` is what stops a size word
beating an instrument noun, and it was HAND-LISTED with the spelled-out `alto`
and `tenor`, so an abbreviated `Alt.` never reached it. It is now **derived** from
the voice instruments' own aliases, which also fixes `Fl. Alt.`, `Cl. Alt.` and
`Trb. Tenore`. Validated on 1380 margin labels across 10 editions —
[LEXICON_TR_ALT_2026-08-31.md](benchmarks/omr-margin-labels-2026-08/LEXICON_TR_ALT_2026-08-31.md).

⚠️ **THE SAME PAGE, THE SAME EVIDENCE, AND THE THIRD INSTANCE OF THE FAMILY —
BUT THIS ONE IS NOT A LEXICON FAULT** (fixed 2026-09-06, `contextual.py`). On
that same Litolff Beethoven 5, `lookup('Tp.')` returns **Timpani at `high`** and
the timpani still exported as a **second trumpet**. `Tp.` is Timpani in the
German and Italian tradition and Trumpet in the English one, so it is declared
in `AMBIGUOUS_ALIASES`, which hands the slot to
`score_layouts.resolve_ambiguous_label` — and the canonical layout puts the
timpani AFTER the trombones while this edition prints it BETWEEN the trumpets
and the trombones (the deviation `score_layouts` already documents where it
explains pinning). The aligner is monotone, so staff 8 took the second trumpet
slot; being ambiguous had also withdrawn the PIN that would otherwise have
taught the aligner the print's order. **A correct lexicon, overturned by the
prior.**

**The evidence was already on the page and needed no lexicon change**: `Tr.`
stands four staves up on the same system, and an engraver does not name one
section with two different abbreviations on one system. So the prior **may not
move a staff onto an instrument a different alias on the same system already
names**.

⚠️ **The constraint is ASYMMETRIC — it refuses only an OVERTURN and never
removes the lexicon's own answer — and `Tr. Bas.` on p.48 is what forces that.**
That staff's candidates are Trombone and Trumpet and **both** are separately
named on its system (`Tr. Alt.`/`Tr. Ten.`, and `Tr.`), so a rule excluding
every clashing candidate would have nothing left to choose and would break a
reading that is already right. Measured over the 1422-label corpus
(`probe_ambiguous_cooccurrence.py`): 86 of 158 ambiguous-alias occurrences clash
— 52 `cor`, 18 `tp`, 9 `tr bas`, 7 `basso`/`bassi` — and hand-adjudicated the
rule **keeps or restores the right answer in 86 of 86 and blocks a correct
overturn in 0**.

⚠️ **The control that matters is `basso`, and it passes because every clash is
HANDEL's.** `c0a80ae7` fixed `Basso.` at the foot of an orchestral score by
letting position overturn the lexicon's `Bass voice` to Contrabass; no
orchestral page in the corpus names Contrabass twice, so that overturn is
untouched — confirmed in the live A/B, where `ambiguous_labels_resolved` falls
2 → 1 and the survivor is exactly that Contrabass. Handel's *Messiah* prints
`BASSO` (the bass **voice**) and `Bassi` (the string basses) on one page and
needs both first answers as they stand; there the two labels block each other,
which is the rule doing the right thing rather than a limit on it. The probe
**fails** if an orchestral source ever joins that list.

Same-tree A/B on `--pages 23,44`, scored against the hand-read lineup: **24/29 →
26/29 correct**, the 17-staff finale system **16/17 → 17/17 exact**, `Timpani ->
Trumpet` ×2 eliminated and no other confusion moved. Exactly **3 staff records
change**, all slot 8, all `Trumpet(score_order_ambiguity)` → `Timpani(label)` —
the name is now attributed to the page it was read from instead of to the prior.
⚠️ The remaining 3 errors (`Violin`/`Viola` → Trombone on the reduced 12-staff
system) are a different fault and this does not touch them. Known limit,
accepted with its reason: a real *tromba bassa* on a page that also prints `Tr.`
would be blocked from the correct overturn; nothing in either corpus prints one,
and the lexicon already records Trombone as much the commoner reading. Pinned by
`test_contextual_ambiguity_uniqueness.py`, every test run RED with the guard
removed.

⚠️⚠️ **THE BUG LIVES IN EXACTLY ONE OF THREE REGIMES, AND IT IS NOT THE WEB
APP'S.** Measured on all three, same tree, same edition:

| window | what it is | fix vs control |
|---|---|--:|
| `--pages 0-4` | **what the web app actually does** (`local_omr.py:233` is `range(min(n_pages, max_pages))`, default 5) | **byte-identical, 0 records** |
| `--pages 23,44` | a window SPANNING the movement boundary | **3 records, 24/29 → 26/29** |
| 88 pages | the whole work | **no-op** (already correct) |

**The bug needs a window that spans the movement boundary** — one holding both a
reduced 12-staff system and the finale's 17-staff lineup, so the timpani has a
trombone run to be displaced past — **and thin enough that the layout fit has
little evidence.** Pages 0-4 are movements 1-3 only: an 11-slot reference, no
trombones, the timpani at slot 6 where the canonical layout also puts it, so
nothing overturns and the guard never fires. At 88 pages the fit has enough
systems to get slot 8 right on its own. ⚠️ **So this is NOT a fix to the default
web-app path**, and must not be described as one; its reach is the CLI with an
explicit `--pages` spanning movements, and any run with `OMR_MAX_PAGES` raised —
which is the whole-work use case this project is actually for. It ships because
it is correct, cheap, and **proven inert in the other two regimes** rather than
because it moves a production number.

⚠️ **Corollary for anyone measuring identity work: there are THREE cells, not
two.** Narrow-at-the-front (what production does) and narrow-anywhere (what a
repro does) are different regimes, and they differ precisely in whether the
window crosses a movement boundary — which is what exposes this whole class of
bug. A fix scored only on pages 0-4 and only on the whole work would have
measured this one at exactly zero, twice.

The committed 88-page artefact
(`benchmarks/omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json`)
already has slot 8 = Timpani and `ambiguous_labels_resolved = 1` — with a whole
work's worth of systems voting, the layout fit proposes Timpani or abstains, and
the guard is a **no-op** there. So the fix repairs narrow runs and is invisible
on that artefact; do not quote 24/29 → 26/29 as a whole-work number. **This is
the third time page-set size has changed an identity result** (the whole-work
session measured `--pages 0-2` collapsing 11/12 → 4/12, reproducible with
`OMR_MAX_PAGES=5`), so score any identity change on BOTH a narrow set and the
88-page extract — they can disagree in either direction, and here they do.

⚠️ **The 7 residual errors on that 88-page run are MIS-SLOTTING, not
mis-naming**, and the distinction is what tells you where to look. Scored:
800/807, `Violin -> Trombone` ×4, `Viola -> Trombone` ×2, `Timpani -> Trombone`
×1, all on 12-staff systems (the 17-staff finale systems are **663/663**). Every
wrong staff carries `instrument_source: label` — the strings land on slots
9/10/11, the finale's trombone slots, and inherit the name those slots were
correctly given by the finale's own labels, since a name is stamped per SLOT and
written onto every staff of that slot on every page. The tail is anchored right
(Cello 15, Contrabass 16), so it is an off-by-three in the monotone DP over a
reduced system: 12 staves against a 17-slot reference needs five deletions and
it deleted 12/13/14 instead of 9/10/11. That is `slots.align` / `assign_slots`,
**not** the movement reference and not the absent-instrument veto — neither is
in play in that artefact.

**The same shape again, 2026-09-03, and the same answer: DERIVE the cross
product.** A contrabassoon is printed as a BASSOON name with a contra- qualifier
— four languages of noun against four of qualifier plus the abbreviations a
crowded margin uses — so its spellings are a cross product and the hand-list held
six of about twenty-five. ⚠️ **The missing ones did not abstain**: the bassoon
noun inside them matches on its own, so `Contra-Fagott` and `Cont. Fag.` read as
**Bassoon** and `C. Fagotto` as Bassoon at HIGH confidence. `_CONTRA_ALIASES` is
now generated from `_BASSOON_ALIASES`; `contraf` stays listed apart, being a
truncation rather than qualifier-plus-noun. **This does not loosen the gate** —
every generated string still has to appear word-bounded and exact.

⚠️ **The reported string was not where the damage was.** `Contrafagott` on a
Mahler scan is what got noticed *because it abstained*; measured over 1422 real
margin labels the live cost was **ten staves of the scan benchmark's own Brahms 1
/ Breitkopf**, whose `K. Fag.` read as Bassoon on a page that also prints two
real bassoon staves. Fix the family the reported string belongs to, not the
string.

**Two more decisions recorded there.** (1) **The OCR fold belongs in the
lexicon, admitted on RARITY**: `_OCR_FOLD` gained `y → v` (a printed `Violino`
read as `Yiolino`) because `y` occurs in only `tympani` and `xylophone`, both of
which resolve on the exact pass before the fold runs. Common-letter pairs —
`a/u`, `b/h`, `c/e`, `n/m` — are **refused by name**, at the priced cost of
`Fug.`→`Fag.`, `Oh.`→`Ob.` and Mahler's `Veelle.`; a gated single-substitution
matcher was prototyped, measured collision-free and **not adopted**. (2)
**Reader markup belongs to the reader.** Surya writes a stacked part number as
`\frac{1}{2}`, which survives normalization and dilutes `coverage`; that is
folded in `staff_labels_surya._plain_text`, not in the lexicon, because LaTeX is
the reader's output format. It changes **zero** resolutions on 1422 labels — the
Brahms strings are the two HORN staves and the page prints `Hörner` once braced
across them, so abstaining is right and no lexicon can recover them.

Validation harness, and the one to use for any future lexicon change (MusicXML
part names cannot see a margin-abbreviation fix):
[benchmarks/omr-lexicon-2026-09/FINDINGS.md](benchmarks/omr-lexicon-2026-09/FINDINGS.md)
— `read_margin_labels.py` dumps what the readers actually emit, `resolve_labels.py`
replays a dump through two revisions' lexicons.

**`Hr.` / `Trpt.` were fixed the same day, once measured** — 0 collisions
against the other 409 aliases and the 1271-name reference corpus, 24 of the
1422-label dump move and all 24 are Brahms 1's own horn/trumpet staves.
⚠️ The instrument NAME is right in every case; the transposition offset is
exact only where the key TRAILS the alias (`Hr. (E)` → -4), because
`_parse_bare_key` has only ever read the token AFTER a match — `(C) Hr.`
falls back to the positional default, the same pre-existing limit `A-Klar.`
has had since 2026-08-31.

**The last open item — a whole system margin arriving as ONE label — closed
2026-09-05, and it was a reader fault, not a lexicon one.** Re-reading the
exact pages (Beethoven 5 → *Piccolo*, Mahler 5 → *Trombone*) with the raw
per-block output surfaced showed Surya returning **exactly one OCR block for
the whole crop** on both — every instrument name on the page, one block,
where a healthy read splits one block per staff. `_assign` was never wrong
about which staff the block's centroid landed nearest; nothing recorded a
block's own SIZE, only its centroid, so a block spanning the whole crop
looked identical to a normal label. `_surya_worker._lines_with_boxes` now
also keeps each block's height, and `_assign` drops a block taller than half
the SYSTEM's own tick span before the nearest-tick test — scale-invariant
by construction, since the ratio is to the crop's own span, not a pixel
count. Measured: both bad blocks sit at **1.04×** the span (padding pushes
them slightly past 1.0); all 17 blocks Surya correctly split on Boléro's own
dense page sit at **1.5–4.7%** — a ~22× gap with 0.5 in the middle of it.
⚠️ **The first regression test attempt passed vacuously either way** — it
asserted on label LENGTH, and a single huge GLYPH is one character, not a
long string, so a tall block that should be rejected still produces a SHORT
string. Fixed to assert on staff ASSIGNMENT directly, and run red (gate
disabled) before green to confirm it actually exercises the mechanism. See
[benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md](benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md).

---

## Reading and reproduction are different questions, and now measured apart

Every figure below OMR-NED is taken at the far end — our exported MusicXML
against a truth MusicXML — so recognition and serialisation are fused. That is
why nine "detected, then dropped on the way out" bugs had to be found by
forensics: in OMR-NED a signal read perfectly and lost in the exporter is
indistinguishable from one never read.

**A page we RENDER has an exact truth available for free.** Verovio draws
MusicXML directly and, with `svgBoundingBoxes`, emits a `<rect>` per notation
object in the same frame as the glyph, plus every glyph's SMuFL codepoint —
image and inventory from one act, no labeling (`tools/omr/page_truth.py`).

⚠️ **A PAGE TRUTH IS NOT AN ENCODING TRUTH.** On the Brahms fixture, against the
file it was rendered from: dynamics 19 glyphs vs 19 `<dynamics>` (agree), G clefs
**28** glyphs vs **14** `<sign>G</sign>`, slurs **82** arcs vs **164** `<slur>`
tags. A clef is printed at every system and declared once; MusicXML writes a slur
at each end and the engraver draws one arc. The reader sees 28 and 82.

| | asks | tool |
|---|---|---|
| reading | did we see the ink, and call it the right kind | `page_truth` + `score_reading` |
| translation | did what we saw reach the file | `score_translation` |
| reproduction | does the file say what the truth says | `omr_ned` |

**Reading F1 0.919** over 11 engraved works / 3220 scoreable symbols, against
OMR-NED 0.1306 on the same works. The decomposition is the point:
**noteheads 0.999** (856 of 856), rests 0.993, time-sig digits 0.997, flags
0.992, clefs 0.969 — so the engraved residual is **not** a failure to see notes.
What is left splits three ways, and the split is the actionable part.
⚠️ **A family whose F1 climbs as the centre tolerance widens is FOUND AND
LOOSELY PLACED, not missed** — different work entirely. **Ties 0.260 → 0.504**
at 2 staff spaces: most ties are there. **Slurs 0.518 → 0.631**, barely moving —
real absences; on the Brahms page 16 of 40 have no arc within TWO spaces while
the 24 found sit at a median 0.09. And **over-emission** — dynamic letters
precision 0.421, key accidentals 0.722, both emitting more than the page prints.
⚠️ The tie/slur *classification* lever is NOT the answer and is already spent:
`00b68e24` (`claude/export-accents-arcs`) built the position-grammar veto,
measured it on both families and shipped it **default-off** — engraved neutral,
scan refused. This measurement says why it could not have helped much: ties are
mislocalised and slurs are absent, and neither is a labelling error.

⚠️⚠️ **`accidental` IS EXCLUDED AND THE NEAR-MISS IS WORTH KEEPING.** It scores
recall 0.257 and was about to be reported as the largest reading gap. It is not
a pipeline result: **Verovio draws one accidental per `<alter>`, not per
`<accidental>`** — Brahms 1 has 54 `<accidental>` and 149 `<alter>` and it drew
149; Beethoven 5 has ZERO `<accidental>` and 13 `<alter>` and it drew 13. The
rendered page carries accidentals a real engraver would never print. **What
caught it was a contradiction with an existing number** — `wrong pitch` is zero
on these works, which cannot be true of a reader missing three quarters of the
accidentals. `page_truth.render_fidelity` now measures the disagreement per work
and declares the family unreliable; `score_reading` marks it `(RENDER)` and
keeps it out of the pool. Including it gave 0.898; excluding it, 0.919.

⚠️⚠️ **THE HAIRPIN EXPORT BUILT ON THIS BRANCH WAS A DUPLICATE AND HAS BEEN
REMOVED AGAIN (`2ad144fb`, undone).** `53e6f233` on `claude/mystifying-curran-613606` already wires
`<wedge>` into both exporters AND fixes the staff attribution, and it *improves*
pooled OMR-NED (0.1304 → 0.1299) where the duplicate costs +11 edits for want of
exactly that fix; its findings are `benchmarks/omr-hairpins-2026-09/FINDINGS.md`.
It was invisible to the checks made — `KNOWN_GAPS` reflects **main**, and a
worktree scan sees only *uncommitted* work. **`git log --all --oneline -S "<the
thing>" -- tools/omr/` before building anything.** The DETECTION half is
genuinely unclaimed: scope in
[docs/scope-cv-hairpin-detection-2026-09-04.md](docs/scope-cv-hairpin-detection-2026-09-04.md).

⚠️ **HAIRPINS ARE PERFECT ON ENGRAVINGS AND ~1% ON SCANS, and the engraved
corpus hid it.** Reading F1 **1.000** against exact page truth (n=3); over 11
SCANNED pages the detector finds **1 hairpin against 198 `<wedge>` of truth** —
Brahms 1 p2 alone encodes 136 and we read one. A three-symbol sample on clean
pages cannot falsify a claim about a thin line on a scan. ⚠️ **This is the shape
Phase 4f already moved to classical CV** — stems and beams left the detector on
the stated grounds that YOLO bounding boxes are structurally bad at thin lines,
and a hairpin is a thin diagonal line with no `line_detection` path at all
(`staff_detector` mentions hairpins only to reject them). The discriminator such
a reader would need is measured: **a hairpin is always BELOW its staff, 8 of 8
in the page truth**, which is also what fixes the attribution error — 3 of
Mahler's 4 are filed under staff 18 while standing in staff 17's band.

**Stage 2 priced the open ninth export gap.** `wedge` sat in `KNOWN_GAPS` as
un-priceable from that inventory; the funnel prices it: **9 hairpins read across
three works and every one discarded** (Mahler 5 4-of-6, Tchaikovsky 6 3-of-6,
Brahms 4 2-of-5) — half a reading problem, half an export problem, and the export
half is free. It also found a **new** one no existing check can see: Beethoven 5
detects 36 fermatas, its truth has 36, and **35** reach the file —
`export_coverage` fires only on the categorical case (truth some, ours zero).

⚠️ **The two stages read different images on purpose** (stage 1 a Verovio render
whose ink is known, stage 2 the LilyPond fixtures the headline uses), so their
per-family counts are NOT comparable to each other — compare within a stage.
⚠️ **Neither says anything about scans**: renderer truth exists only where we
make the page, and no public symbol-level ground truth for real printed scans
exists to borrow (DeepScoresV2 is rendered, MUSCIMA++ is handwritten).
Controls: matching is on centres, not IoU, and the pooled F1 moves 0.846→0.876
across 0.25–1.5 spaces of tolerance; re-rendering at 600 dpi moves Brahms 1
0.854→0.868 and Tchaikovsky 4 0.787→0.789, so it is not a resolution artefact.
Full reading, including the two frame errors it found in itself:
[benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md](benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md).

---

## OMR-NED — the metric other people also report

Every other number in this repo is bespoke and therefore incomparable to
published work. OMR-NED (*Sheet Music Benchmark*, ISMIR 2025, arXiv:2506.10488)
is the standard: `(insertions + deletions) / (symbols_pred + symbols_truth)`
over musical symbols, **lower is better**, computed by `musicdiff` 5.2.

```bash
python3 -m tools.omr.omr_ned --bootstrap                 # once — builds .venv-omrned
python3 -m tools.omr.training.orchestral_eval --omr-ned  # scores the whole benchmark
python3 -m tools.omr.omr_ned pred.musicxml truth.musicxml
```

musicdiff needs Python ≥ 3.10 + music21 ≥ 9.9.1 and the host is 3.9, so it runs
out of process in a gitignored `.venv-omrned` and talks JSON — the same shape
`maestro_bridge.py` uses for node. `tools/omr/_omrned_worker.py` runs INSIDE
that venv and must never import from `tools.*`.

⚠️ **A fresh git worktree has NEITHER venv.** `.venv-omrned` and `.venv-surya`
are repo-root-relative and gitignored, so in a worktree the scorer refuses and
— worse — Surya silently self-disables, which makes a `--direction-text` run
score without the direction reader while looking like a normal run. Point at
the main checkout instead of re-bootstrapping:

```bash
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-surya .venv-surya
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/weights \
        tools/omr/training/data/weights          # WEIGHTS, the third one
```

(No env override exists for the Surya venv — `staff_labels_surya.VENV_DIR` is
computed from the file's own location — hence the symlink.)

⚠️ **The WEIGHTS symlink is the third one and it fails ASYMMETRICALLY** (found
2026-09-05): weights resolve CWD-relative, so without it `scan_eval` dies on
`FileNotFoundError: …hollow-graft-shift09….pt` while `orchestral_eval` still
runs — the same shape as the Surya trap, where one benchmark looks healthy and
the other does not.

⚠️ **And a FOURTH: `scan_eval` ignores `OMRNED_PYTHON`** and resolves
`.venv-omrned` worktree-relative (found 2026-09-06), so the env override that
serves `orchestral_eval` does not serve it. Symlink that one too:

```bash
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned
```

**Four symlinks, and three of the four fail on the SCAN side only** — a worktree
that runs `orchestral_eval` cleanly proves nothing about `scan_eval`.

⚠️⚠️ **A CACHED A/B FAILS SAFE-LOOKING, AND `scan_eval` CACHES BY DEFAULT.**
`scan_eval.run_pipeline` opens with `if pred.is_file() and raw.is_file() and not
force: return`, so **two arms sharing a fixtures dir with an empty `--tag` reuse
the first arm's transcriptions and the second arm never runs.** Caught
2026-09-06 one step short of being reported.

**The failure mode is what makes it dangerous**: a cached A/B always reports
*"identical on every bucket and every row"*, which is exactly the clean
"my change doesn't reach the metric, no regression" result a flag-guarded change
hopes for. **Nothing about the output invites suspicion.** The tell was WALL
TIME — minutes against hours — not the numbers.

**So: give every arm its own `--tag` (it needs `=`, as `--tag=-myarm`) or its own
work-dir, and check the clock before believing an identical A/B.** Contrapositive
worth knowing: arms that return *different* numbers did genuinely both run.

⚠️ **This paragraph is where the current figure lives, and nowhere else.** It
used to be restated in PROJECT_STATUS.md, NOTES.md and the next-steps doc, and
the `a271b1e` merge left three of the four copies stale without a warning: two
branches had each edited different copies, git auto-merged all of them cleanly,
and only the copy that CONFLICTED was resolved with a fresh measurement
(`ae7c259`). A conflict is loud; a clean auto-merge of the same fact held in
four places is silent, and the copy that loses is whichever file happened not
to collide. So the other three link here, and a new measurement updates this
paragraph only.

⚠️ **THE BENCHMARK'S DEFINITION CHANGED ON 2026-09-02 — 3 WORKS TO 11 — AND NO
FIGURE CROSSES THAT BOUNDARY.** At Sean's decision the headline widened from the
canonical three to eleven engraved orchestral works (see the *Orchestral
end-to-end benchmark* section for the set and why each is in it). A pooled
OMR-NED is a property of **the work set it is pooled over** as much as of the
pipeline, so an 11-work figure and a 3-work figure are measurements of different
things: **comparing them is invalid in either direction**, and a rise or fall
across the boundary is not progress or regression. For the record, the last
3-work figures were **0.0849 / 623 edits** (default, with the direction reader
on) and **0.1066 / 767** (`--no-direction-text`), both on `bc4214d`; that
three-work arc opened at 0.3164 on 2026-08-31. Those numbers are history and
belong to a benchmark that no longer exists — they are written here, in prose,
precisely so nobody reaches for them as a baseline for the block below.

The boundary is enforced, not just documented: `current-accuracy.json` carries a
`benchmark` stamp naming the work set and the date, `accuracy_record.check()`
refuses a record whose stamp disagrees with `BENCHMARK_WORKS`, and a record
written before 2026-09-02 has no stamp at all — so it is detectably
pre-boundary rather than silently comparable. Recording one configuration over a
new work set also **drops** the other configuration's run until it is
re-measured, so the paragraph can never state an 11-work default beside a 3-work
variant.

<!-- accuracy:begin name=headline -->
Current on the engraved orchestral benchmark, measured on `6b230bd7`: **pooled 0.1122 / 2362 edits** over 11 works (Mahler 5 0.0209 at best, Dvorak 9 0.3380 at worst), across 10665 truth + 10381 predicted symbols. The direction reader is ON by default and needs `.venv-surya` or Tesseract; with neither — `--no-direction-text`, and what a machine with no OCR rung gets — **0.1214 / 2532**, measured on `6b230bd7`.

| work | OMR-NED | edits | note recall | precision | duration rate |
|---|--:|--:|--:|--:|--:|
| Mahler 5 | 0.0209 | 40 | 0.917 | 0.917 | 1.000 |
| Beethoven 5 | 0.0293 | 38 | 1.000 | 1.000 | 1.000 |
| Tchaikovsky 4 | 0.0444 | 69 | 0.925 | 0.925 | 1.000 |
| Bruckner 5 | 0.0931 | 185 | 0.962 | 0.962 | 1.000 |
| Brahms 1 | 0.0943 | 390 | 0.956 | 0.955 | 0.992 |
| Mozart 41 | 0.1025 | 301 | 0.991 | 0.991 | 0.947 |
| Beethoven 3 | 0.1294 | 215 | 0.975 | 0.975 | 1.000 |
| Mozart 40 | 0.1415 | 218 | 0.762 | 0.762 | 0.952 |
| Tchaikovsky 6 | 0.1855 | 266 | 0.756 | 0.747 | 0.985 |
| Brahms 4 | 0.2136 | 401 | 0.959 | 0.943 | 0.933 |
| Dvorak 9 | 0.3380 | 239 | 0.975 | 0.975 | 1.000 |
<!-- accuracy:end -->

**An outside comparison exists, on our own fixtures and our own scorer.**
Published OMR-NED figures are pooled over other corpora and are context, never
comparison — so Audiveris 5.11 (plus oemer and homr, both since ruled out as
architecturally unable to read a conductor's page) was run on the SAME fixtures
this benchmark uses and scored through the SAME musicdiff bridge:
`benchmarks/omr-vs-industry-2026-09/` (`run_industry.py`,
`run_audiveris_scan.py`, per-engine records, per-category tables, and FINDINGS
with five addenda — two of them corrections of the file's own earlier claims).

⚠️ **Read its figures against the pool they were measured on, not against the
block above** — the scan benchmark's era moved 5 → 11 → 20 rows on 2026-09-04
and the Audiveris arm covers the 11-row pool; `scan-comparison.json` carries
that boundary stamp explicitly. Two operational facts worth knowing before
re-running it: Audiveris rasterizes PDFs at 300 dpi and hard-refuses images over
20 MP (so the harness renders each page at the highest DPI under that cap and
records it per row), and its batch mode does not exit on macOS after a
successful export (the harness polls for the file, then kills it).

⚠️⚠️ **THE 20-ROW SCAN GATE HAS A NOISE FLOOR OF ROUGHLY ±6 EDITS, AND ITS
RECORDED 0.8444 IS NOT A BASELINE FOR THE CURRENT TREE** (both measured
2026-09-05, `benchmarks/omr-merge-verification-2026-09/`; branch
`claude/merge-verification-2026-09-05`). Two separate corrections:

- **Not byte-deterministic.** `DETERMINISM_2026-09-04.md` measured a noise floor
  of exactly 0 — on the **five-row** era, and the bullet above now says so. On the
  20-row gate `beethoven-984073-p4` scores **4673 then 4679 on two runs of one
  tree**. So assume **≥ ±6 edits** on any single-arm 20-row figure; a smaller
  per-row delta is NOT evidence, and an A/B on the same tree is the only way to
  attribute one.
- **`c378412f`, which stamped 0.8444, is not an ancestor of much that has since
  landed** — the CV hairpin reader (`cf81b524`, 2 → 106 exported `<wedge>` on this
  benchmark), the Surya block-rejection (`823a88b4`), `condensed_parts.py`,
  `class_aliases.py`, ~385 lines of `export.py`; `git diff c378412f <head> --
  tools/omr` is 28 files. **A fresh run compared against 0.8444 measures that
  whole stack, not the change under test.** Re-run the control arm on the merge
  base instead — that is what showed the 2026-09-05 landing contributed exactly
  zero (0.8441 pooled, six rows moving, all of them inherited).

⚠️ **Two rows of that table are not read the way the others are.**
`dvorak-sym9-mvt4`'s excerpt auto-shrank to **3 bars** against everyone else's
6-8 (the one-page fit in `excerpt()`), so its denominator is a third of the
rest and its ratio is the noisiest in the set — it sits at the bottom of the
table on a third of the evidence. And `mozart-sym40-mvt1`'s note recall is not
a recognition number: its Viola plays divisi double stops, the truth splits
them into two voices and the page prints one two-note chord, so ~41% of its
notes land in `order` bars with **every pitch present on both sides**. Both are
measured in
[benchmarks/omr-corpus-widening-2026-09/FINDINGS.md](benchmarks/omr-corpus-widening-2026-09/FINDINGS.md) §5.

**Generated — do not hand-edit, here or anywhere.** `68be549` made this the
only place the figure is stated; this block makes it the only place it is
*written*, from `benchmarks/omr-ned-2026-08/current-accuracy.json`:

```bash
python3 -m tools.omr.training.orchestral_eval --omr-ned --record   # measure, record, propagate
python3 -m tools.omr.accuracy_record --check                       # has it drifted?
```

`--record` refuses a run without `--omr-ned`, over a subset of the works, with a
work that FAILED (silently absent from the results, so the pool would be smaller
than the benchmark), or with a failed pipeline pass — each would state a figure
for the whole benchmark that is not one. `test_accuracy_record.py` runs
`--check`, so a hand-edited figure fails the suite. HISTORY IS NOT MANAGED THIS
WAY and must not be: "pooled 0.2595 → 0.2489" against the commit that did it is
a frozen fact and is never rewritten.

⚠️ **Every figure measured before 2026-09-02 sits on a different fixture and is
not directly comparable to the current one** — including the 0.3164 opening
baseline. The Beethoven fixture's render dropped every fermata over a rest
(`musicxml2ly` does that), charging ~105 edits (≈0.014 pooled) against ink a
perfect reader could never have read; the render was completed on 2026-09-02
(`_restore_rest_fermatas` in `orchestral_eval.py`). Historical transitions stay
quoted as measured, with that floor in them — see the discontinuity note beside
the fix table in `docs/next-steps-omr-2026-09-01.md`. **That is a separate
discontinuity from the work-set one above, and they landed on the same day**:
one changed what the three pages CONTAIN, the other changed HOW MANY pages there
are. A figure from before 2026-09-02 differs from a current one for both
reasons at once, which is another way of saying it cannot be differenced.

Full
reading, and the findings it surfaced that note recall is blind to, in
[benchmarks/omr-ned-2026-08/FINDINGS.md](benchmarks/omr-ned-2026-08/FINDINGS.md),
[WRONG_NOTE_ATTRIBUTION_2026-09-01.md](benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md)
and [SLURS_2026-09-01.md](benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md).

**The next gap should be caught by a test, not by a day of forensics** — and
the eighth (accents) and every one since WERE. The count lives in ONE place,
numbered in `export_coverage.py` with the closing commit beside each entry;
prose that restates an ordinal goes stale the way a restated figure does.
Repeatedly a signal was recognised correctly and lost on the way to the file,
and the early ones were found only after the metric bucket they fell into grew
large enough for someone to open it. `tools/omr/export_coverage.py` asks the
question that found the seventh, on every run of the suite:

```bash
python3 -m tools.omr.export_coverage --all   # the inventory, with reasons
```

It compares element COUNTS between the truth file and our export, and reports
only the categorical case — the truth has some, we emit **zero**. That is the
signature of an export gap; emitting fewer than the truth is a recognition
shortfall and belongs to the accuracy metric. All seven read `truth N, ours 0`.

⚠️ **The obvious version of this check does not work**, and the reason is worth
keeping: auditing the DETECTOR'S CLASS SPACE for classes nothing downstream
mentions calls accidentals *consumed* — because they are, into `pitch` — and
clefs and time-signature digits likewise. Run on the benchmark it surfaced
`repeatDot` ×4 and `fingering3` ×1 while a 64-edit gap sat in plain sight. The
question is never "does anything consume this class"; it is "does anything the
reader would SEE come out".

`KNOWN_GAPS` is an inventory rather than a suppression list — every element we
knowingly drop, with its reason and its size — and anything not on it fails.
**And an entry that has been CLOSED must leave it**, or the list stops
describing the exporter and starts describing its history —
`test_the_inventory_has_no_stale_entries` enforces exactly that. Both former
open items are now closed: **hairpins** (`wedge`) left the list when the
hairpin export landed (staff attribution + `<wedge>`/LilyPond emission, merged
in the 09-05 reconciliation; export closed — DETECTION is still partial, 4 of
Mahler's 6, so hairpin counts remain a recognition matter), and **accents**
were closed by the articulations work (`0eb1271`, merged `bdda54d`
2026-09-02): `articAccent*` is attached by `_attach_articulations_in_cell`,
both exporters emit it, Mahler 6-for-6 against its truth (verified live
2026-09-04).

⚠️ **The accents claim outlived its fix by two days in this file** — a gap
that stayed CLOSED in the code and open in the doc, which seeded a work order
to "close" it again. `benchmarks/omr-export-gaps-2026-09/FINDINGS.md` §1
holds the reconciliation and names the failure shape:
*fixed-then-kept-open-in-prose*, the documentation dual of
detected-then-dropped.

**Three traps when reading it.** (1) The metric is SYMMETRIC — swapping
prediction and truth does not change the score, it only changes which file is
parsed strictly, which is why `score_pair` is keyword-only. **The same symmetry
rewards emitting MORE symbols**, so a ratio that falls while `omr_ed` RISES is
dilution, not recognition — the first cut of the slur work did exactly that.
(2) A large `entire
measure insert/delete` bucket is amplified, not necessarily severe: a measure
differing only by a fermata is charged delete-whole-bar + insert-whole-bar. Open
the op list before believing it. (3) **`wrong note` does not mean wrong
pitches.** musicdiff maps `noteins`/`notedel` to `wrong note` and
`pitchnameedit` to a separate `wrong pitch`, which is zero on all three works —
so `wrong note` counts notes the aligner would not PAIR, and what usually stops
it pairing is the duration. One misread rhythm costs about eight edits there.

⚠️ **Traps (2) and (3) were both re-measured on the 20-row scan gate 2026-09-05
and both need qualifying** (`benchmarks/omr-scan-attribution-2026-09/`):

- **(2) is a LOWER bound on elementwise cost, and none of it is recoverable by
  re-scoring.** `_block_diff_lin` is a cost-MINIMISING DP over bars, so a pair
  is charged whole-plus-whole only where elementwise pairing would cost MORE.
  The fermata case above is real where bars are sparse, but "amplified, not
  necessarily severe" is the wrong instinct to carry into a fix: where this
  bucket is large the bars genuinely failed to correspond, and scoring
  differently will not shrink it. On the scan gate it is 29,685 edits (39.6%),
  and bar segmentation is sound on 17 of 20 rows — the exceptions are the three
  rows where `_stitch_slots` refuses and emits one part per system.
- **(3)'s `wrong pitch` is STRUCTURALLY UNREACHABLE under `AllObjects`, not
  empirically zero.** `AllObjects` excludes `Voicing` (32767 & 131072 = 0), and
  without Voicing musicdiff pairs notes *by pitch* — so every pitch error is
  REQUIRED to become `noteins` + `notedel` and land in `wrong note`. A zero
  `wrong pitch` therefore cannot be read as "our pitches are right" at any
  detail level that excludes Voicing. ⚠️ Related and checked clean here:
  `get_omr_ed_dict` silently files unmappable ops under `directionins` →
  `wrong direction`.

Two tools open a number up rather than restating it:

```bash
python3 benchmarks/omr-ned-2026-08/attribute_wrong_notes.py   # cause per part
.venv-omrned/bin/python benchmarks/omr-ned-2026-08/dump_ops.py PRED TRUTH
```

---

## Local OMR CLI (`tools/omr/`)

In parallel with the web app, you can run the OMR pipeline standalone — no Docker, no DB, no auth. Useful from another Claude session, a notebook, or a one-off script.

```bash
# From the repo root, transcribe → JSON:
python3 -m tools.omr.transcribe path/to/score.pdf --out out.json

# Specific pages, with overlay PNGs for visual debugging:
python3 -m tools.omr.transcribe score.pdf --pages 0-4 \
    --out out.json --overlays-dir overlays/

# JSON → LilyPond or MusicXML:
python3 -m tools.omr.export out.json --format lilypond --out out.ly
python3 -m tools.omr.export out.json --format musicxml --out out.musicxml

# .ly compiles to PDF:
lilypond out.ly  # → out.pdf
```

From Python:

```python
from pathlib import Path
from tools.omr.transcribe import transcribe, DEFAULT_WEIGHTS

result = transcribe(
    pdf_path=Path("score.pdf"),
    pages=[0, 1, 2],
    weights=DEFAULT_WEIGHTS,
)

# Walk the structure
for page in result["pages"]:
    for sys_ in page["systems"]:
        for staff in sys_["staves"]:
            for measure in staff["measures"]:
                for det in measure["detections"]:
                    if det["category"] == "notehead":
                        print(measure["measure_index"], det["class"],
                              det["bbox_page"], det["confidence"])
```

Full JSON schema + flag reference: [`tools/omr/README.md`](tools/omr/README.md).

---

## Key technical details

### Authentication
- JWT access tokens (8 hr expiry, `ACCESS_TOKEN_EXPIRE_MINUTES=480` in `.env`)
- httpOnly refresh cookie (7 day expiry) — auto-refresh on 401 via axios interceptor
- `AuthProvider` wraps the entire React app. `useAuth()` throws outside it.
- Auth state syncs to the axios client via `setAccessToken()` in `App.tsx`'s `AppShell`

### Database
- SQLite via aiosqlite (async). File lives at `/app/data/reengrave.db` in the container, backed by the `db` Docker named volume.
- SQLAlchemy 2.0 async style. All models in [`backend/database/models.py`](backend/database/models.py).
- Models include `Score`, `FlaggedDifference`, `KnowledgePattern`, `AutoAcceptRule`, `GradusScore`, `ComparisonSession`, `User`, `Payment`, `ScoreAccess`, `PasswordResetToken`, `TokenBlacklist`.
- **No migrations** — tables created via `create_all_tables()` on startup. Schema changes require dropping and recreating the DB.

### File storage
- Uploads: `/app/uploads/` → exposed as `/uploads/` via FastAPI `StaticFiles` and nginx proxy
- Exports: `/app/exports/`
- Snippet images: `uploads/{score_id}/snippets/{diff_id}_pdf.png` and `_xml.png`
- Local OMR JSON: `uploads/{score_id}/{pdf_stem}.omr.json`
- Local OMR MusicXML: `uploads/{score_id}/{pdf_stem}.musicxml`
- Gradus uploads: `uploads/gradus/{id}/`
- Comparison uploads: `uploads/compare/{session_id}/`
- All backed by Docker named volumes so they survive container recreation

### ⚠️ Erasing the staff lines before YOLO is MEASURED AND REFUSED

The natural architecture — do the classical CV first, record it, erase those
lines, and hand YOLO a cleaner page — costs **7-13 pooled reading points and up
to a third of the noteheads**. Measured 2026-09-04 against exact page truth, same
page and weights, on the case most favourable to it (clean engraved pages, where
staff-line removal is easy):

| | Brahms 1 | Mozart 41 |
|---|--:|--:|
| staff lines intact (what ships) | **0.876** | **0.921** |
| erased before YOLO | 0.805 | 0.793 |
| noteheads, intact | **1.000** | **0.996** |
| noteheads, erased | 0.870 | **0.774** (recall 0.642) |

Two mechanisms, both already recorded elsewhere here: **domain shift** — the
detector has never seen staff-less music, and the ScoreAug/Augraphy fair test
already priced that shape (augmented 0.122 vs production 0.652) — and **the
erasure is destructive**, since a notehead sitting ON a line loses ink when the
line goes (the same effect that leaves "every glyph in pieces" for
`key_signature_locator` on scans). ⚠️ And it MANUFACTURES the confusion it was
meant to remove: YOLO's `beam` detections go 46 → **105**, precision 0.783 →
0.343, on staff-line residue.

`remove_staff_lines(cells)` already runs BEFORE detection (`transcribe.py:3986`),
so both variants exist; **the CV rung takes the erased one and the detector takes
the original, deliberately** (`line_detection` step 1, `staff_header`, and
`direction_text._blank_detections`, which subtracts every detection so "find the
text" becomes "find the ink"). **The pattern that works is: erase for the CV
consumer, BOUND THE SEARCH for everyone else, never erase for the detector.**
n=2 works, engraved; a scan would be worse, not better. Full reading in
[docs/scope-cv-hairpin-detection-2026-09-04.md](docs/scope-cv-hairpin-detection-2026-09-04.md) §1b.

### Local OMR engine notes
- `tools/omr/transcribe.py` loads the YOLO model once per call, then iterates pages.
- The image pipeline is canonical-cell-based: each measure is sliced and rescaled so staff span is constant, giving YOLO a scale-invariant input.
- Phase 4f introduced classical-CV stem and beam detection (morphological opening + connected components) because YOLO bounding boxes are structurally bad at thin lines.
- Production weights (scan side): `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt` — **not a training run.** Rounds 3–5 measured that fine-tuning on the scan-label corpus DELETES whole classes (tie/slur/beam/augmentationDot/accidentalFlat/restWhole/ledgerLine → exactly 0) under every method tried (eleven arms: no-warmup, low LR, freeze, teacher distillation…), so the ship is surgery: the hollow fine-tune's seven notehead-class head rows grafted onto the 09-03 production (`deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`, itself a 1-epoch hollow fine-tune of the Phase-3.3 `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`), with a per-class confidence floor baked into those rows' biases (bias-shift 0.9 ≈ threshold 0.25 → 0.45). First checkpoint in three rounds to beat production on every measure of all three gate axes: half-noteheads 27 → 31, pitch+duration recall 0.435 → 0.510, dense notehead recall 0.941 → 1.000, scan-e2e pooled OMR-NED 0.7517 → 0.7493 (4 of 5 rows improve; the harness measured byte-deterministic on that FIVE-row era — noise floor exactly 0), 28 classes with 0 collapsed; exported ties 60 → 97 of 271. Records: `ROUND5_METHOD_2026-09-04.md` (benchmarks/omr-labeling-survey-2026-09/, lands with branch `claude/scan-weights-round4-continue-074940`) and `DETERMINISM_2026-09-04.md` (benchmarks/omr-scan-e2e-2026-09/, branch `claude/scan-e2e-determinism`). **Weights ROUTE by input domain when not pinned** (since 2026-09-03): scanned PDFs get this file, digitally engraved PDFs get the imgsz2048 checkpoint, which measures better there (0.1399 vs 0.1421 pooled) — see `OMR_WEIGHT_ROUTING` in the knobs table.
- Phase 3.4 attempted to add 6 custom classes (barlines, textDynamic) and caused catastrophic forgetting — those classes are now learned via classical CV instead, not YOLO. See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.
- **The 208-class space spells 32 glyphs TWICE, under two names, and consumers read one** (fixed 2026-09-04, `tools/omr/class_aliases.py`). The vocabulary is two annotation sets concatenated — fine at ids 0-135 (`dynamicF`, `articStaccatoAbove`, `tupletBracket`), coarse at 136-207 (`dynamicLetterF`, `articulationStaccato`, `tupleBracket`). Forty classes carry the SAME name at both ids so a name lookup sees both; thirty-two do not, and every consumer here was written against the fine spelling. A detection at id 192 was a forte `export._DYNAMIC_LETTER` could not spell — dropped with no warning, the same fault as `fingering3`/`tuplet3`. Confirmed mechanically by asking each consumer what it returns for both spellings. **It cost nothing when found** (the coarse block fires ZERO times across 3 engraved fixtures and 29 scanned pages of 9 publishers); what makes it live is the LABELING side — 26 hollow-campaign boxes are classed `dynamicLetter*` and `catalog.yaml` carries the coarse spelling at ids 190-195, so the next fine-tune trains ids the exporter cannot read. Renamed at the one place the model's `names` are read, so no call site knows. ⚠️ **Only 11 EXACT TWINS are renamed.** A coarser name is not a synonym: `numeral4` is NOT `timeSig4` (one numeral class covers meters, tuplet digits, fingerings and measure numbers — and a spurious `timeSig4` once shipped a 2/4 page as common time at 390 bar-check failures), `articulationStaccato` states no SIDE, `tuple` no NUMBER, `clefC` no LINE. Those 21 are recorded in `COARSER_THAN_CANONICAL` with what closing each would take, and `unaccounted()` fails the suite on any name in neither table — so a wider class space is a loud failure, not a silent drop.

### Claude Vision OMR notes
- Uses `claude-opus-4-6` (configurable). Two-stage prompt:
  1. Header pass — title, composer, parts, key sigs, time sigs.
  2. Per-page pass — measure-by-measure notes per staff per voice.
- Returns JSON via strict-JSON prompting (no markdown fences) and feeds it into `musicxml_builder` to produce valid MusicXML.
- Supports per-page progress callbacks via `progress_callback` arg — used by the web app to update `Score.metadata_json["omr_progress"]` after each page.
- Token budget per page is large (`MAX_TOKENS_PAGE = 32768`) because dense orchestral pages take a lot of room.

### Verovio rendering
- Python bindings (`import verovio`) — NOT a CLI tool. The `verovio` pip package is bindings only.
- Used in `claude_vision.py` for MusicXML → SVG → PNG rendering.
- SVG → PNG conversion chain: cairosvg (preferred) → rsvg-convert → inkscape (fallback).

### Payments / access gate
- Vision comparison requires payment ($5/score) OR admin email bypass.
- If `STRIPE_SECRET_KEY` is not configured, access falls back to admin-only.
- Admin emails: comma-separated list in `.env` as `ADMIN_EMAILS`.
- `VisionComparisonPaywall` component handles the UI gate on the ReviewUI page.
- **Gradus Library, theory checks, and local OMR are FREE** — no payment gate.

### nginx (frontend container)
- `^~` prefix modifier on `/uploads/` prevents the regex location from intercepting it.
- Without `^~`, the `~* \.(js|css|png...)` regex would match snippet PNGs and serve cached static files instead of proxying to backend.

### Maestro theory layer (shipped 2026-05-24, M0–M4)
- `backend/modules/theory_layer.py` calls `backend/modules/maestro_bridge.py`, which shells out to `tools/maestro_bridge/analyze.ts` via **node + tsx on the host**. Setup: `git submodule update --init && (cd tools/maestro_bridge && npm install)`.
- **Off by default.** `MAESTRO_BRIDGE_ENABLED=true` turns on enrichment (key detection / rhythm + beat-mapping validation / scholarly cross-check against 5 curated seed works). `MAESTRO_PITCH_RERANK_ENABLED=true` turns on M4 in-pipeline pitch re-ranking + auto-correction — local YOLO engine only (Vision OMR emits no pitch candidates).
- **Not available inside the Docker container** — the backend image has no Node, by design (personal-use scope: the bridge is for host-side / Claude-session runs). A web-app OMR run inside Docker silently skips theory enrichment.
- Hooks: `local_omr.py` → `enrich_omr_result()` + `apply_pitch_corrections()`; `claude_vision_omr.py` → `compute_theory_hints()`.
- Plan + per-milestone results: [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md).

---

## Environment variables

All in `backend/.env` (local) or `backend/.env.production` (prod):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLite path (set by docker-compose, don't change) |
| `SECRET_KEY` | JWT signing key — `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_EMAILS` | Comma-separated, bypass Stripe payment gate |
| `ANTHROPIC_API_KEY` | Claude Vision API key (used by claude_vision_omr + claude_vision diff) |
| `STRIPE_SECRET_KEY` | From dashboard.stripe.com |
| `STRIPE_PUBLISHABLE_KEY` | From dashboard.stripe.com |
| `STRIPE_PRICE_ID` | Create a product in Stripe dashboard |
| `STRIPE_WEBHOOK_SECRET` | From dashboard.stripe.com/webhooks |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `FRONTEND_URL` | Base URL of frontend (for Stripe redirect URLs) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry (480 = 8 hours) |
| `UPLOAD_DIR` | File upload path (set by docker-compose) |
| `EXPORT_DIR` | Export output path (set by docker-compose) |
| `OMR_WEIGHTS_PATH` | Pin one YOLO weights file for every input (disables scan/engraved routing) |
| `OMR_WEIGHT_ROUTING` | `1` on (default) → pick weights by input domain, scanned vs digitally engraved; `0` pins the default weights. See the OMR knobs table. |
| `OMR_ENGRAVED_WEIGHTS` | Override the engraved-side weights file used by routing |
| `OMR_CLEF_WEIGHTS` | Optional clef-**specialist** weights (CLI: `--clef-weights`); default off. Not general-purpose weights — see the OMR knobs table. |
| `OMR_MAX_PAGES` | Max pages per OMR job (default 5) |
| `OMR_CONF_THRESHOLD` | YOLO min confidence (default 0.25) |
| `OMR_IMGSZ` | YOLO inference image size (default 512; larger is not better) |
| `OMR_DPI` | PDF rasterization DPI (default 300; CLI uses 600 — see the knobs table) |
| `OMR_LEFT_EDGE_SPLIT` | `1` on (default) → recover stacked systems the connectivity rule merged when staff-body ink faked a connection; `0` disables. See the knobs table. |
| `OMR_DIRECTION_TEXT` | `1` on (default) → read the printed words inside each system and export them as `<words>`; `0` disables. Self-disables with no OCR rung. See the knobs table. |
| `OMR_CELL_LINE_TRACE` | `1` on (default since 2026-09-04) → localize each measure cell's stored staff-line grid onto the ink under it (warped scans). Priced on the widened gate: pooled 0.8387 → 0.8345. `0` disables. See the knobs table. |
| `OMR_ARC_ATTRIBUTION` | `move` (default) → give each slur/tie to the staff of its system whose noteheads it hugs; `drop` removes instead of regifting (measured worse — see the knobs table); `off` disables. |
| `OMR_ARC_RECLASS` | `0` off (default) → export-time tie/slur grammar veto; measured on both families and NOT shipped (scan side refused, +130 edits). See the knobs table. |
| `OMR_CHOIR_GROUPING` | `1` on (default since 2026-09-05) → cues for choir-barred / differently-indented pages (pair-local left-edge merge + grouped-system open-score guard). `0` disables. See the knobs table. |
| `MAESTRO_BRIDGE_ENABLED` | `true` → theory-layer enrichment (host-side only; default off) |
| `MAESTRO_PITCH_RERANK_ENABLED` | `true` → M4 pitch re-rank + auto-correct (local engine; default off) |
| `MAESTRO_PITCH_RERANK_THRESHOLD` | Min re-rank confidence to auto-correct (default 0.9) |
| `MAESTRO_TIMEOUT_S` | Bridge subprocess timeout (default 60) |
| `MAESTRO_NODE_BIN` / `MAESTRO_TSX_BIN` / `MAESTRO_ANALYZE_TS` | Override node / tsx / analyze.ts paths |

---

## Common tasks

### Add a new backend route
All routes are in [`backend/main.py`](backend/main.py). Auth-protected routes use `Depends(get_current_user)`.

### Add a new frontend page
1. Create `frontend/src/pages/NewPage.tsx`
2. Add route in `frontend/src/App.tsx` (protected or public)
3. Add nav link in `frontend/src/components/Navigation.tsx` if needed

### Train a new YOLO model
See [`tools/omr/training/`](tools/omr/training/) (and `HANDOFF_PREMIUM_TRAINING.md` / `VAST_AI_SETUP.md` for cloud GPU runs). The canonical pipeline:

```bash
# 1. Prep DSv2 dataset (one-time)
python3 tools/omr/training/download_dataset.py
python3 tools/omr/training/prepare_yolo_data.py
python3 tools/omr/training/build_catalog_yaml.py

# 2. (Optional) Convert your hand-labeled .verdict.json files to YOLO labels
python3 tools/omr/training/verdicts_to_yolo_labels.py

# 3. Train
python3 tools/omr/training/train_yolo.py
```

### Hand-label cells for OMR training

Hand-labeled cells become YOLO training data: each labeled cell exports as an image + a label file of symbol boxes. **Anything you don't box is treated as background** (the model is penalized for firing there), so completeness matters. Verdicts autosave; the UI serves at **http://127.0.0.1:5050** (port 5050, not 8001).

**Two modes:**

*Triage* — the model pre-labels, you confirm/correct. Fast when the model is mostly right.
```bash
# 1. Pick cells (orchestral selector; page is 1-based, N = cells/page). Over-sample, then
#    filter by density for a tractable batch.
python3 -m tools.omr.annotate.select_cells_orchestral \
    --out-dir benchmarks/omr-labeling-NEW --plan "tag=/abs/score.pdf:12:6,tag=/abs/score.pdf:55:6"

# 2. Pre-label with the model → writes detections/ the UI triages. GOTCHAS:
#    --weights DEFAULTS to generic yolov8m.pt (override!); --time-n-runs defaults to 5 (set 1);
#    --cells is a list of cell_ids (zsh: ${=IDS} word-splits, plain $IDS does NOT).
IDS=$(python3 -c "import json;print(' '.join(e['cell_id'] for e in json.load(open('benchmarks/omr-labeling-NEW/cells.json'))))")
python3 -m tools.omr.annotate.run_yolo --manifest benchmarks/omr-labeling-NEW/cells.json --cells ${=IDS} \
    --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    --out-dir benchmarks/omr-labeling-NEW/yolo-scratch --detections-out benchmarks/omr-labeling-NEW/detections \
    --baseline-verdicts "" --conf 0.25 --imgsz 2048 --time-n-runs 1
# Raw orchestral cells = ~100+ dets/cell (mostly low-conf rest/notehead FPs). Filter to ~18/cell:
# keep conf>=0.50 + per-class NMS, backing the raw set up to detections-pre-filter/.

# 3. Serve
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-NEW   # → http://127.0.0.1:5050
```

*Draw-from-scratch* — blank canvas, you box every element. Best for dense/bleedy scores where the model over-detects. Skip run_yolo; write empty `detections/<cell>.json` = `{"cell_id":"<id>","detections":[]}`. Pair with SPARSE cells (rank a candidate pool by connected-component count on each `_nostaff.png`; keep the lightest ~5–15 elements/cell) or it's brutal.

**What to box vs skip:**
- **BOX** the symbols YOLO detects: noteheads, rests, accidentals, clefs, flags, dynamics (`p`/`f`/hairpins), ornaments, articulations, augmentation dots, ties, slurs, time-sig digits.
- **SKIP** classical-CV structural elements — **staff lines (`staff`), stems (`stem`), beams (`beam`)**: detected by classical CV upstream (`staff_detector`, `line_detection`), 0 in all prior labels, and YOLO can't bbox thin lines. They become background. ⚠️ **"They become background" is not free, and on 2026-09-04 it was measured costing whole classes.** Anything left unboxed on an image you train on is taught to be nothing — there is no "unknown" in the loss — and a fine-tune on this corpus takes `beam` and `ledgerLine` to ZERO within one epoch. Both are **consumed by the pipeline**: `rhythm.resolve_rhythms_for_cell` keeps a YOLO beam wherever no CV beam overlaps its x-range (worth pooled 0.1917 → 0.1861) and `transcribe`'s ledger-ladder arbitration reads `ledgerLine` detections directly (0.1506 → 0.1431), so on every round-3/4/5 candidate both rules were dead, silently. **Do not fix this by hand-labeling them** — a human still cannot bbox a thin line. The escape is the TEACHER drawing them (`build_rehearsal_versions.py`) or restoring their head rows after training (`merge_class_head.py`). `stem` and `staff` are genuinely CV-only and cost nothing; `beam` and `ledgerLine` are not. See `benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md`.
- **SKIP** free text — "sempre", "dolce", tempo marks, instrument names, rehearsal letters: no class exists (`textDynamic` is only for *dynamic* words like cresc./dim.).
- **Barlines** (`barlineSingle`) OK to box (collected toward a future barline class); ledger lines low-value.
- **Ink-bleed / mostly-FP cells are GOOD** — dropped FPs become hard-negative background that suppresses bleed hallucinations. Don't `f` every blob: confirm real notes, leave bleed **pending** (pending and FP convert identically → no label). Too bled to read → skip the cell.
- **Edge-clipped extreme-range notes** — label what's in the *image*, not the musical measure. Notehead cropped out → skip; partly visible → box the visible part. Cells crop at `ORCH_PAD_STAFF_LINES` staff-spaces (`select_cells_orchestral`; raised 2.5 → 5.0 in June 2026 because 2.5 clipped ledger notes); raise further and re-cut only the unlabeled cells if clipping persists.

**UI hotkeys:** `t`/`f`/`u` = TP/FP/unsure (triage) · `c` = fix class (`/` searches) · `b` = redraw bbox · `a` = draw a new box, stays in draw mode after each (`Esc` stops) · `Del`/`Backspace` = remove selected box · `Tab`/`Shift+Tab` = next/prev cell (autosaves). In a pass (below), `1`–`n` pick the symbol you are drawing.

#### Single-symbol pass mode

One symbol kind at a time is much faster than deciding every class on every
cell — and the picker was what made it slow, 174 classes to scroll for a pass
that only ever needs one. A batch may ship a **`batch_config.json`** naming
the classes this sweep is for. **It is optional: with no such file the server
and UI behave exactly as before**, which `test_annotate_server.py` pins.

```json
{
  "pass_name": "hollow noteheads",
  "note": "every half or whole notehead the detector missed",
  "classes": [
    { "label": "half notehead",
      "on_line": "noteheadHalfOnLine",
      "in_space": "noteheadHalfInSpace",
      "click_box": true },
    { "label": "whole notehead",
      "on_line": "noteheadWholeOnLine",
      "in_space": "noteheadWholeInSpace",
      "click_box": true }
  ]
}
```

`classes` (alias `active_classes`) is a list of **palette slots**, and a slot
is one of:

| form | means |
|---|---|
| `"restWhole"` | a plain class |
| `{"name": "restWhole", "label": …, "click_box": …}` | the same, with options |
| `{"on_line": …, "in_space": …}` | a **staff-position pair** — one slot, and the click's y picks which |

Number keys `1`–`n` select the slot; a **single**-slot palette needs no key at
all. **A pass opens every cell already in draw mode** (since 2026-09-03): just
click the symbols — no per-cell `a` step; `Esc` steps out for that cell, and
the verdict hotkeys work regardless. `a` re-enters draw mode as always, and
the class is **assigned for you** — no picker opens. Both halves of a pair draw in different colors with a
`·line` / `·space` tag, so a mis-snap is visible on the image; `b` on a drawn
box redraws it (that only ever worked on model detections), and moving one
across the staff grid **re-derives** its variant. The full 174-class picker is
one **button** away in the pass bar — never a hotkey, because leaving the pass
should be an act and not a slip.

**`click_box` makes a plain CLICK the whole label**, and it is declared per
slot rather than hardcoded: a rests pass omits it and keeps drag-to-draw,
because a rest's height varies with its value and no fixed box is right. Where
it is on, the box is the glyph's own size, **measured, not guessed** — SMuFL
sets the em box to four staff spaces and the committed Bravura templates trim
to exactly `size_px/4` tall at every rendered size, so `noteheadHalf` is
**1.000 staff spaces at aspect 1.167** and `noteheadWhole` 1.000 at 1.722
(`_symbol_metrics` reads it out of `symbol_library/data/manifest.json`).
Override per slot with `{"height_spaces": …, "aspect": …}`.

⚠️ **The placed box is deliberately TIGHTER than a hand-drawn one.** Sean's 29
hollow-notehead boxes from 2026-09-02 measure a median 199×178 px against a
100 px staff space — 1.78 spaces — and AUDIT.md flags exactly that: "the boxes
are generous … YOLO will learn a slightly loose box prior". A click places
121×102. Do not "fix" the difference by widening the default to match the
older labels.

**Which variant is geometry, not appearance** (`snap_to_staff`): notehead
centres sit on a half-space grid, so an even step is a line and an odd step a
space, and the parity keeps working through the ledger positions above and
below the staff. The grid uses each cell's **own measured line positions** —
one real cell reads 400/502/603/698/800, and snapping off a single median from
the top line would put its third line 4 px out. A cell with no staff geometry
abstains and the picker opens instead. The arithmetic lives in Python and the
browser calls `/api/cell/{id}/snap`, so the tested code is the code that runs.

⚠️ **Beyond the staff the grid anchors on MEASURED ledger rungs, not on
extrapolation** (2026-09-03, `tools/omr/annotate/ledger_grid.py`). Ledger
pitch is a fact about the engraving — Litolff prints rungs ~1.10× the staff
spacing, Peters/Breitkopf/Simrock ~0.975×, measured over the 357
hollow-campaign labels — so extrapolating at the staff spacing mis-suggested
**38–39% of 2nd-ledger-and-beyond variants against 4.6% inside the staff**
(Sean's reported defect, and it also planted at least 2 silently-wrong labels
in v8). The endpoint now reads the rungs off the cell image at the clicked x
(3.4 ms; bands of long ink spans, white gaps up to 0.9 spaces bridged because
a whole note's counter splits the one rung printed THROUGH it) and rebuilds
the outside grid on them: 2nd-ledger agreement 57.4% → 70.2% with the
in-staff grid untouched (0 changes across all 214 in-staff labels, pinned by
`test_ledger_snap.py`). A click past an incomplete ladder's reach falls back
to the old extrapolation — a lone rung steering a deep grid measured worse
than the constant. A corrected constant pitch cannot work (both signs of
publisher spread) and wing-recentring measured worse both ways it was tried;
both are recorded refused in
[benchmarks/omr-snap-ledger-2026-09/FINDINGS.md](benchmarks/omr-snap-ledger-2026-09/FINDINGS.md).

**The multi-pass campaign rule.** A campaign sweeps the **same cell set**
several times — whites, then rests, then accidentals — and the set becomes
complete across passes, not within one. So:

- **Verdicts accumulate**; a later pass adds to what an earlier one drew.
  Verified rather than assumed (against the real hollow batch, then pinned by
  `test_added_detections_survive_a_new_serving_session`). Human boxes also
  outlive the model detections they were drawn beside — but a verdict on a
  *model* detection is keyed by detection id and is dropped if that id leaves
  `detections/`, so don't regenerate detections mid-campaign.
- **An inspected-and-empty cell IS recorded** — this is what makes coverage
  provable. Tabbing away from a cell in a pass stamps the pass name into a new
  `inspected_passes: []` field on the verdict and saves, even when nothing was
  drawn. So a cell that legitimately holds none of this pass's symbols writes
  `added_detections: []` **plus** `inspected_passes: ["<pass>"]` — distinct
  from a never-opened cell, which still has no file at all. Coverage for a pass
  is then every verdict file whose `inspected_passes` contains it: the hollow
  batch's 48/48 would be 48 files, not 25. (Stamped on the way OUT, not on
  open, so it means "looked and moved on".) The field is additive and the
  no-config path never writes it; `_reconcile_with_detections` carries it
  across a detection regeneration untouched, the same as drawn boxes.
- **An inspected-empty cell exports as NOTHING, by design.** The YOLO
  converter's `_is_filled` is False for `added_detections: []` with no decided
  detection, so a swept-empty cell is counted `n_empty` and emits no label —
  it is a coverage marker, **not** a background-only training cell, and the
  converter never reads `inspected_passes` (no converter change was needed;
  `test_inspected_empty_is_excluded_from_yolo_export` guards it). That is the
  safe reading mid-campaign: a cell is only background where its own pass drew
  the symbols around it.
- **Export only when the set's passes are complete.** Anything unboxed trains
  as background, so exporting after the whites pass alone teaches the model
  that every rest and accidental in those cells is nothing. This is the same
  fact that forced `verdicts-merged/` in the hollow batch — and now
  `inspected_passes` is how you tell the passes ARE complete without eyeballing
  every cell.

A corrupt config, or one naming no class that exists, **refuses to start** with
a one-line error; an unknown class among usable ones is dropped with a loud
warning. Serving the full picker to someone who asked for a pass would be the
quiet failure.

#### Pre-fill verdicts from the reference (2026-09-02)

When the batch's pages have a reference encoding in the score library, the
reference can decide most of the verdicts before a human opens the batch.
**The detector places the boxes; the reference confirms or relabels them** —
`tools/omr/training/mxl_verdicts.py`. This is the REVERSE of the closed
MXL→bounding-box path (F1 0.064): nothing is placed in pixel space from the
file. The transcription already carries per-measure detections with a pitch
and a duration each; the reference measure is a note sequence too; the two are
aligned (`measure_align.py`, a longest-common-subsequence) and every pair is a
verdict on a box that already has coordinates. ⚠️ **The alignment key is
STAFF POSITION, not pitch** (2026-09-03): the reference note's position comes
from its pitch and the written clef the MusicXML carries, the detection's from
its box against the staff lines, and the pipeline's own clef reading is used by
neither. The first real run (Brahms 1 / Breitkopf, 56 cells) abstained on 30
cells with `0 of N matched` under step matching — the scan's bass and alto
staves read as treble, every pitch on them off by a constant, every box in the
right place. `--match step` / `exact` remain for engraved pages where the clef
is trusted. The truth is read by
`musicxml_truth.py`, stdlib only — it handles `.mxl`, chords, `<backup>`,
pickups numbered 0 — so the pre-fill runs anywhere the JSON opens, no music21.

```bash
python3 -m tools.omr.transcribe score.pdf --pages 174-177 --out out.json
python3 -m tools.omr.training.mxl_verdicts \
    --bench-dir benchmarks/omr-labeling-NEW --transcription out.json \
    --truth library/reference/<composer>/<work>/<file>.mxl \
    --windows windows.json --work-id <work_id> --dry-run      # then --write
python3 -m tools.omr.training.mxl_verdicts ... --score            # against human verdicts
```

| the reference and the reading say | verdict written |
|---|---|
| half note ↔ `noteheadBlackOnLine` | `WRONG_CATEGORY` → `noteheadHalfOnLine` (size kept; on an EXACT pair the on-line/in-space variant follows the reference's own position — 2026-09-03, fixed 2 of 3 flips, zero regressions) |
| quarter ↔ `noteheadBlackInSpace` | `TP` |
| a head the batch has no detection for | an added box `M<n>` (a draw-from-scratch batch gets its labels this way) |
| a detected head the reference lacks | left **pending**, annotated — the human decides |
| a reference note the reading never found | a **hint**: dotted ghost at the pitch's staff position, x estimated; never a label |

**Three joins, each abstaining rather than guessing.** (1) Page ↔ reference
measures: a hand-verified window row — the shape of
`benchmarks/omr-scan-e2e-2026-09/works.json` (`page.pdf_page_index`,
`window.first_ref_measure`, `staves[i].parts`); these rows are the
"movement start" facts, and a file holding several editions must be narrowed
with `--work-id` / `--row-id` or it refuses — and `work_id` there is the
score LIBRARY's id (`brahms--symphony-1`, what the row carries), not the
dossier's (`brahms-sym1-mvt1`); the wrong one is refused as "no usable window
rows", not silently matched to nothing. A file holding one work needs neither.
⚠️ **`--work-id` is not always narrow enough, and since the 2026-09-04 gate
widening Beethoven 5 is the case that proves it.** That work is held in TWO
scans of the SAME Litolff plate, offset by one PDF page (575951 carries an
extra leading page), so 575951's p.2/p.3/p.4 land on `pdf_page_index` 1, 2
and 3 — exactly where 984073's p.1/p.2/p.3 already sit. Three collisions, and
structural rather than unlucky: widening the gate along that edition pair adds
one more each time. So Beethoven 5 refuses on `--work-id` alone and needs
`--row-id`; the other four works are one edition each and narrow fine. The
refusal is the point — a page index means one page of one edition, and picking
silently would read one scan's page against the other's window. Global measure = window start +
this staff's measures in earlier systems + measure index; a staff whose count
across the page disagrees with the window abstains (`--trust-measure-counts`
overrides). (2) Staff ↔ parts: a system whose staff count differs from the
row's abstains whole; a condensed staff (`parts: [0, 1]`) merges its parts
with unisons collapsed and rests dropped. (3) Alignment strength ≥ 0.5 of the
longer side, else the cell abstains — a bar from the wrong measure matches a
few notes by chance.

Verdicts land on the BATCH's own detection ids, matched by overlap after the
transcription's cell frame is mapped onto the batch's through the two staffs'
line positions. Provenance goes in `notes` (`mxl_prefill: C5 half m12`), the
field the server keeps on save. A verdict file that already carries human work
is **never overwritten** without `--force`. Per-cell records go to
`<bench>/prefill/`, which the annotate UI reads: the cell list gains a
**queue order** ("most left for me first" = pending detections + missing-note
hints, abstained cells on top) and the cell page draws the hints (`h`
toggles). Noteheads with a pitch and no duration — a head whose stem the CV
never found, which on a scan is exactly the head worth confirming — are
aligned as single-note events rather than dropped with the voicing.

**The window rows are DRAFTED, not typed** (`tools/omr/training/draft_windows.py`):
given the batch's transcription and a hand-verified base row for an earlier
page of the same edition, it chains the measure window page by page: a page's
bars are the SUM of its systems' counts (each system's count is the mode
across its staves, and a staff that disagrees with its own system is
flagged). A system printing as many staves as the base row is the full
lineup and is paired by POSITION — the margin reader's word is only a
cross-check there, because it turns `Kontrafagott` into `Bassoon` and
`Hörner in Es` into `Trumpet` on the Breitkopf Brahms — while a shorter
system (tacet staves suppressed) is paired by instrument name in order of
appearance. ⚠️ `staff_index` is numbered across the PAGE, not per system
(system 1's staves continue the count), so both the draft and the pre-fill
join a staff to the row by its position within its system, never by index.
Every drafted row carries `"confidence": "draft"` and a `check` list; the
human confirms the first measure of each page against the print and fills
`parts` for any staff of a shorter system whose instrument was not read.

`--write-hints` writes `prefill/` (hints and queue order in the UI) and
leaves `verdicts/` alone, so a batch can be labeled WITH the hints while the
labels stay independent — which is what `--score` then measures.

⚠️ **`--score` compares over the batch's OWN pass classes**, which is why the
Brahms number cannot answer the question it was meant to. That batch is a
hollow-notehead sweep, so its verdicts contain hollow boxes and nothing else:
scoring reports **precision 0.60 / recall 0.333 over 5 pre-filled boxes against
9 human ones**, and the black heads and rests — the bulk of the 179
confirmations — are not in it and never can be. `--score-classes all` (or a
comma list) widens the comparison, and **refuses** unless `--cells` or
`--score-inspected-for PASS` restricts it to cells a human actually swept for
those classes. Without that restriction the number is not a weak result for the
pre-fill but a measurement of which pass was run: a hollow sweep drew no black
noteheads, so every correctly pre-filled black head would be charged as a false
positive. So the deciding number needs a handful of cells labeled COMPLETELY,
then `--score --score-classes all --score-inspected-for <that pass>`.

⚠️ **MEASURED 2026-09-03: precision 0.84 exact / 0.94 kind**, over 50
pre-filled boxes against 94 human ones, on six Brahms cells labeled
COMPLETELY by hand. Read precision, never recall — the pre-fill proposes only
noteheads and a complete human pass boxes slurs, hairpins and rests too. The
eight errors are **concentrated, not diffuse**: 2 grace notes, 3 on-line /
in-space flips and 3 unmatched, with six of the eight in two of the six cells.
Excluding the grace ceiling, 44/50 = 0.88. ⚠️ The sample is BIASED — those
cells were chosen as the ones the pre-fill decided most, i.e. the densest bars,
where alignment slips most; n=50 gives roughly a 0.71–0.93 interval.

**So pre-filled TPs are a queue, not labels — today.** That is a statement
about the current detector, not about the approach: **six of the eight errors
are the DETECTION's box placement**, which the pre-fill inherits and cannot
improve, so pre-fill precision is downstream of recognition and should rise
with it untouched.

⚠️ **A grace note cannot be labelled from either source, and this is a
ceiling rather than a bug.** The transcription holds **0 `Small` detections on
any page** — a grace head is read as an ordinary notehead — and the reference
holds **0 grace notes in 28,579**, because this encoding does not record them.
Two plausible fixes were tried and refuted: `expected_head_class` already
preserves the detector's size, and including grace notes in the alignment
changed nothing and was reverted. ⚠️ Note that `truth_tokens`' docstring
justifies skipping grace notes because "the detector labels them `*Small`" —
**false on a scan**, and it makes the skip actively harmful the moment a
reference DOES carry `<grace/>`, since the grace detection then pairs with the
next real note. The untried route is geometry: a grace head is smaller than
its neighbours (41×38 against 51–83 in the same cell).

Full reading, with the ideas for widening this:
[docs/handoff-2026-09-03-prefill-measured.md](docs/handoff-2026-09-03-prefill-measured.md).

⚠️ **Which signals separate the 8 errors was then measured, and the
aligner's own confidence is the wrong axis**
([benchmarks/omr-prefill-admission-2026-09/FINDINGS.md](benchmarks/omr-prefill-admission-2026-09/FINDINGS.md)):
all six `near` matches are exact-correct (filtering them LOWERS precision,
0.840 → 0.818) and `strength_exact` ranks the cleanest cell (0.333) below
every error cell (0.75–0.917). What separates: per-cell PARITY CONSISTENCY
(do the exact-correct boxes agree on one diatonic-parity → line/space
mapping — the one inconsistent cell holds 4 of the 8 errors), a size veto
for grace heads (< 0.85× the cell's median in both dimensions, 2/2 caught
for 1 deferred), and re-deriving the on-line/in-space VARIANT from the
matched reference note instead of the detector (fixes 2 of 3 flips, breaks
nothing — the alignment key already trusts that position). The composite
reaches 37/37 in-sample at 0.74 coverage; that is a ceiling demonstration on
n=50 biased cells, not a claim — the out-of-sample test is a random
completion pass scored by the same probe.

**Shipped into the pre-fill 2026-09-03 (Phase A):** the variant rule and
size veto above, a tie-chain collapse (below), and an **admission tier on
every decision** — `admission: labels|queue` with `admission_reasons`
(near match, variant corrected, grace-sized, or the cell-level demotion: any
flip demotes its whole cell), priced by `--score` as a per-tier table.
Six-cell A/B: exact **0.84 → 0.88**, kind unchanged, labels tier
**22/22 = 1.000** at 0.44 coverage — stricter than the probe's 0.74 because
pre-fill time has no human calibration. ⚠️ **The tiers are metadata**: what
is written does not change, and nothing is auto-admitted until the random
completion pass prices the tiers out-of-sample.

⚠️ **MEASURED 2026-09-03 (Phase B): pre-fill precision really is DOWNSTREAM
of recognition — 0.880 → 0.961 exact from a change of WEIGHTS alone**, no
pre-fill code touched (`rerun_on_weights.sh`, one arm per checkpoint). The
batch's committed transcription was made with the pre-hollow
`imgsz2048-ft-30ep`; re-reading its pages with scan production
(`hollow-ft-2026-09-03`) also takes kind precision to 1.000, the trustworthy
`labels` tier from 22 boxes to **44 of ~50**, batch CONFLICTs 4 → **0** and
unexplained "extra" hints 200 → **58**. ⚠️ Noteheads fall 4260 → 2419 on the
same pages, and the control that proves this is junk rather than loss is the
MISSING-hint count — reference notes the reading never found — which falls
too (20 → 15). ⚠️ **That control is for NOTEHEADS and does not extend to
the class space** — corrected the same day against the training session's
finding that hollow-family weights suppress **rests and accidentals**
because the completion pass left them unlabeled, i.e. background
([NEXT_ITERATION.md](benchmarks/omr-labeling-survey-2026-09/NEXT_ITERATION.md)).
This arm shows it too: rests fall 1380 → 951. And the missing-hint control
is nearly blind to rests by construction, since `prefill_cell` drops them
from the alignment on condensed staves. Segmentation stays byte-identical
either way. **A batch's hints
age with the weights**: this one's are a checkpoint stale, and refreshing is
`--write-hints`, which never touches `verdicts/` or `detections/`.

⚠️⚠️ **PHASE C ANSWERED IT, 2026-09-03: pre-filled boxes are NOT admissible
as labels, and the in-sample 1.000 did not survive contact with a random
sample.** Sean labeled 49 cells completely and blind — the 25 pre-registered
at seed 20260903 ([PHASE_C_CELLS.json](benchmarks/omr-prefill-admission-2026-09/PHASE_C_CELLS.json),
status and box counts recorded BEFORE labeling) plus 24 more. The committed
analysis, the pre-registered 25: **exact 0.838, `labels` tier 0.849** over
74 boxes. The other 24 scored 1.000, so pooled out-of-sample is **0.915 over
141 boxes** — every honest reading is under the 0.97 bar that was set in
advance. **The queue reading stands, now on evidence rather than caution.**

⚠️ **The Phase A tiers were fitted to the six cells' error MODES and the
random sample fails differently** — every admission policy lands between
0.815 and 0.859, because `near` is 0 on all 12 errors, `parity_ok` is 1 on
10 of them and `small` is 0 on 11. There is nothing for a band to separate.
Six errors are line/space flips where the BOX sits ¼–½ a staff space off the
hand-drawn one (so both detector and reference name a position from a
misplaced box while the human labels the ink); **four are rest VALUE
disagreements** — `restQuarter` against a human's `rest8th` at IoU 0.65–0.82,
the same glyph, the reference's duration against the printed one. Rests are
the weak class and were invisible before: out-of-sample noteheads **0.943**,
rests **0.722**. ⚠️ The reference-variant rule from Phase A is a **no-op**
under `hollow-ft` (0 overrides on 141 boxes) — it earned its keep on the
older weights and costs nothing, but it is not holding the number up.
Contamination and scorer artifacts were both ruled out: the blind server's
log shows all 49 cells saved through it, and no error box has a human box of
its own class overlapping it. Full reading:
[FINDINGS.md](benchmarks/omr-prefill-admission-2026-09/FINDINGS.md) "Phase C".

⚠️ **A pass whose labels will SCORE the pre-fill must be run BLIND**
(`annotate.server --blind`, added 2026-09-03): scoring against a human who
was shown the hints measures agreement with what the human was told. The UI
draws hints **by default** and every `Tab` is a page load, so the `h` toggle
resets on each cell — "just press `h`" is not a protocol. `--blind`
withholds the hints, `prefill_status` AND the queue order, that last one
because "most left for me first" tells the human which cells the pre-fill
found hard. Verdicts are untouched.

⚠️ **A completion pass's PALETTE is a training decision, not a convenience.**
The batch's active config was a stale 9-slot palette with no
`accidentalNatural`, slur, tie or hairpin, while its six complete cells hold
5 naturals, 8 slurs, 6 ties and 5 hairpins — labeling under it would have
made every one of them background, which is the exact mechanism
`NEXT_ITERATION.md` blames for the hollow weights' rest/accidental
suppression. Use `batch_config.completion.json` (14 slots). And ⚠️ **14 is
still not the class space**: those cells also hold `keyFlat`, `clefG`,
`timeSig8`/`9`, `ornamentTrill`, an `accidentalNaturalSmall` and two
grace-sized heads, all boxed through the FULL PICKER. Complete means
complete; only staff lines, stems, beams and free text are skipped.

⚠️ **Every cell of that sample already HAS a verdict file** — from the
hollow sweep — so an unreached cell is not empty, it holds hollow boxes and
nothing else. Score with `--score-inspected-for completion` (and the probe's
`--inspected-for`), or a wider score charges each correctly pre-filled black
head as a false positive and reports which pass was run. Both tools then
score exactly the cells that are finished, at any point mid-labeling.

⚠️ **The five CONFLICTs were then reviewed and NONE is a tremolo
abbreviation** — the handoff's hypothesis is corrected in place. Three are
the reference's TIE-SPLITS (one printed dotted-half encoded as tied
fragments; the human's hollow boxes were already right), two are accidental
glyphs (a flat's loop, a natural) the detector misread as hollow heads over
empty-and-correct human verdicts. So a within-measure tie chain now gets the
same reconcile-by-the-reading collapse tremolo has
(`measure_align.collapse_tie_chains`, 2026-09-03): a chain collapses to one
head of the summed value only where the reading placed at most one head at
its position, may begin tied in from the previous bar and end tied onward,
and abstains where the total fits no single written value (2.5 beats IS
printed as tied heads). Measured on the batch: `s3-m6` resolved (conflict
and both blank-paper hints gone); `s2-m2` STAYS a conflict because the
reading shows two heads at the position — a duplicate detection, the gate's
honest answer until the re-ship cleans it up. The two accidental fakes are
the same family as the probe's phantom TPs: false detections the alignment
can claim.
[benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/CONFLICT_REVIEW.md](benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/CONFLICT_REVIEW.md).

⚠️ **Not yet measured beyond one work.** The Mahler 5 / Peters batch cannot
be the one: the library holds Mahler 5 movements 1-3 and the batch is the
Adagietto (movement 4). The Brahms 1 / Breitkopf batch can — same PDF as the
scan benchmark's `brahms-sym1-mvt1-317803-p1` row, reference on disk. The
runbook is [docs/runbook-prefill-brahms1.md](docs/runbook-prefill-brahms1.md);
the precision `--score` prints there decides whether pre-filled `TP`s can be
admitted without a glance. Until that number exists, treat pre-filled
verdicts as a queue, not as labels. Guarded by `test_mxl_verdicts.py`,
`test_draft_windows.py`, `test_measure_align.py`, `test_musicxml_truth.py`.

#### A checked-out batch has no images until you re-cut them

`benchmarks/*/cells/` is gitignored — the PNGs are large and reproducible — so
a batch arrives on another machine, or in a git worktree, with its `cells.json`,
its `detections/` and its `verdicts/` intact and **not one image**. The server
answers 404 for every `/api/cell/{id}/image` and the canvas draws nothing: a
blank cell page whose sidebar, hotkeys and hints all work, which reads as "the
batch shows no music". The tell is on startup — `WARN: cells dir missing`.

```bash
python3 -m tools.omr.annotate.recut_cells --bench-dir <batch> --dry-run   # then without
```

⚠️ **Do not repair this by re-running the cutter.** A cutter's job is to CHOOSE
cells: `select_cells_orchestral` samples, and `rank_and_trim.py` rewrites
`cells.json` and deletes the PNGs it did not keep. Pointing either at a batch
that has been labeled can renumber the cell set and orphan every verdict in it.
`recut_cells` never writes `cells.json` and never deletes anything.

⚠️ **The FRAME is what makes this safe, and it is checked rather than assumed.**
Every saved box — a drawn notehead as much as a model detection — is stored in
the cell's CANONICAL frame, so an image re-cut at a different padding is not a
slightly different picture: it is the same music at a different scale, with
every box in the batch landing somewhere else on it, and nothing downstream
would say so. The two cutters here disagree on padding on purpose
(`select_cells_orchestral` patches `PAD_*_STAFF_LINES` to 5.0;
`cut_candidate_cells.py` keeps the pipeline's own values) and the manifest does
not record which was used — but it does record `cell_canonical_w`/`_h` and
`staff_line_ys_canonical`, so the mode is DERIVED by cutting under each and
keeping the one the manifest already agrees with. No match, no write: a
mismatch aborts the batch, and `--allow-partial` is needed to write the rest.

Note the modes coincide on a sparse page — `measure_extractor` grows the pad
where the neighbouring staff is more than 6 spaces off — so they are only
distinguishable where staves are crowded, which is what
`test_recut_cells_e2e.py` builds its fixture to be. That suite cuts a
synthesized page, deletes the images and re-cuts them **byte-identically**
under both modes.

#### ⚠️ A fine-tune on this corpus DELETES CLASSES — gate for it

Measured 2026-09-04 over eleven method arms
(`benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md`).
Fine-tuning the 208-class detector on ~600 narrow cells does not merely
"degrade" it: **whole class families go to exactly zero at full notehead
strength** — tie 249→0, slur 184→0, beam 188→0, augmentationDot 150→0,
accidentalFlat 80→0, restWhole 396→0 on the 5-page scan benchmark.

**It is not a confidence shift** — every fine-tune's median confidence is HIGHER
than production's. **It is not the labels** — completing them moved the number
3%, and handing the model 3417 teacher-drawn boxes did not help either. **It is
not a hyper-parameter** — warmup off, `warmup_bias_lr=0`, lr 1e-5, a frozen
backbone and the shipped 896 recipe all collapse identically. The corpus
contains ~30 of 208 classes, so the other ~178 see only negative gradient.

    # seconds, on 30 held-out dense cells — run this BEFORE the slow gates
    python3 benchmarks/omr-labeling-survey-2026-09/probe_class_inventory.py \
        --baseline prod=<production.pt> --ckpts-dir <sweep-dir>
    # gate axis 3 on the scan benchmark, from raw JSONs scan_eval already wrote
    python3 benchmarks/omr-labeling-survey-2026-09/probe_confidence_shift.py \
        --arms prodbase <tag> --gate prodbase

**The repair is head surgery, not retraining.** A YOLOv8 head is per-class in
exactly one place — `model.22.cv3.{0,1,2}.2`, a 1×1 conv with one weight row and
one bias per class — so `merge_class_head.py` puts the base's rows back for
every class the corpus does not teach, and `--bias-shift` bakes a per-class
confidence floor into the rows that stay (the pipeline has only one global
`conf_threshold`). ⚠️ The 208-class space has **40 duplicated names**
(`augmentationDot` at 40 and 159, `clefG` at 5 and 141) because DSv2 carries two
naming families; `--keep` keeps every index of a name.

**Convert finished verdicts → YOLO labels:**
```bash
python3 -m tools.omr.training.verdicts_to_yolo_labels --verdicts-dir benchmarks/omr-labeling-NEW/verdicts \
    --manifest benchmarks/omr-labeling-NEW/cells.json --version-name v<n>-<date>-<tag> \
    --out-root data/user-labeled --labeler sean --description "..."   # --dry-run first
python3 -m tools.omr.training.build_catalog_yaml --root data/user-labeled   # unions the versions in catalog-versions.txt → catalog.yaml
```

**Which versions the catalog unions is a recorded decision, not a directory
listing** — `data/user-labeled/catalog-versions.txt` is the membership record,
and `build_catalog_yaml` refuses to run without it (or an explicit
`--versions`), so a rebuild reproduces the committed membership exactly and
can never silently widen it. A freshly converted version is **not**
auto-included: admitting one means editing the manifest (a committed,
reviewable diff — `test_training_pipeline.py` pins the membership, so do it
deliberately). Currently v1–v4 are in; v5/v6 (clef-heavy, narrows the density
prior) are excluded per PROJECT_STATUS.md open decision #13, and v7 (hollow
noteheads) is an open training-time decision.

The catalog is **capped at nc=208 by default** (custom-class boxes — barlines, textDynamic — are filtered into `_nc208/` copies) so fine-tuning matches the DSv2 checkpoints' class count; a mismatched `nc` silently re-initializes the classification head (the Phase 3.4 collapse). `train_yolo.py` refuses an nc mismatch unless you pass `--allow-nc-expansion`; `--emit-full-catalog` also writes an uncapped `catalog-214.yaml` for a deliberate future expansion.

⚠️ **NEVER "just re-run the converter" on an EXISTING version.** It copies each cell's PNG out of the batch's gitignored `cells/` directory, and those are not regenerable (phase-1 has drifted) and are largely gone: measured 2026-09-03, **11 of v8's 122 source PNGs still exist**, so a re-run silently writes an 11-cell version over the 122-cell one and exits 0. To correct a mislabeled class after export, hand-edit the class id in `labels/<cell>.txt` (coordinates do not move), the batch verdict, AND the version's own merged export source — then heal the version's `metadata.json`, which still records the old class, with `python3 -m tools.omr.training.heal_version_metadata --version data/user-labeled/<version> --expect-cells <cell_id> --write` (re-derives the class fields from the labels; never touches labels or images).

**AUDIT a finished pass before it reaches training.** Two failure modes, neither visible to
the other's check, both found on the Brahms completion pass and now tooled
(`benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py`, plus
`benchmarks/omr-cell-grid-tilt-2026-09/audit_labels_vs_measured_grid.py` for inside-staff
parity). ⚠️ **LEDGER-ZONE PARITY: measure the INK, never the BOX** — a click-placed box
inherits the slot the snap chose, so its centre is biased toward the grid that placed it, and
ink-inside-the-box "confirms" whichever box you measure. Use the blob on `*_nostaff.png`.
Rate: **6 of 76 ledger-zone labels (~8%) on Brahms, 19 of 275 (6.9%) campaign-wide, against 0
inside-staff parity errors.** ⚠️ **SHAPE-vs-CLASS: a parity audit cannot see a wrong KIND** —
a rest labeled a notehead has no parity to be wrong about; the box geometry separates them
cleanly (that whole rest: 2.13 × 0.72 spaces, aspect 2.97:1, against a median notehead's
1.19 × 1.00 at 1.19:1), and it sat INSIDE the staff where no parity check reaches. Both
auditors write nothing — every hit is a candidate for a human.

⚠️ **THE RAW FLAG RATE IS AN UPPER BOUND, NOT THE DEFECT RATE — measured
2026-09-03 on a genuine out-of-sample batch (Simrock/Dvořák 9, labeled after
the tool existed): 7 of 102 ledger-zone labels flagged (6.9%, matching the
Brahms rate), but adjudicated by hand ONLY 1 was real — true rate ~0.9%.**
The 6 false positives share one mechanism: a printed LEDGER LINE survives
staff-line removal and print-merges into the SAME connected component as
its neighbouring notehead, pulling `blob_centre`'s centroid toward the rung
by up to a full half-step. **Five candidate fixes were tried against both
the Brahms corrections and the Simrock false positives and NONE
generalises** — including the literal fix proposed for it, which resolves
Simrock 4/4 and breaks Brahms 0/6, because it only has room to work where
the human's box carries generous padding around the head, a labeling
convention that differs across batches and is recorded nowhere. Do not
re-try a box-relative geometric fix without reading
[LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md](benchmarks/omr-snap-ledger-2026-09/LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md)
"The rung-merge failure mode" first — it has the numbers. `blob_centre` now
reports the winning component's height/width in staff spaces alongside
every parity suspect, as context only: width alone does NOT separate a
rung-merge (Simrock's four measure 1.91–2.14sp) from a normal label (40 of
Brahms's 76 ledger-zone labels, all uncontested, measure the same). **Every
candidate still needs a human looking at the actual ink against the known
step positions** — the standard both the Brahms corrections and the
Simrock false positives were settled by, and the only thing that has
worked twice.

**A third check, and the first needing no image at all: edge fragments.**
`transcribe._drop_clipped_notehead_fragments` already screens the
DETECTOR's output for a notehead-shaped sliver flush against a cell's crop
boundary — the neighbouring staff's ink bleeding into this cell's padding —
but had never been applied to HAND-DRAWN labels, which face the identical
ambiguous ink. Found live in the training corpus (v3-2026-06-09-mahler5,
v4-2026-06-10-la-mer, both in `catalog-versions.txt`, both in the round-4
run): two `notehead*` labels at 0.52–0.54sp tall — inside the measured
fragment band (0.29–0.56sp), under the genuine floor (0.60+). ⚠️ **Height
alone reads "rest"; WHERE in the cell settles it.** Both boxes sit flush
against the cell's own top edge, capturing only the tip of a much larger
shape that belongs to the staff above — not a symbol in this measure, so
the likely correction is delete, not relabel. `audit_ledger_zone_labels.py`
now checks this third: a sub-0.6sp notehead label whose bbox is within
`CELL_EDGE_TOLERANCE_SPACES` (0.5sp — hand-drawn boxes leave 0.07–0.28sp
of margin, unlike a model's box which is 1px-flush) of the cell's own top
or bottom. Manifest-only, so it reaches every batch, including the four
`hollow2-2026-09` batches with no re-cut `cells/`. Validated the same way:
finds exactly the 2 known cases and **adds zero false positives across the
full 1666-label campaign**. Credit: scanned-weights session, both for the
two live cells and for the missing WHERE-in-the-cell field.

**Then COMMIT the results** (labeling runs in the main checkout, and verdicts are irreplaceable human work — don't leave them sitting untracked):

```bash
git add data/user-labeled/ benchmarks/omr-labeling-NEW/cells.json \
    benchmarks/omr-labeling-NEW/verdicts/ benchmarks/omr-labeling-NEW/detections/
git commit -m "Labeling batch <date>: <n> cells → v<n>"
# (cells/ PNGs are gitignored by design; *_pre_cleanup/ dirs are scratch — don't add them)
```

### Change the Claude Vision diff prompt
Edit [`backend/modules/claude_vision.py`](backend/modules/claude_vision.py). The diff prompt is in `compare_measure_pair`. Returns JSON: `{ has_difference, difference_type, description, confidence, is_omr_error }`.

### Change the Claude Vision OMR prompts
Edit [`backend/modules/claude_vision_omr.py`](backend/modules/claude_vision_omr.py). Two prompts: `HEADER_PROMPT` (title/parts) and `PAGE_PROMPT` (notes). Strict-JSON output — don't break the format.

### Regenerate the status board

`docs/progress-dashboard.html` is a generated status board — headline figures
and the per-work table come from `current-accuracy.json` and git, the narrative
from `docs/progress-dashboard.content.json`. **Do not hand-edit the HTML.**

```bash
python3 -m tools.dashboard.generate            # rewrite the page
python3 -m tools.dashboard.generate --check    # non-zero if it is stale
python3 -m tools.dashboard.generate --serve    # preview on localhost:8600
```

### Reset the database
```bash
docker compose down
docker volume rm reengrave_db
docker compose up -d
```

### Run with production compose locally (for testing)
```bash
export DOMAIN=localhost ACME_EMAIL=test@test.com
docker compose -f docker-compose.prod.yml up -d
```

### Benchmarks
Per-phase reports + verdict sets live in [`benchmarks/`](benchmarks/). The most important file: [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md) — full story of how the Phase 4 (rhythm + voicing + line detection) work came together.

---

## Known limitations / TODOs

- **MusicXML correction patching is a stub.** `export_module.apply_corrections_to_musicxml()` copies the original file and injects accepted diffs as XML comments rather than actually patching the XML. Real measure-level patching (replacing `<measure>` elements with `human_edit_value` content) is not yet implemented.

- **Custom OMR classes (barlines, textDynamic) are not YOLO-learned.** Phase 3.4 tried to expand from 208 → 214 classes and caused catastrophic forgetting (F1 cratered to 79.3%). Barlines are currently detected by classical CV; textDynamic isn't detected at all. Re-introduce when there are ~200+ examples per new class, or seed via synthetic warm-up.

- **Per-measure rhythm sums are approximate.** Bar-check warnings on LilyPond output reflect the rhythm-parsing approximation from Phase 4c/g (fractional offsets like 1/32, not full-beat errors). Note: MusicXML voice-splitting via `<backup>` *was* implemented 2026-05-23 (`tools/omr/export.py`, `_mxl_voice_events`) — older notes claiming otherwise are stale.

- **MusicXML repeat signs are dropped on export** — no `<repeat>` barline emission yet (see NOTES.md item 6; tied to multi-type barline classification, item 5).

- **A cell's stored staff lines were the staff's IDEAL lines — FIXED, default-ON since 2026-09-04** (`OMR_CELL_LINE_TRACE`, see the knobs table). Diagnosed 2026-09-03 (`benchmarks/omr-cell-grid-tilt-2026-09/FINDINGS.md`): staves tilt/bow 8–17 px, end-of-staff cells carried residuals past the parity-flip line, and `pitch_resolver` read whole bars against the wrong grid. Unpriceable on the 5-row gate (0.4% exposure); the 2026-09-04 widening raised exposure to 8.6% and the fix measured pooled 0.8387 → 0.8345 with −217 of −233 edits on exactly the tilted rows (`WIDENED_PRICING_2026-09-04.md`). The rigid-comb slide ships; per-line tracing stays refused (it aliases past half a spacing). The annotate snap keeps its own grid handling (`test_ledger_snap.py`); re-cuts compare the unlocalized frame grid (`recut_cells.frame_mismatch`).

- **The meter is read from the header by shape, and voted across the system** (2026-08-31). The detector does not read time signatures on real scans — on page 1 of the IMSLP Beethoven 5 it finds *zero* time-signature digits in any header, on a page printing `2` over `4` legibly on all twelve staves. Worse than silence, it used to fill the gap: five `timeSig4` boxes fired on **barline** fragments mid-bar, each became 4/4 via the single-digit guess in `parse_time_signature`, and the page shipped as common time on every staff. `tools/omr/time_signature_locator.py` reads it instead, the way the clef and key signature are read — by geometry. A meter's placement is rigid (numerator in the upper two staff spaces, denominator in the lower two, centred on each other), so the search is one-dimensional: a composite template per candidate meter, built from the Bravura `timeSig0-9` glyphs already in `tools/omr/symbol_library/`, slid along the header window in x. Readings are then **voted across the staves of a system**, because that is where a meter is printed. Measured (`benchmarks/omr-timesig-2026-08/`) over a corpus that is half pages printing no meter at all: **4 correct, 0 wrong, 12 correct abstentions** — across a 600 dpi scan of 19th-century type and LilyPond pages set in a different font from the templates. Beethoven 5 p.1 now emits 2/4 instead of 4/4, and its LilyPond bar-check failures fall 154 → 104. Two discriminators were measured and REJECTED for moving with the printing rather than the answer: ink coverage (separates on the scan, then inverts — engraved TRUE reads score below scanned FALSE ones) and whitespace gutters (no separation at all). `timeSigCommon`/`timeSigCutCommon` have no templates, so common-time pages abstain here and stay with the detector, which reads those two glyphs well.

- **A part is the same staff on every system, not one staff on one system** (2026-08-31). `export.to_musicxml` emitted one `<part>` per (page, system, staff), so a part was never continuous: two pages of a piano prelude came out as **24 parts of 3 bars** instead of 2 parts of 36. That is why OMR-NED could not be read as a recognition score on anything longer than one system, and why `orchestral_eval` capped its excerpts at one page. `export._stitch_slots` now joins staves by ORDINAL across every system and page, and **refuses when the systems disagree about how many staves they have** — printed orchestral scores suppress tacet staves (Beethoven 5 scan p.3 is 11 then 8), and joining those by position would graft one instrument's music onto another; the old per-system parts stand there. Measured on WTC I Fugue 1, two pages, against the Gradus reference: **20 parts → 2**, 3 measures per part → **27** (the reference has 27), OMR-NED **0.9819 → 0.8668**, and the dominant error changes from `entire measure insert/delete` to **`wrong note`** — the metric has stopped measuring the exporter and started measuring the reading. Single-system pages are unaffected. `benchmarks/omr-first-run-2026-08/EXPORT_PARTS.md`.

- **Durations fail on scans because hollow noteheads are invisible, not because the rhythm layer is wrong** (2026-08-31, NOT FIXED — `benchmarks/omr-first-run-2026-08/DURATIONS.md`). Beethoven 5 p.1 prints 68 half notes and the output contains 8; twenty of twenty-six duration errors are a half read as something shorter. The heads are not misclassified, they are **not detected** — at 600 dpi bitonal on this print the half notehead's counter has closed to a thin diagonal sliver inside an otherwise solid head, and a detector trained on clean engraving does not call that hollow. The control settles it: the same music engraved by LilyPond gives 31 hollow detections against 30 real half notes, and pitch recall 0.926 with pitch+duration recall **also 0.926** — every correctly-located note there has the right duration. Four fixes were measured and none shipped: reclassifying by ink fill (nothing to reclassify), counters as enclosed holes (662 candidates for 68 notes), Bravura `noteheadHalf` template matching (15 of 68 at threshold 0.50, none above), and thinning the ink before re-detecting (4 → 9 of 26, while inflating `noteheadWhole` 1 → 5). The lever is a labeling batch through `tools/omr/annotate/`, and ⚠️ **not** ink-degradation augmentation, which is the obvious idea and is already disproven — see the domain-augmentation entry in NOTES.

- **Key-signature accidentals are found by template, not by clustering ink** (2026-08-31). `key_signature_locator` thresholds the header to an ink mask and keeps the accidental-sized connected components — on a scan whose staff-line removal leaves every glyph in pieces, nothing accidental-sized survives: given the CORRECT clef for every staff of Beethoven 5 p.1 it reads **2 of 12**, on a page where eight of the ten it misses print three flats legibly. `tools/omr/key_signature_template.py` slides the Bravura `accidentalFlat`/`accidentalSharp` templates instead and reads **11 of 12** standalone. Two bounds make it work: the search runs only between the **clef** (matched by its own template — the caller knows which clef) and the **meter** (`locate_time_signature`), because a flat's outline correlates with a G clef at 0.57-0.59 against real flats' 0.65-0.76, too close to separate by score. Positions come from the **ink centroid inside the matched box**, not the box centre — box centres leave ±0.5 step of jitter, enough for the fit to read three flats as five. End to end on p.1: key signatures **4/12 → 7/12 correct with 0 wrong**, exact-pitch recall **0.571 → 0.619** against unchanged step recall, so the accidental gap halves; over six pages, staves spoken for 29% → 39%. Curated ground truth unchanged except the Pastoral, **9 → 11 correct, 0 wrong**.

- **Two rules the template reader needed, both found by breaking WTC p.17.** (1) **It may not infer.** `fit_key_signature` recovers slots nothing was detected at, which is right for a reader that only ever loses accidentals; this one can gain a spurious match, and inference compounded five matches into *seven sharps* on a four-sharp page. (2) **It may not carry across systems.** `key_signature_vote` resolves a part by taking the reading with the most accidentals — sound only while every reader under-counts. One staff's spurious fifth sharp was carried onto **every treble staff of all five systems**, taking the page from 10 correct to 5 correct and 5 wrong. `StaffCandidate.can_carry` keeps such a reading on its own staff. ⚠️ **The reader speaks only into GAPS** (where detector and locator both found nothing). Letting the fuller reading win instead is worth +1 on beet5-p2 and +2 on the Pastoral and costs a WRONG reading on the cleanest page in the corpus — priced and refused. Staves with no clef read get the reader against the positional default at `DEFAULTED_CLEF_WEIGHT`, too weak to justify a departure, so the vote can keep it only where it agrees with the system: the clef gate moves from the staff to the page.

- **Common time is read; cut common was measured and withheld** (2026-08-31). `timeSigCommon` and `timeSigCutCommon` were added to `symbol_library/builder.py` and the library rebuilt (every pre-existing template came back byte-identical — the check that mattered, since the clef and key-signature readers share it). A letter meter is one glyph two spaces tall centred on the middle line, padded into the same four-space box so the search stays one-dimensional, and `C` is the strongest reading in the corpus: five common-time pages at 0.745-0.761 against 0.50-0.62 for scanned digit meters. **Cut common is still not searched for, and is now READ** (2026-09-01). Withholding the template does not produce an abstention — it produces `C`. Fifteen of the 97 dossier works open on a ¢, and on those pages the reader was confidently wrong: Mozart 40 i at 11 staves of 11 and Brahms 4 i at 13 of 13, so a 2/2 page shipped as 4/4 with every bar measured against a meter twice too long. Putting the template in fails BOTH ways — nine false systems, *and* it still loses to plain `C` on the real ¢ pages, because a C is a SUBSET of a cut-C's ink and the template with less to account for scores higher. So the stroke is read by POSITION after `C` has won (`_looks_cut`): the middle of a C is hollow, its aperture faces right. Over 87 staves that matched C, the 24 cut ones fill **1.00** of the centre column and no other exceeds **0.48** — every threshold in 0.50-1.00 gives the same answer. **No new false-positive surface exists by construction**, since the cut reading rides on a `C` that already cleared the threshold and the vote. Also **the vote's agreement floor went 0.5 → 0.70**: every one of the 12 correct readings is agreed by 0.909 of its system or more and the one wrong reading (Beethoven 3 i, a Litolff `3` matching Bravura's `6`) by exactly 0.500. Corpus total over 11 sources: **12 correct, 0 wrong, 3 missed, 40 correct abstentions**, up from 3 wrong; `orchestral_eval --omr-ned` identical to the edit, A/B'd. A wrong meter is not cosmetic — measured on Beethoven 3 i, it costs **390 LilyPond bar-check failures against 164 for no meter at all**. See [benchmarks/omr-timesig-2026-09/FINDINGS.md](benchmarks/omr-timesig-2026-09/FINDINGS.md), including why adding 4/8 (the one repertoire meter with no template) fixes nothing and why the bar-check count rewards the longer meter.

- **A barline is a straight line, not a vertical one** (2026-08-31). The IMSLP Beethoven 5 scan is warped — one barline's x drifts monotonically by up to 40 px between the top staff and the bottom, over three times the clustering tolerance — and `_intersystem_connectivity` dropped a *vertical* column at the cluster's mean x, so three real barlines that had passed the vote (9, 12 and 10 of 12 staves) scored 0.27-0.36 against a 0.40 gate and were thrown away. `measure_extractor._barline_x_at` now fits the line to the staves that observed it and probes along it, using **Theil-Sen and not least squares**, because a note stem that joins the cluster votes too and two such among nine still dragged a least-squares fit off the line. Page 1: 17/17 barlines, 0 false, **16 measures of 16**; pages 2-6 unchanged. Also `_spans_system` — the weakest band of a column along the fitted line — rescues barlines on **braced two-staff systems**, where "both staves must agree" fails whenever one hand plays continuously: on WTC I Prelude 1 p.4 the left hand read all four barlines of every system and the right hand, thick with sixteenths, read none of them and 31 of its own stems, so five systems of three bars each came out as ONE bar (now 4,4,4,4,4,4). The gap test is *not* enough there — a fugue's long stem crosses the brace gap and scores 1.00 connectivity — but nothing except a barline runs from the top of the upper staff to the bottom of the lower. The rescue is **additive**: letting the span test filter instead costs every system its opening rule, which often does not span the brace.

- **A meter carries onto pages that print none** (2026-08-31). A time signature is printed at the start of a movement and nowhere else, and everything upstream worked a page at a time — so page 2 of a 2/4 movement had no meter at all and the exporter fell back to 4/4 on it. `transcribe` now carries the last page's meter onto a page that reads none, tagged `source="carried_from_previous_page"` so it can never be mistaken for something that page said. Beethoven 5 scan pages 1-6: the meter went from **page 1 only** to all six. This is also what makes `select_short_bar_cells` work past a movement's first page — without a meter there is no shortfall to rank by.

- **A meter is believed per STAFF, not per measure** (2026-08-31). Once read, a meter is carried onto every later measure of its staff, so counting measures counts one reading many times: on Beethoven 5 scan p.3 a single `timeSig4` at confidence 0.42, on one staff of nineteen, arrived at the page vote as eighteen unanimous votes for common time. `rhythm._dominant_detected_meter` now takes one vote per staff and requires half the page's staves, and `rhythm.drop_uncorroborated_meter_changes` reverts a mid-staff meter CHANGE that only one staff saw — a change is a system-wide event, printed on every staff at the same bar. The guard is worth having alone: without any reader it takes p.1 from a confident 4/4 to an honest silence.

- **Key signatures are read by position; recall is about a half, given the clef.** The header of every staff is now measured (`tools/omr/staff_header.py`) rather than assumed to sit inside the staff-start measure cell — on faded prints it often doesn't, because `Staff.x_start` is the longest ink run on the middle line and that run can begin past the clef. (It can now also begin too far LEFT, in the instrument name, since Phase 1 started bridging broken lines; `_anchor_column` clamps the leftward walk to the staff's own bracket, which took the share of staves whose window actually contains a clef from 186/455 to 233/455 over 26 pages.) Key signatures are then read by fitting accidental *positions* to the slot table for (clef, N) (`key_signature_geometry.py`), so a missed interior accidental is recovered rather than miscounted, and reconciled across staves and systems (`key_signature_vote.py`). Measured on two ground-truth orchestral pages (42 staves), **given the correct clef**: 18 correct, 0 wrong, 16 missed, 8 correct abstentions (34 of the 42 carry a signature). End to end, where the clef must be read, that is 2 staves of 20 on Beethoven 6 p.2 and 0 of 22 on Beethoven 5 p.2. It only seeds staves where the detector found no key-signature accidental at all, so it cannot make a correctly-detected score worse. **It inherits the clef problem**: the slot table is chosen by the clef, and a wrong clef produces wrong signatures rather than abstentions (measured: bass staves defaulted to treble read 3 flats as 2 sharps), so a staff whose clef is only the positional default is skipped. On scans where every staff reads as treble, the key-signature reader stays quiet — the two features improve together. The slot fit also applies to the **detector's own** keySharp/keyFlat markers, and both readings go through the vote. WTC p.17 (E major, clean engraving): counting the markers reads 6/10 staves correctly, fitting their positions 7/10, reconciling across the page **10/10** — each step fixing a different failure (a stray marker; then three staves whose first sharp went undetected, which only the page can recover). Note the readers take different inputs on purpose: the detector reads the staff-start measure cell, the CV locator reads the header window — on the header crop the model finds *zero* key markers at any imgsz, because a letterboxed sliver is outside what it was trained on. The locator anchors its run on the clef specifically — an oversized cluster at the *head* of the window with a clef's height, not merely the largest ink in it — and abstains when there is none; anchoring on a beam or a note group is what let it read ink in the middle of a bar as a signature. All of this is **on by default** — `--no-header-reading` turns it off.

- **Clef reading is geometric, but clef *detection* is still a model weakness.** Which line a clef names is now measured, not classified (`tools/omr/clef_geometry.py`) — alto/tenor/soprano/mezzo/baritone are the same glyph on different lines, so a class label can never separate them, and all ten clefs now flow through pitch resolution and both exporters. A classical-CV C-clef locator (`tools/omr/clef_locator.py`) covers scores where no model sees a clef at all (19th-century C-clef prints: zero detections even at conf 0.03). It runs only where nothing else read a clef, recognises C clefs only, and abstains otherwise. G/F clef *detection* on degraded scans is unimproved. See `benchmarks/omr-clef-geometry/RESULTS.md`.

- **A five-line window that locked onto the wrong ink is slid back** (step 3d,
`staff_detector._refit_misaligned_group`), by TWO signals because the fault has
two shapes. A window that locked onto a BEAM has an end line far thicker than
the rest (Brahms's contrabass, 18px against 5px). A window that locked onto
LEDGER LINES has end lines printed at staff weight that do not RUN — Brahms's
Violin 1 covered 4% and 6% of the staff's width at a thickness ratio of 1.8,
invisible to the first test, and sat TWO spaces high, so 35 of its 39 notes came
out four staff positions low at a cost of 263 OMR-NED edits. Measured over 270
staves and 5 editions (`benchmarks/omr-phase1-baseline/probe_line_coverage.py`),
the worse end line's coverage over the staff's median is **0.041–0.112 for the
six misfitted windows and 0.682 or more for every correctly placed staff** — a
6× gap with nothing in it, which is why the constant is not a tuned one. It is
RELATIVE to the staff's own median because a faint scan's real lines only cover
0.5–0.7. Slides by 1 or 2, never 3 (a window three spaces off shares no line
with the true staff). ⚠️ **Fixing this uncovered the next problem rather than
finishing one:** with Violin 1 placed correctly its highest notes fall in the
gap above its own cell and inside the Timpani's, and are awarded to the timpani
by `_dedupe_cross_staff_detections`, which resolves a contested glyph by
distance to the nearer band. See the attribution report.

**Which staff a contested glyph belongs to is decided by CONTEXT, not by
distance** (`transcribe._dedupe_cross_staff_detections`). A measure cell is cut
with padding above and below so ledger notes are not sliced off, and on a
conductor's page those bands overlap, so the same ink is detected once per
staff. The old rule kept the copy on the NEARER five-line band — which is wrong
for exactly the case the padding exists for, because an engraver opens the gap
above a staff *for* its ledger notes and they then sit nearer the staff above.
Measured on Brahms: Violin 1's `A6`/`B♭6` exported as `A♭1`/`B♭1` on a timpani
while Violin 1's bars 3 and 4 came out empty. Three kinds of evidence now
apply, in the order a reader uses them:

1. **The ledger ladder** — about the glyph. A ledger note is joined to its staff
   by an unbroken run of ledger lines; the violin's cells carry three rungs per
   note-column at its own ledger positions and there is not one rung between
   those notes and the timpani. COMPLETENESS ONLY (2026-09-01, was
   "completeness before count") — an unbroken ladder outranks anything broken,
   and two broken ladders are NOT evidence either way, because a found rung can
   belong to the other staff's note exactly as a gap can: on the Beethoven
   bassoon pair the ghost's one rung WAS the real C4's own ledger, and counting
   it beat the real note. Two other traps live here: expected rungs are
   `int(d/spacing + 0.25)` because a note ON the first ledger measures ~1.0
   spacings and truncation read 0.994 as needing none (the same note needed its
   ledger in one bar and not the next, one pixel apart); and a low-confidence
   outside-staff notehead with NO rung at all is not a note
   (`_drop_unladdered_noteheads` — the 'g' of "Allegro" as a whole note; fakes
   0.45-0.53 against 0.76+ for every real one, neither signal sufficient
   alone). Pooled 0.1506 → **0.1431**, Beethoven notes **81/81 at
   recall/precision 1.000**. `benchmarks/omr-ned-2026-08/LADDER_EVIDENCE_2026-09-01.md`.
⚠️ **MEASURED 2026-09-05: this veto has NEVER FIRED ON A SCAN.** `_staff_written_ranges(page, dossier)` returns `{}` outright when `dossier is None`, and the scan benchmark runs dossier-free BY PROTOCOL (dossiers are generated from the same MusicXML it scores against). So across the 20-row scan gate all **4,256** cross-staff duplicates are resolved by the ledger ladder or by distance, and the range veto contributes nothing there. It is live only where a dossier is supplied. A family-level substitute was measured and is vacuous — a family's range is the UNION of its members', so percussion spans 0-127, and only 5 detected pitches of 9,219 fall outside their family union (`benchmarks/omr-structural-parts-2026-09/`).

2. **The instrument's written range** — about the part. Two Beethoven bassoon
   staves contested one notehead and distance kept `A♭1`, MIDI 32, below the
   bassoon's `instruments.written_range` of (34, 72), discarding a C4 inside it.
   The staff's instrument comes from the DOSSIER (the contextual pass names
   parts only after this runs), on its usual terms — staff count must equal part
   count, else it abstains. A veto on the IMPOSSIBLE, never on the unlikely.
3. **Distance**, unchanged, as the tie-break — and with neither ledger lines nor
   a dossier it is still the whole rule, so those pages are byte-identical.

⚠️ **The cell pad is 4 spaces or 6, never in between** (`measure_extractor`).
The arbitration is useless if the note is not in its own staff's cell at all, so
the pad GROWS where the neighbouring staff is more than 6 spaces away. It must
not grow otherwise: cell height is coupled to `OMR_IMGSZ`, so it moves
DETECTIONS and not just crops. Measured — a flat 6 costs Mahler and Beethoven
(+20, +59) whose staves sit 1.7 and 3.4 apart; bounding it by the gap instead
starves Mahler's cells of their own stems (duration rate 0.864 → 0.455); and a
marginal 4.0 → 4.6 growth costs the authored `ensemble` fixture three notes of
45. Two rewrites were measured and rejected: one-winner-per-cluster scores worse
(IoU overlap is not transitive, so it chains distinct glyphs together), and
applying strong verdicts before weak ones changes nothing measurable.

**Body text is no longer detected as staves** (fixed 2026-08-28). Row ink-count alone passed the line-length test on justified paragraphs; `staff_detector` now also requires the lines to be *continuous strokes* rather than rows of glyphs (`_line_ink_runs_per_space`). Music tops out at 1.39 runs per staff-space, text starts at 2.02. All music-only scores byte-identical.

- ⚠️ **ON SCANS, MORE LABEL READING CANNOT LIFT THE CLEF NUMBER — the names are
  not printed** (measured 2026-09-05, `benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`).
  `clef_correction` proposes a clef from the instrument's written range and is
  documented as starved of instrument names; over the 20-row scan corpus (217
  truth-carrying staves, 5 publishers) the unresolved staves whose family
  defaults to something OTHER than treble — the entire population it could ever
  be handed — number 29, and **29 of 29 are in the class "no label printed at
  all"**. None is a lexicon refusal, a group-label fragment or an OCR miss:
  Litolff Beethoven's `Viola` and `Violoncello e Basso` on continuation systems,
  Simrock Dvořák's whole p6/p7 lineup, margins measuring zero ink. The families
  labelled on continuation systems are winds and brass, which default to treble
  and are already right; the families dropped are strings and low brass, which
  are the ones that need help. So the constraint is real and is **not** liftable
  by better reading on these editions. ⚠️ Three limits: an edition labelling its
  strings on every system would move it; this says nothing about whether
  `clef_correction` would get those staves RIGHT if handed them; and whether the
  60 already-resolved non-treble labels actually REACH `clef_correction` is a
  separate, unmeasured question about the consumer.

- **End-to-end clef accuracy is 92%, and the detector does most of the work.** Measured 2026-08-29 on 52 hand-read staves (`benchmarks/omr-clef-geometry/eval_pipeline_clefs.py`, `PIPELINE_CLEF_RESULTS.md`): the detector supplies 39 of them at 95% accuracy, the positional default 11 at 82%, the CV locator 2 at 100%. This is the number that matters downstream — a staff carries its clef into every pitch on it and into which slot table its key signature is fitted — and it is much better than the coverage figures below, which are about the CV LOCATOR alone and predate the `imgsz` fix. Every remaining error is a non-treble clef read as treble. A staff that read no clef now takes the clef its own part read in another system when every reading agrees (`contextual._fill_defaulted_clefs`), worth 48/52 → 49/52. With `--dossier`, the work's own parts are joined to the page's slots on the margin LABELS (never on the clefs, which would be circular) and supply the clef where that join is anchored by a label above and below — **50/52 (96%)**. Score-order identity driving clef correction was measured and rejected there: it fixes one staff and breaks another.

- **The CV clef locator reads 8 of 24 real C clefs on hand-read orchestral pages, and declines all 163 staves that carry none** (`orchestral-clef-truth.json`, 10 pages / 187 staves / 4 publishers). An earlier 8-of-10 was a four-page sample and flattered it. Do NOT quote `located / all header cells` (58/720 = 8.1% orchestral) as coverage — most orchestral staves are treble or bass and correctly get nothing, so that ratio is not recall. `probe_cluster_too_big.py` is what separates a rejection from a loss: it cross-tabulates each staff's rejecting branch against its hand-read clef. **The fused cluster (`cluster too big`, 52.9% of orchestral header cells) costs 1 C clef against 90 correct refusals — it is a G clef being seven staff spaces tall, not a bug. Do not go after it.** The leading cost is the single-dot veto: turning `dot_single_clear_is_enough` off recovers 5 real C clefs for 1 false positive (recall 8/24 → 13/24) on that hand-read corpus, the opposite of what the sweep corpora said — **a sweep corpus is built from the candidates the locator fires on, so it oversamples staves where it produces something and cannot answer 'what does this rule cost in the wild'.** Branch shares come from `probe_clef_rejection.py` (orchestral scores only); precision from `check_clef_precision.py` (engraved reference sheet, braced piano, a scanned-orchestral spot check, and one SWEEP corpus per edition). **Nottebohm is out of every harness and test — orchestral scores only.** **Run both — never one alone**; every promising change in this area has looked like a large gain on one while losing on the other. Vertical header clustering (`ClefLocatorConfig.cluster_y_gap_spaces`) is **on** as of 2026-08-31 — Nottebohm 69 → 77 located of 206 for one extra false positive, a flat rate, with reference 5/5, coverage 7/9, `eval_score_order` and `eval_pipeline_clefs` (69/69) all unmoved. **A sweep corpus is built from the locator's own reads**, so unlike the older corpora it cannot be blind to what the locator gets wrong: adding a second edition (`mahler5-clef-sweep.json`, Edition Peters) took the reported FALSE POSITIVES from 7 to **48** without a single regression — they were always there. Twenty-four of Mahler's 41 are not misread clefs at all but the stacked instrument numbers Peters prints LEFT of the bracket, a family the Beethoven scan cannot show. **Never tune a clef threshold on one edition**: a tenor symmetry floor separates cleanly on Beethoven (gap +0.015) and is impossible on Mahler (overlap 0.137) — refused, see `clef_symmetry_populations.py`. What worked instead was POSITION, not shape (`require_cluster_on_staff`, shipped): a cluster ending before the staff's own printed lines begin is margin ink — instrument numbers, the brace — and is SKIPPED, not stopped for, so the clef behind it is still found. **FALSE POSITIVES 48 → 21** (Mahler 41 → 14, Beethoven 7 → 7 exactly neutral) for 2 Mahler misses, and Nottebohm coverage went UP 77 → 79 because skipping beats rejecting. **The F-clef dot veto was then fixed by POSITION too, not shape: FALSE POSITIVES 21 → 13 at zero cost.** The dots of a misread bass clef sit PAST the body's right edge (0.94–1.79 w) where a C clef has nothing, so a second, looser reading of the same two dots is admitted only out there (`dot_clear_right_fraction`) — and the real-clef cost is identically 0 for every height and aspect tried, on both editions, where loosening height at the old 0.55w position cost 27 clefs. It is a second tier, so every veto that fired before still fires. **Then a SINGLE clear dot was made enough on its own (`dot_single_clear_is_enough`): FALSE POSITIVES 13 → 5.** Unlike everything else here this is a TRADE, taken deliberately — 8 false positives removed for 20 declined C clefs (sweep misses 8 → 24, Nottebohm located 79 → 77, orchestral misses 5 → 7). It is defensible because a declined C clef leaves its staff on the default it would have had without the locator, while an accepted F clef transposes every note on the staff; no measurement makes it free. `eval_pipeline_clefs` still holds 69/69 (the contextual layer's `slot_continuity` picks up what the locator drops), `eval_score_order`'s read-clefs arm fell 10 named/5 correct to 8/3, and that is a COVERAGE effect, not an accuracy one: La Mer is byte-identical and the whole movement is Beethoven 5 p.15, where the veto removed one right clef (Viola/alto) and one wrong one (Violin/soprano). The 5 that remain are 3 bass + 2 treble; the G clefs are out of a dot veto's reach by construction. The staff's left edge is a horizontal run ≥ 4 spaces, and where that lands more than 4 spaces into the header window the measurement has FAILED (broken lines) and the rule ABSTAINS (`staff_left_max_spaces`) — 173 of 174 sweep staves land under 3.55 spaces, the outlier at 6.77 is the one staff the rule wrongly cost, and it is now recovered: sweep misses 9 → 8 with nothing else moving. Measuring the edge from the BAND profile instead (`staff_header._walk_left`) was built and REFUSED — it swallows the instrument name, and every variant that recovered that clef cost 2–3 false positives. The measurements, the closed approaches, and the ways the measurements themselves went wrong are in `benchmarks/omr-clef-geometry/RESULTS.md`.

- **Dynamics letters are placed but never checked against where a dynamic is PRINTED** (measured 2026-09-04, NOT FIXED — [benchmarks/omr-dynamics-band-2026-09/FINDINGS.md](benchmarks/omr-dynamics-band-2026-09/FINDINGS.md)). `export.measure_dynamics` joins `f`+`f` into `ff` by x-adjacency and uses **no vertical information at all**. Measured over 1246 letters on 18 pages of 9 publishers, a placement band is there and is clean: 73% of letters stand in their own staff's band, 24% in the band of the staff **immediately above — distance exactly 1, no exceptions**, which is the measure cell's 4-6 space padding reaching into the neighbour's dynamic row. Pooled widest empty interval **−3.04 to −0.52 spaces**, and the lower edge is a plateau (−1.5 to +0.25 changes nothing). ⚠️ **A GATE IS THE WRONG FIX**: an out-of-band letter is usually the neighbour's ink, not junk, and **83% of re-attributed letters are the target staff's SOLE evidence** — because `_dedupe_cross_staff_detections` already removed the twin BY DISTANCE and kept the lower staff's copy, the same failure the ledger-ladder work found for noteheads. So this belongs in that function as another evidence tier, not as an export filter. ⚠️⚠️ **RE-ATTRIBUTION IS PROVEN ON ENGRAVINGS AND FLAT ON SCANS** — canonical 11 works: over-emission 1.19 → 1.04, staves exact by word 52 → 83 of 107, no work worse; 11 scanned pages with hand-verified windows: **16 → 16**. The scan table says why: there we **under**-emit (376 words against 491), so the dominant dynamics error on a scan is a mark never found, not one on the wrong staff. ⚠️ **The scan under-emission was then diagnosed and is NOT mainly a placement problem**: of a 129-mark shortfall, **14** are read and discarded by the eventless-measure branch (see the direction-text section above — this is that bug, live), ≤31 more are detected letters in a run that spells no dynamic and is thrown away whole (15 of them a lone `s`, an `sf` whose `f` was missed), and the rest were never read — **137 of the shortfall coming from the two Beethoven 5 p.2 scans alone**, with the other nine pages emitting 191 against a truth of 183, i.e. over-emitting slightly just like the engraved arm. Refuted on the way: **confidence** as a filter costs 233 of 911 good letters to remove half of 35 bad ones.

- **Orchestral conductor's scores.** The current model was trained predominantly on DSv2 (synthetic) + 60 hand-labeled real cells. Dense conductor's scores (Mahler 5, Debussy La Mer) work but with more false negatives on small dynamics + grace notes. The labeling pipeline (`tools/omr/annotate`) is the path to fixing this.

- **PDF.js crop region in DiffCard is incomplete.** `PDFjsRenderer.tsx` has a TODO for full crop viewport implementation.

- **No database migrations.** Schema changes require dropping and recreating the DB (all data lost). Add Alembic migrations before going to production with real user data.

- **Single-server architecture.** Background tasks (OMR, Vision diff) run in FastAPI `BackgroundTasks` — no task queue. Long jobs will fail if the server restarts. For production scale, replace with Celery + Redis.

- **Frontend field names still say "audiveris".** `FlaggedDifference.audiveris_confidence`, `AutoAcceptRule.min_audiveris_confidence`, and `KnowledgePattern.pattern_type === 'audiveris_failure'` are vestigial — they now refer to the primary OMR engine's confidence (local YOLO). Rename when there's a DB migration story.

---

## Deployment

See [`scripts/setup-vps.sh`](scripts/setup-vps.sh) (first-time server bootstrap) and [`scripts/deploy.sh`](scripts/deploy.sh) (update). Production uses [`docker-compose.prod.yml`](docker-compose.prod.yml) with Traefik v3 for automatic Let's Encrypt SSL.

Minimum server spec: **4 vCPU, 8 GB RAM** (ultralytics CPU inference needs RAM headroom for the model + page rasters). Recommended: Hetzner CPX31 (~$14/mo) or DigitalOcean 8 GB Droplet ($48/mo). GPU not required for inference, but a CUDA-capable box drops per-cell time by 5–10×.

```bash
export DOMAIN=yourdomain.com ACME_EMAIL=you@yourdomain.com
cd /opt/reengrave && bash scripts/deploy.sh
```
