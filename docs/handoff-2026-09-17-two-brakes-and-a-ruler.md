# Handoff: two brakes released, and a convention that turned out to be a RULER

**START HERE.** Nothing is merged. Two PRs are open and **stacked**:

| PR | branch | base | what |
|---|---|---|---|
| **#53** | `claude/brakes-unnamed-staves-486cfd` | `main` | the unnamed block — **the one with payoff** |
| **#54** | `claude/stem-direction-sideways` | **#53's branch** | the stem direction — low payoff, one real finding |

⚠️ **#54 is stacked on #53 and does not depend on it.** They touch different
files (`adjudicators/identity.py` vs `adjudicators/rhythm.py`); #54 was
branched off #53 only to reuse a benchmark harness. Rebase it onto main if #53
is not wanted.

**Suite: 4,455 passed / 11 skipped / 0 failed** on the #54 tip, run in two
halves whose selected/deselected counts **partition the 4,466 collected tests
exactly** (1846 + 2620 = 4466) — checked, because two green halves are only a
green suite if every test is in exactly one of them. All seven staged derived
checks exit 0.

---

## 1. ⚠️⚠️ SEAN CORRECTED ME TWICE AND BOTH CORRECTIONS CHANGED THE OUTCOME

**This is the most important thing in this document.** Both times I had a
plausible measurement and a wrong conclusion, and both times the correction
was cheap for him and would not have come from more computing.

**(a) "The convention is strong. The failure is elsewhere."** I had measured
his stem convention at 0.787 and concluded it does not hold on this plate. It
does. See §3 — the number was real and the inference was wrong, because the
arbiter I used was **correlated with one of the two parties**.

**(b) "not all notes have stems… whole notes and half notes"** — he corrected
himself before I answered (half notes do have stems), but the question behind
it was the one that mattered and **I had not asked it**: *are we failing to
see the ink, mislabelling it, or disregarding it?* The answer turned out to be
measurable in twenty minutes and it reframed the whole population (§4).

⚠️ **The generalisable bit: a domain expert's one-line objection outranked
four probes.** When he pushed back, the right move was not to defend the
number — it was to ask what else the number could be measuring.

---

## 2. PR #53 — the unnamed block. The one worth reading first.

Sean's own rule, measured on 2026-09-17 and left unshipped, now shipped and
**split at the line where the page stops forcing the answer**:

* **FORCED** — a bottom-contiguous unnamed block that exactly fills the
  reference's trailing same-family run has ONE order-preserving map onto it.
  DECIDED in ADJUDICATE, `family_block`. Reach **5**.
* **BEST** — a block one slot short sits on that run five ways. NARROWED, and
  an **INFER rule** applies the convention that a short string section is
  short at its FOOT (the condensed `Violoncello e Basso`). Reach **15**.
* The condensed member itself is **left narrowed** — abstained on, not picked.

**Measured**, Litolff Beethoven 5 pp.1-4, control **75 of 75** committed slot
verdicts reproduced with the branch disabled: **25 of 25 placements correct
against the hand-read print, ZERO grafts.**

**In the file, one drop bucket moves and nothing else does:**

| | off | this rule alone |
|---|--:|--:|
| `staff_not_identified` | 783 | **141** |
| `events_written` | 1472 | **2114** |
| pitched `<note>` | 965 | **1527** |
| held-out staves | 25 | 5 |
| parts / measures | 12 / 1332 | **unchanged** |

Every other drop bucket identical **to the unit**, `balanced: True` in every
arm. Per part via music21: Violin I +189, Violin II +176, Viola +74,
Contrabass +27; **Cello +0**, which is the result agreeing with itself.

⚠️ **INFER's third rule and its FIRST NON-DURATION TARGET.**
`staged/brakes.py` measured 1 of 28 decisions able to hand work to the stage.
This is the second.

