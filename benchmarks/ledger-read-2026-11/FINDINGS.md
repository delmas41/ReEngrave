# 2.255 -- read the ledger lines better (STAGED GATHER; Sean 2026-11-02)

Written by the manager from the lane report (lane-2.255-ledger-read 0733a0771; the hook refused the lane's FINDINGS write). Flag `OMR_LEDGER_READ`, default OFF.

## Cause and process lesson

No single big cause: far heads whose ledger count abstains are a long tail of ink cases. One mechanism isolated and proved: the ledger walk takes the band nearest one pitch out; Litolff's hand-drawn ledgers sit 1.0-1.3 sp apart, so the head's own flat outline row is often nearer that pitch than the real ledger, and the post-walk filter then drops the outline AND every ledger past it (`glyph/6/1/7/11/0`: ink at 3041/3025/3006, Sean "ledger 3", walk took the outline at 3016 and saw one ledger). Other misses: a ledger hidden behind a chord-mate head (`10/1/0/0/10`), a ledger merged into a slur or the next head (`10/0/8/10/13`, `10/0/3/6/2`), a box on half a head (`10/1/8/7/4`), Litolff first ledgers at 1.52-1.54 sp just past the 1.5 limit (`6/1/1/11/1`, `6/1/10/3/1`).

Lessons: a filter after a greedy choice silently costs whatever lay behind the choice. `--replay-gathered` cannot measure a GATHER reader (both arms replay one record) -- re-read the slices and compare two records.

## Census (20261029-night slices; Litolff pages 1/6/10, Brahms 0/5)

- Abstained: Litolff 346 (197 read toward another staff = refutations, not failures), Brahms 290 (219 refutations).
- True failures, Litolff: not_a_note 65, no_rungs 34, count_does_not_fit 26, no_line 14.
- The 25 Litolff far heads 2.248 r4 writes blue: count_does_not_fit 9, no_rungs 8, no_line 5.
- Crop look: Litolff no_rungs ~2 of 6 are genuinely missed rungs (crop sheets `out/2.255/census/` on the lane worktree, not committed).

## Built (54211c8db)

1. The head's outline rows are removed BEFORE the walk, not only after.
2. Sean's stacked-window idea (2026-11-02, "not sure if it is best") fits count_does_not_fit: `snap_rung_in_gap` slides a window across a wide gap and counts a ledger only from ends on both sides of the head's column or one level stroke; each part of the split gap must be one walk pitch.

Tried and dropped (each turned Brahms neighbour-staff refutations into own-staff reads, or moved heads already read): a white gap up to 1.75 sp; stubs on both sides required for a through-ledger; a one-sided jut yielding to a staff-side ledger. On-line vs in-space from a one-sided jut is open.

## Measures (2-page dev subset; OFF = night slices, ON = same slices with re-read ledger rows; 2.248 r4 ON in both)

- Control: OFF re-read reproduces the record Litolff 629/639, Brahms 714/714.
- Litolff: blue -3, pitches ~2 -- `6/1/7/11/0` blue F6 -> plain Eb6 (Sean r4 tile 10: right); `10/1/7/4/0` -> plain (r4 tile 12: right); `6/1/0/6/1` blue Eb6 -> plain D6 (unjudged). Brahms: no change.
- Judged right->wrong 0, unwritten->wrong 0. Fast tier 9,729 passed.
- Tiles `out/print/2.255-tiles/` (3 changed + 9 controls), not yet shown to Sean.

## Not verified

Frozen 8-page sample; carry tile 12 (page 11 not in the slices); r4 tiles 5, 6, 8, 9 unchanged; `10/1/7/0/2` now reads -6 on a one-sided jut (not written on these pages).

## 2.255 r2 -- first ledgers against the system's own pitch (lane-2.255-ledger-read 5871f715e; flag still OFF)

Written by the manager from the lane report.

**Cause.** `NOTE_GAP_MAX_SPACES` = 1.5 is a cut-off, not a convention: "this gap has room for one more ledger", which needs two gaps each no shorter than the page's smallest ledger pitch. Litolff draws ledgers at its own pitch (per-system first-gap median 1.04 sp on p10, 1.2 on p6; smallest ≈ 0.75 of median), so the true test is 2 × 0.75 = 1.5 × the system's own median. A fixed 1.5 fits only a page drawn at 1.0 sp (Brahms). **Lesson:** a limit on hand-drawn plates is measured against the page's own pitch; r1's dropped global 1.75 was the same fix with the wrong ruler.

**Built.** `annotate/ledger_grid.local_gap_max` (1.5 × median read ledger-chain gap per (page, system), cap 1.9 sp, needs ≥ 8 gaps, None unless > 1.5 so Brahms is untouched); `count_ledgers_between(gap_max=)` uses it only after the hidden-ledger look finds nothing; `FarHeadPage.read` retries a `count_does_not_fit` once with it. NOT CONFIRMED beyond Litolff: the 0.75 factor and 1.9 cap are Litolff measurements (CLAUDE §4: may only narrow) — reads are currently written plain; whether to write them blue is open until Sean's tiles.

**Measures (2-page dev subset, Litolff p6/p10, Brahms p0/p5).** Control: OFF re-read reproduces the record 629/639 (same 10 as r1) and 714/714. Litolff 11 abstained->read (7 new, all p6); Brahms none. Exported file: 8 Litolff hosts differ, 0 Brahms — 7 corrected pitch or lose blue; 1 note LOST: `10/1/2/9/7` (blue A3, P3) now read by the neighbour staff, overlapping P4's head `10/1/3/9/6` (possible twin drop; untileable, absent from ON file). Judged right->wrong 0, unwritten->wrong 0; Sean's far-head answers 2 new wrong->right (r4 tiles 8, 9). Fast tier 9,731 passed.

**Refutations.** Brahms 219 -> 219. Litolff 179 -> 191: none became an own read, but 12 new rows where the neighbour now reads (8 of them a 1.5-1.7 sp gap the widened limit fits) — these move ownership and need tiles; only `10/1/2/9/7` is written on the dev pages.

**Not fixed, measured.** `10/0/8/10/13`, `10/0/3/6/2`: the ledger is wholly inside the slur/head blob, no separable stroke — stay abstained (counted, blue). `10/1/0/0/10`: hidden behind a chord head; only a one-sided jut shows (the dropped r1 try).

**Tiles** `out/print/2.255-r2-tiles/` (lane branch; 7 changed + 5 controls; key `out/print/2.255-r2-tiles-key.json`). Not run: frozen 8-page sample, whole movement.
