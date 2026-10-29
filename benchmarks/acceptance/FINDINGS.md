# Acceptance — FINDINGS

## ties and slurs (2026-10-29)

Lane `lane-arcs-1029` (STAGED, exported file; counts and tiles only, no code under `tools/` changed). Same saved records as the ranking (main 1b47854a4, through INFER), exported from SAVED verdicts with no re-adjudication, pages as the ranking (Litolff 1,2,4,6,8,9,10,11,16; Brahms 0,4,5,8,12,14,19,25). Scripts: `out/print/arcs-1029/` (`arcfates.py` per-arc fate list, `summ.py`, `p0score.py`, `under.py`, `sysarc.py`, `pick.py`). Raw lists were left in the session scratchpad `/private/tmp/claude-501/arcs/{litolff,brahms}.json` (rows per arc box and clusters per place).

**Cause and process lesson.** The ranking's "ties and slurs not written" is a sum of unlike things. Counted once per printed curve it is 473 (Litolff, 52.6/page) and 798 (Brahms, 99.8/page), not 751 / 1,281. More important, the biggest group (a slur "binds fewer than two notes") is not mostly a reading shortfall: about a third of those boxes already have BOTH ends anchored to heads by `Q.SYSTEM_ARC` (2.166), a value only tie pairing reads. Lesson: before ranking a refusal, split it by what the record already holds for the same ink; the same "value computed and unread" shape as 2.166 left behind.

**Method.** `arcfates.py` wraps (read-only, at run time) `staged/export.py::_arcs_by_kind` to capture the merge groups and `tools/omr/export.py::_paired_spans` to ask, per slur group, whether it alone binds two notes. Each `Q.ARC_BOX` gets one fate: refused (named rule), tie marked, slur marked, or twin naming an already-named pair. Twins and the two halves of a barline-cut arc are clustered (boxes on one page with IoU > 0.5, plus one merge group) into one "place".

**Control.** The exporter's `arcs_not_written_total` minus `ink_is_a_staff_line` and `claimed_by:key_signature`: Litolff 1,056 - 301 - 4 = 751; Brahms 3,854 - 2,570 - 3 = 1,281. Both are exactly the ranking's figures. My per-box breakdown of the same ink totals 761 (Litolff) / 1,354 (Brahms), because it also lists the twin boxes (19 / 56) that the exporter counts as written information.

**Per-page counts by fate** (arc boxes; Litolff p1,2,4,6,8,9,10,11,16 / Brahms p0,4,5,8,12,14,19,25 -- the full per-page rows are in `summ.py` output)

| fate | Litolff total (/pg) | Brahms total (/pg) |
|---|--:|--:|
| `ink_is_a_staff_line` (not a cost) | 301 (33.4) | 2,570 (321.2) |
| key-signature slot (not a cost) | 4 | 3 |
| tie written (marked) | 211 (23.4) | 340 (42.5) |
| slur written (marked) | 126 (14.0) | 363 (45.4) |
| slur binds fewer than two notes | 345 (38.3) | 379 (47.4) |
| tie: no head near the arc | 93 (10.3) | 195 (24.4) |
| tie: no start head / no stop head | 61 / 42 | 68 / 36 |
| tie: no pair at one position | 39 | 64 |
| tie: not adjacent | 32 | 93 |
| tie: narrowed (more than one pair, chords) | 13 | 143 |
| tie: enters from previous system / runs off the system | 29 / 20 | 68 / 36 |
| tie: pair decided, not in file (voices, end not in file) | 25 | 80 |
| tie: spelling differs / pitch contradiction | 3 / 17 | 61 / 2 |
| tie: `not_a_tie` (arc judged a slur) | 17 | 60 |
| twin naming an already-named pair | 19 | 56 |
| kind refused (same-pitch accidental unread, stacked slur) | 2 | 12 |

Written arcs lose a few more at the end (`arc_ends_in_one_chord` 37 L / 85 B; file has 165 tie links and 81 slurs on Litolff).

**True count with double-counting removed** (clusters = printed places, one row per curve):
- Litolff: 1,018 places, of which 272 staff-line boxes and 4 key-slot; 269 written (180 tie + 89 slur); **473 not written, 52.6 per page** (ranking bound 83.4).
- Brahms: 3,538 places, of which 2,226 staff-line and 2; 512 written (265 + 247); **798 not written, 99.8 per page** (ranking bound 160.1).
- Still an upper bound: a place counts as unwritten if the detector drew an arc box there and the file wrote nothing, so a false arc box counts. Round 7 (below) found most detector arcs fake; the crop look and p0 below put this at "mostly real".

