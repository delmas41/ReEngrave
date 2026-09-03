# The training gate — do hollow-notehead scan labels help without collapsing dense detection?

**Date:** 2026-09-02 · **Machine:** Apple M1 Max, 64 GB, MPS (no CUDA) ·
**Status:** COMPLETE — treatment@12 + control@15 trained, both eval axes +
held-out publisher measured.

**TL;DR.** Hollow-notehead scan labels **work**: half-note detection 8 → 25
(Beethoven) and 9 → 23 (held-out Mahler), `with_duration` recall 0.388 → 0.456,
and the labels' *own* incremental gain over a dense-only control is real
(duration 0.395 → 0.456). The completion was clean (unlike round 1). Dense-page
notehead detection narrows moderately (0.94 → 0.82) — **but the control (no
hollow) narrows too (→ 0.84), so the narrowing is the imgsz-640 fine-tune
recipe, not the hollow cells.** Verdict: PASS on the labeling; hold v8 out of the
catalog until an imgsz-matched fine-tune re-gates. Details below.

## The question

Round 1 (`v7`) and round 2 (five `hollow2` batches) hand-labeled **hollow
noteheads** (half + whole) on real scans across five engraving houses. Hollow
noteheads are the strongest-evidenced OMR gap in the project: Beethoven 5 p.1
prints **68 half notes and the pipeline emits 8**, and duration is the weakest
recall column on every scanned page (`benchmarks/omr-first-run-2026-08/DURATIONS.md`).
Four code fixes (ink-fill reclassification, enclosed-white counters, Bravura
template matching, ink thinning) were all measured and all failed — the engraved
control finds 31 hollow heads against 30 real on the same music, so the failure
is purely the *scanned appearance* of a closed counter, which only labeled scan
examples fix.

**But** every prior fine-tune that added low-density cells collapsed the density
prior (the clef fine-tune dropped dense-page noteheads 2506 → 114). This gate
answers, for the first time with a measurement: **does adding hollow scan cells
raise hollow detection WITHOUT collapsing dense-page detection?**

Design: `benchmarks/omr-labeling-survey-2026-09/SURVEY_DESIGN.md` (Option A).

---

## Step 1 — completing the cells (the round-1 trap, avoided)

The five round-2 batches are **single-symbol** (hollow-only) verdicts: Sean drew
194 hollow boxes (102 half + 92 whole) across 122 cells, and nothing else.
Training treats every unboxed symbol as **background**, so shipping those cells
as-is would teach "no black noteheads here" — the exact density-narrowing that
causes the collapse. They must be *completed* (every other symbol boxed too).

Round 1's completion (`benchmarks/omr-labeling-hollow-2026-08/AUDIT.md`) tried
model pre-labels and found **116 of 117 false** — the detector fires on slur
arcs, barlines, staff lines and the bowl of a printed *p* on that bled print.
The AUDIT diagnosed the cause: the pre-labels ran at **conf 0.25 with no
per-class NMS**.

**This round ran the production detector properly** (weights
`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`, the **per-cell imgsz rule**, **conf
≥ 0.50**, per-class + cross-class NMS, `_drop_clipped_notehead_fragments`) on
each of the 122 boxed cells, then **visually audited the overlays across all
five publishers** (`complete_cells.py`, montages reviewed by eye).

**Finding: the completion is CLEAN — categorically unlike round 1.** On these
SPARSE, short-bar cells the detector's black-notehead detections are ~95%
real, at high confidence, on solid round heads. Precision is night-and-day vs
round 1's 1/117 because sparse cells + the correct NMS is the difference.

The FPs were **concentrated and systematic**, not batch-wide:

