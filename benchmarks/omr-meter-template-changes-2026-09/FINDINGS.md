# The best meter reader only ever looked at the first bar

2026-09-15, branch `claude/meter-template-at-changes`, base
`origin/claude/gather-stage-coverage-qp6j01` (`3bf14280`).
**New flag `OMR_METER_TEMPLATE_AT_BAR`, DEFAULT OFF. Nothing on any existing
path changes; with the flag off the record is byte-identical.**

`gather.gather_meter` hands `locate_time_signature` nothing but
`header_cells_for_page(pws)` — one crop per staff, the HEADER window only. So a
time signature printed anywhere else on a staff, which is to say a meter
**CHANGE**, is read by the DETECTOR alone (`_meter_from_digits`,
`_meter_from_letter`) — the weak reader, on exactly the ink it is worst at.
CLAUDE.md prices that: on a Breitkopf scan the glyph readers vote `9/4` where
the page prints `9/8`, miss the real change, and propose five spurious `4/4`
changes just over `METER_CHANGE_FLOOR`.

This points the template reader at candidate mid-staff bar heads as well.

---

## 1. REACH FIRST — and the briefed design is WRONG AS STATED on a scan

`probe/candidate_columns.py`, over committed legacy transcriptions (real
detector output; a cloud container has no weights, so this is what exists).
Committed table: `out/candidate-columns.json`.

| document | columns on the page | candidate columns (>=1 staff sees meter-shaped ink) | probes if every staff is asked | header probes today |
|---|--:|--:|--:|--:|
| **Brahms 1 / Breitkopf p1-3** | 51 | **38 (74.5%)** | **525** | 83 |
| Mahler 5 / Peters p11 | 25 | 9 (36.0%) | 90 | 26 |
| Beethoven 5 / Litolff p1 (a movement OPENING) | 33 | **0** | 0 | 12 |

⚠️⚠️ **THE BRIEF'S ASSUMPTION — that one staff's detection names a handful of
candidate bars — IS FALSE ON A SCAN. On Brahms three quarters of the page is a
candidate.** Tightening the gate does not rescue it: a two-staff quorum on the
DETECTIONS still leaves 30 of 51 columns (58.8%), three leaves 23 (45.1%). The
detector fires meter-shaped ink all over a dense scan, which is the same fact
that produces its five spurious changes.

**So the candidacy gate is NOT where the safety can live**, and the design is
not abandoned but re-anchored: candidacy stays at its loosest
(`METER_TEMPLATE_AT_BAR_MIN_CANDIDATE_STAVES = 1`, because the whole point is
to ask the staves that detected NOTHING) and the safety moves entirely onto
ACCEPTANCE. Cost is real and bounded rather than hidden: 525 windows at a
measured **20.2 ms each** is ~11 s for a three-page document.

⚠️ Litolff p.1's clean **0** is the mechanism agreeing with itself — a movement
opening prints its meter in the header and nowhere else, so there is nothing to
ask about. It is also a reminder that a per-document reach of zero is normal.

---

## 2. THE EMPTY-WINDOW MEASUREMENT — the number that decides this

⚠️⚠️ **THIS PROJECT HAS ALREADY PAID FOR THIS HAZARD ONCE.** CLAUDE.md, the
key-signature section, in terms: *"the locator found no run and abstained; the
template found a clean window and answered a confident `fifths: 0` — a key
signature fabricated out of a crop containing none. **The reader that can say
'zero' is the one that must never be given an empty window.**"* A mid-staff bar
head is an empty window almost everywhere, and `min_score` was calibrated on
HEADER windows where a meter is usually present.

`probe/empty_window.py --check`, exit **0**. Committed: `out/empty-window.log`,
`out/empty-window.json`.

**1,612 mid-staff bar-head windows, TEN real scanned pages, TWO publishers**
(Brahms 1 / Breitkopf p6, p22, p42-45; Beethoven 5 / Litolff p56, p57, p63,
p86). Every one is a continuation page of a movement already under way, so
**every answer is a false positive and no answer is a miss** — a deliberately
one-sided measurement.

