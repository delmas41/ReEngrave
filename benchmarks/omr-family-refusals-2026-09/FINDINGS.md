# A per-family "is this really one" refusal — ROADMAP 3.4g

Branch `claude/family-refusals-3.4g`, off `origin/main` `5f109dd2`.

**What this item is for, and it is a person who measured it.** Sean's first
stage-review pass on Litolff Beethoven 5 p3 `staff/3/0/9` (ROADMAP 3.4,
2026-09-23) marked 23 boxes as *nothing*. **Eighteen of them reached no stage
at all** — `ledgerLine` x11, `arpeggiato` x3, `accidentalFlat` x2,
`accidentalNatural`, `restQuarter` — because
`adjudicate_notehead_is_not_a_notehead` was the whole pipeline's only "is
this really one" question and it is asked of noteheads. A reader whose
reading is filed and then read by nobody is the ABSENT/DECLINED collapse the
record exists to prevent, happening to the person.

---

## 0. What was built

Seven `@decision`s in `tools/omr/staged/adjudicators/family_precision.py`,
one per gathered family that had none, each declaring `Q.HUMAN_BOX_VERDICT`
and reading it through `notehead_precision._human_not_a_symbol` — the same
function, imported, never a second copy:

| quantity | domain | geometric rules | what its refusal REACHES besides the census |
|---|---|---|---|
| `Q.LEDGER_IS_NOT_A_LEDGER` | `Q.GLYPH_BOX` narrowed to `ledgerLine` | `on_a_staff_line`, `tall_not_a_rung` (and `not_at_a_rung_step`, held back) | `notehead_precision._ledger_rungs_in_cell` — a refused rung is not counted in ADJUDICATE's own ladder |
| `Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL` | `Q.GLYPH_BOX` narrowed to `accidental*` | none | **nothing** — see §6 |
| `Q.REST_IS_NOT_A_REST` | `Q.REST` | none | `export._place_notes`, `not_a_rest:<reason>` |
| `Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO` | `Q.GLYPH_BOX` narrowed to `arpeggiato` | none | **nothing** — see §6 |
| `Q.ARC_IS_NOT_AN_ARC` | `Q.ARC_BOX` | none | `export._place_arcs`, before `Q.ARC_KIND` |
| `Q.DYNAMIC_IS_NOT_A_DYNAMIC` | `Q.DYNAMIC_LETTER` | none | `adjudicate_dynamic` — a refused letter is not spelled into a word |
| `Q.ARTICULATION_IS_NOT_AN_ARTICULATION` | `Q.ARTICULATION_MARK` | none | `export._place_articulations`, before `Q.ARTICULATION_OWNER` |

**Six of the seven are human-only, and that is a statement about the evidence
rather than a placeholder.** "Shape from the class, role from the geometry"
(DECISIONS 2026-09-23) says a geometric rule needs a CONVENTION somebody can
state and a MEASUREMENT somebody has made. Exactly one family has both today.
Inventing a shape test per family to make the file look symmetrical would
have been seven unmeasured defaults shipped at once.

Plus, from the coordinator's mid-lane correction (Sean: *"'belongs to violin'
were about the fact that they belonged to a different staff"*), a new human
answer **`owner:other`** — *another staff, and I cannot say which* — read by
every per-family refusal AND by `notehead_is_not_a_notehead` as reason
`human_other_staff`, and skipped by name in `ownership._human_owner`, whose
value must be a staff key. Dropped on this staff, relocated nowhere
(CLAUDE.md §10). Documented in `review/SIDECAR.md`; offered by the viewer as
the word *other staff*, key `o`.

One framework addition: `adjudicate.DecisionSpec.subjects_classed`, a
DECLARED tuple of class-name prefixes narrowing `subjects_from`. Three
families (`ledger`, `accidental`, `arpeggiato`) have no quantity of their own
— `gather_coverage.FAMILY_TO_Q` maps all three to `None` — so their only
domain is `Q.GLYPH_BOX`, whose rows are **every** detection on the page
(8,486 on four Litolff pages). Without the narrowing each would file an
abstention per glyph and bury 1,878 ledger verdicts under 6,608 no-ops.

---

## 1. §LEDGER — the convention, and what measuring it found

Sean, 2026-09-23 (`docs/DECISIONS.md`): what the detector boxed as
`ledgerLine` and he marked as nothing was *"often a staff line, a bar line or
extra ink"*; a LEDGER LINE stands OUTSIDE the staff, at a whole number of
spaces beyond the top or bottom line, short and horizontal.

Three candidate rules follow. **All three were measured on the three records
before any of them was written** — `probe/ledger_geometry.py`, **17,313
`ledgerLine` boxes, every one carrying a page frame** (`no_page_frame` 0 on
all three) — and they came out very differently.

### 1a. The population

| record | `ledgerLine` boxes | inside the staff band | of those, within 0.25 spaces of a line | outside the band |
|---|---|---|---|---|
| `beethoven5-p1-p4` | 1,878 | 1,370 (73%) | 1,059 | 508 |
| `beethoven5-litolff-mvt1-whole` | 7,617 | 5,122 (67%) | 4,011 | 2,495 |
| `brahms1-breitkopf-mvt1-whole` | 7,818 | 1,222 (16%) | 1,125 | 6,596 |

⚠️ `ledgerLine` is the **largest single class** on the Litolff four-page
record — 1,878 of 8,486 detections, against 978 `noteheadBlackOnLine` and
916 `noteheadBlackInSpace` (1,894 for the two spellings together, so the
black noteheads edge it as a FAMILY and no single class comes near it). Two
thirds of the ledger boxes are inside the staff band, where the convention
says a ledger line cannot be.

### 1b. The tolerance, DERIVED

