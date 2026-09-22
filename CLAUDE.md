# ReEngrave — CLAUDE.md

This is the SPEC: what the system is, what it is for, how to run it, and the
rules a session works under. It is kept under 6,000 words. It restates no
measurement — every number it needs is produced by a tool it names, and every
history it refers to lives in a benchmark `FINDINGS.md` or in the archived
chronicle.

**Read in this order, and nothing else before you start:**

1. This file.
2. [ROADMAP.md](ROADMAP.md) — the phases and the status of every item. Your
   work is an item on it or it is not work.
3. [docs/DECISIONS.md](docs/DECISIONS.md) — what has been decided, by whom,
   why. Append-only.
4. [docs/plan-2026-09-22-from-here-to-a-finished-score.md](docs/plan-2026-09-22-from-here-to-a-finished-score.md)
   — the assessment that produced the roadmap, if you need the reasoning.

The 850 KB chronicle this file replaced is
[docs/chronicle-2026-09.md](docs/chronicle-2026-09.md). It is the record of
every measurement, refusal and mistake from May to September 2026. **Read it
by search, never front to back, and never brief a lane from it** — its
sentences are corrected in place and a stale one reads exactly like a work
order. `PROJECT_STATUS.md`, `NOTES.md`, `version_memory.md` and
`PROJECT_BRIEF.md` are frozen historical files.

---

## 1. What the product is

ReEngrave reads a scanned or engraved orchestral score and produces a
MusicXML file and a LilyPond-engraved PDF of the same music. Input is a PDF,
normally an IMSLP edition held in the score library. Output is meant to be
cleaned up by a musician, not re-entered.

**Definition of done** (plan §4): one command, a whole movement, MusicXML
and a LilyPond PDF, in which every bar the reader could not read is MARKED
as unread and never invented, every staff is named or held out and counted,
meter/key/clef are right or abstained, and the cleanup — counted in
fix-actions per page — is small enough that Sean would rather fix than
re-enter.

Sean is a musician who reads these plates. He is the cheapest evidence in the
project. Ask him.

---

## 2. The ten rules

Every session, every lane, every brief.

1. **Brief from the tree, not from a document.** `git log --all -S <thing>`,
   `ls benchmarks/`, and `python3 -m tools.omr.staged.check` before the first
   line. A withdrawn investigation changes no code and is invisible to a code
   search, so open the benchmark directory named after the thing.
2. **Say which path.** Every claim about a mechanism names LEGACY or STAGED.
   "Shipped" without a path is not a claim.
3. **Ask first.** How would a human read this off the page, and which
   engraving convention governs it. One line to Sean before code. If nobody
   can be asked, write `CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT
   CONFIRMED` at the top and proceed.
4. **One objective, three measures.** Report against the acceptance set
   (§6). Anything a lane measures internally is a control, never a headline.
5. **Reach before accuracy, and print before default.** No default flips on
   agreement with our own reading. A crop is cheaper than a lane.
6. **Connect, never guess.** A wiring change may connect a decision; it may
   not let one guess. Guessing lives in INFER and is labelled.
7. **A control must be able to fail.** Run it in a state where it fails
   before trusting it where it passes. A number that is exactly another
   number is a computation, not a measurement.
8. **A fallback never converts "cannot tell" into an answer** — not into
   "same", not into "clean", not into a whole rest that means silence.
9. **No new flag, benchmark directory, derived check or handoff without a
   roadmap item.** Findings go in the benchmark's `FINDINGS.md`; general
   lessons become a rule here or a line in `DECISIONS.md`; nothing else is
   restated anywhere.
10. **The tree outranks every ledger** — a commit message, a report, a
    handoff, this file. `git merge-base --is-ancestor` settles where work is.

---

## 3. Two readers, one product path

There are two OMR pipelines in the tree.

**STAGED** (`tools/omr/staged/`) is the product path (DECISIONS 2026-09-22).
Every decision is filed against a subject on an append-only record, may
abstain, and can be traced. It exports MusicXML. It does not yet export
LilyPond, is not yet called by the web app, and lacks several legacy filters —
those are Phase 3 items on the roadmap.

**LEGACY** (`tools/omr/transcribe.py`, `tools/omr/export.py`,
`tools/omr/contextual.py` and their satellites) is FROZEN: bug fixes only, no
new mechanisms, no new flags. It is what the web app and every benchmark run
until Phase 3 replaces them, and it is the reference reader for A/B. Its 39
flags are frozen with it and may not be read from `tools/omr/staged/`.

