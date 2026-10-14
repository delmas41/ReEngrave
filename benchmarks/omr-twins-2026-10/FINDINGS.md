# ROADMAP 2.119 -- twins: why one note is written and its look-alike is not

2026-10-14. Read-only study of the `20261013-night` records (gathered on ca46eae4), exported on origin/main ffb66049
(2.117 partial bars ON, 2.115 re-centring ON). Written by the manager from the lane's report (the lane's Write tool
refused report files); every number is printed by a script in this directory (`run.sh` gives the order; outputs in `out/`).

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* Twin = same head type, stem direction and position kind (line / space / outside the staff), one written and one not,
  paired one-to-one, same staff preferred. Falsified if Sean says a pair does not look alike.
* "Written" = reaches the MusicXML, not "right": Sean's truth has no pitch/duration, so a wrongly written note is invisible here.
* Brahms detection is NOT measured: 376 of 382 truth heads are production's own confirmed boxes (re-found by construction);
  only 6 drawn heads are independent.
* The record has no sub-floor detector boxes and no INFER margins, so "how close did it come" cannot be answered for C or A.
* Litolff stems were read off the page raster by the lane (the same reader agrees with Sean's stem boxes on 371/382 Brahms heads).

## Fates of truth notes (export hook totals equal the exporter's own: Brahms 10,311 notes, Litolff 6,573)
| | Brahms p0 (382 heads) | Litolff p1 (50 clean hollow heads) |
|---|--:|--:|
| written plain | 273 | 27 |
| written blue | 50 | 9 |
| duration narrowed / chord value undecided | 24 / 2 | 0 |
| refused as not-a-notehead | 6 | 1 |
| in a held bar / in a partial bar's red gap | 21 / 6 | 0 |
| not detected | 0 (by construction) | 10 |
| class wrong (hollow called black) | 0 | 3 |
| owner wrong, pitch undecided | 0 | 0 |
Brahms: 29 heads in 8 uninspected cells left out. Litolff: the 9 leaked cells (2.112) dropped.

## Ranked split points (69 pairs: Brahms 58, Litolff 11)
| | split point (first stage where the missed twin parts) | pairs |
|---|---|--:|
| A | ADJUDICATE duration left narrowed, INFER did not collapse it (19 `beam_discounted_uncertain`) | 24 |
| B | EXPORT bar-sum hold-out (14 voice over-full, 4 nothing before/after the gap, 3 short without an unread symbol) | 21 |
| C | detector: no box (Litolff) | 8 |
| D | inside a partial bar's red gap | 6 |
| E | refused as `stacked_head_duplicate` | 5 |
| F | detector: class wrong (Litolff) | 3 |
| G | chord value undecided | 2 |

## What differs between the twins (top 5)
* **A** -- the heads are identical (conf 0.81 vs 0.80; box 1.28x1.14 vs 1.28x1.15 spaces). The beam reader found no beam ink
  at the missed note's stem in 15/24 pairs (twins 6/24); the detector's own beam boxes sit near the missed stem in 16/24
  (twins 7/24) but the ink reader cannot confirm them, so the length stays open. INFER collapsed 32 of 63 narrowed notes on
  the page and not the other 31.
* **B** -- the note is fully read (duration + pitch decided, 21/21); its bar does not add up (3-quarter bars summing 4.0-7.0,
  or 1.0-2.0 short). In 11/21 another note in the bar was lost earlier at A or E: a cascade.
* **C** -- the same half note (Sean's boxes 1.20x1.01 vs 1.21x1.02 spaces). Written Litolff hollow heads sit near the
  detector floor (conf median 0.40, min 0.20, 9/36 under 0.30), so the missed ones are plausibly just under it.
  On-line halves missed 10/26, in-space 4/24.
* **D** -- a fully read note between a partial bar's first and last unread symbol; in 6/6 another note in that bar was lost at A or E.
* **E** -- two heads one step apart in a chord (~1.0 space): the stack fit counts the blob as ONE head (k=1) for all 5 missed
  notes vs k=2 for 4/5 twins. Page-wide, none of the 170 k=2 heads was refused as a duplicate.

## Surprises
* Cascade: 27 of 69 pairs (B + D) are fully read notes lost only because their bar is held or gapped; 17 of those 27 have a
  note lost earlier at A or E. Fixing A and E would also recover much of B and D.
* Ledger heads are missed 21.5% on Brahms vs 11-12% on lines/spaces -- through A and B, not the detector.
* Owner and pitch lose no notes on either page.
* 3 Litolff hollow heads are cut by the cell's lower edge (boxes 0.38-0.47 space tall).

## Controls
* Truth matched to itself comes out written for 382/382 Brahms and 50/50 Litolff.
* Truth shifted 3 spaces still touches a box for 12/382 Brahms and 0/50 Litolff.
* 40/40 written Brahms string-part notes have their pitch in the MusicXML bar; the same check finds the pitch for only
  5 of 21 missed notes (12 of those 21 bars are empty in the file). Weak check; the stronger one is the hook's total
  equalling the exporter's own report.

## Crops for Sean
`crops/sheet_1.png` to `sheet_5.png`, three pairs each, a small red corner bracket and "A"/"B" only. Sheet 1 = split A,
2 = B (whole bar), 3 = C, 4 = D (whole bar), 5 = E. Which side is the written twin is in `crops/LEGEND.md` (seeded coin flip).
