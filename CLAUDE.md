# ReEngrave — CLAUDE.md

## What this project is

ReEngrave is a web application for music score quality control. It takes a scanned PDF of a music score, runs optical music recognition (OMR) to produce MusicXML, then uses Claude Vision to compare each measure of the original PDF against the re-engraved output and flag differences. A human reviews those differences, accepts/rejects/edits them, and then exports a corrected, publication-quality engraved score.

Over time the system learns from human decisions, building auto-accept rules for patterns it has seen before.

**Stack:** FastAPI + SQLite + in-house OMR (YOLOv8l + classical CV; `tools/omr/`) + Claude Vision API + Verovio + LilyPond · React + Vite + React Query · Docker Compose

> **Note (May 2026):** the OMR engine was changed from Audiveris to a local Python pipeline (`tools/omr/transcribe.py`). The pipeline was developed across 9 sub-phases — see `benchmarks/omr-phase4-session/retrospective.md` for the full story. The Docker image no longer needs a JDK or Audiveris build, but the YOLO weights file (~88 MB) is **not** in git — see "OMR weights" below.

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

If the file is missing, OMR jobs fail fast with a clear error in `Score.metadata_json['omr_error']`. The web app still works for direct MusicXML uploads.

### Hot-patching without a full rebuild

For quick backend iteration, copy files directly into the running container and restart uvicorn:

```bash
docker cp backend/modules/some_module.py reengrave-backend-1:/app/modules/some_module.py
docker restart reengrave-backend-1
```

For frontend changes, a full `docker compose build frontend && docker compose up -d frontend` is required (Vite bakes env vars at build time).

### Default login

Register at http://localhost/register. To give yourself admin access (bypasses Stripe payment gate), add your email to `backend/.env`:

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
│   ├── requirements.txt
│   ├── Dockerfile               # python:3.11-slim + LilyPond + opencv runtime
│   ├── .env                     # local secrets (never commit)
│   ├── .env.production.example  # template for prod deployment
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (reads .env)
│   │   ├── security.py          # JWT + bcrypt helpers
│   │   └── limiter.py           # slowapi rate limiter
│   ├── database/
│   │   ├── models.py            # SQLAlchemy ORM models + Pydantic response schemas
│   │   └── connection.py        # async engine, get_db() dependency
│   ├── modules/
│   │   ├── local_omr.py         # PDF → JSON + MusicXML via tools.omr (replaces Audiveris)
│   │   ├── claude_vision.py     # MusicXML + PDF → flagged diffs via Claude Vision
│   │   ├── export_module.py     # MusicXML / LilyPond / PDF export dispatcher
│   │   ├── lilypond_engrave.py  # MusicXML → LilyPond → engraved PDF (fallback path)
│   │   ├── file_import.py       # save uploads, detect file type
│   │   ├── imslp_agent.py       # IMSLP search + PDF download
│   │   └── analytics.py         # self-improving pattern learning
│   └── routers/
│       ├── auth.py              # register, login, refresh, logout, /me
│       └── payments.py          # Stripe checkout + webhook
├── tools/
│   └── omr/                     # In-house OMR pipeline (Phase 4)
│       ├── transcribe.py        # PDF → structured JSON (entry point)
│       ├── export.py            # JSON → LilyPond / MusicXML serializers
│       ├── yolo_detector.py     # ultralytics YOLOv8l wrapper
│       ├── line_detection.py    # classical-CV stems + beams (Phase 4f)
│       ├── rhythm.py / voicing.py / pitch_resolver.py
│       ├── staff_detector.py / measure_extractor.py / preprocessing.py
│       └── training/data/weights/  # gitignored; mounted from host omr-weights/
├── omr-weights/                 # gitignored, mounted into the container
│   └── deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt   # ~88 MB
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # routes + AuthProvider wrapper
│   │   ├── main.tsx             # React entry, QueryClient, BrowserRouter
│   │   ├── api/client.ts        # typed Axios client, JWT injection, auto-refresh
│   │   ├── context/
│   │   │   └── AuthContext.tsx  # global auth state, session restore on mount
│   │   ├── types/index.ts       # TypeScript interfaces (mirror backend schemas)
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # score library + analytics
│   │   │   ├── ScoreProcess.tsx # Step 1: ReEngrave (OMR)
│   │   │   ├── ReviewUI.tsx     # Step 2: Vision comparison + diff review
│   │   │   ├── Export.tsx       # Step 3: export score
│   │   │   ├── IMSLPSearch.tsx  # search and download IMSLP scores
│   │   │   ├── FileUpload.tsx   # upload local PDF or MusicXML
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
└── docker-compose.prod.yml      # production (Traefik + SSL)
```

---

## The pipeline

```
[User] → Upload PDF or search IMSLP
    ↓
