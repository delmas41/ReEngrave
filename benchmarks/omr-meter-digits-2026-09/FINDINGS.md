# A second, independent reader of the printed meter digits

2026-09-29, branch `claude/meter-digits-2.29`, base `origin/main` `8c652d89`.
**Conceptual wiring, proved by MICROSCOPIC RED->GREEN tests -- no gathers, no
base-vs-arm re-adjudications, no crop batches, no whole-work run** (Sean,
2026-09-29 DECISIONS: "our process spends too much time and context on
pricing runs"). Relayed mid-lane, again: "Why tests? I want wiring,
structure" -- tests kept to one RED->GREEN per connection plus one control
each, not a fixture library.

## The problem this wires against

CLAUDE.md / ROADMAP 2.12h/2.12i: on Brahms 1/i Breitkopf `317803`, the
header-template reader (`time_signature_locator`, NCC against a Bravura
raster) reads the opening `9/8` as `9/4` on all ten staves it reads -- the
plate's own "8" is a poor NCC match to the template at this weight, and the
"9" reads correctly, so it is a shape confusion in the DENOMINATOR alone.
ROADMAP 2.12l separately refuses the mid-system change to `6/8` at bar 9
(the detector boxed both digits as noteheads) and files the refusal as a
witness with NO value -- a change is known to be printed there, but nothing
states what it is.

## What was built

**Reader** (`tools/omr/meter_digit_ocr.py`): Tesseract, restricted to
digits, reused verbatim from `bar_number_text`'s own config (`--psm 7`, no
upscale -- that module's own measured choice). `read_meter_digits(image,
split_row=...)` splits the crop at the caller-supplied MIDDLE staff line and
OCRs the numerator/denominator halves SEPARATELY, then applies a
plausibility filter (denominator in {1,2,4,8,16,32}; numerator 1-16; never
reads `C`/cut-C -- those are symbols, not digits, and stay `time_signature_
locator`'s alone). CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT
CONFIRMED, stated in the module docstring: the split point being the
middle staff line would be falsified by a signature engraved off-centre, or
one whose two rows differ enough in height that the middle line misses the
gap between them -- neither checked against a real plate.

**Why this is a SECOND witness, not the same signal twice** (CLAUDE.md 10:
"two witnesses off the same raster fall silent together"): the two readers
disagree about MECHANISM. The template reader slides a fixed Bravura glyph
over the strip and takes the best normalized cross-correlation -- a shape
match. Tesseract reads stroke topology, trained broadly, with no fixed
template. The fault that sinks the template reader on this plate (its own
"8" resembling Bravura's "4") has no reason to also sink stroke-topology
OCR, and the two would need a SEPARATE, measured explanation before being
trusted as agreement -- argued in the module's own docstring, not merely
asserted here.

**Two new quantities** (`tools/omr/staged/record.py`): `Q.METER_OCR`
(opening, filed on the STAFF subject, mirrors `Q.METER_TEMPLATE`) and
`Q.METER_OCR_AT_BAR` (a mid-bar change, filed on the CELL subject, mirrors
`Q.METER_TEMPLATE_AT_BAR` -- kept separate for the same reason that pair is
separate: pooling the opening and a change would make bar 9 argue about
what bar 1 prints).

**GATHER** (`tools/omr/staged/gather.py`):
- `_gather_meter_ocr_header` runs inside `gather_meter`, on the exact same
  header crop `locate_time_signature` already reads. No flag -- Tesseract-
  only, always attempted, abstains cleanly where Tesseract is unavailable,
  the same convention `Q.PRINTED_BAR_NUMBER` (ROADMAP 2.13) ships under.
- `gather_meter_ocr_at_bars` -- its OWN flag, `OMR_METER_OCR_AT_BAR`, default
  OFF (an unpriced GATHER change; `OMR_METER_TEMPLATE_AT_BAR`'s own
  measurement and default from ROADMAP 2.12i are untouched). Tries OCR at a
  mid-staff bar head from EITHER of two starting points: a detector
  `timeSig*` box at that cell (reuses `_bar_head_window`, 2.12i's own
  window), or -- where the detector boxed the change's digits as noteheads
  instead -- this staff's own stacked notehead pair near the barline
  (`_meter_digit_pair_box`). The pair geometry is the SAME thresholds
  `notehead_precision.METER_DIGIT_X_MAX_SPACES` / `_PAIR_X_TOL_SPACES` /
  `_PAIR_Y_GAP_MIN/MAX_SPACES` ROADMAP 2.12l already measured -- imported,
  never restated -- applied LOOSER (no cross-staff quorum) because firing
  here only spends one OCR call, never a verdict; the quorum stays
  `notehead_precision`'s alone.

**ADJUDICATE** (`tools/omr/staged/adjudicators/rhythm.py`,
`adjudicate_meter`):
- Where `Q.METER_TEMPLATE`'s and `Q.METER_OCR`'s own opening readings
  AGREE: DECIDED exactly as before (the template's own share still sets the
  margin), but `used` now names the OCR rows too and
  `detail["ocr_agrees"] = True` -- a second witness, never a second vote.
- Where they DISAGREE: never an argmax on either reader's share (CLAUDE.md
  rule 5/6). This system's own bars are asked which candidate they
  corroborate, through the SAME `_corroborate` function `_carry_meter`
  already uses (`_bar_corroboration_margin`, net `Term.weight`). If the bars
  prefer one: DECIDED on the bars' own say (`detail["settled_by"] =
  "bars"`). If the bars have nothing assessable either (as in this file's
  own tests, and as Brahms's opening system in fact has -- no note/rest
  evidence gathered in the fixture): `Ruling.narrow`, reason
  `template_ocr_disagree`, two `Candidate`s (the template's, the OCR's) --
  "it is one of these," never a silent pick.
- Where the template is SILENT and OCR alone read something: not decided
  from OCR's own say. The reading is folded into `_meter_fallbacks`'s
  existing detail as `ocr_only_candidate` -- a name for the carry ladder (or
  a human) to weigh, never an assertion.
- At a ROADMAP 2.12l digit-witness cell (mid-system, no template reading at
  all): `_ocr_at_bar_candidates` is fetched ONCE, beside
  `_meter_digit_witness_cells`, in `_with_segments` -- the same shape
  `_carry_meter` already uses for `n_cells` (a `Q.` read one call deeper
  inside `_meter_changes` is invisible to `inventory`'s depth-3 helper walk
  and reads as an inert declaration; measured directly -- see below). Filed
  on the `declined_changes` entry as `ocr_candidate`, ABSENT-NOT-ZERO.
  `_carry_meter`'s own `meter_change_digits_misread` abstention now
  surfaces that same candidate in its `detail` -- still an ABSTENTION; the
  value is never asserted by this wiring.

## Tests

`tools/omr/tests/test_staged_meter_ocr.py`, 8 tests, one per connection plus
one control each:

1. Reader: a plausible pair reads; CONTROL, an impossible denominator ("7")
   refuses even though both halves parsed cleanly; a second run of digits in
   one half also refuses (reuses `bar_number_text`'s own parser).
2. GATHER: a plausible reading is filed as `Q.METER_OCR` on the header
   subject; CONTROL, no Tesseract available abstains (`READER_UNAVAILABLE`)
   rather than silently filing nothing.
3. ADJUDICATE: agreement cites the second reader without re-deciding;
   CONTROL, OCR silent leaves the template-only vote byte-identical to
   today's behaviour; disagreement -- the literal Brahms 9/4-vs-9/8 case,
   with no bar evidence to settle it -- NARROWS, never argmaxing either
   reader's share.

**RED verified**: the whole test file, run against `origin/main` `8c652d89`
in a throwaway worktree, fails collection outright --
`ImportError: cannot import name 'meter_digit_ocr' from 'tools.omr'` -- because
none of this module, quantities or wiring exist there. GREEN on this branch,
8/8.

## Gate

`pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider`: **3,881
passed / 3 skipped, 0 failed** (full run on this branch, this file's own 8
tests included). One incidental fix was needed along the way, not on this
item's own logic: the new flag `OMR_METER_OCR_AT_BAR` needed a row in
`docs/flags-2026-09.md` before `test_flag_triage.py`/
`test_flag_docs_match_predicates.py` would pass -- added, `research`/OFF,
alongside `OMR_METER_TEMPLATE_AT_BAR`'s own row.

`python3 -m tools.omr.staged.check`: **TOTAL 245, status=ok** -- measured
directly against `origin/main` `8c652d89` alone in a throwaway worktree
(also 245, status=ok) and against this branch: byte-identical total, this
lane adds ZERO open findings. Two intermediate findings surfaced and were
fixed before landing, not left open (CLAUDE.md rule 7 -- a control that
cannot fail is not a control, and the same discipline applies to a check
that cannot fail): `inventory` first flagged `meter` declaring
`meter_ocr_at_bar` in `wants` and never reading it (the read was one call
too deep -- fixed by fetching `_ocr_at_bar_candidates` in `_with_segments`
and passing it down, the same shape `n_cells` already uses); `capture`
first flagged both new quantities as `UNCLASSIFIED` (observed with no
`score`) -- fixed by filing `score = min(numerator_confidence,
denominator_confidence) / 100.0`, the same convention
`Q.PRINTED_BAR_NUMBER` uses for its own Tesseract confidence.

## Not done, named rather than hidden

- No gather of a real page was run; the OCR reader has never been pointed
  at the actual Brahms plate. Whether it in fact reads `9/8` where the
  template reads `9/4` is UNMEASURED -- this lane wires the CONNECTION, per
  Sean's 2026-09-29 instruction, and a priced gather is the next lane's job.
- `gather_meter_ocr_at_bars` is default OFF behind its own research flag;
  promoting it needs the same kind of measurement `OMR_METER_TEMPLATE_AT_BAR`
  (2.12i) was refused on, run fresh with the OCR reader in the arm.
- The middle-staff-line split point is CONVENTION ASSUMED, not confirmed
  against a real plate (stated in the reader's own docstring).
- Grace notes/fingerings, bowing marks, and every other named-but-parked
  item from 2.27b/2.27c are untouched; this lane is scoped to 2.29 alone.

## ROADMAP 2.46 — the 36-abstention cascade, diagnosed and fixed

Manager's finding (2026-09-30): the full whole-movement Brahms record
(`library/_shared-records/brahms1-breitkopf-mvt1-whole-20260930b.record.json`,
through INFER, commit `2718c450`) showed `Q.METER` DECIDED on only 16 of 53
systems, 37 ABSTAINED (36 `meter_change_digits_misread`, 1
`meter_return_not_read`) — refining GATHER+ADJUDICATE per Sean's priority.

### The 36 all trace to 5 underlying witness cells

`rhythm._meter_digit_witness_cells` files a `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`
refusal (reason `is_a_meter_digit`, ROADMAP 2.12l) back as a per-CELL witness
on the record. Every one of the 36 abstentions on the whole-movement record
traces to exactly 5 such cells (`_carry_meter` never chains a carry onto a
carry — only a `voted` system is a source, so every abstained system that
walked back landed on the SAME source, `system/0/0`, or on its own local
witness):

| cell | staves w/ the pattern | coverage | REAL printed meter change? |
|---|---|---|---|
| `page/0 system/0 cell/3` | 8 of 14 | 0.571 | **NO** — crop shows a barline then an ordinary note-plus-dot(s) figure repeated across the tutti (`out/print/2.46/w_p0_s0_c3_staff*.png`); no digit ink anywhere |
| `page/1 system/0 cell/1` | 13 of 14 | 0.929 | **YES** — the already-documented 6/8 return (2.12h/2.12i/2.12l), a clean stacked "6" over "8" (`w_p1_s0_c1_staff0.png`) |
| `page/4 system/1 cell/5` | 8 of 14 | 0.571 | **NO** — the identical note-plus-dot/accent figure, with an `sf` beneath it (`w_p4_s1_c5_staff0.png`) |
| `page/6 system/0 cell/0` | 1 of 12 | 0.083 | already sub-floor either way; crop (`w_p6_s0_c0_staff8.png`) shows a system-opening clef/key-signature (flats), not digits |
| `page/6 system/1 cell/0` | 5 of 11 | 0.455 | already sub-floor either way; crop (`w_p6_s1_c0_staff0.png`) shows a rehearsal number ("106") + clef/key-signature at a system's own opening |

Crops rendered from `library/editions/brahms/symphony-1-op68/brahms--symphony
-1-op68--breitkopf-hartel-brahms--imslp317803.pdf` at 600 dpi (pdf pages
1, 2, 5, 7 = record pages 0, 1, 4, 6), measured against the actual ink, not
a downscaled thumbnail; every crop ≥1280 px wide. **Verdict: 1 of 5 real, 4
of 5 false** (2 of the 4 false ones were the only ones actually reaching the
old floor and doing the damage; the other 2 were already sub-floor).

### The mechanism: `is_a_meter_digit`'s own docstring named the exact gap

`notehead_precision.py`'s ROADMAP 2.12l comment named the falsifying case
explicitly and marked it "NOT CONFIRMED WITH SEAN": *"a crop showing a real,
same-interval chord repeating at one x on most staves of a system."* The
false witnesses above are exactly that case — a repeated note-plus-articulation
figure whose y-gap (0.98–1.15 staff spaces, measured) happens to fall inside
the digit pair's own narrow window (0.30–1.20 spaces), on enough staves
(57%) to clear the OLD floor (`METER_DIGIT_QUORUM_COVERAGE = 0.5`, borrowed
from `rhythm._required_corroboration`, a floor sized for a VALUE candidate
that has a SECOND, independent check (bar-length fit) backing it up). A
digit witness has no such second check — cross-staff repetition is the
WHOLE of its evidence — so it must lean on that evidence harder.

**Fix 1** (`tools/omr/staged/adjudicators/notehead_precision.py`):
`METER_DIGIT_QUORUM_COVERAGE` raised 0.5 → 0.8 (CONVENTION ASSUMED, citing
CLAUDE.md §10's "printed... on EVERY staff of the system" for the closest
confirmed analogue, a key change; no numbered convention entry exists yet
for meter specifically — NOT CONFIRMED WITH SEAN). 0.571 and 0.929 are far
enough apart that the exact cut does not matter; margin on both sides.

**Fix 2** (`tools/omr/staged/adjudicators/rhythm.py`, `_carry_meter`): even
after Fix 1, a genuinely real witness on a source system must not veto
every later system regardless of that system's OWN bars — CLAUDE.md §10:
"the carry is weighed by the bars, not gated." Before this fix, the
"too few assessable bars" branch abstained `meter_change_digits_misread`
unconditionally whenever the SOURCE carried a witness, even where `here`'s
own one assessable bar agreed with the carry 1-for-1 (`bars_agree: 1,
bars_disagree: 0` — exactly `system/1/1` and `system/6/0` on the real
record). New `clean_here` gate: the digit-misread abstention only fires
where `here`'s own (too-few-to-decide) bars do NOT cleanly corroborate;
where they do, the SAME `carried_uncontested` path ROADMAP 2.22b already
built for "no vote against the carry" takes over. This never loosens the
DISAGREEING case (a bar that contradicts the carry still abstains, labelled
by the witness exactly as before) — only the previously-unconditional VETO
on a system with clean, if sparse, corroboration.

### Proof

RED→GREEN, `tools/omr/tests/test_staged_meter_digit_witness.py`:
- Pre-existing 17 tests: 3 updated as a straightforward CONSEQUENCE of the
  coverage constant moving (the toy fixture's own floor changed; not a
  regression in their own claim) — `TestIsAMeterDigitFiresOnlyWithCrossStaffQuorum`
  raised from 4 to 10 staves so "bare quorum" (9/10) and "below quorum"
  (8/10, the exact real-world false-positive shape) stay distinguishable.
- 2 new tests: `test_ONE_clean_agreeing_bar_is_no_longer_vetoed_by_a_stale_witness`
  (RED confirmed via `git stash` of both production files: fails
  `AssertionError: ABSTAINED is not DECIDED` on the unrepaired tree) and its
  CONTROL, `test_CONTROL_one_bar_that_DISAGREES_still_abstains_digits_misread`
  (passes on both trees — the gate must never loosen the disagreeing case).
- 19/19 pass on the repaired tree.

`pytest -m "not slow" tools/omr/tests`: **4,176 passed, 3 skipped, 2
xfailed, 0 failed** (base + 2). `python3 -m tools.omr.staged.check`:
**TOTAL 245, status=ok** — unchanged.

### Priced: Brahms pdf pages 0-1 (record pages 0-1), GATHER+ADJUDICATE, `--weights auto --route-weights`

| system | `Q.METER` before | `Q.METER` after |
|---|---|---|
| `system/0/0` | DECIDED `voted` 6/8 (declined_changes carried a false `meter_change_digits_misread` witness at cell 3) | DECIDED `voted` 6/8 (declined_changes now empty of that false witness) |
| `system/1/0` | ABSTAINED `meter_return_not_read` | ABSTAINED `meter_return_not_read` — **unchanged, correctly**: this is the real m.9 return, a genuine reading gap, not this item's bug |
| `system/1/1` | ABSTAINED `meter_change_digits_misread` (citing the stale `system/0/0` cell-3 witness, despite `bars_agree: 1, bars_disagree: 0` of its own) | **DECIDED `carried_uncontested` 6/8** (`bars_agree: 1, bars_disagree: 0`) |

This is the SAME system ROADMAP 2.45 named as the blocker for its own
far-rest fix (`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §21):
2.45's own hand check predicted that a DECIDED 6/8 at this system would
resolve the 3-rest group to the lower staff — now DECIDED, not hypothetical.

