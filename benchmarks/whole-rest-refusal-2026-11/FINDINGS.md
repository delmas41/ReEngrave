# Whole rests refused at export (ROADMAP 2.270) -- 2026-11-05

STAGED. Records: 20261104-night (main 636ec4742), both plates, through infer.

## Cause
- The detector boxes a whole rest as a black notehead (Litolff: 85 noteheadBlackInSpace, 18 on-line, 5 other of 108).
- `rhythm.py:adjudicate_notehead_is_a_whole_rest` decides it a whole rest (`shape_and_position_agree`).
- `export.py:_place_notes` then drops it as `ink_is_a_whole_rest` and writes nothing: the 2026-09-15 guard (7189ac998, `OMR_WHOLE_REST_INK` fb786b6c6), "REFUSED, NOT CONVERTED". No reader turns the verdict into a rest row.
- The `empty_bar_whole_rest` search runs only in bars with no head or rest box; the refused box counts, so it never runs there (all 108 Litolff boxes have no search row).
- DECISIONS 2026-10-29: "Improve the reader first" -- no roadmap row was opened until this one.

## Counts (trace; confirmed 3 subjects per bucket against the raw rows)
- Litolff: 108 boxes in 106 bars; 49 boxes / 48 bars left unread (37 alone in the bar); 40 harmless (a written restWhole twin); 19 in bars with written heads.
- Brahms: 56 boxes in 43 bars; 1 bar unread; 44 in bars with written heads.

## Sean's answers (answers.json; crops in tiles/, red box = the refused mark)
- Tiles 1-6 whole rests; 7-8 whole rests in a second voice; 9 quarter; 10-12 eighths.
- Extras 1-2 dotted halves; 3 whole rest (same crop as tile 6); 4 part of an F clef; 5 tremolo slash.
- 16 distinct marks: 8 whole rests, 8 not (6 real notes, a clef fragment, a tremolo slash).

## Lesson
- The reader, not only the export, is wrong: it decides "whole rest" for stemmed notes, clef ink and a tremolo slash. The trace agent's own look called tiles 9, 10, 12 "copies off their own staff"; Sean says they are notes. An agent's look is a control, not evidence.
- 2.145 converts head-boxed eighth/quarter rests; the whole-rest case had no converter, and the refusal hid a reader that was never measured against the print.

## Next
Sean 2026-11-05: "Fix the reader"; "Then if we can't make enough progress add the stem rule" (lane-2.270-whole-rest-reader).
