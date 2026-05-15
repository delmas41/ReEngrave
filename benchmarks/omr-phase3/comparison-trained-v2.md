# Phase 3.1 — YOLO direct P/R vs template matcher, on the 25 verdict cells

**Date:** 2026-05-15
**Builds on:** [comparison-trained.md](./comparison-trained.md) (which left direct P/R as a TODO under "Honest caveats")

## What this measures

The 25 hand-annotated verdict cells in `benchmarks/omr-phase2.5/verdicts/` are
labelled against **template-matcher** detection IDs. To get YOLO precision/recall
on the same human ground truth, we ported each verdict to its nearest YOLO
detection of the same category within ±30 px (canonical pixels), then ran the
existing scorer.

Pipeline:

```
tools/omr/annotate/port_verdicts_to_yolo.py
  --tm-verdicts-dir     benchmarks/omr-phase2.5/verdicts
  --tm-detections-dir   benchmarks/omr-phase2.5/detections
  --yolo-detections-dir benchmarks/omr-phase3.1/detections   ← the strongest
                                                               trained YOLO
                                                               (yolov8m r2,
                                                               imgsz 1280)
  --out-dir             benchmarks/omr-phase3.1/verdicts-yolo
```

YOLO weights used: `deepscoresv2-yolov8m-r2-imgsz1280-50ep.pt` (as recorded in
`benchmarks/omr-phase3.1/_summary.json`). The task brief called these weights
"yolov8l-full"; no such weights file exists in the repo. The phase3.1 detection
dir is bit-identical to `benchmarks/omr-phase3/r2/detections/` (same weights,
same conf=0.25, same seed — verified for all 25 verdict cells). r2 is the
strongest trained YOLO available right now — 42.2 % mAP@0.5 on DeepScoresV2
dense val. Re-run with new weights if a true L-sized "full DeepScoresV2" run
is added later.

Porting rule:

| TM verdict | YOLO match? | Counted as |
|---|---|---|
| **TP** | found in ±30 px, same category | YOLO TP |
| **TP** | no match | **YOLO FN** (real symbol, YOLO blind) |
| **FP** | found | YOLO FP (replicated TM mistake) |
| **FP** | no match | dropped (YOLO win, but not credited in the math) |

YOLO detections with no TM verdict to inherit stay pending — they're outside
the human-labelled subset and can't be scored. There are 294 of those, so a
huge chunk of YOLO's output (mostly clefs, augmentation dots, beams, dynamics)
is uncredited here. **This is a lower bound on YOLO's true recall.**

## Headline result on the 25 verdict cells

|  | Template matcher (Phase 2.8) | **YOLO r2 (this report)** |
|---|---|---|
| TP | 242 | **205** |
| FP | 20 | **1** |
| FN | 0 *(by construction — TM defines GT)* | **37** |
| **Precision** | **92.4 %** | **99.5 %** ✅ |
| **Recall** | **100 %** *(by construction)* | **84.7 %** |
| **F1** | 96.0 % | **91.5 %** |
| Median time / cell | ~1100 ms | **76 ms** (≈15× faster) |
| Avg detections / cell | 10.6 | 24.9 (mostly outside the ported subset) |

YOLO precision is **7.1 points higher** than the template matcher; recall is
**15.3 points lower**. The recall is asymmetric and concentrated — see below.

## Per-category breakdown

| Category | TM (TP/FP) | TM P | YOLO (TP/FP/FN) | YOLO P | YOLO R | Verdict |
|---|---|---|---|---|---|---|
| notehead | 231 / 19 | 92.4 % | **197 / 1 / 34** | **99.5 %** | 85.3 % | YOLO precision wins by 7 pts; recall loses by 15 |
| rest | 5 / 0 | 100 % | 5 / 0 / 0 | 100 % | 100 % | tie (small N) |
| accidental | 1 / 1 | 50 % | 1 / 0 / 0 | 100 % | 100 % | YOLO wins (small N) |
| flag | 5 / 0 | 100 % | 2 / 0 / 3 | 100 % | **40 %** | **YOLO loses** — misses 3 of 5 flags |

