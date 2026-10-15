# ROADMAP 2.118 -- a detailed re-gather report, stage by stage

2026-10-14, branch `lane-2.118-regather-report` (code 1dc191d8), not merged. Written by the manager from the lane's
report (the lane's Write tool refused this file).

Sean, 2026-10-14: *"Our regather reports need to start becoming more detailed. We should have details like (but not
limited to). How many total bars, how many symbols of each kind, how much is unknown, unread, what is being held out or
guessed, how much certainty surround the guessing, and ultimately what happens to those numbers at each stage, including
export."* -- and, asked for suggestions, the manager added: run header, definition-of-done panel, cleanup cost per page,
per instrument, detected-then-dropped, one example key per top reason, regression guards, biggest movers.

## What was built
`tools/omr/staged/regather_report.py` -- a read-only derived module like `readout`/`trace`, registered in
`reach.NOT_A_STAGE` (product code, not a benchmark, because the overnight script calls it):
`extract` (record -> small facts JSON, so the Brahms record is loaded once), `build` (one movement), `night`
(both movements beside the previous night). Wired as a new LAST step of
`benchmarks/acceptance/overnight/compare_20261009.sh` (runs `check` + `regather_report night`; a failure there only
adds a README line); a test pins its position.
**Reused:** the exporter's own report, `Record`, `guess_of`, `trace.stage_of_decider`, 2.106 margins, `judged score`,
`check`. Partial bars and the blue kept notes (`onset_from_partial_bar_*`, 2.117) are their own rows.
**Computed here:** the per-symbol funnel (what ADJUDICATE said, then who settled it), margin bands, bar states per
part from the MusicXML, the movers.

## Imbalances found (findings, not typos)
* Brahms: the record refuses 3,407 boxes as `too_narrow`, the exporter drops 3,315 -- 92 unexplained. The other
  refusal reasons agree (23/23 Litolff, 24/25 Brahms).
* Brahms: the exporter counts 684 unread-empty bars, the file shows 683, plus 5 red bars on repeated bar numbers.
* Brahms prints bars 189 and 190 twice (endings); the exporter's held and partial lists are keyed by bar number and
  cannot tell the two apart.
* `dot_role_balance` reads `balanced: False` on both movements.
* 465 Litolff and 2,838 Brahms articulation boxes are kept but have no verdict at all.
* Row balance: Litolff 71/71, Brahms 71/73.
* LilyPond compiles on both; warnings Litolff 25 (previous night 30), Brahms 445 (previous 93).

## Headline numbers, 20261013-night (export re-run on the current tree)
| | Litolff | Brahms |
|---|--:|--:|
| bars plain / guessed / partial / held out / unread-empty | 3,559 / 949 / 156 / 705 / 691 | 3,853 / 625 / 765 / 1,057 / 683 |
| total bars | 6,060 | 6,988 |
| notehead boxes | 11,399 | 24,260 |
| noteheads refused | 1,549 | 4,635 |
| notehead length decided / narrowed / abstained | 8,190 / 343 / 1,317 | 13,535 / 3,027 / 3,063 |
| notes written (of which blue) | 6,573 (1,701) | 10,311 (2,077) |

## Tests
`tools/omr/tests/test_regather_report.py`, 11 tests (a funnel that balances; an imbalance that is reported; a guessed
symbol with its margin band; bars by state; a repeated bar number; the compare-script wiring). The 11 + the staged
check / reach / readout / wiring test files: 65 passed. **The full fast tier did NOT complete** (stopped at ~3% after
5 min) -- it must run before landing.

## Limits
* Only 408 of 31,768 Litolff refusals and 667 of 76,364 Brahms refusals carry a 2.106 margin, so "how close did it
  come" covers few refusals.
* "Guessed at glyph level" counts guesses in the record, including ones the exporter does not write.
* Held-out events per instrument omit bars on a doubled staff.
* `check`'s open count (192) is a tree number with no previous-night value.
* The record was gathered on ca46eae4; the export, LilyPond and report were re-run on the current tree; the previous
  night's side uses that night's own export.

Reports: `20261013-night/beethoven5-litolff.report.md|json`, `brahms1-breitkopf.report.md|json`, `check.txt`.

## 2.135 -- the balance row counted only the exporter's drops (STAGED, report only)
Section 9 row "refusal vs exporter drop" had `{"exporter dropped"}` as its only out, so a refused box that 2.80b then
wrote as an eighth rest (2.122, `part_join.refusals_reinstated`) showed as an imbalance. 20261014-night Brahms
`not_a_notehead:too_narrow`: record 3,407 = 3,315 dropped + 92 read as rests, printed IMBALANCE +92. The row now has
"read as rest" as its own part, and the section-5 line (which already used `agrees`) prints dropped + read-as-rest and the
same signed figure. Tests (`test_regather_report.py`): the Brahms-shaped facts failed before the fix (+92 printed); a box
that truly goes nowhere (3,407 / 3,315 / 0) still reports an imbalance. Re-rendered from the saved facts + coverage (no
gather): section 9 reads 77 of 77 rows balance. `check` open count unchanged at 192.
