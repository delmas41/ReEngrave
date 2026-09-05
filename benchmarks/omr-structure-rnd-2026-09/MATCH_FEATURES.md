# H3 — inter-staff gap fingerprints and register continuity as pairwise MATCH features

> ## ⚠️ PARKED MID-FLIGHT, 2026-09-05
>
> This workstream was **redirected by the coordinator on 2026-09-05**, at Sean's
> direction, before the A/B through `slots.align` was started. **Do not read the
> tables below as a finished negative on H3 as a whole.** What was reached is the
> **discriminator stage**, which is complete, self-contained and was the stage
> the brief nominated as the cheap kill. What was NOT reached is stated in its
> own section, by clause, and no number is reported for it.
>
> The redirect does not invalidate anything here: H3 was scored throughout
> against `works.json`'s **hand-read printed lineups**, never against a reference
> encoding, so it already sits on the right side of the new line.

**MEASUREMENT ONLY. No pipeline code was touched.** `tools/omr/slots.py` is
imported and called. The probe is
[`probe_match_features.py`](probe_match_features.py); output
[`match-features.json`](match-features.json). Fixture loading, the re-detection
assertions, the vendored labels, the truth construction and the **partner
metric** are imported from [`probe_union_roster.py`](probe_union_roster.py), so
every continuity number here is the same object H1′ reports.

---

## PRE-REGISTERED TARGET

Written into the probe's docstring before the first run, verbatim from the brief:

1. a new `_pair_score` term must be worth **more than 1.5** where
   `beethoven-…-p4` needs it, **and**
2. **`brahms-…-p3` must stay 28/28** (its insert margin is also 1.5), **and**
3. the p.4 union must be reached by the **CORRECT ROUTE** — gap Timpani, append
   Basso — not merely at the correct SIZE. Roster size alone would have declared
   arm C a success; only the continuity column caught it.

### VERDICT ON WHAT WAS RUN: **NOT MET — neither feature separates the two rows.**

| clause | status |
|---|---|
| (1) worth > 1.5 on p.4 | ❌ **evaluated and failed at the discriminator stage.** The gap feature's own argmax never beats the diagonal on either p.4 row at **any** skip cost in 0.05–2.00 (best 14/22, the diagonal's own score, against a ceiling of 21). Its signed margin toward the truth path is positive but tiny: it would need a weight of **4.06** to be worth 1.5, against a bracket-group swing of 3.0. |
| (2) brahms-p3 stays 28/28 | ⚠️ **NOT REACHED as an A/B.** What is measured: the gap feature *alone* holds brahms-p3 at **28/28** across skip costs 0.45–2.00, so it is not obviously destructive. That is a discriminator result, **not** the required A/B through `slots.align`. |
| (3) correct route on p.4 | ⚠️ **NOT REACHED.** No roster was built with a feature term, so there is no route to check. **No roster-size claim is made anywhere in this document.** |

**The separation question the brief made decisive — does either feature separate
`beethoven-…-p4` (a real lineup change) from `brahms-…-p3` (identical lineups,
noisy blocks)? — is answered NO for both features and for their combination.**
Per the brief's own method (*"if it does not separate those two, stop and
report; wiring it into the DP cannot rescue it, and that is arm C's lesson"*),
that is the stopping point, and it coincides with the redirect.

---

## Provenance