The only category where YOLO clearly underperforms TM is **flag** (40 % recall).
On accidentals and rests YOLO matches or beats TM, but the verdict sample is
tiny in those buckets.

## Where YOLO loses, in detail

Forensic walk on the 37 ported-TP-without-YOLO-match cases (the "YOLO FNs"):

| Failure mode | Count | What's happening |
|---|---|---|
| **No YOLO bbox within 30 px at all** | **33** | YOLO truly didn't see the symbol — model blind spot |
| YOLO bbox present but mislabelled as `coda` | 4 | YOLO confidently predicts `coda` (cat=`unknown`) at notehead locations. Genuine misclassification, not a wrapper gap |
| Wrapper category-map miss (e.g. unmapped notehead variant nearby) | 0 | None found |

So almost every FN is a **real model failure**, not a fixable wrapper bug.
Expanding `_CATEGORY_MAP` will not help recall on this set.

### Per piece

| Piece | Cells | TM TPs | YOLO TP | YOLO FP | YOLO FN | YOLO P | YOLO R | TM-FPs avoided by YOLO |
|---|---|---|---|---|---|---|---|---|
| **wtc-p5** (Bach WTC page 5) | 15 | 207 | 198 | 0 | 9 | 100 % | **95.7 %** | 5 |
| **wtc-p10** (Bach WTC page 10) | 5 | 30 | 6 | 1 | 24 | 85.7 % | **20 %** | 2 |
| **beet5** (Beethoven 5th, dense orchestral) | 5 | 5 | 1 | 0 | 4 | 100 % | **20 %** | 12 |

YOLO is **near-perfect on WTC page 5** (its in-distribution case: clean
two-staff keyboard score, light texture) and **catastrophic on WTC page 10
m1–m4**, where it misses 24 of 30 TM TPs. Those four measures are worth a
separate eyeball pass — likely an image-quality, scale, or notation-style
issue specific to that page.

