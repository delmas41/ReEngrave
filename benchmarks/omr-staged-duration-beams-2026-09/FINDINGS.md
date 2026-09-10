# The duration reader — a MARK must be attached to its notehead

⚠️ **No benchmark was run and nothing here is a score.** Every number is a
control or a diagnosis. The change is **staged-pipeline only** — the legacy
`tools/omr/rhythm.py` is untouched, so no engraved or scan figure anywhere
moves.

Acts on
[`benchmarks/omr-staged-meter-engraved-2026-09/FINDINGS.md`](../omr-staged-meter-engraved-2026-09/FINDINGS.md)
§6, which separated **two independent faults** in the bar sums and asked for
them to be worked apart. **Both are fixed**, in that order and in two commits,
and they turned out to be **one family**: a mark the page prints is gathered,
and the decision that needs it looks in the wrong place.

⚠️⚠️ **THE FIXTURE NOW READS EVERY BAR CORRECTLY — 16 assessable, 16 right,
from 12 assessable and 7 right.** `A-DUR-8` is closed on this document. It is
ONE document; see §7.

**The fixture.** `beethoven-sym5-mvt4` bars 203-218, rendered through LilyPond
at 23 parts with every part playing every bar (`render_meter_change.py`), so
the ink is perfect by construction and a bar that fails to sum is the reader's
fault. Truth `{203: 3/4, 209: 4/4}`. Engraved weights
(`imgsz2048-ft-30ep`), as `run_arms.py` records for this family of fixtures.

```bash
python3 benchmarks/omr-staged-meter-engraved-2026-09/render_meter_change.py \
    --work beethoven-sym5-mvt4 --first 203 --last 218 --out-dir out/
OMR_SURYA_KEEP_ALIVE=0 python3 -m tools.omr.staged out/<pdf> --pages 0-2 \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    --out staged.json
python3 benchmarks/omr-staged-duration-beams-2026-09/barsum.py staged.json \
    "0:0-8=3.0,1:0-2=3.0,1:3-8=4.0,2:0-8=4.0"
```

---

## 1. THE RESULT — 12 assessable / 7 right → 14/10 → **16/16**

Off each record's **own** duration verdicts, under the **shipping** candidate
policy, every page of the fixture. A `*` marks a bar read wrong.
`out/barsums.txt` carries the three arms in full.

| | assessable | correct | narrowed verdicts |
|---|--:|--:|--:|
| before | 12 | 7 | 147 |
| the stem tier alone (Fault 1) | 14 | 10 | 29 |
| the marks alone (Fault 2) | 13 | 11 | 147 |
| **both** | **16** | **16** | 29 |

⚠️ **The four arms are ONE gather adjudicated four times** (`readjudicate.py`,
§6a), so they carry no detector jitter, and the harness reproduces the
pipeline's own record exactly before any arm is read. The two halves COMPOSE:
each alone is worth +3 and +4 correct bars, together +9.

**No bar goes from right to wrong at either step**, and the cross-staff
agreement rises everywhere it was already right: `p0c0` 5 of 8 → **8 of 8**,
`p2c3` 15 of 23 → **22 of 23**.

⚠️ **The four bars Fault 1 could not touch were EXACTLY Fault 2 and did not
move under it** — `p1c1`/`p1c2` at 2.0, `p1c4` at 3.5, `p1c5` at 6.0,
reproducing §6's own counts (17 of 23 and 20 of 23) to the staff. That the two
faults were independent is a measurement, not a claim; and all four are right
once the marks are attached.

## 2. THE MECHANISM — a beam ends at a stem, and a stem is not a centre

A beam stroke runs from the **first stem it joins to the last**, and a stem
stands at the **side** of its notehead. So the outer note of every beamed group
has its centre roughly half a notehead width past the stroke's end, and
`_beam_levels` was testing exactly that centre.

Measured over the fixture's narrowed durations (`probe_stem.py`):

