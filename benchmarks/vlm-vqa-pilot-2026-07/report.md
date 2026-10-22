# VLM-as-verifier pilot: Claude on real degraded orchestral score scans

**Question:** Can Claude answer narrow visual questions about scanned orchestral music cells accurately enough (>=95%) to serve as a cheap verifier for the local YOLO OMR pipeline?

**Answer: No.** Across 6 question types, on real (not clean-rendered) scans, neither Claude Haiku 4.5 nor Claude Sonnet 5 clears the 95% bar on any question type. The best single result — augmentation-dot presence on Sonnet 5 — reaches 89.7%, still 5.3 points short. This stands in sharp contrast to the ONOTE benchmark's reported 97–99% for Gemini-class models on **clean synthetic renders**, and is consistent with the hypothesis that the published numbers don't transfer to real, degraded scans.

Run date: 2026-07-10. Actual API spend: **$1.03** (hard budget $2.00).

---

## Methodology

### Ground truth

Ground truth was derived programmatically from the existing hand-labeled YOLO training data (no new labeling was done):

- **Source:** `data/user-labeled/v1-2026-05-18-orchestral` (60 cells, Mahler 5 + Beethoven 5, general orchestral pages) and `data/user-labeled/v2-2026-06-08-beet5` (37 cells, Beethoven 5 pp. 45–75, a denser conductor's-score section) — **97 cells total**.
- **Class ID -> name mapping:** read from `data/user-labeled/catalog.yaml` (`names:` list, 214 entries — the 208-class DeepScoresV2 vocabulary + 6 custom classes at indices 208–213: `barlineSingle`, `barlineDouble`, `barlineFinal`, `repeatRight`, `repeatLeft`, `textDynamic`). This is the exact mapping `verdicts_to_yolo_labels.py` used to *write* the label files, so it is authoritative — the project's own docs warn that `tools/omr/training/deepscores_classes.py` can have different spellings than the trained/labeled vocabulary, so it was not used.
- **Cell images:** both version directories already contain an `images/` folder (symlinks into another local worktree's `benchmarks/*/cells/` directories). All 97 symlinks resolved to valid PNGs — no missing images, no fallback to the main-checkout `benchmarks/omr-labeling-*/cells/` search was needed.

Six question types were derived from each cell's label file (`class_id cx cy w h` lines, mapped through the catalog):

| # | Question | Derivation |
|---|---|---|
| Q1 | `notehead_count` | count of all `notehead*` classes |
| Q2 | `hollow_notehead_present` | any `noteheadHalf*`/`noteheadWhole*`/`noteheadDoubleWhole*` (unfilled) vs. `noteheadBlack*` (filled) |
| Q3 | `accidental_present` | any `accidental*` class |
| Q4 | `rest_count` | count of all `rest*` classes |
| Q5 | `dynamic_present` | any `dynamic*` class (letters, hairpins) |
| Q6 | `augmentation_dot_present` | `augmentationDot` class present |

**Distribution gate.** Any question type with fewer than 10 cells in the minority/nonzero class would have been skipped as degenerate. All six passed; **no question types were skipped**:

| Question | Distribution | Kept? |
|---|---|---|
| Q1 notehead count | 68/97 cells nonzero | Yes |
| Q2 hollow notehead present | True=32, False=65 | Yes |
| Q3 accidental present | True=22, False=75 | Yes |
| Q4 rest count | 45/97 cells nonzero | Yes |
| Q5 dynamic present | True=21, False=76 | Yes |
| Q6 augmentation dot present | True=12, False=85 | Yes (minority class exactly at the 10-cell floor) |

### Models and API design

- **Models:** `claude-haiku-4-5-20251001` and `claude-sonnet-5` (exact IDs verified against the current model catalog).
- **One call per (cell, model)** — one image + all 6 questions batched into a single prompt, using structured outputs (`output_config: {format: {type: "json_schema", ...}}`) to force a single well-formed JSON object back — no markdown-fence parsing, no manual JSON-extraction heuristics.
- Images sent at **native resolution** (base64 PNG), no downsampling — cells are already small crops (mean ~1552x758 px, smallest 331x146).
- Thinking disabled where applicable: `thinking: {"type": "disabled"}` explicitly on Sonnet 5 (which otherwise defaults to adaptive thinking when the parameter is omitted); no `thinking` parameter sent to Haiku 4.5 (it predates the parameter).
- 194 total API calls (97 cells x 2 models), run concurrently (8 workers) with a live budget tracker that would abort new calls once projected spend crossed $1.90.

### Cost

| | Estimated (upfront) | Actual |
|---|---:|---:|
| Haiku 4.5 | $0.2599 | $0.2127 |
| Sonnet 5 | $0.7797 | $0.8212 |
| **Total** | **$1.0396** | **$1.0338** |

**Actual spend: $1.03**, well within the $2.00 hard budget. Mean input tokens/call: Haiku 1,917, Sonnet 5 2,499 (Sonnet 5's newer tokenizer runs ~30% more tokens on the same content, as documented). Mean output tokens/call: Haiku 55, Sonnet 5 65. **Zero API errors, zero JSON-parse failures, zero refusals across all 194 calls** — structured outputs delivered a valid, schema-conformant object every time.

Note: costs computed at Sonnet 5's sticker price ($3/$15 per MTok). An introductory rate ($2/$10, through 2026-08-31) may apply to the account, in which case actual billed cost is lower than shown.

---

## Accuracy results

### Full accuracy table (exact match; +/-1 tolerance for count questions)

| Question | Kind | Haiku 4.5 exact | Haiku +/-1 | Sonnet 5 exact | Sonnet +/-1 | **95% gate** |
|---|---|---:|---:|---:|---:|:---:|
| Q1 notehead_count | count | 18.6% | 41.2% | 30.9% | 66.0% | **NO-GO** |
| Q2 hollow_notehead_present | bool | 50.5% | — | 77.3% | — | **NO-GO** |
| Q3 accidental_present | bool | 82.5% | — | 88.7% | — | **NO-GO** |
| Q4 rest_count | count | 51.5% | 78.4% | 49.5% | 85.6% | **NO-GO** |
| Q5 dynamic_present | bool | 79.4% | — | 88.7% | — | **NO-GO** |
| Q6 augmentation_dot_present | bool | 85.6% | — | 89.7% | — | **NO-GO** (closest: 5.3 pts short) |
| **Mean across 6 questions (exact)** | | **61.4%** | | **70.8%** | | |

n=97 for every cell in every row (0 parse/API errors on either model). **Verdict: NO-GO on all six question types, for both models.** No question type passes even under the +/-1 count tolerance.

### Per-version breakdown (exact match)

| Question | Haiku v1 (n=60) | Haiku v2 (n=37) | Sonnet v1 (n=60) | Sonnet v2 (n=37) |
|---|---:|---:|---:|---:|
| Q1 notehead_count | 20.0% | 16.2% | 28.3% | 35.1% |
| Q2 hollow_notehead_present | 53.3% | 45.9% | 71.7% | 86.5% |
| Q3 accidental_present | 78.3% | 89.2% | 86.7% | 91.9% |
| Q4 rest_count | 46.7% | 59.5% | 51.7% | 45.9% |
| Q5 dynamic_present | 78.3% | 81.1% | 88.3% | 89.2% |
| Q6 augmentation_dot_present | 83.3% | 89.2% | 88.3% | 91.9% |

Sonnet 5 does noticeably better on the v2 conductor-score cells for hollow-notehead detection (86.5% vs 71.7%) — likely because the v2 batch was cut with the SPARSE-cell strategy (few elements per cell), so despite coming from a denser source page, the individual cells contain fewer overlapping symbols to confuse.

### Confusion notes on the worst question type: Q1 (notehead count)

Notehead counting is the worst performer for both models by a wide margin:

- **Haiku 4.5:** MAE 2.97. Skews toward **over-counting** (50 over vs. 29 under). Worst cases are wild: on `beet5-p35-sys0-s6-m1` (truth=22, dense chordal passage) Haiku said **47** — more than double; on `beet5-p35-sys1-s13-m8` (truth=0, a rest-only measure) it hallucinated **12** noteheads.
- **Sonnet 5:** MAE 1.64, notably better but far from usable. Largest errors are **under-counts on dense multi-voice cells**: `beet5-p5-sys1-s5-m1` (truth=24) -> 13; `beet5-p25-sys0-s2-m1` (truth=11) -> 3; `beet5-p55-sys0-s2-m8` (truth=13) -> 6.
- Both models' worst failures cluster on cells with many noteheads packed into beamed/chordal groups — the same orchestral density the project's OMR docs flag as hardest for the in-house YOLO model. Asked to count symbols in a busy image, the VLM appears to produce a rough visual impression rather than an exact tally.
- **Q4 rest count** shows a milder form with a clear systematic **under-count bias** on both models (Haiku: 40 under vs. 7 over; Sonnet: 34 under vs. 15 over) — rests get missed far more often than hallucinated.
- **Q2 hollow-vs-filled** is near a coin flip for Haiku (50.5%; TP=18 / TN=31 / FP=34 / FN=14) — Haiku over-predicts "hollow present" (52 yes-predictions vs. 32 actually true), indicating genuine visual confusion between half/whole noteheads and filled quarter noteheads on degraded scans. Sonnet reaches 77.3% (FP drops to 3, but FN rises to 19 — it misses real hollow noteheads instead).

### Haiku vs. Sonnet 5 — is Haiku good enough?

**No — Sonnet is clearly better, and even Sonnet isn't sufficient.** Sonnet 5 beats Haiku on 5 of 6 question types, sometimes by a lot:

- Largest gaps: Q2 hollow-notehead presence (+26.8 pts), Q1 notehead exact count (+12.3 pts, and +24.8 pts at +/-1 tolerance).
- Q4 rest count is a statistical tie on exact match (51.5% vs 49.5% — nominally Haiku), but Sonnet's +/-1 accuracy (85.6% vs 78.4%) and MAE (0.68 vs 0.96) are both better, so this is exact-count noise, not a real Haiku advantage.
- Mean exact accuracy across the 6 questions: Haiku 61.4%, Sonnet 70.8% — ~9.4 pts, at ~4x the per-call cost ($0.0022 vs $0.0085 per cell).

If a VLM verifier were pursued despite these results, Sonnet 5 would be the only defensible choice — Haiku's near-chance hollow-notehead discrimination disqualifies it. But neither model is close to the >=95% target on any question type, so the verdict is NO-GO for unsupervised auto-accept/auto-reject use.

---

## Ground-truth bias caveat (quantified)

Ground-truth boxes may miss symbols the labeler skipped (the labeling workflow explicitly allows leaving ambiguous bleed "pending", which converts to no-label). That would bias "presence" questions by making some cells look emptier than they are. Three checks:

1. **Dropped "unsure" verdicts (direct check).** Version metadata records `n_unsure_dropped` = 1 for v1 and 1 for v2 — only 2 detections across all 97 cells were left unsure and dropped. Not a plausible driver of the measured gap.
2. **Bleed proxy correlation.** Correlating each cell's `n_fp_dropped` (count of model detections the labeler rejected — a density/bleed/noise proxy) against the cell's question-mismatch rate: Pearson r = 0.073 (Haiku), 0.139 (Sonnet) — weak. Splitting at the median FP-dropped count shows no meaningful difference (Haiku: 39.0% mismatch on low-bleed vs 38.3% on high-bleed; Sonnet: 30.0% vs 28.4%). **The accuracy gap is not concentrated on the noisiest/most ambiguous cells** — errors occur broadly, including on cleanly-labeled cells, pointing at genuine VLM visual-counting limits rather than a labeling artifact.
3. **Blank cells.** 4/97 cells have zero labeled classes relevant to the questions (`beet5-p15-sys0-s0-m0`, `beet5-p65-sys2-s5-m16`, `beet5-p65-sys2-s5-m6`, `beet5-p65-sys3-s6-m15`) — legitimate "nothing to count" ground truths (their only content is structural: staff lines, which are classical-CV territory and deliberately unboxed).

A small labeler-omission effect can't be fully excluded with a proxy, but the data does not support it as the main explanation for the distance from 95%.

Additional caveats:

- **n=97 is small**; the 95% gate needs <=4 errors per question — a handful of borderline cells can move a question several points. Q6's minority class (12 true cells) sits exactly at the 10-cell inclusion floor, so its accuracy is dominated by the majority "false" class (predicting always-false would score 87.6%; Sonnet's 89.7% is barely above that baseline).
- **Prompt sensitivity untested.** One prompt formulation, one pass, no few-shot examples, no crop-and-zoom tool use, thinking disabled. Any of those could move the numbers; this pilot measures the cheap single-shot configuration that would actually be economical as a per-cell verifier.
- **Label-vocabulary edges.** Ledger lines, slurs, ties, staff/stem/beam are excluded from the question set by construction; `textDynamic` (word dynamics like "cresc.") counts as a dynamic in ground truth but the prompt told the model not to count text-only expressions unless a letter/hairpin was present — 1 cell has textDynamic (alongside hairpins/letters, so no conflict in practice).

---

## Data-resolution notes

- **No missing images** — all 97 `images/` symlinks resolved (they point into worktree `cool-kare-05197c`'s benchmark cells dirs, which exist on this machine). The fallback search of the main checkout was not needed.
- **Class mapping** came from `data/user-labeled/catalog.yaml` (the mapping the label writer used), not `deepscores_classes.py`, per the project's spelling-divergence warning. Note the catalog vocabulary contains duplicate spellings from DSv2's two annotation sets (e.g. `ledgerLine` id 1 vs `legerLine` id 136; `dynamicF` id 93 vs `dynamicLetterF` id 192) — both spellings appear in the labels and both are handled by the prefix-based question derivation.
- **Zero API failures / parse failures / refusals** across 194 calls.

---

## Files in this directory

- `run_pilot.py` — reproducible pilot script (ground-truth extraction, distribution gate, cost estimation with hard-budget abort, API calls, results.json output, stdout accuracy summary). Reads `ANTHROPIC_API_KEY` from `backend/.env` in the main checkout; never prints it. Supports `--dry-run`, `--limit N`, `--models haiku,sonnet`, `--workers N`.
- `results.json` — per-cell, per-model raw parsed answers vs. ground truth, plus token usage and cost per call, distribution-gate stats, and totals.
- `report.md` — this file.