**Brahms p0 at FILE level, against hand truth** (84 ties, 69 slurs, `data/hand-truth/pages/imslp317803/0.json`; written spans read from the exported MusicXML note pairs, matched 1:1 by place: x-overlap >= 0.6 of the shorter and the truth centre within the span's staff rows +-5 sp):
- ties: truth 84, written 33, right 20 -> recall 0.24, precision 0.61. At box level (ranking) it was recall 0.62 / precision 0.66: **the file loses 38 points of tie recall after the detector.**
- slurs: truth 69, written 74, right 43 -> recall 0.62, precision 0.58 (box level 0.89 / 0.72).
- wrong kind at the right place: 15 truth ties written as slurs, 9 truth slurs written as ties (24 of 107 written arcs). Kind-blind: 87 of 107 written arcs sit on a truth arc (precision 0.81), 87 of 153 truth arcs are found (recall 0.57).
- invented (written, no truth): 20 (16 slur, 4 tie). Missing: 66 (17 slur, 49 tie).
- fate of the 66 missing truth arcs (nearest detector box, IoU >= 0.3): 25 have a box whose fate is "marked" (the matcher or a later loss; unresolved), 8 `no_pair_at_one_position`, 6 `ink_is_a_staff_line` (real ties dropped as false staff-line boxes: 6 of 84 truth ties), 6 no detector box at all (3 slur, 3 tie), 4 written as slur, 4 `no_stop_head`, 3 `no_head_near_the_arc`, 3 slur-binds-fewer, 2 `no_start_head`, rest singles.
- **What this truth cannot see:** it is boxes, not pairs, so a right-place arc may still bind the wrong notes; it is one page of one plate (none for Litolff); the page state is still `labeling`, not `verified`; a cross-barline curve may be one truth box or two; my matcher is a tolerance rule, so the 25 "marked" misses are partly its own error (a control I could not make fail). It cannot say whether a written arc the truth lacks is a real arc nobody boxed.

**Crop look (rule 7, 10 minutes, mine not Sean's).** 35 randomly drawn arcs the file drops, across all the groups: about 34 look like a real tie or slur on the print (my reading of the contact sheet, tiles not enlarged); one (a tiny speck, `no_start_head`) is not. So the groups are mostly real cost, not detector fakes. Sean's 12 blind tiles decide it.

**Top causes** (STAGED path, with the rule's file:line)
1. **Slur "binds fewer than two notes"** (Litolff 195 places, Brahms 224): the two-note minimum `len(covered) < 2` at `tools/omr/export.py:2795`, over `_noteheads_under` (`tools/omr/export.py:2592`, pad `_SLUR_ARC_PAD_NOTEHEADS` 0.25 at `:1877`, a number tuned in 2026-09), counted at `tools/omr/staged/export.py:2609`. It asks the BOX which heads it covers. What the record holds for the same ink: `Q.SYSTEM_ARC` rows of these boxes (Litolff / Brahms) are both-ends-anchored for 99 of 287 / 123 of 379, `end_unanchored` for 188 / 178. And heads under the box (within +-0.5 sp x, +-6 sp y): fewer than two DETECTED for 146 of 195 / 90 of 224 places; at least two detected but fewer than two written 27 / 76; at least two written, so the rule or the voice filter refused it, 22 / 58. Two causes, then: (a) a head never detected or never written under the curve (a reading shortfall owned by notes), (b) a curve whose ends the system trace found and the slur pairing never asked (`staged/export.py` calls `_paired_spans` with boxes only; only `adjudicate_tie_pair` reads `Q.SYSTEM_ARC`, commit 0e9311136).
2. **Tie pair: no head near the arc / no start head / no stop head** (Litolff 73 + 42 + 36, Brahms 142 + 61 + 25 places): `_flank_search` and `adjudicate_tie_pair`, `tools/omr/staged/adjudicators/ownership.py:3036` / `:3241` (reasons at `:3085-3171`). In 57 of 93 Litolff and 106 of 195 Brahms "no head near" boxes the system trace itself has an unanchored end: the head is not in the record, so this is a notes shortfall again, not a pairing rule.
3. **Tie narrowed / not adjacent / no pair at one position** (Brahms 81 + 52 + 37 places; Litolff 9 + 20 + 27): `ownership.py:3395-3416` (`more_than_one_pair` is the file's `tie_pair_narrowed`). 40 of the 143 narrowed Brahms boxes already read as two adjacent heads at one position: a chord tie that names more than one head pair. Prior work: the tie-chain FINDINGS (776 tie ends land in chords on Brahms p0-3) and `omr-chord-tie-2026-09`.
4. **Tie read as slur / slur as tie** (p0: 24 of 107 written arcs): the detector class decides, `ownership.py:2808` `adjudicate_arc_kind`. Not a new axis; `OMR_ARC_RECLASS` was already REJECTED (page-facts s5).
5. **`tie_spelling_differs`** (Brahms 61 boxes, 38 places): `staged/export.py:2452`. The pairing is right and only the far head's accidental is not restated; the file still refuses it. Prior work: tie-pairing FINDINGS found 11 of 20 "wrong pairs" were the same case.
6. **Real ties dropped as `ink_is_a_staff_line`**: 6 of 84 truth ties on Brahms p0 (the ranking called this "not a cost"; it is for most boxes, not for these).

**Prior work used (and how today's groups relate).**
- `omr-arcs-system-2026-10` (2.166): built `Q.SYSTEM_ARC`, full-curve trace + head anchors, producer only; Sean's 13 tiles 7 right / 1 wrong / 1 swapped / 4 unanchored. Kept. Relation: group 1 and the unanchored ends in group 2. The erase half (`OMR_SYSTEM_ARCS_ERASE`) is OFF and not touched here.
- `omr-staged-arc-export-2026-09` and `omr-arc-recovery-2026-09`: made `arcs_not_written` a four-way partition (this lane reuses it as the control) and found the file wrote a quarter to a third of the encoding's arcs on Litolff (32 of 111 slurs, 80 of 300 ties); no recall claimed (page truth is not an encoding truth). Today's rate stays an upper bound for the same reason.
- `omr-staged-tie-chain-2026-09`: no `Q.TIE_LINK` built on purpose; the 76% "binds fewer than two" share is the detector's (arc boxes with no notes under them); a chain is not a link. Relation: group 1.
- `omr-tie-pairing-2026-09` (and `omr-chord-tie-2026-09` by its title and header only): the "wrong pair" premise was largely the arc's CLASS plus a spelling probe; pairing repaired by geometry. Relation: groups 4 and 5.
- `omr-arc-attribution-2026-09`: arc owner by the staff whose heads it hugs (2,644 / 14,814 fires, ink-rules); kept. Not a cause here.
- Round 7 (`omr-queue-arcs-2026-09/ROUND7_FINDINGS.md`, as quoted in the 2.166 FINDINGS): production arc precision 0.232, 260 of 268 teacher arcs fake. Today's crop look (34 of 35 real) is on arcs that already passed ADJUDICATE and were drawn by the detector; rounds 8-9 "by CV + anchors" were SUPERSEDED by 2.166 and I did not reopen them.
- page-facts s5: `OMR_ARC_RECLASS` REJECTED (+130 scan edits, all tie->slur). Not proposed. LEGACY `contextual.py` / `export.py` arc handling was read only through `_merge_arcs_across_barlines` / `_noteheads_under` / `_paired_spans`, which STAGED already imports; no LEGACY flag is read.
- Not read in full (headings only): `omr-arc-grammar-2026-09`, `omr-queue-ties-2026-09`, `benchmarks/_archive` arc files, `docs/ink-rules.md` beyond its arc rows (lines 171-187).

**Sean's 12 blind tiles.** `out/print/arcs-1029/blind/tiles/sheet.png` (single tiles `tile_01..12.png`, README in that folder), key at `out/print/arcs-1029/blind/key.json` (outside the tile folder). One neutral orange box on each, nothing of ours drawn. Plain question: "Is there a tie or slur here, and between which notes?" 10 arcs the file drops spread over six fate groups (two slur-binds-fewer on Litolff, one on Brahms; no-head-near on both plates; narrowed; no-stop-head; no-pair-at-one-position; not-adjacent; decided-not-in-file) and 2 controls (tile 7 a written tie, tile 8 a written slur). Not answered yet; judged right-to-wrong cannot be measured by this lane (no change was made: 0 by construction).



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
