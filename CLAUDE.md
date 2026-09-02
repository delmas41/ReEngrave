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
| `OMR_LEFT_EDGE_SPLIT`  | `1` (on) | **On by default.** A second, narrow barline scan at each system's shared left edge that *adds* a system break where that left column is empty even though the wide connectivity window found staff-body ink — recovering two stacked systems that the wide window MERGED because a measure number, stem, or `a 2.` marking faked a connection. Union-only (never merges) and gated so it never creates a size-1 system. Measured across 964 library pages: fixed 27 over-merged symphony pages vs 1 mild residual (Mozart K22), 0 size-1 created; ground-truth eval 20/23 → 22/23. Set `0` to disable. See `benchmarks/omr-system-grouping-2026-09/FIX_PLAN.md`. |

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
python3 -m tools.library.build_wishlist --out data/score-library/wishlist.json
```

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

Coverage is what the detector gives: 4 of the 5 triplet groups on the Mahler
page. The fifth carries no marker at all, at any confidence.

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

Current on the engraved orchestral benchmark: **pooled 0.2209** (Mahler 0.0455,
Beethoven 0.1775, Brahms 0.3185), from an opening baseline of 0.3164. Full
reading, and the findings it surfaced that note recall is blind to, in
[benchmarks/omr-ned-2026-08/FINDINGS.md](benchmarks/omr-ned-2026-08/FINDINGS.md),
[WRONG_NOTE_ATTRIBUTION_2026-09-01.md](benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md)
and [SLURS_2026-09-01.md](benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md).

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
| `OMR_LEFT_EDGE_SPLIT` | `1` on (default) → recover stacked systems the connectivity rule merged when staff-body ink faked a connection; `0` disables. See the knobs table. |
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

- **The meter is read from the header by shape, and voted across the system** (2026-08-31). The detector does not read time signatures on real scans — on page 1 of the IMSLP Beethoven 5 it finds *zero* time-signature digits in any header, on a page printing `2` over `4` legibly on all twelve staves. Worse than silence, it used to fill the gap: five `timeSig4` boxes fired on **barline** fragments mid-bar, each became 4/4 via the single-digit guess in `parse_time_signature`, and the page shipped as common time on every staff. `tools/omr/time_signature_locator.py` reads it instead, the way the clef and key signature are read — by geometry. A meter's placement is rigid (numerator in the upper two staff spaces, denominator in the lower two, centred on each other), so the search is one-dimensional: a composite template per candidate meter, built from the Bravura `timeSig0-9` glyphs already in `tools/omr/symbol_library/`, slid along the header window in x. Readings are then **voted across the staves of a system**, because that is where a meter is printed. Measured (`benchmarks/omr-timesig-2026-08/`) over a corpus that is half pages printing no meter at all: **4 correct, 0 wrong, 12 correct abstentions** — across a 600 dpi scan of 19th-century type and LilyPond pages set in a different font from the templates. Beethoven 5 p.1 now emits 2/4 instead of 4/4, and its LilyPond bar-check failures fall 154 → 104. Two discriminators were measured and REJECTED for moving with the printing rather than the answer: ink coverage (separates on the scan, then inverts — engraved TRUE reads score below scanned FALSE ones) and whitespace gutters (no separation at all). `timeSigCommon`/`timeSigCutCommon` have no templates, so common-time pages abstain here and stay with the detector, which reads those two glyphs well.

- **A part is the same staff on every system, not one staff on one system** (2026-08-31). `export.to_musicxml` emitted one `<part>` per (page, system, staff), so a part was never continuous: two pages of a piano prelude came out as **24 parts of 3 bars** instead of 2 parts of 36. That is why OMR-NED could not be read as a recognition score on anything longer than one system, and why `orchestral_eval` capped its excerpts at one page. `export._stitch_slots` now joins staves by ORDINAL across every system and page, and **refuses when the systems disagree about how many staves they have** — printed orchestral scores suppress tacet staves (Beethoven 5 scan p.3 is 11 then 8), and joining those by position would graft one instrument's music onto another; the old per-system parts stand there. Measured on WTC I Fugue 1, two pages, against the Gradus reference: **20 parts → 2**, 3 measures per part → **27** (the reference has 27), OMR-NED **0.9819 → 0.8668**, and the dominant error changes from `entire measure insert/delete` to **`wrong note`** — the metric has stopped measuring the exporter and started measuring the reading. Single-system pages are unaffected. `benchmarks/omr-first-run-2026-08/EXPORT_PARTS.md`.

- **Durations fail on scans because hollow noteheads are invisible, not because the rhythm layer is wrong** (2026-08-31, NOT FIXED — `benchmarks/omr-first-run-2026-08/DURATIONS.md`). Beethoven 5 p.1 prints 68 half notes and the output contains 8; twenty of twenty-six duration errors are a half read as something shorter. The heads are not misclassified, they are **not detected** — at 600 dpi bitonal on this print the half notehead's counter has closed to a thin diagonal sliver inside an otherwise solid head, and a detector trained on clean engraving does not call that hollow. The control settles it: the same music engraved by LilyPond gives 31 hollow detections against 30 real half notes, and pitch recall 0.926 with pitch+duration recall **also 0.926** — every correctly-located note there has the right duration. Four fixes were measured and none shipped: reclassifying by ink fill (nothing to reclassify), counters as enclosed holes (662 candidates for 68 notes), Bravura `noteheadHalf` template matching (15 of 68 at threshold 0.50, none above), and thinning the ink before re-detecting (4 → 9 of 26, while inflating `noteheadWhole` 1 → 5). The lever is a labeling batch through `tools/omr/annotate/`, and ⚠️ **not** ink-degradation augmentation, which is the obvious idea and is already disproven — see the domain-augmentation entry in NOTES.

- **Key-signature accidentals are found by template, not by clustering ink** (2026-08-31). `key_signature_locator` thresholds the header to an ink mask and keeps the accidental-sized connected components — on a scan whose staff-line removal leaves every glyph in pieces, nothing accidental-sized survives: given the CORRECT clef for every staff of Beethoven 5 p.1 it reads **2 of 12**, on a page where eight of the ten it misses print three flats legibly. `tools/omr/key_signature_template.py` slides the Bravura `accidentalFlat`/`accidentalSharp` templates instead and reads **11 of 12** standalone. Two bounds make it work: the search runs only between the **clef** (matched by its own template — the caller knows which clef) and the **meter** (`locate_time_signature`), because a flat's outline correlates with a G clef at 0.57-0.59 against real flats' 0.65-0.76, too close to separate by score. Positions come from the **ink centroid inside the matched box**, not the box centre — box centres leave ±0.5 step of jitter, enough for the fit to read three flats as five. End to end on p.1: key signatures **4/12 → 7/12 correct with 0 wrong**, exact-pitch recall **0.571 → 0.619** against unchanged step recall, so the accidental gap halves; over six pages, staves spoken for 29% → 39%. Curated ground truth unchanged except the Pastoral, **9 → 11 correct, 0 wrong**.

- **Two rules the template reader needed, both found by breaking WTC p.17.** (1) **It may not infer.** `fit_key_signature` recovers slots nothing was detected at, which is right for a reader that only ever loses accidentals; this one can gain a spurious match, and inference compounded five matches into *seven sharps* on a four-sharp page. (2) **It may not carry across systems.** `key_signature_vote` resolves a part by taking the reading with the most accidentals — sound only while every reader under-counts. One staff's spurious fifth sharp was carried onto **every treble staff of all five systems**, taking the page from 10 correct to 5 correct and 5 wrong. `StaffCandidate.can_carry` keeps such a reading on its own staff. ⚠️ **The reader speaks only into GAPS** (where detector and locator both found nothing). Letting the fuller reading win instead is worth +1 on beet5-p2 and +2 on the Pastoral and costs a WRONG reading on the cleanest page in the corpus — priced and refused. Staves with no clef read get the reader against the positional default at `DEFAULTED_CLEF_WEIGHT`, too weak to justify a departure, so the vote can keep it only where it agrees with the system: the clef gate moves from the staff to the page.

- **Common time is read; cut common was measured and withheld** (2026-08-31). `timeSigCommon` and `timeSigCutCommon` were added to `symbol_library/builder.py` and the library rebuilt (every pre-existing template came back byte-identical — the check that mattered, since the clef and key-signature readers share it). A letter meter is one glyph two spaces tall centred on the middle line, padded into the same four-space box so the search stays one-dimensional, and `C` is the strongest reading in the corpus: five common-time pages at 0.745-0.761 against 0.50-0.62 for scanned digit meters. **Cut common is not searched for.** A C with a stroke through it correlates with any vertical ink crossing any rounded blob: with it enabled the sweep claimed a meter on *seven systems that print none*, at 0.51-0.56 over a 0.50 threshold, and no page in the corpus prints a real ¢ to measure the other side against. 2/2 spelled in digits is still read. Corpus total: **8 correct, 0 wrong, 21 correct abstentions.**

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
   those notes and the timpani. COMPLETENESS BEFORE COUNT — an unbroken ladder
   outranks a broken one however long, because a gap is what you see when the
   rungs belong to something else lying in the way.
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

- **End-to-end clef accuracy is 92%, and the detector does most of the work.** Measured 2026-08-29 on 52 hand-read staves (`benchmarks/omr-clef-geometry/eval_pipeline_clefs.py`, `PIPELINE_CLEF_RESULTS.md`): the detector supplies 39 of them at 95% accuracy, the positional default 11 at 82%, the CV locator 2 at 100%. This is the number that matters downstream — a staff carries its clef into every pitch on it and into which slot table its key signature is fitted — and it is much better than the coverage figures below, which are about the CV LOCATOR alone and predate the `imgsz` fix. Every remaining error is a non-treble clef read as treble. A staff that read no clef now takes the clef its own part read in another system when every reading agrees (`contextual._fill_defaulted_clefs`), worth 48/52 → 49/52. With `--dossier`, the work's own parts are joined to the page's slots on the margin LABELS (never on the clefs, which would be circular) and supply the clef where that join is anchored by a label above and below — **50/52 (96%)**. Score-order identity driving clef correction was measured and rejected there: it fixes one staff and breaks another.

- **The CV clef locator reads 8 of 24 real C clefs on hand-read orchestral pages, and declines all 163 staves that carry none** (`orchestral-clef-truth.json`, 10 pages / 187 staves / 4 publishers). An earlier 8-of-10 was a four-page sample and flattered it. Do NOT quote `located / all header cells` (58/720 = 8.1% orchestral) as coverage — most orchestral staves are treble or bass and correctly get nothing, so that ratio is not recall. `probe_cluster_too_big.py` is what separates a rejection from a loss: it cross-tabulates each staff's rejecting branch against its hand-read clef. **The fused cluster (`cluster too big`, 52.9% of orchestral header cells) costs 1 C clef against 90 correct refusals — it is a G clef being seven staff spaces tall, not a bug. Do not go after it.** The leading cost is the single-dot veto: turning `dot_single_clear_is_enough` off recovers 5 real C clefs for 1 false positive (recall 8/24 → 13/24) on that hand-read corpus, the opposite of what the sweep corpora said — **a sweep corpus is built from the candidates the locator fires on, so it oversamples staves where it produces something and cannot answer 'what does this rule cost in the wild'.** Branch shares come from `probe_clef_rejection.py` (orchestral scores only); precision from `check_clef_precision.py` (engraved reference sheet, braced piano, a scanned-orchestral spot check, and one SWEEP corpus per edition). **Nottebohm is out of every harness and test — orchestral scores only.** **Run both — never one alone**; every promising change in this area has looked like a large gain on one while losing on the other. Vertical header clustering (`ClefLocatorConfig.cluster_y_gap_spaces`) is **on** as of 2026-08-31 — Nottebohm 69 → 77 located of 206 for one extra false positive, a flat rate, with reference 5/5, coverage 7/9, `eval_score_order` and `eval_pipeline_clefs` (69/69) all unmoved. **A sweep corpus is built from the locator's own reads**, so unlike the older corpora it cannot be blind to what the locator gets wrong: adding a second edition (`mahler5-clef-sweep.json`, Edition Peters) took the reported FALSE POSITIVES from 7 to **48** without a single regression — they were always there. Twenty-four of Mahler's 41 are not misread clefs at all but the stacked instrument numbers Peters prints LEFT of the bracket, a family the Beethoven scan cannot show. **Never tune a clef threshold on one edition**: a tenor symmetry floor separates cleanly on Beethoven (gap +0.015) and is impossible on Mahler (overlap 0.137) — refused, see `clef_symmetry_populations.py`. What worked instead was POSITION, not shape (`require_cluster_on_staff`, shipped): a cluster ending before the staff's own printed lines begin is margin ink — instrument numbers, the brace — and is SKIPPED, not stopped for, so the clef behind it is still found. **FALSE POSITIVES 48 → 21** (Mahler 41 → 14, Beethoven 7 → 7 exactly neutral) for 2 Mahler misses, and Nottebohm coverage went UP 77 → 79 because skipping beats rejecting. **The F-clef dot veto was then fixed by POSITION too, not shape: FALSE POSITIVES 21 → 13 at zero cost.** The dots of a misread bass clef sit PAST the body's right edge (0.94–1.79 w) where a C clef has nothing, so a second, looser reading of the same two dots is admitted only out there (`dot_clear_right_fraction`) — and the real-clef cost is identically 0 for every height and aspect tried, on both editions, where loosening height at the old 0.55w position cost 27 clefs. It is a second tier, so every veto that fired before still fires. **Then a SINGLE clear dot was made enough on its own (`dot_single_clear_is_enough`): FALSE POSITIVES 13 → 5.** Unlike everything else here this is a TRADE, taken deliberately — 8 false positives removed for 20 declined C clefs (sweep misses 8 → 24, Nottebohm located 79 → 77, orchestral misses 5 → 7). It is defensible because a declined C clef leaves its staff on the default it would have had without the locator, while an accepted F clef transposes every note on the staff; no measurement makes it free. `eval_pipeline_clefs` still holds 69/69 (the contextual layer's `slot_continuity` picks up what the locator drops), `eval_score_order`'s read-clefs arm fell 10 named/5 correct to 8/3, and that is a COVERAGE effect, not an accuracy one: La Mer is byte-identical and the whole movement is Beethoven 5 p.15, where the veto removed one right clef (Viola/alto) and one wrong one (Violin/soprano). The 5 that remain are 3 bass + 2 treble; the G clefs are out of a dot veto's reach by construction. The staff's left edge is a horizontal run ≥ 4 spaces, and where that lands more than 4 spaces into the header window the measurement has FAILED (broken lines) and the rule ABSTAINS (`staff_left_max_spaces`) — 173 of 174 sweep staves land under 3.55 spaces, the outlier at 6.77 is the one staff the rule wrongly cost, and it is now recovered: sweep misses 9 → 8 with nothing else moving. Measuring the edge from the BAND profile instead (`staff_header._walk_left`) was built and REFUSED — it swallows the instrument name, and every variant that recovered that clef cost 2–3 false positives. The measurements, the closed approaches, and the ways the measurements themselves went wrong are in `benchmarks/omr-clef-geometry/RESULTS.md`.

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
