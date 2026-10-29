# Acceptance — FINDINGS

## 2026-10-29 product ranking (STAGED, exported file)

Written by the manager from the ranking lane's report. The lane was a subagent whose write was refused ("subagents return findings as text"). Scripts, crops and judged scores are on branch `lane-ranking-1029b` (a10b7a336), `out/print/2.229-ranking/`. The `work/` outputs were left local in worktree `agent-abbe8b17c659e77cb`.

**Method.**
- **New:** the fresh frozen-sample GATHER on main 1b47854a4 (through INFER; OMR_FILL_FROM_STROKES ON), at `lane-2.222-one-head/out/lane-report/2.222-gather/{litolff,brahms}.record.json`.
- **Old:** overnight 20261022-night (also through infer).
- Both exported by today's exporter from SAVED verdicts, with no re-adjudication, and matched by place (page, system, cell, staff, onset, pitch).
- Pages: Litolff 1,2,4,6,8,9,10,11,16; Brahms 0,4,5,8,12,14,19,25.
- **Control:** the new Litolff saved-verdict export and its replay through export give NOTHING CHANGED on 5,677 notes and rests.

**Cause and process lesson.** Most "unread empty bars" are not unread music. About 70% of Litolff's 279 and about 65% of Brahms's 116 print a WHOLE REST. One symbol falls through three upstream owners into the same unread bar:
1. **No detector box.** 96 Litolff and 43 Brahms bars hold no head or rest glyph. GATHER keeps the rest only as an unclaimed ~1.3 x 0.75 sp `blob` stroke.
2. **`restWhole` refused in ADJUDICATE** as `rest_touches_two_staff_lines` or `rest_off_center`: 72 Litolff, ~21 Brahms. A hanging whole rest touches its line by definition.
3. **Read as a black head and refused in EXPORT** as `ink_is_a_whole_rest` (refused, not converted): 25 Litolff.

Lesson: split an "unread" count by the fate of the glyphs in the cell before opening a lane. A second lesson (rule 7): `augmentation_decided_but_unattached` (346 on the Brahms pages) is a ledger artifact (benchmarks/omr-aug-dots-2026-10/FINDINGS.md) and is not ranked.

**Ranking, biggest first** (fix-actions per page, Litolff / Brahms):

| # | kind | Litolff /pg | Brahms /pg | evidence | blind spot | probable owner |
|---|---|---|---|---|---|---|
| 1 | ties and slurs not written | <= 83 (751) | <= 160 (1,281) | our exporter ledger; Brahms p0 hand truth at box level: ties recall 0.62, slurs 0.89 | upper bound (an arc named twice counts twice; 71 Litolff pairs); arcs never boxed | claim order layer 5 (arcs, Q.SYSTEM_ARC 2.166, tie pairing) |
| 2 | red bars (durations do not add up) | 27.3 (246 bars) | 20.5 (164) | our marks; Litolff 147 short / 99 over | bars that add up by accident | `voice_overfull` 94 L / 98 B (INFER voices); "short, no unread symbol" 119 L / 39 B; a tempo-mark note read as a head |
| 3 | a bar printing a whole rest, written unread | ~21 of 31.0 unread | ~9.5 of 14.5 | lane's crops of the print, NOT Sean's: Litolff 18/23, Brahms 9/9 | the ~30% rest are real lost notes | layer 3 rests + the unclaimed blob stroke (2.194); ADJUDICATE `restWhole` shape tests |
| 4 | pitched heads not written | 34.3 (value undecided 30.0) | 46.3 (41.1) | our exporter accounting | a head written with a wrong value | layer 5 (stems/flags/beams, 2.202), INFER narrowing |
| 5 | dots decided but never placed | 8.1 | 17.1 | our ledger; Brahms p0 hand truth: dots recall 0.983, precision 0.991 | flag curls boxed as dots | layer 3 (dot-role window) |
| | check load: blue notes / rests | 138.4 / 3.8 | 107.0 / 13.2 | the file's own marks | how many are wrong | INFER |

