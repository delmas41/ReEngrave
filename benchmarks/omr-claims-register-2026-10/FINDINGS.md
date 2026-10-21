# ROADMAP 2.181 -- the claimed-area register: header column + clefs (plan 2026-10-20 §7 step 2)

Path: STAGED. GATHER `gather.gather_claimed_register` files `Q.CLAIMED_AREA` rows (owners `clef`, `leading_column`; 2.177 already files
`meter`), pure helpers in `staged/claims.py` (`claims.covering`; `reach.NOT_A_STAGE`), ONE consult `adjudicators/claimed_by.consult` in
`adjudicate_notehead_is_not_a_notehead` and `adjudicate_rest_is_not_a_rest`. Flag `OMR_CLAIMED_REGISTER`, default OFF.

## Design, in plain words

- A claim is one row on the STAFF: the area (page px), its owner, the read it rests on, its standing (READ / NARROWED), and, measured in
  GATHER, the share of every overlapping box's OWN ink inside the area (and, for the header column, whether that ink is a line running on
  past the box: barline / bracket / brace). GATHER decides nothing; no raster is changed.
- Owners: `clef` from a located clef (READ; the boxes it overrode are NAMED, 2.11's `is_a_clef` carried over); `clef` from a clef-sized
  detector `clef*` box -- READ only in a system's first bar (a system opens with a clef), NARROWED anywhere else (detector alone, 2.144);
  `leading_column` from just left of the staff's start to the first clef (own clef, else the narrowest clef offset of the system's other
  staves) -- a PRIOR per Sean 2026-10-20 ("idk possibly but not normally"); `meter` (2.177) read through the same consult.
- The consult: REFUSE (`claimed_by:<owner>`) on a READ claim holding >= 0.5 of the box's ink (meter / clef: not a stemmed head; clef: not
  where the detector scored the head above the clef box; column: only line-shaped ink and no stem). NARROW (`claim_narrowed:<owner>`,
  {notehead|rest first, the owner's ink}, written blue `#1F6FEB` by export) where a claim holds the box but cannot refuse it. Refusals sit
  where `is_a_clef` sat; narrowing only at the very end, so a shape rule's refusal is never lost to a narrowing.
- ON retires `is_a_clef`, `on_another_symbols_box`, `on_the_staffs_leading_barline`, the 2.177 `inside_meter` read and
  `rest_is_a_barline`'s leading (cell 0 left edge) case. OFF runs them unchanged.
- The first build made later-bar clef boxes READ at a bar's start (as 2.176 did). Litolff crops showed two real eighth rests and a slashed
  half inside such boxes being refused, so those boxes became NARROWED before the measurement below.

## Measurement -- 20261018-night records, flag OFF vs ON at main's defaults (2.177 ON), exported file (`replay_2_181.py`, `compare_2_181.py`)

OFF == main: the Litolff OFF MusicXML is byte-identical to the same replay run on an `origin/main` tree (`cmp`).

### Litolff
- Claims: 42 located clef, 308 clef READ + 52 NARROWED (detector), 331 header columns (309 own clef, 22 system), 12 meter.
- Heads refused by owner: clef 30, leading_column 26, meter 2 (none newly refused: every one was already refused). Rests: meter 4.
- Narrowed (written blue): heads clef 8 + leading_column 1; rests clef 2.
- Parity with the old rules: is_a_clef 30/30 -> claimed_by:clef. on_another_symbols_box 3 -> 2 still refused by another rule
  (nearer staff, duplicate box), 1 narrowed (a mid-bar F clef `14/0/3/12/4`, now written blue). on_the_staffs_leading_barline 1 ->
  narrowed (the bracket's beak `14/0/0/0/2`: the line test needs the stroke to run on past the box, and the beak is its end). 2.177
  inside_the_meter rests 4/4 -> claimed_by:meter. rest_is_a_barline leading case: 0 on the record (all 7 cell-0 refusals are at the
  right edge, unchanged).
- Real notes lost: 0 (no decided head newly refused). Notes in file 11,344 -> 11,346 (the two non-notes above, now blue).
- Newly blue (were plain): 7 heads + 2 rests, all looked at in crops. 5 heads and both rests look real (2.144's must-keep `9/0/3/11/1`,
  `16/1/7/2/6` among them); 2 are slashed halves. This is the cost of a NARROWED detector clef: real notes marked blue.
- Red bars 636 -> 641. 3 bars (`4/1/1/0`, `4/1/4/0`, `7/0/9/0`) had barline slivers move `too_narrow` -> `claimed_by:leading_column`,
  which export counts as positively identified (not an unread gap), so they leave "partial" (187 -> 184) and show red. 2 bars hold the
  two non-notes now written blue. Bars with events 5,054 -> 5,055.
- Judged (`judged score --doc litolff`): identical OFF and ON, 137/25/6/1/15/103.

### Brahms
(pending: ON arm running at the time of writing)

## Tests and checks
- `tools/omr/tests/test_staged_claims_register_2_181.py` (22): line test, column extent, standing, covering, GATHER rows, every
  refuse/narrow branch, stemmed controls, flag-OFF old rules, meter through the register, rests, export blue guess.
- Fast tier (before the standing change): 8,659 passed, 1 failed (`test_staged_check`, derived wiring; fixed after: a `.owner` token
  had closed a known gap). `staged.check` TOTAL 193, status ok.

## Tiles
`out/print/2.181-review/` (12: 9 register changes -- 5 heads and 2 rests now blue, 2 old refusals now blue -- and 3 controls, the first
note after a READ clef). Key `out/print/2.181-key.json`, made by the same `tiles_2_181.py` run and asserted equal. Litolff only (Brahms
ON was still running). Question: "is the thing in the blue box a note, or what is it?"
