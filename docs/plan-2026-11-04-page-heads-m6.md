# Plan 2026-11-04 — heads and ledger lines read once on the page (ROADMAP 2.260e; M6 of plan-2026-11-03-page-ledger §C)

STAGED. Design step, no code (Sonnet design agent; filed by the manager, citations spot-checked). Paths: `g` = tools/omr/staged/gather.py, `so` = tools/omr/staged/stroke_owner.py, `ps` = tools/omr/staged/page_strokes.py. Sean, 2026-11-04: "read and claim once ... passed on to every subsequent view or cell cut", and "Don't add more work".

## 1. The head and ledger reads today
All are GATHER on cell crops unless marked. The one LEGACY item is `pitch_resolver.py:180`, frozen and not read by `staged/`. Call lines are `g`.

**Head position and extent**
- **Stem-end heads.**
  - `gather_stem_end_heads` g:1291, called at :17526. Reads `page.binary` at an orphan stem end.
  - Appends an ink-only candidate box under RESCUE_STEM_HEAD. ADJUDICATE weighs it (notehead_precision.py:3549-3566). EXPORT writes it blue (export.py:498).
- **Position.**
  - `gather_notehead_positions` g:1506, called at :17598. Files `Q.NOTEHEAD_STAFF_POSITION` (g:1654) on the Glyph subject `(page, system, staff, cell, box index)` (g:1587).
  - Base value: the detector box centre against the cell's own grid.
  - Overrides: the line-cut (:17597, cell raster) and the hole (`OMR_HEAD_HOLE_POSITION`, ON, cell raster).
  - Ink extent (`OMR_HEAD_INK_EXTENT`, page raster) is **OFF** in the tree (head_extent.py:49-50, an allow-list; flags-2026-09.md:162). The comment at g:1621 saying "ON" is stale. The tree outranks it.
  - An ink-centre candidate is filed only for far heads (g:1638-1650, ON). It is a candidate, never a placement.
- **Consumers of position.**
  - ADJUDICATE: `ownership.py` tie and slur ends (2404-2506, 3313), `rhythm.py` (2264, 2318, 2649, 10296), `aug_dot_join.py:455`, `notehead_precision.py:3032`.
  - EVALUATE: `consequences.py:90` (`restate_pitch`).
  - EXPORT: `export.py:2685` (arc ends).
- **Extent and fill.**
  - `gather_head_oval` g:8546 (:17679, page raster).
  - `gather_head_ink` g:8498 (:17682). Files `Q.HEAD_INK` off `page.binary`.
  - `gather_notehead_ink` g:10417 (:17660). Files `Q.NOTEHEAD_INK` off the erased cell raster.
  - `gather_stacked_head_fit` g:11288 (:17671).
- **Head claim.** ADJUDICATE `stroke_owner`. A head owns a cell stroke when a detector box covers at least 0.5 of it (so:59; tier 1 at so:65-74; adjudicators/stroke_owner.py:333). The claim is derived from the box. Sean called that rule "arbitrary" (DECISIONS 2026-10-30).

**Ledger count**
- **Far-head count.**
  - `gather_far_head_ledger_positions` g:1843, called at :17690. Runs per detector box in each cell's `detections` (g:1938).
  - It runs only if the box's rounded position is below -1 or above 9 (g:1955; ledger_grid.py:512-523).
  - Raster: `page.rgb` gray with the staff lines left in (g:1872).
  - Files `Q.FAR_HEAD_LEDGER_POSITION` (g:1755) and `Q.FAR_HEAD_OWNER_LEDGER`, one row per candidate staff (g:1764).
  - Consumers: adjudicators/position.py:32, ownership.py:260, `restate_pitch` (consequences.py:130-180).
  - It must run after `gather_notehead_stem_cross_ink` (:17677), because its not-a-note gate reads that row (g:1706-1710).
