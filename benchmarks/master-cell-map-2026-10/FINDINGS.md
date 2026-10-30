# ROADMAP 2.231 -- a master cell map (STAGED)

2026-10-29/30, branch `lane-2.231-master-cell-map` (c0ca30b1f). Sean, 2026-10-29: "Is there a master version of each cell - in case multiple passes are needed and so that our test runs are using the same cell/tiles?" -- "Yes". (Written by the manager from the lane's report; the subagent's write was refused by the hook.)

CONVENTION ASSUMED: none about the page. A process assumption only: a lane NOT about cells is measured on the master's cells (`--cell-map`); a lane ABOUT cells (staves, barlines, pads, line removal) re-cuts and lists what it moved (`cell_map moved`). WHAT WOULD FALSIFY IT: a lane that is both -- it must run both ways and report both. NOT CONFIRMED with Sean.

## Cause and process lesson
Cause: a cell is not stored; it is the output of `pipeline.prepare_pages` (render -> detect_staves -> page-wide barlines -> extract_measures -> remove_staff_lines), re-run at the start of every gather. Any upstream change silently changes the pixels every crop-sensitive reader and the detector see: the 2.221 m2 barline lane moved Litolff p9 s1's boundary 1526 -> 1470 and a 0.07 detector rescue on the re-cut crop flipped (a real quarter lost). Tiles and answers keyed by glyph index / cell index are one gather's snapshot and drift the same way.
Lesson: "same pages, same tree apart from the change" was enforced for tree and record, not for the INPUT the readers see. Anything recomputed in both arms is part of the change unless frozen and proved equal by hash, with a mismatch that raises (the detector cache, 2.189, did this for model output; this does it for the crops).

## Prior work
- `git log --all -S extract_measures` (106 commits), `-S cell_index` (51): cells always cut per run; `measure_extractor._build_measure_cell` is the one cutter, re-used here.
- `tools/omr/annotate/recut_cells.py` (+tests): the labeling side met the drift first (labeled cell PNGs not regenerable); its re-cut REFUSES on a frame mismatch -- same stance.
- `benchmarks/omr-cell-grid-tilt-2026-09` (localised grid moves stored rows, never the crop) and `omr-cell-pad-record-2026-09` (a cell records its pad): why the snapshot keeps the grid record and pads, not just the box.
- `tools/omr/detector_cache.py` (2.189): the pattern copied (key that makes a stale hit impossible, RAISE, opt-in arg, stamp).
- `lane_report` frozen sample + slices (2.188): froze pages and saved rows, not the cells of a `--from gather` arm.
- `docs/ink-rules.md`: no rule about cell identity; the padded-cell rules (owned_by_another_staff, belongs_to_a_nearer_staff, crop-edge slivers) are why a moved crop changes readings.
- `benchmarks/page-claim-order-2026-10/FINDINGS.md`: the barline change that moved the p9 cell.

## What was built
1. The record cannot rebuild cells (it holds staff_lines and cell_box, not the grid offset, pads, upscale, columns or pixels), so the builder runs prepare_pages itself (no detector; ~7 s/page Litolff, ~11 s Brahms).
2. Master per pdf+dpi, `library/_shared-records/cell-maps/<pdf-sha16>-dpi600/` (manifest.json + pages/pNNN.json.gz): every Staff and Barline, page extras (system_structure columns, deletion_counts, staged_page_wide, deskew), every cell's scalars, and a sha256 of every pixel array (pixels not stored: ~2 GB raw per Litolff page). Version `cm-<12hex>` = hash of pdf sha + dpi + page geometry hashes; the manifest also names build commit, dirty, OMR_* overrides, sha256 of every tools/omr source loaded when it cut.
3. Loader: render + hash check, rebuild the page's staves/barlines from the master (no detect_staves, no barline pass), cut each stored cell at its box with `_build_measure_cell`, `remove_staff_lines`, whole-snapshot equality. Any mismatch raises `CellMapError`; never re-cuts.
4. `moved` / `verify`: every staff, barline, column, cell (p s st c) the current tree cuts differently, old -> new; `verify` exits 1.
5. Tiles: lane_report key.json rows carry `position` (page, system, staff, cell, page box) and `cell_map` (version or null); `judged` carries them only when present (`judged build --check` current, 1869 tiles, before and after).

## Masters (cutting code identical to 12325ce29, the 20261029-night overnight)
| plate | pages | master | version |
|---|---|---|---|
| Litolff imslp984073 | 1-16 | cell-maps/55d95838e0709b92-dpi600 | cm-54ccb4729528 |
| Brahms imslp317803 | 0-26 | cell-maps/be40c09fbd9f55f0-dpi600 | cm-2d494f8fc055 (built twice, same tag) |

## Controls
- Unit tests (10, synthetic page): loaded == fresh pixel-identical; missing page / dpi / other pdf / moved render raise; perturbed master caught both un-hashed and re-hashed; rebuild needs --force; a planted barline loss moves the re-cut arm and not the loaded one.
- Litolff p9-10, --through adjudicate, shared detector cache: fresh vs --cell-map records IDENTICAL apart from provenance; 619/619 cell_box equal; loaded arm 2123 detector-cache hits, 0 misses.
- Fails where it should: OMR_BARLINE_SYSTEM_COLUMNS=0 -> `cell_map verify` exit 1, "barlines p9 s1: removed [1470] added [1526]", 20 cells p9 s1 st0-9 c5/c6 bbox 1470 -> 1526. Re-cut arm moved those 20 boxes (74 detector misses); loaded arm kept all 619 (0 misses), its only other difference the gather-side barline claim the same flag controls.
- Against the overnight: `against-record` on beethoven5-litolff-mvt1-whole-20261029-night (12325ce29), pages 1-16: every cell box and staff equal, 0 mismatches. Control: the 20261022-night record on p9-10 DISAGREES on exactly the 20 p9 s1 c5/c6 cells.
- Brahms against its overnight record: pending the Brahms gather (see below).

## How to use it
`docs/running.md` §2b. A lane not about cells: `lane_report ... --from gather --cell-map master`; a lane about cells: `cell_map moved|verify PDF --pages ...`; after a staff/barline change lands: `cell_map build PDF --pages ... --force` then `cell_map against-record PDF REC`.
