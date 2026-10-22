Re-price `OMR_CV_HAIRPINS` on the current default tree, then close the dynamics gap in the staged pipeline.

Read `docs/scope-dynamics-reading-2026-09-09.md` first — it has the full reasoning, the refusals, and why this order. Short version: over the 20-row scan gate the symbol ledger reads `hairpin` **matched_exact = 0 with 0 spurious** (140 missing) against `dynamic` (letters) at 244 exact + 73 attribute-error vs 127 missing. Both families miss roughly the same absolute amount; only the hairpins are at zero recall.

## Task 1 — the re-run (this is the whole point; no new code)

`OMR_CV_HAIRPINS` (`tools/omr/transcribe.py:3106`, default OFF) is a built, measured classical-CV reader that finds **96 hairpins across the 20-row gate against a truth of 192**, where the detector finds 3. It is off because it cost OMR-NED when priced on **2026-09-07**: 11 rows worse, 8 unchanged, 1 better.

**The reason to re-run it:** its own docstring attributes **+37 of the +76 total edit movement to Brahms 1 p2 alone** — and says the anchor rule is *not* in the causal path there, because that row is one of the three where `_stitch_slots` REFUSED, so no hairpin could cancel a truth hairpin whatever `_wedge_anchors` picked. **`OMR_SLOT_STITCH` went default ON on 2026-09-08**, one day after that arm ran, and Brahms p2 is *the* row it repairs (27 fragment parts → 14 continuous parts, 0% → 100% ledger correspondence). So half the flag's measured cost sat on a row that has since been structurally fixed.

⚠️ This is an argument from dates and the flag's own attribution, **not a measurement**. It may well come out the same. That is why it is a re-run and not a ship.

Do:
1. `scan_eval` OFF vs ON over the 20-row gate on the current tree (with `OMR_SLOT_STITCH` at its new default).
   - ⚠️ **Give each arm its own `--tag=` (it needs the `=`, e.g. `--tag=-hpoff`) or its own work-dir.** `scan_eval.run_pipeline` opens with `if pred.is_file() and raw.is_file() and not force: return`, so two arms sharing a fixtures dir with an empty tag silently reuse the first arm's transcriptions — and a cached A/B always reports "identical on every bucket and every row", which is exactly the clean result a flag-guarded change hopes for. **Check the wall clock**, not the numbers: minutes vs hours is the tell.
   - Validity control the previous arm used: assert **0 of 20 rows differ in any NON-hairpin detection**, so the movement is attributable to this flag.
2. **Score per row, never pooled.** `benchmarks/omr-hairpin-cv-2026-09/probe/scan_arm_table.py` refuses to pool on purpose: the two Mahler rows err in opposite directions (p3 misses fifteen, p2 invents two), and 8 of 20 rows carry no truth hairpin at all so they can only ever be hurt.
3. **Split each moved row's delta BY BUCKET** with `benchmarks/omr-ned-2026-08/dump_ops.py`. This is the step the docstring names as needing no new arm: `entire staff` / `entire measure` movement is the stitch refusal; `wrong crescendo` on a row whose parts *joined* is the anchors. Note musicdiff maps a wedge we INVENT and one we MISS to the same bucket, so the bucket alone says only that unpaired-wedge count moved.
4. ⚠️ The gate's noise floor is roughly **±6 edits** — a single-row delta smaller than that is not evidence.

Decide from the per-row table whether the flag defaults ON. If the cost has moved off Brahms p2 and onto rows whose parts join, the anchor hypothesis is live and `_wedge_anchors`' documented blindness to `duration_beats` is the next thing to test.

## Task 2 — put dynamics into the staged pipeline

All three dynamics decisions are declared stubs and **nothing is behind them**: `Q.DYNAMIC_LETTER` and `Q.WEDGE_BOX` are declared in `tools/omr/staged/record.py` (lines ~297-298) and emitted by **no gatherer** (`grep -n "Q.DYNAMIC_LETTER\|Q.WEDGE_BOX" tools/omr/staged/gather.py` returns nothing).

- Add gatherers for both to `tools/omr/staged/gather.py`.
- ⚠️ Gather them **in page pixels against the staff's own bottom line**, not the measure cell's frame — cell padding varies with staff crowding and would move the number without moving the ink.
- Then implement `adjudicate_dynamic` in `tools/omr/staged/adjudicators/text.py`.

The composition already declared in `adjudicate.py:77-83` is the right one, and `Q.GLYPH_OWNER` is the one piece here that is **not** a stub — so gathering the letters routes placement through a real ownership adjudicator instead of bolting the band rule into `_dedupe_cross_staff_detections` by hand. That matters because the measured placement fault is that the upstream dedupe keeps the wrong copy **by distance** (24% of letters land in the staff above, and 83% of re-attributed letters are the target staff's sole evidence *because the pipeline made it so*).

⚠️ **The hairpin reader's band discipline is the fix for the letters' placement problem, not the reverse.** `hairpin_detection.BAND_TOP/BOTTOM_SPACES` (0.3–6.0 below the bottom staff line) is the same band the letters occupy (+0.0..+5.6 per the band study), but it searches per staff in page pixels so attribution is right by construction.

## Task 3 — stop binning partial letter runs

`export.measure_dynamics` (`tools/omr/export.py:1464`) discards a letter run that spells nothing in `_DYNAMIC_WORDS`. Measured: **49 letters in 31 runs**, dominated by a lone `s` (15 of 31) — an `sf` whose `f` was not detected. A read mark thrown away, the same detected-then-dropped shape this repo has paid for ten times. Needs a decision on what a partial run exports as (`<other-dynamics>` is the obvious candidate).

⚠️ **This one is priceable without the full gate** — see below.

## A cheap local control before the slow arms

`docs/cloud-session-capabilities-2026-09-09.md` records that Brahms 1 / Breitkopf p1–p3 are fully reproducible from committed files: `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json` (3 pages, 83 staves, 10,523 detections) + its `reference.mxl` + the hand-verified windows in `benchmarks/omr-scan-e2e-2026-09/works.json`. So `transcription → export → musicdiff → OMR-NED` closes with **no weights**, which makes it a fast sanity arm for any export-side change (Task 3, and the export half of Task 2) before spending hours on `scan_eval`.

⚠️ One row is not the gate — treat it as "worth running the real arm for", never as the arm.

## Housekeeping

Per the repo's own convention, update `CLAUDE.md`, `PROJECT_BRIEF.md` and `version_memory.md` after each commit, and put the measurement in a `benchmarks/*/FINDINGS.md` rather than in prose. If a claim in CLAUDE.md turns out to be stale, correct it in place and say so — the tree outranks the ledger.
