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
record — 1,878 of 8,486 detections, more than every `noteheadBlack*`
spelling put together. Two thirds of them are inside the staff band, where
the convention says a ledger line cannot be.

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
| `breitkopf whole` | _not run_ | | | | | |

The BASE refuses nothing on any record: the arm is the only thing moving,
which is what says the numbers are the rule's and not the rebuild's.

### 2b. `glyph_owner` — **0 verdicts changed, and that is the finding**

| record | `glyph_owner` verdicts (base / arm) | **moved** |
|---|---|---|
| `beethoven5-p1-p4` | 1,386 / 1,386 | **0** |
| `litolff whole` | 6,013 / 6,013 | **0** |
| `breitkopf whole` | _not run_ | |

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
| `breitkopf whole` | _not run_ | | | | |

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
| `breitkopf whole` | _not run_ | | | | |

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

Actions 68, human rows 127, verdicts naming a human row 7,953 (was 7,899), verdicts changed 729 (was 729), notes 8,588 -> 8,777.

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
  "not_a_rest:human_not_a_symbol": 1
 },
 "written": {
  "notehead": 45,
  "rest": 6
 },
 "refused_total": 20,
 "written_total": 51
}
```

**The two accidentals he owned to Violin II** (`glyph/3/0/9/1/0`, `glyph/3/0/9/7/2`) — both `accidentalNatural`, both carrying `owner:staff/3/0/8` and **NEITHER carrying a `Q.GLYPH_BAND_DISTANCE` row**, which is read straight off the amended record and is exactly why they reached nothing before: `adjudicate_glyph_owner`'s domain is that quantity, so the contest never saw either of them:

* `act-0008` `delete_box` on `glyph/3/0/9/1/0` — weighed by [['accidental_is_not_an_accidental', 1]], `reached_nothing` = False
* `act-0010` `own_box` on `glyph/3/0/9/1/0` — weighed by [['accidental_is_not_an_accidental', 1]], `reached_nothing` = False
* `act-0045` `own_box` on `glyph/3/0/9/7/2` — weighed by nothing, `reached_nothing` = False

⚠️ **READ FROM `out/sean-viola-p3-after-owner-other-only/`** — the FIRST re-run, before the named-owner rule the first re-run's own result forced. The second re-run was still going when this file was assembled; re-run the command in §7 and then `write_findings.py` to replace this section.

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