`ON_A_STAFF_LINE_TOL_SPACES` is the **p75 of the measured gap between a
`ledgerLine` box's centre and its nearest modelled staff line, over the boxes
INSIDE the band** — the one population where the ink can only be a staff-line
fragment, so the number is registration scatter and nothing else:

| record | n | p50 | **p75** | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| `beethoven5-p1-p4` | 1,370 | 0.145 | **0.245** | 0.355 | 0.420 | 0.485 | 0.500 |
| `litolff whole` | 5,122 | 0.135 | **0.235** | 0.345 | 0.425 | 0.487 | 0.500 |
| `breitkopf whole` | 1,222 | 0.110 | **0.162** | 0.238 | 0.278 | 0.390 | 0.493 |

**0.25 spaces** is the smallest round value covering all three p75s. The bound
that matters is the other one: the first legal rung stands ONE WHOLE SPACE
beyond the outer line, so the tolerance is **four times clear of it**, and
the largest registration error `rhythm.py` measures on this plate is a whole
STEP (0.5 spaces) — still half the distance to the first rung. Pinned by
`test_the_tolerance_is_the_measured_one_and_holds_at_its_edge` and by the
positive control in §1e.

### 1c. `tall_not_a_rung` — small, and honest about it

| record | height p5 / p50 / p95 / p99 / max (spaces) | aspect h/w p50 / max | **taller than wide** | **height > 0.5 spaces** |
|---|---|---|---|---|
| `beethoven5-p1-p4` | 0.20 / 0.28 / 0.37 / 0.41 / 0.68 | 0.092 / 0.400 | **0** | **7** |
| `litolff whole` | 0.20 / 0.28 / 0.37 / 0.41 / 1.04 | 0.092 / 0.784 | **0** | **22** |
| `breitkopf whole` | 0.20 / 0.29 / 0.38 / 0.42 / 0.63 | 0.136 / 0.571 | **0** | **8** |

**⚠️ THE ASPECT ARM SEAN'S WORDING SUGGESTS IS DEAD.** *Taller than wide* —
i.e. a barline or a stem — fires **0 of 17,313**. The detector never draws a
`ledgerLine` box around a whole barline; where it fires on barline ink it
draws a SHORT HORIZONTAL SLICE of it, and no proportion test can separate
that from a rung. **The arm is therefore not written.** A rule that cannot
fire is not a conservative rule; it is an unmeasured one wearing a zero.

What ships is the HEIGHT floor at 0.5 spaces — past p99 (0.41–0.42) on all
three — catching 7 / 22 / 8 boxes. Small, measured, and crop-checked (§5).

### 1d. `not_at_a_rung_step` — MEASURED AND HELD BACK

`RUNG_STEP_SHIPS = False`, exactly the `notehead_precision.UNLADDERED_SHIPS`
precedent. Over the boxes **unambiguously** outside the staff (at least 1.25
spaces clear of the outer line, so the nearest rung is always within half a
space and the number measured is scatter, not band-edge clamping), the offset
from the nearest rung step is:

| record | n | p5 | p25 | p50 | p75 | p90 | p95 | max |
|---|---|---|---|---|---|---|---|---|
| `beethoven5-p1-p4` | 188 | 0.075 | 0.250 | 0.330 | 0.385 | 0.450 | 0.470 | 0.495 |
| `litolff whole` | 955 | 0.073 | 0.188 | 0.285 | 0.380 | 0.455 | 0.470 | 0.500 |
| `breitkopf whole` | 3,611 | 0.015 | 0.070 | 0.135 | 0.257 | 0.402 | 0.455 | 0.500 |

**On Litolff the distribution is very nearly UNIFORM on a lattice whose
half-period is 0.5.** A uniform distribution over the lattice carries no
signal at all: the measurement cannot tell a rung from anything else, and a
rule read off it would refuse 522 (p1-p4) / 1,945 (whole) boxes on evidence
indistinguishable from noise. **Breitkopf's same measurement IS peaked** (p50
0.135, p25 0.070, mode at 0.05–0.10), so the lattice is resolvable on that
plate and not on this one — which makes the cause the registration of
`Q.STAFF_LINES` against a MERGING bitonal plate, **not** the convention.
`rhythm.py` records the same cause in its own tolerance: a scanned staff tilts
and bows 8–17 page px, *up to a whole STEP*, and a whole step is half the
rung lattice.

"Print before default" (CLAUDE.md §2 rule 5) forbids shipping it on the
strength of the convention alone. The signal is computed on every ledger box
and recorded in `detail["rung_step_signal"]`; it sets no value, and the rule
declares no reason (so `brakes.vocabulary_gap` stays able to fail). **518 of
the 657 boxes the shipped rules KEEP on `beethoven5-p1-p4` would be refused
by it** — that is the size of what is being held back, and four of them are
cropped for Sean in §5.

What would have to change first: a staff-line model that follows the bow
(`OMR_CELL_LINE_TRACE` traces one per cell and this decision does not read
it), re-measured on Litolff, with the offset histogram peaked.

### 1e. The positive control, on the print

A rung **one whole space below line 1 with a notehead standing on it must not
be refused**. Pinned three ways:

* `test_a_rung_one_space_below_line_1_with_a_head_on_it_is_KEPT` (and the
  mirror above line 5, and the second and third rungs);
* the tolerance is asserted `< 0.5` spaces, i.e. under half the distance to
  the first rung;
* and on the plate: `out/print/litolff-p1p4-p3-s0-st7-c6-g14-kept.png` shows
  a real first ledger line at step −1.85 (0.925 spaces beyond the band),
  sitting on the blue rung dash with the noteheads it carries — KEPT.

---

## 2. Base vs arm, on ONE tree

