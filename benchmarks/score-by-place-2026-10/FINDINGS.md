# 2.211 Score by place, not by box id (2026-10-27, Sean "Yes")

## Cause first (rule 3), and the process lesson

**Cause (shared measuring tools, not STAGED/LEGACY).** A detector can box one head twice (the head, and the head with its stem). ADJUDICATE writes one
of the two; a change can move which. Our tools identified a note by that box:
- the by-box-id list (`benchmarks/staff-eraser-2026-10/lost_notes.py`: `set(off rg) - set(on rg)`) calls the swap a lost note;
- `lane_report.pair_hosts` paired by box CENTRE within half a staff space; the head box and the head+stem box have centres 1-2 sp apart, so the
  twin fell outside it;
- the judged scorer (`judged.py`) reads the verdicts of the box Sean was shown, so a twin refused as `stacked_head_duplicate` while the other box is
  written reads as wrong (Litolff `tile_05` `glyph/4/0/7/7/10`: the note written is `/2`, a quarter F4 in both arms).
In each the exported music is identical. A box is the detector's id for a piece of ink; the music is what EXPORT wrote.

**Process lesson.** Match what is measured on the thing the product ships (the written event at a place in the file), never on an
intermediate identity. This is the second time (FINDINGS 2.206 sections 5 and 11) a measuring tool, not the reader, produced the "regression".

## What changed (`tools/omr/staged/lane_report.py` only, plus tests)

- `parse_symbols` now records each written note's `onset` (divisions, backup/forward/chord/grace aware) and `voice`.
- `place_of(host)` = (page, system, staff, cell) from the glyph key + (part, bar, onset) from the XML.
- `pair_hosts` in three rounds: (1) same place and same pitch; (2) the old page-position rule on what is left (it carries a note whose onset
  moved because an earlier note in its bar changed value, which is reported on that note); (3) same place, different pitch or kind, so a changed
  pitch at its place reports as a pitch change. A box swap with the same music pairs in round 1 and reports nothing.
- Judged: `by_place` attaches each right->wrong / right->lost row to the OFF file's written event for its box (the host written from that key, else
  the host whose centre lies inside the box, which is the `/10` case). The ON file is read at that place: same pitch and value and dots ->
  `same_music` (printed, not a regression); something else or nothing written -> stays right->wrong; no OFF event at that place ->
  `not_found` on its own line, never right or wrong (rule 8).
- `lane_report lost-notes --work DIR` replaces the by-rg `lost_notes.py` (lost = no note at its place, with the verdicts that differ).
- `lane_report rescore --work DIR [--box-keyed] [--drop N]` re-scores a finished report's saved arms.
- `judged.py` is unchanged: its per-box status is still the scorer's answer; the place attachment is applied on top in the report.
- Known limit: a note whose onset shifts AND whose ink moved more than half a space reports as lost + gained (as before).

## Control (rule 7): re-score the saved arms of 2.206d and 2.205b

`--box-keyed` strips the onsets, so it is the old rule; it must (and does) reproduce the saved reports exactly.

| report | measure | BEFORE (box) | AFTER (place) | planted 5 lost (AFTER) |
|---|---|---|---|---|
| 2.206d litolff | by-rg lost notes (old lost_notes.py) | 21 | 11 | 16 (= 11 + 5) |
| 2.206d litolff | file notes | +25 -16 | +24 -15 | +24 -20 |
| 2.206d litolff | judged right->wrong | 1 (`tile_05`) | 0 (1 `same_music`) | |
| 2.206d brahms | by-rg lost notes | 14 | 10 | 15 (= 10 + 5) |
| 2.206d brahms | file notes | +50 -12 | +48 -10 | +48 -15 |
| 2.205b litolff | file notes | +35 -13 | +34 -12 | +34 -17 |
| 2.205b brahms | file notes | +29 -10 | +29 -10 | +29 -15 |

Twins with a changed pitch (2.206d tiles 4 and 7: D4 -> E, B4 -> A4) are not hidden: they now report as pitches (litolff ~16 -> ~18, brahms 0 -> ~2).
The 2.205 report shows one twin (Litolff) and its judged tile was not in that sample's right->wrong. Tests: `tools/omr/tests/test_staged_lane_report_2_211.py`
(each positive has a twin that must still fire, including the old rule failing the swap).
