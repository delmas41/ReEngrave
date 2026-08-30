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

## Mechanism — the first explanation was WRONG

The initial reading was that cells are canonically rescaled before detection, so `imgsz`
sets an **upscale ratio** and a narrow cell blown up makes the detector fire on texture.
Pooled across all cells the false positives did track that ratio (13 → 35 → 51 per cell
as the ratio went ≤1 → 1–2 → 2–4), which looked like confirmation.

**It was an artefact of the pooling** — ratio and `imgsz` are correlated there. Splitting
the cells into size bands separates them, and the answer flips:

| `imgsz` | FP/cell, cells 600–1000px | 1000–1500px | ≥1500px |
|--:|--:|--:|--:|
| 640 | 8.5 | 12.7 | 8.8 |
| 1280 | 32.6 | 32.4 | 20.7 |
| 2048 | 52.6 | 60.0 | 45.2 |

At a given **`imgsz`** the FP rate is nearly identical across bands. At a given **ratio**
it is not: ratio 0.80 gives 8.5 FP/cell in one band while ratio 0.89 gives 28.7 in
another, a 3× gap.

So the driver is **absolute `imgsz`**, not cell-relative scale. Ultralytics letterboxes
the input to `imgsz × imgsz` regardless of source size, so a larger `imgsz` is simply
more pixels, more anchors and more detections — FP/cell rising ~6× for a 10× area rise.

**This changes the fix.** It is not a cell-relative rule; it is a smaller constant.

> ### Correction (2026-08-28) — the letterbox claim, and what it changes
>
> **Ultralytics does not letterbox to `imgsz × imgsz` here.** `predictor.pre_transform`
> builds `LetterBox(imgsz, auto=rect)`, and for a single image `rect` is true, so it
> scales the **longest side** to `imgsz` and pads only to a stride multiple: a 300×1200
> cell at `imgsz 512` is fed as 128×512, not 512×512. Forcing the square path changes
> only the padding — content is still scaled by `imgsz / longest side`. So what the model
> is shown is `canonical staff space × imgsz / longest side of cell`, a property of the
> cell.
>
> **The size-band evidence above is real but cannot separate the two hypotheses.** A
> canonical cell is 12 staff spaces tall (4 for the staff, 4 padding either side), so its
> height is pinned near 1200 px whatever the music. Every cell narrower than that has
> `longest side = 1200` and is therefore shown `imgsz / 12`, with width not entering at
> all — which is most measure cells. Where the bands *do* separate them, the numbers here
> lean the other way: the **≥1500 px band has the lowest FP rate at every `imgsz`**
> (8.8 / 20.7 / 45.2 against 12.7 / 32.4 / 60.0). Those are the width-dominant cells,
> shown a smaller staff space.
>
> **The direction of this document is right and its measurements stand** — 2048 really is
> far too large, and 512 really is much better. What changes is that the fix is a rule
> rather than a number: a constant lands inside the good band on wide header cells and
> past its edge on the narrow interior cells of the same page. Head-to-head at the
> pipeline's own 600 DPI, per-cell beats 512 on every fixture and every metric (ensemble
> 45 notes against 57, precision 0.956 against 0.684). Nor is a *smaller* constant the
> answer: on WTC cells the width cap squeezes the canonical staff space to 19, where
> `imgsz 256` loses half the noteheads that 512 and per-cell both find — there is an
> absolute-resolution floor as well as a scale ceiling.
>
> Landed as `yolo_detector.imgsz_for_cell`. Full reconciliation, with the letterbox
> shapes measured directly: `../omr-detector-scale/RESULTS.md`.

## Confirmation on authored ground truth

The hand-labeled cells understate precision by design (see the caveat below), so the
decisive check is the end-to-end harness from `claude/recognition-improvement-next`
(`tools/omr/training/end_to_end_eval.py`), which authors truth in music21, renders it
through LilyPond, and asks the pipeline to recover it. That session found the same
over-detection independently — "keyboard returns 111 notes for 27, a precision of 0.14
on a clean render. **Whatever the mechanism**, it is not a subtle accuracy loss" — without
identifying the cause.

The cause is `imgsz`. On their `keyboard` fixture, 27 true notes:

| `imgsz` | notes | pitch recall | pitch precision | duration |
|--:|--:|--:|--:|--:|
| **640** | **24** | **0.815** | **0.917** | **0.955** |
| 1280 | 19 | 0.333 | 0.474 | 0.111 |
| 2048 (their baseline) | 111 | 0.593 | 0.144 | — |

and on `melody`, 24 true notes: recall 0.292 → **0.583** and precision 0.219 → **0.519**
going from 2048 to 640. Both axes improve on clean, authored input.

## Why this does not contradict Phase 3.3

Phase 3.3 reports **F1 98.8%** at `imgsz=2048` — 238 TP, 2 FP, 4 FN — on the **Bach WTC
verdict set**, a clean keyboard score, with the model fine-tuned at 2048. That number
stands. It is a measurement on *wide, clean, keyboard* cells.

These are *narrow, degraded, orchestral* cells. Bach's cells span two staves and a few
measures, so 2048 barely upscales them; an orchestral cell is a sliver and gets blown up
several-fold. Same setting, opposite effect — which is the whole point: the setting
should not be a constant.

## Recommendation

**Lower the constant.** `imgsz=640` is the best value tested, on both the hand-labeled
cells and the authored end-to-end fixtures, on both precision and recall.

Note the two current defaults already disagree: `transcribe.py`'s CLI uses **2048**,
while `CLAUDE.md` documents the web app's `OMR_IMGSZ` as **1280**. Neither is right as a
constant, and the CLI is the one on the bad side.

## Result of the change, on all three end-to-end fixtures

Default moved 2048 → **512**. Every metric on every fixture improves:

| fixture | pitch recall | pitch precision | duration | notes reported (truth) |
|---|---|---|---|---|
| melody | 0.292 → **0.625** | 0.219 → **0.714** | 0.286 → **1.000** | 32 → 21 (24) |
| keyboard | 0.593 → **0.852** | 0.144 → **1.000** | 0.438 → **1.000** | 111 → 23 (27) |
| ensemble | 0.711 → **0.956** | 0.681 → **0.915** | 0.906 → **0.930** | 47 (45) |

`ensemble` also now reports **4 parts against 4**, where it previously collapsed to one
— the "four staves came back as one part" symptom in
`benchmarks/omr-end-to-end/RESULTS.md`.

Bracketing 384 / 512 / 640 / 800 picked 512: 384 wins `keyboard` outright (recall 0.963,
precision 1.000) but costs `melody` badly (recall 0.375), and 800 collapses `melody`
entirely. 512 is the only value at or near best on both, with duration accuracy 1.000 on
each.

**Reproducing this needs `--imgsz` threaded through
`tools/omr/training/end_to_end_eval.py`**, which lives on the recognition session's
branch rather than on main. That change defaults the flag to `None` so the harness uses
whatever `transcribe` defaults to — the first run of this comparison silently reported
the old numbers because the flag pinned 2048.

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
