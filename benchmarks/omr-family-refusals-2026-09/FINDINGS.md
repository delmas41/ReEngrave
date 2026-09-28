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

---

## §3.4g-3 — a rung with no BOXED head abstains; the paper is the second witness (2026-09-28)

Branch `claude/ledger-ink-3.4g3`, off `origin/main` `8226aa93`. Sean,
2026-09-27 (`out/print/ADJUDICATION-sean-2026-09-27.json`), on the four
`no_head_on_the_rung` crops of §3.4g-2: crops 1 and 3 are REAL rungs whose
printed notehead the detector never boxed; 2 is the bottom staff line; 4 is a
whole rest hanging on the bottom line. So the refusal was being witnessed by
the detector's recall alone — the witness that fails exactly where heads fuse
with their rungs — and a missing box is *cannot tell* (CLAUDE.md §2 rule 8).

### Part A (ADJUDICATE) — `no_head_on_the_rung` stops refusing on boxes alone

Where no notehead box is near the rung (the 3.4g-2 test, unchanged), the
ledger decision now ABSTAINS `rung_without_boxed_head` — unless Part B's ink
witness settles it. The abstention carries its evidence (`used`, the head
facts, `ink_witness: null`, and GATHER's own abstention reason as
`ink_witness_declined` where GATHER could not look). `inside_the_staff`,
`on_a_staff_line`, `tall_not_a_rung` are untouched. `export._family_refusals`
now names abstentions by reason (`abstained_reasons`), so 79 of these are not
read as 79 `no_staff_geometry`.

⚠️ **The brief said crop 2 was refused on position "as before". It was not.**
Its centre is 0.315 spaces outside line 1 in the PAGE frame (step -0.63), past
`ON_A_STAFF_LINE_TOL_SPACES` 0.25, so 3.4g-2 refused it `no_head_on_the_rung`
like the other three; crop 4 likewise (0.29 spaces). Under Part A alone all
four ABSTAIN; the two refusals can come back only through Part B. On the cell
raster both boxes lie ON the bottom staff line (the erasure removed it — see
the crops): the page-frame `Q.STAFF_LINES` sits ~0.3 spaces off on this
merging plate, the registration cause `RUNG_STEP_SHIPS = False` already
records. A cell-frame line test would catch both; not built here.

RED first: `out/red-run-g3.txt` — the Part A tests against `8226aa93`: 5
failed, 2 passed (the two positive controls).

`probe/readjudicate_ledger_g3.py` — BASE = 3.4g-2's function from `8226aa93`
swapped into today's registry, ARM = this tree, one tree, full ADJUDICATE ->
EXPORT in both; **control: the BASE tally equals 3.4g-2's recorded arm reason
for reason**; "nothing else moves" is MEASURED by comparing every verdict of
every quantity (outcome, value, reason):

| record | control | `no_head` refused -> abstained | verdicts moved, all quantities | `<note>` base / arm | census |
|---|---|---|---|---|---|
| `beethoven5-p1-p4` | 1,878 of 1,878 | **18 -> 18** | 18, all `ledger_is_not_a_ledger` | 1,769 / 1,769 | balanced, `[]` |
| Litolff whole | 7,617 of 7,617 | **79 -> 79** | 79, all `ledger_is_not_a_ledger` | 8,686 / 8,686 | balanced, `[]` |
| Breitkopf whole | 7,818 of 7,818 | **38 -> 38** | 38, all `ledger_is_not_a_ledger` | 7,872 / 7,872 | balanced, `[]` |

`notes_not_written` identical on every record; `unladdered_signal` identical
base/arm on every record (below).

⚠️ **The one consumer of kept rungs does NOT yet treat an abstained rung as
not-kept.** `notehead_precision._ledger_rungs_in_cell` skips a rung only when
its verdict `value is True`, so an ABSTAINED rung (value `None`) is counted —
that file belongs to lane 2.7b and was not edited. Measured effect: none (the
`unladdered_signal` histogram is identical base/arm on all three records — a
rung with no head near it is by construction on no head's ladder search — and
that signal does not ship, `UNLADDERED_SHIPS = False`). The fix is one line
for 2.7b: skip unless the verdict is DECIDED `False`. EXPORT reads no kept
rung anywhere; `glyph_owner` reads GATHER's anonymous ladder (2.14).

