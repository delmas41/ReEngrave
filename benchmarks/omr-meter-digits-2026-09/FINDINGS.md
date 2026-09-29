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