Shared by both: the detector (`yolo_detector.py`, the weights, weight
routing), staff/system/barline/measure extraction (`staff_detector.py`,
`system_grouping.py`, `measure_extractor.py`, `preprocessing.py`), the header
readers (`staff_header.py`, `clef_*`, `key_signature_*`,
`time_signature_locator.py`), `line_detection.py`, the direction-text and
margin-label readers, the library, the dossiers, the fact sheet.

---

## 4. The staged pipeline

### 4a. Stages

| stage | question | acts when |
|---|---|---|
| **GATHER** | what is on the page? | always — decides nothing |
| **ADJUDICATE** | what does this ONE thing mean, on what evidence? | it can read it; else abstains |
| **EVALUATE** | what follows NECESSARILY from what we now know? | the answer is forced |
| **INFER** | what is most LIKELY, given everything at once? | the answer is best — labelled |
| **EXPORT** | write it, and count what did not make it | always |

The stage a change belongs in is decided by one question: does the answer
FOLLOW, or is it merely BEST? EVALUATE goes silent where two answers both
fit; INFER is the only stage allowed to choose between them, it may only
collapse a NARROWED verdict to one of that reader's own candidates, and it
never overturns a DECIDED one. EXPORT refuses to argmax a narrowing.

### 4b. The record (`staged/record.py`)

- **Subjects** form a tree: `Kind.DOCUMENT > PAGE > SYSTEM > STAFF > CELL >
  GLYPH`. A glyph's last coordinate is an index into the detector's output
  for that cell, so ink the detector did not fire on has no glyph subject;
  `Q.INK` is the population beneath that (one row per connected ink
  component, filed at an offset ordinal).
- **Rows** are Observations (a reader saw something, with `reader`, `frame`,
  `score` — a ruler reading has `score=None`) or Abstentions (a reader looked
  and could not say, with a reason word). `State.READ / DECLINED / ABSENT`
  keeps *a reader found nothing* apart from *no reader ran*, and that
  distinction is the reason the record exists.
- **Verdicts** are `Outcome.DECIDED / NARROWED / ABSTAINED` with a `basis`
  (which rows) and a `reason`. `NARROWED` carries candidates and their
  support. `Verdict.correlated` records which witnesses share provenance.
- **Quantities** (`record.Q`) are the vocabulary. Their producers and
  consumers are DERIVED by `gather_coverage`, `wiring` and `reach`; do not
  type the list anywhere.
- **Scope** (`EXACT / SELF_AND_ANCESTORS / SELF_AND_DESCENDANTS`) says where a
  consumer looks. A quantity filed on a STAFF read by a DOCUMENT decision
  returns nothing at `EXACT` and fails silently; `wiring --check` catches
  the declared cases.
- **Provenance**: every record is stamped with the commit and `dirty`. A
  record from a dirty tree, or with `dirty is None`, is not a baseline.
- **`Evidence.correlated_groups`**: rows from one reader on one crop are ONE
  signal. A position hung off a glyph row is absorbed by that glyph's own
  term; a second witness needs its own quantity and its own reader.

### 4c. The decisions

28 adjudicators in `staged/adjudicators/` (`structure.py`, `identity.py`,
`header.py`, `clef.py`, `ownership.py`, `rhythm.py`, `text.py`), registered in
`adjudicate.REGISTRY` and run in `adjudicate.ORDER`:

`system_membership, staff_group, measure_partition, staff_ordinal,
system_staff_count, instrument, slot_index, part_partition, group_symbol,
clef, key_signature, glyph_owner, arc_owner, arc_kind, articulation_owner,
fermata_owner, ornament_owner, stem_direction, notehead_is_a_whole_rest,
tuplet_ratio, duration, event, voices, onset_column, wedge_anchor, meter,
dynamic, direction`

Each declares `wants`, `implicates`, `checked_by` and `reasons`; `inventory
--check` reports a declaration the body does not read. Stubs: none
(`adjudicate.stubs()` is the truth, not this line).

**EVALUATE** (`consequences.py`, `evaluate.py`): `restate_pitch` (position +
clef ⇒ pitch), `respell_accidental` (key ⇒ sounding alteration),
`move_glyph` (ownership ⇒ pitch re-derived), `size_measure_rest` (a lone
dotless whole rest takes the BAR's length), `reconcile_duration` (a beam
level re-read by ±1 only where exactly one re-reading lands the bar), and
the join. Rule order matters and is asserted: `move_glyph` runs after
`respell_accidental`, which is why the sounding pitch is routed at EXPORT
and not revised in EVALUATE.