### Part B (GATHER) — `Q.LEDGER_INK_UNDER`

`gather.gather_ledger_ink`, beside `gather_ink` and off the SAME staff-erased
raster (`READERS.CV_INK`; CLAUDE.md §9: erase for the CV consumer, never for
the detector). Per `ledgerLine` box, `gather.ledger_ink_under`: the ink
fraction in a notehead-sized window (1.3 x 1.0 spaces) centred on the rung,
and the same window half a space above and below (a head sits ON its rung or
hangs beside it), with the rung's stroke rows (box +- 0.1 space) removed from
count AND area; value = the best of the three; `detail` carries all three and
a BACKGROUND = the smaller of the two windows one full space above/below.
Declined, never defaulted: no erased raster -> `no_mask`; no unit ->
`no_staff_geometry`. Registered in `record.Q` (CLAIM `measurement`;
`capture.UNSCORED` `relation`), declared in the ledger decision's `wants` and
`composed_from`; every detail key it writes is read by the decision.

The rule, only where no boxed head is near:

| witness | outcome |
|---|---|
| `under >= LEDGER_INK_KEPT_MIN` (0.55) AND `under - background >= LEDGER_INK_KEPT_CONTRAST_MIN` (0.10) | KEPT, `ink_under_the_rung` |
| `under <= LEDGER_INK_REFUSED_MAX` (0.05) | REFUSED, `no_head_on_the_rung` — two witnesses (box row + ink row in `used`) |
| anything else, or no witness | ABSTAINED, `rung_without_boxed_head` |

### The thresholds, measured — `probe/ledger_ink_hist.py`, `probe/ledger_ink_thresholds.py`

On a real ARM gather of Litolff pdf pages 1-12 (4,947 ledger boxes; the
priced page 3 alone has 500). Populations by the same record's 3.4g-2
verdicts (which read no ink): POS_on = kept with a notehead box ON the rung
(548); POS_near = kept, nearest head <= 0.75 sp (495); NEG = refused
`inside_the_staff` (3,414) + `on_a_staff_line` (407); TARGET = no boxed head
(50). `out/ledger-ink-hist-litolff-p1-12.json`, `…-p3.json`,
`out/ledger-ink-thresholds-litolff-{p1-12,p3}.txt`.

`under`:

| population | n | p5 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|
| POS_on | 548 | **0.574** | 0.718 | 0.847 | 0.902 | 0.974 |
| POS_near | 495 | 0.563 | 0.731 | 0.847 | 0.900 | 0.976 |
| NEG_inside | 3,414 | 0.0 | 0.024 | 0.259 | 0.520 | 0.810 |
| NEG_online | 407 | 0.0 | 0.106 | 0.339 | 0.594 | 0.830 |
| TARGET | 50 | 0.0 | 0.007 | 0.373 | 0.733 | 0.794 |

`under - background` (contrast): POS_on p5 **0.098**, p25 0.43, p50 0.61;
NEG_inside p50 0.15, p75 0.40, p95 0.68. (Page 3 alone: POS_on `under` p5
0.54, NEG_inside p50 0.18 / p95 0.75.)

Where they separate: **at the bottom, cleanly** — 0 of 548 POS_on (minimum
0.076) and 0 of 495 POS_near read `under <= 0.05`, against 1,024 of 3,821
negatives and 15 of 50 targets. **At the top, not by these negatives**: 23%
of them clear both keep thresholds, because inside the band the erased raster
still holds the staff's own notes — a staff-line fragment is where the
detector fires beside a head. So the KEEP thresholds are the positives' own
p5s (under 0.574 -> 0.55; contrast 0.098 -> 0.10; together 501 of 548 = 0.91
of positives kept), and they are only ever applied to a box that is outside
the band, off every line, rung-thick and has no boxed head.

**RED (the windows swapped — background read as `under`)**: AUC against the
negatives **0.786** vs **0.931** for the real window (POS_on, pages 1-12). On
page 3 alone (37 / 417) the gap is narrower, 0.887 vs 0.940 — positives sit
in dense neighbourhoods, so the neighbourhood alone separates somewhat; the
window adds what the neighbourhood does not. The control can fail and on the
one page nearly did, which is why the thresholds come from twelve.

