# OMR next steps — handoff, 2026-08-28

Written at the end of the contextual-analysis session, after its work merged to `main`
(`bf8ed2d`) along with the `imgsz` fix (`4f39fe4`). Four threads are open and ranked.
Each says what it is, why it matters, where to start, and what would count as done.

**Read `PROJECT_STATUS.md` first for the current state.** This file is only the
forward-looking part.

> **Progress, 2026-08-28 (later the same day).** Thread 1 is **done** — see below.
> Before it, three branches carrying finished, measured work were merged to `main`,
> because two of them were about to change the ground the remaining threads stand on:
> the **dossier layer** (external truth from the Gradus MusicXML, seeding clef and key
> per staff — Beethoven 5 R .642→.691, Brahms 1 R .206→.253), the **per-cell `imgsz`
> rule** with the mechanism correction below, and the **clef header-cluster** work
> (measured, shipped off by default). PR #4 also merged, so that bullet is gone.
> Threads 2, 3 and 4 are still open and are still ranked as written.

---

## The one thing to know before starting anything

**Every measurement taken before 2026-08-28 went through a broken `imgsz`.** The CLI
defaulted to 2048 and the backend to 1280, and the pipeline was reporting **2–4× the
notes that exist**. `imgsz` is now derived **per cell** rather than fixed
(`yolo_detector.imgsz_for_cell`); `--imgsz 512` is the best fixed value and
`--imgsz 2048` reproduces the old behaviour.

Fixing it moved end-to-end pitch precision on the `keyboard` fixture from **0.144 to
1.000**, and improved every metric on all three fixtures
(`benchmarks/omr-imgsz-sweep-2026-08/findings.md`).

> **Correction to the mechanism.** This section previously said ultralytics
> "letterboxes to `imgsz²` regardless of cell size, so both were buying anchors".
> It does not: `predict` builds `LetterBox(imgsz, auto=rect)` and scales the
> *longest side* to `imgsz`, padding only to a stride multiple — a 300×1200 cell at
> `imgsz 512` is fed as 128×512. What the model is shown is
> `canonical staff space × imgsz / longest side of cell`, so the right setting
> depends on the cell. That is why the fix is a rule and not a number: a constant
> lands inside the good band on wide header cells and past its edge on the narrow
> interior cells of the same page. Measured in
> `benchmarks/omr-detector-scale/RESULTS.md`, which reconciles the two independent
> findings; the practical advice above is unchanged, and 512 remains far better
> than 2048.

So: any older number is suspect, including "100% pitch coverage" in
`benchmarks/omr-real-world/README.md` — which measures *coverage*, not correctness — and
the July probe's false-positive flood. Re-measure before building on one.

---

## 1. One-line percussion staves — DONE, 2026-08-28

**What it was.** `_group_into_staves` accepted only five-peak windows, so a percussion
part printed as a single rule produced **no `Staff` at all**, and every staff below it
carried a `staff_index` one lower than its true slot.

**What it cost, measured.** La Mer p.25 has 21 parts in one system, the twelfth being
Cymbales on one rule. The detector reported 20, so both harp staves, four divided violin
staves, violas, celli and basses — nine parts — were each read as their neighbour.

**What was not obvious.** Nothing about the row identifies a percussion staff: it is a
long inked row between the page's staves, and so is the single surviving line of a
five-line staff printed too lightly for the peak gates. That second case turned out to
be the **commoner** one — the first version of the rule fired on 4 of 10 sampled
Beethoven 5 pages, a score with no one-line parts, finding a clarinet staff and a
first-violin staff. The condition that carries the rule therefore asks the *page*, not
the peak list: is there a line-length run one or two staff spaces above or below? The
other four lines are printed whether or not the row pass saw them.

Over 47 pages of five scores it now fires 14 times, all on La Mer and Mahler 5; twelve
were rendered and read (Cymb., Trg., Becken, Gr. Tr., Kl. Tr.) and every one is a
labelled percussion part. On the 12-page Phase-1 corpus exactly one page moves.

**Where it lives.** `staff_detector._single_line_staff_rows`, evidence and the full
measurement in `benchmarks/omr-phase1-baseline/RESULTS.md`, ground truth for La Mer p.25
in `ground-truth.json`, regression in `test_pipeline.py::TestLaMerPage25`.

**What it deliberately does not do.** Percussion CONTENT is not read: one-line staves are
skipped by barline detection and cell extraction, because a cell is canonicalised by a
five-line span a single rule does not have, and a staff two spaces tall would vote
"barline" for every stem crossing it. The slots were the fix.

---

## 2. Key signatures — the cause was found, and it was neither of the two candidates

**Diagnosed 2026-08-28.** The thread asked whether this is a detection failure or a
reading failure, and said to check before building an inference layer. It is **neither**.