- **Owner ledger rungs.**
  - `gather_ownership_evidence` g:2510 (:17607). Files `Q.LEDGER_RUNG_INK` (g:2748) and `Q.LEDGER_OWNER_DENSITY` (g:2756), erased cell raster of each candidate staff.
  - Consumers: ownership.py:1464-1543, notehead_precision.py:3337.
- **Ledger boxes.** `gather_ledger_ink` g:9076 (:17651). Files `Q.LEDGER_INK_UNDER` on detector `ledgerLine` boxes.
- **Page map.** The page map holds ledger stubs as `horizontal` strokes joined `ledger|head` (stroke_map.py:742-798), and a head stack cut at its waist `head|head` (stroke_map.py:652). Nothing reads them for a count.

## 2. Cause and process lesson
- **Why heads are read per cell.** A head is a subject only if the detector boxed it, and everything about it (position, extent, ledger job, claim) hangs off that box.
- **Why an unboxed head has no subject.**
  - The ink is on the page map as a blob stroke. No box covers it, so `stroke_owner` leaves it unclaimed for stems and beams (so:34-35).
  - It has no Glyph, so no position, no far read, and no arc-end to bind. CLAUDE §7: "no stage can repair it".
- **Why a head box drawn off its ink fails (2.264, tile 9).**
  - The box reads 9.38 and rounds to 9, the first space, so `far_head_needs_ledger_read(9)` is false. The ledger read never runs.
  - The hole read 10.51 and was refused off-grid.
  - The ink reader that could move it is OFF, and it moves only positions -1 to 9 (head_extent.py:37).
  - Truth is 10, a head on the first ledger below the staff.
- **The record disagrees on tile 9.** FINDINGS 2.260b says the upper dyad head is unboxed. FINDINGS 2.264 says the box is off. Whether these are one cause is not established. The M6a census settles it.
- **Possible double reads.** Twins of one head in two cells get separate far reads. How many disagree is not established.
- **Process lesson.** Each head reader was added to fix its predecessor's miss, and all of them ask the box, never the ink.
- **2.217 warning (ROADMAP 2.217).** A ledger count rebuilt on the stroke map was wrong 9/9 where today's reader was right 9/9. The map cannot see stubs fused into heads. M6 therefore does not rebuild the ledger count.

## 3. The one reader (`staged/page_heads.py`, GATHER, decides nothing)
- **Place.**
  - Where `gather_notehead_positions` is called now (:17598): after the page map (:17557) and the arc claim (:17576), before `gather_cv_lines` (:17626).
  - Heads then claim before stems and beams (so:65-74).
  - The hairpin claim (:17621) lands later. Whether a hairpin touching a head matters is not established.
- **What a head is.**
  - A head is the page blob stroke (or `head|head` band) that a detector box stands on, or a head-shaped blob with no box.
  - Boxes are mapped to page pixels as `ps.split_inputs` does, twins folded to one.
  - The extent is the stroke's box. The existing `head_ink.trim_head` on `page.binary` is read beside it for heads on a staff line, because the eraser thins them.
  - The position is the extent's centre against the staff lines at its own x (`staff_of` and `PageStaff.lines_at`), as page-facts says.
  - A box ADJUDICATE refused as a head stays refused (`head_extent.refused_as_head`).
- **Files.** One `Q.PAGE_HEAD` row per head on the page subject, shaped like `Q.PAGE_STROKE`. It carries the stroke ordinals, the extent, the local staff and float position, `source` (box or ink_only), and the ledger result.
- **Ledger count, once.**
  - The reader is today's `far_head_reader`, unchanged. It is driven from the page head list, one job per head.
  - The trigger is "a rung touches the head's ink, or the ink centre rounds outside -1..9" (page-facts:270-273). It no longer waits on the box's rounded position. This is what tile 9 needs.
  - It still runs at :17690 for the gate order above.
  - The ink centre only triggers the read. The ledger count places the head.
