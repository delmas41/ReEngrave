# `Q.INK` — the ink is the population, and classification is an attribute

2026-09-17. `A-DUR-5`, Sean's standing request since 2026-09-09, built as the
**PRODUCER ONLY**. `OMR_INK`, ~~**default OFF**, allow-list~~ —
⚠️⚠️ **CORRECTED 2026-09-17 EVENING AND WRONG ABOUT BOTH HALVES: the flag
is DEFAULT ON (Sean's call, same day) and the predicate is a DENY-list**,
which is what CLAUDE.md's *"A flag's OFF test must follow its DEFAULT"*
requires of a default-ON flag. The line is struck rather than deleted
because it is what four other ledgers copied, and because it cost a later
session a killed 15-minute gather. Now derived-checked by
`tools/omr/tests/test_flag_docs_match_predicates.py`. Everything measured
below is unaffected — the arms named their flags explicitly.

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
key passed as `**detail` never enters the WRITTEN inventory at all — and a key
the tool does not know is written can never be reported unread, whoever reads
it. Checked exactly rather than asserted: `Q.GLYPH_BOX.bbox_page_px`,
`Q.GLYPH_BOX.x_center_page` and `Q.GLYPH_BOX.category` are **absent from all
138 written pairs**, because `gather_detections` passes them as `**box_detail`.
⚠️ The bare NAMES do appear, from other gatherers that spell them out — so the
blind spot is per `(quantity, key)` PAIR, which is the grain this question
reports in. This reader
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

## 12. Roadmap 1.1b, second half — `arc_owner`'s `considered` is three copies of one set, and the fix is spelling (2026-09-22)

The first half of 1.1b (compact JSON, `6b7dd3a3`) left Breitkopf at 59.3
MB/page against a 20 MB/page budget and named `arc_owner`'s `considered`
lists as the remaining 75 %. This section measured WHAT in those verdicts is
large, whether the content can change, and what a spelling change buys.

### 12.1 Per FIELD, not per quantity

`byte_share.py` sizes a verdict whole. Splitting an `arc_owner` verdict by
field on the two compact shared records (probe: `pool_control.py`'s
predecessor, streamed with `ijson`; numbers are compact-JSON bytes):

| field | Breitkopf (2,207 verdicts) | Litolff (779 verdicts) |
|---|---|---|
| `basis` | 68.0 MB · 37.1 % | 16.9 MB · 37.7 % |
| `correlated` | 56.9 MB · 31.0 % | 13.7 MB · 30.7 % |
| `considered` | 56.8 MB · 31.0 % | 13.7 MB · 30.6 % |
| `detail` | 0.75 MB · 0.4 % | 0.19 MB · 0.4 % |
| everything else | < 0.2 MB | < 0.1 MB |

So the verdict is **99.2 % three id lists**, and they are the SAME ids three
times: `considered` (median 1,828 ids on Breitkopf, 1,600 on Litolff),
`basis` = `considered` ∪ closures (median 2,381 / 2,063), and `correlated`
= the same rows regrouped by `(reader, frame, quantity)` (median 1,827 /
1,599 ids in ~10 / ~18 groups). Per verdict the ids are ~1,777 `glyph_box`
rows, ~14 `staff_spacing`, ~8 `glyph_owner` verdicts and the 1 `arc_box`
(Breitkopf; Litolff 755 / 12 / 2 / 1).

**`considered − used` is IDENTICAL for every arc in a system**: exactly one
distinct set per system on both documents (7 systems each). That is
`adjudicate_arc_owner` reading `ev.rows(Q.GLYPH_BOX, scope=SELF_AND_DESCENDANTS,
subject=system)` once per arc, as its rival-staff rule requires, and the
harness recording that read faithfully. `wedge_anchor` has the same shape at
smaller scale (47 verdicts, 80 KB each, 35 / 32 / 32 %).

### 12.2 The content cannot shrink; the spelling can

The three fields are harness-computed (`adjudicate_one`), and `basis` is
load-bearing: `Log.closure` walks it, and `Evidence._admit`'s circularity
filter reads that closure, so a later decision that reads an `arc_owner`
verdict would see a different closure if `basis` were cut. Narrowing the
read itself (form 1 in the roadmap row) is an algorithm change to the rival
search and was not attempted. Recording the population as a "count plus a
query" would change `Verdict` and every consumer.

What was done instead: `tools/omr/staged/record_io.py` pools the lists **in
the file only**. Verdicts of one quantity, one decider and one system share
a core; each verdict's list is written as a reference to the core plus its
private ids at their positions (`{"$pool": id, "ins": [[0, "obs:005283"]]}`),
`correlated`'s inner groups are interned by content, and `record.pools`
holds each core once. `Log`, `Verdict`, `Evidence`, every stage, and the
in-memory `result` dict the CLI hands `--musicxml` are untouched.
`load_record` expands a file back to exactly the dict `Log.to_json`
produced; a list under 64 ids or a group of one is written inline exactly
as before, so every test fixture's record is byte-for-byte what it was.

### 12.3 Result

`pool_control.py` on the two compact shared records:

| document | compact (1.1b first half) | pooled | per page |
|---|---|---|---|
| Litolff `beethoven5-p1-p4-ink-identity-slim` | 75.0 MB | **32.2 MB** (42.9 %) | 18.8 → **8.0 MB/page** |
| Breitkopf `brahms1-breitkopf-p0-p3-ink-slim` | 237.3 MB | **52.7 MB** (22.2 %) | 59.3 → **13.2 MB/page** |

Against the original `indent=2` files (146.4 / 461.1 MB) that is 22 % and
11 %. Both acceptance scans are under the 20 MB/page budget. Pooling costs
0.9 s / 2.7 s at write time including the self-check, against a 93 s/page
gather. On the pooled Breitkopf the largest quantity is now `duration` at
9.7 MB (18.8 %), then `arc_kind` 5.1 MB, `glyph_box` 4.6 MB,
`stem_direction` 4.4 MB, `arc_owner` 3.3 MB (6.5 %): no single lever above a
fifth of the file.

### 12.4 Controls, each able to fail

1. **The writer checks itself**: `pool_id_lists` expands its own output and
   raises `PoolMismatch` unless every pooled field deep-equals the input.
   `test_record_pools.py` breaks `_decode` and watches it raise.
2. **`expand(pool(record)) == record`, every key**, on both real records —
   and, in the same run, bare `json.loads` of the pooled text is REQUIRED to
   differ from the original (89 / 100 pools written), so the equality was
   won by expansion and not by a writer that pooled nothing.
3. **`trace --run <pooled> --empty-claims` is byte-identical** to the
   original on both documents (the first half's own control), through the
   routed loader; a per-subject trace of an `arc_owner` verdict on the
   pooled file reads its full considered count.
4. **A dangling reference raises** rather than reading as an empty list.
5. `record_slim.convert` on a pooled file copies `pools` and the references
   through verbatim (tested); `positional_store.stream_observations` never
   sees them (observations are not pooled).
6. `check`: open findings unchanged at 255; fast tier green (see the
   roadmap row for the counts).

### 12.5 Blast radius, enumerated rather than feared

The roadmap row worried that "every `benchmarks/*/*.py` script that parses a
raw verdict dict" was in scope. Separating readers of a verdict's VALUE from
readers of its three id-list fields bounds it: a pooled file differs from an
unpooled one in `considered`, `basis`, `correlated` and the added
`record.pools` key, nothing else. Readers of those fields, all routed through
`record_io.load_record`: `trace.py`, `brakes.py`; `reinfer.py`,
`probe/reach.py` (infer-stage), `probe/edges.py` (plumbing),
`dynamics_arm.py` (dedupe), `summarize.py` (meter-boundary),
`readjudicate.py` (duration-beams); plus the loaders that hand a record to
a consumer (`export`/`lilypond` CLIs, `inventory`, `wiring.with_run`,
`acceptance`, `factsheet`). `byte_share.py` now counts `record.pools` as its
own row. The ~90 other benchmark scripts read verdict values only and are
unaffected by construction.

### 12.6 Not established, and one thing noticed

- Whole-movement pages were not measured (the 1.1 gathers are the first
  data); a page denser in arcs than Breitkopf p0–p3 is bounded by the pooled
  form's per-system core, not per-arc, so density in ARCS no longer scales
  the file — density in NOTES does, through `duration` and `glyph_box`.
- `Evidence.correlated_groups` is O(n²) over `_seen`: ~1,800² pair tests per
  `arc_owner` verdict, 2,207 verdicts on Breitkopf. That is an ADJUDICATE
  wall-time cost, not a size one, and was NOT measured here. It is the
  natural next question if a whole-movement adjudicate is slow.

## 13. ROADMAP 2.4c — the first consumer lands: an UNREAD MARK

2026-09-28. `A-DUR-5`'s own text named the shape this rung would need: *"we
know what this blob is in 3 of the 10 systems and they all line up."*
`Q.ONSET_COLUMN` is that alignment, already built and already measured
against a null (SS5 above); this is the decision that reads both of them
together. `adjudicators/unread_mark.py`, registered in `adjudicate.ORDER`
right after `Q.ONSET_COLUMN` (its one dependency).

### 13.1 REACH FIRST — the two shared whole-movement records hold no
component boxes at all

Before anything else: does `library/_shared-records/beethoven5-litolff-
mvt1-whole-20260923.record.json` and `brahms1-breitkopf-mvt1-whole-
20260923.record.json` carry the per-component form this decision needs?
Grepped directly (`grep -o ink_bbox_canonical | wc -l`, the one key that
tells the two `Q.INK` forms apart): **0 occurrences in either file**, against
5,270 / 6,685 occurrences of `ink_total_area_px` (the SUMMARY form's own key,
one row per CELL). Both whole-movement records were gathered under
roadmap 1.1's default (`component_rows=False`), which drops the box and
keeps only the aggregate — exactly what SS3 above (`gather_ink`'s own
docstring) says it would. **So this decision's own compatibility test
(`test_an_old_record_without_ink_rows_abstains_and_does_not_crash`) is not
a hypothetical: it is the shape of every record this project has committed
so far**, and a whole-movement run needs `--ink-rows` before this decision
can see anything on it at all — a real cost (SS2 above: the schema switch
alone is ~3-4% of a record; `--ink-rows` also loses roadmap 1.1b's slimming).

So REACH was measured on ONE FRESH PAGE per acceptance scan instead, gathered
with `--ink-rows --no-surya --no-ocr` (another session held the Surya
server), weights `hollow-graft-shift09-2026-09-04`: Litolff Beethoven 5 pdf
page 3 (2 systems, 19 staves), Breitkopf Brahms 1 pdf page 1 (2 systems, 27
staves). Population, per the brief, component-by-component:

| | Litolff p3 | Breitkopf p1 |
|---|--:|--:|
| total `Q.INK` component rows | 1,780 | 6,055 |
| (a) zero detector coverage | 809 | 3,655 |
| (b) of those, notehead-sized (`[1.0, 1.8] x [0.34, 1.8]` staff spaces — floor imported from `notehead_precision.TOO_NARROW_MIN_SPACES`, ceiling from `omr-notehead-width-2026-09`'s own measured p5–p95 band) | 38 | 107 |
| (c) of those, at a column `Q.ONSET_COLUMN` already calls corroborated (`n_witness >= 2`, this component's own staff not among the witnesses) | **7** | **21** |

**Non-zero on both pages — not DEAD AT ZERO.** ⚠️⚠️ **(c) WAS MEASURED
TWICE, AND THE FIRST NUMBER WAS WRONG BY A FRAME-MIXING BUG THIS PROJECT HAS
NAMED BEFORE.** The first pass (and the first draft of the decision itself)
converted `ONSET_COLUMN_TOLERANCE_SPACES` to pixels using `Q.INK`'s own
`cell_staff_space_px` — which is the component's CANONICAL-frame unit
(`gather_ink` measures it off `cell.image_no_staff`, the rescaled crop),
not the PAGE-frame unit every other quantity in this test is expressed in
(`bbox_page_px`, `Q.CELL_BOX`, `Q.STAFF_LINES`, `Q.ONSET_COLUMN`'s own
`x_page`). On Litolff that canonical unit is 100.0px against a real
page-frame `Q.STAFF_SPACING` of **15.75px** — a 6.3x error — and the
raw (wrong-unit) pass reported (c) = 13 / 37. Caught by a test that
fabricated the exact shape (`test_the_SAME_component_at_an_uncorroborated_x_
does_not_fire` passing for the wrong reason), then confirmed by hand on
`cell/3/0/2/5`: a real candidate sitting 9.14 page-px from its nearest
column, comfortably inside the wrong 10px tolerance and comfortably outside
the right 1.575px one. `Q.ONSET_COLUMN`'s own `_system_spacing` reads
`Q.STAFF_SPACING` for exactly this reason; the fix here is CONNECT, not a
new measurement — read the same quantity the sibling decision already reads.
The table above is the CORRECTED (c).

### 13.2 The rule, and its stage

**ADJUDICATE** (`adjudicate_unread_mark`, `Q.UNREAD_MARK`, scope CELL,
`subjects_from=Q.INK`): decided `True` ("unread_mark") where at least one
component in the bar passes zero-coverage, notehead-sized and corroborated-
column AND neither guard excludes it; decided `False` ("no_mark") where the
component-form data was present and nothing in the bar qualifies (an ANSWER,
`notehead_is_not_a_notehead`'s own reasoning for its False branch); abstains
only where the INPUT is missing (`no_ink_component_rows`, `no_onset_column`,
`no_page_frame`). The value is a bare `True`/`False` — no pitch, no
duration, no class is ever written; `detail` names the triggering component,
its size, and the column that corroborated it.

Two guards, both stated as CONVENTION ASSUMED / NOT PRINT-CONFIRMED (nobody
was available to ask, CLAUDE.md rule 3), narrower than the notehead-sized
window so they cannot swallow it:

- **touches a barline** — `measure_extractor.py`: a cell is bounded by its
  own adjacent barlines, so `Q.CELL_BOX`'s edge IS the barline; a component
  within 0.5 staff spaces of it is excluded (a SHATTERING plate's barline
  fragment). Fired on 3 of Breitkopf's 21 candidates, 0 of Litolff's 7.
- **lies on a staff line's y** — a component both short (inside the
  notehead floor but well under a genuine note's own height) and centred on
  one of `Q.STAFF_LINES`' five values is excluded (a MERGING plate's line
  residue). Fired on 0 of the 28 real candidates on either page — reported
  here as UNEXERCISED ON REAL DATA rather than omitted, exactly the
  discipline `Verdict.correlated`'s own dead-arm history asks for.

### 13.3 What fired

**Litolff p3: 7 of 7 corroborated candidates fire** (0 guard exclusions, 0
duplicate-cell collapses). **Breitkopf p1: 16 of 21** (3 barline exclusions,
2 candidate pairs sharing one cell collapse to one verdict each, since a
decision fires once per BAR not once per component). Zero abstentions on
either page once component rows exist — every bar with any ink tested clean.

### 13.3b ⚠️⚠️ THE CROP PASS FOUND THE DOMINANT FAILURE MODE, AND IT IS NOT
EITHER GUARD

This is my own read while cutting the crops, for quality control before
handing them to Sean — not a recorded verdict, and not a substitute for his.
**Breitkopf: 6 of 6 crops cut are printed DIRECTION-WORD TEXT, not notes**
— `espr.`, `arco` (twice), `unis.` (twice) and a dynamic `p` — every one a
word or letter sitting above or below the staff, at a column another staff's
REAL note corroborates by coincidence (these directive words are commonly
printed at a beat that also carries a note in a nearby part). **Litolff: 5
of 6 look like plausible real noteheads** sitting cleanly on the staff's own
second line; the sixth (`cell/3/0/1/3`) sits in dense, ornate ink between
two staves and is genuinely ambiguous — see its own crop note below.

**Why neither guard catches the text.** `ink_detector_coverage` — the
"zero coverage" test itself — is computed only from the YOLO detector's own
boxes (`gather_ink`'s `detections` argument); a direction word is read by a
completely different subsystem (`gather_direction_words`, Surya/Tesseract
OCR over an ink-minus-detections band) that writes `Q.DIRECTION_WORD`, never
a detector box. So a word's ink is "zero coverage" to this rule NO MATTER
WHETHER SURYA RAN — disabling it for this measurement (`--no-surya --no-ocr`,
REACH FIRST's own instruction) is not the cause. Neither the barline guard
nor the staff-line guard has any reason to fire on a normal printed letter
sitting cleanly above a staff. **This decision, as built, has no way to
tell a letterform from a notehead by shape alone at the sizes involved** —
"espr." and "arco"'s individual letters routinely fall inside the same
1.0–1.8 x 0.34–1.8 staff-space window a real head does (SS13.2's own table).

**This was the OPEN QUESTION, and it did not exist as a testable population
until this crop pass ran.** Manager review (2026-09-28) asked for the cheapest
CONNECT — excluding a component overlapping a `Q.DIRECTION_WORD` or
`Q.DYNAMIC_LETTER` region — built and PRICED; see SS13.9. Until then, and
still true of the residue SS13.9 measures: this decision's fired verdicts on
a plate with heavy direction-text (Breitkopf, and likely any full orchestral
score) run heavily toward printed words, not missed notes, and the two
acceptance documents diverge sharply enough (0/6 vs 5/6 plausible on the
crop sample) that this is a PLATE fact, not a tuning question — exactly
CLAUDE.md's own axis (Litolff MERGES, Breitkopf SHATTERS) showing up a
second time, in a population this project had not yet tested. Manager
review also required the hold-out itself to go RECORD-ONLY
(`export.UNREAD_MARK_HOLDS_OUT = False`) until this population is trusted —
see SS13.4's rewrite.

### 13.4 EXPORT — RECORD-ONLY until print-checked (manager review 2026-09-28)

⚠️⚠️ **REVISED. The original landing held the bar out live; manager review
reverted that** for the reason SS13.3b measures: a held-out bar throws away
notes that were read CORRECTLY, and 6 of 6 Breitkopf crops turned out to be
printed text, not missed notes — rule 5, print before default, cuts against
shipping a hold-out this population has not earned.

`export.UNREAD_MARK_HOLDS_OUT` — a MODULE CONSTANT, `notehead_precision.
UNLADDERED_SHIPS`'s own pattern, never an env flag — defaults `False`. With
it `False`: `adjudicate_unread_mark` still fires exactly as before (nothing
in ADJUDICATE changed), and `export.py` still RECORDS every bar it fires on
— `report["possibly_unread_mark"]` (`bars`, `holds_out`, the full `marked`
list, each entry's own `held_out` flag) — but the bar's notes are written
UNCHANGED, exactly as if no mark existed. The full hold-out branch (`_mxl_
empty_measure`, `bars_held_out_unread_mark`, `notes_held_out_unread_mark`,
the `possibly_unread_mark` refusal name, all unchanged from the original
landing) is fully built and kept alive behind the constant, proved by
`TestTheHoldOutBranchStillWorksWhenTrusted`, which flips it in-process.
`report["bars_held_out_unread_mark"]["held"]` is the (today, empty)
`held_out=True` subset of `marked`, so the two report keys read consistently
whichever way the constant is set.

⚠️ **A STATED SCOPE LIMIT, NOT AN OVERSIGHT** (unchanged by the record-only
revision, since it concerns the HOLD-OUT branch's own accounting): the six
SECONDARY family accounts (`arcs`/`ties`, `articulations`, `dot_role`,
`ornaments`, `wedges`, `fermatas`) fold an unread-mark hold-out's marks into
2.8's own `bar_does_not_add_up` bucket rather than getting a seventh named
bucket apiece — forking six family-accounting sites was out of scope for
this lane. Every one of those families' own accounting EQUALITY still
balances; only the stated REASON is imprecise where the two mechanisms
coincide with a mark on a chord/tie/dynamic, and only once the constant is
trusted to run.

### 13.5 Tests, RED first

`tools/omr/tests/test_staged_unread_mark.py`, 20 tests across four classes.
RED confirmed by inspection rather than a literal old-tree run (worktree
hygiene: this branch never held the pre-2.4c tree): `git show origin/main:
tools/omr/staged/record.py | grep -c UNREAD_MARK` returns 0, so code shaped
like `adjudicate.REGISTRY[Q.UNREAD_MARK]` fails at collection with
`AttributeError` before this lane's commits, exactly as importing
`adjudicators.unread_mark` does (`ModuleNotFoundError`).

* `TestTheAdjudicateDecision` (9): the population test, its negative control
  at an uncorroborated x (CLAUDE.md rule 7 — and the control that caught the
  frame-mixing bug above), the too-few-witnesses control, the covered-
  component control, the size-window control, both original guard tests
  (each with its own dead-threshold bug found and fixed mid-lane), and the
  old-record compatibility case.
* `TestTheDirectionTextGuard` (4): a component inside a direction-word box
  is not marked, the SAME component with no word box IS marked (the control
  that can fail), a non-overlapping word box does not blanket-exclude, and
  the `Q.DYNAMIC_LETTER` half of the guard.
* `TestExport` (4): by default a decided mark is RECORDED but the bar's
  notes are written unchanged; the no-mark negative control; the decided-
  `False` control; the bar-sum-already-claimed-it case is not also recorded.
* `TestTheHoldOutBranchStillWorksWhenTrusted` (3): flipping
  `UNREAD_MARK_HOLDS_OUT` to `True` in-process reproduces the original
  landing's hold-out exactly (own refusal name, own counters, the two
  report keys agree), it is still not confused with the bar-sum refusal, and
  the flip does not leak into a later call that never set it.

### 13.6 Landing numbers

Two landings on this branch: the original (hold-out live, 14 tests) and the
manager-review revision (record-only + text guard, 20 tests). Numbers below
are the REVISION's.

`pytest tools/omr/tests -m "not slow" -q`: 3,447 passed, 3 skipped, 0 failed
(this branch's own test file contributes 20 of those; the origin/main
fast-tier count was not separately measured, only `staged.check`'s baseline
was, via `git stash` below). `staged.check`: origin/main baseline measured
at **253** (via `git stash`, not assumed); this branch reports **251**,
unchanged by the revision — `staged.reach` and `staged.wiring` each lose one
entry (`Q.INK`, `DETAIL Q.INK.ink_bbox_canonical`) because this decision is
the consumer both were waiting for, per each entry's own "LEAVES THIS LIST
the day a decision reads it" clause; `staged.health` gains and then loses
one EMPTY CELL (`unread_mark` — a scanner-visibility fix in the test file's
own `_decide` helper, not a real gap, see its comment). Adding
`Q.DIRECTION_WORD`/`Q.DYNAMIC_LETTER` to `wants` opened no new inventory or
wiring gap (both are already-consumed GATHER quantities elsewhere). **N
fell, and stayed fallen.**

### 13.7 Crops

12 crops cut (6 Litolff, 6 of 16 Breitkopf, `benchmarks/omr-ink-gather-2026-
09/probe/crop_unread_mark.py`, self-contained — re-gathers the one page
in-process rather than depending on a saved multi-MB record file), under
`out/print/u24c-<label>-cell-<page>-<system>-<staff>-<cell>.png` with a
`.json` sidecar per tile (`VERDICT_none_yet: null`). Each crop draws the
flagged staff's own `Q.STAFF_LINES` (blue), the corroborated column's x
(green dashed), and corner brackets on the exact flagged ink component
(red), labelled `p/sys/staff/cell` in the corner — `feedback_send_sean_the_
crop`'s own rule: never crop between two staves, never leave the subject
unnamed. Sean adjudicates; this job does not claim their accuracy.

⚠️ **THE 6 PER PAGE ARE THE FIRST 6 BY SUBJECT KEY (STAFF, THEN CELL), NOT A
RANDOM OR STRATIFIED SAMPLE.** On Breitkopf that sorts toward the lower
strings (staves 8–12), which is exactly where `arco`/`pizz.`/`unis.`
markings cluster on an orchestral page — so SS13.3b's 6-of-6 text rate may
overstate the true-population rate on the other 10 fired bars this pass did
not crop. The opposite bias is just as real: a stratified or random sample
was not built here, so neither number should be quoted past "the two plates
disagree sharply on this small sample."

### 13.9 The text guard, built AND priced (manager review 2026-09-28)

The third guard: exclude a component whose page box overlaps a
`Q.DIRECTION_WORD` (a word Surya/Tesseract actually READ and the lexicon
accepted) or `Q.DYNAMIC_LETTER` (a detected `dynamicPiano`/etc glyph)
observation anywhere on the SAME SYSTEM. Both are CONNECTED, not
re-derived — the same discipline `Q.ONSET_COLUMN` itself is read under.

⚠️⚠️ **THE PLAN WAS WRONG, AND IT WAS WRONG BEFORE ANY CODE RAN.** The
instruction going in was that this could only be unit-tested tonight,
because the reach gathers ran `--no-surya --no-ocr` to leave the shared
Surya server alone. Checked against the tree: **`--no-surya`/`--no-ocr` gate
only `gather_margin_labels`** (the instrument-name reader, `staff_labels_
surya`/`staff_labels_tesseract`); `gather_direction_words` takes no such
parameter and calls Surya UNCONDITIONALLY (`gather.py:3747` on). Both saved
gathers from SS13.1 therefore already carry real `Q.DIRECTION_WORD` rows —
Breitkopf: 8 accepted words of 205 candidates (the other 197 `no_reading`
abstentions); Litolff: similarly abstention-heavy. **No new Surya call was
made** to get the numbers below — only a re-read of data this session had
already produced, honouring "do not start a Surya gather" while still
pricing the guard rather than leaving it a promise.

**Re-adjudicating both saved records with the guard added:**

| | before (SS13.3) | after | excluded |
|---|--:|--:|--:|
| Litolff p3 | 7 | **7** | 0 |
| Breitkopf p1 | 16 | **11** | 5 |

The 5 excluded on Breitkopf are `cell/1/0/1/3`, `cell/1/0/10/1`,
`cell/1/0/12/3`, `cell/1/1/2/0`, `cell/1/1/8/0`. The first three are
INDEPENDENTLY CONFIRMED by eye in the SS13.3b crop pass as `espr.`, `unis.`
and `arco` — the guard removed exactly the bars a human already read as
text, not an unrelated set. Litolff's 0 exclusions are consistent with
SS13.3b's own read (5 of 6 Litolff crops looked like real noteheads; there
was little text to connect to on that page).

⚠️⚠️ **AND IT IS MEASURABLY A PARTIAL FIX.** `cell/1/0/10/3` and
`cell/1/0/11/3` — BOTH independently confirmed by eye as printed text
(`espr. arco` and `arco`, the SAME crop pass) — are STILL AMONG THE 11 THAT
FIRE after the guard. Their ink sits where a word is printed, but no
`Q.DIRECTION_WORD` OBSERVATION covers that exact box: the reader's own
lexicon gate is deliberately narrow (CLAUDE.md: "never loosen") and on this
page it abstains `no_reading`/`not_in_lexicon` on the large majority of
candidates, so a genuine word the OCR/lexicon chain did not accept leaves no
box for this guard to connect to. **The guard inherits the direction-text
reader's own recall ceiling; it does not exceed it.** The 11 still-fired
Breitkopf bars must not be read as "cleared" by the guard's silence — several
are very likely more unrecognised text, not missed notes, and only a human
crop review (or a recall-side fix to the direction-text reader itself, out
of scope here) can tell which.

**What this changes and does not change.** It does not change the decision
to ship record-only (SS13.4): a guard that removes under a third of one
page's measured false positives, on a REACH-ONLY page pair rather than the
committed acceptance set, is not grounds for trusting the hold-out live. It
DOES mean the next step is sharper than "gather with Surya and see" — the
data already shows the guard helps and is incomplete, so the next step is
either widening the lexicon/recall on this page's specific vocabulary or
finding a shape-side signal (text is usually laid out in a straight
baseline row at fixed letter spacing; a single isolated notehead is not) to
catch what OCR recall misses.

### 13.8 Not established

- The direction-text guard (SS13.9) is priced only on two REACH pages, not
  the committed acceptance set, and even there removes fewer than half of
  the measured Breitkopf false positives (recall-limited, not shape-limited)
  — the residue is the new ranked #1, not a closed question.
- The two guards' exact tolerances are asserted, not print-measured (SS13.2).
- Whole-movement reach: not measured. `--ink-rows` costs the roadmap-1.1b
  slimming AND the schema switch (SS2 above), so a real whole-movement run
  needs the ink-summary persisted ALONGSIDE a decision-time re-derivation, or
  a second full gather pass — unbuilt.
- The `on_a_staff_line` guard fired zero times on 28 real candidates; it is
  shape-plausible (SS4/SS10) and untested against a real staff-line-residue
  case that also happens to be notehead-sized and corroborated. A crop pass
  that finds one would be the first real exercise of it.
- Cross-staff bleed (CLAUDE.md's measure-cell-padding note, SS10) is not
  separately guarded: a component that is genuinely the NEIGHBOUR staff's
  ink, reaching into this cell's vertical padding, would need to be far
  enough from every `Q.STAFF_LINES` value to dodge the sliver guard and
  still land in the notehead-sized window — plausible on a crowded page,
  unmeasured here. The crops are the instrument for finding one.

## 14. ROADMAP 2.52 — a whole rest the detector never boxed, found by search

Sean / `docs/DECISIONS.md` 2026-10-01: *"If a bar has no notes it should
expect to find a whole note rest and look in the middle of the bar first.
If it finds it then the bar is complete."* Context: the
`origin/lane-2.51-unboxed-ink` branch's own crop pass found ~3 whole-rest-
shaped blobs with NO detector box at all on Litolff p3 (§15 below, landed
2026-10-08; §14 on its own branch), named by tile, e.g. `glyph/3/0/9/13`. Before this lane,
every rest reading in `tools/omr/staged/` starts from a box the detector
drew (`Q.REST`, `Q.NOTEHEAD_IS_A_WHOLE_REST`, `size_measure_rest`) — a bar
the detector left completely boxless, notehead or rest, left no trace on
the record at all and exported looking complete (CLAUDE.md §9: "a box it
never drew has no subject").

### 14.1 The build, GATHER + ADJUDICATE only

`gather.gather_empty_bar_rest_search` (`READERS.CV_REST_SEARCH`, files
`Q.EMPTY_BAR_REST_SEARCH`): for every cell with NO notehead- or rest-class
detection box at all (a GATHER-level fact, read off the raw detector boxes
passed to GATHER — no ADJUDICATE dependency), re-measures the cell's own
connected ink components (`_ink_components`, the SAME function `gather_ink`
uses, over `cell.image_no_staff`) against the cell's own LOCALLY-corrected
staff lines (`cell.staff_line_ys_canonical`, `OMR_CELL_LINE_TRACE`'s own
per-cell comb, ON by default since 2026-09-04 — CLAUDE.md §10's "measure
locally" rule, already wired for every canonical-frame reader and reused
here rather than restated). Shape and position tests are IMPORTED, not
restated, from `adjudicators.rhythm`: `_rest_shaped`/
`WHOLE_REST_INK_MAX_HEIGHT_SPACES`/`_MIN_ASPECT`/`_MAX_ASPECT` (size and
proportion), `WHOLE_REST_STEP`/`_STEP_TOLERANCE` (hangs under the 4th line
from the bottom), and `HALF_REST_STEP`/`REST_SLOT_TOLERANCE_HALF` as the
guard against the other filled rest shape — a half rest sits ON the 3rd
(middle) line, not hanging under the 4th, and a candidate closer to
`HALF_REST_STEP` than `WHOLE_REST_STEP` is excluded before the whole-rest
test ever sees it. The search tries the bar's own middle third first
(`EMPTY_BAR_MIDDLE_FRACTION`); only if nothing matches there does it widen
to the whole bar's interior (a measure cell has no horizontal padding, so
"the bar" and "the cell's own canonical width" are one quantity).

`adjudicators.rest_search.adjudicate_empty_bar_whole_rest` (ADJUDICATE,
`Q.EMPTY_BAR_WHOLE_REST`, a SEPARATE quantity from the GATHER row it reads
— `Q.EMPTY_BAR_REST_SEARCH` is this raster's own IDENTIFICATION, the
decision's own INTERPRETATION of it, the same split `Q.UNREAD_MARK` makes
from `Q.INK`): `found=True` → DECIDED `whole_rest_found_by_search`, this
bar is a whole-bar rest. `found=False`, or GATHER could not even test →
ABSTAIN, never a `False` that would claim the bar is empty (CLAUDE.md §2
rule 8 — "not found" is not evidence the bar has nothing in it). Nothing
here writes a `Q.REST`/`Q.DURATION` row or touches EXPORT — wiring the
found verdict into `size_measure_rest` so it actually sizes the bar is
explicitly out of scope for this GATHER+ADJUDICATE-only lane (`reach.
KNOWN_GAPS`, Sean 2026-09-30) and is the obvious next item once the search
is confirmed.

### 14.2 Tests, RED→GREEN

`tools/omr/tests/test_staged_empty_bar_rest_search.py`, 12 tests, run RED
first (every one fails on `AttributeError`/`KeyError` against the tree
before `gather_empty_bar_rest_search`/`rest_search.py` existed — confirmed
by deleting both and re-running, 12 of 12 fail). Population: a whole rest
centred in a synthetic bar is found (`witness=middle`); an OFF-CENTRE one
is found only by widening (CLAUDE.md §2 rule 7's own shape — the middle-
first search must not be the only search); a half-rest-shaped block on the
3rd line is correctly NOT a whole rest (the control that can fail); an
empty bar with no ink at all is not found (`reason=no_ink`, kept apart from
a shape that was found and rejected); a bar with a notehead OR a rest box
already present is never even searched (`Q.EMPTY_BAR_REST_SEARCH` is never
filed — CLAUDE.md's 2026-10-01 "leave the whole rest alone": this lane only
FINDS, it never removes). ADJUDICATE half: a found search result decides
the bar; a not-found result and a no-ink result both ABSTAIN rather than
deciding `False`; a missing/geometry-abstained GATHER row passes its own
reason through. `pytest -m "not slow"`: 4,257 passed (base 4,245 + 12), 0
failed, 3 skipped, 2 xfailed. `python3 -m tools.omr.staged.check`: 245 →
248 (all three new findings are inventoried and explained: two `wiring.
KNOWN_GAPS` entries for two recorded-only detail fields, one `reach.
KNOWN_GAPS` entry for the deliberately out-of-scope EVALUATE/EXPORT wiring
— the convention this file's own §13.4/§13.6 precedent set).

### 14.3 Real data — both acceptance documents, GATHER+ADJUDICATE small
re-gather (`tools.omr.acceptance_quick`, current tree)

**Litolff pp.1–3** (Beethoven 5 mvt 1, MERGING plate): 56 boxless bars
across the three pages, **27 found, 29 not found** (25 of the 27 found in
the bar's own middle third, 2 only by widening). On the count page (p3)
alone: 20 boxless bars, **13 found, 7 not found**. `cell/3/0/9/13` — the
EXACT tile the 2.51 lane named by eye — is among the 13 found here,
confirmed by crop below.

**Brahms pp.0–1** (SHATTERING plate): only **9** boxless bars total across
both pages (consistent with CLAUDE.md §10's "Litolff MERGES and Breitkopf
SHATTERS" — a shattering plate's ink rarely goes completely unboxed), **1
found, 8 not found**. The one found case is on the count page (p1),
`cell/1/1/7/3`.

### 14.4 Crops — every finding verified against the print

`out/print/2.52/litolff-p3-empty-bar-rest-search.png` (full count-page
contact sheet, every found bar boxed green with the ink outlined orange and
the target line drawn blue, every not-found bar boxed red) and
`out/print/2.52/brahms-p1-empty-bar-rest-search.png` (the one Brahms p1
case). Individually zoomed and read BY EYE against the print (not
committed separately — the contact sheets above carry the same boxes at
full page resolution):

- `cell/3/0/9/13` (Litolff, middle): a real whole rest, hanging exactly
  under the 4th line from the bottom, orange box tight on the glyph. The
  2.51 lane's own named tile, now found.
- `cell/3/0/5/0` (Litolff, **widened** — the search's own off-centre case,
  not the middle third): a real whole rest in the horn part, correctly
  found only once the search widened past the middle third.
- `cell/3/1/2/1` (Litolff, middle): a real whole rest.
- `cell/1/1/7/3` (Brahms, middle): a real whole rest, confirmed on the
  SHATTERING plate too.
- `cell/3/0/1/0` (Litolff, **not found**): correctly abstained — this bar
  holds a TIED half note sustained across the barline (no new attack, so no
  new notehead box either), not a rest. "Not found" here is the right
  answer: there is no rest to find, and the decision abstains rather than
  claiming one.

4 of 4 found cases crop-verified as real whole rests; 1 of 1 not-found case
spot-checked is a genuine non-rest bar (a tied continuation), not a missed
rest — exactly the population rule 8's abstention is for.

### 14.5 Not established

- Only 1 of 29 (Litolff) / 8 of 8 (Brahms) not-found cases were crop-
  checked; the rest could in principle hide a real rest this search's shape
  or position tolerance misses (a crop-clipped rest at a system edge, an
  unusually tall/short print) — the contact sheets carry every one of them
  for a fuller pass.
- EVALUATE/EXPORT wiring (does a found whole rest actually SIZE the bar and
  reach the file) is deliberately not built here — `reach.KNOWN_GAPS`'s own
  entry says so. The acceptance proxies (bars that "add up", held-out bar
  counts) are therefore UNCHANGED by this lane and were not re-measured —
  this is a GATHER+ADJUDICATE-only lane per Sean's 2026-09-30 instruction.
- `bar_width_px`/`n_components` (recorded-only detail fields, `wiring.
  KNOWN_GAPS`) and `bbox_page_px` on a found row are read by nothing in
  `tools/omr` yet; the crop script above is their first real consumer, kept
  as a standalone script rather than landed in the tree (no roadmap item
  for a 2.52-specific crop tool).

## 15. ROADMAP 2.51 — how much printed ink has no detector box, and what is it

*Landed 2026-10-08 from `lane-2.51-unboxed-ink` `78d05d85` (ROADMAP 0.8 triage, Sean: "Yes to all"); written there as §14, renumbered here because main's §14 is 2.52. Text otherwise as the lane wrote it.*

2026-10-01, `lane-2.51-unboxed-ink`. MEASUREMENT ONLY — no production code
touched. STAGED. Reuses `Q.INK`'s own per-component fields
(`ink_detector_coverage`, `ink_explained_by`, `ink_bbox_canonical`,
`width_spaces`/`height_spaces`, `bbox_page_px`) exactly as GATHER wrote them,
and the REAL `gather._explaining_detections`/`gather._coverage` functions for
the control (§15.3) — reused, not reimplemented (rule 1).

**Re-gather needed**: the committed `20261001` whole-movement records
(`library/_shared-records/{beethoven5-litolff,brahms1-breitkopf}-mvt1-whole-
20261001.record.json`) are the SUMMARY form (roadmap 1.1's default) — every
`unread_mark` verdict on both abstains `no_ink_component_rows`, confirming no
per-component box survives. One small `--ink-rows` re-gather per document,
unattended, `--through adjudicate` (first movement page through the count
page, per `acceptance_quick`'s own rule never to gather the count page
alone): Litolff pages 1-3, Brahms pages 0-1, both `--weights auto
--route-weights --dpi 600`, plus a third on the engraved acceptance page
(`benchmarks/omr-staged-engraved-2026-09/out/fixture/beethoven-sym5-mvt1-
m1-24.pdf`, page 0, `--dpi 300`) for the control in §15.3. Scripts under
`benchmarks/omr-ink-gather-2026-09/unboxed-2.51/`, run with `PYTHONPATH=.`
from the repo root.

### 15.1 What was subtracted, and what was not

- **Staff lines**: already removed, LOCALLY (CLAUDE.md §10's own rule), by
  `gather._ink_components`'s own input — `cell.image_no_staff`, the
  staff-line-erased raster computed per CELL before any component is found.
  This is upstream of this script; nothing here re-derives it.
- **Stems**: `stem` is CV-only (CLAUDE.md §9: "`stem` and `staff` are CV-only
  and cost nothing") and is never a YOLO detection, so it never appears in
  `ink_explained_by` — every stem pixel reads as uncovered unless subtracted
  separately. Subtracted here as an axis-aligned BOX overlap between each
  ink component's canonical bbox and every `Q.STEM` row filed on the same
  cell (same canonical frame) — an approximation, not a pixel mask, stated
  plainly.
- **⚠️ NOT subtracted, because the brief did not name it, but it dominates
  the residue and should be read alongside every number below: BARLINES.**
  `barline` is not a detector class either — `measure_extractor.py`'s own
  `Q.BARLINE_COLUMN` is a CV quantity, not a `glyph_box` row, confirmed here
  by grepping the gathered quantity list (no `barline*` class ever appears
  among 22 distinct `glyph_box` classes on the engraved control page). A
  barline is therefore a THIRD member of the "never boxed by design" family
  alongside staff lines and stems, and this pass did not get asked to
  exclude it. §15.2's control result is the direct consequence.

### 15.2 Totals, per page

| page | total ink px | covered % | stem % | **uncovered %** |
|---|--:|--:|--:|--:|
| Litolff p3 (count page) | 33,583,719 | 27.48 | 12.42 | **60.10** |
| Brahms p1 (count page) | 46,456,846 | 25.16 | 11.03 | **63.81** |
| Beethoven engraved p0 (control) | 5,441,125 | 48.83 | 6.11 | **45.06** |

Per-staff uncovered % ranges widely on both scans (Litolff 44.9–71.6%,
Brahms 46.4–93.6% — `litolff-p3-result.json`/`brahms-p1-result.json` in
`unboxed-2.51/` have the full per-staff table), consistent with a page-level
average hiding a lot of staff-to-staff variation rather than a uniform rate.

**The control at §15.3 explains why the engraved number is nowhere near
zero**: 93% of near-zero-coverage, line-shaped ink on the engraved page sits
within 20 px of a cell boundary — i.e. at a barline, the family this pass
was not asked to subtract. The same check on Litolff finds 93% of its
line-shaped uncovered ink at a cell edge too; on Brahms only 56% — the
SHATTERING plate's barlines break into fragments that don't all land flush
with the cell boundary the way Litolff's MERGING plate's do (reproduce with
`unboxed-2.51/barline_check.py <record>`). **The headline uncovered-%
numbers above are therefore NOT a clean measure of genuine detector misses
— a large, unquantified share on all three pages is ink the pipeline never
intended to box at all.** This was not pre-registered and is reported as
found, per rule 8: an uncovered-ink number that does not separate "never
meant to be boxed" from "missed" would silently read as a much worse gap
than the detector actually has.

### 15.3 The control (rule 7: it must be able to fail)

**It failed where predicted to pass** (the engraved control, §15.2) — a real,
useful failure, diagnosed above as the barline gap, not a bug in the
coverage arithmetic (confirmed by re-deriving it from the record's own
`ink_detector_coverage` field, not a value this script computed).

**It passed, 10 of 10, on the deleted-box test.** For 5 real, isolated
notehead detections per scan count page (a `glyph_box` row whose own box
covers ≥60% of its matching ink component's area, `ink_detector_coverage`
already ≥0.5 and `ink_explained_by` naming only that one class), the
detection list for its cell was rebuilt EXACTLY from the record's own
`glyph_box` rows (the same raw input `gather._explaining_detections` reads)
with that one box removed, and `gather._coverage` — the real function, not a
reimplementation — was called again:

| doc | before cov (real box present) | after cov (box removed) | width/height spaces |
|---|--:|--:|---|
| Litolff | 1.000, 1.000, 0.983, 0.862, 0.868 | 0.000 ×5 | 1.14×0.57, 1.27×0.50, 1.15×0.50, 0.70×1.40, 1.20×0.39 |
| Brahms | 0.970, 0.753, 0.945, 1.000, 0.606 | 0.000 ×5 | 1.43×0.84, 2.03×1.28, 1.58×0.71, 1.06×0.17, 1.47×1.75 |

Every deleted box reads zero-coverage ink afterward, as it must. Most land
inside or near the project's OWN measured notehead band (1.26–1.78 wide ×
0.34–1.8 tall, `omr-notehead-width-2026-09/FINDINGS.md`) — none of the ten
would have been excluded by that band, though several fall outside the
BRIEF's narrower 1.0–1.4 × 0.8–1.2 window used for §15.4's groups (see the
note there). The control's own failure mode (another overlapping detection
still explains the component after the chosen one is removed) did not occur
in this sample of 10 — reported, not hidden; a larger sample could surface
it. Reproduce with `unboxed-2.51/control.py <record> <page> --n 5`.

### 15.4 Groups, by size/shape relative to the local staff space

Bands exactly as specified in the brief: head-sized 1.0–1.4 × 0.8–1.2 sp;
digit/letter-sized 0.3–1.0 wide × 0.5–1.6 tall with height ≥ width;
line-like aspect ratio ≥ 3:1 either way; speck area < 0.08 sp²; else
"other". **⚠️ CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED**:
nobody was available to ask Sean before this pass, these bands are the
brief's own and are narrower than the project's own measured notehead band
(§15.3) — a real head that prints narrower or taller than 1.0–1.4×0.8–1.2
(roughly a third of the confirmed control heads above) is NOT counted
`head_sized` here and instead falls in `other`/`digit_letter_sized`. Counted
only over components whose OWN uncovered share exceeds half their area (so
a mostly-covered component contributing a sliver of uncovered edge does not
pollute the shape counts):

| group | Litolff p3 n | Litolff px | Brahms p1 n | Brahms px |
|---|--:|--:|--:|--:|
| head_sized | 10 | 64,173 | 13 | 59,799 |
| digit_letter_sized | 50 | 170,848 | 79 | 209,960 |
| line_like | 765 | 13,022,333 | 951 | 7,803,193 |
| speck | 60 | 14,430 | 2,561 | 74,013 |
| other | 178 | 4,451,742 | 531 | 18,658,220 |

`line_like` is the largest bucket by area on Litolff (64% of its own
uncovered-majority mass); `other` is largest on Brahms (63%) — consistent
with CLAUDE.md §10's own "Litolff MERGES and Breitkopf SHATTERS": Breitkopf's
shattered ink breaks into shapes that don't cleanly fit any of the four
named bands, landing in `other` far more than Litolff's.

### 15.5 Crops, and a one-word guess per tile (not a judgement)

`out/print/2.51/litolff-p3-uncovered-contact-sheet.png` and
`.../brahms-p1-uncovered-contact-sheet.png` — the 20 largest head-sized and
digit-sized uncovered components per page, ≥3×, rendered from the real PDF
at the gather's own DPI, uncovered box tinted red, nearby `glyph_box`
detections drawn thin blue. One-word guess per tile, eyeballed quickly, not
a verdict:

- **Litolff (20 tiles)**: the large majority are letters of printed
  direction-word text (`dolce`, the `a.2` divisi marking) that the
  head/digit-sized geometric window happens to catch; a handful of
  `head_sized` tiles sit on a bare staff line with no visible round head at
  all (a likely staff-line-thickening false positive in that band, not
  print-confirmed); 1–2 tiles do show what looks like a real small notehead
  beside text.
- **Brahms (20 tiles)**: essentially ALL 20 are individual LETTERS of
  printed direction words — `pizz.`, `dim.`, `espr.` — each letter its own
  ink component on this SHATTERING plate, several (`p`, `i`, `z`, `d`, `m`)
  landing squarely inside the head-sized or digit-sized window by
  coincidence of a serif letterform's proportions. This corroborates
  roadmap 2.4c's own crop finding (`unread_mark.py`'s module docstring,
  SS13.3b: "6 of 6 Breitkopf crops... are printed direction-word text") at a
  much larger sample on the same mechanism, independent of that decision's
  own `Q.DIRECTION_WORD`/`Q.DYNAMIC_LETTER` overlap guard (this pass applies
  no text guard at all, and still lands almost entirely on text).

### 15.6 What this does and does not establish

- The dominant population in the head/digit-sized uncovered bands on BOTH
  scans is printed TEXT, not missed noteheads — confirmed by eye, not
  print-measured bar-by-bar.
- The flat uncovered-% headline (§15.2) is inflated, by an amount this pass
  did not quantify precisely, by barline ink — a THIRD by-design gap this
  brief did not ask to exclude (§15.1). Any future use of this number as a
  detector-quality proxy needs that subtraction first, or it will read as a
  much worse recall gap than the detector actually has.
- The deleted-box control (§15.3) establishes the MECHANISM correctly
  surfaces a real missing head as uncovered, notehead-sized ink when one
  really is missing — it does not establish how OFTEN that happens on these
  two pages, since the ten real heads tested were still present (this
  pass never actually removed a detection from the live pipeline, only from
  a reconstructed per-cell list fed to the real coverage function).
- Not measured: whole-movement reach (both re-gathers were the count-page
  range only, per CLAUDE.md §6b); any consumer wiring (`Q.INK`/
  `Q.UNREAD_MARK` stay exactly as documented in §13 — this pass adds no new
  consumer); a precise "uncovered minus barline" corrected percentage.

## 16. ROADMAP 2.53 — bars full of notes with no detector box at all (2.52's complement)

*Landed 2026-10-08 from `lane-2.53-unboxed-bars` `ad41435b` (ROADMAP 0.8 triage, Sean: "Yes to all"). The lane wrote this as its ROADMAP row; it lives here per rule 9. The branch's re-gathered `benchmarks/acceptance/quick/` outputs were NOT landed (they would overwrite main's). The two contact sheets are under `out/print/2.53/`. Text otherwise as the lane wrote it.*

**diagnosed, no fix — not a weights/routing/extraction defect** (branch `lane-2.53-unboxed-bars`, MEASUREMENT+DIAGNOSIS only). Re-gathered both count pages fresh, GATHER+ADJUDICATE only (`tools.omr.acceptance_quick`'s own CLI call, `--through adjudicate`, `--weights auto`; its `*.record.json` is gitignored and wasn't on disk) — confirmed the same 29/8 split, `weight_routing.weights` = production scan weights (`hollow-graft-shift09-2026-09-04.pt`) on both, `conf=0.25`, `dpi=600`. **Litolff (29 not-found): 28 of 29 cells already have SOME `Q.GLYPH_BOX` (ledgerLine 10, tie 8, slur 8, arpeggiato 7, beam 6, fermataAbove 5, cautionary clef 4, dynamics 3, accidentals 2, 1 each of keyFlat/articStaccatoAbove/flag16thDown/timeSig4) — never a whole-cell miss, only the notehead/rest CLASS is missing.** Only `cell/1/0/8/12` has zero `Q.GLYPH_BOX` of any class, but even there `Q.STEM` (CV-only) fired and `Q.INK` shows a real 74%-share blob with `ink_detector_coverage_max=0.0`. Re-ran both pages with `--conf 0.10` (same weights/dpi/extraction): **24 of 29 gain a notehead- or rest-class box scoring 0.10–0.25** — `noteheadHalfInSpace`×13, `noteheadHalfOnLine`×11, `restQuarter`×3, `noteheadBlack*`×4, `noteheadWhole*`×2, `restWhole`×1 — i.e. a CONFIDENCE FLOOR on the notehead class, concentrated on HOLLOW (half-note) heads sitting under ties/ledger lines/beams/fermatas, not a weights/routing/cell-extraction defect (cell boxes and canonical frames identical between the two confs). 5 of 29 (`cell/1/0/8/13`, `11/3`, `2/0/3/7`, `7/11`, `3/0/5/12`) get nothing new even at 0.10 — a deeper miss where the head's own ink is entangled with beam/ledger/fermata ink; not resolved here. No positional pattern (only ~7 of 29 sit at a system/staff edge; the rest are mid-system, mid-staff) — the common thread is hollow-head shape under crossing ink, not page position. **Brahms (8 not-found) is NOT the same population**: all 8 are cell index 7 across staves {0,1,2,6,7,8,10,12} of page 0 system 0, and every glyph in every one is `timeSig6/8/9` only — no notehead, no tie/slur/beam/ledgerLine at all. Crop-confirmed BY EYE: these are the cautionary "9/8" tail digits ROADMAP 2.47b/2.47c/2.47bc/2.47b(majority) already diagnosed — not missed notes; the brief's "full of notes" premise does not hold for Brahms. Crops: `out/print/2.53/{litolff-p3,brahms-p1}-unboxed-not-found-contact-sheet.png` (cell boundary blue, conf-0.10 detector boxes faint, notehead/rest green vs other amber, labelled `class:score`). 

**Recommendation, not built** (later built as ROADMAP 2.55, merged and switched ON 2026-10-01): a global `OMR_CONF_THRESHOLD` drop is a GATHER change needing two full re-gathers to price (rule 6b) and risks new false positives elsewhere; a narrower targeted low-confidence rescue restricted to cells `_empty_bar_candidate_cells` already flags as notehead/rest-free needs a convention question to Sean first (is a 0.10–0.25-scored box trustworthy enough to KEEP) before any build.
