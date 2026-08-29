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

The local OMR pipeline needs a YOLOv8l weights file (`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`, ~88 MB). It's gitignored.

```bash
# docker-compose mounts /Users/seanjohnson/Desktop/ReEngrave/omr-weights/ → /app/tools/omr/training/data/weights/
ls /Users/seanjohnson/Desktop/ReEngrave/omr-weights/
# Should contain: deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
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
│   ├── deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt   # ~88 MB — PRODUCTION
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
| `OMR_WEIGHTS_PATH`    | `tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` | Override weights file path |
| `OMR_CLEF_WEIGHTS`    | _(unset)_ | Optional **clef-specialist** weights — a checkpoint fine-tuned to read clefs, **not** general-purpose detection weights. You don't need it: header reading (clef + key signature) is on by default and needs no extra files. When set, a 2nd detector reads each staff's clef from its header and overrides the main clef, which helps on some orchestral scans (decoupled; the main detector still does all symbols). **Pointing this at ordinary weights makes clefs worse.** See `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`. CLI: `--clef-weights`. |
| `OMR_MAX_PAGES`       | `5`     | Hard cap on pages per OMR job |
| `OMR_CONF_THRESHOLD`  | `0.25`  | Min YOLO detection confidence |
| `OMR_IMGSZ`           | `512`   | YOLO inference image size. **Larger is NOT better** — ultralytics letterboxes to `imgsz²` regardless of cell size, so a big value buys anchors and false noteheads, not recall. Measured: `benchmarks/omr-imgsz-sweep-2026-08/findings.md` |
| `OMR_DPI`             | `300`   | PDF rasterization DPI (CLI default is **600** — they differ on purpose). **Coupled to `OMR_IMGSZ`, and the best pair depends on the music:** 300 wins on sparse authored fixtures (ensemble precision 0.684 → 0.915), 600 wins on dense orchestral pages (Mahler recall 0.042 → 0.208, duration 0.000 → 0.200). Unifying them in either direction regresses the other family. **Do not 'fix' the inconsistency without measuring both.** See `benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md` |

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

## Orchestral end-to-end benchmark

`benchmarks/omr-orchestral-e2e/` — renders an excerpt of a Gradus MXL back to
PDF through LilyPond, so every note is known by construction, at eighteen
staves. The first measurement of note accuracy on a conductor's page.

```bash
python3 -m tools.omr.training.orchestral_eval
python3 -m tools.omr.training.orchestral_eval --works mahler-sym5-mvt1 --no-dossier
```

The input is engraved, not scanned, so a failure is a failure of recognition on
dense music and cannot be blamed on print quality. It says nothing about scan
robustness.

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

### Local OMR engine notes
- `tools/omr/transcribe.py` loads the YOLO model once per call, then iterates pages.
- The image pipeline is canonical-cell-based: each measure is sliced and rescaled so staff span is constant, giving YOLO a scale-invariant input.
- Phase 4f introduced classical-CV stem and beam detection (morphological opening + connected components) because YOLO bounding boxes are structurally bad at thin lines.
- Production weights: `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (Phase 3.3, F1 98.8% on 25-cell Bach WTC verdict set).
- Phase 3.4 attempted to add 6 custom classes (barlines, textDynamic) and caused catastrophic forgetting — those classes are now learned via classical CV instead, not YOLO. See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.

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
| `OMR_WEIGHTS_PATH` | YOLO weights path override |
| `OMR_CLEF_WEIGHTS` | Optional clef-**specialist** weights (CLI: `--clef-weights`); default off. Not general-purpose weights — see the OMR knobs table. |
| `OMR_MAX_PAGES` | Max pages per OMR job (default 5) |
| `OMR_CONF_THRESHOLD` | YOLO min confidence (default 0.25) |
| `OMR_IMGSZ` | YOLO inference image size (default 512; larger is not better) |
| `OMR_DPI` | PDF rasterization DPI (default 300; CLI uses 600 — see the knobs table) |
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
- **SKIP** classical-CV structural elements — **staff lines (`staff`), stems (`stem`), beams (`beam`)**: detected by classical CV upstream (`staff_detector`, `line_detection`), 0 in all prior labels, and YOLO can't bbox thin lines. They become background.
- **SKIP** free text — "sempre", "dolce", tempo marks, instrument names, rehearsal letters: no class exists (`textDynamic` is only for *dynamic* words like cresc./dim.).
- **Barlines** (`barlineSingle`) OK to box (collected toward a future barline class); ledger lines low-value.
- **Ink-bleed / mostly-FP cells are GOOD** — dropped FPs become hard-negative background that suppresses bleed hallucinations. Don't `f` every blob: confirm real notes, leave bleed **pending** (pending and FP convert identically → no label). Too bled to read → skip the cell.
- **Edge-clipped extreme-range notes** — label what's in the *image*, not the musical measure. Notehead cropped out → skip; partly visible → box the visible part. Cells crop at `ORCH_PAD_STAFF_LINES` staff-spaces (`select_cells_orchestral`; raised 2.5 → 5.0 in June 2026 because 2.5 clipped ledger notes); raise further and re-cut only the unlabeled cells if clipping persists.