**What was actually wrong.** The staff's left edge was lost, so the header was cropped
out of every measure cell and nothing ever looked at it. `_staff_x_extent` read a fixed
±2px band around the middle line's nominal row; a printed line is 3px thick and wanders
2px on this material, so it left the band and the longest surviving run started hundreds
of pixels in — past the clef, past the signature. Nine of the twelve staves in Beethoven
5 p.15's first system began between x=274 and x=773 on a system whose staves all start
at x≈172.

Fixed (`omr: read the staff line where it actually is`): three of five lines must carry
ink within 0.35 staff spaces. Full measurement in
`benchmarks/omr-phase1-baseline/RESULTS.md`, including the correction it forces on the
earlier diagnosis — "28 runs with 11-space gaps" was a fact about the band width, not
about the page; the same staff is 2 runs with a 0.3-space gap when read properly.

**Consequences already banked.** Beethoven 5 p.15 clefs went from **0 of 23 read** (the
"19/19 DEFAULTED" this file reported) to **13 of 23**. Beethoven 5 p.10 now matches
hand-read ground truth on staves, systems *and* bars, and the two `xfail` tests that
recorded those gaps are retired.

**The other half of the thread is done too.** `key_signature_read` and
`key_signature_unread_reason` now distinguish "the signature here is empty" from "nothing
read this staff", which is what made a C minor page reporting 0/0 on every staff look
like a wrong answer rather than a silence. p.15 now says: read on 4 of 23 staves.

**What is left, and it is now sharply scoped.** Of the 19 unread staves on p.15:

- **8 have no clef.** The reader abstains there on purpose — a signature fitted against a
  guessed clef is a guess squared. This is the clef thread, not this one.
- **11 have a clef, and neither the detector's markers nor the CV locator found
  accidentals in the header.** The page plainly prints three flats on them.