The crops are not a simulation of the input: the probe runs the pipeline's own
`detect_staves -> detect_barlines -> extract_measures -> remove_staff_lines`,
none of which needs weights, so these ARE the cells a real run would hand the
reader.

At the reader's own shipped floor (`min_score = 0.50`):

| window width | windows | answered | rate | columns with **2** staves agreeing | columns with **3** |
|---|--:|--:|--:|--:|--:|
| **4.0 staff spaces (shipped)** | 1612 | 16 | 0.99% | **2** | **0** |
| 6.0 | 1612 | 25 | 1.55% | 4 | **0** |
| 8.0 | 1612 | 40 | 2.48% | 5 | **1** |

⚠️⚠️ **THE 8-SPACE ROW IS THE FINDING, NOT A FOOTNOTE: the three-staff quorum
is NOT unconditionally safe — it is safe AT THIS WINDOW WIDTH.** Widen the
window and a false consensus appears. The two constants are not independent
safeguards; they are one safeguard measured at one operating point, and the
shipped pair (4 spaces, 3 staves) is the only combination measured at zero.

**POSITIVE CONTROL** — without it a zero from a dead reader is
indistinguishable from a zero from a careful one. A real Bravura `3/4` stamped
into 225 of those same windows at the staff's own scale: **225 tried, 225
answered, 225 with the right `raw`**, scores 0.542-0.993. ⚠️ It is deliberately
OPTIMISTIC (clean template ink on a real scanned surround), so those scores are
an UPPER bound on what a true reading looks like and must never be quoted as a
true-positive distribution.

### `min_score` was NOT moved, and that is a decision

The false answers thin out between 0.50 and 0.55 (16 / 7 / 2 / 1 at
0.50 / 0.52 / 0.54 / 0.55) and it is tempting. **Refused, for two reasons.**
They thin out **SMOOTHLY, with no gap anywhere** — a constant read off a smooth
slope is fitted to a wish, which is the `_SLUR_ARC_PAD_NOTEHEADS` refusal one
family over. And the positive control's own minimum is **0.542**, so a floor at
0.55 already refuses the weakest clean reading; a real printed-and-scanned
meter would score lower still. CLAUDE.md also records `min_score` as shared
with the legacy path and set on an 11-source corpus, and refuses moving it on
less.

⚠️ **The false population is dominated by `C`** — 13 of the top 16 answers at 4
spaces. A common-time glyph is a small rounded blob two spaces tall, the
cheapest shape on a music page to fake, and CLAUDE.md already records the
letter path producing a false positive from one 0.377-confidence
`timeSigCommon`. It is recorded and **not gated on**: four rows is not a
threshold.

---

## 3. WHAT SHIPPED

**GATHER** (`tools/omr/staged/gather.py`):

* `frame_bar_head(i)` — a new FRAME. A reading over four staff spaces of a bar
  head and one over the whole bar are not the same observation; this module's
  own header says two readers of one quantity on different crops are two
  signals, on the same crop one.
* `_bar_head_window(cell, spaces)` — slices the measure cell the pipeline has
  already cut, to its first `METER_TEMPLATE_AT_BAR_WINDOW_SPACES = 4.0` staff
  spaces. A slice, not a fresh extraction: building a new crop would put this
  pass on a second, unpriced cutting path with its own padding and canonical
  scale. Abstains where there is no five-line geometry.
* `_meter_candidate_columns(...)` — `{system: {cell: n_staves_that_saw_ink}}`,
  cell 0 excluded exactly as `_meter_changes` excludes it.
* `gather_meter_at_bars(...)` — for each candidate column, ask **every staff of
  that system**, including the ones that detected nothing. Files
  `Q.METER_TEMPLATE_AT_BAR` on the **STAFF** subject with the bar in
  `detail["cell"]`, which is how `Q.METER_GLYPH` already carries it.

