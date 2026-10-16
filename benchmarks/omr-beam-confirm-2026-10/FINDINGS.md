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

### 7.6 Sean's answers (2026-10-15, recorded `out/print/2.126-review/answers.json`)
Verbatim: "2.126 1. 8 2.8 3.8 4.4 5.8 6-9. 8" (tiles 1-3, 5-9 eighth; tile 4 quarter). **9/9 agree with the record.** The 6 repaired cases are right (q86+q93, q110+q118, q1009, p6 bar 102); the 2 unjudged page-6 side effects (quarter -> eighth) are right; the 3 controls are right. Caveat: the q110/q118 stem cut (0.7) and the q1009 hook margin (0.02) were measured on single Brahms cells. Per CLAUDE.md section 4 ("a cut-off is a measurement"), those two flags may only narrow until another publisher confirms them.

## 8. ROADMAP 2.140 -- a beamed note decided an eighth that is a sixteenth (2026-10-15; STAGED GATHER + ADJUDICATE; landed ON 2026-10-16, see 8.9)

**CONVENTION ASSUMED:** the strokes at a stem's tip are the beam levels of that stem (the outermost at the tip, each further level inward of it, 2.141h's stacking geometry), and
a staff line is not a stroke. **WHAT WOULD FALSIFY IT:** a notehead, slur end, hairpin or another voice's stem beside a stem that passes the 0.45-space column and the 1.6-space sideways
reach test and is counted as a stroke; a double beam whose gap is filled in so no white shows and whose thickness is under the cut. **NOT CONFIRMED:** every number below is one
reader's reading of the page, none is Sean's; only the 9/9 and 7/9 eye checks and tile 4's "16,16" (Sean 2026-10-15, 2.136 answers) are human evidence. Sean's answers to the
11 tiles in `out/print/2.140-review/` are what confirm or refute it.

