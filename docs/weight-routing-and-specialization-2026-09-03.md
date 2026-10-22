# Weight specialization and routing — the decision record (2026-09-03)

Written at Sean's request as the durable record of the 2026-09-03 discussion.
The question he raised: weights trained on one source work well on that
source; reused across publishers and scan qualities they should decay; broad
training should win everywhere at a small cost at home — so could weight
*categories* be chosen per input? Digital weights for digital engraving, scan
weights for scanned PDFs, maybe publisher- or era-specific weights?

This document holds what the project's own measurements say about each
assumption, the decision they led to (**fork on exactly one axis — scanned vs
digitally engraved — and defer the rest behind measured triggers**), what
shipped, and the process any future specialist weights must go through. The
implementation-level record (classifier thresholds, probe data, A/B
verification) is
[benchmarks/omr-weight-routing-2026-09/FINDINGS.md](../benchmarks/omr-weight-routing-2026-09/FINDINGS.md);
this is the strategy-level one.

---

## 1. The three assumptions, against what this project has measured

### 1.1 A specialist is strong at home — and the production base was already a specialist

No experiment was needed to confirm the first assumption, because the base
model has embodied it all along: trained predominantly on DeepScoresV2 —
*rendered* engraving — it IS "digital weights." F1 **98.8%** on the WTC
verdict set and pooled OMR-NED **0.13–0.14** on the engraved orchestral
benchmark, against **0.7960** on the five-publisher scan benchmark
([RESULTS.md](../benchmarks/omr-scan-e2e-2026-09/RESULTS.md)) — a factor of
~6, the largest accuracy cliff in the project. The sharpest single symptom:
Beethoven 5 p.1 prints 68 half notes and the pre-hollow output contained 8,
while an engraved control of the same music found 31 against 30.

### 1.2 Off-domain decay is real — and it arrives as collapse, not fade

The second assumption is measured repeatedly, and the decay is worse than the
gradual erosion one might picture:

- **The clef fine-tune** (July 2026) fixed its target and collapsed dense-page
  noteheads **2506 → 114** — fine-tuning a shared detector on sparse cells
  narrows its density prior. Robust to box fixes, label completion,
  anti-forgetting recipes, NMS and confidence sweeps. Dead recipe.
- **Phase 3.4's class expansion** (nc 208 → 214) silently re-initialized the
  head and cratered F1 to 79.3%. Dead recipe; the nc cap now guards it.
- **Domain augmentation** (synthetic scan degradation, the obvious idea for
  the scan gap) made things *worse* than clean fine-tuning: dense real-cell
  notehead recall production **0.652** → clean control **0.384** → augmented
  **0.122** — while the augmented arm scored *best* on synthetic validation.
  Dead recipe, and a warning about synthetic val sets.
- **Widening the test set exposes hidden specialization**, exactly as Sean's
  question assumed: the engraved benchmark's 3 → 11 widening found the eight
  new pages scoring roughly **2×** the incumbents' error, after sixteen fixes
  tuned on three pages
  ([FINDINGS.md](../benchmarks/omr-corpus-widening-2026-09/FINDINGS.md)).
  ⚠️ *A benchmark of three pages cannot falsify a story about one of them.*

### 1.3 The broad-vs-narrow trade exists in the limit — but is not the current binding constraint

The third assumption — broad weights slightly worse at home than a dedicated
specialist — is where the measurements add the correction that shaped the
decision. At this project's data scale the trade has barely materialized:

- The hollow labeling campaign was deliberately **publisher-diverse** (five
  publishers in Phase 1, four more in Phase 2), and the gate showed the labels
  lift scanned half-note detection **8 → 25 and generalize across
  publishers**; the density cost seen in the gate run was the *training
  recipe* (imgsz-640, epoch count — a pure-dense control fell the same way),
  not the diverse labels
  ([GATE_RESULTS via SHIP_RESULTS.md](../benchmarks/omr-labeling-survey-2026-09/SHIP_RESULTS.md)).
- The shipping run then held dense recall at **exactly 0.941 (Δ 0.000)**
  while lifting scanned half-notes 8 → 27 — and the engraved benchmark moved
  only **+0.0022 net, with 6 of 11 works improving** and one work
  (mozart-sym41, +0.0146) carrying the net.