**UI hotkeys:** `t`/`f`/`u` = TP/FP/unsure (triage) · `c` = fix class (`/` searches) · `b` = redraw bbox · `a` = draw a new box, stays in draw mode after each (`Esc` stops) · `Del`/`Backspace` = remove selected box · `Tab`/`Shift+Tab` = next/prev cell (autosaves).

**Convert finished verdicts → YOLO labels:**
```bash
python3 -m tools.omr.training.verdicts_to_yolo_labels --verdicts-dir benchmarks/omr-labeling-NEW/verdicts \
    --manifest benchmarks/omr-labeling-NEW/cells.json --version-name v<n>-<date>-<tag> \
    --out-root data/user-labeled --labeler sean --description "..."   # --dry-run first
python3 -m tools.omr.training.build_catalog_yaml --root data/user-labeled   # unions all versions → catalog.yaml
```

The catalog is **capped at nc=208 by default** (custom-class boxes — barlines, textDynamic — are filtered into `_nc208/` copies) so fine-tuning matches the DSv2 checkpoints' class count; a mismatched `nc` silently re-initializes the classification head (the Phase 3.4 collapse). `train_yolo.py` refuses an nc mismatch unless you pass `--allow-nc-expansion`; `--emit-full-catalog` also writes an uncapped `catalog-214.yaml` for a deliberate future expansion.

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

- **OMR time-signature detection is unreliable.** The DSv2 model often misclassifies time-sig digits, so this field is `null` for many pages. *(Branch `claude/omr-time-signature-inference-e547f1`, unmerged: `parse_time_signature` now drops left-edge instrument-number misreads; a page meter is back-filled from a dominant detected C/cut-C glyph, else from a per-column beat-sum vote — conservatively, so dense pages still stay `null` rather than guess wrong. See `tools/omr/README.md` → "Time-signature inference".)*

- **Key signatures are read by position; recall is about a half, given the clef.** The header of every staff is now measured (`tools/omr/staff_header.py`) rather than assumed to sit inside the staff-start measure cell — on faded prints it often doesn't, because `Staff.x_start` is the longest ink run on the middle line and that run can begin past the clef. (It can now also begin too far LEFT, in the instrument name, since Phase 1 started bridging broken lines; `_anchor_column` clamps the leftward walk to the staff's own bracket, which took the share of staves whose window actually contains a clef from 186/455 to 233/455 over 26 pages.) Key signatures are then read by fitting accidental *positions* to the slot table for (clef, N) (`key_signature_geometry.py`), so a missed interior accidental is recovered rather than miscounted, and reconciled across staves and systems (`key_signature_vote.py`). Measured on two ground-truth orchestral pages (42 staves), **given the correct clef**: 18 correct, 0 wrong, 16 missed, 8 correct abstentions (34 of the 42 carry a signature). End to end, where the clef must be read, that is 2 staves of 20 on Beethoven 6 p.2 and 0 of 22 on Beethoven 5 p.2. It only seeds staves where the detector found no key-signature accidental at all, so it cannot make a correctly-detected score worse. **It inherits the clef problem**: the slot table is chosen by the clef, and a wrong clef produces wrong signatures rather than abstentions (measured: bass staves defaulted to treble read 3 flats as 2 sharps), so a staff whose clef is only the positional default is skipped. On scans where every staff reads as treble, the key-signature reader stays quiet — the two features improve together. The slot fit also applies to the **detector's own** keySharp/keyFlat markers, and both readings go through the vote. WTC p.17 (E major, clean engraving): counting the markers reads 6/10 staves correctly, fitting their positions 7/10, reconciling across the page **10/10** — each step fixing a different failure (a stray marker; then three staves whose first sharp went undetected, which only the page can recover). Note the readers take different inputs on purpose: the detector reads the staff-start measure cell, the CV locator reads the header window — on the header crop the model finds *zero* key markers at any imgsz, because a letterboxed sliver is outside what it was trained on. The locator anchors its run on the clef specifically — an oversized cluster at the *head* of the window with a clef's height, not merely the largest ink in it — and abstains when there is none; anchoring on a beam or a note group is what let it read ink in the middle of a bar as a signature. All of this is **on by default** — `--no-header-reading` turns it off.

