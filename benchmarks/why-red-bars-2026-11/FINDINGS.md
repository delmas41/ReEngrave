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

## 2026-11-23 -- overnight 20261122-night vs 20261117-night: why the red-bar count stood still (agent read, STAGED; not judged)

Sean: "why after all that our red bars number didn't move at all. I am guessing that is because of something later than the reader." Cause: red is decided at EXPORT (`export._bar_holds_out`, `_partial_bar_plan`/`_plan_one_stream`, `_red_bar_applies`) by plain addition against the meter, and the meter is right (Litolff 2/4 in all 339; Brahms 6/8 in 488). A held value makes a bar partial, never red, so red counts only bars where every mark was handed over as READ and one is missing, extra or wrong. Process lesson: reader work that turns unread bars into written ones feeds the red count unless the other marks in the bar are right too; red falls only by finding marks delivered confident and wrong.
- Churn (matched by page/system/staff/cell/part): Litolff red both 307, red->not 34, not->red 32; Brahms 435 / 57 / 57.
- Every mark READ with a pitch and still red: Litolff 238 of 311 (131 short, 107 long); Brahms 337 of 492 (146 short, 191 long). Two voices in only 21 / 19 of those.
- Refused or guessed upstream: Litolff 73 (`duration_narrowed` 10, `too_narrow` 9, `rest_stroke_into_a_head` 8, guessed 33); Brahms 155 (`too_narrow` 60, `duration_narrowed` 32, `one_ink_merged` rests 20).
- Arithmetic groups (which mark is at fault NOT established): Litolff motif bars, three eighths with the opening eighth rest missing, 52 bars, in 49 the detector drew no rest box; Brahms 54 bars short by half a plain note (missed dot?); Litolff 52 single-quarter bars, 16 heads measure hollow; long by one rest 25 / 63; long by one note 30 / 55.
- Brahms was classed from the exported file, not its record. Crops `out/print/overnight-1122-redbars/`; data in the session scratchpad `redbars/cls3.json` (not kept).
