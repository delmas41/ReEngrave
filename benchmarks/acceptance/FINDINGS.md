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

### 2026-10-29 addendum: the one Litolff right->wrong (tile `2.83-fix-review/tile_05`) is a box swap, not a lost note
Cause (lane-rtw-1029, report text committed by the manager). Litolff p4 cell 4/0/7/7 holds one printed head. The detector gives two boxes on it, identical on 10-22 and today: `/2` (head-sized, score 0.672, F4) and `/10` (3.29 sp tall, score 0.364, read as A4).
- **On 10-22** `Q.STACKED_HEAD_FIT` abstained (`ambiguous`), so neither box was refused and both were written as an F4+A4 chord.
- **Today** the fit commits (k=1). `OMR_ERASER_FIX` (landed 10-27) changed the stem and ink rows. Box `/2` is kept (`notehead_precision.py:2166`) and `/10`, the judged box, is refused as `stacked_head_duplicate` (`:2213`). The printed quarter is still written, at its right pitch, and the invented A4 is gone.
- The 1-page eraser OFF/ON run scores it "same music at its place (box swap)". Judged right->wrong is 0 by place.

Class: on the 9 sample pages, 13 boxes written on 10-22 are now refused as `stacked_head_duplicate`, about 5% of the 248. 2 went from two heads to one, like this tile. 11 flipped keeper. Unverified by crop.

Proposed: the keeper is picked by head-box shape and centring, not ink alone. That is 2.212's job (PARKED). Lesson: a refusal can hang on a GATHER row that is "ambiguous" in one run and committed in the next; score by place before calling it a loss.