| | count |
|---|--:|
| the head's box overlaps a beam **and** a stem of that head meets it | **114** |
| no box overlap — genuinely not under a beam | 104 |
| no CV beam in the cell at all | 55 |
| no box overlap and no stem read | 8 |
| box overlap but no stem read | 4 |

and the overshoot of the centre past the stroke's end clusters at **0.35-0.47
notehead widths** — the stem offset and nothing else.

`BEAM_EDGE_TOLERANCE_WIDTHS` (1.0) then caught those 114 as **POSSIBLE**, so
the duration came out as a RANGE. `_bar_lengths_for` collapses a range to
`candidates[0]`, and `Ruling.narrow` orders by support, so the collapse always
took the **longer** note. ⚠️ **A verdict that says "it is one of these" was
consumed as if it had decided**, in the one direction that inflates a bar —
this project's own named anti-pattern, against `Evidence.admitted`'s explicit
*"THE POINT IS THAT A CONSUMER NEED NOT COLLAPSE THE SET EARLY"*.

⚠️⚠️ **`Q.STEM` WAS DECLARED IN `wants` AND `composed_from` AND READ BY
NOTHING**, with a `KNOWN_GAPS` entry saying so, inside the decision whose own
docstring calls the beam level its fragile input. 916 stem rows on this
three-page record. *The value existed and nothing read it*, again — and this
time it was not harmless.

## 3. WHY THIS AND NOT A CANDIDATE POLICY — the policy question DISSOLVES

§6 measured that "take the lowest candidate" fixes the dense page and breaks
the mixed one, and refused it as *a fudge that fits*. Simulated offline on ONE
saved record (`sim_beam_association.py`, no re-transcription, so no detector
jitter), rule A is the shipping centre test and rule B adds the stem tier:

| | assessable | correct | narrowed |
|---|--:|--:|--:|
| A, top candidate — **what shipped** | 10 | 7 | 149 |
| A, lowest candidate | 13 | 10 | 149 |
| **B, top candidate** | **13** | **10** | **16** |
| B, lowest candidate | 13 | 10 | 16 |

⚠️ **RULE B IS INSENSITIVE TO THE POLICY, AND THAT IS THE CLAIM.** Under it the
two policies give the same answer on every bar of all three pages, because the
ambiguity was an artefact of the association rather than a reading. Fixing the
association upstream is what §6 asked for, and it reaches rule A's *best* arm
without choosing a candidate at all.

⚠️ **The pipeline was then checked against the probe and the probe against the
pipeline.** A live `--pages 0-2` run reproduces the simulation in both
directions (narrowed 147 → 29 against a predicted 149 → 16; the residue is
`reconcile_duration`, which the offline simulation does not run).

⚠️ **AND IT WAS RE-MEASURED ON THE MERGED TREE.** `origin/main` moved under
this branch with the CAUTIONARY rule and the scan-side meter bookkeeping fix
(`_meter_changes`, `_last_cell_per_staff`), which the merge folded into the
same file. A live run after the merge is **identical bar for bar and count for
count** — 14 assessable, 10 correct, the same staff tallies. `out/barsums.txt`
carries all three arms.

## 4. THE RULE — box overlap, and NO CONSTANT

A stem is attached to a notehead, and joined to a beam, when their **boxes
overlap**. Both separations were measured before the rule was written, and
neither needs a tolerance:

* **stem ↔ beam**: of 707 pairs overlapping in x, **685 also overlap in y**;
  the 22 that do not are separated by **35 px or more**, with nothing in 1-34.
* **notehead ↔ stem**: 819 heads take **exactly one** stem; where none
  overlaps the nearest is **94 px** away but for three pairs at 1-2 px.

⚠️ **ADDITIVE, NEVER SUBTRACTIVE.** `_stem_joined` is a second tier beside the
centre test — the shape `_dedupe_cross_staff_detections`'s ledger ladder
already has. It can only turn a POSSIBLE into a CERTAIN, so a page whose stems
are not read behaves exactly as before, and stem-ONLY (dropping the centre
test) was measured and refused: same bars, but 60 narrowed against 16, because
a head whose stem the CV missed loses its beam entirely.

