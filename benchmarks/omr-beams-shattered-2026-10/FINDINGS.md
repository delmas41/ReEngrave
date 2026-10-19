# ROADMAP 2.170 -- beams on the shattering plate (STAGED GATHER+ADJUDICATE; flag `OMR_BEAM_REFUSED_OFF_THE_TIP`, default OFF)

Records: 20261018-night (main 2bb43b85, through infer). Code: this branch off main 7f668d66. Probes: `probe/`.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

1. **A beam joins every stem it spans AT THE STEM'S END** (Gould, *Behind Bars*, "Beams"; omr-beam-confirm-2026-10 §9.2; Sean
   2026-10-16 "the stem tip decides beamed or not", 2.146 tiles 33/33 + hand truth 41/41). So a stroke that stands nowhere near
   a note's own stem end is not that note's beam, whatever else it is (slur, hairpin, staff line, a neighbour's beam).
   **Falsified by** a note the rule decides unbeamed that Sean reads as beamed (a tile below), or a beam whose ink reaches the stem
   while no stroke row of either reader stands at the tip (the readers' fault, but the rule would then write it wrong).
2. **A note with no beam and no flag at its stem is its head's value** -- the pipeline already reads every unmarked head this way
   (`head_and_marks`), with the flag window as the only guard. This lane makes a head whose every nearby stroke was REFUSED go
   the same way. **Falsified by** a changed note carrying a flag the detector never boxed and the tip window could not read.
   **NOT CONFIRMED** for this population: the 2.146 rule demanded the flag window read clean; here it is unread. Tiles below.
3. The two zone sizes (stem x +- 0.3 space, tip +- 0.6 space) are 2.81's (`BARE_STEM_ACROSS_SPACES`, `BARE_STEM_TIP_SPACES`),
   set before this lane and not refitted. They only NARROW what the rule may touch (a stroke inside the zone keeps the narrowing).

## 1. Brief from the tree (rule 1)

* 2.38 (`Q.BEAM_STEM_JOIN`, the stem-to-beam ink join) and 2.38b/c: merged. 2.146: research + `OMR_STEM_TIP_DECIDES_BEAM` ON
  (clean tip = run reader no run + flag window clean -> no beam; "a beam at the tip" branch REMOVED after tile 13).
  2.153 `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` parked OFF. 2.155 `OMR_STEM_AT_BAR_EDGE` ON (a stem refused at the cell edge).
  2.169 `OMR_STEM_PAIR_AT_HEAD` ON (in these records). 2.121 §1: on Brahms p0, 51 of 52 `beam_discounted_uncertain` were BARE
  stems beside a refused slur/tie box. 2.146 §9.5: of 81 still narrowed, 48 had no own CV stem, 26 had the flag window unread.
* Refuted/withdrawn: the "a beam run at the tip decides n levels" branch (2.146 tile 13). Nothing on "shattered" beams was built.

## 2. The causes, counted (20261018-night; `extract_2_170.py`, `cells_2_170.py`, `causes_2_170.py`, `tips_2_170.py`)

Population: every first `adjudicate_duration` verdict NARROWED `beam_discounted_uncertain` or `beams_ambiguous`
(Litolff 455 + 93 = 548; Brahms 2,250 + 143 = 2,393). Standing after EVALUATE/INFER: still narrowed Litolff 361, Brahms 1,850.
First cause per head, from the cell's own rows (own stem = a CV stem box overlapping the head box; "beam ink at the tip" = a
stroke whose ink row reads >= 1.75 lines thick, covering the stem's x, within 0.5 space of its far end):

| cause | Litolff | Brahms | what my eyes saw (ours, not evidence) |
|---|--:|--:|---|
| (d) **no beam ink at the stem tip** -- the refused strokes are slurs, hairpins, staff lines, text or a neighbour's beam, and the note is unbeamed | **279** | **1,319** | Brahms 16 sampled: 14 unbeamed quarters / dotted quarters / chord members, 1 a bass clef boxed as heads, 1 a tremolo chord; Litolff 7 sampled: 6 quarters, 1 unclear (possible flag) |
| (b) no own CV stem found | 191 | 933 | Brahms 11 sampled: **9 not notes** (slivers boxed at barlines, a rest), 2 real; Litolff mixed |
| (c) beam ink at the tip counted, but left a range / refused (`not_straight`, `no_stem_at_ends`, arc ...) | 68 | 124 | Brahms 3 sampled: all real beams (2 refused `not_straight` on a sloped beam fused with a slur; 1 sixteenths) |
| (a) **shattered**: the only beam ink at the tip is a detector box `_kept_beams` dropped for a shorter CV piece, or a CV piece stopping short of the stem | 10 | 17 | Brahms 1, Litolff 1 sampled: both real eighths |

Why the 2.146 rule did not decide the (d) heads: the tip's beam-run reader read NO run on almost all of them (Brahms ~1,150 of
1,309), but the FLAG window abstained: `ink_not_flag_shaped` 336, `head_at_this_end` 266, `crosses_both_sides` 176, `runs_on` 163,
`occupied` 74 (Brahms; Litolff the same order). A slur or hairpin crossing near the tip is exactly what makes that window say
"cannot tell". So on both plates the narrowing is not a beam the reader cannot tie to a stem: it is an unbeamed note held
narrowed by strokes it correctly refused. The shattered beam the brief named is real but small (27 heads over both plates).

**The fix targets (d)**, the biggest real-note cause. (b) is mostly not notes and is left alone (deciding them would write
non-notes); (a) is guarded, not fixed: the rule's zone test sees the dropped detector box at the tip and keeps the narrowing.
