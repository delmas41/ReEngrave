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


## Sec.8. ROADMAP 2.73 -- a hollow head CUT BY A LINE is one head

PATH: STAGED, GATHER+ADJUDICATE only (first two stages, Sean 2026-09-30). Branch
`lane-2.73-line-cut-heads`, built on `lane-2.70-hollow-half` (subsumes it: its
`hollow_head_bare_stem` rule and beamless-cell gate fix are kept unchanged) merged
with main. Not merged.

Sean (2026-10-09): *"half notes, especially ones that are on lines or ledger
lines, get split up into two smaller boxes instead of one large box around the
notehead. I think the way the boxes are automatically choosing the hollow noteheads
is off."* Artefacts: `out/2.73/`.

### 8a. The mechanism, measured (Brahms 317803 pdf 0, Sean's 27 hand-labelled half heads, 600 dpi)

`score_handtruth_2_73.py` is the first scorer on the hand truth: a hand head is
FOUND when a kept notehead box's centre lies within 0.6 sp of his box's centre;
SINGLE when only one does; POSITION when ADJUDICATE's position (`notehead_position`
where decided, else GATHER's rounded `notehead_staff_position`) is the line/space
his box centre reads against the hand cell's own staff lines; HALF when the
duration is a half or a dotted half. (27 raw boxes; `q711`/`q712` are two prefill
halves of ONE head that he confirmed unfixed -- both count against the one merged
head.) Before, on `lane-2.70-hollow-half` + main: found 20, single 18, position 19,
half 20 (of 27). Four distinct causes, none of them the hollow reading itself:

1. **A head on a line is a ring with a line through its hole**: two white half-holes,
   one either side. The detector boxes ONE of them (0.58-0.89 sp tall, top or
   bottom edge ON the line, class `noteheadHalfInSpace`), sometimes both.
   14 of 14 on-line heads show it (`proto`: two enclosed holes of like size,
   point-symmetric about the line; 0 of 11 other partial boxes on the page, 0 of
   13 in-space heads, do).
2. **2.42's slot competition was not per head**: `Q.STACKED_HEAD_FIT` groups every
   box on one stem and side; an octave apart (Violoncello e Basso doubling, 3.5 sp)
   the fit calls them ONE slot, and the box with more ink deleted the WHOLE box
   (IoU 0.99-1.0 with Sean's) of the other head. 5 of his 13 in-space heads.
3. **`max(centre, ring)` ink prefers half a ring**: the partial box has the higher
   ring fraction by construction, so the keep choice kept it over the whole head.
4. **Circles**: one rule keeps a box, the next refuses it (2.30 keeps A and
   refuses B; 2.42 then keeps B -- already refused -- and refuses A): both lost.
   4 of his 14 on-line heads lost every box this way.

### 8b. What is built

- GATHER `Q.HEAD_LINE_CUT` (`READERS.CV_HEAD_LINE_CUT`, `gather.head_cut_by_line` /
  `gather_head_line_cut`): a box <= 0.95 sp tall, >= 0.9 sp wide, whose edge is
  within 0.3 sp of a line row, with the MIRROR HOLE in the unerased raster (two
  enclosed holes, areas 0.02-0.45 sp^2 and within 0.4-2.5x of each other, centres
  0.25-1.1 sp apart, common centre within 0.5 sp of the box, a line running past the
  head: the longer side >= 0.75 ink, the shorter >= 0.4). Files the standard head box
  centred on the line; never edits `Q.GLYPH_BOX`. `gather_notehead_positions` files
  the line as the head's position (`from_head_cut`, the detector's own reading rides
  on the row); `gather_notehead_ink` reads the ink on the rebuilt head and adds
  `ink_off_line`, the same windows with the line rows left out.
- ADJUDICATE `head_cut_piece` (one decision per cut head; a whole box keeps it, else
  the best piece, never the last box); 2.42 competes only among boxes on one head
  (overlap or <= 0.15 sp, unless both are implausible as heads), shape (head-
  filling) before ink, and the INK names the class of a black/half pair; 2.30 shape
  before score; the keep/refuse circle broken only where the winner was refused in
  favour of THIS box and this box could be a head.
- `rhythm`: the 2.23 hollow cut 0.5 -> 0.75 (Sean's 222 filled Brahms heads read
  centre >= 0.85, 5th percentile 1.0; Litolff p3 black-class kept heads 207/228
  >= 0.95; his 8 Litolff half notes 0.51-0.72) and `ink_off_line` may decide. **The
  cut was chosen under both floors, not at the tiles -- but his 8 tiles sit between
  0.5 and 0.75 and were looked at before the cut moved; it is not a blind test.**

### 8c. Scorecard (Sean's 27 half heads; the page was also the development page)

| | found | one head | box (IoU>=0.5, detector or rebuilt) | position | half / dotted half |
|---|--:|--:|--:|--:|--:|
| before | 20 | 18 | 15 | 19 | 20 |
| after | **27** | **27** | **27** | **27** | **27** |

14 on a line and 13 in a space, each 27/27 after. **This page is where the
mechanism was found and its thresholds checked, so 27/27 is not an out-of-sample
number; the out-of-sample evidence is 8d-8f.**

### 8d. Population (GATHER+ADJUDICATE small re-gathers, same weights, glyph keys
identical in both arms, base = `b408558e`, arm = `18ba2671`) -- position and duration APART

| | heads | newly kept | newly refused | position moved | duration moved (kept in both) |
|---|--:|--:|--:|--:|--:|
| Brahms pdf 0-1 | 1,491 | 13 | 5 | 1 (11 -> 10, a cut piece) | 0 |
| Litolff pdf 1-3 | 1,286 | 15 | 6 | 2 (both a cut head's, to the line) | 6 |

Brahms: 13 newly kept = Sean's 9 + his whole + 1 tremolo-slash swap (kept junk for
kept junk) + 2 real beamed heads on pdf 1 the old rule refused. Litolff: the 15 are
halves (or the black twin of a head already kept) plus 2 quarters; the 6 refused are
the other box of a head whose twin is now kept. Duration moves on Litolff: 3
quarter -> NARROWED half/black/whole (ink reads hollow; one is a `p` dynamic's bowl
boxed as a head, `glyph/2/0/2/1/12`), 2 narrowed -> narrowed with the hollow
candidates, 1 quarter -> half (`hollow_head_bare_stem`). Black-class kept heads the
ink reads decisively hollow: Litolff p1-3 5 -> 13 of 740, Litolff p6 2 -> 12 of 573,
Brahms 1 -> 1 of 1,007.

### 8e. Sean's 8 Litolff half notes + head-fill tiles 5, 6 (blind, judged 2026-10-09)

