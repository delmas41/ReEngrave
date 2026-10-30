# ROADMAP 2.233 -- pitched heads not written: value undecided (STAGED)

Branch `lane-2.233-value-undecided` 18eb9d0db (two flags built, default OFF, NOT landed, NOT in the combined test). Written by the manager from the lane's report (the hook refused the lane's write).

## Cause and process lesson
1. The ranking row mislabels its unit: "pitched heads not written" = `dropped_unknown_duration` + `dropped_no_pitch`, and the first includes RESTS. Litolff sample: 111 of 308 are rests (96 `rest_stands_where_no_rest_hangs`, 15 `rest_slot_contradicts_class`; 12 cropped are all small black whole-rest bars -- the whole-rest family), 27 no_pitch; pitched heads 170 (21.2/pg). Brahms 303 heads (37.9/pg), 23 rests.
2. The pitched residue is what earlier lanes (2.146, 2.170, 2.81, 2.121) left; every bucket is an old case. The causes are UPSTREAM of duration: claim order and the stroke map, not the value rules.
3. Lesson (rule 7): split a count by what the unit is (rest, false box, head) before it opens a lane.

## Census (frozen-sample slices of 20261029-night re-adjudicated through INFER; heads, per page)
| bucket | Litolff | Brahms | cause from crops |
|---|---|---|---|
| beam_discounted_uncertain (bare stem) | 47 (5.9) | 164 (20.5) | Brahms 12/12 cropped are bare stems (unbeamed value); 97/164 dotted chord heads with a slur end or dot by the tip; the tip window reads "not clean" because ink another owner CLAIMED (dot, slur, accidental) sits in it |
| beams_ambiguous | 53 (6.6) | 59 (7.4) | Litolff 4/6 plain beamed eighths, 2 false boxes; second level only "possible" -> print is the lower level (4/4) |
| chord_value_undecided | 51 (6.4) | 54 (6.8) | heads of adjacent staves or a false box merged into one chord: `voicing.group_chords_in_measure` groups by x alone |
| no_pitch | 27 | 0 | not value |
| other small | 16 | 31 | |
| rests | 111 | 23 | whole-rest family |
Litolff narrowed heads by stems attached: stems 0 (25) mostly false boxes (4/6); stems 2 (19+) all one head shared by two voices (unison eighths, 2.75) -- so 2.204's one-stem-per-head stays parked.

## Built (OFF, recommend not landing)
- `OMR_UNISON_BEAM_TIPS`: reach zero (NOTHING CHANGED both plates); both readers miss the first stem's beam because the stroke map fuses head and stem.
- `OMR_TIP_WINDOW_FROM_STROKES`: fails -- Brahms right->wrong 2 (glyph/0/0/9/3/3, Sean "8"), flags +4 -37, red bars up on both; the stroke tip window is occupied by claimed dot/slur/accidental strokes.

## What a real fix needs (upstream)
- Tip readers honor claims: a stroke `Q.STROKE_OWNER` gave to an arc/dot/accidental is not a flag and does not make the tip "unclean" (claim order: "a later reader may mark claimed ink but never take it"). Result stays GUESSED (Sean's 2.81 pricing, bare-stem quarter 0.80-0.86).
- Stroke map: a beam group's first stem fused into its head must still read as joined to the beam (2.198 territory).
- Chord grouping by shared stem, not by x alone.
- Ranking: take rests and false boxes out of the row.
