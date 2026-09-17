# `Q.INK` — the ink is the population, and classification is an attribute

2026-09-17. `A-DUR-5`, Sean's standing request since 2026-09-09, built as the
**PRODUCER ONLY**. `OMR_INK`, **default OFF**, allow-list.

> *"I really don't want to lose the 'here is a blob of ink but we don't know
> what it is' gather data point. It can be used in every decision point if
> needed to help rule things out or determine patterns like — this is the same
> unrecognizable blob on every system at bar 51 ... or we know what this blob
> is in 3 of the 10 systems and they all line up and are there for the same
> thing."* — Sean, 2026-09-09

> *"Missing doesn't make sense to me. We can only gather what we see. We may or
> may not be able to classify it correctly initially - or at all - but ink is
> ink. There is nothing that should be classified as unseen - only
> unclassified."* — Sean, 2026-09-17

> *"even staff residue should go through the process and hopefully our rules
> and measurements will determine at the appropriate stage that it is just
> that - staff residue."* — Sean, 2026-09-17

---

## 0. THE SHORT VERSION

| | |
|---|---|
| **Reach** | 1,244 rows on Litolff Beethoven 5 p.62 (17 staves, 221 cells); 6,055 on Breitkopf Brahms 1 p.1 (27 staves, 202 cells). **1.8 s and 2.6 s**, against 13-15 s for the detector on the same page. 0 refusals on either. |
| **Pre-registered target** | ✅ **17 of 17 staves carry a row at the printed `3/4`; 16 of 17 unclassified.** |
| **Alignment vs a null** | Litolff **0.63×** columns / **0.43×** alone. **Unclassified ink scores identically to all ink.** |
| **Second publisher** | Breitkopf **0.87 / 0.83** — much weaker, and the composition inverts (56% specks against 1%). |
| **Composition** | Reported whole, nothing removed. Litolff: 67.5% mark-sized, 25.6% vertical, 5.7% merged blobs, 1.0% speck, 0.2% line residue. |
| **Flag off** | **Byte-identical to `origin/main`** (md5 `8f8bf9ee…`), with a positive control showing the flag adds 1,244 rows. |
| **Consumer** | **None, deliberately.** Seven detail keys are on `wiring.KNOWN_GAPS` as OPEN. |
| **Mutation battery** | 19 arms, **19 red**, positive control in the same class, restore VERIFIED. |

⚠️⚠️ **AND A CORRECTION TO THE RECORD FELL OUT OF THE PRE-REGISTERED TEST:
the printed `3/4` on p.62 is at CELL 6, not cell 8**, and the `timeSig3` +
`timeSig4` this project reads at cell 8 is **one barline broken into two
fragments**. See §6.

---

## 1. WHAT WAS BUILT, AND WHAT IT IS NOT

`record.Q.INK` + `gather.gather_ink`, one row per connected component of a
measure cell's staff-line-erased image, carrying:

* the box in **both frames** — canonical (cell-local) and **page pixels**;
* `width_spaces` / `height_spaces` / `ink_fill` / `ink_area_px` — the shape;
* `ink_detector_coverage` and `ink_explained_by` — **what share of it the
  detections account for, and which classes.** Not a verdict about what it is;
* `ink_n_components` / `ink_share_of_cell` — **the merge warning** (§4).

**It is not a supplementary tier of "blobs" beside the detections.** Until this
rung, every measurement in GATHER started from a DETECTION, so the record's
population was the detector's output and ink it did not fire on produced no row
at all — the ABSENT/DECLINED collapse `record.py` exists to prevent, happening
to the ink itself. `Q.INK` makes the population the ink and the classification
an attribute that may be absent and may later be revised.

⚠️ **NOTHING IS FILTERED.** No size gate, no shape gate, no confidence cut. A
one-pixel speck gets a row; a staff-line remnant gets a row; a barline gets a
row. Four mutation arms pin that directly. The reason is stage doctrine rather
than caution: a threshold here is a decision taken in the wrong stage, and it
is the one kind that cannot be revisited, because a row that was never created
is evidence no later rule can reconsider.

