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

## 2026-11-23 -- the missed motif eighth rest (small test, Litolff, STAGED; agent read, sheet not yet judged)

Cause: the detector DOES box the rest, as the wrong kind, and that box takes the rest's ink. Of the 52 red three-eighth bars: 26 carry an `accidentalDoubleSharp` box on the rest's ink (kept by ADJUDICATE `adjudicate_accidental_is_not_an_accidental`), 5 a `clefF` box, 5 are near-misses of the 2.99 ink rest reader `adjudicate_unboxed_ink_is_a_rest` (`max_column_share` 0.93-0.97 against 0.92). The ink measures like rests we read (width 1.39, height 2.28 against 1.39 / 2.29); 2.99 steps aside on `already_read_as_a_glyph`. 47 of Litolff's 82 double-sharp boxes are this size and place. 2.192's `on_a_rest` fires only when a rest box also stands there. Miss rate about 16-21% (199 motif bars written right). In a random 15, 4 are not the motif. Brahms: 84 red 6/8 bars short by one eighth, not checked. Process lesson: "no rest box" measured the wrong thing; ask what box stands on the ink. Sheet `out/print/overnight-1122-rest8/contact-sheet.png`.

## 2026-11-23 -- 2.334 built OFF (`lane-2.334` 186ec0615, `OMR_REST_BOXED_AS_OTHER`, STAGED ADJUDICATE)

Cause: the 2.99 ink rest gather (`gather_unboxed_rest_ink`) always measured these rests; its coverage test counted ANY detector box as "already read", whatever its kind, and nothing at ADJUDICATE refused the double-sharp box; a `clefF` box was also taken at GATHER as the bar's opening clef. Lesson: coverage that ignores box kind lets one wrong label silence a correct ink reader. Rule: a mark with an eighth rest's shape standing alone in the staff is an eighth rest whatever the detector called it; never a sharp/natural/flat (full-height stroke on the left), never a real double sharp (a small x about one space tall), never a clef (taller or wider). Both sides of the unchanged 2.99 eighth windows: Sean's judged claim tiles 7/7 eighth rests pass, 0/13 sharp/flat/natural pass; Litolff whole movement 0/59 real-accidental-boxed inks pass, 42 double-sharp-boxed and 14 clefF-boxed pass; Brahms 6/1,045 pass (agent's crops: all six are eighth rests), 205 double-sharp-boxed and 3 clefF-boxed pass. No real double sharp on our plates (that side rests on the size convention). Change: `adjudicate_accidental_is_not_an_accidental` refuses with `eighth_rest_shaped_ink`; the 2.99 reader then reads it once. Frozen sample, re-adjudicated 20261122-night (control reproduces): Litolff rests +16, red 153 -> 139 (15 cleared, 1 new); Brahms rests +9, one phantom flat gone, red 130 -> 126; judged right->wrong 0, wrong->right 1. The 5 `max_column_share` near-misses are rests printed shorter (1.8-1.9 sp); cut unchanged. Brahms 6/8 bars short by one eighth: 80, the same wrong-kind box in 23. Not run: `judged_claims`, fast tier. Sheet (manager looked: all 12 are eighth rests, our look): lane worktree `out/print/2.334-rest-boxed-as-other/contact-sheet.png`.

## 2026-11-23 -- the other red-bar groups, from the record (small test, 20261122-night, STAGED; agent's look at crops, not judged, except where Sean's tiles are named)

