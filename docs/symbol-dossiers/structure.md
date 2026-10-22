# Structure — the staff, the barline, the system, and the marks at the left edge

**Family: `structure`.** 2026-09-20. Research, not repair: nothing here was
changed, no arm was run, no page was transcribed. Every figure carries its file
and its n. Written against
`claude/integration-2026-09-18` at `4215c810`.

One `##` section per symbol, each with Sean's five questions. The family's
symbols, and what each one's state is in one line:

| symbol | in the 208-class space? | gathered? | decided? | reaches a consumer? |
|---|---|---|---|---|
| the five-line **staff** | `staff` (id 134, 207) — but read by CV, not the model | yes, 6 quantities | no — it is a measurement | 3 of 6 LIVE; `staff_extent` and `staff_skew` read by nothing |
| the **one-line percussion staff** | no | only as a `Staff` with `len(line_ys) < 5` | no | flag OFF; excluded from the barline vote |
| the **barline** | **NO CLASS EXISTS** | as a per-staff COUNT only | `measure_partition` (echoes the count) | yes — it is what a bar is |
| the **systemic barline** | no | `Q.SYSTEMIC_COLUMN` — **abstain-only, never observed** | no | no |
| `repeatDot` | yes (id 2, 138) | **no quantity names it** | no | no — `<repeat>` is a declared export gap |
| `segno`, `coda` | yes (id 3/139, 4/140) | **no quantity names either** | no | no |
| `brace` | yes (id 0, 136) | **no quantity names it** | `group_symbol` — decided from IDENTITY, not from the glyph | **no: the verdict is read by nothing** |
| the **family bracket** | **NO CLASS EXISTS** | `Q.BRACKET_BLOCK` (inferred from barlines) | `staff_group` | yes, additively |
| the **system** | n/a | `Q.GAP_BRIDGING` (a page-level boolean) | `system_membership` | **no: the verdict is read by nothing** |
| the **measure cell** (as a frame) | n/a | `Q.CELL_BOX`, `Q.CELL_STAFF_SPACE` | no | yes — the arc merge, the duration reader |
| `ottavaBracket` | yes (id 135) | **no quantity names it** | no | no |
| `ledgerLine` | yes (id 1) | `Q.GLYPH_LADDER` | inside `glyph_owner` | yes |

**The derived tools are the authority for that table, not this file.** Run
them: `python3 -m tools.omr.staged.reach`,
`python3 -m tools.omr.staged.gather_coverage`,
`python3 -m tools.omr.staged.inventory`,
`python3 -m tools.omr.staged.capture`. Every count above and below was read off
one of those four on this tree.

---

## 0. What this dossier starts from — and the one place it disagrees

Four documents already answer part of Sean's five questions for this family.
They are cited in place below rather than re-derived; this section says what
each contributes and where the per-symbol reading **adds to** or **disagrees
with** it.

| prior document | what it already settles for `structure` |
|---|---|
| [`docs/position-grammar-confusables-2026-09-04.md`](../position-grammar-confusables-2026-09-04.md) §2 | **Q1, organised by MARK.** VERTICAL STROKE (stem vs barline) and HORIZONTAL STROKE (tenuto vs ledger) are this family's two entries. §4's R1–R6 are the design rules behind Q2. §5 already names `repeatDot → repeat barlines` with its hook. |
| [`benchmarks/omr-family-positions-2026-09/FINDINGS.md`](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md) + `tools/omr/staged/positions.py` + `capture.py` | **Q3.** Eleven families got a symbol-specific position quantity; **ten producers, no consumers**, `OMR_FAMILY_POSITIONS` default OFF. And Sean's warning on what such a fact is for. |
| `tools/omr/staged/ASSUMPTIONS.md` **A-GROUP-1 … A-GROUP-4** | **Q4/Q5 for the bracket and the brace** — the all-zero abstention, the brace-is-an-instrument rule, additive-never-overruling, and the silence on two-staff systems. |
| [`docs/exploration-what-is-on-the-page-2026-09-09.md`](../exploration-what-is-on-the-page-2026-09-09.md) §A, §C2 | the traversal-order axis (`segno`/`coda`/`repeatDot`/no `volta`), `ottava` as the highest damage-per-instance miss, and **measure numbers as an independent witness on `measure_partition`**. |

### ⚠️⚠️ THE DISAGREEMENT: "VERTICAL STROKE — stem vs barline (already solved; the precedent)"

§2 of the position-grammar doc files the barline under **already solved**, on
this ground:

> *"Nothing but a barline runs from the top of the upper staff to the bottom of
> the lower — a fugue's stem crosses the brace gap and scores 1.00
> connectivity, which is why the span test exists (`_spans_system`)."*

**That is true, and it is true of about 8% of the barlines on a conductor's
page.** Three checks on this tree:

1. **`_spans_system` is called at exactly ONE site** — `measure_extractor.py:786`,
   inside `if n_staves < 3:`. On a system of three or more staves it never
   runs. The discriminator there is `_intersystem_connectivity` (filter at
   **≥ 0.4**, rescue at **≥ 0.7**), which asks *what fraction of the gaps are
   inked*, not *does it span*. MEASURED HERE (grep + read on this tree).
2. **The span test's own evidence is n = 4 braced piano systems of WTC I**
   (`SPAN_MIN_INK` comment: every real interior barline 1.00, every stem and
   false candidate ≤ 0.52). Nothing orchestral.
3. **It CANNOT hold on a conductor's page, by a convention this repo itself
   measured.** `[C58]` — *interior barlines STOP at instrument-family
   boundaries* — is what `OMR_BRACKET_COLUMNS` is built on. A real orchestral
   interior barline therefore does **not** run from the top staff to the
   bottom one, so a rule saying *"only a barline does"* has nothing to fire on.

And Sean's own form of the rule — *a barline's two ends sit ON the outer staff
lines, a stem's do not* — reads **0 of 19 print-settled barlines in the CELL
frame at every tolerance**, because a measure cell is the staff plus 4 + 4
spaces and clips the ends. In the PAGE frame it reads **11–13 of 19 against 0
of 63 stems** — but that sample is drawn from marks that CROSS staves, which
`benchmarks/omr-barline-height-2026-09` counts as **7 of 82 Litolff barlines
and 4 of 49 Breitkopf ones**.

**So the correction is:** the *mark-alphabet* question is solved for the
system-crossing barline and for the braced grand staff. **The ordinary interior
barline on one staff of an orchestral system has no print-adjudicated
discriminator at all** — it is separated today by a vote plus a connectivity
threshold, and Sean's endpoint rule is `0 of 19` against it because none of the
adjudicated cases is that kind. The position-grammar doc is not wrong; its
"already solved" is scoped to the case its own precedent came from, and the
scope is not stated.

### The family-wide answer to Q3, from `capture.py`

⚠️ **NOT ONE SYMBOL IN THIS FAMILY APPEARS IN `capture.py`'s TABLE.** Run on
this tree it grades 14 families — articulation, clef, direction, dynamic,
fermata, key, note, ornament, rest, slur, tie, time, tuplet, wedge — and the
structure marks are absent for **two different reasons that must not be
pooled**:

* **`staff`, the barline, `stem`, `beam`, `ledgerLine`** have quantities but no
  `shape` row in `capture`'s sense — *"an observed quantity carrying the
  detector's confidence"* — because they are CLASSICAL-CV readings and carry no
  detector score. They are invisible to that table by construction, not by
  omission.
* **`brace`, `repeatDot`, `segno`, `coda`, `ottavaBracket`** have **no quantity
  at all**, so they are absent from `capture` *and* absent from the eleven
  families `positions.py` gave a position to. They are named only by
  `gather_coverage` §5's **NO QUANTITY NAMES IT** list.

So the honest Q3 answer for the whole family, before any per-symbol detail:
**the eleven-family position sweep did not reach a single structure symbol**,
and the one structure-adjacent position fact that DOES exist
(`Q.METER_GLYPH_POSITION`) was measured **on a broken barline** — see the
barline's Q1 below.

---

## `staff` — the five ruled lines

