# Claimed area -- a plan (ROADMAP 2.178)

**Date:** 2026-10-20. **Path:** STAGED (GATHER files the claim; ADJUDICATE
consults it). **Read from:** main `e293dca49`; no code changed, no gather run.
Sean, 2026-10-20: *"if the one page glance sees the brackets it could identify
them and then claim the ink so it couldn't be confused for something else"*,
corrected to *"i meant claimed area"*. Lane 2.177 (the meter object) had pushed
no branch when this was written (`git branch -r` shows none named
`lane-2.177-meter-object`); this plan treats 2.177 as its first step and says
what 2.177 must file so the rest can build on it.

## In plain words

Today we read each bar on its own, and the detector keeps boxing the big
marks of the page as little ones: the bracket and the system's barline become
noteheads (Sean's 2.176 tiles: four brackets, five clefs), the loops of a 6/8
become whole notes (2.173: 53 of the 56 whole notes we wrote were not notes), a
flat of the key signature becomes an eighth rest, the hook of an *ff* becomes a
quarter. Each time we have added one small rule saying "a head is not a head
because it is X" -- there are now about twenty of them, each with its own
numbers fitted on our two plates.

The idea is to turn that around. Read the big marks first, from the whole
page or system: brackets and braces, the system barline, clefs, key
signatures, meters, words and dynamics, hairpins, slurs and ties. When one is
read, it CLAIMS the space it is printed in, and that claim is written on the
record as a plain fact ("this area belongs to the meter at bar 1"). Every
later reader that boxes something inside a claimed area sees the claim and
refuses its box -- marked unread, never re-valued, never invented -- with ONE
rule instead of twenty.

Two things we already learned decide the shape of it. First, a claim must be
the right SIZE: the meter's two numerals are one area and nothing else is ever
printed inside it, but a slur's box is mostly paper over real notes, so a slur
may claim only its own curved stroke. When the hairpin probe blanked whole
boxes it erased the hairpins themselves, and when a "meter column" was read
loosely off the neighbouring staves it was eighteen staff spaces wide and
swallowed eleven real eighth rests. Second, a claim is a FACT, never a
decision: it says where a mark's ink is, not what a box inside it means. Where
two claims overlap, or the claiming mark is itself unsure, the box inside is
narrowed and written blue, never refused on a guess.

What it buys: on the file, tens of bars per movement that stop going red for
a fake event (2.176 released 9 Brahms bars with two such rules; 2.173 took about 50
invented whole notes out), plus the 2.167e real rests a too-wide claim is
losing. What it does not buy: the larger causes of red bars -- symbols never
boxed and wrong note values (2.167c: two thirds of held bars) -- are untouched
by any claim. Its real value is one mechanism in place of twenty patches, one
that a third publisher can confirm or refute as a whole.

---

## 1. Which marks are read first, and may claim

Ordered by how reliably each is read on Litolff (merging) and Breitkopf
(shattering) today. "Reach" is boxes of other families that stand on the mark
and are now refused by a per-pair gate, from the FINDINGS named.

1. **Staff lines and the system's leading barline / bracket / brace column.**
   Geometry (`staff_detector`, `measure_extractor`; `Q.STAFF_LINES`,
   `Q.CELL_BOX`). The leading-edge cut is clean: 23 Brahms head boxes between
   0.00 and 0.44 sp of the first cell's left edge, none between 0.44 and 1.0
   (`head_on_mark.py` docstring; `omr-non-notes-2026-10/FINDINGS.md` §3), 32
   Brahms + 1 Litolff boxes refused, Sean's tiles 4/4 brackets. Barline
   slivers are the largest non-note population of all: `too_narrow` 937 of
   2,042 (`omr-non-notes` §1), 3,037 Brahms ink (`omr-unwritten-notes` §2.167b).
   The bracket itself is NOT read: `bracket_reader.py` has no consumer
   (`omr-bracket-reading-2026-09/FINDINGS.md`), `Q.BRACKET_BLOCK` mirrors
   `system_grouping`'s inference (`gather._gather_bracket_blocks`). The column
   left of the clef is claimable from geometry alone (page-facts §2: only a
   clef stands before the key accidentals).
2. **Clefs.** The CV locator names the head boxes it overrode
   (`gather._occupied_notehead_rows` -> `Q.CLEF_LOCATED.detail
   ["overrode_glyph_subjects"]`; `notehead_precision._is_a_clef`): a CONNECT
   with no measurement, the one gate built as a claim already. Reach: `is_a_clef`
   9 + `on_another_symbols_box` 5 Brahms / 1 Litolff (`omr-non-notes` §1, §4);
   Sean's 2.176 tiles 5/5 clefs. Mid-bar clefs are a lane in flight (2.144).
3. **Key signatures.** The slot window from the first key-shaped box to the
   run's end (`key_slots.key_slot_window`, ROADMAP 2.100; page-facts §2, Sean
   2026-10-12). Reach: rests refused `rest_in_a_key_signature_slot` 21 Litolff /
   20 Brahms, 3/3 right by crop (`omr-unwritten-notes` §2.167e Q2); heads,
   flags, arpeggiati, accidentals through the same window.