⚠️ **IT COULD NOT BE BUILT FROM THE DETECTION RECORD, AND THAT WAS RE-CHECKED
RATHER THAN INHERITED.** A-DUR-5's justification is that at the printed meter
the other staves *"carry no unclassified detection at that column"*. Measured
on today's tree at the cell the meter is actually printed in: **zero `timeSig*`
detections on any of the 17 staves**, and the non-span detections there cover
**0.00** of the component on 14 of them. There is nothing to re-weight.

⚠️ **THE PRECEDENT IS REUSED, NOT REINVENTED.** The span rule —
*a detection wider than a glyph can be is mostly paper and explains nothing* —
is `direction_text.BandConfig.max_blank_width_spaces`, **imported**, and a
mutation arm fails if it is restated as a literal.

---

## 2. REACH AND COST — first, because a zero here would end the job

```
Litolff Beethoven 5 p.62   rows 1244  refusals 0  staves 17  cells 221  detections 1440
                           prepare 3.6s   detect 12.6s   ink 1.84s
Breitkopf Brahms 1 p.1     rows 6055  refusals 0  staves 27  cells 202  detections 3951
                           prepare 6.6s   detect 14.7s   ink 2.55s
```

The ink pass costs **12-17% of the detector's own time on the same page** and
needs no model. `probe/ink_reach.py` prints reach before anything else and
**exits 2 declaring itself DEAD** if the gatherer produced no row — the
discipline every sibling arm in this repo has and `local_arm.sh` did not.

⚠️ **THE COST THAT IS NOT TIME IS RECORD SIZE, AND IT IS THE ONE A WHOLE-WORK
RUN WOULD FEEL.** A `Q.INK` row serialises to **529 bytes** (measured over 20
rows of the unit fixture), so the layer adds roughly **0.6 MB per Litolff page
and 3.1 MB per Breitkopf page** — and Breitkopf is the expensive one precisely
because its ink fragments (§3). Over a sixteen-page movement that is ~10 MB and
~50 MB against records this project already measures in the hundreds of MB.
**That is a real argument for the flag staying off by default** and for a
consumer being built before anyone turns it on for a whole work.

---

## 3. COMPOSITION — the whole population, nothing removed

⚠️ **THIS IS NOT A FALSE-POSITIVE RATE AND MUST NOT BE QUOTED AS ONE.** Staff
residue is not a false row; it is correctly gathered ink a later stage should
NAME. What follows is what the population *is*. The buckets are the probe's own
vocabulary — nothing under `tools/` knows them.

**Litolff Beethoven 5 p.62 — 1,244 rows**

| shape | rows | share | classified | unclassified |
|---|--:|--:|--:|--:|
| `mark_sized` | 840 | 67.5% | 284 | 556 |
| `vertical` (barline/stem/bracket) | 319 | 25.6% | 8 | 311 |
| `blob` (a merge, >=4x4 spaces) | 71 | 5.7% | 0 | 71 |
| `speck` (<0.25 spaces both ways) | 12 | 1.0% | 0 | 12 |
| `line_residue` (flat, >=2 spaces wide) | 2 | 0.2% | 0 | 2 |
| **total** | **1,244** | | **292** | **952** |

**Breitkopf Brahms 1 p.1 — 6,055 rows**

| shape | rows | share | classified | unclassified |
|---|--:|--:|--:|--:|
| `speck` | 3,395 | **56.1%** | 632 | 2,763 |
| `mark_sized` | 2,322 | 38.3% | 1,120 | 1,202 |
| `blob` | 252 | 4.2% | 1 | 251 |
| `vertical` | 70 | 1.2% | 2 | 68 |
| `line_residue` | 16 | 0.3% | 5 | 11 |
| **total** | **6,055** | | **1,760** | **4,295** |

