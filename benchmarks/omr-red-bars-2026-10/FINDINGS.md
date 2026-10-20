# 2.173 -- a bar that does not add up is written in red, never held out

Sean 2026-10-19: *"Written in red instead of held out is the way to go."* STAGED EXPORT (MusicXML `export.py`, LilyPond
`lilypond.py`), flag `OMR_RED_BARS` (**OFF**; `1` writes it). Records: `20261018-night` (Litolff 1.1 GB, Brahms 7.3 GB), replayed
EXPORT-only, flag OFF vs ON, `replay.py` (loads each record once). Nothing merged, nothing flipped.

## What it does
**REVISED 2026-10-19 (Sean: "Each note with its own color")**: the notes are NOT recoloured. Inside a red bar each note/rest keeps its own status colour (black READ, blue #1F6FEB GUESSED); the BAR is marked red by the bracket + words only (MusicXML and LilyPond). Everything below that says "every note red" / "red \override per voice" is superseded; numbers are unchanged (colour only).
* Where EXPORT held a bar out under 2.8 (`bar_does_not_add_up`) and the 2.117 partial-bar planner could not place a gap, the bar
  is written through the ordinary writer: each event at its own read value, its own READ/GUESSED carrier, **no padding rest,
  no `<forward>`, nothing moved**. A 2.117 partial bar keeps its own path (it is not a held bar).
* MusicXML: every `<note>` colour `#D00000` (the existing UNREAD red; a GUESSED note's blue is replaced for the drawing only, its
  `reengrave:guessed` carrier stays), one red bracket start/stop over the bar and one words direction
  `does not add up: should hold X, counted Y (quarters)`.
* Coverage: `report["bars_written_red"]` (bars, rows, read, guessed, two_voice, `bars_list` = per bar ids, want, counted per voice,
  and every event row with kind/pitch/beats/`READ|GUESSED`/glyph key). Not in `bars_held_out_sum`, not in `partial_bars`.
* LilyPond: same predicate (`SX._red_bar_applies`). Printed values stay the read values. `Timing` is ONE clock for the whole
  score, so a per-staff `measureLength` was tried first and **failed** (2,179 barcheck warnings, every later bar off): the staves
  drift. What stands: SHORT bar = an invisible `s` skip fills the clock (prints nothing, not a rest); OVERFULL bar =
  `\scaleDurations W/counted` (note shapes unchanged, no tuplet bracket drawn). Red `\override` per voice, red `TextSpanner`
  bracket, words set to take no horizontal room (without that Litolff went 48 -> 146 pages).
* Not red (stays held, counted): a lone whole-bar rest whose length disagrees with the meter (2.79: two parts disagree about the
  bar; the rest has no value of its own to keep). Zero such bars on either plate.
* Acceptance: `bars_add_up_control` skips a measure carrying the "does not add up" words and counts it `written_red`; the proxy
  `bars_written_red` is its own number (`machine_proxies`, `render_table`).

## Numbers (20261018-night, replayed)
| | Litolff OFF | Litolff ON | Brahms OFF | Brahms ON |
|---|---|---|---|---|
| notes reaching the file | 6,626 | **8,119** | 11,991 | **14,842** |
| rests | 953 | 1,158 | 4,151 | 5,281 |
| bars held out (sum) | 624 (1,570 rows) | **0** | 915 (3,954 rows) | **0** |
| bars written red | - | 624 (1,691 rows: 1,318 READ, 373 GUESSED; 9 two-voice) | - | 915 (3,954 rows: 3,636 READ, 318 GUESSED; 21 two-voice) |
| notes not written (total) | 6,015 | 4,445 | 15,310 | 11,356 |
| 2.117 partial bars | 174 | 174 | 541 | 541 |
| LilyPond PDF pages | 48 | 70 | 79 | 121 |
| LilyPond barcheck failures | 0 | 2 | 0 | 0 |
| LilyPond "compressing over-full page" | 0 | 6 | 8 | 33 |
| MusicXML import (music21; MuseScore not installed) | ok, 0 irregular, 0 warn | ok, 617 irregular, 0 warn | ok, 3 irregular, 2 wedge warn | ok, 905 irregular, 0 warn |

Remaining holds apart from structural: **none** (`bars_held_out_sum` 0; the 2.117 `stay_held_by_reason` that held 564 Litolff (196 overfull, 340 short with no unread symbol, 28 nothing
before/after the gap; the other 60 are doubled-staff copies) / 915 Brahms (497 / 281 / 137) bars is
empty because those bars are now red). The Litolff 60 doubled-staff copies are written red too (rows go through the ordinary
writer; the accounting equality holds, no `Unbalanced`).

## Controls (each can fail)
* **OFF = main**: `xml_sha`/`ly_sha` of my tree with the flag OFF equal a checkout of `origin/main` (b8cab51e3) on both plates
  (Litolff 75c35cbbcff168b1 / 92cde3bf152c855a; Brahms fcdd1553a91aede8 / f5cbe7c397a43647), and a second OFF run after ON in the same
  process equals the first (the export does not mutate the record).
* **Nothing invented**: the held list under OFF and the red list under ON name the same bars (part, staff, bar_key, ordinal) with the same row counts on both plates (Litolff 564 = 564, Brahms 915 = 915; the 60 doubled copies were never listed as held). Also: every red bar's rows are the held bar's events (same bars, same rows: 1,570 -> red 1,691 only because the 60 doubled-staff
  copies' 121 rows were never charged by the hold-out; unit test `test_the_red_bar_events_equal_the_held_bars_events`); no `<rest>`/`<forward>` is
  added to a red measure (unit test), and an independent parse of the ON file (`acc_check.py`, imports nothing from the exporter)
  finds **0 measures that are not red and whose voice sum differs from the meter**, 624 / 915 red-marked.
* **"Bars add up" does not count them**: `bars_add_up_control` exact 4,598 / 5,347 in both arms; `written_red` 624 / 915; its
  `partial_unread` falls by exactly the red count (held bars were counted there as empty marked bars).

## Sean's judged tiles (`judged score` ... `judged_cross.py`)
`judged score` compares VERDICTS, and this change is EXPORT-only, so right/wrong/narrowed counts per verdict cannot move
(Litolff 157/30/7, Brahms 126/22/8, unchanged). What moves is whether a judged note REACHES THE FILE. Judged subjects in a bar that
was held and is now written red: **Litolff 24** (right 11 [9 READ, 2 GUESSED], wrong 3 [1 READ, 2 GUESSED], unscored 9, not_found 1),
**Brahms 29** (right 18 [15 READ, 3 GUESSED], wrong 8 [4 READ, 4 GUESSED], unscored 3). So the held bars carried 29 judged-right
notes into the file, and also 11 judged-WRONG ones (4 Brahms READ ones are rests/numbers Sean said were something else). Red marks the
bar, not those notes: that is the cost of "write it, don't hide it" and why the READ/GUESSED rows are kept per event.

## Known edges
* LilyPond barcheck: the 2 Litolff failures are bars with a fragment of a tuplet (the MusicXML count scales per head, the legacy
  Lily tuplet run groups differently), so the skip is mis-sized. Left, named.
* Pages: +22 / +42 pages. Part is simply more notes (+22% / +24%), part is the red words above every red bar and the "compressing
  over-full page" warnings (0 -> 6, 8 -> 33): the label is small and takes no horizontal room but it still adds height.
* MusicXML bracket in a two-voice red bar stops after voice 2, so it can end short of the bar's end. Cosmetic.
* MuseScore is not installed here; the import check is music21's (parses clean, no warning; irregular measures counted as expected).

## Files
`replay.py` (EXPORT replay, both arms), `show.py`, `pdfcheck.sh`, `import_check.py`, `acc_check.py`, `judged_cross.py`, `crops.py`;
crops `out/print/2.173/` (README says what red means). Tests `tools/omr/tests/test_staged_red_bars_2_173.py`.

## Second half: `OMR_WHOLE_NEEDS_HOLLOW_NO_STEM` (Sean 2026-10-19 "Do both")
Where: `rhythm.adjudicate_duration`, the final whole-class decision only (one block before the closing `head_and_marks` returns; 2.174's beam join,
`_beam_levels`, `head_and_marks` assembly untouched). Rule: a detector-whole box whose ink reads FILLED (`_reads_filled`, or the 2.148 interior
reading "black"), or that a stem touches (`own_stems`), abstains `whole_class_filled_or_stemmed` (unread, nothing invented). A box whose fill
was not read at all is not contradicted and stands. Default OFF (built; the landing agent flips it with 2.173). Tests
`test_staged_whole_needs_hollow_2_173.py` (6: filled no stem, stem through the middle, flag OFF = old whole, three controls).

Measured on the EXPORTED file, OMR_RED_BARS=1 both arms, ADJUDICATE..INFER re-decided over each whole 20261018-night record on this tree
(`rerun_whole.py`; the OFF baseline is the re-decision, not the stored export, which predates 2.170/2.17x):
| | OFF | ON |
|---|---|---|
| Litolff whole notes in the file | 2 | **0** (14 verdicts abstained) |
| Brahms whole notes in the file | 53 | **45** (31 verdicts abstained) |
| Litolff notes / red bars | 8,142 / 618 | 8,140 / 616 |
| Brahms notes / red bars | 14,987 / 890 | 14,981 / 882 |
All whole notes in both arms sit in red bars (55 of the coordinator's 56 reproduced). Crops: `out/print/2.173-whole/` (print only, every OFF whole).
* **Removed (Litolff 2, Brahms 8): none is a real whole.** Litolff: a filled quarter head with a stem; a stemmed head. Brahms: eight rest curls
  (quarter-rest lower curls, incl. tile 5's bar).
* **Still written as a whole, 45 on Brahms (hand look at every crop)**: about 30 are METER DIGITS (the loops of 9/8, 6/8), about 13 more rest
  curls, one chord cluster under slurs, one hollow dotted half. They are hollow and unstemmed, so this rule cannot see them: they need a
  different witness (digit ink / rest shape), which is NOT in this lane. 53 of 56 invented wholes -> 45 still there.
* **Real whole lost: none** on either plate by hand look; Sean's judged tiles do not move (Litolff right/wrong/narrowed 159/29/6 both arms,
  Brahms 129/22/5 both arms).