**INFER** (`infer.py`, `inferences.py`): three rules, each with its own gate:
`collapse_slot_index_to_family_block` (default ON, print-verified) and two
duration rules (`collapse_duration_by_column`, `collapse_duration_to_barline`,
default OFF, never print-checked — roadmap 2.3). The harness enforces: runs
after EVALUATE, refuses an unfrozen log, writes only where the record has no
answer, never invents a value, supersedes visibly.

**EXPORT** (`staged/export.py`): MusicXML only. Reuses the legacy pure
renderers (`_mxl_*`) over its own positions. The accounting control is an
EQUALITY — every gathered notehead is written or counted under a named
refusal (`duration_narrowed`, `no_pitch`, `staff_not_identified`,
`owned_by_another_staff`, `ink_is_a_whole_rest`) — and `to_musicxml` RAISES
`Unbalanced` rather than returning a flag. A staff the join could not name is
held out of the file and counted (`OMR_HOLD_OUT_UNIDENTIFIED`). A bar we read
nothing in exports as a measure rest with `measure="yes"` withheld, because
we read NOTHING there, not silence. `status_census` is a partition over every
family with an `unaccounted` bucket a test requires empty; prefer it to any
headline coverage number.

### 4d. The derived checks

`python3 -m tools.omr.staged.check` runs all of them and writes
`benchmarks/acceptance/open-findings.json`. Exit 2 = a check is broken; exit
1 = N open findings; exit 0 = clean. **N must go down.** A finding leaves the
list when it is wired, not when it is explained; a `KNOWN_GAPS` entry is a
reason a gap EXISTS, never a reason one is acceptable.

The parts: `inventory` (declarations vs bodies), `health` (decides / abstains
/ records), `wiring` (declared input read where it is filed), `reach` (does
every quantity reach a live consumer), `gather_coverage` (declared vs
gathered quantities, detector families with no quantity), `capture` (shape /
position / raster / resolution per family), `brakes` (refusals whose premise
may have expired), `trace` (what each stage did to one symbol; `--subject`,
`--family`, `--empty-claims`), `conventions` (the 114-entry engraving
registry and what reads it), `no_producer` (a parameter threaded with no
supplier), `export_coverage` (elements the truth has and we never emit),
`accuracy_record` (the recorded engraved figure agrees with the tree).

Three blind spots, by construction: none of them sees a GATHER change
(`readjudicate` and `reexport_arm` rebuild from a saved record — pricing a
GATHER change needs two full re-gathers); none of them sees the DETECTOR;
and `wiring` matches a detail key by bare name, so an unrelated module
naming the same string reads as a consumer.

---

## 5. Running things

### 5a. Setup

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

**A git worktree has none of the four repo-root-relative assets.** Symlink
all four or the scan side fails while the engraved side looks healthy:

```bash
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-surya .venv-surya
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/weights tools/omr/training/data/weights
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
```

The library (`library/`, 6.4 GB) is machine-local and resolves to the main
checkout from any worktree. A cloud container has no weights and no library
and can only re-export or re-adjudicate a committed record.

### 5b. The staged pipeline (product path)

```bash
python3 -m tools.omr.staged score.pdf --pages 0-2 --weights omr-weights/<file>.pt --out rec.json
python3 -m tools.omr.staged score.pdf --pages 0 --weights <...> --musicxml out.musicxml
python3 -m tools.omr.staged score.pdf --pages 0-2 --weights <...> --against legacy.omr.json
```

Options: `--pages`, `--weights`, `--dpi`, `--conf`, `--imgsz`, `--out`,
`--against`, `--musicxml`, `--no-surya`, `--no-ocr`, `--work-id`, `--sheet`,
`--no-roster`, `--progress`. There is no `--dossier` and there will not be
one: a dossier reaches the pipeline only through a human-confirmed fact
sheet (`--sheet`, §8), so the measurement path is structurally unable to
consume a truth file.

Operational facts worth more than they look:
- Run a long gather WITHOUT `--musicxml` and export separately: the CLI
  imports the exporter AFTER the gather, so an edit to `export.py` mid-run
  reaches it, while an edit to an already-imported module does not. Land
  every edit before the run; the provenance stamp names the tree that
  FINISHED, not the code that ran.