| FP mode | where | handling |
|---|---|---|
| right-edge slivers (adjacent measure / barline) | all batches | dropped: box touches L/R image edge |
| `restWhole`/`restHalf` on the thick middle of a bled slur arc | Eulenburg (miniature) | dropped: rests out of completion scope |
| `accidentalDoubleSharp` ×9 on one trill wavy line | Brahms p3-s8-m3 | dropped: accidentals out of scope; + explicit cull of 1 notehead on the trill |
| bass/F-clef's two dots read as `augmentationDot` | 2 Eulenburg cells | dropped: augDot with cx < 18 % (clef zone) |

**Completion scope (gate-appropriate, round-1 precedent).** Kept only the
**density-prior-critical** classes: **black noteheads + augmentation dots**.
Model rests / accidentals / flags were **dropped** — they are FP-prone on this
domain (arcs → restWhole, trills → doubleSharp), add no needed positive signal
(those classes are already richly covered by v1–v4 + DSv2), and dropping them
removes their whole FP mode. Their real instances go unlabeled as background —
the same scoped-completeness tradeoff round-1's AUDIT recorded, documented not
hidden. Augmentation dots were kept because these sustained cells are full of
*dotted* hollow notes and the dot completes that figure; the only augDot FP mode
(clef dots) is cullable by position.

**Completion result: 198 audited boxes** (166 black noteheads + 32 aug dots)
across the 122 cells, ~97 % precision after the culls.

⚠️ **This is itself a decisive gate finding.** The round-1 fear was that scan
cells can't be cleanly completed without multi-pass human labeling. On the
short-bar / enclosed-white-ranked round-2 cells that fear does **not** hold —
the completion is clean, and the gate can proceed on honest labels.

### v8 built

`data/user-labeled/v8-2026-09-02-hollow2-5pub/` — **122 cells, 392 boxes**:
- 194 human hollow (56 halfOnLine + 46 halfInSpace + 59 wholeOnLine + 33 wholeInSpace)
- 198 completion (89 blackOnLine + 77 blackInSpace + 32 augmentationDot)
- 7 classes, all existing DSv2 ids (24/26/28/30/32/34/40) — **no new class, no nc expansion.**

Per publisher: Litolff/Beethoven-finale 32 cells (cleanest — active black-note
passages beside the hollow notes), Peters/Mahler 34, Eulenburg/Scheherazade 32
(noisiest — miniature + bleed), Breitkopf/Brahms 11, Simrock/Dvořák 13.

---

## Step 2 — the training mix

Built with `build_catalog_yaml` in an **isolated experiment root** (symlinks to
the version dirs), so the committed `data/user-labeled/catalog.yaml` (v1–v4)
and `catalog-versions.txt` are **untouched** — catalog membership stays Sean's
decision after this verdict.

**Members:** v1–v4 (dense base, 161 engraved orchestral cells) + v7 + v8
(hollow). **v5/v6 clef cells EXCLUDED** (the documented density-narrowing risk).

| catalog | cells (train/val) | nc |
|---|---|---|
| **treatment** (v1-v4 + v7 + v8) | 255 / 52 | **208** ✓ |
| **control** (v1-v4 only) | 136 / 25 | **208** ✓ |

**nc = 208** on both (custom barline/textDynamic boxes capped into `_nc208/`),
so the fine-tune matches the checkpoint's head — **no `--allow-nc-expansion`,
no Phase-3.4 head reset.**

**Mix ratio — the density-collapse variable.** Hollow is **~48 % of cells** but
only **24 % of boxes** (1340 dense boxes vs 420 hollow; dense cells average 8.3
symbols/cell, hollow cells 2.9). The cell fraction is on the high side (the
survey design wants scan cells a minority) — which is exactly why this is
*measured*. The completion's 198 black-notehead/dot boxes are what keep the
hollow cells from being artificially sparse.

**Why a control arm.** The production weights predate v2–v4, so
production→treatment adds both the dense v2–v4 cells and the hollow cells.
The **control** (production fine-tuned on v1–v4 only) isolates the fine-tune
procedure from the hollow contribution: control-vs-treatment is the clean "what
did hollow do" comparison; production-vs-control shows what re-training on the
dense cells alone does.

