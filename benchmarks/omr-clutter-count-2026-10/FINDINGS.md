# 2.113 -- clutter count (does a READ neighbour touching the subject make readings fail?)

CONVENTION ASSUMED: "READ" for a neighbouring glyph = a live DECIDED verdict whose decider is not `infer:*` and whose reason is a
reading of the page, not bar arithmetic (note: `head_and_marks`, `hollow_head_bare_stem`, `hooks_counted`, `stem_value_follows`,
`chord_mate_shares_the_stem`; rest: `rest_class`, `whole_rest_means_the_bar`; dynamic: `spelled`; arc: any decided `arc_kind`;
accidental: any decided). That is the code's nearest thing to the CLAUDE.md §4 READ bar; no per-verdict "READ bar" flag exists in the
record. One staff space = median notehead box height (Litolff 20.5 px, Brahms 32.3 px at 600 dpi). "Touching" = box gap <= 0.25
space, "near" = <= 1 space. Stems/flags/structural boxes are parts, never clutter. "Wrong" = Sean's answer disagrees with the STANDING
verdict in the 2026-10-11 night record (`judged.score_row`); it is the scoring of 2.106, not a fresh judgement.
WHAT WOULD FALSIFY IT: a different READ definition, or a record where more wrongs exist (n is tiny, below).
NOT CONFIRMED: that any wrong reading was *caused* by a neighbour (this is association, not cause); unboxed ink (hairpins, merged
clef/beam mass) is not measured here at all -- that is `Q.INK`'s job.

## Data
Tiles: `benchmarks/acceptance/judged-tiles.json` (647 tiles). Record = the one the committed 2.106 baselines used:
`library/_shared-records/{beethoven5-litolff,brahms1-breitkopf}-mvt1-whole-20261011-night.record.json` (read-only streaming).
Used = glyph-subject, non-follow-up, non-control tiles whose key exists in this record, with the record's box inside the tile's page
bracket (13 of 175 kept on the manifest's doc alone, no bracket to check: 12 right, 1 wrong). Duplicate subjects collapsed.
Result: **152 scored tiles = 11 WRONG, 141 RIGHT, 24 UNDECIDED (narrowed/abstained, kept apart)**. Unavailable: 80 glyph tiles whose
key is not in the night record (subject_not_in_record 51+29, snapshot keys; NOT substituted from another gather), 28 whose box
disagrees with the tile's bracket (7+21: same key, different mark on re-gather), 128 `unscored`/`not_found` (meter, key accidental,
dynamic-owner... no comparator or no verdict at the key), 179 tiles with no glyph subject (cell/bar tiles).
Tiles were cut where the reader was in doubt, so RIGHT here is not a random sample of the score.

## Result (commands: `python3 benchmarks/omr-clutter-count-2026-10/clutter_count.py --record R --doc D --out rows-*.json`, then `analyse.py`; full table in `analysis.txt`)

| clutter definition | WRONG | RIGHT | Fisher p | shuffle-labels p |
|---|---|---|---|---|
| READ neighbour touching (<=0.25 sp) | 6/11 (55%) | 85/141 (60%) | 0.76 | 0.76 |
| READ neighbour within 1 sp | 8/11 (73%) | 115/141 (82%) | 0.44 | 0.70 |
| READ non-arc neighbour touching | 4/11 (36%) | 56/141 (40%) | 1.00 | 1.00 |
| READ non-arc neighbour within 1 sp | 6/11 (55%) | 85/141 (60%) | 0.76 | 0.76 |
| any non-part neighbour touching | 8/11 (73%) | 105/141 (74%) | 1.00 | 1.00 |

Wilson 95% intervals on WRONG are about 0.28-0.79 (touching), so the data cannot exclude a moderate effect either way.
Clutter is the NORM: 52-54% of 600 randomly sampled noteheads per record touch a READ glyph and ~75% have one within a space
(`pop-*.json`). By symbol kind (touching READ, WRONG vs RIGHT): notehead/duration 2/6 vs 69/115; notehead/not-a-note 0/1 vs 5/13;
arc 1/1 vs 11/12; rest-ish 3/3 vs 0/1 (n=4: too few). Per record the signs agree (Litolff 4 wrong, Brahms 7).

Controls. Shuffle: permuting the WRONG/RIGHT labels gives a typical |rate difference| of 0.10-0.13, bigger than the observed
-0.02 to -0.06, so the observed difference is exactly what noise gives. Sanity PRESENT: 340/357 chord heads whose chord mate is READ
see a READ neighbour (95%; misses are mates > 1 space apart). Sanity ABSENT: 0/143 heads with no non-part glyph within 1 space report a
READ neighbour. (Both are checks of the neighbour code, by construction.)

## The 11 WRONG tiles (tile images in `out/print`, nothing new cropped)
With a READ neighbour touching (6):
* Brahms 2.78-phase2 #5 (16th vs 8th): a beam block; the READ notehead/arcs just sit by it; the error is the beam count, not merging.
* Brahms 2.80-review-2 #4, #5 (eighth rests refused "ink_already_read_as_a_glyph"): the touching READ "neighbour" is the same rest drawn
  a second time by the detector. This is the one real clutter mechanism -- a duplicate claim on the same ink -- and removing READ ink
  would make it worse (the subject would lose its ink), not better.
* Brahms 2.81 tile_07 (eighth rest kept as a notehead): the neighbours are a rest and arcs; a shape misread, they just sit nearby.
* Litolff 2.75 litolff_04 (tie vs slur): the READ heads are the arc's own end notes; present by definition, not a cause.
* Litolff 2.81 tile_22 (slashed head on a stem crossed by a barline): arcs touch; the confusion is the stem/barline ink.
With no READ neighbour touching (5):
* Litolff 2.102 tile_09: value supplied by bar arithmetic (INFER) over a plainly printed head; no clutter at all.
* Brahms 2.81 tile_18: a clean dotted head, wrong on flag/beam evidence; no clutter.
* Brahms 2.83 tile_01: hollow dotted half, hairpin close but not touching; the dot was missed; no clutter.
* Litolff 2.88-review-2 tile_04 (an alto clef kept as a notehead) and Brahms 2.81 tile_15: genuinely crowded ink (clef mass, beams,
  hairpin wedges, dots) -- but the crowding is UNBOXED or unread ink, which this count (READ neighbours) cannot see.
Plain words: in 1-2 of 11 the neighbour's ink is plausibly implicated (duplicate claim; beam block); in 2 more the clutter is ink nobody
read. In the other 7 the reading failed on its own evidence.

## What this supports / does not
Supports: a READ neighbour touching the subject is as common among right readings as among wrong ones here, so "remove what is READ"
would not, on this evidence, remove the cause of most misreadings. Does not support: any claim about unboxed ink (the 2 crowded-ink
cases suggest a separate question for `Q.INK`), nor any effect of size < ~30 points of rate (n=11).
Not examined: records older than the night one (a tile cut from an earlier gather whose error was since fixed counts RIGHT here).
