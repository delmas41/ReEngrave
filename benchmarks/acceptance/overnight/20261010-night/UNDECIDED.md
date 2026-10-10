# Which bars went undecided overnight, and what made them so

Lane `lane-overnight-undecided`, 2026-10-10. Sean asked: *"Is there a way to show me which measures went undecided and to show me a few systems side by side."* An investigation, not a code change: nothing under `tools/` was touched.

Compared: **last night** `20261009-all` (main `00473387`) and **tonight** `20261010-night` (main `26fdb4d0`), both through INFER, both gathered from a clean tree (`dirty: false` in both records' provenance). STAGED path throughout. "Undecided" means ADJUDICATE's duration verdict for a notehead is NARROWED (a set of candidates) where it was DECIDED (one value) the night before: `kept -> narrowed` in `readout diff`'s words.

## 1. The answer

- **Brahms: 1,991 notes went kept -> narrowed, 344 went narrowed -> kept. Litolff: 388 and 89.** Notes that are narrowed at ADJUDICATE: Brahms 2,190 -> 3,860 of 24,260 gathered (9.0% -> 15.9%); Litolff 507 -> 793 of 11,399.
- **99% of them carry one reason word, `beam discounted uncertain`** (Brahms 1,976 of 1,991; Litolff 329 of 388). The word is not new: `git log -S` puts every reason word between 2026-09-07 and 2026-09-30. What is new is what feeds it.
- **It is mostly one item: 2.74.** Its ink test now refuses a stroke over a head as "not a beam" (`too_thin`: thinner than 1.75 staff lines), and the rule-8 guard added with it narrows the head between "no beam" and "one beam" instead of deciding it. **1,802 of the 1,991 Brahms notes (90.5%) carry a stroke 2.74 newly refused; 1,639 (82.3%) carry nothing else.** 2.77b (a stem side read by the ruler where no stem was attached) is the other input on 306 (15.4%), 162 of them alone. 2.77's two ink refusals (`through_heads`, `no_stem_at_ends`) are on 43 (2.2%). Four notes (0.2%) show no changed guard input: two are `head fill from ink` notes whose head is read open tonight (the hollow-head items), two are unexplained. On Litolff the split is 2.74 alone 226 (58%), 2.77/2.77b ink alone 52 (13%), 2.77b alone 36 (9%), combinations 43, none 31 (8%; 10 of them `head fill from ink` with the head read open tonight, 21 unexplained).
- **None of the other landed items appears on these notes** (2.75 tie/slur, 2.78, 2.61d, 2.12f, 0.9, 2.68, 2.71, 2.72, 2.76): no counter of theirs differs. 2.69 (hooks), 2.70 (hollow head, bare stem) and, on 4 notes, the 2.75 arc change show up only on the way back, narrowed -> kept. The one exception on the way in is the 7 + 19 `head fill from ink` notes, where `head_is_open` flips from black to open: the hollow-head family (2.70 / 2.73), not separated further.
- **What the print shows (for Sean to judge, not a verdict):** the three Brahms systems with the most such notes, and 20 notes drawn at random, are heads with a stem, often a dot, and **no beam that I can see**; hairpin wedges and slur arcs lie beside them. Last night 1,847 of the 1,991 had been *decided* with one or more beam levels over the head (1 level 1,191; 2 levels 394; 3: 164; 4: 63; 5 or more: 35; none: 144), i.e. eighths, 16ths, 32nds, 64ths; the only strokes I can see in the crops that could have counted are the wedges and arcs. Tonight each of them is capped at `no beam | one beam`: `dotted 8th | dotted quarter` or `8th | quarter`. 1,333 of the 1,991 (67%) still have last night's answer among tonight's candidates; for 658 (33%), essentially the 656 read with 2 or more levels, last night's answer is ruled out.
- **A finding the brief did not expect:** the exporter's bar numbers are **not** the printed ones. At every system I checked on the print the export is **3 higher on Brahms from p13 on** (251 printed, 254 exported) and **1 to 2 higher on Litolff** (452 printed, 454 exported). The CSVs give both. See section 2.

## 2. Which bars went undecided

Files (`benchmarks/acceptance/overnight/20261010-night/undecided/`):

| file | what |
|---|---|
| `undecided-bars-brahms1-breitkopf.csv`, `undecided-bars-beethoven5-litolff.csv` | one row per bar with at least one kept -> narrowed note, sorted by count (Brahms 375 rows, Litolff 183) |
| `undecided-bars-*.txt` | the same as a short text: transitions, distribution, top 10 bars, top systems |
| `changed-notes-*.csv` | one row per note that changed (Brahms 2,335, Litolff 477): subject, page/system/staff/cell, export bar, last night's value, tonight's candidates, reason, the guard input that differs |

A bar is keyed on **(page, system, cell)** (CLAUDE.md §10: a cell index restarts per system). Columns: `page, system, cell, bar_in_system, bars_in_system, export_bar, printed_bar_confirmed, printed_bar_by_eye, system_start_margin_reading, system_start_state, kept_to_narrowed, narrowed_to_kept, staves_with_new_undecided, staves, reasons, notes_in_bar_tonight_kept / narrowed / other`. The page number is the PDF page index (the same as the record's).

Brahms: **375 of 514 bars** (73%) hold at least one newly undecided note; Litolff **183 of 505** (36%). Brahms bars by number of newly undecided notes: 1 note 66 bars, 2: 58, 3: 37, 4: 38, 5: 36, ... up to 30 in one bar.

### How the bars are numbered, and what to trust

- `export_bar` is the exporter's own measure number: `offset(page/system) + cell + 1`, the `document` scheme in `coverage.json` `measure_numbering`. The formula is **checked against every held-out bar the exporter itself listed** (`bars_held_out_sum.held[].measure`): 0 mismatches on 2,755 Brahms and 1,009 Litolff bars, and `lud_bars.py` exits 3 on the first mismatch. So `export_bar` is the bar number *in the MusicXML/LilyPond files*.
- **It is not the printed number.** `lud_printed_numbers.py` crops the number printed at the start of each system (`out/print/overnight-20261010-undecided/printed_bar_numbers.png`). Read by eye, for the systems in the top-10 lists:

  | Brahms system | p3 s0 | p13 s1 | p14 s1 | p16 s0 | p16 s1 | p18 s0 | p18 s1 | p22 s0 | p23 s1 | p25 s0 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | printed first bar | 38 | 251 | 273 | 303 | 315 | 336 | 343 | 409 | 444 | 472 |
  | export first bar | 38 | 254 | 276 | 306 | 318 | 339 | 346 | 412 | 447 | 475 |

  | Litolff system | p3 s0 | p7 s0 | p10 s0 | p10 s1 | p12 s0 | p13 s0 | p15 s1 | p16 s0 | p16 s1 |
  |---|---|---|---|---|---|---|---|---|---|
  | printed first bar | 49 | 171 | 274 | 288 | 338 | 366 | 452 | 472 | 489 |
  | export first bar | 49 | 172 | 275 | 289 | 339 | 367 | 454 | 474 | 491 |

  So the export is right at p3 on both and over-counts by 3 on Brahms by p13 (the 3 are added somewhere between p3 and p13), and by 1 then 2 on Litolff (one between p3 and p7, one between p13 and p15). The record's own margin-number reader agreed at 7 of 35 Brahms systems and 8 of 28 Litolff systems and abstained or misread at the rest (`printed_bar_check` in `coverage.json`); its "disagree" deltas on Litolff (-1, -2) match what I read, on Brahms many readings are misreads (`8`, `9`, `10`), so I did not use them.
- `printed_bar_by_eye` = the printed number at the system's start + the cell index, filled **only for the systems in the table above**; it assumes the exporter's cell count in that system is the printed bar count (not checked). `printed_bar_confirmed` is filled only where the margin reader agreed with the export. Everywhere else the printed number is left empty: not guessed.
- The cause of the export's over-count (a bar split in two, or counted twice, upstream) is not investigated here.

### Top 10 bars per movement

Brahms (`p/s` = page / system; "bar x/y" = bar in system; notes are newly undecided; printed number by eye except where marked):

| # | where | export bar | printed bar | notes | staves |
|---|---|---|---|---|---|
| 1 | p13 s1, bar 10/12 | 263 | 260 | 30 | 10 (0 1 2 3 4 9 10 11 12 13) |
| 2 | p18 s1, bar 6/8 | 351 | 348 | 24 | 7 |
| 3 | p13 s1, bar 9/12 | 262 | 259 | 23 | 8 |
| 4 | p3 s0, bar 10/10 | 47 | 47 (margin reader agrees) | 22 | 6 |
| 5 | p25 s0, bar 2/10 | 476 | 473 | 22 | 9 |
| 6 | p13 s1, bar 4/12 | 257 | 254 | 20 | 9 |
| 7 | p16 s1, bar 5/9 | 322 | 319 | 19 | 11 |
| 8 | p23 s1, bar 9/10 | 455 | 452 | 19 | 5 |
| 9 | p14 s1, bar 6/9 | 281 | 278 | 18 | 5 |
| 10 | p18 s0, bar 3/7 | 341 | 338 | 18 | 6 |

Top systems by newly undecided notes: p13 s1 159 (11 bars, 13 staves), p22 s0 83, p16 s0 76, p14 s1 72, p8 s0 63, p0 s0 61, p21 s1 61, p15 s1 60.

Litolff:

| # | where | export bar | printed bar | notes | staves |
|---|---|---|---|---|---|
| 1 | p15 s1, bar 3/20 | 456 | 454 | 12 | 4 (0 1 3 4) |
| 2 | p15 s1, bar 4/20 | 457 | 455 | 12 | 4 |
| 3 | p10 s1, bar 8/15 | 296 | 295 | 10 | 3 |
| 4 | p7 s0, bar 16/17 | 187 | 186 | 9 | 4 |
| 5 | p16 s0, bar 1/17 | 474 | 472 | 9 | 4 |
| 6 | p3 s0, bar 4/16 | 52 | 52 (margin reader agrees) | 7 | 1 |
| 7 | p10 s0, bar 5/14 | 279 | 278 | 6 | 1 |
| 8 | p16 s1, bar 8/15 | 498 | 496 | 6 | 1 |
| 9 | p12 s0, bar 3/15 | 341 | 340 | 5 | 3 |
| 10 | p13 s0, bar 4/16 | 370 | 369 | 5 | 1 |

Top systems: p15 s1 44, p14 s1 27, p7 s0 24, p16 s0 23, p12 s0 20, p10 s1 18, p13 s0 18, p5 s0 17.

## 3. What made them undecided

All of this is read off the two records. Each changed note has an ADJUDICATE duration verdict on both nights; the verdict carries the counters the decision branched on. `lud_extract.py` pulls them for the 2,335 / 477 changed notes of each movement, `lud_attrib.py` pairs last night's with tonight's.

### 3.1 The reason words (tonight's), kept -> narrowed

| reason | Brahms | Litolff | introduced (`git log -S`) |
|---|---|---|---|
| beam discounted uncertain | 1,976 | 329 | `a8538665` 2.25b (2026-09-29), `9b7798d9` 2.43 |
| head fill from ink | 7 | 19 | `076102a4` 2.23 (09-29) |
| beam certain not joined | 4 | 3 | `71426afe` 2.38b (09-29) |
| beams ambiguous | 3 | 36 | `d9904e5a` (09-07) |
| flags disagree | 1 | 0 | `573bebfc` 2.18b (09-29) |
| flag ink unread | 0 | 1 | `25d8ce9f` 2.18c (09-29) |

No reason word dates from 10-09. The attribution therefore goes through **what newly feeds** `beam discounted uncertain`. In `rhythm.py` it fires when `(discount_removed_all_marks and (own_stems or reach_stem)) or ink_removed_all_marks or far_removed_all_marks`, the head is not hollow, no flag reads, and nothing is left over the head. At `00473387` the code held **only the first branch, and only with `own_stems`**: `_not_a_beam_by_ink` and `Q.BEAM_STROKE_INK` have 0 occurrences in that commit's `rhythm.py`.

### 3.2 Guard input -> item

| what differs on the note (from the verdict's counters, last night -> tonight) | code path | introduced by | item |
|---|---|---|---|
| `beams_not_by_ink` 0 -> n, reason `too_thin` / `not_straight` / `one_stem` | `ink_removed_all_marks` | `56fa83ab` 10-09 11:38 (the ink reader and its three tests); `4fc81f65` 12:02 (thickness measured locally); `0f880dde` 12:20 (the rule-8 guard: a refusal that leaves a marked head unmarked narrows) | **2.74** |
| `beams_not_by_ink` 0 -> n, reason `through_heads` | same | `34972ddc` 10-09 14:31 "Rhythm leftovers: ... a stroke through the heads is not a beam" | **2.77** (the code comment calls it 2.75) |
| `beams_not_by_ink` 0 -> n, reason `no_stem_at_ends` | same | `0d08e10c` 10-09 16:05 (Rhythm leftovers review); refined `3a5b5af4` | **2.77** / 2.77b |
| `beam_side` None -> up/down, with neighbour/arc/far-side strokes dropped and `stems_attached = 0` | `reach_stem`, `far_removed_all_marks` | `3a5b5af4` 10-09 23:43 "2.77b: a head's beams are the ones its own stem reaches (ruler direction at >= 2.0 spaces, rule 8 where nothing of its own is read)" | **2.77b** |
| narrowed -> kept, `hooks_counted` | | `6c14783e` 10-09 09:28 | **2.69** |
| narrowed -> kept, `hollow_head_bare_stem` | | `a116c4ee` 10-09 10:18 | **2.70** |

The threshold is `BEAM_THICKNESS_RATIO_MIN = 1.75` staff-line thicknesses (median stroke thickness). `lud_side_check.py`: the 162 Brahms notes whose only differing input is the stem side all have `stems_attached = 0`, and each had a neighbour-staff, decided-arc or far-side stroke dropped: last night the head had no CV stem so the first branch could not fire; tonight the ruler gives it a side and it does.

### 3.3 The partition (every kept -> narrowed note once; `partition.txt`, `rollup.txt`)

| item whose guard input differs | Brahms (of 1,991) | Litolff (of 388) |
|---|---|---|
| 2.74 only | 1,639 (82.3%) | 226 (58.2%) |
| 2.77b only | 162 (8.1%) | 36 (9.3%) |
| 2.74 + 2.77b | 143 (7.2%) | 28 (7.2%) |
| 2.77 only | 22 (1.1%) | 52 (13.4%) |
| 2.74 + 2.77 | 20 (1.0%) | 13 (3.4%) |
| 2.77 + 2.77b | 1 | 2 |
| none differs | 4 (0.2%) | 31 (8.0%) |

Strokes the ink refused, by the ink's reason, Brahms (notes): `too_thin` 1,692, `not_straight` 35, `one_stem/too_thin` 26, `one_stem` 21, `no_stem_at_ends` (alone or with `too_thin`) 28, `through_heads` (alone or with `too_thin`) 15, `not_straight/too_thin` 8.

The "none differs" notes (Brahms 4, Litolff 31): the reason `head fill from ink` goes with `head_is_open` flipping False -> True on **every one** of the 7 Brahms and 19 Litolff notes that carry that reason (counter read for all of them), so those belong to the hollow-head family (2.70 `a116c4ee`, 2.73 `18ba2671`); 2 Brahms and 10 Litolff of the "none differs" are of that kind. What is left unexplained: **2 Brahms, 21 Litolff** (18 `beams ambiguous`, 2 `beam certain not joined`, 1 `beam discounted uncertain`; none carries a GATHER change line either, `unattributed.txt`).

**This is attribution by the inputs the decision itself recorded, not an A/B.** An A/B needs a re-gather per item (2.74 changes GATHER, so `readjudicate` is blind to it, CLAUDE.md §6b). It says which guard fired; it does not say the guard is wrong.

### 3.4 Last night's answer against tonight's candidates

Brahms: 1,333 notes (67%) keep last night's value among tonight's candidates; 658 (33%) do not. Last night's beam levels over the 1,991 notes: 0 levels 144, 1 level 1,191, 2 levels 394, 3 levels 164, 4 levels 63, 5 or more 35. The 658 are almost exactly the 656 with 2 or more levels: tonight's candidates are always `no beam | one beam` (`0.75 | 1.5` for a dotted note, `0.5 | 1` for a plain one). Commonest transitions (beats, last night -> tonight): 0.75 -> `0.75 | 1.5` 619, 0.5 -> `0.5 | 1` 567, 0.375 -> `0.75 | 1.5` 223, 0.25 -> `0.5 | 1` 170, 0.1875 -> `0.75 | 1.5` 107 (`attribution-*.txt` has the full table). Litolff: 329 keep it, 59 do not (last night's levels: 0: 42, 1: 293, 2: 29, 3: 16, 4: 8).

### 3.5 Narrowed -> kept (344 Brahms, 89 Litolff)

| how it was decided tonight | Brahms | Litolff |
|---|---|---|
| `head_and_marks` after a disputed stroke was refused by the ink (last night `beam certain not joined` 217, `beams ambiguous` 20): **2.74** (237 incl. 9 with another item's input too) | 237 (69%) | 6 |
| `hooks_counted` (last night `flag ink unread` / `flags disagree`): **2.69** | 85 (25%) | 21 (24%) |
| `head_and_marks` after `through_heads` / `no_stem_at_ends` (last night `beams ambiguous`): **2.77** | 10 | 43 |
| `hollow_head_bare_stem`: **2.70** | 4 | 10 |
| `head_and_marks` after the arc decision changed (decided-arc strokes 1 -> 0): the 2.75 family | 4 | 0 |
| other (2.77b side only 4 / 1; none differs 0 / 8) | 4 | 9 |

So **2.74 both narrows 1,802 and resolves 237 Brahms notes**: where a certain stroke was disputed (`beam certain not joined`), refusing it as `too_thin` decided the note. 2.77 does the same on Litolff: 43 resolved against 67 narrowed.

### 3.6 Is the cut near the real beams?

`thickness-*.txt`: histogram of all `Q.BEAM_STROKE_INK` rows. Brahms 13,583 strokes: a mode at 1.0-1.5 staff-line thicknesses (8,267, about the width of a staff line), a second mode at 2.5-4.0 (2,646, beams), and a valley at 1.75-2.5 (618). 10,205 (75%) fall under the cut; 1,672 sit in 1.5-1.75, the shoulder of the thin mode. Litolff 3,985 strokes: modes at 1.0-1.25 (1,273) and 2.0-2.5 (1,113), valley 1.75-2.0 (99), 48% under the cut. On both plates the cut lies in the valley, not on a mode. That says the refusals are not borderline in bulk; it does not say each one is right.

## 4. The pictures

`out/print/overnight-20261010-undecided/` (committed; `.gitignore` does not exclude `out/`). 600 dpi page pixels from `preprocessing.render_page`, the deskewed raster GATHER read. LEFT = last night, RIGHT = tonight. **Blue** box = a note DECIDED last night, its value written; **orange** = the same note UNDECIDED tonight, the values it may be written (`8th|qtr` = eighth or quarter); **green** = the opposite change (narrowed -> kept, both panels). Grey numbers = export bar numbers; `stN` = staff index. The legend, page, system and bars are on each image. The boxes are tonight's GATHER boxes (`bbox_page_px`).

| file | shows |
|---|---|
| `system_01.png` (10441 x 3813) | Brahms p13 s1, export bars 254-265 (printed 251-262), **159** newly undecided notes + 1 the other way; 13 staves, flute to double bass |
| `system_01_zoom.png` | the same, export bar 263, staves 0-3, 16 notes, at 2x |
| `system_02.png` (10459 x 3783) | Brahms p22 s0, export bars 412-423 (printed 409-420), **83** notes |
| `system_02_zoom.png` | export bar 416, staves 0-3, 9 notes |
| `system_03.png` (10417 x 3711) | Brahms p16 s0, export bars 306-317 (printed 303-314), **76** notes |
| `system_03_zoom.png` | export bar 313, staves 1-4, 8 notes |
| `system_04.png` (9727 x 3673) | **Litolff** p15 s1, export bars 454-473 (printed 452-471), **44** notes; drawn at 2x for legibility |
| `system_04_zoom.png` | export bar 456, staves 0-3, 10 notes |
| `sample_random_brahms.png`, `sample_random_litolff.png` | **20 / 10 notes drawn at random** (seed 20261010) from all the kept -> narrowed notes, one tile each, the subject boxed: the check on the three systems having been picked for having the MOST such notes |
| `printed_bar_numbers.png` | the printed number at the start of the three Brahms systems and the Litolff one, next to the export's |
| `control_clef_*.png`, `frame_control_*.txt` | the frame control (below) |

What I see (a reading, not a measurement; Sean is the umpire): in all three Brahms systems the noteheads carry stems and often dots but **no beam**; a decrescendo or crescendo wedge sits between the staves (system 1, 2) and a "cresc." with slurs in system 3. Last night's labels on them are 16th, 32nd, 64th, dotted 16th. In the 20 random Brahms tiles I see no beam on the boxed head in any (18 of the 20 had a stroke the ink refused, 17 `too_thin` and 1 `one_stem`; the other 2 are the side-only and no-stroke kind); 8 of the 20 had a value with 2 or more beam levels last night (16th ... dotted 64th), 10 had one level (an eighth or dotted eighth) and 2 none (a quarter); for 12 of the 20 last night's value is still among tonight's candidates. Whether the right answer is dotted quarter, quarter or eighth is the print's to say; I do not read it from these crops. Litolff is murkier: the plate is blobby, heads fuse with staff lines, and in the 10 random tiles at least one (p13 s0 st3, last night 64th, tonight `8th|16th`) shows a real beam over two heads. I would not call the Litolff change right or wrong from these crops.

### Frame control (do the boxes sit on the print?)

Checked per page, each with a version that must fail (`lud_frame_control.py`, `frame_control_*.txt`):

| page | staff-line contrast on the lines | with every line moved half a space | clef boxes: ink inside vs moved 1.5 widths right | drawn note boxes: ink inside vs moved |
|---|---|---|---|---|
| Brahms p13 | +0.679 | -0.527 | 0.48 vs 0.16, true > moved on 47/47 | 0.85 vs 0.19, 160/160 |
| Brahms p22 | +0.886 | -0.710 | 0.57 vs 0.30, 29/30 | 0.85 vs 0.19, 83/83 |
| Brahms p16 | +0.733 | -0.576 | 0.50 vs 0.17, 60/60 | 0.86 vs 0.24, 75/76 |
| Litolff p15 | +0.420 | -0.295 | 0.53 vs 0.28, 25/25 | 0.85 vs 0.51, 44/44 |

The control crop (`control_clef_brahms_p13_s1.png`, one per system) draws a box we know, the leftmost clef of the system (`clefF` `glyph/13/1/12/0/0`), in green on the ink, and the same box moved right in red off it. **The frame lines up; the deskew and DPI are right.** The two nights' GATHER boxes are the same: 24,260 of 24,260 Brahms and 11,399 of 11,399 Litolff note pairs have the same subject on both sides, minimum IoU 1.000 (`lud_frame_control.py` prints it). Tonight's boxes therefore serve both panels.

## 5. How this was read, and one deviation

- Everything is read from the saved first-two-stages diff (`library/_shared-records/overnight-20261010-night/compare/<doc>-first-two-stages.json`; its `changed_pairs` lists every matched symbol, not only changed answers, so the `status` field is the thing to filter on) and from the two nights' records, `20261010-night` for coordinates and bar totals and both nights for the duration verdict counters.
- ⚠️ **DEVIATION from the brief ("read records only via `record_io.load_record`").** `load_record` measured **5.4 GB resident on the 0.8 GB Litolff record, 6.6x the file**, so the 5.3 GB Brahms record would need ~35 GB. The machine had 10.6 of 12.3 GB of swap used, 11 GB of disk free (not the ~20 GB in the brief) and two other lanes' gathers running, so I did not load it. `lud_extract.py --stream` reads the same file with `ijson` (738 MB peak, 83 s), keeps only unpooled fields (`basis`, `considered`, `correlated`, the only pooled ones, are never read), and feeds `readout.adjudicate_status` through a shim for the verdict statuses. **Control:** on the Litolff record both readers produce **byte-identical output** (503 bars, 11,912 boxes, 882 duration verdicts, 331 staves, 5,377 cells) for tonight's record and for last night's duration verdicts; a perturbed copy is reported different (`reader-control.txt`). The Brahms record was read once per night, streamed; the `load_record` reader was run only on the small record.
- Because the stream reader does not expand `basis`, "a `Q.HEAD_STEM_REACH` row is in the verdict's basis" was dropped; the 2.77b branch is identified instead by `beam_side` going None -> up/down with `stems_attached = 0` (the ruler fallback is the 2.77b addition; no other path gives a side where none was read).
- `lud_run_all.sh` regenerates everything (machine-local; about 10 minutes; under 1 GB resident). The extract JSONs are scratch and are not committed.

## 6. Where the brief and the data disagree

- **Disk and memory.** About 11 GB free, not 20; swap nearly full. See section 5.
- **Bar numbers.** The brief assumed the export's bar number could be mapped to a printed one. It maps exactly to the *file's* number (checked), but the file's number is 1-3 bars ahead of the print after the first few pages on both movements. Printed numbers are given only where read.
- **"13 items landed".** One item does almost all of it (2.74, 90% of Brahms notes). 2.77b adds 15%, 2.77 2%, the hollow-head family 7 notes. The 2.75 tie/slur change, 2.78, 2.61d, 2.12f and the rest of the other session's list do not appear among the 1,991.
- **`changed_pairs` lists every matched note**, 24,260 of 24,260 on Brahms, not the changed ones (the new `head_stem` / `stem_value` lines from 2.78 differ on every note). The status pair is what picks out the changes.
- The `rhythm.py` comments call the through-heads and no-stem-at-ends rules "ROADMAP 2.75"; the commits are "Rhythm leftovers" and ROADMAP calls the lane 2.77 (2.75 is tie vs slur).

## 7. Not done, and what this suggests (none of it a ROADMAP item; Sean's call)

- I did not judge any note right or wrong. Sean's eye on `sample_random_brahms.png` (20 tiles) and `system_01_zoom.png` answers whether 2.74's `too_thin` refusal is right on Breitkopf, which is the question behind 1,802 of the notes.
- If it is right, the notes are undecided only because of the rule-8 guard `ink_removed_all_marks` (`0f880dde`: a refusal that leaves a marked head unmarked narrows). The refused strokes here lie beside decided hairpins and slurs; 2.25b already treats a stroke that is a decided arc's own ink as a *connection* and not a guess. Whether a refusal that is a connection to a decided hairpin should decide instead of narrow is a design question for Sean (it would be a lane of its own and needs a GATHER-side reading of hairpin ink; "the hairpin, named and NOT built" is in the comment above `_flag_levels_table`).
- The exporter's bar over-count (+3 / +2) wants tracing. The numbers above show where it enters (Brahms between p3 and p13, Litolff between p3 and p7 and p13 and p15).
- 2 Brahms and 21 Litolff kept -> narrowed notes have no changed guard input and no GATHER change line; unexplained.
