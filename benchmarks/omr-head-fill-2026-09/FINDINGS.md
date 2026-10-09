# ROADMAP 2.23 -- a head's fill (hollow vs black) is read from the ink, not only from the detector's class

PATH: STAGED. Branch `claude/head-fill-2.23`. Not merged.

`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` Sec.17b: on Litolff 1/i
(Beethoven 5/i, Litolff `984073`, a MERGING plate -- CLAUDE.md Sec.10), the
single biggest minimal-fix class over the whole movement's held bars is
`F` -- **300 bars**, 405 released as the sole fix -- "one note's head fill
or stem misread", 278 of them a lone quarter-valued chord in a 2/4 bar.
Sec.17b's own crops (`out/print/held-mvt-2026-09-29-litolff-F-*.png`) read as
hollow (half/whole) heads the detector called BLACK on a MERGING plate.

Today the head's fill comes ONLY from the detector's class
(`noteheadBlack*` vs `noteheadHalf*`/`noteheadWhole*`). This item asks
whether the ink under the box says something the class does not, and if
so, wires it in as a NARROW, never a flip.

## Sec.1. First: read the crops by eye, then measure -- is there a gap?

### Sec.1a. The six `F`-class crops, read by eye

`benchmarks/omr-bar-sum-holdout-2026-09/out/r222/litolff-F-jobs.json`
names 6 subjects (page/system/cell, `judged_quarters=2.0`, `voice_sums=
[1.0]` on every one -- the bar is short by exactly one quarter, the
signature of a half misread as a quarter). Zoomed crops of all six
(`held-mvt-2026-09-29-litolff-F-0{1..6}-F.png`, red corners bracket the
subject):

- **#1** (`glyph/1/0/8/8/{3,4}`, m9, P9): a visible white sliver inside
  the black ink, merged with the staff line -- a hollow head whose border
  fused with its own rung.
- **#3** (`glyph/3/0/10/4/1`, m52, P11): stem visible, head sits at the
  cell boundary; ambiguous by eye alone at this zoom.
- **#5** (`glyph/5/0/5/5/{0,1}`, m117, P8): reads as fully solid black at
  10x zoom -- no visible hollow. This one may be a genuine BLACK head
  whose bar is short for a DIFFERENT reason (a spurious/missing event
  elsewhere); `F` is the MINIMAL single-letter fix, not a claim that the
  head itself is the fault.
- **#6** (`glyph/6/0/8/3/{1,4,7}`, m145, P11): unambiguous -- a clear white
  hole inside the black ink at 5x zoom, sitting on the staff line.

