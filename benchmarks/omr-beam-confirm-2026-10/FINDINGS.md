# ROADMAP 2.121 -- confirm the beam on a beamed note's stem (2.119 twins split A)

2026-10-14. STAGED. Diagnosis read off the 20261013-night records, the 2.119 `pairs.csv`/`analysis_ranked.json` and Sean's hand truth
(Brahms 317803 pdf 0, `data/hand-truth/pages/imslp317803/0.json`, which boxes beams, flags, stems, slurs, ties). Scratch scripts were lost
in a reboot; the method is stated so it can be redone.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* Convention: a slur or tie is not a beam (Sean 2026-10-09, "a beam never has an arc"; thinner than any beam). A stem with no beam and no
  flag is its head's own value. Falsified by Sean answering "eighth" on a changed tile. NOT CONFIRMED by Sean; default OFF.
* Truth class of a note = Sean's stem box touching the head, then a beam box over the stem's x/y (beamed), a flag box at its end
  (flagged), else bare. Pairing is geometric, not his own statement.

## 1. Diagnosis: the brief's premise is mostly wrong
Of the 24 missed notes of split A (Brahms p0), by Sean's own boxes: **19 bare (no beam, no flag), 4 beamed, 1 flagged.** The twins
differ from the missed notes in more than the head: 11 of 24 twins are beamed, 9 bare, 4 flagged.
* **19 bare stems (the quarters): the "beam" boxes beside them are slurs and ties.** The ink reader was right to refuse them
  (`too_thin` 10 notes; the 2.25b decided-arc discount 10; overlapping). Of the detector `beam` boxes near these stems, 9 match a truth
  slur at IoU >= 0.84 and the rest are tie fragments; none matches a truth beam at the stem. The narrowing stood only because 2.74/2.25b
  rule 8 will not turn a refusal into an unmarked note. Crops (drawn: head red, detector beam boxes green, slur/tie boxes blue) showed it.
  The twin that was written had no such box in its stem's beam zone (`yolo_kept` 0).
* **4 truly beamed**: 2 with no stem found at all (`no_stem`, `beams_ambiguous`: q110/q118, the fused-column stem finder, 2.82/2.83's
  open item); 2 `beam_certain_not_joined` (q93/q86; a long stem, the beam read, the join not witnessed). Not a beam-reading fault.
* **1 flagged** (q1009): a flag the tip reader did not see (`flag_ink_unread`).
* Whole page: of 52 truth-matched `beam_discounted_uncertain` narrowings, **51 are bare stems, 0 beamed**, 1 no stem.
So "confirm the beam" would make eighths out of quarters. What is missing is a positive reading that the refused strokes ARE slur ink.

## 2. The fix (default OFF, `OMR_ARC_INK_NOT_BEAM`)
* ADJUDICATE (`rhythm.adjudicate_duration`, `beam_discounted_uncertain` branch; new `_refused_stroke_facts`): files per refused stroke
  what it was refused as (`arc`, `ink:too_thin|bowed|one_stem|through_heads`, `neighbour_staff`, `far_side`, `beyond_stem`) and whether
  it stands at the stem tip. Detail only; no verdict changes.
* INFER `collapse_arc_ink_not_beam`: collapses to the head's own unbeamed candidate only where the own stem is seen, no beam/flag/level
  stands on it, the tip window reads clean, and EVERY refused stroke is `arc`, `too_thin` or `bowed`; an ink-shape refusal at the tip
  declines (2.81: where a refused real beam stands); `one_stem` (2.82), `through_heads`, neighbour/far/beyond decline. No bar arithmetic.
  ONE witness (the decided slur glyph and the ink test read the same ink), so the result is GUESSED (blue) with both candidates.
  It never makes an eighth, never shortens a note.
* 25 tests (`test_staged_arc_ink_not_beam_2_121.py`): positives from the real q1319/q1272 shape; controls for each refusal kind,
  tip unread / hook, no per-stroke facts (old records), real-beam and flag reasons (q93, q1009), decided duration, default OFF + typo.

## 3. Measurement (one gather = the record's own GATHER rows, re-decided on this tree, flag OFF vs ON; Brahms pages 0-1, Litolff 0-3)
* Brahms: 19 durations change narrowed -> decided by the rule, **no other verdict quantity differs**. 7 are on Sean's page 0 and
  truth-matched: **7 of 7 bare (0 quarters-that-are-eighths)**; they are split-A notes q412 q1278 q1277 q419 q414 q1272 q418 (7 of 24
  collapse; the rest decline on tip not read clean / ink-shape refusal at the tip). Values: 4 dotted quarters, 2 quarters, 1 at 1.75
  (double dot -- to look at in the tiles). Notes written 642 -> 645 (all 3 blue), guessed 137 -> 135 (changed bar sums), bars held 63 -> 63;
  noteheads in held bars 396 -> 409: 16 of the 19 collapsed notes sit in bars that stay held (the cascade, 2.119 B/D), so the
  yield in written notes is small.
* Litolff: 1 duration changes; bars held 69 -> 70, notes written 872 -> 872 (that bar now holds an event that fails its sum).
* Re-run after the reboot (one gather re-decided, flag OFF vs ON, same slices): identical numbers (Brahms 19 changed, Litolff 1).
* `judged score` over the Brahms pages 0-1 slice, OFF vs ON: right 48 -> 51, wrong 5 -> 5, narrowed 11 -> 8 (no regression).
  `staged.check` TOTAL 192 (= main). Fast tier on the branch before the merge: 7,872 passed, 1 failed (the stale judged index, fixed on
  main 88391a63); the 2.121 tests + the flag/infer/judged-index tests after merging main: 96 passed.

## 4. Sean's yes (2026-10-14) and blind tiles
Sean said yes to building the tiles and to recording this fix as the actual 2.121. 15 tiles in `out/print/2.121-review/` (13 notes whose value
the rule changed: 7 on page 0, 5 on Brahms p1, 1 Litolff; plus 2 controls Sean's own boxes call a beamed note (tile 10) and a flagged note
(tile 6), both left narrowed by the rule). Nothing drawn but a small red corner bracket; the question is "what is this note's value?
(quarter / eighth / other)"; the key is `tiles_MANIFEST_HIDDEN.json` (do not show it). Tile 12 is the one at 1.75 beats (two dots): the
rule picks the head's own unbeamed candidate, so the dot count is the dot reader's; it needs a look.

## 5. Split out (a separate item; the manager claims the number)
The other 5 of the 24: q110/q118 (`beams_ambiguous`, NO own stem found: the fused-column stem finder, 2.82/2.83's open item); q93/q86
(`beam_certain_not_joined`: beam read at `levels_certain` 1 with `certain_conflicts` 1, join not witnessed, long stem); q1009
(`flag_ink_unread`: a printed flag the tip reader did not see). None is a slur case; this rule leaves all five narrowed (tested).