`probe/readjudicate_ledger.py` rebuilds one saved record and adjudicates it
TWICE in one process: the BASE with the ledger geometry returned to nothing
(an unmeetable tolerance and an unreachable height floor — what the decision
did before it existed; the human rules stay and are inert on records holding
no human row), the ARM as shipped. The record's own committed verdicts are an
INPUT, never a baseline (CLAUDE.md §6b). It prints its population first and
exits 2 declaring itself DEAD AT ZERO if the record holds no ledger box.

⚠️ Blind to GATHER, like every tool of its shape — which is fine here,
because this lane files no new GATHER row.

### 2a. Ledger verdicts per record

| record | boxes | `on_a_staff_line` | `tall_not_a_rung` | kept | abstained | base refused |
|---|---|---|---|---|---|---|
| `beethoven5-p1-p4` | 1,878 | **1,214** | **7** | 657 | 0 | 0 |
| `litolff whole` | 7,617 | **4,708** | **22** | 2,887 | 0 | 0 |
| `breitkopf whole` | 7,818 | **1,408** | **8** | 6,402 | 0 | 0 |

The BASE refuses nothing on any record: the arm is the only thing moving,
which is what says the numbers are the rule's and not the rebuild's.

### 2b. `glyph_owner` — **0 verdicts changed, and that is the finding**

| record | `glyph_owner` verdicts (base / arm) | **moved** |
|---|---|---|
| `beethoven5-p1-p4` | 1,386 / 1,386 | **0** |
| `litolff whole` | 6,013 / 6,013 | **0** |
| `breitkopf whole` | 24,795 / 24,795 | **0** |

This is not a null result. It is the answer to item 3 of the brief, and it is
structural:

> **`glyph_owner`'s ladder tier cannot see a refused rung, because the
> rung -> glyph join does not exist on the record.** `Q.GLYPH_LADDER` is built
> in GATHER by `gather._observe_ladder` from an anonymous list of rung
> rectangles (`_ledger_index` yields bare `(x0, x1, y)` tuples), and the row
> it files records `expected` and `found` as **COUNTS**, naming none of the
> ledger glyphs it matched. No ADJUDICATE refusal can reach it without a
> GATHER change — and a GATHER change is invisible to `readjudicate` and needs
> two full re-gathers to price. **Reported, not faked.**

Pinned behaviourally rather than asserted in prose:
`test_gather_s_own_ladder_row_NAMES_NO_RUNG_GLYPH` calls `_observe_ladder`
for real, asserts it found its rung (the positive control) and asserts the
row's detail names no glyph subject. The day that row names its rungs, the
test goes red and the discount can move to `glyph_owner` too.

### 2c. The ladder the refusal DOES reach

ADJUDICATE has its own ledger search — `notehead_precision.
_ledger_rungs_in_cell`, where the rungs ARE glyph subjects — so the join
exists there and the discount is applied there.
`adjudicate_ledger_is_not_a_ledger` runs before
`adjudicate_notehead_is_not_a_notehead` in `ORDER` for exactly that reason.
Over the noteheads that produce an `unladdered_signal`:

| record | signals | `ledger_found == 0` base -> arm | `== 1` | `== 2` | `would_fire` base -> arm |
|---|---|---|---|---|---|
| `beethoven5-p1-p4` | 488 | 278 -> **282** | 58 -> 55 | 13 -> 12 | 278 -> **282** |
| `litolff whole` | 2,455 | 1,343 -> **1,349** | 385 -> 381 | 92 -> 90 | 1,343 -> **1,349** |
| `breitkopf whole` | 3,132 | 2,138 -> **2,138** | 243 -> 243 | 117 -> 117 | 2,138 -> **2,138** |

Noteheads lose the only rung that joined them to their staff, and it was a
staff-line fragment. **Nothing changes in the file**, because
`notehead_precision.UNLADDERED_SHIPS = False` — the signal is recorded, not
acted on. That is the whole of what the discount buys today, and it is stated
rather than inflated.

### 2d. `<note>` and the census

| record | `<note>` base | `<note>` arm | `notes_not_written` identical | census `unaccounted` | `family_refusals` all balanced |
|---|---|---|---|---|---|
| `beethoven5-p1-p4` | 1,769 | 1,769 | yes | `[]` | yes |
| `litolff whole` | 8,696 | 8,696 | yes | `[]` | yes |
| `breitkopf whole` | 7,872 | 7,872 | yes | `[]` | yes |

The ledger rule moves the ACCOUNTING and not the music, which is the honest
outcome for a rule whose only live consumer today is a signal that does not
ship. The new `family_refusals` block is a partition
(`refused + kept + abstained == verdicts`, where `verdicts` is counted from
the rows themselves rather than restated) and it balances on every family.

---

## 3. Sean's sidecar, re-run

`python3 -m tools.omr.staged.review.rerun <litolff whole> <sean.sidecar.json>
--staff staff/3/0/9 --out out/sean-viola-p3-after`

`reached_nothing` **23 -> 0**, by kind:

| action kind | before | after |
|---|---|---|
| `confirm_box` | 3 | 0 |
| `delete_box` | 18 | 0 |
| `own_box` | 2 | 0 |

Actions 68, human rows 127, verdicts naming a human row 7,949 (was 7,899), verdicts changed 730 (was 729), notes 8,588 -> 8,777.

Staff census on `staff/3/0/9` after:

```json
{
 "staff": "staff/3/0/9",
 "refused": {
  "not_a_notehead:human_not_a_symbol": 8,
  "not_a_notehead:clipped_fragment": 3,
  "ink_is_a_whole_rest": 1,
  "duration_narrowed": 4,
  "owned_by_another_staff": 3,
  "not_a_notehead:human_other_staff": 1,
  "not_a_rest:human_not_a_symbol": 1
 },
 "written": {
  "notehead": 44,
  "rest": 6
 },
 "refused_total": 21,
 "written_total": 50
}
```

