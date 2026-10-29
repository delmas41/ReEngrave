# Measuring

The acceptance set, the three measures, how to A/B without fooling
yourself, the test tiers, and the flags. Moved out of `CLAUDE.md` §6 and §7
on 2026-10-13 (`docs/claude-md-migration-2026-10-13.md`).

## 0. How a lane reports (Sean, 2026-10-21) -- read this first

Sean: "Can we simplify the measurements?" ... "Set that up as a rule". Every lane
reports the SAME three things and nothing else unless Sean asks:

1. **What changed in the exported file**, flag OFF vs ON: symbols written that
   were not, and symbols no longer written, by kind (notes, rests,
   accidentals, flags, dots, ...), one line per plate, plus red bars. Produced
   by the ONE shared command, `python3 -m tools.omr.staged.lane_report --flag OMR_X --out DIR`
   (`docs/running.md` §2b), never by a lane's own script.
2. **Were the changes right**: Sean's 12 blind tiles -- ~9 drawn at random
   (seed stated) from the changes, ~3 controls, a neutral orange where-to-look
   marker, the key in a separate file.
3. **Did anything Sean already judged get worse**: his judged answers that go
   right->wrong (`tools.omr.staged.judged`). Must be 0; each one is shown.
   A lane reports **unwritten->wrong** beside it (a judged answer OFF left unwritten -- narrowed or abstained -- that ON writes with a wrong value or kind; `lane_report`, ROADMAP 2.218); both must be 0 to land. Re-score saved arms with `python3 -m tools.omr.staged.lane_report rescore --work DIR/work --plates litolff`.

