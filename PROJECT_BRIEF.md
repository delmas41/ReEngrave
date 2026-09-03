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

## Running it

- **Web app:** `docker compose up -d` → http://localhost
- **CLI:** `python3 -m tools.omr.transcribe score.pdf` — no Docker needed
- **Production:** a self-hosted VPS via `scripts/deploy.sh` +
  `docker-compose.prod.yml` (Traefik, Let's Encrypt). This is the deploy
  path actually in use — see the note in `version_memory.md` about the
  unused/disabled GitHub Actions Vercel+Railway workflow.

Full setup and environment variables: CLAUDE.md → "Running locally" and
"Environment variables".