**The two accidentals he owned to Violin II** (`glyph/3/0/9/1/0`, `glyph/3/0/9/7/2`) — both `accidentalNatural`, both carrying `owner:staff/3/0/8` and **NEITHER carrying a `Q.GLYPH_BAND_DISTANCE` row**, which is read straight off the amended record and is exactly why they reached nothing before: `adjudicate_glyph_owner`'s domain is that quantity, so the contest never saw either of them:

* `act-0008` `delete_box` on `glyph/3/0/9/1/0` — weighed by [['accidental_is_not_an_accidental', 1]], `reached_nothing` = False
* `act-0010` `own_box` on `glyph/3/0/9/1/0` — weighed by [['accidental_is_not_an_accidental', 1]], `reached_nothing` = False
* `act-0045` `own_box` on `glyph/3/0/9/7/2` — weighed by [['accidental_is_not_an_accidental', 1]], `reached_nothing` = False


### 3a. The two re-runs, and what the named-owner rule moved

The lane re-ran Sean's sidecar TWICE, and both are kept because the
difference between them is the finding that forced the second commit:

| | `owner:other` only | + the named-owner rule |
|---|---|---|
| `reached_nothing` | **0** | **0** |
| verdicts naming a human row | 7,953 | 7,949 |
| verdicts changed | 729 | **730** |
| `staff/3/0/9` written | `notehead` 45, `rest` 6 | `notehead` **44**, `rest` 6 |
| `staff/3/0/9` refused | 20 | **21** — the new one is `not_a_notehead:human_other_staff` 1 |
| `act-0045` on `glyph/3/0/9/7/2` | named, **weighed by nothing** | **WEIGHED** by `accidental_is_not_an_accidental` |

So the rule does exactly what Sean's clarification asked for: the accidental
he marked *belongs to Violin II* is now REFUSED on the Viola instead of
reaching a decision that declined it. The other of the two
(`glyph/3/0/9/1/0`) was already refused, but only because he ALSO deleted
that box — which is why one case was not enough to see the gap.

⚠️⚠️ **AND THE MUSICXML IS BYTE-IDENTICAL BETWEEN THE TWO RUNS** — both files
are 83,899 lines and 8,777 `<note>` elements, and `diff` over them is empty.
One NOTEHEAD moved from `written` to `refused` on this staff and no element
moved in the file. That is not a contradiction to wave through: the staff
census's `written` counts the DETECTIONS `_place_notes` placed into cells,
and the file's `<note>` count is taken after later gates that can still
withhold a whole bar (`bar_does_not_add_up` refuses 906 notes on
`beethoven5-p1-p4` alone). **The two are different populations and this lane
did not establish which gate swallowed the difference** — the one command
that would is a `coverage()` run on each amended record with
`notes_not_written` compared bucket by bucket, and it is not run here. What
IS established: the accounting moved by exactly one, in the direction and on
the subject Sean named, and the music did not move at all — the same shape
3.4 recorded for its own first pass.


Deciders that NAMED a human row for the first time (`per_stage.ADJUDICATE.by_decider`, which sits under `verdicts_naming_a_human_row` -- NAMED, not weighed):

* `adjudicate_accidental_is_not_an_accidental` — 18
* `adjudicate_arc_is_not_an_arc` — 1
* `adjudicate_arpeggiato_is_not_an_arpeggiato` — 3
* `adjudicate_dynamic_is_not_a_dynamic` — 2
* `adjudicate_ledger_is_not_a_ledger` — 15
* `adjudicate_rest_is_not_a_rest` — 3


---

## 4. The derived checks

`python3 -m tools.omr.staged.check`: **258 -> 267, +9**, every one a
`KNOWN_GAPS` entry that is named, and none suppressed.

| check | before | after | why |
|---|---|---|---|
| `inventory` | 12 | **19** | **+7**: one `<family>_is_not_a_<family> wants 'human_box_verdict'` per family |
| `reach` | 25 | **27** | **+2**: `accidental_is_not_an_accidental`, `arpeggiato_is_not_an_arpeggiato` |
| `health` | 0 | 0 | closed by the named per-family tests (§4b) |
| `brakes` | 9 | 9 | held at baseline (§4b) |
| `source_text_tests` | 47 | 47 | held at baseline (§4b) |
| every other | — | unchanged | |

### 4a. The nine new entries, named

Seven in `inventory.KNOWN_GAPS`, one per family:

    ledger_is_not_a_ledger wants 'human_box_verdict'
    accidental_is_not_an_accidental wants 'human_box_verdict'
    rest_is_not_a_rest wants 'human_box_verdict'
    arpeggiato_is_not_an_arpeggiato wants 'human_box_verdict'
    arc_is_not_an_arc wants 'human_box_verdict'
    dynamic_is_not_a_dynamic wants 'human_box_verdict'
    articulation_is_not_an_articulation wants 'human_box_verdict'

**The gap is the PRODUCER and it is structural, which is why N goes up rather
than a check being silenced.** `Q.HUMAN_BOX_VERDICT` has no gather site and
never will: a human is not a gather rung, and a `gather_human_boxes()`
reading a review sidecar would put a review artefact inside the measurement
path — the structural refusal that keeps a dossier out of it (CLAUDE.md §5b).
`review/human_evidence.py` files the rows and is in `reach.NOT_A_STAGE`. Every
decision that reads a human witness opens exactly one of these; 3.4A and 3.4C
opened one each before this lane opened seven. **The real repair is
ROADMAP 3.4b-check** — give the derived checks a declared out-of-pipeline
producer, so a human reader is WIRED rather than explained — and these nine
entries are its measured size.

