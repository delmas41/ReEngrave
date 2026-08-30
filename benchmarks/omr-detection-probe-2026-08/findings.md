# The July "domain gap" conclusion, re-measured — 2026-08-28

The July 2026 probe (`benchmarks/omr-detection-probe-2026-07/findings.md`) asked
whether the orchestral OMR wall is a threshold problem or a domain gap. It
concluded **domain gap**, and that conclusion is the stated reason the project
stopped trying to improve detection and moved to deterministic verification
layers.

The 2026-08-28 handoff flagged it for re-measurement because the probe ran at
`imgsz 2048` on narrow orchestral cells — the geometry the `imgsz` fix was
about. It also said one part of the finding was **not** in doubt: *"the probe
found zero real time-signature digits recovered at conf 0.10, and mostly-treble
clefs. That stands on its own and is not an imgsz artefact."*

That part was wrong. It is an `imgsz` artefact, and completely so.

## The controlled comparison

Same pages, same weights, same confidence (0.25), same cells — **only `imgsz`
differs**. Staff-start cells, 300 DPI, production weights.

**Boléro p.1** — 24 staves, printed **3/4**:

| `imgsz` | timeSig digits | clefs | noteheads |
|---|---|---|---|
| per-cell (192–736) | **36** | **24 / 24** | 14 |
| 512 | 36 | 24 / 24 | 15 |
| **2048 (July's setting)** | **0** | 13 | **705** |

**Mahler 5 p.1** — 17 staves, printed **2/4**:

| `imgsz` | timeSig digits | clefs | noteheads |
|---|---|---|---|
| per-cell (352–384) | **7** | **18** | 55 |
| **2048 (July's setting)** | **0** | **1** | **671** |

The recovered digits are not marginal: on Boléro they are `timeSig3` and
`timeSig4` at **0.94–0.95 confidence**, in measure 0 of 18 staves, and the page
comes out reading 3/4 — the correct printed meter. July reported this exact page
as detecting a meter *nowhere*, at any threshold.

The notehead columns are the same story from the other side: 705 → 14 on
Boléro, 671 → 55 on Mahler. July's "2.4–3.5× false-positive flood when the
threshold drops" was measuring the flood `imgsz 2048` was already producing.

## Whole-page re-run

`rerun_july_probe.py` repeats July's method end to end (conf 0.25 vs 0.10):

| | July (imgsz 2048) | now (per-cell) |
|---|---|---|
| Boléro clefs read | 11 / 24 | **24 / 24** |
| Boléro noteheads @0.25 → @0.10 | 372 → 1310 (**3.5×**) | 141 → 142 (**1.007×**) |
| Boléro real time-sig digits | 0 → 0 | **36 → 36** |
| Mahler clefs read | 4 / 18 | **14 / 17** |
| Mahler noteheads @0.25 → @0.10 | 5816 → 13699 (2.4×) | 96 → 158 (1.6×) |
| Mahler real time-sig digits | 0 → 0 | **7 → 9** |

Lowering the threshold now barely moves anything, in either direction. The
detector at the right scale is neither blind nor flooding.

## What this changes, and what it does not

**Changes.** "The detector cannot see clefs or meters on orchestral pages" is
not a fact about the detector. It was a fact about the input scale. Two of the
three pillars of the July conclusion — invisible meters, mostly-treble clefs —
do not survive the re-measurement, and neither does the flood that made
threshold-lowering look impossible.

**Does not change.** A domain gap is still real for *some* classes on *some*
prints, and it is now specific rather than general: on Beethoven 5 p.15, key
signature flats are not detected at conf 0.25, 0.10 **or 0.05** — the same three
markers at every threshold, while clefs go 16 → 28 — with the per-cell `imgsz`
already in effect (`benchmarks/omr-key-signature/RESULTS.md`). That is a genuine
blindness to one class on one kind of print, not a scale artefact.

Nor does this revalidate synthetic domain augmentation, which was disproven on
its own terms in `benchmarks/scoreaug-fair-test`.

## Method note

This is the second time in one day that a confident measurement turned out to
describe the instrument rather than the page — the first being "28 contiguous
runs with 11-space gaps" in the Phase-1 baseline, which was a fact about a 2px
band. Both were load-bearing for strategy. Before concluding that the pipeline
*cannot* see something, check what it was shown.

Reproduce: `python3 benchmarks/omr-detection-probe-2026-08/rerun_july_probe.py`
(writes `results.json`).
