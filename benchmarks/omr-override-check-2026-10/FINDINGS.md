# ROADMAP 2.165 -- one shared override check (Sean 2026-10-17)
(intended path: benchmarks/omr-override-check-2026-10/FINDINGS.md; the subagent harness refused to write a .md)

Path STAGED, all stages. Flag OMR_ONE_OVERRIDE_CHECK, default OFF. Branch lane-2.165-one-shared-check.
Measured at 49af4d6a = origin/main 09cabd92 + origin/lane-2.162-narrowed-bar-length 4a610224 (its flag OFF) + this lane.
Records: 20261016-night, both plates, whole records replayed through INFER from their GATHER rows (review.rerun,
pages_2_162 slices, no gather), one replay at a time. The base arm is the same tree with the flag OFF.

1. BUILT
- One guard in record.Log.record -> override_check.check(). TABLE has 44 rows, keyed by (stage, reading-order step)
  of the new verdict and of the one it supersedes, or, for a first verdict, the earlier step its reason overturns
  (IMPLIED_PRIOR).
- Rules a row may carry:
  * a later step only widens or confirms an earlier DECIDED value, and settles a narrowing only within it;
  * the stem may give a head its tip beams and dots, never overwrite its decided FILL (except a whole-class box);
  * EVALUATE only writes what is forced;
  * INFER never overturns DECIDED, and its result must be labelled inferred;
  * the bar sum only confirms; GUESSED exceptions are the 2.154 bare stem, the 2.158 lone event and the shared-stem
    majority.
- A refusal keeps the prior and is recorded as a near miss (Log.near_misses(), record "near_misses").
- An unknown pair raises UnguardedOverride under pytest; in a run it is refused as no_row. That happened 0 times.
- 2.162 helper:
  * r_bar_sum_known_length calls bar_length.bar_length(...).known;
  * bar_length.narrowed_bar_length_unknown() is True whenever the guard is on, so every bar consumer gets ranges;
  * the meter row raises if the helper is off.
- Shared stem (stem_value.py + share_stem_value):
  * a head's own reading is its decided FILL;
  * two fills that disagree, or any split other than all-but-one: stem_heads_disagree (NARROWED, nothing
    overwritten, EXPORT holds the heads out);
  * three or more with one dissent: stem_heads_one_dissent, GUESSED to the majority; every head on the stem is blue
    and the dissent is marked likely_misreading.

2. VIOLATION -> ROWS
- 1 -> bar_sum_confirms_only (+_step3/_dot/_stem/_stem_guess/_rest)
- 2 -> meter_bars_need_a_known_length + the helper hook
- 3 -> stem_value_over_a_head (+variants) + the shared-stem rule
- 4 -> export_never_writes_a_chord_mode (stem_heads_disagree held out)
- 5 -> export_never_judges_a_refused_carry (bars_meter_unread_carry_refused)
- 6 -> flag_never_reopens_an_open_head (open_head_kept_over_a_flag)
- 7 -> bar_sum_reinstates_only_in_a_known_bar
All 19 supersedes= sites have a row (a test derives the sites from the code).

3. REACH (refused attempts, Litolff / Brahms)
- bar_sum_confirms_only 72 / 120
- bar_sum_confirms_only_stem 0 / 1
- stem_value_over_a_head 4 / 14
- stem_value_over_a_step3_head 0 / 1
- flag_never_reopens_an_open_head 4 / 7
- no_row 0 / 0
- total 80 / 143
Shared-stem rule:
- stem_heads_disagree 61 / 32 heads
- stem_heads_one_dissent 24 / 12
- stem_value_from_evidence decided 126 -> 41 / 387 -> 343
The helper, switched on by the guard, restores the carried 6/8 on 6 Brahms systems the base refused (+3 relabelled).
Litolff meters are unchanged.

4. UNREAD vs GUESSED (Litolff / Brahms)
- notes changed: 153 / 384
- newly UNREAD: 61 notes in 30 bars / 40 in 23 bars (mostly stem_heads_disagree)
- newly GUESSED: 24 in 8 bars / 61 in 44 bars (Brahms: 49 downstream of the restored 6/8, 12 one-dissent)
- GUESSED -> READ (refused bar moves): 62 / 102
- UNREAD -> READ: 2 / 20

5. JUDGED (base -> on)
- right->wrong: 3, all bar moves Sean had judged right (2.154 L8, L11, B3)
- wrong->right: 3 (2.154 L14, L21, B13)
- narrowed->right: 3 (2.154 L12; 2.81 B08, B14)
- right->undecided: 0 in the scorer. At EXPORT, 1 glyph is held out: glyph/6/1/6/11/3 (2.70 t5 = 2.88 t12, "half").
- The alto clef boxed as a head (2.88 t5) goes wrong -> undecided.
- 2.78 t2 (three halves) stays right and becomes blue.
- One row was adjusted against a judged tile: whole_class_on_a_stem takes the stem value (2.78, Sean 2026-10-09;
  2.78-phase2 t11).