Two in `reach.KNOWN_GAPS`, and each states two true things:

1. **The tool cannot see the read that exists.** `export._family_refusals`
   reads every family refusal through `rec.verdicts_of(quantity)` in a LOOP
   over `family_precision.FAMILY_REFUSALS`, derived from the adjudicators'
   own table rather than typed twice. `reach.qname()` resolves a literal
   `Q.X` or a literal string and nothing else — the same blind spot
   `inventory._gather_sites` documents paying for on `gather_cv_lines`. The
   other five family refusals are absent from this list only because each has
   a second reader that names it literally.
2. **And the census really is their only reader.** Neither `accidental` nor
   `arpeggiato` reaches a MusicXML element on any path. So the entry would be
   half-true even with a loop resolver.

Each of the nine leaves the list only when the fact it records changes — a
STAGE observing the quantity, or the family gaining a reader that is not the
census — never because a read landed.

### 4b. Findings that were avoidable, and were avoided

A first cut returned the human reason as a VARIABLE (`reason=reason`). That
makes `brakes.vocabulary_gap` report the whole MODULE as UNRESOLVED — every
decision in it, not just the one — because it reads the `reason=` slot's AST.
`brakes` went 9 -> 17. The repair is a two-branch literal dispatch in
`_refused_by_a_human` (and the same in `notehead_precision`), which is the
price of keeping that check able to fail. `brakes` is back at 9.

`health` likewise reported seven decisions as untested, because the
parametrised sweep names its quantities through a module-level table and
`health` scans each test FUNCTION's own AST. The repair is
`TestEachFamilyByName` — seven named cells beside the sweep, each asserting
what its decision DECIDES, what it RECORDS and which REASON it gives.
`health` is back at 0.

And a first cut of the test file used `inspect.getsource` four times, which
CLAUDE.md §6c forbids and `source_text_tests` counts. All four are now
behavioural: `_place_notes` is CALLED, `gather._observe_ladder` is CALLED,
and the dynamic consumer is proved end to end by two `f` letters spelling
`ff` and the same pair with one refused spelling `f`. `source_text_tests` is
back at 47.

---

## 5. The crops

`probe/crop_ledger.py`, written under `out/print/` (never `out/crops/` —
`.gitignore` excludes the latter), manifest
`out/print/crop-manifest-litolff-p1p4.json` with `VERDICT_none_yet: null` on
every row and the shipped constants stamped beside the population.

Four per reason and four of the boxes the rule KEEPS, cut from
`imslp984073.pdf` at 600 dpi, behind `crop_inferred._frame_ok` — **imported,
not copied**; a crop whose frame control is a second copy of somebody else's
is a crop whose control has not been run. **The control fired: 3 of 16
candidates were REFUSED** (`FRAME CONTROL FAILED`, contrast 7.77 / -80.83 /
-12.25), so 13 crops were written.

Each crop draws the staff's own five `Q.STAFF_LINES` in GREEN (Sean,
2026-09-23: *"there is a staff at the top and a staff at the bottom - i dont
know which staff the cell is focussing on"*), the rung steps the convention
allows as BLUE dashes, and a RED CORNER BRACKET on the exact box — never a
margin tick at its x. The caption carries the staff step, the gap to the
nearest staff line and how far beyond the band the box sits.

⚠️ **The verdicts in the crops are the decision's own, run there, not a second
copy of its rule.** `crop_ledger.build()` asserts that every quantity the
decision DECLARES is one this probe puts in the Log, so a widened declaration
fails loudly instead of quietly starving every crop.

Population by reason on `beethoven5-p1-p4` (the manifest carries it):
`on_a_staff_line` 1,214 · `tall_not_a_rung` 7 · `kept` 139 ·
`not_at_a_rung_step_WOULD_FIRE_held_back` 518.

The four `..._WOULD_FIRE_held_back` crops are the ones worth reading first:
they are boxes §1d's held-back rule would refuse and the shipped rules keep,
and Sean's verdict on them against the print is what says whether the uniform
offset distribution is the page or the staff-line model.

---

## 6. What could NOT be done, stated rather than dressed up

1. **`accidental` and `arpeggiato` refusals reach the EXPORT census and
   nothing else.** Neither family reaches a MusicXML element on any path.
   What the decision buys for those two is exactly that a human's *nothing*
   lands on the record as a verdict he can be shown, instead of on no stage —
   which is 3.4g's gate for them and no more than that. (The accidental's own
   consumer is ROADMAP 2.7, parked: DECISIONS 2026-09-23.)
2. **`glyph_owner`'s ladder is out of reach without a GATHER change** — §2b.
3. **`not_at_a_rung_step` does not ship** — §1d. The convention is Sean's and
   is not in doubt; what is in doubt is whether `Q.STAFF_LINES` can resolve
   the rung lattice on a merging plate, and the measurement says it cannot.
4. **The aspect arm of `tall_not_a_rung` is refuted, not deferred** — §1c,
   0 of 17,313.
5. **`heads_over` in `probe/ledger_geometry.py` is x-overlap within one cell
   and is NOT a positive control.** It says a notehead's x range overlaps the
   rung's inside the same bar; it says nothing about the head standing ON
   that rung. It is reported by the probe and is used as evidence nowhere.
   The positive controls are the fixtures in §1e and the crops.
6. **Six of the seven families have no geometric rule**, because nobody has
   stated a convention for them and nothing has been measured — §0.

---

## 7. Reproducing every number here, one command each

