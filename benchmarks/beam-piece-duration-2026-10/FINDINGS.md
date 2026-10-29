# ROADMAP 2.219 -- a box judged a beam piece still gets a duration (phase 1, read-only count)

**Verdict: CLOSE. The exported file never writes a box judged not-a-notehead. What 2.204 counted is a stale duration on the
record, already ROADMAP 2.143 (parked OFF by Sean 2026-10-16).**

## Cause and process lesson
- STAGED ADJUDICATE `rhythm.adjudicate_duration` (tools/omr/staged/adjudicators/rhythm.py ~4570) still decides a value for a refused head
  unless `OMR_REFUSED_HEAD_NO_DURATION` is set (it is default OFF; its code comment says "default ON" -- stale, the flag is OFF).
  That is the 2.204 tile-10 value (`glyph/0/0/10/1/16`: identity `is_a_beam_piece` decided, duration 0.5 decided).
- STAGED EXPORT `export._place_notes` (export.py ~1259-1302) reads `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` BEFORE the duration and
  `_drop("not_a_notehead:<reason>")` + `continue`s for every decided reason (only `belongs_to_a_nearer_staff` may relocate, only a
  reinstated rest 2.145 may become a rest). `is_a_beam_piece` is consumed (also in `_NOT_A_GAP_REASONS`, so it is not even a red gap).
- Lesson: a verdict count is not a file count (rule 7). 2.204's "43 Litolff / 6 Brahms" counted records; the file writes none.
  The only live route for a stale value is a non-file consumer (INFER bar sum, `reconcile_chord_duration`, review tiles) -- that is 2.143.

## Count (exported file, comparable process: same arm, same tree, same pages)
Source: 2.204r3 OFF arm (`OMR_STEMS_FROM_STROKES=0`, all landed flags ON), `mini-record.json` (verdicts) with the SAME run's
`symbols.json` `hosts` (what the MusicXML wrote; xml `<note>` counts equal hosts incl. rests on Litolff, Brahms differs only by
chord/voice duplicate rows). Plates: Brahms p5,p14 (1256 written notes); Litolff (1452); Litolff p6 (556). ON arm identical +-.
Match: by PLACE (page + host centre inside the not-a-head box) -- the 2.211 / `lane_report.written_at` rule -- and ALSO by id;
id matches: 0. Script: `count_written.py` (reads JSON only).

Boxes decided not-a-head and WRITTEN at their place, by reason (OFF arm):

| reason | Brahms | Litolff | Litolff p6 |
|---|---|---|---|
| is_a_beam_piece (decided not-a-head: 3 / 3 / 6) | **0** | **0** | **0** |
| notehead_is_a_duplicate_box / stacked_head_duplicate | 15 | 91 | 46 |
| too_narrow / clipped_fragment | 4 | 0 | 1 |
| head_cut_piece | 0 | 2 | 0 |
| tremolo_slash_crosses_stem / on_a_dynamic_letter | 0 | 0 | 4 |
| written under the box's OWN id | **0** | **0** | **0** |

- Duplicate/stacked rows: the note written there is the TWIN's genuine head (the duplicate box overlaps it); not a leak.
- Every other overlap (9 boxes) was checked: the written note's id carries a decided "is a notehead" verdict (a different, genuine box
  overlapping the refused one), 9/9. Crops below.
- Stale decided durations on refused boxes in the record (the 2.204 object, not the file): Brahms 300 (190 too_narrow, 3 beam piece),
  Litolff 197 (2 beam piece), Litolff p6 77 (6 beam piece). None reaches the file as its own note.
- Brahms tile 10 box: no written note within 80 px; the box is beam ink (Sean: "Beams"); not in the file.

## Crops (rule 7): `out/print/2.219/tiles/` (sheet.png + tile_01..08), key outside at `out/print/2.219/key.json`
8 orange-boxed refused boxes that overlap a written note (4 Brahms, 2 Litolff, 2 Litolff p6). Looking at them: the written note
at each is a real head (tiles 1-4 quarter heads beside the box, 5-8 head-and-fragment overlaps); none is beam ink written as a note.

## Recommendation
Close 2.219 as measured-zero at the file. Residual (stale value read by INFER / chord-mate / tiles) = 2.143, parked OFF on Sean's
ruling; do not reopen without his word. Fix if ever built: turn `OMR_REFUSED_HEAD_NO_DURATION` on (2.143), nothing in EXPORT.