Five parallel horizontal rules; the grid every vertical position in the score
is measured against. Produced by `tools/omr/staff_detector.detect_staves`
(classical CV, row ink projection), **not** by the detector, even though
`staff` is class 134 and 207 in the 208-class space. Six staged quantities
carry it: `Q.STAFF_LINES` (5 y positions, page px), `Q.STAFF_SPACING` (page
px), `Q.CELL_STAFF_SPACE` (one space in a CELL's own canonical frame),
`Q.STAFF_EXTENT` (`x_start, x_end`), `Q.STAFF_SKEW` (measured wander),
`Q.SYSTEM_STAFF_COUNT`.

### 1. What sets it apart — and what it is confused with

The fact that identifies a staff is **continuity, not ink density**. A staff
line is one unbroken stroke over its whole length; everything else that fills a
horizontal row of a page is made of many short runs.

| confused with | how it fools the detector | the discriminator | grade |
|---|---|---|---|
| **a paragraph of justified body text** | five text baselines are as evenly spaced as five staff lines, and a justified row clears the line-length gate | ink RUNS per staff-space along the row: music tops out at **1.39**, text starts at **2.02**, medians 0.017 and 2.59, over **310 staves on 7 scores and 20 text blocks** | MEASURED HERE — `staff_detector._line_ink_runs_per_space` docstring; `[C-none]` (no registry entry) |
| **five lines of FIVE DIFFERENT staves** | on a pocket score the wind staves print lighter than the strings, a single page-wide prominence floor rejects most wind rows, and the one survivor per staff is evenly spaced | the page's own structure: a strict pass, then `_has_the_rest_of_a_staff` | MEASURED HERE — Beethoven 5 p.10, spacing **142.5 px** read as a staff against the true **15.8**; the page reported 18 staves where it prints **22**, `benchmarks/omr-phase1-baseline/RESULTS.md` |
| **a beam**, taken as the staff's end line | a beam is at staff-line pitch and runs the width of the group | end-line THICKNESS ratio ≥ `MISFIT_THICKNESS_RATIO` × median (Brahms contrabass: **18 px against 5**) | MEASURED HERE — `staff_detector._refit_misaligned_group` |
| **ledger lines**, taken as the staff's end lines | printed at staff weight, so thickness cannot see them | end-line COVERAGE: Brahms Violin 1's false end lines covered **4% and 6%** of the staff width at a thickness ratio of 1.8 | MEASURED HERE — same function |
| **a page border / title rule / footer** | one long inked row | only rows BETWEEN the first and last accepted staff line are candidates | MEASURED HERE — `_single_line_staff_rows` |
| **a tenuto, or a ledger line** | all three are horizontal strokes at or near lattice pitch | `position-grammar-confusables` §2 **HORIZONTAL STROKE**: a ledger line lies ON the extended half-space lattice, continues a ladder run, and **matches the staff's own measured line thickness**; a tenuto sits OFF the lattice about a space beyond its head with nothing centred through it | the discriminators are named there; ⚠️ see below for the one that is unread |

⚠️⚠️ **AND ONE OF THOSE DISCRIMINATORS IS RECORDED AND READ BY NOTHING — this
dossier's one ADD to the HORIZONTAL STROKE entry.** That entry says the
measurements *"already exist in the pipeline's JSON"* and names **the staff's
own measured line thickness, "recorded per staff since the frame-retention
work."** It is: `measure_line_geometry` returns it and `gather_geometry:133`
files it as `Q.STAFF_SKEW`'s `thickness_px` detail. **`reach` reports
`Q.STAFF_SKEW` UNREAD on this tree** and `reach.KNOWN_GAPS` records it as an
OPEN FINDING.

⚠️ Be precise about what is missing: `staff_line_removal` measures line
thickness AGAIN, per cell, from the cell's own ink — deliberately, because it
varies **0.06–0.31 spaces across the corpus** — so a thickness figure does
exist where a ledger/tenuto rule would run. What does not exist is any
comparison: `wiring.KNOWN_GAPS` records the page-level one as *"a second
reading that nothing compares against the first"*, and **no rule anywhere reads
either one to name a horizontal stroke.** That matters because the doc names
the live risk: *"a tenuto misread as a ledger feeds false rungs into
attribution, and the reverse starves it."*

⚠️ **Ink COVERAGE is the obvious discriminator and it does not work.** Heavy
notation ink interrupts a real staff line, so genuine staves in Beethoven 5 and
La Mer fall to **0.62–0.70** coverage, directly on top of body text at
**0.62–0.72**. (MEASURED HERE, `_line_ink_runs_per_space` docstring.) This is
worth carrying: the quantity that separates is *how the ink is arranged*, not
how much of it there is.

### 2. Best method: YOLO / CV / other

**Classical CV, and the repo has measured why the alternative is worse.** Two
independent results:

* Erasing the staff lines before handing the page to YOLO costs **7–13 pooled
  reading points and up to a third of the noteheads** — Brahms 1 0.876 → 0.805,
  Mozart 41 0.921 → 0.793, notehead recall on Mozart 41 falling to **0.642**;
  and YOLO's `beam` detections go 46 → **105** at precision 0.783 → 0.343, on
  staff-line residue. MEASURED HERE, n = 2 engraved works,
  `docs/scope-cv-hairpin-detection-2026-09-04.md` §1b.
* The shipped arrangement is therefore *erase for the CV consumer, bound the
  search for everyone else, never erase for the detector* — and `staff` is in
  the class space but nothing reads a `staff` detection: `FAMILY_TO_Q` maps the
  family to `STAFF_LINES`, which the CV reader produces.

### 3. Where on the page the deciding information lives

Three places, and they are in **three different frames**, which is the standing
hazard for this family:

| fact | where it lives | frame |
|---|---|---|
| the five line positions | the page raster, row-projected over the whole page width | PAGE px (`Q.STAFF_LINES`) |
| line spacing | the same, per staff | PAGE px (`Q.STAFF_SPACING`) |
| the staff space INSIDE a measure cell | the cell's own canonical raster | CELL canonical px (`Q.CELL_STAFF_SPACE`) |

⚠️ **`Q.CELL_STAFF_SPACE` is not a constant and assuming it is would be wrong
on half the cells of a conductor's page.** The nominal is
`CANONICAL_STAFF_SPAN_PX / 4 = 100`, but `_upscale_to_canonical` scales a
too-wide cell by WIDTH, so its staff stays smaller. MEASURED HERE: **1,167 of
1,180 Litolff cells sit at exactly 100 and 13 do not**; on Breitkopf only
**514 of 817** do (`docs/RESUME-HERE-2026-09-20.md` §5.2 — where the manager's
own probe used a flat 100 and had to be corrected). A flat constant is right
98.9% of the time on one plate and 63% on another.

⚠️ **The lines are not straight on a scan.** A scanned staff tilts or bows
**8–17 page px (0.3–0.65 staff spaces) across its width**, measured over 7
staves of 5 editions; `Staff.line_ys` is five ideal rows and
`_build_measure_cell` copies those five constants into every cell, so an
end-of-staff cell's grid can be **half a space** off the print — which is the
distance from a line to the space beside it. `OMR_CELL_LINE_TRACE` (default ON)
slides the five rows as ONE RIGID COMB onto the ink beneath each cell.
MEASURED HERE, `benchmarks/omr-cell-grid-tilt-2026-09/FINDINGS.md` §1 (8 of 9
flagged labels reproduced) and `WIDENED_PRICING_2026-09-04.md` (pooled
0.8387 → 0.8345, **−233 edits, −217 of them on exactly the three tilted rows**;
the widened pool holds **8.6%** of cells past the parity-flip line against the
old corpus's 0.4%). `[C8]`.

⚠️ **Per-line tracing ALIASES and was refused.** On Dvořák 9 p.8 staff 4 the
true displacement is **−0.55 spaces**, past half a spacing, so stored line *k*
matches printed line *k+1*; the per-line matcher answered **+0.32** — a
correction 0.87 spaces the wrong way. A five-line comb cannot alias inside one
spacing. MEASURED HERE, same FINDINGS.

### 4. Stage by stage

| stage | what happens | verified |
|---|---|---|
| **GATHER** | `gather_geometry` (`gather.py:106-134`) observes `STAFF_LINES`, `STAFF_SPACING`, `STAFF_EXTENT`, `STAFF_SKEW` per staff; `gather_measures` observes `SYSTEM_STAFF_COUNT` and `STAFF_ORDINAL`; `gather_notehead_positions` observes `CELL_STAFF_SPACE` | `gather_coverage` §1 |
| **ADJUDICATE** | `adjudicate_system_staff_count` (#4) and `adjudicate_staff_ordinal` (#3) — **both echo the gathered row**: `Ruling(value=int(rows[-1].value))`. There is no decision about whether a staff IS a staff. | `adjudicators/structure.py:52-84` |
| **EVALUATE** | nothing. No consequence reads the staff grid. | `grep Q.STAFF_ tools/omr/staged/consequences.py` → nothing |
| **INFER** | nothing. | `tools/omr/staged/inferences.py` |
| **EXPORT** | `staged/export.py:404-415` reads `STAFF_SPACING` and `STAFF_LINES` **as observations, not verdicts**, for the arc merge. `<staff-lines>` is never written (in `NOT_NOTATION` as `staff-details`). | `export_coverage.py:282` |

⚠️⚠️ **`Q.STAFF_EXTENT` and `Q.STAFF_SKEW` are gathered and read by NOTHING.**
`reach` reports both UNREAD (run on this tree). `gather_coverage` files them
under *GATHERED (observed)*, i.e. as healthy — which is why the gap needed a
fifth instrument to see. `reach.KNOWN_GAPS` records both as **OPEN FINDINGS,
NOT EXCUSED**. The sharp form: **the measured tilt that `OMR_CELL_LINE_TRACE`
exists to correct is recorded on the record and never consulted by any stage**
— the correction happens in `measure_extractor`, upstream, and the number
travels no further.

### 5. Abstain or best-guess — and what leans on this

**(a) Can it abstain?** Partly, and it is the strongest abstention in the
family. `gather_geometry` files `ABSTAIN.NO_STAFF_GEOMETRY` for a staff with
fewer than two lines (`STAFF_SPACING`) and for a staff whose wander was never
traced (`STAFF_SKEW`) — and the comment says why in terms: *"DECLINED, not
zero. A staff whose wander was never traced and a staff measured to be
perfectly straight are different facts."* `Q.CELL_POSITION_BASIS` is the
same discipline one level down: a cell with no five-line grid files ONE
refusal for the cell rather than one per mark.

**What CANNOT abstain: the staff's existence.** `detect_staves` returns a list.
A window that locked onto the wrong ink either gets slid back or is emitted as
a staff; there is no `Q` for *"this might not be a staff"*, no confidence on
`Q.STAFF_LINES` (it is `CLAIM.MEASUREMENT`, `score=None` by design), and no
decision that could refuse one. The 22-vs-18 Beethoven fault above was a
**silent** staff count error that held a green test assertion in place.

**(b) What leans on this, and is it independent?** Everything. The staff grid
is the denominator of the whole project:

| leans on the staff grid | how |
|---|---|
| every **pitch** | `notehead_staff_position` = `(y_center − top_y) / half_step` off the cell's grid |
| every **clef** reading | `Q.CLEF_POSITION`, same grid |
| every **key signature** | `Q.KEYSIG_RUN_POSITION`, same grid |
| every **rest** slot | whole vs half rest differ ONLY in which line they touch |
| the **barline** | `BARLINE_MIN_HEIGHT_FRAC × staff_span` — the gate is a fraction of the staff |
| the **system** | gaps are measured between staff bottom and staff top |
| every constant in **staff spaces** | `Q.STAFF_SPACING` / `Q.CELL_STAFF_SPACE` is the unit |

⚠️ **The independence answer is bad, and it is bad in the way this repo has
already named.** Every one of those readers takes its ruler from the same CV
pass over the same raster. A page whose staff detection is degraded is a page
where the pitch, the clef, the rests and the bars are all read against a
displaced grid — and none of them can act as an umpire over the others,
because they share the fault. This is *the bars are not an independent umpire
over a bad reading* at the level of the coordinate system rather than of one
decision.

**The one genuinely independent witness that exists is the DOSSIER** — clef,
key, meter and measure count from a MusicXML file, `source_kind` not `page` —
and it does not fall silent when the raster does. It is also **not wired into
the staged path**: `reach.KNOWN_GAPS[Q.DOSSIER_FACT]` records that the staged
CLI has no `--dossier`, so nothing ever supplies one.

**Evidence grade:** run-counts and tool output MEASURED HERE on this tree;
tilt figures MEASURED HERE (n = 7 staves / 5 editions for the residual, 20-row
scan gate for the price); the body-text separation MEASURED HERE (n = 310
staves / 7 scores / 20 text blocks); line thickness as a *number*
LITERATURE only (`[L7]`: Bravura 0.13, applications 0.08–0.16 — a 2× spread,
never measured on a plate here).

---

## The one-line percussion staff

A single ruled line standing among five-line staves, carrying unpitched
percussion. **It is not in the class space and there is no detection for it.**
`staff_detector._single_line_staff_rows` finds it; `OMR_ONE_LINE_STAVES`
(default **OFF**) decides whether it becomes a `Staff` at all.

### 1. What sets it apart — and what it is confused with

⚠️ **It cannot be found the way the others are, and the reason is structural**:
it has no internal spacing to calibrate against. One inked row on its own is
also what a page border, a rehearsal rule, a trill line, a hairpin and *the
single surviving line of a badly printed five-line staff* look like.

What identifies it is **the company it keeps** — a rule as long as the page's
own staves, standing between them, with nothing else at staff-line pitch
anywhere near it. Five tests, each counted apart
(`staff_detector.py:500-590`):

| test | rejects |
|---|---|
| between the page's first and last staff line | borders, titles, footers |
| ≥ `SINGLE_LINE_CLUSTER_WIDTH_FRAC` of the longest candidate | trill lines, hairpins, text fragments |
| no other lone row within `SINGLE_LINE_CLEARANCE_SPACES` | one broken five-line staff read as two percussion rules |
| ≥ `SINGLE_LINE_MIN_WIDTH_FRAC` of the median staff width | short rules |
| `_has_the_rest_of_a_staff` is False | a five-line staff whose other four lines the peak gate lost |

### 2. Best method

**Classical CV, by elimination** — there is no class to train and a box round a
single rule is the thin-line case YOLO is structurally bad at.

### 3. Where the deciding information lives

**Not on the mark. Beside it.** Every one of the five tests above is a
comparison against the *page's other staves*: their x-window, their median
width, their line pitch. This is the clearest case in the family of a symbol
whose identity is entirely contextual.

### 4. Stage by stage

**There is no quantity and no decision.** A one-line staff either becomes a
`Staff` with `len(line_ys) == 1` (flag ON) or does not exist (flag OFF, the
default). Downstream it is then handled by **exclusion**:

* `measure_extractor.detect_barlines:558` drops it from the barline vote —
  *"a staff two spaces tall answers 'there is a barline here' for any stem that
  crosses it"* — and counts the exclusion
  (`n_one_line_staves_excluded_from_barline_vote`).
* `positions.py:581-589` files `Q.CELL_POSITION_BASIS` ONCE per cell:
  *"a one-line percussion staff has no grid at all"*.
* `_gather_bracket_blocks` refuses systems under 3 staves.

### 5. Abstain or best-guess — and what leans on this

**(a)** The flag IS the abstention, and it is a page-wide one. Off, the page
is read as if the staff were not printed.

**(b) What leans on it: the staff ORDINAL of every staff below it.** This is
the sharpest consequence in the family. `_group_into_staves` accepts only
five-peak windows, so a missing one-line staff makes **every staff below it
carry a `staff_index` one lower than its true slot** — which becomes a wrong
instrument, a wrong clef and wrong pitches for the whole lower half of the
system (`_single_line_staff_rows` docstring, ASSERTED as a mechanism, and
`benchmarks/omr-part-join-2026-09` measured the arity consequence: Mahler p2's
21-entry lineup against our 17 parts, **4,815 symbol rows / 32.1% of the
unassessable mass** in cause B).

**Measured reach**: **81 staves in 13,302 (0.61%)** across 702 library pages,
and they are real — 72 of 81 on a work independently recorded as scored for
unpitched percussion, 4 adjudicated false by eye
(`benchmarks/omr-one-line-staves-2026-09/FINDINGS.md`). Priced: **engraved
−144 edits** (`dvorak-sym9-mvt4` 239 → 95, `entire staff` 42 → 0),
**scan page-normalised −212**, **scan as the gate scores it today +65**.

⚠️ **It still reads no percussion NOTES** (§6 of that FINDINGS), and a
labeling batch cut with the flag ON contains cells a batch cut without it does
not, while `cells.json` records no flag — an unfixed hazard to irreplaceable
human work.

**Evidence grade:** census MEASURED HERE (702 pages, n = 81); prices MEASURED
HERE (11 engraved works, 20-row scan gate); the ordinal-shift mechanism
ASSERTED (stated in the docstring, never isolated).

---

## The barline

A thin vertical rule dividing bars. **There is no barline class in the 208-class
space** — checked, not assumed:
`python3 -c "from tools.omr.training.deepscores_classes import *; [c for c in DEEPSCORES_V2_CLASSES if 'barline' in c]"` returns `[]`, and the same over the
208-name catalog (`data/user-labeled/catalog.yaml`) returns `[]`. It is found
entirely by classical CV, in `tools/omr/measure_extractor.py`.

⚠️ `yolo_detector._CATEGORY_MAP` contains five barline keys (`barline`,
`barlinesingle`, `barlinedouble`, `barlinefinal`, `barlineheavy`) mapping to a
`barline` category. **None of them can ever fire**, because no class of that
name exists. The mapping is dead code that reads like coverage.

### 1. What sets it apart — and what it is confused with

**Start from the prior answer.**
`docs/position-grammar-confusables-2026-09-04.md` §2 **VERTICAL STROKE** files
this as *already solved; the precedent*: nothing but a barline runs from the
top of the upper staff to the bottom of the lower. **§0 above shows that is
scoped to the braced grand staff and the system-crossing barline — roughly 8%
of the barlines on a conductor's page — and that `_spans_system` runs on
`n_staves < 3` only.** This section is about the other 92%.

Sean's own rule is the right one and it is the model case for this whole
dossier: **a barline's two ends sit ON the outer staff lines; a stem's do
not.** That is a PAGE-frame fact, and the cell cannot see it.

What the shipped reader uses instead is three shape gates inside the staff
band (`_detect_barlines_in_window`):

| gate | value | rejects |
|---|---|---|
| height ≥ `BARLINE_MIN_HEIGHT_FRAC × staff_span` | **0.80** | note stems |
| width ≤ `BARLINE_MAX_WIDTH_LINESPACINGS × spacing` | **0.7** | accidentals, chord clusters, bled ink |
| aspect `h/w` | **≥ 8.0** | anything merged with a neighbour |

| confused with | measured | grade |
|---|---|---|
| **a note stem** | thickness alone cannot separate them: Bravura `thinBarlineThickness` **0.16** against `stemThickness` **0.12**. Height and position must. | LITERATURE `[L74]` |
| **an aligned column of chord stems** | on Beethoven multi-staff systems, 2 columns with **8–9 of 11** staff votes had inter-staff connectivity **0.1–0.3** — stem columns that passed the vote | MEASURED HERE, `_intersystem_connectivity` docstring |
| **a long stem in a fugue** | WTC I p.6 has one at x = 3018 scoring **1.00 connectivity** and it is not a barline — which is why `_spans_system` exists on top | MEASURED HERE, `_spans_system` docstring |
| **a time-signature digit pair** | Litolff p.62's printed `3/4` that this project cited for weeks is **ONE BARLINE BROKEN INTO TWO FRAGMENTS** at the cell's left edge, read as `timeSig3` + `timeSig4`. ⚠️⚠️ **And the family-position fact does NOT refuse it** — measured over 10 rows on that page: the staff-11 pair reads `half` = **upper** + **spans**, i.e. roughly one fragment in each half of the staff, at **4.16 and 4.34 steps tall against a real digit's ~4**. *"Neither the `half` field nor the height separates them from a printed numerator and denominator."* | MEASURED HERE — `benchmarks/omr-family-positions-2026-09/FINDINGS.md` §4, n = 1 page / 10 rows; `[C34]` refutation |
| **a false `timeSig4`** | five of them fired on barline fragments and shipped a 2/4 page as common time at **390 bar-check failures** | MEASURED HERE, `class_aliases.py:28` |
| **a bracket** | a bracket is ~3× a thin barline's ink (`bracketThickness` 0.5 vs 0.16) and is the one non-barline object that spans a whole system — **2 of 5 held editions print exactly that** | LITERATURE `[L75]` + MEASURED HERE `[C60]` |
| **scan damage**, vs a dashed barline | a dashed barline's dashes and gaps are REGULAR at ~2:1 (`dashedBarlineDashLength` 0.5 / `GapLength` 0.25). **A regularity test on a broken vertical run has never been tried here.** | LITERATURE `[L78]`, untested |

⚠️⚠️ **THE PAGE FRAME IS WHAT MAKES SEAN'S RULE WORK, AND IT WAS MEASURED ON
2026-09-20.** `benchmarks/omr-vertical-runs-page-2026-09/FINDINGS.md`, against
blind print verdicts, both publishers pooled:

| tolerance (staff spaces) | 0.15 | 0.25 | 0.40 | 0.60 | 1.00 |
|---|--:|--:|--:|--:|--:|
| barlines fire — **CELL** frame (of 19) | 0 | 0 | 0 | 0 | 0 |
| barlines fire — **PAGE** frame (of 19) | 2 | **11** | **12** | **13** | 18 |
| stems fire — CELL frame (of 58) | 0 | 0 | 0 | 0 | 6 |
| stems fire — **PAGE** frame (of 63) | 0 | **0** | **0** | **0** | 11 |

**Between 0.25 and 0.60 staff spaces the rule fires on 11–13 of 19 barlines and
on ZERO of 63 stems.** In the cell frame it was 0 and 0 — no signal in either
direction, because a measure cell is the staff plus 4 + 4 staff spaces and a
barline taller than that has its ends clipped BY the crop.

⚠️ **Read the STEM column, not the barline one.** The barline sample was drawn
from a `too TALL` bucket, so *"these marks are tall"* is true by construction.
The decisive, non-circular result is the empty false-positive side.
⚠️ **The NARROW form (one staff) is still 0 of 19 in both frames** — none of
the adjudicated barlines sits on exactly one staff, so this lane establishes
nothing about the commonest kind. A sibling lane sizes it:
`benchmarks/omr-barline-height-2026-09` counts **82 Litolff barlines of which 7
cross every gap** and **49 Breitkopf ones of which 4 do** — roughly **8%**.

### 2. Best method: YOLO / CV / other

**CV, and it is design rule R1 rather than a fresh finding.**
`position-grammar-confusables` R1: *"The class space is frozen at 208; classes
are priors, not verdicts. No `curvedLine` or `dot` superclass in the model: an
nc change silently re-initializes the classification head (the Phase 3.4
collapse)."* The measured collapse is **F1 cratered to 79.3%**
(`benchmarks/omr-phase3.4b/comparison-trained-v4.md`). `NOTES.md` item 5
records the two remaining routes: post-process the CV barline by inspecting the
pixel pattern either side, or re-introduce YOLO classes once 200+ examples per
type exist. ⚠️ R6 applies to the second route — *never tune a positional
threshold on one edition* — and `omr-barline-height-2026-09` is the instance:
Sean's own reach convention is TRUE on Litolff and ABSENT on Breitkopf.

⚠️ **A third method is now live and named: a PAGE-frame vertical-run reader.**
`tools/omr/vertical_runs_page.py` (2026-09-20) emits vertical ink with page
coordinates at **0.0–0.1 s/page**, cross-controlled at **1,920 of 1,920** and
**2,305 of 2,305** against `detect_stems`'s accepted strokes. It **names
nothing** and **no adjudicator reads it**.

⚠️ **The cell population is not bigger, it is double-counted**: 6,128 cell
candidates against 3,465 page runs on Litolff pp.1-4 — a mark in a gap is a
candidate in BOTH neighbouring cells. *The page frame is the first count of
vertical marks on these pages that is a count of MARKS.*

### 3. Where the deciding information lives

**Four places, in ascending order of what they cost:**

1. **Inside the staff band** — the shape gates. Cheap, per staff, already live.
2. **In the inter-staff GAPS** — `_intersystem_connectivity`: is the column
   inked where it crosses the whitespace between staves? Separates stem
   columns from real barlines on orchestral pages, **and inverts on open
   scores** — Nottebohm p.31: 4/4 votes and **0.00 connectivity on every
   barline of every system**, so the filter would throw all of them away. The
   shipped rule asks the system which kind it is before letting connectivity
   filter.
3. **Across the whole system height** — `_spans_system`, the *weakest band*
   of 8. Measured over four braced WTC systems: **every real interior barline
   1.00, every stem and false candidate ≤ 0.52.** The band-by-band minimum is
   what makes it a SPAN test: a column half-inked over its whole length
   averages the same as a barline broken in the middle.
4. **At the ENDS** — Sean's rule, §1. Available for the first time in the page
   frame; **nothing consumes it**.

⚠️ **A barline has NO position quantity, and the family-position sweep did not
reach it.** `positions.py` gave eleven families a symbol-specific staff-relative
fact; the barline is not one of them, and `capture.py`'s table does not list it
(§0). The nearest thing that exists is `Q.METER_GLYPH_POSITION` — which was
measured **on barline fragments** and does not separate them from a printed
meter. So Sean's standing warning applies to this symbol with an instance
attached: *"position is an option for helping us determine something but will
rarely be a clear rule that determines by itself… 2 numbers not connected, one
in the upper half and one in the lower half, could be a time signature. Due to
ink bleed they may appear connected."* On p.62 it is a barline, and the
geometry says meter.

⚠️ **The x is not constant down the page.** One barline's x drifts
**monotonically up to 40 px** between the top staff and the bottom on the
Litolff Beethoven 5 — more than 3× the clustering tolerance — so three real
barlines that had passed the vote (9, 12 and 10 of 12 staves) scored
**0.27–0.36** against a 0.40 gate and were discarded. `_barline_x_at` fits the
line to the staves that observed it and probes along the fit. ⚠️ **Theil-Sen,
not least squares**: a note stem near the column votes too, and two such among
nine dragged a least-squares fit far enough off that a real barline still
scored 0.36 with the slope modelled. Page 1 then read **17/17 barlines, 0
false, 16 measures of 16**. MEASURED HERE, `[C57]`.

⚠️ **And position does not predict reach on every plate.** Sean's convention
*"a barline goes all the way through a system at the beginning and end but not
necessarily in the other bars"* is **true on Litolff (7 of 7 first, 0 of 68
interior) and ABSENT on Breitkopf (median share 0.923 at all three positions,
with four INTERIOR barlines crossing every gap while its FIRST crosses none —
the ordering inverted, not missing)**. MEASURED HERE,
`benchmarks/omr-barline-height-2026-09/FINDINGS.md`, n = 2 publishers, 8 pages.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER** | ⚠️ `gather_measures` (`gather.py:232-240`) observes `Q.BARLINE_COLUMN` as **`last + 1` — the COUNT of cells cut for this staff**, with `note="n_cells cut for this staff"`. Not positions. Not types. The quantity's own comment in `record.py:353` says *"a fitted barline, x per staff"*, which the code does not do. |
| **ADJUDICATE** | `adjudicate_measure_partition` (#2) reads `Q.BARLINE_COLUMN` and returns `int(rows[-1].value)` — it echoes the count. Abstains `no_barline` where there is no row. |
| **EVALUATE** | nothing reads the partition as a consequence. |
| **INFER** | `inferences.collapse_duration_to_barline` uses the barline as *a system-wide instant* — a note with no next onset in its bar runs to the barline, and a neighbouring staff at the same column has measured the same gap. Behind `OMR_INFER`, **default OFF**. |
| **EXPORT** | `staged/export.py:381` builds one `StaffRun` per `MEASURE_PARTITION` verdict; `_document_bar_offsets` uses a system's bar count for document-wide measure numbering. **No `<barline>` element is ever written** by either exporter. |

⚠️⚠️ **`Q.BARLINE_COLUMN` BEING A COUNT IS LOAD-BEARING AND HAS ALREADY COST
AN ESTIMATE.** `ASSUMPTIONS.md` A-DUR-6 named the double barline as *"the cheap
independent reader"* for a meter change; checked 2026-09-09, it is not — the
quantity is a per-staff count of cells and **no barline-type classification
exists anywhere**. The correction is recorded in place.

⚠️ **`<barline>` is a declared export gap and it is the right shape of entry.**
`export_coverage.KNOWN_GAPS["barline"]` rolls up `<bar-style>` and `<repeat>`
as children: *"A repeat cannot be written without its bar-style anyway."*

### 5. Abstain or best-guess — and what leans on this

**(a) Can it abstain?** `adjudicate_measure_partition` abstains
`no_barline` when no row exists. But the CV reader itself does not abstain in
any useful sense — it returns a list of accepted columns, and a page whose
barlines it half-reads produces a confident wrong bar count. The acceptance
rules are a tiered vote (`n_staves ≤ 2` both must agree, …, `> 12` just 50%
with a floor of 5) plus a connectivity filter plus a rescue prong; each tier is
a threshold with no recorded abstention branch.

⚠️ **The one place the record CAN say "the staves disagree" is at EXPORT, and
it refuses correctly.** `_document_bar_offsets` names three conditions —
`no_staff_decided_its_bar_count`, `staves_disagree_about_the_bar_count`,
`a_part_holds_two_runs_on_one_system` — and on any of them returns the WHOLE
FILE to per-part numbering, because *"a file numbered document-wide up to the
bad system and part-wise after it is a file in which `<measure number=N>`
means two different things with nothing saying where the boundary lies."*
⚠️ **A majority vote is available there and is REFUSED** — nine staves reading
4 against one reading 3 is INFER-stage work.

**(b) What leans on the barline, and does it fail on the same pages?**
Everything that is per-bar:

| leans on it | how it fails when the partition is wrong |
|---|---|
| **every bar sum** | a merged bar sums to a MULTIPLE of the meter, a split bar to a fraction |
| **the meter** (`OMR_METER_FROM_BARS`, `OMR_METER_CARRY`) | both weigh the carried meter against the bars; a wrong partition is a wrong weighing |
| **every measure number** | `_document_bar_offsets` sums system bar counts |
| **the arc merge** | an arc is joined across a barline only if it ends ON its cell's right edge |
| **the cell frame itself** | a measure cell IS the span between two barlines |

⚠️⚠️ **The independence answer is the worst in the family and the repo already
named it.** The barline reader and the bar-sum arbiter come off the **same
raster** and fail together: *a page whose meter the reader mangles is a page
whose bars do not sum.* Both `measure_partition`'s declared `checked_by`
entries — `measure_count_warning` (cross-staff bar-count agreement) and
`rhythm_sum_warning` — are read off the same ink as the partition. The
cross-staff count is the *better* of the two, because `groups.py`'s
`measure_count_across_staves` redundancy compares **the COUNT, not the
positions** — staves are engraved with different spacing, so two staves' x
positions legitimately differ while their count cannot. But it is still twelve
readings of one page.

⚠️ And `measure_count_warning` **fired ZERO times across all 29 stored
transcriptions** (MEASURED HERE, the probability-gates survey) — corroborated
by `benchmarks/omr-majority-steering-2026-08` finding 0 disagreeing staves over
27 systems. A check that never fires is not evidence that the partition is
right.

⚠️⚠️ **THE ONE GENUINELY INDEPENDENT WITNESS IS ALREADY NAMED AND IS NOT
BUILT: the printed MEASURE NUMBER.**
`docs/exploration-what-is-on-the-page-2026-09-09.md` §A states it exactly —
*"the engraver has already told us how many bars are on the line, and we count
them with geometry instead… the printed number is an independent witness in the
record's own sense — a different reader, no shared ancestor. It is also the
only page-side quantity that could corroborate a bar count without a reference
file."* It is ranked **6th** of that document's seven proposals, with a REACH
caveat that is the real blocker: it is small text (the `direction_text` rung's
problem) and `numeral*` covers meters, tuplet digits, fingerings **and** measure
numbers under one name.

⚠️ The same document's §C2 also records what this dossier's Q4 measured from the
other side: *"A barline is one event for the whole system, not one per staff.
Partly used (`_spans_system` rescues braced systems); **not represented as a
shared fact**."* That is `Q.BARLINE_COLUMN` being a per-staff count — the two
readings agree.

**Evidence grade:** class-space absence MEASURED HERE (grep on this tree);
page-frame separation MEASURED HERE (n = 19 barlines / 63 stems, 2 publishers,
8 pages, both scans, ONE adjudicator, barline half circular); Theil-Sen fix
MEASURED HERE (n = 1 page, 17/17); thickness ratios LITERATURE only.

---

## The systemic barline — and `Q.SYSTEMIC_COLUMN`

The one thin rule at a system's left edge running its full height, present
where the interior barlines stop. It is the only ink that crosses a family gap.

### 1. What sets it apart

**Two facts, both positional, both measured:**

* It sits at **exactly `x_start`** — the x where the staff lines begin.
  MEASURED HERE on an 8-staff LilyPond render at 200 dpi (staff space 13.8 px):
  columns ≥ 99% inked at **bracket 218–224, systemic bar 235–237, final barline
  1493–1495**; mimicking `Staff.x_start` gave **235**, *"the same 3 px"*.
  `[C83 + L75]`.
* It is about **0.16 staff spaces** wide, against a bracket's **0.5** — *"a
  bracket is ~3× the barline's ink everywhere."* At 4 mm / 300 dpi that is
  **1.9 px vs 5.9**; at 600 dpi **3.8 vs 11.8**. LITERATURE (Bravura
  `engravingDefaults`), reproduced on the render.

| confused with | separator |
|---|---|
| the **bracket** standing beside it | thickness (3×), and terminals |
| the **brace** | a brace is curved and *never forms a full column* — measured on the render, braces peaked at **0.5–0.7** of the gap |
| a gap bridged by **nothing** (an inter-system gap) | max column ink **0.16** on the render |

⚠️⚠️ **DEGRADATION INVERTS THE ANSWER, and the threshold is measured.** At
staff-space **≤ 7.6 px** the analyser reported **17 bridging columns across a
real inter-system gap — a false MERGE produced purely by resolution.**
MEASURED HERE,
`benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`.
Combined with `[L8]` (a conductor's score at the 4 mm floor rendered at 300 dpi
gives ~11.8 px), an orchestral score is at the hard end of this by
construction.

### 2. Best method

CV, and the shipped reader is `gap_crossing_runs` / `left_edge_barline_counts`
in `system_grouping.py`. A thin rule is the thin-line case.

### 3. Where the deciding information lives

Two bands, and which one you use decides what you can see:

* **wide** (`_robust_x_window`: the page-MEDIAN `x_start`/`x_end` ± 4 spacings)
  — `gap_bridging_counts`. Poisoned by body ink out in the staff and by a page
  whose systems are indented differently.
* **narrow** (`x_start − 2.0` … `x_start + 4.5` spacings) —
  `left_edge_barline_counts`, and its pair-local mirror `pair_left_edge_count`.
  `LEFT_BAND_RIGHT_SPACINGS = 4.5` is on a **measured plateau**: flat for
  RIGHT ≥ 3 across 45/45 settings and 300/600 dpi, because the leftmost barline
  sits at a different offset per edition (~0 spacings on Beethoven, +1.4–3 on
  La Mer).

⚠️ **Do not use `Staff.x_start` alone for the window.** It is the longest
contiguous ink run on the middle staff line, so on a degraded scan it lands
wherever the line happens to be unbroken: Beethoven 9 p.60 staff 3 reports
`x_start=885, x_end=1826` against ~275/~2485 for its neighbours, which produced
a window that missed the bracket entirely and a false system break. The shipped
window is the MEDIAN. (The mirror-image fault cost the key-signature work
eleven empty header crops — see the header dossier.)

### 4. Stage by stage

⚠️⚠️ **`Q.SYSTEMIC_COLUMN` IS DECLARED AND HAS NEVER BEEN OBSERVED.**
`gather_coverage` §1b reports it as the sole member of *ABSTAIN-ONLY (a reader
declared it and never read)*; `reach` reports it UNREAD with `produced —`. Its
only write in the whole tree is `gather.py:182`, an
`ABSTAIN.SYSTEM_TOO_SMALL` on systems under 3 staves.

**And the count it names IS computed** — `system_grouping.systemic_column_counts`
runs inside `assign_systems` on every page with `OMR_BRACKET_COLUMNS` on
(default). Its result reaches the record **only** as `Q.BRACKET_BLOCK`, a
`mirror=True` re-derivation of `Staff.group_index`. So the quantity exists, the
measurement exists, and nothing joins them.

| stage | what happens |
|---|---|
| GATHER | abstain-only, as above |
| ADJUDICATE | `adjudicate_system_membership` declares it in `composed_from` and **never reads it**; `adjudicate_staff_group` declares it in `DOWNHILL` |
| EVALUATE / INFER / EXPORT | nothing |

### 5. Abstain or best-guess — and what leans on this

**(a)** It abstains and does nothing else. `ABSTAIN.SYSTEM_TOO_SMALL` is an
honest word for a real refusal, and it is the only thing this quantity has ever
said.

**(b)** The systemic barline is the **veto that decides system membership** —
via `gap_bridging_counts`, not via `Q.SYSTEMIC_COLUMN`. Everything structural
leans on it: which staves are one system, therefore which staves vote on a
barline, therefore where the bars are, therefore every measure number.

⚠️ **Its independence is real and is worth naming**, because it is rare in this
family: the left-edge complex is a *different physical object* from the
interior barlines, drawn by the engraver for a different reason, and
`[C61]` measured that **0 of 147 read left-edge blocks span two systems over 57
pages**. That is why the veto is safe — it can merge an over-split page, never
split a correct one. What it cannot do is state a system's EXTENT: on a
section-bracketed edition the maximal left-edge object is a section bracket, so
reading it over-splits on **27 of 57 pages** (Bach 0 of 11 exact against
Litolff's one-bracket pages at 7 of 12).

**Evidence grade:** geometry MEASURED HERE on a synthetic LilyPond render
(n = 1) + SOURCED (Bravura); degradation cliff MEASURED HERE (n = 1 page);
`0 of 147` MEASURED HERE (57 pages, 5 publishers); ⚠️ **19th-century plate
practice for the systemic barline is explicitly UNSOURCED** — the harvest found
no authoritative source and refused to guess. *"This is the biggest hole."*

---

## `repeatDot` — and the repeat barline

Two small round marks straddling the middle line beside a heavy barline. Class
**`repeatDot`**, ids 2 and 138.

### 1. What sets it apart — and what it is confused with

The dots are at **FIXED staff positions**: centred in spaces 2 and 3, i.e. at
**±1 space from the centre line**, with `repeatBarlineDotSeparation` **0.16**
staff spaces from the inner barline. So a repeat sign is recognisable from two
round marks at known heights beside a heavy barline **with no need to read the
barline's own structure** — and the SIDE the dots fall on tells which way the
repeat faces. LITERATURE (`[C76 + L77]`, Wikipedia *Repeat sign* + Bravura).

| confused with | separator | grade |
|---|---|---|
| **an augmentation dot** | an aug dot sits at its note's own space, half a space ABOVE for a note on a line, and NEVER below; a repeat dot is at ±1 space from the CENTRE line regardless of any note | LITERATURE `[L77]` vs MEASURED HERE `[C48]` |
| **an F-clef's two dots** | header-window only, straddling line **4**, and past the clef body's right edge at **0.94–1.79 notehead-widths** — the region where a C clef has nothing | MEASURED HERE — the clef-locator dot veto took false positives **48 → 13 → 5** |
| **a staccato dot** | on the notehead side, opposite the stem, centred on the head in x | LITERATURE `[L58]` |
| **speckle on a scan** | nothing measured | — |

⚠️ **The convention is ASSERTED here: its POSITIONS are sourced from the
literature and nothing has been measured on a plate.** The registry's own
*Would be falsified by* is *"measuring detected `repeatDot` positions against
the middle line on a plate that prints repeats"* — never done.

### 2. Best method

**The dots are YOLO's (the class exists and fires); the BARLINE half is CV's
and does not exist** — and this is already `position-grammar-confusables` §5's
own row: *"repeatDot → repeat barlines · repeat signs are NOTES item 6, dropped
on export today; **dots + CV barline = the anchor pair, no model change**."*
What is missing is the barline TYPE, not the dots.

⚠️ **R2 (family closure) puts `repeatDot` in a labelling family with
`augmentationDot` and `articStaccato*`**, with the note that F-clef dots ride
inside the clef's box. So a future labelling pass must present the three
together, *"so the human makes the role call once, in context"* — otherwise it
teaches "this exact shape is background" on half the evidence.

### 3. Where the deciding information lives

**Beside the mark, not on it.** A pair of dots at ±1 space is the whole of the
dot-side evidence; everything that makes it a *repeat* rather than two dots is
the heavy barline adjacent to it, and the side it stands on.

### 4. Stage by stage

**There is no quantity, no decision, and no export, at any stage.**

* GATHER: `FAMILY_TO_Q["repeat"] = None` — `gather_coverage` §5 lists `repeat`
  under **NO QUANTITY NAMES IT** (1 class). The ink reaches the record only as
  an anonymous `Q.GLYPH_BOX`.
* ADJUDICATE / EVALUATE / INFER: nothing.
* EXPORT: `staged/export.py:2983` names it explicitly —
  `"repeatDot": "repeat barlines are a KNOWN GAP of the legacy exporter too"`.
  `export_coverage.KNOWN_GAPS["barline"]` carries the same gap for `<repeat>`
  and `<bar-style>`.
* An earlier class-space audit surfaced **`repeatDot` ×4** on the engraved
  benchmark (MEASURED HERE, `export_coverage.py:65`) — so it does fire, rarely,
  on that corpus.

⚠️ **`volta` is not in the class space at all** (checked on this tree:
`[c for c in names if 'volta' in c]` → `[]`), so first/second-time bars cannot
be read even if the repeat were.

### 5. Abstain or best-guess — and what leans on this

**(a) No.** There is nothing to abstain: no decision exists. An anonymous
`Q.GLYPH_BOX` carrying `repeatDot` is the breakthrough document's case exactly —
*a carefully recorded "cannot tell" about a subject that does not correspond to
anything* would at least be a record; here there is not even that.

**(b) Nothing leans on it today**, and that is the finding. What *would* lean
on it if it existed: the playback order, and nothing else — a repeat changes no
pitch and no duration. So this is the cheapest gap in the family to leave open
and the cheapest to close: it needs one gathered quantity and one export
branch, and the ink is already detected.

**Evidence grade:** positions LITERATURE only; the F-clef confusion MEASURED
HERE (n = clef-locator sweep corpora, 2 editions); reach MEASURED HERE (×4 on
the engraved benchmark); the gap MEASURED HERE on this tree by
`gather_coverage`.

---

## `segno` and `coda`

Navigation marks. Classes **`segno`** (ids 3, 139) and **`coda`** (ids 4, 140).
Treated in one section because the finding is identical for both and Sean does
not need it twice.

### 1. What sets it apart

Both are large, distinctive, unique glyph shapes printed clear of the staff —
in shape terms the easiest marks in this family. **Nothing in this repo has
measured either.** The `_CATEGORY_MAP` comment records a frequency count from
`benchmarks/omr-phase3/r2`: **`coda` ×4, `segno` ×1** across 30 verdict cells —
which is a count of detections, not of printed marks, and is the only number
this repo holds about them.

Confusable with: nothing measured. ASSERTED: a `coda` is a circle crossed by
two strokes and the nearest printed thing to it on an orchestral page is a
fermata or a large ornament; no confusion has been observed or looked for.

### 2. Best method

**YOLO**, by elimination: both classes exist, both fire, and both are compact
distinctive shapes of the kind boxes are good at — the opposite of the thin-line
case that moved stems and beams to CV.

### 3. Where the deciding information lives

**On the glyph.** These are the rare marks in this family whose identity is
NOT contextual — a segno is a segno wherever it stands. What IS contextual is
what it *means* (which bar to jump to), and that is a document-level fact no
stage in this pipeline has a scope for.

### 4. Stage by stage

**Nothing, at every stage, for both classes.** `gather_coverage` §5 lists
`coda` (1 class) and `segno` (1 class) under **NO QUANTITY NAMES IT**.
`FAMILY_TO_Q["coda"] = None`, `FAMILY_TO_Q["segno"] = None`. No adjudicator, no
consequence, no inference, no export element. `export_coverage.NOT_NOTATION`
mentions segno once, under `sound` — *"MIDI playback — tempo, dynamics as
velocities, segno/dacapo jumps"* — i.e. as a thing deliberately not carried.

### 5. Abstain or best-guess — and what leans on this

**(a)** No decision exists, so no.

**(b) Nothing leans on them.** They change no note. But
`docs/exploration-what-is-on-the-page-2026-09-09.md` §A puts them in a category
of their own — *the page's traversal order, printed and modelled nowhere*:
*"the `repeat` family is `repeatDot` ONLY — we have the dots, not the sign —
and `volta` is not in the class space at all. Together these mean **the printed
order is not the playing order**, and no part of either pipeline represents
that. This is a whole axis, not a gap."* That is the honest framing, and this
dossier adds nothing to it except the per-symbol confirmation that
`FAMILY_TO_Q` is `None` for all three.

They are also a **section landmark**, and this project has a standing need for
exactly that:
*"a thin-thick barline is a MOVEMENT BOUNDARY, which is exactly where a carried
meter, key and lineup must all stop being carried"* — and `OMR_METER_CARRY` is
now default ON, so a carried meter crosses every boundary the pipeline cannot
see. A `coda` is not a movement boundary, but it is in the same class of cheap
structural landmark, and it is the only one of them **already detected by the
model**.

**Evidence grade:** the gap MEASURED HERE (`gather_coverage` on this tree);
the frequency ×4 / ×1 MEASURED HERE (n = 30 verdict cells, one benchmark, 2026
vintage); everything else ASSERTED or unmeasured.

---

## `brace`

A curly flourish at the left edge enclosing the staves ONE PLAYER reads.
Class **`brace`**, ids 0 and 136 — the first class in the space.

### 1. What sets it apart — and what it is confused with

| fact | grade |
|---|---|
| **A brace means ONE PLAYER**, not two staves. The evidence for it is the INSTRUMENT being a keyboard or a harp. | ASSERTED `[C65]` — declared with its falsifier, never measured |
| **A brace is CURVED and can never form a full column.** On the LilyPond test render braces peaked at **0.5–0.7** of a gap's height and never spanned it. | MEASURED HERE `[C84 + L64]`, n = 1 synthetic render |
| A bracket is straight-sided with square terminals; a brace is not. | LITERATURE (IU *Brackets*) |

⚠️⚠️ **THE CONFUSION IS ALREADY SHIPPED AND IT IS NOT WITH ANOTHER GLYPH — IT
IS WITH A STAFF COUNT.** This is **A-GROUP-2** verbatim, cited rather than
re-derived. All three incumbent sites decide brace-vs-bracket by
`len(staves) == 2` (`export.py:681`, `:3446`, `:3523`), and
`to_musicxml:3843-3848` writes `<part-group><group-symbol>brace</group-symbol>`
whenever `len(slots) == 2`. Brahms 1 p.1 reads bracket blocks
**`[2,2,2,2,2,7,1,3]`** — five PAIRS that are `2 Flöten`, `2 Oboen` and so on —
so **consuming "block of 2" as a brace declares five wind pairs to be pianos.**
MEASURED HERE (the block reading), `tools/omr/staged/ASSUMPTIONS.md` A-GROUP-2.

⚠️ And on **Simrock (Dvořák 9)** the braces on instrument pairs were what the
bracket reader read *instead* of the one whole-orchestra bracket — it "states
blocks" on 16 of 18 Simrock systems and **those are its BRACES**, wrong about
the bracket. MEASURED HERE, `benchmarks/omr-bracket-reading-2026-09` §2.

### 2. Best method

**Unclear, and nobody has tried.** The class exists and nothing reads a `brace`
detection. The CV reader `bracket_reader.py` DOES see braces — on Bach/Peters
*"the last strip shows an unmistakable brace over the continuo"* — and its own
level-separation problem is that *"the brace is not reliably on either side"*
of the bracket in x; what separates them is **what they REACH**, not where they
stand.

⚠️ A brace is a curved thin stroke — the shape class this repo moved to CV for
stems and beams. But it is also compact and distinctive, unlike a hairpin. No
measurement exists either way.

### 3. Where the deciding information lives

**Per the shipped design: not on the glyph at all.** `adjudicate_group_symbol`
keys on the INSTRUMENT (`BRACE_FAMILIES = {"keyboard", "harp"}`), on the
explicit ground that the staff count is what the incumbent gets wrong. Per the
geometry: at the system's left edge, in the same band as the bracket,
separable by *reach* and by *never forming a full column*.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER** | `FAMILY_TO_Q["brace"] = None` — **no quantity names the glyph**. The comment says why: *"the GLYPH; `Q.GROUP_SYMBOL` is the verdict"*. So the record holds a verdict about a mark whose ink it never gathered. |
| **ADJUDICATE** | `adjudicate_group_symbol` (#8, `Kind.SYSTEM`, `Mode.ADDITIVE`): abstains `no_group` with no `Q.STAFF_GROUP`, abstains **`no_identity`** with no named instrument, else returns `brace` if any family is keyboard/harp, else `bracket`. |
| **EVALUATE / INFER** | nothing. |
| **EXPORT** | ⚠️⚠️ **`Q.GROUP_SYMBOL` is read by NOTHING.** `reach` reports it UNREAD; `reach.KNOWN_GAPS` calls it *"an OPEN FINDING — a DECIDED verdict no stage reads."* The staged exporter writes no `<part-group>` at all; the legacy one writes the `len(slots) == 2` brace above. |

⚠️ **Reach is measured and is zero.** `group_symbol` abstains `no_identity` on
**22 of 22 staves** on the measured page, because `instrument` abstains
`no_evidence`. MEASURED HERE (CLAUDE.md's `<part-group>` scoping). So today the
decision is a pure no-op *and* its verdict has no consumer — two independent
reasons it cannot act.

### 5. Abstain or best-guess — and what leans on this

**(a) Yes, and it abstains well** — `no_identity` is exactly right: *"the
honest answer with no identity is 'I do not know what symbol this is', and
saying so lets the incumbent rule stand rather than replacing it with a
guess."* That is the design working. ⚠️ It also means the **wrong incumbent
rule stands everywhere**, which is the design working and the output being
wrong at the same time.

**(b) What leans on it.** `<part-group>` affects rendering only — no note
moves. But the *reasoning* it embodies leans on `Q.INSTRUMENT`, which is the
weakest chain in the whole pipeline: `instrument` abstained `no_evidence` on
**75 of 75 staves** on the Litolff record because `run_staged` took `pdf_path`,
rasterised with it and **dropped it**, so `gather_margin_labels` filed
`not_implemented` on every staged run this repo has ever made
(MEASURED HERE, `benchmarks/omr-part-join-phase2-2026-09/`). That has since been
repaired, but the dependency is the point: **a brace decided from identity
fails exactly on the pages where identity fails**, and identity fails where the
margin is unlabelled — which `[C70]` measures as the continuation systems of
the strings.

**Evidence grade:** the `len(staves)==2` hazard MEASURED HERE (block reading,
n = 1 page); the curvature fact MEASURED HERE on a synthetic render (n = 1);
`[C65]` itself ASSERTED and declared so; the zero reach MEASURED HERE.

---

## The family bracket

The straight-sided rule with square terminals enclosing an instrument family at
a system's left edge. **It is NOT in the 208-class space** — checked on this
tree: `bracket` matches only `tupletBracket` (a tuplet marker) and
`ottavaBracket`. Nothing detects it.

### 1. What sets it apart — and what it is confused with

**The shipped answer is that we do not read it at all. We INFER where the
families are from where the interior barlines STOP.** `[C58 + L63]`.

| confused with | separator | grade |
|---|---|---|
| the **systemic barline** standing beside it | thickness 3× (`bracketThickness` 0.5 vs `thinBarlineThickness` 0.16); and the bracket has terminals | LITERATURE `[L75]` |
| a **sub-bracket** (like instruments within a family) | `subBracketThickness` **0.16** against 0.5 — a 3× difference, *"so the two levels are separable by thickness alone"* | LITERATURE `[L64]` |
| a **brace** | reach, not x position | MEASURED HERE |
| the **staff lines themselves** | ⚠️ a reader fault: `BRIDGE_GAP_TOLERANCE_SPACINGS` (0.6) closes a 19 px kernel over a 12.75 px white gap between staff lines, so every column inside the staff becomes one solid run per staff — **shaped exactly like a bracket over a single staff**. Fixed by dropping runs that cross no inter-staff gap. | MEASURED HERE, `benchmarks/omr-bracket-reading-2026-09` §3a |

⚠️⚠️ **`CLAUDE.md`'s "the bracket encloses exactly the system" IS FALSE AND IS
THE ONE ENTRY THE CONVENTION HARVEST WOULD RAISE WITH SEAN DIRECTLY.** An
8-staff LilyPond test score prints **four per-family brackets (2 staves each)**
plus the systemic barline; read off the print at 600 dpi, **2 of the 5 editions
in the scan corpus print NO section bracket at all** (Litolff and Simrock print
one bracket for the whole orchestra).

| publisher (work) | at the left edge | section brackets? |
|---|---|---|
| Peters (Bach, Brandenburg 3) | three brackets 3\|3\|3 + a brace on the continuo | yes, 3 |
| Breitkopf (Brahms 1) | two brackets 9\|5 + braces on pairs | yes, 2 |
| unidentified scan (Mahler 5) | section brackets + braces on pairs | yes |
| **Litolff (Beethoven 5)** | **ONE bracket, whole orchestra** | **no** |
| **Simrock (Dvořák 9)** | **ONE bracket, whole orchestra, + braces** | **no** |

MEASURED HERE, hand-read at 600 dpi, `[C60]`. ⚠️ **The falsifier is already met
in the awkward direction**: on Litolff and Simrock a single whole-orchestra
bracket makes *"a bracket spans the system"* accidentally TRUE — which is
precisely why it must not be relied on.

⚠️ **And a bracket BLOCK is an ENGRAVING unit, not an instrument family.**
Breitkopf brackets winds + brass + timpani as ONE block against the strings:
the bracket runs straight through the clarinet/bassoon boundary and terminates
between timpani and violin I while the systemic barline runs on. MEASURED HERE
`[C59]`. ⚠️ Registry entry `[C59]` therefore **DENIES IN ITS TITLE** what
`adjudicate_staff_group` asserts in its `checked_by` — recorded as one of the
three declared-but-absent checks in `docs/RESUME-HERE-2026-09-20.md` §1.3.

### 2. Best method: YOLO / CV / other

**Neither — INFER it.** This is the family's strongest measured result and it
runs against intuition.

`tools/omr/bracket_reader.py` was built (390 lines, CV, model-free) and
measured against hand-read PRINT truth:

| | systems | bracket READER, exact | pixel rule (old default) | `OMR_BRACKET_COLUMNS` (today) |
|---|--:|--:|--:|--:|
| Bach / Peters, printed **3\|3\|3** | 22 | **5** | 16 contain all three | **22 contain all three; 21 exactly `[2,5,8,9]`** |
| Brahms / Breitkopf, printed **9\|5** | 15 | **1** | **0** exactly `[8]` | **15 of 15** exactly `[8]` |

Self-consistency across two systems of one page with the same lineup: reader
**0.882 disagreement**, repaired incumbent **0.055**. **Recommendation in the
findings: do not wire it in.** `bracket_reader.py` has **no consumer and no
flag** to this day. MEASURED HERE,
`benchmarks/omr-bracket-reading-2026-09/FINDINGS.md`, n = 102 systems / 60
pages / 5 publishers.

### 3. Where the deciding information lives

**In the inter-staff gaps, in WHAT CROSSES THEM — counted as OBJECTS, not as
pixels.**

⚠️⚠️ **The incumbent pixel rule could never have worked, and the reason is a
UNIT ERROR.** `gap_bridging_counts` returns `(number of crossing objects) ×
(each object's width in px)`; only the object count is evidence, because a
barline stands at the same x in every gap while a stem stands wherever the
music put it. The ratio is then ≈ `3 / (n_bars + 3)` and crosses 0.5 near three
bars a system. **Over 2,841 gaps of 248 systems the largest value below the 0.5
cut is 0.4962 and the smallest above is 0.5000** — a continuum, with 292 of
2,841 gaps in the ±0.05 band. Counting objects instead moves the same cut onto
an **EMPTY interval**: over 1,130 gaps, largest below **0.333**, smallest above
**0.778**. Within-page instability **0.384 → 0.055** over 144 pages, 5
publishers. MEASURED HERE,
`benchmarks/omr-bracket-stability-2026-09/FINDINGS.md`.

⚠️ **`BRACKET_COLUMN_MIN_EVIDENCE = 3` is load-bearing, and its own populations
are disjoint.** A LilyPond render bars per staff, so a 25-staff Bruckner system
carries **two** crossing columns in total; taking a ratio of 1 against a median
of 2 manufactured **11 groups**. Median informative columns per system:
engraved **0 ×6, 1 ×3, 1.5, 2 — max 2**; scanned **5, 6, 7×2, 8×5, … — min 5**.
A floor anywhere in 3..4 reads both corpora identically.

⚠️ **A column crossing EVERY gap is DISCARDED**, because a constant added to
both sides of a ratio is not neutral. On p.23 the winds|brass gap keeps 3 of 6
systemic columns (ratio 0.500 — the knife edge, no split) and 1 of 4 once the
two spanning columns are removed (0.250 — split, agreeing with the other
systems of that lineup). ⚠️ **That discarded object is the full-system
bracket**, which is why reading the bracket and inferring the families are
genuinely different questions.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER** | `_gather_bracket_blocks` observes `Q.BRACKET_BLOCK` per staff as a **`mirror=True` re-derivation** of `Staff.group_index`, because `_assign_groups` returns nothing. Three declining branches are mirrored as abstentions: `SYSTEM_TOO_SMALL` (< 3 staves) and `NO_COLUMN_EVIDENCE` — **A-GROUP-1**, the all-zero case, where *"a refusal and a reading are byte-identical"* on the old record because `_assign_groups` writes `0` from four branches plus a fifth path that never calls it. |
| **ADJUDICATE** | `adjudicate_staff_group` (#1) — `Mode.ADDITIVE` (**A-GROUP-3**: replayed over 67 stored transcriptions, additive consumption changed 20 exports, added 108 bracket groups, kept braces 2 → 2, **zero content differences outside the group lines**). Abstains `block_unavailable` on anything but `State.READ`. |
| **EVALUATE / INFER** | nothing. |
| **EXPORT** | via `group_symbol`, which reaches nothing (above). |

⚠️ **`Q.BRACKET_BLOCK` is 22/22 PRECISE and 22/39 RECALLED** — *"the absent
case is roughly half the population and is the whole reason this decision was
chosen to go first: it must ANCHOR a grouping where present and ABSTAIN where
absent — never assign."* MEASURED HERE, `adjudicate_staff_group` docstring.

⚠️ **It is structurally silent on the population the incumbent fires on** —
**A-GROUP-4**, which files this as *a limit, recorded so nobody reads a null as
a pass*. `_assign_groups` refuses systems with fewer than 3 staves, so on a
real two-staff page this measurement **cannot speak at all**. The two failure
modes people cite — a two-staff orchestral extract read as a piano, and a real
piano on a crowded page — are different problems and this can only ever address
the second. *"A test showing 'no change on piano pages' is measuring the
silence, not the fix."*

### 5. Abstain or best-guess — and what leans on this

**(a) Yes, and this is the best-abstaining decision in the family.** Two
distinct abstention reasons, mirrored from the reader's own branches, plus an
explicit `State.DECLINED` vs `ABSENT` split that makes *"I declined to
partition"* distinguishable from *"I read one family"* — which the legacy
record could not express at all (`group_index = 0` on four different branches).

**(b) What leans on it:** `Q.GROUP_SYMBOL` (which nothing reads),
`Q.INSTRUMENT` (via `wants` — and **that declaration is inert**, per
`inventory --check` on this tree), `slots.py`, and `OMR_CHOIR_GROUPING` cue C.

**Independence: the bracket inference and the barline reader are the SAME
signal.** Both read crossing columns in the inter-staff gaps of the same
raster. So a page whose barlines are broken is a page whose family boundaries
are unreadable, and *the bracket cannot arbitrate the barline*. ⚠️ **The one
genuinely independent witness is the printed BRACKET itself**, and it is
measured to be a worse reader (5/22, 1/15). That is an unusual and useful
result: here the independent witness exists, was built, and loses.

**Evidence grade:** print truth MEASURED HERE (hand-read at 600 dpi, n = 5
editions / 37 systems for the exactness table); stability MEASURED HERE (144
pages, 2,841 + 1,130 gaps, 5 publishers); thicknesses LITERATURE only; the
`[C59]`-vs-`staff_group` contradiction MEASURED HERE (registry vs code on this
tree).

---

## The system

Not a mark — a grouping. Which staves are read together as one stretch of
music. Decided in `tools/omr/system_grouping.assign_systems`, recorded as
`Q.SYSTEM_MEMBERSHIP` and `Q.SYSTEM_STAFF_COUNT`.

### 1. What sets it apart — and what it is confused with

**A system break is a gap that no vertical ink crosses.** Not a big gap — an
*empty* one.

⚠️⚠️ **STAFF SPACING CANNOT SEPARATE A SYSTEM FROM A GROUP, BY CONSTRUCTION.**
LilyPond's own shipped defaults (staff spaces, basic/minimum): staff-inside-group
**9 / 7**, across-group-boundary **10.5 / 8**, system→system **12 / 8** — under
compression both floor at **8**, so no distance threshold can separate them.
Measured on a real page: within-group **4.98**, across-group **6.50**,
between-system **8.02** — *and a denser variant's within-system gap hit 8.09,
larger than the other page's inter-system gap*. REFUTED HERE `[C85]`.
Independently: within one Brahms system the gaps run **17–237 px** and within
one Beethoven system **130–345 px**, both wider than the gaps BETWEEN systems
on a piano page, with x-overlap 1.00 for every pair.

| confused with | what happens | grade |
|---|---|---|
| **two stacked systems read as one** (over-MERGE) | stray ink in the gap — a measure number, a restarted instrument label, a stem, an `a 2.` marking — makes bridging nonzero. B9 p.60 had **324** crossing columns at the true break; B5 p.40 had 3 and 11; Eroica p.36 read one 22-staff system for a true [11, 11] | MEASURED HERE |
| **one system read as many** (over-SPLIT) | the gap heuristic on a conductor's page: Beethoven 9, 12 pages — gap-based **52 "systems"**, most common size **1 staff (37%)**; bridging **18 systems**, sizes 10–13, no 1-staff systems. Page 40 alone: one 12-staff system as `[3,1,2,1,5]` | MEASURED HERE, `system_grouping` module docstring |
| **a page whose systems are indented DIFFERENTLY** | the page-MEDIAN `x_start` lands between the modes. Bach Brandenburg 3 p.59: system 1 at x_start **792–836**, system 2 at **178–200**, median **450**, window `[359, 4554]` cuts system 2's bracket and systemic barline out of the scan; the 12-staff system shatters into `3/3/3/1/2` and its stems out-vote its barlines — **122 measure-cells against a true 10** | MEASURED HERE |
| **a choir-barred / Mensurstrich system** | interior barlines stop at each vocal staff, so a bracketed group's interior gap is crossed by **nothing** — *"impossible for a true open score"* | ASSERTED `[C86]`, consequence MEASURED |
| **a multi-column page layout** | `MIN_X_OVERLAP_FRAC = 0.5` — two staves that barely overlap in x are never one system regardless of connectivity | ASSERTED |

### 2. Best method

**CV connectivity, and the veto shape is what makes it safe.** Distance
proposes a break; connectivity VETOES it. *The veto can merge an over-split
page, never split a correct one* — which is licensed by `[C61]`'s measured
*0 of 147 left-edge blocks span two systems over 57 pages*.

### 3. Where the deciding information lives

**In the inter-staff gaps, in two bands, and the second band exists because the
first one is poisonable.**

| cue | band | direction | flag |
|---|---|---|---|
| wide connectivity | page-median `x_start..x_end` ± 4 spacings | veto a distance break | always |
| **cue A** — left-edge SPLIT | `x_start − 2.0 … + 4.5` spacings, page-anchored | ADD a break where the left column is EMPTY | `OMR_LEFT_EDGE_SPLIT`, **ON** |
| **cue B** — pair-local MERGE | the same band, anchored at the PAIR's own left edge | CANCEL a break made for lack of evidence | `OMR_CHOIR_GROUPING`, **ON** |
| **cue C** — open-score guard | `_window_blind_systems` + `_is_grouped_system` | keep a grouped system out of open-score mode | `OMR_CHOIR_GROUPING`, **ON** |

Each is one-directional by construction, so none can undo the others' validated
fixes. Cue A is union-only; cue B is merge-only and *"a band that finds nothing
changes nothing, so a page where it never fires is byte-identical"*.

**Measured:**
* **cue A**: across **964 library pages**, fixed **27 over-merged symphony
  pages** against **1 mild residual** (Mozart K22 p4), **0 size-1 systems
  created**; ground-truth eval **20/23 → 22/23**. Guarded end-to-end by 4
  scanned pages / 3 publishers with hand-read truth.
* **cue B/C**: Bach row OMR-NED **0.9241 → 0.8152**, edits **6735 → 6236**,
  cells **122 → 11 against a true 10**; all ten pooled scan rows
  byte-identical; the 11-work engraved benchmark **edit-for-edit identical**; a
  **969-page** library probe found **757 examined break-gaps reading 0 ×735 /
  ≥4 ×22 with nothing at 1–3**, and the 10 changed pages were each
  hand-adjudicated toward the truth (7 exact heals, **zero false merges**).

⚠️ **Bracket-groups ALONE as cue C's condition was FALSIFIED**: LilyPond open
scores manufacture "groups" from bridging jitter — pooled engraved OMR-NED
**0.1306 → 0.8560**, nine works' barlines deleted. The second condition (a
window-blind internal gap) is what makes it safe. **Do not loosen it.**

⚠️⚠️ **A LIVE DOC/CODE DIVERGENCE, already known and open.** The module
docstring (`system_grouping.py:34-45`) describes a band running *"from the top
line of the upper staff to the bottom line of the lower staff"* and argues that
extending through both staves is what discriminates barlines from stems. The
code measures **the gap only** (`upper.bottom_y + 2 … lower.top_y − 2`,
`gap_crossing_runs:293-294`). This is recorded in
`benchmarks/omr-system-grouping-2026-09/research/repo-state.md:98-107`, and
attempt 3 of `RULE_FIX_ATTEMPT_2026-08-31.md` proved **implementing the
documented version does not help** — so it is open whether the code or the
prose is wrong. It is *not* a new finding; it is named here because a reader
of the docstring will otherwise believe the band is wider than it is.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER** | ⚠️ `gather_systems` observes `Q.GAP_BRIDGING` as a **single page-level boolean `True`** (`gather.py:222`) when connectivity was usable, or abstains `NO_INK` when the gap-heuristic fallback ran. **Not per gap. Not a count.** `gather_measures` observes `Q.SYSTEM_STAFF_COUNT` per system. `Q.LEFT_EDGE_INK` — the narrow band cue A reads — is **declared and has no gatherer at all** (`reach` reports it a GHOST). |
| **ADJUDICATE** | `adjudicate_system_membership` is **decision #0** and returns `int(rows[-1].value)` of `Q.SYSTEM_STAFF_COUNT`. Its own docstring says so: *"Today's rule already runs in GATHER — `assign_systems` decides it while measuring. This records the result."* ⚠️ It declares `Q.GAP_BRIDGING` in `wants` **and never reads it** — `inventory --check` reports the declaration inert on this tree. |
| **EVALUATE / INFER** | nothing. |
| **EXPORT** | nothing reads `Q.SYSTEM_MEMBERSHIP`. |

⚠️⚠️ **`Q.SYSTEM_MEMBERSHIP` — decision #0's verdict — IS READ BY NOTHING.**
`reach` reports it UNREAD on this tree; `reach.KNOWN_GAPS` records it as an
**OPEN FINDING**: *"It appears in `implicates`, in `DOWNHILL`, in
`legacy.EXTRACTED_QUANTITIES` and in `wants` — all DECLARATIONS, none of them a
read."* The system grouping that everything structural depends on is decided in
GATHER, mirrored into a verdict, and consumed by nobody.

### 5. Abstain or best-guess — and what leans on this

**(a) Can it abstain?** The adjudicator abstains `no_evidence`. The READER
cannot: `assign_systems` returns a grouping. There is no state in which the
pipeline says *"I cannot tell how many systems this page has."* `Q.GAP_BRIDGING`
can abstain `NO_INK` for the whole page, which is the honest fallback signal,
and **nothing reads it**.

**(b) What leans on the system, and the answer is: the barline vote, and
therefore everything.**

* The barline vote's DENOMINATOR is `len(staves)` of the system. Merge two
  systems and the vote threshold doubles while half the staves cannot see any
  given barline — the Bach case, where 122 cells came out against a true 10.
* `Q.MEASURE_PARTITION` is per staff, but its cross-staff check
  (`measure_count_across_staves`) is keyed on the SYSTEM.
* `Q.SYSTEM_STAFF_COUNT` is the input to `slot_index` and `part_partition` —
  so a mis-grouped page mis-joins parts.
* `Q.ONSET_COLUMN` is scoped `Kind.SYSTEM`: *a column through a system is one
  instant of music*. A wrong system is a wrong instant.

⚠️ **Independence:** the system reader, the barline reader and the bracket
inference all read crossing columns in the inter-staff gaps of the same
raster. They are one witness wearing three names. The measured consequence is
the resolution cliff: at staff-space **≤ 7.6 px** the same analyser reported
**17 bridging columns across a real inter-system gap** — all three would be
wrong together, and none could flag the other.

**Evidence grade:** cue A MEASURED HERE (964 pages, 27 fixes / 1 residual);
cue B/C MEASURED HERE (969-page probe, 1 stress row, 10 engraved fixtures);
`[C85]` REFUTED HERE (LilyPond defaults SOURCED + 1 real page); the
`Q.GAP_BRIDGING` boolean and the unread `Q.SYSTEM_MEMBERSHIP` MEASURED HERE by
`reach` / `gather_coverage` on this tree.

---

## The measure cell, as a FRAME

Not a mark. The rectangle everything inside a bar is read in: the staff plus
**4 staff spaces above and 4 below**, cut per measure, rescaled so the staff
span is constant. `tools/omr/measure_extractor._build_measure_cell`;
`Q.CELL_BOX` (page px, CORNERS) and `Q.CELL_STAFF_SPACE` (cell canonical px).

**This section is here because the cell's padding is the single largest source
of cross-staff confusion in every other dossier in this set.**

### 1. What the padding does — and the confusions it manufactures

The pad exists because a ledger note and its stem live in the gap the engraver
opened for them. Four spaces already reaches through both of Mahler's
neighbours (measured inter-staff gaps: **Mahler 1.7–1.9, Beethoven 3.2–3.4,
Brahms 3.5–8.7 staff spaces**). So on a conductor's page **a cell routinely
contains the neighbouring staff's ink.**

| confusion it causes | measured | where |
|---|---|---|
| **a neighbour's notehead read as this staff's** | Brahms Violin 1's `A6`/`B♭6` exported as `A♭1`/`B♭1` on a timpani while Violin 1's bars 3-4 came out empty | CLAUDE.md, ladder-evidence work |
| **the cell's own EDGE read as a hollow notehead** | 7 `noteheadWholeInSpace` on a page whose truth contains no whole note — two of them the bowl of the **g** in *legato*, one the lower bowl of the **8** of a 6/8 on the staff above. Interior noteheads 0.61–1.12 spaces tall; fragments **0.29–0.56** | `_drop_clipped_notehead_fragments`, pooled 0.2209 → **0.2137** |
| **one printed arc detected twice** | 48 pairs of arcs placed in ONE cell at IoU ≥ 0.7, **19 of them detected on two different staves** | `benchmarks/omr-arc-recovery-2026-09` |
| **a dynamic letter attributed to the wrong staff** | **24% of 1,246 letters** stand in the band of the staff immediately above — *distance exactly 1, no exceptions* | `benchmarks/omr-dynamics-band-2026-09` |
| **an `ff` exported as `ffff`** | 688 of 1,386 ownership verdicts RELOCATED instead of resolving; both copies of one contest name the same owner | `benchmarks/omr-staged-dedupe-2026-09` |
| **a pitched note where the page prints silence** | **14 of 25** phantom notes stand OUTSIDE the staff altogether (steps 10-17), entering through the padding; ⚠️ and **5 of those 14 stand above the TOP staff of their system**, where the padding has no neighbour to name | `benchmarks/omr-phantom-notes-2026-09` |
| **a barline's ENDS clipped away** | the cell frame gives Sean's barline test **0 of 19** at every tolerance; the page frame gives 11–13 | `benchmarks/omr-vertical-runs-page-2026-09` |
| **the vertical-run population double-counted** | 6,128 cell candidates against **3,465** page runs on the same four pages | same |

⚠️⚠️ **DO NOT FIX A CLIPPED NOTE BY GROWING THE PAD.** Measured at
`PAD_*_STAFF_LINES = 5`: Brahms 0.3420 → **0.3732 (+128 edits)**, cross-staff
duplicates removed **135 → 390**. A taller crop makes more contested glyphs,
and the contest is resolved by distance to the nearer band — which for a note
in a gap the engraver opened *for* it is the wrong staff. ⚠️ And cell height is
coupled to `OMR_IMGSZ`, so a small change **moves DETECTIONS, not just the
crop**: growing the authored `ensemble` fixture's pad from 4.0 to 4.6 cost it
three notes of 45 for no gain. **The pad is four, or six where there is
unambiguously room for six, and nothing between.**

### 2. Best method

n/a — it is a crop, not a reading. What the evidence says is **which frame a
question should be asked in**: a question about a mark's ENDS (barline vs stem),
about ownership between staves, or about a page-wide column must be asked in
PAGE pixels. A question about a mark's internal shape can be asked in the cell.

### 3. Where the deciding information lives

⚠️ **THE FRAME HAZARD IS THE MOST-REPEATED FAULT IN THIS REPO AND THREE BOX
CONVENTIONS DISAGREE IN ONE RECORD:**

| quantity | convention |
|---|---|
| `Q.GLYPH_BOX.value` | `[name, x, y, w, h]` |
| `Q.STEM.value`, `Q.VERTICAL_RUN` canonical | `[x, y, w, h]` |
| `Q.INK.detail.ink_bbox_canonical`, `Q.CELL_BOX`, every `bbox_page_px` | `[x0, y0, x1, y1]` CORNERS |

Reading one as another gives a **negative width and a clean, believable zero** —
it cost `benchmarks/omr-ink-extent-2026-09` a whole run, reporting
`NO_INK_UNDER_BOX` on **100 of 106** rows. ⚠️ And `Q.STEM`'s documented
convention was **wrong in the code comment** until 2026-09-18.
**Assert the convention against the row's own stated spans before comparing.**

⚠️ **A cell index is not a part ordinal**: it RESTARTS at 0 on each system of a
page. Keying a bar on `(page, cell)` merged system 0's third bar with system
1's third bar and then scored it — which made a duration arm's bar-level
figures wrong when first published (44/43 → corrected 78/74).

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER** | `gather_detections` observes `Q.CELL_BOX` **before** the detections and independently of whether there are any — *"a bar we detected nothing in still HAS one, and it is the neighbour of a bar that does"* — and **abstains** rather than defaulting where `bbox_page_px` is absent. `gather_notehead_positions` observes `Q.CELL_STAFF_SPACE`. |
| **ADJUDICATE** | `adjudicate_duration` reads `Q.CELL_STAFF_SPACE` for the augmentation-dot window (`rhythm.py:515, 624`) and **DECLINES the dot** where no unit exists rather than measuring against a number written for another frame. |
| **EVALUATE / INFER** | nothing. |
| **EXPORT** | `staged/export.py:422` indexes `Q.CELL_BOX` **once**, not per staff, for the arc merge across barlines. |

⚠️ `Q.CELL_BOX` had to be a **GATHER** change, and that has a consequence for
every future measurement of it: `readjudicate.py` rebuilds from a saved record,
so a new gathered quantity never enters — **an A/B there needs two full
re-gathers.** `reexport_arm.py` has the mirror-image blind spot.

### 5. Abstain or best-guess — and what leans on this

**(a) Yes, and both cell quantities abstain properly.** `Q.CELL_BOX` abstains
`NO_STAFF_GEOMETRY` with a `frame_note`; `Q.CELL_POSITION_BASIS` is a refusal
filed once per cell. The reason `Q.CELL_BOX` must not be defaulted is stated:
deriving the edge from the glyphs inside would put it wherever the outermost
detection falls, *so an arc that genuinely reaches the barline would test as
ending in open space.*

**(b) What leans on the frame: every measurement in the pipeline except the
ones deliberately taken on the page.** And the independence question has a
sharp answer here — **the CV hairpin reader works in page pixels per staff and
is right BY CONSTRUCTION, while the dynamic letters go through per-measure
cells and lose 24% to the staff above.** Same page, same ink, two frames, two
error rates. That is the cleanest demonstration in the repo that the frame, not
the reader, is often the fault.

**Evidence grade:** all figures MEASURED HERE with their benchmarks named;
n varies per row and is stated in each source.

---

## `ottavaBracket`

The `8va` / `8vb` bracket and its dashed continuation. Class
**`ottavaBracket`**, id 135.

### 1. What sets it apart — and what it is confused with

A horizontal dashed line with a hook at one end, printed clear above or below
the staff, preceded by an `8`. **Nothing here has measured it.**

Plausible confusables, ASSERTED, none looked for: a dashed **barline**
(`[L78]`, the only entry that names a dash-to-gap ratio, 2:1); a **trill
extension line**; a **hairpin** (a thin near-horizontal line printed in the
same band below the staff — and the repo already records `SPAN_CLASSES` and the
hairpin reader as a band-based classical-CV rung); the **`8` of a time
signature** (which `_drop_clipped_notehead_fragments` has already caught being
misread, as two hollow noteheads).

### 2. Best method

Unmeasured. The class exists and fires; the mark is a long thin line, which is
the shape class this repo moved to CV for stems, beams and hairpins.

### 3. Where the deciding information lives

**In its SPAN, and that is the whole problem.** An ottava is not a mark at a
point — it is a scope, like an in-bar accidental. The record has nowhere to put
a span: `gather_coverage.FAMILY_Q_IS_ELSEWHERE` says exactly this of
accidentals — *"it is SCOPE rather than a mark: it holds to the barline, which
is a span the record has nowhere to put."*

⚠️ And a measure cell cuts the span, exactly as it cuts a slur. So an ottava
over four bars is up to four detections, with the same merge problem
`_merge_arcs_across_barlines` solves for arcs and nothing solves here.

### 4. Stage by stage

**Nothing, at every stage.** `gather_coverage` §5 lists `ottava` (1 class)
under **NO QUANTITY NAMES IT**; `FAMILY_TO_Q["ottava"] = None`. `grep -rn
ottavaBracket tools/omr/` returns three hits and all three are in
`annotate/build_archetypes.py` — the labelling UI's symbol archetypes. No
adjudicator, no export.

### 5. Abstain or best-guess — and what leans on this

**(a) No.** No decision exists.

**(b) ⚠️ THIS IS THE HIGHEST-COST MISS IN THE FAMILY PER MARK, and the reason
is arithmetic: a missed ottava costs EVERY NOTE IN ITS SPAN AN OCTAVE.**
`docs/exploration-what-is-on-the-page-2026-09-09.md` §A says it in terms —
*"a span that shifts every note under it by an octave. A missed one is not one
wrong note, it is every note in the span wrong by twelve semitones. **Highest
damage-per-instance of anything in this list.**"* — and files it beside the
in-bar accidental as the other case where *the missing quantity is a SPAN, not
a mark*.
Nothing else in this dossier can be wrong about a pitch; this one can be wrong
about dozens at once, silently, and the resulting music is internally
consistent — the bar still sums, the intervals are still right, so **no
bar-sum, cross-staff or self-consistency check in the pipeline can see it.**

The only witness that could is a **written-range** check against the
instrument — which needs identity, and identity is the weakest link. Or the
DOSSIER, which does not come off the raster. Neither is wired.

⚠️ **Reach is unmeasured**: nobody has counted `ottavaBracket` detections on
any corpus here, and nobody has counted `<octave-shift>` elements in any truth
file. **Measure reach before accuracy** applies to this one in full.

**Evidence grade:** the gap MEASURED HERE (`gather_coverage` on this tree);
the octave cost ASSERTED (arithmetic, never observed in a file here);
everything else unmeasured.

---

## `ledgerLine` — as it bears on structure

Short rules extending the staff's grid for notes outside it. Class
**`ledgerLine`**, id 1. **Fully covered in the noteheads dossier** — this
section states only what a structure reader needs.

### 1. What sets it apart

A ledger line is a **fragment of the staff grid**, so it shares every property
with a staff line except length and pitch:

* **thicker** than a staff line — `legerLineThickness` **0.16** vs
  `staffLineThickness` **0.13**, about 23% heavier. LITERATURE `[L6]`.
  ⚠️ *"23% is not a large margin and may not survive a low-resolution bitonal
  scan"*, and it has never been measured on a plate here.
* **NOT at the staff's own spacing** — and this is the structure-relevant
  finding. `[C3]`, MEASURED HERE over three independent populations, two of
  them detector-free: Litolff hi-res **1.102**, hollow-08 Litolff **1.135**,
  Eulenburg 1.050, Jurgenson 1.055, Universal 1.030 — against Breitkopf
  **0.975**, Peters 0.977, Simrock 0.975, Novello 0.975. Extrapolating the
  in-staff grid outward at 1.000× accumulates **+0.065 / +0.223 / +0.319 /
  +0.541 half-steps on Litolff — it FLIPS at rung 4**.
  ⚠️ **A corrected CONSTANT is swept and refused**: no single factor serves
  Litolff's 1.03–1.11 and Breitkopf's 0.97–1.00.
* **confused with a TENUTO**, and that is `position-grammar-confusables` §2
  **HORIZONTAL STROKE** (Sean's own example). The three discriminators it names
  are lattice parity, ladder continuation / a head centred through it, and
  matching the staff's own measured line thickness. ⚠️ The third is
  `Q.STAFF_SKEW.thickness_px` and **nothing reads it** — see the staff section.
  The risk is in the evidence chain, not just the export: *"a tenuto misread as
  a ledger feeds false rungs into attribution, and the reverse starves it."*
* **also confused with**: a staff-line remnant that survived erasure; a hairpin;
  a beam fragment. Measured the other way — `remove_staff_lines` clears a median
  **55%** of a Litolff cell's line ink, and the surviving residue does NOT come
  out as residue-shaped rows (**2 of 1,244** on Litolff, **16 of 6,055** on
  Breitkopf) because it is CONNECTED to everything else and lives inside the
  blobs.

### 2. Best method

**Both, and the split is already shipped.** The DETECTOR supplies
`ledgerLine` detections; the annotate UI's snap grid reads the RUNGS off the
cell image directly (`tools/omr/annotate/ledger_grid.py`, 3.4 ms), because
extrapolation mis-suggested **38–39% of 2nd-ledger-and-beyond variants against
4.6% inside the staff**, and reading them took 2nd-ledger agreement
**57.4% → 70.2%** with the in-staff grid untouched (0 changes across all 214
in-staff labels).

### 3. Where the deciding information lives

Between the staff and the note, as a **LADDER**: an unbroken run of rungs at
the staff's own outward pitch. `_observe_ladder` (`gather.py:648-675`).

### 4. Stage by stage

`Q.GLYPH_LADDER` is observed per glyph per candidate staff, as
`found == expected` — **COMPLETENESS ONLY, NEVER COUNT**. It is read by
`adjudicate_glyph_owner` (`ownership.py:71`), which is the cross-staff
ownership contest. LIVE on `reach`.

⚠️ **Why completeness and not count**: *two broken ladders are not evidence
either way, because a found rung can belong to the other staff's note exactly
as a gap can.* On the Beethoven bassoon pair the ghost's single rung WAS the
real C4's own ledger, and counting rungs beat the real note. MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this

**(a)** The ladder test returns a boolean per candidate; the OWNERSHIP decision
above it abstains. A glyph inside the staff gets no ladder row at all (`return`
before observing), which is correct and is an ABSENT rather than a DECLINED.

**(b)** Cross-staff notehead ownership leans on it, and therefore every pitch
in a gap between two staves. Independence: the ladder is read off the same
raster as the notehead, so it is the correlated-witness shape again — but it is
a *different object* (a rung vs a head), which is the strongest form of
within-raster independence available and is why it outranks distance.

**Evidence grade:** ledger pitch MEASURED HERE (9 publishers, three
populations, two detector-free); thickness LITERATURE only; the ladder rule
MEASURED HERE (pooled 0.1506 → 0.1431, Beethoven notes **81/81** at
recall/precision 1.000).

---

# What we do not know

**1. Whether any of these readers is RIGHT, on most of the population.**
Almost every figure here is a self-consistency or an A/B number. The
print-adjudicated ones are: the bracket blocks (5 publishers, hand-read at 600
dpi), Sean's barline test (19 barlines / 63 stems, 2 publishers, **both
scans**, one adjudicator, and the barline half circular by sampling), and the
phase-1 staff counts (2 pages). Everything else is the pipeline agreeing with
itself.

**2. The one-staff barline.** `benchmarks/omr-barline-height-2026-09` puts the
marks Sean's page-frame test was measured on at roughly **8% of the barlines on
the page**. The other 92% — the ordinary interior barline on one staff — has
never been print-adjudicated at all.

**3. Whether the system-grouping docstring or its code is wrong.** The band is
gap-only; the prose says it runs through both staves; implementing the prose
was tried and did not help. Open since 2026-08-31.

**3b. Whether Sean's endpoint rule works on the ORDINARY interior barline.**
§0's disagreement leaves this open in both directions: the rule is `0 of 19`
in the cell frame, `11–13 of 19` in the page frame, and **neither sample
contains a one-staff barline**. The page-frame lane names the fix itself — a
crop pass sampling from the ACCEPTED and `too WIDE` buckets, never again from
`too TALL`. It is a print pass, not code.

**4. Reach for four symbols.** Nobody has counted `ottavaBracket`, `segno`,
`coda` or `repeatDot` detections on any corpus here, nor `<octave-shift>` /
`<repeat>` elements in any truth. Four gaps whose size is unknown.

**5. Whether a barline TYPE is readable at all.** NOTES.md item 5 names two
routes (pixel-pattern post-processing; new YOLO classes at 200+ examples per
type) and neither has been tried since Phase 3.4's collapse.

**6. `Q.GAP_BRIDGING` as a page-level boolean.** The per-gap counts that decide
system membership and bracket blocks are computed and never recorded. So a
record cannot answer *"how close was this system break?"* — only *"connectivity
was usable."*

**7. Anything about the ENGRAVED family for the structure marks.** Every
barline, system and bracket figure of the last week is from two scans. The
engraved fixtures are byte-identical under most of these flags **by
construction**, which is a control, not a measurement.

**8. n throughout.** 2 publishers and 8 pages for the 2026-09 barline and
system work; 5 publishers and 144 pages for the bracket stability; 964–969
library pages for the two system cues. One adjudicator for every print reading.

---

# Questions for Sean

**1. The bracket sentence in `CLAUDE.md` is wrong and the harvest flagged it
for you by name.** *"A barline runs a system's full height and the bracket
encloses exactly it"* — the barline half is sound, the bracket half is false on
2 of 5 held editions, and it is *accidentally true* on Litolff and Simrock
because they print one whole-orchestra bracket. Do you want it corrected in
place, or left with the correction beside it?

**2. Is a family BRACKET worth reading at all?** We built the reader. Against
your own print truth it scores **5 of 22** and **1 of 15** where inferring the
families from where the barlines stop scores **22/22** and **15/15**. The
recommendation on record is *do not wire it in*. Do you agree that the printed
bracket is simply not the signal — or is there a case (a publisher, a layout)
where you would expect the reading to win?

**3. Do repeats matter to you enough to build them?** Today `repeatDot` is
detected and thrown away, no barline type is read, `volta` is not in the class
space, and `<repeat>` is a declared export gap. You asked for single / double /
final / repeat barlines distinguished (NOTES item 5). It is cheap for the DOTS
and expensive for the BARLINE. Would dots-plus-a-heavy-barline-anchor be worth
having on its own, knowing the bar-style would still be wrong?

**4. `ottavaBracket` — where does an octave shift actually appear in your
repertoire?** It is the only mark in this family that can silently move dozens
of notes by an octave, no internal check can catch it, and **nobody here has
counted one.** If it is rare in 19th-century orchestral scores, it stays a
footnote; if it is not, it outranks everything else in this dossier.

**5. `Q.SYSTEM_MEMBERSHIP` and `Q.GROUP_SYMBOL` are DECIDED and read by
nothing.** The system grouping every bar depends on is settled inside GATHER
and mirrored into a verdict no stage consumes. Is that acceptable as a
recording layer, or do you want the decision actually moved — which would mean
`assign_systems` proposing rather than deciding?

**6. The one-line percussion staff.** The flag is OFF, it costs **+65 edits**
on the scan gate as scored today and **−144 / −212** on the other two
instruments, and while it is off **every staff below a percussion rule carries
the wrong ordinal**. That is an identity error dressed as a missing staff. Do
you want it on, accepting the metric regression?

**7. Your barline test now works — in the page frame, 11–13 of 19 against 0 of
63 stems.** Nothing reads it. The reader returns vertical ink with page
coordinates and NAMES NOTHING. Is *"is this vertical mark a barline"* a
decision you want built — and if so, should an accidental's vertical stroke be
in its domain at all? (That question was left open for you on 2026-09-18 and
has not been answered.)

**8. ⚠️ The disagreement in §0, put to you directly.** Our own design note
files stem-vs-barline as *"already solved; the precedent."* On this tree the
span test that solves it runs **only on systems of fewer than three staves**,
its evidence is four braced piano systems, and the convention it rests on
(*interior barlines STOP at family boundaries*) says it cannot hold on a
conductor's page. Do you read that as *the precedent was only ever about the
grand staff and we over-generalised it*, or is there a form of the rule for the
one-staff orchestral barline you have in mind that we have not tried?

**9. Tenuto vs ledger: the discriminators exist and nothing reads either of
them.** The design note says the measurements *"already exist in the pipeline's
JSON"*. They do — line thickness is measured twice, once per staff
(`Q.STAFF_SKEW.thickness_px`, unread) and once per cell inside
`staff_line_removal` — and **nothing compares them and no rule names a
horizontal stroke with either.** Is that confusion worth a consumer, given that
a tenuto read as a ledger feeds FALSE RUNGS into the cross-staff ownership
contest and the reverse starves it? Nobody has counted how often it happens.