**That bucket was worked, and two defects came out of it (2026-08-28).** The header
cell's staff lines were not where the print has them — off by 0.12 spaces on average and
0.47 at worst, against slots half a space apart — because the cell inherited the staff's
page-wide model and the header sits at the far left end where a line wanders furthest.
And a clef cut up by staff-line erasure stops anchoring the search, while its fragments
join the run ahead of the signature. Both fixed (`refine_staff_lines_in_cell`; the
locator's tail pass). Given true clefs, p.15 system 0 goes from 0 correct / 3 wrong to
3 correct / 0 wrong; end to end 0/1 wrong → 1 correct / 0 wrong, with clefs 15 → 16.
Five approaches were measured and ruled out along the way — see
`benchmarks/omr-key-signature/RESULTS.md`.

**What is left is the clef.** Two of p.15's string staves read treble where they are
alto and tenor, and a wrong clef picks a wrong slot table. That, plus the detector's
blindness to these flats at any confidence, is the whole of the remainder. The inference ideas below stay parked; there is no case
for guessing a signature from the music while the printed one is sitting unread in a
window nobody can read.

**Still true:** do NOT reuse per-staff Krumhansl-Schmuckler profile fitting. Measured and
noise — median margin between best and second-best signature 0.0000, 62 of 80 staves
under 0.01 (`benchmarks/omr-clef-key-fit-2026-08/findings.md`).

**Correction to an earlier note here:** this file previously said the two orchestral
ground-truth PDFs (`beet5-p2`, `pastoral-p2`) were gone from this machine. They are
not. They live under `tools/omr/training/data/imslp/`, which a git WORKTREE reaches
through a symlink — and the symlink, not the corpus, was missing. All three pages score,
and the whole benchmark is reproducible: `beet5-p2` 10 correct, `pastoral-p2` 9,
`wtc-p17` 10, none wrong. Create the link before measuring from a worktree.

---

## 3. Score-order prior — DONE, 2026-08-28

**Shipped** as `tools/omr/score_layouts.py`: a library of ten standard layouts and a
monotone alignment of a system's staves against them, with gaps on both sides and a
*continuation* move so one part can take several staves (two horns, a harp, divided
violins).

**What it buys.** Beethoven 5 p.15 — a scan with no text layer, where contextual
analysis used to stop at "no text layer — instrument identity unavailable" — now names
10 of 12 staves, 8 correctly: the whole wind and brass section, the timpani, and the
first violins. Measured against hand-read instrumentation on two pages
(`benchmarks/omr-score-order/`): **23 named and 23 right** with correct clefs, **12
named and 11 right** by position alone.

**`Tp.` is settled.** `instruments.AMBIGUOUS_ALIASES` declares the ambiguity and the
prior reads the answer off the position — timpani below the trumpets, trumpet where the
trumpets are, no opinion where it cannot see. The alias table is unchanged, so a page
the prior cannot read keeps the reading it had.

**Two things the measurement forced, worth carrying forward.**

- *Confidence is agreement, not margin.* The natural score margin between neighbouring
  traditions is ~0.05 per staff, on pages read perfectly — so a margin threshold rejects
  good answers. What separates a confident staff from a doubtful one is whether the
  plausible layouts agree about **that staff**. The strings at the bottom are the same
  in every tradition; the middle of the woodwind is where traditions differ.
- *Clefs choose the tradition.* Position alone picks the German large-orchestra layout
  for La Mer; the true clefs pick the French one, which is right. A bassoon in bass clef
  and a viola in alto are the anchors.

**What it must not do, and does not.** Identity deduced from position does not drive
clef correction. The two errors on Beethoven 5 p.15 are a viola and a cello whose clefs
are misread as treble and which the prior therefore reads as violins; letting it rewrite
those clefs would close the loop on its own mistake. It is written into the JSON as
`instrument_source: "score_order"` and stops there.

**Still open here.** The library is ten European layouts, and the prior inherits the
clef problem — which is now, after threads 2 and 4, the single thing most of this
project's remaining accuracy is waiting on.

---

## 4. The July "domain gap" conclusion — DONE, and it did not survive

**Re-measured 2026-08-28.** Same pages, same weights, same confidence, same cells;
only `imgsz` differs.

| Boléro p.1 (printed 3/4) | timeSig digits | clefs | noteheads |
|---|---|---|---|
| per-cell `imgsz` | **36** | **24 / 24** | 14 |
| `imgsz 2048` (July's setting) | 0 | 13 | 705 |

Mahler 5 p.1 tells the same story: 0 digits and 1 clef at 2048, **7 and 18** per cell.
The recovered digits are `timeSig3` / `timeSig4` at **0.94–0.95 confidence** in measure 0
of 18 staves, and the page reads 3/4 — correctly. End to end, dropping the threshold to
0.10 now moves Boléro's noteheads from 141 to 142, where July measured 372 → 1310.

**This includes the part this file said was not in doubt.** "Zero real time-signature
digits at conf 0.10, and mostly-treble clefs" was an `imgsz` artefact like the rest.

**What survives.** A domain gap for *specific classes on specific prints*, not a general
wall: Beethoven 5 p.15's key-signature flats are undetected at conf 0.25, 0.10 **and
0.05** alike, with the per-cell `imgsz` already in effect. That one is real, and it is
now the sharpest open detection question in the project.

> ⚠️ **Superseded 2026-08-29 — this was the fourth measurement to describe the
> instrument rather than the page.** The flats are NOT undetected. At conf 0.25
> the detector finds three of them in staff 0's header and labels them
> `accidentalFlat` rather than `keyFlat`; the key-signature path consumes only
> the `key*` classes, so they are discarded before anything positional runs. It
> is a class-ROLE mismatch, not blindness, and the role is contextual — the
> worst thing to ask a per-cell detector for. See
> `benchmarks/omr-keysig-blindspot-2026-08/findings.md`, which also records the
> fix being implemented, measured at −1 on the only ground truth, and held back.

Full measurement and a committed re-run script (July's was scratch):
`benchmarks/omr-detection-probe-2026-08/`. The July file carries a supersession banner,
and `docs/internal-consistency-checks.md` — which rests on the old conclusion — is
annotated.

---

## Also open, lower priority

- **Clefs are still defaulted on the densest pages.** The whole-pipeline rerun found
  **12/12 DEFAULTED** on handel-reduction p20 and **19/19** on Beethoven 5 p15 — not one
  clef read, so every pitch there rests on a positional guess. `clef_correction.py` can
  fix these given instrument identity, but those PDFs have no text layer, so it needs
  `vision_fallback=True` (`tools/omr/contextual.py`). Cheap to try: ~1c per system,
  bounded per work.
- **`benchmarks/omr-real-world/README.md` records no settings** — no DPI, no `imgsz`, no
  conf. That is why the May table could not be used as a baseline. Record settings with
  results from now on; `rerun_baseline.py` does.
- **Host `anthropic` SDK is 0.28.0 against a 0.116.0 pin.** The July upgrade only reached
  the Docker container. Structured outputs fail on the host; the margin-label pilot works
  around it with a venv.
- **The merge queue is empty as of 2026-08-28.** `reengraved-score-evaluation`,
  `recognition-over-detection` and `omr-clef-fusion-fix` are all on `main`, and PR #4 is
  merged. Note for next time: the dossier branch had drifted 41 commits behind and its
  merge needed three conflicts resolved by hand. Finished work costs more the longer it
  sits.

---

## Two method lessons that cost real time today

**1. A confident number can be measuring the wrong thing.** Twice:

- System grouping was first evaluated with a ground-truth-free proxy ("instrumentation is
  constant, so staves-per-system should cluster tightly"). It *rewards merging every page
  into one system* and duly reported success for a variant that was merging two systems
  into one on 6 of 12 pages.
- The replacement ground truth — counting systems off whole-page thumbnails — was also
  wrong, because at that scale a brass-to-strings bracket gap is indistinguishable from a
  system break. Five single-system pages were labelled as two.

**What worked: render the left margin and count the BRACKETS.** One bracket, one system.
More generally: render the thing and look at it before believing a metric.

**2. Record the settings with the result.** The May benchmark's missing DPI/`imgsz`/conf
made a three-month comparison unrecoverable, and cost a false regression report along the
way.
