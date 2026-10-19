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

## 2.167d -- why simple bars miss what we read elsewhere

Sean 2026-10-19 on the 2.167c tiles: "They seem like simple measures and we are just missing details that we are finding elsewhere without a problem."
STAGED, records 20261018-night (main 2bb43b85; worktree on main 13c6cd10+). Probes `probe/2.167d/` (`d0*` record extract, `d1_rerun.py` GATHER-only re-cut, `d2` control, `d3` sheets, `d4` box fates,
`d5/d6` join and table, `d7` meter column, `d8` new boxes, `d9` position, `d10` crops, `d11` scale; my item lists `items_lit.json`, `items_bra.json`; data in `probe/2.167d/data/`). No product code changed, nothing written to a record.
Same 45 + 45 held bars as 2.167c (same seeded sample, same order). Weights: the routed production file (`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, the record's own input_domain `scanned`), never phase-j-mix.

**Controls.** The bar's own cell re-built by the shipped `extract_measures` and run through `YoloDetector.detect` (iou 0.7, agnostic NMS off, imgsz by `imgsz_for_cell`) reproduces the record's detector boxes: Litolff 433 of 433, Brahms 859 of 859 (the other 7 Brahms boxes are `yolo_rescue_wedge` rows, a later pass). The re-cuts use the shipped `_build_measure_cell`; the staff space shown to the detector is 16.0 px in the bar crop, the half-bar shifts and the double-width crop on every bar (`d11`), but only 14.2 px (Litolff) / 11.6 px (Brahms) in the whole-system strip (the 2048 imgsz cap), so the system strip is a handicapped test.
**Who says it is right:** the items below are my look at the crops (ours, not Sean's, not evidence). I could not read 10 + 8 bars (dense, muddy) and 1 + 1 are voices; items come from 34 Litolff and 36 Brahms bars.

### What each cause is (92 items: 38 Litolff, 54 Brahms; in brackets, bars)

| cause (first place the symbol is lost) | Litolff | Brahms | all |
|---|--:|--:|--:|
| A. never boxed (no box of any class at 0.05) | 2 (2) | 3 (3) | 5 |
| B. boxed in the right class but UNDER the 0.25 floor (the record does not keep it) | 7 (6) | 14 (12) | 21 |
| C. boxed at 0.25+ but in the WRONG class (black head called a rest; rest called arpeggiato / accidental) | 8 (8) | 2 (2) | 10 |
| D. boxed right at 0.25+, then dropped or mis-valued by a later gate | 4 (4) | 22 (11) | 26 |
| F. boxed, but in the NEIGHBOUR cell (a head at the barline) | 1 (1) | 0 | 1 |
| E. non-note ink boxed as a note/rest and written (clef curl, key flat, digit, dynamic f, barline-edge ink, a rest of the staff above) | 12 (11) | 6 (6) | 18 |
| G. one chord of a second counted as two events (EVALUATE grouping) | 2 (2) | 6 (3) | 8 |
| H. one rest ink boxed twice in two classes, both written | 2 (1) | 1 (1) | 3 |

Lost real symbols (A-D, F) are 63 items (Litolff 22, Brahms 41); extras (E, G, H) are 29. D counts one item per kept box, so Brahms bars 0, 4, 14, 38, 39 weigh 6, 3, 3, 2, 2.

**The dominant cause is not the crop window. The detector SEES most of these symbols, and either keeps them under a floor (B, 21), calls them something else (C, 10) or a later gate throws a correct box away (D, 26).** Of the 63 lost real symbols: B+C 31 (49%), D 26 (41%), never boxed 5 (8%), neighbour cell 1 (2%). By plate: Litolff 17 of 22 are A/B/C (detector side); Brahms 14 of 41 are B (flags and dots) and 22 are D (gates). Extras (29) are a further third of the held bars' items.

### (1)-(2) what the detector and the gates did, by cause
- **B (under the floor)**: `gather.gather_detections` calls `detect(conf_threshold=0.25)`; a box at 0.05-0.25 never reaches the record (the only second floor, `RESCUE_CONF_FLOOR` 0.10, runs on a cell with NO box at all). Brahms: 13 of 14 B items are augmentation dots and flags (dot 0.06-0.24, flag 0.12-0.24 beside a head the detector kept at 0.7+); Litolff: black heads welded to staff lines (0.10-0.24) and eighth/quarter rests (0.18-0.20). In the 90 bars the base pass holds 0.10-0.25 boxes: Litolff 63 note, 20 rest, 4 flag, 5 dot; Brahms 36 note, 25 rest, 17 flag, 15 dot (`d9`), against 94 flags/dots kept at 0.25+ in Brahms.
- **C (wrong class)**: 4 of 4 Litolff heads boxed as `restWhole`/`restHalf` (0.26-0.35) are square black blocks filling the space between two lines; `family_precision.adjudicate_rest_is_not_a_rest` refuses them (`rest_has_a_stem`) and nothing re-reads the ink as a head, so the head is lost. Also quarter rests boxed `arpeggiato` 0.49-0.63 (3 bars), an eighth rest boxed `accDoubleSharp` 0.26 (Brahms 42).
- **D (gates)**: 6 real rests of Brahms p3 system 0 (oboe and timpani header bars), boxed 0.34-0.83 and DECIDED rests, are dropped by `family_precision.adjudicate_rest_is_not_a_rest` -> `key_slots.meter_column_occupant` (`rest_is_a_meter_digit`, header cell 0 only): the "meter column" it read off the sibling digit boxes is page x 793-1291, 497 px, about 18 staff spaces wide, so rests at x 989-1259 fall inside (`d7`). Ten kept heads (0.63-0.85) in 4 Brahms bars are lost to `duration_narrowed` / `chord_value_undecided` (the 2.170 lane's beams). Dots: 4 dot boxes at 0.4-0.8 sit beside heads written plain or a chord's two dots (one per head) are read as a double dot; the function that does it is not traced here.
- **E / G / H**: no gate refuses them, the detector's own class stands: a treble-clef curl as `rest8th` 0.70, a key-signature flat as `rest8th` 0.26, a rehearsal "0" as a hollow head, the hook of a dynamic f as a head, an accidental as `restQuarter` 0.30, a barline sliver as `noteheadWhole` 0.32. Chords of a second with the heads displaced either side of the stem become two events (Litolff bars 20, 38; Brahms 16, 24, 43), cause by 2.167c's account, grouping function not traced here.

### (4) where the never-boxed and the lost items stand in the crop
Not at the edge: none of the 63 lost items has its box centre within 1 staff space of a barline; medians 6.8 sp (A), 3.7 (B), 2.3 (C), 4.1 (D). The one neighbour-cell item (Litolff 7, a head at the barline whose stem is the barline) is a guess of mine. A mild edge effect exists in the whole census: of all notehead/rest/flag/dot boxes the detector draws at 0.05+, the share kept at 0.25+ is 0.18 (Litolff) and 0.47 (Brahms) in the first tenth of the bar, 0.5-0.8 in the middle, 0.53 / 0.51 in the last tenth, but those edge boxes are mostly clef, key and barline ink, not lost symbols.

### (5) the second detector pass, GATHER-only (A-C = 36 detector-side items)
Found = a box of the wanted family at 0.25+ at the item's spot, same weights, same settings. Shifted half a bar right / left: 5 / 1 of 21 (B only). Double-width crop: 16 of 36. System strip: 3 of 36 (handicapped scale). Any variant: 23 of 36 (A 2 of 5, B 17 of 21, C 4 of 10; Litolff 7 of 17, Brahms 16 of 19). Almost all of it is the same ink getting a higher score in the wider crop: of the 33 / 25 new boxes the double-width crop adds in the 45 Litolff / Brahms bars, 24 / 19 were already boxes under the floor (e.g. the Brahms bar 2 dot is 0.13 in the bar crop and 0.60 in the wide one, same pixels, same staff space). So a second pass here is a context-dependent LOWER FLOOR, not a new look at unseen ink.
Cost, same bars, by my look at all 58 new double-width boxes (ours, not evidence; tiles `sheets/new_wide_*`, not committed): Brahms about 22 of 25 are real flags, dots and rests (precision about 0.9); Litolff about 5 of 33 are the right symbol in the right class, about 7 more are a real head or rest in the wrong class, about 21 are false or unclear (accidentals, stems, beams, dynamic f). New boxes at 0.25+ per variant over 45 bars, Litolff / Brahms: shift right 8 / 18, shift left 17 / 11, double-width 33 / 25, system 24 / 49. A shifted window alone would recover little (the symbols are not near an edge) and cost 11-18 new boxes per plate.

### (6) the same symbol read fine nearby
Brahms bar 7 (contrabass p20): the first Gb3 eighth's flag is read at 0.68, the second's at 0.22; same bar, same engraving, both in the middle of the crop (x 2-4 of 21.9 sp and 11-13); nothing I can measure differs except the lower flag's stem crossing three staff lines. Brahms bar 2: the first dot 0.51, the second 0.13, both round dots in a clear space. Litolff: the same black head is `noteheadBlackInSpace` 0.85 where it is an oval (bar 35) and `restWhole` 0.35 where scan blur squares it between two lines (bar 2; also bars 5, 41, 42). So "found elsewhere without a problem" is the same symbol at a higher score: the score is the only thing I can show differs, and I cannot show its cause.

### What a fix would be, and its reach (estimates, none measured on the exported file)
1. Widest and cheapest: a per-class floor below 0.25 for `dot`, `flag*` and rest classes in held bars (or a second pass at the bar crop widened by half a bar each side), then the existing gates. Reach: B is 21 of 63 lost real symbols (33%; Litolff 32%, Brahms 34%). Precision by my look is about 0.9 on Brahms and 0.15-0.35 on Litolff, so it must be per plate or per class and proven on Sean's tiles first (CLAUDE.md rule 5: print before default). It does not touch the bar-sum rule.
2. Re-read a refused rest box whose ink is a black head (`rest_has_a_stem`) as a head candidate: 4 of 22 Litolff lost symbols (18%).
3. Bound the meter-column gate to the digits' own width: 6 rests in 2 of 45 Brahms bars, n too small to scale.
4. The 29 extras are class errors the gates do not catch (clef curl, key flat, digit, accidental, barline ink): a separate fix per ink.
Not done: no fix built, no tile put to Sean beyond the 8 crops `out/print/2.167d/`; D's dot and narrowing mechanisms are named, not traced.