[ScoreProcess page] → "ReEngrave" button
    → POST /api/scores/{id}/process/omr
    → local_omr.run_local_omr() (in a thread, via asyncio.to_thread):
        1. tools.omr.transcribe.transcribe()  → structured JSON (rendered
           at 300 DPI, YOLOv8l at imgsz=1280 by default — env-overridable)
        2. tools.omr.export.to_musicxml(json) → MusicXML string
        3. Both written to uploads/{score_id}/{pdf_stem}.{omr.json,musicxml}
    → Score.musicxml_path = ...musicxml; Score.status = "review"
    → Score.metadata_json["omr_json_path"] = ...omr.json
    ↓
[ReviewUI page] → "Run Vision Comparison" button
    → POST /api/scores/{id}/process/compare
    → claude_vision.py:
        1. Verovio renders MusicXML pages → PNG
        2. pdf2image renders PDF pages → PNG
        3. Each page pair → Claude Vision API (claude-opus-4-6)
        4. Diffs saved as FlaggedDifference records
        5. Snippet images saved to uploads/score_id/snippets/
    ↓
[ReviewUI page] → Human reviews each FlaggedDifference
    → PATCH /api/diffs/{id}/decision  (accept / reject / edit)
    ↓
[Export page] → Choose format
    → GET /api/scores/{id}/export?format=lilypond|pdf|musicxml
    → export_module.py:
        - musicxml: copy + comment-stub corrections (TODO: real patching)
        - lilypond: if Score.metadata_json["omr_json_path"] exists →
                    tools.omr.export.to_lilypond() directly (skip musicxml2ly)
                    else MusicXML → musicxml2ly → .ly
        - pdf:      lilypond .ly → lilypond CLI → .pdf
```

### OMR knobs

The defaults aim for "first-page preview is fast, full transcription
still tractable on CPU." Override via env vars on the backend container:

| Env var               | Default | What it tunes |
|-----------------------|--------:|---|
| `OMR_WEIGHTS_PATH`    | `tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` | Override the weights file path |
| `OMR_MAX_PAGES`       | `5`     | Hard cap on how many pages of a PDF the OMR step processes |
| `OMR_CONF_THRESHOLD`  | `0.25`  | Min YOLO detection confidence |
| `OMR_IMGSZ`           | `1280`  | YOLO inference image size (larger = slower but finds small noteheads) |
| `OMR_DPI`             | `300`   | PDF rasterization DPI (600 in the standalone CLI, 300 here to keep latency reasonable) |

---

## Local OMR pipeline (`tools/omr/`)

In parallel with the web-app Audiveris flow above, there is a local
Python OMR pipeline under `tools/omr/`. It uses a YOLOv8l detector
fine-tuned on DeepScoresV2 (currently **F1 98.8%** on the Bach WTC
verdict set) and produces structured JSON detections without going
anywhere near a browser, Docker, or database.

**Use this when you want to transcribe a PDF without spinning up the
full web stack — e.g., from another Claude session, a CLI script, or
inside a Python notebook.**

### One-shot CLI

```bash
# From the repo root, transcribe one or more pages → JSON
python3 -m tools.omr.transcribe path/to/score.pdf --out out.json

