# H1′ — the reference roster as a UNION over a page's systems

**2026-09-05. MEASURED. No pipeline code was touched** — `tools/omr/slots.py` is
imported and called; arm A is the shipped `build_reference` + `align` run
unmodified, and arm B swaps only the roster constructor for the benchmark-local
`build_reference_union` in
[`probe_union_roster.py`](probe_union_roster.py), calling the same unmodified
`slots.align`. Output: [`union-roster.json`](union-roster.json).

---

## PRE-REGISTERED SUCCESS CRITERION

Written into the probe's docstring before the first run, and taken verbatim from
the brief:

1. **arm B must produce the correct 12-slot union on BOTH Beethoven 5 p.4 rows**
   (`beethoven-sym5-mvt1-984073-p4`, `beethoven-sym5-mvt1-575951-p4`), **and**
2. **arm B must not degrade any row arm A already gets right.**

> A union that fixes p4 by breaking Brahms p3/p4 is a failure, exactly as the
> bracket-shape detector was.

## VERDICT: **NOT MET.** Arm B is a strict NO-OP on this corpus.

| | |
|---|---|
| criterion 1 — p4 union is 12 | ❌ **11 on both rows.** Zero insertions on all 10 scored rows. |
| criterion 2 — no regression | ✅ trivially: arm B's roster is byte-identical to arm A's everywhere. |

Arm B did not fail by over-reaching. It failed by **never firing**: across all
ten scored rows the merge DP made **0 insertions**, so the union equals the
single-system roster every time. `merge_trace` in the JSON records this per row.

---

## Provenance