⚠️ **THE Y GUARD IS UNEXERCISED BY THIS FIXTURE AND IS TESTED DIRECTLY
INSTEAD.** Sweeping a y tolerance from 0 to 64 px changes no bar and moves
`narrowed` by one, because on a clean engraving every beam sits at its stems'
ends. It is kept because a stem in another octave crossing a beam's column is a
real case and the x test alone would join them —
`test_a_stem_that_misses_the_beam_in_Y_does_NOT_join` exercises it on
synthetic ink, **carrying its positive control inside the test**, and the
mutation arm that removes the y half of the overlap turns it red.

**Mutation arms, all red on the intended test** (`M1` x-only overlap, `M2`
every stem in the cell counts as attached, `M3` stem tier disabled, `M4`
joined ids ignored in `_beam_levels`): 1, 1, 4 and 4 failures of 7. The two
tests that survive M3/M4 are the two CONTROLS, which must pass on both trees.

## 5. ⚠️⚠️ FAULT 2 — THE SAME FAMILY: A MARK MUST BE ATTACHED TO ITS NOTEHEAD

§6 said this one *"most needs a crop in front of a human"*. It did not need
one: the record answered it, and the encoding the page was **rendered from**
then confirmed it, which is stronger evidence than a crop.

**`Q.FLAG` and `Q.AUG_DOT` are gathered on the MARK's own glyph subject and
were read on the NOTEHEAD's, so not one of them ever reached a duration.**
`gather_rhythm_marks` writes them at `R.glyph(..., gi)` — the flag's or the
dot's own detection index — while `adjudicate_duration` did `ev.rows(Q.FLAG)`
and `ev.rows(Q.AUG_DOT)` on the notehead's subject:

```
                     before                 after
flag    (glyph-scoped)   134 rows, 0 read     112 attached, 109 deciding
aug_dot (glyph-scoped)   157 rows, 0 read     157 attached
durations carrying a dot          0                        156
beam_evidence == "flag"           0                        109
```

⚠️ It accounted for **both directions** of the residual, checked against the
truth encoding measure by measure:

| bar | we read | truth says |
|---|---|---|
| **m211** (4/4) | `quarter + 8th-rest` × 4 = **6.0** on 20 of 23 staves | **100 eighths** and 80 eighth rests — the missing FLAG |
| **m207/m208** (3/4) | a plain **half**, 2.0, on 7 of 13 | 8 parts play a **dotted half** — the missing DOT |

⚠️ And the two constants the adjudicator carries for exactly this —
`DOT_ABOVE_NOTE_MAX_SPACES` / `DOT_BELOW_NOTE_MAX_SPACES`, with a paragraph of
measured justification about Brahms's double stops — **were declared in the
staged module and used by nothing in it**. The attachment that comment
describes was never performed.

### 5a. A FLAG HANGS ON A STEM, and here that beats the legacy rule

`rhythm._flag_for_notehead` matches a flag to a notehead on **x-centre
proximity**, and says in its own docstring why: it cannot enforce stem
direction because *"the notehead's stem direction isn't reliably available from
a 0-stem detector"*. ⚠️ **On this path it is** — `gather_cv_lines` reads the
stems, 916 rows on this record — so that limitation is stale here. A flag is
drawn FROM the stem's far end, so a flag is claimed only where its box meets a
stem whose box meets this head: the same `_boxes_overlap` primitive Fault 1
introduced, reused rather than restated.

⚠️⚠️ **AND A SECOND BUG WAS IN THE SAME TWO LINES: `levels = len(flags)`.** A
flag class NAMES A VALUE — a single `flag16thUp` is one glyph and TWO levels —
so counting glyphs would have read every sixteenth as an eighth. Counting is
right for beam strokes, which are drawn one per level, and wrong for flags.
`_FLAG_LEVELS` is derived from `rhythm._FLAG_DURATIONS` rather than restated.

