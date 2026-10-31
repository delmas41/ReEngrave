# Clef pseudo-label training — scoping plan

**Status:** proposed (not started). Written 2026-07-12 after validating that LEGATO
reads orchestral clefs reliably (2 Mahler pages) but its meter is not trustworthy.

## Goal & hypothesis

**Problem (validated):** on real orchestral scans the YOLO model detects ≈0 clef
glyphs, so the pipeline falls back to the position-default → **all-treble**
(Mahler p13: 26/26 treble; idx1: 14 treble / 3 bass / 1 spurious tenor, missed
alto+perc). The clef *glyphs are clearly on the page* — the model just doesn't
fire on the real engraving. This is a **synthetic→real domain gap**, not a
missing-class problem.

**Hypothesis:** adding **real-scan clef examples** to the training set will make
YOLO fire on real clefs, **without catastrophic forgetting**, because clefs are
already existing classes — we add examples, not classes.

## Why this is low-forgetting-risk (the key insight)

Every past training collapse (imslp-catalog Phases A–L, Phase 3.4 F1→79.3%, the
nc=214 footgun) came from **expanding the class head** (nc 208→214) which
re-initialized the classifier. **This plan does NOT add classes.** Treble/bass/
alto/tenor clefs are existing DSv2 classes (`clefG`/`clefF`/`clefC…` → see
`transcribe.py::_clef_name_from_class`). We keep **nc=208**, so:

- No head re-init → the specific mechanism of every prior collapse is absent.
- We fine-tune **from the production checkpoint**, not from scratch.
- We **mix in** a sample of the original DSv2 data so the model doesn't drift.
- Low LR, few epochs (the verified anti-forgetting recipe).

## The labeling pipeline: LEGATO-assisted, human-gated

LEGATO gives clef *type per voice*, top-to-bottom (its `%%score` voice order),
but **not pixel boxes**. And the valuable cases are exactly the disagreements,
where LEGATO *might* be wrong — so a human confirms. We combine three sources,
each doing what it's good at:

1. **Geometry proposes a STARTING clef per staff (accelerator, not truth).**
   Most staves carry one clef at the start; `staff_detector` +
   `measure_extractor` locate that region and a connected-component blob gives a
   bbox. This is only a *first proposal* — see the completeness caveat below.
2. **LEGATO provides WHAT (the type)** — each staff's clef from its top-to-bottom
   sequence, and it also emits **inline mid-bar clef changes** in the ABC, which
   can seed proposals for those too.
3. **Human triages AND completes (the confidence gate).** Load proposals into the
   existing `tools/omr/annotate` UI (`t`/`f`/`c` to confirm/correct types; `a` to
   draw boxes the proposal missed). The human confirms types **and adds any clef
   the geometry didn't propose** — critically, **mid-bar clef changes** (a part
   switching clef for range). LEGATO's errors never reach the labels.

### Label completeness is load-bearing (must not skip)

Clefs are **not** always at the start of a staff — parts change clef mid-bar for
range (the "clef-reset" case). In YOLO labeling, **anything left unboxed becomes
background the model is penalized for firing on**. So boxing only start-of-staff
clefs and missing a mid-bar change would *teach the model to suppress clef
changes* — reinforcing the exact weakness we're fixing. Therefore: **box every
clef present in each cell, initial and mid-bar.** The training side needs no
special handling (a mid-bar treble clef is the same class as an initial one), so
completeness in the *labels* is the whole job. Geometry's start-of-staff proposal
is a convenience; the human owns completeness. (For Phase 0, we can skip the
geometry auto-proposer entirely and box from scratch with LEGATO type hints.)

Output: verdicts → `verdicts_to_yolo_labels.py` → a **new** `data/user-labeled/
vN-<date>-clef` → `build_catalog_yaml.py` (unions versions, nc=208 capped).

## Training recipe (anti-forgetting)

- Start from `omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (production).
- `train_yolo.py`, **nc=208** (no `--allow-nc-expansion`).
- Dataset = new real-clef labels **+ a sampled slice of DSv2** (rehearsal, so we
  don't forget the 98.8% we have).
- Low LR, ~few epochs. Consider freezing early backbone layers.
- Write to a **new** file, e.g. `deepscoresv2-yolov8l-clef-ft-<date>.pt`. **Never
  overwrite production.**

## Eval / keep-or-discard gate

Keep the new weights **only if BOTH** hold; otherwise discard (rewind):

1. **No forgetting:** F1 on the Bach WTC verdict set stays ≈98.8% (regression =
   forgetting = discard). Use `eval_on_score_cells.py`.
2. **Real lift:** clef-detection rate on a held-out set of real orchestral pages
   (Mahler/Debussy) goes up materially, and the pipeline stops defaulting to
   all-treble. Measure with the `second_opinion_pass` clef-presence + the raw
   clef-detection-rate metric.

## The four rewind rails (nothing is lost)

| Asset | Isolation | Rewind |
|---|---|---|
| Code | new branch off current | `git checkout` |
| Weights | new `.pt`, production untouched | keep loading old file |
| Data | new `data/user-labeled/vN` | drop it from the catalog |
| Pipeline | `OMR_WEIGHTS_PATH` env | point back |

Worst case of failure = one unused `.pt` on disk (like the kept-but-never-loaded
`phase-j-mix` weights). No existing asset is modified.

## Cost

- **LEGATO pre-labeling + eval:** local/CPU (~75 s/page LEGATO, cached).
- **Human triage:** minutes/page.
- **The fine-tune:** needs a GPU — a vast.ai run (see `VAST_AI_SETUP.md`),
  roughly a few dollars for a short fine-tune. This is the only spend, and it
  buys nothing lost — only the new `.pt`.

## Risks & mitigations

- *LEGATO clef errors* → human triage gate (they never reach labels).
- *Forgetting* → nc=208 (no head re-init) + checkpoint fine-tune + DSv2 rehearsal
  + the Bach-F1 eval gate.
- *Voice↔staff alignment* → geometry owns location; human owns the type mapping.
- *Too little data to move the needle* → start tiny (Phase 0), measure, scale
  only if there's lift.

## Complementary lever (not either/or)

**Domain augmentation** (ScoreAug/Augraphy — already being explored in the
"Domain augmentation for training" session) attacks the same gap from the other
side: make *synthetic* clefs look scanned, no labeling needed. Real labels +
augmentation together is the strongest fix. Worth coordinating so the two efforts
compound rather than duplicate.

## Phased execution (go/no-go before compute)

- **Phase 0 — prove the loop (cheap, ~1–2 pages).** LEGATO-assisted-label 1–2
  real pages → tiny fine-tune → eval. Success = Bach F1 held AND real-clef
  detection up on those pages. Also proves the rewind works. **Decision gate:**
  only scale if Phase 0 shows lift with no regression.
- **Phase 1 — scale (only if Phase 0 passes).** Label a real-orchestral batch
  (10–30 pages across Mahler/Debussy), fine-tune, full eval, deploy the new `.pt`
  via `OMR_WEIGHTS_PATH` only if the gate passes.

## Before we start — what I need from you

1. Approve this approach (or adjust).
2. OK to spend a few $ on a short vast.ai fine-tune for **Phase 0** only.
3. Nothing else — Phase 0 touches no production asset.
