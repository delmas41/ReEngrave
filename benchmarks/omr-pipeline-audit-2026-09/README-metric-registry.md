# `metric-registry.json` — what it is, and what wiring it in would take

**Written by Agent III of the 2026-09-07 pipeline audit. A PROPOSAL. Nothing in
`tools/` was modified.** The reasoning, the critique it came out of, and every
figure's provenance are in [`MEASUREMENT_SYSTEM.md`](MEASUREMENT_SYSTEM.md).

## What it is

One file holding every measurement this project makes today, converted to one
unit — **% of achievable, 0-100, higher is better** — with, per row: the raw
metric and its native direction, the reversible transform, the **ceiling** and
its **kind**, **status** and **evidence pointer**, `n`, `era_key`, `noise_floor`,
`summability_class`, `pool_key`, and `scoreable: true|false` with a `why_not`
sentence when false.

Regenerate:

```bash
python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_ceiling_engine_independence.py
python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_pct_of_achievable.py
python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_measurement_hygiene.py
python3 benchmarks/omr-pipeline-audit-2026-09/probe/build_metric_registry.py
```

All four are read-only over committed artefacts. They run no pipeline, score no
XML, need no venv and take under two seconds.

Today: **48 rows — 35 scoreable, 13 not.** Ceiling status: 25 measured,
1 measured-single-source, 1 measured-and-corroborated, 1 measured-unreliable,
17 assumed, 3 unmeasured.

## Wiring it into `docs/progress-dashboard.html`

`tools/dashboard/generate.py` is already most of the way here and was
deliberately not touched.

**1 · `pipeline_metrics()` reads the registry instead of six artefacts.** It
currently re-derives every figure inline from `RECORD`, `READING`, `SCAN_GATE`,
`ENGRAVED_1TO1`, `NORMALISED` and `HAIRPIN_CV`. The registry is that same data
with a ceiling, an era and a trust level attached. `_resolve_cell` needs no
change at all — a registry row *is* a cell (`display`, `detail`, `source`).
Content-JSON cells keep referring to metrics by key; the keys are the registry
`id`s (`reading:clef`, `scan:pitch`, `engraved:omr_ned`), already the same names.

**2 · `_status()` collapses from two axes to one.** Today it branches on `rate`
(higher better, `RATE_GREEN=0.90`) or `ned` (lower better, `NED_GREEN=0.15`) —
two hand-set thresholds doing the work a ceiling should do. Under the registry
there is one number and one threshold pair. Keep the native value in the tooltip
so nothing is lost; the transform is reversible and the registry stores both.

**3 · Trust must be visible, not just recorded.** Render
`ceiling.status == "assumed"` differently from `"measured"` — a hatched bar
against a solid one is enough. A row scored against a guessed ceiling and one
scored against an externally corroborated ceiling must not look identical.

**4 · Unscoreable cells keep the grey they already have, and gain a reason.**
They render grey today from hand-written `detail` strings in the content JSON;
the registry supplies `why_not` from one place. Ten of the thirteen are
`visibility` — the harness cannot see the stage — which is a ceiling of zero
information, not a low score.

**5 · A delta column, gated on four conditions.** This is where the value is for
Sean's *"a quick read on whether we are improving"*, and where a naive
implementation would do the most damage. Show a change only when **all four**
hold; otherwise print "—" with the reason on hover:

- equal `era_key`;
- equal `ceiling.value` **and** `ceiling.evidence` (a recomputed ceiling silently
  changes what 100 % means — a second era boundary);
- magnitude above the row's own `noise_floor`, applied **per row** (±6 edits is
  0.007 points pooled on the 20-row scan gate and ~0.5 points on one row);
- `companions.edits` moving in the same direction as the ratio — otherwise the
  delta is **DILUTED**, not an improvement. Live example in
  `MEASUREMENT_SYSTEM.md` §A6.

**6 · Two build-time refusals, in the shape `accuracy_record.check()` has.** A
registry whose `ceiling.evidence` names a missing file fails the build; a delta
across `era_key` raises rather than rendering.

## Three things not to do

⚠️ **Do not put a single top-line number on the board.** Engraved and scan have
different ceilings, different noise floors and different eras. The registry makes
them un-poolable by construction (`pool_key`), which is `generate.py`'s own
standing warning — *"one colour per stage would be a lie"* — promoted from a
comment to a schema property. Two numbers, always.

⚠️ **Do not pool by averaging percentages.** `rules.pooling`: a pool is
recomputed from the underlying counts. Dvořák 9's excerpt auto-shrank to three
bars; averaging would give it the same weight as a 27-staff Brahms page.

⚠️ **Do not default a missing ceiling to anything but the conservative value.**
`rules.assumption_direction`: `F = 0` for an error metric, `C = 1` for a rate.
Both understate. A missing ceiling must never be able to manufacture a 100.

## Prerequisites this does not supply

- **`scan_eval.py` writes no commit and no machine-checked era** (§A1). Forty-two
  of forty-eight result artefacts cannot be dated from their own contents. Until
  that is fixed, `era_key` for scan rows is assembled by hand in
  `build_metric_registry.py` and is only as good as the assembly.
- **The scan structural floor is an estimate, not a number** (§B4). The exact
  value would come from scoring the page-normalised truth *as the prediction*
  against the raw truth — one cheap musicdiff run over 15 small files. That is
  the single highest-value measurement on this list.
- **The `input` ceiling is empty** (§B6). Every scan detector row is scored
  against an assumed ceiling of 1.0 — the claim that a perfect reader could
  recover every symbol from a bitonal 600 dpi scan of 1870 type.
- **Human review cost is not measured at all** (§A9), and it is the thing the
  project exists to reduce.