### 8.1 The case and the reader that stopped at one level (Brahms p18 sys1 staff12 cell7 = 2.136 control tile 4; records `20261014-night`, streamed, never loaded whole)
Three sixteenths (glyphs 5, 17, 11) under a double beam; verdicts 5, 11, 17 are DECIDED 0.5 / beam_levels 1 (`head_and_marks`), detail `cv_beams 1, yolo_kept 0, levels_certain 1,
levels_possible 1`. STAGED GATHER `cv_lines` filed ONE stroke over them (`[1289,535,364,63]` canonical, ink thickness 54 px = 0.637 sp, one beam): the staff line at page y 6832 lies
in the 2-px gap between the two beams (page runs 6811-6829 and 6831-6850, 0.66 and 0.66 sp), so the second beam fused with the erased line and was lost. The detector's `beam` box over
the stack (`[946,553,696,113]`) was dropped by `rhythm._kept_beams`, which keeps a detector box only if no CV stroke overlaps it in x. Fix 1's own widening
(`_fused_double_beams`, a stroke twice another's thickness) cannot fire: there is no second stroke to measure against (cannot tell is not "one"). **The reader: `cv_lines`
(GATHER) + `_kept_beams` dedup (ADJUDICATE); margin: the box stands 0.774 beams taller than one beam would for its width, cut 0.6 (+0.174); the page shows 2 strokes of 0.66 sp.**
Glyph 17 (the middle head) has no own stem attached (its stem box starts 0.7 sp below the head box): no rule here reaches it, it stays a decided eighth (named, not fixed).

### 8.2 What was built (all default OFF, one flag `OMR_BEAM_STEM_LEVELS`; row in `docs/flags-2026-09.md`)
* GATHER `gather.beam_runs_at_stem_end` / `gather_beam_stem_levels` (new `Q.BEAM_STEM_LEVELS`, reader `cv_beam_levels`): per CV stem and per end, the strokes down a column 0.45 sp
  beside the stem on each side, unerased raster, each staff-line band erased unless ink stands outside it and runs unbroken across it; a stroke is >= 0.36 sp thick and its ink goes on
  sideways >= 1.6 sp (a head is ~1.2 wide). Files nothing unless the flag is set at gather time.
* ADJUDICATE `rhythm.adjudicate_duration` (after the existing fused-thickness widening): a beamed head with `certain >= 1` whose page count at its tip (a stroke >= 1.8 x one beam counts
  as that many) is above `certain`: with the detector's stack box also taller than one beam (`stack_box_excess_beams` >= 0.6) and the page count `certain + 1` the level DECIDES; the
  page count alone NARROWS (`beams_ambiguous`, eighth/sixteenth, never plain); the box alone does nothing. Detail `beam_stem_levels` carries both witnesses and the box margin.
* Tests `tools/omr/tests/test_staged_beam_stem_levels_2_140.py`, 17, each RED case beside a control that can fail (a staff line alone is 0 strokes, and counted if the erasure is
  removed; a head beside the stem is not a stroke; the box alone changes nothing).

### 8.3 Count: DECIDED eighths (0.5, beam_levels 1) whose stem tip shows a second stroke on the page raster (`probe/count_2_140.py`, the product reader on the 600 dpi page, locally per stem)
Sources: Litolff `20261014-night` rows + `out/2.141h/arms/lit-f1/durations.json` (fix 1 ON); Brahms `20261014-night` standing duration verdicts (`out/2.140/brah-durations.json`).
| movement | decided eighths | no own stem read | >= 2 strokes at the tip (page witness) | ...and the detector stack box agrees (both witnesses) | page only |
|---|---|---|---|---|---|
| Brahms | 6,741 | 140 | **88** | **35** | 53 |
| Litolff | 3,703 | 208 | **181** | **8** | 173 |
The box alone (A < 2 strokes, box excess >= 0.6) fires on 954 Brahms and 154 Litolff eighths; a sample of 9 Brahms shows single beams (my eye): it is not a witness by itself, so it moves nothing.
**Who says it is right:** not a reference. My eye on the page crops (`probe/sheet_2_140.py`, not Sean): Brahms both-witness sample 9 of 9 show two beams with a white sliver; Brahms page-only random
9, about 7 show two; **Litolff page-only: I cannot tell on this blobbed plate (staff lines 6-10 px thick fuse with beams), likely many false**, which is why the page alone only narrows.

### 8.4 Page replay, flag OFF vs ON (`probe/replay_2_140.py`: the record's pages streamed, the reader's rows built from the page raster, `pipeline.decide`; `out/2.140/replay-*.json`)
**Control, and it does not fully pass:** the OFF replay reproduces the record's own standing durations on 1,381 of 1,434 Brahms p18 glyphs and 2,018 of 2,114 Litolff p4+p6 (the rest differ because
fix 1 is now ON in the code and the saved records pre-date it, plus the known document-wide calibration of a restricted re-decide, 2.141h); so every figure is ON vs the OFF replay, not vs the record.
The reader ran on the PAGE raster, not the canonical cell raster: its rows exist in a record only after a re-gather with the flag set.
| pages | verdicts changed | eighth -> sixteenth DECIDED | sixteenth -> thirty-second DECIDED | decided -> narrowed | follows a changed stem |
|---|---|---|---|---|---|
| Brahms p18 | 28 | 14 | 2 | 12 | 0 |
| Litolff p4, p6 | 53 | 7 | 0 | 45 | 1 (`stem_value_follows`) |
Named cell: Brahms (18,1,12,7) tile 4: glyph 5 eighth -> sixteenth DECIDED (page 2 strokes, box 0.774), glyph 11 -> NARROWED (the box does not reach its stem: `x` 1647 past the box's end 1642), glyph 17 unchanged.
I looked at the 14 Brahms eighth -> sixteenth crops (all show two beams with a white sliver, two of them only faintly) and 9 of the 12 narrowed (all show a double or heavier beam); the 3 other narrowed and the two thirty-second crops I did not view as crops (my eye only). The two thirty-second cases (tiles 1 and 4) are the weakest
claim (a third stroke next to two) and are the first thing Sean's tiles test.

### 8.5 Tiles for Sean (`out/print/2.140-review/`, 600 dpi, RED = the bar, BLUE = the changed notes, nothing of ours drawn, hidden key `out/2.140/tiles-key.json`, same question as 2.141)
11 tiles: Brahms 1 (2->3 levels), 2 (mixed), 4 (2->3), 6, 7 (narrowed), 8 (= 2.136 tile 4), 11; Litolff 3, 5 (both-witness, a scan I cannot judge); controls 9 (Litolff, plain beamed eighths,
unchanged) and 10 (Brahms, plain eighths under one beam where the box witness alone says taller). A control that disagrees with Sean is the blind spot. Litolff narrowed-only cells were
refused by the frame control (staff lines do not sit where the page says), so no Litolff page-only tile exists.

### 8.6 Limits
* The ON numbers are a replay with page-raster rows; the real GATHER rows (canonical cell raster) are unmeasured until a re-gather.
* The box threshold (0.6) and the 1.6 sp reach rest on one Brahms cell and a Litolff sample: by CLAUDE.md section 4 they may only narrow until another publisher confirms them; the DECIDE path is
  proposed only on both witnesses and only behind a flag until Sean's tiles.
* A head whose stem box does not touch it (glyph 17), a stem past the detector box, and Litolff's fused staff lines are named misses, not handled.
* The tile 4 middle note is an example of an own-stem gap that is 2.142-adjacent (not edited here).

### 8.7 Sean's answers to the 11 tiles (2026-10-15, `out/print/2.140-review/answers.json`) and the causes found
Raw: "1.16 2.16,16,16 3.8. 4.16. 5.8,8,8 6.16,16,16. 7.16,16,16 8.16,16. 9.8,8,8. 10.8,8,8. 11.16,16,16". As built (8.2) it made 9 wrong values right, 5 wrong values narrowed, both controls right, and **6 right values wrong**:
tiles 1 and 4 (Brahms, 16 made 32) and 3 and 5 (Litolff, 8 made 16). Causes, each measured locally at the stem (page replay, `probe/replay_2_140.py`, `score_2_140.py`):
* **(a) Brahms tiles 1/4, the third level.** The stem-tip runs were 0.86/0.96/0.62 and 0.83/0.79/0.65 of one beam; the third is a staff line (page y 3611 on staff 13 of system 0; the run 3603-3616 is centred on it) plus a sliver of ink, bridged into
  a "stroke" by the band rule. And the box witness was not independent of the count it was judging: the box was measured against ONE counted CV stroke although two were already counted, so a box that spans two beams read 1.7 beams tall; measured
  against both strokes' span it reads 0.91 / -3.1. Fixes: `stack_box_excess_beams` now expects the height of ALL CV strokes already counted over x; a page stroke under 0.7 of one beam (`BEAM_STEM_RUN_UNIT_RATIO_MIN`; the thin extras read 0.51-0.65, every stroke on a cell Sean called right reads >= 0.76) is not counted.
* **(b) Litolff tiles 3/5, the second level.** The "second stroke" was 0.38-0.52 of a beam, 0.38 sp = one staff line of that plate (6 px): a staff line. Page count and box were NOT two readings of one ink here (box = detector, count = raster)
  and the box clearing its cut (0.659 vs 0.6, tile 5) was a near-miss that the count's false stroke then promoted. Fix: a page stroke must be at least 1.75 staff-line thicknesses, measured locally (`BEAM_STEM_RUN_LINE_RATIO_MIN`, the existing beam-thicker-than-a-line convention, Sean 2026-10-09).
**After the fixes, replay on all 11 cells: 22 notes right, 4 narrowed (tile 7 x3, tile 8 glyph 11), 0 wrong** (the 9 right ones stay right; tiles 1, 3, 4, 5 back to Sean's values). Honest limits: the cuts 0.7 and 1.75 were chosen after seeing these tiles (a fit to 11 cells, not a held-out test), so
the second set of tiles is the test. Other cells whose value now changes (decided, outside the 11): Brahms (18,0,1,6) x2, (18,0,11,1) x3 (8 -> 16, crops look like double beams to me) and Litolff (6,1,7,0) x1 (box excess 0.616 vs 0.6, the thinnest margin; the tile's bar bracket is unclean): blind tiles `out/print/2.140-review-2/`, key `out/2.140/tiles2-key.json`.

### 8.8 Round 2 (Sean 2026-10-16, `out/print/2.140-review-2/answers.json`): Brahms tiles 1, 2 right (5 notes); Litolff (6,1,7,0) glyph 5 WRONG (we 16, Sean 8)
**Why a "0.571 run" passed the 0.7 rule: it is not a bug in the rule.** 0.571 is the run's thickness in staff SPACES; the 0.7 cut is on that run over one beam (unit 0.75 sp on this cell): 0.571 / 0.75 = **0.76**, above 0.7 (the key printed the
raw spaces; the first run was 1.27 sp = 1.69 beams, counted once). The run is a staff line of that plate (0.38 sp) plus a sliver, not a stroke, and it cleared both stroke cuts by a small margin (0.76 vs 0.7; 9 px against 1.75 lines of ~5 px);
the box witness cleared its cut by **0.016** (0.616 vs 0.6). Two near-misses together decided a value. **Fix (CLAUDE.md section 4: a cut tuned on our plates may only narrow; a refusal says how close it came):** a box witness within
`BEAM_STACK_BOX_NEAR_MISS` = 0.05 of its cut cannot decide; it narrows (eighth/sixteenth, blue) and `detail.beam_stem_levels.box_near_miss` records it. Test: a box at ~0.62 narrows, one at 0.774 still decides.
**Replay of all 14 tiles' cells (round 1 + round 2; `probe/score_2_140.py`, replay2-*.json): 27 notes right, 5 narrowed, 0 wrong**; the Litolff cell is now narrowed. No other cell's value changes against the previous rule (Brahms p18 still 26 changed: 15 decided, 11 narrowed;
Litolff p4/p6 now 7 changed, all narrowed, none decided), so no new tiles. Limits unchanged: the 0.05 margin is a convention-free guard, not a measurement; the stroke cuts (0.7, 1.75 lines) still have only 0.06-0.1 of clearance on this cell, so a Litolff
decided level now needs every witness well clear; none exists in the 14 cells.

### 8.9 Landed ON (2026-10-16)
`OMR_BEAM_STEM_LEVELS` default ON in `gather.beam_stem_levels_gather_enabled` and `rhythm.beam_stem_levels_enabled` (explicit `0/false/no/off` disables). Sean 2026-10-16: 14 tiles, 27 right, 5 narrowed, 0 wrong after the round-2 fix. Caveat: cut-offs fitted to Sean's tiles; a third publisher not yet checked. The GATHER reader files `Q.BEAM_STEM_LEVELS` rows only at the next re-gather; on a record without them `_stem_tip_strokes` returns None and ADJUDICATE duration is unchanged from flag-off (no raise).

## 9. ROADMAP 2.146 -- beams, globally (2026-10-16; research, no product code)

Sean 2026-10-16: *"Let's spend the day tackling the biggest issues - one at a time. Let's start with beams. I want to think globally
about beams."* His two hypotheses: (a) a beam's thickness is measured against THAT score's staff, never as an absolute width;
(b) *"the connection to the end of stems is the most important factor - more important than width."*

### 9.1 How big the beam problem is (20261014-night re-gather reports, section 7)
* Brahms: **2,173** heads narrowed `beam_discounted_uncertain` (4th reason on the movement); Litolff **244**. 2.121 §1 showed on
  Brahms p0 that 51 of 52 such narrowings are BARE stems beside a refused slur/tie box -- the reader asks "is the detector's box
  near this stem a beam?" and, when it refuses the box, leaves the note uncertain instead of reading the stem's own tip.

### 9.2 Engraving rules that help find a beam (Gould *Behind Bars* ch. "Beams"; Ross; SMuFL engraving defaults; standard practice)
| rule | evidence it gives | STAGED today |
|---|---|---|
| A beam joins its stems AT THEIR ENDS; the stem stops at the beam's outer edge | a thick run leaves the stem TIP | GATHER `beam_runs_at_stem_end` (`Q.BEAM_STEM_LEVELS`, 2.140) reads it, but only COUNTS levels after a beam box is accepted |
| Every stem of a group touches the primary beam (>= 2 stems) | >= 2 tips on one stroke | core-stroke "stem at each end" (2.82) -- ends only, from the box's side |
| Thickness 0.5 sp (SMuFL `beamThickness` 0.5); gap 0.25 sp (`beamSpacing`), so levels 0.75 sp apart | thickness and level pitch in STAFF SPACES | thickness as a ratio to the LOCAL staff-LINE thickness (1.75), plus 0.36 sp in the tip reader |
| Number of beams = value (1 eighth, 2 sixteenth, 3 32nd) | level count at the tip | 2.140 (ON) |
| A beam is STRAIGHT (never an arc); slant at most ~1-2 sp over the group | sagitta ~0 | `BEAM_SAGITTA_MAX_SPACES` 0.40 |
| Slurs/ties are curved, tapered (thin ends, ~0.2 sp at the middle), and end at NOTEHEADS (a stem-side slur clears the tips by ~0.5 sp) | no tip contact; thin | arc refusal, `too_thin`, 2.121 INFER collapse (guessed blue) |
| A flag hangs from the tip on the RIGHT, curls back within ~1 sp | short run at the tip | flag/tip-window readers |
| A beam stays on its stem side; stems of a beamed group usually all point one way (mixed groups exist) | side of the run | `side` in rhythm |
| Inside the staff a beam end sits, straddles or hangs on a line (no thin white wedge) | beam y quantised to 0.25 sp against the lines | not read |
| Groups follow the beat (6/8: 3 eighths; 2/4: 2 or 4) and do not cross a barline | group length | not read; the bar may only CONFIRM (CLAUDE.md §4) |
| Fractional beam (beamlet) ~ one notehead wide, on the dotted/short note's side, at the secondary level | short second run at the tip, on the primary's side | `BEAM_BEAMLET_GAP_SPACES` |
| EXCEPTIONS: two-note tremolo beams between half notes do NOT touch the stems; grace/cue beams are ~0.6 size; cross-staff beams (rare in orchestral scores) | falsifiers of the tip rule | tremolo readers (2.71/2.137) |

### 9.3 Sean's hypotheses tested on his own boxes (Brahms 317803 pdf 0 hand truth: 50 beams, 69 slurs, 84 ties, 276 stems with a tip; raster = the PDF at 600 dpi, ink < 180; `probe/beam_vs_arc_2_146.py`, `probe/tip_probe.py`)
* **(b) stem-tip contact.** Truth stems whose tip touches the stroke's ink: **beams 50/50 have >= 2; slurs 58/69 none, 7 one,
  4 >= 2; ties 82/84 none.** Read FROM THE STEM (every truth stem: does a run >= 0.36 sp thick leave its tip and run >= 1.5 sp?):
  **beamed 127/129 yes; flagged 1/36 yes (35 stop within 1 sp); bare 1/111 yes.** The two beamed misses read no run at all
  (not yet cropped). Read this way the detector's beam box is not needed to tell beamed from bare.
* **(a) thickness against the staff.** Median thickness: beams 0.61 sp (p10 0.38) = 2.86 lines; slurs 0.28 sp (p90 0.32) =
  1.33 lines; ties 0.22 sp. On ONE page staff space (31-33 px) and line (6-8 px) are both constant, so the two rulers separate
  equally (tip reader: 0.36 sp, 0.40 sp and 1.75 lines give 127/1/1, 125/1/0, 127/0/1 beamed/flag/bare). Which ruler is safer
  ACROSS plates is NOT measured here: the staff space is what the engraver set the beam by (0.5 sp); the line thickness is
  what the printing/scanning weight changes. Needs a second plate's truth (Litolff has none for beams).
* Thickness alone overlaps (thinnest beams 0.22-0.38 sp vs thickest slurs 0.32-0.34 sp); tip contact plus a reach past
  1.5 sp does not. **Sean's (b) holds on his page: the connection to the stem end is the stronger witness.**

### 9.4 Proposed changes, ranked (for Sean; none built)
1. **The stem tip decides "beamed or not".** Where a stem's tip is read (`Q.BEAM_STEM_LEVELS` row on its own stem): a beam run
   at the tip => beamed with that many levels; a tip reading clean (no run, no flag ink) => NOT beamed, written plain (READ),
   whatever detector beam boxes stand nearby. Detector boxes become a second source only where no tip is read. Targets the
   2,173 Brahms / 244 Litolff `beam_discounted_uncertain`. STAGED ADJUDICATE `rhythm.adjudicate_duration`. Measure on the
   hand-truth page first (truth per stem exists), then named pages.
2. **One ruler: staff spaces.** Express the beam thickness cut in the local staff space (0.36 sp, the tip reader's own) and
   keep the line ratio only as a guard; verify on a third publisher (2.101's held-out plates) before trusting either.
3. **More stems.** The tip rule is only as good as the stem finder (CV stems 0.76 recall on this page, 1.7-stems). A beam run
   found from a HEAD's expected stem column can also witness the stem (a beam is where the stem ends).
4. Later: tremolo exception (beam not touching half-note stems), beam y snapped to sit/straddle/hang.

Limits: one page, one publisher, truth stems (our own stem finder will do worse); the 0.36 sp / 1.5 sp cuts were set before
this test (2.140), not fitted to it.

### 9.5 Change 1 built (Sean 2026-10-16: "Yes, build change 1 here"), flag `OMR_STEM_TIP_DECIDES_BEAM`, default OFF (branch `lane-2.146-stem-tip-beam`)
STAGED ADJUDICATE `rhythm.adjudicate_duration` (new `_stem_tip_beam_verdict`): where every stroke over a stemmed head was
refused (the branch that narrowed `beam_discounted_uncertain`), the head's OWN stem tip decides -- `Q.BEAM_STEM_LEVELS` (2.140)
reads no beam run and `Q.STEM_TIP_INK` reads no hook -> no beam (`stem_tip_reads_no_beam`); n runs -> n levels
(`stem_tip_reads_a_beam`). No row, flag window unread/disputed, or a hook -> the narrowing unchanged (rule 8). 10 tests
(`test_staged_stem_tip_decides_beam_2_146.py`), each positive with a flag-off control.
* **Sean's hand-truth page (Brahms pdf 0)**, small re-gather p0-1 on this tree (`acceptance_quick`, through ADJUDICATE),
  re-decided off/on (`probe/replay_score_2_146.py`): 62 `beam_discounted_uncertain` heads; **41 decided no beam, all 41
  right** (37 on truth bare stems; 4 chord heads on a plain down stem, cropped: dotted quarters); 0 wrong; 21 stay narrowed.
* Brahms p1 (no truth): 19 no beam, 1 one beam, 60 stay narrowed. Litolff p1-3 (small re-gather): 14 no beam, 35 stay.
* Why heads stay narrowed (Brahms p0-1, 81): 48 the rule is never reached (no own CV stem -- the stem finder, §9.4 item 3);
  26 the tip reads clean but the flag window never read that end (`Q.STEM_TIP_INK` absent: kept narrowed on purpose -- a
  flag the detector missed would become a quarter); 7 no tip row.
* 34 blind tiles `out/print/2.146-review/` (Brahms p1 20, Litolff p2-3 14, every changed note; hidden key `out/2.146/`).
