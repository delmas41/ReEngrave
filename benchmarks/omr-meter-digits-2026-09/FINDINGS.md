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

## ROADMAP 2.46 truth check: who says the 34 DECIDED systems are right?

2026-10-01, branch `lane-2.48-classify` (day-manager lane). STAGED,
ADJUDICATE only, per CLAUDE.md §6b (the overnight 20261001 full re-gather,
`THROUGH=adjudicate`, commit `342ec6244bdd`, Brahms whole movement pages
0-26). Who says it's right (rule 7): the reference ENCODING
(`library/reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl`,
`source_kind: encoding`, used here only as MEASUREMENT truth — never fed to
the pipeline) and a direct crop of the print, per Sean's convention that a
print check and an encoding check must agree before either is trusted.

**The reference's own meter history for the whole 513-bar movement is three
lines, not a long list**: `<time>` appears at measure 1 (6/8), measure 8
(9/8), measure 9 (6/8 — the return). Every other bar of the movement is 6/8
by the carry. This matters: it means the 34-system comparison this item asks
for collapses to one question — does any DECIDED system's bar range cover
measure 8, and if so does it say 9/8?

**Extracted all 53 `Q.METER` verdicts with `tools.omr.staged.record_io
.load_record` + `readout.run_from_result`** (never re-derived by hand):
34 DECIDED, all thirty-four `6/8` (`voted` once at `system/0/0`, `carried` /
`carried_uncontested` elsewhere); 19 ABSTAINED (1 `meter_return_not_read`,
16 `carry_not_corroborated`, 2 `carry_outweighed_by_the_bars`).

**Bar ranges**: `printed_bar_number` (a DIFFERENT, sparser quantity — a
margin-digit OCR read, not the record's own bar accounting) is corroborating
but noisy (e.g. `page3/system1` reads "8" immediately after `page3/system0`
read "38" — a misread, not a new count); it was used only as a cross-check,
never as the join key. The join key is `Kind.CELL` counts: `cell/{page}/
{system}/{staff}/{cell}` (⚠ the staff field sits BEFORE cell in the subject
key — a first pass that took the wrong field as the cell index overcounted
every system's bar total by double; corrected before anything downstream
ran). Cumulative real bars across the 53 systems in page/system reading
order comes to 515 against the reference's 513 — a 2-bar drift consistent
with the reference's own anacrusis handling, not a join error.

**The one place a DECIDED system's own evidence disagrees with its own
decided value**: `system/0/0`'s meter value carries BOTH `segments: [{6/8,
from_cell: 0}]` (the decided, voted value) AND a `cautionary` field — a
SEPARATE, corroborated 9/8 candidate at `from_cell: 7`, `staves_reading_it:
9 of 10`. `from_cell: 7` is this system's LAST cell. Crop-checked at the
gather's own 600 dpi (`out/print/2.46/brahms-p0-system0-cautionary-tail.png`):
cell 7 is a ~113px-wide sliver (every real cell in this system is 500-700px)
holding nothing but a courtesy time-signature sign printed to the right of
the system's actual last barline — not an eighth bar. The adjudicator
correctly filed it `cautionary` rather than folding it into `segments`
(CLAUDE.md §10: "a cautionary meter after a system's last barline governs no
bar") and the system's 7 REAL bars (cells 0-6) are all 6/8 in the reference
too — **right**.

`out/print/2.46/brahms-p1-system0-m8-m9-head.png` crops the very next
system, `page/1 system/0` — the ONE system that ABSTAINS
(`meter_return_not_read`). The crop shows the margin digit **"8"** at the
system's left edge (confirming `printed_bar_number`'s own correct read
here), a printed **9/8** on every staff at cell 0, and a printed **6/8**
return at cell 1 — exactly measures 8 and 9 of the reference. This is the
movement's ONLY meter excursion, and it falls entirely inside the one
system that correctly declines rather than guesses. No DECIDED system's bar
range reaches measure 8 or 9.

### Result

| | count |
|---|---|
| right | **34 of 34** |
| wrong | **0** |
| can't-align | 0 |

All 34 DECIDED meter verdicts agree with the reference encoding at
per-bar granularity, confirmed by two 600-dpi print crops. The remaining
`declined_changes`/`cautionary` entries attached to OTHER decided systems
(e.g. `page5/system1`'s 4/4 cautionary, `page19/system1`'s 4/4 cautionary)
are candidates the adjudicator correctly left unapplied — the reference has
no meter change anywhere near those bars either, so these are the ALREADY
-documented false digit witnesses (ROADMAP 2.46's own "4 of 5 false" count),
not a new finding.

**Nothing to fix here.** The one real gap (`page/1 system/0`,
`meter_return_not_read`) is unchanged and already named by ROADMAP 2.46 as
"the one REAL gap, untouched" — this item confirms by an independent
method (reference encoding + print crop, not the adjudicator's own log)
that it is the ONLY gap, and that every DECIDED system is correct.