4. **Meters.** Template + OCR readers (`gather_meter`, `*_at_bars`);
   2.177 builds the object. Reach: Brahms 39 digit loops written as wholes
   (2.173, `omr-unwritten-notes` §2.167e Q4), ~10 black/half-class loops on
   page 1 (`plan-2-176b` FINDINGS §2.176b), plus the eleven REAL eighth rests
   `rest_is_a_meter_digit` refuses because `key_slots.meter_column` is 497 px
   wide (§2.167d cause D, §2.167e Q2). Litolff: 0 digits boxed as heads.
5. **Rests, beams, tremolo slashes** (within-bar marks, read per cell, not
   from the big picture, but they claim today): rest curls as whole notes
   (25 Brahms, 2.173 `on_a_rest`), `is_a_rest_twin` 24, beam pieces
   (`is_a_beam_piece`, 2.77b), slashes 37 Brahms / 12 Litolff (2.137),
   `tremolo slash` ink 58 / 116 (§2.167b).
6. **Dynamic letters and direction words.** Detector `dynamic*` boxes plus
   the 2.107 letter look (`gather_letter_look`, `Q.LETTER_LOOK_COVER`).
   Reach: the "tremolo / dynamic letter / clef / beam / key slot / meter
   digit" bucket ~150 / ~215 ink (§2.167 Part 2); held-bar sample 1 in 110
   (an *ff* hook; an "e" of *cresc.*, `omr-non-notes` §5). Reliability is the
   weakest of the structural marks: the ink pick was wrong on 2 of 2 narrowed
   tiles (ROADMAP 2.107), and the letter's BOX is wider than its ink (the
   first `on_a_dynamic_letter` build refused two real notes beside an *sf*,
   `notehead_precision.py` §2.76 comment).
7. **Hairpins.** CV reader, 2 -> 106 of 198 wedges exported
   (`omr-hairpin-cv-2026-09/FINDINGS.md` §7b); a hairpin touches nothing
   (§3b). A hairpin exclusion for beams was measured and NOT built: it would
   drop 12 Brahms / 6 Litolff real beams (DECISIONS 2026-10-09, 2.74).