```bash
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
B=benchmarks/omr-family-refusals-2026-09

# §1 the measurement (writes out/ledger-geometry.json and the row caches)
python3 $B/probe/ledger_geometry.py \
  $L/beethoven5-p1-p4.record.json \
  $L/beethoven5-litolff-mvt1-whole-20260923.record.json \
  $L/brahms1-breitkopf-mvt1-whole-20260923.record.json

# §1 the reach of each candidate rule, swept, off the row cache
python3 $B/probe/ledger_reach.py

# §2 base vs arm on ONE tree, per record
python3 $B/probe/readjudicate_ledger.py $L/<record>.json --out $B/out

# §3 Sean's sidecar
python3 -m tools.omr.staged.review.rerun \
  $L/beethoven5-litolff-mvt1-whole-20260923.record.json \
  benchmarks/omr-stage-review-2026-09/out/sean-viola-p3/sean.sidecar.json \
  --staff staff/3/0/9 --out $B/out/sean-viola-p3-after

# §4 the checks
python3 -m tools.omr.staged.check
python3 -m tools.omr.staged.inventory --check
python3 -m tools.omr.staged.wiring --check
python3 -m tools.omr.staged.reach --check
python3 -m tools.omr.staged.gather_coverage

# §5 the crops
python3 $B/probe/crop_ledger.py --record $L/beethoven5-p1-p4.record.json \
  --pdf <library>/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --label litolff-p1p4 --dpi 600

# this file, re-assembled from the probe outputs
python3 $B/probe/write_findings.py

# §0 the tests
python3 -m pytest tools/omr/tests/test_staged_family_refusals.py -q
python3 -m pytest tools/omr/tests -m "not slow" -q
```

### RED first

`out/red-run.txt` holds the captured pair. With the eight modified modules
restored to `origin/main` and `family_precision.py` removed, the new test
file fails at COLLECTION (`1 error during collection`); with them back,
`50 passed` (61 once the named per-family cells and the behavioural consumer
tests were added). The restore used `cp` plus a plain `show origin/main:
<path>` redirect — never a checkout of a dirty file (CLAUDE.md §13) — and the
working tree was compared afterwards to confirm nothing was lost.

