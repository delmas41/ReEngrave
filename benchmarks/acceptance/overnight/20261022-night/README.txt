compare 20261022-night vs 20261020-night, tree a2eae688030feebf177a40e2b0f2404dafd61f28 start 2026-10-23T15:10:40Z
beethoven5-litolff: readout diff exit 1
brahms1-breitkopf: readout diff exit 1
done 2026-10-23T15:44:19Z

== Manager summary 2026-10-23 (main a2eae6880, through infer; first whole-movement run with 2.186 one ink one mark, 2.190, 2.192, 2.193 ON)
Acceptance (vs 20261020-night):
  Litolff notes reaching file 8887/11797 -> 8887/11797 (0.753 -> 0.753); held-out bars 0 -> 0; red bars 508 -> 507; bars add up 4834 -> 4835; unread bars 529 -> 529
  Brahms  notes reaching file 15165/24375 -> 15174/24375 (0.622 -> 0.623); held-out bars 0 -> 0; red bars 650 -> 628; bars add up 5749 -> 5786; unread bars 349 -> 349
  (noteheads logged unchanged, 11797 / 24375; a first-two-stages diff shows ONLY the accidental family moved on Litolff -- every other family matched 1:1)
Sean's judged tiles, SAME current index on both records (right/wrong/narrowed):
  Litolff 159/32/6 -> 159/32/6 ; Brahms 142/21/5 -> 142/21/5   (no judged answer moved; the tiles do not cover accidentals, so this says "nothing judged got worse", not "accidentals are right")
Wall: Litolff 66 -> 67 min, Brahms 233 -> 224 min.
Accidental census (exporter, coverage.json accidental_reading), old -> new:
  Litolff  heads_contradicted 74 -> 3 ; applied (printed accidentals written) 460 -> 521 ; owners decided 664 -> 570 ; heads owned 558 -> 543 ; owners sharing a head 106 -> 27 ; unowned 37 -> 36 ; no_candidate 702 -> 372
  Brahms   heads_contradicted 740 -> 24 ; applied 2544 -> 3102 ; owners decided 4439 -> 3504 ; heads owned 3489 -> 3366 ; owners sharing a head 950 -> 138 ; unowned 205 -> 240 ; no_candidate 1786 -> 677
  new reasons (2.186): Litolff owned_by_another_staff 190, one_ink_absorbed 222, ownership_undecided 2 ; Brahms 693 / 1182 / 6
  pitches altered by the key 2525 -> 2434 (Litolff), 5875 -> 5251 (Brahms); carried_in_bar 162 -> 177, 633 -> 782

Surprising / worse:
  - NOTHING in the three headline measures or the judged tiles got worse. Litolff is flat to the note (8887 both); Brahms +9 notes, +37 bars add up, -22 red bars.
  - PARTITION BROKEN: the census `unaccounted` was 0 on both plates and is now 14 (Litolff) and 176 (Brahms). Those are exactly the `on_a_rest` abstention counts (14, 176) in this run's summary: a reason the exporter's accidental partition does not list, so the partition control no longer balances. heads_balanced is still True. Needs a one-line add to _accidental_census; the glyphs are abstained, not lost.
  - Fewer accidentals DECIDED (664 -> 570, 4439 -> 3504) yet MORE written (+61, +558): the glyphs dropped are duplicates of one ink (heads_contradicted 74 -> 3, 740 -> 24), so the head that was contradicted (writes nothing) now gets one answer. That is the intended effect; but 222 + 1182 glyphs now abstain `one_ink_absorbed` and 190 + 693 `owned_by_another_staff` -- no Sean tile has checked either.
  - Pitches altered by the key fell (-91, -624) and carried_in_bar rose (+15, +149): bars that had a contradicted accidental now carry a printed one forward. Not checked against the print.
  - Wall: Brahms 9 min faster, Litolff 1 min slower; no change worth reading into.
Fix e040a950f: accidental census now counts on_a_rest (unaccounted 0 on Litolff record; was 14 Litolff / 176 Brahms).
