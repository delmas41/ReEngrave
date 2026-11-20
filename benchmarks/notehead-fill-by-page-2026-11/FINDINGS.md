# Is hollow-or-solid tuned to one publisher? (ROADMAP 2.326), 2026-11-19

STAGED, GATHER + ADJUDICATE. Small test, read-only; filed by the manager from the lane agent's report (branch
`lane-2.326-fill-smalltest` ec614563e: scripts, per-head rows, histograms). Crops `out/print/2.326-fill/`.

## Cause, and what it teaches

The manager's diagnosis (from the 2.325 audit's rank 1) is MOSTLY FALSIFIED. The reader that decides -- the
slit test, "paper runs between ink across the head's middle rows" (2.148; 0.18 / 0.06) -- separates Sean's
hollow and solid heads on BOTH plates with the same numbers, because it does not depend on the head's shape.
Where the file is wrong or blue, the cause is the BOX the fill is read in, not the fill measure. Lesson: an
audit of constants is a map; before naming a fragile number, measure the chain that actually decides, on
judged marks. And again: measure the mark, not its box (Sean 2026-11-18).

## Truth heads (Sean's tiles and the one hand-labelled page)

Litolff 76 hollow (all halves, tiles only; no hand-labelled Litolff page) / 74 solid. Brahms 37 hollow (33
from p0) / 485 solid. NO whole note has ever been judged on either plate: the whole-note cuts are unchecked.

## Against today's cuts (Sean's marks)

| measure | Litolff hollow: hollow / between / solid | Litolff solid read hollow | Brahms hollow | Brahms solid read hollow |
|---|---|---|---|---|
| slit on the detector box (decides today) | 69 / 3 / 4 | 0 | 35 / 1 / 1 | 0 |
| slit on the trimmed head (2.220) | 62 / 0 / 2 | 0 | 23 / 0 / 0 | 11 |
| centre window (2.23) | 50 / 7 / 19 | 3 | 30 / 7 / 0 | 1 |

The 11 Brahms solid heads read hollow on the trimmed head: the trim runs BELOW the head and takes in paper
between its stem and the next mark (harmless today only because the slit on the box reads them black first).
The centre window and hole-size measures ARE plate-dependent (Litolff halves' centre 0.61 vs Brahms 0.27) but
no longer decide first.

## What the file does with those heads

Litolff hollow: 55 right plain, 15 right but blue, 2 narrowed, 2 refused as not a note, 2 WRONG (quarters).
Brahms hollow: 33 right plain, 1 narrowed, 3 refused (`head_cut_piece`; twin not checked). No solid head is
written hollow on either plate. The 2 wrong: `glyph/6/1/5/11/1` -- trimmed head 1.778 spaces wide, over the
1.75 cap, refused as not one head; `glyph/2/1/0/11/2` -- read hollow, a guard dropped the half (which guard
not established). Of the 15 blue Litolff halves, 8 are blue because the detector box is not one head's size.

## Page-relative candidates

"As black as this page's solid heads" cannot be tested here: both scans are bitonal, the page's solid heads
are exactly 1.0 (a computation, rule 7). No candidate separates both plates with a gap; none proposed.

## Frozen sample (code's count; changes, not fixes)

Heads left blue, narrowed or abstained because of a fill reading: Litolff 36 (24 are blue halves because the
detector box is not head-sized -- their own ink reads hollow on 19), Brahms 6.

## Outcome

No change to the fill cut. The one-plate numbers sit AROUND it: the detector-box head-size gate (24 blue
Litolff halves, 0 Brahms), the 1.75-space width cap on the trimmed head, and the trim reaching below the head
on Brahms. The rule as a musician says it: a head is hollow where paper runs between its own ink across its
middle -- read on the head's own ink, never its box; never from paper beside or below the head; never from
one speck in a black head; never a quarter where heavy ink closes the slit to specks (Sean: half).
One blind tile for Sean: `out/print/2.326-fill/blind/tile_01.png` (`glyph/2/0/7/4/5`, written a blue half).
Possible third-publisher check, not examined: `benchmarks/omr-labeling-hollow*-2026-09/` holds Sean's
hollow-head labels on Durand, Universal, Jurgenson, Novello, Peters, Simrock and Eulenburg plates.

## Sean's answer to the blind tile (2026-11-19)

`glyph/2/0/7/4/5` (Litolff page 2), written today as a blue half: "Litolff mark is a sharp sign blending into
the barline." So it is not a notehead. The hollow reading was honest about the ink (a sharp has paper inside
it); the fault is upstream of the fill test -- a detector box on a sharp joined to a barline is taken as a
head. This is the "box that is not a notehead written as a note" cause already open under ROADMAP 2.319, and a
Litolff MERGE case (page-facts: Litolff merges; an ink component is not a mark). `answers.json` here.