⚠️⚠️ **THE COMPOSITION INVERTS BETWEEN PUBLISHERS AND THAT IS THE LARGEST
SURPRISE HERE.** Litolff yields **5.6 components per cell** and Breitkopf
**30**. The same reader over the same code produces a population of mostly
mark-sized objects on one plate and a population of mostly specks on the other.
CLAUDE.md already records these two documents at opposite ends of an ink axis
(Litolff *"low-res bitonal"*, 49 flag boxes and 35 dots; Breitkopf 371 and
656); this is that axis showing up in the ink itself.

⚠️ **STAFF RESIDUE DOES NOT COME OUT AS RESIDUE-SHAPED ROWS, AND I EXPECTED IT
TO.** `line_residue` is **2 rows of 1,244** on Litolff. That is not because the
residue is absent — measured separately, `remove_staff_lines` clears a median
**55%** of a Litolff cell's ink, so nearly half the line ink survives — it is
because the surviving residue is **connected to everything else**. It is inside
the `blob` and `mark_sized` rows, not beside them. §4.

---

## 4. ⚠️⚠️ A COMPONENT IS A PIECE OF INK, NOT A MARK — measured, and reported on the row

Measured over the 221 cells of Litolff p.62:

| | p05 | p50 | p95 |
|---|--:|--:|--:|
| components per cell | 2 | **4** | 13 |
| largest component's share of the cell's ink | 0.225 | **0.464** | 0.911 |
| staff-line ink cleared by `remove_staff_lines` | 0.296 | **0.550** | 0.742 |

So on this plate **the median cell's biggest component holds nearly half its
ink**, and on Breitkopf the failure runs the other way — one mark shatters into
many rows.

**This is reported, not repaired.** Every row carries `ink_n_components` and
`ink_share_of_cell` so a consumer can see when it is looking at a merge instead
of a mark. Repairing it would mean deciding where one mark ends, which is not
GATHER's business and is precisely the later-stage job this layer exists to
feed.

⚠️ **IT BOUNDS WHAT THE LAYER CAN CURRENTLY SUPPORT.** A rule that reads a
component AS A MARK is safe on the mark-sized 67.5% of a Litolff page and
unsafe on the 5.7% that are merges and on most of a Breitkopf page. A rule that
reads a component as *ink at this x* is safe on both — which is exactly the
alignment question, and is why the deliverable below is alignment and not a
shape verdict.

---

## 5. ALIGNMENT, AGAINST A NULL — the deliverable

The null is a **circular shift** of each staff's component x positions inside
its own cell span: it keeps every within-staff interval and every shape exactly
as printed and destroys **only the cross-staff phase**. That is the null
`adjudicate_onset_column` was measured against, and beating a re-draw would
only show that music is not uniform noise. 5 seeds.

The tolerance is `ONSET_COLUMN_TOLERANCE_SPACES` = **0.10 staff spaces**,
**imported**, because inventing a second notion of "same x" is exactly what
this probe must not do.

**Ratios below 1.00 mean MORE aligned than chance** (fewer columns are needed
to hold the same rows; fewer rows stand alone).

### Litolff Beethoven 5 p.62 — 17 staves, one system

| arm | rows | columns real/null | ratio | alone real/null | ratio |
|---|--:|---|--:|---|--:|
| all ink | 1,244 | 357 / 563.2 | **0.63** | 115 / 270.0 | **0.43** |
| **unclassified only** | 952 | 304 / 482.8 | **0.63** | 118 / 275.6 | **0.43** |
| shape `vertical` | 319 | 59 / 222.2 | **0.27** | 8 / 181.6 | **0.04** |
| shape `mark_sized` | 840 | 287 / 446.4 | 0.64 | 113 / 266.4 | 0.42 |
| shape `blob` | 71 | 42 / 55.2 | 0.76 | 24 / 45.4 | 0.53 |
| shape `speck` | 12 | — | — | — | too few, not scored |
| shape `line_residue` | 2 | — | — | — | too few, not scored |

