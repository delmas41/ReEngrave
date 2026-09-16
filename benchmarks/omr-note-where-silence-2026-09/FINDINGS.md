# A pitched note where the page prints silence — opened, and it is THREE faults in one costume

2026-09-15. Sean's one unanswered observation from the first cleanup artefact
(`docs/handoff-2026-09-11-phase-2-opened.md` §3), taken to the ink.

> *"in bars where it should be just whole note rest in two four. It's showing
> an actual quarter note, not a quarter note rest."*

One document: Beethoven 5 / Litolff `984073`, pdf pages 1-4, 2/4 throughout,
the shared record (`library/_shared-records/beethoven5-p1-p4.record.json`,
md5 `d3620ba9cb70fc93f6b7ee91b6cbe40a`). No fresh gather; no weights needed.

---

## 1. The population reproduces, to the unit

Re-derived from a fresh re-export of the shared record on the current tree, by
an instrument written from scratch (`probe/population.py`) rather than the one
the handoff used:

| | |
|---|--:|
| bars parsed | 1,183 |
| bars whose ENTIRE content is one **PITCHED** note | **118** |
| ...of which UNDERFULL against the declared `<time>` | **44** |
| ...of which a lone **QUARTER** in a 2/4 bar | **26** |

and all six instances the handoff names (`P1 m45`, `P1 m85`, `P1 m88`,
`P1 m89`, `P2 m49`, `P2 m87`) come back at `duration=96` of `192`. So the
handoff's figures stand and the two instruments agree.

---

## 2. ⚠️⚠️ THE HEADLINE: THE 26 BARS ARE NOT ONE FAULT, AND FOUR IN FIVE ARE THE OPPOSITE FAULT

Every one of the 26 was cropped at 34 px per staff space and looked at against
the print, on contact sheets that also carried five glyphs the record itself
calls `restWhole` and five it calls a notehead, drawn identically as controls.
Where a panel was not decisive on its own, the whole printed staff was rendered
as a strip and the bar compared with **its own neighbours** — same part, same
plate, same ink, which is the only fair control for a bar. Verdicts are
committed row by row in [`adjudicated-26.json`](adjudicated-26.json).

| what the print actually shows | n |
|---|--:|
| a **WHOLE REST** the detector called a notehead — Sean's fault, exactly | **5** |
| a **REAL NOTE**, in a bar whose other music was never read | **18** |
| **neither** — the box sits on a slur apex or a stem/staff-line junction | **3** |

⚠️⚠️ **So the brief's hypothesis is true of one bar in five and false of the
rest, and a repair that emptied all 26 bars would delete 18 real notes.** The
18 are a *missing-note* problem wearing an *invented-note* costume: the note we
wrote is right, and the reason the bar looks absurd is that its bar-mates are
absent. That is the same shortfall the arc work measured from the other side
(*108 of 550 refused arcs sit in bars where the detector produced NO
notehead*), reached here through a different door.

⚠️ **This is why the split matters more than the count.** A reader of the
handoff's `26` would size this job as 26 wrong notes to remove. It is 5.

⚠️ **One of the 26 was adjudicated WRONG on the contact sheet and right on the
strip** (`P8 m69`: a solid black rectangle in the rest's own slot, which the
strip shows is a real note plus a rest, with genuine whole-rest bars m70/m71
next door). That single case is the argument for the strip: a crop shows you
the ink, and only its NEIGHBOURS tell you what the engraver was doing.

### The decisive picture

`probe/strip.py` renders a printed staff end to end and labels each bar with
what our file says stands in it. On `p4/s0/st0` — the Flauti, tacet mm 82-89
and re-entering at m90 — the print shows **one small blob per bar at the same
height in every one of those bars**, and our file reads
`m82 R · m83 R · m84 R · m85 D5/quarter · m86 R · m87 R · m88 D5/quarter ·
m89 D5/quarter`, then real ledger notes at m90-91. The bars are identical on
the page; three of eight became notes.

And the record settles what the blob is without leaving the record: in that
same staff, `glyph/4/0/0/1/2` (m83) is **classed `restWhole`** at h=0.67 staff
spaces, aspect 2.33; `glyph/4/0/0/3/1` (m85) is **classed
`noteheadBlackInSpace`** at h=0.79, aspect 2.22. Same ink, same slot, two
different class names.