**What the judged check counts (lane-scorer-blue, 2026-10-29).** Litolff p10, `glyph/10/0/9/6/3` (2.220-plan tile 5, Sean "half"): a half written blue OFF and a quarter written blue ON scored 0 over 132 tiles. Two causes. (1) The 2.220 galleries have no `manifest.json`, so `judged.item_rows` gave their tiles no subject and they were `unscored`; a value gallery's `key.json` (tile, plate, glyph key as `subject` or `rg`, a `written` value or `off`/`on` type words) is now read as its manifest, and the index rebuilt (`python3 -m tools.omr.staged.judged build`). (2) The verdict scorer reads DECIDED durations only, so a blue note that INFER narrowed and then changed value (verdict `narrowed` on both arms) moved nothing. `lane_report.written_moves` now also scores the value EXPORT WROTE at each judged one-value glyph tile's place (same pitch, never a chord-mate; undotted base counts as Sean's value, as in `judged._duration`), plain or blue alike: right->wrong if it moves away from Sean's answer, wrong->right if toward it. A moved pitch or a gone note is a lost/changed note, not a value change. Counts print with their blue share, e.g. "right->wrong 1 (1 blue)"; the LANDING CHECK line carries it and fails on any nonzero count, blue or not. Not covered: judged rests, arcs and pitch (Sean's answers give no pitch), and tiles whose gallery has neither manifest nor such a key.

Measured on the **frozen page sample** (about 8 pages per plate, drawn at
random once and fixed, `benchmarks/lane-report/sample.json`), which takes
minutes (`lane_report` reads it; `benchmarks/lane-report/FINDINGS.md`). No
lane runs a whole-movement replay; the whole movement is the overnight
Sean runs. Trade-off accepted: a rare case may miss the sample and is caught
overnight. The report opens with the cause and the process lesson (CLAUDE
rule 3). Everything below is the background these three rest on.

**Exception -- the shared ink map path (Sean, 2026-10-22):** a step that changes no output (records, links or slims the stroke map) reports only the fast tests and a byte-identical control -- no lane_report, no tiles. The three measures apply at the milestones where a reader switches to the map, as the new path against main.

**Fail fast (Sean, 2026-10-25: "Don't take too long testing if we can rule out issues quickly"):** a lane first runs lane_report on a 2-page-per-plate subset (`LANE_REPORT_SAMPLE`); if notes not written jump or any judged answer goes right->wrong, it stops and finds the cause there. The full frozen sample runs only once the subset is clean.

**List why every lost note was lost (Sean, 2026-10-26 "Yes"):** before the full sample, the subset's lost notes are grouped by their refusal reason ON vs OFF and the top groups looked at on crops. Judged answers cover only notes Sean has seen; a reader whose cut-off was set on old input can drop unjudged notes with no right->wrong (2.206b: the stem-tip reader read slur starts as hooks on the restored ink; found only by tiles, after a 2-hour full run). A fix to a SHARED input (the image, the stroke map) also lists every downstream reader whose OFF readings sit near its cut-off.

## 1. The acceptance set and the three measures (plan §4)

| document | kind | count page |
|---|---|---|
| Beethoven 5 mvt 1, Litolff `984073` | scan, bitonal, MERGING plate | pdf index 3 (works row `...984073-p3`) |
| Brahms 1 mvt 1, Breitkopf `317803` | scan, SHATTERING plate | pdf index 1 (works row `...317803-p2`) |
| Beethoven 5 mvt 1 bars 1-24, Verovio render, 18 parts | engraved, exact page truth | page 0 |

- **Engraved:** reading F1 against the page truth (`page_truth.py`,
  `score_reading.py`) and musicdiff against the encoding (`omr_ned.py`). The
  current engraved figure is written in exactly one place,
  `benchmarks/omr-ned-2026-08/CURRENT.md`, generated by `accuracy_record
  --update` and checked by `--check`.
- **Scans, machine proxies:** notes reaching the file over gathered; bars
  that add up to the meter in force; parts named; `held_out`; `unread_bars`.
  Controls, never objectives -- a proxy that improves while the count worsens
  is what the count exists to catch.
- **Scans, the count:** Sean adjudicates the fixed page against the print on
  `benchmarks/omr-cleanup-count-2026-09/CATEGORIES.md` (unit = one
  FIX-ACTION with a declared scope; categories `missing / wrong / spurious /
  would-not-notice`), results committed under
  `benchmarks/omr-cleanup-count-2026-09/counts/`. It is read as *what to fix
  next*, never as *are we winning*. Deferred for now (Sean, 2026-09-30: too
  far from usable to count); offer crops or "name the worst thing" instead.
- **Hand-labeled page truth** (ROADMAP 1.7, `data/hand-truth/README.md`):
  Sean (2026-10-08): *"I would like all our tests to finally be tested on
  hand-labeled pages only"*. Scorer: `benchmarks/hand-truth-score-2026-10/`.

`python3 -m tools.omr.acceptance` (ROADMAP 1.3) runs all of it and writes
`benchmarks/acceptance/current.json`.

## 2. How to A/B without fooling yourself

- **Until further notice, EVERY test is GATHER + ADJUDICATE only** (Sean,
  2026-09-30: *"I want all our tests for now to just be the first 2 stages. I
  want to focus on the gather and identification"*), including scoring
  against the reference: compare a head's measured STAFF POSITION with the
  reference pitch converted through ADJUDICATE's clef -- never `Q.PITCH`
  (EVALUATE) or the exported file. The small re-gather's default is the
  same (ROADMAP 1.6b): the gather stops `--through adjudicate`, and the tool
  reports per family gathered boxes, kept vs refused by reason, owner and
  duration decided/narrowed/abstained by reason, staff position, the clef per
  staff, meter per system -- all counted off `readout`'s own
  `Run`/`adjudicate_status`, never re-derived, with the `readout html` page
  alongside. `--against` diffs two records with `readout diff`. Only `--full`
  runs through INFER, exports, and reports the page proxies, print-vs-ours
  and the per-part per-bar score (the SECOND view, written to
  `benchmarks/acceptance/quick/`).
- **Two re-gathers** (Sean, 2026-09-30): the SMALL one by day, the FULL one
  overnight, which Sean runs -- never ask. Commands in `docs/running.md` §3.
- **Base vs arm on ONE tree.** The committed verdicts of the shared records
  under `library/_shared-records/` no longer reproduce on today's tree
  (`readjudicate --control` 2,760 of 2,993,
  `benchmarks/omr-shape-role-2026-09/FINDINGS.md`); they are inputs, not
  baselines. A shared record is a snapshot of the reader that made it (two
  Litolff records differ by more than a date -- one holds 0 margin labels).
- **A GATHER change needs two full re-gathers**; `readjudicate.py` and
  `reexport_arm.py` are structurally blind to it and a zero from either is
  not evidence.
- **Give every arm its own `--tag` or work dir.** `scan_eval` caches by
  default and a cached A/B reports "identical on every row" -- the clean
  result a flag-guarded change hopes for. The tell is wall time.
- **The 20-row scan gate has a noise floor of about +/-6 edits** and is not
  byte-deterministic; a per-row delta under that is not a result
  (`benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md`).
- **OMR-NED is symmetric and rewards emitting FEWER symbols.** It is the
  engraved control only. Under `AllObjects` it pairs notes by pitch, so
  `wrong pitch` is structurally zero and pitch errors land in `wrong note`.
  Never quote it as the reason a note-deleting rule is safe; the evidence
  for that is crops.
- **A print check is a crop with a ruler**, cut from the PDF at the gather's
  own DPI, behind a frame control that can fail, with the SUBJECT marked (a
  corner bracket on the exact head, not a margin tick at its x). The crop
  must NAME and DRAW the staff the subject is filed on. Commit crops under
  `out/print/` -- `.gitignore` excludes `benchmarks/**/crops/`. Blind tiles
  for Sean: nothing of ours drawn, big numbers baked on for his phone; he
  answers "N. 4/8/16", "Dot 4" = dotted quarter; answers go in that
  directory's `answers.json` and a DECISIONS line.
  **Refused heads (2.143, parked OFF):** a head refused as not-a-notehead is not a note -- read its refusal reason, never its duration (the record still carries a stale DECIDED duration on ~1,020 Litolff refused heads). Set `OMR_REFUSED_HEAD_NO_DURATION=1` for a tile/replay run to see them as ABSTAINED.
- **Reach before accuracy.** An arm prints its population first and exits
  non-zero declaring itself DEAD at zero; a change that moves nothing
  because it is inert and one that moves nothing because the page holds
  nothing to move are the same number.
- **A refusal test needs a positive control in the same class**, or it
  passes by refusing everything. A new test is run RED against the
  unrepaired tree first and the commit says so.
- **New weights are tested Sean's way:** graft into a COPY of production and
  compare on GATHER+ADJUDICATE only (`--through adjudicate`); harness
  `benchmarks/omr-weights-ab-2026-09/run_ab.sh` (P-vs-P control = zero
  differences).

## 3. Tests

`pytest tools/omr/tests` runs everything; `pytest -m "not slow"` is the fast
tier (target under two minutes) derived from `tools/omr/tests/durations.json`
-- a file `durations.json` measured is fast or slow by that measurement
alone; a file it has NOT measured (new) is fast by default UNLESS its source
CODE (comments and docstrings do not count, since 2026-10-07) contains
`library/`, `omr-weights` (even inside a benchmark name like
`omr-weights-ab`), a venv or a `.pdf"` path: then the WHOLE file goes slow
silently until it is measured -- compare the passed count after a merge.
Re-measure the durations with `python3 -m tools.omr.tests.measure_durations`
(ROADMAP 0.4f) on a machine that has the library, weights and venvs, from a
clean tree; it refuses a dirty one and leaves all-skipped files unmeasured.

No new test may assert on module source text (`inspect.getsource`, AST
walks) except the flag-direction guard and a gather-shape check; `check`
counts the rest. Mutation batteries were one-off proofs; their `FINDINGS.md`
stand, the scripts are archived (ROADMAP 0.4d), and no new ones are written.
Do not edit `tools/` while a suite is running -- a source-level assertion
reads the new file with the old line numbers and fails on correct code.
pytest's reported time is test time, not wall time; a starved run reads
exactly like a hang. Run with at most 4 workers (`-n 4`) so the shared box
stays usable.

## 4. Flags

The full table with a verdict on every flag is `docs/flags-2026-09.md`. The
product path reads at most 15. A flag is `promote` (behaviour kept, flag
removed), `delete` (measured and refused, code removed, FINDINGS kept),
`research` (behind `OMR_RESEARCH`, never read by the product path, with a
review date), or `frozen` (legacy only).

Convention while flags exist: a default-ON flag's off test is a deny-list
(`not in ("0","","false","no","off")`); a default-OFF flag's on test is an
allow-list (`in ("1","true","yes","on")`) -- so a typo leaves the default in
force. `test_flag_default_direction.py` derives and checks this by AST.

Detector knobs that are not flags: `OMR_IMGSZ` 512 (larger is not better --
ultralytics letterboxes), `OMR_DPI` 300 in the web app and 600 on the CLI
(coupled to imgsz; do not unify without measuring both families),
`OMR_CONF_THRESHOLD` 0.25, `OMR_WEIGHTS_PATH` pins weights and disables
routing.