### 5b. A DOT NEEDS A UNIT, AND THE UNIT IS NOT A CONSTANT

The dot window is expressed in staff spaces, and there was **no staff-space
unit on the record in the cell's own frame**. `Q.STAFF_SPACING` exists and is
the PAGE's (41.25 px here) while every glyph box in a cell is canonical
(a notehead is ~128 px wide) — two frames, and comparing them is the substrate
error this project keeps paying for.

⚠️⚠️ **THE NOMINAL WOULD HAVE BEEN WRONG ON HALF THE CELLS.**
`CANONICAL_STAFF_SPAN_PX / 4 = 100` is what a cell gets *if* it is scaled by
height, but `_upscale_to_canonical` scales a too-wide cell by **width**
instead. Measured over this fixture's 368 cells:

```
px per staff SPACE:  100 x184   56 x59   46 x56   38 x15   99 x14
                      47 x13    55 x10   98 x9    39 x8
min 38.5   max 100.0
```

**Exactly half the cells are under 60 px.** A hardcoded 100 would have made
the dot window two to three times too generous on them.

So `Q.CELL_STAFF_SPACE` is gathered where `_cell_grid` already computes it —
whose own docstring records that this arithmetic *"was computed inline and
thrown away"* once before, and was then kept only INSIDE a notehead's
position. It is the same finding one layer on. A one-line percussion cell has
no gaps to derive it from and gets the unit `measure_extractor` already writes
for exactly that case; where neither exists the decision **declines the dot**
rather than measuring against a number written for another frame.

### 5c. THE CLAIM IS RECIPROCAL

The legacy rule assigns each dot to its own nearest target, globally. A staged
decision sees ONE notehead, so it asks the same question from the other end: a
dot is claimed only where **this** head is the best target the dot has in the
cell. Two heads can never both take one dot — which is the double-stop case
the asymmetric window exists for.

### 5d. THE ARMS

Seven mutation arms, all red on the intended tests: flags read on the
notehead's own subject (4 failures), flag levels counted as glyphs (1), dots
read on the notehead's own subject (6), the dot window made symmetric (1), the
reciprocal check dropped (1), a flag not required to touch a stem (2), a
missing unit defaulting to 100 (1).

⚠️⚠️ **AN EIGHTH ARM SURVIVED AND THE RULE WAS DELETED, NOT THE TEST.**
`_attached_flags` opened with `if not attached_stems: return [], 0`. It could
not be broken, because `any()` over an empty list is already False — a second
spelling of a rule that lives one line below. A rule a mutation cannot break is
a protection that is not there.

⚠️ **AND AN EXISTING TEST WAS PASSING FOR FREE.**
`test_a_dot_adds_half_of_what_stands` asserted the right arithmetic on a
fixture that wrote `Q.AUG_DOT` onto the NOTEHEAD's subject — a subject shape
`gather` never produces. It went green for as long as the bug lived. The
helper now emits a dot as what it is: its own detection, with its own glyph
index and its own box.

## 6. ⚠️⚠️ THE SCAN ARM — the stem tier survives, the marks do not REACH, and it is NOT free

Run because §6 of the predecessor named exactly two unknowns and neither could
be answered on a LilyPond render: **how much survives on a scan**, and
**whether a wrong stem can hand a note a flag it has not got**. Litolff
Beethoven 5 mvt1, **pdf pages 1-4** (12 / 22 / 19 / 22 staves), whose windows
are hand-verified in `benchmarks/omr-scan-e2e-2026-09/works.json` and whose
movement is **2/4 throughout** — so every bar's truth is 2.0 quarters and no
per-cell truth table is needed. `out/scan-arm.txt`.

### 6a. ONE GATHER, FOUR ADJUDICATIONS — and the harness proves itself first

⚠️ **Running the staged CLI twice compares two DETECTOR runs as much as two
rules**, which is how the first engraved before/after disagreed with an offline
simulation by two bars. `readjudicate.py` rebuilds a `Log` from ONE saved
record's observations and abstentions and re-runs ADJUDICATE over it, so the
arms differ only in the rule.