⚠️ **The fault is therefore a DETECTOR CLASSIFICATION ERROR**, upstream of
GATHER: `gather_glyph_families` routes by CLASS, so a whole rest the detector
calls a notehead never becomes a `Q.REST` row and no later stage can see it.
There is no missing dedupe pass, no relocation, no duplicate, no wrong bar and
nothing invented by the exporter — all five alternatives were checked and none
holds. **0 of the 26 suspect cells hold a detected rest of any kind.**

---

## 3. The reach of the real fault, and the witnesses that separate it

The lone-quarter-in-2/4 window is one view of the fault, not its size: a
misnamed whole rest can also land in a bar holding other ink, and can be
exported as a HALF note, which in 2/4 fills the bar and never shows up as
underfull at all. So the whole notehead population was swept
(`probe/reach.py`), with the cuts derived from a population the rule never
judges — the document's **own 395 correctly-detected `restWhole` glyphs**:

| | height (staff spaces) | aspect (w/h) |
|---|---|---|
| the document's `restWhole` | p05 **0.46** p95 **0.84** | p05 **1.63** p95 **3.09** |
| the document's noteheads | median **1.31** | median **1.14** |

| witness | fires on (of 2,347 noteheads) | on the adjudicated 26 |
|---|--:|---|
| SHAPE alone | **148** | 5 rests, 0 notes |
| POSITION alone (the slot) | **310** | 4 rests, **2 real notes**, 1 junk |
| SHAPE **and** POSITION | **25** | **25 of 25 are whole rests** |

⚠️ **NEITHER WITNESS IS ADMISSIBLE ALONE**, and this is measured rather than
asserted. POSITION alone is nearly uninformative: the band a whole rest hangs
in is where C5 and D5 live in treble, i.e. where ordinary music is. SHAPE alone
fires 148 times and most of those are not whole rests.

⚠️⚠️ **ALL 25 FIRES WERE CROPPED AND ADJUDICATED, not just the 5 already in the
hand set.** Scoring a rule on the rows that happen to be in your truth set is
scoring it on its easy cases. **25 of 25 are whole rests; zero are real notes.**

### POSITION is established two ways, and the second one is the finding

The absolute slot is measured against `Q.STAFF_LINES`, which models a staff as
five **ideal** rows — while a scanned staff tilts and bows 8-17 page px across
its width (CLAUDE.md, `OMR_CELL_LINE_TRACE`). Measured consequence: this
document's own correctly-read whole rests spread over staff steps **2.5 to
5.9**, against a nominal 5.5.

So a **neighbouring bar of the same staff** holding a detected `restWhole` at
nearly the same height counts as position evidence too. A tacet part prints a
whole rest in *every* bar, and a shared registration error **cancels between
two rows of one staff**. It is what catches `P1 m85` — one of the instances
Sean named — which the absolute slot misses at step 4.21.

⚠️ **The neighbour witness is not independent of the DETECTOR, only of THIS
GLYPH.** That is weaker than CLAUDE.md's *"a second witness must not come off
the same raster"*, and it is the strongest thing available here. Stated rather
than dressed up.

⚠️ **CONFIDENCE IS DELIBERATELY NOT A WITNESS.** The flagged glyphs do sit low
(median 0.36 against 0.66), and a confidence filter is measured and REFUSED one
family over at 233 good dynamic letters lost to remove half of 35 bad ones. A
tier that is a proxy for ink quality is not evidence about what a glyph IS.

### The cuts, swept — and two of them are NOT on a plateau

`probe/sweep.py` moves each cut and reports what changes:

| cut | shipped | plateau | what a loosening admits |
|---|--:|---|---|
| max height (spaces) | 0.84 | **0.80-0.84 only** | 0.90 adds 2 — both ambiguous ink in bars holding real notes |
| min aspect | 1.63 | **none** | 1.40 adds 2 (ambiguous); 1.80 **loses 2 real whole rests** |
| max aspect | 3.09 | **2.40-4.50, an EMPTY INTERVAL** | the widest real catch is 2.35; the next thing admitted is a 5.49 sliver of line residue |
| slot tolerance (steps) | 1.0 | 1.0-1.5 | 2.0 adds 2 |
| neighbour reach (bars) | 2 | 2 only | 3, 4 and 8 all add the same 1 |
| neighbour height (steps) | 1.5 | 1.0-3.0 | — |