✅ **THE CLAIM A-DUR-5 RESTS ON HOLDS: unclassified ink aligns exactly as
strongly as all ink** — 0.63 / 0.43 against 0.63 / 0.43. Unnamed ink is not
noise that happens to be left over; on this plate it lines up like the named
ink does.

✅ **AND THE RATIOS REPRODUCE `Q.ONSET_COLUMN`'S OWN FIGURES FROM A DIFFERENT
POPULATION.** That work measured 1.62× on columns and 2.29× on events standing
alone, i.e. **0.62 and 0.44 in this direction**, over NOTE EVENTS on a
different document. This arm reads **0.63 and 0.43** over INK COMPONENTS. Two
populations, two documents, two readers, the same numbers — which is the
strongest corroboration in this write-up and was not designed for.

✅ **THE GEOMETRY SEPARATES, IN THE ORDER SEAN PREDICTED.** `vertical` rows —
barlines, which run the system's height — are enormously more aligned than
chance (0.04 alone); `mark_sized` next; **`blob` weakest**, which is the result
agreeing with itself, since a merge has no well-defined x.

### Breitkopf Brahms 1 p.1 — 27 staves, two systems

| arm | rows | columns ratio | alone ratio |
|---|--:|--:|--:|
| all ink | 6,055 | **0.87** | **0.83** |
| unclassified only | 4,295 | 0.83 | 0.73 |
| shape `speck` | 3,395 | 0.83 | 0.72 |
| shape `mark_sized` | 2,322 | 0.78 | 0.62 |
| shape `blob` | 252 | 0.59 | 0.49 |
| shape `vertical` | 70 | 0.70 | 0.33 |

⚠️⚠️ **THE RESULT DOES NOT TRANSFER AT FULL STRENGTH, AND THE HONEST HEADLINE
IS THE PAIR, NOT THE BETTER HALF.** The ordering survives (`mark_sized` beats
`speck`; `vertical` is strongest by the *alone* measure) but every ratio is far
nearer chance, because **56% of the population is specks** and specks are
where ink fragments rather than where marks are.

⚠️ **WHAT IS NOT ESTABLISHED FOR THE SECOND PUBLISHER:** no crop was
adjudicated on it, so I cannot say whether a Breitkopf `mark_sized` row is a
mark. The Litolff target was hand-verified against the print; nothing on
Breitkopf was.

### ⚠️ A PROBE DEFECT THE SECOND PUBLISHER FOUND IMMEDIATELY

The first Brahms run keyed columns on the **cell index alone**. A cell index
RESTARTS at 0 on each system, so on a two-system page `cell 3` names two
different bars at two different page x, and pooling them puts unrelated ink in
one column span — which destroys alignment **by construction** and reads as
*"this publisher's ink does not line up"*. Litolff p.62 is one system and could
not expose it. Keyed on `(system, cell)`, Brahms's *alone* ratio goes
**0.94 → 0.83**. Same defect CLAUDE.md records for the duration arm's bar
figures; it is now a comment at the site.

### ⚠️ THE SHIPPED TOLERANCE DOES NOT CARRY A COLUMN ACROSS THIS PLATE

Reported, **and not acted on**. At the printed meter the same column's page x
drifts **13.9 px — 0.88 staff spaces — down the 17 staves**, which is the
plate's own warp:

| tolerance | widest column in the cell | columns in the cell |
|---|--:|--:|
| 0.05 sp (0.8 px) | 8 of 17 staves | 65 |
| **0.10 sp (1.6 px)** — the shipped value | **13 of 17** | 38 |
| 0.25 sp (3.9 px) | 15 of 17 | 21 |
| 0.50 sp (7.9 px) | **17 of 17** | 13 |
| 1.00 sp (15.8 px) | 17 of 17 | 6 |

