# ReEngrave — CLAUDE.md

## What this project is

ReEngrave is a web application for music score quality control. It takes a scanned PDF of a music score, runs optical music recognition (OMR) to produce MusicXML, then uses Claude Vision to compare each measure of the original PDF against the re-engraved output and flag differences. A human reviews those differences, accepts/rejects/edits them, and then exports a corrected, publication-quality engraved score.

Over time the system learns from human decisions, building auto-accept rules for patterns it has seen before.

**Stack:** FastAPI + SQLite + Audiveris (Java OMR) + Claude Vision API + Verovio + LilyPond · React + Vite + React Query · Docker Compose

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
│   ├── Dockerfile               # eclipse-temurin JDK + Python + Audiveris
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
│   │   ├── audiveris_omr.py     # PDF → MusicXML via Audiveris subprocess
│   │   ├── claude_vision.py     # MusicXML + PDF → flagged diffs via Claude Vision
│   │   ├── export_module.py     # MusicXML / LilyPond / PDF export dispatcher
│   │   ├── lilypond_engrave.py  # MusicXML → LilyPond → engraved PDF
│   │   ├── file_import.py       # save uploads, detect file type
│   │   ├── imslp_agent.py       # IMSLP search + PDF download
│   │   └── analytics.py        # self-improving pattern learning
│   └── routers/
│       ├── auth.py              # register, login, refresh, logout, /me
│       └── payments.py          # Stripe checkout + webhook
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
    → audiveris_omr.py: Audiveris subprocess → produces .mxl (ZIP-compressed XML)
    → Score.status = "review", Score.musicxml_path set
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
        1. Decompress .mxl → plain XML (_ensure_plain_xml)
        2. Apply accepted corrections (currently: XML comment stubs; TODO: real patching)
        3. LilyPond: musicxml2ly → .ly file
        4. PDF: musicxml2ly → lilypond CLI → .pdf
```

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
| Full review-loop with human accept/reject | The web app (Audiveris + Claude Vision flow above) |

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

### Audiveris quirks
- Audiveris v5.4 exports `.mxl` (ZIP-compressed MusicXML), not `.xml`
- `audiveris_omr.py` detects both `.mxl`, `.xml`, `.musicxml`
- `export_module._ensure_plain_xml()` decompresses `.mxl` before passing to `musicxml2ly`
- Audiveris needs the full JDK (not just JRE) and 2–4 GB RAM for the JVM
- The Docker image builds Audiveris from source — this takes ~10 min on first `docker compose build`

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

- **Audiveris confidence parsing is heuristic.** The confidence score is parsed from Audiveris stdout via regex. It may not always be present.

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
