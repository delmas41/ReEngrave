# Handoff — 2026-09-03, end of the pre-fill session

Read this first in a fresh session. It says where the branch stands, what is
measured, what is not, and what Sean's next moves are. Everything below is
committed and pushed on `claude/score-labeling-training-system-iech0i`
(PR #5, draft, mergeable against `main`).

## Standing rules for the session (Sean's preferences)

- Manage all work from the main session; use **Sonnet agents** for research,
  and for every commit / merge / push / deploy. Opus only when necessary.
- After every commit update **CLAUDE.md, PROJECT_BRIEF.md and
  version_memory.md**. `version_memory.md` is the running changelog.
- Sean likes checklists and a visible running list of parallel work.
- Commit trailers and PR footer: see the session's system instructions.
  Never put a model name in a repo artifact.

## What this branch built (all on PR #5)

| piece | file | tests |
|---|---|---|
| stdlib MusicXML / MXL reader (chords, backup, pickups, clef per note) | `tools/omr/training/musicxml_truth.py` | `test_musicxml_truth.py` |
| per-measure aligner on STAFF POSITION, weighted LCS, tremolo / tremolando collapse | `tools/omr/training/measure_align.py` | `test_measure_align.py` |
| verdict pre-fill CLI (`--dry-run` / `--write` / `--write-hints` / `--score` / `--debug-cell`) | `tools/omr/training/mxl_verdicts.py` | `test_mxl_verdicts.py` |
| window-row drafter (bars chained per system, staves paired by position or instrument) | `tools/omr/training/draft_windows.py` | `test_draft_windows.py` |
| annotate UI: `prefill/` served, queue order, ghost hints (`h`), red conflicts | `tools/omr/annotate/server.py`, `static/index.js`, `static/cell.js` | `test_annotate_server.py` |

Docs: `docs/status-brief-2026-09-02-labeling-and-training.md` (inventory
and plan), `docs/runbook-prefill-brahms1.md` (how to run the batch), the
CLAUDE.md subsection "Pre-fill verdicts from the reference".

## How the pre-fill decides (the rules that took the day to find)

1. **Alignment key is staff position, not pitch.** Reference position comes
   from its pitch plus the clef the MusicXML carries; the detection's from
   its box against the staff lines. The pipeline's own clef reading is used
   by neither, because on the Breitkopf scan bass and alto staves read as
   treble. Percussion (no clef) falls back to step keys on both sides.
2. **Weighted LCS**: exact position = 2, within a half-space = 1. A bar is
   trusted only with at least one EXACT match, then recall of the
   reference's NOTES (not rests) ≥ 0.5 with ≥ 2 found, or ≥ 0.8 matched.
3. **Neighbour heads stay out**: only detections within the reference's own
   vertical range (±2 positions) enter the alignment. A flute bar of 4 read
   21 heads, 17 of them the oboe's and piccolo's from the cell padding.
4. **Joins abstain rather than guess**: staff count ≠ row's, a staff whose
   bar count disagrees with its system, page count ≠ window, missing
   measure. `staff_index` is numbered across the PAGE, so staves are joined
   by position within their system, never by index.
5. **`bbox_page_px` is `[x0, y0, x1, y1]`**, not `[x, y, w, h]`.
6. **Tremolo / tremolando are reconciled by the READING.** A reference run
   of ≥ 3 repeated equal notes collapses to one head of the total value; an
   alternating run `A B A B …` (≥ 4) collapses to two heads, each with the
   figure's full written value. Either collapses only where the reading
   placed ≤ 1 head at the run's position(s); a page that printed the run
   out is left as written. Black read where collapsed reference says
   hollow → relabelled. Hollow read where reference says black → left
   pending with a `CONFLICT` note and a red hint. Sean chose this so the
   MXL keeps helping on every other hollow note.
7. Human verdict files are never overwritten without `--force`; provenance
   goes in `notes` (`mxl_prefill: C5 half m12`).

## Measured, and not measured

Brahms 1 / Breitkopf batch
(`benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/`, inputs
`transcription.json`, `windows.json`, `reference.mxl` pushed by Sean; the
committed `prefill/` is hints only):

- **51 of 56 cells pre-filled**; 179 TP, 10 relabels, 189 added boxes,
  22 missing-note hints, 200 extra hints, **5 conflicts** for Sean.
- 5 abstentions, all on the right bar (width ratio 1.0), thin readings.
- Against Sean's 14 hollow boxes: the disagreements were all Breitkopf
  tremolo abbreviations, now routed as conflicts rather than relabels.
- **Not measured by a human: black heads and rests**, the bulk of the
  confirmations. Until Sean spot-checks those, treat pre-filled `TP`s as a
  queue, not as labels (CLAUDE.md says the same).
- The Mahler 5 / Peters batch cannot be scored: the library holds
  movements 1–3 and the batch is the Adagietto.

The committed `prefill/` was refreshed on 2026-09-03 and carries the
tremolo collapse and the conflict hints. To refresh it again (from the repo
root — the module path needs it, and the window rows' `work_id` is the
library's `brahms--symphony-1`, so pass no `--work-id`):

```bash
B=benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1
python3 -m tools.omr.training.mxl_verdicts --bench-dir $B \
    --transcription $B/transcription.json --truth $B/reference.mxl \
    --windows $B/windows.json --write-hints
```

## Sean's checklist

- [ ] Open the Brahms batch (`python3 -m tools.omr.annotate.server --bench-dir
      benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1 --port 5051`;
      cell PNGs are gitignored and must be re-cut on the Mac first, see the
      runbook) and look at the 4 cells carrying the 5 red `CONFLICT` hints.
- [ ] Spot-check a handful of black-head and rest confirmations.
- [ ] Decide whether pre-filled `TP`s can be admitted without a glance
      (the `--score` precision on those is the number that decides it).
- [ ] Optional later pass: box tremolo strokes as `tremolo1`–`tremolo5`.
- [x] Gated training run on v7 + the four new hollow batches — done on main
      (`ef51612`, PASS on the labels; v8 held out of the catalog until an
      imgsz-matched fine-tune re-gates it).
- [ ] Merge PR #5 when satisfied.

## Environment notes for the cloud session

- Container has no `skimage` / `music21`: 23 pre-existing failures and 27
  collection errors in the full suite, identical with the branch stashed.
  The new modules' suites (154 tests across annotate + training) are green.
- Installed for tests: pytest, numpy, fastapi, httpx, pillow,
  opencv-python-headless, uvicorn, pymupdf, pyyaml.
- The previous session left an hourly `send_later` check-in on PR #5 bound
  to itself (`trig_013AZGMZ9uZZwZMvNSrQurre`); a new session that takes
  over the PR should subscribe to it and can delete that trigger.
