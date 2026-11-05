# Plan 2026-11-04 — one beam reader on the page map (ROADMAP 2.260c; M4 of plan-2026-11-03-page-ledger §C)

STAGED. Design step, no code (Sonnet design agent, tree d25d56adc; filed by the manager, citations spot-checked). Build after 2.262 lands.

Paths: `g` = tools/omr/staged/gather.py, `r` = tools/omr/staged/adjudicators/rhythm.py. Sean, 2026-11-03: "Read once. Claimed once." The page record is the one ledger. A cell is a view. A later reader marks claimed ink but never takes it. No stage after GATHER reads pixels.

## 1. The five reads today (all STAGED GATHER)
Line numbers are for this tree. Call order is g:17561, 17626, 17710, 17713, 17715.

- **A. `gather_cv_lines`** g:5069, call :17626.
  - Reads: the cell's erased raster `image_no_staff`, through the shared, frozen `line_detection.detect_lines`/`detect_beams` (line_detection.py:1514, `rescue_tall_beams=True`, head boxes as gate; g:5127).
  - Files: Q.STEM and Q.BEAM_STROKE (reader CV_LINES, value = cell-canonical xywh, detail x0/x1/y_center/image/staff_lines_erased; g:5174-5204). Beside them: Q.STEM_TIP_INK (flags, g:5232) and Q.BEAM_STEM_JOIN, a stem x beam x two-ends cross product per cell (`_observe_beam_stem_join` g:7414, call :5261).
  - A sixth call of the same finder sits at g:672 (low-confidence rescue). It keeps the stems and drops the beams it just found.
- **B. `gather_detector_beams`** g:12332, call :17710.
  - Reads no pixels. It copies the detector's `beam` boxes into Q.BEAM_STROKE (reader DETECTOR, image "original"; g:12350). Per its docstring, a box bounds the stack, not a stroke.
- **C. `gather_beam_stroke_ink`** g:12709, call :17713.
  - Reads: the unerased `cell.image` (g:12731). The arcs are not erased from it.
  - Files: one Q.BEAM_STROKE_INK per row of A and B (thickness, ratio to the local line, sagitta, end stems, core, `cut`; g:12620-12775).
  - It says why it uses the original raster (g:12641-12643): the staff erase thins a beam on a line, 34 px against 49 px.
- **D. `gather_beam_stem_levels`** g:12882, call :17715.
  - Reads: unerased `cell.image`. At each end of each Q.STEM it takes a column 0.45 sp beside the stem and records the strokes (`beam_runs_at_stem_end` ~g:12840).
  - Files: Q.BEAM_STEM_LEVELS.
  - The window is clipped to the raster (g:12853) and files no `cut` fact.
- **E. The beam part of `gather_stroke_map`** g:7869, call :17561.
  - Reads: the erased cell raster again, at 16 px/sp (stroke_map.py:42).
  - Files: horizontal and curve strokes with `touches` in Q.STROKE, plus `cut` (g:7940).

**Consumers**, ADJUDICATE unless stated:
- **Q.BEAM_STROKE**
  - `_beam_reader_looked` r:355; `_kept_beams` r:379 (keeps a detector box only where no CV stroke overlaps it in x).
  - `_strokes_on_a_system_arc` r:1664, `_no_beam_at_the_stem_tip` r:1705, `_beam_join_witness` r:3310.
  - `adjudicate_duration` r:4949.
  - The `beam_mate` stem direction r:9588.
  - Tuplet adjudicator: declared in `wants` (r:6511-6514), but the body reads none.
  - notehead_precision.py:768 (a head box that is a beam piece).
  - Export: `_beam_boxes_by_cell` export.py:2477, call :5469, then `annotate_beams`. This is where the exported "beams" count comes from.
  - GATHER: `gather_notehead_stem_cross_ink` g:11687, which runs at :17677, before B at :17710. It sees only the CV beams.
- **Q.BEAM_STROKE_INK**
  - `_beam_ink_rows` r:1356, `_not_a_beam_by_ink` r:1802 (too_thin r:1890-1891), notehead_precision.py:773.
  - `_stem_tip_strokes` r:1577 takes its beam-thickness unit from these rows, so D depends on C.