Reading: a few hundred boxes cannot saturate a YOLOv8l, so pooled diversity
has been close to free while specialization has been the expensive direction.
But the trade Sean predicted is not imaginary — the ship run's own Pareto
frontier is it, already measurable: epoch 1 = maximum dense-hold (0.941,
duration 0.435), epoch 2 = maximum hollow (0.483) at −5 dense points. More
scan data will sharpen that frontier, which is exactly when per-domain
weights stop being optional.

---

## 2. The decision: fork on ONE axis, defer the rest

### 2.1 Why scanned-vs-engraved earns the fork

1. **The gap is a factor of ~6** (§1.1) — no other partition of the corpus
   comes close.
2. **The prior conflict is real at the ink level.** A scan reader must call a
   solid-looking head with a closed counter a half note; applied to clean
   engraving that prior misreads filled quarters. One set of weights holding
   both priors is exactly what the frontier in §1.3 prices.
3. **The router is trivially reliable.** Where the ink comes from — one
   full-page raster image vs vector drawings — separates with empty measured
   gaps (total coverage 0.95 vs 0.000; drawing counts 4 vs 428 over 147
   pages; see FINDINGS.md). No model, ≤ 77 ms per document.
4. **Both weights already exist, each measured best on its side** — the ship
   run accepted +0.0022 on engraved because there was one slot; routing
   un-pays it.
5. **Precedent:** per-domain configuration already won here twice — the
   DPI 300/600 split (sparse vs dense) and the `OMR_CLEF_WEIGHTS`
   decoupled-specialist slot. Note the clef-slot's lesson carries over: a
   specialist is safe when its *role* is narrowed (a second detector reading
   only headers; a whole-run weights choice), not when one shared detector is
   asked to specialize — that is the §1.2 collapse.

### 2.2 Why publisher- and era-specific weights are deferred

Deferred, not refused forever — but every current measurement points away:

1. **No publisher-specific model failure has been measured.** The pooled
   five-publisher hollow labels generalized; the one held-out-publisher
   wobble (Mahler/Peters p.172) is unscored and consistent with
   over-detection stripping, a caveat rather than a failure.
2. **Where publisher sensitivity IS measured, it lives in classical-CV
   thresholds, and per-edition tuning was explicitly refused there.** The
   tenor symmetry floor separated cleanly on Beethoven (gap +0.015) and was
   impossible on Mahler (overlap 0.137) — hence *"never tune a clef threshold
   on one edition."* The fixes that traveled were position-not-shape rules.
   Per-publisher *weights* would be that refused move, at far higher cost.
3. **Labels are the scarce resource.** Sean's hand-labeling hours come in
   batches of a few hundred boxes; splitting a phase across per-publisher
   pots starves every pot, and pooling is what passed the gate.
4. **Every weights file multiplies the eval surface.** One trustworthy
   headline took real work (`accuracy_record`, benchmark stamps, the
   four-stale-copies incident); N weight files means N benchmark tracks or
   unverifiable claims.
5. **Era mostly collapses into the same fork.** The scanned corpus *is*
   19th-century plate engraving; the digital corpus *is* modern typesetting.
   A separate era axis buys almost nothing today.

### 2.3 ⚠️ The triggers that reopen the question

Reopen on a measurement, not a hunch. Any of:

- **The publisher×symbol survey surfaces a publisher pooled labels cannot
  fix** — a labeling batch lands, the other publishers' rows move, that
  publisher's row does not.
- **A scan sub-family shows a forked preference of its own** — e.g. bitonal
  ccitt/jbig2 vs grayscale scans measurably preferring different
  checkpoints on the scan benchmark's rows.
- **The Pareto frontier starts binding at epoch 1** — dense recall falling
  the moment the specialist metric rises, on the first epoch, means capacity
  is finally contested and a dedicated fork is the honest resolution.

If a trigger fires, §4 applies unchanged; the router extends to N-way by
adding verdicts and targets, and nothing about the seam needs redesign.

---

## 3. What shipped (2026-09-03)

`transcribe()` routes when nothing pins the weights:

