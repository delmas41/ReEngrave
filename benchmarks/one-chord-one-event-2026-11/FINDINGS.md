# 2.300 — one chord is one event (STAGED, ADJUDICATE + EXPORT grouping)

Written by the manager from the lane's report (agent FINDINGS writes are
refused). Branch `lane-2.300-one-chord-one-event` c6927bfd5, flag
`OMR_ONE_CHORD_ONE_EVENT` default OFF. NOT LANDED: waiting on Sean's 12 tiles
(`out/print-from-worktrees/2.300-r1/sheet.png`, key beside it).

## Cause and process lesson

Of Sean's three 2.291 "chord counted as two events" bars only tile 7 is a
chord split. 2.291 read the per-head row list as if it were the exporter's
events (a claim about a mechanism made from the wrong stage's rows).

- Tile 7 (Litolff p2 s1 st4 c14): the heads of a SECOND stand ~1.0 head width
  apart; both groupers join by x only within 0.6. The left head touches no
  stem (1-4 px off its box) so `adjudicate_head_stem` abstains `no_stem` and
  it keeps a quarter beside a half.
- Tile 10: the chord is already one event; the bar is red for a false 16th
  rest at the sharp (2.288's ground, still open).
- Tile 11: already one event; two voices come from `Q.VOICES` counting two
  heads owned by another staff (voices lane).

**Lesson:** a diagnosis names the stage whose rows it read; "events" are the
exporter's, not the head list.

## Count before building (flag OFF)

| plate | red bars | one stem, two events (bars / notes) | merging sums to the meter |
|---|---|---|---|
| Litolff 9 pp | 191 | 19 / 79 (~10%) | 14 |
| Brahms 8 pp | 155 | 13 / 59 (~8%) | 11 |

"Sums to the meter" is arithmetic: a lead, not evidence. The lane's own crop
look (13 pairs: 4 clearly a second, 2 clearly not, 3 unsettled) is not
evidence either.

## What was built (`tools/omr/staged/one_chord.py`, one geometry: a step apart, one head width over, one stem)

1. Head-to-stem join (`stem_value._stem_of_a_second`): a head no stem touches
   takes its neighbour's stem when the stem stands between them; only when its
   own value is decided and the neighbour's value is >= its own. Written BLUE.
2. Grouping (`rhythm.adjudicate_event`, `voicing.group_chords_in_measure`):
   two LONE heads on one decided stem with equal values are one event; a group
   already holding two heads is never joined (a beamed run stays). Two whole
   heads in that geometry join with no stem.

A first draft keyed on the stem id alone and was wrong twice (rescued two flat
signs boxed as heads into notes; changed two decided Brahms values); both
removed by the guards above.

## Measured (flag OFF vs ON, same tree, pages, stages)

| plate | red bars | notes in red bars | stopped red | became red | notes lost/gained | values changed |
|---|---|---|---|---|---|---|
| Litolff | 191 -> 180 | 590 -> 548 | 12 | 1 | 0 / 0 | 1 (tile 7, quarter -> half) |
| Brahms | 155 -> 146 | 477 -> 431 | 9 | 0 | 0 / 0 | 0 |

- The bar that became red (Litolff 4/1/1/9) summed right before only through a
  compensating error (a chord read as two quarters). It is tile 5.
- Side effects NOT fixed: legacy `annotate_beams` sees merged chords —
  Litolff flags +10, beams -12/+2; Brahms flags +2, beams -2; slurs -4 / -2
  (a slur whose two ends are now one chord is dropped).
- Conservation holds, unaccounted 0. judged right->wrong 0; judged_claims no
  new contradiction. Flag OFF byte-identical. check 228.
- Real-case controls: tile 7 becomes one chord; tiles 1, 6, 10, 11, 12 and an
  unjudged two-voice mirror bar are identical to OFF.

## Open before landing

- Sean's tiles.
- The FULL fast tier was not re-run after the last three fixes (only the
  touched files): run it on the merged tree.
- The beam/flag/slur side effects need a look: are the beamed dyads still
  written with the right value and beams?
- Nothing retired; two groupers remain (now one geometry).

## Next

Brahms p0: of 58 stemless heads nearly every pair is a STACKED pair (dx 0, a
third apart) with the stem on the other head — a stacked-mate join, not the
second join, is what reaches Sean's 11 Brahms stem labels.