⚠️⚠️ **TWO OF THE SIX CUTS SIT ON A PLATEAU ONE STEP WIDE OR LESS, AND THAT IS
THE MAIN RESERVATION ABOUT THIS REPAIR.** They are percentiles of the
document's own rest population, which is a derivation rather than a fit — but
it is a derivation from **one document**. The seven glyphs a one-step loosening
would admit were all cropped: none is a clean isolated whole rest, so the cuts
are load-bearing rather than cosmetic, which is an argument for keeping them at
the conservative edge and **not** an argument for trusting them on a second
publisher.

⚠️ The upper aspect bound costs nothing and exists for a reason of principle:
the 5.49 sliver it excludes is **not a whole rest either**, and a decision may
only claim what it can support — excluding it by description rather than
reaching the right outcome through a wrong one.

---

## 4. What shipped

`Q.NOTEHEAD_IS_A_WHOLE_REST` + `adjudicate_notehead_is_a_whole_rest`
(`Kind.GLYPH`, `Mode.ADDITIVE`, `subjects_from=Q.NOTEHEAD_CLASS`), consumed by
`export._place_notes` as a **refusal to write a note**, counted under
`ink_is_a_whole_rest`.

⚠️ **THE STAGE IS ADJUDICATE and the boundary is the reason.** What ink is on
the page is a GATHER fact; *what does this ONE thing mean, and on what
evidence* is ADJUDICATE's question. It is placed in `ORDER` **before**
`Q.DURATION` and `Q.EVENT`: a question about what a thing IS cannot honestly be
settled after the questions that assume the answer.

⚠️ **IT DOES NOT RECLASSIFY.** Nothing manufactures a `Q.REST` row. The bar
falls to the exporter's existing padded measure rest, which says *we read
nothing in this bar* — weaker than *we read silence*, and the statement the
record can support.

⚠️ **A `False` verdict names WHICH witness refused.** `not_rest_shaped` and
`not_where_a_whole_rest_can_hang` are different facts about the page, and
folding them together would hide that the second names the population a
shape-only rule would have deleted.

⚠️⚠️ **A DEFECT THE TESTS CAUGHT AND NO COUNT COULD HAVE.** The neighbour
witness first read `detail.bbox_page_px` off the neighbour's `Q.REST` row —
where `gather_glyph_families` does not put it; the geometry is on
`Q.GLYPH_BOX`. The witness fired zero times, silently, and *"no neighbour on
this staff"* and *"the witness is dead"* are the same number. Only a test
asserting that a specific page finds a neighbour can tell them apart.

---

## 5. MEASURED — one gather, adjudicated twice, exported twice

`arm.py`. ⚠️ **A plain re-export cannot see this change**: re-exporting a saved
record replays saved verdicts, so both arms would come back identical whatever
the rule did. The arm rebuilds a `Log` from the record's GATHER rows, re-runs
ADJUDICATE and EVALUATE, and only then exports; the OFF arm is the full `ORDER`
with this one quantity removed, which is exactly what `main` does.

⚠️ **It is structurally blind to a GATHER change.** Nothing in this repair is
in GATHER, so that is a statement about the instrument and not a hedge.

**CONTROL FIRST: the OFF arm reproduces 2,993 of 2,993 of the record's own
duration verdicts** before any arm is read. **REACH: 2,347 noteheads asked, 25
answered *this is a whole rest*** — the same 25 the offline probe found, by an
independent path — `slot` 20, `neighbouring_bar` 5, `not_rest_shaped` 2,202,
`not_where_a_whole_rest_can_hang` 120.

| | OFF | ON |
|---|--:|--:|
| pitched `<note>` | **1,618** | **1,596** |
| `<rest>` written | 566 | 566 |
| `measure_rests_read` | 92 | 92 |
| `empty_bars_padded` | 184 | **193** |
| slurs / dynamics / articulations / fermatas / parts | 40 / 195 / 48 / 41 / 75 | identical |
| ties | 91 | **90** |

**22 pitched notes removed and ZERO added**, which is the shape the rule
promises — it can only ever refuse.

⚠️ **THE 25 VERDICTS ACCOUNT EXACTLY**: 22 reached the file as a refusal
(`ink_is_a_whole_rest` 0 → 25 counts all of them), and the other 3 were already
being dropped for another reason — `no_pitch` 215 → 213 and `duration_narrowed`
339 → 338. The accounting control stays an EQUALITY on both arms.