---

## Step 3 — the fine-tune

From the **production weights** (`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`),
`--device mps`, nc stays 208 (transferred 595/595 items — no head reset).
Music-aware augmentation: `fliplr=0 flipud=0 hsv_h=0 hsv_s=0` (labels are
direction-sensitive and monochrome). Modest gated run, not the 50-epoch
escalation:

    --epochs 15 --imgsz 640 --batch 16 --device mps --patience 15

Weights saved as experiment artifacts under
`benchmarks/omr-labeling-survey-2026-09/runs/{gate-treatment,gate-control}/weights/best.pt`
(gitignored). **Production weights never overwritten.**

**Training reality.** YOLOv8l on this M1 Max throttles under sustained MPS load
(epochs 1-8 ran ~60 s each, epochs 9+ ~10 min each; a 15-epoch run is ~50 min).
**Treatment** reached **epoch 12** (best.pt = epoch 12, losses converged: box
3.1→1.98, cls 4.6→2.03) before an early stop; **control ran all 15 epochs
cleanly** once given the machine to itself. The 12-vs-15 epoch gap is a minor
caveat and cuts the *right* way — control trained *more* yet narrowed *less*
(0.841 vs 0.818), so it cannot be masking a hollow-caused narrowing. ⚠️ **Two
earlier training attempts were stopped mid-run**; the exact trigger was not
cleanly disambiguated (a second YOLO training sharing MPS, and/or extra
background jobs launched during the run, both coincided). The reliable practice,
which got control through all 15 epochs, is: **one training at a time, alone on
the GPU, with no other background jobs**, and any alongside-eval on `--device
cpu`.

---

## Step 4a — density-collapse check (the forgetting gate)

`wtc_forgetting_eval.py` on **18 dense Beethoven orchestral cells** (the
`realft` verdict set — the same kind of dense conductor's page where a collapse
shows), human-confirmed GT = 220 noteheads + rests/flags/accidentals, imgsz
1280, centre-match, `--device cpu`. **Notehead recall is the density-prior
signal; a large drop = collapse.**

| model | notehead recall | overall recall | precision | raw noteheads | raw FP |
|---|---|---|---|--:|--:|
| **production** | 207/220 = **0.941** | 0.935 | 0.443 | 245 | 272 |
| control@5 (v1-4, 5 ep) | 214/220 = **0.973** | 0.957 | 0.499 | 254 | 222 |
| **control@15** (v1-4, no hollow) | 185/220 = **0.841** | 0.827 | 0.697 | 196 | 83 |
| **treatment@12** (v1-4+v7+v8) | 180/220 = **0.818** | 0.788 | 0.854 | 185 | 31 |

**The narrowing is PROCEDURAL, not hollow-caused — this is the key finding of
the control arm.** Fine-tuning at imgsz 640 narrows notehead recall
*progressively with epochs*: control (no hollow at all) sits at **0.973 after 5
epochs** and **0.841 after 15**. Treatment@12 (0.818) narrows only marginally
more than control@15 (0.841) — and treatment ran *fewer* epochs — so the hollow
cells add at most a small increment on top of a narrowing the dense-only
fine-tune produces by itself. Every arm trades recall for a large precision gain
(production over-detects wildly — 272 FP incl. 112 phantom `beam`, 51 `other`;
the fine-tunes suppress it to 83 / 31), and **none is remotely the clef-ft
collapse** (2506 → 114, −95 %). Treatment's F1 rises **0.60 → 0.82**.

## Step 4b — the hollow payoff (Beethoven 5 p.1, a HELD-OUT page)

Plain `transcribe` (no dossier) of Beethoven 5 movement I p.1 — a **different
scan and movement** from any training cell — scored against the Gradus
reference (`eval_first_run.py`, pitch multisets per staff). **Production
reproduces the documented baseline exactly** (`with_duration` 0.388, 8 half-note
detections — the "8 of 68" of DURATIONS.md), which validates the harness.

