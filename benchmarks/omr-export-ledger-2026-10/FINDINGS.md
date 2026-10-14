# ROADMAP 2.122 + 2.123 -- the export ledger balances; a bar is named by where it stands

2026-10-14, branch `lane-2.122-export-ledger`. STAGED EXPORT. Records: the `20261013-night` Brahms and Litolff
records, re-exported on this tree. No flag; the MusicXML and LilyPond are byte-for-byte unchanged (only the report grew).

## 2.122 -- where the 92 went
Brahms: the record refuses 3,407 boxes `too_narrow`; `notes_not_written["not_a_notehead:too_narrow"]` = 3,315.
All 3,407 are `noteheadBlack*` boxes with a NOTEHEAD_CLASS; 3,315 have no other reading, **92 carry
`NOTEHEAD_IS_AN_EIGHTH_REST = True`** (ROADMAP 2.80b). `_place_notes` reinstates those as eighth RESTS (Sean, Brahms
Contrabass bar 13) and writes them, so they were in no ledger: not dropped, not a notehead. **They are not lost; the
ledger simply had no line for "refused, then written as something else".**
Fix: `_place_notes(reinstated=)` counts each by the refusal it overturns; report `part_join["refusals_reinstated"]`
(`refused_then_read_as_rest`, `placed_as_rest`, `dropped_after`). Brahms: 3,315 + 92 = 3,407 (record). Litolff: 0
reinstated, 258 dropped, unchanged. The regather report's cross-check now reads `record_refused == dropped + read_as_rest`.

## 2.123 -- bars named by (page, system, cell), not printed number
The exporter's held/partial lists already carried page/system/staff/cell, but the file-side consumer (regather_report)
joined them to the MusicXML on `(part, printed number)`. Brahms prints 189-190 twice (56 file bars on those numbers,
14 parts x 4), so a repeat was filed apart and "684 vs 683 unread-empty" appeared: **the exporter's 684 was right;
the report's file tally mis-filed one bar.** The unread-empty bars also had a COUNT and no list.
Changes (export.py): every bar entry (`bars_held_out_sum.held`, `partial_bars.bars`, `possibly_unread_mark.marked`,
new `unread_empty_bars.list`, new `bars_held_out_sum.held_doubled_staff_copies`) carries `bar_key` = `page/system/cell`
and `ordinal` = place among the part's `<measure>` elements in the file; `measure` stays as the printed LABEL.
`to_musicxml` RAISES `Unbalanced` if a list names a bar twice (part, staff, bar_key / ordinal) or a list's length
differs from its counter. The doubled-staff held copies (59 on Litolff) were counted but never named; now named.
LilyPond twin builds counts only, no number-keyed lists, so nothing there to re-key.
Consumer: `regather_report.read_musicxml` keys file bars by `(part, ordinal)` (number kept as label), `bar_states`
joins on ordinal (falls back to number for an old coverage file), adds the check "unread-empty bars named by the
exporter".

## Re-export, 20261013-night (this tree)
| | Brahms | Litolff |
|---|--:|--:|
| record `too_narrow` refusals | 3,407 | 258 |
| dropped + reinstated | 3,315 + 92 | 258 + 0 |
| unread-empty: exporter / list / file | 684 / 684 / 684 | 691 / 691 / 691 |
| file bars carrying `unread`: file vs (unread + held + held-doubled + partial) by ordinal | 2,506 = 2,506, sets equal | 1,552 = 1,552, sets equal |
| every listed ordinal's file `number` equals the entry's `measure` | yes (all four lists) | -- |
| lists unique on (part, bar_key) | yes | yes |

## Tests
`tools/omr/tests/test_staged_export_ledger_2_122_123.py` (10; the `_RED` ones fail on main: no `refusals_reinstated`,
`unread_empty_bars`, `bar_key`), the repeated-ending fixture of 2.85 reused (numbers 1,2,3,2,3,4 = six entries);
`test_regather_report.py` updated (repeat kept as its own bar by ordinal; cross-check with a control that can fail).
Pre-existing on main, not touched: 3 failures in `test_staged_export.py` (`..._PADDED_...`, two `measure_yes`).