| input | classifier verdict | weights served |
|---|---|---|
| scanned PDF (ink = full-page raster) | `scanned` | `deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt` (production) |
| digitally engraved PDF (ink = vector drawings) | `engraved` | `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (prior production) |
| blank / ambiguous / unopenable | `unknown` | default (production) |

Semantics: an explicit `--weights` / `OMR_WEIGHTS_PATH` / `weights=` skips
classification entirely; `OMR_WEIGHT_ROUTING=0` is the kill switch;
`OMR_ENGRAVED_WEIGHTS` overrides the engraved target; a missing engraved file
falls back soft (one stderr line) so no machine that worked before can start
failing; any scan page wins the document verdict (an IMSLP scan behind a
digitally generated cover is a scan); text is not a signal (scans carry OCR
layers). The verdict and per-page evidence are recorded in the result JSON as
`weight_routing`. The web app routes too — the container mounts both files.

Verified by 35 new tests and a byte-identity A/B on both sides of the fork
(routed ≡ explicitly pinned, field-for-field, on the LilyPond Beethoven 5
fixture and the Litolff Beethoven 5 scan). **No benchmark figure moved**: all
26 harness call sites pin weights explicitly. A side effect worth naming: the
recorded engraved headline (0.1306 on `44a1745`) was measured with the prior
weights, so default engraved runs now use the weights the record describes —
record and shipped behavior agree again.

⚠️ One duplicate fact remains: `tools/omr/training/end_to_end_eval.py`
carries its own hardcoded `DEFAULT_WEIGHTS` (the prior checkpoint, consumed
by `orchestral_eval`'s `--weights` default). Routing made it *coherent* —
the benchmark measures what routing serves engraved inputs — but it is still
a second copy of a weights fact; reconcile it whenever the headline is next
re-recorded.

---

## 4. The process for ANY future specialist weights

The checklist the hollow ship validated; every step exists because skipping
it has already failed once here.

1. **A measured trigger first** (§2.3), stated with numbers, before any
   training run. "It would probably help" is what the domain-augmentation arm
   said too.
2. **Fine-tune FROM the broad base, never from scratch and never on the
   specialist slice alone.** Oversample the broad data so the specialist
   slice is a clear minority (the ship used 2× dense: 30% of cells / 14% of
   boxes hollow); keep music-aware augmentation (no flips, no hue).
3. **`save_period=1` and pick the checkpoint on external ground truth.** The
   narrowing scales with epochs, so the early checkpoint is the shipping
   knob; the internal val is a noisy proxy and does not get a vote. Map the
   Pareto frontier and ship only a clear win.
4. **Gate on BOTH benchmarks.** The specialist must win its own domain AND
   hold the other inside threshold (dense notehead recall within ~2–3 pts;
   pooled OMR-NED not materially regressed). A specialist is only testable if
   its domain *has* a benchmark — the scan benchmark's existence is what made
   this fork possible at all, and a publisher fork would first need a
   per-publisher one.
5. **Wire it as a routing target**: a constant beside the others, an env
   override, soft fallback to the default, provenance in the result JSON.
   Never a new required file, never a change to explicit-weights behavior.
6. **Do not split the labeling budget ahead of the trigger.** Pooled,
   publisher-diverse labeling is the measured winner until the day §2.3
   fires.

---

## 5. Cross-references

- Implementation, probe data, thresholds, A/B:
  [benchmarks/omr-weight-routing-2026-09/FINDINGS.md](../benchmarks/omr-weight-routing-2026-09/FINDINGS.md)
- The hollow gate and ship (the fork's two sides measured):
  [benchmarks/omr-labeling-survey-2026-09/SHIP_RESULTS.md](../benchmarks/omr-labeling-survey-2026-09/SHIP_RESULTS.md)
- The scan domain, measured:
  [benchmarks/omr-scan-e2e-2026-09/RESULTS.md](../benchmarks/omr-scan-e2e-2026-09/RESULTS.md)
- Why narrow benchmarks hide specialization:
  [benchmarks/omr-corpus-widening-2026-09/FINDINGS.md](../benchmarks/omr-corpus-widening-2026-09/FINDINGS.md)
- The dead recipes §1.2 leans on: PROJECT_STATUS.md's July arc
  (domain augmentation, the clef fine-tune, the Phase 3.4 collapse).
