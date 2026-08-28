# `imgsz=2048` is validated on clean keyboard cells and wrong on orchestral ones

**Date:** 2026-08-28
**Verdict:** the CLI default of `imgsz=2048` costs **4–13× more false positives** on real
orchestral cells and **buys no recall**. On two of three orchestral sources, `640` wins
on precision *and* recall.
**Reproduce:** `python3 benchmarks/omr-imgsz-sweep-2026-08/sweep.py`

---

## Where this came from

The whole-pipeline rerun ([../omr-real-world/RESULTS-2026-08-28.md](../omr-real-world/RESULTS-2026-08-28.md))
found `imgsz` swinging noteheads 11× on handel-reduction p20 — 246 at 1280 against 2799
at 2048 — where six cells counted by eye give 2.7 noteheads/cell.

## Method

161 hand-labeled cells (`data/user-labeled/` v1–v4). Only `imgsz` varies; conf 0.25,
iou 0.5 and agnostic NMS are pinned to `transcribe.py`'s production values. Matching is
by **centre, not IoU** — notehead boxes are a few pixels across and box regression is
loose, so IoU understates agreement a human would call correct.

## Result

| imgsz | precision | recall | FP |
|--:|--:|--:|--:|
| **640** | **0.226** | **0.739** | **1498** |
| 960 | 0.144 | 0.688 | 2420 |
| 1280 | 0.092 | 0.673 | 3926 |
| 1600 | 0.066 | 0.663 | 5565 |
| 2048 | 0.050 | 0.695 | 7814 |

**Recall is flat across the whole range** (0.739 → 0.695, best at the *smallest* setting)
while false positives grow **5.2×**. The stated rationale for a large `imgsz` — "catches
small noteheads" — is not supported on this data.

Per source, which is where it gets decisive:

| source | P@640 → P@2048 | R@640 → R@2048 |
|---|---|---|
| **la-mer** | 0.621 → 0.268 | **0.894 → 0.765** |
| **beethoven-5** | 0.194 → 0.046 | **0.661 → 0.604** |
| mahler-5 | 0.166 → 0.033 | 0.764 → **0.824** |

On la-mer and Beethoven 5, **640 wins on both axes**. Only Mahler 5 gains recall at 2048
(+0.06), against a 5× precision collapse.

## Mechanism, confirmed

Cells are canonically rescaled before detection, so `imgsz` sets an **upscale ratio**,
not an absolute size. False positives track the ratio, not the setting:

| upscale (`imgsz` / cell long edge) | median FP/cell | n |
|---|--:|--:|
| ≤ 1 | 13.0 | 577 |
| 1–2 | 35.0 | 199 |
| 2–4 | 51.0 | 29 |

Visual confirmation on `beet5-p55-sys0-s4-m3` (8 labeled noteheads): at 2048 the model
emits 42 boxes, most of them small and sitting on **staff lines**, largely missing the
labeled heads; at 640 it emits 38, larger and far better aligned to them.

## Why this does not contradict Phase 3.3

Phase 3.3 reports **F1 98.8%** at `imgsz=2048` — 238 TP, 2 FP, 4 FN — on the **Bach WTC
verdict set**, a clean keyboard score, with the model fine-tuned at 2048. That number
stands. It is a measurement on *wide, clean, keyboard* cells.

These are *narrow, degraded, orchestral* cells. Bach's cells span two staves and a few
measures, so 2048 barely upscales them; an orchestral cell is a sliver and gets blown up
several-fold. Same setting, opposite effect — which is the whole point: the setting
should not be a constant.

## Recommendation

Scale `imgsz` with cell size, targeting an upscale ratio of **≤ 1** — never enlarge a
cell before detection:

```python
imgsz = clamp(round_to_32(max(cell_w, cell_h)), 640, 2048)
```

Note the two current defaults already disagree: `transcribe.py`'s CLI uses **2048**,
while `CLAUDE.md` documents the web app's `OMR_IMGSZ` as **1280**. Neither is right as a
constant, and the CLI is the one on the bad side.

## Caveat on the absolute numbers

Precision is understated everywhere. The hand-labeled sets deliberately include
**ink-bleed and mostly-FP cells as hard negatives**, and the labeling doctrine leaves
bleed *pending* rather than boxed (CLAUDE.md → "Hand-label cells"), so unlabeled real
ink is scored as a false positive. The **relative** comparison is sound — the same
ground truth is used at every setting — but do not read 0.226 as the model's precision.

## Open question this raises

`benchmarks/omr-detection-probe-2026-07/findings.md` concluded the orchestral wall is a
**domain gap, not a threshold problem**, partly from a conf-0.10 probe that "floods
noteheads with 2.4–3.5× false positives". That probe ran on narrow orchestral cells —
exactly the geometry where a large `imgsz` inflates. Some of that flood may be an
`imgsz` artifact. This does **not** overturn the conclusion (the zero-real-time-signature
-digits finding stands on its own), but the probe is worth re-running once `imgsz` is
fixed.
