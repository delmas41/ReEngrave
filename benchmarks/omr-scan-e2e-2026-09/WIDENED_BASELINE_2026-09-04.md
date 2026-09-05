# First widened baselines — the 11-row scan-e2e pool, two checkpoints

2026-09-04, on `84a5ccac` (the promotion commit: six verified rows join the
gate, 5 → 11), in a fresh worktree (`claude/scan-rebaseline`) with the three
mandatory venv fixes (`OMRNED_PYTHON` + the `.venv-omrned` / `.venv-surya`
symlinks — the trimmer resolves `ROOT/.venv-omrned` directly, and without the
Surya link the OCR rungs silently self-disable, changing the numbers).

⚠️ **THE POOL CHANGED MEANING AT `84a5ccac` AND NO FIGURE CROSSES THAT
BOUNDARY.** Every scan-e2e pooled number measured before the widening —
production 0.7517 / 7894 and the shipped graft 0.7493 / 7872 — is a **5-row
figure**. The numbers below are the FIRST figures for the 11-row pool; they are
the reference every future widened comparison differences against, and
comparing them to any 5-row figure is invalid in either direction (same
boundary discipline as the engraved benchmark's 3 → 11 widening). The 0.75-era
figures are history: they are restated here, in prose, precisely so nobody
reaches for them as the baseline for the tables below.

## The four pooled numbers

| checkpoint | pool | OMR-NED | edits | truth | pred |
|---|---|---|--:|--:|--:|
| prior-prod (hollow-ft-2026-09-03) | **11-row** | **0.8575** (0.8575298072504777) | 35458 | 23377 | 17972 |
| prior-prod (hollow-ft-2026-09-03) | 10-row (excl. bach) | **0.8457** (0.8456975019629511) | 29081 | 19828 | 14559 |
| production (hollow-graft-shift09-2026-09-04) | **11-row** | **0.8535** (0.8535376403021709) | 35817 | 23377 | 18586 |
| production (hollow-graft-shift09-2026-09-04) | 10-row (excl. bach) | **0.8387** (0.8387022350396539) | 29082 | 19828 | 14847 |

The 10-row pools are computed from the per-row sums (pooled OMR-NED =
Σedits / Σ(truth+pred)); the 11-row pools are the harness's own, re-verified
against the same sums. `scan_eval.py` has no per-row pool-exclusion mechanism,
so the Bach stress row enters the default pool — **whether it keeps pool
membership is an open decision for Sean** (the Boulanger precedent: a
structure-failure row dominates a pool and turns it into a segmentation
metric). Both readings are stated for both checkpoints so that decision has
its numbers either way.

## Does the ship decision hold on the deeper gate? Yes — on both pool readings, with one caveat opened up

`hollow-graft-shift09-2026-09-04` was shipped as the scan-side default on
2026-09-04 (`0e9f005b`) off the 5-row gate (0.7517 → 0.7493, −22 edits). On
the widened pool:

| pool | graft − hollow-ft, OMR-NED | graft − hollow-ft, edits |
|---|--:|--:|
| 11-row | **−0.0040** (0.8575 → 0.8535) | **+359** (35458 → 35817) |
| 10-row (excl. bach) | **−0.0070** (0.8457 → 0.8387) | **+1** (29081 → 29082) |

The headline metric favors the graft on both readings. The caveat is the edit
column: this metric's symmetry rewards emission, and a ratio that falls while
edits rise is the documented dilution signature — so the edit rise was opened
up rather than believed or dismissed:

- **The 11-row edit rise is Bach, entirely.** +358 of the +359 is the stress
  row, where the graft emits 326 more symbols into a page both checkpoints
  shatter identically (6 "systems", 122 measure-cells against 10 true bars).
  On a page whose score is dominated by structure charges, more emission costs
  edits mechanically.
- **On the 10 non-bach rows the graft is edit-neutral (+1) and wins 7 rows of
  10** (Dvořák p6 −100, Brahms p2 −125, Mahler p2 −61, Mahler p3 −34,
  Beethoven-575951 p1 −13, Dvořák p5 −7, Brahms p1 −2), losing the three
  densest Litolff-plate Beethoven readings (984073-p1 +61 — the loss already
  known from the 5-row gate — 984073-p2 +158, 575951-p2 +124).
- **Exact-pitch note recall — the number the metric's symmetry cannot flatter —
  favors the graft on both axes**, over the 7 rows carrying a staff→parts map
  in `works.json` (identical coverage in both arms; the other 4 rows abstain
  by design, no errors): hollow-ft matched 1522/2323, recall 0.655, precision
  0.755 (2015 predicted); graft matched **1610**/2323, recall **0.693**,
  precision **0.775** (2078 predicted). More right pitches at higher
  precision is recognition, not dilution.
- **The element counts show where the graft's extra emission goes** (see
  below): on the 10 non-bach rows, notes *fall* (4823 → 4794 — the confidence
  floor believing fewer noteheads, §3b's mechanism) while ties rise 293 → 420
  against a truth of 805, beams 1369 → 1454, rests +39. The tie recovery that
  motivated the graft holds on the widened set.

So: **the ship decision holds.** The graft is the better checkpoint on the
widened gate by pooled OMR-NED on both readings, by exact-pitch recall and
precision where they are measurable, and by element recovery in the categories
the hollow-ft under-emits — at the price of three dense Beethoven rows where
the floor costs edits, and more emission into the Bach wreckage.

## Per-row: prior-prod (hollow-ft-2026-09-03), tag `widened-hollowft`

| row | OMR-NED | edits | truth | pred | measures det/exp | staves |
|---|--:|--:|--:|--:|---|---|
| beethoven-sym5-mvt1-984073-p1 | 0.6925 | 1225 | 1064 | 705 | 16/16 | 12/12 |
| beethoven-sym5-mvt1-984073-p2 | 0.8862 | 4291 | 3004 | 1838 | 31/32 | 22/22 |
| beethoven-sym5-mvt1-575951-p1 | 0.7660 | 1375 | 1064 | 731 | 16/16 | 12/12 |
| beethoven-sym5-mvt1-575951-p2 | 0.8759 | 4347 | 3004 | 1959 | 32/32 † | 22/22 |
| dvorak-sym9-mvt1-405834-p5 | 0.4381 | 680 | 792 | 760 | 8/8 | 15/15 |
| dvorak-sym9-mvt1-405834-p6 | 0.7741 | 2711 | 2022 | 1480 | 7/7 | 15/15 |
| brahms-sym1-mvt1-317803-p1 | 0.9209 | 3436 | 2083 | 1648 | 8/7 | 14/14 |
| brahms-sym1-mvt1-317803-p2 | 0.9479 | 6735 | 3399 | 3706 | 15/15 | 27/27 |
| mahler-sym5-mvt1-local-p2 | 0.7122 | 1178 | 1148 | 506 | 9/9 | 17/17 |
| mahler-sym5-mvt1-local-p3 | 0.8932 | 3103 | 2248 | 1226 | 8/8 | 13/13 |
| bach-brandenburg3-mvt1-468678-p1 | 0.9160 | 6377 | 3549 | 3413 | 122/10 ‡ | 24/24 |

## Per-row: production (hollow-graft-shift09-2026-09-04), tag `widened-graft`

| row | OMR-NED | edits | truth | pred | measures det/exp | staves |
|---|--:|--:|--:|--:|---|---|
| beethoven-sym5-mvt1-984073-p1 | 0.7152 | 1286 | 1064 | 734 | 16/16 | 12/12 |
| beethoven-sym5-mvt1-984073-p2 | 0.8833 | 4449 | 3004 | 2033 | 31/32 | 22/22 |
| beethoven-sym5-mvt1-575951-p1 | 0.7626 | 1362 | 1064 | 722 | 16/16 | 12/12 |
| beethoven-sym5-mvt1-575951-p2 | 0.8770 | 4471 | 3004 | 2094 | 32/32 † | 22/22 |
| dvorak-sym9-mvt1-405834-p5 | 0.4306 | 673 | 792 | 771 | 8/8 | 15/15 |
| dvorak-sym9-mvt1-405834-p6 | 0.7279 | 2611 | 2022 | 1565 | 7/7 | 15/15 |
| brahms-sym1-mvt1-317803-p1 | 0.9192 | 3434 | 2083 | 1653 | 8/7 | 14/14 |
| brahms-sym1-mvt1-317803-p2 | 0.9459 | 6610 | 3399 | 3589 | 15/15 | 27/27 |
| mahler-sym5-mvt1-local-p2 | 0.6882 | 1117 | 1148 | 475 | 9/9 | 17/17 |
| mahler-sym5-mvt1-local-p3 | 0.8873 | 3069 | 2248 | 1211 | 8/8 | 13/13 |
| bach-brandenburg3-mvt1-468678-p1 | 0.9241 | 6735 | 3549 | 3739 | 122/10 ‡ | 24/24 |

The "measures det/exp" column is the **page total** (sum over detected systems
of the per-staff modal count) against the window's measure count — NOT
`scan_eval.py`'s own `meas` column, which prints the max per staff and reads
16/32 on a two-system page whose structure is right. Page totals and system
counts are **identical between the two checkpoints on every row** —
segmentation does not depend on the weights (the Phase B finding, reproduced
on all 11 pages), so every per-row delta above is recognition, not structure.

† 575951-p2 reads 17+15 = 32 — which IS the true split: the plate's own
printed numbers (17 over system 1, 34 over system 2, 49 opening p.3;
VERIFICATION.md) make system 1 = mm 17–33 (17 bars) and system 2 = mm 34–48
(15 bars). An earlier revision of this footnote claimed a "true 16+16" and
called the read a coincidence — corrected 2026-09-04 (spotted by the error-
forensics pass): the high-res read is exactly right. The 984073-p2 read of
31/32 is the expected one: the m19|m20 barline missed on that low-res
raster, i.e. its system 1 reads 16 where the print says 17; recorded in the
row's `verified_by`.

‡ **Bach is the documented stress row and scored exactly as VERIFICATION.md
predicted**: the pipeline shatters the page into six "systems"
(12+3+3+3+1+2 staves), 122 measure-cells against 10 true bars, and both
checkpoints score ~0.92 on it honestly. That is its purpose — it measures page
segmentation on this layout, not note recognition, which is the argument for
deciding its pool membership deliberately.

## Element counts vs truth

Counting replicates ROUND5_METHOD §3 (`<tie>` start+stop, `<rest>` any), and
the counter was validated by reproducing DETERMINISM_2026-09-04.md's recorded
5-page table exactly before being trusted on 11.

**11-row pool:**

| element | truth | prior-prod (hollow-ft) | production (graft) |
|---|--:|--:|--:|
| tie | 805 | 302 | **456** |
| rest | 2716 | 1752 | 1762 |
| note | 6915 | 6047 | 6101 |
| slur | 404 | 282 | 292 |
| beam | 3452 | 1973 | 2125 |
| time | 252 | 68 | 74 |

**10-row pool (excl. bach — whose truth carries 0 ties):**

| element | truth | prior-prod (hollow-ft) | production (graft) |
|---|--:|--:|--:|
| tie | 805 | 293 | **420** |
| rest | 2671 | 1598 | 1637 |
| note | 5916 | 4823 | **4794** |
| slur | 386 | 266 | 276 |
| beam | 2066 | 1369 | 1454 |
| time | 241 | 68 | 74 |

Same signature as the 5-row era: the graft recovers ties (+127 of a 512-tie
hole on the non-bach rows) and beams while emitting slightly *fewer* notes —
the floor works by believing fewer noteheads. The rest hole (1637 of 2671)
remains nobody's business here, as before.

## The built-in control: both checkpoints reproduce the determinism probe EXACTLY

The harness is byte-deterministic (noise floor 0.0000 —
DETERMINISM_2026-09-04.md) and the promotion commit touched only
`works.json` / `VERIFICATION.md`, so the five original rows in these runs had
to reproduce the probe's recorded values exactly, or the tree had drifted and
no baseline should be recorded. They did, on **every original row, both
checkpoints, to full float precision** — and the stronger fact: **every
prediction file is byte-identical** to the probe's fixture.

| row | hollow-ft vs det-a | graft vs det-c |
|---|---|---|
| beethoven-984073-p1 | 0.6924816280384398 / 1225 — EXACT, bytes identical | 0.7152391546162402 / 1286 — EXACT, bytes identical |
| beethoven-575951-p1 | 0.766016713091922 / 1375 — EXACT, bytes identical | 0.7625979843225084 / 1362 — EXACT, bytes identical |
| dvorak-405834-p5 | 0.4381443298969072 / 680 — EXACT, bytes identical | 0.4305822136916187 / 673 — EXACT, bytes identical |
| brahms-317803-p1 | 0.9209327258107746 / 3436 — EXACT, bytes identical | 0.9191648822269807 / 3434 — EXACT, bytes identical |
| mahler-local-p2 | 0.7122128174123338 / 1178 — EXACT, bytes identical | 0.6882316697473814 / 1117 — EXACT, bytes identical |

This also closes a tree-equivalence loop worth keeping: this worktree
(`84a5ccac`, off the labeling branch) *lacks* the `OMR_CELL_LINE_TRACE`
addition to `measure_extractor.py` that the determinism tree (`b8b10514`)
carries, and its `transcribe.py` differs only in the `DEFAULT_WEIGHTS`
constant (bypassed here — weights are pinned explicitly). Byte-identical
predictions from both sides now prove that addition inert for transcription in
both directions.

## Reproduction

```bash
git worktree add <dir> -b <branch> 84a5ccac && cd <dir>
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned
ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-surya .venv-surya
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
OMR_SCAN_EVAL_WEIGHTS=/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt \
  python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --wait-for-cpu \
  --tag widened-hollowft --out benchmarks/omr-scan-e2e-2026-09/results-widened-hollowft.json
OMR_SCAN_EVAL_WEIGHTS=/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
  python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --wait-for-cpu \
  --tag widened-graft --out benchmarks/omr-scan-e2e-2026-09/results-widened-graft.json
```

Provenance details, each verified during the runs:

- `84a5ccac`'s `scan_eval.py` predates the `OMR_SCAN_EVAL_WEIGHTS` hook (it
  lives on the round4-continue branch), so the hook — the identical four
  lines — is ported here in the same commit as this record. Without it both
  arms would silently run `DEFAULT_WEIGHTS`, which at this commit is the
  graft.
