# ROADMAP 2.166 -- arcs read once per system, then only their stroke erased (2026-10-17; STAGED GATHER; branch `lane-2.166-system-arcs`)

Sean 2026-10-17: *"Can we treat arcs the way we treat hairpins - taking into account the system or page view and then
erasing them?"* / *"Open the system level arc"*. Flag `OMR_SYSTEM_ARCS`, **default OFF**. No DECISIONS line from this lane.

**CONVENTION ASSUMED:** an arc's stroke is one thin run per page column, smooth from column to column, and it curves;
a head, stem, barline or beam is taller, straighter or thicker than the stroke where the arc meets it; a tie joins two
adjacent heads at one staff position, across barlines too (page-facts §1, DECISIONS 2026-10-01). **WHAT WOULD FALSIFY
IT:** a head, rest, dot or accidental Sean values losing ink to the erase; a blue line Sean reads as two arcs or as not
an arc. **NOT CONFIRMED:** every cut-off is set on Litolff 984073 and Brahms 317803 only; 25 tiles out, unanswered.

## 1. What existed (brief from the tree)

* **No arc tracer had ever been built** (`docs/symbol-dossiers/arcs.md` §2). Round 7 (`omr-queue-arcs-2026-09/
  ROUND7_FINDINGS.md`) recommended one after Sean judged 260 of 268 teacher arc candidates fake; production arc
  precision 0.232 -- the detector OVER-produces arcs.
* **Arcs are read per measure cell** (`gather.gather_detections`, one crop per bar, no horizontal pad): a curve across
  a barline arrives as two `slur`/`tie` boxes, or one box plus a tail boxed as a head or a beam (2.164 Sec.17: 20
  Litolff / 12 Brahms tails standing as notes). `Q.ARC_BOX` per piece (capture).
* **ADJUDICATE reads boxes, not ink**: `adjudicate_arc_kind` (detector class decides; Sean's two-note rule 2.75 via
  `_flank_search`), `adjudicate_tie_pair` (heads outside the box's ends, one staff position, adjacency, one barline
  either side on the owner staff, never across a system; "a tie cut in two ... each half names the SAME pair"),
  `adjudicate_arc_owner`. The only ink reading of an arc was 2.60's `Q.ARC_INK_SHAPE` -> `Q.ARC_IS_NOT_AN_ARC`.
* **Hairpins/dynamics are read on the page**: `gather_wedge_boxes` -> `hairpin_detection` over `pws.page.binary`;
  dynamic letters carry page-pixel staff bands (2.68, DECISIONS 2026-10-09). **Box-erase trap**
  (`omr-hairpin-cv-2026-09` §5): blanking slur/tie/beam boxes wiped the hairpins under them.
* **2.164** (`OMR_ARC_TAIL_NOT_A_HEAD`, OFF, branch only) refuses one symptom (a left-edge head box on a cut arc's
  tail with no head-wide oval); Sean 18/18 "Tie" on its tiles.

## 2. What was built (`tools/omr/staged/arcs_system.py`; one hook line in `gather.gather()` after the last detector call)

1. **Page ink without staff lines** (`composite_ink`): every cell's `image_no_staff` scaled back to page pixels,
   AND-ed where cells overlap; the raw page where no cell reaches.
2. **One trace per detector `slur`/`tie` box** (`trace_arc`): a greedy thin-stroke follower over page columns (runs
   <= 0.6 sp on the composite and <= 0.95 sp on the RAW page, so a stem cut into pieces by the staff-line removal is
   never followed), crossing gaps <= 0.75 sp (barlines, stems), bridging an arc that lies ALONG a staff line on the
   raw page at a quarter of a gap's cost (raw-only points trimmed off both ends), up to 3 sp past a box edge the crop
   CUT (box within 0.4 sp of its cell's edge), no steeper than 1:1 past its own box. Abstains (no erase) when the trace
   inks < 50% of its box's columns, lies flat on a staff line, or is STRAIGHT (>= 2 sp within 0.15 sp of a line: a
   beam or a line). Up to 3 seed columns.
3. **Join** (`join_traces`): traces on one (page, system, staff) sharing columns at one y, or end-to-start within a
   gap, are one curve.
