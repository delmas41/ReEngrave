# Phase 1 missed barline — Beethoven 5 p.2 system 0 — not fixed, and why

**2026-08-30.** Beethoven 5 p.2 (IMSLP imslp-575951, page_index 1, dpi 450),
system 0, is missing one bar: Phase 1 reads 16 measures where the page has
17. This blocks `benchmarks/omr-real-scan-notes-2026-08/`'s measure-range
tripwire, which refuses to emit a ground-truth file while the count
disagrees. A prior session localised the mechanism to three independent
guards, all in `tools/omr/measure_extractor.py`, and asked this session to
fix it if a safe fix exists. It does not. All three guards were tried, in
order, on branch `claude/phase1-missed-barline`; each recovery attempt was
measured against the 1038-test suite, the hand-verified layout fixture, and
a 166-page real-scan corpus scan before being tried against the next guard.
**No code shipped** — the working tree is unmodified from `main`.

## The bug, confirmed

Violino I system 0's cell widths (px): `[405, 228, 146, 156, 150, 299, 112,
210, 206, 211, 201, 200, 191, 207, 177, 224]`. The 299px cell (x 1504–1803)
is two bars; the missing barline sits at x≈1707–1711, hand-read across the
system and visible on the resting Timpani staff with no competing ink at
all. Reproduced exactly on this branch (`tools/omr/preprocessing.render_page`
→ `staff_detector.detect_staves` → `measure_extractor.detect_barlines` →
`extract_measures` → `resegment_fused_measures`, no YOLO): system 0 reads 16
cells, system 1 reads 15 (correct), `majority_bars_by_system` returns
`{0: 16, 1: 15}` — the whole-system miss is invisible to majority steering,
as a prior benchmark (`omr-majority-steering-2026-08`) already showed for
this class of bug.

## Guard 1 — the same-staff dedup starves the vote (confirmed and fixed)

`_detect_barlines_in_window` collects every column that independently passes
the barline shape test (height/width/aspect), then — inside
`_find_internal_barline_candidates`'s narrow resegmentation window only —
throws away any candidate within `BARLINE_MIN_DISTANCE_PX` (60px) of an
already-kept one, always keeping the **leftmost**. On staves 7–10 (the
strings), the final beat before the true barline carries a full-height note
stem 27–35px to its left, and that stem independently clears every filter
the barline itself clears (81–100% of staff span vs. the barline's
98–100%). The dedup keeps the stem and throws the real barline away. Only
staves 5 and 6 (no competing stem nearby) keep their true candidate, so only
2 of 6 real votes reach the resegmentation vote/connectivity gate — one
short of its floor (`max(2, round(0.30×11)) = 3`).

Verified directly by dumping the pre-dedup connected-component list for
system 0's 6 lower staves at x∈[1504,1803]: all 6 independently detect a
component at x=1703–1711 with height 98–100% of span, at or above the
competing stem's height on every affected staff.

**Fix tried:** a naive "disable the same-staff dedup entirely" was tried
first and rejected — it let the caller's cross-staff clusterer (12px
tolerance) transitively chain the cell's whole dense stem-and-ornament
region into one 74px-wide blob and report its mean, x=1697, not a real
barline (the true position is x≈1707–1711). A silently-wrong candidate is
worse than the vote-starved empty result it replaced.

The fix that ships correctly: keep the dedup's one-candidate-per-window
sparseness (so the downstream clusterer isn't flooded), but pick the
**tallest** candidate in a **fixed** window (anchored at the candidate that
opens it, not a sliding anchor — a sliding anchor reintroduces the same
transitive-chaining smear) instead of the leftmost. Implemented as
`_dedup_barline_candidates(candidates, dist, strategy)` with
`strategy="tallest"` used only by `_find_internal_barline_candidates`; the
global whole-page pass (`_detect_barlines_per_staff`) keeps
`strategy="leftmost"`, byte-identical to today. With this fix,
`_find_internal_barline_candidates(bin_img, staves_of_system_0, 1504, 1803)`
returns **`[1708]`** — 2–4px from the hand-read x≈1707–1711, essentially
exact.

**This fix alone does not recover the bug.** The 299px cell is only 1.451×
the system's 206px median, which clears neither the resegmentation
conservative trigger (`RESEGMENT_WIDTH_WARN_FACTOR = 2.0`) nor the steered
trigger (`RESEGMENT_STEER_WIDTH_FACTOR = 1.5`) — so
`_find_internal_barline_candidates` is never even called on this cell by
`resegment_fused_measures` in either mode. Confirmed: with only guard 1
patched, beet5 p.2 system 0 stays at 16 cells.

**Guard 1's fix was corpus-tested on its own merits anyway** (it's a real,
independently-diagnosed bug, not a guess): `python3 -m pytest tools/omr/tests
-q` stays at **1038 passed**; the 12-page hand-verified
`phase1_layout_eval.py` fixture shows **no change**; a 166-page scan (the
full Beethoven 5 IMSLP scan, 87 pages, and the full Beethoven 6/Pastoral
IMSLP scan, 79 pages, both Phase-1-only + `resegment_fused_measures` with
majority steering — matching `transcribe.py`'s actual call) changed exactly
**6 of 166 pages**, always by +1 measure, never a loss. All 6 were cropped
and inspected: `beet5 p.15 sys1`, `beet5 p.77 sys0`, `beet5 p.85 sys0`,
`pastoral p.10 sys1`, `pastoral p.39 sys1`, `pastoral p.45 sys0`. Five land
cleanly in whitespace between visually distinct or visually-repeated note
groups (see `evidence/beet5_p15_sys1_v3.png`,
`evidence/pastoral_p39_sys1_v3.png`). The sixth (`pastoral p.10 sys1`,
`evidence/pastoral_p10_sys1_v3.png`) looked ambiguous on first crop — the
line sits close to stems and a slur — so it was checked quantitatively: at
x=2460, 3 of the system's 9 staves show a genuine unbroken full-height ink
column (staff 11: 100% of span), confirming a real drawn stroke, not a
coincidental stem alignment. Guard 1's fix is not shipped in this round
regardless, because it does not satisfy the task's single pass/fail
condition (system 0 must go 16→17) — but it is a correct, narrowly-scoped,
corpus-validated finding on its own, and a candidate for a future,
separately-scoped change.

## Guard 2 — the width-outlier trigger (loosening it is reachable, but the fix still doesn't land)

With guard 1's fix in place, lowering `RESEGMENT_WIDTH_WARN_FACTOR` from 2.0
to 1.40 (clearing the cell's 1.451× ratio) does let
`_find_internal_barline_candidates` run on the cell in the conservative
(non-steered) pass — for the first time, it is even asked the question. It
answers correctly: candidate `[1708]`. **But the split is still rejected**,
by the third guard below, so system 0 stays at 16.

This change also breaks two unit tests that exist specifically to pin this
boundary: `TestSteeredResegmentation::test_sub_2x_cell_split_only_when_steered`
and `::test_inert_when_count_already_met` — both fail with the factor
lowered, because their fixtures were written to assert exactly the
"conservative pass ignores sub-2x cells" behaviour this change removes.

## Guard 3 — the sliver floor (the one that actually blocks it, and the one that cannot be safely loosened)

The candidate `_find_internal_barline_candidates` finds at x=1708 splits the
299px cell into pieces of 204px and 95px. The system's median is 206px, so
the trailing piece is 95/206 = **0.461×** median — just under
`RESEGMENT_MIN_PIECE_FRAC = 0.5`. The split is rejected as a sliver. The
17th bar is genuinely short (confirmed by the hand-read x≈1710 target and
the piece width matching it almost exactly), and that is precisely the
shape of case this floor exists to catch.

Lowering `RESEGMENT_MIN_PIECE_FRAC` from 0.5 to 0.40 (clearing 0.461) — on
top of both prior changes — **does** recover the bug:

```
BEFORE resegment, system 0: 16 cells, system 1: 15 cells
AFTER  resegment (all 3 guards loosened), system 0: 17 cells, system 1: 15 cells
```

System 0 goes 16→17, system 1 stays at 15, exactly as required. But:

* It breaks a third pinned test —
  `TestSliverSplitRejected::test_off_center_candidate_produces_sliver_and_is_rejected`
  — which exists specifically to prove a near-edge candidate cannot
  manufacture a sliver measure. `pytest tools/omr/tests -q`: **3 failed,
  1035 passed** (down from 1038 passed, 0 failed).
* The 12-page hand-verified fixture (`phase1_layout_eval.py`) still shows no
  change (none of its 12 pages happen to hit this exact shape), so it
  cannot see the damage below on its own.
* The 166-page corpus scan (same corpus as guard 1's measurement) jumps from
  **6 changed pages to 28** — 24 additional pages change once the sliver
  floor drops, all net gains, totalling **+44 measures** across the corpus
  (vs. +8 for guard 1 alone).

One of those 24 is unambiguous, confirmed damage:
**`pastoral p.0, system 1: 4 cells → 10 cells` (+6 in one system on one
page).** The pre-resegment cell that grew was already a 1934px outlier
(3.57× the system's 542px median) — a long, uninterrupted string tremolo
passage (Beethoven 6's opening "murmuring brook" figure: identical
repeating eighth-note groups under `dimin.` markings). All three loosened
guards together sliced it into 7 near-equal pieces at 6 new x-positions
(1751, 2011, 2288, 2562, 2836, 3133), evenly spaced roughly every 270–290px.
**Every one of the 6 new lines lands in the middle of continuous, uniform
repeating figuration — none corresponds to a real barline** (see
`evidence/pastoral_p0_sys1_fused_cell.png`): the ostinato produces a
coincidental cross-staff stem alignment at regular intervals, which is
exactly the failure mode `_intersystem_connectivity` was built to catch —
and does catch, at the guards' original settings. Loosened together, the
guards let it through six times over on one page alone.

This is the same class of damage `benchmarks/omr-phase1-baseline/RESULTS.md`
documents for the WTC p.6 x=4476 false barline (there, stem alignment with
no cross-gap ink deleted real notes from the page). Here it is worse:
one continuous passage cut into seven arbitrary fragments.

## Verdict

Three independent guards each protect against a real failure mode
(same-staff duplicate detections, isolated width outliers with no internal
barline, and near-edge candidates that would manufacture slivers). Guard 1
was genuinely miscalibrated and has a correct, narrow fix that does not by
itself regress anything measured. Guards 2 and 3 are not miscalibrated in
the same sense — they are doing their job on the corpus at large, and this
one bar happens to need both of them to step back at once because the
missing 17th bar is itself unusually narrow (0.461× median). Loosening both
enough to admit it demonstrably fabricates barlines elsewhere, confirmed by
a 4×-scale jump in one system on one page, sliced through continuous
uninterrupted music.

**This bug is not fixed at the Phase-1 CV layer without a real accuracy
cost elsewhere on the corpus.** No code is shipped. A semantic signal these
three width/count-based guards structurally cannot see — e.g. a
work-specific measure count from a dossier, or a beam/stem-continuation cue
distinguishing "genuinely narrow final bar" from "arbitrary slice through
an ostinato" — is what real recovery would need; both are out of scope for
a Phase-1-only change.

## Reproduction

All of the below run against an unmodified checkout (nothing in this repo
was changed):

```bash
# The bug itself, unresegmented and resegmented (majority-steered, matching transcribe.py):
python3 -c "
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import detect_barlines, extract_measures, resegment_fused_measures, majority_bars_by_system
pws = detect_barlines(detect_staves(render_page(
    'tools/omr/training/data/imslp/beethoven-symphony-5/pdfs/imslp-575951/score.pdf', 1, dpi=450)))
cells = extract_measures(pws)
print(sorted({c.measure_index for c in cells if c.system_index == 0}))  # 16 cells, 0..15
out = resegment_fused_measures(pws, cells, expected_bars_by_system=majority_bars_by_system(cells))
print(len({c.measure_index for c in out if c.system_index == 0}))  # still 16 — majority is blind to a whole-system miss
"

# Regression baseline (unaffected either way, since nothing is changed):
python3 -m tools.omr.training.phase1_layout_eval
python3 -m pytest tools/omr/tests -q   # 1038 passed
```

The three experimental patches (dedup strategy, `RESEGMENT_WIDTH_WARN_FACTOR
1.40`, `RESEGMENT_MIN_PIECE_FRAC 0.40`) were applied and measured in this
session but are **not present in the working tree** — this document and
`evidence/` are the record of that measurement.