**RECORD** — `Q.METER_TEMPLATE_AT_BAR`, a **separate quantity**.
⚠️ `adjudicate_meter` takes every `Q.METER_TEMPLATE` row as a vote on the
system's OPENING, so filing a mid-staff reading there would make a change at
bar 9 argue about what bar 1 prints. The precedent is exact:
`Q.KEYSIG_TEMPLATE_FIT` is separate from `Q.KEYSIG_CLEF_FIT` because pooling
them would have moved the CLEF decision. Pinned by a test.

**ADJUDICATE** (`tools/omr/staged/adjudicators/rhythm.py`) — one contiguous
block between `BEGIN/END template-at-bar consumer` markers, plus three marked
one-to-four-line call sites, so a rebase onto the parallel weighing work is
mechanical. **It touches no weighing constant and no existing flag.**

* `METER_TEMPLATE_AT_BAR_MIN_STAVES = 3` — the consensus, and the only new
  number. Justified by section 2's table and by the convention: a meter change
  is printed on EVERY staff of a system at one bar, so agreement across staves
  is the shape the real thing has. This project has made that argument twice
  before (`vote_system_time_signature.min_staff_fraction`,
  `OMR_KEYSIG_CORROBORATION`).
* `_template_readings_at_bars(ev)` -> `{cell: {(num, den, raw): {staves}}}`.
  The key carries the printed FORM, for the reason `_meter_changes` already
  keys on it: `C` and `4/4` are one length and two engravings.
* `_admit_template_consensus(...)` — folds an agreeing set into `readings`,
  **GAPS ONLY**: a staff that read its own digits keeps that reading. Inherited
  from `adjudicate_key_signature` rather than re-decided, and for the same
  reason — the second reader is the one that can OVER-produce.
* `staves_from_bar_head_template` is written onto the segment, **absent rather
  than zero** when nothing was admitted.

⚠️ **THE STRUCTURAL BOUND, asserted rather than assumed: this pass can add
STAVES to a bar and never a bar to the page.** The gatherer only looks where
some staff already saw meter-shaped ink, so every candidate column already has
a `Q.METER_GLYPH` row and `_meter_changes` already visits it.

---

## 4. FLAG-OFF BYTE-IDENTITY, and how the control could have failed

**With the flag off, `gather_meter_at_bars` returns having written nothing at
all** — not an abstention per staff per column. That is the strongest available
form: the record is byte-identical, not merely equivalent. The trade is stated
rather than hidden: a flag-off record cannot distinguish this pass from one
that ran and found nothing. For an unpriced default-OFF mechanism that is the
right side to err on, and `direction`'s `OUT_OF_SCOPE` convention was
considered and declined because it would cost a few hundred rows a page to say
*"a flag is off"*.

⚠️⚠️ **THE CONTROL COULD HAVE PASSED VACUOUSLY AND THIS IS EXACTLY WHERE.**
CLAUDE.md records the wedge work's byte-identity control passing because the
function under test *was never called on any fixture* — every file had
`grep -c '<wedge' == 0`. The identical trap is live here: a fixture of blank
cells produces zero rows with the flag ON **and** OFF, because
`locate_time_signature` is an NCC against Bravura templates and blank paper (or
a hand-drawn rectangle) scores nothing.

So `test_FLAG_ON_WRITES_ROWS` stamps a **real Bravura meter** into the fixture
and asserts rows appear, and `test_the_reader_ANSWERS_on_a_stamped_bar_head`
asserts the value is `(3, 4)`. The OFF zero means something only because the ON
arm is non-zero on the same fixture. A third test
(`test_a_blank_bar_head_is_refused_and_a_stamped_one_is_not`) carries its own
positive control inside one test body, for the same reason.

---

## 5. THE EXACT COMMAND SEAN RUNS TO PRICE IT

⚠️ **This is a GATHER change and CANNOT be priced here.** `readjudicate.py`
rebuilds ADJUDICATE from a SAVED record, so a quantity the gather did not write
can never enter it — it would report `0 moved` and pass its own control at
100%, the *"control that was never testing what its name says"* family.
`reexport_arm.py` has the mirror blind spot. **Only two full re-gathers answer
it**, and this container has no `omr-weights/` and no `library/`.