**Blue marks by rule:**
- Litolff: fill_part_key 699, fill_clef_gap 234, accidental_family 152, onset_from_partial_bar 129.
- Brahms: accidental_family 439, onset_from_partial_bar 264, fill_part_key 137.

**Not a fix cost:** box de-duplication drops, `owned_by_another_staff`, `ink_is_a_staff_line` false arcs, unowned accidentals (Brahms p0 accidental precision 0.65, most are false boxes), and the dot ledger.

**A second kind inside "unread empty".** Heads between two staves where the far-head owner read abstains (`count_does_not_fit`): the bar is called empty and its heads are dropped as owned elsewhere. This is 44 Litolff and 24 Brahms bars (crop `litolff/unread_empty_p4_0_9_9.png`). About 1 in 12 no-glyph bars is a plain missed chord.

**Brahms p0 against hand truth** (box level, GATHER + ADJUDICATE, 194/202 cells):
- noteheads recall 0.984, precision 0.992;
- owner 375/375, position 373/374;
- CV stems 0.978;
- rests recall 1.0, precision 0.94;
- accidentals recall 1.0, precision 0.65;
- ties 0.62/0.66, slurs 0.89/0.72;
- time-signature digits 0.79.

The reading is close to done on this page; what is wrong is binding (arcs) and bar sums. No truth exists for exported durations.

**Moved since 10-22:**
- notes and rests written: Litolff 5,684 -> 5,677; Brahms 6,519 -> 6,539
- red bars: 265 -> 246; 166 -> 164
- blue marks: 1,198 -> 1,353; 930 -> 991
- unread-empty bars: 279 -> 279; 122 -> 116

The movement comes from the gather side.

**Sean's judged answers, right -> wrong** (old vs new, sample pages):
- **Brahms:** right 63 -> 64, right->wrong 0.
- **Litolff:** right 91 -> 95, wrong -> right 5, **right->wrong 1**. The tile is `2.83-fix-review/tile_05` (`glyph/4/0/7/7/10`, Sean "4"): a real quarter with stem and flat that is now unwritten. It was refused as `notehead_is_not_a_notehead` (`stacked_head_duplicate`) and also carries `head_ink: not_one_head`, with two `accidentalFlat` boxes on one flat. Cause not isolated (crop `litolff/right_to_wrong_p4_0_7_7.png`).

**Not judged by Sean.** Rows 1 and 3 should go to him as blind tiles before either opens a lane. The arcs row needs a per-arc fate list first. The whole-rest share comes from a crop sample (32 bars), not a census.

## whole-rest bars (2026-10-29)

STAGED. Lane `lane-whole-rest-1029`, m0 (cause only; nothing built). Sample: the frozen-sample records of `lane-2.222-one-head/out/lane-report/2.222-gather` (main 1b47854a4, through INFER), pages as in the ranking. Scripts and outputs: `out/lane-report/whole-rest/` (fates.py reused from `lane-ranking-1029b`). 12 blind tiles for Sean: `out/print/whole-rest-m0-tiles/` (sheet `tiles/sheet.png`, key `key.json` outside the tile folder). NOT yet judged by Sean.