⚠️ **Second publisher reach is ZERO and it is not a failure**: Breitkopf
labels nearly every staff, so `slot_index` never abstains there and the rule
has nothing to do. **n = 1 document for correctness.**

---

## 3. PR #54 — the stem direction. Low payoff, one real finding.

**Shipped**: a tier that borrows from a head sharing the same BEAM
(`reason="beam_mate"`). Scored LEAVE-ONE-OUT on the 1,443 heads a stem
already decided:

| reading | accuracy | reach |
|---|--:|--:|
| baseline, always the commoner direction | 0.506 | — |
| where the beam SITS relative to the head | 0.829 | 228 |
| the CONVENTION | 0.787 | — |
| beam-mate, majority | 0.938 | 167 |
| **beam-mate, UNANIMOUS** | **0.984** | **152** |

⚠️⚠️ **AND IT IS WORTH ALMOST NOTHING IN THE FILE: `<voice>2</voice>` 24 → 26.
Two tags.** Pitched notes, backups and the voice split are otherwise
unmoved. A record improvement, not a file improvement, and it must not be
quoted as one.

### 3a. ⚠️⚠️ THE CONVENTION IS STRONG AND IT IS MEASURING THE GRID

Accuracy against the projected direction, by distance from the middle line in
staff steps:

| 0-1 | 1-2 | 2-4 | **4-6** | 6+ |
|--:|--:|--:|--:|--:|
| **0.537** | 0.776 | 0.860 | **0.939** | **0.765** |

**It rises steeply and then REVERSES**, and neither end is the convention's
fault. At the boundary, half a step of grid error flips the answer and
two-voice writing lives there. **In ledger country it reverses — and a note
three spaces clear of the middle line is the LEAST ambiguous case the
convention has.** 44% of ledger-country heads are off-grid against 11% inside
the staff, and that is where `omr-phantom-notes-2026-09` already measured
**14 of 25 phantom notes standing outside the staff altogether**. Crossing
with the grid residual does not move it (0.757 vs 0.771).

**So the convention is a RULER for the position, not a reader of stems.** A
confident stem and a confident convention that disagree mean one of
`Q.NOTEHEAD_STAFF_POSITION` and `Q.STEM` is wrong, and this says which zone.

### 3b. ⚠️⚠️ THE ARBITER WAS CORRELATED WITH ONE PARTY

Before Sean's correction I put the projection and the convention to a third
reading — the beam — and found it siding with the projection **79 times in
83**. The probe's docstring claimed the beam *"shares an input with neither"*.
**False**: the projection and the beam are BOTH readings of ink inside the
measure cell, and the convention is the only one of the three that depends on
where the STAFF LINES are. An arbiter correlated with one party sides with its
own family.

*The bars are not an independent umpire over a bad reading* — with the
correlation running through **the FRAME**, a fourth door onto that room after
ink, convention and a shared assumption.

### 3c. ⚠️⚠️ INFER IS THE RIGHT STAGE AND CANNOT SERVE THIS QUANTITY

`Q.STEM_DIRECTION` is ORDER 17; its only consumers, `Q.EVENT` (21) and
`Q.VOICES` (22), read it **inside ADJUDICATE**. A fourth-stage rule would
write the verdict after both readers had already looked. **The 2026-09-17
handoff's "evidence exists sideways and no rule takes it" has a reason: the
stage that may take it runs too late.** Worth carrying to the other 26
decisions in that audit — the handoff numbers them as a population, and at
least one of them is in this shape rather than merely unwired.

---

## 4. ⚠️ THE `no_stem` POPULATION IS INK WE DID NOT READ

Sean's question, measured after he asked it
(`probe_is_the_ink_there.py`). For each of the 793 `no_stem` heads, how far
is the nearest stem row **in the same bar**?

| | heads | |
|---|--:|--:|
| touching | 1 | 0.1% |
| within ¼ staff space | 45 | 5.7% |
| ¼–1 space | 119 | 15.0% |
| 1–3 spaces | 247 | 31.1% |
| more than 3 spaces | 170 | 21.4% |
| **no stem ink ANYWHERE in the bar** | **211** | **26.6%** |

