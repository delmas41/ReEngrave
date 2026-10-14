# ROADMAP 2.117 -- a bar that does not add up keeps what was read

2026-10-14, branch `lane-2.117-partial-bars` (code `f7e30768`), not merged. STAGED EXPORT only.
Written by the manager session from the lane's report (the lane's Write tool refused this file); every number
below is the lane's, from `OMR_PARTIAL_BARS=measure` / `=1` exports of the two `20261013-night` records.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* ASSUMED: in a bar that does not add up, the events from the opening barline up to the first refused glyph have
  certain onsets (prefix), and the events after the last refused glyph are anchored back from the closing barline
  when the meter is read or carried (suffix). Only the span between is unread.
* FALSIFIED BY: a note the detector never boxed standing ahead of a prefix event (its onset would then be wrong and
  nothing in the kept span can catch it -- the bar sum used to); or a refused glyph that is not where the gap is.
* NOT CONFIRMED with Sean: the look of the gap (red rest(s) + the word "unread"); the narrow gap definition.

## Sean, 2026-10-14
"I want to make sure that the measure math isn't keeping us from getting info. If we have a bar and know that there
is a quarter note in the measure on beat 1, I don't want that [lost] because we can't figure out beat 3."

## The rule (flag `OMR_PARTIAL_BARS`: off default / `measure` = plan + report, file identical / `1` = write)
* A gap is located only from the refused-glyph ledger + each glyph's box x. Owner copies and duplicate boxes are
  not gaps; a `too_narrow` refusal is (Sean read one as a real eighth rest).
* Prefix and suffix stop after an event whose duration was guessed.
* A bar with no refused glyph stays held: the missing note's position is unknowable.
* Over-full bars stay held: no witness says which duration is wrong.
* Encoding: MusicXML per voice = prefix notes, a red `unread` word, red rests cut into clean values, suffix;
  never `measure="yes"`. LilyPond the same with red rests + `unread` markup. Gap rows are counted under
  `unread_gap_in_partial_bar`, so `Unbalanced` still holds in both writers.
* Partial bars are reported apart from held bars and from `bars add up` (which passes them by construction:
  the red gap fills the bar, so it proves nothing about them).

## Measurement (`measure` mode, no effect on the file)
| | Brahms 317803 | Litolff 984073 |
|---|--:|--:|
| held bars that become partial | 765 of 1,822 | 156 of 861 |
| rows recovered | 1,920 of 6,192 (31%) | 265 of 1,973 (13%) |
| rows left in the red gap | 252 | 35 |
| meter read / carried (partial bars) | 597 / 168 | 156 / 0 |
| prefix-only / suffix-only / both | 301 / 392 / 73 | 64 / 86 / 6 |
| still held: over-full | 490 bars / 2,657 rows | 191 / 769 |
| still held: short, no refused glyph | 197 | 412 |
| still held: nothing before or after the gap | 370 | 43 |

A wider gap definition would plan 774 Brahms / 224 Litolff bars; the narrower one is kept.

## Export, flag on vs off
| | Litolff | Brahms |
|---|--:|--:|
| pitched notes written | 6,361 -> 6,573 | 9,148 -> 10,311 |
| held bars | 861 -> 705 | 1,822 -> 1,057 |
`Unbalanced` not raised; `bars add up` control unchanged (6,060 / 6,988 exact, 0 short, 0 over-full); both LilyPond
files compile, barcheck warnings unchanged (Litolff 0, Brahms 199).

## Tests
`tools/omr/tests/test_staged_partial_bars_2_117.py`, 12 tests (quarter on beat 1 survives; suffix anchored from the
barline; the gap is red/unread, never a plain rest; no locatable gap stays held; off == measure). Fast tier 7,783
passed before the last two logging edits; the new file, flag-triage and bar-sum tests re-ran green after.

## For Sean
`out/print/2.117-partial-bars/` -- 7 Brahms bars (beam-narrowed, too-narrow/clipped, suffix-only, prefix-only, one
that stays held), print beside our LilyPond bar; black = read, blue = guessed, red = the unread gap.
Open questions: (1) does red rest + "unread" read clearly (a red quarter-rest glyph can still look like silence)?
(2) a prefix assumes no missed note stands ahead of it -- write prefix/suffix notes plain, or blue?

## Sean's rulings 2026-10-14
*"Use a red bracket instead, write kept notes blue"* (on the two questions above). Changed, in BOTH writers:
* **The gap is a red bracket, not a rest.** MusicXML: a red `<bracket>` start/stop and a red `unread` word around an invisible `<forward>` of the gap's length (timing balanced, no `<rest>`, no `<note>`). LilyPond: an invisible skip `s1*n/d` under a red text-spanner bracket with `unread`. Counted still under `unread_gap_in_partial_bar`; `Unbalanced` unchanged.
* **Every kept event of a partial bar (prefix and suffix) is GUESSED, blue `#1F6FEB`**, rules `onset_from_partial_bar_prefix` / `_suffix` (stage EXPORT), counted apart in `report["guessed"]["by_rule"]`. A voice that adds up on its own stays plain; an event already guessed keeps its own rule. Kept rests are blue too.
* `acceptance.bars_add_up` now counts a bar with a `<forward>` as `partial_unread`, apart from `exact`.

Re-export (flag ON, same two 20261013-night records): Litolff partial 156 bars (65 prefix + 123 suffix blue events), held 861 -> 705; Brahms partial 765 (867 + 971 blue), held 1,822 -> 1,057. Guessed total off -> on: Litolff 1,527 -> 1,790, Brahms 1,034 -> 2,943; written notes + rests plain on = 5,734 / 11,393. `bars_add_up`: Litolff exact 6,060 -> 5,904 + 156 `partial_unread`; Brahms 6,988 -> 6,223 + 765; short/overfull 0. Both LilyPond files compile (barcheck warnings unchanged: 0 and 199). Crops re-cut (8 tiles, incl. one 2.5-beat gap).