- **Handed to every cell view.**
  - Each cell box standing on a page head gets the same rows under the existing quantities: `Q.NOTEHEAD_STAFF_POSITION`, `Q.FAR_HEAD_LEDGER_POSITION`, `Q.FAR_HEAD_OWNER_LEDGER`.
  - They carry a new reader (CV_PAGE_HEADS) and `page_head=[id]` in detail, and the detector's own value is kept on the row.
  - Consumers do not change.
- **Claim.**
  - Head ink is claimed owner `head`, and ledger stubs owner `ledger`, as `Q.CLAIMED_AREA` rows in the shape M3 and M4 use.
  - `_head_claims` sits beside `_arc_claims` (adjudicators/stroke_owner.py:113-131).
  - Ink an earlier owner holds (arc trace, whole rest, area) is marked contested, never taken.
- **A dyad head the detector never boxed.**
  - The reader files a page head with `source=ink_only`: position, claim, and ledger count. It creates **no Glyph and no note**.
  - That lets the tie test see a head position at that end (a tie is read from position, DECISIONS 2026-11-03).
  - Writing the note needs a Glyph. The only vehicle is a candidate box appended by GATHER, as the stem-end reader does (g:1171-1230), decided in ADJUDICATE and written blue.
- **What ink evidence would let GATHER file one:**
  - A head-shaped blob: at least 0.25 sp² and at most 3.0 sp wide (so:172, so:170).
  - It touches a `Q.STEM` stroke that a boxed head also touches.
  - It sits on the convention's side, or the opposite side for a second (DECISIONS 2026-09-30).
  - No earlier tier claims it, and no box covers 0.5 of it.
  - For a ledger dyad, a rung touches it.
- **Is that allowed.**
  - CLAUDE §3: reading and claiming the ink is allowed.
  - CLAUDE §4: it can only be written GUESSED (blue).
  - §7 is a statement about the detector. Precedent is Sean's 2026-10-29 ruling, scoped to "a stem end with no head box". The dyad's other head is not at a stem end, and the "displaced head of a second" was parked unruled (DECISIONS 2026-10-29). So the note stays out until Sean says yes (question in §7).
- **Out of reach.**
  - Heads fused where the split refuses (`split_refused`, stroke_map.py:122).
  - Ledgers hidden behind a chord mate or merged into a slur (FINDINGS ledger-read 2.255, open).
  - Both stay detector-side or blue and are counted.

## 4. Migration (`OMR_PAGE_HEADS`, default OFF; old reads stay in the tree as the control)
The arms are re-adjudicated records on the same pages and stages.
- **M6a, file only.**
  - Adds `Q.PAGE_HEAD` rows and claims. Nothing reads them. Export is byte-identical.
  - Census through `claim_readout`: heads per page against boxes, ink-only heads, and ink position against box position differing by 0.5 step or more.
  - Controls that can fail:
    - A planted double box must fold to one head.
    - Tile 9 must reproduce 9.38 against an ink position near 10.
    - Brahms p0 black heads stay at 374/378 owning their ink, and the half-head plant must break it (capture-readout FINDINGS).
    - Time and peak RSS on Brahms p5 and p0 (the 2.262 lesson).
- **M6b, views and ledger once.** Cell views plus the folded far read. Retires the per-cell job build (g:1938-1955) and the box-rounded trigger.
- **M6c, claim.** `_head_claims` replaces the box-overlap head claim (so:59) where a page head exists.
- **M6d, only on Sean's yes.** An ink-only candidate box for a non-stem-end dyad head, written blue.
- **Kept as cell detail** (plan-2026-11-03 §B.4): head fill, `head_ink`, `head_oval`, `notehead_ink`.
- **The owner-ledger readers** (`LEDGER_RUNG_INK`, density, ink_under) retire only after the owner rows come from the page head.
- **Each retirement needs three things.**
  1. `python3 -m tools.omr.staged.check`, showing no reader of the old rows is left.
  2. The three measures with the old call skipped.
  3. The old read shown failing where the page read is right (2.217).
