# 2.291 — Why bars are red (2026-11-10)

STAGED, measure only. Branch `lane-2.291-why-red-bars` 641d48b2f. Written by the manager from the lane report (the lane's own Write was refused by a hook). Scripts are on the lane branch named below.

## Cause and process lesson
A red bar is NOT a bar with an uncertain value. It is a bar whose read events sum to the wrong length while no reader
flagged anything: `export._bar_holds_out` finds a voice sum off the meter; `_partial_bar_plan` / `_plan_one_stream`
find nothing to anchor a gap on (`voice_overfull`, `short_without_an_unread_symbol`,
`nothing_before_or_after_the_gap`); `_red_bar_applies` writes it red with every event it read. A narrowed value makes
a bar PARTIAL (blue + a red gap), never red. Lesson: we read the red count against the stage that names uncertain
values, but red bars are the opposite population — nothing was flagged — so no blue/narrowing work drives it down.

## Counts
Default pages: Litolff p1-2, 71 notes in 24 red bars; Brahms p0,4, 72 in 19. All saved pages: Litolff 623 notes in
191 bars; Brahms 672 in 155. Meter wrong: none seen. The lane's automatic families (`classify.py`): SHORT (a member
never read), LONG / LONG_FLAG (a value too long), VOICES, FALSE (a rest that is not one), TWIN.

## Sean's tiles (answers/answers-2.291-r1.json) — 11 of 12 bars answered
The families hold on 4 of 11 (tile 2 SHORT; 3 and 8 FALSE; 12 LONG) — **the lane's ranking is NOT confirmed**.
What the eleven bars are: ONE CHORD counted as two events — two heads on one stem or a second apart (tiles 7, 10,
11; a cause the lane did not name); a rest counted that is not printed (3, 8, and the 0.25 in 10); a printed eighth
rest never read (2); a value mis-read (1, 4, 12 — 12 is a flagged eighth read as a quarter); one bar read RIGHT and
red only for a phantom second voice (6); one undetermined (9). Both "two voices" bars he judged (1, 11) have one voice.
Tile faults on our side: boxes cut noteheads / held another staff's marks (4, 6, 11); an inset was mistaken for a tile.

## What follows
Chord grouping (two heads on one stem are one event) is the largest single cause in the sample and belongs at the
front of the notehead work; false and missed rests are the 2.288 lane's ground. Count the chord pattern across all
red bars before building.

## Not verified
Saved slices predate this week's landings; Brahms p4 system 0 is judged against a meter `derived_from_bars` (circular).