- Cost on a scan: ~93 s/page with the margin-label rungs, ~267 s/page with
  the direction-word reader; `OMR_DIRECTION_TEXT_SCAN_GATE=1` skips the
  latter on a page proved to be a scan. Unattended: `OMR_SURYA_KEEP_ALIVE=0`
  so the run owns its own processes. **Never `pkill -f llama-server`** — the
  resident server is shared with other sessions; use
  `python3 -m tools.omr.staff_labels_surya --stop` only when nothing else is
  reading.
- A record with the ink layer is ~115 MB/page on Breitkopf. Roadmap 1.1
  persists the ink summary instead.

Other staged commands:

```bash
python3 -m tools.omr.staged.check                     # every derived check, one number
python3 -m tools.omr.staged.export rec.json --out out.musicxml
python3 -m tools.omr.staged.trace --run rec.json --subject glyph/1/0/2/4/1
python3 -m tools.omr.staged.trace --run rec.json --family note
python3 -m tools.omr.factsheet draft score.pdf --record rec.json -o sheet.json
python3 -m tools.omr.factsheet show sheet.json
```

### 5c. The legacy pipeline (frozen; benchmarks and the web app until Phase 3)

```bash
python3 -m tools.omr.transcribe score.pdf --pages 0-4 --out out.json --overlays-dir overlays/
python3 -m tools.omr.export out.json --format musicxml --out out.musicxml
python3 -m tools.omr.export out.json --format lilypond --out out.ly && lilypond out.ly
python3 -m tools.omr.training.orchestral_eval --omr-ned --record   # the engraved 11-work figure
python3 -m tools.omr.accuracy_record --check
```

The web app: `POST /api/scores/{id}/process/omr?omr_engine=local` →
`backend/modules/local_omr.py` → legacy `transcribe` + `to_musicxml`, capped
by `OMR_MAX_PAGES` (5). Export: `backend/modules/export_module.py` → legacy
`to_lilypond` → `lilypond` binary. Review: `backend/modules/claude_vision.py`
renders MusicXML with Verovio, rasterises the PDF, diffs each pair with Claude
Vision, and a human accepts/rejects each diff; `apply_corrections_to_musicxml`
is a stub that adds an XML comment (roadmap 3.4 replaces it with corrections
filed as evidence in the record). The `claude_vision` OMR engine
(`claude_vision_omr.py`) is a secondary reader and is not on the roadmap.

---

## 6. Measuring

### 6a. The acceptance set and the three measures (plan §4)

| document | kind | count page |
|---|---|---|
| Beethoven 5 mvt 1, Litolff `984073` | scan, bitonal, MERGING plate | pdf index 3 (works row `…984073-p3`) |
| Brahms 1 mvt 1, Breitkopf `317803` | scan, SHATTERING plate | pdf index 1 (works row `…317803-p2`) |
| Beethoven 5 mvt 1 bars 1–24, Verovio render, 18 parts | engraved, exact page truth | page 0 |

- **Engraved:** reading F1 against the page truth (`page_truth.py`,
  `score_reading.py`) and musicdiff against the encoding (`omr_ned.py`).
  The current engraved figure is written in exactly one place,
  `benchmarks/omr-ned-2026-08/CURRENT.md`, generated by
  `accuracy_record --update` and checked by `--check`.
- **Scans, machine proxies:** notes reaching the file over gathered; bars
  that add up to the meter in force; parts named; `held_out`; `unread_bars`.
  Controls, never objectives — a proxy that improves while the count worsens
  is what the count exists to catch.
- **Scans, the count:** Sean adjudicates the fixed page against the print on
  `benchmarks/omr-cleanup-count-2026-09/CATEGORIES.md` (unit = one
  FIX-ACTION with a declared scope; categories `missing / wrong / spurious /
  would-not-notice`), every two weeks, results committed under
  `benchmarks/omr-cleanup-count-2026-09/counts/`. It is read as *what to fix
  next*, never as *are we winning* — the moment it becomes a number to drive
  down it will be gamed the way OMR-NED was, in the opposite direction.

`python3 -m tools.omr.acceptance` (roadmap 1.3) runs all of it and writes
`benchmarks/acceptance/current.json`.

### 6b. How to A/B without fooling yourself

