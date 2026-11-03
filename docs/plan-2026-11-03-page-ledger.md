# Plan 2026-11-03 — the page is the ledger (ROADMAP 2.260 step 2; finishes 2.240 steps 4-5)

STAGED. Design step, no code (Sonnet design agent, tree 53712c264; filed by the manager). Approved direction, Sean 2026-11-03: "Which of our symbols actually benefits from being cut down by the cell? ... I wonder if we shouldn't have the page-wide read be the primary place we are storing all of our information, and then go into the cells for specific details." -> "Open another slot and start it this way".

## The principle
The cell cut helps nothing by itself; the cell bundles three separable things: (1) ZOOM for the detector (weights tuned on cell crops -- the detector input never changes), (2) the BAR as an index for rhythm/voices/bar sums, (3) the LOCAL STAFF (measured at the subject's x -- works in page coordinates). So the PAGE record is the one ledger: every mark in page coordinates, claimed once; a cell is a VIEW (detector crop mapped back) plus a bar index; a cell is entered only for fine detail (head fill, dot beside a head, accidental shape) and the result is written back to the page mark, keyed with provenance, never to a cell id alone.

## A. Cause (why 2.240 steps 4-5 were never built)
- Step 4 looked mostly done: 2.221 m2 (10-29) landed page-wide tilted barline columns (Theil-Sen, `measure_extractor.py:1290-1299`) and claims the whole rule (`gather.py:295`), but cells are still cut at `bl.x`, the stroke map still sees two half-barline strokes on 78% (Litolff) / 83% (Brahms) of staff-barlines, and arc/hairpin/barline claims name cell-local ordinals `[[cell, ordinal]]` (`stroke_owner.py:119`).
- Step 5 (page stroke map) "changes every erased-raster consumer at once" and had no symptom of its own -- rank 7 on the 11-02 big-items list. 2.231 froze the cell as the unit of reproducibility; detector labels are cut on that frame.
- Its costs arrived as separate lanes (2.204 barline abstentions, 2.259 clipped beams, 2.258 arc pieces), each patched locally.
- **Process lesson:** a design whose big step has no symptom queues behind the lanes that carry its symptoms, which keep paying for it one reader at a time.
- 2.260 step 1 audit: no stage after GATHER reads pixels; GATHER files cell-framed records (boxes, Q.STROKE, Q.BEAM_STROKE_INK, Q.GLYPH_BOX) and later stages re-judge cut pieces; strokes carry no "cut by the cell edge" fact (`stroke_owner.py:133-143`).

## B. Design
1. **Page stroke map** (GATHER, decides nothing). Strokes in page px: kind, length, thickness, run measured once on the page raster; staff position at the stroke's own x (`LocalStaff`); one id, later one claim owner. Assembled, not recomputed: each staff's own erased band (top line -0.5 sp .. bottom line +0.5 sp) from its `cell.image_no_staff`, placed by `bbox_page_px` / `upscale_factor` (`gather.py:7912`); everything outside the bands from `page.binary`. The frozen eraser is reused; each neighbour's lines are erased by its own band (removes the 118 / 508 flat tie/beam boxes on another staff's line). Built after the detector and structure (`map_strokes` takes detector boxes, `gather.py:7894`), before any claim or per-bar reader, after the tilted barline column is carved out (else heads/stems touching a barline fuse). Detector boxes map to page px by the same transform; step-1 page marks de-duplicate twins. Size (estimate, unmeasured): ~60-100 MB transient label array per page, memory neutral to slightly lower (cells overlap ~1.3x); Q.STROKE rows shrink ~17-19%; record ~1% of Brahms' 1.87 GB; peak 12.3 GB unchanged (dominated by verdict payloads). Measure with `.nbytes` + 2.249's peak-RSS line on 2 pages per plate.
2. **Bar index.** Keep the key (page, system, cell) (page-facts :281). A mark's bar is decided by its x against the tilted column at its own y, stored as a table over page marks/strokes. Changes membership only for edge ink (tilt >= 0.45 sp on 2.8% of Litolff staff-barlines; 501 L / 1,157 B edge-straddling slurs, ties, beams, hairpins).
3. **Readers that move first:** beams, flags, stems read outward from each stem tip on the page map -- replacing the five beam reads on one cell (`gather_cv_lines` gather.py:5056, `gather_detector_beams` :12314, `gather_beam_stroke_ink` :12686, `gather_beam_stem_levels` :12849, `stroke_map`) and their re-judges (`rhythm.py` `_not_a_beam_by_ink` :1802 / too_thin :1891, tip readers, `_beams_from_strokes` :4120). Then barlines as tilted columns; then arcs as 2.258 allows; far-note ledgers last (2.217 parked: old reader beat the stroke reader 9/9 vs 0/9 -- check the old reader fails first).
4. **Stays a cell detail, writes back:** head fill, augmentation dots, accidental shape, all detector reading.
5. **Interim guard:** a `cut` fact on the stroke (edge contact top/bottom/left/right, ignoring the page border); a cut stroke makes a reader say "cannot tell" and count it, never refuse (rule 8). The honest form of the parked 2.259 patch.

