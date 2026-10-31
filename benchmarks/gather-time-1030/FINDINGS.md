# Brahms overnight slowdown 224 -> 352 min (20261022-night a2eae6880 -> 20261029-night 12325ce29) -- diagnosis (STAGED)

Branch `lane-gather-time-1030` 63cc667da (timer harness `timed_run.py`, `results/*.timers.json`). Written by the manager from the lane's report; diagnosis only, nothing changed.

## Cause and process lesson
1. MEASURED: per-page CPU is only ~10-13% higher on the new commit (p5 alone 292 -> 319 s; p5+p12 490 -> 555 s, cache warm, serial). New readers add it: stroke_map +9 s/page, head_ink +6, key_object +2, ADJUDICATE stroke_owner +1.5, printed_bar_numbers +1.5, page_claims +1.3, arc_claim +0.8; offsets gather_stem_end_heads 39 -> 21 s and fewer model calls (3301 -> ~3036 per 2 pages). Largest single reader unchanged on both: far_head_ledger_positions ~35 s/page.
2. INFERRED (not measured on the whole run): the remaining ~100 min is memory pressure. Peak RSS slope per page ~2.1 GB (A) -> ~3.5 GB (B, +67%); linear to 27 pages A ~62 GB, B ~97 GB on a 64 GB machine; swap 6.4 of 7.2 GB used when checked. Predicts small slowdown on few pages (Litolff 16 pages: 67 -> 68 min) and large on the whole Brahms movement. The overnight logged no RSS/swap, so this is a prediction.
3. Record write is small: ~15 s/GB, ~5 min for 19.6 GB vs ~2.5 for 8.8 (+3 of the +128 min), but it holds a ~20 GB string in RAM at the end.
4. NO duplicate pass: every gather_* and stage entry point is called once per page.
Lesson: a wall-time total with no per-stage, per-page or memory record cannot tell "more work" from "same work, swapping"; a record that grows 2.2x is a RAM problem before it is a disk problem. The per-verdict payloads (duration 4.0 GB, voices 7.3 GB, stem_value 2.4 GB of 19.6) should be slimmed or flushed before more readers go in -- shared ink map step 9 (`OMR_SLIM_BASIS`). Compare warm with warm: a cold detector cache (+180 s) made B look +48%.

## Per-stage seconds (warm, serial, shared box)
| run | gather | adjudicate | groups+evaluate+infer | to_json+dump+write | total |
|---|---|---|---|---|---|
| p5+p12 A | 374 | 83 | ~6 | ~8 | 490 |
| p5+p12 B | 411 | 93 | ~6 | ~11 | 555 |
Brahms is GATHER ~75-80%, ADJUDICATE ~15-20%. 4-page runs were noisy from other lanes' load (one Surya call 246 s vs 18 s) and are not used.

## Proposed (not built)
Stamp per-stage seconds, per-page gather seconds, peak RSS and swap into the record's provenance in the overnight run.