⚠️ **`--control` re-adjudicates with nothing disabled and diffs against the
record the pipeline wrote**: **2993 of 2993** duration verdicts reproduced
exactly on the scan, **1356 of 1356** on the engraving, 0 differ, 0 extra. A
rebuild that does not reproduce the record is not a control, and a silent
mismatch would make every number below a measurement of the harness.

⚠️ **AND THE CONTROL WAS RE-RUN AFTER `Q.METER`'s SEGMENTS LANDED.** PR #29
made a meter change reach a file, and `evaluate`'s `size_measure_rest` and
`reconcile_duration` both consume the meter — so a duration could have moved
underneath these figures without anyone touching the duration code. It did not:
on the merged tree the control still reports **2993 of 2993 reproduced exactly,
0 differ, 0 extra**, so every scan figure below stands unchanged.

⚠️ **AND THE ARMS WERE RE-RUN ON THE FINAL TREE.** `_cell_boxes` was extracted
from the two helpers *while the first pass of arms was in flight* — which
breaks this repo's own rule about editing a source file mid-run, and the honest
repair is a control rather than an argument. All three arms were re-run after
the tree settled and are **byte-identical, md5 for md5**, with `rhythm.py`'s own
md5 unchanged across them. (An apparent 2549-vs-2449 discrepancy that prompted
the re-run was a misreading of the harness: `mark_census` counts verdict ROWS,
including ones `evaluate` later supersedes, and `--control` counts unique
SUBJECTS.)

### 6b. THE RESULT — and the two halves come apart completely

| | assessable bars | correct | per-staff readings right |
|---|--:|--:|--:|
| off (both) | 71 | 67 | 401 of 733 |
| **the STEM tier alone** | — | — | **430** |
| **the MARKS alone** | — | — | **401 — unchanged** |
| on (both) | **78** | **74** | 429 |

⚠️⚠️ **THE BAR FIGURES WERE WRONG WHEN FIRST PUBLISHED AND THE CORRECTION IS
WORTH MORE THAN THE NUMBERS.** They read 44/43 → 49/48, because the probes
keyed a bar on `(page, cell)` — and **a cell index RESTARTS at 0 on each system
of a page** (measured: Litolff p.2 runs 0-15, then 0-14), so system 0's third
bar and system 1's third bar were being merged into one pseudo-bar and then
scored. It survived four pages unnoticed because this document's truth is
UNIFORM, so merging changed which pseudo-bars cleared the quorum and nothing
else; it was caught by the FIRST fixture whose truth is not uniform. The key is
now `(page, system, cell)`. ⚠️ Per-staff readings were keyed on the full event
subject all along and are **unaffected** — which is why the headline result did
not move.

**On a scan the stem tier is the entire gain and the marks half does nothing.**
Not because the rule fails: because the detector finds almost no marks to
attach. Over four dense scan pages carrying 2347 noteheads it fires **49 flag
boxes and 35 augmentation dots**; over three engraved pages carrying 1118 it
fires **134 and 157**. That is a DETECTION limit, and it is the same shape this
project already records for hairpins — perfect on engravings, ~1% on scans.

### 6c. ⚠️⚠️ IT IS NOT FREE, AND ONLY THE PER-STAFF VIEW SHOWS IT

At bar level the picture is clean — **0 bars right → wrong**, 11 becoming
assessable and all 11 right. ⚠️ **That cleanliness is the cross-staff quorum
doing its job, not the rule being harmless.** Four bars stop clearing the
quorum, which is an honest abstention replacing a marginal majority — and the
merged-key version of this table reported only ONE of those four, so the
merging was hiding real losses as well as inflating nothing.

Underneath, per (page, cell, staff) reading:

```
      54  ( 7.4%)  wrong -> RIGHT
      26  ( 3.5%)  ⚠️ RIGHT -> wrong
```