```bash
python3 benchmarks/omr-meter-template-changes-2026-09/local_arm.py \
    --pdf "$HOME/Desktop/ReEngrave/library/editions/brahms/symphony-1/<the Breitkopf PDF>.pdf" \
    --weights "$HOME/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt" \
    --pages 0-3 --out-dir /tmp/meter-at-bar
```

(The arm takes any PDF and any weights file; substitute the real Brahms 1 /
Breitkopf path from the score library.)

It gathers TWICE, flag off then on, and prints REACH before anything else,
exiting non-zero and declaring itself **DEAD** if the ON arm asked nothing.
**Breitkopf Brahms 1 p0-3 is the fixture** precisely because CLAUDE.md records
its meter reading as known-bad: `9/8` voted `9/4`, the real change at m8
missed, five spurious `4/4`. What to look for, in order:

1. **Reach** — candidate columns, windows asked, windows answered.
2. **The `9/8` at m8** — does a consensus of three or more staves read it at
   the right bar?
3. **The five spurious `4/4`** — do they GAIN template staves, which would make
   the document worse, or does the reader refuse those bars?
4. **Every system's opening** — it must not move. The arm prints
   `systems whose OPENING moved` and flags a non-zero.

⚠️ It runs without `--musicxml` deliberately: CLAUDE.md records that
`staged/__main__.py` imports the exporter AFTER the gather, so an edit during a
long run kills a finished gather.

---

## 6. TESTS, BATTERY, CHECKS

`tools/omr/tests/test_meter_template_at_bar.py` — **33 tests, all green.**

**Mutation battery** (`mutation_battery.py`): **15 arms, 15 red, 0 survivors**,
including `POSITIVE_everything_refuses` in the same class as the refusal arms
(with the quorum set beyond any reachable number the ACCEPT tests go red — if
they had not, every refusal test above them was passing for free).

⚠️ It takes a **byte snapshot and restores from it, then VERIFIES the
restore**, because CLAUDE.md records a battery that `git checkout`ed the files
it mutated when HEAD did not have the new function and destroyed the change it
had just certified. `git status` after the run listed only the intended files.

| check | exit |
|---|---|
| `python3 -m tools.omr.staged.health --check` | **0** |
| `python3 -m tools.omr.staged.inventory --check` | **0** (14 problems, 0 not on `KNOWN_GAPS` — the same 14 as the base branch) |
| `python3 -m tools.omr.staged.gather_coverage` | lists `METER_TEMPLATE_AT_BAR  TEMPLATE  gather_meter_at_bars` |
| `pytest tools/omr/tests/test_flag_default_direction.py` | **3 passed**; 10 default-ON / 11 default-OFF, all consistent, and the new flag is derived as default-OFF |

⚠️ **`inventory --check` caught a real defect before it shipped.** The first cut
fetched the template rows inside `_meter_changes`, which sits one helper too
deep, so `meter` was reported as declaring `meter_template_at_bar` in `wants`
and **never reading it** — the *inert declaration* anti-pattern, bought with a
green line. `last_cell` had been moved for exactly this reason and this follows
it: the rows are now fetched in `_with_segments` and passed in.

⚠️ **A second defect was caught by a test asserting on the SEGMENT rather than
on the candidate.** `staves_from_bar_head_template` was set on the candidate
and `_with_segments`' projection is a WHITELIST, so it was dropped on the way
out — computed and thrown away, in the change whose own purpose is to stop
that.

---

## 7. WHAT IS NOT ESTABLISHED

* ⚠️⚠️ **NOTHING HAS BEEN PRICED.** No page was gathered with the flag on.
  Every figure here is a property of the READER over crops, or of the tree.
  Section 5 is the measurement, and it has not been run.
