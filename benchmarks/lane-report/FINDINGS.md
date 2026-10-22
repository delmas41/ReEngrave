# 2.188 -- the shared lane report (tooling, no default)

Command: `python3 -m tools.omr.staged.lane_report --flag OMR_X --out DIR` (docs/running.md §2b). STAGED, ADJUDICATE..EXPORT replay of the
20261020-night records; a GATHER flag re-gathers (`--from gather`, built, NOT run end to end -- needs two detector gathers; first
user should smoke it on one page).

**Frozen sample** (`sample.json`, seed 2188, `random.Random(2188)` over every page of the record holding staves, nothing excluded):
Litolff pages 2 4 6 8 9 10 11 16 (of 1-16); Brahms pages 0 4 5 8 12 14 19 25 (of 0-26). Each plate also LOADS its opening page
(Litolff 1, Brahms 0 -- in the Brahms sample anyway) and never counts it: the first run, without it, could not size a whole rest
(606 `size_measure_rest` verdicts missing) because the meter is printed on page 1 -- a slice is only faithful with the page whose
meter/key every later bar inherits.

**What the controls showed (CLAUDE rule 7).**
- Identity (unknown flag, OFF==ON): first build reported "+185 -185 notes" on Litolff -- padding rests/notes written with no glyph box were
  paired by list; fixed (they are counted per bar, never paired); now `NOTHING CHANGED` on both plates.
- OFF reproduces the record: Litolff 8958/8958, Brahms 12324/12324 duration/rest verdicts (row ids blanked: a slice renumbers rows).
- Known effect, `OMR_DOT_POSITION_OVER_WEDGE` (landed ON 2.180; OFF=0 vs ON=1): Litolff nothing; Brahms notes +6, dots +16, ties +6,
  articulations +1, blue -7/+4, red bars 174 -> 166, judged wrong->right 4, right->wrong 0. The control line says ON reproduces the
  record (default-ON flag), OFF moves 20 verdicts -- as it must.
- Tiles: 12 (9 changes stratified by kind, 3 controls), orange box, key outside the folder; looked at the sheet, boxes sit on the symbol.

**Wall time** 11 min for both plates at `--workers 4` (Brahms ~10 min an arm), 16 min at the default 2. First run adds ~2 min of slicing.
That is "minutes", not seconds: the cost is the ADJUDICATE..INFER replay of ~9 dense pages per arm.

**Known limits.** Pairing is by page position (a symbol with no glyph box is counted per bar, no tile). Red-bar warning words show as
`words`. A flag read at import time is safe (one process per arm); a flag read only in the web path is not exercised. Context page
means a cross-page rule that needs a page other than the opening one is not reproduced (the control line would say so).

**2.188b (2026-10-21): tiles follow the counts.** `pick_tiles` now draws the ~9 case tiles in proportion to how many changes each kind has (largest remainder; any kind with >= 10% of changes gets at least one), not one per kind. Found on 2.186, where 201+58 accidental changes got one tile. Test: `test_tiles_follow_the_counts_and_a_tenth_gets_one` (twin: a 5% kind gets none).

# 2.189 -- read the page once (detector raw-output cache)

