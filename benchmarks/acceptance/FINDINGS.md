# Acceptance — FINDINGS

## red bars (2026-10-29)

STAGED EXPORT of the saved frozen-sample records (main 1b47854a4, `lane-2.222-one-head/out/lane-report/2.222-gather`), no re-adjudication, no gather. Scripts and crops: `out/red-bars/` on `lane-red-bars-1029`. Control: the export reproduces the ranking's counts exactly (Litolff 246 = 147 short + 99 over, 5,677 hosts; Brahms 164 = 66 + 98, 6,539 hosts).

**Prior work used.** 2.173 (omr-red-bars): what a red bar is (held bar written, nothing padded). 2.8 bar-sum hold-out and 2.117 partial bars: the `why` field (`short_without_an_unread_symbol`, `voice_overfull`, `nothing_before_or_after_the_gap`). voices lanes (omr-staged-voices, omr-voice-split, omr-unison-two-voices): the rules for when a bar is two voices. omr-staged-duration-beams, beam-piece-duration, omr-duration-narrowed: where a value is decided. 2.167c (held bars, voices 2-7%) and 2.179 census: earlier counts. ink-rules duration/voice rows and page-facts (eighth only on evidence, tuplet only where marked, grace notes never in the sum). Kept: the exporter's own report as the record of what was counted. Dropped: any per-bar fix by arithmetic (CLAUDE s4: the bar sum is the weakest witness; here it also fails as a classifier, see the cross-tab). Tried and dropped this lane, controls failed: an interior-barline stroke test (13% of non-red Litolff cells show one, 16-19% of red: no signal) and "far head in the bar" as a cause (cells with a far head are red 10.0% vs 10.3% without).

**Cause and process lesson.**
1. `voice_overfull` is not a voice problem. `export._plan_one_stream` (export.py:5656) returns it whenever any stream's total exceeds the bar, for one voice too. Of 99 Litolff / 98 Brahms overfull bars only 3 / 1 were written as two voices. Real voice-split faults are a minority (below). The ranking's label sent the first read wrong.
2. Arithmetic alone cannot say why a bar is red. Against the crops: bars whose total is fixed by removing one event were really a missing flag (value), a neighbour's ink, or a cut bar; single-event short bars were a missing rest, a cut bar, or unclear. Rule 7: classes below rest on my reading of the print (n = 23 Litolff, 16 Brahms), NOT Sean's, until the tiles come back.
3. The commonest faults are a mark absent from the reading that is then scored as "no mark": 3 of 3 Brahms flag cases checked on the record are `head_and_marks` DECIDED 1.0 READ with the flag plainly on the print.

**Counts, per page (Litolff 9 pages, Brahms 8).** Record-own splits (ours, exact):
| | Litolff /pg | Brahms /pg |
|---|---|---|
| red bars | 27.3 (246) | 20.5 (164) |
| short / overfull | 16.3 / 11.0 | 8.2 / 12.2 |
| a doubled-staff copy of another red bar | 2.2 | 0 |
| a whole rest in the bar (whole-rest lane; counted, left) | 0.4 | 1.6 |
| neighbouring cells sum to the bar or to two bars (cut/shifted bar, arithmetic) | 3.8 | 1.2 |
| written as two voices, a voice does not fill | 2.7 | 1.0 |
| overfull, one extra event compatible / one value compatible / both / neither | 4.7 / 0.8 / 2.6 / 0.8 | 2.5 / 1.6 / 5.4 / 0.5 |
| short, one event only / standard gap with 2+ events / other | 4.2 / 5.2 / ... | 1.6 / 5.0 / ... |
| same-cell red on 4+ staves of a system (a column) | 69 bars in 12 columns | 34 bars in 7 columns |