- **Base vs arm on ONE tree.** The committed verdicts of the shared records
  under `library/_shared-records/` no longer reproduce on today's tree
  (`readjudicate --control` 2,760 of 2,993); they are inputs, not baselines.
- **A GATHER change needs two full re-gathers**; `readjudicate.py` and
  `reexport_arm.py` are structurally blind to it and a zero from either is
  not evidence.
- **Give every arm its own `--tag` or work dir.** `scan_eval` caches by
  default and a cached A/B reports "identical on every row" — the clean
  result a flag-guarded change hopes for. The tell is wall time.
- **The 20-row scan gate has a noise floor of about ±6 edits** and is not
  byte-deterministic; a per-row delta under that is not a result.
- **OMR-NED is symmetric and rewards emitting FEWER symbols.** It is the
  engraved control only. Under `AllObjects` it pairs notes by pitch, so
  `wrong pitch` is structurally zero and pitch errors land in `wrong note`.
  Never quote it as the reason a note-deleting rule is safe; the evidence
  for that is crops.
- **A print check is a crop with a ruler**, cut from the PDF at the gather's
  own DPI, behind a frame control that can fail, with the SUBJECT marked (a
  corner bracket on the exact head, not a margin tick at its x). Commit
  crops under `out/print/` — `.gitignore` excludes `benchmarks/**/crops/`.
- **Reach before accuracy.** An arm prints its population first and exits
  non-zero declaring itself DEAD at zero; a change that moves nothing
  because it is inert and one that moves nothing because the page holds
  nothing to move are the same number.
- **A refusal test needs a positive control in the same class**, or it
  passes by refusing everything. A new test is run RED against the
  unrepaired tree first and the commit says so.
- **A shared record is a snapshot of the reader that made it.** Two Litolff
  records differ by more than a date (one holds 0 margin labels).

### 6c. Tests

`pytest tools/omr/tests` runs everything; `pytest -m "not slow"` is the fast
tier (target under two minutes) derived from `tools/omr/tests/durations.json`
— a new test file is fast by default. No new test may assert on module
source text (`inspect.getsource`, AST walks) except the flag-direction guard
and a gather-shape check; `check` counts the rest. Mutation batteries were
one-off proofs; their `FINDINGS.md` stand, the scripts are being archived
(roadmap 0.4d), and no new ones are written. Do not edit `tools/` while a
suite is running — a source-level assertion reads the new file with the old
line numbers and fails on correct code. pytest's reported time is test time,
not wall time; a starved run reads exactly like a hang.

---

## 7. Flags

The full table with a verdict on every flag is
[docs/flags-2026-09.md](docs/flags-2026-09.md). The product path reads at
most 15. A flag is `promote` (behaviour kept, flag removed), `delete`
(measured and refused, code removed, FINDINGS kept), `research` (behind
`OMR_RESEARCH`, never read by the product path, with a review date), or
`frozen` (legacy only).

Convention while flags exist: a default-ON flag's off test is a deny-list
(`not in ("0","","false","no","off")`); a default-OFF flag's on test is an
allow-list (`in ("1","true","yes","on")`) — so a typo leaves the default in
force. `test_flag_default_direction.py` derives and checks this by AST.

Detector knobs that are not flags: `OMR_IMGSZ` 512 (larger is not better —
ultralytics letterboxes), `OMR_DPI` 300 in the web app and 600 on the CLI
(coupled to imgsz; do not unify without measuring both families),
`OMR_CONF_THRESHOLD` 0.25, `OMR_WEIGHTS_PATH` pins weights and disables
routing.

---

## 8. Data the reader can use that does not come off the page

- **The score library** (`library/`, catalog committed at
  `data/score-library/catalog.json`): 289 editions across 29 publishers,
  1,745 reference encodings, keyed on `work_id` = genre + number
  (`beethoven--symphony-5`), never the dossier id
  (`beethoven-sym5-mvt1`). Every fact carries `source_kind`: `catalog`
  (from IMSLP's work page — admissible in production, does not fall silent
  when the raster is bad), `page` (read off the plate — an OMR output, refused
  as a second witness), `encoding` (from MusicXML — a truth file, refused in
  any measurement path). Ingest: `python3 -m tools.library.ingest imslp
  <pdfs>`; downloads are manual through IMSLP's JavaScript gate (do not
  defeat it, pace requests). `verify` checks presence; nothing yet checks
  the mirror question (54 held editions were unindexed until 09-20).
