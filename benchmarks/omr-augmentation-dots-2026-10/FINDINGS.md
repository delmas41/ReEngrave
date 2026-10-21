# ROADMAP 2.180 -- augmentation dots (STAGED ADJUDICATE, measured on the exported file)

Branch `lane-2.180-augmentation-dots` off main 022bb99f5. Records `20261018-night`. Probes in `probe/` (x1 extract, x2 fates,
x3 Sean's p0 truth, x5 ghost heads, x6 unplaced, x7 note side, x4 look-sheets, replay/diff, 2.179-bar check, tiles).
Flag **`OMR_DOT_POSITION_OVER_WEDGE`, default OFF**.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* ASSUMED (page-facts 2.128, Sean "Always in a space"): an augmentation dot stands in a space right of its head; a staccato or
  staccatissimo stands above/below. A mark right of ONE head, in its augmentation window, at that head's own dot step (2.128
  positions, both known), with NO head above/below it, is that head's dot even when the 2.131 shape test calls it a wedge.
* FALSIFIED BY: Sean's tiles `out/print/2.180-review/` showing the changed notes are not dotted.
* NOT CONFIRMED. DECISIONS 2026-10-14 says "a wedge is never an augmentation dot"; these marks are round dots touching a staff
  line (2.133: the line's ink spoils the shape). A wedge that POINTS at a head is untouched.

## 1. What existed
2.12c role by position; 2.124 balance; 2.127 `OMR_AUG_DOT_JOIN` (ON); 2.128 `OMR_DOT_POSITION_JOIN` (ON); 2.131
`OMR_STACCATISSIMO_SHAPE` (ON; wedge test before the augmentation window, no head -> `wedge_without_a_head`); 2.151 (ON); 2.78
stem shares the dot. A read dot already reaches values set later: every narrowed candidate carries `dots`, and
EVALUATE/INFER/2.165/2.158 pick only among candidates.

## 2. Fates (step 1), every box with a `Q.AUG_DOT` row
| fate | Brahms (9,740) | Litolff (601) |
|---|--:|--:|
| (a) decided augmentation, applied in ADJUDICATE | 4,784 (+19 rests) | 14 (+2 rests) |
| (f) applied by a value set later (reconcile 208, chord mate 69, INFER bar 72, stem 2) / lost on a later value | 351 / 4 | 0 / 0 |
| (b) head duration abstained: 559 a ghost copy (owner copy dotted 455, narrowed-all-dotted 50, plain 10, not found 37) | 569 | 0 |
| (b) head narrowed: every candidate dotted (544 beam uncertain) / some dotted | 565 / 8 | 1 / 0 |
| (x) augmentation, head decided plain | 5 | 0 |
| (c) role abstained: ambiguous 482, wedge without a head 77, on a stroke 42, barline 8, wedge points away 5 | 614 | 142 |
| (d) staccato / staccatissimo | 2,704 / 116 | 442 / 0 |
| (e) chord/shared stem: carried by the stem value (2.78); 69 reach their note only via the chord mate | in a, f | -- |
The 2.167e "1,142 unresolved" are 1,066 dots that DO reach a dotted value (owner copy; or every candidate dotted, the note held
out for its BEAM) and ~60 that do not. Sean's Brahms p0 truth (131 dots): 125 applied, 4 narrowed-all-dotted, 1 abstained,
**1 never boxed** (unseen dots are small; 2.179's sample: 3 bars).

Crops looked at (mine, not evidence): Brahms ~250 (staccato 24+30: all real staccatos; ghost 18: 17 real dots carried by the
owner; abstained 84: ~1/3 real dots, mostly beside a note already dotted/narrowed, rest periods/stem ends/flag curls;
`wedge_without_a_head` beside a head 24+30: 21/24 and ~19/30 round dots on a line; plain-beside-dot other 23: ~8 dots, rest flag
curls). Litolff ~90 (staccato 24+30 all right; abstained 38: no dots -- f tips, slur ends, periods). Litolff has no wrong fate.
Note side: Brahms notes written PLAIN with a dot box beside them: 120 staccato (right), **39 wedge_without_a_head**, 12 ambiguous.

## 3. Biggest wrong fate, fix
A round dot touching a staff line reads as a wedge, has no head above/below, abstains, and its note is written PLAIN and READ.
`rhythm._wedge_beside_a_head` (from `adjudicate_dot_role`, where it returned `wedge_without_a_head`): one head of the staff left of
the mark in the augmentation window, mark at that head's dot step (position True) -> `augmentation`
(`beside_a_head_in_its_dot_space`, `position_admitted`). Two heads alike, a mark on a line, no position, or far right abstain as
before. `_attached_dots`: a position-only dot never makes a SECOND dot (the first ON arm double-dotted 5 Brahms notes).
Tests `test_staged_dot_position_over_wedge_2_180.py` (11).

## 4. On the exported file (replay ADJUDICATE..EXPORT of the night records, `probe/replay_2_180.py`, off vs on)
| | Litolff OFF | ON | Brahms OFF | ON (first arm, before the double-dot guard) |
|---|--:|--:|--:|--:|
| notes in file (pitched) | 8,525 | 8,525 | 15,015 | 15,026 |
| dotted notes | 21 | 21 | 4,780 | 4,819 |
| red bars | 636 | 636 | 860 | 844 |
| bars that add up (control) | 4,578 | 4,578 | 5,432 | 5,458 |
| dot roles changed | 0 | | | 60 (all wedge_without_a_head -> beside_a_head_in_its_dot_space) |
Litolff files byte-identical. Brahms durations changed 63: 40 longer (35 by one dot: 4->dotted 4, 2->dotted 2, 8->dotted 8;
5 double dots, removed by the guard), 18 same value / new decider, 2 narrowed->decided (meter reconciliation), 3 narrowed still;
0 shorter. Judged (Sean's tiles): Litolff 159/29/6/1/20/129 both; Brahms 129/22/5/0/19/191 both (no judged tile touches these notes).
Guarded ON arm re-run: `replay2` (see the ROADMAP row when it lands).

## 5. Lane 2.179's 24 "dot boxed, note written undotted" Brahms red bars (manager's check)
On 2.179's own base record (`probe/why2_2179_bars.py`): in those bars 25 of 28 decided augmentation dots ARE on a head decided
dotted (1.5 / 3.0, `dots: 1`), 3 on a chord narrowed for its beam with every candidate dotted. The red-bar row prints `type`
without the dot (`quarter` with beats 1.5 = a dotted quarter), so those bars are red for another reason, not a lost dot. Only 1 of
the 24 holds a `wedge_without_a_head` mark. File-level OFF/ON on that record: `probe/check_2179_bars.py`.

## 6. Tiles
`out/print/2.180-review/tiles/` (12: 9 notes the flag dots, 3 controls), README, key `_key/key.json`, one run, checked equal.
Fast tier 8,635 passed; `staged.check` 193.