A full whole-movement re-adjudication (all 53 systems) was NOT run here
(proof budget, CLAUDE.md §6b — "build and wire," a scoped re-gather over
the two pages holding the real and both floor-clearing false witnesses is
the proof this item needs); the manager's own next whole-movement re-gather
is the instrument that confirms the predicted collapse of the other ~33
abstentions sharing the same `system/0/0` source.

### Not done, named rather than hidden

- No whole-movement re-adjudication was run; the prediction that most of
  the remaining ~33 `meter_change_digits_misread` abstentions collapse to
  `carried_uncontested` (since they share the SAME now-clean source) is
  UNMEASURED past pages 0-1.
- No convention-registry entry exists for "a meter change prints on every
  staff of the system" (the key-signature analogue is cited, not a numbered
  meter entry) — CONVENTION ASSUMED, not confirmed with Sean.
- The `is_a_meter_digit` geometry test itself (tight x, 0.30-1.20-space
  y-gap) is untouched; only the CROSS-STAFF COVERAGE floor moved. A future
  false positive at ≥0.8 coverage (a genuinely orchestra-wide unison
  note-plus-dot figure) is not excluded by construction.

---

## ROADMAP 2.72 — Brahms 1/i p.2: `9/8` read `9/4`, the bar-9 `6/8` change never read, `system/1/1` abstained

