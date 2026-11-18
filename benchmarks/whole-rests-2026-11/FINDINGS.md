# Whole-bar rests in red bars (ROADMAP 2.315) -- 2026-11-17

STAGED. Written by the manager from the lane's report (branch `lane-2.315-whole-rests`, 8442a5a9b).

## Cause and process lesson

About three in four red bars that print only rests are bars where no reader ever put a box on the whole rest.
The empty-bar search (`gather_empty_bar_rest_search`, GATHER) never looks in a cell that holds ANY head or rest
box -- a neighbour staff's head or a barline's ink counts -- and where it does look it tests the ink with
detector-box numbers (0.84 sp tall, aspect 1.63); real whole rests measure 0.82-0.89 sp tall, aspect 1.56-1.62,
and miss by a hundredth. Lesson: 2.270 re-measured "is this a whole rest" on the ink in one reader and nobody
checked the other readers asking the same question.

## Part 0 (2.311 saved gathers, main 803c90513, both with Litolff p1; crops of 59 + a seeded sample of 112)

- Rest-only red bars: 76 of 585 (Litolff 41, Brahms 35).
- Never seen: 58 (Litolff 27, Brahms 31); the search never ran for about three in four of them.
- Seen as a rest, then lost: 10 (9 Litolff `rest_slot_contradicts_class`: the slot is measured on straight page
  lines, not the local staff lines).
- Claimed as a word: 4. Read as a rest, bar red for bookkeeping: 4 (none is the whole-rest-in-another-meter case).
- Brahms p0 swept cells: whole rests 8 right, 0 wrong, 0 unread; 0 of Sean's 16 labelled rests in a red bar.
- Sean's set-b tiles 8 and 12: both never seen (the search never ran).
- Seen in passing, not this lane: at least 2 Litolff half notes written as quarter rests.

## Change (flag `OMR_WHOLE_REST_SEARCH_OWN_BAR`, default OFF)

The search looks in every cell and uses the 2.270 ink rule (at most 0.92 sp tall, at least 1.2 sp wide -- the
1.2 is the lane's number: rests 1.33-1.67 against two flag pieces at 1.02; NOT confirmed on another publisher).
EXPORT (`_place_found_whole_rests`) writes the rest, blue where other boxes stand, only when every box in the bar
is positively not its own mark; narrowed / clipped / too-narrow refusals leave the bar unwritten. One whole rest
per bar; where it sits along the bar is not used (page-facts, Sean 2026-11-17).

## Measures

- Litolff (with p1), off vs on: rests +15 -1, blue marks +6, red bars 168 -> 168; 15 bars from nothing to a whole
  rest (7 blue, 8 plain). Judged right->wrong 0, unwritten->wrong 0 on 302 tiles.
- Brahms: NOT measured (preview predicts 24 bars; Litolff predicted 14, measured 15).
- Controls from real bars (set-b tiles 8, 12; the 2.288 r3 notehead) pass. Fast tier 10754 passed before a
  one-line last edit; 97 targeted tests after it.

## Not verified

Brahms; the 15 Litolff gains unlooked; Litolff p1 m51 had a blue rest OFF and none ON; the 1.2 sp width;
`judged_claims` not run; why red bars did not fall.

## Landed ON 2026-11-17 (main 0fd3219e2), with the lost rest fixed

- Litolff P1 m51 (blue OFF, unwritten ON): its only head-classed box was a refused `clipped_fragment` -- a note
  of the next staff cut off at the cell edge about 3.7 spaces below the staff -- and the new write rule counted
  it as a possible note of the bar. `export._clipped_piece_of_the_next_staff` now ignores such a piece when it
  sits 3 or more spaces beyond the staff with no ledger line between (measured: 181 clipped pieces in searched
  Litolff bars sit 3.4-5.7 spaces out; 168 have no ledger-line box beyond the staff; the 13 that do keep the bar
  unread). Real-bar control `TestLitolffP1M51` fails before, passes after.
- Re-export of the saved Litolff ON record: 20 bars gained, 0 lost; the 15 first gains hold; m51 is back (blue);
  5 new gains, all blue (4 looked at by the landing agent: only a whole rest; P12 m206 not looked at).
- The manager looked at the first 15 gains and the loss at full size: every bar holds only a whole rest.
- Brahms NOT measured before landing; the overnight run of 2026-11-17 is its first measure.
- Combined fast tier on the final tree: 10,783 passed, 0 failed.
