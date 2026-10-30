# Running ReEngrave

Setup, the two pipelines' CLIs, re-gathers, the web app and deployment.
Moved out of `CLAUDE.md` §5, §11 and §12 on 2026-10-13
(`docs/claude-md-migration-2026-10-13.md`). Read this when you need to run
something; `CLAUDE.md` holds the rules.

## 1. Setup

```bash
cd /Users/seanjohnson/Desktop/ReEngrave
docker compose up -d                 # web app at http://localhost, API :8000
docker compose logs -f backend
docker compose build backend && docker compose up -d backend   # after code changes
```

`docker compose restart` does not pick up `.env` changes; `up -d` does. Admin
bypass of the payment gate: `ADMIN_EMAILS=you@example.com` in `backend/.env`.
Hot-patch: `docker cp <file> reengrave-backend-1:/app/<path> && docker
restart reengrave-backend-1`.

Weights are gitignored under `omr-weights/`, mounted into the container:
`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt` (scan production),
`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (engraved, by routing),
`deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt` (prior). Never load
`phase-j-mix`.

### A lane agent works in the worktree it was started in (2026-10-29)

A hook lets an agent Write/Edit only inside its own session's worktree, so a lane that makes its own with `git worktree add` gets every edit refused. Start lane agents with the Agent tool's `isolation: "worktree"`; inside it, `git fetch && git switch -c lane-X origin/main` and `git push origin HEAD:lane-X`. An edit that is refused is reported, never redone through a shell redirect or script.

### A git worktree has none of the four repo-root-relative assets

Symlink all four or the scan side fails while the engraved side looks healthy:

```bash
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-surya .venv-surya
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/weights tools/omr/training/data/weights
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
```

The library (`library/`, 6.4 GB) is machine-local and resolves to the main
checkout from any worktree.

### Cloud sessions

A cloud container has no weights and no library and can only re-export or
re-adjudicate a committed record. **Its clone is SHALLOW** (121 commits from
2026-10-01 on the 2026-10-07 audit): `git log -S`, `--follow` and blame
bottom out at the graft, so rule 1's brief needs `git fetch --unshallow
origin main` (or a blobless bare fetch into the scratchpad) before any "when
was this added" or "not merged" claim (0.8 found 41 such rows on main).

## 2. The staged pipeline (product path)

```bash
python3 -m tools.omr.staged score.pdf --pages 0-2 --weights omr-weights/<file>.pt --out rec.json
python3 -m tools.omr.staged score.pdf --pages 0 --weights <...> --musicxml out.musicxml
python3 -m tools.omr.staged score.pdf --pages 0 --weights <...> --musicxml out.musicxml --lilypond out.ly --pdf out.pdf
python3 -m tools.omr.staged score.pdf --pages 0-2 --weights <...> --against legacy.omr.json
```

Options: `--pages`, `--weights`, `--dpi`, `--conf`, `--imgsz`, `--out`,
`--against`, `--musicxml`, `--lilypond`, `--pdf`, `--no-surya`, `--no-ocr`,
`--work-id`, `--sheet`, `--no-roster`, `--movements`, `--progress`,
`--through <stage>`.

- ROADMAP 4.2: `--movements "1:0-11,2:12.1-20"` names movement boundaries by
  PDF page (or `page.system`); a meter/key carry never crosses one, and
  `--musicxml`/`--lilypond`/`--pdf` then write one file per movement
  (`out-mvt1.musicxml`, ...). `tools.omr.staged.export` takes the same option
  to split an existing record with no re-gather. Omitted, a document is one
  movement.
- `--pdf` compiles the `.ly` with the `lilypond` binary (reusing
  `--lilypond`'s own text when both are given); `lilypond` absent still
  writes the `.ly` and exits 0.
- There is no `--dossier` and there will not be one: a dossier reaches the
  pipeline only through a human-confirmed fact sheet (`--sheet`,
  `docs/data-sources.md`), so the measurement path is structurally unable to
  consume a truth file.

Operational facts worth more than they look:

- Run a long gather WITHOUT `--musicxml` and export separately: the CLI
  imports the exporter AFTER the gather, so an edit to `export.py` mid-run
  reaches it, while an edit to an already-imported module does not. Land
  every edit before the run; the provenance stamp names the tree that
  FINISHED, not the code that ran.
- Cost on a scan: ~93 s/page with the margin-label rungs, ~20 s/page more
  with the direction-word reader (3-36 s, 2026-10-08; it was 267 s before
  the width-scaled token cap), which now runs on scans -- no script sets
  `OMR_DIRECTION_TEXT_SCAN_GATE` any more. Unattended: `OMR_SURYA_KEEP_ALIVE=0`
  so the run owns its own processes. **Never `pkill -f llama-server`** -- the
  resident server is shared with other sessions; use
  `python3 -m tools.omr.staff_labels_surya --stop` only when nothing else is
  reading.
- A record with the ink layer is ~115 MB/page on Breitkopf; ROADMAP 1.1
  persists the ink summary instead. Read a record file ONLY via
  `record_io.load_record` (ROADMAP 1.1b pools in the file).

Other staged commands:

```bash
python3 -m tools.omr.staged.check                     # every derived check, one number
python3 -m tools.omr.staged.export rec.json --out out.musicxml
python3 -m tools.omr.staged.trace --run rec.json --subject glyph/1/0/2/4/1
python3 -m tools.omr.staged.trace --run rec.json --family note
python3 -m tools.omr.staged.readout show rec.json --page 3 --staff 2 --cell 4 [--through gather] [--format jsonl|csv]
python3 -m tools.omr.staged.readout diff base.json arm.json --arm code|weights [--family note]   # GATHER+ADJUDICATE only
python3 -m tools.omr.staged.readout html arm.json [--against base.json] --out page.html        # the print, coloured per stage
python3 -m tools.omr.factsheet draft score.pdf --record rec.json -o sheet.json
python3 -m tools.omr.factsheet show sheet.json
python3 -m tools.omr.acceptance_quick --doc beethoven5-litolff [--against other.record.json]  # the SMALL re-gather; add --full for the exported second view
```

`readout` (ROADMAP 1.5) only reads a record: it refuses one whose GATHER
holds no glyph (a gather run without `--weights auto`) and matches two runs'
symbols by box overlap, never by glyph index.

**One command (ROADMAP 4.1, BUILT not merged):** `python3 -m tools.reengrave
import <work_id> [--edition ID] [--movements SPEC] [--yes] [--dry-run]` ranks
editions (`build_wishlist`'s logic), uses a held one or opens IMSLP for the
one click and watches `~/Downloads`, then runs `tools.omr.staged` per
movement into `out/<work_id>/`. Never defeats the IMSLP download gate.

## 2b. The lane report (ROADMAP 2.188; the one command every lane reports with)

```bash
python3 -m tools.omr.staged.lane_report --flag OMR_X --out out/lane-report/2.NNN          # OFF=0 vs ON=1
python3 -m tools.omr.staged.lane_report --flag OMR_X=2 --flag OMR_Y=0:1 --plates litolff --out DIR   # ON=2 ; OFF=0 ON=1
python3 -m tools.omr.staged.lane_report --out DIR                                          # no flag: OFF==ON, must print "NOTHING CHANGED"
```

Runs the tree OFF and ON through EXPORT on the **frozen page sample** (`benchmarks/lane-report/sample.json`, 8 pages per
plate drawn once with seed 2188 from the 20261020-night records, plus each plate's opening page loaded for its meter/key,
never counted), one fresh process per (plate, arm), `--workers N` (default 2, max 4). It prints, per plate, what changed in
the exported MusicXML by kind (`+` gained `-` lost `~` changed; notes, rests, accidentals, dots, flags, beams, ties, slurs,
articulations, fermatas, ornaments, tuplets, note values, pitches, blue marks, dynamics, wedges, words, clef/key/meter), red bars,
the OFF==record control, and Sean's judged answers going right->wrong / right->gone / wrong->right; and writes
`DIR/tiles/` (12 tiles + `sheet.png`, neutral orange box, seed `--seed`, default 2188), `DIR/key.json` (outside the tile
folder), `DIR/report.txt|json`, `DIR/work/` (each arm's MusicXML). **Stage:** `--from auto` (default) replays the saved GATHER
rows through ADJUDICATE..EXPORT (`adjudicate`); a flag named in a GATHER module (`gather.py`, `positions.py`, ...) is re-gathered
for both arms (`gather`, the detector, slow); `--from adjudicate` on such a flag is refused. A flag named nowhere in the tree is
refused unless `--allow-unknown-flag` (the can-it-fail control). The first run cuts the sample pages out of the 8.8 GB Brahms
record (streamed, one reader at a time under `.record-load.lock`) into `library/_shared-records/lane-report-slices-*`. Wall time:
about 16 min for both plates at 2 workers (Brahms is ~13 min an arm). The sample is frozen: `lane_report sample` refuses to
re-draw without `--force`, Sean's word.

**Read the page once (ROADMAP 2.189).** `YoloDetector._predict` is the one seam to ultralytics' `predict`
(`tools/omr/detector_cache.py`). With `OMR_DETECTOR_CACHE=DIR` (or `python3 -m tools.omr.staged ... --detector-cache DIR`) it stores, per
model call (every pass: production cell, 2.172 views, 2.179 stem-end, rescue floors, `detect_image`, the second weights, routed weights),
the head tensor's CANDIDATES -- every anchor whose best class beats the conf floor -- BEFORE NMS, and on a hit re-runs the same
`non_max_suppression` + `scale_boxes` with the caller's `iou` / `agnostic_nms`. So a lane that changes how boxes are merged, NMS'd
(IoU, class-agnostic within a family), or anything after, is served from the cache and equals a fresh read. It cannot serve a lane that
changes the conf floor, the crop the model sees (pixels, `imgsz`, view, shifts, anti-alias), the weights, or multi-label NMS: those are a
MISS (the key is sha256 of weights-file hash, ultralytics+torch versions, device, conf, imgsz, shape/dtype/pixel-hash of every image), never
a reuse. A corrupt, partial, mismatched or checksum-bad entry RAISES `DetectorCacheError`. `lane_report --from gather` uses one shared,
persistent cache (`library/_shared-records/detector-cache`, gitignored; `--detector-cache DIR|off`) for OFF and ON and for every later run
on the frozen sample; the first run of a sample page reads it, every later one does not. `LANE_REPORT_SAMPLE=file.json` points the report at a
smaller page list (a control; the report says it is not the frozen sample). Cache OFF unless a dir is given; each process prints
`detector-cache: N hit, M miss, ... MB` on exit.

**Read the same cells (ROADMAP 2.231, the master cell map).** Cells are cut fresh in every gather, so an upstream staff or
barline change moves them and two arms can read different cells. A MASTER (`tools/omr/staged/cell_map.py`, machine-local
under `library/_shared-records/cell-maps/<pdf-sha16>-dpi600/`, gitignored) freezes per page every staff, barline, the
page-wide columns and every cell's box and line ys, plus a sha256 of every pixel array, with a version tag naming the cells
(`cm-...`). `python3 -m tools.omr.staged PDF --pages ... --cell-map library/_shared-records/cell-maps` (or `lane_report
--from gather --cell-map master`) LOADS the cells instead of re-cutting: no `detect_staves`, no barline pass; the cells are
cut at the stored boxes and proved hash-equal to the master; a pdf/dpi/page the master lacks, a render that differs, or a
cut that does not reproduce RAISES (`CellMapError`), never re-cuts. The record's provenance names the master
(`provenance.cell_map`); lane tiles' `key.json` carry `cell_map` and `position` (page, system, staff, cell, page box).
`cell_map build PDF --pages ...` writes a master (a page that cuts differently is refused without `--force`: rebuild only
deliberately, after a staff/barline change lands); `cell_map moved PDF --pages ...` lists every staff, barline, column and
cell (`p s st c`, old -> new) the CURRENT tree cuts differently -- a lane whose job is cells reports this; `cell_map verify`
is the same with exit 1 on any difference; `cell_map against-record PDF REC` checks a master against a record's
`cell_box`/`staff_lines` rows. Findings: `benchmarks/master-cell-map-2026-10/FINDINGS.md`.

## 3. The two re-gathers

(Sean, 2026-09-30; `docs/measuring.md` §2 has the A/B rules.)

- **SMALL** (by day, iteration only): `python3 -m tools.omr.acceptance_quick
  --doc <beethoven5-litolff|brahms1-breitkopf> [--against other.record.json]`
  gathers from the movement's first page through the count page (never the
  count page alone -- a lone page loses the meter/key carry and misreports
  the hold-out count in both directions), in minutes, `--through adjudicate`
  by default. It never writes `current.json` and never substitutes for the
  overnight run.
- **FULL** (overnight, Sean runs it -- never ask): both movements,
  `benchmarks/acceptance/overnight/regather_20260930.sh` (`TAG=...`,
  `THROUGH=adjudicate` by default), compared by `compare_20261009.sh`. Only a
  through-infer full re-gather feeds `benchmarks/acceptance/current.json`.

## 4. The legacy pipeline (frozen; benchmarks and the web app until Phase 3)

```bash
python3 -m tools.omr.transcribe score.pdf --pages 0-4 --out out.json --overlays-dir overlays/
python3 -m tools.omr.export out.json --format musicxml --out out.musicxml
python3 -m tools.omr.export out.json --format lilypond --out out.ly && lilypond out.ly
python3 -m tools.omr.training.orchestral_eval --omr-ned --record   # the engraved 11-work figure
python3 -m tools.omr.accuracy_record --check
```

The web app: `POST /api/scores/{id}/process/omr?omr_engine=local` ->
`backend/modules/local_omr.py` -> legacy `transcribe` + `to_musicxml`, capped
by `OMR_MAX_PAGES` (5); `omr_engine=staged` is wired (ROADMAP 3.3) but
`local` remains the default. Export: `backend/modules/export_module.py` ->
legacy `to_lilypond` -> `lilypond` binary. Review:
`backend/modules/claude_vision.py` renders MusicXML with Verovio, rasterises
the PDF, diffs each pair with Claude Vision, and a human accepts/rejects each
diff; `apply_corrections_to_musicxml` is a stub that adds an XML comment
(ROADMAP 3.4 replaces it with corrections filed as evidence in the record).
The `claude_vision` OMR engine (`claude_vision_omr.py`) is a secondary reader
and is not on the roadmap.

## 5. Web app internals

- Auth: JWT access (8 h) + httpOnly refresh cookie (7 d); `AuthProvider`
  wraps the app; axios auto-refreshes on 401.
- DB: SQLite via aiosqlite at `/app/data/reengrave.db` (Docker volume `db`),
  SQLAlchemy 2.0 async, models in `backend/database/models.py`. **No
  migrations** -- schema changes drop the DB (`docker compose down && docker
  volume rm reengrave_db && docker compose up -d`).
- Storage: `/app/uploads/{score_id}/...` (PDF, `{stem}.omr.json`,
  `{stem}.musicxml`, `snippets/`), `/app/exports/`, Gradus and comparison
  uploads under `uploads/gradus/` and `uploads/compare/`.
- Verovio is Python bindings, not a CLI; SVG -> PNG via cairosvg ->
  rsvg-convert -> inkscape.
- Payments: Vision comparison is $5/score or admin; Gradus, theory checks
  and local OMR are free. nginx `^~ /uploads/` must precede the static regex.
- Maestro theory layer (`theory_layer.py`, `maestro_bridge.py`) is host-side
  Node, off by default, not in the container.
- Frontend: React + Vite + React Query; pages under `frontend/src/pages/`;
  `docker compose build frontend` after any change (Vite bakes env at build).
- Known stubs: correction patching (above), the PDF crop in `DiffCard` (a
  placeholder; no PDF.js or Verovio in the frontend since 3.6d). The
  `audiveris_*` names were retired 2026-10-08 (3.6e).
- The stage review viewer (ROADMAP 3.4) cannot be opened from the app's
  browser pane on localhost; Chrome refuses port 5060 (`ERR_UNSAFE_PORT`).

## 6. Deployment

`scripts/setup-vps.sh`, `scripts/deploy.sh`, `docker-compose.prod.yml`
(Traefik, Let's Encrypt); 4 vCPU / 8 GB minimum.