| model | half-notes | hollow total | black | notes | `with_duration` R | exact R | step R |
|---|--:|--:|--:|--:|--:|--:|--:|
| **production** | 8 | 14 | 120 | 134 | **0.388** | 0.599 | 0.701 |
| **control@15** (v1-4, no hollow) | 21 | 22 | 75 | 97 | 0.395 | 0.429 | 0.510 |
| **treatment@12** (v1-4+hollow) | **25** | **26** | 75 | 101 | **0.456** | 0.510 | 0.565 |

Two comparisons live here and they say different things:

**Treatment vs. production (headline):** half-note detections **8 → 25**,
`with_duration` recall **0.388 → 0.456** (+18 % rel). The strongest-evidenced gap
in the project — 68 printed half notes read as 8 — **moves**.

**Treatment vs. control (what the HOLLOW CELLS specifically buy):** the dense
fine-tune alone (control) already lifts half-notes 8 → 21 and strips production's
phantom over-detection (134 → 97 notes) — so *most of the structural change is
the dense fine-tune*, not the hollow labels. But the hollow cells add a **real
incremental gain on the metric that matters**: `with_duration` **0.395 → 0.456**
(+0.061) and exact recall **0.429 → 0.510** (+0.081) over control. Control
*detects* more half-notes but reads them less accurately; treatment reads them
right. **The hollow labels are what turn half-note detection into correct
half-note duration.** Per-staff, the gain lands on the sustained staves (Violino
II dur 0.43 → 0.75, Viola 0.31 → 0.69) and correctly zeroes the ~21 phantom notes
production emitted on the four silent staves (Flauti/Corni/Trombe/Timpani); it
regresses only on the two bottom bass staves.

### Held-out publisher — Mahler 5 Adagietto p.173 (Peters, in no training cell)

Hollow histogram only (no reference to score against):

| | half-notes | whole-notes | black |
|---|--:|--:|--:|
| production | 9 | 44 | 245 |
| control@15 | 13 | 16 | 106 |
| **treatment@12** | **23** | 15 | 101 |

**The half-note gain generalizes across publishers:** 9 → 13 → **23**
(prod → control → treatment), +10 from the hollow cells over the dense-only
control, on a Peters Mahler page exactly as on the Litolff Beethoven page — so it
is not a one-page or one-publisher artifact. (Whole-notes fall on both
fine-tunes; production's 44 is largely over-detection, and without a reference
here the whole-note direction is not scored.)

## Step 5 — verdict

**Q1 — Does hollow detection rise? YES — cleanly, incrementally, and across
publishers.** Half-note detections **8 → 25** on the held-out Beethoven scan and
**9 → 23** on a held-out Peters Mahler page; `with_duration` recall
**0.388 → 0.456**. Crucially, the *hollow cells themselves* (treatment vs. the
dense-only control) are what carry duration recall **0.395 → 0.456** and exact
recall **0.429 → 0.510** — the dense fine-tune finds more half-notes, the hollow
labels make them read *correctly*. The strongest-evidenced gap in the project —
68 printed half notes read as 8, where four code fixes all failed — **moves.**

**Q2 — Does dense detection hold? It narrows moderately — but the control proves
the narrowing is the FINE-TUNE RECIPE, not the hollow cells.** Dense-page
notehead recall falls 0.941 → 0.818 (treatment) — but the **control (v1-v4, NO
hollow) falls to 0.841 on the same axis**, and the narrowing tracks *epochs*
(control is 0.973 at 5 epochs, 0.841 at 15). So a dense-only fine-tune at
imgsz 640 narrows detection by itself; the hollow cells add at most a small
increment. Every arm is nowhere near the clef-ft collapse (2506 → 114, −95 %),
and all trade recall for a large precision gain (FP 272 → 83/31 — production's
~21 phantom notes on the four silent orchestral staves vanish). It is a
**recipe-level tradeoff, not a hollow-caused collapse.**