- **Default ON.** Only on Sean's tiles, as a deny-list.

## 5. Measures
- **Three measures** (docs/measuring.md:7-23), on the frozen sample, plus capture first for a GATHER lane (:36): `claim_readout` and `claim_order`.
  1. What changed in the exported file, from `lane_report`.
  2. Sean's 12 blind tiles.
  3. Judged right->wrong, which must be 0, and unwritten->wrong, which must be 0.
- **Must move.**
  - The 2.264 tie arcs: litolff_02's family (3 arcs) and the r2 tiles 2 and 9 (tile 9 is "unwritten" in answers-2.260b-r3-rescore).
  - Tile 9's position, 9.38 to 10.
  - The 84 Litolff blue far heads (which record they were counted on is not established).
    - Census them by reason first. The 2.255 reasons are not_a_note, no_rungs, count_does_not_fit and no_line.
    - M6 is expected to fix only the trigger, twin and box-off causes. The no_rungs tail is not promised.
  - A head that gains a pitch or a note is a tile for Sean, not a win.
- **Must not move.**
  - Brahms p0 hand truth (`hand_truth/score.py`). Named hand arcs q1099, q1233, q953, q1071 and q1405 identical. Black heads at 374/378.
  - Judged right->wrong 0. Red bars 42 -> 42.
  - `claim_order` violation and OPEN pairs not rising.
  - Seconds and RSS on p5 and p0 reported, with no budget set because none is established.

## 6. The rule that owns each value M6 may change
- **Pitch and position outside the staff: the ledger lines only.**
  - page-facts:254-282 (Sean 2026-10-01, and 2026-10-27 "focusing on ledger lines") and CLAUDE §5.
  - The ink centre is a trigger or candidate only (head_extent.py:204-209; DECISIONS 2026-10-31 on 2.248 r1's mistake).
  - A head in the first space with no ledger touching it is on-staff (page-facts:270-273).
- **Position is measured locally.** At the head's x or its own bar's lines (page-facts:245-252). `Q.PAGE_HEAD` uses `lines_at` at the stroke's x.
- **Owner: the ledger lines name the owner.** page-facts:223-243, with the stem as a second witness and `OMR_OWNER_LEDGER_WINS`. M6 copies owner rows unchanged. Any change to a pitch or an owner needs Sean's tiles, and a fix that moves one stops and asks.
- **A tie is read from position, not pitch** (DECISIONS 2026-11-03).
- **A stale fact to fix, no question needed.** page-facts:284-287 says a hollow head's position is the box centre, not the hole. Sean's later ruling (DECISIONS 2026-11-03) landed the hole ON, 11/11 right. The M6a commit updates the page-facts line with its scope.

## 7. Risks, and one question for Sean
- **Eraser-thinned heads.** The page map is staff-erased, so a head on a line reads thin. Mitigation is the `trim_head` comparison in M6a.
- **Merged plates.** Litolff merges heads with rungs. The `ledger|head` split (stroke_map.py:742-798) must hold, or the head loses its ink.
- **Gate order.** The ledger count cannot move before the stems exist (g:1706-1710), so claim and count are two places.
- **Wrong twin folds.** Two real heads a unison apart must not fold. M6a's plant control covers this.
- **Brahms cost.** It is unbounded and untimed.
- **Junk ink-only heads.** The first stem-end tiles had 3 of 7 junk: a bar number, a flat, a flag (DECISIONS 2026-10-29). M6d would need the word and accidental claims first.

**Question for Sean** (a grep of page-facts and DECISIONS found no ruling): may GATHER file a head the detector never boxed, when it is head-shaped ink on a stem that a boxed head also touches but not at the stem's end (the other head of a dyad), written blue until your tiles, as the stem-end heads are?