Print classes, projected from the crop sample (wide error, about +-15 points; ours until Sean's tiles):
| class | Litolff /pg | Brahms /pg | rests on |
|---|---|---|---|
| value read wrong (eighth flag/beam missed or invented, dot missed) | 5.3 | 7.8 | my crop look: Litolff 5 of 23, Brahms 6 of 16 |
| extra ink counted (neighbour staff head/rest, tempo-mark note, accidental read as head) | 5.0 | 4.5 | my crops |
| bar cut at a false or missed barline | 4.7 | ~0 | my crops + arithmetic pairs |
| symbol on the print not written: rest with no box | 4.1 | ~0 | my crops (3 of 12 Litolff short; quarter/eighth rests) |
| symbol not written: head/chord (merged with a beam; refused as duplicate, too narrow, value undecided) | 2.7 | 3.3 | my crops |
| voices wrong (two voices read as one; one beam group split in two) | 2.7 | 3.9 | my crops |
| cannot tell | 2.7 | 1.1 | |
Not found in the sample: meter wrong (meter is `carried` in 239 of 246 Litolff, 154 of 164 Brahms bars and the staves of a column agree), tuplets, grace notes counted.

**Top causes, upstream, owner.**
1. Value read wrong. Flag/dot absent from the reading becomes a READ plain value: `rhythm.adjudicate_duration` (rhythm.py:4615, `head_and_marks` returns at 5823-5826; flags via `_attached_flags` 2099, hook/tip reader 5451, 5582); dots decided but unattached `export.py:3038`. Owner: claim-order layer 5 (flags/beams on stems; beams 2.202 ON, stems 2.204 parked) and layer 3 dots (ranking row 5). The flag reader consumes the erased raster (ink-rules row 104, retires with 2.206). No lane yet on "absent flag = READ quarter" (rule 8).
2. Extra ink counted. A glyph the owner/pitch chain lets through: `restate_pitch` falls back to the geometry position when the far-head decision abstained (`consequences.py:111-131`), so a tempo-mark note (G6, `Q.NOTEHEAD_POSITION` abstained `ledger_not_read`) and a neighbour staff's head (position 11.4, owner `distance`, `ownership.py:655`) are written; cells are padded so the neighbour's ink is inside. Owner: layer 1/3 (words above the staff; each cell claims its own, 2.186) and the far-head owner 2.216 (already next on the roadmap). 2.222 one-head check covers the "slab" case.
3. Symbols not written. A quarter/eighth rest never boxed stays an unclaimed `blob` stroke (the same fall-through as whole rests; `consequences.size_unboxed_rest` consequences.py:819 only sizes rests that were proven); heads dropped as `too_narrow` / `chord_value_undecided` / duplicate (`export._place_notes` 1145). Owner: layer 3 rests + 2.194 unclaimed blob; whole rests belong to lane-whole-rest-1029, arcs to lane-arcs-claim-1029, head trim to lane-head-trim-1029. Not duplicated here.
Next (Litolff only, ~17%): the cut bar. `gather_measures` (gather.py:268) records only the cell COUNT; the cut is in the shared measure extractor. System 9/1 cell 5 (10 of 10 staves overfull) and cell 6 (9 short) are one missed barline; 6/1 cells 12-13 (6 and 9 staves short) one false cut. One wrong column makes ~10 red bars. The structure adjudicator already names the check (`structure.py:206`, "merged bar sums to a multiple, split bar to a fraction") but nothing acts on it.

**Tiles for Sean** (blind, only the orange box drawn): `out/red-bars/tiles-1029/tiles/` (sheet.png, tile_01-12), key in `out/red-bars/tiles-1029/key.json` (outside the tile folder). 10 red bars across the classes + 2 controls that add up (the exporter's own sum, not red, not partial, not unread). Question: "Is anything in this bar missing, extra, or a different value?" Caveat: Brahms bars are 12-16 spaces wide, the tile is 12 wide, so the orange box runs off the edge on those.

Not measured: Sean's judged answers right->wrong (nothing changed in the file). Open: the print classes need Sean's tiles before any lane opens (rule 7).

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

### 2026-10-29 addendum: the one Litolff right->wrong (tile `2.83-fix-review/tile_05`) is a box swap, not a lost note
Cause (lane-rtw-1029, report text committed by the manager). Litolff p4 cell 4/0/7/7 holds one printed head. The detector gives two boxes on it, identical on 10-22 and today: `/2` (head-sized, score 0.672, F4) and `/10` (3.29 sp tall, score 0.364, read as A4).
- **On 10-22** `Q.STACKED_HEAD_FIT` abstained (`ambiguous`), so neither box was refused and both were written as an F4+A4 chord.
- **Today** the fit commits (k=1). `OMR_ERASER_FIX` (landed 10-27) changed the stem and ink rows. Box `/2` is kept (`notehead_precision.py:2166`) and `/10`, the judged box, is refused as `stacked_head_duplicate` (`:2213`). The printed quarter is still written, at its right pitch, and the invented A4 is gone.
- The 1-page eraser OFF/ON run scores it "same music at its place (box swap)". Judged right->wrong is 0 by place.

Class: on the 9 sample pages, 13 boxes written on 10-22 are now refused as `stacked_head_duplicate`, about 5% of the 248. 2 went from two heads to one, like this tile. 11 flipped keeper. Unverified by crop.

Proposed: the keeper is picked by head-box shape and centring, not ink alone. That is 2.212's job (PARKED). Lesson: a refusal can hang on a GATHER row that is "ambiguous" in one run and committed in the next; score by place before calling it a loss.
