# ReEngrave — Version Memory

A running log of changes made to this project, newest first. Updated after
every commit alongside CLAUDE.md and PROJECT_BRIEF.md.

---

## 2026-09-03 — Labeling UI: the click-to-box snap reads ledger rungs off the page

**Why:** Sean reported the hollow-campaign defect that the single-symbol
click-to-box sometimes suggested on-line for an in-space note — on ledger
lines only, never inside the staff. Probing the 357 committed hollow-campaign
labels confirmed it exactly: wrong-suggestion rate 4.6% inside the staff,
3.3% at the 1st ledger, **38.1% / 39.3% at the 2nd and beyond**. Mechanism:
inside the staff the snap grid anchors on the cell's own measured line
positions, but beyond it extrapolated at the staff spacing — and measured
ledger pitch is publisher-dependent in BOTH directions (Litolff ~1.10× the
staff spacing, Peters/Breitkopf/Simrock ~0.975×), so no corrected constant
can fix it (swept and refused: best variant recovers 3 of 29 wrongs).

**What:** new `tools/omr/annotate/ledger_grid.py` measures the ledger rungs
printed at the clicked x (thin bands of long ink spans; white gaps up to 0.9
spaces bridged because a whole note's counter splits the one rung printed
THROUGH it; the band's peak-span rows are what must be rung-thin), and
`snap_to_staff` gained an optional `ledger_rungs=` that anchors the outside
grid on them — line slots on the rungs, spaces on their midpoints, the old
extrapolation past an incomplete ladder's reach and wherever no rungs were
read. In-staff behaviour is byte-identical (0 changes across all 214
in-staff labels) and every failure of the reader is an abstention back to
the old grid. Measured on the labels: 2nd-ledger agreement 57.4% → 70.2%,
16 rows recovered vs 7 "broken" — of which visual adjudication showed 2 are
**wrong labels the old snap itself planted** (Sean accepted a wrong
suggestion unnoticed; v8 data-quality follow-up), 3 are artifacts of judging
at stored box centres that sit ON the old grid, 1 real miss, 1 unresolved.
The unbiased hand-positioned subset: baseline 7/13 → ink 10/13. 3.4 ms per
click. Guarded by `tools/omr/tests/test_ledger_snap.py` (8 tests: in-staff
frozen, defect case flips, incomplete ladder abstains, reader reads through
a hollow head, endpoint end-to-end). Probe + eval + refused alternatives:
`benchmarks/omr-snap-ledger-2026-09/FINDINGS.md`.

---

## 2026-09-03 — Scan vs engraved weight routing (on by default)

**Why:** the hollow fine-tune ship left the two domains preferring different
checkpoints — scans want the hollow weights (half-notes 8→27 on beet5-p1),
digitally engraved input the prior production weights (11-work OMR-NED 0.1399
vs 0.1421) — and one weights slot forced one side to pay the other's cost.

**What:** when no weights are pinned (`--weights` / `OMR_WEIGHTS_PATH` /
`weights=` all absent), `transcribe()` now classifies its input by where the
ink comes from — a scanned page is one full-page raster image (total coverage
≥ 0.95 on every scan measured), an engraved page is vector drawings (428–2058
paths vs 0–4, gap empty over 147 probed pages) — and routes: scanned →
hollow-ft, engraved → prior production, ambiguous/blank → default. Any scan
page wins the document verdict (an IMSLP scan behind a digital cover is a
scan); a missing engraved file falls back soft; explicit choice always skips
classification. Verdict + evidence recorded in the result JSON as
`weight_routing`. New: `tools/omr/input_domain.py`,
`transcribe._route_weights`, env `OMR_WEIGHT_ROUTING` / `OMR_ENGRAVED_WEIGHTS`,
35 tests. Costs ≤ 77 ms per document. Side effect: default engraved runs use
the same weights the recorded accuracy headline was measured with, so the
record describes shipped behavior again. Measurements + A/B verification:
`benchmarks/omr-weight-routing-2026-09/FINDINGS.md`. The strategy decision —
why exactly ONE fork, why publisher/era weights are deferred and what
measured triggers reopen them, and the checklist future specialist weights
must pass — is recorded in
[docs/weight-routing-and-specialization-2026-09-03.md](docs/weight-routing-and-specialization-2026-09-03.md).

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