# Specific pages, with overlay PNGs for visual debug
python3 -m tools.omr.transcribe score.pdf --pages 0-4 \
    --out out.json --overlays-dir overlays/

# Convert JSON → LilyPond (.ly) or MusicXML (.musicxml):
python3 -m tools.omr.export out.json --format lilypond --out out.ly
python3 -m tools.omr.export out.json --format musicxml --out out.musicxml

# .ly compiles to PDF: lilypond out.ly  → out.pdf
# .musicxml opens in MuseScore, plays back in DAWs, etc.
```

The JSON groups detections by `page → system → staff → measure` with
each notehead carrying `pitch`, `duration_beats`, `duration_type`, and
`dots`. The exporter groups same-x noteheads into chords via
`tools/omr/voicing.py` and serializes via `tools/omr/export.py`. Full
schema + flag reference: [`tools/omr/README.md`](tools/omr/README.md).

### From Python

```python
from pathlib import Path
from tools.omr.transcribe import transcribe, DEFAULT_WEIGHTS

result = transcribe(
    pdf_path=Path("score.pdf"),
    pages=[0, 1, 2],
    weights=DEFAULT_WEIGHTS,
)
for page in result["pages"]:
    for sys_ in page["systems"]:
        for staff in sys_["staves"]:
            for measure in staff["measures"]:
                for det in measure["detections"]:
                    ...  # det["class"], det["bbox_page"], det["confidence"]
```

### When to use what

| Task | Use |
|---|---|
| Quick PDF → structured detections | `python3 -m tools.omr.transcribe ...` |
| One-off Phase-1-only run (staves + measures, no symbol detection) | `python3 -m tools.omr.run_pipeline ...` |
| Hand-labeling cells to grow the training catalog | `tools/omr/annotate/` FastAPI app |
| Retraining the detector | `tools/omr/training/` |
| Full review-loop with human accept/reject | The web app (the same pipeline above, run from `backend/modules/local_omr.py`) |

### Production weights

`tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`
(84 MB, Phase 3.3, F1 98.8%). The `transcribe.py` `DEFAULT_WEIGHTS`
constant points here. Other checkpoints (earlier phases, the
realft-v1b attempt) live alongside in the same directory — see
`tools/omr/README.md` for the chain.

**Best for** clean engraved PDFs. **Degrades on** handwritten scores,
extreme densities (dense conductor's scores), and any class the model
hasn't been trained on yet (custom barline classes are captured in the
labeling UI but not yet learned — see "Known limitations" below).

### Pipeline at a glance

```
PDF → render_page (PyMuPDF, 600 DPI default)
    → detect_staves (horizontal ink projection)
    → detect_barlines + extract_measures
    → MeasureCell × N  (canonical scale-normalized cells)
    → YoloDetector.detect (yolov8l, imgsz=640, agnostic_nms=True)
    → line_detection (classical CV stems + beams)
    → pitch_resolver  (clef + key sig + accidentals  → "F#4")
    → rhythm          (beams + flags + dots          → duration_beats)
    → transcribe.py groups by (system, staff, measure) → JSON
    → export.py (voicing → LilyPond or MusicXML)
