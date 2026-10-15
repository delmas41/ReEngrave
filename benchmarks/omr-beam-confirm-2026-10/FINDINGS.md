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

## 6. Sean's answers (2026-10-14, recorded `out/print/2.121-review/answers.json`) and the landing
Sean, verbatim: "1-5. Dot 4 6.8 7.2 8-9. Dot 4 10.8 11-15. Dot 4" -- tiles 1-5, 8-9, 11-15 dotted quarter (1.5); 6 and 10 eighth; 7 half.
Scored against `tiles_MANIFEST_HIDDEN.json` (manager's read, verified against the manifest rule values):
* Controls 6 and 10 (a flagged note, a beamed note): right -- the rule left both narrowed.
* Of the 13 notes the rule changed, **9 exactly right**; **0 quarters made eighths** (the rule never makes an eighth).
* Wrong, all four written BLUE (GUESSED): tiles 4 and 13 a missed augmentation dot (rule 1.0 vs Sean 1.5) and tile 12 an extra dot
  (rule 1.75 vs Sean 1.5) -- the dot reader's, handed to 2.127; tile 7 (Litolff) a half read as a black head (rule 1.0 vs 2.0) -- a hollow-head
  fill error, not this rule's.
* Sean: "Land" -> `OMR_ARC_INK_NOT_BEAM` default ON (an explicit off-word turns it off).

## 7. ROADMAP 2.126 -- the five real beam/flag cases (+ a sixth), split out of 2.121

2026-10-15. STAGED, GATHER (all four repairs are GATHER readers; ADJUDICATE is unchanged). Lane `lane-2.126-beam-flag`. Truth: Sean's Brahms 317803
pdf 0 page (`data/hand-truth/pages/imslp317803/0.json`, 277 stems, 50 beams, 42 flags); the sixth case is Sean's own answer to 2.134 tile 10.
**Everything is behind a flag, default OFF.** Nothing here is promoted; Sean decides from the tiles.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* Convention: a stem and a flag hook are single strokes that cross the staff and ledger lines in their way (the staff-line ERASE wipes a stem
  piece it takes for the line, and the scan thins a stem on both flanks of a line); a flag's own curve is not a second stem; a stem fused with a
  stack of heads still reaches past them at one end. NOT CONFIRMED by Sean as a rule. Falsified by a tile where a bridged stem, a counted hook or a
  found stem is not on the print (Sean answers on the tiles below).
* Truth class of a head = Sean's STEM box touching it, then a FLAG box at the stem's far end (flagged), else a BEAM box over the stem's column that
  reaches that end (beamed), else bare (`truth_durations.py`). Pairing is geometric, not his statement.

### 7.1 What a human reads, and the gate that failed (record: this tree `0d607e2e`, Brahms p0 and p6 gathered once each, flags off = base)
Crops at 600 dpi with nothing of ours drawn: the bars of `out/print/2.126-review/` (tiles 2, 5, 8, 9 are the four cases).

| case | a human reads | gate that failed (measured) | fixed |
|---|---|---|---|
| q86, q93 (cell 0/0/0/4) | one chord of two heads on ONE down stem, the stem running to a beam at its foot: eighths (a beam joins stem ends; one stem, one value) | `beam_certain_not_joined`: `Q.BEAM_STEM_JOIN` (`gather.beam_stem_join_ink`) read NOT joined: one blank run of **46 px against the 21.7 px tolerance (-24.3)**. The run is the erased staff-line band (25 rows) plus two real breaks of the stem either side (8 and 14 rows, raw page): the likely cause (read off the raw page, not traced in `staff_line_removal`) is a 13-px stem piece between two thin spots that the erase takes for the line (it erases any vertical run no taller than 2x the line's thickness, 14 px at 600 dpi here) | yes |
| q110, q118 (cell 0/0/0/5) | the chord at the right end of a beamed group, stem down to the beam end: eighths | `no_stem` -> `beams_ambiguous`: the stem is fused with the 2-head stack as one run too wide; `line_detection._thin_stem_in_run` protrusion **75 px against the 80 px cut (-5 px = -0.05 space)**; the other gaps of the sorted column extents are 50, 74, 44 | yes |
| q1009 (cell 0/0/9/3) | a down stem with ONE flag hook at its foot: an eighth | `flag_ink_unread`: the hook count was "unresolved, 1 or 2": a 28-row ledger line crossing the band was a second run in 36.7% of the columns (support `[1.0, 0.367]`) against `STEM_TIP_HOOKS_GLITCH` 0.12 (-0.247); the 5 rows of it the shipped `_tip_line_rows` classed did not cover it | yes |
| Brahms p6 sys0 staff11 cell5 bar 102 (P14; Sean's 2.134 tile 10: eighth) | an UP stem with a flag at its top: an eighth | `no_stem` -> `beam_discounted_uncertain`: the detector DID box the flag (`flag8thUp`, conf 0.64); the stem (run x 291, w 28, h 379) was condemned by `_drop_paired_strokes` as the "second stroke of an accidental" with the flag's own curve (x 383, w 7, h 219, 100% inside the flag box; the stem 0.44 inside it): centres 81.5 px apart against 90 (inside by 8.5), overlap 219/219 against 0.6 | yes |

The sixth case is NOT a tip-reader miss: the flag was boxed and never attached because the head had no stem (a lone uncontested head gets no ruler row,
`gather_head_stem_reach` runs for contested heads only). It is the 2.87 "flag-curve family" (13 strokes on Sean's page 0).

### 7.2 The four mechanisms (each flag default OFF; functions changed by name)
1. `OMR_BEAM_JOIN_LINE_BRIDGE` (q86/q93). `gather.beam_stem_join_ink` (new keyword `line_rows`), `gather._observe_beam_stem_join` (passes it only
   under the flag), new `gather.line_rows_across_stem`, `gather._cell_raw_ink`, `gather.beam_join_line_bridge_enabled`. Rows where the RAW page inks
   BOTH flanks of the stem (0.1-0.5 space out, >= 0.7) are set aside and each flank's blank run is measured alone against the SAME tolerance. Real
   case: 31 rows set aside, longest remaining blank run **10 px against 21.7 (margin +11.7)**. A real break wider than the tolerance on a flank, or a
   gap with no line in it, stays NOT joined (both tested); the intervening-stroke guard still runs first on the erased image. Flag off: no new key.
2. `OMR_HOOKS_LINE_BRIDGE` (q1009). `gather.stem_tip_hooks` (new keyword `line_rows`), `gather._observe_stem_tip_ink` (two call sites, via
   `gather._hook_line_rows`), new `gather.line_rows_past_flag`, `gather.hooks_line_bridge_enabled`. A run of attached ink in the hook band that is at
   least 75% line rows (raw page inked beside the stem AND 0.9-1.2 spaces out, >= 0.85: a ledger line runs past any flag, a hook does not) is not a
   hook. Real case: the ledger line ends just LEFT of the stem (left flank 0.2-0.38) so the right side alone is asked; second-run support
   0.367 -> **0.10 against the 0.12 cut (margin +0.02, thin)**; counted 1, `hooks_counted`.
3. `OMR_STEM_FINDER=...,thin_run_stack` (q110/q118). `line_detection._thin_stem_in_run` (new parameter `protrude_spaces`), `detect_stems` (picks it).
   Protrusion cut 0.8 -> **0.7 space** for the stem fused with a stack. ⚠️ **A cut tuned on ONE cell (75 px)**: CLAUDE.md §4 says such a cut may only
   NARROW; this one is behind its own allow-list name, is not in `STEM_FINDER_STAGED_DEFAULT`, and is priced by the stems it adds on Sean's page (7.3).
4. `OMR_STEM_FINDER=...,pair_flag_curve` (p6 bar 102). `line_detection._drop_paired_strokes` (new `on_flag`), `detect_stems`, new constant
   `FLAG_CURVE_MIN_SHARE` 0.8 (the share `OWNER_MIN_SHARE` gives an accidental). A stroke whose PARTNER lies >= 0.8 inside a detector flag box and which
   does not itself is not condemned by that partner; both inside, or neither, is the shipped rule. A flag stays out of `refuse_owned` (its box wraps a
   short flagged stem whole, 2.87).
* Tests: `tools/omr/tests/test_staged_beam_flag_2_126.py`, 21 tests; **10 fail on main** (the four positives and the flag-default tests), the rest are
  the shipped behaviour and the controls (a flank break wider than the tolerance, a gap with no line, two real hooks, a hook with no ledger line, a
  protrusion under the new cut, heads without a stem, a stem the shipped cut already finds, no flag box, both strokes in the box, an accidental box).
  The ledger fixture models what the real q1009 raster does (the line piece the counter sees is on the right of the stem only).
* Flag docs: `docs/flags-2026-09.md` rows plus the `OMR_STEM_FINDER` names.

### 7.3 Controls (one small gather per arm: Brahms p0 and p6, serial, `--through adjudicate`; base = `0d607e2e`, arm = `279a486a`, same weights)
The brief said "no gather"; the GATHER repairs cannot be priced on a re-decided record (`review.rerun` is blind to a GATHER change), so I ran the two
pages once per arm (4 gathers of 4-6 minutes), one at a time. Arm env: `OMR_STEM_FINDER=<staged five>,thin_run_stack,pair_flag_curve`,
`OMR_BEAM_JOIN_LINE_BRIDGE=1`, `OMR_HOOKS_LINE_BRIDGE=1`. Base reproduces all six failures above on this tree.
* **The five p0 cases, arm:** q86, q93, q110, q118 `decided head_and_marks` eighth (`stem_agrees`); q1009 `decided hooks_counted` eighth. p6 bar 102:
  `decided head_and_marks` eighth. All six are Sean's reading of the print (his boxes for p0; his 2.134 answer for p6).
* **Hand-truth scorer** (`python3 -m tools.omr.hand_truth.score ... --derive`, Brahms p0, 277 stems), base -> arm: CV stems found **270 -> 274
  (recall 0.975 -> 0.989)**, not Sean's ("invented") **22 -> 22** (all four new stems are his); heads on their right stem **363 -> 371 of 378**; stem
  direction right 346 -> 354, abstained 13 -> 5, wrong 1 -> 1; durations of heads with no right stem: narrowed 2 -> 0, decided 11 -> 5. Detector families
  (beam, flag, notehead, ...) identical (the repairs move CV and downstream only). **Nothing right at base is lost**: a `diff` of the two score reports
  shows only improvements.
* **Truth class vs record duration** (`truth_durations.py`, every black head of the page): right 280 -> **285**, wrong 3 -> 3 (the same three), narrowed
  57 -> 52, **lost 0, newly wrong 0**; the only changes are the five cases.
* **Sean's past answers** (`judged score REC --doc brahms`, page 0 slice, 600-tile index): right 19 -> **22**, wrong 3 -> 3, narrowed 11 -> 8,
  not_found 68 -> 68 (the 2.81-phase2, 2.81 and 2.83 galleries each gain one right).
* **Side effects on page 6 (no truth page):** two heads decided QUARTER at base are decided EIGHTH on the arm (`glyph/6/0/10/5/1`, `glyph/6/0/9/4/0`:
  the same `pair_flag_curve` condemnation). I cropped both: each is a printed flagged eighth, so the base was wrong and the arm right -- but that is
  my reading, so both are tiles 6 and 7 for Sean. Page 0: no other duration changed (the `head_stem` rows that differ carry only the new stems' ids).
* Tiles, `out/print/2.126-review/` (9; key `tiles_2_126_MANIFEST_HIDDEN.json`, shuffled with seed 2126): the 4 cases as 4 tiles (q86+q93 and q110+q118
  are one chord each: one stem, one value), 2 unjudged page-6 side effects, **3 controls** the flags do not touch (a flagged eighth the tip reader
  counted, a beamed eighth the beam reader joined, a plain quarter). RED corners = the bar, BLUE corners = the note, a big number; nothing of ours is
  drawn; frame control (staff lines carry >= 2x the gaps' ink, and the half-space-shifted test fails) passed for all 9.

### 7.4 What this does NOT show, and the risks
* One page of one plate (Breitkopf, top staves) plus page 6 unjudged: Litolff has no truth page, so no rate is claimed. `thin_run_stack` and
  `pair_flag_curve` each come from ONE cell; the hook margin is +0.02, the join margin +11.7 px, the stack margin 5 px.
* q110/q118 are DECIDED eighths on a stem found by a cut that was measured on that very cell (flag OFF, so nothing ships); under CLAUDE.md §4
  ("a cut-off tuned on our two plates may only NARROW until another publisher confirms it") this must not be promoted to a default on this evidence
  alone. If Sean wants it on before another publisher is checked, it should arrive as a GUESSED (blue) read, not a DECIDED one.
* The beam join and the hook count read the raw raster beside the stem; a staff line that hides a real stem break exactly under it would be bridged
  (the flank rule bounds each side to the tolerance, tested).

### 7.5 Tests and check (on the committed tree)
* Fast tier, `python3 -m pytest -q -m "not slow" tools/omr/tests` (serial: `pytest-xdist` is not installed for this Python, so `-n 4` is refused):
  **8,057 passed, 11 skipped, 833 deselected, 2 xfailed** in 12:50.
* `python3 -m tools.omr.staged.check`: **TOTAL open = 192** (= main; the new flags are read, the new detail keys are filed through a dict spread).
* Raw outputs: `raw-2.126/` (both score reports, `truthdur.json`, the two judged reports, `casecheck.py`, `durdiff.py`).