* ⚠️ **ACCURACY IS UNMEASURED IN ONE DIRECTION.** Every window in section 2 is
  EMPTY, so the false-positive side is measured and the TRUE-positive side is
  not: no page in reach prints a mid-staff meter change, so **it has never been
  shown that this reads a real one**. The positive control shows the reader
  answers on stamped ink, which is a liveness check and not a recall figure.
* ⚠️ **The consensus's COST is unmeasured and one-sided.** A real change on a
  badly-read system where only two staves clear the floor is refused by
  `METER_TEMPLATE_AT_BAR_MIN_STAVES = 3`, and that refusal has never been
  observed, let alone priced.
* ⚠️ **The quorum is safe at 4 spaces and NOT at 8** (section 2). The two
  constants are one safeguard at one operating point.
* n = 10 pages, 2 publishers, all SCANS. The engraved family is untouched by
  construction and was not measured.
* The committed transcriptions section 1 reads were made with past weights on
  past trees; the candidate population under current production weights may
  differ.
* ⚠️ The empty-window pages are **downscaled renders** committed for other
  investigations, not 600-dpi originals. Staff spacing is normalised to the
  canonical cell before the reader sees it, so the reader's operating point is
  right — but the ink it is reading is not the ink a production run reads.
* ⚠️ `A-DUR-5` (unclassified ink as a gathered fact) was confirmed **not built**
  and deliberately not built here.

---

## 8. THE RANKED NEXT WORK

1. **Run section 5.** Until then this is a mechanism with a measured
   false-positive rate and no measured benefit.
2. **If it reads the Brahms `9/8` at m8** — that is the standing blocking
   objection to `OMR_METER_CARRY` and `OMR_METER_FROM_BARS` addressed at its
   root, which CLAUDE.md names as *the lever: the meter GLYPH readers, not the
   weighing and not a placement rule*.
3. **If it does not** — the reach figure says why, and the honest next question
   is whether the window should be anchored on the detection's own x rather
   than on the bar's left edge. That is a different rule and needs its own
   measurement; it is not a tweak to this one.
4. ⚠️ **Do not raise `min_score` for this population without a gap.** Measured
   here: there is not one.

---

## 9. THE MERGE WITH `claude/meter-corroboration` — and one claim above is now stale

2026-09-15, branch `claude/meter-template-merged`, merging integration
`878c0a7c` (which carries A-METER-6 and flips `OMR_METER_CARRY` /
`OMR_METER_FROM_BARS` ON) into `6522d26c`. Two conflicting hunks in
`rhythm.py`, both in the meter change path.

⚠️⚠️ **SECTION 6's SECOND DEFECT NOW DESCRIBES CODE THAT NO LONGER EXISTS.**
It says *"`_with_segments`' projection is a WHITELIST, so it was dropped on the
way out"*. That whitelist was a **hand-written dict literal**, and the merge
DELETED it. Saying so here rather than editing section 6 keeps the history —
the defect was real and the test that caught it still guards the field — but a
reader must not go looking for that literal. It is gone.

**(1) The per-cell `readings` loop — two independent additions, one anchor.**
Theirs adds `staves_with_a_meter.add(staff)` INSIDE the per-staff `else:`;
mine adds `template_admitted = _admit_template_consensus(...)` AFTER the loop.
Git cannot sequence two insertions at one point. Both kept, correctly scoped —
theirs at 16 spaces inside the loop, mine at 8 after it — because later code
both branches agree on reads `staves_with_a_meter` in
`cand["staves_reading_a_meter"]` and `template_admitted` in
`if template_admitted.get((num, den, raw))`.

⚠️ **A SEMANTIC CHOICE WAS TAKEN HERE AND IS DOCUMENTED AT THE SITE: the
template's staves DO NOT feed `staves_with_a_meter`.** That set is A-METER-6's
WEAKER witness, defined over what the DETECTOR's glyphs said, and recorded
precisely so the weaker rule can be priced later **without a re-gather**.
Folding a second reader into it would silently change what such a pricing
measures — two readers pooled into one number defined over one of them. The
template's contribution is reported APART as
`staves_from_bar_head_template`, which is this repository's own convention
(`cv_glyphs` beside `detector_glyphs`; `detector` beside `cv_hairpins`) rather
than a new one.