```

YOLO handles "thing-like" symbols (notes, clefs, accidentals, dynamics).
Classical CV (`line_detection.py`) handles "line-like" symbols (stems,
beams) — YOLO bounding boxes are structurally poor at thin lines, and
the Phase 3.3 model emits **zero stem detections**. Hybrid approach
gets the best of both: each algorithm runs on the shapes it's good at.

Phase 1 (staves/measures) is ~1–3 s/page CPU. Phase 3 (YOLO) is
~0.15–0.4 s/cell on CPU; faster on MPS/CUDA when available
(`device="auto"` in `YoloDetector`).

---

## Key technical details

### Authentication
- JWT access tokens (8 hr expiry, configured in `.env` as `ACCESS_TOKEN_EXPIRE_MINUTES=480`)
- httpOnly refresh cookie (7 day expiry) — auto-refresh on 401 via axios interceptor
- `AuthProvider` wraps the entire React app. `useAuth()` throws if called outside it.
- Auth state syncs to the axios client via `setAccessToken()` in `App.tsx`'s `AppShell`

### Database
- SQLite via aiosqlite (async). File lives at `/app/data/reengrave.db` in the container, backed by the `db` Docker named volume.
- SQLAlchemy 2.0 async style. All models in `database/models.py`.
- No migrations (Alembic is installed but not used — tables created via `create_all_tables()` on startup). **Schema changes require dropping and recreating the DB.**

### File storage
- Uploads: `/app/uploads/` → exposed as `/uploads/` via both FastAPI `StaticFiles` mount and nginx proxy
- Exports: `/app/exports/`
- Snippet images saved at: `uploads/{score_id}/snippets/{diff_id}_pdf.png` and `_xml.png`
- Both directories backed by Docker named volumes so they survive container recreation

### Local OMR (replaces Audiveris)
- `backend/modules/local_omr.py` wraps `tools.omr.transcribe.transcribe()` + `tools.omr.export.to_musicxml()`
- Runs in `asyncio.to_thread` so it doesn't block the event loop
- Writes both `{score_id}/{stem}.omr.json` (structured) and `{score_id}/{stem}.musicxml` (for Claude Vision + the existing export path)
- The MusicXML the in-house exporter produces is single-voice-per-part; the `export_module` LilyPond/PDF path prefers the OMR JSON directly to skip a lossy musicxml2ly hop
- Legacy `.mxl` (ZIP-compressed MusicXML) handling in `export_module._ensure_plain_xml()` is now only used for directly-uploaded MusicXML files
- Weights file (~88 MB) is mounted from `omr-weights/` on the host — not in the image

### Verovio rendering
- Python bindings (`import verovio`) — NOT a CLI tool. `verovio` pip package is bindings only.
- Used in `claude_vision.py` for MusicXML → SVG → PNG rendering
- SVG → PNG conversion chain: cairosvg (preferred) → rsvg-convert → inkscape (fallback)

### Payments / access gate
- Vision comparison requires payment ($5/score) OR admin email bypass
- If `STRIPE_SECRET_KEY` is not configured, access falls back to admin-only
- Admin emails: comma-separated list in `.env` as `ADMIN_EMAILS`
- `VisionComparisonPaywall` component handles the UI gate on the ReviewUI page

### nginx (frontend container)
- `^~` prefix modifier on `/uploads/` prevents regex location from intercepting it
- Without `^~`, the `~* \.(js|css|png...)` regex would match PNG snippets and serve cached static files instead of proxying to backend

---

## Environment variables

All in `backend/.env` (local) or `backend/.env.production` (prod):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLite path (set by docker-compose, don't change) |
| `SECRET_KEY` | JWT signing key — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_EMAILS` | Comma-separated, bypass Stripe payment gate |
| `ANTHROPIC_API_KEY` | Claude Vision API key |
| `STRIPE_SECRET_KEY` | From dashboard.stripe.com |
| `STRIPE_PUBLISHABLE_KEY` | From dashboard.stripe.com |
| `STRIPE_PRICE_ID` | Create a product in Stripe dashboard |
| `STRIPE_WEBHOOK_SECRET` | From dashboard.stripe.com/webhooks |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `FRONTEND_URL` | Base URL of frontend (for Stripe redirect URLs) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry (480 = 8 hours) |
| `UPLOAD_DIR` | File upload path (set by docker-compose) |
| `EXPORT_DIR` | Export output path (set by docker-compose) |
| `OMR_WEIGHTS_PATH` | Override the YOLO weights file path (default: `tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`) |
| `OMR_MAX_PAGES` | Max PDF pages per OMR job (default: 5; raise on a beefy host) |
| `OMR_CONF_THRESHOLD` / `OMR_IMGSZ` / `OMR_DPI` | YOLO + rasterization knobs (see "OMR knobs" above) |

