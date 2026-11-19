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

## Research 2026-11-19: the single-stem note between double stems

Asked for by Sean (DECISIONS 2026-11-19, two lines: he does not know the answer; his fallback, if nothing is
found, is unison). A research agent's report, filed by the manager. Crops: `out/print/2.321-research/`.
**Nothing here is a page fact.** Who says it's right: the print for what is printed (the two ties); the
reference encoding (`library/reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl`, a MuseScore
file whose header names the same Breitkopf scan, IMSLP #317803) is ONE EDITOR'S READING; no printed player-2
part is in the library; no engraving manual was opened (Gould, Read, Ross, Stone: not reached).

- **No written rule found.** Opened: Wikipedia "A due", the LilyPond part-combining manual, one Steinberg forum
  thread -- none rules on a single stem with no "a 2". The rest were search summaries only.
- **Bassoons, Brahms bars 81-82 (tile 2):** two parts, then a dotted-quarter F and a quarter E-flat on a single
  stem under a slur, then split again; no "a 2", no "1.", no rest. The encoding gives both notes to BOTH
  bassoons. This is Sean's case.
- **Horns, bars 91-94 (tile 4 = bar 92):** the dotted quarters in bars 91 and 93 show ONE stem but TWO tie arcs,
  one above and one below -- two players holding the note (the print). The encoding gives both horns both notes.
- **Trumpets bars 90-93:** single stems with "a 2" printed at bar 89.
- **Tiles 1 and 3 (bar 87):** no single-stem unison there; an octave on one stem, then double-stemmed notes.
  The boxed bars go from single to split, the reverse of the tile question.
- **Tiles 5-7 (1st Violins, printed bars 365-367): ONE melodic line, not two parts.** A tie below plus a slur
  above on one note, and a stem that changes direction near the middle line. The "lower part stops with no
  rest" is OUR READER turning a tie plus a slur and a stem flip into two voices. The encoding writes one voice.
- **Signs on the page, as the agent puts them (its own knowledge, unsourced):** unison -- two ties or two slurs
  on the note, split stems resuming with no entry mark, an "a 2" in force; one player -- "1.", "Solo", "2.", or
  a rest for the other player. Divided strings: a single note is the whole section unless "div." is in force.

**Outcome:** the evidence leans to unison for wind pairs and agrees with Sean's fallback; it is not settled by
a rule. What would settle it: a printed Horn 2 or Bassoon 2 part for those bars, or the same bars in the
Simrock 1877 first edition (in the library, not examined). New fault found: a single line with a tie and a
slur and a stem flip is read as two voices (tiles 5-7).

## Correction 2026-11-19: tiles 5-7 ARE two voices (Sean)

Shown tiles 5-7, Sean: "All of those measures look like two voices. And it swapped the stems or goes from double stems down to single stems, I think mostly because of it not wanting to run into the slurs or ties. I think that's just meant to be tidiness for the engraving." So the "new fault" above is WITHDRAWN: the reader's two voices on Brahms
1st Violins bars 365-367 agree with him; the research agent's "one melodic line" and the reference encoding's
single voice were wrong for these bars. Lesson: an agent's look and an editor's encoding were both stated as
a finding before Sean had seen the tiles (rule 7: who says it's right). The day's rule (page-facts §1): in a
bar with more than one voice, a single note or single rest is unison unless a solo marking is printed.
