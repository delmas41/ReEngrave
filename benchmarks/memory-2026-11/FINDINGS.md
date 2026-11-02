# 2.249 — Brahms fits in memory (STAGED; Sean "Memory fix", 2026-11-01)

Written by the manager from the two lane reports (afc3069d, a8726c33); the
lane hook refuses subagent FINDINGS writes. Branch `lane-2.249-memory`.

## Cause and process lesson

- **m1 cause (GATHER):** `pipeline.prepare_pages` rendered and cut EVERY page
  before gathering the first and held them to the end: Brahms 0-5 RSS 24.4 GB
  after prepare (15.4 GB image arrays, ~2.6 GB cell images per page). The
  record was then built as one string (`json.dumps` +7.3 GB, encode +1.9 GB).
- **m2-m5 cause (ADJUDICATE / write):** a verdict's `basis` was stored as its
  full transitive closure. A verdict consulting a document-wide verdict (key,
  clef, staff identity, meter) takes in every page's rows, so each basis grows
  with the page count and the total with its square. Brahms 0-3: an
  `arc_owner` basis averaged 11,390 ids, 37% on other pages (`basis_reach.py`).
  `basis` is ~95% of the record file (Litolff 20261031: duration 739 MB,
  voices 697 MB, stem_value 560 MB; the largest `detail` key 12 MB).
- **Lesson:** a few pages cannot predict a whole movement when a stored value
  holds a closure — ask how each stored field scales with document size, and
  use a memory measure that can fail.
- **Measuring errors found:** macOS RSS overstates (freed large blocks stay
  resident as `MALLOC_LARGE_REUSABLE`; 10.4 GB RSS vs 3.7 GB footprint on
  Brahms 0-1) — the run meter and `sample_pid.py` report `phys_footprint`.
  `mem_run.py` held every page alive through `_seen_pws` (fixed). Record bytes
  depend on the hash seed (`stroke_owner` census iterates a set): compare
  records under `PYTHONHASHSEED=0` (existing nondeterminism, not fixed).
- **Identity arms run serially on an idle machine.** Surya's 20 s per-crop
  guard (`crop abandoned ... 20.0s`) falls back to tesseract under load and
  changes margin labels and words; check every word/label difference against
  that arm's abandoned-crop lines before believing it.

## Changes

- m1 (e81d3bd25): `pipeline.PreparedPages` prepares one page at a time;
  `record_io.dump_to_file` streams the record (byte-identical,
  `test_record_stream.py`); `run_meter.py` prints a `[run]` line per page and
  stage and writes `provenance["run"]`.
- m2 (00ba3557f): `Log.drop_memos()`; closure memo released per quantity.
- m3 (01fa0780d): cyclic GC paused while pooling and writing.
- m4 (44fe04749): `LazyBasis` — basis held as `considered`, spelled out only
  when read; closure walks the considered graph; memo capped at 30M ids.
- m5 (cb034cb3e): bases stay lazy through `to_json` (CLI); pooling planned
  once and applied per verdict as written.

## Identity

- m1 vs main d2223f51c (serial, shared detector cache; `identity/`):
  Litolff 1-4 MusicXML identical, 0 of 41,289 verdicts differ by (quantity,
  subject). Brahms 0-5: pages 0-3 identical row for row; 81 of 102,533
  verdicts on pages 4-5 differ, all from 2 Surya failures in the base arm
  (p4 staff 4/0/4 label `|` vs `K-Fag.` → Bassoon m68 B♭ plain vs blue
  natural; p5 `Cresc` read in the branch; p5 alone reads identically).
- m2-m5: replay of saved GATHER rows through EXPORT (`replay.py`,
  `PYTHONHASHSEED=0`, arm A = tree before m2): record and MusicXML
  byte-identical on Litolff 1-4, Brahms 0-3 and Brahms 0-5.

## Measures

| | before | after |
|---|---|---|
| Litolff 1-4 (m1) | 695 s, 13.5 GB RSS | 463 s, 7.3 GB RSS (4.3 footprint) |
| Brahms 0-5 (m1) | 3232 s, 44.2 GB RSS | 2795 s, 22.0 GB RSS (6.3 footprint) |
| Litolff 1-4 live after ADJUDICATE (m4) | 1.17 GB | 0.23 GB |
| Brahms 0-3 live after ADJUDICATE (m4) | 3.60 GB | 0.71 GB |
| Brahms 0-5 replay peak RSS (m4+m5) | 13.2 GB | 6.0 GB |
| Brahms 0-5 ADJUDICATE (m4+m5) | 541 s | 271 s |
| Brahms 0-5 record write (m4+m5) | 212 s | 429 s (re-spells bases; win 4) |

**Whole Brahms, m1-m3 tree** (pages 0-26, another lane beside it):
completed, exit 0, 15,529 s. GATHER 8,936 s (footprint 2-8.5 GB throughout),
ADJUDICATE 3,096 s (footprint to 46 GB), GROUPS 27 s, EVALUATE 2,005 s,
INFER 555 s, record write 642 s (35.5 GB record), peak footprint 55.9 GB in
`to_json`. The 20261031-night run on main was killed after 12 h 49 min.
m4+m5 on the whole movement is NOT measured (estimate 10-15 GB peak);
Sean decides the run.

## Remaining wins (estimates, ranked)

1. Record file quadratic in pages (35.5 GB at 27): store `considered`, drop
   the derivable basis — linear (~3-5 GB), write ~10x faster. CHANGES THE
   RECORD FORMAT — Sean's item.
2. EVALUATE superlinear (2,005 s whole vs 45 s on 4 pages): profile a 6-page
   replay; m4 may already help.
3. GATHER `far_head_ledger_positions` ~40% of GATHER (~82 s/page Brahms):
   89% is `cv2.resize(INTER_AREA)` in `head_template._window`; a per-head
   window cache could be byte-identical. Not measured on Litolff.
4. Lazy write re-spells bases (Brahms 0-5 write 212 → 429 s): spell once per
   pass.
5. Surya readers: direction words ~21 s, margin labels ~8 s per Brahms page.
6. Sort `stroke_owner` rivals so records compare without a fixed seed —
   changes census key order in the file — Sean's item.