- **Rosters** (`works` tier, `edition_instrumentation`): what a work is
  scored for, parsed from the IMSLP page; N instruments is not N staves.
- **Dossiers** (`data/dossiers/*.json`, 97 works, generated from MusicXML):
  meter, bar count, written clef and key per PART. `slot_facts_for_system`
  abstains unless part count equals staff count, i.e. on every condensed
  conductor's page — which encoded part sits on which printed staff is a
  property of the engraving and is not in the file.
- **The fact sheet** (`tools/omr/factsheet.py`): auto-drafts 29–44 of ~55
  facts from catalog + dossier + record, a human corrects the rest, and every
  correction is recorded as a disagreement with a reader. It is the only
  rung by which a dossier reaches the pipeline (`--sheet`), and a supplied
  clef speaks GAPS ONLY.
- **The conventions registry** (`tools/omr/conventions.py`, 114 entries):
  which engraving convention each decision claims; 44 are read by nothing.

---

## 9. The detector, labels and weights

The detector is the foundation every stage stands on and the one thing no
stage can repair: a box it never drew has no subject. Facts that govern
design here:

- **Fine-tuning on the label corpus DELETES classes** (measured eleven
  ways). The recipe that works is head surgery: graft the fine-tuned head
  rows for the classes the corpus teaches onto the production checkpoint
  (`merge_class_head.py`), with a per-class bias floor. Gate every
  candidate on the three axes in `benchmarks/omr-labeling-survey-2026-09/`.
- **Never erase staff lines before the detector** (costs 7–13 reading
  points and up to a third of the noteheads). Erase for the CV consumers,
  bound the search for everyone else.
- **Weights route by input domain** (`input_domain._classify_page`, a
  measured vector-vs-raster test with an empty gap over 147 pages) —
  legacy path only until roadmap 3.2. `image_type` in the catalog is
  IMSLP's crowd label and reads `Typeset` on 7 of 289; never key on it.
- **The 208-class space is spelled twice**; `class_aliases.canonicalize_names`
  at the one place the model's names are read leaves 157 canonical names.
  `numeral*` and `tuple*` are coarser than the fine names and are not
  synonyms.
- **Anything unboxed on a training cell is background.** `stem` and `staff`
  are CV-only and cost nothing; `beam` and `ledgerLine` are consumed and a
  fine-tune takes them to zero in one epoch. Labeled cell PNGs are not
  regenerable; never re-run the converter on an existing version.
- Labeling: `tools/omr/annotate/` (server at `127.0.0.1:5050`, single-symbol
  passes with `batch_config.json`, click-to-box, `--blind` for scoring
  passes). Pre-filled verdicts are a QUEUE, not labels (blind out-of-sample
  0.915 under the 0.97 bar). Workflow and hotkeys: chronicle §"Hand-label
  cells".

---

## 10. Facts about the page that are load-bearing

Each of these has cost at least one lane and is still true.

- A whole rest means the BAR whatever the meter; a lone quarter rest does
  not. A dot sits a space higher on a line note; the window is asymmetric.
  A beam runs from the first stem it joins to the last, and a stem stands at
  the SIDE of its head — so the outer note's centre is half a head past the
  stroke. An arc is drawn OVER its notes, a hairpin BETWEEN them. A tie's two
  heads are at one staff position (empty interval 0.168 vs 0.435 spaces). A
  key change is printed at one bar on every staff of the system. A
  cautionary meter after a system's last barline governs no bar. A meter is
  printed at a movement's start and nowhere else; the carry is WEIGHED by
  the bars, not gated. Stems: up → right, down → left; right-and-down does
  not exist (96 of 96 against print). Sean's middle-line convention is strong
  and where it looks wrong it is measuring the grid.
- **A page truth is not an encoding truth**: a clef prints per system and
  is declared once; MusicXML writes a slur at each end; Verovio draws one
  accidental per `<alter>`. Do not divide one by the other.
- **Two witnesses off the same raster fall silent together**: the bars are
  not an independent umpire over a bad meter reading; an arbiter correlated
  with one party sides with its family (through ink, convention, frame, or
  a shared assumption). A second witness must come from a different source
  (`source_kind: catalog`, the roster, a clef-free range check).
- **The measure cell is padded 4 spaces (6 where the neighbour is far)** and
  on a conductor's page that reaches the next staff's ink; cross-staff
  ownership is a CONTEST resolved by `glyph_owner` (ladder completeness,
  then range, then distance), and a resolved contest DROPS the loser — it
  never relocates it. Do not grow the pad.