2026-10-09, branch `lane-2.72-meter`, off `origin/main` `404285f3`+. STAGED,
GATHER + ADJUDICATE only. Truth is Sean's, off the print (held-bar tiles 1-4,
`out/print/2.65-held/answers.json`, DECISIONS 2026-10-09): bar 8 (the header
of pdf page 1) prints **9/8** on every staff; bar 9 prints a **6/8** change on
every staff, two voices, each adding up; a meter holds until a printed change
(CONFIRMED, not asked again).

### The three failures, traced

**1. The header read `9/4` — GATHER (the whole-stack correlation) and, once
that is fixed, ADJUDICATE (a courtesy filed as a change).**

* *GATHER.* `time_signature_locator.locate_time_signature` takes ONE
  normalised correlation of a four-space Bravura stack at one x. The
  numerator's width and weight set where the stack sits; the denominator is
  scored wherever that leaves it, and both halves feed one number. On the
  plate's 14 header cells the stack reads `9/4` on all 10 staves that clear
  its floor (4 are under 0.50), every one with a runner-up within 0.04-0.09
  (`9/8` never second). Read from its own bottom half, the best `8` leads the
  best `4` on **10 of 10** staves by **0.22-0.33**. The ink never changed; the
  question put to it was about the numerator's shape. (`image_no_staff` also
  loses the rows of the 8's top and bottom arcs where they stand on staff
  lines — the lower half reads as an `A` — which the stack cannot see round
  and the half-template, searched with a half-space of vertical slack, can.)
