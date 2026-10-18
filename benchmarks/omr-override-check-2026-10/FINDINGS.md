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
