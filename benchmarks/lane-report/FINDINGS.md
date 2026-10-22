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

# 2.189 -- read the page once (detector raw-output cache; STATUS: built, controls pending)

**Level cached: BEFORE NMS.** `YoloDetector._predict` (3 call sites: `detect`, `detect_image`, `detect_view`; every gather pass goes through them, incl. routed
and second weights) calls `tools/omr/detector_cache.py`. A miss runs ultralytics unchanged and, while it runs, takes the head tensor's candidates (anchors whose
best class beats the conf floor; taken BEFORE `non_max_suppression`, which converts xywh->xyxy in place) plus the letterboxed shape. A hit rebuilds the tensor and
runs the same NMS (caller's `iou`/`agnostic_nms`) and `scale_boxes`. A real-weights probe on a synthetic crop: cold == no cache; warm == no cache, including after
changing iou 0.7->0.5 and agnostic False->True (served from the cache, 0.003 s vs 0.3 s). Cannot serve: conf floor, crop pixels/imgsz/view/shifts, weights,
multi-label NMS (all are a different key = a miss).
**Key:** weights-file sha256, ultralytics+torch version, device, conf, imgsz, shape/dtype/pixel sha256 per image. dpi and view are in the pixels; `iou`/`agnostic` are
deliberately not in the key (applied at serve time). Corrupt/partial/misfiled/bad-checksum entries RAISE (unit-tested: truncated, non-zip, wrong filename, edited payload).
**Tests:** `tools/omr/tests/test_detector_cache.py` 10 pass (cold==warm==none, NMS change served exactly, conf/pixel/imgsz/weights/shape each a miss, batch, corruption).
**Merge check:** `git merge-tree` of this branch with `origin/lane-2.186-one-ink-one-mark`: no conflict (the seam is 3 one-line `predict` -> `_predict` edits + one method).
**Measured so far:** Litolff pages 2,4 gather with no cache: 818 s (record 137 MB). Controls (a) cold/warm/none byte-identity, (b) on real pages, (c) merge-only flag through lane_report
from a warm cache, and the cold-vs-warm lane_report wall time were NOT run: the box had another lane's lane_report gathers queued (hours) and the disk fell below the 15 GB floor
(Sean/coordinator 2026-10-21), so the runs were stopped. Script: `/private/tmp/claude-501/ctrl189/ctrl_a.py` pattern (none, cold, warm; sha256 of the record; delete after hashing).
**Step 2:** `benchmarks/acceptance/overnight/regather_20260930.sh` now exports `OMR_DETECTOR_CACHE=$OUT/detector-cache/<id>` and writes
`python3 -m tools.omr.detector_cache summary LOG` (hits/misses, detector seconds, weights hash, bad entries) to `summary.txt`; `DETECTOR_CACHE=off` disables. Time split and cache
size per movement: NOT MEASURED yet (needs the controls' gathers; whole-movement cache is a projection only).
