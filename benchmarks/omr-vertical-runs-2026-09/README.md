# `Q.VERTICAL_RUN` — the vertical-run population, accepted AND refused

⚠️ **THE FINDINGS FILE WAS REFUSED TO THIS LANE** — the fifth time on
2026-09-18 — so the synthesis lives in the **commit messages of branch
`claude/vertical-runs-gather-2026-09`** and in the agent's final report, and
the artefacts are under `out/`. Read `git log` on that branch, oldest first.

## What is here

| file | what it is |
|---|---|
| `vertical_run_arm.py` | the arm: faithfulness control, reach, Sean's barline test in two forms, the length distribution, the cost |
| `probe_can_a_cell_hold_two_staves.py` | the STRUCTURAL half of the negative — read off the shared records' own `Q.STAFF_LINES`, no re-cut and no detector |
| `probe_crop_edge_reach.py` | the positive inside the negative, with its circularity named |
| `mutate.py` | 19 arms, three targets, two judges |
| `out/litolff.txt` `out/litolff.json` | Litolff Beethoven 5 pp.1-4 |
| `out/breitkopf.txt` `out/breitkopf.json` | Breitkopf Brahms 1 pp.0-3 |
| `out/two-staves.txt` | the structural proof |
| `out/crop-edge-reach.txt` | the discriminator that does separate |
| `out/mutate.txt` | 19 RED, 0 survivors, restore md5-verified |

## How to run it

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 benchmarks/omr-vertical-runs-2026-09/vertical_run_arm.py \
  --pdf library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --pages 1,2,3,4 \
  --record library/_shared-records/beethoven5-p1-p4.record.json \
  --crop-rows benchmarks/omr-stem-crop-pass-2026-09/out/litolff-rows.json \
  --crop-manifest benchmarks/omr-stem-crop-pass-2026-09/out/crop-manifest-litolff.json \
  --crop-adjudication benchmarks/omr-stem-crop-pass-2026-09/ADJUDICATION-litolff.json \
  --label "Litolff Beethoven 5 pp.1-4" --json out/litolff.json
```

⚠️ **NO WEIGHTS ARE NEEDED.** The arm re-cuts with `prepare_pages` and runs the
shipped `gather_cv_lines` rung; the detector never runs. It needs `library/`
(the PDF and the shared record) and ~30 s per four pages plus the record
stream. `--break-faithfulness` is the positive control on the control.

## The one-paragraph result

**REACH**: 6,128 candidates on Litolff pp.1-4 against 1,920 `Q.STEM` strokes,
and 6,816 against 2,305 on Breitkopf — so the record was carrying about a third
of the population the pipeline looked at, and **64.7% / 54.6% of it is refused
by a DIMENSION bound.** **FAITHFULNESS**: the flag-off re-cut reproduces both
records exactly, **1,920 = 1,920** and **2,305 = 2,305**, 0 cells disagreeing,
and flag-ON moves not one stroke. **SEAN'S BARLINE TEST is now computable and
is a CLEAN NEGATIVE** — 19 of 19 print-adjudicated barlines fire at no
tolerance in either form of the rule, while 6 of 58 adjudicated stems do —
because a barline taller than the cell has its ends **clipped by the cell**,
which the `too TALL` bucket's median end offsets of **−4.00 and +4.00 staff
spaces** name on both publishers and `probe_can_a_cell_hold_two_staves.py`
proves structurally. **The test is unavailable on the staged path, not
refuted.** **COST**: 0.96–1.11 MB/page, 1.6–2× the ink layer.
