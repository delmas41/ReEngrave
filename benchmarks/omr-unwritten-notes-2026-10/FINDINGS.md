# ROADMAP 2.167: why noteheads never reach the file (STAGED, read-only)

Records: 20261016-night (main 1d42c4aa). Landings 2.158/2.159/2.161/2.164/2.166 are NOT in them. Probes: `probe/2.167/`.
Controls: the instrumented export reproduces the overnight `notes_not_written` dict exactly on both plates (Litolff 5,916; Brahms 14,997);
the slim Brahms load (drops `considered`/`correlated`) gives rows byte-identical to the full load on Litolff; bucket sums are asserted.

## Prior work that answers parts
omr-stem-pair-rule-2026-09 (PAIRED rule deletes stems; 62 of 80 deleted stems on a head were paired with ANOTHER real stem),
omr-stem-notehead-gate-2026-09 (`OMR_STEM_NOTEHEAD_GATE`, default OFF, +80/+152 strokes all on a head, no-stem heads 793->720, 1,529->1,351;
never put to Sean), omr-head-fill Sec.17 (2.161: 2,633 / 7,475 no-stem heads), omr-bar-sum-holdout (2.22/2.30).

## Part 1
a. `head_stem: no_stem` = `stem_value.adjudicate_head_stem`: no `Q.STEM` row of the head's cell (padded into neighbours) has a box overlapping the
head's detector box (`geometry.stem_touches_head`, zero tolerance). `Q.STEM` rows are the CV finder's accepted vertical runs
(`line_detection.detect_stems`). Counted per notehead-classed box, kept or refused, copies included. Litolff 2,633 of 11,399 boxes.
b. Whole notes are counted (23 of 2,633; only 45 whole-class boxes exist in the movement). no_stem does NOT stop writing: export has no refusal
named for it. Of 710 kept (not non-note, not copy, not rest ink) no_stem heads: 360 in file, 154 in held bars, 13 partial bars, 115 duration narrowed,
67 chord_value_undecided, 1 no_pitch. Cost: kept no_stem heads are lost to narrowing/chord disagreement 25.6% vs 2.7% for stemmed heads.
Of the 2,633: 1,065 are copies owned by another staff (stem lives in the other cell), 703 refused as non-notes by verdict.
c. Seeded random 40 of the 760 kept no_stem Litolff heads (`p2_stems.py`; shipped finder re-run per cell, control 40/40 cells reproduce Q.STEM):
39 of 40 have a vertical run >= 1.5 sp beside the head. (i) finder never outputs it: 33 (PAIRED/accidental rule 14, too WIDE 7, too TALL 5, too SHORT 4,
cell EDGE 2, never a candidate 1); (ii) accepted stem beside the box, contact test fails: 6; (iii) connected then lost: 0 by construction; 1 no ink.
By my eyes (ours, not evidence) 2-3 of the 40 are not notes. Tiles: out/print/2.167-stems/ (11 incl. 2 controls).

## Part 2: first cause, by box and by ink
Litolff 11,399 boxes = 9,047 distinct ink. In file 6,474 ink (8,276 boxes; 1,802 extra copies, correctly refused). File notes 6,731 = 6,474 - 31
(red gap) + 288 re-written on the doubled Contrabass staff (derived residue, not instrumented). Ink NOT in file: 2,573 (+31 gap).
Brahms 24,260 boxes = 20,295 ink; in file 12,403 (2,751 extra copies); NOT in file 7,892 (+233 gap); notes 12,152 closes to within 18.

| first cause (ink not in file) | Litolff | Brahms | real notes? |
|---|--:|--:|---|
| bar held out, durations do not sum | 1,237 | 2,612 | real, pitched; held by design |
| duration NARROWED (beams / head fill) | 292 | 1,232 | ~12 of 16 eyeballed Litolff real |
| too_narrow box | 236 | 3,037 | non-notes (barline slivers, 8th rests): 16/16 Brahms eyeballed |
| clipped_fragment | 199 | 310 | mostly cut copies / letters (eyeballed) |
| ink read as whole rest | 108 | 15 | rests |
| chord_value_undecided | 96 | 211 | real |
| no_pitch (clef-abstained staves) | 95 | 0 | real |
| tremolo / dynamic letter / clef / beam / key slot / meter digit | ~150 | ~215 | non-notes |
| owned_by_another_staff, no twin kept | 30 | 53 | copy whose owner lost it |

Copies refused as owned_by_another_staff: 1,326 / 3,055 (990 / 2,117 have a twin written; 195 / 621 a twin in a held bar).
Sean's judged tiles on these boxes are only tens, so the real/non-note splits are mine (ours, not evidence).