- **Q.BEAM_STEM_LEVELS**
  - `_stem_tip_strokes` r:1577, feeding `adjudicate_duration` r:5216-5256 (page count plus the detector's stack box, 2.140), `_stem_tip_beam_verdict` r:1625 (clean tip means no beam, 2.146) and `_no_beam_at_the_stem_tip` r:1705 (2.170).
- **Q.BEAM_STEM_JOIN**
  - `_beam_join_witness` r:3310.
- **Q.STROKE**
  - `_beams_from_strokes` r:4121 (`OMR_BEAMS_FROM_STROKES`, ON since 10-28; DECISIONS.md:188; beam_strokes.py).
  - stroke_owner.py:328, stem_value.py:671, r:4654.

**Where two reads re-ask the same ink**
- A and E both open `image_no_staff` and both find the beam stack. `_kept_beams` settles A against B by x-overlap. `_beams_from_strokes` then judges B against E.
- C re-measures what A and B just filed, on a different raster. D re-counts the tip that E's `tip_reading` (beam_strokes.py:303) counts too, and its unit comes from C.
- Whether D and the detector's stack box are independent witnesses (r:5216) is not established. Both read `cell.image`, and CLAUDE §5 says two witnesses off one raster fall silent together.
- "Is this beam an arc's or a hairpin's ink" is asked from boxes in `_strokes_on_a_system_arc` (r:1664) and `_beams_on_owned_strokes` (r:4642, `OMR_BEAMS_HONOUR_CLAIMS` ON), although the arc and hairpin claims exist (g:17576, :17621). This is the 2.260b lesson: ask the claimed object, not the pieces.

**Where the cell edge cuts a beam** (2.259)
- The cell is the staff plus a pad (stroke_map.py:69-70). A tall up-stem beam stands above it.
- A files the sliver, and C measures 0.26 sp. `_not_a_beam_by_ink` read that as `too_thin`.
- D clips its window at g:12853 with no `cut` fact. E's tip level goes missing.
- M0 (landed ON) records `cut` on C and E and makes r:1890 and r:5296-5299 say cannot-tell (`cut_abstains`, `beam_cut_kept` r:5410). That only softens it: the thickness stays a sliver's, and D is not covered.
- How many of the 105 narrowed heads are still cut after M0 is not established.

## 2. Cause, and the process lesson
`git log -S` dates the reads:
- A and B: 2026-09-07.
- Q.BEAM_STEM_JOIN: 09-29 (2.38).
- C: 10-09 (2.74).
- D: 10-15 (2.140).
- E: 10-22 (2.195).
- `_beams_from_strokes`: 10-22 (2.202).

Each reader was added to fix a case its predecessor could not judge, and none was ever removed. ROADMAP.md:251 shows step 10 ("delete the old readers") not started. Five readers of one beam, on three rasters, can disagree, and the disagreement is then settled by guard rules in `adjudicate_duration`.

**Process lesson:** a reader added beside an old one is a second witness only if it reads a different source. All five read the cell crop, which has already cut the beam. A new reader that does not retire its predecessor adds a guard rule instead of a fact.

## 3. The one reader (`staged/page_beams.py`, STAGED GATHER, decides nothing)
- **Place.** Where `gather_cv_lines` is called now (g:17626): after the head boxes are final, after `gather_arc_claim` (:17576) and `gather_hairpin_claim` (:17621), and before `gather_notehead_stem_cross_ink` (:17677). Claim order: heads, then arcs and hairpins, then stems and beams. `page_map_pre` is dropped in the claims-off branch (g:17573). Keep the map in both.
- **Reads.** Only rows and the in-memory PageMap (page_strokes.py:339): Q.PAGE_STROKE strokes (kind, thickness, profile, sagitta, `ends`, `touches`, `staff`), the Q.STEM rows moved to page px with the transform at g:7933, head boxes, and the claim rows. It reads no raster.
- **Walk.**
  1. Bucket the strokes by `PageMap.staff_of`, with an x-sorted array of verticals per staff.
  2. For each Q.STEM end, bisect to its vertical stroke (`find_stem_stroke` logic, beam_strokes.py:254, on page px).
  3. Follow `touches`, plus gaps up to `JOIN_MAX_GAP_SPACES`, to horizontal and curve strokes inside the tip window (`TIP_OUTWARD`/`TIP_INWARD`).
  4. Take each stroke's role from `beam_strokes.roles(face_join, trough)`, the cut-offs already landed in 2.202. Follow the beam's own `touches` to the other stems it joins.
  - Nothing here is new tuning.
- **Cost.** O(strokes + stems·log per staff). There is no stems x beams x ends product (that is `_observe_beam_stem_join` today), and no box x piece x exclude scan (the 2.262 pattern). Heads enter only through the bisect. Timed on Brahms p5, not one page.
- **Files, keeping the row shapes.** Cell views, with `reader=CV_PAGE_BEAMS` (new READERS entry) and `page_strokes=[ordinals]` in detail:
  - Q.BEAM_STROKE: cell-canonical xywh, not clipped to the cell.
  - Q.BEAM_STROKE_INK: same keys, derived from the stroke row.
  - Q.BEAM_STEM_LEVELS: same `ends` runs, from strokes.
  - Q.BEAM_STEM_JOIN: from the touch or gap test.
  - A view goes in each cell that holds a joined stem, once per (cell, page ordinal). A beam measured whole has no `cut`.
  - B stays. It is the one different source, the neural reader.
- **Consumer changes.** The only ones planned are the four tests `reader == CV_LINES` for beams (r:393, :1699, :3273, :5217), which become "a CV beam reader". Later, `_beams_from_strokes` reads the views (M4d).
- **Gaps in the stroke row.** Staff-line thickness comes from `cell.staff_line_thickness_canonical` (g:7439), a conversion and not a pixel read. `core` and `end_stems` come from `profile_sixteenths` and `touches`, which are different measurements, so M4a measures them before anything reads them.
- **Claim.**
  - Only a beam-role stroke (two stems or more, thick, straight) is claimed, as owner `beam`, unit `ink`. It is filed as a Q.CLAIMED_AREA row on the staff, in the shape `stroke_owner` reads (`[[cell, ordinal]]`, stroke_owner.py:121-127), with the page ordinals in detail as arcs_system.py:955 does.
  - Stubs, hooks and thin spans stay unclaimed and are counted. They are the flag reader's.
  - A stroke an earlier owner has claimed (arc, hairpin, word, head) is marked `contested` in the view and never taken (the `_owner_mask` rule, r:4068).
  - Page-id claim values for non-arc owners are M3's open list. `stroke_owner` gets a `_beam_claims` beside `_arc_claims` and `_hairpin_claims`.

## 4. Migration (flag `OMR_PAGE_BEAMS`, default OFF; LEGACY untouched)
Old reads stay in the tree and run when the flag is off, so the control is the whole pipeline against the whole pipeline. Each retirement is a sub-row of 2.260c with its own default-OFF flag (`OMR_PAGE_BEAMS_RETIRE_*`). The arms are re-adjudicated records on the same pages and stages.

- **M4a, file only.** Adds `beam_role`, joined stems and tip levels to the Q.PAGE_STROKE rows. Nothing reads them. Export is byte-identical. Controls that can fail:
  - Parity against A's strokes by place, not by id, with the bands shifted 6 px as M2 did.
  - Beams lying on a staff line, which test the eraser thinning (g:12641).
  - A cut beam, which should come out whole.
  - Timing and RSS on Brahms p5 and p0.
  - 12 disagreements as crops to Sean: which side does the print back?
- **M4b, A and C retire.** The cell views replace A's beam rows and C's ink rows. Reports the three measures. A and C are one question.
- **M4c, D and Q.BEAM_STEM_JOIN retire.** Levels and join come from the stroke graph. Evidence: Sean's 2.140 and 2.146 tiles re-scored, and the judged answers.
- **M4d, E's beam use retires.** `_beams_from_strokes` reads the views. The cell Q.STROKE rows stay for the other kinds (M5 and M6).
- **M4e, re-asks retire.** `_strokes_on_a_system_arc` and `_beams_on_owned_strokes` read the beam claim. This reworks a later-stage rule (measuring.md:36) and does not revert the capture.
- **Each retirement needs three things.**
  1. A `grep` showing no reader of the old rows is left (`python3 -m tools.omr.staged.check`).
  2. The three measures with the old call skipped.
  3. The old read shown failing where the page read is right (rule 7; ROADMAP.md:251 on 2.217: check the old reader fails first).
- **Default ON.** Only on Sean's tiles, and as a deny-list, as 2.260a did.

## 5. Measures and gates
- **Reports** (docs/measuring.md:7-23, plus :36 for a GATHER lane):
  1. What changed in the exported file, by kind, from `lane_report`.
  2. Sean's 12 blind tiles on those changes.
  3. Judged right->wrong, which must be 0, and unwritten->wrong, which must be 0.
  - Also `claim_readout` and `claim_order`. A violation pair or an OPEN pair that rises is the wrong way.
  - Pages: Litolff p6+p16 (the M0 pages; the floor to beat is M0's notes +3, beams +4); Brahms p0 (hand truth) and p5 (heaviest). The ~9 Litolff pages with ~40 clipped beams are not named in the sources.
- **Must move.**
  - Litolff `duration_narrowed` heads: 105 on the 20261031-night frozen pages, 56 `beams_ambiguous` and 49 `beam_discounted_uncertain` (ROADMAP 2.259 row). That count predates M0, so the baseline is re-censused with M0 and M3 ON. Whether the 105 sit inside the 137 below is not established.
  - START HERE's ~210 Brahms and 137 Litolff unwritten heads.
  - Brahms is unbounded: M4's own cost is unknown there.
  - A head that gains a value is a tile for Sean, not a win.
- **Must not move.**
  - Brahms p0 hand truth. The scorer does not score CV beams (hand_truth/score.py:67), so beam parity has its own control (M4a).
  - Judged right->wrong 0 and unwritten->wrong 0.
  - Red bars (42 -> 42 on Brahms p0+p5 at M3).
  - The `beam_mate` and stem-direction counts, and the exported beams count, are reported. Both read these rows.
  - Cost: seconds and peak RSS per page on Brahms p5 and p0, against the reads retired. No number is set because none is established.

## 6. The rule that owns each value
- **Duration, eighth against quarter.**
  - page-facts.md:94-102 and CLAUDE §4: an eighth only on a flag or beam read on its stem, or a value shared from it. Bar arithmetic never supplies one.
  - page-facts.md:92: every note on one stem shares one written value. Heads that disagree are undecided (:54-57).
  - M4 only supplies the beam fact. The decision stays in `adjudicate_duration`.
- **What counts as a beam.**
  - page-facts.md:39-52: it joins a second note, has no arc, and is thicker than a hairpin's line. A flag seen is a flag even inside a detector beam box. Clean tip means no beam. A beam owns the stemmed notes under its width (2026-10-28).
  - :70-73: it runs from its first stem to its last, and the outer note's centre is half a head past the stroke.
  - page-facts.md:41-42: open heads are never beamed. Hairpin and arc ink is theirs (2.261, 2.260b).
- **Whose ink.** CLAUDE §3, claim order, and page-facts.md:110 (arcs and hairpins read page-wide).
- **Stem direction (`beam_mate`).** CLAUDE §5 (up to the right, down to the left) and page-facts.md:34 (stem second, beam third). Its inputs change, so it is reported.
- **Not touched.** Pitch, owner staff and kind of head (CLAUDE §5: the ledger lines name the owner). A fix that moves one stops and asks.
- **A doc that disagrees with the tree.** page-facts.md:340 calls `OMR_BEAMS_FROM_STROKES` OFF and held. The tree has it ON (r:4056, DECISIONS.md:188, flags-2026-09.md:165). The tree outranks (rule 10); the M4a commit fixes the line, with its scope.

## 7. Risks, and one question for Sean
- **2.262 not landed.** M4a is timed on top of it, on Brahms p5.
- **Unclipped views.** Whether any consumer assumes a box inside the cell frame is not established. M4a feeds a negative-y box through the consumers.
- **Eraser thinning.** A beam on a line may read thinner on the erased page raster. The ratio test (1.75 lines, r:1054) and the 0.5 sp cut-off (beam_strokes.py) are different families. M4a counts the cases where they disagree.
- **Cell twins.** The overlap is about 1.3x, so a beam appears in two cells. Dedup by (cell, page ordinal).
- **Merged plates.** Litolff merges a beam into a head blob (r:4583-4590). The split in stroke_map.py:616-698 must hold, or `head` claims it and the beam is lost.
- **Ordering.** The cross-ink reader (g:11687) must keep seeing the beam rows. The views are filed at A's place.
- **Beams between staves** are not covered. Not established.

**Answered (Sean 2026-11-04):** "Every beam is within a bar - horizontal is easy. Vertical is hard because beams can be outside of a cell or show up in multiple cells." Sean, same day: "Don't add more work. We want it to read and claim once and we want that info to be passed on to every subsequent view or cell cut." -- one page read, one claim, the same result handed to every cell view; no extra controls for the vertical case.
