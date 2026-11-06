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

## Lane 2.270 build (2026-11-05, branch lane-2.270-whole-rest-reader; flags default OFF)

### Prior work
2.145 (`head_rest_shape`) converts head-boxed EIGHTH/QUARTER rests on their ink; 2.230 (`OMR_WHOLE_REST_HANGS`, `_PLAIN`, `_FOUND_WHOLE_REST`) reads a detected `restWhole` by ink and writes the bar's search-found rest; 2.257 r2 puts a displaced whole rest in its own voice (`_own_voice_from_written_events`); the 09-15 guard (7189ac998) refused, never converted. Nobody read the ink under a head-boxed whole rest.

### Cause (measured on the 20261104-night slices)
`adjudicate_notehead_is_a_whole_rest` measures the DETECTOR'S BOX (height <= 0.84 sp, aspect 1.63-3.09) and the slot. The detector boxes a head's interior, so a stemmed quarter, three eighths, a clef fragment and a tremolo slash have rest-sized boxes. The INK says otherwise: trimmed height of Sean's 8 whole rests 0.44-0.83 sp; filled non-rests 1.02-1.59 sp; three dotted halves/slash hollow; 7 of the 8 non-rests have a stem row (`notehead_stem_cross_ink` or `head_stem_reach`) and the slash has ink on BOTH sides of it (0.41/0.59; heads 0.00-0.03). Those readers were on the record; nothing in the decision read them.
Process lesson: a decision that names its evidence "shape" must measure the shape of the ink, not of the box the detector drew; the reader's own bar (0.84 sp, "narrow plateau") was set on 25 boxes of one plate and never checked against the ink.

### What changed (STAGED)
- `OMR_WHOLE_REST_FROM_INK` (rhythm `_whole_rest_ink_read`, in `adjudicate_notehead_is_a_whole_rest`; export `_place_notes`, `_rest_twin_in_bar`, `_whole_rest_ink_was_read`, `_own_voice_from_written_events`): veto on stem / straddled stem / hollow / trimmed height > 0.92 sp; a decided rest whose ink was measured is written as `restWhole` (plain alone in its bar's boxes, blue otherwise); no conversion where the detector also boxed the rest (twin: Litolff 40 of 108; first build wrote them twice, +44 red bars); the 2.257 r2 bar-sum rule makes it the other voice.
- `OMR_WHOLE_REST_STEM_RULE` (Sean's fallback): the stem tests only (stem, straddle); no conversion.

### The 16 marks (tile by tile, re-adjudicated from the saved 20261104-night slices)
| mark | Sean | FROM_INK | STEM_RULE alone |
|---|---|---|---|
| 1-5 (Litolff) | whole rest | written rest (heights .44-.77) right | still refused (old) |
| 6 (Brahms, = extra 3) | whole rest | written rest right | still refused |
| 7 (Litolff) | rest, 2nd voice | the detector's own twin restWhole is written; head box refused as its twin right | same |
| 8 (Litolff) | rest, 2nd voice | written blue, voice 2 right | still refused |
| 9, 10, 12 (Brahms) | quarter, eighths | no longer a rest (`has_a_stem`); not written: `owned_by_another_staff` (owner rule, not this lane) | same |
| 11 | eighth | no longer a rest; `mark_group_duplicate` (its twin is written) | same |
| extra 1, 2 | dotted halves | no longer a rest; WRITTEN as notes right | same |
| extra 4 | F-clef fragment | no longer a rest (`ink_is_head_tall` 1.055); now WRITTEN as a note WRONG (no clef claim on it) | still dropped as a "rest" (accidentally right) |
| extra 5 | tremolo slash | `straddles_a_stem`, refused, counted right | same |
So: rests 8/8 written; stemmed notes 6/6 no longer deleted by the whole-rest rule (2 now written, 4 held by other, existing rules); slash right; the clef fragment is the one wrong (a note written on clef ink: the clef lanes 2.251 / 2.269 own it).

### Three measures (lane_report, saved 20261104-night slices re-adjudicated, FROM_INK ON vs OFF, frozen sample plus Sean's answer pages)
- Litolff pages 2,3,4,6,8,9,10,11,12,13,15,16: rests +55, notes +2 (two real eighths), beams +3, blue marks +18 -1, flags -1; unread-bar words -49 +2; red bars 299 -> 300 (my colour count: 0 new, 47 gone); notes not written 3505 -> 3452; judged right->wrong 0, unwritten->wrong 0.
- Brahms pages 4,7,12,17 | 19,20,21,22,25 | 5,8,14 (three runs, disk): notes +2/+3/+1, rests +1, dots +4, tie +1, blue +4 +1; right->wrong 0, unwritten->wrong 0 in all three. The F-clef fragment is among the +notes (p25).
- `python3 -m tools.omr.staged.check` TOTAL 227 -> 227. Fast tier: 6 failures found (flag-doc rows, ink-rules page, one static count) and fixed; rerun below.
- Not judged by Sean: 76 Litolff / 18 Brahms changed places; 12 blind tiles cut from them (out/print/2.270, key out/print/2.270-key.json).

### r1 (Sean's 12 tiles, answers-2.270-r1.json)
Tiles 1-8 right (whole rests; 6 an eighth; 7-8 second voice). Tile 9 (Brahms 17/0/12/3/8, eighth rest): written right in both arms; ON turns it and its bar blue (`onset_from_partial_bar_prefix`): the bar was already red (1.5 of 3), now its refused quarter (`owned_by_another_staff`) no longer counts as a whole rest. Tile 10 (19/0/10/5/8, quarter F4): right, blue OFF -> plain ON because tile 11 now fills the bar. Tile 11 (19/0/10/5/3): the file writes a DOTTED quarter (`<type>quarter</type><dot/>`, duration 12); the lane report's "quarter" counts the dot as a separate symbol, so the dot IS read (existing duration reader, 1.5 beats) and nothing is missing. Tile 12 (14/0/3/5/14) was mine: `ink_is_head_tall` freed a 0.62 sp wide, 1.49 sp tall piece of a sharp; fixed by `ink_not_head_shaped` (ink < 0.9 sp wide is neither head nor rest; real heads 1.29-1.59, rests 1.27+), refused and counted. Fast tier 10007 passed; Brahms ON notes +6 -> +4; judged right->wrong 0 both plates; tile out/print/2.270-r1 (looked at: box on half a sharp, nothing written).
