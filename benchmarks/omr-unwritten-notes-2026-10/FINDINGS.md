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

## 2.167e -- Sean's tile questions (unison flags, eighth rests, aug dots, invented whole note)

Sean 2026-10-19, on the six 2.173 red-bar crops (`out/print/2.173/`, numbered 1-6: litolff p13 s0 st8 c5, litolff p1 s0 st9 c2, litolff p5 s0 st1 c2, brahms p5 s0 st8 c0, brahms p8 s1 st8 c11, brahms p19 s0 st10 c3): *"Why are we not getting flags on both sides of the unison notes? We seem to be missing simple 8note rests. Are they not being read or being dumped? How are we missing Aug dots? Tile 5 is the strangest to me - how did it invent a whole note?"*
STAGED, records 20261018-night (main 9de907bf; no product code changed, nothing written to a record). Probes `probe/2.167e/` (`e2` cell dump, `e5` per-box table, `e7` whole-movement extract, `e8`-`e24` the counts below; the `*_all.json` extracts are 18 + 47 MB and not committed, `e7_extract.py` rebuilds them in 15 s / 80 s). Red-bar list: the 2.173 replay's `red_rows.json` (624 Litolff / 915 Brahms bars, copied to `data/`). Crops: `out/print/2.167e/` (blue box = the symbol; README).
**Who says it is right:** the record says what the readers did; my look at the print crops says what the symbols are (ours, not Sean's, not evidence). Where a number rests on my look it says so.

### Tile by tile (what the record holds)

- **Tile 3 (unison).** Litolff `glyph/5/0/1/2/13`: ONE black head at 0.27, a stem up at its right (flag8thUp 0.59 boxed) and a stem down at its left (flag8thDown 0.48 boxed), `flag_is_not_a_flag` false for both. `adjudicate_head_stem` (stem_value.py) narrowed it `two_stems`, not `unison_two_voices`: `_one_stem_per_head` wants one stem that reaches 0.8 spaces on one side only, and the up-stem's row runs 1.0 space below the head as well (the two strokes touch at the head). `adjudicate_stem_value` abstained `ambiguous_stem`; `adjudicate_duration` decided 0.5 `head_and_marks` (both flags agree). `adjudicate_event` filed ONE glyph as one event and `adjudicate_voices` said one voice. So the flag of the other voice was counted and thrown away as a witness, and the other voice's note was never made. The file has one eighth.
- **Tile 4 (rest).** Brahms `glyph/5/0/8/0/18`: the second eighth rest, `rest8th` 0.32, was refused `rest_is_a_duplicate_box` by `family_precision._duplicate_box_refusal` (ROADMAP 2.15). Box 13 (`rest8th` 0.49, a double-width box over BOTH rests) overlaps it and outranks it; box 13 itself was refused as a duplicate of the first rest (0.57, kept). The rule never asks whether the box that outranks it survived. The first beamed eighth head at the cell's left edge was never boxed.
- **Tile 6 (dot).** Brahms `glyph/19/0/10/3/5`: the dot after the quarter was boxed `augmentationDot` 0.44. `adjudicate_dot_role` (rhythm.py, 2.131 `OMR_STACCATISSIMO_SHAPE`, ON) tries the staccatissimo-wedge test BEFORE the augmentation window: the dot sits on a staff line, so its ink reads taller than wide (hw 1.346 against floor 1.3, taper 0.75 against 0.8, height 0.70 sp in 0.40-0.85) and `mark_tip` finds no head: `wedge_without_a_head`, abstained, never tried as an augmentation. The head beside it (a quarter) is written plain.
- **Tile 5 (whole).** Brahms p8 bar 160, see Q4 below.
- **Tiles 1 and 2 are neither.** Tile 1: nine heads (three stacked columns, two staves) and no rest or dot in the print; all nine heads are valued as eighths (`beam_levels` 1; the middle stem reads 0 though the stroke runs across all three) and the LilyPond rendering flags the third event instead of beaming it (export's beam grouping, not traced here). Tile 2: one black head was boxed twice, `noteheadBlackOnLine` 0.73 and `noteheadHalfOnLine` 0.38 at the same box (glyphs 1 and 5); `adjudicate_event` grouped both as one chord and the half (2.0) was written, so the bar counted 3.5 for 2.0. 61 Litolff and 31 Brahms heads are boxed twice in two classes and both kept (10 + 4 in red bars, `e22`).

### Q1. Why no flags on both sides of the unison notes?

**Because the record holds one head, and one head becomes one note in one voice.** Nothing between GATHER and EXPORT turns a head's second stem into a second note. `adjudicate_head_stem` (rule `unison_two_voices`, 2.87) keeps both stems as candidates so that `adjudicate_duration` (2.141h `_unison_two_voices`, 2.75 per-voice beam count) can count each stem's beams and flags on its own side; `adjudicate_event` x-clusters glyphs, one glyph one event; `adjudicate_voices` builds streams from stem direction over events; `export.py` has no "unison" in it. The second voice's flag is consumed as a witness for the one value.
- **How general** (kept heads whose `head_stem` is narrowed with a stem on each side; both plates): Litolff **522** = 471 `unison_two_voices` + 51 `two_stems` with a stem flush left and one flush right (the tile-3 shape; the rule missed it); Brahms **245** = 206 + 39. In red bars: 80 Litolff, 53 Brahms. Another 62 + 37 `two_stems` heads have stems that are not left-and-right. Sample of 32 (16 per plate, seeded 2167, my look): most are a head with a stem up at the right and a stem down at the left, the a2 / divisi unison; a few are a head beside a barline or ledger stroke. Read the 767 as an upper bound, about two thirds real by that sample.
- **What the shared heads got:** duration `head_and_marks` decided for 400 of 471 Litolff / 141 of 206 Brahms rule-fired heads; the rest narrowed (`beams_ambiguous`, `beam_discounted_uncertain`) or settled by the bar.
- **Function behind it:** `stem_value.adjudicate_head_stem` / `_one_stem_per_head` (which heads count as a unison), `rhythm.adjudicate_event` + `adjudicate_voices` (one head, one voice), `export` (writes each glyph once).

### Q2. Missing simple eighth rests: not read, or dumped?

**Mostly read; a few are dumped by two rules, and more were never boxed.** Whole movement, `rest8th` boxes at 0.25+ and what the standing `rest_is_not_a_rest` verdict did (Litolff / Brahms): boxes 217 / 4,117; **kept 169 / 3,495**; refused 48 / 622: duplicate 14 / 495, key-signature slot 21 / 20, clipped by crop 2 / 71, outside its staff 1 / 19, meter digit 4 / 11, stroke into a head 5 / 5, dynamic letter 1 / 0, overlaps a head 0 / 1. The rescue reader (`unboxed_ink_is_a_rest`, ink the detector never boxed) found a further 70 / 426 eighth rests (written).
My look at the refusals (12 crops, 3 per gate, Brahms): key-slot (3/3) and outside-staff (2/3) are flats and wedges, correctly refused; clipped-by-crop 2/3 wedges. **`rest_is_a_meter_digit` 3/3 are real eighth rests** (Brahms p3 header bars, 2.167d cause D: the "meter column" read off the digit boxes is 18 spaces wide), 11 in the movement, 9 of them in red bars. The duplicate rule is right almost always: of the 508 duplicate-refused eighth rests with an overlapping box found, IoU with the box that refused them is 0.56-0.68 (quartiles) (one rest boxed twice); only 2 sit at IoU under 0.15 with centres apart. **Chain drops** (the rest refused is real, only a refused box covered it, as tile 4): Litolff 0 eighth (but 13 quarter, 5 whole, 1 16th), Brahms **4 eighth** (1 in a red bar: tile 4), 14 quarter, 35 whole, 1 16th.
**Never boxed or boxed under the 0.25 floor** (no refusal, the record does not hold them): in the 2.167d 90-bar hand sample the lost eighth rests are Litolff 2 (1 never boxed, 1 at 0.20) and Brahms 10 items in 6 bars (6 meter digit, 1 never boxed, 1 at 0.18, 1 duplicate, 1 boxed as an accidental). That is a hand sample, 45 bars a plate; it is not scaled to the 564 / 915 red bars here.
- **Stage by stage (eighth rests, whole movement, record counts + that sample):** GATHER (no box, or under `conf_threshold` 0.25): the largest share by the sample, not countable from a record; ADJUDICATE `family_precision.adjudicate_rest_is_not_a_rest`: 11 meter-digit (real), 4 chain, about 15 in all against 3,664 kept; EVALUATE/EXPORT drop none (a kept rest is written; the 2.173 files hold 1,158 / 5,281 rests).
- **Functions:** `family_precision._duplicate_box_refusal` (2.15, `REST_DUPLICATE_IOU_MIN` 0.02, never asks whether the box that outranks it was itself refused), `key_slots.meter_column_occupant` (via `rest_is_a_meter_digit`), `gather.gather_detections` floor.

### Q3. How are we missing augmentation dots?

Four places, in order of the pipeline. Whole movement, `augmentationDot`-class boxes at 0.25+ (Litolff / Brahms): 154 / 6,840.
1. **Never kept: under the 0.25 floor** (GATHER, `gather_detections`). Not in the record. 2.167d's Brahms sample: 6 of 11 lost dot items were 0.06-0.24, 1 never boxed.
2. **Boxed, role refused** (ADJUDICATE `rhythm.adjudicate_dot_role`): decided augmentation 17 / 6,296; unresolved **99 / 393**: `dot_role_ambiguous` (no head in either window) 78 / 269, `on_a_stroke` 12 / 42, `wedge_without_a_head` 2 / **73** (tile 6; 26 of the 73 in red bars, 36% against 19% of heads there), no notehead in cell 4 / 0, barline 2 / 7, wedge points away 1 / 2. Another 38 / 143 are re-read as staccato by position.
3. **Read, attached, then not applied** (the head's own value). Of Brahms' 6,296 decided dots, 5,154 name a head with a decided dotted value (30 double); **573 name a head whose duration is narrowed and 569 one whose duration is abstained**, 10 a head decided with no dot. So about 18% of the read dots are dropped because the head's value is unresolved (2.167d "value not applied"). Litolff: 16 of 17 reach a dotted head.
4. **Stray chord or double dots** (wrong reads, 2.167d: 3 double-dot misreads in 45 Brahms bars).
- **Functions:** `rhythm.adjudicate_dot_role` (the wedge test ahead of the augmentation window), `rhythm.adjudicate_duration` / `_attached_dots`, `gather.gather_detections`.

### Q4. Tile 5: how did it invent a whole note?

**Ink.** The lower curl of a Breitkopf quarter rest (the rest SHATTERS): `glyph/8/1/8/11/11`, detector `noteheadWholeInSpace` 0.285, page box [4993, 6372, 5029, 6403]; the rest itself is `restQuarter` 0.65 (glyph 4, kept, written as the rest). The CV stem finder read the rest's own vertical body as a stem (`obs:260547`, centre line in the middle of the box, x_frac 0.5).
**Stages.** `adjudicate_notehead_is_not_a_notehead` (notehead_precision) let it stand: its fragment gates ask IoU 0.9+ against a rest or digit box (`is_a_rest_twin`, `is_a_time_signature_digit`) and `family_precision._rest_overlaps_notehead_refusal` needs IoU 0.3 AND the same centre and only ever refuses the REST; a curl that is the lower third of a rest box passes. `adjudicate_head_stem` then joined it to that stem `one_stem`, and **`rhythm.adjudicate_duration` gave it 4.0 from the detector's class alone** (`head_and_marks`, the closing `return` of the function; `_HEAD_BEATS["noteheadWhole"]`). The 2.130 guard (a whole-class head with a stem read flush at its SIDE is a half, `whole_class_on_a_stem`) did not fire because `_stem_flush_to_head` excludes a stem through the middle. The centre window of the head's ink reads 0.73 (filled), the stem verdict is decided: two readings against "a whole", ignored. The bar then counted 7 against 3 and went red.
**Against CLAUDE?** Yes, three ways. §5 / DECISIONS 2026-10-09: *a whole note has no stem*; a head the stem joined must never be a whole. §4: nothing uncertain is written unmarked, and the manifest row is status READ (0.285 box, an ink reading that contradicts it, a stem that contradicts it). Rule 8: "cannot tell" written as an answer.
- **How general.** Heads with a standing decided WHOLE (written 4.0), whole movement: Litolff **8**, Brahms **67**. I looked at all 75 (`out/print/2.167e/` crops 4-6 and my sheets): **none is a whole note.** Litolff 7 are whole-rest blocks (black rectangle under a line) read as `noteheadWhole*` at 0.26-0.42, 1 the blob of an `sf`; Brahms 39 are the loops of the 8 / 6 of 6/8 in header cells (0.26-0.63), 25 the lower curl of a rest (tile 5), 2 flat bowls, 1 the tail of an f. By the record's own ink: **42 of the 75 have a filled centre (>= 0.6) or stem ink** (Litolff 8, Brahms 34: 26 filled, 7 filled with a stem, 1 hollow with a stem); the other 33 are hollow loops (digits, curls) with no stem. 72 of the 75 are `head_and_marks`, 3 (Litolff) were settled by the bar (`bar_disagrees_with_decided`); 8 have a stem joined. **In the exported 2.173 files there are 56 whole notes (Litolff 2, Brahms 54), every one inside a red bar, 46 of them marked READ.** 53 are in my list of 75; the other 3 are real dotted wholes (6 beats, a real dot, crop checked). 29 of the 56 have a filled centre or stem ink; the other 27 are hollow loops. So the red bars with a "whole" in them are red because of an invented whole.
- **Not the same as** the 3 real dotted wholes, and not counted: an invented HALF (tile 2's double box, 61 + 31 twins, above).
- **Functions:** `rhythm.adjudicate_duration` (class value `head_and_marks` for an open head whose ink reads filled or whose stem is attached), `notehead_precision.adjudicate_notehead_is_not_a_notehead` (no containment test against another family's box), `stem_value.adjudicate_head_stem` (a rest's body joins as a stem).

### What this does not say
No fix built, no flag flipped. Counts of eighth rests and dots lost under the floor are from a 45-bars-a-plate hand sample; the 767 shared heads are an upper bound (about two thirds by a 32-crop look); the 75-whole look is mine. A fix for Q4 is the smallest of the four (an open-class head whose centre reads filled, or whose stem is decided, narrows instead of deciding, as `head_fill_from_ink` already does for a black head over a hollow reading) and would touch 29 of the 56 written wholes by the record's ink alone; the other 27 need a digit / rest-fragment witness. Proposed to Sean before dispatch, not built.


## 2.280 -- why read heads have no stem row (Sean 2026-11-08 overnight, after the 2.278 micro KILL; diagnosis only, no code in tools/)

STAGED GATHER (`line_detection.detect_stems`, `gather_cv_lines`) files the `Q.STEM` rows; STAGED ADJUDICATE (`stem_value.adjudicate_head_stem`) joins a head to a row (`geometry.stem_touches_head`, zero tolerance, with the 2.161 duration-side bridge in `rhythm`). LEGACY is not involved. Records: the 20261104-night slices (`library/_shared-records/lane-report-slices-20261104-night/`, the frozen 9 Litolff + 8 Brahms pages; no full record loaded, no other `tools.omr` process was touched: a 10 GB Litolff gather was running, so I used slices and re-adjudicated the slices, 6-13 GB). Probes `probe/2.280/` (`p1_population.py` .. `p16_tall.py`, `p9_tiles.py`); data `out/2.280/`; tiles `out/print/2.280/` (12 + key.json). Branch `lane-2.280-stem-diagnosis`.

### Cause and process lesson

**Cause.** "No stem row" (2.278: 27% of Brahms and 35% of Litolff beam-family narrowed heads) is three different things, and only one of them is a stem finder fault on a clean note. Of the 83 narrowed heads with no touching stem row on the frozen pages (Litolff 42, Brahms 41), by my look at every one (ours, not evidence; Sean's tiles are out): **30 (36%) are not notes** (Litolff 16 whole-rest blocks and 1 word letter; Brahms 13: 7 accidentals, 3 clef pieces, 1 word letter, 1 slur piece, 1 small bar); **51 (61%) are real heads whose stem is on the page and fused into a bigger piece of ink** (Litolff 23 in chord and beam clumps, against ledger lines or against a barline; Brahms 18 heads of a second whose stem stands on the partner head, and 10 single heads); 2 Litolff I cannot call. Those 51 are the real loss. The stem finder cuts a COMPONENT out of the page and judges its size and pairing; a stem that is fused to a head, a second, a ledger line, a barline or a chord tower is not a component of stem size, so it is refused as too WIDE or too TALL, or never offered. The ink holds the stem (50 of the 51 have a vertical run of 1.5 sp or more at the head's side); the cut-out step loses it.

**Process lessons.** (1) 2.275 and 2.278 counted a head as "a real narrowed note" from the duration verdict alone. On Litolff 16 of 132 narrowed heads (12%) are whole-rest blocks that the SAME record already decides as whole rests (`NOTEHEAD_IS_A_WHOLE_REST` decided True, `shape_and_position_agree`) and that 2.270 writes as rests (10 written as rests, 6 refused as rest ink, none as a note); the duration reader never consults that verdict, so two verdicts on one ink disagree and a census reads the unreconciled one: the "value computed and never read" class again, on a verdict this time. On Brahms 13 of 41 are accidentals and clef pieces boxed as heads and counted as lost notes. A headline number made of verdicts is not a count of notes (rule 7: 2.275's "12 of 12 real" was a look at the narrowed class, not at the no-stem part of it). (2) A cause named by the filter that fired ("too WIDE", "too TALL") names the finder, not the ink; the ink classes (rest block, accidental, second, chord tower, clump) are what a fix has to be keyed to. (3) Nobody owns the 8.0-space stem cap: the largest refusal today (below) is a number with no measurement behind it (2.169: "3.5-space figure NOT CONFIRMED").

### History from the tree (every stem effort, ON or OFF today, why it stopped)

| effort | what it did | today | why it stopped |
|---|---|---|---|
| omr-stem-pair-rule (09-17) | measured: `_drop_paired_strokes` deletes 244 strokes; 73 of 793 no-stem heads (9.2%) would stop abstaining | no code | bounded at 9.2%; premise false (62 of 80 deleted strokes were paired with another real stem) |
| omr-stem-ink (09-17) | measured: the missing stems are printed (95.8% / 93.1% have a run >= 1.75 sp); right-up/left-down agrees 95.9% / 98.2% | no code | measurement only |
| omr-stem-stroke (09-18) `OMR_STEM_STROKE` | column-profile reader inside fused blobs; reach 346 of 793 (43.6%) Litolff, 544 of 1,529 (35.6%) Brahms no-stem heads; re-finds 98% of the shipped stems | **OFF** | Litolff quality undetermined (82.6% vs a 96.1% bar, then withdrawn), beam risk unpriced; never tiled for Sean |
| omr-stem-attachment (09-18) | the attachment convention as a tier | refused, no code | marginal reach 371 / 483 |
| omr-stem-notehead-gate (09-20) `OMR_STEM_NOTEHEAD_GATE` | a stroke meeting a detected head is never pair-deleted; no-stem 793 -> 720, 1,529 -> 1,351 | **OFF** (`line_detection.stem_notehead_gate_enabled` returns OFF unless the env is set; no run script sets it). `gather.py` L5314 says "default ON since 2026-11-02": that comment came in with merge 65c1b3e7c2 and is wrong against the code | fixtures inverted (page total two errors cancelling), never put to Sean; superseded by 2.169 |
| omr-stem-run-split (09-20) | two stems as one run: confirmed, but 3 runs of 4,225 | no code | 0.23% of heads |
| 2.87 `OMR_STEM_FINDER` (10-10) | five repairs: thin_run, pair_evidence, attach_tolerance, refuse_owned, pair_head_end | **ON** (staged default) | landed |
| 2.155 `OMR_STEM_AT_BAR_EDGE` (10-16) | a run refused at the cell edge whose end stands in a head box is that head's stem | **ON** | landed (Sean's 40 tiles) |
| 2.161 `OMR_HEAD_STEM_BRIDGE` (10-17) | duration side only: a head with no touching row but ink running into a stem beside it takes that stem for the first step | **ON** | landed; it reads the stem in ink without filing a row, so the join and every later consumer still see "no stem" |
| 2.167 (10-16..18) | census: of 40 kept no-stem Litolff heads 39 have a run >= 1.5 sp; Sean's tiles: the 4 "paired" refusals are real stems | measured | opened 2.169 |
| 2.169 `OMR_STEM_PAIR_AT_HEAD` (10-18) | a stroke ending in a head's rows is never pair-deleted; 346 Litolff / 280 Brahms no-stem heads gain a stem | **ON** | landed (Sean tiles 5/5); the TALL clause was not built ("3.5 sp NOT CONFIRMED") |
| 2.170 (10-19) | beams, not stems: bare quarters decided | **ON** | landed |
| 2.179 `OMR_STEM_END_HEADS` (10-20) | the other direction: a stem with no head gets a head looked for | **ON** | landed |
| 2.204 `OMR_STEMS_FROM_STROKES` (10-25..28) | stems from the stroke map, claimed strokes first | **OFF**, parked by the stop rule | right->wrong 0, but notes not written +5% Litolff: the new stems brought their own `stem_readers_disagree` abstentions beside the old finder's (two readers voting per head) |
| 2.205 `OMR_STROKE_OWNER` (10-26) | one owner per page stroke; heads, accidentals, dynamics claim first | **ON** | ownership alone changes nothing in the file; its consumer (2.204) is OFF, so no stem reads "unclaimed strokes only" |
| 2.216 (10-28) | the ledger lines decide the owner where they clash with the stem | **ON** | landed; the stem is a second witness only |
| M6 / 2.260e (11-05) | heads and ledger lines read once on the page; `OMR_PAGE_HEADS`, `OMR_PAGE_HEAD_VIEWS`, `OMR_PAGE_HEAD_CLAIM` | merged **OFF** | export identical; the head claim costs one right->narrowed; nothing reads a stem from a claimed head yet |
| 2.278 micro (11-09) | beam group read once | **KILLED** | no stem row for 27% / 35% of its heads: this lane |

### Method and controls (rule 7)

Same shipped functions throughout: the 2.167 `p2_stems.py` method (re-cut the page as production cuts it, re-run `detect_lines` with the record's own boxes, collect every vertical run with the filter that refused it), same head-to-stem test as `adjudicate_head_stem`. Controls:
- **Cell control: the re-run's accepted stems equal the record's `Q.STEM` rows, box for box**: Litolff 233 of 235 cells, Brahms 145 of 147 (the 4 differing cells are counted, not dropped).
- **The 2.278 headline reproduces and splits**: on the m4b-sample slices the beam-family narrowed counts are exactly 2.278's (Litolff 182, Brahms 269); "no stem row" 63 / 73 = 40 / 46 heads with NO stem touching plus the rest with two or more distinct stems touching (37 / 37 touch; `adjudicate_head_stem` can narrow `two_stems`), so about a third of 2.278's "no stem row" is the dyad / two-stem case, not a missing stem.
- A control that can fail: the not-a-note heads (rests, accidentals). A reader that files a stem for them is wrong (below, the naive run test fails it 11 of 30).
- The export fates come from re-adjudicating the same slices on the current tree and running the shipped export with `_place_notes` instrumented (`p8_fates.py`; Litolff 2,100 / Brahms 3,100 `notes_not_written_total` on the sample pages).

### Counts

**Narrowed kept heads on the frozen pages, current tree** (`p15_narrowed_rest.py`): Litolff 132: 16 whole-rest blocks (already rests), 26 no stem row (20%), 88 stem row, 2 no pitch. Brahms 163: 122 stem row, 41 no stem row (25%) (1 of them a refused whole-rest block). So the no-stem share of narrowed notes is about 20% Litolff and 25% Brahms once rests are taken out and 2-stem heads are not counted as stemless; 2.278's 35% / 27% included the rests and the two-stem heads.

**The 83 narrowed no-stem heads, first cause of the finder against what the ink is** (my look at all 83; `p3_buckets.py` x `p6_labels.py`):

| plate | what the ink is (my look) | n | finder's first cause |
|---|---|--:|---|
| Litolff 42 | whole-rest block kept as a head (R) | 16 | no vertical ink 15, never a candidate 1 |
| | real head, stem fused into a clump / ledger lines / barline (H) | 23 | WIDE 9, contact fails 9, never a candidate 2, EDGE 1, TALL 1, no ink 1 |
| | word letter / unclear | 1 / 2 | |
| Brahms 41 | accidental, clef piece, word letter, slur piece boxed as a head (N) | 13 | contact fails 6, no ink 4, never 1, PAIRED 1, TALL 1 |
| | head of a second, stem on its partner (D) | 18 | WIDE 15, never 2, contact fails 1 |
| | single head, stem fused or near (S) | 10 | TALL 4, contact fails 4, WIDE 1, never 1 |

**Like-for-like with 2.167** (kept heads, no touching stem row, minus copies owned by another staff, refused non-notes and whole-rest ink, as 2.167 excluded; `p12_likeforlike.py`): Litolff 185 heads (9 pages) now against 2.167's 40 seeded of 760 (10-16); Brahms 140 now (2.167 Part 1 was Litolff only).

| first cause | Litolff 10-16 (40) | Litolff now (185) | Brahms now (140) |
|---|--:|--:|--:|
| PAIRED with a neighbour | 14 (35%) | **0** | 5 (3.6%) |
| too WIDE | 7 (17.5%) | 32 (17.3%) | 33 (23.6%) |
| too TALL | 5 (12.5%) | **60 (32.4%)** | 37 (26.4%) |
| too SHORT | 4 (10%) | 10 (5.4%) | 8 (5.7%) |
| cell EDGE | 2 (5%) | 16 (8.6%) | 2 (1.4%) |
| never a candidate | 1 (2.5%) | 14 (7.6%) | 28 (20.0%) |
| stem found, contact fails | 6 (15%) | 48 (25.9%) | 22 (15.7%) |
| no vertical ink | 1 (2.5%) | 5 (2.7%) | 4 (2.9%) + 1 |

What shrank: **PAIRED, 35% to 0 on Litolff** (2.169 ON, as built). What stayed: WIDE (17.5% to 17.3%), EDGE, no ink. What now leads: **TALL (32% / 26%)**, which was 12.5% and is the largest refusal on both plates because nothing owns it. The refused TALL runs are 8.0-12.0 sp, median **8.4 sp**, quartiles 8.1 / 8.2 / 8.4 / 9.2 / 10.9 (Litolff) and 8.1 / 8.2 / 8.4 / 9.5 / 9.9 (Brahms): they are chord towers (a stem through 3-5 stacked heads, my look at 12 Litolff ones) just over `STEM_MAX_HEIGHT_LINES = 8.0` (line_detection.py L170). The 60 / 37 are mostly heads whose duration is DECIDED (the 193 / 106 "decided with no stem row" heads: black 1.0 for 131 of Litolff's 193, 46 + 32 (dotted) of Brahms's 106), so what they cost is not a narrowed note but a stem tip nobody read: whether a flag or beam was there stays unlooked (a quarter is the default, never shortened without evidence, CLAUDE section 4). Absolute counts do not compare: 2.167 counted the whole movement (760 kept no-stem Litolff heads), this is 9 of its pages.

### Crops (rule 7: the biggest bucket before it counts)

Contact sheets (my look, ours): every one of the 83 narrowed heads; 12 of the Litolff TALL refusals. Findings: of Litolff's 16 "no vertical ink" heads 15 are whole-rest blocks (a half-oval hanging from a line; 5 of the 16 rests overlap a `restWhole` box scored 0.34-0.60; none has any vertical ink: there is no stem to find). Litolff WIDE: heads in beam clumps and heads on ledger lines whose stem runs through the ledger lines (a "WIDE" run of stem plus ledger ink); contact-fails: a stem beside a clump head by up to 0.5 sp. **Brahms WIDE 15 of 16 are the displaced head of a second: both heads fused into one blob with the stem standing on the partner; the stem is plainly visible below or above.** Brahms contact-fails: 6 are accidentals boxed as heads (sharps and naturals read as a black head) and 4 are single heads with the stem 0.1-0.5 sp away. Not looked at: whether the 193 / 106 decided heads hide flags.

### Do the page strokes already hold it? ("value computed, never read")

Per head, any `Q.PAGE_STROKE` whose box touches the head's x-range (0.5 sp) and y-range and reaches 1 sp beyond it; `Q.HEAD_STEM_REACH` (the 2.58d ruler `gather.measure_head_stem`, filed ONLY for contested heads and second-only heads, read by `ownership` and by `rhythm._second_only_evidence`, never by the head-to-stem join) up or down extent >= 1.5 sp:

| the 51 real heads | page VERTICAL stroke at the head | page BLOB / barline stroke at the head | none | `head_stem_reach` >= 1.5 sp |
|---|--:|--:|--:|--:|
| Litolff H 23 | 3 | 2 / 10 | 8 | 4 |
| Brahms D 18 | 3 | 1 / 0 | 14 | 2 |
| Brahms S 10 | 6 | 1 / 0 | 3 | 6 |

So the page strokes hold a stem-shaped stroke at 16 of 51 real heads (31%) and the filed ruler row at 12 (24%; only 14 of the 51 even have a ruler row, 37 have none, because the ruler is run for contested heads only): a small part, and none for the Brahms seconds (the stem and the second head are ONE blob on the page too, so the page map fails where the cell finder fails). Ten of the 23 Litolff heads stand against a page barline stroke (the stem ink merged with the barline column; 2.155 handles a run at the CELL edge only). This agrees with 2.204's parking: moving the same component filter to page strokes does not reach the fused stems.

### What would reach them: the head-anchored ruler that is already in the tree

Two tests on the 83, both mine (ours) and both on the head's own ink:
- **A crude run test** (`p11_headrun.py`): is there a vertical ink run of 1.5 sp or more in the band at either side of the head? Real heads: **50 of 51**. Not-a-note heads, the control that can fail: whole-rest blocks 1 of 16, accidentals and clef pieces **10 of 14**, so 11 of 30 not-notes get a "stem": the naive test FAILS its control, as it should.
- **The shipped ruler** (`p18_ruler_all.py`: `gather.measure_head_stem`, ROADMAP 2.58d, run unchanged on the page raster for each of the 83). It is already a head-anchored read: a 0.18-sp column slid at the head's engraving edge (down -> left, up -> right), a run of 0.8 sp or more past the head, up to 9 sp, answers `up` / `down` / `both` (through-ink: a barline or a through-stem, "claims nothing") / `none`.

| my label | up or down | both (through-ink) | none |
|---|--:|--:|--:|
| Litolff real heads 23 | 12 | 6 | 5 |
| Brahms second heads 18 | 8 | 9 | 1 |
| Brahms single heads 10 | 9 | 1 | 0 |
| **real heads 51** | **29 (57%)** | 16 (31%) | 6 (12%) |
| rest blocks 16 (Litolff) | 0 | 0 | 16 |
| accidentals, clef pieces, word, slur piece 14 | **8** | 2 | 4 |

So the ruler that 2.58d wrote for contested heads already answers a stem direction for 29 of the 51 real heads that have no row (57%), says nothing for all 16 rest blocks (a real control that held), and is fooled by 8 of the 14 accidental / clef-piece heads (the control that fails: it reads the original raster, blind to what an accidental has already claimed). Its `both` answer is where the Brahms seconds land (9 of 18): the stem passes the head on both sides because the head sits against its pair's stem. It is NOT used for these heads: `gather_head_stem_reach` files it only for contested and second-only heads (14 of the 51 have a row), and the join (`adjudicate_head_stem`) reads `Q.STEM` rows only. That is the "value computed, never read" bucket, in a different shape from the page-stroke one: the tree has a head-anchored stem read, measured and tested in 2.58d, and the join cannot use it.

### The one change at the source

**The stem is read from the head, not the head from the stem.** For a kept head that has no `Q.STEM` row after the finder, ask the head's own ink at its engraving edge (the 2.58d ruler, which is that question), on UNCLAIMED ink, and file the answer as an ordinary `Q.STEM` row (the same row the finder files; new reader name `cv_head_stem_ruler`) that the existing join, direction, tip and chord readers then read as they read any stem. Two things the shipped ruler lacks, both with an owner in the tree: (a) it must read the page ink MINUS the ink the page has already claimed (accidental, key, clef, bracket, barline, ledger rung, 2.277 "claimed ink is final"), which is what fences the 8 accidentals it is fooled by; (b) a `both` answer is a chord stem, not a barline, when the run ends in another kept head's box (the stem always ends at a head, 2.179) and a barline when it ends in none; that decides the Brahms seconds. The shipped finder keeps every row it has; the new reader fills only where there is none and abstains (no row, counted) wherever the ruler says `none`, or `both` with no head at an end, or the two sides disagree. It is a CONNECTION of a decision the tree already makes (rule 6), not a new guess. It adds no flag to the product until the micro test passes (rule 9: a roadmap item first).

**Rules that own each value it would touch** (checked, not assumed): stem presence and side: CLAUDE section 5 "Stems: up -> right, down -> left; every note on one stem shares one written value", `conventions.py` C9 + L10 (96 of 96 against print). Which staff owns the head: the ledger lines decide (page-facts; 2.216 `OMR_OWNER_LEDGER_WINS`); the new row must not be offered to `glyph_owner` as a stem witness against the ledger lines. Duration: CLAUDE section 4 "a note is an eighth only on evidence: a flag or beam read on its stem; bar arithmetic never supplies one": the row only makes the tip readable; every value stays with the existing beam and flag readers (2.202, 2.170, 2.146). Direction: `Q.STEM_DIRECTION` from the side convention. Pitch and far-head position are not touched (a far head is placed by its ledger lines only, 2.248).

**How it composes with read once / claim once (2.277).** It runs after the claims it must respect and reads only what they leave, so the accidental that the shipped ruler mistook for a stem is already someone's ink; it claims the ink it reads as a stem (owner family `stem`, the 2.205 stroke owner already has the slot), so no later reader can take the stem for a beam or a slur; and it never overturns a decided row. It is not 2.204 (which gave every head a SECOND stem opinion from the stroke map that disagreed with the finder's, and failed on its own abstentions): here a head has one opinion where it had none. It does not need the page-wide beam pass (M4) or the page head list (M6) to exist, but it is the natural next step after M6c, which claims the head first.

**What it does not do:** the 30 not-notes. The 16 Litolff whole-rest blocks need the duration reader to read the whole-rest verdict the record already holds (they cost nothing in the file today: 10 written as rests, 6 refused as rest ink); the 7 Brahms accidentals, 3 clef pieces and 3 other marks boxed as heads are a claim question (2.277). Neither is a stem fix and neither is counted as one. And it does not touch the 299 decided no-stem heads' TALL refusals directly; those heads gain a row too (the ruler's 9-sp run is longer than the finder's 8.0 cap) and the beam / flag readers then look at their tips, which is where a hidden eighth would show.

### Micro test (pre-registered here, before any code; offline GATHER-side prototype in `probe/`, nothing in `tools/`, no flag, export untouched)

Population: the 83 narrowed no-stem heads, the 299 decided no-stem heads (193 + 106), and 200 seeded heads that already have a shipped stem row (100 a plate, same 17 pages). Arms: (A) the shipped ruler as it stands (the numbers above: reach 29 of 51, false 8 of 14 accidentals); (B) the ruler on unclaimed ink with the chord-through rule.
1. **Reach (must pass):** arm B files a stem for at least 85% of the 51 real heads (arm A: 57%); baseline 0 by construction. Sean's tiles confirm the sample.
2. **False stems (must pass):** at most 1 of the 30 not-a-note heads (arm A: 8 of 30; the control can fail, and it does).
3. **Agreement (must pass):** on the 200 heads that already have a stem, the same stem (box IoU >= 0.5) and the same direction in at least 98%; every disagreement is looked at on a crop, never settled by our own reading.
4. **Side control (must fail when broken):** arm B with the engraving side flipped (up -> left): reach must drop by at least 30 points, or the convention is not doing the work.
5. **Sean's tiles** (the 12 in `out/print/2.280/`: "Does the boxed note have a stem, and which way does it go?"): arm B's answer matches his on at least 9 of the 10 test tiles and 2 of 2 controls.
6. **Judged:** Sean's judged answers right -> wrong = 0 (`python3 -m tools.omr.staged.judged score`).
**Kill:** 2, 3 or 6 fails, or reach under 60%. The whole movement is the overnight's job; this measures 17 frozen pages.

### Tiles for Sean

`out/print/2.280/` (12 tiles + key.json + README): one staff, one thin blue box (the head plus 4 staff spaces above and below), nothing else drawn; "Does the boxed note have a stem, and which way does it go?" Ten test heads (Litolff: 2 whole-rest blocks, 3 clump heads; Brahms: 3 heads of a second, 1 single, 1 accidental boxed as a head; the picks are seeded, see key.json) and 2 controls (a clear stemmed black head, Litolff; a clear stemmed half note, Brahms). The 17 frozen pages hold no whole note (32 whole-class boxes looked at are 6/8, 9/8 digit loops, halves and rests), so there is no whole-note control; the two rest tiles and the accidental tile are the "no stem possible" controls. Bucket, my label and the record's reading are in key.json only. Sean's answers: none yet.

### What this does not say

My labels are mine (ours): the 83 and the 20 TALL looks are not Sean's; his tiles check a 12-head sample. The sample is 17 frozen pages, not the movement. "Real head" means a head on the print, not a head the file should keep. The 193 / 106 decided no-stem heads were not looked at for flags. The `two_stems` narrowing was inferred from the m4b-sample split (40 + about 23 of 63), not replayed. Nothing was built: the 57% is the shipped ruler as it stands, and nothing says its direction is right (that is what the tiles and bar 5 are for). The shipped ruler was run on the page raster for the 83 only, not on the decided heads.
