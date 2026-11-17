# Ledger count: why it refuses (ROADMAP 2.312) -- 2026-11-17

STAGED. Written by the manager from the lane's reports (branch `lane-2.312-ledger-count`, 2fe4c6a94: scripts
`cause_look.py`, `rung_why*.py`, `blue66.py`, `sean4.py`, crops in `look/`, `why30/`). No code changed.

## Cause and process lesson

The 2.311 small test's "the fallback decides 24% / 41% of Litolff far heads" was inflated twice: by boxes the
reader itself calls not a head, and by copies of a neighbour staff's note seen in this staff's padded cell.
Lesson: tally by reason word AND by what reaches the exported file before sizing a cause; a refusal word
(`no_rungs`) hid four different faults.

## Litolff, 443 own-staff far heads where the count refused (saved records, frozen sample)

- 183 are boxes refused as heads (clipped fragment 118, on text 36, too narrow 18, tremolo slash 11): not written.
- 202 "no printed line found at the box" (`no_rungs` 146, `no_line_at_the_note_box` 56); 39 "count does not fit";
  19 "a line is there but not one this head can sit on".
- How the fallback (`consequences.restate_pitch`, reason `position_and_clef_ledger_unread`, 2.248 r3) is written:
  GUESSED (blue) via `export.far_unread_guess_of`; 3 plain after a clef change (never gets the blue mark).
  The manager's "written plain" to Sean was wrong (corrected to him the same day).

## What reaches the file (pages 4, 8, 10, traced export; real heads, count refused: 128)

- 66 written blue; 2 written plain (clef-change branch).
- 60 carry the blue verdict but are not written: `owned_by_another_staff` 52, `mark_group_duplicate` 5,
  `chord_value_undecided` 2, `wide_box_unread` 1. All counted under `notes_not_written`; none silent.

## The 66 written-blue heads, why the count refused (the lane's code-level look)

| cause | heads |
|---|---|
| count does not fit | 12 |
| line shared with a neighbour head (reads with other heads' ink left in, refuses once it is removed) | 12 |
| reads on the page ink alone, refused in the real run (input not found) | 11 |
| a line is printed but the box is too small and misses the 0.40 sp band at its edge | 10 |
| no line and no stub-like ink beside the head | 10 |
| first space / first ledger, no line seen | 8 |
| stub ink exists, finder's tests failed | 3 |

No single cause is above a fifth. Manager's grouping (ours, not measured as one mechanism): 22+ rest on the
BOX (its edge and a 0.40 sp band) rather than the head's ink, and 12 on removing neighbours' ink.

## Sean's four judged-wrong tiles (answers-2.311-ledger.json)

- Tile 2 (B5, one ledger line): box edge 1.23 sp out; finder saw no line.
- Tile 6 (F6, three): finder saw one rung at 1.59 sp.
- Tile 8 (D6, two): finder saw both lines (1.36, 2.29 sp); the box is 0.89 sp tall and its edge is 0.46 sp past
  the line, outside the 0.40 band.
- Tile 11 (C2, two): box 0.64 sp tall, refused `not_a_note:too_narrow`; without that, `count_does_not_fit`.

## Not done

Brahms not re-run; no fix built; the three measures, tiles and fast tier not run. The tile set
`out/print/2.312-r1` was NOT sent to Sean (most boxes are neighbour-staff copies).