**What happened to the 22 bars that changed**, keyed on the bar rather than the
part so the join cannot move it:

| | bars |
|---|--:|
| the bar's ONLY note goes, and it takes a padded measure rest | **9** |
| the bar's only note goes and a detected rest was ALREADY there | **7** |
| a note goes and the bar keeps its others | **6** |

⚠️ **THE SEVEN ARE THEIR OWN SMALL FINDING**: those bars held a `restWhole`
detection *and* a notehead reading of a second whole rest, so the file printed
a measure rest and a quarter note side by side in one silent bar — visibly
absurd, and exactly the shape Sean was describing.

⚠️ **AND THE SIX SAY THE LONE-QUARTER WINDOW WAS NEVER THE FAULT'S SIZE.** Six
of the 22 phantoms stood in bars that hold other music, where no
underfull-bar filter would ever have found them. The removed notes are written
as quarters, halves, eighths and wholes — *"a lone quarter in 2/4"* was one
window onto the fault, not its extent.

⚠️ **ONE TIE IS LOST** (91 → 90): an arc that was binding a phantom head. It is
counted here as a cost and **was not adjudicated against the print** — though a
tie bound to a whole rest cannot have been right.

⚠️⚠️ **THE ARM'S OFF FILE IS NOT THE PIPELINE'S ARTEFACT, and quoting its bar
figures against §1's would be an error.** The part join is itself an ADJUDICATE
decision and has changed since this record was gathered (handoff §5.2), so
re-running ADJUDICATE gives **75 fragment parts** where the pipeline's own
export gives 12 — which renumbers every measure and strips the `<time>` most
bars are scored against. What IS comparable is the note count, and it matches
the pipeline export exactly at 1,618. The per-bar table above is computed OFF
ARM vs ON ARM, never against §1.

**Suite 3,867 passed / 19 skipped**; `inventory --check`, `health --check`,
`gather_coverage` and `export_coverage --all` all exit 0, and `health`'s
`EMPTY CELLS` is `none`. ⚠️ One test fails, `test_direction_text.py::
TestReaderSelection::test_the_env_var_restricts_the_rungs`, and it is
**PRE-EXISTING and environmental** — checked out at the merge base `ce7b8ba7`
it fails identically, because `default_readers()` returns `[]` where there is
no `.venv-surya`, which is the worktree symlink trap CLAUDE.md already records.

**Mutation battery: 11 arms, all RED**, including the positive control in the
same class (*refuse everything*, which fails exactly the accept tests).
⚠️ **The first run had TWO SURVIVORS and both were the same test fault**: the
neighbour fixtures placed the far rest at `WHOLE_REST_NEIGHBOUR_BARS + 1`, so
widening the constant to 99 moved the fixture with it and the test passed for
every value of the thing it was supposed to pin. The distances are literals
now. *A test named for a hazard it does not reach*, arriving against its author.

---

## 6. What is NOT established

* **ACCURACY of the 18.** The hand verdict on those rows is only that ink of a
  notehead's kind stands there — not that we read the right pitch or the right
  duration.
* **The adjudication is one reader's**, this session's, against the print. It
  is not Sean's.
* **n = 1 document, 1 publisher, 4 pages of ~16**, on the *low-res bitonal* end
  of the corpus, which CLAUDE.md already calls the pessimistic end. A print
  whose whole rests are thinner, or whose staves are cleaner, would give a
  different shape band — and two of the six cuts have no plateau to absorb
  that. **Breitkopf Brahms 1 p0-3 is where this should be re-measured**, and it
  is the same second document the meter floors and the dotted rest both need.
* **The ENGRAVED family is untouched by construction** and was not measured.
* **No OMR-NED figure is claimed.** The metric is symmetric and rewards
  under-prediction, so deleting 25 symbols would be rewarded whether or not
  they were wrong — which is the trap this repair is most exposed to, and the
  reason the evidence here is crops rather than a score.

---

## 7. What this does NOT fix, and it is the larger half

**18 of the 26 bars Sean was looking at are bars we UNDER-read, not bars we
over-read.** Nothing here touches them. The ranked follow-on is the detection
shortfall those bars share with the arc work's 108 — and the honest framing for
a cleanup count is that *a lone note in an underfull bar* is a symptom with at
least three causes, and only the print separates them.