Two of six are unambiguously hollow by eye; one (#5) looks genuinely
solid. This is exactly why the fix must be a NARROW decided by the bar's
own arithmetic (reconcile_duration), never a flip on ink alone -- ink
alone would be wrong on #5.

### Sec.1b. The measurement: does `Q.NOTEHEAD_INK` separate them?

Ported the GATHER half only of `claude/no-ink-head-2.6h` (`a8394476`) --
`gather.notehead_ink_under` / `gather_notehead_ink`, `Q.NOTEHEAD_INK` (two
windows, `center` and `ring`, off BOTH `cell.binary` and `cell.image_no_
staff`) -- into `tools/omr/staged/{gather,record,capture}.py`. Did NOT
port `a8394476`'s own ADJUDICATE half (`notehead_precision._no_ink_
under_box`, measured DEAD AT ZERO and not merged -- ROADMAP row 2.6h).

Re-gathered (CLAUDE.md Sec.5a setup; `--no-surya --no-ocr`, own weights):

- **Engraved control**: `benchmarks/omr-staged-engraved-2026-09/out/
  fixture/beethoven-sym5-mvt1-m1-24.pdf`, pages 0-2, `imgsz2048-ft-30ep.pt`,
  dpi 300 -- the fixture whose truth F1 is 0.951, so the DETECTOR's own
  `noteheadHalf`/`noteheadBlack`/`noteheadWhole` class is a trustworthy
  proxy for the true fill on this population.
- **Litolff**: pdf idx 1-6 (the six pages the `F` crops sit on),
  `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, dpi 600.

372 engraved heads, both `ink_raw` and `ink_net` windows, grouped by the
DETECTOR's own class:

| class | n | `center` (min / median / max) | `ring` (min / median / max) |
|---|--:|---|---|
| `noteheadBlack*` | 532 rows | 1.0 / 1.0 / 1.0 | 0.652 / 0.751 / 0.862 |
| `noteheadHalf*` | 206 rows | 0.070 / 0.108 / 0.449 | 0.477 / 0.573 / 0.652 |
| `noteheadWhole*` | 6 rows | 0.964 / 1.0 / 1.0 | 0.509 / 0.536 / 0.537 |

**There is a clean, decisive gap between BLACK and HALF**: every confirmed
BLACK head reads `center == 1.0` exactly; every confirmed HALF head reads
`center <= 0.449`. At threshold `center <= 0.5` AND `ring - center >=
0.1`: **206/206 HALF heads admit "hollow"; 0/532 BLACK heads do; 0/6 WHOLE
heads do.**

**KNOWN GAP, found by the same measurement, not papered over**: WHOLE
heads read `center == 1.0` too -- indistinguishable from BLACK by this
test. A whole notehead's box is wide and short; shrinking 30% on every
side (`NOTEHEAD_INK_CENTER_SHRINK`) lands the "centre" window back on the
ellipse's own ink rather than its hole. **This test can only ever catch
a HALF head misread as BLACK, never a WHOLE head misread as BLACK.** That
is the correct, safe failure mode (rule 8: it abstains rather than
guessing), and it is why the built rule still offers `whole` as a
candidate FOR THE BAR TO CHOOSE, never claims the ink witnesses it.

**Conclusion: yes, there is a separating gap** -- proceed to ADJUDICATE.

## Sec.2. Built (ADJUDICATE): `rhythm.adjudicate_duration` NARROWS on decisive disagreement

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (nobody has
been asked, CLAUDE.md rule 3): a hollow head's own interior stays
near-empty even where its border merges with neighbouring ink; a
genuinely filled BLACK head does not. It would be falsified by a
Sean-adjudicated crop where a confirmed BLACK head reads this way, or a
confirmed HOLLOW head does not (this benchmark's own crops, Sec.4, are the
first test of it).

`tools/omr/staged/adjudicators/rhythm.py`, `adjudicate_duration`: reached
only where NOTHING else already narrowed or added a mark to this note
(no flags, no ambiguous beams, no stem-tip flag ink -- `beam_evidence ==
"none_over_this_note"`, guard `not tip_ink`) and the detector's own class
says BLACK (`base == 1.0`) -- a hollow head never carries a beam or a
flag, so this is exactly the right population. Reads `Q.NOTEHEAD_INK` off
the SAME glyph (`_ink_reads_decisively_hollow`, either raster alone is
enough, same two-raster safety the gather side states). Where decisive,
`Ruling.narrow` over three candidates -- `black` (the detector's own
reading, support 1.0), `half` (support 2.0 -- the single-step misread
Sec.17b's crops show), `whole` (support 1.0, the rarer two-step misread,
included so `reconcile_duration`'s own bar arithmetic can still pick it
where it is the unique landing). **Never flipped outright** -- `reason=
"head_fill_from_ink"`, `Outcome.NARROWED`, exactly the shape 2.19/2.22's
`reconcile_duration` already knows how to search (`_admitted` reads a
NARROWED note's own candidates; no change needed there).

Thresholds (`HEAD_FILL_HOLLOW_CENTER_MAX = 0.5`,
`HEAD_FILL_HOLLOW_RING_GAP_MIN = 0.1`) are the Sec.1b engraved measurement,
with margin on both sides of the gap.

## Sec.3. Priced on the re-gathered pages

**Whole-movement re-gather (pages 1-6, both `F`-crop pages) was attempted
and KILLED, not completed** -- CLAUDE.md Sec.6b's noise floor and
Sec.13's "sessions in parallel" both understated it: load average 6.6-6.8
on this shared machine, two OTHER sessions' processes each holding ~98%
CPU throughout, my own gather sat at 0.0% CPU (frozen wall-clock, not
progressing) for 5+ minutes at a stretch, on page 6 of 6 after ~17 minutes
elapsed. This is the exact "frozen-CPU-time shape... contention, not a
hang" `claude/no-ink-head-2.6h` (`a8394476`) already named. Killed rather
than re-risked (that commit's own precedent); **pricing the full 300-bar
`F` population is NOT DONE and needs a re-attempt when the machine is
less loaded** -- this is the honest state, not a number to round up.

**Fell back to ONE page** (Litolff pdf idx 6, containing the original
`F`-06 crop, m145) -- cheap, and it completed. `--musicxml` on a lone page
carries no `<time>` (the meter is declared at the movement's START, page
0, not on this page), so `bar_sum_check.py` reports every bar
`unassessable` on this file -- an artefact of slicing one page out of a
movement, not a property of this rule. Bar-level pricing therefore reads
the RECORD directly (`Q.EVENT`/`Q.DURATION`), not the exported file.

**Reach, on this one page**: 786 notehead-classed glyphs read
`noteheadBlack*`. Of those, **8 read decisively hollow by ink**
(`center <= 0.5` and `ring - center >= 0.1`, either raster) -- 1.0% of the
population, in line with a genuinely rare misread, not a threshold that
fires promiscuously. Of those 8:

- **2 are genuinely BEAMED** (`beam_evidence == "read"`, both `beats =
  0.5`, real eighth notes) -- the ink's hollow-shaped reading on these is
  a FALSE POSITIVE by the ink test alone, and the marks-gate
  (`beam_evidence == "none_over_this_note"`) correctly keeps them OUT of
  this rule's population. Crops #2/#3 below.
- **4 sit where the beam READER NEVER RAN on that cell**
  (`beam_evidence == "reader_declined"`) -- a different state from "ran
  and found nothing", and the gate (matching `flag_ink_unread`'s own
  convention, same file) correctly declines these too rather than
  narrowing under an unknown beam context. Crops #4/#5 below (2 of the 4).
- **1 is the original `F`-06 crop's own BLACK-classed member**
  (`glyph/6/0/8/3/4`): `ink_net` centre reads **0.6036** -- just ABOVE the
  `0.5` threshold, so the rule correctly declines (rule 8: not decisive,
  left alone). Crop #6.
- **1 reaches the rule and NARROWS** (`glyph/6/1/9/2/9`, `beam_evidence ==
  "none_over_this_note"`): `Ruling.narrow` to `[black 1.0q, half 2.0q,
  whole 4.0q]`, `reason="head_fill_from_ink"`. It stayed NARROWED, not
  DECIDED -- `reconcile_duration`'s cause is `Q.METER`, and this system's
  meter ABSTAINS (the same, already-documented Sec.17a gap: "3,058 [Brahms]
  held bars sit on systems whose `Q.METER` ABSTAINS" -- this is Litolff's
  own instance of it), so the bar arithmetic that would pick among the
  three candidates never runs. **This is an orthogonal, pre-existing gap,
  not a defect introduced by this rule.** Crop #1.

**A caveat worth recording rather than hiding**: the one glyph that
reached and narrowed has a low detector confidence (0.257, against a
0.504 page median) and a page-pixel box only 6.3px wide -- narrow even
for this scan's own noisy population, and possibly a fragment rather
than a clean notehead detection. Confidence alone is not evidence about
what a glyph IS (CLAUDE.md Sec.9's own caution), and 0.257 is within this
page's ordinary noisy range, so this is flagged, not dismissed.

**Also notable, and NOT this rule's effect**: on this fresh re-gather,
the DETECTOR ITSELF already reads two of the original `F`-06 crop's three
boxed glyphs as `noteheadHalfOnLine` (correctly!) rather than
`noteheadBlackOnLine` -- a run-to-run detector variance between the
original whole-movement gather and this one-page re-gather, consistent
with CLAUDE.md Sec.6b's "a shared record is a snapshot of the reader that
made it" and the scan gate's own noise floor. It is evidence the specific
historical misread is not perfectly deterministic, not evidence this
rule fixed it.

**Engraved control, re-checked on the SAME re-gather used for Sec.1b**: 0
of 372 heads carry `reason == "head_fill_from_ink"` and 0 carry a
resolved `head_fill` -- the rule does not fire at all on the engraved
fixture, where the detector's own BLACK/HALF/WHOLE class already agrees
with the truth at F1 0.951. No real BLACK head is narrowed wrongly.

## Sec.4. Crops

6 banded crops, `benchmarks/omr-head-fill-2026-09/out/print/head-fill-2026-09-0{1..6}.png`,
manifest `head-fill-2026-09-manifest.json` (`VERDICT_none_yet: null`).
GREEN = the staff's own lines; red verticals = the cell's x-span; red
corners bracket the subject glyph's own box. **Frame control
(`crop_losers_2_6b._frame_ok`) REFUSED #2 and #4** (contrast -84.2 and
-99.75) -- kept in the manifest with `frame_ok: false` per the others'
convention, not presented as evidence.

| # | subject | frame | what it shows |
|---|---|---|---|
| 1 | `glyph/6/1/9/2/9` | ok (28.7) | the one head that reached and NARROWED |
| 2 | `glyph/6/0/3/8/19` | REFUSED | genuinely beamed, ink false-positive, gate protects it |
| 3 | `glyph/6/1/11/5/3` | ok (29.1) | genuinely beamed, ink false-positive, gate protects it |
| 4 | `glyph/6/0/0/9/1` | REFUSED | beam reader declined, gate protects it |
| 5 | `glyph/6/1/1/0/8` | ok (110.6) | beam reader declined, gate protects it |
| 6 | `glyph/6/0/8/3/4` | ok (202.4) | the original `F`-06 BLACK member, borderline ink, correctly declined |

## Sec.5. Gates

- RED -> GREEN: `tools/omr/tests/test_staged_notehead_ink.py` (14 tests,
  ported GATHER half only -- the pure measurement, positive controls for
  BLACK and HOLLOW synthetic heads, the orchestration on a fake cell).
  `tools/omr/tests/test_staged_duration.py::
  TestAHeadsFillIsReadFromTheInkNotOnlyTheClass` (9 tests): a decisive
  BLACK-vs-hollow disagreement NARROWS to `[black, half, whole]`;
  POSITIVE CONTROL -- a dense centre (the engraved BLACK reading) still
  DECIDES; no `Q.NOTEHEAD_INK` row at all is unchanged (rule 8); an
  ambiguous reading that clears neither threshold is unchanged; a HOLLOW-
  classed head is not this rule's population even with ink rows attached;
  `flag_ink_unread` (2.18c) takes priority when it already narrowed the
  note (`not tip_ink` guard); it never decides straight to `half` -- stays
  NARROWED (rule 6); the ink row is in the verdict's `basis`; either
  raster alone (`ink_raw` XOR `ink_net`) is sufficient. Confirmed RED
  first by reverting the `rhythm.py` diff and re-running: 4 of 9 fail
  (`AssertionError`) against the unmodified tree.
- `pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider`:
  3784 passed, 3 skipped, 0 failed (full run, no mid-run edits).
- `python3 -m tools.omr.staged.check`: **247, status ok** (unchanged; `wiring` 69->67 and `reach` 25->24 both went from `broken` to `ok`
  once the ADJUDICATE consumer was wired -- confirming `Q.NOTEHEAD_INK`
  reaches a live consumer) (baseline on this
  tree before this change: 247, confirmed by stashing this diff and
  re-running).

## Sec.6. Recommendation

**Ship the GATHER + ADJUDICATE mechanism** (safe, tested, reach-confirmed
on a real scan page, zero false narrowing on the 372-head engraved
control, and it costs nothing where it does not fire -- 785 of 786 black
heads on the priced page are untouched). **Do not yet claim it releases
the 300-bar `F` population** -- that number needs the whole-movement
re-gather this session could not complete (killed at page 6/6 GATHER
after ~17 min of shared-machine contention), and the one page priced
turned up exactly one reaching case, blocked from resolving by an
unrelated, already-documented gap (Sec.17a's meter-abstains-on-system
problem, not this rule).

**Next steps, in order**:
1. Re-attempt the whole-movement Litolff (and ideally Brahms) re-gather
   on a quieter machine/window to price the real `F` population and get
   `bar_sum_check` numbers with a declared meter.
2. Sean's read on the 4 valid crops (#1, #3, #5, #6) -- in particular
   whether #1's low-confidence, 6px-wide box is a real notehead at all.
3. If §17a's meter-carry question (already asked, 2.22) is answered, a
   second pass over the SAME re-gather would show whether this rule's one
   narrowed case actually resolves once the meter is decided.



## Sec.7. ROADMAP 2.70 -- a hollow head with nothing on its stem is a half note

PATH: STAGED, ADJUDICATE (`rhythm.adjudicate_duration`, the 2.23 block).
Branch `lane-2.70-hollow-half`. Not merged.

CONVENTION CONFIRMED (Sean, DECISIONS 2026-10-09, answering Sec.2's
"CONVENTION ASSUMED"): *"A hollow note with nothing on the stem is always a
half note."* Evidence he judged blind: `out/print/2.65-headfill/`
(`answers.json`, `compare-20261009-all.txt`).

### 7a. Why the tiles failed on today's tree (measured, `--through adjudicate`, Litolff pdf p6 alone, `--weights auto`)

Today's detector boxes tiles 5 and 6 TWICE -- a `noteheadBlack*` and a
`noteheadHalf*` box on one head -- and the duplicate rules keep the BLACK one
and refuse the half (`stacked_head_duplicate` for tile 5, `notehead_is_a_
duplicate_box` for tile 6). On this page 9 refused half boxes lost to a
black keeper; the stacked-head keep choice is "the box with the most ink"
(`notehead_ink_under`'s `best`), which prefers a filled box over a hollow
one by construction -- a bias that deletes half notes. NOT changed here.

| tile | Sean | today's box | why 2.23 did not narrow it, why nothing decides it |
|---|---|---|---|
| 5 | half | black `glyph/6/1/1/0/10` | ink reads hollow (centre 0.4745 on both rasters, ring 0.79), stem attached, tip ink read none. Gated out by `beam_evidence == "reader_declined"`: the cell holds NO beam, so `Q.BEAM_STROKE` is DECLINED (abstention `no_line_accepted`: the reader RAN and accepted nothing) and `Evidence.state` calls that declined. A reader that looked and found none was spelled "cannot tell". |
| 6 | half | black `glyph/6/0/8/3/4` | THREE causes, none the gate: ink `net` centre 0.6036 (> the 0.5 cut; `raw` 0.93 because the staff line passes through an on-line head's hole); the black box ends 2 px short of its stem (`stems_on` is overlap with no tolerance, so `own_stems` is empty -- only the refused half twin touches it); and the keeper of the double detection is the black box. Not fixed: loosening the cut to 0.61 would be fitting one tile. |
| 3 | half + slash | none | the detector draws NO head box here today; a `restQuarter` box (iou 0.43) covers the stem and slash. Unreachable by ADJUDICATE; 2.71 is not what blocks it (the cell's one beam stroke is a neighbour's, y 0-65). |
| 4 | whole rest | black `glyph/6/0/0/9/1` | ink_net reads hollow (centre 0.23) but there is NO stem, so the new rule does not apply; today's tree decides quarter (unchanged -- the refusal control holds: not half). |

### 7b. What is built

`hollow_head_bare_stem` (new reason on `adjudicate_duration`): DECIDES `half`
(dots apply) where ALL hold -- the detector class is black; `Q.NOTEHEAD_INK`
reads decisively hollow by 2.23's own cut (NOT loosened); the head has its
OWN stem; no beam stroke was read over it BEFORE 2.43's hollow-zeroing
(`strokes_before_hollow == (0, 0, 0)`); no flag box attached; the stem tip
was MEASURED and shows no hook (`_stem_tip_flag_ink` is False; a tip nobody
measured stays "cannot tell"); and the CV beam reader LOOKED
(`_beam_reader_looked`: strokes filed, or every abstention is
`no_line_accepted`/`no_stems_to_join` -- never `not_implemented`/
`reader_unavailable`). A hollow head with no stem keeps 2.23's NARROWING
(whole, or a whole rest boxed as a head -- never half). The 2.18c block and
`_stem_tip_flag_ink` are untouched (fence: `lane-2.69-flag-hooks`); the rule
CALLS `_stem_tip_flag_ink` for cells the old spelling skipped, so a signature
change there needs a merge look.

⚠️ Found, not changed: with the beam reader's `ran_empty` read as `reader_
declined`, 2.18c's `flag_ink_unread` narrowing is ALSO unreachable in any
beamless cell (the existing tests add a decoy beam to reach it). That is the
2.69 lane's block.

⚠️ Found, not changed: a hollow-reading head with a beam stroke READ over its
stem (strokes_before_hollow > 0) is narrowed `[black, half, whole]` by 2.23
-- the read beam levels (eighth ...) are not candidates. 2.43 zeroes the
strokes for any open-reading head and 2.23 then ignores them. This rule
stands down there (test `test_a_beam_joined_to_this_stem_blocks_it`), but the
narrowing itself drops a read beam.

### 7c. Red -> green

`tools/omr/tests/test_staged_duration.py::
TestAHollowHeadWithNothingOnItsStemIsAHalfNote` (13 tests). Against the
unrepaired tree (`rhythm.py` reverted): 4 FAIL (`bare stem under hollow ink
is DECIDED half`, `reaches a cell the beam reader RAN in and accepted
nothing`, `a dot still lengthens the half`, `the ink row is in the basis`),
9 pass -- the refusal/positive controls: beam reader never ran, no stem,
stemless hollow head in a beamless cell (whole-rest control), beam joined to
the stem (`strokes_before_hollow` read non-zero in the same fixture), flag on
the stem, hook at the tip, tip unread, black ink agrees (quarter), ink not
decisive (0.6). Green on the repaired tree.

### 7d. Population (GATHER+ADJUDICATE, base arm = the same tree with the rule's gate forced to "cannot tell", `scr` wrapper in the lane scratch)

| page(s) | black-class kept heads | ink reads hollow | stem + eligible | duration changed |
|---|--:|--:|--:|--:|
| Litolff pdf p6 | 669 | 3 | 1 (tile 5) | **1** (quarter -> half) |
| Litolff pdf p3 | 252 | 3 | 0 (all stemless) | 0 |
| Brahms pdf p0-1 | 1,054 | 1 | 0 (stemless) | 0 |
| engraved Beethoven fixture p0-2 | 262 | **0** (centre 1.0 on all 262, both rasters) | 0 | 0 |

The rule is correct and dead-small: the 0.5 ink cut admits 7 of 1,975
scan black heads. The loss is upstream of this rule -- the CUT and the DEDUPE.
Eight Litolff heads the detector calls black, that carry a stem, and whose ink
centre reads 0.50-0.72 (ring gap >= 0.1) were cropped
(`out/print/2.70/halfnote_01..08.png`, manifest alongside) and look like half
notes by eye; they are NOT decided and NOT judged by Sean. They are the
question for the next step (what cut, measured against his answers, never
fitted to them).

### 7e. Gates

`pytest -m "not slow" tools/omr/tests -q` and `python3 -m tools.omr.staged.
check` -- numbers in the lane report.