**Median gap 2.01 spaces.** Not mislabelled, not disregarded — **not read**.
At most 6% look like an attachment near-miss, and widening the test past a
quarter space starts claiming the NEIGHBOURING note's stem.

⚠️ From the record rather than from memory: **a whole note has no stem, a half
note does** — half notes get one 309 times against 103 that do not, so those
103 are MISSES. Only the 9 whole notes are correct abstentions, which is what
the shipped rule already excluded. ⚠️ The same table shows the attachment test
has false POSITIVES: **8 whole notes were given a stem.**

### 4b. ⚠️ NO, THE STEMS ARE NOT BEING ERASED — asked and answered

Sean, after the above: *"We decided to do CV with stems so they would end up
being erased similar to the staff lines — correct? Are they missing because we
already got rid of them?"*

**Nothing erases stems.** `staff_line_removal` erases a vertical ink run ONLY
where it is no taller than the line's own printed thickness; anything taller —
notehead, stem, beam, barline — is *"left entirely alone"*. That module exists
because naive row-erasure *"severs noteheads in half and disconnects stems
from their flags"*, which is precisely the worry.

**And on this record the erasure cannot explain the misses, because it is a
CONSTANT:**

| | |
|---|--:|
| bars the CV stem rung saw with `staff_lines_erased: True` | **1183 of 1183** |
| bars returning `no_ink` (the rung ran, found no candidate) | **400** |
| stemless share in the erased condition | 0.355 |

There is no unerased condition to compare against, so a thing that happened
everywhere cannot explain why some heads have stems and others do not.

⚠️ **THAT RULES OUT ONE VERSION OF THE QUESTION AND NOT THE OTHER.** It kills
*"some bars lost their stems"*; it says nothing about *"erasure degrades every
stem a little"*, which is invisible to a test with no control arm. **The arm
that would answer it: run `detect_stems` on `image_no_staff` and on
`cell.image` over the same cells and compare counts.** Not done.

⚠️ **THE CV/YOLO POINT IS REAL, BY A DIFFERENT MECHANISM THAN ERASURE.** YOLO
finds **ZERO** stems even at confidence 0.05 — thin lines are structurally bad
for bounding boxes, which is why Phase 4f moved them to classical CV. The
consequence is the part that matters: **a stem CV misses is missed outright.**
Noteheads have two readers; stems have ONE, with no second opinion.

**So the suspects are CV's own filters, nameable from `detect_stems`:**

* a vertical morphological opening one staff-space tall — **a stem broken by
  faint printing fails it outright**, and this plate is low-res bitonal;
* `min_height_lines = 2.0`, while beamed stems are legitimately short (the
  docstring records a WTC cell holding 15 stems where a 2.8-space floor finds
  5);
* anything within ~0.8 spaces of the cell edge is dropped, to reject barlines;
* ⚠️ **anything appearing as a parallel PAIR is dropped** — `_drop_paired_
  strokes`, which exists to reject sharps and naturals, both of which are two
  parallel verticals. **Two adjacent stems could trip it**, and that is
  testable against the record already committed here: check whether missing
  stems cluster where another vertical sits about half a staff space away.

---

## 5. ⚠️ RANKED NEXT WORK — and it starts with CROPS, not code

**1. The ledger-line positions, against the print.** This is §3a's finding and
it is the biggest lever available, because **position is PITCH**. Everything
in this document is agreement between two of our own readings; **not one note
has been checked against the page.** The step is: take the ledger-country
heads where the convention and the stem disagree, crop them from the PDF, and
look. That turns *"these disagree"* into *"this one is wrong"*, and it needs
no new code — `omr-phantom-notes-2026-09/probe/extract_crops.py` already
recovers print crops.