`out/2.73/sean-tiles-before-after.txt`. Before: 0 of 8 half (all quarter). After: 3
DECIDED half (#1, #3, #7), 3 NARROWED with half a candidate (#2, #6, #8), 2 still
quarter (#4, #5). Head-fill #5 half (now via the half-class box), #6 still quarter;
#4 (a WHOLE REST boxed as a head) stays quarter -- the control holds: never half.
Why #4 and #5 stay quarter, and #2, #6, #8 stay narrowed: the ink
reads hollow (centre 0.52-0.57, ring gap 0.26-0.33) but the cell has fewer than two
stems so the beam reader abstains `no_stems_to_join`, and the stem-tip reader abstains
`occupied` -- 2.70's bare-stem rule needs the tip MEASURED, so it says cannot tell.
Head-fill #6 (not one of the 8): the ink_net window reads hollow (0.60) but the black box ends short of its stem (`stems_attached` 0), so there is no own stem to test. Sean's rule
("hollow + nothing on the stem = half") is not wired where "nothing on the stem" is
unmeasured; whether an `occupied` tip on a decisively hollow head may count as
nothing is a question for him -- NOT changed here.

### 8f. Controls

- Engraved Beethoven fixture p0-2 (`out/2.73/engraved-control.txt`): 371 note glyphs,
  0 `head_line_cut` rows, 0 black-class heads read hollow (0 of 251), and NOT ONE
  refusal, position or duration differs between arms; the positive control: 103 of 103
  half-class heads read hollow.
- `head_cut_by_line`: in-space hollow head (one hole), black head with a line through
  it, head-sized box, box edge off the line, two holes with no line past the head
  (a slash), a chord second -- each returns None; 0 of 11 other partial boxes on
  Brahms pdf 0 carry a row. On Litolff pdf 1-3 exactly 2 rows are filed, both on
  black-class kept boxes (`glyph/1/0/7/1/1` an eighth on a ledger line, `glyph/2/1/4/14/6`
  a quarter on a staff line) and both are real heads cut by a line on the crop: their positions move to the line (9 -> 8, 1 -> 2),
  the whole of Litolff's "position moved" above. Their durations did not move.
- Whole-rest box (head-fill #4) stays quarter; a chord's neighbour a second away is
  not merged (`TestOneHeadOneBox`); a refused winner no longer shields a beam sliver
  boxed as a head (an earlier version of this change did: Brahms `0/0/10/1/16`, Litolff
  `2/0/8/13/9`; caught on the crops, fixed, test pinned).

### 8g. Red -> green, gates

`tools/omr/tests/test_staged_head_line_cut_2_73.py` (37): against the unrepaired tree
(HEAD before the commit, extracted by `git archive`) 29 FAIL, 8 pass (the controls).
`test_staged_duration.py`'s "not decisive" fixture moved 0.6 -> 0.85 with the cut.
`pytest -m "not slow" tools/omr/tests`: 6,475 passed, 11 skipped, 0 failed.
`staged.check` TOTAL 192 (unchanged; `wiring`, `inventory`, `reach`, `capture` ok).

### 8h. Not done, found

- `Q.GLYPH_BOX` stays the detector's partial box; downstream consumers that read
  the box (stem association, the 2.70 stem test) still see half a head. The rebuilt
  head is on `Q.HEAD_LINE_CUT`.
- Black-class heads with a decisive hollow reading on a merged plate can be a letter
  or a blob (`glyph/2/0/2/1/12`): the narrowing keeps black among the candidates.
- 10 print crops of newly decided heads Sean has not judged: `out/print/2.73/`.


## Sec.9. ROADMAP 2.73 follow-up -- what stood in the stem-tip window (coordinator, after Sean judged the 10 crops)

Sean on the 10 crops (`out/print/2.73`): 1-6 half, 7-8 eighth, 9 half, 10 NOT A NOTE (a
dynamic `p`); none worse than main. Open: the 2.70 tiles #4, #5 (and #2, #6) stop at 2.70's
"stem tip MEASURED" test because the tip reads `occupied`. The brief said a staff/ledger
line sits in the tip window.

### 9a. What the record says (`out/2.73/`, lane scratch `tipwhy.py`; not a guess)

The occupants of the 2.70 tiles' tip windows, off the record's own boxes (canonical px,
staff space 100):
- #4 (cell 6/1/11/4): an `arpeggiato` detection that IS the stem's own ink -- its box ends
  1 px inside the window. No line.
- #5 (6/1/6/11): the head's own doubled box ends 1 px inside the window. No line.
- #2, #6 (6/0/4/2, 6/0/4/1): a neighbouring head's box ends 1-5 px inside the window; #6's
  bottom window also holds two `ledgerLine` boxes.
- #8 (Litolff p3 3/1/6/0): a real `beam_stroke` overlapping the window by 17 px, and key-
  signature boxes: a real occupant.
So the cause in 3 of the 4 checked is a box that TOUCHES the window, not a line in it. No
occupant was a slur/tie (a wide arc box is already cut by the 4-space width cut), so
"a decided arc is not a flag" was NOT built: nothing here would use it.

### 9b. What changed (GATHER `Q.STEM_TIP_INK`; the hook counter `stem_tip_hooks` untouched)

1. A detection box explains ink in the tip window only if it overlaps it by MORE than
   0.1 staff space in both axes (`STEM_TIP_BLOCKER_TOLERANCE_SPACES`, detector box edges
   being good to about that). A box that really overlaps still abstains `occupied`.
2. The rows a horizontal line stands on at the tip's x -- ink in both probes just beyond the
   two bands, which a flag hanging from ONE side never reaches -- are left out of both
   bands (`line_rows_left_out`); a window that is mostly lines is declined.
3. **Rejected, with the crops that say so:** the first build also dropped `ledgerLine`
   detections from the blockers. 3 of 3 newly FOUND tips on Brahms p0 and one on Litolff
   (`0/0/9/2,4,5`, `2/1/9/13`) were short thick ledger lines, no longer than the two bands,
   read as flags -- neither excluded as line rows nor stopped by the left guard. The
   boxes stay blockers (test pinned). Brahms p0 with the final code: 0 new found rows, tips
   measured bare 221 -> 288, `occupied` 495 -> 428.

### 9c. Re-score (follow-up alone = the merge commit `d5e2b5f8` vs `56ee7c50`, same weights)

| | before the follow-up | after |
|---|---|---|
| Sean's 8 Litolff half notes | 3 decided half, 3 narrowed, 2 quarter | **6 decided half (#1,#2,#3,#4,#5,#7), 2 narrowed (#6, #8)** |
| head-fill #4, a WHOLE REST boxed as a head | quarter | quarter (control holds) |
| head-fill #5 / #6 | half / quarter | half / quarter |
| his 27 hand heads (found / one head / box / position / half) | 27 / 27 / 27 / 27 / 27 | 27 / 27 / 27 / 27 / 27 |
| the 10 crops against Sean (1-6 half, 7-8 eighth, 9 half, 10 not a note) | 1-6 half, 7-8 narrowed, 9 narrowed, 10 narrowed | 1-6 half, 7-8 narrowed, **9 half**, 10 narrowed |
| engraved control | 0 cut rows, 0/251 black read hollow | the same; no verdict differs (371 heads) |

Follow-up alone, population: Brahms pdf 0-1 0 heads change; Litolff p1-3 2 move
(`2/0/7/6/1` quarter -> half, `2/1/3/11/5` narrowed -> half; both real half notes on the crop);
Litolff p6 3 move (Sean's #2, #4, #5). No head is newly kept or refused, no position moves.
Stem-tip rows (count pages): Litolff found 30 -> 34, bare 644 -> 924, `occupied`
1,704 -> 1,419; Brahms found 27 -> 28, bare 815 -> 1,001, `occupied` 1,458 -> 1,271.

Still not decided: #6 (its tips now read bare, but the cell holds two beam strokes and the
2.70 rule's other gate keeps it narrowed -- not the tip) and #8 (a real beam stroke in its
window -- rule 8). Crops #7, #8 (eighths) stay narrowed `beam_certain_not_joined`; #10 (the `p`)
stays narrowed -- that is the dynamic-owner lane's, not this one's.

### 9d. Merge with main

`origin/main` (2.74 beams, 2.69 hooks + dot, 2.68) merged into this branch: no conflict, none in
`rhythm.py` (git merged it cleanly; 204 duration/tip/hook/2.73 tests pass on the merge).

## Sec.10. ROADMAP 2.71 -- the tremolo slash is its own mark (2026-10-09)

Path: STAGED, GATHER + ADJUDICATE only. Branch `lane-2.71-trem-slash`, off main
`0a06e5c2`. Sean, 2026-10-09 (DECISIONS): *"The trem slash is very different from a
beam. Beams have to be connected to other notes - slashes never are. The hook of a flag
is very different from a slash. The slash crosses both sides of the stem with a thick
line at an angle."* / *"A hollow note with nothing on the stem is always a half note."*

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond those lines:** the
numbers (`gather.STEM_SLASH_*`). A slash is read when a stroke followed outward from a
stem's edge on both sides reaches >= 0.35 spaces each way, lies on one straight line
(residual <= 0.15 spaces), leans >= 12 degrees, is >= 1.4 staff-line thicknesses thick
across, and neither runs on to another stem nor stands on a head's end. Set on two plates
(Litolff p1-3 + p6, Brahms p0-1). Falsified by a print-confirmed slash it refuses
(a level one; a very short one) or a stroke it passes that Sean reads as something else.
Every crop below is my eye, not Sean's.

### 7.1 What a slash did on today's tree (a / b / c)

(a) **Became a beam level?** Not on these pages: 2.74's one-stem / thin tests already
refuse the slash strokes the CV reader boxes (zero duration verdicts on Litolff p6 or p1-3
count a slash as a level). The one place a slash-footprint stroke still reached the beam
tier is Brahms p1 cell 1/0/4/3 (4 narrowed heads, see 7.4), and its verdicts did not change.
Where it DID leak was the stem-tip reader: Litolff p6 cell 6/1/3/1's top tip read
`found=True` (`head_at_this_end`, ink 0.50 right / 0.18 left) off the slash -- a flag-shaped
reading the 2.69 narrowing would have turned into `eighth|...` -- and now reads `found=False`.
(b) **Boxed as another glyph?** Yes, three ways. A **notehead** box on the slash, kept as a
head: Litolff p6 `glyph/6/1/11/3/3` (black, narrowed `beam_discounted_uncertain`), Litolff p2-3
four more (+1 refused only as a duplicate), Brahms p0 two -- 2.49's three-test refusal had
missed these (its split read them round). A **rest** box on the stem: Litolff p6
`glyph/6/1/11/5/2` (`restQuarter`, 4.5 spaces tall, decided a quarter REST).
(c) **Blocked the half?** The rest box is the case that matters (7.3): it replaced the note,
so the hollow head the ink shows has no box and no decision at all. A slash over a hollow head
that IS boxed did not block the half: 2.43's hollow zeroing already drops beam levels there.

### 7.2 What was built

GATHER `Q.STEM_SLASH` (`gather.stem_slashes`, `_observe_stem_slashes`, `READERS.CV_STEM_SLASH`;
one row per `Q.STEM`, value = number of slashes, a READ zero where none; `detail.strokes` lists
every stroke that crossed the stem with its `reason` -- `None` for a slash, else `one_sided`,
`not_at_an_angle`, `too_thin`, `not_straight`, `joins_another_stem`, `runs_on`, `at_a_head`,
`too_short` -- its angle, thickness ratio, reach, footprint box and centre line, plus
`head_at_end` and `bare_stem_spaces`). The ONE place a slash is named; four readers consume it:
* **hook / tip reader** (`gather._observe_stem_tip_ink`, now handed the raster with the slash
  blanked -- `blank_slashes`): a slash is not a hook, and a real hook beside one is still
  counted (unit-tested both ways; 2.69's own both-sides refusal stays as the fallback);
* **beam path** (`rhythm._not_a_slash`, a tier before the 2.25b/2.74 guards): a stroke inside a
  read slash's footprint is not a level and, being a mark of another kind and not an absence,
  never narrows the head (`beams_slash` in the verdict detail);
* **rest** (`family_precision._rest_on_a_slashed_stem_refusal`, `rest_is_a_slashed_stem`, after
  `rest_has_a_stem` so no standing reason changes): a rest box on a slashed stem AND taller
  than 3.8 spaces is the note's stem;
* **notehead** (`notehead_precision._slash_read_under_box`, the second witness inside
  `_tremolo_slash_crosses_stem` and `_is_tremolo_slash`): a notehead-classed box holding most of
  a read slash's centre line, on the shaft, is the slash.
Shared helpers edited, named for the fence: `gather._observe_stem_tip_ink` (one keyword + one
line; `lane-rhythm-leftovers`/2.73 also touch the tip test), `rhythm.adjudicate_duration` (one
tier after the ledger-line tier, one detail key), `notehead_precision._tremolo_slash_crosses_stem`
/ `_is_tremolo_slash` (2.73's `stacked_head_duplicate` is the next function down and is
untouched).

### 7.3 The missing head (what would recover it)

Litolff p6 tile 3 is the case where nothing is left to adjudicate: the detector's only boxes
are the stem+slash as `restQuarter` and a tie; the half note's ring (hollow, on the bottom
line, left of the stem) has no box. `Q.STEM_SLASH` now records `head_at_end` per stem: a
slashed stem with no head box at either end is the population. Litolff p6: 1 of 7 (this one);
Litolff p1-3: 2 of 13 (3/0/9/0 and 3/0/10/4 -- the only box there was the slash itself, now
refused); Brahms p0-1: 5 of 20, of which two are real quarter rests and two stroke crossings of
a barline-like stem (7.4). **Recovery, NOT built (never invent a head; no head in the record
to file a value against):** a GATHER reader that files a head from ink at the stem's head end
-- 2.73's line-cut-head rebuild is the same shape (`lane-2.73-line-cut-heads`, not in main) --
then ADJUDICATE reads the fill off that ink and the half rule (2.70) takes it. The rest refusal
is the half of this that needed no new reader: the bar no longer holds a silence where a note
stands, it holds an unread mark.

### 7.4 Population (base = main `0a06e5c2` on a clean copy; arm = this branch; the small
re-gathers, `--through adjudicate`)

| page(s) | stems read | slashes read | notehead boxes refused (new) | rests refused (new) | duration verdicts changed |
|---|---|---|---|---|---|
| Litolff p6 | 618 | 7 | 1 | 1 | 0 |
| Litolff p1-3 | 1,189 | 13 | 5 (4 kept, 1 was a duplicate) | 0 | 0 |
| Brahms p0-1 | 1,150 | 20 | 2 | 0 | 0 |

Stem-tip rows that flipped `found` or the hook reading: 1 (p6 cell 6/1/3/1, True -> False), the
rest only density. **No duration verdict moved anywhere**, nor any other family. The cost:
the reader passes some strokes that are not slashes -- two real Brahms p1 quarter rests (their
zigzag crosses the CV "stem" exactly as a slash does; kept rests by the rest rule's height
test, measured median 2.8 spaces against the 4.5 of tile 3) and one slur/barline crossing
(Brahms p1 cell 1/0/4/3, 4 clipped heads whose verdicts were already `beam_discounted_uncertain`
and did not change). Not eye-checked: Brahms cells 0/0/10/0 (angle 50) and 1/0/3/4 (angle 13,
thickness 5.3 lines).

### 7.5 Measured and refused

* **A "how long is the plain thin stretch of the stem" test** to separate a quarter rest from a
  slashed stem (`bare_stem_spaces`, still recorded): the real Litolff slashes read 0.57-1.08,
  the two Brahms rests 0.95 and 1.06. The populations overlap; built as a reader refusal,
  it took four of seven real slashes on p6 and the tile 3 rest with it (run, saw it, removed).
  The rest rule asks the box's own height instead.
* **A bounding-rectangle test of "the box covers the slash"** (first build): an angled stroke's
  rectangle is mostly paper and the detector's box held 64% of it; the stroke's centre line
  holds the right share (the missed p6 `11/3/3` -> refused).
* **A head box at a stem end explaining the stroke there**: with boxes at BOTH ends the one on the
  slash is the suspect (a stem has its head at one end; the detector boxes slashes as heads), so
  `at_a_head` applies only where the other end has no head box.

### 7.6 Tests, gates

`tools/omr/tests/test_staged_stem_slash.py` (38). RED first: written before any implementation,
26 of 33 failed on the unrepaired tree (the 7 that passed are controls that cannot fail there:
a bare stem reads nothing, a half note without a slash is unchanged, ...). Controls in the
same class: a real slash read; a one-hook flag not a slash (and still counted beside one); a
real two-note beam stays a beam; a plain half note unchanged; a staccato dot / accent beside a
stem not a slash; a chord head at the stem end not a slash; a quarter-rest-height box with a
slash row stays a rest; a real head at the stem end beside a slash kept.
Crops: `out/print/2.71/` (`tile_01..09.png`, `manifest.json`, `render.py`) -- blind, subject
bracketed, nothing of ours drawn; by my eye all 9 brackets sit on a slash at a stem's tip
(tile 5 is tile 3's stem+slash box, the one the rest rule refuses).

## Sec.11. 2.78 one stem, one value — Phase 1 (2026-10-09)

Path: STAGED, GATHER + ADJUDICATE only. Branch `lane-2.78-one-stem-one-value`, base main
`3ec53272` + the docs-only `f027c8e7` (the brief said the base already held it; it did not,
so it was fast-forwarded in). Both small re-gathers are on that tree, clean (`dirty False`,
commit `f027c8e7`). **No product code. Nothing is built, nothing is judged yet: the tiles in
`out/print/2.78-review/` are waiting for Sean.**

**The rule (Sean, DECISIONS 2026-10-09, "no exceptions"):** every notehead on ONE stem has the
SAME written value; a stem carrying a hollow head cannot also carry a filled one; a filled
'head' box on a half note's stem is not a note (a slash or a misreading). **CONVENTION ASSUMED /
WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond that line:** (i) that "value" includes DOTS (a
dotted chord is dotted on every head) -- the brief says so, DECISIONS says "the same written
value"; falsified by Sean reading a tile where one head of a chord is dotted and the other is
not (tiles 3 and 13 ask; by my eye the print shows a dot beside BOTH heads in tile 13 and in
the dotted chords of tiles 5 and 12, and tile 3's second box looks like a slash at the stem's
tip, not a head);
(ii) that the repair direction for a fill conflict is "the filled box is the non-note" in every
case, not only the slash ones (tiles 2, 6, 7, 11 ask; **tile 9 is the counter-case**: by my
eye its DECIDED hollow whole-class box is a smeared black blob at the top of a beamed stem, so
there the hollow reading is the wrong one, and tile 14 looks like one half note carrying a
duplicate filled box).

### 11.1 The join: what the record says about "these heads share a stem"

**No verdict says it. That is the finding.** What exists:

| where | what it is | why it is not the join |
|---|---|---|
| `Q.STEM` (GATHER, one row per CV stem, `[x, y, w, h]` canonical, filed on the CELL) | the stems | says nothing about heads |
| `Q.NOTEHEAD_STEM_CROSS_INK.detail.stem` (GATHER, per head) | the stem row a head was split against | the FIRST overlapping row only; no row where the head leaves no area on one side; a measurement, never a verdict |
| `Q.STACKED_HEAD_FIT.detail.stem` (GATHER, per head) | stem + side | only heads on the SAME side of a stem |
| `rhythm._stems_on`, `notehead_precision._stem_rows_on`, `gather._stacked_boxes_overlap` | a bare box-overlap test, no tolerance, recomputed privately in each reader | three copies, never filed |
| `Q.STEM_DIRECTION` (ADJUDICATE, per head) | which way the stem points, decided "from the whole group on the stem" | its `detail.heads_on_stem` is the number of noteheads in the whole CELL (the code passes `len(_heads_in(ev, cell))`; it reads 5 on both heads of the 2-head stem in `cell/3/0/5/2`, a cell that holds 5 noteheads), not on the stem: mis-named |
| `Q.EVENT` (ADJUDICATE, per cell) | chord = heads within an x tolerance, blocked only by an explicit opposite stem direction | not stems: of the 90 / 93 stem groups below, 12 / 6 are split across events, and 74 of 154 / 98 of 185 multi-head events stand on no shared stem |
| `export._events` -> `voicing.group_chords_in_measure` (EXPORT) | a chord's duration is the MODE of its heads' durations, `Counter.most_common(1)` | on a two-head disagreement that is whichever head came first in x order: an argmax over a disagreement (rule 8), and it is where the stem rule is "enforced" today |

This probe uses `rhythm._boxes_overlap` between each kept notehead's `Q.GLYPH_BOX` and the
`Q.STEM` rows of its own cell (the join ADJUDICATE's duration decision actually uses),
cross-checked against the filed `cross_ink` stem: 414 of 414 (Litolff) and 332 of 332 (Brahms)
agree -- but that is the same test written twice, so it is a consistency check, not evidence.
Looseness of the join, measured: 109 of 765 (Litolff) and 48 of 871 (Brahms) stemmed heads
overlap 2+ stem rows (12 / 5 stem groups are the same head-set from duplicate rows, counted
once); 7 of 187 / 5 of 186 group heads have the stem's centre in the MIDDLE half of the head's
width, where a real stem is flush with a side (CLAUDE.md §10). 223 / 224 kept heads have no
stem row at all (whole notes, missed stems); the rule cannot touch them.

### 11.2 Population (small re-gathers, `--through adjudicate`, `acceptance_quick`)

A HEAD is a notehead-family box ADJUDICATE kept, narrowed or abstained (refused / given-away
boxes are not heads). Litolff pages 1-3 (movement start through the count page, pdf 3): 988
heads (933 decided + 55 narrowed, 0 abstained; 192 refused, 106 given away). Brahms pages 0-1
(count page pdf 1): 1,095 heads (922 + 173 narrowed, 0 abstained; 339 refused, 57 given away).

| stems carrying 2+ heads | Litolff all (p3 only) | Brahms all (p1 only) | both, all |
|---|---|---|---|
| **multi-head stems** | **90 (42)** | **93 (36)** | **183** |
| agree: every head decided, one value (the CONTROL) | 76 (34) | 66 (27) | 142 |
| (a) decided heads disagree on FILL (hollow vs filled) | 5 (2) | 0 (0) | 5 |
| (b) decided heads disagree on DOTS | 0 (0) | 2 (0) | 2 |
| (c) decided heads agree, another head NARROWED / ABSTAINED | 1 (0) | 4 (2) | 5 |
| &nbsp;&nbsp;c1 the narrowing still holds the decided value | 0 | 0 | 0 |
| &nbsp;&nbsp;c2 the narrowing EXCLUDES the decided value (a hidden contradiction) | 1 (0) | 4 (2) | 5 |
| &nbsp;&nbsp;c3 abstained (unread) | 0 | 0 | 0 |
| (d) anything else | 8 (6) | 21 (7) | 29 |
| &nbsp;&nbsp;d1a whole-class box + half-class box (fill, dots equal) | 0 | 1 (1) | 1 |
| &nbsp;&nbsp;d1b decided heads differ only in beam/flag level | 6 (6) | 2 (0) | 8 |
| &nbsp;&nbsp;d2 no head decided: both narrowed IDENTICALLY | 2 (0) | 18 (6) | 20 |
| stems with >= 1 head UNREAD (abstained) | 0 | 0 | 0 |

Stems the rule would flag as a CONTRADICTION (a + b + c2): **6 of 90, 6 of 93, 12 of 183
(6.6 %)**; with the level / class disagreements (d1): 21 of 183. d2 is agreement in ignorance:
one narrowed fact held twice. Heads on a multi-head stem: 187 of 988 (Litolff), 186 of 1,095
(Brahms) head-memberships. Everything is from ONE count-page range per document; the pages
differ (Litolff p3: a 2, d1b 6, no c; Brahms p1: c2 2, d1a 1, d2 6, no a or b), so the split
between causes is not stable across plates and n is small.

**Two populations are empty, and an empty population is not a pass.** (c1) and (c3) are zero
on both plates: no narrowing on either plate still holds a decided mate's value, and no head is
abstained (`duration` abstains only on `no_notehead`/`unknown_head`/rests). Nothing here can say
whether a "transfer the stem's value to an unread head" step is right. (b) is zero on Litolff
because **no multi-head stem on Litolff p1-3 carries a dot at all** (0 of 90); on Brahms 27 of
93 do, and 2 disagree.

Mechanism, as far as the record shows (my reading of the verdict `detail`, not Sean's):
* (a) + (c2) -- 10 stems, each a hollow head decided beside a filled box (5 + 5; the filled box
  is DECIDED in (a) and NARROWED eighth|quarter in (c2)). Per filled box, from the record:
  6 of 10 have the stem's centre in the middle half of the box (0.49-0.67 of its width; a real
  head has its stem flush with a side, §10), 2 are small boxes at the edge (1.14 x 0.90 and
  1.00 x 0.81 sp), and **2 look like ordinary heads standing at the stem's edge** (Litolff
  `cell/2/1/8/2` 1.6 x 1.45 sp at 0.94; Brahms `cell/1/0/0/4` 1.38 x 1.33 at 0.08, where the
  DECIDED box beside it is a 2.68 sp wide whole-class box). So in those 2 the hollow reading,
  not the filled one, may be the wrong one: Sean's tiles 14 and 9 decide whether the rule's
  direction ("the filled box is the non-note") holds there. By my eye tile 9 is exactly that
  counter-case: the stem carries a beam, and a hollow head is never beamed (2.43), so a hollow
  reading on that stem is the misreading.
* (b) -- 2 stems: the undotted half box is 1.49 x 0.70 sp (a half-height box, 5.0 head-heights
  from the stem end) and 1.04 x 1.01 sp (narrower than a head).
* A `Q.STEM_SLASH` row on the stem is a weak separator by itself: it stands on 5 of the 12
  contradiction stems (a + b + c2) against 5 of the 142 agreeing ones (those agree because 2.71
  already refused the slash box); it misses 7 of 12.
* (d1b) -- the same stem, two readings of its beams: `glyph/3/0/5/2/0` counts 2 strokes
  (`beams_by_stem` 2, `beams_far_side` 0) and `/3` counts 1 (`beams_by_stem` 1, `beams_far_side`
  1), both with `stems_attached` 1 and the same `beam_side` up. Inferred from those detail
  fields, not traced further: each head re-derives the level from the strokes on its own side
  of ITS OWN position along the stem, while the level is a property of the STEM's tip. Same
  numbers on `3/0/7/6` (2 strokes vs 1, `beams_far_side` 0 vs 2).
* (b) -- Brahms `cell/0/0/5/2`: a dotted half and an undotted half on one stem; by my eye the
  print shows a dot beside both heads (tile 13).

### 11.3 Controls

* **Reach first**: 90 and 93 multi-head stems -- not dead. Rule 8 / rule 7's empty-population
  warning applies to (b) on Litolff, (c1), (c3), above.
* **The join has a negative control that can fail**: sliding every stem box 10 head-widths right
  takes the multi-head stems 90 -> 0 (Litolff) and 93 -> 8 (Brahms; the slid stem lands on a
  neighbouring chord on the denser plate); sliding 12 head-heights down takes both to 0.
* **The "agree" control is not one value**: Litolff 19 beamed eighths, 28 quarters, 29 halves;
  Brahms 47 eighths, 9 dotted quarters, 5 dotted halves, 2 quarters, 1 each of sixteenth, half,
  whole. Not all one class.
* **Not controls**: the page-box affine residual (0.00 everywhere) is a computation -- GATHER
  derives each page box from the canonical one by the same affine; "heads of a stem share a
  column" (90 of 90, 93 of 93) follows from the join. The control that can fail on the page is
  the frame control below.
* **Frame control on the tiles** (`readout.frame_control`, mean ink on the staff lines minus half
  a space off them, on the same deskewed raster the boxes live in): Litolff p3 +116.7, p2
  +108.8; Brahms p0 +214.1, p1 +159.2; the same renders rolled half a space down read -117.4,
  -112.8, -212.2, -158.5. Litolff's deskew is 0.25 degrees, which is why the tiles are cut from
  `render_page(...).rgb` and not re-rendered from the PDF as 2.71's were.
* **Who says it's right**: nobody yet. Every cause above is my reading of the record; the tiles
  are Sean's to judge.

### 11.4 Tiles for Sean: `out/print/2.78-review/` (14, blind, order shuffled)

Each is the page at 600 dpi, x2, a red corner bracket on the stem and every head on it, nothing
else drawn, one question: *What note value is printed on this stem, and is every mark on it a
notehead?* `manifest.json` holds our readings per head and the cause; it is not shown to the
judge. Spread: 4 fill (a), 4 hollow-vs-narrowed (c2), 2 dots (b), 1 beam level (d1b), 1 whole
vs half class (d1a), and **2 controls where every head agrees** (a half chord with a slash row
that 2.71 already handles, and a dotted-half chord, each a neighbour of a conflict stem), so a
judge who calls everything a conflict is caught. Selection spec: `out/2.78/tile-selection.json`.
Not covered, deliberately: d2 (no contradiction) and (c1)/(c3) (no population).

### 11.5 Proposal: where the rule belongs (NOT built; waits for Sean's tiles)

CLAUDE.md §4a, does the answer FOLLOW or is it BEST?
* **That a stem has one value FOLLOWS** -- it is the convention, Sean says no exceptions, so a
  stem whose heads hold two values is a contradiction in every case. Detecting it is forced.
  That is not INFER's: INFER may only collapse a NARROWED verdict to its own candidates and
  never overturns a DECIDED one, and (a), (b), (d1) are DECIDED against DECIDED.
* **Which head is wrong does NOT follow.** The convention says one reading is wrong, not which.
  Where the evidence cannot say, rule 8: narrow or abstain, never pick, and never the exporter's
  mode vote.

So, in order:
1. **ADJUDICATE, a connection (rule 6): file the join once.** One per-head verdict (name left
   open; `Q.HEAD_STEM` is the shape `Q.STEM_DIRECTION` already has, filed on the head, derived
   from the group): DECIDED where exactly one distinct stem row is flush with a side of the head,
   NARROWED where two distinct stems reach it, ABSTAINED where none. It replaces the three
   private box-overlap copies, and it is where the duplicate-row and mid-body cases (11.1) are
   decided instead of counted.
2. **ADJUDICATE, a new decision ordered after `duration` and before `event`, in its own file**
   (so it touches none of the fenced functions in `rhythm.py` / `gather.py` / `ownership.py`),
   filing its own per-stem value; per component:
   * all heads decided and equal -> files nothing new (the control, 142 of 183);
   * a narrowing whose candidates still hold the decided mates' value, or narrowings with ONE
     common candidate -> that FOLLOWS (an intersection), so it is the stem's DECIDED value.
     Population today: 0, so it cannot be priced;
   * **a contradiction (a, b, c2, d1) -> never decided by a vote.** Fill: Sean's ruling names the
     filled box as the non-note, but the refusal (`notehead_is_not_a_notehead`) may fire only
     where a per-box witness already on the record agrees -- candidates: a `Q.STEM_SLASH` row on
     the stem, the stem through the middle of the box, a box smaller than a head, off the stem
     end -- and their separating power is exactly what Sean's tiles measure (the slash row alone
     misses 7 of 12). The witnesses can also point the OTHER way: a beam joined to the stem
     rules out a hollow head (2.43), which is the reading to refuse on tile 9 by my eye. So the
     direction is per-box evidence; whether Sean's "filled box on a hollow stem" may also stand
     alone as the direction when the evidence is silent is the question tiles 2, 6, 7, 11 put to
     him, not yet a default. Where no witness holds: both readings stay as a NARROWING and the stem is
     `stem_value_conflict`, which EXPORT must count and hold out (the 2.8 mechanism), not write;
   * dots: a decided augmentation dot (`Q.DOT_ROLE`) read for any head of the stem is the
     chord's, if Sean's reading (i) holds; else narrow;
   * levels (d1b): one count per STEM from the strokes joined to that stem (`Q.BEAM_STEM_JOIN`),
     not a recount per head position; disagreement narrows.
3. **EVALUATE / EXPORT only consume it**: `reconcile_duration` must run after the stem step (it
   changes one note to land a bar; on a chord that would put two values on one stem), and
   `export._events` stops mode-voting a stem it has a `stem_value_conflict` for.

It goes in ADJUDICATE rather than EVALUATE because Sean's 2026-09-30 rule is that every test is
GATHER + ADJUDICATE only, and a stem rule that exists only at EVALUATE cannot be measured the way
this lane is measured. The one thing that does need a stage past ADJUDICATE is the consumers (3).

Open for Sean, one line each, on the tiles: is the filled box on a hollow stem the non-note in
EVERY case (not only the slash)? is a dotted chord's dot on every head? does a stem with two
beam levels read as the higher or is it a misread of one head?

### 11.6 Not done / limits

No product code, no flag, no test. The records are 113 MB each and are not committed
(`/private/.../scratchpad/l278-quick-{lit,brahms}`, regenerable: `python3 -m
tools.omr.acceptance_quick --doc <id> --out-root <dir>`, 349 s and 713 s). `check` N before
193 (`out/2.78/check-before.txt`). One count page per plate; c1, c3 and (b)-on-Litolff are empty.

Reproduce (from the repo root, records as above):
`python3 benchmarks/omr-head-fill-2026-09/probe/l278_population.py REC.json --count-page N
--json out.json`; tiles:
`python3 benchmarks/omr-head-fill-2026-09/probe/l278_tiles.py --record lit=REC --pop lit=out.json
... --select benchmarks/omr-head-fill-2026-09/out/2.78/tile-selection.json --out out/print/2.78-review`.
Outputs: `out/2.78/population-{litolff-p1-3,brahms-p0-1}.{txt,json}`.

## Sec.12. 2.78 one stem, one value — Phase 2 (2026-10-09)

Path: STAGED. Measurement is GATHER + ADJUDICATE (CLAUDE.md §6b); the one EVALUATE rule below is priced by a REACH print only, never
scored. Branch `lane-2.78-one-stem-one-value`, off main with the Phase 1 branch (Sean's answers `102b92bc`) merged. Built on Sean's ruling
on the 14 blind tiles (DECISIONS, 2026-10-09): the value belongs to the STEM; it is read from the stem's own evidence (beams and flags, the
hollow heads, the dots); a head that disagrees takes the stem's value; a box is refused ONLY with a per-box witness (a slash crossing it, or
a duplicate of another head at the same position), never by fill alone. **Not merged.**

**RULE, CONFIRMED (Sean, DECISIONS 2026-10-09): *"Whole notes never have stems."*** (tiles 5 and 9.) A box on a stem is therefore never a
whole note: a whole-class box standing on a shared stem casts no vote for the stem's base or levels and takes the stem's value, and a whole
VALUE is not among the values a stem can have (it is dropped from a narrowing). It was an assumption until the coordinator relayed Sean's
answer; it is a rule in the code now, with no switch. Tile 9 is the case it decides, and the test holds a control that can fail: with the
rule's predicate removed the same stem is decided a half.

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED** (two, each a documented rule in the code, both put to Sean on the new tiles):

1. *A stem's beam level is what the head NEAREST ITS TIP reads* (tile 1: one head a 16th, the other an eighth, Sean: eighth). A head far from
   the tip also sees strokes BETWEEN the heads, which are not beams. A physical argument with ONE judged case behind it. The same pattern
   moves the beam level of 59 heads in the four records measured (58 down, 1 up: `out/2.78/p2-level-changes.txt`), and new tiles 5, 6, 7, 9
   and 10 ask. Falsified by a stem where the tip-nearest head's count is wrong and the far head's right.
2. *On a hollow stem, a dot read for a decided FILLED box is not the stem's* (a filled box on a hollow stem is the slash or a duplicate in
   6 of Sean's 6 non-note cases; a dot near it belongs to something else). Not judged; only the hollow heads' and whole-class boxes' dots
   count there. Falsified by a dotted hollow chord whose only dot was read on a filled box. New tiles 4 and 12 ask about dots.

### 12.1 Two readings of Sean's answers I could not take, and why it changes nothing built

DECISIONS says the filled box is a real half note on tiles 11 and 7. The print says otherwise, by my eye (not Sean's): on tile 11 (and its
stated twin, tile 10) the black box is the thick black blob at the stem's TIP, and the second half note is a hollow head mid-stem with the
slash through it that has NO box at all; on tile 7 the black box is the blob at the tip and "2 half notes" are the two stacked hollow heads
at the bottom, which the detector boxed as ONE 2.04-space-tall box. The count the answer gives (2 notes) equals the number of boxes only by
coincidence. Nothing built depends on it: the stem decision files a value and refuses nothing, so a filled box without a witness is kept and
takes the stem's half either way (the T11-style control in the tests asserts exactly that). **But see 12.4: the slash fix refuses tile 7's
black box, which the brief's list of expected refusals (tiles 2, 3, 4, 6, 8, 14) did not include. That is the one place this reading
matters, and it is Sean's to settle.**

### 12.2 What was built

* **`Q.HEAD_STEM`** (ADJUDICATE, `adjudicators/stem_value.py`, after `Q.DURATION` in `adjudicate.ORDER`): the head-to-stem join, filed once on
  each notehead (value: the stem row id). Reasons: `one_stem`; `stem_by_reach` (two stems touch it, only one reaches 0.8 of a staff space
  past the head — a fragment does not); `stem_by_side` (the stem on the side CLAUDE.md §10 puts it: up → the head's right, down → its left,
  96 of 96, read from the decided `Q.STEM_DIRECTION`); `stem_by_flush`; `two_stems` NARROWED when none of these settles it; `no_stem`
  ABSTAINED. A refused box and another staff's relocated copy are still JOINED (it is geometry) but are not members of the value.
* **`Q.STEM_VALUE`** (same file): the stem's written value as it applies to that head, `{beats, written, dots, beam_levels, head_fill,
  stem}`. Base from the hollow heads (a hollow head is a half; a hollow head under a certain beam narrows, 2.43), levels from the head
  nearest the tip, dots from the heads that may carry them. DECIDED (`stem_agrees` when the head already says it,
  `stem_value_from_evidence` when it differs); NARROWED `stem_levels_unread` where the stem's own evidence cannot say; ABSTAINED
  `lone_head`, `ambiguous_stem`, `no_stem`, `not_a_member`. It never overturns a head's own `Q.DURATION` and never refuses a box.
* **`consequences.share_stem_value`** (EVALUATE, one rule): where the stem value is DECIDED and a head's standing duration differs (or is
  narrowed), the duration is restated to the stem's, once, `single_pass`, ranked above `Q.METER` in `evaluate.DOWNHILL` so it runs before
  every meter rule and the bar sums read heads that agree. Without it `Q.STEM_VALUE` is producer-only and `check` N is 194 (see 12.8). A
  NARROWED stem value fires nothing.
* **`gather.py`, the tremolo-slash reader** (12.5): two narrow fixes that give `Q.STEM_SLASH` back three real slashes it missed, two of them on
  tiles 7 and 8.
* `readout._hv` renders the new quantity; `test_stage_review_evidence.STAGES_THAT_SEE_A_HUMAN_BOX` names the two new quantities.

### 12.3 The score on Sean's 14 (replay of the fresh GATHER, final tree, `p2-armB_*.txt`; value read off `Q.STEM_VALUE`)

The control comes first: the replay reproduces the record's own verdicts for what the rule reads (duration 1807/1807, stem direction
1286/1286, the two notehead refusals 1286/1286, owner 1135/1135 on Litolff p3; same on Brahms p1), and **the control can fail**: with one
GATHER row perturbed it reports "CONTROL FAILED: 5 verdicts differ" and exits 1 (`out/2.78/p2-break-control.txt`).

| tile | doc | Sean's value | our stem value | verdict |
|---|---|---|---|---|
| T1 | Litolff | eighth | eighth (the 16th head takes the tip-nearest head's count) | right |
| T2 | Litolff | half | half (the black box beside two hollow halves takes the half) | right |
| T3 | Brahms | dotted half | dotted half (the undotted half takes the dot) | right |
| T4 | Brahms | dotted half | dotted half (the black box takes it) | right |
| T5 | Brahms | dotted half | dotted half (the whole-class box, 6.0, takes it: whole notes never have stems) | right |
| T6 | Litolff | half | half | right |
| T7 | Litolff | half | the black box is REFUSED (slash crossing it, 12.4); the remaining head keeps its own half and the stem value is `lone_head` | right for the head left; the refusal is outside the brief's list |
| T8 | Brahms | dotted half | the black box is REFUSED (a twin of a refused slash box); the dotted half is `lone_head` | right; refusal on the list |
| T9 | Brahms | eighth | NARROWED quarter or eighth (`stem_levels_unread`), answer inside; the whole-class head is dropped from the vote | narrowed, answer inside |
| T10 | Litolff | half | half (`stem_agrees`), kept | right |
| T11 | Litolff | half | half; the black box is KEPT (no witness) and takes the half | right (the real-note control) |
| T12 | Brahms | dotted half | dotted half (`stem_agrees`) | right |
| T13 | Brahms | dotted half | dotted half (the undotted half takes the dot) | right |
| T14 | Litolff | half | half (the black box beside a hollow head takes the half) | right |

12 right, 1 narrowed with the answer inside (T9), 0 wrong; T7 and T8 each have a refused box that is not scored (not a member) and a
remaining head that is right. Tiles 2, 3, 4, 6 and 14 (Sean: the black box is not a note) have NO refusal: those boxes are kept and their
VALUE is what is corrected (12.4 says why no witness was built for them).

### 12.4 Refusals: only with a per-box witness

Two boxes are refused across both count pages, both by `Q.STEM_SLASH` crossing them (`out/2.78/p2-refusal-diff-*.txt`): tile 8 (Brahms) and
tile 7 (Litolff). Everything else is unchanged (matched glyph pairs 5,342 and 5,717; 0 only in base, 0 only in arm). I looked for the
other per-box witnesses the ruling names (`out/2.78/p2-refusal-witnesses-*.txt`, over the kept boxes: 988 Litolff, 1,095 Brahms) and
**found a population of about one each, so none was built**:

* (a) a twin of an already-refused slash box: none on Litolff, one on Brahms (tile 8, which the slash reader now refuses anyway);
* (c) a cross-class duplicate on one stem (IoU >= 0.5 with another head): one on Litolff (tile 14, the pair `glyph/2/1/8/2/6` and
  `glyph/2/1/8/2/7`), none on Brahms. A witness exists for tile 14's box and I did not refuse it: one case is not a rule, and the box is
  kept and takes the half, which is the value Sean gave;
* (b) a box that passes the slash shape and the stem crossing and fails ONLY the tip-position test: one on Litolff (tile 11) and three on
  Brahms (tile 4 and two with no judged tile). **Tile 4's box is not a note (Sean) and tile 11's is (DECISIONS), and both sit in this
  class**, so shape plus crossing cannot separate them; that is the reason a refusal by shape or fill alone must not be built.

Tiles 2, 3 and 6 have no witness at all, so their boxes are kept and corrected in VALUE.

**For Sean, because it is not on the brief's list: tile 7's black box (`glyph/2/1/9/11/1`, Litolff) is now refused as a tremolo slash.** It
comes ONLY from the slash-reader fix (`45fcbe14`), which can be reverted on its own. By my eye the box is the blob at the tip and not a
note (12.1); DECISIONS reads it as a real half note. If Sean's reading is right, the cost is one box.

### 12.5 Why `Q.STEM_SLASH` missed tiles 7 and 8, and the fix

Captured on the real ink (`out/2.78/p2-slash-ab.txt`), two causes in `stem_slashes`/`_track_stroke`: (1) a BOLD slash's contact with the
stem runs longer than the contact cap (1.3 spaces), so it was thrown out as a clump; (2) the stem flares at its tip, so the stroke's first
column read no ink and the tracker gave up. Fixes: `STEM_SLASH_MAX_CONTACT_SPACES` 1.3 → 1.6, and `_track_stroke` retries up to
`round(0.06 * space)` columns further out only when the FIRST column tracked nothing (`STEM_SLASH_START_SKIP_SPACES`). A/B on the two
records, base vs arm: stems with a slash 13 → 15 (Litolff, of 1,189 stems), 20 → 21 (Brahms, of 1,150): **3 of 2,339, each a real slash
by eye** on the ink (`out/print/2.78-slash-fix/`: three raw ink crops of the stems whose status changed, not ruled print crops). Both
changes carry a control restoring the old value and failing, and the "clump over the cap" control still rejects. Neither touches a fenced
function. A GATHER change, so it is priced by two fresh gathers (the `B` arm), not by replay. It is its own commit (`45fcbe14`).

### 12.6 Population, before and after (kept heads on a stem with >= 2 kept members)

Stem values (ADJUDICATE), replay of the FRESH GATHER on the final tree:

| page | multi-member stems | heads' own readings: agree / all-narrowed-identical / decided DISAGREE / mixed | after the stem value: agree / all-narrowed | heads whose value changed |
|---|---|---|---|---|
| Litolff p3 (count page) | 81 | 68 / 2 / **10** / 1 | 79 / 2 | 11 |
| Brahms p1 (count page) | 88 | 63 / 17 / **5** / 3 | 70 / 18 | 8 |
| Litolff, other pages (arm X) | 261 | 191 / 7 / **56** / 6 (+1 narrowed-differ) | 254 / 7 | 69 |
| Brahms, other pages (arm X) | 168 | 121 / 29 / **13** / 2 (+3 narrowed-differ) | 136 / 32 | 19 |

The same table on Phase 1's gather rows (arm A, `p2-armA_*.txt`, which lack the slash fix) agrees within one stem (Litolff 82 stems, 11
disagree → 0, 12 heads changed; Brahms 89 stems, 5 → 0, 9 changed). The count pages' ADJUDICATE table says "after: no stem with decided
heads that disagree"; the EVALUATE row below is what the STANDING durations say, and they are not quite the same (Brahms, one stem).
Stem-value reasons over the count pages: Litolff `stem_agrees` 140, `stem_value_from_evidence` 23, NARROWED `stem_levels_unread` 4;
Brahms 127 / 13 / 36. The join: Litolff `one_stem` 655, `stem_by_side` 40, `stem_by_reach` 10, `two_stems` NARROWED 59, `no_stem` 223;
Brahms 822 / 42 / 0 / 6 / 224 (`p2-stem-value-distribution.txt`).

**What EVALUATE adds, a reach print** (`out/2.78/p2-evaluate-reach.txt`; the replay with ADJUDICATE then EVALUATE; reach, not accuracy):

| record | decided stem values | `share_stem_value` firings | stems with a decided-heads DISAGREEMENT, after ADJUDICATE → after EVALUATE |
|---|---|---|---|
| Litolff p3 | 163 | 11 (10 decided restated, 1 narrowed settled) | 10 → **0** |
| Brahms p1 | 140 | 7 (5 restated, 2 settled) | 5 → **1** |
| engraved p0–p2 (control) | 12 | **0** | 0 → 0 (4 multi-head stems, all agreeing) |

* The firings are the same 11 and 8 heads as the ADJUDICATE table except ONE: Brahms p1's tile 9 (`obs:034176`). That stem's value is
  NARROWED (quarter or eighth), so EVALUATE is silent by design, and its whole-class box keeps its decided 4.0 — **a decided whole on a
  stem, which Sean's confirmed rule says cannot be.** The follow-on that would close it: where a head's DECIDED value is a whole and it
  stands on a stem, the whole is impossible (it follows), so narrow that head's duration to the stem's candidates. NOT BUILT: it turns a
  decided verdict into a narrowing in EVALUATE, which wants Sean's look, and it is one head on this page.
* The engraved control has a real population (12 decided multi-head stems, all already agreeing) and fires zero times. A freshly gathered
  engraved page 0 has 73 noteheads each on its own stem, so it cannot test the rule and is not claimed as a control.
* The transitions on the count pages (18 firings): `(0.25,0,2)->(0.5,0,1)` ×6 (a 16th beside an eighth on a stem, the tile 1 pattern),
  `(1.0,0,0)->(2.0,0,0)` ×3 and `(2.0,0,0)->(3.0,1,0)` ×2 (the tile 2/6/13 patterns), three narrowed durations settled (to a half, a half
  and a dotted half), and four single other moves: an eighth to a quarter and an eighth to a half (Litolff), a dotted eighth to a dotted
  quarter and a dotted whole to a dotted half (Brahms). The eighth-to-a-half one is the RISKY direction (the stem has a hollow head and
  the tip-nearest head read a beam) and has no judged case; new tile 6 is the nearest.
* Level changes over all four records: `(2→1)` 44, `(3→1)` 5, `(4→1)` 2, `(1→0)` 6, `(2→0)` 1, `(0→1)` 1 — 58 heads went DOWN, 1 UP: the
  rule overwhelmingly removes strokes the far head counted BETWEEN the heads.

### 12.7 The 12 new blind tiles: `out/print/2.78-phase2-review/` (NOT shown to Sean; he judges later; they do not block landing)

Same style as `2.78-review/`: a crop at 600 dpi cut from the gather's own deskewed raster, with the staff lines drawn, the subject stem
marked by a corner bracket, a frame control in `manifest.json` that can fail, shuffled order, no readings on the images. Our readings are in
`manifest.json` only. Seed 2782. None of the 14 judged stems appears. Ten are decisions that CHANGED and two are controls that did not:

| tile | page | cause | what our reading does |
|---|---|---|---|
| 1 | Litolff p7 | changed, BASE | two black-classed boxes and a half head on one stem become halves (three heads) |
| 2 | Litolff p1 | control, unchanged | beamed: both heads already read the same eighth |
| 3 | Litolff p1 | control, unchanged | hollow: both heads already read the same half |
| 4 | Brahms p2 | changed, DOTS | an undotted half takes the dotted half beside it, hollow heads only |
| 5 | Brahms p0 | changed, LEVELS 2→1 | the other plate: a 16th takes the eighth at the tip |
| 6 | Litolff p7 | changed, LEVELS 1→0 | the RISKY direction: the stem becomes a quarter because the tip-nearest head read no beam |
| 7 | Litolff p3 | changed, LEVELS 2→1 | the NEIGHBOUR of judged tile 1 in the same beamed group (lower head a 16th, tip-nearest an eighth); Sean's tile 1 answer should carry |
| 8 | Litolff p6 | changed, BASE | a decided black box beside a decided half head becomes a half |
| 9 | Litolff p5 | changed, NARROWED→DECIDED | a head narrowed 16th or eighth beside a decided eighth |
| 10 | Litolff p5 | changed, LEVELS 3→1 | the far head read a 32nd, the tip-nearest an eighth |
| 11 | Litolff p6 | changed, BASE+LEVELS+WHOLE | a whole-class box on the stem of a beamed eighth: the confirmed rule |
| 12 | Brahms p3 | changed, DOTS | a filled quarter takes the dotted quarter beside it, no hollow head |

(Page numbers are PDF page indexes, so p3 on Litolff is the count page for a stem not among the 14.)

### 12.8 Tests, `check`, fast tier

* `test_staged_stem_value.py` (42): the join, Sean's tile patterns, the keep-the-real-note control (T11), narrowing, the whole-notes rule
  with a control that can fail, refused/relocated heads not members. `test_staged_stem_slash_reader_2_78.py` (7). `test_staged_share_stem_value.py`
  (12). All written RED first, each against a clean copy of the parent: the stem tests (ImportError, `stem_value` did not exist), the slash
  tests (4 of 7 fail there; the 3 that pass are controls of the old behaviour), and the EVALUATE tests (**7 fail, the 5 stay-silent controls
  pass as they must**, which a tree with no rule cannot do otherwise). The agree-already control was run with the rule's equality guard
  broken and fails (`CONTROL FAILED AS IT SHOULD`).
* `check`: baseline N = 193 on main. With only the two new decisions N was **194**, the +1 being `reach`'s finding that `Q.STEM_VALUE` had no
  live consumer. Adding a `KNOWN_GAPS` entry (the producer-only route other quantities take) would have hidden it, and CLAUDE.md §4d says a
  finding leaves the list when it is WIRED, not when it is explained. `share_stem_value` is the consumer, the gap entry is removed, and N is
  **193** (`out/2.78/p2-check-final.txt`, the run on the final code head).
* Existing tests edited: `test_staged_evaluate_order.py` (the pinned rule order now includes `share_stem_value` before the meter rules) and
  `test_stage_review_evidence.py` (two quantities added to the set of stages that see a human box).
* Fast tier (`pytest tools/omr/tests -m "not slow"`), `tools/` clean throughout each run: on `5f1c71c3` (this lane's last code commit)
  **6,802 passed, 11 skipped, 2 xfailed, 825 deselected as slow, 0 failed**, 583 s; then again on `565af7f9`, the merge of `origin/main`
  `40875f6a` (2.12f landed; it touches `adjudicate.py` and `ownership.py`, merged without conflict, `ORDER` holds both lanes' entries):
  **6,841 passed, 11 skipped, 2 xfailed, 825 deselected, 0 failed**, 576 s. `check` on the merged head: N = **193**
  (`out/2.78/p2-check-merged.txt`). Every commit after the merge touches only `benchmarks/` and `out/`.

### 12.9 Not done / limits

* **EXPORT is unchanged.** Where a stem value is NARROWED, EVALUATE is silent, the heads keep their own durations, and `export._events`
  (`voicing.group_chords_in_measure`) still takes a chord's duration as the MODE of its heads' — an argmax over a disagreement. Holding that
  stem out and counting it is an export change and has no roadmap item yet. A DECIDED stem value is restated first, so the vote has nothing
  to decide there.
* **A narrowed duration that `share_stem_value` settles is now written** where it used to be counted under `duration_narrowed`: 1 on
  Litolff p3 and 2 on Brahms p1. That is the rule doing what it is for, and also a change to the export refusal count that I did not
  measure at the exported-file level (this lane measures GATHER+ADJUDICATE only).
* **The leftover decided whole on a narrowed stem** (12.6, Brahms p1, tile 9's stem), and the same pattern is unmeasured on other pages.
* The two assumptions at the top, and the tile 7 refusal (12.4), are Sean's to settle.
* `Q.STEM_VALUE` reads only the head's own beam levels and the stem's heads; it does not read the bar. Whether a stem's value fits the meter
  is `reconcile_duration`'s, after this rule.
* No whole-movement run was made. The overnight re-gather will price the GATHER change (the slash reader) properly; the replay prices only
  the ADJUDICATE and EVALUATE changes.


## Sec.13. 2.89 EXPORT stops mode-voting a chord (2026-10-11, STAGED export; branch `lane-2.89-chord-export`)

`voicing.group_chords_in_measure` gives a chord the MODE of its heads' (beats, type, dots). Sec.12.9 left that open. Now `export._chords_whose_value_would_be_voted`
(last step of `_place_notes`) removes every head of a chord whose written heads disagree and `_place_notes` counts each under `chord_value_undecided`;
`Unbalanced` still holds (balanced True on every record below). Agreeing chords, and chords 2.78 settled, are untouched. No flag: base vs arm is the
same record re-exported with the function patched to a no-op (`probe`-style scripts were scratch; `probe/2.89_tiles.py` is committed).

| record | chords voted before | heads refused after | bars whose note count changed | pitched `<note>` base -> arm |
|---|---|---|---|---|
| Litolff whole movement (`...20261010-night`, tree has 2.78) | 49 | 109 | 18 | 5589 -> 5563 |
| Litolff p1-3 (`acceptance_quick --full`, this tree) | 6 | 15 | 4 | 810 -> 798 |
| Brahms p0-1 (`acceptance_quick --full`, this tree) | 13 | 29 | 2 | 563 -> 569 |
| engraved (`acceptance --doc beethoven5-engraved`) | 0 | 0 | 0 | document block identical (DEAD on this control: no chord disagrees) |

Why the notes fall by fewer than the heads (Litolff whole: 109 heads, 26 notes): 85 of the heads sat in bars the bar-sum hold-out already withheld
(`notes_held_out_sum` 2575 -> 2490). Why Brahms rises: a bar that no longer carries the voted chord can add up and is then written.
Stem state of the voted chords (`Q.HEAD_STEM`/`Q.STEM_VALUE`): none shares one stem with a narrowed value. Litolff: 28 no_stem, 11 lone_head+no_stem, 4 no_stem+one
decided, 6 ambiguous/lone; Brahms: 7 lone_head, 2 lone_head+decided `stem_value_from_evidence`, 4 other. They are x-grouped heads the reader never tied to one stem,
so "narrowed stem" was the wrong picture: the vote is mostly over heads that may be two voices, or a chord whose stem was missed (Litolff merges, Breitkopf shatters).
Not built: a decided-stem head winning over a stem-less one at the same x (refused with them for now), and 2.78's tile 9 follow-on.
Cost: `test_stage_review_evidence` 'two notes where the plate has one' is now one note FEWER (the human's relabelled half is refused with the machine's
quarter). Fast tier: see ROADMAP/version_memory. Tiles `out/print/2.89-review/` (11, blind; `manifest.json` holds the old vote).

### 13.1 Are the voted chords two voices? (manager's question, 2026-10-11; read off `Q.STEM_DIRECTION` / `Q.HEAD_STEM` on the 11 tile chords)

* **4 of 11 are two voices on two separate stems with OPPOSITE decided directions** (tiles 7, 9, 10, 11: one head up on its own stem, the other down on its own stem).
* 3 have one head's direction decided and the other's abstained (tiles 2, 4, 8). 4 have no direction on any head (tiles 1, 3, 5, 6; Litolff, no stem found).
  So at most 4 are provably two voices, none is provably one chord, and 7 cannot be told.
* **Why the voice split never separated them:** the staged exporter's notehead dict (`_place_notes`' `_det`) carries no `stem_direction` key, so
  `voicing.group_chords_in_measure`'s own divisi guard (opposite stem directions never merge) cannot fire on this path. The chords are merged by x
  first, and `Q.VOICES` / `_voice_split` then assigns whole EVENTS to streams, so the two voices arrive already fused into one event. Not changed here.

### 13.2 Sean's answers on the 11 tiles (2026-10-11; `out/print/2.89-review/answers.json`)

Verbatim: *"Tile 1 is 1 voice probably an instrument that can play chords - it is strange though. 2. 2 voices unison 3-6. One voice 7. 2 voices 8. 1 9-11. 2"*.
ONE voice (a real chord): tiles 1, 3, 4, 5, 6, 8. TWO voices: 2 (unison), 7, 9, 10, 11.

| group | tiles | stem directions (13.1) | result |
|---|---|---|---|
| opposite decided directions, separate stems | 7, 9, 10, 11 | up vs down | 4 of 4 two voices: the stem-direction test is right |
| one direction decided, other abstained | 2, 4, 8 | partial | 2 is two voices (unison); 4 and 8 are one voice: partial direction does not settle it |
| no direction on any head | 1, 3, 5, 6 | none | all 4 are ONE voice (real chords whose heads we read at different values) |

So 6 of the 11 voted chords are real chords read at disagreeing values (a reading fault; refusing them is right under 2.89), and 5 are two voices the
export fused (7, 9, 10, 11 by stem direction; 2 a unison). The voice-carry fix is NOT started; the manager asks Sean.


## Sec.14. 2.90 two voices at one x are written as two voices (2026-10-11, STAGED export; branch `lane-2.90-voice-carry`)

**Diagnosis verified (rule 10).** `_place_notes`' head dict carried no stem direction, so `voicing.group_chords_in_measure`'s divisi guard (opposite
directions never merge) never fired on this path and two voices at one x were fused before `Q.VOICES` / `_voice_split` saw them. `Q.STEM_DIRECTION` and
`Q.HEAD_STEM` existed on the record and nothing in EXPORT read them. Reach (same record, 2.89 refusal set, classified by the heads' decided stems;
`probe/2.90_reach.py`):

| record | 2.89-refused chords | opposite decided directions | distinct decided stems, same direction | one stem / unknown |
|---|---|---|---|---|
| Litolff whole (`...20261010-night`) | 49 | 2 | 0 | 47 |
| Brahms whole (`...20261010-night`) | 178 | 39 | 5 | 134 |

**What EXPORT now does** (`staged/export.py`; `voicing.py` untouched, LEGACY unchanged): `_stem_facts_of` carries each head's DECIDED direction and stem id
into the head dict; `_settle_divisi_pairs` (before 2.89's refusal) keeps those directions in a bar only where (1) EVERY chord of the bar has a decided
direction and (2) the two streams `split_events_into_voices` makes carry the same total time; otherwise the directions come off the bar's heads and the bar is exactly what 2.89
left it. `_voice_split` keeps `Q.VOICES`' split where it already parts every up/down pair and otherwise (the record fused the pair) takes Sean's 2.21
rule 1 (same beat, opposite stems, always two voices) on the exporter's own events. Heads sharing one decided stem id are never split (a stem with two
directions has them taken off). Counted: `report["part_join"]["divisi_at_export"]`, `written.two_voice_bars_from_exporter_stems`. Accounting equality holds.

**Why the two conditions.** The first version split every pair. On Litolff it held out five bars that were written before: `split_events_into_voices`
puts an unknown-direction event in voice 1 (a guess about a stem nobody read, rule 8), so voice 2 carried only the notes whose stem was decided down and was short.

**Results (one record, one tree, base = no stem facts = 2.89 vs arm; `probe/2.90_ab.py`).**

| record | pairs: kept two-voice / left fused (unknown dir / unequal time) | two-voice bars written base -> arm | refused heads `chord_value_undecided` | pitched notes | bars changed |
|---|---|---|---|---|---|
| Litolff whole | 5 / 6 (1 / 5) | 1 -> 2 | 109 -> 109 | 5563 -> 5551 | 3 (1 gains a voice, 2 newly held out) |
| Brahms whole | 10 / 65 (14 / 51) | 1 -> 7 | 377 -> 369 | 6990 -> 6990 | 6 (all gain a voice; 0 notes gained or lost) |
| engraved (`beethoven5-engraved`) | 0 pairs: DEAD control | | | 354 -> 354 | 0; `acceptance --doc beethoven5-engraved --no-write` identical but timestamps |

* **Litolff, the two bars that got worse (Part 11 and Part 12 measure 18 are one bar on a doubled staff):** the print has two voices of four eighths (crop, octave
  Bs); we read 6 of the 8, in two streams of three that carry equal time but not the bar. The old file wrote the six as four fused events that happened to
  add up to 2/4. It is now held out (`bar_does_not_add_up`): the bar was not read, and the old file claimed it was.
* **Brahms:** the six bars that change are agreeing-value pairs (a fused chord written before) that now come out as two voices with the rests in both
  (`Q.VOICES` already named them; they only fit once the events were separate). Zero notes gained: the 8 heads released from `chord_value_undecided` land in
  bars that still do not add up (`bar_does_not_add_up` 8469 -> 8477).
* **Same direction, different stems (5 Brahms chords):** not handled. `split_events_into_voices` needs an up and a down, so two same-direction stems at one x
  have no voice split in the existing convention; they stay refused by 2.89.

**Sean's 11 tiles** (`probe/2.90_tile_status.py`):

| tile | Sean | arm |
|---|---|---|
| 1, 3, 4, 5, 6, 8 | one voice | unchanged: no up/down pair in the bar, still refused (positive control: the one-voice tiles are not split) |
| 2 (unison) | two voices | **stems alone cannot separate it**: A4 is decided down on stem `obs:060098`, F5 has no decided direction and no decided stem. Stays refused. |
| 7 | two voices | opposite directions found, bar left fused: the two streams carry 3.0 vs 2.5 quarters (a note or rest of the down voice unread) |
| 9 | two voices | left fused: one chord (Gb5, Bb5) has no decided direction |
| 10 | two voices | left fused: streams 2.5 vs 2.0 (the down voice's Eb4 is read 1.0; the up voice's 1.5) |
| 11 | two voices | **kept as two voices** |

So 1 of the 4 provable two-voice tiles is written as two voices; the others are two voices by decided stems whose bar we do not read completely, and writing them as
two voices would only hold the bar out. That is a reading fault in the other voice (value or missing rest), not a voice-carry fault.

**Not built / open.** Tile 9's undecided chord (the exporter cannot say which voice it belongs to; that is an INFER question, not export). The unequal-time cases (51 Brahms bars) are
the larger population: a second voice with an unread rest or a misread value. Blind tiles for the voices newly kept apart: `out/print/2.90-review/` (see `manifest.json`;
our values live there only).

### 14.1 Sean's answers on the 10 tiles (2026-10-11; `out/print/2.90-review/answers.json`)

Verbatim: *"I'll only give one number if both values are the same. 1.8 2.8 3-5. Dot2 6. Top voice 8, 4, dot 4 bottom voice dot 2 7. Dot 4 8.2  9 top voice red box is a quarter and the lower box is around an sf. The actual bar has a 4 and 4 rest on top and a whole note rest on bottom"*. Tile 10 unanswered. Convention: one number = both voices share that value.

| tile | bar written? | our values vs Sean | verdict |
|---|---|---|---|
| 1, 2 | yes | eighth/eighth, both right | right |
| 3, 4, 5 | yes | dotted half both voices, right | right |
| 8 | yes | half/half, right | right |
| 6 | held | bottom voice is a DOTTED half, we read half | holding was right |
| 7 | held | dotted quarter on both, our values right | held by the bar sum (the rest of the bar is not read to the meter); not checked further here |
| 9 | held | the lower "head" is ink around an `sf`, not a note; the bar is a quarter + quarter rest over a whole rest | holding was right; an `sf` read as a notehead is a GATHER/precision miss (2.76-style): named, not fixed |

Every bar the export WRITES (1, 2, 3, 4, 5, 8) is right on both voices, 6 of 6. No held bar was wrong to hold. Tiles 7/10 split-and-hold vs refuse (the label for a
bar where the other voice is short): left as is; relabelling was not shown to be file-identical, so not done.

## Sec.15. ROADMAP 2.137 -- tremolo slashes still boxed as noteheads (2026-10-15)

Path: STAGED, GATHER + ADJUDICATE only, no gather. Branch `lane-2.137-trem-slash`, off main `ca70f1ad`. Records: the saved
`20261014-night` pair (read through `record_io.load_record`). Sean, 2026-10-15 (page-facts §1, general scope): *"They are never oval
shaped - always thick diagonal lines."* Fix: `OMR_SLASH_AT_STEM_END`, **default OFF**. Probes: `probe/2.137_redecide.py`,
`2.137_p0_records.py`, `2.137_tiles.py` (+ `2.137_tiles_spec.json`); outputs `out/2.137/`; tiles `out/print/2.137-review/` (10, blind).

### 15.0 The anchor case is not a slash

Brahms p14 sys1 staff7 cell0 (bar 274, P10, 2.134 tile 13): what a human reads is a high dotted quarter ABOVE the staff with three
LEDGER LINES under its head. The three strokes sit exactly one staff space apart (page y 5935 / 5987 / 6021, space 30 px at 600 dpi),
read 0.2-0.3 degrees, and the detector boxed them `ledgerLine`. `Q.STEM_SLASH` already refuses all three (`one_sided`, correctly). The
record keeps ONE head there (the dotted quarter) and that is right; nothing is standing as a head that should not. The ROADMAP row's
"three slashes on one stem" was read off the ledger lines. Tile 4 is this bar, as a control.

### 15.1 What stands as a head and is a slash (diagnosis, no code)

Census: every kept `notehead_is_not_a_notehead` box that GATHER filed a `Q.NOTEHEAD_STEM_CROSS_INK` row for (Brahms 5,807 of 19,665 kept;
Litolff 4,683 of 9,850). The shape witness: elongation >= 1.8, fill <= 0.55, both sides >= 0.30, angle 10-70; plus every kept box holding a
passing `Q.STEM_SLASH` stroke (Brahms 17, Litolff 10). Each candidate then read on a 600 dpi crop (contact sheets, the box bracketed), one line
of what a human reads: *a thick diagonal stroke across the stem, usually the first of a stack of two or three at the stem's tip; a half or
dotted-half head at the other end of the stem.*

Confirmed by crop and standing as heads on the night records: **Brahms 37, Litolff 12** (49). Two more candidates are NOT slashes: Brahms
`15/1/7/5/9` is a quarter rest's zigzag and Litolff `11/0/2/11/1` is the curl of a bass clef beside a barline.

Which of the 2.49 / 2.71 tests let each of the 49 through (first failing test; margins are the measured values):

* **A. POSITION only** (shape and crossing pass; the box centre lies 0.07-0.49 box-heights from the stem's tip, under the 0.5 floor):
  Brahms 16, Litolff 10. The first slash of a stack sits at the tip; the measured positions hug the cut (median 0.43 box-heights).
* **B. the 20-degree SHAPE floor only** (angle 10.9-19.7 degrees, position fine): Brahms 10.
* **C. angle floor AND position:** Brahms 9, Litolff 2.
* **D. crossing share fails, the 2.71 stroke witness stood** (ink split 0.16/0.84 and 0.20/0.80, the stem in the box's left third; a stroke
  read across both sides): Brahms 2 -- position refused them again.
* 2.71 as a whole: of the 27 kept boxes that hold a passing slash stroke, ALL fail the POSITION test and nothing else (0.15-0.50).

Not guilty: crossing share split between stacked slashes (every share was 0.27-0.73), a stem not found (every candidate has a matched stem
by construction -- see 15.5 for the unmeasured population), a head box without the slash centre line (all 27 hold it).

### 15.2 Control (rule 7)

* A real head the 2.71 stroke witness sits under: Litolff `12/0/2/8/7` (half head, elongation 1.25, position 0.25). Dropping POSITION from
  the stroke witness alone would refuse it; the oval witness keeps it. A unit test pairs the two (`..._oval_with_a_stroke...` is kept, the
  same box with elongation 2.0 is refused), so the control can fail.
* Real heads near a slash: Litolff `13/0/5/8/5` (the half head under the slash `13/0/5/8/4`; the old keep-choice kept the SLASH and refused
  this head, the flag keeps the head) -- tile 2; the anchor head, Brahms `14/1/7/0/4`, kept before and after -- tile 4.
* The oval witness over everything else: of the 10,490 kept boxes with a cross row, the flag refuses 51 and each of the 51 was read on its crop.

### 15.3 The fix (flag `OMR_SLASH_AT_STEM_END`, default OFF)

`notehead_precision._slash_at_stem_end` (read by `_tremolo_slash_crosses_stem` and `_is_tremolo_slash`, so a stacked group never keeps a slash
either). A box is refused as the slash it is when its own ink is NOT OVAL -- elongation >= 1.8 and fill <= 0.55 (2.49's own cut-offs), angle
10-45 degrees, fill >= 0.15 ("thick") -- AND the stroke crosses the stem (each side >= 0.30 of the glyph's own ink, or a passing `Q.STEM_SLASH`
stroke under the box). POSITION is recorded (`position_ok`), never asked. Reason stays `tremolo_slash_crosses_stem`; the verdict carries a
signed margin (fraction of the cut), the tightest axis and `refused_via`; a KEPT near miss files its negative margin
(`detail.tremolo_slash_signal.at_stem_end`). A refused slash is never a notehead and never a rest, the head beside it is kept, the written
value never changes (2.71).

What decides and what only narrows: "never oval, thick, diagonal, across both sides of one stem" is Sean's convention and decides. The cut-offs
are 2.49's (shipped on Sean's review) plus two measured on these two plates only (the 10-degree floor, the 0.15 fill floor): so the flag stays OFF
until Sean has read the tiles, and the margins are on the record. The confirmed slashes' tightest margins: median 0.125 of the cut, minimum 0.001
(Brahms), 0.026 (Litolff); tightest axis is the 0.55 fill ceiling for 30 of 49.

### 15.4 What the flag does on the night records (ADJUDICATE only; `probe/2.137_redecide.py`, flag off then on, per subject)

Control: the flag-OFF arm reproduces the saved Litolff verdicts exactly (every reason count identical). On Brahms it differs from the saved record in
ONE reason, `is_a_meter_digit` 30 -> 0 (a decider the limited re-run omits feeds it); the comparison is therefore arm-on against arm-off, per subject.

* Brahms: +38 refused (37 slashes + the rest zigzag, wrong label, right outcome); 10 boxes already refused (duplicate/stacked) now carry the slash
  reason; 1 box leaves the refused set (`12/0/10/0/14`, the second slash of a stack whose partner is now refused; elongation 1.76, 0.02 under the cut:
  a slash still stands there, as before).
* Litolff: +13 refused (12 slashes + the bass-clef curl, wrong label, right outcome); 8 already-refused now carry the slash reason; 2 boxes
  leave the refused set because the slash that beat them in the stacked keep-choice is gone: `13/0/5/8/5` (a real half head, tile 2) and
  `16/0/0/8/13` (not yet looked at on a crop).

### 15.5 Checks

* **Hand-truth scorer, Brahms p0** (`out/2.137/handtruth-p0-{off,on}.txt`; the page-0 slice of the night record re-decided by `rerun`, the off-arm
  reproduces the saved record's 3 slash refusals): notehead recall at ADJUDICATE 0.990 -> 0.990 (378 of 382 matched both ways, 4 lost both ways --
  no head lost); precision 0.952 -> 0.962 (439 read both ways); owner 377 right / 0 wrong and position 375 right / 1 wrong both ways. Independent
  witness: Sean's own 16 hand-drawn `tremolo1` boxes on this page overlap 4 kept head boxes at IoU >= 0.3 with the flag off and 1 with it on (3 fixed;
  none of the 4 newly refused page-0 boxes overlaps a truth notehead).
* `judged score` (Sean's past answers), night records, flag-off: Litolff right 108 / wrong 11 / narrowed 4 / abstained 1 / not_found 13 / unscored
  99; Brahms 70 / 10 / 18 / 1 / 7 / 145. None of the 72 subjects the flag changes (49 Brahms + 23 Litolff) is a judged subject, so the score is
  identical with the flag on BY CONSTRUCTION -- a computation, not a measurement.
* Tests: `test_staged_slash_at_stem_end_2_137.py` (15; 8 RED on main, the 7 controls pass on main) + `test_staged_tremolo_slash.py` (27) pass.

### 15.6 Not fixed, and what Sean is asked

* Slashes whose ink reads round because two sit in one box (Brahms `16/0/10/2/5` elongation 1.27, `11/1/10/8/6` 1.55, the pair partner
  `12/0/10/0/14` 1.76) still stand as heads: the oval witness cannot read them. At least 3 seen.
* Slash boxes no stem reached have no cross-ink row and no shape on the record (Brahms p0 `0/0/4/3/5`, a half-class 83 x 110 box on Sean's
  tremolo truth box, IoU 0.36): unmeasured population, needs a GATHER change (not this lane's fence).
* The two label errors (rest zigzag, bass-clef curl) are refused rightly under the wrong reason.
* Blind tiles for Sean: `out/print/2.137-review/` (10 tiles: 5 fixed slashes, 3 real-head controls, 2 label-error cases; kinds only in `manifest.json`).
  Red corners = the bar, blue corners = the box in question; nothing of ours is drawn.

### 15.7 Fast tier and check (the one open item)

Fast tier (serial, 738 s): 8,048 passed, 12 skipped, **2 failed** -- `test_flag_triage.py::test_every_read_flag_is_documented` and
`test_flag_docs_match_predicates.py::test_undocumented_is_exact_no_stale_entries`. Both say the same thing: `OMR_SLASH_AT_STEM_END` has no row in
`docs/flags-2026-09.md` (the two tables `OMR_BARE_STEM_RANK` sits in, lines ~48 and ~172). That file is outside this lane's fence, so the rows are NOT
written here; they are the landing step: `| OMR_SLASH_AT_STEM_END | off | ADJUDICATE ... roadmap 2.137 |` in both tables. No other failure.
`python3 -m tools.omr.staged.check`: TOTAL open=192 (limit 192; `staged.margins` open=0).

### 15.6 Sean's answers (2026-10-15)

Recorded in `out/print/2.137-review/answers.json`. Tally: 5/5 fixed slashes right, 3/3 controls right, 1 right outcome with wrong label (tile 6, a
quarter-rest piece refused under the slash reason), 1 wrong (tile 9, a real head refused).

* **Tile 9 (Litolff `glyph/11/0/2/11/1`) is a real half note refused as a slash.** The key called it a bass-clef curl; Sean reads a deformed, large,
  open-ended half note, a printing defect that has come up in several tests, extremely rare, which he expects to need human eyes. So the right outcome
  for this kind is a head left UNREAD and marked for a human, never silently refused.
* **The anchor case named in ROADMAP 2.137** (Brahms p14 sys1 staff7 cell0, 2.134 tile 13) is ledger lines, not slashes, as the lane found. The
  manager misread that crop.
* **Still open at landing:** the flag still lacks rows in `docs/flags-2026-09.md` (the 2 fast-tier failures in 15.5), to be added at landing.

## Sec.16. ROADMAP 2.159 -- the head reader does not see simple Litolff halves (2026-10-17; STAGED GATHER + ADJUDICATE; branch `lane-2.159-head-reader-halves`)

Sean 2026-10-17: "We should also figure out the head reader - I'm not sure why it doesn't see simple half notes". Read off
the 20261016-night records (main `1d42c4aa`) through the per-page slices of their GATHER rows and duration verdicts, the
whole records (streamed) for the refusal verdicts, and the PDF pages; nothing gathered. Probes `probe/*_2_159.py`, outputs
`out/2.159/` (not committed but the tile key).

### 16.1 What the tree says about "20 halves narrowed by head_fill_from_ink" (rule 10)

* Crops 1-22 of `litolff-unread-35` are 21 heads (11 and 12 are one condensed-staff head). **14 of them** are narrowed
  `head_fill_from_ink`. The other 7 are not a head-reader problem: the detector classed them half/whole and a later step
  narrowed them (crops 2, 14 `whole_class_filled_on_a_stem`; 4, 7 `open_head_flag_contradiction`; 9, 16 decided half, then
  `dot_seen_beside_a_plain_note`), or the note is not a half (5, `beam_discounted_uncertain`, "partial q." on 10-14).
* `head_fill_from_ink` on the night records: Litolff **114**, Brahms **231** (the overnight summary; no 236 found).
* **Most of them are not notes.** ADJUDICATE already REFUSES the box as not a notehead (or as a whole rest) on 67 of the
  114 Litolff and **216 of the 231 Brahms** boxes (`too_narrow` 32 / 160 -- on Brahms nearly all quarter rests boxed as
  heads, seen on the round-2 tiles -- `clipped_fragment` 9 / 40, `stacked_head_duplicate` 12 / 2, ...): 2.143's stale
  durations. **Real notes: Litolff 47, Brahms 15.** Nothing later overturned any of the 14 crop heads: the live verdict is
  the ADJUDICATE narrowing itself.

### 16.2 Why each was not decided a half (the first 2.148 gate it failed, measured on its own rows)

`head_fill_from_ink` is reached only where the 2.23 centre window ALREADY reads the head hollow; what fails is 2.148's first
step, which decides a half only for (a) a head-sized DETECTOR box (0.9-1.8 sp tall, 1.1-1.9 wide) (b) whose slit share is
>= 0.18 (c) with a stem box touching that box.

| cause (first gate failed) | Litolff notes (all boxes) | Brahms notes (all boxes) |
|---|---|---|
| box too SHORT (< 0.9 sp): the detector boxed only part of the head; its slit reading is of a rim | 11 (45) | 4 (176) |
| box too TALL (> 1.8 sp): head + accidental / neighbour / chord in one box | 9 (23) | 3 (6) |
| box too WIDE (> 1.9 sp) | 6 (13) | 5 (7) |
| box too NARROW (< 1.1 sp, the key-flat guard) | 3 (14) | 0 (34) |
| head-sized, slit reads hollow, but NO STEM box touches the head box | 16 (16) | 2 (4) |
| head-sized, slit between 0.06 and 0.18 | 2 (3) | 1 (4) |

Counted independently on the notes: box not head-sized Litolff 29 / Brahms 12, no own stem 32 / 10, and **every one of
the 62 fails at least one of the two** (none is head-sized with a stem). A staff line or ledger through the head was not a
separate cause here (the slit share already counts white between ink row by row); no late step overturned a reading.

The 14 crop heads (sp = staff spaces; `rows_share` = 2.148 slit on the detector box; centre ink = 2.23 window raw / line
rows out; located = the slit on the head box an earlier reader located, 16.4):

| crop | glyph | detector box w x h, head-sized | own stem | rows_share | hole | 2.23 centre ink | cause | located rows_share |
|---|---|---|---|---|---|---|---|---|
| 1 | 1/0/9/11/1 | 1.16 x 0.89 no | yes | 0.00 | 0 | 0.68 / 0.25 | short | 0.40 (part-boxed) |
| 3 | 5/1/4/2/1 | 1.68 x 1.27 yes | no | 0.08 | 0 | 0.70 / 0.41 | between | - |
| 6 | 7/0/3/2/2 | 1.12 x 1.46 yes | no | 0.43 | 0 | 0.53 / 0.49 | no stem | - |
| 8 | 9/0/4/2/8 | 1.91 x 1.66 no | yes | 0.60 | 0.09 | 0.67 / 0.50 | wide | - |
| 10 | 10/0/3/2/1 | 1.35 x 0.89 no | yes | 0.37 | 0 | 0.43 / 0.33 | short | 0.70 (part-boxed) |
| 11,12 | 10/1/10/5/4 | 1.13 x 0.67 no | yes | 0.05 | 0 | 0.83 / 0.61 | short | 0.64 (line cut) |
| 13 | 10/1/1/8/8 | 1.43 x 0.37 no | yes | 1.00 | 0 | 0.57 / 0.57 | short | 0.64 (re-centre) |
| 15 | 11/0/1/9/2 | 1.29 x 0.95 yes | no | 0.11 | 0 | 0.82 / 0.58 | between | - |
| 17 | 11/0/2/12/2 | 1.40 x 2.07 no | yes | 0.44 | 0.11 | 0.69 / 0.46 | tall | - |
| 18 | 11/1/7/8/2 | 1.68 x 0.83 no | yes | 0.82 | 0 | 0.63 / 0.62 | short | - |
| 19 | 12/0/7/8/13 | 1.14 x 0.77 no | no | 0.00 | 0 | 0.71 / 0.33 | short | 0.10 (part-boxed) |
| 20 | 14/0/3/3/6 | 1.09 x 0.88 no | no | 0.13 | 0 | 0.47 / 0.29 | short | 0.64 (part-boxed) |
| 21 | 14/1/3/11/4 | 1.06 x 1.41 no | no | 0.14 | 0 | 0.69 / 0.61 | narrow | - |
| 22 | 14/1/3/12/1 | 1.16 x 1.34 yes | no | 0.31 | 0 | 0.60 / 0.48 | no stem | - |

Crops, one per cause (red = detector box, green = located head box, right = the binarized pixels inside the red box x10,
the measures printed): `out/print/2.159-diagnosis/` (`index.json`).

### 16.3 Sean's question (2026-10-17): "Are we still using the split rule for hollow heads? I thought we found that the ink percentage was a better rule?"

Both run on main: 2.148's slit share first (>= 0.18 hollow, <= 0.06 solid, head-sized box only), then 2.23's centre window
as the fallback (centre ink <= **0.75** and ring - centre >= 0.10). Each stored measure ALONE, best single cut and errors
at it, on every BLACK-classed head Sean judged a duration for (Litolff 79, 26 of them hollow; Brahms 83, 1 hollow;
`probe/separate_2_159.py`) and on his Brahms pdf 0 hand-truth page (387 black-classed boxes, 1 hollow;
`probe/truth_p0_2_159.py`):

| measure | Litolff judged, all boxes | Litolff judged, head-sized boxes | Brahms judged | Brahms hand truth p0 |
|---|---|---|---|---|
| slit `rows_share` (2.148) | cut 0.19: **0 errors** (hollow 0.35-1.00, black 0-0.03) | 0 | 0 | 0 (black <= 0.11, the hollow 0.67) |
| enclosed hole share (2.148) | 4 (4 halves read 0: the Litolff slit opens out of the rim) | 4 | 0 | 1 |
| 2.23 centre-window ink fraction | cut 0.93: 3 (blacks in loose boxes read 0.44) | cut 0.93: **0** (black all 1.00, hollow 0.35-0.85) | 0 | 0 |
| whole-head ink percentage, lines erased (ink / head area) | cut 0.70: **16** (13 halves missed) | 13 | 1 | 1 |
| whole-head ink percentage, raw | 26 | 23 | 0 | 0 |

On his own judged heads the split (slit) rule separates hollow from black with the widest gap, and the whole-head ink
percentage is the WORST measure (a thin-slit Litolff half is 60-85 % ink, as dark as a black head in a loose box). The
centre-window ink fraction also separates, but only at a cut near 0.9 (2.23's 0.75 misses the slit halves, why 2.148 was
built), a cut fitted on these two plates. Caveats: 1 hollow black-classed head on Brahms in either set (Brahms halves are
mostly classed half by the detector); the judged set is the heads earlier lanes chose to ask about. **None of this is why
the 14 were missed: the measures read most of them hollow; the boxes and the stems stopped the decision (16.2).**

### 16.4 Built (flag `OMR_HEAD_FILL_LOCATED_BOX`, default OFF)

The top cause is the detector box that is not one head's size. Where an earlier GATHER reader LOCATED the head (2.39b
`notehead_recentre`, 2.73 `head_line_cut`, 2.115 part-boxed re-centre) the 2.23 windows were already read on that standard
head box; the slit was not.
* GATHER `gather.head_interior_white_located`: the same `head_interior_white` on the located head box, off the PAGE raster
  (Sean 2026-10-14, 2.115 round 2), filed beside the detector-box reading as `Q.NOTEHEAD_INK.detail.interior_white_located`
  (`box_cell`, `located_by`). Decides nothing.
* ADJUDICATE `rhythm.adjudicate_duration` first step, flag ON: a black-classed head whose detector box is NOT head-sized,
  not refused as a notehead, whose located box still holds the detector box's own centre (moved within one head, not onto
  a neighbour: Brahms `glyph/11/1/10/3/10`, a judged dotted quarter whose re-centre jumped 0.75 sp onto the head above),
  whose located slit share is >= 0.18 (2.148's cut, not re-fitted) AND whose 2.23 window on that same box reads hollow, on
  its own stem, is a half. It only ever says HOLLOW: a solid located reading changes nothing.
* Rejected on the way. Round 1 (no 2.23 or refusal guard): 24 Litolff changes, 14 of them flips of DECIDED values -- white
  specks in a beamed cluster (an eighth, `glyph/16/0/0/4/8`) and in an `ff` boxed as a head (`glyph/16/1/2/3/7`, whose stem
  mates the shared-stem rule then also made halves). Round 2 (2.23 guard): 10 Litolff / 24 Brahms changes, 6 and 22 of them
  boxes the record refuses as not a notehead (the Brahms ones quarter rests). Final: + not refused.
* Tests `tools/omr/tests/test_staged_head_fill_located_2_159.py` (15): positive + flag-off, solid, between, 2.23-solid,
  moved-box, no-stem, head-sized and older-record controls; the GATHER reading on a ring vs a filled head and its two
  declines. The positive fails with the located read removed (run RED).

### 16.5 Replay (fixed harness `review.rerun`, 2.157, per page; the GATHER reading injected from the page raster)

`probe/replay_pages_2_159.py`, flag OFF vs ON, everything else shipped. CONTROL: the OFF arm's first ADJUDICATE duration
verdict equals the stored one on **14,272 / 14,272** Litolff and **32,389 / 32,389** Brahms glyphs (all pages, round 2;
the final guard re-run on the pages that had changes: 4,649 / 4,649 and 6,184 / 6,184). Probe control: the page-raster
slit on the detector box agrees with the stored cell-raster one on 49/51 Litolff and 202/203 Brahms heads (same side of
0.18). A per-page replay is faithful for ADJUDICATE; the live verdict was compared OFF vs ON only.

* **Reach (final): Litolff 4 heads, Brahms 3** (one a box the record calls a whole rest), every one `head_fill_from_ink`
  narrowed {half, quarter, whole} -> decided half; nothing written shorter, no decided value moved.
* **Of the 14 crop heads, 4 become decided halves** (crops 1, 10, 11/12, 13: 5 of the 22 crops). The other 10 have no
  located head (8, 17, 21, and 18 short with no re-centre), no stem attached (3, 6, 15, 19, 20, 21, 22) or a between
  reading (3, 15, 19).
* **Sean's judged tiles: 0 judged glyphs change** on either plate (duration or otherwise): no hollow head he judged is now
  called black and no black one hollow.
* Our own look (not evidence): the 4 Litolff heads look like halves; of the 2 Brahms notes, one is part of an `ff` boxed
  as a head with a stroke for a stem, one looks like a black head crossed by a line. Brahms does not confirm; it stays OFF.

### 16.6 Tiles for Sean

`out/print/2.159-review/` -- 8 tiles: every changed head that is a note and that he has not judged (Litolff 4, Brahms 2)
plus 2 controls that can fail (a Litolff head he judged a half, a Brahms head he judged a quarter), shuffled, one blue box,
"Tile N" only; key `out/2.159/tiles-key.json` (each tile's blue box re-found in the PNG at its key offset); `answers.json`
`{}`. Fewer than the ~20 asked for: the flag changes only 6 notes.

### 16.7 Not done / next

* What remains is the stem and the box, not the fill: 32 Litolff / 10 Brahms real-note heads have no stem box touching the
  DETECTOR box (crop 22: the stem stands just left of the box), and 20 Litolff / 9 Brahms not-head-sized boxes have no
  located head at all (chords, head + accidental). Reading the stem against the located head box would add at most 3
  (Litolff `14/0/3/3/6` = crop 20, `15/0/0/2/2`; Brahms `18/1/0/4/10`); not built (step 2, the stem reader).
* 283 of the 345 `head_fill_from_ink` boxes are non-notes with a stale duration (2.143, parked OFF).

### 16.8 Sean's answers (2026-10-17) and the not-a-head guard

Sean, verbatim: "1. Ff 2. 2 3.2 4.trem slashes 5.4 6.2 7-8.2". Recorded in `out/print/2.159-review/answers.json` (the
manifest now names each tile's glyph; `benchmarks/acceptance/judged-tiles.json` rebuilt, 1154 tiles). **The 4 Litolff
changes (tiles 2, 6, 7, 8) are halves: 4 / 4 right. Both Brahms changes are NOT notes** (tile 1 part of an `ff`, tile 4
tremolo slashes). Both controls right (3 half, 5 quarter).

**Why tiles 1 and 4 got through** (their stored readings, `probe/why_kept_2_159.py`): the existing readers SAW both and
fell short only of REFUSING the box.
* Tile 1 (Brahms `glyph/18/1/9/6/15`): GATHER filed `Q.NOTEHEAD_LETTER_INK` -- the head lies on a `dynamicF` box -- but only
  0.264 of the head is inside it (the `f`'s hook pokes above the detector's `f` box), under the dynamic-letter refusal's
  0.4 cut, so `notehead_is_not_a_notehead` kept it. (The 2.139 lexicon word works on the text reading of the letters and
  says nothing about this head box.)
* Tile 4 (`glyph/16/1/10/0/7`): the 2.49 / 2.137 slash test read the ink CROSSING the stem (35 % / 65 % either side) and
  in position; it failed only the 10-degree angle floor (8.8 degrees), so no refusal.

**Guard (in the located-box rule only, no new number):** the rule does not read a head that GATHER filed as lying on a
dynamic letter (`Q.NOTEHEAD_LETTER_INK` present) or whose ink the slash test read as straddling a stem (`crossing_ok`, or
the 2.71 stroke witness). A refusal needs the readers' cuts; a half decided from a substitute box does not get to ignore
their readings. The 4 Litolff halves carry neither reading. Tests: two built on tiles 1 and 4 (their own row values) plus
a one-side-of-the-stem control; both tile tests fail with the guard removed (run RED).

**Replay (all pages, same records, no gathers):** control 14,272 / 14,272 and 32,389 / 32,389. **Reach: Litolff 4, Brahms
0.** Tiles 1 and 4 (and the Brahms whole-rest box) now unchanged; Litolff tiles 2, 6, 7, 8 still decided halves; no other
judged head changes. The rule is now right 4 / 4 on Sean's tiles but reaches one plate only and 4 of its 47 real-note
`head_fill_from_ink` heads; the flag stays OFF.

## Sec.17. ROADMAP 2.164 -- tie ends and barline ink boxed as heads at a bar's left edge (2026-10-17; STAGED GATHER + ADJUDICATE; branch `lane-2.164-tie-ends-as-heads`)

Sean 2026-10-17, on the 2.160 sheets of the 25 lowest-ink left-edge head boxes: *"almost entirely tie ends ... or a bar
line"*; then *"Yes run that fix. Make sure to find out why it was calling those notes"*. No gathers: the 20261016-night
records (main `1d42c4aa`), the PDF pages at 600 dpi, `review.rerun`. Probes `probe/*_2_164.py`; outputs `out/2.164/`.

**CONVENTION ASSUMED:** a notehead is an oval about one space tall and 1.25 wide (filled, or an outline whose top and
bottom edges stand a space apart); a tie's end is one thin stroke; a barline is a hair wide. **WHAT WOULD FALSIFY IT:**
a head Sean values whose columns read as thin as a tie's stroke. **NOT CONFIRMED:** the refusal cut (half a head's
width of head-tall columns) is measured on these two plates only; tiles out, unanswered.

### 17.1 Who the 226 candidates are (2.160's geometry; `probe/extract_2_164.py`, `probe/why_2_164.py`)

| | Litolff | Brahms |
|---|--:|--:|
| 2.160 candidates (a left-edge head box with an arc from an earlier bar ending on it) | 20 | 206 |
| already refused by a shipped ADJUDICATE rule on the night record | 6 (`too_narrow` 5, `belongs_to_a_nearer_staff` 1) | 192 (`too_narrow` 180, `clipped_fragment` 7, nearer staff 2, dynamic letter 1, tremolo slash 1, dot 1) |
| **stand as notes** | **14** | **14** |
| of those, by the lane's eye (NOT evidence; `probe/look_2_164.py`): an arc's tail | 8 | 12 |
| of those, the box holds a real head | 6 | 2 |

**The Brahms split asked for.** 2.160 read Brahms's median erased ink 1.00 as "most are real tied-to notes". They are
not: **180 of the 206 are barline slivers** (boxes 0.24-0.45 sp wide, every one starting at the cell's left edge, full
ink because staff-line erasure does not touch a barline), already refused `too_narrow`; 12 more are refused by other
rules. Of the 14 that stand, **12 are tie/slur tails** and **2 are real tied-to notes** (`16/0/11/3/7`, `16/0/11/5/3`,
black heads a tie runs into). Sean's 25: 15 stand (13 tails, plus #6 `2/0/7/10/3` and #8 `14/1/2/11/5`, large boxes
around a real half and the tie -- his "very large box around a note and other things"); the other 10 (#7, #15-18, #21
`too_narrow`, #19 and #22 nearer staff, #20 dynamic letter, #24 dot) were already refused and never reach the score.

### 17.2 Why the 20 standing tails were called notes (one row = one mechanism, measured on its own rows)

| mechanism | count (of 20) | what the record says |
|---|--:|---|
| GATHER: the bar's crop CUT the arc at the barline | 20 | the detector runs once per measure cell (`gather.py`, `detector.detect(c, ...)`) and a measure cell has no horizontal padding; the previous bar's arc box ends 0.002-0.357 sp from its own cell's right edge (all 226 candidates <= 0.357), and this bar's crop sees a short stroke at its left edge with no context |
| detector: a head class at low confidence, on a line | 20 | `noteheadHalfOnLine` 11, `noteheadBlackOnLine` 6, `noteheadHalfInSpace` 2, `noteheadWholeOnLine` 1 (18 of 20 "on a line": the tail lies along a staff line); conf 0.27-0.58, inside the real heads' range (2.160) |
| `too_narrow` never met | 20 | the floor is for `noteheadBlack*` only: 14 are hollow/whole classes; the 6 black boxes are 1.68-2.24 sp wide |
| dot rule (2.59) and `on_a_barline` never met | 20 | boxes 0.78-2.69 x 0.44-1.81 sp, none <= 0.75 on both sides; `on_a_barline` is asked only inside the dot rule |
| slash (2.49/2.137) never asked | 19 | no `Q.NOTEHEAD_STEM_CROSS_INK` row: no stem crosses the box (17 have no stem at all) |
| rest twin (2.142), rest shape (2.145) | 20 | no rest box under any; none rest-shaped. The 2.150b stroke test reads rest boxes only |
| re-centre (2.115) never moved the box | 20 | declined `box_already_head_sized` 16, `below_threshold` 3, no row 1 |
| no ink cut separates them | 20 | staff-erased ink 0.22-0.86 (2.160: real heads reach down to 0.486) |

**Then later readers used them as notes:** pitch `position_and_clef` 20 of 20 (an invented pitch); duration decided
from the class (`head_and_marks`) 16 (12 halves, 3 quarters, 1 whole), `stem_value_follows` 1 (a half-classed tail on
a real stem, Brahms `18/1/3/5/19`, gave its two real stem mates a dotted half), narrowed 3; alone in the bar 2 -- one
is 2.158 tile 14 (`5/1/4/2/1`), guessed a half by `OMR_LONE_EVENT_FILLS_BAR`.

Crops, one per mechanism (blue = our head box, orange = the previous bar's arc box): `out/print/2.164-why/` (1 the tie
cut at the barline; 2 hollow class so no width floor; 3 black class wider than the floor; 4 written as a half; 5 a
barline sliver, already refused; 6 the control, a box holding a real head).

### 17.3 The fix, built OFF: `OMR_ARC_TAIL_NOT_A_HEAD`

* **GATHER** `gather.gather_head_oval` (a new function; its single call line in `gather()`, after
  `gather_notehead_stem_cross_ink`, is the one edit outside new functions in `gather.py`) files `Q.HEAD_OVAL` on every
  notehead box starting within 0.5 sp of its bar's left edge, from the pure `head_oval.oval_width` on the PAGE raster:
  per pixel column, a run of ink lying wholly on a staff/ledger line's rows is left out (a line THICKENED by a head's
  outline is kept); a column is head-tall when its ink spans >= 0.5 sp; the value is the widest run of head-tall
  columns, in staff spaces.
* **ADJUDICATE** `notehead_precision._arc_tail_refusal`, reason `is_an_arc_tail` (after the shape rules, before the
  same-mark rules), refuses only when ALL THREE hold: the box starts within 0.5 sp of the bar's left edge; a tie/slur
  box in the PREVIOUS cell of the staff ends within 0.4 sp of that cell's right edge (the crop cut it) and overlaps the
  box's rows (+-0.5 sp); and the oval width is under 0.625 sp (half a standard head). Margin filed. Any missing
  witness (no row, a system's first bar, no arc) keeps the box.
* **Separation** (`probe/oval_sweep_2_164.py`, swept head-tall 0.5-0.7 sp and slack 0.1-0.25 sp; chosen 0.5 / 0.25):
  the 20 eye-tails 0.25-0.59 except one at 1.14 (Litolff `13/1/4/2/2`, kept: an error only toward keeping); the 8
  boxes on real heads 1.42-1.78; **Sean's 189 valued heads >= 0.688**; his non-heads and rests reach down to 0.33 /
  0.56 (outside the rule's domain). The gap under the real heads is thin (0.59 -> 0.688): a narrow cut, which is why
  the cut arc and the left edge are also required. Known blind spot (synthetic test): a hollow head in a space whose
  outline thickens the two lines by only 1-2 px reads thin; none among Sean's 189.
* Tests `tools/omr/tests/test_staged_arc_tail_2_164.py` (18): the measure (filled head on a line, hollow head merged
  into the lines, a tail crossing a line, a tail on a barline, declines, flag default); GATHER files only for a
  left-edge head and only while ON; ADJUDICATE refuses the tail and keeps the controls (a real tied-to head at 1.44,
  flag off, no arc, an arc ending inside its bar, an arc on other rows, a head inside the bar, no oval row, a system's
  first bar). Mutations: rule removed -> the refusal test fails; the oval cut opened -> the real-tied-note control and
  the hollow-head test fail. Fast tier 8402 passed, 0 failed; `staged.check` 192.

### 17.4 Reach (`probe/scan_2_164.py` static domain; `probe/replay_2_164.py` review.rerun OFF vs ON, `Q.HEAD_OVAL` injected in the ON arm from the same function on the same page raster)

| | Litolff (whole movement) | Brahms (slice: the 10 systems holding every domain head that stands as a note) |
|---|--:|--:|
| rule domain (left-edge head + cut arc in the previous bar) | 29 (20 stand as notes) | 241 (16 stand) |
| control: OFF arm vs stored | 14,385 agree; 19 differ = exactly the 2.158 guesses (the record predates 2.158 ON) | not faithful on a system slice (no carry from other systems); OFF vs ON only |
| **boxes refused `is_an_arc_tail`** | **7** (`3/1/5/3/1`, `3/1/5/3/3`, `3/1/5/15/2`, `4/0/5/12/14`, `5/1/4/2/1`, `12/1/10/11/4`, `13/0/1/10/9`) | **12** (all 12 eye-tails) |
| other glyphs changed | 0 | 2: the stem mates of `18/1/3/5/19` lose the tail's dotted half (`stem_value_follows` -> narrowed `beam_discounted_uncertain`) |
| real tied-to heads in the domain, kept | 13 (oval 1.14-2.48) | 4 (1.42-1.53) |

Every refused box is one the lane's eye calls a tail; every box holding a head is kept.
**2.158 tile 14** (`glyph/5/1/4/2/1`): OFF a `lone_event_fills_bar` half at E-flat 4; ON refused `is_an_arc_tail`, so
the bar holds no head and makes no lone-event guess (the real half was never boxed: the bar goes unread, not invented).

### 17.5 Sean's judged heads (`python3 -m tools.omr.staged.judged score` on the replay mini records)

Litolff whole: right 138 / wrong 26 / narrowed 8 / abstained 1, **identical OFF and ON, no tile changes**; Brahms slice
identical too. Of the 19 refused boxes only tile 14 is judged (2.158, parsed `other`). **No real note is lost.**

### 17.6 Blind tiles: `out/print/2.164-review/`, 20, answers `{}`

`probe/tiles_2_164.py`, seed 2164: the 18 refused boxes Sean has not judged (Litolff 6, Brahms 12; tile 14 left out as
judged) and 2 CONTROLS, real tied-to notes at a bar's start the rule keeps (Litolff `2/1/1/14/3`, Brahms
`16/0/11/3/7`). One blue box, "Tile N", nothing else ours. Question: "Is the mark in the blue box a note, or not a
note?". Key `out/2.164/tiles-key.json`, apart from the tiles. Litolff `3/1/5/3/1` and `3/1/5/3/3` are two boxes on one
tail.

### 17.7 Limits

Flag OFF; no DECISIONS line from this lane. Brahms was replayed on a system slice, not whole (a whole Brahms replay is
~7 GB); the static scan says the slice holds every standing head the rule can reach. Barline ink with no cut arc beside
it is not refused by this rule (the Brahms barline slivers are already `too_narrow`). A refused box still carries its
stale duration row on the record (unchanged behaviour); it leaves the bar. Litolff `13/1/4/2/2` (a slur tail by eye) is
kept: its box reaches the next head's ink.
