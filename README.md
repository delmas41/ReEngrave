# ReEngrave

ReEngrave reads a scanned or engraved orchestral score (a PDF, normally an
IMSLP edition held in the score library) and produces a MusicXML file and a
LilyPond-engraved PDF of the same music. Every bar the reader could not read
is MARKED as unread and never invented; every staff is named or held out and
counted. The output is meant to be cleaned up by a musician, not re-entered.

Personal-use project, in active development. **Start with
[CLAUDE.md](CLAUDE.md)** — it is the spec, kept under 6,000 words, and says
what to read next and in what order.

## Two pipelines, one product path

| Path | Where | Status |
|---|---|---|
| **STAGED** | `tools/omr/staged/` | the product path: GATHER → ADJUDICATE → EVALUATE → INFER → EXPORT, every decision on an append-only record, may abstain |
| **LEGACY** | `tools/omr/transcribe.py`, `export.py`, `contextual.py` | frozen (bug fixes only); still drives the web app and the benchmarks until roadmap Phase 3 |

Shared by both: the YOLOv8 detector, staff/system/measure extraction, the
header readers, the score library, the dossiers and the fact sheet.

## Quick start

```bash
# The product path, one page, through to a compiled PDF
python3 -m tools.omr.staged score.pdf --pages 0 --weights omr-weights/<file>.pt \
    --musicxml out.musicxml --lilypond out.ly --pdf out.pdf

# The derived checks (one number; it must go down)
python3 -m tools.omr.staged.check

# The fast test tier
pytest tools/omr/tests -m "not slow"

# Web app (legacy engine by default; see CLAUDE.md §5a and §11)
docker compose up -d          # → http://localhost
```

Weights are gitignored under `omr-weights/` and the score library
(`library/`, 6.4 GB) is machine-local; CLAUDE.md §5a says how a worktree or a
cloud container gets at them.

## Documentation map

| Doc | What's in it |
|---|---|
| [CLAUDE.md](CLAUDE.md) | The spec: what the system is, the ten rules, how to run and measure it |
| [ROADMAP.md](ROADMAP.md) | The phases and the status of every item; work is an item here or it is not work |
| [docs/DECISIONS.md](docs/DECISIONS.md) | What has been decided, by whom, why (append-only) |
| [docs/plan-2026-09-22-from-here-to-a-finished-score.md](docs/plan-2026-09-22-from-here-to-a-finished-score.md) | The assessment that produced the roadmap |
| [docs/flags-2026-09.md](docs/flags-2026-09.md) | Every `OMR_*` flag with a verdict |
| `benchmarks/<name>-2026-09/FINDINGS.md` | Every measurement, one directory each |
| [docs/chronicle-2026-09.md](docs/chronicle-2026-09.md) | The archived record, May–September 2026; search it, never read it front to back |

`PROJECT_STATUS.md`, `NOTES.md`, `version_memory.md` and `PROJECT_BRIEF.md`
are frozen historical files.

**Stack:** Python 3.11+ · ultralytics YOLOv8 + OpenCV · LilyPond · FastAPI +
SQLAlchemy (async SQLite) · React + Vite + TypeScript · Verovio · Claude API ·
Docker Compose (Traefik in production).
