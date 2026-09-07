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
P=benchmarks/omr-pipeline-audit-2026-09/probe
python3 $P/probe_ceiling_engine_independence.py
python3 $P/probe_measurement_hygiene.py
python3 $P/probe_input_ceiling_from_labels.py
python3 $P/probe_retro_stamp.py
python3 $P/probe_human_cost.py
# these two need musicdiff; the rest do not
OMRNED_PYTHON=/path/to/.venv-omrned/bin/python python3 $P/probe_structural_floor.py
python3 $P/probe_pct_of_achievable.py
python3 $P/build_metric_registry.py
```

Six of the eight are read-only over committed artefacts and need no venv. Only
`probe_structural_floor.py` scores XML — 15 small pairs through the musicdiff
bridge, seconds, no pipeline. It reads truth fixtures from the `reconciliation`
worktree (`fixtures/` is gitignored) and **refuses to run** unless every
fixture's sha256 matches the canonical arm's.

**v0.2.0 (round 2): 55 rows — 38 scoreable, 17 not.** Ceiling status: 25
measured, 1 measured-directly, 1 measured-and-corroborated, 1
measured-single-source, 1 bounded-above, 1 refuted-as-a-ceiling, 1
pre-registered, 1 measured-unreliable, 1 not-a-defect-rate, 18 assumed, 4
unmeasured. v0.1.0 is preserved in git at `ac88148e`; `metric-registry.v0.2.0.json`
is a snapshot of the current file.

⚠️ **Two schema changes since v0.1.0 that a consumer must handle.**
`comparable_as` replaces the single `era_key` equality test — see §R4, and note
the round-1 rule forbade the competitive comparison the registry itself prints.
And every **scan** row's unit is now explicitly *"% of achievable **under page
fidelity**"* (`ceiling.constraint`): the metric's unconstrained floor is zero,
reachable by emitting the encoding instead of the page, which the project calls
an anti-feature.

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
- ✅ **The scan structural floor is now MEASURED** (§R2): 0.2123 pooled over 15
  rows, three controls passing, no output of ours in the measurement.
- **The `input` ceiling has a bound and a refutation, not a value** (§R3).
  Noteheads are bounded above at 0.971 on one batch; hairpins are refuted as a
  ceiling (a human drew 17 on 55 scanned cells). No class has a ceiling VALUE.
- **Human review cost does not reproduce from committed artefacts** (§R7). The
  project's only figure (197) is computed over a record set that is not
  committed; only its `contradicted` component re-derives (26 of 1,571).
- **Five scan rows still have no floor** — the four Mahler and one Bach rows have
  no hand-read staves map.
- **`orchestral_eval` still has no repeat-run noise floor**, so no engraved row
  can carry one and no engraved delta can be gated.