4. **Anchor** (`anchor_ends`): the head beside each end (centre <= 1.6 sp beyond / 0.8 sp inside the end, <= 2.5 sp
   in y); shape `two_heads_one_position_adjacent` (<= 0.25 sp apart, no head between: a tie's shape),
   `one_position_heads_between`, `two_positions`, `end_unanchored`, `one_head_both_ends`. Filed as `Q.SYSTEM_ARC`
   (MEASUREMENT, `READERS.CV_SYSTEM_ARC`) on the curve's leftmost piece with its pieces, cells, ends, anchors and the
   boxes the stroke runs through. `Q.ARC_KIND` / `Q.TIE_PAIR` are NOT changed (`reach.KNOWN_GAPS`: producer only).
5. **Erase** (`erase_in_cell`), on each cell's `image_no_staff` only (original kept on
   `cell.image_no_staff_with_arcs`; `cell.image` and `pws.page.binary` never touched): only traced runs, only inside
   the arc's own boxes (+0.25 sp) or a box holding nothing but its stroke, never a column > 1.6x the arc's median
   stroke, never a canonical run reaching past the stroke's rows, never inside a protected box (heads, stems,
   accidentals, dots, articulations, ledger lines, beams, hairpins, ...). Exempt: a NOTEHEAD box whose ink off the
   stroke is < 0.06 sp^2 (2.164's tail), and a BEAM box doing the same that lies >= 50% inside one of the arc's own
   boxes (the detector's twin read).
6. ⚠️ `gather_empty_bar_rest_search` runs before the hook (it must precede the rescue, which must precede this) and
   still reads the un-erased raster.

Tests `tools/omr/tests/test_staged_system_arcs_2_166.py` (17), each guard with a MUTATION twin that goes red without
it: a tie cut at a barline read as ONE arc (two without the join); the tail boxed as a head erased (kept with every
head protected); a touched hollow head keeps every pixel (loses ink unprotected); an unboxed filled head keeps every
pixel (loses ink under a box erase); a hairpin inside the arc's box keeps its ink, boxed or not (wiped by a box
erase); flag off files and erases nothing; the detector's image and the page raster are never touched.

## 3. Measures

Page A/Bs (`probe/page_ab.py`): GATHER+ADJUDICATE, flag OFF vs ON, the detector run ONCE per page and cached so both
arms see identical boxes (`same_detector_boxes` true on all 8), one page at a time. Pages: Litolff pdf 2, 3, 4, 5, 13;
Brahms pdf 1, 18, 26. Outputs `out/2.166/ab_*.json`; summary `out/2.166/summary.json` (`probe/summarize.py`).

| | Litolff (5 pages) | Brahms (3 pages) |
|---|--:|--:|
| detector arc pieces | 1,127 | 1,989 |
| traced (read) / abstained | 833 / 294 | 856 / 1,133 |
| arcs after joining | 649 | 666 |
| **arcs read WHOLE across a barline (were 2+ pieces)** | **70** | **44** |
| shape: two heads, one position, adjacent (a tie's shape) | 143 | 190 |
| shape: one position, heads between | 46 | 74 |
| shape: two positions | 113 | 73 |
| shape: an end with no head beside it | 347 | 329 |
| head boxes holding nothing but the stroke (tails boxed as heads), erased | 10 | 10 |
| beam boxes doubling an arc, holding nothing but its stroke | 75 | 78 |
| `tie_pair` / `arc_kind` verdict tallies changed | 0 / 0 | 0 / 0 |
| glyphs with any verdict changed OFF -> ON | 3 | 25 |

* **Abstentions are mostly the detector's fakes**: Brahms's 1,133 abstained pieces (57%) sit with round 7's precision
  (0.23); about half the arcs have an end with no head beside it -- fakes, plus arcs whose head was never boxed. Not
  judged.
* **2.164's tails**: of the 6 tiled tails on these pages, 2 (Litolff `3/1/5/3/1`, `3/1/5/3/3`, two boxes on one tail)
  are read as the end of the cut tie and erased; `3/1/5/3/1` moves `decided quarter -> narrowed head_fill_from_ink`:
  the head gate sees an empty box, but no rule refuses an inkless head box -- **the erase alone does not retire 2.164**.
  The other 4 are tails lying ALONG a staff line (e.g. `13/0/1/10/9`: the bounded raw-line bridge stops before the
  tail, by design) or whose previous-bar piece abstained.
* **Downstream changes** (all in `out/2.166/ab_*.json`): Litolff 3 (the tail above; one eighth-rest gate; one narrowing changes its reason). Brahms 25,
  mostly pdf 1: **8 heads in one cell (`1/0/0/0`) go from 1 beam level to 2 and a 9th to narrowed** -- the CV beam-stroke reader
  (`Q.BEAM_STROKE`) finds two long new strokes once a long slur near the beams is erased (NOT resolved; likely
  wrong); 8 heads go `narrowed -> decided` (`stem_tip_reads_no_beam` / `head_and_marks`) once slur ink leaves the
  stem tips; 4 eighth-rest gates flip; one tremolo-slash refusal is undone (`18/1/3/6/5`, now a dotted eighth).
* **Sean's judged tiles on these pages** (138 glyphs): 3 verdicts change; **0 heads, rests, dots or accidentals lost**
  (no notehead, rest or accidental verdict on a judged glyph changes). `1/0/0/6/5` (Sean "4"): narrowed -> quarter,
  RIGHT. `1/0/11/0/13` (Sean "8th"): narrowed -> quarter, WRONG (the beam-stem join OFF made through the slur's ink is
  lost ON). `1/0/10/0/17`: an eighth-rest gate decided -> abstained, no duration change.
* Ink inside protected head boxes: none by construction in the canonical frame; the tile cutter's page-pixel overlay
  shows 1-10 px at box borders (rounding of the canonical -> page map), not an erase inside a box.

## 4. Blind tiles: `out/print/2.166-review/`, 25, `answers.json` `{}`

`probe/tiles.py`, seed 2166, Litolff pdf 3, 13 and Brahms pdf 1, 18; glyphs already in the judged index or 2.164's
tiles are never asked again. 13 ARC tiles (12 arcs read differently from the per-bar reading -- joined across a
barline, or run through a box holding only its stroke -- and 1 control, a tie read whole inside one bar): the traced
line drawn thin in blue, its two ends as two blue dots; *"Is the blue line one tie, one slur, or something else?
Which two notes does it join?"* 12 HEAD tiles (11 head boxes with erased ink inside or within half a space, 1
control: a head beside an arc, kept whole): one blue box; *"Is the mark in the blue box a note, or not a note?"* Key
`out/2.166/tiles-key.json`, apart from the tiles.

## 5. Sean's 13 arc answers (2026-10-17) and what they changed

He saw the 13 ARC tiles redrawn by the manager (`out/print/2.166-arcs-clear/` in the start-here worktree, print left,
our traced pixels blue right), numbered 1-13 = our tiles 1, 2, 6, 7, 10, 11, 12, 14, 16, 18, 19, 23, 25. Verbatim:
*"1. Tie 2. Slur 3.tie 4. Tie 5. Slur 6. Tie on one side of the barline and a slur on the other. The blue line swaps
arcs. 7. Tie 8. Tie 9. Tie 10. Tie 11 slur 12. Tie 13. Tie"*. Recorded in `out/print/2.166-review/answers.json`
(manifest names only the answered tiles; the 12 box tiles stay blind), judged index rebuilt; scored by
`probe/record_answers_2_166.py` -> `out/2.166/arc_answers_scored.json` (our call: a tie's shape -> tie; two positions
or heads between -> slur; an unanchored end -> no call):

| | tiles |
|---|---|
| right | 7 (1, 6, 7, 16, 23, 25 tie; 10 slur) -- 3 of them joined across a barline |
| wrong | 1 (14: Sean tie, we saw a head between its ends) |
| a curve that swapped arcs | 1 (11) |
| no call (an end with no head beside it) | 4 (2 slur, 12 tie, 18 tie, 19 slur) |

**Tile 11, why** (Brahms pdf 1, `glyph/1/1/11/1/21`; fixture `tools/omr/tests/data/system_arc_tile11.npz` cut by
`probe/fixture_tile11.py`): the tie's piece in bar 1 is cut at the barline; in bar 0 its other half runs just above
the SLUR and the two touch beside the barline. There the composite run is the two strokes merged (20 px against the
stroke's 6-7); the trace took that blob's CENTRE as the stroke's height, the prediction dropped 5 px, and the walk
continued along the slur. Not curvature: HEIGHT continuity across a merge. **Guards** (tests on the fixture, each
with a mutation twin): a run thicker than 1.6x the stroke's recent median (+2 px) bridges as a gap, so the height
and slope carry across it (tile 11 now stays on the tie: y 157 at x 175, rising to the head); pieces joined end to
start must continue in height along the left end's tangent and their end tangents must agree within 0.35; each end
joins only the piece that continues it best; shared-column joins need 60% of the shared columns to agree.

**The long Brahms slur** (pdf 1, cell `1/0/0/0`, 8 eighths read as sixteenths ON): NOT the erase's own remnant. A
first guard (never erase within 1 sp of where the stroke merges with other ink; test + mutation) removed the straight
bar the erase used to leave, and the judged tile `1/0/11/0/13` (Sean "8th") is no longer changed. But the 8 heads
still change: with the crossing slurs erased, a long HAIRLINE under the beams that no arc box covers (so nothing here
may erase it) becomes two clean full-width strokes to `Q.BEAM_STROKE` (canonical 643-1911, y 449-537), read as a
second beam level. OFF, the crossing slur ink hid it. The defect is the beam reader taking an unstemmed hairline for a
beam level; the erase exposes it. Flat thin slurs are no longer refused as "straight" (only a straight trace as thick
as a beam, >= 0.4 sp, is). Brahms pdf 1 now: 16 glyphs change, 2 judged (`1/0/0/6/5` right; an eighth-rest gate).

**Check 194 vs 192** (`staged.check` on an `origin/main` snapshot vs this branch, diffed): both new findings are the
ONE fact that `Q.SYSTEM_ARC` is produced and read by nothing -- counted once by `staged.reach` (its KNOWN_GAPS entry
keeps it from failing, not from counting) and once by `staged.gather_coverage` ("UNREAD -- produced, and NOTHING
anywhere reads it", 10 -> 11). Both close the day an adjudicator reads the joined curve.

## 6. Sean's 12 box answers (2026-10-17)

Shown in the order of our tiles 3, 4, 5, 8, 9, 13, 15, 17, 20, 21, 22, 24. Verbatim: *"1. A large box that has 2 half
notes in it. 2. Barline 3. Dot 4 4. Tio of a dot 4 - box is too small 5. Dot 4 6. 2 7. Dot 4 8.Tip of a half note -
box is too small 9. Tie 10. Barline 11.2 12.8"*. Recorded in `out/print/2.166-review/answers.json`, judged index
rebuilt; scored by `probe/record_box_answers_2_166.py` -> `out/2.166/box_answers_scored.json` against both arms of the
page A/B records (`notehead_is_not_a_notehead`, `duration`).

**The erase arm equals base on all 12** -- no note dropped, no non-note dropped or kept differently by the erase:

| tile | Sean | base = erase arm |
|---|---|---|
| 5, 9, 24 | dotted quarter, dotted quarter, eighth | kept, value right |
| 13 | half | kept, half |
| 15 | dotted quarter | kept, read a dotted eighth (value wrong, both arms) |
| 22 | half | REFUSED as a note (wrong, both arms) |
| 4, 21 | barline | refused (right) |
| 20 | tie | kept as a note, duration narrowed (wrong, both arms; Litolff `13/0/0/0/25`) |
| 3 | a box holding 2 half notes | kept, a half (box-size problem) |
| 8 | tip of a dotted quarter, box too small | refused (box-size problem) |
| 17 | tip of a half, box too small | refused (box-size problem) |

T3, T8 and T17 are box-size problems for the detector or the re-centre stage, not this lane. ⚠️ But T8 and T17 are
real notes' partial boxes that this lane classed **stroke-only** (their ink off the traced stroke is under 0.06 sp^2)
and so erased inside: a small box on a note's edge can look like a tail. It changed no verdict here (base already
refuses them), but the stroke-only exemption is not safe on its own: it should also require the box to sit where the
crop CUT the arc (2.164's left-edge test), or be dropped. T20 (a tie kept as a note) is the case the exemption exists
for; the erase emptied it, yet the head gate still keeps it (narrowed, `head_fill_from_ink`).

## 7. Limits / next

Flag OFF. (Round 2, Sec. 8: `adjudicate_tie_pair` / `adjudicate_arc_kind` now read the joined curve.) The erase perturbs the CV beam reader on Brahms pdf 1 (one cell, 9 heads) and makes
one judged eighth a quarter: until that is understood the ERASE should stay off even if the READING is kept. Arcs
lying along a staff line are bridged only ~3 sp. Single pages only; no whole-movement replay (a GATHER change needs a
gather, not `review.rerun`).

## 8. Round 2 (2026-10-18): the consumers, the exemption fix, a lean replay

**Built** (flag `OMR_SYSTEM_ARCS`, default OFF; the rows exist only while it is on). STAGED ADJUDICATE:
* `adjudicate_tie_pair` reads `Q.SYSTEM_ARC` (found through the staff: the row names every piece of the joined curve).
  CONNECT, NEVER GUESS: where the local flank search found NO head at an end (`no_start_head` / `no_stop_head` /
  `no_head_near_the_arc` -- the bar's pad stops at the barline the tie crosses) AND the joined curve's two ends landed on
  two DIFFERENT heads at one staff position with nothing between (`two_heads_one_position_adjacent`, page-facts 1, Sean
  2026-10-01) AND neither head was refused as a notehead, it decides `paired_by_system_arc`. Every other shape, an
  unanchored end, a slur, and every local refusal that is itself a finding (`not_adjacent`, `no_pair_at_one_position`,
  `spans_a_whole_bar`, `*_system`) stays abstained. Where the local search DOES pair, the row only records `agrees`.
* `adjudicate_arc_kind` RECORDS the system arc's shape and its agreement with the reading in `grammar["system_arc"]`; it
  acts on nothing (the tie->slur half of any grammar veto measured +130 edits on a scan, `OMR_ARC_RECLASS`).
* `reach.py`: the `Q.SYSTEM_ARC` KNOWN_GAPS entry LEAVES (it has a reader). **check open-findings 194 -> 193.**
* The tiny-box erase exemption now also needs 2.164's test: a NOTEHEAD box is "all stroke" only if it starts within half
  a space of its bar's left edge AND holds < half a head's width of head-tall columns (`head_oval`, same cut as
  `notehead_precision`); `OMR_ARC_TAIL_NOT_A_HEAD` off, no cell or no raster keeps the box (rule 8). Beam boxes unchanged.
* Erase stays OFF-by-intent: hairline-as-beam on Brahms pdf 1 is known and not fixed here.

Fast tier `pytest -m "not slow" tools/omr/tests`: 8460 passed, 0 failed (serial; no xdist here).

Tests: `test_staged_system_arc_consumers_2_166.py` (12; each refusal has its positive control: no row -> abstains; two
positions / heads between / unanchored / slur -> abstain; a thin stroke at the left edge is exempt, a head-tall blob at
the left edge is not).

**Lean replay** (`probe/page_ab.py`, flag OFF vs ON, detector cached, the pages holding Set I tiles; Litolff 2/4/5 and
Brahms 26 not re-run, their v1 files are in `out/2.166/v1/`):

| page | tie_pair abstained -> `paired_by_system_arc` | arc_kind changed | other glyph verdicts changed | judged glyphs changed |
|---|--:|--:|--|--|
| Litolff 3 | 0 | 0 | 0 | 0 |
| Litolff 13 | 2 | 0 | 1 eighth-rest gate | 0 |
| Brahms 1 | 3 | 0 | 14 duration, 2 eighth-rest gates | 3 (below) |
| Brahms 18 | 5 | 0 | 2 duration, 1 notehead_is_not_a_notehead, 1 rest gate | 0 |

10 ties anchored, all from `no_head_near_the_arc` / `no_stop_head` / `no_start_head`; `decided:paired` counts and
`narrowed` counts unchanged on every page. The tail erase no longer moves anything on Litolff 3 (0 glyphs changed; was 3:
the exemption fix). Judged glyphs changed on Brahms 1: `1/0/0/6/5` (Sean "4") narrowed -> quarter, RIGHT (as before);
`1/0/10/0/17` an eighth-rest gate decided -> abstained, no duration change (as before); `1/1/11/1/21` (Set I tile 11, Sean
"tie on one side, slur on the other") abstained -> tie_pair start `1/1/11/0/7`, stop `1/1/11/1/23` -- the arc on the tie
side, consistent with his answer, NOT a verdict he gave on the pair. The earlier WRONG `1/0/11/0/13` (narrowed ->
quarter) does not change any more. **right -> wrong on judged glyphs: 0.**

**Blind tiles** `out/print/2.166-review-2/` (10: the 9 new ties on unjudged bars + 1 control a per-bar pairing the joined
curve agrees with), nothing of ours drawn, key `out/2.166/tiles2-key.json`, one run of `probe/tiles2.py` (asserts files =
manifest = key). Question on each: ONE arc joining the first and last notes (a tie), a different arc (a slur), or none?
Not yet answered; nothing else changes until they are.