6. TILES
out/print/2.165-review holds 25 tiles: 23 changed (12 Litolff, 11 Brahms) and 2 controls; answers {}. The key is
out/2.165/tiles-key.json (uncommitted).

7. TESTS
- 32 tests in test_staged_one_override_check_2_165.py; 15 fail with the guard removed.
- Fast tier: 8473 passed, 0 failed.
- check: 192.

8. CONVENTION ASSUMED
- A head's own reading on a shared stem is its fill (beams and dots are the tip's, tiles 1 and 13). Falsified if Sean
  says heads that differ only in beams or a dot also can't be decided.
- Every bar move of a DECIDED value is refused, lengthenings included. This costs the 3 right moves above.

## 9. Sean's answers to the 25 tiles (2026-10-17)

Verbatim: "K- 1.trem slash 2.2 3.flag 4.2 half notes a third apart in one box 5.2 6.8 7.8 8.8 9.dot 4 10.2 11. Trem
slash 12.8 13.dot4 14.8 15.4 16.part of a c clef 17. Flag 18. Trem slash 19.2 20.2 21.trem slash 22.4 23.8 24.8  25. Dot 4"

Recorded in `out/print/2.165-review/answers.json`; the manifest now names each tile's glyph; the judged index is
rebuilt (1225 tiles). Scoring: `probe/answers_2_165.py`.

How each arm is scored (the standing duration in each whole-record replay at 49af4d6a):
* right: a value is written and it is Sean's.
* wrong: a value is written that is not Sean's, or any value is written on a non-note.
* narrowed_holding / narrowed_missing: nothing is written, and the candidates do / do not hold Sean's value.
* held out: nothing is written (abstained, or a `stem_heads_disagree` hold-out).

7 of the 25 tiles are not notes: tremolo slashes (1, 11, 18, 21), flags (3, 17) and part of a C clef (16). Tile 4 is
two halves a third apart in one box, a box-size problem.

### By cause (base -> on)

| cause | tiles | result |
|---|---|---|
| `stem_heads_disagree` | 4, 5, 16, 18 | 2 right halves -> held out (4, 5); 2 non-notes wrong -> held out (16 C clef, 18 slash). Better on non-notes, worse on notes |
| `stem_heads_one_dissent` | 2, 11, 19 | 2 right -> right (now blue); 11 slash wrong in both |
| `stem_value_over_a_head` | 1, 10, 21 | 1 slash wrong -> held out (better); 10 right half -> wrong (the refused stem value was right); 21 slash wrong in both |
| `stem_value_over_a_step3_head` | 12 | right eighth -> narrowed, missing it (worse) |
| `flag_never_reopens_an_open_head` | 3, 6, 17 | **worse on all 3.** 3 and 17 are flags boxed as heads: base held them out, on writes a half (wrong). 6 is a real eighth: right -> narrowed, missing it |
| `bar_sum_confirms_only` | 7, 8, 20, 24 | 2 wrong -> right (7, 20); 2 right -> wrong (8, 24) |
| `bar_sum_confirms_only_stem` | 15 | narrowed holding -> right |
| downstream (2.162's helper restores the carried 6/8) | 9, 13, 22, 25 | 3 narrowed holding -> right; 9 narrowed (missing it) -> wrong (Sean dot 4) |
| plain controls | 14, 23 | right in both |

### Totals

* **Notes (18):** base right 11 / wrong 2 / narrowed holding 4 / narrowed missing 1 -> on right 10 / wrong 4 /
  held out 2 / narrowed missing 2.
* **Non-notes (7):** a value written on 5 in base, on 4 with the flag on. Better on 3 (1, 16, 18: now held out), worse
  on 2 (3, 17: the flag row writes a half on a flag), wrong in both arms on 2 (11, 21: slashes).

### The open question: may the bar lengthen (or move) a DECIDED note?

4 of the 25 tiles depend on `bar_sum_confirms_only` (7, 8, 20, 24); 2 go right and 2 go wrong.

* **Tile 7:** the bar LENGTHENED an eighth to a quarter. Wrong; the guard keeps the eighth (right).
* **Tile 20:** the bar shortened a half to a quarter. Wrong; the guard keeps the half (right).
* **Tiles 8 and 24:** the bar shortened a quarter to an eighth. Both right (Sean 8); the guard keeps the quarter (wrong).

So on these tiles the one lengthening was wrong, and the two right moves were shortenings: a quarter with no flag or
beam made an eighth, which CLAUDE §4 forbids. The judged tiles in §5 split the same way (3 right moves lost, 3 wrong
moves stopped).

### What the tiles say about the rows

* `flag_never_reopens_an_open_head` (violation 6) is wrong on 3 of 3. The "open head carrying a flag" is a flag boxed
  as a head, or a real eighth. Keeping the open value writes a note that is not there. It should not be kept as built:
  the old narrowing (held out) was the better answer.
* Stem rows: Sean's halves on tiles 4 and 5 are held out, and the C-clef box and slash are held out too. The rule
  trades two right notes for two removed non-notes on these tiles.
* `flag` and the tile 4 answer parse as `other` in the judged index (`judged.py` maps no "flag" to `not_a_note`).
