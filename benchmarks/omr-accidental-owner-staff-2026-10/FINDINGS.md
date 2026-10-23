# 2.203 count: `owned_by_another_staff` accidentals, twin or no twin (STAGED, read-only)

Records: `*-whole-20261022-night.record.json` (Beethoven Litolff, Brahms Breitkopf). Script: `count_no_twin.py`
(streams `record.verdicts` + accidental `glyph_box`; live = not superseded). Twin = an accidental box in the OWNING
staff's same cell with IoU > `gather.CONTEST_IOU` (0.3), or `GLYPH_OWNER.detail.owner_box`.

| | Beethoven | Brahms |
|---|---|---|
| live `owned_by_another_staff` | 190 | 693 |
| no twin | 1 | 2 |
| twin, decided (reached a head on owner staff) | 142 | 509 |
| twin, abstained | 47 (one_ink_absorbed 32, no_candidate 9, ambiguous_height 3, owned_by_another_staff 3) | 181 (no_candidate 82, one_ink_absorbed 96, ambiguous_height 1, key_sig_marker 1, owned_by_another 1) |
| twin has no accidental verdict | 0 | 1 |
| GLYPH_OWNER tier: distance / range_veto / group_owner / hairpin_separates | 188 / 1 / 1 / 0 | 581 / 67 / 8 / 17 |
| GLYPH_OWNER tier: staff_band + staff_band_no_box | 0 | 1 + 19 |
| `ownership_undecided` | 2 | 6 |

Findings
- The premise is nearly empty: Beethoven has zero staff-band owners; Brahms has 19 `staff_band_no_box`, but 18 of those
  DO have an accidental twin in the owner cell that was decided, 1 abstained `no_candidate`.
- Cause of the label: `ownership._twin_on` keeps only `notehead*` GLYPH_BOX rows, so for an accidental glyph a
  `staff_band` ruling is always `staff_band_no_box`; the name is wrong for accidentals, the twin exists.
- True no-twin count is 3 (all tier `group_owner`). 
- Largest loss is not the no-twin case: 47/181 twins abstained, mostly `one_ink_absorbed` (another box of the same ink stands
  for it) and `no_candidate` (no head at the accidental's height in the owner cell).

My look (not Sean's; one 10-tile sheet, 600 dpi, box orange): the 3 no-twin and 7 `staff_band_no_box` Brahms cases. All 10 boxes
are real accidentals (flats, one sharp pair, one wide box of stacked flat/natural ink); the 7 staff_band cases each sit
beside the owner staff's head with the other staff's own copy printed nearby. The Beethoven no-twin tile is a dense
cluster where I cannot tell which staff's head it modifies.