---

## Common tasks

### Add a new backend route
All routes are in `backend/main.py`. Add the endpoint there. Auth-protected routes use `Depends(get_current_user)`.

### Add a new frontend page
1. Create `frontend/src/pages/NewPage.tsx`
2. Add route in `frontend/src/App.tsx` (protected or public)
3. Add nav link in `frontend/src/components/Navigation.tsx` if needed

### Change the Claude Vision prompt
Edit `backend/modules/claude_vision.py`. The prompt template is in the `compare_measure_pair` function. The system instructs Claude to return JSON: `{ has_difference, difference_type, description, confidence, is_omr_error }`.

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

---

## Known limitations / TODOs

- **MusicXML correction patching is a stub.** `export_module.apply_corrections_to_musicxml()` copies the original file and injects accepted diffs as XML comments rather than actually patching the XML. Real measure-level patching (replacing `<measure>` elements with `human_edit_value` content) is not yet implemented.

- **OMR confidence is a synthesized average.** `local_omr._confidence_from_result()` averages notehead pitch-resolution coverage and notehead rhythm-resolution coverage. Stored as `Score.metadata_json["omr_confidence"]`. The `FlaggedDifference.audiveris_confidence` column is now a misnomer — it's hardcoded to 0.5 in the Vision flow. Renaming the column needs a DB reset.

- **PDF.js crop region in DiffCard is incomplete.** `PDFjsRenderer.tsx` has a TODO for full crop viewport implementation.

- **No database migrations.** Schema changes require dropping and recreating the DB (all data lost). Add Alembic migrations before going to production with real user data.

- **Single-server architecture.** Background tasks (OMR, Vision) run in FastAPI `BackgroundTasks` — no task queue. Long jobs will fail if the server restarts. For production scale, replace with Celery + Redis.

- **IMSLP downloads are unreliable.** IMSLP's bot-check pages occasionally return HTML instead of a PDF. The file_import module detects this but there's no automatic retry with different headers.

- **Local OMR pipeline does pitch + rhythm + LilyPond/MusicXML export
  (v1).** `tools/omr/transcribe.py` produces a structured `page →
  system → staff → measure → detections` JSON with pitches (including
  key signature + accidentals), durations (whole / half / quarter /
  eighth / 16th / dotted variants), clefs, and time signatures.
  `tools/omr/export.py` serializes to LilyPond or MusicXML. **Caveats**
  for the v1 export: per-measure durations don't always sum exactly to
  the time signature (rhythm parsing is approximate); each staff
  renders as its own Part with no PianoStaff grouping; single voice
  per staff (no stem-direction inference). See `tools/omr/README.md`
  § "Known limitations" for the per-component status.

- **Custom OMR classes (barlines, textDynamic) not yet learned.** The labeling UI captures `barlineSingle/Double/Final`, `repeatRight/Left`, and `textDynamic` at class IDs 208–213, but the current production weights don't see them. Phase 3.4 attempted nc-expansion and caused catastrophic forgetting; refer to `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.

---

## Deployment

See `scripts/setup-vps.sh` (first-time server bootstrap) and `scripts/deploy.sh` (update). Production uses `docker-compose.prod.yml` with Traefik v3 for automatic Let's Encrypt SSL.

Minimum server spec: **4 vCPU, 8 GB RAM** (Audiveris JVM needs ~2–4 GB). Recommended: Hetzner CPX31 (~$14/mo) or DigitalOcean 8 GB Droplet ($48/mo).

```bash
export DOMAIN=yourdomain.com ACME_EMAIL=you@yourdomain.com
cd /opt/reengrave && bash scripts/deploy.sh
```
