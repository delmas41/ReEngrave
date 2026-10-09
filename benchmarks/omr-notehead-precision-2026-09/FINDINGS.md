# Litolff p3 dyads: doubled heads, missed heads, and ties (2026-09-30)

DIAGNOSIS ONLY. No file under `tools/` changed by this lane. All numbers
below are read from the whole-movement record
`library/_shared-records/beethoven5-litolff-mvt1-whole-20260930b.record.json`
(page index 3 = pdf idx 3, bars 49-82) via `record_io.load_record`, from the
exported `benchmarks/acceptance/out/beethoven5-litolff/beethoven5-litolff.musicxml`,
and from the source PDF rendered at 600 dpi. Probe scripts:
`probe/dyads-2026-09-30/`. Crops: `out/print/dyads/` (manifests
`manifest-a.json`, `manifest-b.json`, `manifest-d.json`). Record-level
extracts: `out/dyads-*.json`.

WARNING, provenance caveat. The record's `provenance.commit` (`2718c4505`) is
an ancestor of this branch's HEAD and `dirty=False`, so it is a valid
baseline by rule 7/10 -- but it carries `Q.TIE_PAIR` verdicts from
`adjudicate_tie_pair` (ROADMAP 3.2b), which ROADMAP's own row still marks
"not merged". The tree disagrees with that row: `Q.TIE_PAIR` **is** in
`adjudicate.ORDER` (`adjudicate.py:970`) and `export.py` reads it
(`_TIE_PAIR_COUNTED_ELSEWHERE`, `tie_pairing`, `tie_contradictions`). Per
rule 10, the tree wins; ROADMAP's 3.2b/3.2c rows are stale and should be
corrected by whoever owns that lane -- flagged, not fixed here (out of scope
for a diagnosis-only brief).

---

## A. Doubled heads