⚠️ **MOVING THE CONSTANT ON THIS WOULD BE FITTING TO ONE PAGE**, and it belongs
to `adjudicate_onset_column`, which measured it against a null on a different
document. Recorded so whoever builds the consumer knows the tolerance is the
first thing they will have to argue about.

---

## 6. ⚠️⚠️ THE PRE-REGISTERED TARGET — and a correction to the record

**The target was fixed before anything was built**, because it is the case
A-DUR-5's whole justification rests on: *"At p.62 cell 8 the meter is printed on
every staff, we classify it on 2 of 17, and the other 15 carry no unclassified
detection at that column."*

### 6.1 The cell is wrong

Cropping the plate (`out/print/`, regenerated by `probe/print_evidence.py`):

* `p62-page.png` — page 62, seventeen staves, one system, bar `147` at
  top-left, a **double barline** about three fifths across under *Tempo I.*
* `p62-meter-change-six-staves.png` — that double barline at 400 dpi. A stacked
  **`3` over `4`** stands immediately after it **on every staff shown**.
* `p62-staff0-cells-4-to-9.png` — the pipeline's own cells. The double barline
  and the `3/4` are at the head of **cell 6**. Cells 7, 8 and 9 are rest bars.
* `p62-cell8-head-staves-0-5.png` — cell 8's head on six staves: **staff lines
  and nothing else.**
* `p62-cell6-head-staves-0-5.png` — cell 6's head on the same six: the `3/4` on
  every one.

### 6.2 And the `3/4` the pipeline reads is a barline

Every `timeSig*` detection on the page, with its box in staff spaces
(`probe/meter_cell.py`, shipped readers, no interpretation):

```
cell 8:
  staff  9 timeSig4 conf=0.259 x=0.00 w=0.33 h=1.26 sp   <- the cell's LEFT EDGE
  staff  9 timeSig4 conf=0.274 x=0.00 w=0.34 h=1.79 sp   <- the cell's LEFT EDGE
  staff  9 timeSig4 conf=0.330 x=0.00 w=0.36 h=1.17 sp   <- the cell's LEFT EDGE
  staff  9 timeSig4 conf=0.696 x=0.00 w=0.35 h=1.23 sp   <- the cell's LEFT EDGE
  staff 11 timeSig3 conf=0.269 x=0.00 w=0.35 h=2.08 sp   <- the cell's LEFT EDGE
  staff 11 timeSig4 conf=0.556 x=0.00 w=0.40 h=2.17 sp   <- the cell's LEFT EDGE
cell 6:  (none — on any of the 17 staves)
```

**Staff 11's `timeSig3` + `timeSig4` — the pair that makes the `3/4` — are two
vertically-adjacent fragments of ONE barline**, 0.35 and 0.40 spaces wide at
`x = 0`, at the head of an empty rest bar. `_meter_from_digits` needs two
stacked digits and a broken barline supplies exactly that.