* *ADJUDICATE.* The page before prints a courtesy `9/8` after its last
  barline; 2.12h routes a vote that contradicts a corroborated courtesy to
  the carry ladder. It never fired: 2.47b stopped counting that trailing strip
  in `Q.MEASURE_PARTITION` (`cautionary_tail_not_a_bar`: 7 bars, last bar =
  cell 6) while `_meter_changes` still tested `last_cell == cell`, so the
  `9/8` in cell 7 was filed as a CHANGE at a cell that is not a bar and
  `value["cautionary"]` stayed empty. A glyph past the last bar is a
  courtesy by construction.

**2. The bar-9 `6/8` was never read — three independent reasons.**

* `OMR_METER_TEMPLATE_AT_BAR` was `research`/OFF. Its own gate (2.12i: state
  this `6/8` with a quorum) FAILED: the stack scores **0.44-0.51** on all 14
  windows against a floor of 0.50 (2 read), naming `6/4` or `9/8`.
* Its candidate columns needed a detector `timeSig*` box. The detector boxes
  these digits as NOTEHEADS (2.12l: 13 of 14 staves; the one `timeSig1` is
  staff 9's), so the column opened by luck on this page and would not on
  another.
* `_meter_changes` visited only cells with a `Q.METER_GLYPH` row; a column
  opened by the template readings of the staves alone was never evaluated.

**3. `system/1/1` abstained `meter_change_digits_misread`** because its carry
source (`system/1/0`) held a change it never read; with the change read
(`6/8` at cell 1, 14 of 14 staves) the carry is `6/8` and the system is
DECIDED `carried`.

### What the bars say (asked, as the brief required)

Nothing, for either meter. `system/1/0`, 13 staves with a summable bar in
cell 0: **no staff sums to 4.5 (9/8) or to 9.0 (9/4)**; the sums are all
singletons (10.0, 7.75, 3.5, 8.0 ...), so `bars_assessable: 0` for the carry.
Across the system's 7 cells: 2 staves sum to 3.0 (6/8) in each of cells 2, 5
and 6, 1 staff sums to 4.5 in each of 2, 5 and 6, 1 staff sums to 9.0 in
cell 1. The bars cannot weigh 9/8 against 9/4 on this page (shattered heads,
`benchmarks/omr-bar-sum-holdout-2026-09/`); the READER and the courtesy
decide, and they now agree. Rule 8 holds: with only the ADJUDICATE fix (the
courtesy filed correctly, the header still `9/4`) `system/1/0` ABSTAINS
`meter_return_not_read` rather than asserting either — the `9/4` is no
longer decided against a corroborated courtesy.

### What was built

`tools/omr/time_signature_locator.py`

* `_split_reading` (used by `locate_time_signature`; `config.split_halves`):
  the stack decides THAT a meter stands, WHERE, and the NUMERATOR (its floor
  unchanged); the DENOMINATOR is re-read from the bottom half among the
  listed meters that keep that numerator. Records `stack_raw` (where it
  differs) and `denominator_margin`. A letter form is untouched; a
  denominator outside the stack's column is refused and the stack stands.
  **A first cut re-read the NUMERATOR too and was refused on measurement**:
  on the 11-source header corpus it changed 10 of 496 staves — 4 right to
  wrong, 2 wrong to right, 4 wrong to wrong (Beethoven 5's two `2/4` became
  `4/4`; Beethoven 3's `3` on a Litolff plate moved among `3`, `6`, `9`;
  Dvorak 9) — all numerators but one. The shipped cut moves **0 of 496**
  (`sweep_widened.py --per-staff`; `--no-split` is the old reader), and
  `corpus.json` gains `brahms1-p2-9over8`: stack-only **WRONG** (`9/4`),
  split **OK**; the old 11 sources stay WRONG 0 / correct 9 / missed 3 /
  silent 39.
* `locate_meter_by_halves` (the bar-head reader): each half searched on its
  own with the strip's own half-space vertical slack, a meter = the best
  consistent (one column) listed pair, score = the WEAKER half, floor = the
  header's own `min_score` 0.50 — **no new number**.

`tools/omr/staged/gather.py`: `gather_meter_at_bars` uses the halves reader;
`_meter_candidate_columns` also opens on the stacked-head pair
`notehead_precision.is_a_meter_digit` tests (loose, no quorum; a firing only
spends a reader call); `OMR_METER_TEMPLATE_AT_BAR` default **ON** (deny-list)
and out of `OMR_RESEARCH`; the flag stays as the one-tree A/B switch.
`rhythm._meter_changes`: a glyph in the tail (`cell > last bar`) is a
cautionary; cells the staves' template readings agree on (>= 3 staves, one
meter) are visited with no glyph row.