### Priced by two full re-gathers — `probe/gather_ledger_ink_ab.py`, `probe/compare_gathers_g3.py`

Litolff pdf index 3, `--no-surya --no-ocr`, scan weights
(`hollow-graft-shift09`), 600 dpi, `OMR_DIRECTION_TEXT_SCAN_GATE=1`; both
arms `python3 -m tools.omr.staged` on commit `99a6b278`, **`dirty: False`
both** (the compare refuses otherwise). BASE = the same process with
`gather_ledger_ink` a no-op and the 3.4g-2 decision. The records stay in the
session scratchpad (machine-local). `out/gather-ab-g3-litolff-p3.json`.

| | base | arm |
|---|---|---|
| detector boxes | 1,928 | 1,928 — **identical list** (no jitter; every difference is the change) |
| `Q.LEDGER_INK_UNDER` rows | 0 | 500 (0 abstentions) |
| kept `ledger_line` | 75 | 75 |
| kept `ink_under_the_rung` | — | **1** |
| refused `no_head_on_the_rung` | 8 | **3** (two witnesses) |
| abstained `rung_without_boxed_head` | — | **4** |
| `inside_the_staff` / `on_a_staff_line` | 383 / 34 | 383 / 34 |
| verdicts moved, all quantities | | **5, all ledger** |
| `<note>` | 549 | 549 — MusicXML byte-identical |
| census | balanced | balanced |

Pages 1-12 (the arm gather re-decided on this tree; base = 3.4g-2 on the
same rows; `out/ledger-g3-arm-g3-arm-litolff-p1-12.json`): of **50** former
`no_head_on_the_rung` refusals, **22 KEPT** `ink_under_the_rung`, **15
REFUSED** with two witnesses, **13 ABSTAIN**; 35 verdicts moved, all ledger;
`<note>` 5,476 / 5,476.

`staged.check` **264** (baseline 264): `gather_coverage` lists the quantity
as gathered by `gather_ledger_ink`; `inventory`, `wiring`, `reach` exit 0.

### Sean's four, re-measured off the PDF — `probe/ledger_ink_crops_g3.py`

Pages re-prepared exactly as GATHER prepares them; the cell found by GATHER's
own numbering and checked against the p1-p4 record (**frame controls: the
cell's page box and the rung's canonical-to-page box both 0.0 px off**, all
four); `gather.ledger_ink_under` on the record's own box; today's decision
run over the record's rows plus the measured value. Crop 4's subject exists
on the fresh page-3 gather too (`glyph/3/1/0/6/12`) and its FILED value there
is 0.1314 — the same number.

| n | subject | Sean | under | best | background | contrast | 3.4g-2 | **3.4g-3** |
|---|---|---|---|---|---|---|---|---|
| 1 | `glyph/1/0/3/14/0` | real rung | 0.737 | on | 0.087 | 0.650 | refused | **KEPT `ink_under_the_rung`** |
| 2 | `glyph/2/0/2/2/12` | bottom staff line | 0.005 | above | 0.000 | 0.005 | refused | **REFUSED `no_head_on_the_rung`** |
| 3 | `glyph/2/1/0/12/6` | real rung | 0.937 | above | 0.747 | 0.190 | refused | **KEPT `ink_under_the_rung`** |
| 4 | `glyph/3/1/0/6/12` | whole rest on the bottom line | 0.131 | on | 0.009 | 0.122 | refused | **ABSTAINED** |

**1 and 3 kept, 2 refused. Crop 4 is NOT refused: it ABSTAINS.** The window
centred on the box catches the left corner of the whole rest (0.13), above
the paper floor and far below a head; the machine cannot tell it from a faint
head by ink alone and says so — it never keeps it. Crop 3's contrast (0.19)
clears the floor because the floor is the positives' p5; at 0.2 it would
abstain. It was not tuned to it.

### The crops — `out/print/g3-*`

