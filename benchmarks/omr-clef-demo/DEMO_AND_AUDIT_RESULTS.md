# Clef fine-tune — end-to-end demo + broadened forgetting audit (2026-07-13)

Follow-up to `tools/omr/training/CLEF_FT_PHASE0_RESULTS.md`. Demos the clef
fine-tune end-to-end on a real orchestral page and broadens the forgetting audit
beyond the original 4-cell check. **Headline: the clef fix is real, but the
current `clef-ft` weights are NOT deployable — they collapse notehead detection
on dense pages. Root cause found; corrected retrain in progress.**

Weights:
- production: `omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`
- clef-ft (evaluated here): `omr-weights/deepscoresv2-yolov8l-clef-ft-2026-07-13.pt`

All runs: `--imgsz 1280 --dpi 300` (transcribe) / `--imgsz 1280 --conf 0.25` (eval),
per the "imgsz 1280 everywhere" rule.

---

## Task 1 — Mahler 5 p.11 (printed p.13, m.85) clef read

`tools/omr/transcribe.py`, page index 11: 3 systems, **26 staves**, 221 measures.
Compare `pages[].systems[].staves[].clef` (script: `compare_clefs.py`).

| model | clef distribution | staves changed |
|---|---|---|
| production | **treble ×26** (the all-treble disease) | — |
| clef-ft | **treble ×9, bass ×13, tenor ×4** | 17 / 26 |

Verified against the rendered page (`mahler_p11_render.png`): the mix matches the
score — clarinets / oboes / horns / violins I&II = treble; bassoons /
contrabassoon / tuba / trombones / cellos / basses / timpani = bass. **The clef
fine-tune fixes the all-treble disease on a real orchestral page.**

Remaining clef miss: the **violas** ("Violen", unmistakably an alto C-clef in the
image) are read as **tenor**, not alto — the alto→tenor confusion. (Original
Task 3.)

---

## Task 2 — broadened non-clef forgetting audit (Bach WTC verdict set)

`tools/omr/training/wtc_forgetting_eval.py`. 18 Bach WTC cells with human
verdicts (`benchmarks/omr-phase3.4/verdicts-yolo-realft-ported/wtc-*`), images
from `benchmarks/omr-phase2.5/cells/`. Ground truth = human-confirmed symbols
(TP-verdicted detection boxes ∪ FN noteheads). Both models re-run fresh and
scored identically; the production-vs-ft **delta** is the signal.

### Fair "did it detect the symbol" — center-distance matching (headline)

| center-match | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| production | 216 | 272 | 15 | 0.443 | 0.935 | 0.601 |
| clef-ft    | 206 |  91 | 25 | **0.694** | 0.892 | **0.780** |

**recall Δ (ft − prod) = −0.043.** No meaningful notehead forgetting on clean
music: notehead recall 207/220 → 201/220. clef-ft actually has **higher F1**,
driven by much better precision (far less hallucination: 91 FP vs 272).
Minor real drops: rests 5/5 → 2/5, flags 3/5 → 2/5.

### Strict localization — IoU≥0.5 matching

| iou-match | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| production | 205 | 283 | 26 | 0.420 | 0.887 | 0.570 |
| clef-ft    | 104 | 193 | 127 | 0.350 | 0.450 | 0.394 |

The IoU recall looks catastrophic (0.89 → 0.45) but is an **artifact of box
size**, not misses: clef-ft's notehead boxes average **92×75** vs production's
**60×53**; two concentric boxes that size have IoU≈0.46 (just under 0.5). Same
noteheads, looser boxes. (This is the thread that unravels the real bug — below.)

---

## The real bug — dense-page notehead collapse

The end-to-end Mahler run tells a different story than the sparse WTC cells:

| Mahler p.11 noteheads detected | count |
|---|---|
| production | **2506** |
| clef-ft (agnostic NMS, iou 0.5 — default) | **123** |
| clef-ft (class-aware NMS, iou 0.5) | 125 |
| clef-ft (class-aware NMS, iou 0.85) | 160 |

clef-ft finds **~5%** of the noteheads production does on a dense orchestral
page. Relaxing NMS barely helps (123 → 160), so it is **not** NMS-merging of the
oversized boxes — it is a genuine **detection collapse on dense/cluttered cells**.
Sparse Bach cells (notes far apart) hide it; dense conductor's scores expose it.

### Root cause

Training data defects in the 62 clef cells (`v5`+`v6`), which are sparse *m0*
cells (clef + key sig + a few notes):

