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

## 2.167c -- why bars are held out; voices

Sean 2026-10-19: "How are we at reading multiple voices? I am afraid that would be a big culprit to bars not adding up? Also, show 10 tiles ... the original score next to what we have figured out and what doesn't add up."
STAGED, records 20261018-night (main ad0d8114). Probes: `probe/2.167c/` (`c1_capture.py` runs the shipped export and captures each held bar's events, `c2_features.py`, `c4_sheet.py`, `c5_breakdown.py`, `c6_tiles.py`; my labels in `labels.json`). No product code changed.
Control: the capture finds every bar of the coverage held list (Litolff 564 of 564, Brahms 915 of 915 non-doubled); over/short 196/368 and 501/414.

### Part 1: voices

Answer: multiple voices are NOT the big culprit. In a random 45 held bars per plate that I looked at crop by crop (ours, not Sean's, not evidence), two voices summed as one is **1 of 45 (Litolff, about 13 of 564)** and **3 of 45 (Brahms, about 61 of 915)**; the Brahms 3 are the least sure of my labels. With n=45 the honest range is 0-12% (Litolff) and 1-18% (Brahms).
Mechanical counts over ALL held bars agree: both stem directions among the exporter's events in Litolff 35 of 564 (6%), Brahms 199 of 915 (22%); an up-stem and a down-stem event at one onset (the convention's rule 1): **0 and 3**; the shipped splitter's candidate would fill the bar: **0 and 6**. Bars already written as two voices that still fail the sum: 9 and 21. Most Brahms bars with both directions are one line whose stems change direction along the bar, not two parts.
What the splitter does (STAGED `adjudicate_voices` in `rhythm.py`, plus the exporter's `_divisi_pairs` / `_voice_split`): needs an up-stem and a down-stem event; rule 1: two voices if an up and a down event share an onset column; rule 3: one voice if the merged sum equals the meter; rule 2: two voices only if EACH stream sums to the whole meter AND the streams sit in separate vertical bands; otherwise it abstains `no_voice_convention_fits` (107 Litolff / 638 Brahms, the manager's count). It abstains because nearly all held bars have no opposite-stem pair, and where two parts do share a staff they are not lined up or one part is mostly rests, so neither stream sums. The convention it would need: Sean's 2026-09-29 rules cover the lined-up and the full-bar cases only. Two wind parts on one staff (Ob./Cl./Fag. 1.2, stems up for part 1, down for part 2, rests displaced up and down) would need a further rule: a stem direction is a voice, each voice is summed with its own rests, two voices when each alone fills the meter. That is a PROPOSAL for Sean, not a ruling (`docs/page-facts.md` has only the displaced-rest and dot-side facts); not built here.

### Part 1: why bars are held (random 45 per plate, labels in `probe/2.167c/labels.json`)

(a) two voices summed as one; (b) a note or rest missing (never boxed, or boxed and refused); (c) an extra counted that is not a note of this bar (accidental, clef, key, meter digit, barline-edge ink, another staff's note, one chord split in two events, one ink read as both rest and note); (d) a wrong value (flag/beam missed, dot missed or doubled); (e) meter wrong: 0 seen; (f) doubled staff / copy: 0 (those 60 Litolff bars are outside the 564); (g) other.

| cause | Litolff n=45 | scaled to 564 | Brahms n=45 | scaled to 915 | pooled share |
|---|--:|--:|--:|--:|--:|
| (a) two voices as one | 1 | ~13 | 3 | ~61 | 5% |
| (b) note/rest missing | 22 | ~276 | 8 | ~163 | 30% |
| (c) extra non-note / duplicate | 12 | ~150 | 14 | ~285 | 29% |
| (d) wrong value | 8 | ~100 | 20 | ~407 | 34% |
| (g) other (a barline note plus a rest read as a quarter; an Adagio rest alone) | 2 | ~25 | 0 | 0 | 2% |

Scaling: sample share times that plate's held count, rounded; one seeded draw per plate (2167 / 2168), so each cell is a point estimate with a wide band (8 of 45 is 9-31%). The plates differ a lot; the pooled share is a mix, not a rate.
Inside (b): Litolff 22: 8 show an unboxed head on the page, 14 show a bar with one note and nothing boxed where the rest of the bar stands (a rest not boxed, or not visible to me at this scan quality); Brahms 8: 3 show heads the reader refused (red, duration narrowed), 5 unboxed rests or heads. Inside (c): non-note ink 8 / 8, chord split into two events 3 / 4, one ink counted as rest and note 1 / 2. Inside (d): Litolff flags/beams 6, other 2; Brahms flag/beam 9 (some blue guesses of a quarter on a flagged note, some READ black), dots 9, other 2.
Overfull vs short (sample): Litolff 21 overfull / 24 short, Brahms 32 / 13 (population 196/368 and 501/414). The 37 short bars are b 30, d 5 (Brahms dot misses), c 1, g 1; the 53 overfull bars are c 25, d 23, a 4, g 1. So SHORT points to a note, rest or dot missing; OVERFULL to an extra non-note, a split chord, a flag missed, or two voices. Litolff short by exactly one quarter (218 bars) or an eighth (118) is one rest or note missing; Brahms overfull by an eighth (199 bars) is mostly a flag missed or one extra eighth of ink.
Biggest: pooled, wrong value (d), missing (b) and extra (c) are near thirds; by plate, Litolff is missing items (about half) and Brahms is wrong values (44%) and extras (31%). Fixing (b) on Litolff means boxing rests and heads that merge into thick staff lines (detector recall). Fixing (d) on Brahms means reading flags and augmentation dots (including a chord's dots read as a double dot): a per-symbol reader, not the bar sum, which cannot supply them (CLAUDE.md section 4).
Caveats: labels are my look at 600 dpi crops of coarse scans; a (b) bar can also be a (d) bar; I did not count how many bars would sum after each fix.

### Part 2: tiles

`out/print/2.167c-held-bars/` tile_01..10.png, README.md, index.json (made together by `probe/2.167c/c6_tiles.py`, which checks 10 files == 10 index entries). Side by side, NOT blind. 3 missing note (b), 3 extra counted (c), 3 wrong value (d), 1 two voices (a); 4 Litolff, 6 Brahms.
