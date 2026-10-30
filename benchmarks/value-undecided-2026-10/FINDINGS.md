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

## ROADMAP 2.235 -- stem-tip readers honour the claims (STAGED ADJUDICATE; flag `OMR_TIPS_HONOUR_CLAIMS`, default OFF; branch `lane-2.235-tips-honour-claims`)
CAUSE. The 2.233 story ("a dot or slur end in the tip window makes the tip unclean") is true only in part. Of the 158 Brahms / 49 Litolff `beam_discounted_uncertain` heads (20261029-night sample, re-adjudicated on main with 2.232): 52 / 19 have no own stem (never reach a tip reader); the rest meet GATHER's tip window with the word `crosses_both_sides` (Brahms 55 of 104), `runs_on` 21, `no_room` 10, `occupied` only ~8, `head_at_this_end` 5. The window reads RAW RASTER INK beside the stem and cannot say whose it is, so a dot, a slur end or a neighbour's head beside the stem comes out as "ink on both sides / running on". The strokes `Q.STROKE_OWNER` decided to another mark answer exactly that. LESSON: the 2.233 census counted the claimed ink but never asked which GATHER word each tip carried; the word, not the owner, is the first split (rule 7). The first Brahms/Litolff runs of this lane also read the wrong tree (a census script carried another worktree's path): a script that inserts a path must be run with the tree it names.
BUILT. `rhythm._tips_honouring_claims` behind `_tip_obs` / `_tip_abs` (so `_stem_tip_flag_ink`, `_stem_tip_disputed`, `_stem_tip_unread_why`, `_no_beam_at_the_stem_tip`, hence 2.146 / 2.170 / the bare-stem ranking, all see it): a GATHER tip abstention whose word is in `TIP_CLAIMS_EXPLAIN` becomes a clean observation (`witness: claims`) only where, with strokes DECIDED to another mark left out (`_tips_from_strokes(ignore_owned=True)`), nothing stands at the tip and at least one stroke was left out. Contested or unclaimed ink, a hook, a beam, `head_at_this_end`, an unreadable stem: the abstention stays. No new cut-off. The verdict detail `tips_honour_claims` records, per head, GATHER's word, the owner families left out and what remains.
WHICH OWNERS (converted tips, sample): Brahms 85 tips (GATHER word crosses_both_sides 42, runs_on 23, occupied 7, no_room 7, ink_past_the_tip 4, ink_not_flag_shaped 2); owner families left out: head 60 (another head's blob), arc_trace 40, ledger 10, dot 9, mark 8, arc 3, accidental 2, word 1. Litolff 9 tips (head 9, mark 1, arc_trace 1). A tip GATHER called occupied/crossed whose strokes are clean with NOTHING owned there (8-10 per plate) is left alone: GATHER and the stroke map disagree about ink that nobody claims.
MEASURE (lane_report, 8 pages per plate, ON vs OFF with 2.232 in both): Litolff notes +5 -1, blue marks -3, red bars 201->199; Brahms notes +50 -2 (a note lost = a gained decided head now shares its x in a bar: `group_chords_in_measure` groups by x alone, the chord becomes `chord_value_undecided`; seen on p8 P4 m50, a real dotted half), rests +3, dots +35, blue 25 gained / 54 lost (50 quarter/eighth heads that INFER collapsed to blue are now DECIDED plain by 2.146 `stem_tip_reads_no_beam`), red bars 167->164, notes not written 3155->3104. Judged right->wrong 0 and unwritten->wrong 0 on both plates. Sean's tiles: out/print/2.235-tiles/ (key outside).
SAME BLIND SPOT, LEFT: (1) `Q.BEAM_STEM_LEVELS` (GATHER) counts runs at the tip from raster; not touched. (2) the dot-role reader (2.234) does not read `Q.STROKE_OWNER`. (3) `voicing.group_chords_in_measure` groups by x alone (now costs a note when a neighbour head becomes decided). (4) 52 of 158 Brahms narrowed heads have no own stem: a stem-finder question (2.204), not a tip one. (5) 2.146 writes a clean tip PLAIN: the 50 blue->plain heads are Sean's call (his 2.81 pricing says a bare stem quarter is 0.80-0.86).