- **A cell index restarts per system**; key a bar on (page, system, cell).
- **A canonical cell frame cannot answer a cross-staff question**; page
  pixels are carried beside it, DECLINED rather than defaulted.
- **Litolff MERGES and Breitkopf SHATTERS**: ink components are not marks
  on either plate; 46 of 180 sampled "notehead" boxes were not noteheads and
  a third of Breitkopf's stemless heads are barlines. A notehead is ~1.3
  staff spaces wide; the width floor costs 0 of 103 confirmed heads.
- **The label lexicon** (`instruments.py`): aliases are GLOBAL, so a widening
  admitted for one score is admitted for every score; cross products are
  DERIVED; `Tp.` is Timpani in German and Trumpet in English and is
  resolved by the page's own other labels; a bare `Basso.` reads as a bass
  VOICE without the roster; 29 of 29 unresolved non-treble staves on the
  scan corpus print no label at all.
- **The condensed count cannot come from the page** (`Viola` = 1 part in one
  edition, 2 in another); it is an encoding property.

---

## 11. Web app internals

- Auth: JWT access (8 h) + httpOnly refresh cookie (7 d); `AuthProvider`
  wraps the app; axios auto-refreshes on 401.
- DB: SQLite via aiosqlite at `/app/data/reengrave.db` (Docker volume `db`),
  SQLAlchemy 2.0 async, models in `backend/database/models.py`. **No
  migrations** — schema changes drop the DB (`docker compose down && docker
  volume rm reengrave_db && docker compose up -d`).
- Storage: `/app/uploads/{score_id}/…` (PDF, `{stem}.omr.json`,
  `{stem}.musicxml`, `snippets/`), `/app/exports/`, Gradus and comparison
  uploads under `uploads/gradus/` and `uploads/compare/`.
- Verovio is Python bindings, not a CLI; SVG → PNG via cairosvg →
  rsvg-convert → inkscape.
- Payments: Vision comparison is $5/score or admin; Gradus, theory checks
  and local OMR are free. nginx `^~ /uploads/` must precede the static regex.
- Maestro theory layer (`theory_layer.py`, `maestro_bridge.py`) is host-side
  Node, off by default, not in the container.
- Frontend: React + Vite + React Query; pages under `frontend/src/pages/`;
  `docker compose build frontend` after any change (Vite bakes env at build).
- Known stubs: correction patching (§5c), PDF.js crop in `DiffCard`,
  vestigial `audiveris_*` field names.

---

## 12. Where things are

```
tools/omr/staged/         the product pipeline (§4)
tools/omr/                shared readers + the frozen legacy pipeline (§3)
tools/omr/tests/          4,800+ tests; fast tier via durations.json
tools/omr/training/       dataset prep, training, evals, head surgery
tools/omr/annotate/       the labeling UI
tools/library/            the score library and IMSLP provenance
data/score-library/       committed catalog, wishlist
data/dossiers/            97 generated per-work fact files
data/user-labeled/        hand-labeled YOLO versions + catalog-versions.txt
benchmarks/<name>-2026-09/FINDINGS.md   every measurement, one directory each
benchmarks/acceptance/    open-findings.json, current.json (roadmap 1.3)
benchmarks/omr-cleanup-count-2026-09/   CATEGORIES.md, the count artefacts
library/                  editions + references + _shared-records (gitignored)
omr-weights/              the checkpoints (gitignored)
backend/, frontend/       the web app (§5c, §11)
docs/                     DECISIONS.md, the plan, the chronicle, NEXT-*/handoff-* (historical)
```

Deployment: `scripts/setup-vps.sh`, `scripts/deploy.sh`,
`docker-compose.prod.yml` (Traefik, Let's Encrypt); 4 vCPU / 8 GB minimum.

---

## 13. Sessions in parallel

Work in a worktree off `origin/main`; never `git checkout` a dirty file
(`checkout-index -a` wiped a session's whole tree once); never bare
`git stash`. Fence lanes by FUNCTION NAME before dispatch when two touch one
file. Every lane report is a ledger: check its claims against the tree with
one command before believing it (five of six reports in one night contained
a claim the tree contradicted). A session ends by updating its ROADMAP line
and, if it learned something general, a rule here or a DECISIONS line —
not by writing a handoff.