**Counts re-checked** (the exporter's own per-glyph fates, split by what is in the cell): Litolff 279 unread-empty bars = 96 no head/rest glyph, 85 every glyph judged not a symbol, 44 heads owned by another staff, 25 head refused `ink_is_a_whole_rest`, 18 value undecided, 11 other. Brahms 116 = 43 / 34 / 24 / 1 / 11 / 7. The ranking's 96, 43 and 25 reproduce exactly; Brahms case 3 is 1, not "none".
- Case 2 (restWhole boxed, ADJUDICATE refused): Litolff about 72 bars, 45 `rest_touches_two_staff_lines` + about 20 `rest_off_center` + a few mixed with a notehead refusal; Brahms about 17.

**Cause 1 (the biggest, and it is not "no reader"): a found rest is never written.** 2.52 (`gather_empty_bar_rest_search`, gather.py ~8320-8440, Sean 2026-10-01 "If it finds it then the bar is complete") already searches the bar's middle and `adjudicate_empty_bar_whole_rest` (adjudicators/rest_search.py:48) already DECIDES `whole_rest_found_by_search`. Of the no-glyph bars: **Litolff 54 of 96, Brahms 38 of 43** carry that decided verdict, and nothing reads it: `Q.EMPTY_BAR_WHOLE_REST` is referenced only by gather, adjudicate, reach, record and the rest_search adjudicator, never by EVALUATE, INFER or export.py (ROADMAP 2.52 already says "the found rest not yet read after ADJUDICATE"). Value computed and unread (CLAUDE rule 3 lesson; memory "value computed and unread"). Connecting it is a wiring change, not a guess (rule 6). The remaining 42 L / 5 B are `not_found_by_search`; tile 8 (the emptiest of them) holds a real whole rest, so the search also misses some.

**Cause 2 (case 2): rest_touches_two_staff_lines, family_precision.py:988 `_rest_touches_two_staff_lines_refusal` -> :960-985 `_rest_line_shape` -> :953 `_lines_touched`, tolerance `REST_LINE_TOUCH_TOL_SPACES` :826 = `ON_A_STAFF_LINE_TOL_SPACES` 0.25 sp (family_precision.py:200).** Sean's convention (2026-09-29, a whole rest never touches two lines) is right; the TEST is the problem. The 0.25 sp is borrowed from the ledger rule's centre scatter ("CONVENTION ASSUMED ... not separately measured", its own docstring :817-826), and it is applied to the detector BOX against STAFF-WIDE line values. On Litolff a whole rest's ink is 0.70-0.78 sp tall hanging from line 4 and its bottom sits only 0.33 sp (median; 0.03-0.18 for the lowest) above the next line, so box bottom (box ~0.05 sp taller than the ink) + 0.25 tolerance reaches the next line. Measured LOCALLY on the print (600 dpi, lines read left and right of each box): refused 59 vs kept 40 sampled rests have the same ink height (0.70-0.76 sp vs 0.70) but the refused hang 0.1-0.2 sp lower, gap below 0.33 vs 0.48 sp. The discriminator that exists: a black notehead in a space has an ink run through its centre of 1.31-1.53 sp (n=58, 10th-75th pct), a whole rest 0.70-0.78 sp. Crops of the refused boxes (e.g. litolff p2 0/2/0 box 6, p8 0/1/6/0) are plain hanging whole rests. `rest_off_center` (:630-690, `REST_WHOLE_CENTER_MAX_OFFSET_FRACTION` 1/6, :543): its own docstring says "no crop confirms this exact fraction, CONVENTION ASSUMED"; refused offsets are 0.2-0.4 of the bar; the crops (litolff p4 0/8/0, p9 0/0/9/1) are real hanging whole rests, one beside a clef the playable-span rule did not exclude, one hand-set left of centre.

**Case 3** is the known `OMR_WHOLE_REST_INK` EXPORT refusal (deliberate, "refused, not converted"; flags-2026-09 row) and the parked 2.141 fix 3 `OMR_WHOLE_REST_INK_LEAVES_BAR` (DECISIONS 2026-10-15/16, OFF pending Sean). Not touched; a proposal only after the tiles.

**Prior work, used and not rebuilt.**
- *Kept, and where this lane stands:* 2.98 (a lone whole rest is the bar, sized by the file's meter; Sean 12/12 tiles) and `OMR_LILY_CARRIED_METER_REST` (DECISIONS 2026-10-14) -- these fix the DURATION of a rest we already write, and are what a connected found-rest would flow into. 2.33 / 2026-09-29 whole-rest-touches-two-lines and 2026-09-11 off-centre conventions (ink-rules row "a rest hangs from or sits on ONE line", fires 157 / 96, kept) -- the convention stays; only its measurement is questioned. 2.52 (rest search, Sean 2026-10-01) -- found 98 rests it never delivered. 2.141h tiles and 2.142 (head boxed as a rest twin, `OMR_HEAD_INK_IS_A_REST` ON) cover the reverse direction.
- *Held:* `OMR_WHOLE_REST_INK_LEAVES_BAR` (2.141 fix 3, parked, page-facts section 5). 2026-10-01 Sean "Leave the whole rest alone - those rules are too simple" (no rule refusing a notehead because a rest sits in the bar): this lane does not build one.
- *Rest-sizing / omr-rests-2026-09 / rest-as-note-2026-10:* sizing and the rest-as-note confusion; none touched the touches-two-lines tolerance or the found-but-unread verdict. This cause is new relative to them.
- *Not searched in depth:* LEGACY rest handling (frozen, never called from STAGED), benchmarks/_archive (one rest dir, omr-rest-sizing).

**Proposal for m1 (after Sean):** (1) read `empty_bar_whole_rest` found verdicts into the exported bar as a whole rest, written GUESSED (blue) unless Sean's tiles 1, 5, 9, 10 say READ; (2) replace the 0.25 sp box-edge tolerance with a line-local ink test (ink run height), behind `OMR_WHOLE_REST_HANGS` default OFF; off-centre: widen or drop the 1/6 cut after tiles 3 and 6. No fallback turns "cannot tell" into a rest (rule 8); the 42/5 not-found bars stay unread.
### Whole-rest bars m1 / m2 (2026-10-29; branch `lane-whole-rest-1029`, all default OFF, STAGED, nothing landed)

**m1** (`out/lane-report/whole-rest-m1`, flags `OMR_FOUND_WHOLE_REST` + `OMR_WHOLE_REST_HANGS`, frozen sample, `--replay-gathered`, tag wr1029): Litolff rests +129, lost 0; Brahms +65, lost 0; judged right->wrong 0, unwritten->wrong 0, invented->removed 0. Sean's 12 tiles (`out/print/whole-rest-m1-tiles/answers.json`, DECISIONS 2026-10-29): found-by-search 8/8, refused-restWhole 9/9 right (4 written blue, 5 plain), controls 3/3. Sean: "i think we are close to landing without blue but lets measure to make sure."

**m2** (`out/lane-report/whole-rest-m2`, adds `OMR_WHOLE_REST_PLAIN`, default OFF, effective only with the other two): the found-by-search rest and the ink-rescued restWhole are written READ (plain) unless any other head or rest box (detected, kept or refused) stands in the bar, which stays blue. The three measures, same sample and tag, ON = all three flags:
- *File changes* (the shared command): Litolff rests +129 / lost 0, blue marks +14 -1 (m1: +54 -1), words +2 -138, red bars 246 -> 248, notes not written 2263 -> 2181. Brahms rests +65 / lost 0, blue +14 (m1: +18), words -65, red bars 164 -> 164, notes not written 3184 -> 3157. Net new rest hosts at a place OFF had none: Litolff 73 (59 plain, 14 blue; m1 19 plain, 54 blue), Brahms 27 (13 plain, 14 blue; m1 9 / 18). Brahms keeps half blue because most of its rescued rests share the bar with a twin head or rest box; that is the confusion case by design. Few found-by-search rests land on these 16 pages (2 on Litolff).
- *Sean's judged answers* (254 Litolff + 232 Brahms tiles): right->wrong 0, right->narrowed/gone 0, unwritten->wrong 0 (invented from non-note ink 0), invented->removed 0. `lane_report rescore` agrees.
- *12 new blind tiles* for Sean: `out/print/whole-rest-m2-tiles/` (bar-width crops, nothing drawn; key `out/print/whole-rest-m2-tiles/key.json` outside the tile folder; maker `out/lane-report/whole-rest-m2/make_tiles.py`, seed 4102): 8 plain (6 with another mark in the bar) and 4 blue, none repeated from m1. NOT yet judged by Sean.

**The 2 Litolff red bars (246 -> 248), item 1** (diffed by place, `data/litolff.{off,on}.red-bars.json`; crops `out/lane-report/whole-rest-m2/crops/red1_*`, `red2_*`):
1. p2 system 1 staff 3 bar 0 (measure 34, 2/4, counted 4.5): a CORRECT whole rest (bass staff, flats) now written beside a spurious `rest8th` box standing on the key-signature flat ink (`glyph/2/1/3/0/9`). OFF refused the rest and the bar added up short or was held; ON exposes the false eighth rest. A correct rest exposing a different error (a rest box on key ink the key claim did not take).
2. p11 system 0 staff 2 bar 4 (measure 207, counted 6): a WRONG rest. `glyph/11/0/2/4/5` is a restWhole box on the top of a slur arc, step 8.21 and `outside_its_own_staff: above`. OFF refused it only by `rest_off_center`; dropping the centre test lets it through and nothing else (the outside-staff test does not fire at 8.21) stops it. Of the 49 restWhole boxes OFF refused as off-centre on the sample, 15 have a step outside the whole-rest band (-11 to 15); 14 of them are still not written (other refusals); this is the one that is. A slot band (step 4.15-6.9, or `outside_its_own_staff` unset) kept with the centre test dropped would close it; not built (no scope for it here).

**The `claimed_by:whole_rest` refusal, item 2** (m2 mini-records; `data/*.owner-changes.json`, scripts in `scripts/`): boxes refused ON, OFF none by construction: Litolff 0; Brahms 1 (`noteheadBlackOnLine` `glyph/14/1/11/1/5`, twin of a restWhole box on the same black head). Crop `crops/c1_*`: it IS a real head, but it belongs to the staff above (`owned_by_another_staff`, duration abstained in both arms), so nothing is lost from the file; the claim is wrong about the ink and the refusal is right about this cell only by accident. Boxes touched but not refused (contested, kept): 3 (a head under a whole-rest box on p19, a whole rest under a multi-rest bar on p25, the multi-rest bar), crops `c2_*`, `c3_*`; one found-search claim refused `not_a_whole_rest_block` over real heads (Litolff p6, `c4_*`), harmless. What the `whole_rest` claim tier changed in who takes strokes: Litolff 825 strokes change owner, Brahms 436; 99% are `rest` -> `whole_rest` (the same detector box), the rest unclaimed or refused-claim -> `whole_rest`; Brahms also 1 `head` -> `whole_rest` (the refused head) and 2 strokes to `contested`. No stroke moves to or from a beam, stem or flag owner in either plate: beams and stems take exactly what they took.

**Verdict for Sean's landing question:** 0 judged answers worse, 0 real notes lost from the file; one wrong rest (red 2) and one real head refused in a cell where it was not written anyway. Not landed; defaults untouched.

**m3 (2026-10-29; same branch, same three flags, `out/lane-report/whole-rest-m3`, crops `crops/` and `crops_sheet.png`).** STAGED. The p11 wrong rest (`glyph/11/0/2/4/5`, measure 207) is NOT closed by a position test and none was built: Sean ruled that a whole rest in a multi-voice bar is legitimately displaced (above or below the staff), so a step band would refuse real rests. Cause, from the stroke owner's own record for that cell: the box's one stroke is a horizontal piece 1.59 x 0.55 sp that fits the whole-rest block shape (`whole_rest_block`) AND the neighbouring tie's thin-line shape (`arc` claim), so ownership says CONTESTED; the ink cannot tell a rest from the slur's top line, and an ink-shape test with the existing numbers (`BLOCK_MAX_H_SP`, `REST_BLOCK_MAX_W_SP`) passes it. What was built (flag `OMR_WHOLE_REST_HANGS`, `family_precision._whole_rest_ink_not_a_block_refusal`, no new number): (1) a restWhole whose box is contested with an ARC claim on a block-shaped stroke is NARROWED `claim_narrowed:arc` and written GUESSED (blue), never READ plain; p11 is now blue (1 on Litolff, 0 on Brahms), not refused: with the existing numbers the ink does not say no (rule 8). (2) a restWhole whose every covered stroke is a shape kind that can never be a block (vertical, curve) is refused `whole_rest_ink_not_a_block` (Litolff 0 kept rests affected, Brahms 3 boxes, all unwritten OFF and ON). A first version refused on the size cut (`h > BLOCK_MAX_H_SP`) lost 2 Litolff and 4 Brahms rests OFF wrote; the crops show 5 of those 6 are real hanging whole rests fused with a line stub (`crops/`), so the size cut is NOT used to refuse (the claim tier may keep it: it only claims). Of the 14 other out-of-band boxes: the new check refuses 0 of them (8 Litolff are kept by the rest decision and not written downstream by other refusals; 5 Brahms are `rest_outside_its_staff`, 1 `rest`), as before. Displaced real rests survive: 86 Litolff and 68 Brahms rests in multi-voice bars are in the ON file and none was lost; the 73 + 27 net new rests are all single-voice whole-bar rests. Three measures (ON = all three flags, frozen sample, tag wr1029): *file changes* Litolff rests +129 / lost 0, blue marks +15 -1 (m2: +14 -1; the +1 is p11), words +2 -138, red bars 246 -> 248, notes not written 2263 -> 2181; Brahms rests +65 / lost 0, blue +14, words -65, red bars 164 -> 164, notes not written 3184 -> 3157. ON writes 1224 plain + 44 blue rests (Litolff) and 1963 + 114 (Brahms). *Sean's judged answers*: right->wrong 0 on both plates, unwritten->wrong 0 (invented from non-note ink 0), invented->removed 0. The shared scorer's blind spot (both arms blue) was checked by placing every judged glyph subject on these pages (120 Litolff, 68 Brahms) in the OFF and ON exported symbols and comparing kind, written value, pitch, blue and chord: 0 differ. *Not done:* the p11 bar is still red (a blue wrong rest still adds up wrong); the whole-rest block shape cannot split it without a new measurement. The 12 m2 tiles are still unjudged. The 12 lines the first agent added to `lane_report.run_arm` are removed (the red-bar diff is reproducible from `report.json`); evidence scripts stay in `out/`. Fast tier: 9264 passed, 4 failed before the two bookkeeping fixes below (ink-rules page: 2 new reasons added to `benchmarks/rule-page/rule_kinds.py`, page regenerated; judged index rebuilt for the m1/m2 answers); all four now pass; `python3 -m tools.omr.staged.check` 198.

### 2026-10-29 addendum: the one Litolff right->wrong (tile `2.83-fix-review/tile_05`) is a box swap, not a lost note
Cause (lane-rtw-1029, report text committed by the manager). Litolff p4 cell 4/0/7/7 holds one printed head. The detector gives two boxes on it, identical on 10-22 and today: `/2` (head-sized, score 0.672, F4) and `/10` (3.29 sp tall, score 0.364, read as A4).
- **On 10-22** `Q.STACKED_HEAD_FIT` abstained (`ambiguous`), so neither box was refused and both were written as an F4+A4 chord.
- **Today** the fit commits (k=1). `OMR_ERASER_FIX` (landed 10-27) changed the stem and ink rows. Box `/2` is kept (`notehead_precision.py:2166`) and `/10`, the judged box, is refused as `stacked_head_duplicate` (`:2213`). The printed quarter is still written, at its right pitch, and the invented A4 is gone.
- The 1-page eraser OFF/ON run scores it "same music at its place (box swap)". Judged right->wrong is 0 by place.

Class: on the 9 sample pages, 13 boxes written on 10-22 are now refused as `stacked_head_duplicate`, about 5% of the 248. 2 went from two heads to one, like this tile. 11 flipped keeper. Unverified by crop.

Proposed: the keeper is picked by head-box shape and centring, not ink alone. That is 2.212's job (PARKED). Lesson: a refusal can hang on a GATHER row that is "ambiguous" in one run and committed in the next; score by place before calling it a loss.
