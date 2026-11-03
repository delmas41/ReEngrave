# 2.257 — The viola C clef and the whole rest on its own staff (STAGED; Sean "Open both", 2026-11-03)

Lane `lane-2.257-cclef-rest` 95266e0c7 (Sonnet). Flags `OMR_C_CLEF_READ`,
`OMR_WHOLE_REST_OWN_STAFF`. Written by the manager from the lane's report (a hook
refuses report files from subagents).

## Why it was opened
Blue-note census (20261031-night Litolff frozen 9 pages): 214 blue notes from INFER
`fill_clef_gap` on 6 staves; 27 heads unwritten for `no_pitch` (page 4); 96 clean
whole rests refused `rest_stands_where_no_rest_hangs`.

## Causes and process lesson
- **Whole rests -- NOT the wrong staff** (the census guess was wrong). Of 156
  refused rests on 9 Litolff pages none lands in the whole-rest band on any staff;
  against their own staff's lines 82 hang from a line, 29 stand on one, 45 neither.
  They are displaced second-voice rests. The slot test asks one absolute height
  (the 4th line) of a convention that is "hangs from a line".
- **Clefs:** of 80 clef verdicts 5 narrowed, 4 filled blue. 4/0/9 and 6/1/9: the
  detector boxes the clef ink as a 4.3-4.5 sp `noteheadBlackOnLine`; the 2.11
  override refuses a clef-sized box, the locator goes silent, INFER fills.
  6/1/3: a real WRONG fill -- a tenor clef (locator 2 x 0.95) tied 5.5:5.5 with a
  bass clef 81 sp along the system (a 2.251 mid-system change voting at the
  header), filled bass. 4/0/8 and 4/1/10: fills correct, untouched.
- **Lesson:** each veto was fitted on one plate and nobody asked what a staff's
  first ink is; the slot band fitted on Sean's ten rows became a refusal.

## Fixes
- `OMR_WHOLE_REST_OWN_STAFF` (`adjudicators/rhythm.py`): a restWhole hanging from
  one of its own five lines is read whole.
- `OMR_C_CLEF_READ` (`clef_locator.py` GATHER + `adjudicators/clef.py`): a
  clef-sized notehead box in the clef slot no longer vetoes the locator; a clef box
  beyond 45 sp no longer votes on the header.

## Three measures (both arms on the merged tree)
- WHOLE_REST, Litolff p4/6/8: rests +31, blue -2, notes not written 1039 -> 1008,
  **red bars 97 -> 124** (27 of the 31 new rests share a bar with the other voice's
  notes; the voices stage does not take a displaced rest as its own voice).
  Brahms p5/8: rests +1, red 69 -> 70. Judged right->wrong 0.
- C_CLEF, Litolff p4/6: `fill_clef_gap` blue 79 -> 26, notes +27 -25, pitches ~41,
  blue +6 -83, beams -14. Brahms p5/8: pitches ~15, clefs -3, keys -3 (15 unjudged).
  Judged right->wrong 0.
- Unwritten->wrong 0 on both flags and plates.

## Sean's tiles (2026-11-03; answers-r1.json)
"1-2. Whole rest in second voice 3.box around F clef ( also gets one of the key
flats) 4.whole rest 5. C clef 6. Whole rest in 2nd voice 7. Orange box around a
half note, stem and an accidental 8. C clef 9-10. Whole rest on second voice
11-12. C clef"
- Rests 1, 2, 6, 9, 10 (ON whole, OFF refused) right 5/5; control 4 right.
- Clefs: control 3 (bass fill) right (tile box too wide, catches a key flat);
  control 8 C clef right; changed 5 (alto), 11 and 12 (tenor) right -- the line
  checked by the manager on the print: 5 centred on the middle line, 11 and 12 on
  the 4th line.
- Tile 7 (control, staff/4/0/3, box x 1133 mid-system): a FALSE CLEF ON MAIN -- a
  half note, stem and accidental read as an alto clef (2.251 page-wide claim).
  Open under 2.251, not this lane.

## Decision
Sean "Land whatever is ready": `OMR_C_CLEF_READ` lands ON; `OMR_WHOLE_REST_OWN_STAFF`
stays OFF until round 2 (the voices stage takes a displaced second-voice whole rest
as its own voice, so the bar adds up instead of going red).

## Not established
The 27 lost / 25 gained notes under C_CLEF not inspected one by one; page-4
`no_pitch` heads not re-counted by cause; the hang tolerance is not skew-corrected.