### The hazard that kept the flag off, re-measured

`benchmarks/omr-meter-template-changes-2026-09/probe/empty_window.py`'s own
mid-staff bar-head windows (1,830 here, the probe's slicing rule; ten real
scanned pages: Brahms 1 p6, 22, 42-45; Beethoven 5 / Litolff p56, 57, 63,
86), none printing a change, so every answer is false. The halves reader's
weaker-half score over them: max 0.526, p99 0.469, median 0.294.

| floor | answered | rate | columns with 2 staves agreeing | with 3 |
|---|--:|--:|--:|--:|
| 0.42 | 143 | 7.81% | 28 | 4 |
| 0.45 | 60 | 3.28% | 9 | 2 |
| 0.48 | 10 | 0.55% | 1 | 0 |
| **0.50 (shipped)** | **3** | **0.16%** | **0** | **0** |

The stack reader at the same floor answered 16 of 1,612 (0.99%) with 2
columns of two staves agreeing (2.12i's table). The floor is NOT read off a
gap — the false scores thin out smoothly (the 2.12i warning stands) — it is
the header's own value, and the safety is still the three-staff quorum
(`METER_TEMPLATE_AT_BAR_MIN_STAVES`), which measured zero false columns here
at every floor from 0.48 up. The 14 true windows of the plate score
**0.52-0.62** (the weaker half): headroom over 0.50 is 0.02 on the weakest
one. That is thin, and it is one plate.

### Re-score (small re-gather, GATHER+ADJUDICATE only, clean tree `0510ce3d`)

`acceptance_quick --doc brahms1-breitkopf|beethoven5-litolff`; base = the
manager's `404285f3` records, arm = this branch.

**Sean's tiles 1-4, the meter in force at each tile's bar** (`record.meter_at`
on the system verdict at the tile's cell):

| tile | cell | Sean | before | after |
|---|---|---|---|---|
| 1 | `cell/1/0/0/0` | 9/8 | 9/4 WRONG | **9/8** RIGHT |
| 2 | `cell/1/0/1/0` | 9/8 | 9/4 WRONG | **9/8** RIGHT |
| 3 | `cell/1/0/0/1` | 6/8 | 9/4 WRONG | **6/8** RIGHT |
| 4 | `cell/1/0/3/1` | 6/8 | 9/4 WRONG | **6/8** RIGHT |

(Tiles 5-8, the whole rests, were already right; tile 8's lone rest sits on
`system/1/1`, which now has a meter — the EVALUATE rule that would size it is
outside this item's two stages.)

**Population, every system whose `Q.METER` verdict changes:**

*Brahms pdf p.0-1* (3 systems, 3 changed): `system/0/0` DECIDED 6/8 with a
`9/8` CHANGE at cell 7 -> DECIDED 6/8 with the `9/8` a CAUTIONARY (14 of 14
staves read it in the tail window); `system/1/0` DECIDED `9/4` -> DECIDED
`9/8` with a `6/8` change at cell 1 (14 of 14 staves, support 42.5);
`system/1/1` ABSTAINED `meter_change_digits_misread` -> DECIDED `carried`
6/8. Bar-head windows asked 232, answered 28 (14 + 14, the two real
columns), no false column. Staff-bars whose summed durations equal the meter
in force (a control, not a headline): **41 -> 68 of 204** that have a sum.

*Litolff pdf p.0-3 (count page p.3)*: **0 of 5 systems change** (the `2/4` on
`system/1/0` voted, carried on the rest, identical), 327 -> 327 of 484. Bar-
head windows asked 417, answered 2 (one staff each, no quorum, no change).

Crops of the changed meters Sean has not judged (the page-0 courtesy `9/8`
and the carried `6/8` at the start of `system/1/1`): `out/print/2.72/`
(`manifest.json`); the frame control (the record's staff lines must land on
dark rows of the render) can fail and did not.

### Not done, named rather than hidden

* **The header's staves under the stack floor.** 4 of 14 Brahms header staves
  score under 0.50 on the stack and stay unread; the halves would read all 14
  (the first cut did) but the same first cut flipped Litolff numerators, so
  the header presence rule is untouched. A presence rule on the halves for
  the header would need its own empty-header measurement.
* **Litolff pdf p.62 prints a real `3/4` change** (`system/0/0` cell 6, 17
  staves, digits ~1.3 spaces tall): the halves floor 0.50 admits 2 staves (no
  quorum); at 0.42 it names `3/4` on 4 and `9/4` on 3 — the numeral half is
  the weak one on that plate (0.36-0.51) while every denominator `4` scores
  0.58-0.73. Pooling the per-staff half tables across the system (a change is
  ONE printed event witnessed by every staff) puts `3` first by 0.015 —
  thin. It needs the tables filed with the rows; not done (the page reads
  nothing before or after).
* The whole movement is not re-gathered (proof budget); the other
  `meter_change_digits_misread` abstentions that share a source are
  unmeasured past pages 0-1.
* CONVENTION: none new. The one-column test for a pair (centres within 0.6
  space) is geometric (a time signature centres its two rows), not
  confirmed with Sean.