- **Clef reading is geometric, but clef *detection* is still a model weakness.** Which line a clef names is now measured, not classified (`tools/omr/clef_geometry.py`) — alto/tenor/soprano/mezzo/baritone are the same glyph on different lines, so a class label can never separate them, and all ten clefs now flow through pitch resolution and both exporters. A classical-CV C-clef locator (`tools/omr/clef_locator.py`) covers scores where no model sees a clef at all (19th-century C-clef prints: zero detections even at conf 0.03). It runs only where nothing else read a clef, recognises C clefs only, and abstains otherwise. G/F clef *detection* on degraded scans is unimproved. See `benchmarks/omr-clef-geometry/RESULTS.md`.

- **Body text is no longer detected as staves** (fixed 2026-08-28). Row ink-count alone passed the line-length test on justified paragraphs; `staff_detector` now also requires the lines to be *continuous strokes* rather than rows of glyphs (`_line_ink_runs_per_space`). Music tops out at 1.39 runs per staff-space, text starts at 2.02. All music-only scores byte-identical.

- **End-to-end clef accuracy is 92%, and the detector does most of the work.** Measured 2026-08-29 on 52 hand-read staves (`benchmarks/omr-clef-geometry/eval_pipeline_clefs.py`, `PIPELINE_CLEF_RESULTS.md`): the detector supplies 39 of them at 95% accuracy, the positional default 11 at 82%, the CV locator 2 at 100%. This is the number that matters downstream — a staff carries its clef into every pitch on it and into which slot table its key signature is fitted — and it is much better than the coverage figures below, which are about the CV LOCATOR alone and predate the `imgsz` fix. Every remaining error is a non-treble clef read as treble. A staff that read no clef now takes the clef its own part read in another system when every reading agrees (`contextual._fill_defaulted_clefs`), worth 48/52 → 49/52; two richer sources were measured and rejected there (score-order identity, and the dossier joined by alignment).

- **CV-locator coverage is ~30% on 19th-century prints, ~7% on orchestral, and reading is reliable where it happens.** Coverage is measured by `benchmarks/omr-clef-geometry/probe_clef_rejection.py` (one rejecting branch per header cell); precision by `benchmarks/omr-clef-geometry/check_clef_precision.py` (four corpora — engraved reference sheet, braced piano, a scanned-orchestral spot check, and the hand-read page). **Run both — never one alone**; every promising change in this area has looked like a large gain on one while losing on the other. **The oversized-cluster branch holds most of the rest** — the clef fuses into a cluster bigger than any C clef and the locator stops. Two causes are fixed: the header window fixed the horizontal, and running the ink-fraction test BEFORE the size test fixed *sparse* blockers. The third is diagnosed with a fix written and **off by default** (`ClefLocatorConfig.cluster_y_gap_spaces`): grouping header ink by proximity in both axes stops the movement heading above the staff being strung into the clef's cluster, worth Nottebohm 61 → 72 and Beethoven 5 27 → 33, but of the 19 staves it adds, 5 are bass clefs read as C clefs. **The blocker is `_has_f_clef_dots`**, which is the only thing separating an F clef from a C clef and cannot fire when the dots merge into the clef's body on a degraded print — fix that and the coverage is waiting behind a config default. Scoped in `benchmarks/omr-clef-geometry/NEXT_SESSION_HEADER_CLUSTER.md`; the measurements, ten closed approaches, and two ways the measurements themselves went wrong are in `benchmarks/omr-clef-geometry/RESULTS.md`.

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