**2. Do NOT push further on stems.** The ceiling is measured and low: the
quantity only feeds voice separation and chord grouping, and the best rule
available moved two tags. The 632 unbeamed heads have nothing to borrow from
and I have no answer for them.

**3. The attachment near-misses (45 heads, 6%)** are the only cheap stem win
left, and they are worth less than (1). ⚠️ Before touching them, read §4b:
the cheaper stem question is whether `_drop_paired_strokes` is eating adjacent
stems, which needs no new gather and no crops.

**4. `adjudicate_slot_index`'s docstring gap**, still open from the 09-17
handoff: `adjudicate_part_partition` declares `Q.INSTRUMENT` and reads it at a
scope that returns nothing.

---

## 6. WHAT IS NOT ESTABLISHED

* **n = 1 document, 1 publisher, 4 pages of ~16**, the pessimistic low-res
  bitonal Litolff. The second publisher has **no population** for #53's rule
  and was not run for #54's.
* **No note was checked against the print in either PR.** #53's placements are
  scored against a hand-read *lineup*; the notes inside them are not.
* **There is no truth for the stem work at all** — every accuracy is agreement
  with our own `stem_projection`, which is a reading.
* **No OMR-NED figure**, deliberately: the metric is symmetric and would pay
  for holding music OUT.
* `part_partition` is held at the committed value in every arm.
* Both arms are **structurally blind to a GATHER change**.

---

## 7. GOTCHAS PAID FOR TODAY

* ⚠️⚠️ **Three clean, believable ZEROS, all mine, all caught by a POSITIVE
  control that announced itself by printing NOTHING AT ALL**: beam rows keyed
  by STAFF where heads were keyed by CELL; `Q.GLYPH_BOX` read as `[x,y,w,h]`
  when it is `(smufl_name, x, y, w, h)` — from a helper whose docstring says
  it exists *"so a second reader of the same row cannot get it wrong"*; and
  `key.rsplit("/", 1)[0]` on a subject key, which carries its KIND in the
  FIRST segment, so `glyph/1/0/2/4/1` became `glyph/1/0/2/4` and matched
  nothing. **Use `Subject.from_key(k).at(Kind.CELL)`, never string surgery.**
* ⚠️ **An arm scored one publisher's record against another publisher's print
  truth** and reported **21 grafts that were its own** — `printed-lineups.json`
  is keyed on `(page, system)` and so is every record. Scoring is now opt-in
  per record.
* ⚠️ **A confounded A/B**: `infer.run` fires EVERY registered rule, so an
  `off -> infer` delta mixed the rule under test with the two DURATION rules,
  which put 13 events on WIND staves. **The tell was four wind parts gaining
  notes in a change about strings**, not a failing assertion.
* ⚠️ **A tidy-looking hoist moved work onto the population a branch exists to
  exclude**: sharing a cell-wide scan between two tiers made all 793 stemless
  heads pay for a `SELF_AND_DESCENDANTS` walk they had never paid for — 80 s
  to minutes. **Where `ev.rows` is called matters more than how the loop is
  written.**
* ⚠️⚠️ **`ps` LIES ABOUT ELAPSED TIME ON A PYTEST RUN.** torch spawns children
  that inherit the parent's argv, so `pgrep -f pytest | head -1` picks a
  20-second-old child and reads it as a restarted run. It cost several passes.
  **A percentage that stops moving while CPU advances means ONE slow test, not
  a hang** — find it by counting the progress characters and indexing that
  into `--collect-only`'s ordered list. Here it was
  `test_score_language.py::test_the_only_corpus_wide_change_is_the_nine_litolff_trombones`,
  which walks the 1,422-label corpus that CLAUDE.md already prices at
  23-136 ms per string.
* ⚠️ **`pgrep -f <script>` matches the wait-loop's own command line**, so
  `until ! pgrep -f x.py; do sleep; done` can never exit. Poll the OUTPUT FILE.
* ⚠️ macOS has no `timeout`.
