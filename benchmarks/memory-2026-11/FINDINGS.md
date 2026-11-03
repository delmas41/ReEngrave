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
- **m6 cause (INFER 555 -> 11,689 s on the whole movement, m5):** m4 cleared
  the closure memo whole at its cap (and m2 after every quantity), throwing out
  the document-wide closures every walk passes through. 6-12 pages never hit
  the cap. **Lesson:** a cache cleared at a bound behaves differently only
  under the whole document's working set -- test a cache by shrinking its
  bound on a slice (Brahms 0-11 at a 6M cap reproduced it: INFER 57 -> 620 s).
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
- m6 (75d34b66e): closure memo evicts least-recently-used (60M ids), never
  cleared per quantity.
- m7 (fbab71f89): a LazyBasis is spelled by one walk (`closure_of_many`).
- m8 (ed8770f37): **record format 2** (Sean 2026-11-02, DECISIONS): an
  ADJUDICATE verdict stores `considered` + `basis_from: "considered"` and no
  `basis`; the basis is derived on read (`record_io.RecordBasis`). Format-1
  records load as stored. Compare across formats with `same_record.py`.

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
- m6/m7: record md5 + MusicXML identical to A on Brahms 0-5, 0-11, Litolff 1-4.
- m8 (6b9fcf458, `identity/{l14,b05,b011}.txt`): SAME RECORD by
  `same_record.py` (every row, derived bases spelled) and MusicXML
  byte-identical to A on Litolff 1-4 (42,063 verdicts), Brahms 0-5 (104,513)
  and Brahms 0-11 (198,285).

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
m5 on the whole movement (30,262 s to INFER end): footprint 13.8 GB but INFER
11,689 s (cause m6); the write died on a full disk.

**m8 replays vs A (pre-m2), seconds:** Brahms 0-11 record 4.63 -> 0.65 GB,
ADJUDICATE 1,256 -> 286, INFER 99 -> 36, write 144 -> 11, footprint 18.9 ->
8.6 GB; Brahms 0-5 record 1.81 -> 0.36 GB; Litolff 1-4 0.46 -> 0.12 GB.

**Whole Brahms, m8 tree** (6b9fcf458, pages 0-26, idle machine, Sean "Run it"
2026-11-03): exit 0, **10,780 s** (was 15,529). GATHER 7,125 (idle machine),
ADJUDICATE 1,055 (3,096), GROUPS 27, EVALUATE 1,964 (2,005), INFER 487 (555),
bounded EVALUATE 20, record **1.87 GB written in 27 s** (35.5 GB, 642 s),
**peak footprint 12.3 GB** (55.9). MusicXML 7.5 MB, complete. Not compared
against an earlier whole-movement record (the slices are the identity proof).

## Remaining wins (estimates, ranked)

1. DONE (m8): record file linear, 1.87 GB.
2. EVALUATE is now the largest stage after GATHER (1,964 s whole vs ~40 s on
   4 pages): it does not read closures; needs its own profile.
3. GATHER `far_head_ledger_positions` ~40% of GATHER (~82 s/page Brahms):
   89% is `cv2.resize(INTER_AREA)` in `head_template._window`; a per-head
   window cache could be byte-identical. Not measured on Litolff.
4. DONE (m7/m8): the writer spells no basis. Tools that read many bases
   (review viewer, rerun diffs) now pay a walk per basis on read.
5. Surya readers: direction words ~21 s, margin labels ~8 s per Brahms page.
6. Sort `stroke_owner` rivals so records compare without a fixed seed —
   changes census key order in the file — Sean's item.