**Fixtures.** The **20-row gate**, read-only, from
`/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. Asserted: 20 rows, **396 staves**, 11
multi-system rows, every one of them exactly two systems. (The main checkout's
`fixtures/` is the stale 11-row `..graft09` set — the trap this repo has hit
three times.)

**Scoring key.** `benchmarks/omr-scan-e2e-2026-09/works.json`, **scoring only,
never an input**. Dossiers barred entirely. Read with `json`; no regexes on
structured formats anywhere.

**Staff geometry.** Re-detected — `preprocessing.render_page` (600 dpi) +
`staff_detector.detect_staves`, **no YOLO, no OCR**, because `Staff.group_index`
(`_pair_score`'s second term) is not retained in the fixtures. Every row asserts
its re-detected per-system staff counts against the fixture's; **all 11
multi-system rows matched** (the four rows where re-detection differs from the
fixtures are the Mahler rows, all single-system, all outside this experiment).

**Labels — and which rung read each.** `slots.align`'s dominant term is the
**raw per-system** margin label. The fixtures retain only the resolved,
post-join `instrument`, which is assigned BY the join and therefore circular
(the class-6 result). So labels come from
`vendored-labels/classified.json` — the labels workstream's committed
per-(row, system, position) ladder answers, each carrying `resolved_by`.

| rung | labels supplied |
|---|--:|
| Surya (local, resident server) | **132** |
| PDF text layer | **25** |
| Tesseract | **0** |
| **total fed to the aligner** | **157** |

Reusing them rather than re-running the ladder is sound because
`git diff 672607c9 HEAD -- tools/omr/{instruments,staff_labels,staff_labels_surya,staff_labels_tesseract,staff_detector,contextual,system_grouping,slots,preprocessing}.py`
is **empty** on this tree — the readers that produced those files are the readers
here — and it spends no CPU on a machine where another agent is doing OCR
concurrently. ⚠️ **Deviation, applied identically to both arms:** the shipped
`labels_by_staff` filters to `high`/`medium` confidence and the vendored records
carry no confidence field, so every resolved label was passed through. That gives
arm B *more* label evidence than production would, not less.

## Coverage, before any gain

| | rows |
|---|--:|
| multi-system rows in the gate | **11** |
| scored | **10** |
| abstained | **1** |

* **PRIMARY (5)** — rows carrying `systems_as_printed`, a hand-verified
  **per-system** lineup: `beethoven-…-984073-p3`, `-984073-p4`, `-575951-p3`,
  `-575951-p4` (the last two by `same-as:`), `brahms-…-p2`.
* **SECONDARY (5)** — `beethoven-…-984073-p2`, `-575951-p2`, `brahms-…-p3`,
  `-p4`, `dvorak-…-p7`. Their page-level `staves` list holds exactly
  `n_staves / n_systems` entries, which asserts every system prints the SAME
  lineup. ⚠️ **That is MY reading of the key, not a per-system map the key
  states.** It is kept out of the primary number and labelled everywhere. It
  exists so criterion (2) has rows to be tested on at all — without it, six of
  the eight ordinal-succeeds rows would be unscoreable and "does not degrade"
  would be vacuous.
* **ABSTAINED (1)** — `bach-brandenburg3-mvt1-468678-p1`: the row states no
  lineup, in either form. Counted, not imputed.

## Metric

Per **(system, staff)**: the arm's slot assignment induces a partner — the staff
of the *other* system sharing its slot, or `None`. Truth gives the acceptable
partner set from the two lineups, matched on reference **part sets**
(an LCS over exact part-tuples, with condensation admitted inside the gaps: p.4's
`Bassi{16,17}` is correct against either `Violoncello{16}` or `Basso{17}`).
An empty set is the positive claim "this part is not printed in the other
system". ⚠️ **Each correspondence is counted twice**, once from each side, so a
22-decision row is 11 independent facts.

---

## The A/B table

`strc` = detected per-system staff counts. `labs` = labels resolved on the page.
`uTru` = the truth union size. Each arm: **roster size**, then
**correct / decisions**.

| row | tier | strc | labs | uTru | A (control) | B (union) | C (refutation) |
|---|---|---|--:|--:|---|---|---|
| beethoven-…-575951-p2 | SECONDARY | 11,11 | 14 | 11 | 11 · 22/22 | 11 · 22/22 | 11 · 22/22 |
| beethoven-…-575951-p3 | PRIMARY | 11,8 | 11 | 11 | 11 · 19/19 | 11 · 19/19 | 11 · 19/19 |
| **beethoven-…-575951-p4** | PRIMARY | 11,11 | 13 | **12** | 11 · **14/22** | 11 · **14/22** | 12 · 15/22 |
| beethoven-…-984073-p2 | SECONDARY | 11,11 | 14 | 11 | 11 · 22/22 | 11 · 22/22 | 11 · 22/22 |
| beethoven-…-984073-p3 | PRIMARY | 11,8 | 11 | 11 | 11 · 19/19 | 11 · 19/19 | 11 · 19/19 |
| **beethoven-…-984073-p4** | PRIMARY | 11,11 | 13 | **12** | 11 · **14/22** | 11 · **14/22** | 12 · 15/22 |
| brahms-…-p2 | PRIMARY | 14,13 | 26 | 14 | 14 · 27/27 | 14 · 27/27 | 14 · 27/27 |
| brahms-…-p3 | SECONDARY | 14,14 | 27 | 14 | 14 · 28/28 | 14 · 28/28 | **15 · 24/28** |
| brahms-…-p4 | SECONDARY | 14,14 | 28 | 14 | 14 · 28/28 | 14 · 28/28 | 14 · 28/28 |
| dvorak-…-p7 | SECONDARY | 15,15 | **0** | 15 | 15 · 30/30 | 15 · 30/30 | 15 · 30/30 |
| **PRIMARY pooled** | | | | | **93/109** | **93/109** | 95/109 |
| **SECONDARY pooled** | | | | | **130/130** | **130/130** | 126/130 |

Arm A and arm B are identical on every row, every slot, every decision.

Two rows are worth reading on their own. **`brahms-…-p2` is arm A working
exactly as designed**: 14 staves against 13, system 2 drops the Trumpets, the
Timpani label meets a Trumpet slot, `SCORE_LABEL_CONFLICT` fires, the DP gaps the
slot — 27/27, and the union has nothing to add because the largest system already
holds every part. **`dvorak-…-p7` resolves 0 labels** (Simrock labels a
movement's first page only) and still scores 30/30 on position and bracket group
alone, because both systems print the same fifteen.

---

## Why arm B never fired — the arithmetic, on `984073-p4`

Roster (arm A's, seeded on system 2 — 11 staves, 7 labels, beating system 1's 6):

```
slot     0     1     2     3     4    5    6     7  8  9  10
group    0     0     0     0     1    1    1     2  2  2  2
name    Fl    Ob    Cl   Fag   Cor   Tr   Tp     ·  ·  ·  ·
system 1 groups:  0 0 0 0 1 1 | 2 | 2 2 2 2      (11 staves, 6 labels, none below Tr.)
```

The bracket blocks are read **correctly and differently** in the two systems —
system 1 puts 2 staves in the brass block, system 2 puts 3 — so the group term
*does* see the Timpani. It is not enough:

| path | what it pays |
|---|--:|
| diagonal (what both arms take) | one group conflict at slot 6: **−3.0** |
| the correct union | one slot gap + one insertion **−2.0**, four positions shifted 0.1 **−0.4**, and — the decisive item — **it must give up a match**, since 11 staves over 12 slots means the last staff is inserted instead of scored: **−2.5** |

Diagonal **60.5** vs union **58.6**. The optimal insert-bearing path loses by
**1.5** (`insert_margin` in the JSON, measured on every row). Readable against
the constants that produced it: a `GAP_PENALTY` is 1.0, a bracket-group
agree/disagree swing is 3.0, a label match is 6.0 and a label **conflict** is
−8.0 (a 14.0 swing). **The union is 1.5 short of a signal it does not have** —
because the four string staves that would settle it print no label in either
system, and `SCORE_LABEL_CONFLICT` needs both sides named. A staff that prints
nothing is silent, never contradictory. This is the H1 mechanism, now **measured**
rather than inferred: the HYPOTHESES.md entry marked "ARITHMETIC + DOCUMENTED
BEHAVIOUR, NOT OBSERVED" can be promoted for the label half — 13 labels over 22
positions, 6 in system 1 and 7 in system 2, `Tp.` read by Surya at system 2
position 6 and nothing at system 1 position 6, all in `label_provenance`.

## Arm C — and it closes the reweighting route

**Arm C is a refutation, not a proposal.** Gap and insertion are set to **zero** —
free, the cheapest a union can be made out of the terms `_pair_score` already
has. It answers one question: *can any reweighting of the existing terms separate
p.4, where the union is right, from the rows arm A already gets right?*

**No.** Arm C fixes both p.4 rows' roster size and **breaks `brahms-…-p3`**
(roster 15 against a truth of 14; 28/28 → 24/28). And the two cases are
**indistinguishable by construction**: the insert margin is **1.5 on p.4 and 1.5
on brahms-p3**. Anything that flips one flips the other.

The mechanism is the one the bracket-shape detector already died of.
`brahms-…-p3` prints the *same* fourteen staves in both systems, but
`system_grouping` reads their blocks as `[0×5, 1×3, 2×6]` and `[0×9, 1×5]` — a
**detection disagreement between two systems of one page**, which is exactly
block recall 0.523 "unevenly distributed across systems". On unlabelled staves
`group_index` is the union's only discriminator, and it cannot tell a real lineup
change (p.4) from its own noise (brahms p.3).

⚠️ **Arm C also shows criterion (1) is necessary and not sufficient, and I would
have been fooled by it alone.** Arm C reaches a **12-slot** roster on p.4 and is
still wrong: it inserts the new slot at index 6, *before* Timpani, instead of
gapping Timpani and appending Basso — so continuity moves only 14/22 → 15/22.
A correct-size roster arrived at by the wrong route. The criterion was met in
letter and the join stayed broken. Only the continuity column caught it.

---

## How this could have produced a falsely encouraging number

Stated because the honest reading depends on it. It did not — the result is
negative — but the same construction would have flattered a positive one.

1. **The SECONDARY tier is my own inference from the key**, not a per-system map
   `works.json` states. Its rows are also where arm A scores 130/130, so
   "criterion 2 met" is a weak test: arm B was compared against a control that
   is already perfect there, and it passed by doing nothing.
2. **The partner metric counts each correspondence twice** (once per side), so
   pooled denominators are 2× the independent facts. It also awards a point for
   every correctly-predicted `None`, which on a page where both systems print the
   same lineup is a majority of the decisions.
3. **A single arm-B insertion in the right place would have moved the pooled
   number a long way on n=10 rows**, because the p.4 rows carry 8 of the 16
   PRIMARY errors between them. One page in two editions is not two independent
   positives — the two Litolff scans are the *same engraving*, and their
   agreement is a re-print, not a replication.
4. **The labels were vendored, not re-read.** If the readers had drifted, arm B
   would have been fed a substrate the pipeline no longer produces. Guarded by
   the empty `git diff` over every reader, the lexicon, and `slots.py` itself.
5. **Arm B is seeded on `build_reference`'s own pick**, so it can only ever be a
   superset of arm A. That makes "no regression" partly structural rather than
   earned, and it is why the interesting evidence is arm C, which can regress and
   does.

## Conclusion

**H1′ is refuted on this corpus as a self-contained fix, and refuted for the
right reason rather than by a null.** The union is the correct *shape* — the
truth union on p.4 really is 12, and `align` really does support the gap it would
need — but the roster constructor is not where the information is missing. What
is missing is **any evidence at all on the four unlabelled string staves**, and
no rearrangement of label, bracket group and relative position supplies it: arm C
proves that the reweighting which admits p.4 also admits a phantom slot on a page
whose systems are identical.

**Refutable but not shippable on this corpus**, and the refutation is the useful
half. n = 10 scored rows, 5 of them PRIMARY, and the positives are **one page in
two editions of the same engraving**. What this does establish, on measurement:

* the union roster **costs nothing** — a strict no-op on 10 of 10 rows, including
  three where the ordinal join refuses. It is safe, and it is idle.
* the p.4 deficit is **1.5 in the DP's own units**, against a 3.0 bracket-group
  swing and a 14.0 label swing. That is a size, not a mystery.
* **`group_index` cannot be the discriminator**: its between-system disagreement
  on `brahms-…-p3` is detector noise of the same magnitude as p.4's real lineup
  change. This is a direct, measured argument for **H5** (raise bracket-block
  recall) *before* anything is built on blocks, and against any consumer that
  trusts a group difference between two systems of one page.
* the next term must be worth **more than 1.5 and be independent of the labels**,
  which is precisely **H3** — the gap fingerprint and register continuity. This
  probe hands H3 a number to beat and a row that must not move
  (`brahms-…-p3`, 28/28, insert margin 1.5).

⚠️ Do **not** close H1′ by lowering `GAP_PENALTY`. That is arm C, it is fitted to
two rows of one engraving, and it is measured here to break a correct row.
