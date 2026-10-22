# Handoff — recognition work, 2026-08-28

Branch **`claude/recognition-improvement-next-2f1709`**, 10 commits ahead of
`main`, merged with main once mid-session. Tree clean, **751 tests pass, 3
xfailed**.

> `main` moves fast right now — it advanced 38 commits *during* this session and
> another 4 since the merge. **Fetch and check before doing anything**, and see
> "Gotchas" below.

---

## What this session changed

Two layers, both of which had gone unmeasured for a long time.

### Phase 1 — layout

* **Five staves were collapsing into one phantom.** A global prominence gate
  (0.30 × page max−min) rejected lightly printed wind-staff lines; the
  survivors — one line from each of five staves — are as evenly spaced as the
  staves themselves, so the grouper accepted them as a staff of 142px spacing on
  a page whose real spacing is 15.8. Beethoven 5 p.10 reported 18 staves and has
  22. Fixed with a comb pass calibrated on the page's own spacing and line ink.
  **beet5 p10 18 → 22, p2 16 → 22, p8 16 → 20.**
* **Music was being deleted after a false barline.** Two aligned stems produced a
  barline near the end of a WTC system; the real final measure then looked like
  the blank strip that follows a final barline and was discarded. The measure
  *count* stayed right, so nothing downstream could see the loss. Tails are now
  absorbed.
* A real Phase-1 baseline exists: `benchmarks/omr-phase1-baseline/` (hand-verified
  ground truth + a 12-page corpus probe with `--compare`).

### Phase 4f — stems and beams

* **Staff-line removal was a no-op on most orchestral scores.** Its preserve test
  looked a fixed 4px above and below, which any line thicker than 8px satisfies
  by itself. Mahler cleared **0.9%** of its staff-line ink, Beethoven **0.0%**.
  Now decided by vertical run height against the line's measured thickness:
  **Mahler 89.7%, Boléro 88.5%**.
* **`detect_stems` opened with a kernel exactly one notehead tall**, so noteheads
  survived fused to their stems and the width filter rejected both. Invisible
  until removal worked.
* **`detect_beams` counted anything horizontal** — slurs, ties, ledger lines,
  staff residue. One Mahler cell of half notes under slurs reported 27 beams.
  Replaced by one rule: *a beam is horizontal ink that stems run into*. Error
  against the reference sheet **157 → 3**.
* **An accidental's strokes come in pairs; a stem is single.** Sharps and
  naturals are two parallel verticals ~0.55 spaces apart, passing every stem
  filter. Hand-label error **60 → 24**; the reference sheet's unexplained stem
  over-count went from +7 to −1 on a truth of 48.

### Measurement — the part with the longest half-life

* `benchmarks/omr-phase4-lines/` — a **LilyPond reference sheet** whose stem and
  beam counts are known by construction, engraved at four staff-line thicknesses.
* **31 hand-counted cells** from Sean (16 beams, 15 stems), chosen adversarially:
  cells where two candidate settings *disagreed*, so a count decides between them
  rather than merely scoring one.
* `benchmarks/omr-end-to-end/` — **the first measurement of whether the right
  notes come back.** Authored scores (music21 → `musicxml2ly` → LilyPond → PDF)
  give exact truth for free.

---

## Where it stands

```bash
python3 -m tools.omr.training.phase1_layout_eval --out /tmp/a.json --compare benchmarks/omr-phase1-baseline/snapshot-after.json
python3 -m tools.omr.training.line_detection_eval            # sheet + both hand-label sets
python3 -m tools.omr.training.end_to_end_eval                # notes in vs notes out
```

**End-to-end, 600 DPI (the pipeline default):**

| fixture | parts | measures | notes (omr/truth) | pitch recall | precision | duration |
|---|---|---|---|---|---|---|
| melody | 1/1 | **12/6** | 61/24 | 0.375 | 0.148 | 0.889 |
| keyboard | 2/2 | 4/4 | 45/27 | 0.407 | 0.244 | 0.364 |
| ensemble | 4/4 | 4/4 | **103/45** | 0.400 | 0.175 | 0.167 |

**Structure is now well ahead of content.** `ensemble` is structurally perfect —
4 parts, 4 measures — and still reports 103 notes where the page holds 45.

Stem/beam against ground truth: reference sheet **beams 12/12 exact at every
thickness**, stems within ±2 of 48. Hand-labeled cells: **beams error 8**,
**stems error 23**.

---

## Open threads, most promising first

1. **Note over-detection.** The pipeline reports 2–2.5× the notes that exist on
   clean synthetic input, with structure correct underneath. This is the largest
   single gap between the pipeline and its purpose, and it now has a number to
   move. Start with `ensemble` (structure correct, so nothing else confounds it).
2. **Single-staff over-segmentation.** `melody` reads 12 measures where there are
   6 — with one staff there is no cross-staff vote, so note stems are read as
   barlines. Worst fixture on every metric, and it is the simplest music.
3. **Slurs read as beams.** The residual Boléro over-counts are slurs arcing just
   above a beam group: long, horizontal, near stem ends. The discriminator is
   **curvature** — a beam is straight, a slur bends — which is measurable but
   unbuilt.
4. **The last stem class.** One La Mer cell counted 0 still detects 4. The pair
   rule removed the accidental class; what remains is undiagnosed.
5. **`beet5 p10` system grouping** — `xfail(strict)` in `test_pipeline.py`. Staff
   0 splits into its own system because `_staff_x_extent` bridges one staff space
   and those lines break into ~28 runs with gaps up to **11 spaces**. Measured,
   not assumed: main's bridge does not close it.

**Do not retrain.** Three recipes are disproven in this repo — catalog training,
ScoreAug augmentation, and the clef fine-tune.

---

## Gotchas that cost time here

* **Check the base first.** `git fetch && git log HEAD..main`. Main advanced 38
  commits mid-session; hours of measurement were taken against a stale tree.
* **Run at the pipeline's defaults.** The end-to-end eval was first run at 300
  DPI when `transcribe` defaults to 600 — melody's duration rate moves 0.29 →
  0.89 between them.
* **Never key a fixture to `cell_index`.** Any Phase-1 change re-segments and
  renumbers. The merge silently re-pointed five hand labels at different music.
  Labels now carry `bbox_page_px` and resolve by region overlap, returning a list
  so a region later split into several cells sums correctly.
* **Count pitches, not note objects.** `music21`'s `.notes` counts a chord as
  one; one exported "chord" of 46 pitches read as a single note.
* **`flatten()` interleaves parts by offset.** Align per part, or you measure the
  interleaving — that alone moved a recall figure 0.489 → 0.711.
* **Check a fixture is representative before believing it.** An early spike used
  a lone tiny staff on an empty page and measured the fixture, not the pipeline.
* **Two numbers on `main` were contradicted by the pages** and corrected here:
  Beethoven p.10's staff count (18 → 22, an unexamined carry-over that the
  phantom bug satisfied), and an exact staff count on a Nottebohm page — a
  textbook, not a score, so that test now asserts the property rather than a
  count.
