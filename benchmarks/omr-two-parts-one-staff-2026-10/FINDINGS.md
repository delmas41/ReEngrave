# Two parts sharing one staff -- FINDINGS (ROADMAP 2.182)

STAGED ADJUDICATE (`rhythm.adjudicate_voices` -> `adjudicators/two_parts.py`; `family_precision._duplicate_box_refusal`) + EXPORT
(`export_two_parts.mark_voice_guessed`). Flags, both default OFF: `OMR_TWO_PARTS_ONE_STAFF` (A), `OMR_REST_CHAIN_KEPT_OUTRANKS` (B).
Tests `tools/omr/tests/test_staged_two_parts_2_182.py`. Probes `probe/`. Every right/wrong below is MY look at crops (ours, not evidence).

## 1. Two-voice rate, reconciled
2.167c (random 45 held bars per plate, whole movement): Brahms 3/45 = ~7% (1-18%). 2.179: 80/152 red bars on Brahms pdf 0,1,6,23,24,
pages picked for MOST red bars; 74 of the 80 on wind pages 6/23/24. 2.179's label counts two PLAYERS on a staff: of 8 of its `fv` bars
I looked at, 6 are ONE rhythm (two players as chords on one stem, red for another reason), 1 two rhythms, 1 unclear; only 27 of the 80
have both stem directions read. Two rhythms on one staff ~7% (2.167c) is the right figure.

## 2. Part A witnesses
After Sean's rules 1-3 leave a bar one line or abstained: (a) stems read both ways, every up-stem head above every down-stem head;
(b) all stems read one way, a non-whole/half rest displaced to the other side inside the staff, heads where one line would stem the
other way (a part of rests). Never with `a2` in the bar, never with a head >1 space outside the staff; unread stem -> nearer part by
height, blue `voice_guessed`. `1.`/`2.` are not read by any reader. A looser first version split 52 Brahms bars and made red 153->154.

## 3. Part B rest chain
Only boxes no OTHER rule refuses take part; same-class overlaps settled greedily. On 2.179's 35 `d` bars: 181 duplicate refusals,
104 with a kept rest on the ink, 9 true chains -- each then refused by the same other rule (same ink): 0 restored. The real loss is
58 rests / 28 cells refused as a DIFFERENT-class pair (rest8th vs rest16th/quarter, rule 8): a value question, not built.

## 4. Exported file, 20261018-night records, OFF vs ON
| | Litolff pdf 1,6,10,13,16 | Brahms pdf 0,1,6,23,24 |
|---|---|---|
| splits decided | 0 -> 2 | 0 -> 3 |
| two-voice bars written | 76 -> 78 | 20 -> 21 |
| red bars | 228 -> 227 | 204 -> 204 |
| bars that add up | 1179 -> 1180 | 775 -> 775 |
| rests restored | 1 (rests written 448 = 448) | 0 |
| notes in file | 3435 = 3435 | 4376 = 4376 |
2.179 labelled bars: fv red 78 -> 78, d red 33 -> 33: 0 of 75+35 now right. Judged: Brahms 73/12/4/0, Litolff 159/29/6/1, unchanged.

## 5. Tiles
`out/print/2.182-review/` (8: 5 splits + 3 controls), key `probe/data/tiles_key.json`, one run of `t1_tiles.py make 2182`, check passes.

## Caveats
Whole-movement replay stopped on request. Fast tier green (8658) before the last narrowing commit; staged.check 193. No default flipped.
