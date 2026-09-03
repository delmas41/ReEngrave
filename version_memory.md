# ReEngrave — Version Memory

A running log of changes made to this project, newest first. Updated after
every commit alongside CLAUDE.md and PROJECT_BRIEF.md.

---

## 2026-09-03 — Diagnosed and addressed the failing `Deploy ReEngrave` GitHub Actions workflow

**Why it was asked:** every one of 123 runs of `.github/workflows/deploy.yml`
had failed since it was added on 2026-09-01.

**Root causes found (two independent failures, one per job):**

- [x] **Backend job (Docker build) — wrong build context.** The workflow ran
  `docker build .` from inside `working-directory: backend`, so the build
  context was `backend/`. But `backend/Dockerfile` (and `docker-compose.yml`,
  which builds it correctly) both assume the context is the **repo root** —
  `COPY backend/requirements.txt .` and `COPY tools/ ./tools/` need `tools/`
  and a nested `backend/` folder to exist in the context, neither of which
  exists inside `backend/` itself. Every run failed at `COPY tools/
  ./tools/` with `"/tools": not found`.
  **Fixed:** build from the repo root with `-f backend/Dockerfile .`
  instead of `cd`-ing into `backend/` first.
- [x] **Frontend job (Vercel) — missing repo secrets.** Failed immediately
  with `Error: Input required and not supplied: vercel-token` — the
  `VERCEL_TOKEN` GitHub Actions secret (and likely `VERCEL_ORG_ID` /
  `VERCEL_PROJECT_ID`) was never configured for this repo. Same is true of
  `RAILWAY_TOKEN` for the backend job, just masked by the Docker build
  failing first.

**Decision (asked Sean, he chose):** this workflow targets Vercel + Railway,
but ReEngrave's actual production path is the self-hosted VPS
(`scripts/deploy.sh` + `docker-compose.prod.yml` + Traefik) — Vercel/Railway
were never the real deploy target. Rather than wire up the missing secrets,
**disabled the workflow's automatic trigger** (`on: push` → `on:
workflow_dispatch`, manual-only) so it stops failing loudly on every push,
while fixing the Docker context bug anyway so it isn't left broken if it's
ever triggered by hand or revisited later.

**Files touched:** `.github/workflows/deploy.yml`.

**Follow-up, not done here:** if Vercel/Railway deploys are ever wanted for
real, the four secrets above still need to be added under repo Settings →
Secrets and variables → Actions before a manual run would get past both
jobs.

---

## 2026-09-03 — Added standing docs: `PROJECT_BRIEF.md` and this file

Created per standing preference: CLAUDE.md, `PROJECT_BRIEF.md`, and
`version_memory.md` should all exist and be kept current after every commit.
`PROJECT_BRIEF.md` is the short "what is this project" overview;
CLAUDE.md remains the full technical/working reference; this file is the
running changelog.

---

*Earlier project history (OMR pipeline phases, benchmark results, the
theory layer, etc.) predates this file and is not backfilled here — see
[PROJECT_STATUS.md](PROJECT_STATUS.md) for the narrative history and
`git log` for the full commit record.*
