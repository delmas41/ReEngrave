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



## Sec.7. ROADMAP 2.71 -- the tremolo slash is its own mark (2026-10-09)

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