The Beethoven case is more nuanced: TM had only 5 real symbols among its 17
filled verdicts (the other 12 were TM hallucinations — orchestral score is
the template matcher's stress test). YOLO missed 4 of those 5 *but* did not
repeat any of the 12 TM mistakes. On Beethoven specifically:

- TM precision: 5/17 = 29 % (template matcher really struggles here)
- YOLO precision on the same ground truth: 100 %
- Both engines have low recall, just in different ways.

## Where YOLO quietly wins, but the math doesn't credit

19 of the 25 verdict cells contain detections the template matcher flagged
that the human marked **FP** — i.e. TM mistakes. **YOLO replicated only 1 of
those 20 TM mistakes.** The other 19 are "TM-FP avoided by YOLO" — concrete
evidence that YOLO is more discriminating than TM, but our P/R math here
can't credit them (we'd need ground-truth-style FP-free regions, which the
verdict set doesn't provide).

Beyond that, YOLO emits **294 detections** on these 25 cells that have no
TM verdict to inherit (mostly clefs, augmentation dots, beams, dynamics). Some
fraction of those are real symbols TM doesn't even attempt — they're also
unrewarded in this measurement.

## Speed (recap)

On the same 25 cells:

- Template matcher: ~1100 ms / cell (Phase 2.8 result)
- YOLO r2 on MPS: **76 ms / cell** median (mean 89 ms, min 52, max 154)

≈14× faster. A 100-cell page is ~7.5 s with YOLO vs ~110 s with the matcher.

## Recommendation

**Keep both. Build a voting layer with YOLO as the primary signal and TM as a
recall safety net.**

Reasoning:

1. **Don't drop TM.** Recall drop from 100 % → 85 % overall is too much for a
   QC pipeline whose value is "human reviews everything flagged." A 15 %
   miss rate on real symbols is 15 % of errors going un-flagged. The
   wtc-p10 m1–m4 cells show YOLO has unpredictable blind regions.

2. **Don't drop YOLO.** It's 14× faster, 7 points more precise, sees clefs/
   dynamics/augmentation dots that TM doesn't even try, and avoids 95 % of
   TM's FPs on the same cells. Especially valuable on orchestral input
   (TM precision drops to 29 % on Beethoven; YOLO stays at 100 %).

3. **The combination is cheap.** YOLO 76 ms + TM ~1100 ms ≈ 1.18 s/cell —
   only ~7 % slower than running TM alone. No reason not to do both.

Concrete voting suggestion (cheap to prototype, no retraining):

- **Both engines agree** at the same location/category → high confidence,
  auto-accept candidate.
- **Only TM** detects there → keep, flag for human review (YOLO's miss rate
  is non-zero, can't trust TM-alone signal blindly).
- **Only YOLO** detects there → keep, flag for human review (these are the
  294-per-25-cells "extras" YOLO finds — many real, but unverified in our
  set).
- **Disagreement** (different category at same location) → flag, human resolves.

Before shipping voting, **do the wtc-p10 m1–m4 forensic pass.** If YOLO's
24-symbol miss there is fixable (image preprocessing, tile size, conf
threshold) the case for relying on it strengthens substantially. If it's a
fundamental model limitation, the voting layer is the only safe path.

### What this report does NOT settle

- **Real-world recall on YOLO's "pending" 294 detections.** Many are real
  symbols not in TM's vocabulary (clefs, augmentation dots, beams). To
  measure them we'd need to hand-annotate YOLO's output the same way
  Phase 2.5 hand-annotated TM's — a separate ~hour of human labor.
- **Whether the recall gap closes with a larger model.** r2 is yolov8m at
  imgsz 1280. A yolov8l or yolov8x run on the full (non-dense) DeepScoresV2
  could plausibly close 5–10 of the 33 "no YOLO bbox" misses.
- **wtc-p10 m1–m4 specifically.** All four measures show all 6 TM TPs
  missed by YOLO. This is too clustered to be random — needs a look at the
  cell images and YOLO's actual raw output on those cells.

## Artifacts produced by this run

| Path | What's in it |
|---|---|
| `benchmarks/omr-phase3.1/verdicts-yolo/*.verdict.json` | 25 ported verdicts, one per cell |
| `benchmarks/omr-phase3.1/port_report.json` | Detailed per-cell port stats, matched pairs, orphan lists |
| `benchmarks/omr-phase3.1/results-yolo/report.md` | Standard scorer output for YOLO |
| `benchmarks/omr-phase3.1/results-yolo/per_cell.csv` | Per-cell P/R |
| `benchmarks/omr-phase3.1/results-yolo/per_detection.csv` | Per-YOLO-detection verdicts |
| `tools/omr/annotate/port_verdicts_to_yolo.py` | The port script (clone of `port_user_verdicts.py`'s matching loop, cross-engine flavor) |

Reproduce with:

```bash
python3 -m tools.omr.annotate.port_verdicts_to_yolo \
  --tm-verdicts-dir benchmarks/omr-phase2.5/verdicts \
  --tm-detections-dir benchmarks/omr-phase2.5/detections \
  --yolo-detections-dir benchmarks/omr-phase3.1/detections \
  --out-dir benchmarks/omr-phase3.1/verdicts-yolo \
  --report benchmarks/omr-phase3.1/port_report.json

python3 -m tools.omr.annotate.score \
  --verdicts-dir benchmarks/omr-phase3.1/verdicts-yolo \
  --detections-dir benchmarks/omr-phase3.1/detections \
  --manifest benchmarks/omr-phase2.5/cells.json \
  --out-dir benchmarks/omr-phase3.1/results-yolo
```