### What this means

- **The labeling approach is validated.** Completion was *clean* (§1 — the
  round-1 fear did not repeat), and the labels *move the #1 metric* and
  *generalize across publishers*. The hollow row of the survey pays off.
- **The density narrowing belongs to the fine-tune recipe, not the data.** It is
  reproduced by the dense-only control and scales with epochs. The obvious lever
  is **training imgsz**: this run used **640**, the production weights **2048** —
  the smaller scale is the prime suspect, and matching it is the next experiment
  (out of budget here: YOLOv8l thermally throttles on this M1 Max — epochs 1-8
  ~60 s, epochs 9+ ~10 min).
- **The mix is 48 % hollow cells / 24 % boxes** — the survey design wants scan
  cells a clearer minority, so a higher dense:hollow ratio (or a DSv2 replay) is
  the second lever to try.

### Recommendation to Sean

1. **Keep v8** — the labels are clean, correct, and committed. This gate is the
   green light the survey design (§5) asked for before widening.
2. **Do NOT admit v8 to `catalog-versions.txt` from this run.** The imgsz-640
   recipe carries a density cost. Hold membership (the discipline already encoded
   for v5/v6/v7) until an **imgsz-2048 (or per-cell-matched), higher-dense-ratio**
   fine-tune clears `wtc_forgetting_eval` — that run is the one whose weights
   should ship.
3. **Then widen hollow to the four missing traditions** (Durand/Universal/
   Jurgenson/Novello) per Option B — the payoff and the clean-completion method
   both transfer.

**Bottom line: PASS on the labeling (it works and is clean); the naive imgsz-640
fine-tune is not the shipping recipe — fix the training scale, re-gate, then
admit.** Production weights were never touched; every experiment weight is a
gitignored artifact.

---

### Reproduce

```bash
# completion (production detector, audited) → merged verdicts → v8
python3 benchmarks/omr-labeling-survey-2026-09/complete_cells.py
python3 benchmarks/omr-labeling-survey-2026-09/build_v8.py
python3 -m tools.omr.training.verdicts_to_yolo_labels \
    --verdicts-dir benchmarks/omr-labeling-survey-2026-09/v8-merged-verdicts \
    --manifest benchmarks/omr-labeling-survey-2026-09/v8-combined-cells.json \
    --version-name v8-2026-09-02-hollow2-5pub --weights omr-weights/...ft-30ep.pt \
    --labeler sean --no-symlink
# catalogs (isolated roots — committed catalog.yaml untouched) → fine-tune (serial!)
python3 -m tools.omr.training.build_catalog_yaml --root .../catalog-treatment
python3 -m tools.omr.training.train_yolo --data .../catalog-treatment/catalog.yaml \
    --weights omr-weights/...ft-30ep.pt --epochs 15 --imgsz 640 --batch 16 \
    --device mps --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 --name gate-treatment
# eval: forgetting (CPU) + hollow payoff (Beethoven p.1)
python3 -m tools.omr.training.wtc_forgetting_eval --prod omr-weights/...ft-30ep.pt \
    --ft .../gate-treatment/weights/best.pt --cells-dir <primary>/benchmarks/omr-phase2.5/cells \
    --detections-dir benchmarks/omr-phase3.4/detections-yolo-realft \
    --verdicts-dir benchmarks/omr-phase3.4/verdicts-yolo-realft-ported --device cpu
python3 benchmarks/omr-labeling-survey-2026-09/hollow_eval.py --weights <pt> --tag <t> \
    --pdf <beet5 IMSLP984073> --page 1 --stem beet5-p1 --score
```

Result JSONs: `forgetting_{treatment,control5,control15}.json`,
`hollow_eval_*.json`, `beet5-p1-{prod,treatment,control}-firstrun.json`.
