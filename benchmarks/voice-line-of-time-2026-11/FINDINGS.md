# Voice model small test (ROADMAP 2.321), 2026-11-19

STAGED, EXPORT. Read-only. Filed by the manager from the lane agent's report (branch
`lane-2.321-voice-smalltest` 26ab52fbc, scripts in this directory on that branch). Frozen sample, the
20261117-night records replayed `--from adjudicate`, one plate at a time.

## Cause, and what it teaches

The manager's diagnosis -- the writer makes each player fill the bar -- is FALSIFIED on these pages. 2.314 r5
(ON) already writes one line of time per staff: a rest or single mark speaks for both players, `<forward>`
where a player prints nothing. What stops the remaining bars is upstream of the writer: a printed mark missing
from the record, neighbouring notes counted as one moment, and on Litolff a head with one stem given both an
up and a down event. Lesson: before redesigning a rule, check whether the code already runs it. And "two stems
at one place" is a poor way to find two-player bars: most bars it catches have one player.

## Population (code's count)

Bars with two stems at one place, or an up-stem and a down-stem event at one place.

| | bars | written split | flag-off writing, not red | flag-off writing, red |
|---|---|---|---|---|
| Litolff | 146 | 95 | 35 | 16 |
| Brahms | 33 | 30 | 2 | 1 |

No split bar is red. Decline reasons (code): Litolff `same_direction` 31, fuller voice does not come to the
bar 10, two events of one voice at one place 5, head on a dynamic letter 2, value not read 1, whole rest beside
notes 1, head on a whole-rest box 1; Brahms value not read 2, fuller voice 1. On Litolff 107 of the 146 bars
have no pair of separate stems; 169 of 170 up/down pairs are ONE head written as an up event and a down event.

## The looser rule on the 54 fallback or red bars (decided values only)

It would write 2 Litolff fallbacks (neither red) plus 3 that add up but hold a refused mark. Of the 17 red bars
it writes none. Causes of the 17, by the agent's look at each: a rest not in the record (eighth rest before
three eighths in 2/4) 5; a dot not read (Brahms) 1; neighbouring notes one head width apart counted as one
moment 3; a value misread 3; a value not read 2; another staff's heads or a dynamic letter counted as notes 3;
stem direction 0; the voice model 0.

## Stem direction

Code: Litolff 36 columns in 31 bars with two separate stems at one place read the same way; Brahms 0. Agent's
look at 20 (seed 2321): 19 are two notes one after the other in one voice, a head width apart -- not one
moment; 1 is a half note paired with a `pp` read as a head; 0 wrong directions. Sean's beam tile 2 bar
(Litolff 2/0/10/2) is not in this population on this record.

**Not checked, agent's look only (rule 7: check before it opens a lane):** of the one-head up-and-down pairs,
10 of 16 Litolff heads have only one stem on the page (mostly beamed eighths); 16 of 16 Brahms really have
both. If it holds, many of the 95 Litolff bars written split are one player's line written as a two-player
unison.

## Tiles for Sean (unanswered)

`out/print/2.321-voice-questions/` (7 tiles: Q1 tiles 1-4, Q3 tiles 5-7; Q3's three are consecutive bars of one
Brahms staff, p19 s1 st8 c3-5). `out/print/2.314-voice-questions/` holds 8 earlier tiles for Q2, Q4, Q5.
The agent's look crops: `out/print/2.321-our-look/`.

## Outcome

No redesign of the voice model. Open: whether Litolff gives a one-stem head two stems (a count to check before
any lane); the "one moment" width for neighbouring notes; the missing eighth rests.