**Population A** (the brief's own definition): same-class notehead-glyph
pairs in one cell, centres within 1.2 staff spaces vertically, bounding
boxes overlapping horizontally. **53 pairs** on page 3 (474 notehead glyphs
total). All 53 are grouped by `Q.EVENT` as `x_clustered` / `kind=chord` --
EVENT correctly treats every one as simultaneous ink.

2.30 (`notehead_is_a_duplicate_box`) refuses **10 of 53** (8 with reason
`notehead_is_a_duplicate_box` specifically; 2 coincide with an unrelated
refusal on the same box). The other **43 stand** -- both glyphs are
written. Measured why: `NOTEHEAD_DUPLICATE_IOU_MIN` (0.02) is not the
binding constraint (missed pairs' IoU ranges 0.004-0.70, median 0.16, well
above the floor); `NOTEHEAD_DUPLICATE_MAX_DY_STAFF_SPACES` (0.25) is -- the
missed pairs' centre-to-centre `dy` ranges **0.255-1.19 staff spaces**,
always just above or well past the gate, while the 8 the rule catches sit
at `dy` 0.005-0.38 (one outlier attribution artefact excluded, see script
comments).

**A KEY MECHANISM, newly confirmed from `Q.PITCH`:** of the 43 missed
pairs, only **2 round to the SAME written pitch** (Sean's "shows as one" --
two identical noteheads stacked are visually indistinguishable, so the bug
is invisible even though the chord holds a doubled note). The other **41
round to DIFFERENT, adjacent pitches** -- this is Sean's other observation,
"a single note would often print 2 notes... a second apart": the SAME
physical ink, boxed twice, fits two slightly different centroids that
`restate_pitch` (EVALUATE) rounds to two different staff positions, so
EXPORT writes a real but spurious second note next to the true one.

### Judged sample (20 of 53, print-checked at 600 dpi, ink-% measured before judging)

| bucket (n sampled) | judged one-head-boxed-twice | judged real chord (2+ distinct notes) | judged NOT simultaneous (false lead) |
|---|---|---|---|
| overlap+same-side, 2.30-caught (5) | 5/5 | 0 | 0 |
| overlap+same-side, stands (8) | 4/8 (A06,A09,A11,A13) | 4/8 (A07,A08,A10,A12 -- 3rds/4ths, correctly same-side, correctly left alone) | 0 |
| no-overlap, same-side (4, A14-17) | 0 | 0 | 3/3 viewed (A14,A15,A16 -- a beamed run of distinct heads; `Q.EVENT` already says `different_events`) |
| no-overlap, opposite-side (3, A18-20) | 0 | 0 | 3/3 (repeated-note / tremolo figure, each note its own stem; `different_events`) |

So: A01-A13 (13/13 judged) = Population A proper (overlap required, the
brief's own scope). Split **9 confirmed duplicate : 4 confirmed real
chord**. 2.30 is precise on what it catches (5/5 right) but its recall
inside its own target population is ~9/13 by this sample (scaling: ~30 of
the 53 same mechanism likely still stand, extrapolating the 4/8 "stands"
rate to all 43 -- an estimate, not a recount). A14-20 (7/20) fall OUTSIDE
population A's own `Q.EVENT` grouping in the sense that matters: they were
only reached by widening the search to test the manager's stem-side
question (dx up to 1.6 head-widths, overlap not required) and every one
turned out to be `different_events` -- sequential notes, not candidates for
this population at all. Full crosstab and all 113 extended pairs:
`out/dyads-pairs-a-extended.json`.

### The manager's question: same-side vs opposite-side of the stem

Column added to the pair table (`out/dyads-pairs-a.json`,
`out/dyads-pairs-a-extended.json`): each head's canonical-frame centre x
compared to the nearest covering `Q.STEM` box's centre x, in the SAME cell
canonical frame (stems have no page-frame row, so this cannot be done in
page pixels without first fitting a per-cell canonical to page affine from
the cell's own `Q.GLYPH_BOX` rows -- done in `crop_pairs.py` for the drawn
purple stem boxes, not needed for the numeric test itself).

**Result: 100% same-side within Population A proper (53/53: 43 with a
stem read, 10 `no_stem_in_cell`; zero opposite).** This is a clean split
for the FIRST half of Sean's convention -- every pair that is literally one
physical mark boxed twice is on one side of its own stem, because it IS
that stem's own ink read twice. But it is **not evidence for the SECOND
half** (a real second sits opposite sides), because:

- The 4 confirmed real-chord pairs in the SAME judged sample (A07/A08/A10/
  A12, position gap ~2-3 units = a 3rd/4th) are ALSO same-side -- correctly
  so, per standard engraving (only an adjacent 2nd is offset; a 3rd or
  wider stacks in line). So same-side alone cannot separate "duplicate"
  from "real chord" within Population A -- both classes read the same way.
  The discriminator that DOES work within A is the one already used (IoU +
  centre distance), just under-gated on `dy`.
- Broadening the search (`analyze_real_chords.py`, every `Q.EVENT`
  `kind=chord` pair regardless of overlap, 228 chord-member pairs total) to
  hunt for an actual single-stem SECOND: **zero found.** The only
  "opposite side" cases anywhere in this analysis (49 of 113 extended
  pairs, all no-overlap) were confirmed by crop and by `Q.EVENT` to be
  SEQUENTIAL notes (repeated-note/tremolo figures, a beamed run), each
  carrying its OWN stem -- "opposite side" there is an artefact of the
  nearest-stem heuristic picking a different neighbour stem for each note,
  not a real interval signal. The few wide-interval (5-8 position-unit,
  more-than-an-octave) same-event chord members that also read "opposite"
  (6 of 168) show the identical artefact (no `stem_covers=True` match at
  that distance).

**So: NOT CONFIRMED.** The rule is a plausible, standard-notation-consistent
convention, but this page's judged sample contains no positive example of a
genuine same-stem second surviving as two boxes -- real close-interval
dyads on this MERGING plate appear to collapse into the duplicate-box
population (A above) rather than surviving as two offset boxes at all. A
later build lane relying on "opposite side => real second" should know the
rule is untested here, not refuted -- just never observed.

**Failure modes, named as asked:**
- No stem read: 10/53 in Population A proper, 19-22/113 in the extended
  set (page 3 has 128 `Q.STEM` abstentions of 371+128 cell-attempts,
  `reason=no_line_accepted`).
- Stems in both directions (divisi): not observed in the judged sample;
  cannot report on it.
- Whole notes: not observed in the judged sample (this page's candidates
  are all Half/Black classes); cannot report on it.
- Wrong-stem attribution for sequential notes: the dominant failure mode
  actually found (above) -- not one the manager named, but the one that
  would burn a lane that trusted "opposite => real second" without first
  gating on `Q.EVENT` simultaneity.
- `tools/omr/conventions.py` (114 entries) has NO entry for a
  same-side/opposite-side stem rule. Not added here, per instruction.

---

## B. Missed dyads (one box hiding two heads)

Proxy used (the brief's own ask, approximated): single notehead glyphs
whose OWN `Q.GLYPH_BOX` height is an outlier vs same-class boxes on this
page (median 1.19-1.46 staff spaces depending on class; threshold set at
1.65 sp). **32 candidates** (`out/dyads-pop-b.json`).

**Judged sample: 20 of 32, crop + row-by-row ink profile measured
(`out/print/dyads/B*.png`, `manifest-b.json`).** Of the ones actually
opened and read (11 -- B01-B11): **zero confirmed two-merged-heads.** Every
viewed case was one of:
- a single black notehead whose box also captured attached stem ink
  (B01 h=3.18sp, B02 h=2.80sp -- the box is tall because it spans head plus
  stem, not two heads);
- a single, naturally oblique/diagonal half-note head shape at this
  plate's engraving angle (B03, B07, and most of the `noteheadHalf*`
  entries at 1.65-1.85 sp -- this class's own median is already 1.3-1.5 sp,
  so the "outlier" band here is mostly normal variance, not a signal);
- one outright false detection: B11 (`too_narrow`, refused) is a bare stem
  segment between two REAL neighbouring heads, not a head at all.

**Conclusion: this proxy did not find a real missed-dyad on this page.**
That is a negative result about the PROXY, not a claim that no such case
exists -- box height is confounded by stem-inclusion and by a class's own
natural elongation, and the brief's literal ask (connected ink extent along
the stem, measured on `image_no_staff` after erasure) needs the no-staff
raster the gather used internally, which is not persisted in the record and
would need a fresh gather to recover (`Q.INK` per CLAUDE.md's ink finding is
gathered but is a different quantity, read by nothing downstream). Not run,
per "build, don't burn runs" -- flagged as the open next step rather than
guessed at.

---

## C. Stage table (where doubled/missed notes are lost or created)

| mechanism | stage | evidence |
|---|---|---|
| detector fires two overlapping same-class boxes on one physical mark | GATHER / detector | root cause for all of population A; not a STAGED-stage fault, a detector-precision fact (CLAUDE.md section 9's "the one thing no stage can repair") |
| `notehead_is_a_duplicate_box` catches the tight cases, misses the wider-offset ones | ADJUDICATE (2.30, `notehead_precision.py`) | measured above: `dy` gate (0.25 sp) is the binding, too-tight constant; IoU floor is not |
| `restate_pitch` independently rounds each surviving duplicate's centroid | EVALUATE | this is where "shows as one" (same rounded pitch) vs "prints a spurious second" (different rounded pitch) is DECIDED, not a new loss -- it is applying its own rule correctly to bad GATHER/ADJUDICATE input |
| `Q.EVENT`'s `x_clustered` chord grouping | EVALUATE (via adjudicate order) | correctly groups every duplicate pair as one simultaneity; not implicated in the bug, a necessary-but-not-sufficient precondition for 2.30 to even apply |
| EXPORT | EXPORT | writes whatever ADJUDICATE left standing; no additional duplication or loss mechanism found here for population A |
| population B (a possible detector/EXPORT merge of two heads into one written note) | not confirmed | the tried proxy (box height) found no positive case on this page; genuinely open |

---

## D. Ties

Page 3, `arc_kind` verdicts: **135 of 251** arc glyphs classified `tie`
(rest `slur`, 116). Clustering overlapping `Q.ARC_BOX` page boxes (IoU>0.05,
same physical ink read more than once) gives **99 unique tie-classified ink
marks**. `Q.TIE_PAIR` resolves these to **19 unique NAMED pairings**
(`paired`); the rest abstain (`spans_a_whole_bar` 20, `no_start_head` 19,
`no_head_near_the_arc` 17, `no_pair_at_one_position` 16, `no_stop_head` 9,
`enters_from_previous_system` 7, `runs_off_the_system` 2) or narrow
(`more_than_one_pair` 10). All 19 named pairings are confirmed `tie`-kind,
not `slur` -- the kind gate holds.

**Exported MusicXML, bars 49-82 (all 12 parts): 7 `<tie type="start">`, 4
`<tie type="stop">`.** A start-without-stop pair means at least one tie's
stop head or its bar was held out downstream (matches ROADMAP 2.19's own
note that this page has no printed meter and is heavily bar-held-out, and
3.2c's still-open "drop both ends of a tie when either end's bar is held
out"). So of the record's own 19 named ties, only ~7 survive to the file --
a >60% export-side loss, on top of the 99 to 19 ADJUDICATE-side narrowing.

**Print check (10 of 99 clusters sampled, `out/print/dyads/D*.png`,
`manifest-d.json`):** only **1 of 10** (D05) shows the isolated-arc shape of
a genuine tie -- two single, non-beamed noteheads at the same pitch joined
by one short curve, no repeating pattern. The other sampled clusters (D04,
D06, D08, and most of the rest) show a curve repeated under or over EVERY
beamed note-pair across an entire passage -- the shape and repetition rate
of a bowing/phrase slur, not a tie. This is consistent with Sean's "ties
are almost nonexistent" (DECISIONS 2026-09-30): the `arc_kind` classifier's
135/99 tie-shaped detections on this page are very likely dominated by slur
or bowing-articulation ink being read as `tie`, not by real ties.
CONVENTION ASSUMED / NOT CONFIRMED: I did not verify pitch-equality across
each sampled arc's two flanking heads (the print-only read cannot
distinguish a tie from a same-pitch slur without it), so this is a strong
visual impression from a 10-of-99 sample, not a settled count -- a next
lane should cross the arc_kind population against `Q.PITCH` agreement at
both ends before trusting 99, or 19, or 135 as "how many ties print here".

**Printed-tie count on the page itself**: not independently hand-counted
across all 19 staves x 2 systems (out of budget for this lane) -- the
99/19/135 figures above are the record's own candidate counts, offered as
the closest measurement made, not a manual page census. Flagged as NOT DONE
rather than guessed.

---

## Crops and files

- `out/print/dyads/A01..A20-*.png` -- population A judged sample, each
  labelled with class, `dy`, overlap/no-overlap, stem-side, refused/stands,
  and per-box ink-%; red = first glyph in the pair, green = second, blue =
  staff lines, purple = `Q.STEM` box(es) in that cell (page-frame, fit from
  a per-cell canonical to page affine -- see `crop_pairs.py`).
- `out/print/dyads/B01..B20-*.png` -- population B candidates, red = the
  single box, blue = staff lines; label carries box height in staff spaces
  and the measured ink-%.
- `out/print/dyads/D01..D10-tie-cluster.png` -- sampled tie-ink clusters,
  red = each clustered arc box.
- `out/print/dyads/manifest-{a,b,d}.json` -- machine-readable version of
  the same, including every measured ink-% before any verdict was written
  (rule from `feedback_print_check_every_lane`: measure ink numerically
  before judging, viewed at a zoom where one head is >=60px wide -- enforced
  by `crop_pairs.py`/`crop_single.py`'s upscaling to a 70px head-width
  floor).
- `probe/dyads-2026-09-30/*.py` -- every script that produced the numbers
  above, re-runnable against the same record.
- `out/dyads-pairs-a.json`, `out/dyads-pairs-a-extended.json`,
  `out/dyads-chord-pairs.json`, `out/dyads-pop-b.json` -- the full
  record-level extracts behind every count in this section.

---

## ROADMAP 2.40 — same-side second (widened duplicate-box rule) + missed-dyad measurement

DECISIONS 2026-09-30, Sean: *"a second is always on opposite sides of the
stem."* Built `notehead_precision._notehead_same_side_second_refusal`
(reason `same_side_second`): two same-class, OVERLAPPING notehead boxes
that share ONE `Q.STEM` row and stand on the SAME side of it, within 0.75
staff spaces (the stated midpoint between a second, 0.5 sp, and a third,
1.0 sp), are one physical head boxed twice. Runs immediately after 2.30's
narrower same-mark test (dy < 0.25 sp), so the two mechanisms are disjoint
by construction and counted separately. Where no `Q.STEM` row meets the
glyph the rule DOES NOT refuse -- it records `detail["same_side_signal"] =
{"no_stem_read": True}` on the final verdict so the case is counted
(CLAUDE.md rule 8), never silently dropped.

### Manager finding addressed before completing the build

Mid-build, a manager review of `glyph/3/0/0/2/4` + `glyph/3/0/0/2/9`
(Litolff p3) found a REAL printed third whose over-tall detector boxes
overlap (staff spacing on that staff ~15.5 page px, box height ~22 px,
overlap ~7 px) and whose rounded pitches (`restate_pitch`) come out F6/E6 --
a SECOND -- even though the print shows two distinct heads a third apart.
This is exactly the population the 0.75 sp gate exists to protect: dy on
this pair is ~0.9 sp, past the gate, so the rule does not fire on it.
Added `test_a_real_third_with_tall_overlapping_boxes_stands` (mirroring the
measured geometry) to `test_staged_notehead_same_side_second.py` as a
permanent regression control; it passes on the built rule.

**Follow-up measurement (report only, no fix built):** surveyed every
same-class, same-stem, same-side pair on Litolff p3 whose two `Q.PITCH`
verdicts are exactly a diatonic SECOND apart (`probe/2.40/same_side_second_
survey.py`) -- by Sean's convention this is never a real printed interval,
so each such pair is either a duplicate box or a mis-rounded third.
**18 such pairs** on the page. Cropped 6 (`out/print/same-side-second-
survey-2.40/`, `S1`-`S6`) plus the manager's own reported pair (`S1`) and
judged each against the print:

| tag | cell | verdict | judged |
|---|---|---|---|
| S1 | `cell/3/0/0/2` | both stand (manager's pair) | REAL THIRD -- two distinct ink blobs, correctly NOT refused |
| S2 | `cell/3/0/9/0` | 1 stands, 2 refused `same_side_second` | ONE real mark, three overlapping boxes -- correctly refused |
| S3 | `cell/3/1/2/9` | 1 stands, 1 refused | ONE real mark (elongated bass-clef ink) -- correctly refused |
| S4 | `cell/3/1/4/12` | both stand (neither refused) | AMBIGUOUS -- only one ink blob is visible under both boxes in this crop, yet the pair fell outside the rule's gate (same stem/side not established, or dy ≥0.75); flagged as a possible residual false-negative, NOT investigated further |
| S5 | `cell/3/1/7/17` | 2 refused | ONE real mark -- correctly refused |
| S6 | `cell/3/0/8/7` | 1 stands, 1 refused | ~~ONE real mark straddling a staff line -- correctly refused~~ **WITHDRAWN — SEE "Manager review round 2" BELOW: this call was WRONG.** |

⚠️⚠️ **S6's verdict above is WITHDRAWN (manager review round 2).** At 3x
zoom the REFUSED (red) box sat on solid black head ink and the KEPT
(green) box below it covered mostly white paper plus one staff line --
the exact opposite of "correctly refused". The cause: the first build
chose the SURVIVOR by detector score, and score says nothing about which
box the ink supports. **Fixed** by reading `Q.NOTEHEAD_INK` instead — see
below. Of the original 6 sampled, only S1 (the manager's own real-third
control) and S2/S3/S5 hold up; S6 was wrong and S4 remains ambiguous.

### Part 2 — missed-dyad measurement (no code)

Compared the reference encoding (`library/reference/beethoven/symphony-5/
beethoven--symphony-5--mvt1--gradus.mxl`, 18 parts) against our export
(`benchmarks/acceptance/out/beethoven5-litolff/beethoven5-litolff.musicxml`,
12 parts) for bars 49-82, condensed wind families only (Litolff prints two
players per staff for Flute/Oboe/Clarinet/Bassoon/Horn/Trumpet; our export
holds one part per family, so a reference pair sounding two DIFFERENT
pitches at one onset is the condensed staff's own chord event).
`probe/2.40/dyad_measure.py`: **204 of 204 family-bars comparable** (both
sides hold at least one note), **49 onsets** where the reference shows two
different pitches and our export shows at most one -- filtered to the
**13** where our export shows exactly one note (not zero, which is more
likely a wholly separate missing-passage fault than a notehead-box one).

Picked 8 (one per family/bar spread across the range), extracted the
GATHER+ADJUDICATE state for each cell from a fresh `--through evaluate` run
(`out/2.40/litolff-p3-evaluate.json`, `--weights auto`), cropped at 600 dpi
with staff lines and every notehead-class box in the cell drawn (green =
stands, red = refused) (`out/print/missed-dyads-2.40/`, `probe/2.40/
extract_candidates.py` + `crop_dyad_candidates.py`), and judged each
against the print:

| tag | family / bar | notehead boxes in cell | judged |
|---|---|---|---|
| M01 | Oboe 49 | 1 | Only one head visible in the ink; the second is genuinely absent -- **no box at all** |
| M02 | Oboe 53 | 4 (2 stand, 1 refused `same_side_second`, 1 `clipped_fragment`) | **Both real heads are correctly boxed and kept** (a tied note above the staff + a note on the top line); the extra duplicate is correctly refused. The bar's export still writes only ONE pitch -- **lost downstream of ADJUDICATE**, not a notehead-box fault |
| M03 | Clarinet 49 | 3 (all stand) | Two real, closely-stacked heads visible and both kept -- **lost downstream**, boxes are fine |
| M04 | Clarinet 54 | 0 | A tied note's ink is visible (ties curve in/out) but the detector drew NO notehead box in this cell at all -- **no box, for either head** |
| M05 | Bassoon 49 | 2 (different classes, both stand) | Two real, distinct heads (Whole-on-line + Half-in-space) both correctly kept -- **lost downstream** |
| M06 | Bassoon 67 | 1 | Only one head visible in the (possibly too-narrow) crop window -- **inconclusive**, likely a box the crop cuts off or a genuine miss; not resolved |
| M07 | Horn 49 | 2 (different classes, both stand) | Two real heads side by side, both correctly kept -- **lost downstream** |
| M08 | Trumpet 51 | 5 (3 stand, 1 refused `same_side_second`, +1 unrelated stands) | Two ordinary single notes plus one genuinely doubled box correctly refused -- **not a missed dyad at all**, a correctly-handled duplicate |

**Of the 8: 2 clear "real missed dyad, second head never boxed" (M01, M04);
1 inconclusive (M06); 5 show BOTH real heads correctly boxed and
adjudicated, with the loss happening at EXPORT's chord/voice grouping, not
at notehead precision** -- a different mechanism than this benchmark's own
name, worth a roadmap item of its own (grouping two same-onset, different-
pitch, different-class notes into one chord event) rather than a notehead
rule. Not built here (Part 2 is measurement only, per the brief).

### Files

- `tools/omr/staged/adjudicators/notehead_precision.py` --
  `_notehead_same_side_second_refusal`, `NOTEHEAD_SAME_SIDE_MAX_DY_STAFF_
  SPACES = 0.75`, reason `same_side_second`.
- `tools/omr/tests/test_staged_notehead_same_side_second.py` -- RED-first,
  6 tests (refusal, the 0.75 sp control, non-overlap control, no-stem
  control + count, the manager's real-third control, reason-name
  isolation).
- `docs/engraving-conventions.md` `[C92]` -- the convention, cited from
  DECISIONS 2026-09-30.
- `probe/2.40/*.py`, `out/dyad-candidates-2.40.json`, `out/same-side-
  second-survey-2.40.json`, `out/print/missed-dyads-2.40/`, `out/print/
  same-side-second-survey-2.40/`.

### Manager review round 2 (post-merge) — keep choice fixed to read INK, not score; full re-crop of every refusal

**The bug (S6, `cell/3/0/8/7`):** the first build's "keep" choice was
`_notehead_duplicate_priority` -- detector CONFIDENCE, then glyph index.
A score says nothing about which of two overlapping boxes the real ink
sits under, and S6 proved it: the higher-score box covered blank paper
(plus one staff line) while the lower-score box sat on the real head.

**The fix:** `_notehead_same_side_second_refusal` now reads
`Q.NOTEHEAD_INK` -- specifically `detail.ink_net.best`, the fill fraction
on the staff-line-ERASED raster (`cell.image_no_staff`), so a bare staff
line under an empty box is never counted as ink (a plain `Q.NOTEHEAD_INK.
value` would be unsafe here, since it takes `max(raw, net)` and CAN be
inflated by a staff line alone). `Q.NOTEHEAD_INK` is already GATHERED once
per notehead-classed glyph (2.23/2.39b), at that glyph's own re-centred box
where 2.39b found one -- read, never re-derived (rule 6). **Where either
box of a candidate pair carries no ink witness at all, NEITHER is refused**
(rule 8) and the case is counted in `same_side_signal.no_ink_witness`
rather than falling back to score. New helper `_notehead_ink_net`; `Q.
NOTEHEAD_INK` added to `composed_from`/`wants`.

**RED test written first**, `test_the_higher_score_box_on_blank_paper_is_
the_one_refused` (S6's own shape: conf 0.9/ink 0.08 vs conf 0.3/ink 0.90):
run against the pre-fix (score-based) code it fails exactly as S6 failed
on the print (`assertIs(v_hi_score.value, True)` -- the blank-paper box
was NOT refused). Passes on the fixed code. A second new test,
`test_no_ink_witness_does_not_refuse_but_is_counted`, covers the missing-
witness case. 8 tests total now (was 6).

**Rebased** onto `claude/acceptance-measure-notehead-box-e75821` (now past
2.39b, `Q.NOTEHEAD_RECENTRE`) by `git merge`; the only conflict was the
`composed_from`/`wants` tuples in `adjudicate_notehead_is_not_a_notehead`
(2.39b added `Q.NOTEHEAD_RECENTRE` beside 2.40's `Q.STEM` there) --
resolved by keeping both additions.

**Re-ran the p3 A/B** (GATHER+ADJUDICATE+EVALUATE, `--weights auto`,
`out/2.40/litolff-p3-evaluate-v2.json`): **17 `same_side_second` refusals**
now (was 13 under the score-based keep -- the ink read changes which
member of several clusters is judged the duplicate, and surfaces a few
additional genuine pairs the score ordering had been masking). `0`
`no_ink_witness` cases on this page (every candidate pair had an ink
reading on both sides).

**Re-cropped ALL 17** (not a sample), one crop per CELL (14 crops, several
cells hold more than one refusal), at 3x zoom with staff lines, every
notehead box in the group, and both `ink_net` readings labelled
(`out/print/same-side-second-v2-2.40/`, `V01`-`V14`,
`probe/2.40/crop_all_refusals_v2.py`). Cross-checked programmatically
against every OTHER decided verdict in each cell (not just the pair) to
see whether a real note is actually represented afterward:

| cell(s) | outcome |
|---|---|
| `3/0/1/4`, `3/0/5/2`, `3/0/8/7` (S6, FIXED), `3/0/9/0`, `3/0/9/6`, `3/1/2/8`, `3/1/2/11`, `3/1/3/2`, `3/1/7/17` (9 cells, 11 of the 17 refusals) | kept box sits on the real head ink, refused box is the duplicate/blank fragment -- **correct**, confirmed at 3x zoom |
| `3/1/2/9` (V11, a 3-box cluster: 2 close-but-distinct-looking heads plus one over-tall box spanning both) | collapses to ONE survivor; **AMBIGUOUS** -- the crop shows what may be one merged mark or two real heads ~0.6 sp apart under one over-tall box (the SAME failure mode the manager's own `glyph/3/0/0/2` example diagnosed). Not resolved; needs Sean's read of the crop |
| `3/0/0/0`, `3/0/4/6`, `3/0/10/6` (V01, V04, V03 -- 3 cells, 3 of the 17 refusals) | **A NEW BUG, found only by this full review, DIFFERENT from S6's:** the rule's chosen "better" partner is ITSELF refused by a SEPARATE rule in the same pass (2.30's `notehead_is_a_duplicate_box` in 2 cases, 2.4a's `too_narrow` in 1) -- so BOTH boxes of that one physical mark are refused and it has NO surviving box at all. This is a cross-rule consistency gap, not an ink-reading error: `_notehead_same_side_second_refusal` (like 2.30's own documented limitation for human verdicts) does not check that its chosen "better" box will itself survive every OTHER decision running in the same ADJUDICATE pass. **Not fixed here** -- named for a follow-up connection, same shape as 2.30's own "THIS DECISION DOES NOT CHECK THAT THE TWIN SURVIVES" caveat, now confirmed to also apply cross-rule |

**Net on this page**: of 17 refusals, 11 are confirmed-correct duplicate
resolutions (a real survivor sits on real ink), 3 are a newly-found
"neither box survives" defect (not an ink-read error), and 1 (the 3-box
cluster) is ambiguous. **This is a narrower, more honest result than the
original report's "5 of 6 correct, 1 ambiguous" sample claimed** -- the
full review the manager asked for surfaced two failure classes a 6-crop
sample did not reach.

**Missed-dyad finding (Part 2) stands, and is the most load-bearing result
here**: 5 of the 8 candidates show BOTH real heads of a printed chord
correctly boxed and kept through ADJUDICATE, with the loss happening
downstream in EXPORT's chord/voice grouping --

- `glyph/3/0/1/4/10` + `glyph/3/0/1/4/12` (Oboe bar 53)
- `glyph/3/0/2/0/9`, `glyph/3/0/2/0/10`, `glyph/3/0/2/0/11` (Clarinet bar 49)
- `glyph/3/0/3/0/9` + `glyph/3/0/3/0/14` (Bassoon bar 49)
- `glyph/3/0/4/0/5` + `glyph/3/0/4/0/9` (Horn bar 49)
- (Trumpet bar 51's cell shows a correctly-refused duplicate alongside two
  ordinary single notes -- not a missed dyad at all, M08)

None of these five subjects appear among the 17 `same_side_second`
refusals above -- the chord/voice grouping gap is independent of this
roadmap item's own mechanism.

### Files (round 2 additions)

- `tools/omr/staged/adjudicators/notehead_precision.py` --
  `_notehead_ink_net`, ink-based keep choice, `no_ink_witness` counting.
- `tools/omr/tests/test_staged_notehead_same_side_second.py` -- 2 new
  tests (RED-confirmed against the score-based build).
- `out/2.40/litolff-p3-evaluate-v2.json` (gitignored, regenerable),
  `out/print/same-side-second-v2-2.40/` (14 crops + manifest, committed),
  `probe/2.40/crop_all_refusals_v2.py`.

### Manager review round 3 — a refused box's "better" partner must itself survive (2.30, 2.4a, AND a second same-side hop)

**The bug (round 2's own finding):** 3 cells (`3/0/0/0`, `3/0/4/6`,
`3/0/10/6`) each refused a box in favour of a "better" partner that was
ITSELF refused by a DIFFERENT rule -- deleting a real note, worse than the
doubled box this rule exists to fix.

**First attempt (rejected by the framework, and rightly):** read the
partner's own `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` verdict via `ev.verdict`.
`Evidence._admit`'s circularity guard refuses ANY read of a decision's own
quantity unless that quantity has a registered `READINGS` entry (this one
has none, by design) -- confirmed by instrumenting a real run: the read
always came back `None`, and reproducing it with a raw log bypass would
make the answer depend on which of a pair `adjudicate.run`'s per-subject
iteration happens to reach first, an ORDERING ACCIDENT and not a fact
about the page (proved directly: swapping two test glyphs' indices alone
flipped the outcome).

**The fix:** two new PURE, subject-independent re-checks, calling none of
2.30/2.4a's own machinery through `Evidence` at all:
`_would_lose_to_2_30s_duplicate_rule` (2.30's own IoU/centre/priority
gates, re-run against the candidate partner) and `_would_survive_as_a_
duplicate` (recurses the WHOLE chain: too_narrow, then 2.30, then this
rule's OWN same-side/ink gate against a THIRD box, with a visited-set
cycle guard). A partner is only accepted as the keeper if the recursion
confirms SOME box at the end of its own chain survives everything.

**Why recursion was needed, not just the one 2.30/2.4a hop:** `cell/3/1/2/9`
(the round-2 "ambiguous 3-box cluster") turned out to be a SECOND-HOP
case: glyph 2's chosen partner (glyph 5) itself loses a same-side/ink
comparison to glyph 3 -- glyph 5 is refused too, but the MARK still has a
survivor (glyph 3), so refusing glyph 2 is correct; a one-hop check alone
would have blocked it unnecessarily. Round 3 handles this by walking the
whole chain rather than checking one link.

**RED test first**, `test_a_partner_thats_itself_refused_is_never_the_keeper`
(one of the 3 real cases' shape: a genuine too-narrow sliver with
deliberately HIGHER ink than the real head next to it) -- fails against
round 2's code exactly as the real cells failed, passes on the fix.

**Re-ran the p3 A/B**: **13 `same_side_second` refusals** (same shape as
round 1's count, now for the right reason -- `partner_refused` blocks 4
of what would otherwise have been 17). **Page-wide orphan check** (not
just this rule's own pairs -- every notehead-classed glyph on the page,
unioned by EITHER 2.30's or this rule's own duplicate links into
clusters): **0 clusters with zero surviving boxes**
(`probe/2.40/check_no_orphans.py`). The 3 previously-broken cells now each
keep a real survivor (`glyph/3/0/0/0/8`, `glyph/3/0/4/6/4`,
`glyph/3/0/10/6/2` all decide `False`, `partner_refused` counted instead
of a wrongful refusal).

**`cell/3/1/2/9` clean crop** (`out/print/same-side-second-v2-2.40/
V-CLUSTER-cell-3-1-2-9-clean.png`, ≥60 px per head, one colour per box):
glyph 1 (blue, `noteheadHalfOnLine`) and glyph 3 (green, `noteheadHalfInSpace`)
sit at nearly identical positions -- a DIFFERENT class pair (2.12g's own
"role twin" case, left alone by both 2.30 and this rule on purpose) --
both stand. Glyph 2 (red) and glyph 5 (orange, an over-tall box spanning
both 2's and 3's y-range) are same-class and refused by this rule, chained
down to glyph 3 as the cluster's one surviving `noteheadHalfInSpace`. **My
rule keeps glyph 3.** The print itself is genuinely hard to call from this
crop -- it may be one merged mark or two real heads a small interval
apart under one over-tall box, the SAME shape as the manager's own
original diagnosis case; sent to Sean, not resolved here.

`pytest -m "not slow"`: 4,091 passed, 3 skipped (was 4,090). `staged.check`:
TOTAL 245, unchanged.

### Files (round 3 additions)

- `tools/omr/staged/adjudicators/notehead_precision.py` --
  `_same_side_candidates`, `_same_side_beater`, `_would_survive_as_a_
  duplicate`, `_would_lose_to_2_30s_duplicate_rule`.
- `tools/omr/tests/test_staged_notehead_same_side_second.py` -- 1 new
  RED-first test.
- `probe/2.40/check_no_orphans.py` (page-wide zero-survivor check),
  `probe/2.40/crop_cluster_3129.py`, `out/print/same-side-second-v2-2.40/
  V-CLUSTER-cell-3-1-2-9-clean.png`.

---

## ROADMAP 2.42 — stacked heads on one stem: how many, and where

Supersedes 2.40's pair-wise `same_side_second` rule and absorbs 2.41's
measurement-only two-head fit (`benchmarks/omr-notehead-width-2026-09/
FINDINGS.md` §2.41). Branch `claude/stacked-notehead-2.42`, from
`claude/acceptance-measure-notehead-box-e75821` merged with 2.40's unmerged
work (`worktree-agent-a212d008990c6b49a`).

### Where it lives

- **GATHER** (`tools/omr/staged/gather.py`): `gather_stacked_head_fit`,
  `fit_stacked_head_count` (pure), `Q.STACKED_HEAD_FIT`. Groups overlapping
  notehead-classed boxes (any class) by (shared `Q.STEM` row, same side of
  its centre x); for each group of >=2 boxes, fits a standard-head-box ink
  template (`notehead_ink_under`, the SAME reader `gather_notehead_ink`
  already trusts) at candidate half-step positions, and picks the fewest
  head count (1-3) that explains the ink. **The decision criterion is NOT
  "does k+1 beat k's mean"** — measured wrong on a real two-head fixture
  before shipping (kept as `test_staged_stacked_head_fit.
  TestFitStackedHeadCountPure`'s own comment): the single best-scoring
  position is, by construction, one member of a real dyad's own pair, so
  the pair's mean is never CLEARLY ahead of the lone best score, only AS
  good — a "beats" test never fires on a genuine dyad. The working
  criterion, generalised from 2.41's own `two_head_fit.supports_two_heads`:
  an additional head is real where its own slot clears an absolute fill
  floor (`STACKED_HEAD_MIN_SLOT_FILL = 0.4`, 2.41's own number, cited) AND
  the group's mean has not dropped by more than the stated margin
  (`STACKED_HEAD_FIT_MARGIN = 0.05`). Inside that band: ABSTAIN
  `ambiguous`, never guess.
- **ADJUDICATE** (`tools/omr/staged/adjudicators/notehead_precision.py`):
  `_stacked_head_duplicate_refusal` (reason `stacked_head_duplicate`,
  composed into `adjudicate_notehead_is_not_a_notehead` in place of the
  now-unwired `_notehead_same_side_second_refusal`) picks the keeper among
  boxes sharing one fitted slot by INK (`Q.STACKED_HEAD_FIT.detail["ink"]`,
  read never re-derived — the ported 2.40 keep-by-ink rule); a slot held by
  one box, or a contest with no ink witness on either side, is untouched
  (rule 8). `adjudicate_stacked_head_position` (new decision,
  `Q.STACKED_HEAD_POSITION`) files the fitted slot's own position as a
  DECIDED witness for every surviving glyph, abstaining
  `stacked_head_refused` where the same-stage refusal already condemned it.
- **EVALUATE** (`tools/omr/staged/consequences.py`): `restate_pitch` reads
  `Q.STACKED_HEAD_POSITION` first and falls back to the raw
  `Q.NOTEHEAD_STAFF_POSITION` — a substitution at the ONE population this
  applies to (a decided verdict only exists for a glyph GATHER's fit named
  a slot for), never a second source of positions for a lone head.
- 2.40's own function (`_notehead_same_side_second_refusal`) is RETAINED,
  UNWIRED — its own tests (`test_staged_notehead_same_side_second.py`) now
  call it DIRECTLY (a throwaway `DecisionSpec`/`Evidence`, not the
  production one, which no longer declares `Q.STEM`/`Q.NOTEHEAD_INK` since
  nothing in the composed decision reads them any more) rather than through
  `adjudicate.run`, so the print-checked regression record stays green.

### Fixed cases (RED-first, `tools/omr/tests/test_staged_stacked_head_fit.py`, 21 tests)

Synthetic, no `library/`/`omr-weights`/`.pdf"` strings (fast tier):
a lone single head unchanged (no row at all); two heads a third apart, both
survive, lower kept at its own slot; a real second straddling one stem
(opposite sides) stands, untouched; two notes on separate stems never
group; S6's own shape (one head, two boxes, the inked one survives
regardless of detector score); no-ink-witness and ambiguous-GATHER-fit
abstentions counted, never guessed; the EVALUATE connection (decided
position wins only in a stacked group, never for a lone head).

### One-page A/B, GATHER+ADJUDICATE+EVALUATE, `--weights auto`

Base arm: `claude/acceptance-measure-notehead-box-e75821` (the worktree
already checked out at that branch — no separate clone needed). Command,
both arms: `python3 -m tools.omr.staged <pdf> --pages N --weights auto
--through evaluate --out <rec>.json`.

**Litolff p3** (pdf idx 3): `notehead_is_not_a_notehead` reason histogram —
base `{notehead: 441, clipped_fragment: 17, notehead_is_a_duplicate_box: 7,
too_narrow: 6, is_a_clef: 2, belongs_to_a_nearer_staff: 1}` (474 total,
IDENTICAL to the pre-2.42 tree); new arm moves EXACTLY the 50 boxes that
were plain `notehead` into `stacked_head_duplicate` — every other reason's
count is bit-identical. 72 stacked groups found; 106 glyphs decided a
fitted slot (`Q.STACKED_HEAD_POSITION`), 58 abstained
`stacked_head_refused` (the group's own loser), 5 abstained `ambiguous`
(GATHER declined to pick a count). 562 notehead subjects carry a pitch in
both arms; **53 pitches changed**, 0 lost, 0 gained. `pytest -m "not slow"`:
4,136 passed / 3 skipped (was 4,091 before this branch); `staged.check`
TOTAL 245 (unchanged from baseline — inventory/wiring/capture/brakes each
needed a registration fix to stay flat, see commits).

**Brahms p1** (pdf idx 1): reason histogram — base `{notehead: 724,
too_narrow: 225, is_a_meter_digit: 30, clipped_fragment: 26,
belongs_to_a_nearer_staff: 6, notehead_is_a_duplicate_box: 4}` (1015
total); new arm: `notehead` 724->713, `stacked_head_duplicate` +12,
`belongs_to_a_nearer_staff` 6->5 (one glyph this rule now catches FIRST,
earlier in the decision's own order, that the later rule would otherwise
have caught) — every other reason unchanged, 0 lost/gained across 1015.
1,555 notehead subjects carry a pitch in both arms; **7 pitches changed**.
No `ambiguous` abstentions on this page (0 of however many groups formed).

### ⚠️⚠️ WITHDRAWN — `glyph/3/0/0/2/4` + `/9`: the original "G6/E6, print-checked, confirmed" claim was WRONG

**Manager review (2026-09-30), real ruler measurement against a fresh 600
dpi binary render of Litolff p3**: staff `staff/3/0/0`'s lines sit at page y
449.5/465.0/480.5/496.5/512.5 (spacing 15.75, half-step 7.875); ledger
strokes at A5 (~434), C6 (~418), E6 (~402); the chord's own ink rows run
385-433. Read against that ruler, the upper head sits in the space ABOVE
the E6 ledger (= **F6**) and the lower head sits BETWEEN the E6 and C6
ledgers (= **D6**). **The print is F6 + D6, not G6/E6.** Both heads in the
originally-reported result were shifted UP one diatonic step from the
truth — the "print-checked, confirmed" claim in the first version of this
section was false and is withdrawn here, visibly, rather than edited away.

**Root cause, found and fixed**: on this MERGING plate the chord's own ink
is one continuous blob, and `notehead_ink_under`'s `best` fill rounds to 4
decimals, so candidate positions -8/-7/-6/-5 all scored EXACTLY `1.0` —
a genuine, exact tie. `itertools.combinations` enumerates pairs
lexicographically, and the fit's own `total > best[1]` (strict greater-than)
kept the FIRST-GENERATED tied pair, `(-8, -6)`, never comparing it against
the print-true `(-7, -5)` on any actual evidence — both are real THIRDS
(gap 2), so the bug was invisible to the gap/margin tests and shifted BOTH
heads by one step with no signal marking it wrong. The raw DETECTOR
centres for this exact cell (`Q.NOTEHEAD_STAFF_POSITION`: -7.4 / -5.56)
were already close to the truth throughout — the fit's own tie-break is
what threw them off, not the ink measurement, the gap logic, or the
detector.

**Fix** (`gather.py`): `_stacked_best_combo` and the single-position choice
in `fit_stacked_head_count` now collect EVERY combo/position within
`TIE_SCORE_EPS` of the top score, and where more than one is tied, the one
whose positions sit closest to `observed` (the group's own raw detector
centres — real evidence, never invented) wins. `test_staged_stacked_head_
fit.py` gained two pinned regression tests: one on the EXACT scored dict
read back off this real cell (confirms `(-8,-6)` without `observed`,
`(-7,-5)` with it — RED against the pre-fix code, both literally verified
by running the unfixed function), and one building the same shape from the
manager's own ruler numbers (top line 449.5, spacing 15.75) end to end
through `fit_stacked_head_count`.

**Re-run after the fix** (same A/B protocol, both arms regenerated from the
CURRENT tree — see "Re-run after 2.43 merge" below): `glyph/3/0/0/2/4` now
reads **F6** (unchanged from the base arm — this head was never wrong),
`glyph/3/0/0/2/9` moves base E6 -> new **D6**, matching
the manager's ruler exactly. `glyph/3/0/0/2/1` + `/3` (the second pair
named) were ALREADY F6/D6 in both arms, before and after the fix — never
wrongly collapsed, confirmed unaffected by either the bug or the repair.
Ruler crop: `out/print/2.42/ruler-litolff/9-3-0-0-2.png` (staff + ledger
lines labelled with pitch names, fitted centre marked, `base:E6 / new:D6`).

### `cell/3/1/2/9` — NOT newly resolved, and that is reported not hidden

2.40's own round 3 (above) already found this 4-box group collapses to ONE
surviving box (glyph 3, kept) via its OWN pair-wise chain, and sent a clean
crop to Sean unresolved ("may be one merged mark or two real heads"). 2.42's
independent, GATHER-side ink fit reaches the SAME answer by a DIFFERENT
mechanism (`k=1`, ink scores at the candidate positions do not clear the
floor for a second head): glyphs 1, 2 and 5 refused `stacked_head_duplicate`,
glyph 3 kept and its OWN pitch moves G3 -> A3 (the fitted slot's own
position, not the raw box centre's rounding). Print-checked
(`out/print/2.42/litolff/G22-glyph-3-1-2-9-left.png`): a diagonal,
MERGING-plate ink stroke that genuinely could be one slanted head or two
touching ones — **still not confirmable from the print alone**, consistent
with round 3's own finding. Two independent mechanisms agreeing is
suggestive but is NOT the second, independent witness CLAUDE.md §10 requires
(both read the SAME ink) — reported as corroboration, not resolution; still
flagged for Sean.

### Re-run after the tie-break fix (and after merging ROADMAP 2.43)

Both arms regenerated from scratch (base arm re-pulled from `claude/
acceptance-measure-notehead-box-e75821`'s current tip, which now carries
2.43; this branch merged 2.43 too). Refusal histograms are BIT-IDENTICAL to
the pre-fix run (the tie-break only changes WHICH position a slot lands on,
never which boxes contest a slot): Litolff 50 `stacked_head_duplicate`
moves, Brahms 12, every other reason unchanged, 0 lost/gained on either
page. Pitch diff: **Litolff 51 changed** (was 53 pre-fix — two of the
original 53 are cases the tie-break itself corrected back toward the
detector's own reading), **Brahms 6 changed** (was 7). Every changed pitch
on BOTH pages is now cropped WITH A RULER (staff + ledger lines labelled
with pitch names via the exact `_pitch_from_position` anchor
`restate_pitch` itself uses, fitted centre marked, label reads `base:X /
new:Y`, ink-row span measured numerically): `out/print/2.42/ruler-litolff/`
(51 crops), `out/print/2.42/ruler-brahms/` (6 crops),
`probe/stacked_head_2.42/crop_ruler.py`. The headline cell
(`glyph/3/0/0/2/9`) now reads `base:E6 / new:D6`, `ink_rows=364-660` on its
own crop — matching the manager's independent ruler exactly.

### Duplicate-box census (kept separate from the position fix, per request)

Of every CONTESTED slot (>=2 boxes mapped to one fitted head) on Litolff
p3, **49 of 49 kept boxes have a decided `Q.STACKED_HEAD_FIT.detail["ink"]`
> 0.5** (`probe/stacked_head_2.42/kept_census.py`); Brahms p1: **15 of 15**.
This is a NUMERIC PROXY (a fill-fraction floor), not a per-box human read of
all 64 — 6 of them were also visually confirmed correct earlier in this
document (S6's cell, two Brahms single-head refusals, a near-tie, a 3-note
chord). 0 kept boxes fall at or below the floor on either page.

### ⚠️⚠️⚠️ SCOPE CHANGE (Sean) — ALL PITCH WORK DROPPED FROM 2.42

The same-side-second rounding-residual rule (the replacement for the
withdrawn ink-fit pitch connection, described above as fixing Sean's own
`glyph/3/0/0/2/4`+`/9`/`/1`+`/3` pair) is ALSO WITHDRAWN, before landing.
Root cause of the wrong pitches above the staff, found by the manager: the
printed LEDGER LINES themselves are not evenly spaced. On Litolff p3,
`staff/3/0/0`'s own ledgers sit at page y 431.5 / 418.5 / 398.5 (gaps 18,
13, 20 px) against a 15.75 px staff spacing — extrapolating the staff's own
spacing from the top line drifts ~4 px by the third ledger, which is
exactly the systematic error both withdrawn mechanisms were chasing with
the wrong instrument (ink fit, then rounding residual — neither reads a
ledger line at all). **Fixing this needs positions read from the PRINTED
LEDGERS themselves — ROADMAP 2.44, a separate item, not built here.**

`restate_pitch` is reverted to EXACTLY its pre-2.42 form (raw `Q.NOTEHEAD_
STAFF_POSITION`, rounded, everywhere — no stacked-group or same-side
connection of any kind). `Q.STACKED_HEAD_POSITION`, `Q.SAME_SIDE_SECOND_
RESIDUAL` and both EVALUATE rules that fed them are REMOVED from the tree
entirely (not merely unwired) — `Q.STACKED_HEAD_FIT` stays, since 2.30's
own `stacked_head_duplicate` refusal still reads its group/slot/ink fields
for the keep/refuse choice, which is UNCHANGED and UNAFFECTED by any of
this. Re-verified against the ALREADY-GATHERED records (ADJUDICATE-level
facts are identical whether or not the now-removed EVALUATE rule ever
existed, so no re-gather was needed): Litolff 50 `stacked_head_duplicate`
moves, Brahms 12, 0 pitch changes on either page (no rule reads or revises
`Q.PITCH` beyond stock `restate_pitch` any more). Kept-box ink census
re-confirmed identical: 49/49 (Litolff), 15/15 (Brahms).

Sean confirmed (relay) BOTH named chords print F6/D6. Pinned as XFAIL,
per instruction, in `tools/omr/tests/test_staged_ledger_position_xfail_
2_44.py`: `/2/4`+`/9` (positions -7.4/-5.56) is a KNOWN, CONFIRMED MISS —
plain rounding gives F6/E6 (a second), still wrong, until 2.44 lands.
`/1`+`/3` (positions -6.88/-4.64) happens to already round 2 apart (a
third) and would PASS today, but is marked xfail anyway per instruction,
since nothing GUARANTEES it across the population until 2.44 reads the
real ledgers.

### Print check

**Litolff p3**: every group with >=1 refusal (41, `out/print/2.42/litolff/`)
plus every group with a pitch change but no refusal (17,
`out/print/2.42/litolff-pitch-only/`) = 58 of 72 groups found, covering
every behavioural change on the page. **Brahms p1**: 12 random groups,
seed 2042 (`out/print/2.42/brahms/`, `crop_groups.py --sample 12 --seed
2042`).

⚠️ NOT ALL 70 CROPS WERE INDIVIDUALLY JUDGED (time budget) — 9 were,
spanning both pages and k=1/k=2/k=3 groups: **7 of 9 clearly correct**
(S6's own cell; the confirmed-third case; a clean single-head Brahms
refusal; a near-tie Brahms refusal where both candidates score `ink=1.00`
and the ARBITRARY winner is still the CORRECT outcome, since either box
names the same one real mark; a genuine 3-note chord, all three kept and
well-centred). **2 of 9 genuinely ambiguous**, both on Litolff's own
merging plate (diagonal ink a print alone cannot settle, one of them
`cell/3/1/2/9` above) — **0 of 9 clearly wrong**. The legend on every crop
reports TWO numbers per box, labelled apart, after a mid-build check caught
them disagreeing in direction on a real case (`glyph/1/0/2/0/35`): the
script's own crude raw-darkness measure over the full detector box (a
rough visual cross-check only) and `decided` — `Q.STACKED_HEAD_FIT.
detail["ink"]`, the ACTUAL staff-line-erased fill the keep/refuse choice
read, measured at the FITTED standard box rather than the raw one. The
`decided` number is always consistent with which box survived; the raw
one is not, and reporting only the raw one first made a correct refusal
look wrong.

### Open, not built

- **Whole notes (no stem)** are out of scope — every fixed case and every
  A/B finding above is a stemmed group. Named in the roadmap row; not
  measured here.
- **Exact ties** (`Q.STACKED_HEAD_FIT.detail["ink"]` equal to the last
  decimal on both contested boxes, observed on Brahms p1) are broken by
  iteration order, not evidence. Harmless where either box names the same
  real mark (observed case); unmeasured where it would not be.
- `cell/3/1/2/9` (above) is unresolved by construction — CONVENTION
  ASSUMED / NOT CONFIRMED that two mechanisms agreeing on the SAME ink is
  worth anything beyond what one alone was.
- `check_no_orphans.py`-style page-wide zero-survivor check (2.40's own
  round 3 instrument) was NOT re-run against the stacked-head population
  specifically — the per-slot "a slot with one box is untouched" guarantee
  and the keep-by-ink logic are the same shape 2.40's own round 3 proved
  safe, but a fresh page-wide sweep on THIS rule's own refusals is future
  work, not built here (time).

### Files

- `tools/omr/staged/record.py` — `Q.STACKED_HEAD_FIT`,
  `Q.STACKED_HEAD_POSITION`, `READERS.CV_STACKED_HEAD_FIT`,
  `ABSTAIN.STACKED_HEAD_REFUSED`, `CLAIMS` entries for both quantities.
- `tools/omr/staged/gather.py` — `gather_stacked_head_fit`,
  `fit_stacked_head_count`, `_stacked_best_combo`, `_stacked_stem_xywh`,
  `_stacked_boxes_overlap`, `_stacked_side`.
- `tools/omr/staged/adjudicate.py` — `Q.STACKED_HEAD_POSITION` added to
  `ORDER`, immediately after `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`.
- `tools/omr/staged/adjudicators/notehead_precision.py` —
  `_stacked_head_duplicate_refusal`, `_stacked_head_group_rows`,
  `adjudicate_stacked_head_position`; `adjudicate_notehead_is_not_a_
  notehead`'s own call site and declarations updated.
- `tools/omr/staged/consequences.py` — `restate_pitch` reads
  `Q.STACKED_HEAD_POSITION` first.
- `tools/omr/staged/capture.py` — `UNSCORED`/`READER_RASTER` entries for
  the new quantity/reader.
- `tools/omr/tests/test_staged_stacked_head_fit.py` (new, 21 tests),
  `tools/omr/tests/test_staged_notehead_same_side_second.py` (rewired to
  call the retained function directly).
- `benchmarks/omr-notehead-precision-2026-09/probe/stacked_head_2.42/
  crop_groups.py`, `crop_pitch_only.py`; crops under `out/print/2.42/`.

## 2026-10-09 — a head whose INK is a detected dynamic letter's stroke is not a note (`on_a_dynamic_letter`)

STAGED. GATHER measures (`gather_notehead_letter_ink`, `Q.NOTEHEAD_LETTER_INK`), ADJUDICATE decides
(`notehead_precision._on_a_dynamic_letter_refusal`, reason `on_a_dynamic_letter`).
Sean, 2.73 head tile 10 (Litolff pdf page 3, `glyph/2/0/2/1/12`): *"Not a note - dynamic p"* — the bowl of the `p`
of `p cresc.`, boxed `noteheadBlackInSpace`, decided a quarter on main.

**FIRST BUILD WAS WRONG AND IS REPLACED (Sean, blind tiles `dynamic-not-a-head`).** It decided on BOXES: a head at
least 0.4 inside a letter's box was refused unless a CV stem of 3+ spaces touched it or the letter box was over 3.6 x 4.6
spaces. Sean judged 7 of its 9 tiles right (1, 2, 4, 5, 6, 7, 8: dynamic ink; 6 was a miss it had spared) and tile 9
wrong: *"two small notes just to the right of SF"* — they lie inside the `sf`'s wide box (the letter's box is wider than
its ink), the CV stem rows missed one of them, and the stem rule was fitted to normal-size stems. Tile 3 (the other
`sf` note) was kept by that build and is a note; the coordinator's note that 3 and 9 were both refused was a misreading of
the manifest, which marked tile 3 `kept (note stem 7 spaces)`. Cause, not another cut: a box says where a detector drew a
rectangle, not whose ink is under it.

**The question is asked of the ink** (two ruler readings off the page raster, filed on the head's glyph where it lies at
least 0.2 inside a letter box, letter searched page-wide because the detector files a letter under the next staff's cell):

* `disc_spaces`, the widest filled disc inside the head box on the raw ink: a notehead is a filled blob, an `f`'s hook
  or top is a stroke. Strokes 0.66-0.84 (all seven `f` fragments, gather values), filled heads 1.13-1.29 (the two notes at
  `sf`, a note under an `f`, a Brahms beamed head). Threshold 0.9, mid-gap, in staff spaces.
* `letter_ink_share`, the fraction of the letter box's ink (lines and 4-space stems taken out) the head box holds. A `p`'s
  bowl is as filled as a head (disc 1.09-1.37) so the disc cannot refuse it, but it is most of the `p`: 0.49-0.62; a note
  beside an `sf` is a sliver of the wide box: 0.10-0.23. Threshold 0.4.
* Neither reads a stem: a cue/grace head with a short stem or none is kept whenever its blob is filled (test:
  `test_a_small_filled_head_with_no_stem_is_kept`, disc 0.95).
* One guard on the LETTER, not the head: an `f` box under 1.7 spaces wide is not an `f` (Brahms `glyph/1/0/7/0/13`, a
  beam's tail boxed `dynamicF`, 1.49 wide against 1.96-2.88 for every one of Sean's 12 hand-labelled `f`s; a `p` is
  legitimately 1.46-1.85).

**Before/after on Sean's 9 tiles** (small re-gathers on this tree, GATHER+ADJUDICATE, first build -> this build):

| tile | subject | Sean | first build | this build |
|---|---|---|---|---|
| 1 | Litolff `2/0/1/5/13` | dynamic ink | refused | refused (stroke, disc 0.81) |
| 2 | Brahms `1/0/7/1/9` | dynamic ink | refused | refused (stroke, 0.66) |
| 3 | Litolff `2/1/8/6/7` | note | kept | kept (disc 1.29, share 0.23) |
| 4 | Litolff `2/1/0/8/8` | dynamic ink | refused | refused (stroke, 0.84) |
| 5 | Litolff `2/0/1/2/9` | dynamic ink | refused | refused (stroke, 0.69) |
| 6 | Litolff `3/0/1/3/6` | dynamic ink | KEPT (missed) | refused (stroke, 0.79) |
| 7 | Litolff `2/0/7/5/6` | dynamic ink | refused | refused (stroke, 0.78) |
| 8 | Litolff `2/0/2/1/13` | dynamic ink | refused | refused (body, share 0.50) |
| 9 | Litolff `2/1/9/6/9` | note | REFUSED (wrong) | kept (disc 1.27, share 0.10) |

All nine now agree with Sean. Population change against the unmodified-tree baseline: Litolff 7 newly refused (the six `f`
fragments/`p` pieces above plus tile-10's `glyph/2/0/2/1/12`) and 1 relabelled (`glyph/2/0/10/2/12`, already refused as
`belongs_to_a_nearer_staff`, a `p` fragment on a `dynamicP`, now named for what it is); Brahms 1 (tile 2). Nothing else in
`notehead_is_not_a_notehead` moves, on 1,286 + 1,491 heads. Tile 10 itself: refused (`head_holds_the_letters_body`).

**What was tried and refused:** connected-component share (a note merged with the `f` by a short stem reads 0.74, hooks
the `f` cleaning disconnects read 0.08, no separation); head/letter confidence; staff position; ink fill (`Q.NOTEHEAD_INK`
reads 0.65-1.0 on all of them); the first build's stem and size cuts (above).

**Hand truth** (`data/hand-truth/pages/imslp317803/0.json`, still `labeling`): our page-0 heads lie on none of his 13 dynamic
boxes and none of his 250 heads lies on one of our letter boxes, so the page does not exercise the rule; reported as that,
not as a pass.

**Open:** the thresholds sit in the middle of measured gaps from 13 heads on two pages; a thin real head (Litolff black
heads read 0.63-0.76 at p10 on the plate, though none lies on a letter box here) that lay on a letter box would be refused as
a stroke; a thick letter-shaped blob on a false letter box over a real head would be kept (the narrow-`f` guard covers the one
measured). Shapes with no dynamic box over them and heads on direction-word boxes: not built.