1. **Notehead boxes ~1.6× too loose** — median normalized width **0.047** vs
   production's natural **0.029** (same 2048px canonical scale). Fine-tuning the
   (unfrozen) neck+head taught oversized notehead boxes → the WTC IoU artifact
   and the inference boxes at 92×75.
2. **Incomplete notehead labels** — several cells have real noteheads but **none
   labeled** (e.g. `mahler-p2-sys0-s2-m0`: 0 labeled, 3 real). Unlabeled
   noteheads train as background → a suppression signal.
3. **30 epochs on only-sparse cells** biased the neck+head toward sparse scenes.

Net: notehead detection collapses on dense pages. The original Phase-0 forgetting
check (4 dense cells, count-based) happened not to catch this.

**Conclusion: do not deploy `deepscoresv2-yolov8l-clef-ft-2026-07-13.pt` as the
production default.** The clef *approach* is validated; these specific weights
trade the all-treble disease for a dense-page notehead disease.

---

## Corrected retrain — negative result

`tools/omr/training/build_clef_fix_dataset.py` built a corrected set: human clef
labels + production self-distilled non-clef labels (tight boxes: notehead
norm-width 0.047 → **0.023**, complete) on the 62 clef cells, plus **68 dense
interior anti-forgetting cells** (production-labeled, no clef). Retrained from the
production checkpoint, proven recipe → `deepscoresv2-yolov8l-clef-ft-boxfix-2026-07-13.pt`.

**What it fixed:**
- **Alto** — 3/3 on the 44-cell set, 9/10 on clef-diverse (old-ft was 1/3). The
  alto→tenor confusion is gone (it flipped to a milder tenor→alto on some cells).
- **Non-clef breadth** — WTC rest recall 5/5 (old-ft 2/5); beams back (0 → 64).

**What it did NOT fix — the dense-page notehead collapse persists:**

| Mahler p.11 noteheads | production | old clef-ft | box-fix clef-ft |
|---|---|---|---|
| conf 0.25 (deploy default) | **2506** | 123 | **114** |
| conf 0.10 (aggressive) | — | — | 506 |

114 at conf 0.25; even dropping conf to 0.10 only reaches 506 (still 80% short of
2506) while flooding total detections to 4160. So it is **capability loss, not a
confidence-calibration knob** — no cheap runtime salvage. The collapse is robust
to box-tightening, label completion, anti-forgetting cells, agnostic/class-aware
NMS, iou 0.5→0.85, and conf 0.25→0.10.

**And the retrain regressed the clef objective it was supposed to protect:**
clef detection 100% → 93% (44-set) / 70% (diverse), type accuracy 87% → 73% / 67%
— the 68 anti-forgetting cells diluted the clef signal (clef cells went from 100%
to 48% of the data).

### Mechanism (best supported)

Fine-tuning the production detector's neck+head (freeze 10 → layers 10–22
trainable) for 30 epochs on ~130 low-object-count cells narrows the model's
detection **density prior**. Sparse cells (≤10 noteheads — WTC, the clef cells)
stay within the learned range and detect fine; dense orchestral cells (dozens–
hundreds of noteheads per canonical region) exceed it and collapse. The DSv2
pre-training saw high-density crops; a small low-density fine-tune erases that.
This is why *every* label/NMS/conf fix leaves it unchanged.

---

## Conclusion & recommendation

