# ReEngrave

Music score quality control: take a scanned PDF of a score, run optical music
recognition (OMR) to produce MusicXML, check the result (theory checks,
reference comparison, or Claude Vision diff review), and export corrected
`.musicxml` / LilyPond `.ly` / engraved PDF.

Personal-use project. The primary OMR engine is an in-house YOLOv8l +
classical-CV pipeline (`tools/omr/`, F1 98.8% on the Bach WTC verdict set);
Claude Vision OMR is the secondary engine. An optional theory layer
(`tools/maestro_bridge/`, env-gated) validates harmony/rhythm and re-ranks
ambiguous pitches against key context.

## Two ways to use it

| Use it from | Entry point | Best for |
|---|---|---|
| **Web app** | `docker compose up -d` → http://localhost | Reviewing scores, diff review, comparison sessions |
| **CLI** | `python3 -m tools.omr.transcribe score.pdf` | Batch transcription, scripting — PDF → MusicXML / LilyPond with no Docker |

```
PDF ──► OMR (local YOLO │ Claude Vision) ──► MusicXML ──► review ──► export
              │                                  ▲      (vision diff,
              └── theory layer (optional) ───────┘       theory checks,
                  harmony/rhythm validation,             Gradus comparison)
                  pitch re-ranking
```

## Quick start

```bash
# Web app (needs the YOLO weights file, see CLAUDE.md → "OMR weights")
docker compose up -d          # → http://localhost

# Standalone CLI (no Docker)
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly               # → out.pdf

# Theory layer (optional; runs host-side, needs Node)
git submodule update --init   # pulls tools/maestro_bridge/gradus
```

## Documentation map

| Doc | What's in it |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Full operational reference — setup, project structure, pipeline, env vars, common tasks |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Where the work stands right now |
| [NOTES.md](NOTES.md) | Backlog / parked research ideas |
| [tools/omr/README.md](tools/omr/README.md) | OMR pipeline deep dive — JSON schema, CLI flags, class space |
| [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md) | Theory-layer (Maestro Analyzer) integration plan + results |
| [benchmarks/omr-phase4-session/retrospective.md](benchmarks/omr-phase4-session/retrospective.md) | How the OMR pipeline was built (Phase 4 story) |

**Stack:** FastAPI + SQLAlchemy (async SQLite) · React + Vite + TypeScript ·
ultralytics YOLOv8 + OpenCV · music21 · Verovio · LilyPond · Claude API ·
Docker Compose (Traefik in production).