## C. Migration (each step its own default-OFF flag and ROADMAP sub-row; three measures on 2 pages per plate, master cell map `--cell-map`)
- **M0 `OMR_STROKE_CUT_FACT`** -- `stroke_map.py` + refusals at `rhythm.py:1891` and the tip readers. Parked patch gave Litolff p6+p16 notes +4, beams +4, judged right->wrong 0; ~40 clipped beam strokes on 9 L pages; 105 L heads duration_narrowed.
- **M1 tilted barline column fact** (no behaviour change) -- slope/intercept per column; refit in staged or one line gated by `staged_page_wide` in `_system_barline_columns` (2.221 precedent). Prerequisite for M2.
- **M2 `OMR_PAGE_STROKES`** -- assemble and file the page map beside the cell strokes; nothing reads it. Controls: stroke parity inside one band with no overlap (a perturbed raster must break it); half-barline strokes 78%/83% -> 0. File byte-identical.
- **M3 claim translation** -- `[[cell, ordinal]]` -> page stroke ids for arc, hairpin, barline, word claims; 2.258's trace plugs in here.
- **M4 `OMR_PAGE_BEAMS`** -- one beam reader on page strokes replacing the five reads. Bounded by 105 L duration_narrowed heads; Brahms unknown.
- **M5** barline carve and bar membership by column; retire the per-cell barline claim only where the column claim already refuses/narrows every box it did; 2.204 stems can revive.
- **M6** heads (extent from own ink, Sean's big item 1) and ledgers, old reader as control.
`measure_extractor.py` and `staff_line_removal.py` (LEGACY-shared, frozen) are read, never edited, except the one gated line in M1.

## D. Risks and conflicts
- Detector: crops/pads/imgsz/weights unchanged; assembly reads cells, so use the master cell map.
- Claim order: the map is a fact, built after structure and before any claim; claims name page strokes; a later reader marks, never takes. Cell ordinals and page ids side by side during migration are the main bug source.
- New fusion (head/stem touching a barline) -- the M1 carve first.
- **For Sean:** `docs/page-facts.md:211-215` is stale (says cross-staff ownership is ladder -> range -> distance; step 3 landed the page owner first and Sean found distance/range_veto wrong 11/11 where they overrode it).
- **For Sean to confirm:** DECISIONS 2026-10-16 (2.152: "36 of 84 judged errors are head values / beam counts only the cell can read") -- the page map keeps 16 px/sp, the same resolution, read as compatible.
- DECISIONS 2026-10-29 (no new reading pass per symbol): the page map replaces the per-cell map, so passes do not increase; each step reports added seconds per page.

## E. Open question for Sean
Guard first (M0: a cut stroke says "cannot tell"), or straight to the page stroke map?
