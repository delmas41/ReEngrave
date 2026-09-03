# Phase C — the measurement that decides whether pre-filled boxes are labels

Everything measured so far says the pre-fill is good: precision exact 0.84
→ 0.88 (the variant and tie rules) → **0.961** (better weights alone), with
the `labels` tier at 1.000 over 44 of ~50 boxes. **None of it can settle the
question**, because all of it is the same six cells, and those six were
picked as the ones the pre-fill decided the MOST — the densest bars, where
alignment slips most. A biased sample stays biased however well it scores.

This is the replacement: a **pre-registered random sample**, labeled
**blind**, scored by the harness that is already committed.

## What is registered, and why that word

[`PHASE_C_CELLS.json`](PHASE_C_CELLS.json) was written **before any of these
cells was labeled**, by `select_phase_c_cells.py` at seed 20260903, and it
records for every chosen cell what the pre-fill *already claims* — its
status, its box count, how many of those boxes sit in the `labels` tier
(74 boxes over 25 cells, 73 of them labels-tier). That is the point: the
population and the prediction are both fixed in advance, so the analysis
cannot become a search for the subset that scores best.

- **Seeded** — re-running reproduces the draw exactly; it cannot be re-rolled
  until it flatters something.
- **Excludes the six** already-complete cells.
- **Ordered** — label in rank order. **Stopping early is valid**, because
  the prefix of a shuffle is itself a uniform random sample. That is why 25
  are registered when 12–15 is the ask: the extra ten are headroom you may
  take, not work you owe.

| stop after | pre-filled boxes | labels tier |
|---|--:|--:|
| 10 cells | 43 | 42 |
| **15 cells** | **50** | **49** |
| 20 cells | 61 | 60 |
| 25 cells | 74 | 73 |

⚠️ **A random sample of orchestral cells is mostly SPARSE bars** — 1 to 6
boxes each, against ~8 in the six dense ones — which is exactly the bias
being corrected, and it means these cells are individually quicker to label
than the six were. Four of the 25 are cells the pre-fill ABSTAINS on; they
contribute no boxes to precision, and they are in the list because dropping
them would quietly reintroduce the old bias. Label them anyway: like every
cell here, they become training labels regardless of what they measure.

## Labeling it: BLIND, and why the flag exists

```bash
python3 -m tools.omr.annotate.server \
    --bench-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1 \
    --blind --port 5051
```

⚠️ **A human who is shown the pre-fill's hints cannot measure the
pre-fill.** The score would report agreement with what the human was told.
The UI draws the ghost hints **by default**, and `Tab` to the next cell is a
full page load, so the `h` toggle resets on **every cell** — "just press
`h`" is not a protocol, it is fifteen chances to forget. `--blind` withholds
the pre-fill from the payload entirely: no hints, no `prefill_status`, and
no queue order (that one leaks the same information one step removed, since
"most left for me first" is the pre-fill saying which cells it found hard).
Verdicts are untouched — blind is about what the human SEES.

**Use the completion palette, not the hollow one**, and restart the server
after swapping it (`inspected_passes` is stamped from the live config —
that is why the six cells carry `hollow noteheads`):

```bash
cd benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1
cp batch_config.completion.json batch_config.json   # 14 classes, incl. slur/tie/hairpins
```

Label **every symbol in the image**, not one pass's worth — that is what
makes a widened score legitimate.

⚠️ **The palette swap is not housekeeping; it is the difference between
helping the next training run and harming it.** The batch's ACTIVE config
was a stale 9-slot completion palette with **no `accidentalNatural`, slur,
tie or hairpin** — and the six already-complete cells contain 5 naturals, 8
slurs, 6 ties and 5 hairpins. Labeling under the stale palette would leave
every one of them unboxed, i.e. **background**, which is exactly the
mechanism the training session diagnosed for the completeness regression
(`benchmarks/omr-labeling-survey-2026-09/NEXT_ITERATION.md`: "the completion
pass only labeled black noteheads + augmentation dots, so rests and
accidentals were unlabeled background — and 30 epochs learned to suppress
them"). The 14-slot `batch_config.completion.json` is the one to use.

⚠️ **Even the 14-slot palette is not the whole class space, and the gap is
not hypothetical.** The six complete cells also contain `keyFlat` ×3,
`clefG`, `timeSig8`/`timeSig9`, `ornamentTrill`, an
`accidentalNaturalSmall` and two grace-sized black heads — none of which has
a slot. Sean labeled them through the **full picker** (the button in the
pass bar), which is what "complete" requires. Do the same here: anything
printed that has no number key still gets boxed. Skip only what the campaign
always skips — staff lines, stems, beams and free text.

**These cells are dual-purpose.** They are the Phase C measurement AND they
are step 1 of `NEXT_ITERATION.md` for this batch — the rests-and-accidentals
completion the next cloud run needs. That is why a complete pass here is
worth more than its measurement alone, and why using the right palette
matters beyond this benchmark.

## Scoring it

The cells are stamped `completion` by the palette above, so no `--cells`
list is needed:

```bash
B=benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1
python3 -m tools.omr.training.mxl_verdicts --bench-dir $B \
    --transcription $B/transcription.json --truth $B/reference.mxl \
    --windows $B/windows.json --score --score-classes all \
    --score-inspected-for completion --dry-run
IDS=$(python3 -c "import json;print(' '.join(c['cell_id'] for c in json.load(open('benchmarks/omr-prefill-admission-2026-09/PHASE_C_CELLS.json'))['cells']))")
python3 benchmarks/omr-prefill-admission-2026-09/probe_admission.py \
    --inspected-for completion --cells ${=IDS}      # zsh: ${=IDS} word-splits
```

⚠️ **`--inspected-for completion` is not optional, and this is the one way
this measurement can silently produce a damning wrong number.** Every
registered cell ALREADY has a verdict file, from the earlier hollow-notehead
sweep — so a cell you have not reached yet is not empty, it holds hollow
boxes and nothing else. Scoring every class against that charges each
correctly pre-filled black notehead as a false positive, and the precision
that comes out measures which pass was run. The flag skips any cell not
stamped for this pass and says which; `mxl_verdicts` refuses the same
mistake outright, which is why `--score-inspected-for` appears in the
command above too. Both are safe to run at any point mid-labeling: they
score exactly the cells you have finished.

⚠️ **Score against the SAME reading the sample was registered against.**
The registration used the `hollow-ft-2026-09-03` transcription, because
Phase B showed the pre-fill's output — and therefore which boxes exist to be
scored — moves with the weights. The batch's committed `transcription.json`
is still the older pre-hollow reading; refresh it (and `prefill/`, via
`--write-hints`, which never touches `verdicts/` or `detections/`) before
scoring, or point `--transcription` at the hollow-ft reading directly.

## What the answer means

The number to read is the **`labels` tier's precision**, and the honest bar
was set before seeing it: the tier claims 1.000 in-sample.

- **Holds up (≳0.97 over ~50–70 boxes)** — pre-filled labels-tier boxes can
  be admitted without a human glance. That is the whole point of the
  approach: the reference does the confirming, and hand labeling is spent
  only on the queue tier and on what the pre-fill never proposes.
- **Drops materially** — the tier's rules were fitted to six cells and do
  not generalise; the pre-fill stays a queue, and the failures it makes on
  random cells are the next thing to diagnose. That is a real result too,
  and it is why the sample was registered in advance.

Either way, the labeled cells are training data, so the session pays for
itself even if the measurement disappoints.