⚠️⚠️ **WHY THIS MATTERS BEYOND THIS JOB.** p.62 is the one true scan-side meter
change this project has found, and it is cited as such in
`omr-staged-meter-boundary-2026-09/FINDINGS.md` (*"all four TRUE changes sit at
a non-last cell … Litolff p.62 cell 8 of 13"*), in
`omr-meter-corroboration-2026-09/FINDINGS.md` (*"we read it on ONE staff of
seventeen at support 3.0"*), and in the letter-meter section of CLAUDE.md. The
**bar** is real and the **cell index and the ink are not**.

⚠️⚠️ **AND IT INVERTS A CORRECTION THAT WAS ITSELF A CORRECTION.**
`omr-staged-meter-carry-2026-09/FINDINGS.md` §"CORRECTION TO §11" says the
bar-math anomaly at **cell 6** is *"two cells early"* and the glyph at cell 8 is
exact, concluding *"the glyph is the precise signal and the arithmetic is the
noisy corroborator, not the other way round."* Under the crops the bar math was
pointing at **the right bar** and the glyph at the wrong one.

⚠️ **WHAT IS NOT SETTLED: the BAR NUMBER.** The page prints `147` at its first
bar and the pipeline segments 13 cells, so cell 6 is the page's seventh bar;
the reference encodes the `3/4` change at bar 155. Reconciling those needs a
hand-verified `works.json` window row, which does not exist for this page, and
**nothing here should be read as a claim about it.**

### 6.3 The test itself — PASSED

`probe/target_cell.py`, at cell 6, window read off the print (a two-space-wide
stack spanning the staff, standing clear of the barline) and deliberately
generous:

```
  17 of 17 staves carry a row at the printed meter; 16 of 17 are UNCLASSIFIED
  page x spans 1740.6..1754.5 (13.9 px of drift down the plate)
```

The one "classified" row is staff 5, covered 0.52 by `noteheadBlackInSpace` +
`noteheadBlackOnLine` — **a misclassification of the meter, not a reading of
it**, which is exactly why `ink_explained_by` names the classes rather than
asserting what the ink is.

**So the record now contains a row for the printed meter on every staff, where
before it contained one on none of them.**

---

## 7. CONTROLS

**Flag OFF is byte-identical to `origin/main`** — `probe/flag_off_control.py`
loads `origin/main`'s `gather.py` as a module, runs it and this tree's twice
over the SAME prepared page with a **memoised detector** (so detector jitter
cannot enter), and md5s the serialised rows:

```
origin/main, flag absent : 8f8bf9ee595a190688b0e4107b33486f  rows 6564
this tree,  OMR_INK off  : 8f8bf9ee595a190688b0e4107b33486f  rows 6564
this tree,  OMR_INK=1    : ae4aeef8f49d35e2a3215be9a08f2802  rows 7808
positive control: the flag DOES change the log (+1244 rows)
```

⚠️ The comparison is against **main**, not against my own flag-on arm: the
latter proves only that the branch is taken and cannot see a row this change
added outside `gather_ink`.

**Mutation battery** — `mutate.py`, 19 arms, **19 red**, restore VERIFIED,
refuses a dirty tree, writes an in-flight sentinel. It covers the flag
direction, the erased image, the two no-filter guarantees, the span rule, the
coverage union, both frames, both abstentions, the key space, the merge
counters and the ordering edge, plus a **positive control in the same class**
(`it_never_writes_an_observation`), because every other arm makes the reader do
or say LESS and a battery of those passes by writing nothing.

⚠️ **The first run had one survivor and it was a real test gap.** Mutating
`ink_n_components = len(comps)` to `= 1` survived, because the merged fixture's
true value IS 1 — an **equivalent mutant on that fixture**. The counter is only
worth having if it can say TWO, so the separated cell is now asserted too.

**Derived checks**: `wiring --check`, `inventory --check`, `gather_coverage`
and `health --check` all exit 0 on this tree — and **all four were run again
with `origin/main`'s own `record.py`, `gather.py` and `wiring.py` checked out
in place, where they also exit 0**, because *"checks fail after a change"* and
*"checks were already failing"* look identical in a terminal. Main's wiring
reports **47 problems**; this tree reports 61, and 47 + 7 + 7 balances (§8).

**Unit tests**: `tools/omr/tests/test_staged_ink.py`, 25 tests, every fixture
drawn as pixels rather than mocked — a component test whose input is a
hand-written list of boxes tests the arithmetic and not the reader.

---

## 8. NO CONSUMER, DELIBERATELY — and the tool blind spot that surfaced

Nothing reads `Q.INK`. The brief was the producer only and the reason is
falsifiability: the deliverable of this job is a reach measurement, and a rule
reading the rows in the same change would move the very numbers being used to
decide whether the rows are worth having.

`wiring --check` **says so**: all seven always-written detail keys are reported
unread and are on `KNOWN_GAPS` as OPEN entries, each leaving the list the day a
decision reads it.

⚠️⚠️ **AND MAKING IT SAY SO EXPOSED TWO BLIND SPOTS IN THE TOOL — one
recorded and left open, one fixed because it made `--check` RED.**

**(a) A `**dict` SPLAT IS INVISIBLE TO IT, and that one is left open.**
`wiring.py`'s DETAIL question reads the AST for **literal keyword names**, so a
key passed as `**detail` is never seen. `gather_detections` has written
`bbox_page_px`, `x_center_page` and `y_center_page` through a splat since page
boxes arrived and **this tool has never reported one of them.** This reader
spells its unconditional keys out at the emit site so the gap is visible; the
conditional ones stay in a splat because they are DECLINED by omission, which
cannot be expressed as a literal kwarg. **Widening the scan to follow a dict
built in the same function is ranked next work and was NOT taken here.**

**(b) ⚠️⚠️ A BENCHMARK PROBE COUNTED AS A CONSUMER — THE THIRD INSTANCE OF A
FAMILY THE TOOL ALREADY DOCUMENTS TWICE, AND IT WAS CAUGHT BY `--check` GOING
RED IN THE FULL SUITE HAVING BEEN GREEN STANDALONE AN HOUR EARLIER.** The
moment this work's own probes were committed, **four of the seven `Q.INK`
entries were reported STALE — closed** — because a file under `benchmarks/` had
read them **to take the measurement those entries exist to describe**. The tool
already excludes a TEST ("a test naming a key is not a consumer of it") and its
OWN gap list ("the inventory written to account for the findings closed the
check that produced them"); a probe is the same thing. `_tree_of`'s own
docstring even argues the distinction for the PRODUCER question — *"collapsing
the three would have reported `roster` as fed the moment any probe passed
one"* — and that reasoning had simply not been applied here. **Fixed**:
`details()` now excludes the `benchmark` tree.

⚠️⚠️ **AND THE FIRST DRAFT OF THAT FIX'S COMMENT CLAIMED IT WAS CONFINED TO THE
FOUR `Q.INK` KEYS. IT WAS WRITTEN BEFORE THE MEASUREMENT AND IT IS FALSE** —
this repo's own *asserting a mechanism without measuring it*, committed by the
session that was writing up a measurement. Run, the exclusion surfaces **SEVEN
MORE keys, each written by `gather.py` and named in the whole tree only by a
probe**:

| key | what is unread |
|---|---|
| `Q.BRACKET_BLOCK.n_blocks` | how many family blocks a system was cut into — the question `BRACKET_COLUMN_MIN_EVIDENCE` exists to make answerable |
| `Q.DIRECTION_WORD.gate` | why the scan gate skipped this page (the abstention is consumed, the reason is not) |
| `Q.DIRECTION_WORD.readers_run` | which OCR rungs ran — half of what the ranked "two rungs as independent readings" step needs |
| `Q.GLYPH_BAND_DISTANCE.own` | the contested/uncontested split, re-derived by the adjudicator instead of read |
| `Q.GLYPH_LADDER.found` | how many ledger rungs were SEEN against `expected`; the value is only the boolean |
| `Q.MARGIN_LABEL.y_center_px` | the evidence the label→staff assignment was made on |
| `Q.STAFF_SKEW.thickness_px` | a page-level line thickness nothing compares against the per-cell one |

**They are not new faults; they were invisible.** Each is now inventoried with
its reason. `--check`: **61 problems, 0 unaccounted, 0 stale, exit 0** — against
47 / 0 / 0 on `origin/main`'s own files, which is 47 + 7 (`Q.INK`) + 7 (newly
visible) and balances exactly.

---

## 9. ⚠️ WHAT IS **NOT** ESTABLISHED

* **Accuracy, except at the one target.** 17 of 17 rows at the printed meter
  were checked against the print. **Nothing else was.** The other 1,227 rows on
  that page, and all 6,055 on Brahms, are unadjudicated.
* **That a row is a MARK.** §4 measures the opposite: the median Litolff cell
  yields four components and its largest holds 46% of the cell's ink, while
  Breitkopf yields thirty. **Neither plate gives one row per mark.**
* **That the alignment generalises.** Two documents, two publishers, two pages,
  and the second is much weaker. No engraved page was measured at all.
* **A residue separation.** Sean's fourth point — residue aligns with the STAFF
  LINES while a mark aligns ACROSS STAVES — **could not be tested**, because
  residue does not come out as residue-shaped rows on either plate (2 and 16
  rows of 1,244 and 6,055). What the shape arms DO show is that the more merged
  a row is, the less it aligns, which is consistent with the claim and is not
  it.
* **Any effect on a file.** No MusicXML was exported, no OMR-NED figure is
  claimed, no decision changed. Flag-off is byte-identical by construction.
* **The bar number on p.62** (§6.2).
* **`readjudicate.py` and `reexport_arm.py` are STRUCTURALLY BLIND to this
  change.** They rebuild from a saved record, so a new quantity never enters.
  Only two full re-gathers can price a GATHER change, and **a zero from either
  of those tools is not evidence about this one.**

---

## 10. RANKED NEXT WORK

1. **The residue adjudicator — a DECISION, at ADJUDICATE, over `Q.INK`.** It is
   the job Sean's second correction names, and it now has a population to
   decide over. What it would need that this layer already supplies: the shape
   (`width_spaces`, `height_spaces`, `ink_fill`), the merge warning
   (`ink_n_components`, `ink_share_of_cell`), and the page frame. What it would
   need and **does not have**: the cell's own staff-line rows in the row's
   frame, so that *"this ink lies along a line"* is askable. That is one more
   detail key, not a new quantity.
2. **The cell-6/cell-8 correction, followed into the meter thread.** §6 is a
   fact about ink and cell indices; what it does to the cautionary rule, the
   corroboration guard and `METER_CHANGE_FLOOR` is unmeasured. The cheap first
   question: does `adjudicate_meter` still find a change at cell 8 today, and
   at what support?
3. **A third publisher**, and an ENGRAVED page. The composition inverted
   between two scans; an engraving is where the component representation should
   be at its best and has not been looked at once.
4. **Widen `wiring.py`'s DETAIL scan to follow a `**dict` splat** (§8a) —
   still open, and it is the half of that tool's blind spot this change did not
   touch. The seven keys §8b surfaced are each their own small job.
5. **The seven newly visible detail keys** (§8b), in the order a consumer wants
   them: `Q.GLYPH_LADDER.found` first, because the COMPLETENESS-only rule it
   would let someone revisit is a measured refusal and the count is the
   evidence that refusal rests on.
6. ⚠️ **Not ranked: moving `ONSET_COLUMN_TOLERANCE_SPACES`.** §5 shows it does
   not carry a column across this plate. It is the right thing to argue about
   and the wrong thing to change from one page.

---

## 11. HOW TO RE-RUN

```bash
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf

python3 benchmarks/omr-ink-gather-2026-09/probe/ink_reach.py "$PDF" 62 --cell 6 --system 0
python3 benchmarks/omr-ink-gather-2026-09/probe/target_cell.py "$PDF" 62 --cell 6
python3 benchmarks/omr-ink-gather-2026-09/probe/meter_cell.py  "$PDF" 62
python3 benchmarks/omr-ink-gather-2026-09/probe/flag_off_control.py "$PDF" 62
python3 benchmarks/omr-ink-gather-2026-09/probe/print_evidence.py "$PDF"
python3 benchmarks/omr-ink-gather-2026-09/mutate.py
```

⚠️ Needs weights and `library/`; a cloud container has neither. In a worktree,
symlink `omr-weights/`, `library/` and `tools/omr/training/data/weights` from
the main checkout first — three of the four symlinks CLAUDE.md names fail on
the scan side only.