- All 22 fixture JSONs record the intended absolute weights path and
  `weight_routing: null` (explicit pin skips routing).
- The production graft file
  (`omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`) is
  byte-identical to `omr-weights/round5-merged/d25e0_graftprod_shift0.9.pt`,
  re-checked before the runs.
- Runs sequential (truth fixtures are shared, tags are not); both exited 0 —
  no optional pass failed like a defect on any of the 22 transcriptions.
- Protocol from `works.json`, unchanged: dpi 600, conf 0.25, imgsz null,
  direction text at pipeline default (ON), no dossier. Exact-pitch recall
  above covers the 7 rows with `staves` maps; brahms-p2, mahler-p2/p3 and
  bach have none yet, and `note_recall` abstains there by design.

Result JSONs beside this file: `results-widened-hollowft.json`,
`results-widened-graft.json`.

---

## Addendum, same day: Bach excluded from the default pool

Sean decided the open question above: the Bach stress row is now
`"pooled": false` in works.json, and `scan_eval.py` computes the default
pooled figure over pooled rows only (stress rows still run and report
per-row). **The canonical baselines are therefore this doc's 10-row column:
hollow-ft 0.8457 / 29081, production graft 0.8387 / 29082.** The 11-row
readings above remain the record for Bach's eventual re-admission. Decision
rationale: VERIFICATION.md, same date.