## Fix first
(1) Stem finder PAIRED/WIDE/TALL refusals: biggest cause of no_stem on real notes; OFF flag `OMR_STEM_NOTEHEAD_GATE` exists; re-measure and tile it.
(2) The bar-sum hold: largest real-note bucket (1,237 / 2,612); 95% of Litolff held heads sit in bars with no dropped neighbour, so the sum is off for
another reason; needs its own classification.

## 2.167b -- ranking on 20261018-night

Same probes, same partition, same controls (`probe/2.167/p1_table.py`, `p3_partition.py`, `p3b_ink.py`; new `p9_moves.py`, `p9b_newheld.py`,
`p10_table.py`), rerun on the 20261018-night records (main 2bb43b85, through infer; carry 2.158/2.159/2.161/2.164/2.166/2.162/2.169/2.168).
The 20261016-night records were rerun too, so both columns are one method. Slim outputs: `benchmarks/omr-unwritten-notes-2026-10/2.167b/`.
Controls HELD: instrumented export reproduces `notes_not_written` exactly (1016: Litolff 5,916 / Brahms 14,997 as in 2.167; 1018: Litolff 6,015 / Brahms 15,310,
equal to the overnight coverage.json dict for Litolff and Brahms); buckets sum to the box count and ink clusters to the same 9,047 / 20,295 on both nights
(identical detector boxes, so boxes join one-to-one by subject).

Distinct ink NOT in the file (real / non-note class is the agent's look carried over from 2.167, ours, not Sean's):

| first cause | Lit 1016 | Lit 1018 | Brahms 1016 | Brahms 1018 | class (agent look) |
|---|--:|--:|--:|--:|---|
| bar held out, durations do not sum | 1,237 | 1,395 (+158) | 2,612 | 2,870 (+258) | real, held by design |
| too_narrow box | 236 | 236 | 3,037 | 3,037 | non-note |
| duration NARROWED | 292 | 235 (-57) | 1,232 | 1,126 (-106) | mostly real |
| clipped_fragment | 199 | 199 | 310 | 312 | cut copies / letters |
| chord_value_undecided | 96 | 63 (-33) | 211 | 195 (-16) | real |
| ink read as whole rest | 108 | 108 | 15 | 14 | rests |
| no_pitch (clef-abstained) | 95 | 95 | 0 | 0 | real |
| tremolo slash | 49 | 58 | 114 | 116 | non-note |
| owned_by_another_staff, no twin kept | 30 | 31 | 53 | 58 | copy whose owner lost it |
| is_an_arc_tail (new refusal) | 0 | 6 | 0 | 14 | non-note |

Totals: ink not in file Litolff 2,573 -> 2,664 (+91), Brahms 7,892 -> 8,049 (+157); notes written 6,731 -> 6,626 and 12,152 -> 11,991;
notes_not_written 5,916 -> 6,015 and 14,997 -> 15,310. The file got SMALLER on both plates.

What moved (box level, `p9_moves.py`; Litolff 411 of 11,399 boxes changed bucket, Brahms 752 of 24,260):
- The hold grew by far the most: WRITTEN -> held bar 174 (Litolff) / 333 (Brahms) boxes in 52 / 91 newly held bars. In 43 / 88 of those boxes the old duration
  reason was `meter_reconciliation` (the bar had supplied or moved the value) and the new one is `bar_disagrees_with_decided`: traceable to 2.162 + 2.168
  (the bar no longer moves a DECIDED note, it marks it; the bar still fails its sum, so it is held). In the rest (128 / 228) the cell's own verdicts are unchanged: a
  neighbour in the bar changed value, a bar-level effect I did not trace further, cause unknown.
- Narrowed notes and undecided chords moved into the file or into a hold: narrowed -> WRITTEN 56 / 91 boxes, chord_undecided -> WRITTEN 24 / 11. Their new verdicts
  are `head_and_marks` (and Brahms `stem_tip_reads_no_beam`): consistent with the head-fill / box / stem landings 2.158/2.159/2.161/2.169, but the record does not
  say which one decided each note, so which landing is unknown.
- 2.164 (tie ends / barline ink): no change in too_narrow or clipped_fragment on either plate; either it did not touch these records' boxes or its effect shows in other
  buckets. Unknown. `is_an_arc_tail` (6 / 14 ink) is new; 2.166 (system arcs) is the likely source by name, not proven here.
- Unchanged to the unit: too_narrow (Brahms 3,037 non-notes), whole rest, no_pitch (Litolff 95), dynamic letters, clefs.

Reading: the landings made more notes DECIDED, and more bars then fail their sum, so the largest real-note bucket (bar held out) grew by 158 / 258 ink while the narrowed
bucket shrank by 57 / 106. Net, 2.167 Fix first (2) (what makes a bar not sum) is now larger than before; Fix first (1) (stem finder) shows as narrowed/chord falling.