**Fixtures.** The **20-row gate**, read-only, from
`/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. Asserted: 20 rows, **396 staves**, 11
multi-system rows, all exactly two systems. (The main checkout's `fixtures/` is
the stale 11-row `..graft09` set — the trap hit three times in two days.)

**Gap substrate.** `staff_geometry.line_ys_page` + `line_spacing_px` from those
fixtures, present on all 396 staves. **Pure geometry — no detector, no OCR, no
lexicon.**

**Register substrate.** The fixtures' own notehead detections carrying a
`pitch`, parsed by a real pitch parser (step letter → accidental run → signed
octave), not a regex.

**`group_index`.** Not retained in the fixtures, so it comes from H1′'s cached
structure-only re-detection (`render_page` + `detect_staves`; no YOLO, no OCR).
Used ONLY by the shipped `_pair_score` and by the correlation test below.

**Labels.** `vendored-labels/classified.json`, as in H1′.

**Scoring key.** `benchmarks/omr-scan-e2e-2026-09/works.json`, **scoring only,
never an input**. Dossiers barred entirely.

### Coverage, before gain

| | rows |
|---|--:|
| multi-system rows in the gate | **11** |
| scored | **10** |
| abstained | **1** — `bach-brandenburg3-mvt1-468678-p1`, which states no lineup in either form. Counted, not imputed. |

Tiers are H1′'s and carry its warning: **PRIMARY** (5 rows) carry a hand-verified
per-system lineup; **SECONDARY** (5) are rows whose page-level `staves` list
divides evenly, which is *the previous probe's reading of the key*, not a
per-system map the key states.

---

## The features, and the one normalisation that is not free

**Gap fingerprint.** For each staff, the vertical gap to the staff above and
below, expressed in **staff spaces** (divided by the system's median
`line_spacing_px`) and then divided by **that system's own median gap**. A pair's
distance is the mean absolute difference over the components defined on both
sides; where none is shared the feature **abstains** and the abstention is
counted, never imputed as agreement.

⚠️ **The second normalisation is load-bearing and I inspected two rows before
fixing it.** The two systems of one page are not set to the same vertical
density: on `…-984073-p4` the Corni gap is **7.37 staff spaces in system 1
against 4.13 in system 2 for the same true pair**. Raw gaps are therefore not
comparable between systems, and without the normalisation the feature is
dominated by page layout. The rows I looked at first were `…-984073-p4` and
`brahms-…-p3` — the two rows the target is defined on. **This is a real
methodological debt and it is disclosed rather than hidden**; it can only have
flattered the feature, and the feature still failed.

**Register continuity.** The median MIDI pitch of a staff's pitched noteheads;
pair distance in semitones.

⚠️ **Zero-detection stratum, kept separate as the brief requires.**
`n_noteheads_detected` is recorded beside every register figure. Of **239 staves**
across the ten scored rows, **2 have zero noteheads and 2 have zero pitched
noteheads** (they are the same two: `brahms-…-p4` system 2 position 7,
`dvorak-…-p7` system 1 position 9). Those pairs contribute nothing — **2 of 116
diagonal pairs abstain**. Per the retracted alarm in
`docs/staff-identity-audit-plan-2026-09-04.md`, "this staff has no noteheads" is
**not** treated as evidence of rest and **not** treated as an abstention-worthy
defect; it is simply an absence of evidence for this feature.

---

## The discriminator table

`diag` = the continuity the plain diagonal correspondence scores under the
partner metric. `ceil` = the **best any monotone one-to-one alignment can
reach** (see the artifact note below). `best` = the best continuity the feature's
own argmax alignment reaches anywhere in the skip-cost sweep 0.05–2.00 (40
values). `D` = `Σ distance over diagonal pairs − Σ over the truth path`: the
coefficient of the weight, because a `−W·d` term touches only matched pairs, so
it moves (truth path − diagonal path) by exactly `W·D`. **`D ≤ 0` means no
positive weight can move that row toward the truth at all.** `W*` = `1.5 / D`,
the weight the H1′ deficit would demand.

| row | tier | diag | ceil | gap `best` | gap `D` | gap `W*` | reg `best` | reg `D` | reg `W*` |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| beethoven-…-575951-p2 | SECONDARY | 22/22 | 22 | **22** | +0.000 | — | 16 | +0.0 | — |
| beethoven-…-575951-p3 | PRIMARY | 2/19 | 19 | 9 | +0.080 | 18.66 | 9 | +49.0 | 0.031 |
| **beethoven-…-575951-p4** | PRIMARY | **14/22** | **21** | **14** | **+0.420** | **3.57** | 11 | +31.5 | 0.048 |
| beethoven-…-984073-p2 | SECONDARY | 22/22 | 22 | **22** | +0.000 | — | 18 | +0.0 | — |
| beethoven-…-984073-p3 | PRIMARY | 2/19 | 19 | 6 | **−0.237** | ∅ | 13 | +53.0 | 0.028 |
| **beethoven-…-984073-p4** | PRIMARY | **14/22** | **21** | **14** | **+0.369** | **4.06** | 9 | **−0.27**† | ∅ |
| brahms-…-p2 | PRIMARY | 14/27 | 27 | **24** | +1.097 | 1.37 | 5 | +15.0 | 0.100 |
| **brahms-…-p3** | SECONDARY | **28/28** | 28 | **28** | 0.000 | — | 10 | 0.0 | — |
| brahms-…-p4 | SECONDARY | 28/28 | 28 | **28** | 0.000 | — | 20 | 0.0 | — |
| dvorak-…-p7 | SECONDARY | 30/30 | 30 | **30** | 0.000 | — | 4 | 0.0 | — |

† the register margin on `984073-p4` is **negative** while on the same page in
the other edition (`575951-p4`) it is +31.5. Two scans of the **same engraving**
disagree in sign on the register feature.

### How to read it

**The gap feature is stable but not discriminative.** On the five rows where the
two systems print the same lineup it holds the diagonal — 22/22, 22/22, 28/28,
28/28, 30/30 — over wide skip-cost plateaus (e.g. brahms-p3 for every skip cost
0.45–2.00). That is a real property and it is the half that matters for clause
(2). But **on p.4, the one row where a lineup genuinely changes, it never once
prefers the truth**: its best over the whole sweep is 14/22, exactly the
diagonal's score, against a ceiling of 21. Its signed margin toward the truth
path is positive (+0.37/+0.42) but so small that clearing H1′'s 1.5 deficit would
need a weight of **4.06** — a scale at which one unit of normalised-gap
disagreement outweighs the entire bracket-group swing (3.0). Nothing in the
measurement justifies that scale, and picking it would be arm C in another
costume: a constant fitted to two rows of one engraving.

**Register is not a match feature on this corpus.** Its argmax is worse than the
diagonal on every row that has a diagonal to beat (16/22, 18/22, 10/28, 20/28,
**4/30** against 30/30 on Dvořák). The large positive `D` values are an artifact
of scale, not of signal: register distances are in semitones and run to tens, so
`W*` comes out at 0.03–0.10 — a weight at which the feature would still be
choosing the wrong alignment, only more cheaply. And the sign flip between the
two editions of p.4 (+1.77 vs −0.27 in mean semitones) says the feature is noise
at the magnitude that matters here.

**The one genuine positive, recorded because it is not nothing.**
`brahms-…-p2` is a real lineup change (14 staves against 13, the Trumpets
dropped) and the **gap feature alone lifts it from 14/27 to 24/27, using no
labels and no `group_index` at all**. The shipped aligner already gets that row
27/27 via a label conflict, so this buys nothing today — but it is the only
direct evidence on this corpus that a gap fingerprint carries *any* real
structural information, and it is the row a future attempt should start from.

---

## `group_index` correlation — asked as part of the experiment, not after it

The constraint from H1′: if the evidence correlates with `group_index`, it
inherits that term's between-system detection noise and H3 has measured the same
thing twice. Reported as the **AUC of −distance as a classifier of
`group_index` agreement**, over every cross-system pair of every scored row.
0.5 = independent.

| feature | min | median | max | on `brahms-…-p3` |
|---|--:|--:|--:|--:|
| **gap** | 0.407 | **0.510** | 0.573 | **0.502** |
| register | 0.523 | 0.551 | 0.585 | 0.523 |

**The gap fingerprint passes this test cleanly — median AUC 0.510, and 0.502 on
the very row where `group_index` is noisiest.** It is genuinely independent of
both labels (it never reads one) and of bracket blocks. Register is mildly
correlated (median 0.551) but the correlation is not what sinks it.

⚠️ **So the constraint was satisfied and the feature still failed.** That is the
useful shape of this result: **independence was never the binding problem.** The
gap fingerprint is exactly the label-free, block-free signal H3 asked for, and it
simply does not carry enough information about p.4's lineup change. A future
label-free feature will have to clear an *information* bar, not an independence
bar.

---

## What was NOT reached

* **No arm D.** The A/B through `slots.align` with a feature term added was not
  run. No roster was built with a feature term, so **no roster size, no insert
  margin under the new term, and no route check exist**. Clause (3) is
  unevaluated, and clause (2) is evaluated only in the weak, feature-alone sense
  above.
* **No second corpus.** n = 10 scored rows, 5 PRIMARY, and the positives are
  **one page in two editions of the same engraving** — a re-print, not a
  replication.
* **No sweep of the gap definition.** One normalisation was declared and used.
  Whether a different gap encoding (e.g. gaps as ranks, or block-boundary
  indicators rather than magnitudes) separates p.4 is **not measured** and must
  not be inferred from these numbers in either direction.

---

## How this could have produced a falsely encouraging number

1. **I inspected `…-984073-p4` and `brahms-…-p3` — the two target rows — before
   fixing the gap normalisation.** The normalisation was chosen with those two
   vectors in front of me. It can only have flattered the feature, and the
   feature still failed, but a positive result reached this way would have been
   contaminated.
2. **A ceiling artifact of my own metric, caught and fixed mid-flight.** The
   first version asked "is the feature's argmax *equal to the truth*". On p.4
   that is **impossible by construction**: two system-1 staves (Violoncello,
   Basso) are each acceptable only against the single condensed `Bassi` staff of
   system 2, and a one-to-one alignment can give `Bassi` to only one of them.
   The test could only ever return False on the row it mattered on, which would
   have looked like a decisive negative that was really a bug. The table now
   reports the partner metric against an **exact computed ceiling** (21/22 on
   p.4, not 22/22), so no arm is read against a target it cannot reach.
3. **`best` is a maximum over a 40-value sweep**, so it is optimistic by
   construction — it reports the best skip cost *after* seeing the answer. Even
   under that generosity the gap feature never beats the diagonal on p.4.
4. **`D` prices only matched pairs.** It is exact for a `−W·d` term added to
   `_pair_score`, but it says nothing about interactions with the gap and insert
   moves — which is precisely what an arm D would have measured and did not.
5. **The SECONDARY tier is H1′'s inference from the key**, not a per-system map
   `works.json` states, and it is where the gap feature scores perfectly. "Holds
   the correct rows" is therefore a weak test on a control that is already right.

---

## Conclusion, and what would settle it

**On what was measured: neither feature separates a real lineup change from
detector noise on this corpus, and the gap fingerprint fails despite being
exactly as independent as H3 required.** The stopping rule the brief specified
was reached before the redirect arrived.

What this establishes, on measurement rather than argument:

* **A label- and block-independent geometric signal EXISTS and is measurable.**
  The gap fingerprint's `group_index` AUC of 0.510 is the cleanest independence
  result in this whole workstream, and on `brahms-…-p2` it recovers a real
  lineup change (14/27 → 24/27) from geometry alone.
* **Independence was not the binding constraint — information was.** The signal
  is real and too weak, on this page, at this margin. H1′ handed H3 a 1.5-point
  deficit; the gap fingerprint offers **0.37 per unit weight**, and the weight
  that would close it is larger than the bracket-group term it is meant to
  replace.
* **Register continuity should not be carried forward as a match feature in this
  form.** It is worse than the diagonal on every row that has one, and it
  disagrees in sign between two scans of the same engraving.
* **The honest verdict is "refutable but not shippable here", with a caveat the
  redirect makes larger**: p.4 is one page in two editions, and a feature that
  fails on it has failed on **one** printed lineup change plus one where it
  partly succeeded (brahms-p2). That is not enough evidence to close gap
  fingerprints as an idea — only enough to close *this* encoding of them at
  *this* weight.

**What would settle it:** more rows where the printed lineup genuinely changes
between two systems of one page. This corpus has two such patterns
(`beethoven-p4` ×2 editions, `brahms-p2`) and the feature scores 0/2 and 1/1 on
them. Under the new page-derived benchmark that population is exactly what needs
enumerating first — **the measurement to do next is a census of printed lineup
changes, not another feature.**