8. **Slurs and ties.** 2.166 reads each arc once per system
   (`arcs_system.py`, `Q.SYSTEM_ARC`): 70 Litolff / 44 Brahms arcs read whole
   across a barline on 8 pages; tails boxed as heads 10 / 10; beam boxes that
   are really an arc 75 / 78 (`omr-arcs-system-2026-10/FINDINGS.md` §3). Its
   ERASE stays OFF: erasing a slur let the CV beam-stroke reader find two long
   new strokes and move 8 heads from one beam level to two (§3, "likely
   wrong"). 2.164's tail gate: 18/18 right on Sean's tiles, reach 7 / 12.
9. **Rehearsal marks, printed bar numbers, volta brackets, tuplet numerals,
   repeat dots.** Printed bar numbers are read (`gather_printed_bar_numbers`);
   a rehearsal letter is explicitly not (`text.py:1546`). Reach: a rehearsal
   "0" as a hollow head, one case (§2.167d E). Unmeasured; last.

CONVENTION ASSUMED / NOT CONFIRMED: the order above is reliability on two
plates and one weights file; a third publisher may reorder 3-4 and 6-8.

## 2. What the claimed unit is: a whole AREA or only the mark's OWN INK

**Area** (nothing else is printed inside the mark's extent, by convention):

- The meter: both numerals, one box (DECISIONS 2026-10-20). The area is the
  numerals' OWN extent on THIS staff, never a column read off sibling staves:
  the 18-space `meter_column` refused 11 real eighth rests (§2.167e Q2), and
  the loose "column of another staff's timeSig box" hit 24 real stemmed chord
  notes (plan-2-176b §2.176b). First note after the numerals: nearest real
  head 1.2 box-widths away, so a margin of half a digit width is the most the
  area may grow.
- The clef: the located glyph's box (`Q.CLEF_LOCATED`), which the locator has
  already fitted to the ink; the F clef's dots lie inside it.
- The key signature: the slot window, level with the staff, from the clef's
  right edge to the run's last accidental (`key_slots.key_slot_window`).
  CONVENTION ASSUMED (page-facts §2): nothing but key accidentals stands
  there; a cancelling natural at a key change is inside the run by the same
  rule. WHAT WOULD FALSIFY IT: a print with a rest or note between a clef and
  a later accidental of one signature.
- The column left of the first clef: system barline, bracket, brace,
  instrument name. CONVENTION ASSUMED (CLAUDE §4, page-facts §2): only a clef
  stands before the key, so nothing musical stands before the clef.
- Printed bar numbers, rehearsal marks, volta numerals: their own text box.

**Own ink only** (the mark's box is mostly paper over other marks):

- Slurs and ties: the traced stroke (`arcs_system.erase_in_cell` already
  limits itself to traced runs inside the arc's own boxes, never a column
  wider than 1.6x the stroke, never inside a protected head box). A tie ends
  ON a head; the head's oval is never the tie's.
- Hairpins: the two thin lines. The hairpin probe's first cut blanked every
  span box and erased the hairpins under them (`omr-hairpin-cv` §5 bug 1);
  `direction_text.letter_hiding_kind` learned the same lesson for words
  (`gather._ink_without_detections`: spans, clefs, rests, dynamics are not
  blanked).
- Barlines inside the system: the vertical stroke only. A note's stem stands
  on a barline (2.155, Sean 2026-10-16), a dot sits beside one, a tie crosses
  one.
- Beams and stems: own stroke (a beam's box holds its heads).
- Dynamic letters and words: the letters' body, read off the ink
  (`Q.NOTEHEAD_LETTER_INK` disc / share), never the detector's letter box
  (the *sf* lesson above). The letter look's `Q.LETTER_LOOK_COVER` is already
  a share-of-the-box's-own-ink number; that is the shape a claim takes here.

**Litolff merging.** One ink component on Litolff holds a head, an accidental
and a beam (`omr-non-notes` §2, §3: 4 of 11 boxes refused on an accidental box
were real heads). So a claim is never "the connected component": on a merged
plate an own-ink claim is the part of the component the mark's own geometry
explains (the accidental's fitted shape, the arc's traced stroke), and the
remainder is UNCLAIMED, never "the rest of the blob". An area claim is safe on
Litolff only where the convention says nothing else is printed there (the
header column, the meter), which is why the accidental rule was rightly dropped
in 2.176 and is not revived here.

**Breitkopf shattering.** One mark becomes several boxes (a rest's curl, a
digit's loop). An area claim catches every fragment at once; an own-ink claim
needs the mark's own reader to have traced the whole stroke (2.166's join).

## 3. How a claim is recorded, consulted and contested

**Recorded: a GATHER fact.** One quantity, `Q.CLAIMED_AREA`, filed on the
STAFF (scope `SELF_AND_DESCENDANTS` reaches every cell and glyph; the clef
precedent `_is_a_clef` reads at `SELF_AND_ANCESTORS` for exactly this reason),
one row per claim: owner kind (`meter`, `clef`, `key_slots`, `leading_column`,
`arc`, `hairpin`, `letter`, `barline`, ...), the owner's row id (the read it
rests on), unit (`area` with a page-px box, or `ink` with the component ids /
mask the owner traced), and the owner's own standing (READ, or NARROWED with
its candidates and margin). It decides nothing: it says where a mark's ink is.
It is filed by the owner's reader in GATHER right after the read, so the
forced ordering is DERIVED from the read as `gather.gather`'s docstring
requires; `wiring --check` and `reach` see it like any quantity
(`docs/staged-internals.md` §3, §5). The record's raster is never changed: a
claim is consulted, not erased (the 2.166 erase side effect is the reason).

**Consulted: one gate, one helper.** `claims.covering(ev, box) ->
[(claim, share)]` where `share` is the part of the box's own ink (not its
area) inside the claim -- the `Q.LETTER_LOOK_COVER` shape, generalised. One
rule in `adjudicate_notehead_is_not_a_notehead`, one in
`adjudicate_rest_is_not_a_rest`, and one each for accidentals, flags, dots,
articulations: `claimed_by:<owner>` with the signed margin (2.106). It sits
where `_is_a_clef` sits now -- before the shape rules, because it cites a read
rather than measuring a shape. A refused box stays a `Q.GLYPH_BOX` row and
export counts it under `not_a_notehead:claimed_by:<owner>` (the existing
accounting equality, `staged/export.py`).

**Contested: never by guessing.** Two claims on one ink (a clef box and a
leading column; a key-run flat and a meter numeral) are both filed. The
consumer asks the EVALUATE question -- does a refusal FOLLOW? If every
overlapping owner is a non-note mark, the box is not a note whichever owner is
right: refused, both owners in `used`. If the owners disagree about something
that matters to the box (one claim is `ink` and does not cover the box's ink,
the other is `area` and does), the covering one decides alone. Nothing picks
between two marks by confidence: 2.172's detector-view merge drops a view box
where another family's production box has `conf >= its own`
(`detector_views.py:201`), which is a guess the register should replace with a
narrowing.

**The claiming mark is uncertain: narrow, do not refuse.** A claim inherits
its owner's standing. The meter numerals located but the numbers unread
(2.177: the area is still claimed, the meter abstains) is a READ claim on the
area: the numerals are there whatever they say. A claim whose owner is
NARROWED (a stacked pair on one staff with no quorum, `_is_a_meter_digit`
without its second gate; a clef the contest left narrowed) narrows the box
instead: `notehead_is_not_a_notehead` NARROWED `{notehead, <owner>}`, written
GUESSED (blue, carrying both) and counted as a near-miss for Sean's tiles
(CLAUDE §4; DECISIONS 2026-10-19 "each note its own colour"). A bar holding
one goes red if it does not add up (2.173). An owner that ABSTAINED files no
claim; the per-pair shape rules still run and the box is judged as today.

## 4. What it protects

- **The first note after a clef, key or meter.** The area stops at the mark's
  own extent, so the note is outside it by construction; the 2.176b controls
  (24 stemmed chord notes at a system's first beat, 3 clef tails, 28 Brahms /
  5 Litolff first-notes 1.2-2.4 box-widths from the numerals) become a
  must-keep test over their glyph keys. Compare `_meter_column_witness`
  (0.8 box-widths of a sibling's timeSig box) and `meter_column` (18 sp),
  both of which reach the first note.
- **A note under a slur or beside a hairpin.** Own-ink claims cannot touch
  it: the head's oval is not the stroke (2.166's protected boxes;
  `_head_oval`). The 2.166 beam-stroke side effect disappears because no
  raster is erased.
- **A note touching a barline.** The barline claims its stroke only; 2.155's
  stem-at-bar-edge stays a stem; `too_narrow` still refuses the sliver on
  shape.
- **Ledger lines.** Never claimed by anything (the ledger names the owner,
  CLAUDE §5); a claim covering a rung is a bug the `ledger_is_not_a_ledger`
  tests must catch.
- **Stems crossing beams, flags on stems.** A beam claims its stroke; the
  stem is the stem finder's (`Q.STEM`). The present `refuse_owned` deletes
  any stroke >= 0.8 inside a clef / key / digit / accidental / flag / REST box
  before `Q.STEM` exists (`gather._owner_marks_for_cell`,
  `override-map` §5: 58 Litolff / 126 Brahms stems lost to false rest boxes).
  Under the register the stem finder consults AREA claims only (clef, key,
  meter) and never a rest box.

## 5. Which patches it subsumes, which stay, and the order

**Subsumed (the test becomes the owner's claim; the reason becomes
`claimed_by:<owner>`):** `notehead_precision`: `is_a_clef` (already the model),
`on_another_symbols_box` (clef half of 2.176), `on_the_staffs_leading_barline`
(2.176), `notehead_in_a_key_signature_slot` (2.100),
`is_a_time_signature_digit` (2.47c), `is_a_meter_digit` (2.12l),
`on_a_read_meter` (2.173), `on_a_dynamic_letter` both forms (2.76, 2.107),
`is_an_arc_tail` (2.164), `on_a_barline` (the dot case), `is_a_beam_piece`
(2.77b, once the beam claims its stroke). `family_precision`:
`rest_in_a_key_signature_slot`, `rest_is_a_meter_digit`, `rest_on_a_dynamic_
letter`, `rest_is_a_barline` (2.105c), `in_a_key_signature_slot` for
accidentals / flags / keysig markers / arpeggiati. GATHER: `refuse_owned`'s
box list (`_owner_marks_for_cell`), `blank_point_detections` in the hairpin
reader, `_ink_without_detections` in the word reader, 2.166's erase (OFF),
2.172's `production_stronger` merge.

**Stay (not claims):** shape rules `too_narrow`, `clipped_fragment`,
`is_a_dot`, `off_staff_glyph`; same-family rules `notehead_is_a_duplicate_
box`, `stacked_head_duplicate`, `head_cut_piece`, `rest_is_a_duplicate_box`;
ownership `belongs_to_a_nearer_staff`, `glyph_owner`; within-bar ink
readings `is_a_rest_twin`, `on_a_rest`, `is_a_rest_shape`, `rest_has_a_stem`,
`rest_overlaps_a_notehead`, the tremolo tests (2.49/2.137/2.71) -- a rest or a
slash is read at the bar, not from the big picture; they may join the register
as `ink` claims last (step 7), never as areas.

**Migration order.** Never delete a gate first. Each step (a) files the
claim in GATHER, (b) adds the one consult, (c) proves on the 20261018-night
records that the set of boxes refused by the old reason equals the set refused
`claimed_by:<owner>` (plus named, crop-checked differences), (d) only then
retires the old test, keeping its reason string as an alias in the census so
`check`'s open-findings number and the regather report stay comparable.

## 6. How each step is measured

- **On the exported file**, whole-record replay OFF vs ON at current defaults
  (`replay_2_176.py` / `compare_2_176.py` pattern): notes in file, red bars,
  heads refused by reason, rests refused by reason; every removed box looked
  at in a crop; every removed box that was in a judged tile named.
- **Blind tiles to Sean**: refused boxes AND the controls that must stay
  (first note after the mark; a note under the arc; a rest beside the key).
  One blue box, nothing else of ours; the question "is the thing in the box a
  notehead / rest? if not, what is it?" (`tiles_2_176.py`).
- **Must-keep controls**, automated over glyph keys: the 2.176b 24 chord notes
  + 3 clef tails + 28/5 first-notes; the eleven 2.167e real eighth rests the
  meter column refuses today (must become KEPT); 2.176 controls 9 and 11;
  `judged score --doc litolff|brahms` totals never worse.
- **Who says it is right**: the print (crops), Sean (tiles), never the
  record's own verdicts (rule 7). A step whose only evidence is that refusals
  moved between reasons has shown nothing.

## 7. Ranked build sequence

| # | step | reach (from FINDINGS) | model | one question for Sean |
|---|---|---|---|---|
| 1 | **2.177 meter object** (in flight) -- but make it FILE `Q.CLAIMED_AREA` (owner `meter`, unit `area`, the numerals' own box) instead of a private test, and shrink `key_slots.meter_column` to that box | Brahms ~10 black/half loops (plan-2-176b) + 39 whole loops already caught by 2.173 kept out by one rule; 11 real eighth rests restored (§2.167e Q2, 9 in red bars); Litolff 0 | Sonnet (in flight) | "At a 6/8 change bar, is anything ever printed between the two numerals and the first note -- a cautionary accidental, a rest?" |
| 2 | **The register + the header column + clefs**: `Q.CLAIMED_AREA`, `claims.covering`, the one consult in head and rest precision; claims from `Q.CELL_BOX` (leading column) and `Q.CLEF_LOCATED`; subsume `is_a_clef`, `on_another_symbols_box`, `on_the_staffs_leading_barline`, `rest_is_a_barline`'s leading case; fold 2.144's mid-bar clef | 2.176: 37 Brahms + 2 Litolff boxes, 9 bars released, 0 real notes lost of 39; `is_a_clef` 9; 2.148 tiles 3 clefs + 1 C-clef piece | Opus (a record quantity with scopes, wiring and reach checks; `reach.NOT_A_STAGE`) | "Is anything but the bracket, brace, barline and instrument name ever printed left of the first clef?" |
| 3 | **Key signature slots** as an area claim; subsume the five `in_a_key_signature_slot` gates | rests 21 / 20 (3/3 right by crop); heads, flags, arpeggiati uncounted; 2.176 held-bar accidentals 2 of 110 | Sonnet | "At a key change mid-system, do the cancelling naturals count as part of the signature's run?" |
| 4 | **Dynamic letters and words** as own-ink claims; subsume `on_a_dynamic_letter` (both), `rest_on_a_dynamic_letter`; `_ink_without_detections` reads the register | ~150 / ~215 bucket shared with clefs/slashes (§2.167); held-bar sample 1 in 110 | Sonnet | "When an f's hook runs under a beamed group, how do you tell the hook's ink from the head's?" (one crop) |
| 5 | **Arcs and hairpins** as own-ink claims in place of the OFF erase; subsume `is_an_arc_tail`; INFER `collapse_arc_ink_not_beam` and 2.74's hairpin/beam question consult the register | tails 10 / 10 per 8 pages, 2.164 7 / 12; beam boxes doubling an arc 75 / 78; hairpin/beam 12 / 6 real beams must not be lost | Opus (touches the CV beam and stem-tip readers) | "Does a tie's ink ever enter the head's oval, or only touch its edge?" |
| 6 | **Stem finder reads the register**: `refuse_owned` consults area claims only; no stroke deleted for a rest box | 58 Litolff / 126 Brahms stems (override-map §5, 2.150) | Sonnet | re-show 2.150 tile 11 / 2.150b tile 20 ("stems of quarter notes") |
| 7 | **Within-bar marks** (rests, beams, slashes) as ink claims; subsume `on_a_rest`, `is_a_rest_twin`, `is_a_beam_piece`, the slash gates | rest curls 25 Brahms, slashes 58 / 116 ink, beam pieces (uncounted) | Sonnet | "A rest in the other voice standing under a chord -- can its curl ever touch a head?" |
| 8 | Rehearsal marks, bar numbers, volta, tuplet numerals | one case seen (§2.167d E) | Sonnet | none until a count exists |

Each step: OFF flag, both plates, the §6 measures, Sean's tiles, then ON.
Steps 2 and 5 are where the design can go wrong and should be Opus; the rest
are one owner each.

## 8. Risks, and what would falsify the idea

- **A claim is only as good as the big-picture read.** The bracket is not
  read at all; the clef contest and the meter template both abstain on some
  staves (2.176b: staff 12 below the 0.5 floor). An area claimed from a wrong
  read removes real notes silently. Guard: a claim's owner standing travels
  with it; blind tiles of refusals per owner; the must-keep controls.
- **Too wide.** The 18-space meter column is the precedent. Guard: areas are
  the mark's OWN extent plus at most half a digit width; a claim wider than
  its owner's box is a test failure.
- **Litolff's blobs.** A claim by component eats heads (the dropped accidental
  rule). Guard: own-ink claims are the owner's fitted shape, never the
  component; no area claim where the convention does not say "nothing else
  is printed here".
- **Erasing changes other readers.** 2.166's erase moved beam levels. Guard:
  the register never touches a raster; readers consult it.
- **Confidence tiebreaks are guesses.** 2.172's merge and 2.176's "clef box
  scored at least as high" both decide by the detector's number. Guard:
  overlapping claims narrow; never argmax.
- **Reach is bounded.** Non-notes in the WRITTEN file are rare (Brahms 0 of
  81, Litolff 2-5 of 39, `omr-non-notes` §2); the extras live in red bars
  (8%), and two thirds of red bars are missing symbols or wrong values
  (§2.167c), which no claim fixes. Expect tens of bars per movement, not
  hundreds.

**What would falsify it.** (1) After steps 1-3, a fresh random sample of red
bars (the `sample_2_176.py` draw) still finds the same non-note kinds at the
same rate -- then the population is accidental stacks, rest curls and merged
blobs, which need shape readers, not claims. (2) Refusals `claimed_by:*` on
Sean's blind tiles are real notes more often than the gates they replace (2.176:
0 of 39). (3) A third publisher prints something musical inside an area the
convention says is empty (a rest between clef and key; a note in the meter
column) -- then that area claim is a cut-off, not a convention, and may only
NARROW (CLAUDE §4). The idea survives any one of these as a smaller thing: an
own-ink register for arcs, hairpins and letters only.
