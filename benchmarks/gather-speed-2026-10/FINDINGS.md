# ROADMAP 2.191 -- gather speed, output unchanged

## Cause (cProfile, warm detector cache, one page per plate; STAGED gather)
Litolff p2 (253 s profiled) and Brahms p4 (461 s). Plain words:
- **Not one hot loop: it is waiting plus C calls on many small cells.** Surya (separate llama process) 21-25 s a page, a `tesseract` process per direction crop 12 s (Litolff) / 38 s (Brahms) run ONE AT A TIME, OpenCV connected-components/morphology/resize on ~400 cells, imports (~20 s, slow disk).
- **`provenance` runs three `git` calls in a row** (rev-parse, status, ls-files): 49 s (Litolff) and 104 s (Brahms) in the profiled runs on this box. Fixed cost per run, but it is most of a one-page lane measurement.
- **Beam-stroke ink** (`beam_stroke_ink` + `local_line_thickness` + `_median_filter_1d`): per-column python loops, `_ink_runs` called 2.4 M (Litolff) / 3.8 M (Brahms) times; 18-25 s a page.
- **Brahms far-head ledger reader** (`head_template._best_for`): 71.6 s of one Brahms page (16%). It cuts and `cv2.resize`s the same candidate window (2.4 M resizes) and re-centres it for each of the 2-3 templates scored over one grid.
- **`_ink_components`**: pure function of a cell's erased raster, run 3x per cell by five readers (~4 s).
- Adjudicate (20 s / 55 s) is already tuned (memoised closures); the rest is spread thin.

## Process lesson
A page-time claim is cheap to check and was wrong twice here: wall time on this shared box swung 2x between identical runs (448 s vs 738 s Litolff, other lanes' pytest/gathers), so speed is judged on CPU seconds (user+sys), and "the detector is the slow part" (2.189's guess) was 24%/10%. Also the first "before" run on a freshly checked-out base tree (b2_lit) disagreed with its own rerun (b3_lit) in the 2.186/2.190 fields; the rerun matched the after-run exactly. A single run is not a baseline; rerun the baseline once.

## What changed (all behaviour-identical, no flag, no threshold)
1. `gather._best_overlap_runs` replaces the per-column `_ink_runs` + max-overlap loop in `beam_stroke_ink` and `local_line_thickness` (same float arithmetic, strict `>` = first of equals); `_ink_runs` and `_median_filter_1d` without np.diff / per-window np.median.
2. `gather._ink_components` keeps its answer on the cell (checked against the raster object).
3. `staff_labels_tesseract.read_crops_text`: crops OCR'd by up to 4 threads, order preserved.
4. `head_template.match_head_template`: each (dx, shift) window cut once for all templates; centred masked vectors memoised per (array, mask).
5. `__main__._provenance`: the three git calls run together.
Test: `tools/omr/tests/test_gather_speed_2_191.py` (each fast routine against the old routine on random input; includes a perturbed reference that must fail).

## Control (same main efa099d7f for both arms; PYTHONHASHSEED=0; `ms`/timing, provenance and worktree paths stripped)
- Litolff p2,4: base rerun == mine, 0 differing record fields, MusicXML byte-identical, coverage json identical.
- Brahms p0,4: MusicXML byte-identical; record identical except `page_n_rejected_by_lexicon` on the direction-word abstentions (43-69 values). The unchanged code differs from ITSELF in that field between two runs (before_bra vs before_bra2: 26 values; Surya read varies run to run), so it is excluded from the control, not hidden.
- It can fail: `BEAM_INK_CORE_RATIO` 1.75->1.5 in my tree -> 513 differing record fields (the beam `core` block) on Litolff p2,4 against the unperturbed record, MusicXML unchanged at that layer (so the record, not the file, is the sensitive control).
- Earlier arm on the previous main (94ade02b9): Litolff identical, Brahms same exception, XML identical.

## Seconds (2 pages per plate, warm shared detector cache, one gather at a time but other lanes loading the box)
| | wall base | wall mine | CPU (user+sys) base | CPU mine |
|---|---|---|---|---|
| Litolff p2,4 (main efa099d7f) | 448 | 410 | 256 | 213 |
| Brahms p0,4 (main efa099d7f) | 961 | 636 | 630 | 582 |
| Litolff p2,4 (main 94ade02b9) | 348 | 407 (loaded) | | |
| Brahms p0,4 (main 94ade02b9) | 966 / 1041 | 765 | | |
Cold (no detector cache) was not re-measured: the model call is unchanged, so the cold cost is warm plus the 2.189 miss cost.

## Proposals that WOULD change output or risk it (Sean to decide)
- Skip `detect_beams` in `gather_stem_end_heads` (it only reads `stems`): ~3-4 s a page; changes behaviour only if beams would have raised.
- Run Surya crops as one batch / fewer dispatches (41-51 per page): changes read order effects possibly.
- Drop the slide grid step in `head_template` (SLIDE_STEP_PX) or prune dx: changes scores.
- Cache cells' `detect_stems` across gather_cv_lines and stem_end_heads (different args today: noteheads/marks differ, so not identical).
- Move `_provenance` off the critical path entirely (stamp at start): the stamp could then name a tree edited during the run.