**(2) `_with_segments` — resolved toward the DERIVED helper, and the literal
deleted.** Theirs calls `_meter_changes` with four positional args and builds
segments through `_segment_from_change` / `_SEGMENT_FIELDS`; mine called it
with five and hand-wrote the segment dict, then patched the field in
afterwards. **The five-arg call is kept and the literal is gone**;
`staves_from_bar_head_template` is now declared in `_SEGMENT_FIELDS` and
reaches the segment through that one projection.

⚠️ **ABSENT-NOT-ZERO IS PRESERVED FOR FREE**: `_segment_from_change` is
`{k: change[k] for k in _SEGMENT_FIELDS if k in change}`, so a change the
template did not contribute to carries no such key at all. No extra guard was
needed and none was added.

⚠️⚠️ **THIS IS STRICTLY BETTER THAN WHAT EITHER SIDE HAD, and it is the same
bug on both sides of the collision.** `_meter_changes` has TWO segment-building
callers — `_with_segments` and `_change_only` — and their branch introduced
`_SEGMENT_FIELDS` *because* A-METER-6's `corroborated` had been added to the
first and not the second, so a `change_only` verdict silently carried no flag
while every unit test stayed green. My literal had the identical shape one
field later: `staves_from_bar_head_template` could never have reached
`_change_only`'s segments. Through the helper it now does.

**⚠️ THE 5-ARG SIGNATURE WAS CHECKED, NOT ASSUMED.** `878c0a7c`'s
`_meter_changes` takes **four** positional parameters — `git show
878c0a7c:tools/omr/staged/adjudicators/rhythm.py` confirms it — so a five-arg
call against their tree alone would be a `TypeError`. It works after the merge
only because git auto-merged my `templates: Optional[dict] = None` parameter
into their function body outside the conflict region. Both call sites were then
read back and both are five-arg.

**⚠️ ONE MUTATION ARM WENT `BAD ANCHOR (occurs 0x)` AND THAT IS THE BATTERY
WORKING.** `the_segment_projection_drops_it` mutated the deleted literal. It
was **re-pointed at `_SEGMENT_FIELDS`** rather than dropped: the hazard did not
go away, it moved into the derived projection — and mutating it there covers
BOTH segment sites where the literal only ever covered one. An arm that can
never go red trains the next reader to ignore the list, which is why a
`BAD ANCHOR` is reported as a problem rather than counted as a pass.

### Results on the MERGED tree

| | |
|---|---|
| `test_meter_template_at_bar.py` | **33 passed** |
| `test_staged_header_rhythm.py` + `test_flag_default_direction.py` | **96 passed**, 7 subtests |
| flag directions | **12 default-ON / 11 default-OFF**, all consistent; `OMR_METER_TEMPLATE_AT_BAR` still derived default-OFF; `OMR_METER_CARRY`, `OMR_METER_FROM_BARS`, `OMR_METER_SEGMENTS` now ON |
| `health --check` | **0** |
| `inventory --check` | **0** — 14 problems, **0 not on `KNOWN_GAPS`**, and `meter_template_at_bar` is NOT reported inert |
| `gather_coverage` | **0** |
| mutation battery | **15 arms, 15 red, 0 survivors**, restore VERIFIED |

⚠️ `inventory --check` was re-run on the MERGED tree specifically, because the
merge changes what reads what and that check is what caught this branch's inert
declaration the first time.

⚠️ **Nothing in sections 1-8 is re-measured by this merge.** The reach and
empty-window figures are properties of the READER over crops and the merge does
not touch it. **Nothing is priced, still** — `local_arm.py` is unchanged and its
two full re-gathers remain the only thing that can price it. ⚠️ With both meter
flags now ON by default, that arm's output will differ from what sections 1-8
would predict: the OFF arm is no longer a plain reader baseline but a
carry-and-bars baseline, and the comparison is still valid because both arms
inherit those defaults equally.