**A 2:1 trade, not a free win** — and on the engraving every move was one way,
so this is precisely what the engraved fixture could not price. Split: the stem
tier is 49 up / 20 down, the marks 2 up / 2 down. Adding the marks to the stem
tier costs **one net reading** (430 → 429), well inside the noise of a
20-reading swing.

### 6d. THE FALSE-ATTACHMENT PROBE — a rate, from the page alone

⚠️ **A note under a beam carries no flag.** An engraver draws one or the other,
so a notehead with a beam level READ over it AND a flag attached to its stem is
a contradiction — one of the two readings is wrong. It needs no truth file, and
it does not say WHICH, so it is a rate to compare between printings and never a
count of errors.

| | flagged notes | contradictions | rate |
|---|--:|--:|--:|
| engraved | 112 | 3 | **2.7%** |
| **scan** | 37 | 7 | **18.9%** |

**Seven times the rate, on a seventh of the population.** So the worry behind
this arm is REAL and it is BOUNDED: a scan's stems are worse and the flag half
does pick up noise from them — and there is so little of it that the bar-level
answer never moves. **No gate is added.** A rule that switched the flag half
off by print quality would be fitted to one scan of one publisher, and the
measured cost of leaving it on here is one reading in 733.

## 6e. ⚠️ AN INDEPENDENT SESSION CORROBORATED IT FROM THE OTHER END

Worth recording because it was not asked for and did not come from this
measurement. The sibling meter session re-ran its own boundary arms on top of
this duration work and reports the carry's discrimination on the engraved
`beethoven-sym5-mvt4` widening from **+6.0 / −8.0 to +8.0 / −8.0** — a swing of
14.0 → **16.0**, with the true meter's bars going 7-fit/2-not to 8-fit/1-not —
attributing it to *"a sibling's DURATION work [making] the bars read better,
which is the dependency the design predicts"*.

⚠️ **It is corroboration of the bar-sum repair, not of the meter mechanism**,
and it is one page of one document either way. What makes it worth a line is
that the two sessions measured different quantities on different fixtures and
the direction agrees.

## 7. WHAT THIS DOES NOT ESTABLISH

* ⚠️⚠️ **n = 1 DOCUMENT, 1 FIXTURE, 3 PAGES, ENGRAVED.** "Every bar right" is a
  statement about sixteen bars of one LilyPond render, not about the reader.
  The fixture was chosen because its ink is perfect by construction, which is
  what makes a failure the rule's fault — and equally what stops a success
  from generalising on its own.
* ✅ **THE SCAN CASE IS MEASURED — see §6**, on ONE scan of ONE publisher,
  four pages. The stem tier carries it (+29 net readings); the marks half does
  not reach (49 flags and 35 dots over 2347 noteheads) and costs one net
  reading. ⚠️ It is a **2:1 trade at reading level, not a free win**, and the
  contradiction rate is **18.9% against 2.7% engraved**.
* ⚠️ **A SECOND PUBLISHER'S SCAN IS STILL UNMEASURED**, and the whole meter
  thread already has a case where a result held on a second document and broke
  on a second publisher's scan. Brahms 1 / Breitkopf is in the gate with a
  hand-verified window and is the obvious next arm.
* **No OMR-NED figure was taken on either family**, and none applies: the
  legacy exporter does not use this code path.
* ⚠️ **`A-DUR-8` IS CLOSED ON ONE ENGRAVED DOCUMENT AND THE SCAN IS BETTER,
  NOT RIGHT.** 48 of 49 assessable bars, against 43 of 44 — the bar sums on a
  scan were already nearly right where they were assessable at all, and what
  moved is how MANY bars can speak (44 → 49) rather than whether they are
  believed. Re-pricing `METER_CARRY_FLOOR` or `METER_FROM_BARS_FLOOR` still
  needs a second publisher first.
* **The four residual bars are gone, so nothing is left to attribute.** If a
  bar sum is wrong on the next fixture, it is a NEW finding, not this one.