Each: LEFT the cell as the detector saw it, RIGHT staff-erased as the witness
reads it; the staff's own lines GREEN; the rung box a RED corner bracket; the
three head windows MAGENTA (solid = best), the two background windows CYAN;
both verdicts and every number in the caption. Manifests
`out/print/crop-manifest-g3-seans-four.json` and
`crop-manifest-g3-ink-kept.json`, every row `VERDICT_none_yet: null`; the
frame control refused none.

- Sean's four: `g3-litolff-p1p4-p1-s0-st3-c14-g0-sean1-real`,
  `…-p2-s0-st2-c2-g12-sean2-bottom-line`, `…-p2-s1-st0-c12-g6-sean3-real`,
  `…-p3-s1-st0-c6-g12-sean4-whole-rest`.
- 8 newly KEPT `ink_under_the_rung` (of 22 on pages 1-12; one per staff
  first, seeded): `g3-litolff-p1-12-p2-s1-st10-c14-g9`, `-p5-s0-st6-c13-g8`,
  `-p5-s1-st1-c6-g5`, `-p5-s1-st3-c10-g1`, `-p6-s1-st7-c8-g14`,
  `-p8-s0-st6-c10-g3`, `-p9-s0-st10-c4-g2`, `-p9-s1-st3-c0-g10`
  (`-ink_kept.png`). The re-measured value equals the filed one on all 8 (a
  control that could fail).

⚠️ **Not adjudicated. To this lane's eye (not Sean's), 7 of the 8 are real
rungs with a head on or hanging from them, and one is not**:
`glyph/6/1/7/8/14` — the "rung" is a long horizontal stroke the cell's own
line model does not cover (it looks like the staff's bottom line), and the
ink under it is the word *cresc.* The witness cannot tell a head from a
letter — it is ink — and the keep side has no negative population to bound
it (above). Same registration family as crops 2 and 4.

### What could NOT be done, or was done differently from the brief

1. **Crop 4 abstains; it is not refused** — measured 0.131, between the floor
   and a head. "2 and 4 refused" is half met.
2. **Crop 2 was never a position refusal** (0.315 sp outside line 1 in the
   page frame); it is refused now by the ink.
3. **The ADJUDICATE consumer of kept rungs** (`_ledger_rungs_in_cell`, lane
   2.7b's file) still counts an abstained rung; effect measured zero.
4. **The negatives cannot bound the keep thresholds** (in-band ink holds the
   staff's own notes); they are the positives' p5s.
5. **Pricing is one page** (p3), as briefed; the threshold population is a
   second, arm-only gather of pages 1-12, re-decided on its own rows.
6. The gathered records are not committed (~10 MB and ~135 MB).

### Checks and tests

- RED: `out/red-run-g3.txt` (5 failed / 2 passed against `8226aa93`).
- `pytest tools/omr/tests -m "not slow"`: **3,323 passed, 3 skipped** (was 3,320 before the threshold tests).
- `python3 -m tools.omr.staged.check`: **264** (baseline 264).

### Reproducing

```bash
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
B=benchmarks/omr-family-refusals-2026-09
PDF=<library>/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
python3 $B/probe/readjudicate_ledger_g3.py $L/<record>.json --out $B/out        # Part A, SEQUENTIALLY
OMR_DIRECTION_TEXT_SCAN_GATE=1 python3 $B/probe/gather_ledger_ink_ab.py --arm base -- $PDF --pages 3 --weights $W --no-surya --no-ocr --out base.json
OMR_DIRECTION_TEXT_SCAN_GATE=1 python3 $B/probe/gather_ledger_ink_ab.py --arm arm  -- $PDF --pages 3 --weights $W --no-surya --no-ocr --out arm.json
python3 $B/probe/compare_gathers_g3.py base.json arm.json --out ab.json        # clean tree only
python3 $B/probe/ledger_ink_hist.py arm.json --out hist.json
python3 $B/probe/ledger_ink_crops_g3.py --record $L/beethoven5-p1-p4.record.json --pdf $PDF \
  --label litolff-p1p4 --subjects glyph/1/0/3/14/0 glyph/2/0/2/2/12 glyph/2/1/0/12/6 glyph/3/1/0/6/12 \
  --names sean1-real sean2-bottom-line sean3-real sean4-whole-rest --manifest m.json
```
