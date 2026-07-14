# ScoreAug domain-augmentation — FAIR test (fine-tune + control)

**Date:** 2026-07-13 · **GPU:** rented vast.ai RTX 4090 (Greece, ~1.2 h, ~$0.55 incl. one dead-network host destroyed) · **Branch:** `claude/scoreaug-fair-test-a2928e`

## TL;DR — augmentation does NOT help; it hurts. Fine-tuning on DSv2-dense hurts, period.

The prior run (2026-07-13, from-COCO, no control) was inconclusive. This run fixes
both flaws: it **fine-tunes the production checkpoint** (nc=208, no head reset) and
adds a **clean-trained control**. The result is unambiguous:

- **Arm A (augmented) LOSES to Arm B (clean)** on real dense recall — the reverse
  of the hypothesis. Success required A > B; we got A ≪ B.
- **Both arms regress** the keyboard-WTC guardrail (−0.12 to −0.14 recall).
- So **augmentation is net-negative**, and fine-tuning production on DSv2-dense
  (clean *or* augmented) is counterproductive for real-scan detection.

**Do not promote either checkpoint. Do not pursue ScoreAug/Augraphy-on-DSv2 further.**

## The experiment (3-way, one box)

| Model | What | Weights |
|---|---|---|
| **Baseline** | production, unchanged | `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` |
| **Arm A** | fine-tune production on the **AUGMENTED** dense set | ScoreAug blank+show-through + Augraphy (6 effects) |
| **Arm B** (control) | fine-tune production on the **CLEAN** dense set | identical recipe, no augmentation |

Identical recipe both arms (only `--data`/`--name` differ): fine-tune from
production, **15 epochs, lr0 0.001, batch 2, imgsz 1280**, music-safe augs, no
backbone freeze, **no head reset** (nc-guard passed — production nc=208, data
nc=208, all three checkpoints verified to load 208 classes / 19 notehead classes,
distinct md5). Clean train = 1362 imgs; augmented train = 1362 + 681 degraded
twins (fraction 0.5); **shared clean val** (352) so the two arms are comparable.

## 1. DENSE WIN test — notehead recall on 140 real hand-labeled orchestral cells

Recall = matched GT noteheads / total GT noteheads (center-match, model-agnostic).
534 GT noteheads: beet5 313 / lamer 132 / mahler5 89. Precision is confounded by
incomplete human GT — the `(tp/n_pred)` column is shown only as context.

**conf 0.25** (imgsz 1280):

| source | GT | Baseline | Arm A (aug) | Arm B (clean) |
|---|--:|--:|--:|--:|
| beet5 | 313 | **0.537** (168/2527) | 0.077 (24/33) | 0.268 (84/582) |
| lamer | 132 | **0.742** (98/237) | 0.311 (41/53) | 0.485 (64/116) |
| mahler5 | 89 | **0.921** (82/1278) | 0.000 (0/4) | 0.640 (57/565) |
| **OVERALL** | 534 | **0.652** (348/4042) | **0.122** (65/90) | **0.384** (205/1263) |

**conf 0.50** (spray-suppressed — same ordering, so the ranking is not a
detection-count artifact):

| source | GT | Baseline | Arm A (aug) | Arm B (clean) |
|---|--:|--:|--:|--:|
| **OVERALL** | 534 | **0.322** (172/547) | **0.097** (52/61) | **0.210** (112/312) |

- Both fine-tunes **collapse** real-dense recall vs production (0.652 → B 0.384 → A 0.122).
- **Arm A (augmented) is far WORSE than Arm B (clean)** — augmentation hurt.
- Detection counts tell the story: production fires **4042** notehead detections
  across the 140 cells, Arm B **1263**, Arm A only **90** (~0.6/cell). Arm A went
  nearly silent on real scans.

## 2. WTC REGRESSION bar — 18 keyboard-Bach cells (center-match GT from ported verdicts)

Absolute F1 here uses a different (model-agnostic) scoring than the historical
98.8%; the meaningful signal is **recall delta vs production ≈ 0**.

| model | overall recall | Δ vs prod | notehead | flag | rest |
|---|--:|--:|--:|--:|--:|
| production | 0.935 | — | 207/220 | 3/5 | 5/5 |
| Arm A (aug) | 0.797 | **−0.139** | 180/220 | 0/5 | 4/5 |
| Arm B (clean) | 0.814 | **−0.121** | 188/220 | 0/5 | 0/5 |

Both arms drop keyboard-WTC recall by ~12–14 points and lose non-notehead symbols
(flags, rests) — the dense-page fine-tune narrowed the model's density prior and
made it fire less on sparse keyboard pages. **Neither passes the regression bar.**

## 3. The decoupling — synthetic val is actively MISLEADING

Final DSv2-dense (synthetic) val, and both arms roughly plateaued by the end:

| model | synthetic val mAP50 | synthetic val recall | REAL-cell recall (§1) |
|---|--:|--:|--:|
| Arm A (augmented) | **0.546** (best) | 0.546 | **0.122** (worst) |
| Arm B (clean) | 0.486 | 0.485 | 0.384 |

Arm A is **best on synthetic-degraded val but worst on real cells**. The Augraphy
degradation created a *new synthetic domain* the model learned well (higher val)
but which is even further from real-scan texture than clean synthetic — so it
transfers worse. This is exactly why the prior from-COCO run's "mAP50 0.54 on
synthetic" meant nothing for real scans: **do not trust synthetic val as a proxy
for real-scan performance.**

## 4. Verdict & recommendation

- **Augmentation hypothesis: DISPROVEN with a control.** A > B was required; A ≪ B.
- **Fine-tuning production on DSv2-dense is counterproductive** — it overfits the
  synthetic domain, collapsing both real-dense recall and keyboard-WTC recall.
  Augmentation makes the synthetic-overfit *worse*, not better.
- **The synthetic→real gap is not a "add paper texture to DSv2" problem.** More
  synthetic training (however degraded) moves the wrong direction.
- **Path forward is NOT more DSv2 training.** The real levers remain: (a) the
  deterministic internal-consistency / dossier verification layers (which *abstain*
  where detection is blind rather than degrade it), and (b) real hand-labeled data
  or a contextual end-to-end second opinion (LEGATO/oemer) — not synthetic
  augmentation. See memory `project_domain_augmentation`, `project_dossier_verification`.

## Reproduce

- Training run-book: `tools/omr/training/HANDOFF_SCOREAUG_FAIR_TEST.md`
- Eval: `bash benchmarks/scoreaug-fair-test/run_eval.sh` (runs on the Mac, CPU)
- Raw: `dense_recall_1280_c25.json`, `dense_recall_1280_c50.json`,
  `wtc_armA.json`, `wtc_armB.json`, `train_csv/*-results.csv`
- Fine-tuned weights (negative result — safe to delete):
  `omr-weights/scoreaug-fair-test/ft-{scoreaug-armA,clean-armB}-best.pt`