**Do not deploy any fine-tuned variant as the production OMR default.**
`clef-ft` and `clef-ft-boxfix` both trade the all-treble disease for a dense-page
notehead disease on exactly the hard target (conductor's scores). The Phase-0
"KEEP / deploy it" call rested on a 4-cell count-based forgetting check that could
not see this. **Task 4 (set `OMR_WEIGHTS_PATH`) is intentionally NOT done.**

The clef *reading* ability is genuinely good, though — both models read clefs well
on the sparse staff-start cells where clefs live. The gain just can't ride on the
shared detector. Recommended path (decouples clef from detection, no forgetting
tradeoff):

1. **Clef-only reader (pragmatic, reuses these weights):** at runtime, keep
   **production** for all symbol detection, but read each staff's clef by running
   a fine-tuned model on that staff's start cell only. Two inferences, but clef
   inference is one small cell per staff. Delivers the clef mix (Task 1) without
   touching notehead detection.
2. **Dedicated tiny clef classifier (cleaner long-term):** a small classifier on
   staff-start crops (5 clef classes), trained on the 62 + more cells, injected
   into `staff.clef`. Fully decoupled; aligns with the "ensemble clef" idea.

Alto is now solved in the fine-tuned weights, so a clef-only reader would inherit
that. Original Task 3's remaining item — more viola/alto cells via the labeling UI
— still applies for pushing tenor↔alto higher, but is secondary.

## Decoupled clef-reader — implemented & validated ✅

Built option 1 in `tools/omr/transcribe.py` (`--clef-weights` / `OMR_CLEF_WEIGHTS`,
`--clef-reader-conf`). When set, a second detector runs on each staff's **start
cell** and its clef overrides the main detector's (before pitch resolution);
production still does all symbol detection. Gated to `cell_idx == 0` → ~1 extra
inference per staff.

Mahler 5 p.11, `--weights <production> --clef-weights <clef-ft-boxfix>`:

| | production alone | clef-ft (coupled) | **decoupled** |
|---|---|---|---|
| noteheads | 2506 | 123 ✗ collapse | **2506** ✓ (detections 4878, identical) |
| clef read | treble ×26 ✗ | realistic, but noteheads dead | **treble 10 / bass 13 / alto 2 / tenor 1** ✓ |

Best of both: **production-quality notehead detection AND a corrected clef mix**
— which neither coupled fine-tune could do. The decoupled clef read matches the
standalone box-fix read on 25/26 staves, and the box-fix alto fix carries through
(2 alto, vs 0 for the coupled clef-ft). Cost: yolo 170s → 232s (+37%) for the 26
staff-start clef inferences.

### Header crop + time-sig reader (done)

The specialist now runs on the **left `header_frac` (default 0.42) of the start
cell** — the clef/key/time header — at a **lower imgsz (default 640)**, and reads
BOTH clef and time signature from that one inference (`_read_staff_header`).

Cropping isn't just about excluding notes: ultralytics letterboxes to `imgsz²`
regardless of input, so a crop only helps if paired with a lower imgsz — and the
crop is what lets imgsz drop without shrinking the glyphs. Because canonical cells
normalise staff span, the clef is always ~96 px, so the best imgsz is
scale-determined (generalises across scores). Sweep on a 0.42 crop
(`tune_header_reader.py`): imgsz 1280 -> 5/26 clef agreement, 768 -> 16/26,
**640 -> 23/26** (lower is better — it keeps the clef near training scale).

Result on Mahler p.11 vs the full-cell prototype:

| | noteheads | clefs | yolo runtime |
|---|---|---|---|
| production | 2506 | treble x26 | 169.6 s |
| decoupled, full cell @1280 | 2506 | t10/b13/a2/t1 | 231.7 s (**+37%**) |
| decoupled, header crop @640 | 2506 | t11/b12/a2/t1 | **173.0 s (+2%)** |

Same clefs (25/26 agreement with the full-cell run, alto intact), same noteheads,
overhead cut from +37% to **+2%** — ~18x cheaper per clef inference.

**Time-sig reader — wired, but model-limited.** `_read_staff_header` also runs the
standard digit parser on the header crop and overrides the meter. The plumbing is
unit-tested (`tools/omr/tests/test_header_reader.py`: stacked 2/4, common-time C,
crop geometry). BUT on Beethoven 5 p.1 (a printed 2/4) it read nothing — a direct
probe shows **neither production nor the clef specialist detects any time-sig
digit** (imgsz 640 or 1280, conf 0.15). That's the DSv2 time-sig domain gap, not a
pipeline bug. So the reader is dormant until a **time-sig-trained specialist** is
dropped into `--clef-weights` — exactly the "staff-header specialist" this pattern
is built to host (it shares the clef crop, so zero marginal cost). The clef read
on Beethoven p.1 does improve (12x treble -> 8 treble / 4 bass), though the Viola
alto is missed — the box-fix model's current ceiling.

### Artifacts (this run)
- `mahler_p11_{production,finetuned,boxfix}.omr.json` + `_ft_noagnostic` / `_ft_iou85`
  / `_boxfix_conf10` diagnostic runs; `mahler_p11_render.png`
- `compare_clefs.py`, `tools/omr/training/wtc_forgetting_eval.py`,
  `tools/omr/training/build_clef_fix_dataset.py`, `reeval_boxfix.sh`
- `wtc_forgetting_{center,iou}.txt` / `_boxfix_center.txt`; `clef_eval_boxfix_*.txt`
- weights (gitignored): `omr-weights/deepscoresv2-yolov8l-clef-ft-boxfix-2026-07-13.pt`