Cause across all four groups: a box of the wrong kind is trusted, and a box of any kind blocks the reader that would see the mark rightly; almost never a chord counted twice. Lesson: ADJUDICATE asks "is this that kind?" and never "what else could this ink be, judged by where it stands?"; 2.334 fixed that for one shape only.
- Too long by one rest. Litolff, all 25: in 17 the extra rest is not a rest -- 12 accidentals boxed as rests (10 sharps as 16th/32nd/quarter rests, 2 key-change flats), 2 letters, 2 stem or arc, 1 ink written as rest and head; all kept by `adjudicate_rest_is_not_a_rest`; 6 real rest with a wrong note; 2 unsettled. Brahms, seeded 16 of 63: 8 an eighth's flag never read, written quarter (`rhythm.adjudicate_duration` has no flag box and `_stem_tip_flag_ink` runs only when `beam_evidence == "none_over_this_note"`; these cells say `reader_declined`, the 2.318 r6 gate); 3 a stem+flag boxed as a quarter rest; 5 other.
- Too long by one note, seeded 12 per plate: Litolff 10 false heads (5 stemless on dashes or arc ends, 2 on a sharp or dynamic, 3 on rest ink), 1 two voices as one, 1 missed beam; Brahms 7 false heads (accidentals, letters, a clef, a ledger fragment), 2 two voices as one, 3 other; kept by `adjudicate_notehead_is_not_a_notehead`. No chord counted twice in either sample.
- Litolff single-quarter bars, all 52: 16 are half notes -- `gather_head_ink` reads them hollow, but `_head_ink_reads_hollow_unread_black` applies only to boxes not head-sized, so the 2.148 first read stands and the note is written a quarter, READ. 32 have a printed quarter rest never written: 21 boxed `arpeggiato` (2.99 steps aside, `already_read_as_a_glyph`), 8 under ledger-line boxes, 2 twin rest boxes both refused, 1 boxed as a bass clef.
- Brahms short by half a note, seeded 15: 8 a printed dot not read (5 with no box, ink 0.5-0.65 sp, 0.2-0.4 sp right of the head; 1 boxed double sharp; 1 joined to another head; 1 role ambiguous); 5 a printed eighth rest not written (2 double-sharp boxes = 2.334; twins refused; clef header; claimed by a word). `OMR_DOT_BY_HEAD_INK` re-measures only boxed dots.
- Sean's judged tiles in these bars: m118 his quarter rest written a half note; m168 a head on the `f` written a half ("not a half"); m169 his half note written a quarter; m154 his second-voice whole rest written a quarter note.
Sheets `out/print/overnight-1122-longbars/`. ROADMAP 2.339 (rests hidden by another box), 2.340 (accidentals boxed as rests or heads), 2.341 (hollow heads and unboxed flags).

## 2026-11-23 -- 2.339 built OFF (`lane-2.339` a64cd4d11, `OMR_QUARTER_REST_BOXED_AS_OTHER`, STAGED ADJUDICATE)

Cause: the quarter-rest ink was measured all along by the 2.99 gather; three kinds of box blocked the reader -- an `arpeggiato` box no decision ever refused, small in-staff ledger boxes ("claimed by another class"), and twin rest boxes of different classes both refused by 2.15. Lesson, as 2.334: a box whose kind nobody judges still claims the ink. Rule: a mark with a quarter rest's shape standing alone in the staff is a quarter rest whatever the detector called it; never a real arpeggio (ink immediately left of a head at its height stays unread; control Litolff 11/1/9/9), never a flag box, never a ledger box its own decision kept. Written GUESSED (blue): one real sharp on Brahms p19 boxed as a flag passes the quarter shape test, so shape alone does not settle it. Both sides: standing restQuarter inks pass 642/720 Litolff, 987/1,138 Brahms; Sean's judged quarter rests 5/7; his 13 judged accidentals 0; flag-boxed inks 3/72 (2 quarter rests, 1 sharp); Brahms `arpeggiato` boxes 1/27. No real arpeggio seen on either plate (agent's look). Frozen sample, re-adjudicated 20261122-night: Litolff rests +4 blue, red 139 -> 135; Brahms rests +1, red 126 -> 125 (Brahms control line differs on 4 of 12,350 verdicts in both arms: main moved since the overnight); judged right->wrong 0. Side run Litolff p4, p7, p15: +14 blue rests, red 90 -> 77; in 7/0/8/6 `reconcile_duration` then rewrote the next note eighth -> quarter, blue. Not fixed: twin 7/0/4/3 (left edge fills a column, read as a flat's stem), twin 10/0/1/7 (tie boxes cover 45%), 10/0/3/7 (the real clef covers 40%); Sean's m118 rest not traced. Sheet `out/print/2.339/contact-sheet.png`.