---

## Second addendum: cell-grid localization shipped default-ON (same day)

Sean shipped `OMR_CELL_LINE_TRACE` default-ON after WIDENED_PRICING priced
it (pooled −233 edits, on the exposure). **The deployed default-config
baseline is therefore the flag-on arm: production (hollow-graft-shift09)
pooled 0.8345 / 28849 over the 10-row pool.** This doc's tables were
measured flag-OFF; they remain the flag-off record, and comparisons against
a default-config run must use the flag-on figures (or pin
`OMR_CELL_LINE_TRACE=0` to compare against the tables here). Per-row
flag-on figures: WIDENED_PRICING_2026-09-04.md.

---

## Third addendum (2026-09-05): the re-stamped composed baseline — 11 rows

Sean's coupled ship (choir cues default-ON + Bach re-admitted) closed with
one fresh default-config run (tag `restamp-composed`, graft weights pinned,
tilt localization ON x choir cues ON, all 11 rows pooled):

**CANONICAL SCAN-GATE BASELINE: pooled OMR-NED 0.8303 / 35,046 edits over
23,377 truth + 18,834 predicted symbols, 11 rows.**
(`results-restamp-composed.json`)

Internal consistency, verified: every one of the ten non-Bach rows
reproduces the tilt-on arm's per-row figure TO THE EDIT (the choir cues'
byte-identity guarantee holding under composition), so the 10-row subtotal
is exactly the 0.8345 / 28,849 of the second addendum; Bach enters at
0.8110 / 6,197 (vs 0.8152 choir-only — the tilt x choir composition is
worth a further −39 edits there), and at 0.8110 the once-excluded stress
row now sits BETTER than the pool average. Boundary discipline: no figure
from the 10-row or 5-row eras compares to this one in either direction.