**Level cached: BEFORE NMS.** `YoloDetector._predict` (the 3 `predict` call sites in `yolo_detector.py`: `detect`, `detect_image`, `detect_view`; every gather pass,
routed and second weights included) calls `tools/omr/detector_cache.py`. A miss runs ultralytics unchanged and, while it runs, takes the head tensor's candidates (every
anchor whose best class beats the conf floor; taken BEFORE `non_max_suppression`, which converts xywh->xyxy in place) plus the letterboxed shape. A hit rebuilds the tensor
and runs ultralytics' own NMS (the CALLER's `iou`, `agnostic_nms`) and `scale_boxes`. So a lane that changes NMS or anything merged after it is served from the cache.
Probe on the production weights: warm == no cache after changing iou 0.7->0.5 and agnostic False->True, served with no model call (0.003 s vs 0.3 s).
**Cannot serve:** a changed conf floor, crop pixels / `imgsz` / view / shifts / anti-alias, weights, multi-label NMS (all are a different key = a miss, a fresh read).
**Key:** weights-file sha256, ultralytics + torch versions, device, conf, `imgsz`, shape + dtype + pixel sha256 of every image. dpi and view are in the pixels; `iou` and
`agnostic_nms` are applied at serve time, not keyed. Truncated / non-zip / misfiled / edited-payload entries RAISE `DetectorCacheError` (unit-tested). The cache is not a
recorded setting (`OMR_DETECTOR_CACHE`, `--detector-cache` are left out of the record's provenance, so a cached record equals a fresh one).

**Controls (CLAUDE rule 7), all run.**
- (a) Byte-identity of the gather record, ids included, on 2 sample pages per plate (Litolff 2,4; Brahms 0,4), `PYTHONHASHSEED=0`, timing `ms` fields and the cache env stripped:
  Brahms no-cache == cold == warm; Litolff no-cache == warm (and, earlier, no-cache == cold). Two things that are NOT the cache and differ between ANY two runs: the
  `ms` timing fields, and (with the default hash seed) the order of a 2-element set in two `discounted_own_structure` lists and a count `page_n_rejected_by_lexicon` 59 vs 61 on 27
  abstentions (seen warm vs cold on Litolff before fixing the seed; a no-cache rerun differs from the first no-cache run the same way). Fixing the seed removed both.
- (b) A key part changed is a miss, on the real weights: conf 0.25->0.20, one pixel, `imgsz` 1024->1056 each missed; the unchanged call hit (and 10 unit tests: conf, pixel,
  imgsz, weights, shape, batch, four corruptions).
- (c) A merge-only flag through `lane_report --from gather` from the warm cache == a fresh read: one page (Litolff 2, `OMR_RECENTRE_PART_BOXED`): report identical warm vs
  `--detector-cache off`, but "NOTHING CHANGED" there, so it could not fail; the whole Litolff sample then ran twice: cold (OFF read fresh, ON served from the OFF arm's cache) and
  fully warm give the SAME report (notes +1 -1, flags -1, ties +2, words +1 -1; judged wrong->right 2), i.e. the flag moves the file and the cached ON arm reproduces it.

**Wall time.** One full `lane_report --from gather --plates litolff` (8 pages, two arms): cold 3666 s (OFF 10027 detector calls missed, ON 10047 hit), warm 3045 s (all 10047 hit,
detector seconds served 82 + 74). Saving ~10 min of 61 (-17%) cold->warm; the cold run already had ON warm. Two pages, one arm, no other lane: Litolff no cache 564 s, warm 463 s;
Brahms no cache 1031 s, warm 831 s. A cold miss costs more than a plain call (Brahms 2 pages: 1430 s vs 1031 s on a loaded box: the pixel hash, candidate extraction and
compressed write).
**Size:** 8 Litolff sample pages 29 MB (~3.6 MB/page); Brahms 2 pages 7.2 MB. Projection (not built): Litolff 16 pages ~65 MB, Brahms 27 pages ~100 MB. Persistent sample cache:
`library/_shared-records/detector-cache` (47 MB on disk, Litolff sample filled).
**Merge check:** `git merge-tree` with `origin/lane-2.186-one-ink-one-mark`: no conflict (the seam is 3 one-line `predict`->`_predict` edits plus one method).

**Step 2 (overnight): the detector is a SMALL share, so the overnight script was left as it was** (Sean/coordinator: stop if small). Measured with the seam's timers on
the plain path, 2 pages per plate (gather, `OMR_DETECTOR_TIMING=1`): Litolff 137 s of 564 s (24%), 2719 calls; Brahms 98 s of 1031 s (9.5%), 1961 calls. Scaled to the
overnight wall times (66 / 233 min): a warm cache would save ~16 min on Litolff and ~22 min on Brahms (warm-run measurements agree: -18% / -19%, noisier). The remaining 76-90% is
elsewhere: a cProfile of one Litolff page (below, if it ran). `OMR_DETECTOR_CACHE=DIR` still works on any CLI run, including the overnight script, if Sean wants the ~15-20%.
