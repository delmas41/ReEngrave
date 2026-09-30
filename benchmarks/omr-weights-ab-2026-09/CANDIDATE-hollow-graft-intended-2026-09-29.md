# Candidate: `omr-weights/candidates/hollow-graft-intended-2026-09-29.pt`

**Not committed** (`omr-weights/` is gitignored) — this file records how to
rebuild it and how it was verified. ROADMAP 2.34's "Sean said Run A".

## What it is

The graft **intended** on 2026-09-04
(`docs/handoff-2026-09-04-round5-class-collapse.md:65-71`), built with the
**fixed** `merge_class_head.py` (2026-09-29, `benchmarks/omr-weights-ab-2026-09/FINDINGS.md`
§1). Production's shipped graft (`hollow-graft-shift09-2026-09-04.pt`) used
the pre-fix, backwards tool and carries `distill25/epoch0`'s entire
backbone/neck/box-regression head, not `hollow-ft-2026-09-03`'s
(FINDINGS.md §2). This candidate is what should have shipped: `base`
unconditionally, only the 7 kept classes' `cv3` rows from the fine-tune.

## Build command

```bash
python3 benchmarks/omr-labeling-survey-2026-09/merge_class_head.py \
  --ft omr-weights/round5-sweep/distill25/epoch0.pt \
  --base omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt \
  --keep noteheadHalfOnLine noteheadHalfInSpace noteheadWholeOnLine \
         noteheadWholeInSpace noteheadHalfOnLineSmall \
         noteheadHalfInSpaceSmall noteheadWhole \
  --labels-root data/user-labeled --bias-shift 0.9 \
  --out omr-weights/candidates/hollow-graft-intended-2026-09-29.pt
```

Base and donor both found on disk, unmodified since 2026-09-04:
- base: `omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`
- donor: `omr-weights/round5-sweep/distill25/epoch0.pt`

Tool output: "grafted 42 per-class parameter rows across 3 head scales
onto --base" (7 kept classes x 2 tensors [weight, bias] x 3 head scales)
and "shifted the bias of 7 kept classes by -0.9 across 3 scales".

## Verification (tensor diff, read-only, no retraining)

Script: `verify_graft.py`, run once against the candidate, base, and donor
state dicts (not committed — a one-off check, reproducible from the diff
logic already narrated in `merge_class_head.py`'s own docstring and
FINDINGS.md §2's methodology).

- **595 tensors total.** 589 bit-identical to base. The other 6 are
  exactly `model.22.cv3.{0,1,2}.2.weight` and `.bias` — the three head
  scales' per-class classification conv, weight and bias each. Zero
  tensors differ from base outside those 6 (no backbone/neck/box-
  regression/DFL drift, unlike the shipped production graft).
- **Kept classes' rows** (7 class indices, both weight and bias, all 3
  scales) equal the donor's own rows exactly for weight, and the donor's
  bias minus 0.9 for bias (`torch.allclose`, atol 1e-6) — confirms the
  bias-shift landed on the grafted rows only.
- **Non-kept classes' rows** inside those same 6 tensors (all 201 other
  classes, all 3 scales) equal base exactly, bit-for-bit — confirms
  nothing about the graft leaked past the 7 named classes.

Net: base + 7 grafted, bias-shifted rows; everything else bit-exact to
`hollow-ft-2026-09-03.pt`. This is the object `merge_class_head.py`'s
fixed direction promises and the shipped production graft is not.

## The A/B (Sean's harness, ROADMAP 2.34)

Driver: `run_intended_graft_2026_09_29.sh` (this directory). Runs
`run_ab.sh` (`--through adjudicate`, GATHER+ADJUDICATE only) three times
plus `hollow_eval.py` twice, all via one `nohup`:

1. **Control** production vs. a copy of itself, Brahms 317803 pdf page 1
   — must show zero differences (sanity: the harness itself introduces no
   noise).
2. **Brahms 1/i**, Breitkopf 317803, pdf pages 1-4: production vs. the
   intended graft.
3. **Litolff 984073**, pdf pages 1-4: production vs. the intended graft.
4. **Hollow axis** (`hollow_eval.py --score`), Beethoven 5 p.1 (Litolff
   984073, `--page 1`): half-notes found of 68 printed, for both weights.

Expected wall time: each GATHER+ADJUDICATE arm is ~93 s/page with
`--no-surya --no-ocr` (per CLAUDE.md §5b) — 1 page (control, x2 arms) +
4 pages (Brahms, x2 arms) + 4 pages (Litolff, x2 arms) ≈ 18 page-arms ≈
28 minutes, plus two single-page legacy `transcribe` runs for the hollow
axis (also ~93 s/page each at 600 DPI) ≈ 3 more minutes. Call it
**30-40 minutes** total, unattended.

## Where the results land

- `benchmarks/omr-weights-ab-2026-09/out/production-control-vs-production-control_copy/TABLE.md`
  (and `summary.json` beside it) — the control, must read zero differences.
- `benchmarks/omr-weights-ab-2026-09/out/production-brahms-vs-candidate-brahms/TABLE.md`
  (+ `summary.json`) — Brahms 317803, pages 1-4: GATHER rest-box counts,
  ADJUDICATE verdicts on every rest glyph (duration/glyph_owner/
  rest_is_not_a_rest), and the cross-reference against Sean's rest-queue
  verdicts (`benchmarks/omr-queue-rests-2026-09/verdicts/`) wherever a
  gathered cell overlaps one.
- `benchmarks/omr-weights-ab-2026-09/out/production-litolff-vs-candidate-litolff/TABLE.md`
  (+ `summary.json`) — Litolff 984073, pages 1-4, same readout. NOTE: the
  rest-queue verdicts' Litolff cells are keyed to a *different* Litolff
  scan (`imslp575951`, "hires"), not `imslp984073`, so the cross-reference
  section here is expected to show zero overlapping cells — that is a
  property of which pages Sean adjudicated, not a harness fault.
- `benchmarks/omr-labeling-survey-2026-09/hollow_eval_production-intended-2026-09-29.json`
  and `hollow_eval_candidate-intended-2026-09-29.json` — the hollow
  histogram and (via `--score`) the `eval_first_run` pooled/clef/measures
  figures for Beethoven 5 p.1, both weights.
- Driver's own combined log: `benchmarks/omr-weights-ab-2026-09/out/driver-2026-09-29.log`.

Launched via `nohup`; not waited on. Read the TABLE.md files above once
the driver log's last line is
`=== <date> driver finished ===`.