⚠️ **The DPI is not in these records' provenance** (`{"commit": ..., "dirty":
true}` and nothing else), so `crop_ledger.py` REFUSES to guess and takes
`--dpi` explicitly; 600 is the CLI default CLAUDE.md §7 records, and the
frame control is what says it was right — it passed on 13 crops and failed on
3, which is the control working rather than a number to trust.

---

## §3.4g-2 — Sean's two ledger conventions (2026-09-27)

Branch `claude/ledger-conventions-3.4g2`, resumed from the WIP `5b41b234`
(head-distance probe and fixtures; the lane was killed by the weekly limit)
and merged with `origin/main` `0470fb80`.

Sean, 2026-09-24, on the 13 crops of §5 (`out/print/ADJUDICATION-sean-2026-09-24.json`):
*"the ledger lines will only be on the outside of the staff and only happen
if there are actual notes in the staff"*. Registered as `[C90]` and `[C91]`
in `docs/engraving-conventions.md` (written straight into the registry, as
`C89` was; `conventions --check` clean, 118 entries).

### What changed, in `family_precision.adjudicate_ledger_is_not_a_ledger` only

Order: human -> `inside_the_staff` -> `on_a_staff_line` (outer lines only) ->
`tall_not_a_rung` (tall AND no head ON it) -> `no_head_on_the_rung` -> kept.
`RUNG_STEP_SHIPS` stays `False`.

| reason | rule |
|---|---|
| `inside_the_staff` (new, `[C90]`) | the box's centre is in the band from line 1 to line 5 (step 0..8). No tolerance: the band's edges ARE the outer lines. |
| `on_a_staff_line` (kept) | now reaches only a box just OUTSIDE line 1 or 5, within the measured 0.25 spaces. Kept as its own reason rather than folded into the band with a tolerance, because the band is Sean's statement and the tolerance is registration scatter. |
| `tall_not_a_rung` (tightened) | height > 0.5 spaces AND no notehead box INTERSECTS the rung's box. The 0.5 floor is not retuned; "on" is an intersection and needs no constant. |
| `no_head_on_the_rung` (new, `[C91]`) | no `notehead*` `Q.GLYPH_BOX` in the same cell that x-overlaps the rung with its centre within `HEAD_NEAR_TOL_SPACES`, AND none standing FARTHER OUT than the rung. |

Every box with a cell unit carries `heads_x_overlapping`,
`head_distance_spaces`, `head_outward_spaces` and `head_on_the_box` in its
detail, so a box both conventions condemn shows both.

### The head tolerance — p95, and the outward clause

`probe/ledger_heads.py` (extended with the SIGNED side), over the rungs the
3.4g rules keep:

| record | kept by 3.4g | head distance p50 | **p95** | p99 |
|---|---|---|---|---|
| `beethoven5-p1-p4` | 346 | 0.70 | **2.67** | 5.895 |
| Litolff whole | 1,777 | 0.86 | **2.67** | 4.995 |
| Breitkopf whole | 6,305 | 0.58 | **1.885** | 2.93 |

`HEAD_NEAR_TOL_SPACES = 2.75`, the smallest quarter-space value covering all
three — the arithmetic that made `ON_A_STAFF_LINE_TOL_SPACES` 0.25.

⚠️ **A symmetric tolerance alone cuts long ladders.** Of the kept rungs past
2.75 spaces, split by which side of the rung the x-overlapping heads stand:

| record | past 2.75 | a head farther OUT (ladder inner rung) | heads only STAFFWARD (the beam shape) | no head x-overlapping |
|---|---|---|---|---|
| p1-p4 | 23 | 5 | 10 | 8 |
| Litolff | 122 | 43 | 35 | 44 |
| Breitkopf | 89 | 51 | 19 | 19 |

The outward heads sit 2.9-4.6 spaces off — four- and five-rung ladders, and
nothing at the 6+ spaces a neighbouring staff's head would sit at. So a head
farther out than the rung keeps it at any distance (`[C4]`: the ladder runs
from the staff to its note). This is an ADDITION to the brief's "within a
measured vertical tolerance", made because the measurement said the
symmetric rule alone would refuse 99 plausible inner rungs.

### `tall_not_a_rung`, re-measured on its one miss (crop 9, `glyph/4/1/2/5/14`)

Height **0.68 spaces in BOTH frames** (canonical 68 on a 100-unit cell space;
page 10.7 px on a 15.75 px staff spacing) — not a frame artefact. A
`noteheadBlackOnLine` (`glyph/4/1/2/5/1`, 1.37 spaces tall) has its centre
**0.085 spaces** from the rung's and its box contains the rung box's whole
height; a second head (`glyph/4/1/2/5/8`) overlaps it by 0.52. On the merging
plate the rung's box has swallowed the ink of the head standing on it, so the
height was measuring the head. Crop 8 (the beam): 0.62 spaces, its nearest
x-overlapping head 2.975 spaces STAFFWARD, no intersection — still refused.
Whole-record effect: tall refusals **7 -> 1 / 22 -> 5 / 8 -> 0**; of the
released boxes 5 / 15 / 7 become KEPT, 1 / 2 / 0 are refused
`inside_the_staff` and 0 / 0 / 1 `on_a_staff_line`.

### Sean's 13 crops under the new rules

All 13 agree with Sean. RED first: the fixtures (`TestSeansThirteenCrops`)
fail on the 3.4g rule.

| n | subject | Sean | 3.4g | **3.4g-2** | step | heads: nearest / farthest out (spaces) |
|---|---|---|---|---|---|---|
| 1 | `glyph/4/0/9/1/7` | no — middle of the staff | kept (held-back would fire) | **`inside_the_staff`** | 4.96 | 2.06 / — |
| 2 | `glyph/4/0/9/5/14` | no | kept (held-back would fire) | **`inside_the_staff`** | 1.49 | 4.205 / — |
| 3 | `glyph/4/1/7/5/21` | **yes** | kept (held-back would fire) | **kept** | -6.72 | 0.515 / -0.515 |
| 4 | `glyph/1/0/2/15/3` | no — whole-rest bar | `on_a_staff_line` | **`inside_the_staff`** | 5.55 | 0.245 / — |
| 5 | `glyph/2/0/10/14/10` | no | `on_a_staff_line` | **`inside_the_staff`** | 2.14 | 1.05 / — |
| 6 | `glyph/3/0/2/14/1` | no — whole rest | `on_a_staff_line` | **`inside_the_staff`** | 5.65 | none in the cell |
| 7 | `glyph/3/0/5/13/5` | no — whole rest | `on_a_staff_line` | **`inside_the_staff`** | 0.15 | 2.725 / — |
| 8 | `glyph/2/0/1/4/12` | no — a beam | `tall_not_a_rung` | **`tall_not_a_rung`** | -6.04 | 2.975 / -2.975 |
| 9 | `glyph/4/1/2/5/14` | **yes** | `tall_not_a_rung` (wrong) | **kept** | 12.58 | 0.085 / 0.505, on the box |
| 10 | `glyph/4/1/9/11/17` | no — middle of the staff | `tall_not_a_rung` | **`inside_the_staff`** | 4.32 | 0.415 / — |
| 11 | `glyph/3/0/7/6/14` | **yes** | kept | **kept** | -1.85 | 1.21 / 1.21 |
| 12 | `glyph/3/0/7/7/8` | **yes** | kept | **kept** | -1.90 | 1.125 / 1.125 |
| 13 | `glyph/4/1/2/3/19` | **yes** | kept | **kept** | 10.22 | 0.585 / 1.145 |

⚠️ **Crops 4, 6 and 7 are refused `inside_the_staff`, not
`no_head_on_the_rung`.** All three lie inside the band, and position runs
first because the head tolerance was measured on boxes OUTSIDE it. Under the
other order only crop 6 would read `no_head_on_the_rung`: crops 4 and 7 each
have an x-overlapping `notehead*` box (0.245 and 2.725 spaces off) standing
at the whole-rest slot (step 5.5): on crop 4 a `noteheadWholeInSpace` at step
5.06 on top of a `restWhole` at the same 5.06 (`glyph/1/0/2/15/5` and `/2`),
on crop 7 a `noteheadBlackInSpace` at step 5.60 (`glyph/3/0/5/13/4`) — the
WHOLE REST boxed by the detector as a head. And `notehead_is_a_whole_rest` runs after this decision in
`adjudicate.ORDER`, so the ledger rule cannot know. The refusal is right
either way; the limit is recorded (`[C91]` Known exceptions) and pinned by
`test_crop_6_is_condemned_by_BOTH_conventions_and_the_record_says_so`.

### Base vs arm, on ONE tree — `probe/readjudicate_ledger_g2.py`

BASE = 3.4g's function loaded from `origin/main` and swapped into today's
registry entry; ARM = this tree. Full ADJUDICATE -> EXPORT in both.
**Control first, and it could fail: the BASE ledger tally equals 3.4g's
recorded arm reason for reason — 1,878 of 1,878 / 7,617 of 7,617 / 7,818 of
7,818.** Run sequentially; logs `out/arm-g2-*.log`, results
`out/ledger-g2-arm-*.json`.

| record | boxes | `inside_the_staff` | `on_a_staff_line` | `tall_not_a_rung` | `no_head_on_the_rung` | kept |
|---|---|---|---|---|---|---|
| p1-p4 before | 1,878 | — | 1,214 | 7 | — | 657 |
| p1-p4 **after** | | **1,370** | **156** | **1** | **18** | **333** |
| Litolff before | 7,617 | — | 4,708 | 22 | — | 2,887 |
| Litolff **after** | | **5,122** | **698** | **5** | **79** | **1,713** |
| Breitkopf before | 7,818 | — | 1,408 | 8 | — | 6,402 |
| Breitkopf **after** | | **1,222** | **284** | **0** | **38** | **6,274** |

Transitions (the boxes that MOVE): kept -> `inside_the_staff` **311 / 1,110 /
97**; kept -> `no_head_on_the_rung` **18 / 79 / 38**; `tall_not_a_rung` ->
kept **5 / 15 / 7**; `on_a_staff_line` -> `inside_the_staff` 1,058 / 4,010 /
1,125 (a renaming — the same boxes, now refused on position). Newly refused
from kept: **329 / 1,189 / 135**; newly kept: **5 / 15 / 7**.

| record | `glyph_owner` moved | `unladdered_signal` `ledger_found==0` base -> arm | `<note>` base / arm | `notes_not_written` identical | census `unaccounted` / balanced |
|---|---|---|---|---|---|
| p1-p4 | **0** of 1,386 | 282 -> 278 | 1,769 / 1,769 | yes | `[]` / yes |
| Litolff | **0** of 6,013 | 1,349 -> 1,344 | 8,686 / 8,686 | yes | `[]` / yes |
| Breitkopf | **0** of 24,795 | 2,138 -> 2,138 | 7,872 / 7,872 | yes | `[]` / yes |

**`glyph_owner` does not move, and that is expected, not a result:** its
ladder tier reads `Q.GLYPH_LADDER`, GATHER's anonymous rung COUNT (§2b), so
no ADJUDICATE refusal reaches it until roadmap 2.14. ADJUDICATE's own ladder
does see the change — the rescued rungs give a few heads their rung back
(`ledger_found==0` 282 -> 278, 1,349 -> 1,344) — and that signal does not
ship (`UNLADDERED_SHIPS = False`). The music does not change on any record.

### The crops — `probe/crop_ledger_g2.py`

From `beethoven5-p1-p4` (the record Sean's 13 came from), 600 dpi, frame
control imported (`crop_inferred._frame_ok`) — **it fired on 2 of 16
candidates** (contrast -39.38 and 7.77), so 14 were written, all under
`out/print/g2-litolff-p1p4-*`. Each draws the staff's own lines (GREEN), the
box (RED bracket), every notehead box that x-overlaps it (ORANGE) and both
verdicts. Manifest `out/print/crop-manifest-g2-litolff-p1p4.json`, every row
`VERDICT_none_yet: null`.

- kept -> `inside_the_staff`: `p4-s0-st9-c2-g6`, `p2-s0-st5-c4-g5`,
  `p2-s0-st4-c2-g13`, `p2-s0-st4-c1-g6`
- kept -> `no_head_on_the_rung`: `p1-s0-st3-c14-g0`, `p2-s0-st2-c2-g12`,
  `p2-s1-st0-c12-g6`, `p3-s1-st0-c6-g12`
- kept by both: `p2-s0-st8-c2-g16`, `p2-s0-st6-c1-g8`, `p2-s0-st5-c1-g25`,
  `p3-s0-st7-c7-g8`
- rescued: `p4-s1-st2-c5-g14` (crop 9), `p4-s1-st7-c5-g21` (crop 3)

⚠️ **Not adjudicated, and one thing is worth Sean's eye first.** To this
lane's eye (not his), two of the four `no_head_on_the_rung` crops
(`p1-s0-st3-c14-g0`, `p2-s1-st0-c12-g6`) look like REAL rungs whose notehead
is printed but was never boxed by the detector — the rule reads the
detector's heads, and on a merging plate the heads on ledger lines are what
the detector loses. The other two look like staff-line fragments beside heads
hanging below line 1. Of the newly refused `no_head` boxes, **8 / 44 / 19**
have no x-overlapping head at all (where a missed head would hide) and **10 /
35 / 19** have heads only staffward past the tolerance. If Sean calls the two
real, the next step is a second witness for "a note is here" that is not the
detector (ink under the rung), not a wider tolerance.

### What could NOT be done, or was done differently from the brief

1. Crops 4, 6, 7 carry `inside_the_staff`, not `no_head_on_the_rung` — above.
2. The head check has an OUTWARD clause beyond the brief's symmetric
   tolerance — measured above; removing it is one line and refuses 99 inner
   rungs.
3. A whole rest boxed as a notehead counts as a head (ORDER) — `[C91]`.
4. `glyph_owner` is unreachable until 2.14.
5. The new refusals are unadjudicated; only the 13 original crops are Sean's.

### Checks and tests

- RED: `out/red-run-g2.txt` — the final test file against `origin/main`'s
  `family_precision.py` (copied aside with `cp`, never a checkout): **19
  failed, 67 passed**; with the 3.4g-2 rule: **86 passed**.
- `pytest tools/omr/tests -m "not slow"`: **3,248 passed, 3 skipped**.
- `python3 -m tools.omr.staged.check`: **267** (baseline 267, unchanged).
  `inventory --check`, `wiring --check`, `reach --check`,
  `conventions --check`: all exit 0.

### Reproducing

```bash
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
B=benchmarks/omr-family-refusals-2026-09
python3 $B/probe/ledger_heads.py $L/beethoven5-p1-p4.record.json   # one record per call
python3 $B/probe/readjudicate_ledger_g2.py $L/<record>.json --out $B/out   # SEQUENTIALLY
python3 $B/probe/crop_ledger_g2.py --record $L/beethoven5-p1-p4.record.json \
  --pdf <library>/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --label litolff-p1p4 --dpi 600
```
