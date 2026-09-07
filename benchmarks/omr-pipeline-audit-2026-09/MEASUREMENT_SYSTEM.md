# How this project measures, what is wrong with it, and one unit to read it by

**Agent III of the 2026-09-07 overnight pipeline audit.** Part A is an
adversarial critique of the measurement estate. Part B designs and prototypes
Sean's requested unit — **% of achievable, 0-100, higher is better** — and Part C
says what it would take to put it on the dashboard.

⚠️ **Nothing here changes pipeline behaviour.** Four read-only probes, one
proposed registry, this document. No arm was run: every figure below is read out
of an artefact already committed, and the artefact is named beside it.

Artefacts written by this session:

| file | what it is |
|---|---|
| `probe/probe_ceiling_engine_independence.py` → `ceiling-engine-independence.json` | is the structural charge a fact about the fixture or about us? |
| `probe/probe_pct_of_achievable.py` → `pct-of-achievable-prototype.json` | the unit, computed on real rows |
| `probe/probe_measurement_hygiene.py` → `measurement-hygiene.json` | visibility census + stamp census |
| `probe/build_metric_registry.py` → `metric-registry.json` | the machine-readable registry, 48 rows |
| `probe/probe_engraved_noise_floor.py` → `engraved-noise-floor.json` | **round 4** — the authorised two-work determinism arm |
| `README-metric-registry.md` | what wiring it into the dashboard would take |

Round 2 adds four more probes and takes the registry to v0.2.0; **round 3** adds
`probe/probe_hairpin_ceiling_value.py`, the shared `probe/_fixtureroot.py` guard
and `RUNBOOK-completion-passes.md`, and takes it to **v0.3.0** — see **ROUND 2**
at the end of this file, which also corrects four things stated in Part A and B.

---

# PART A — the critique

## A1. Forty-two of forty-eight result artefacts cannot be dated

`measurement-hygiene.json`, re-run after tonight's rebase: over `benchmarks/**`,
**48** committed result JSONs match the naming conventions this project uses for
a scored run. **Six carry a commit sha. Thirty-five carry something era-ish;
exactly ONE carries an era a test refuses to let drift** — `benchmarks/omr-ned-2026-08/current-accuracy.json`,
guarded by `accuracy_record.check()` and `test_accuracy_record.py`.

The scan side is where this bites. `benchmarks/omr-scan-e2e-2026-09/` holds
**twenty** `results-*.json` files spanning four different row sets — 1, 5, 11 and
20 rows — and the only way to tell which era a file belongs to is `len(rows)`.
None of them records the commit it was measured on. `results-reconciliation.json`
is the canonical 20-row baseline the dashboard reads, the one CLAUDE.md quotes at
0.8444, and it says nothing about when it was made.

CLAUDE.md already records the consequence: *"`c378412f`, which stamped 0.8444, is
not an ancestor of much that has since landed … `git diff c378412f <head> --
tools/omr` is 28 files."* That sentence is prose in one file. The artefact itself
is silent, so nothing mechanical can catch a fresh run being differenced against
it.

**Repair.** `scan_eval.py` should write the same shape `accuracy_record` already
enforces: a top-level `benchmark` block naming the row set, the date the row set
last changed, the commit, and the flag configuration — and a `check()` that
refuses a file whose row set disagrees with a `SCAN_ROWS` constant held in code.
The engraved side proves the design works; it was simply never extended.

## A2. The ceiling evidence and the headline were measured on different runs — closed the same night, which is the point

⚠️ **This section was written from a stale tree and is corrected in place, which
is itself the finding. See §A11.**

When this audit began, the page-normalised truth — the project's best measurement
work — was attached to the wrong arm. `benchmarks/omr-headline-validity-2026-09/results-normalised-arm.json`
scores the `..graft09` predictions at `transform_version 1.1.0`;
`results-reconciliation.json` scores `.reconciliation`. On the eleven rows they
share, **nine differ**:

| row | reconciliation (20-row) | normalised arm (graft09) | Δ edits |
|---|--:|--:|--:|
| beethoven-984073-p1 | 1283 | 1278 | −5 |
| dvorak-405834-p5 | 661 | 675 | +14 |
| brahms-317803-p1 | 3431 | 3434 | +3 |
| **bach-brandenburg3-p1** | **6148** | **6720** | **+572** |
| (six others) | | | 1–10 |

Ten of eleven sit at or near the documented **±6-edit noise floor**, which is
independent corroboration for that floor. Bach's +572 is not noise — it is a real
configuration difference (the choir-grouping flag moves that row by ~500 edits).
So a ceiling taken from the graft09 arm could not be subtracted from the
reconciliation headline.

**It closed while I was writing.** The `page_normalise` fixes landed tonight and
produced `benchmarks/omr-page-normalise-fixes-2026-09/results-normalised-arm-20row.json`
— `transform_version 1.2.0`, tag `.reconciliation`, `git_head afea84ba`, **20
rows, 15 normalised** — whose `pooled_raw_over_all_scored_rows.omr_ned` is
`0.8443958865999122`, **exactly** the canonical figure to the last digit. The
ceiling and the headline now share an arm, which is the condition the whole
design in Part B rests on, and every scan number in this document has been
recomputed against it.

**The repair the episode argues for is structural, not editorial.** A ceiling is
a *pair* — (metric value, ceiling value) — and the pair is valid only when both
halves carry the same era key. That is why the registry holds `scan:omr_ned`
(20 rows, F assumed 0), `scan:omr_ned:ceiling_measured_15rows` (15 rows, F 0.134)
and `scan:omr_ned:ceiling_corroborated_subset` (5 rows, F 0.152) as **three
rows**, and refuses to difference them.

## A3. Eight of twenty-eight stage-cells have no number at all

`measurement-hygiene.json` §visibility, computed from the status board's own
fourteen stages × two input families:

| family | stages with no number | which |
|---|--:|---|
| engraved | **5 of 14** | 2 system grouping · 3 measure+barline · 9 margin labels · 10 staff→slot · 11 export |
| scan | **3 of 14** | 4 symbol detection · 5 stems+beams · 11 export |
| both | 1 | 11 export |

This is not a complaint about the board — the board says so honestly, in prose,
which is better than most projects manage. It is a claim about what the pooled
figures can be asked. **Four separate incidents in the record are the same fact
arriving as a surprise:**

- the choir-grouping A/B left all eleven engraved works *edit-for-edit
  identical* (`is_a_no_op`-style result, CLAUDE.md `OMR_CHOIR_GROUPING`) — stage 2
  has no engraved number, so of course it did;
- the eventless-measure dynamics fix is invisible to the engraved pool *by
  construction* (0 triggering bars over eleven works, 14 over eleven scan pages);
- `apply_contextual_analysis` died on main for hours and the pooled figure did
  not move — part names provably score **exactly 0 edits** through musicdiff;
- the roster/identity work ships default-ON at a measured cost of **zero edits**.

A measurement system that reported "no information here" rather than a silent
zero would have made all four predictable instead of forensic. That is the
`visibility` ceiling kind in Part B, and it is why a stage with no evidence must
render as *unscoreable*, never as a number.

## A4. `1.000` means four different things on one page

The status board today mixes, without a shared axis:

| what | direction | best | worst | where |
|---|---|---|---|---|
| OMR-NED | lower | 0 | 1 | `engraved:omr_ned` 0.1122, `scan:omr_ned` 0.8444 |
| reading F1 | higher | 1 | 0 | `reading:POOLED` 0.9192 |
| note recall | higher | 1 | 0 | `scan:pitch` 0.8343 |
| "n of m rows" | higher | 1 | 0 | `scan:staves` 20/20 |
| detector recall | higher | 1 | 0 | `scan:hairpin_detect` 1/99 |

`tools/dashboard/generate.py` already handles this with two fields (`rate` /
`ned`) and two threshold pairs (`RATE_GREEN=0.90` / `NED_GREEN=0.15`). Those
thresholds are the tell: **0.15 and 0.90 are hand-set constants with no evidence
behind them**, and they are doing the work a ceiling should do. A scan row at
OMR-NED 0.84 is red; a third of that number is a charge for a printing
convention, and nothing in the colour says so.

## A5. `wrong pitch` is structurally unreachable, and the fix for that is not a fix

CLAUDE.md records it: `AllObjects` excludes `Voicing` (`32767 & 131072 == 0`), so
musicdiff pairs notes *by pitch*, so every pitch error is REQUIRED to become
`noteins` + `notedel` and land in `wrong note`. A zero in `wrong pitch` therefore
carries no information at all.

`results-normalised-arm.json` shows the same structure one level up: the pooled
raw category table has `wrong pitch` **absent entirely** and `wrong note` at
9,308 of 35,569 edits. The registry's answer is to make bucket names carry a
`reachable: false` flag rather than a count, because a category that cannot fire
is not a zero — it is a hole, exactly like a blind stage.

## A6. The scale inherits the metric's reward for under-prediction — measured, live

CLAUDE.md warns that "a ratio that falls while `omr_ed` RISES is dilution, not
recognition". Two committed arms on the identical eleven-row row set:

| arm | truth | pred | edits | OMR-NED | % of achievable (F=0) |
|---|--:|--:|--:|--:|--:|
| `results-widened-hollowft.json` | 23,377 | 17,972 | 35,458 | 0.8575 | 14.25 |
| `results-widened-graft.json` | 23,377 | **18,586** | **35,817** | **0.8535** | **14.65** |

The graft arm emits 614 more symbols, incurs **359 more edits**, and scores
better on the ratio — so % of achievable would report **+0.40 points of
improvement** for a run that got more things wrong. (The graft *did* ship, and
correctly: CLAUDE.md justifies it on three separate gate axes, not on this ratio.
The point is that the ratio alone would have been the wrong reason.)

**Repair, and it is non-negotiable for the new unit:** every error-metric row
carries `companions.edits`, and a delta where the ratio improves while edits rise
is reported as **DILUTED**, not as an improvement. This is `rules.dilution_guard`
in the registry.

## A7. The transform that removes structural charge manufactures its own artefacts

Sean's brief flagged this and it is worse than "33 and 42". Summed over the
fifteen normalised rows of the canonical 20-row arm, `wrong lyric` goes from **30
edits raw to 231 normalised** — a 7.7× growth in a category that cannot occur on
these scores, which print no text a lyric could be. And on **three** rows the
transform makes its own target category *worse*: `entire staff insert/delete`
goes 87 → **484** (beethoven-984073-p3), 90 → **530** (575951-p3) and
715 → **1,222** (brahms-317803-p2), against a pooled fall of 11,927 → 2,236.

That is not a reason to reject the transform. It is the reason a ceiling needs a
control that can fail, and both controls this project built for it are good ones:
`engraved-normalise-noop.json` (`is_a_no_op: true` on all 11 engraved works — it
could have failed and did not), and — new tonight — engine independence (§B2),
which **did** fail, on three rows, and excluded them.

⚠️ One live defect in that evidence, and it is cheap:
`benchmarks/omr-headline-validity-2026-09/engraved-normalise-noop.json` was
written at `transform_version` **1.0.0**, and its raw figures match the
`no_direction_text` arm rather than the default one, while the scan arm it
certifies now runs **1.2.0**. (A second copy landed tonight at
`benchmarks/omr-page-normalise-fixes-2026-09/engraved-normalise-noop.json` — two
copies of one control is the duplication hazard `accuracy_record` exists to
prevent, arriving in the benchmark tree.)

## A8. n=1 flags, and the one place the precedent is enforced

`docs/backlog-2026-09-07-open-items.md` §B names the precedent plainly:
`OMR_MOVEMENT_REFERENCE` shipped default-ON on one work and a second work
measured it four times worse. Three flags currently sit off pending a second
work.

The measurement system does not represent this at all. A row measured on one work
and a row measured on eleven look identical in every table this project prints.
The registry carries `n` and `n_unit` on every row for exactly that reason, and
`scan:omr_ned:ceiling_corroborated_subset` carries an explicit flag saying it is
**5 of 20 rows and 3 of 6 works**.

## A9. Human review cost — the purpose — is not on the board at all

Sean's stated purpose for the project is reducing human review cost. It has been
measured **once**, as a side result
(`benchmarks/omr-identity-harness-2026-09/FINDINGS.md`): between two identity
passes, identity accuracy moved **44 records** and human cost moved **2**
(197 → 195), because driving `impossible` errors to zero converted them into
contradictions and left the reviewer the same number of staves to look at.

It has no harness, no ceiling, no era key and no artefact a registry can read. It
is in `metric-registry.json` as `human:review_cost`, `scoreable: false`, with
that reason written out — because **a purpose that is absent from the measurement
system is a purpose the measurement system will optimise away**, and this project
has now watched it happen once.

**Repair.** A `human_cost` row needs three things and none is expensive: a
definition (staff records a reviewer must open — the harness already computes
`contradicted only / unnamed / not-in-this-work / both`), an artefact that writes
it per arm, and a ceiling. The ceiling is the interesting part: the floor is not
zero, it is *the number of staves a human would have to look at even with a
perfect pipeline* — which for a payment-gated review UI is a genuinely
measurable quantity and the only one that answers "is this worth $5 a score".

## A11. The audit itself started on a stale tree — the hazard, live, on the auditor

The worktree this session was dispatched into was **28 commits behind main**. The
coordinator rebased it mid-session. This is the same hazard CLAUDE.md already
records about `c378412f` ("not an ancestor of much that has since landed …
`git diff c378412f <head> -- tools/omr` is 28 files"), happening to the process
built to audit it.

**What it would have cost, precisely.** After the rebase I re-ran all four probes
and diffed. Three outputs were **byte-identical** — the artefacts I had read were
untouched. The fourth changed, and the change was not cosmetic: a new artefact
had appeared, `results-normalised-arm-20row.json`, **20 rows on the canonical
arm**, which supersedes the 11-row/8-normalised evidence my entire Part B ceiling
rested on. Ceiling coverage went 8 rows → **15**, and the arm mismatch of §A2
went from a live defect to a closed one.

**Three things follow, and they are the actionable part:**

1. **A dispatch instruction must name the commit.** "Work in this worktree" is
   not a specification; `git rev-parse HEAD` is. Every one of tonight's four
   agents would have measured a different tree.
2. **`git log -1 -- <artefact>` is not a substitute for a stamp *in* the
   artefact.** The provenance of `results-reconciliation.json` — commit
   `c378412f` — is recoverable from git and is not in the file. A consumer joining
   two artefacts looks at the files, not at the log. This is §A1's repair with a
   worked example.
3. **Re-run and diff is cheap and catches it.** Four probes, seconds, and the
   diff was the whole finding. Any agent whose conclusion rests on committed
   artefacts should re-run its probes after any tree movement and diff the JSON —
   not re-read the prose.

## A12. A check whose blind spot is invisible in its own output

`docs/architecture-decision-map.md`'s `V4` check compares environment variables
present in the tree against those documented in CLAUDE.md. It matches literal
`os.environ.get("OMR_X")` call sites — so **a variable whose name is held in a
module constant is dropped in silence.**

Verified in this tree, 2026-09-07:

| how counted | distinct `OMR_*` names |
|---|--:|
| literal `os.environ.get("OMR_…")` arguments | **30** |
| any `OMR_*` token in `tools/omr/` + `backend/` | **41** |
| documented in CLAUDE.md | **22** |

The dropped names are not obscure. Four are read through a constant, and two of
them matter:

```
tools/omr/measure_extractor.py:898   ENV_CELL_LINE_TRACE = "OMR_CELL_LINE_TRACE"
tools/omr/measure_extractor.py:921   ENV_ONE_LINE_STAVES = "OMR_ONE_LINE_STAVES"
tools/omr/absent_instrument.py:85    ENV_VAR = "OMR_ABSENT_INSTRUMENT_VETO"
tools/omr/offroster_name.py:91       ENV_VAR = "OMR_ROSTER_SCORE_ORDER_VETO"
```

`OMR_CELL_LINE_TRACE` is a **default-ON production flag**; `OMR_ONE_LINE_STAVES`
landed tonight. A coverage check that reports "36 in tree, 16 undocumented" reads
as an inventory and is a sample, and **nothing in its output says which**.

**Repair, and it generalises past this one check.** Any coverage check must emit
its own denominator's provenance: not "36 found" but "36 found by pattern P, and
P is known not to match forms Q". Better still, make the wider scan the primary
and the narrow one a cross-check that *fails loudly on disagreement* — the shape
`export_coverage.py`'s `unaccounted()` already has, where a name in neither table
fails the suite rather than being dropped.

## A13. A quoted ceiling for a configuration that cannot occur

CLAUDE.md's knobs table gives `OMR_CONDENSED_PARTS` an oracle ceiling of
**−4,195 scan edits alone, −4,557 with `OMR_SLOT_STITCH`**. Verified in this tree
2026-09-07: `condensed_parts` is **read** at `tools/omr/export.py:3331`
(`{int(s.get("condensed_parts") or 1) for s in staves}`) and **written nowhere in
`tools/omr/`**. Every staff therefore reports 1 and the flag is inert even when
set.

The figure is honestly labelled *oracle* in the table. What is missing is the
consequence: **the gap it names is not currently actionable**, because the
information the flag consumes is never produced. That is the mirror image of a
fabricated 100 % — it makes a shortfall look bigger than the pipeline can act on,
and it is the same defect class in the opposite direction.

It is in the registry as `flag:OMR_CONDENSED_PARTS:oracle_ceiling`,
`scoreable: false`, with the grep that establishes it. **The general rule the
registry enforces: a ceiling must name the configuration it was measured under,
and a configuration that production cannot reach makes the row unscoreable, not
merely caveated.**

## A14. Smaller things, named

- **`current-accuracy.json` has no repeat-run noise floor.** The ±6 figure
  belongs to `scan_eval`; nothing has ever measured whether `orchestral_eval` is
  deterministic. CLAUDE.md's hairpin section records detector confidences moving
  between runs on byte-identical code (0.83 → 0.69), which is the shape of a
  non-zero engraved noise floor nobody has priced.
- **`docs/progress-dashboard.content.json` still says the scan side is "a
  separate 5-page benchmark (opened 0.7960)"** in `table_caption`. The scan
  benchmark has crossed two era boundaries since. Hand-curated prose restating a
  measured figure is the exact failure `accuracy_record` was built to end — the
  cure has not been applied to the board's own captions.
- **`RATE_GREEN` / `NED_GREEN` are asserted, not derived.** Under the new unit
  they collapse to one threshold on one axis, and that threshold can then be
  argued about once instead of four times.
- **The pooled figures are recomputed from counts** in `generate.py` (correct),
  but nothing stops a future consumer averaging per-work percentages. The
  Dvořák row's excerpt auto-shrank to 3 bars, so a plain mean would weight it
  equally with a 27-staff Brahms page. `rules.pooling` makes that a schema rule.

---

# PART B — the "% of achievable" scale

## B1. The unit and the two transforms

**0-100, higher is better, on every row, in every table.**

```
error metric (lower better, natural worst W):   pct = 100 * (W - M) / (W - F)
                                       inverse:   M = W - (pct/100) * (W - F)

rate  metric (higher better, natural best 1):   pct = 100 * V / C
                                       inverse:   V = C * pct / 100
```

`W = 1.0` for OMR-NED is not a convention: predicting nothing gives
`ed = truth_symbols` over a denominator of `truth_symbols + 0`, exactly 1. The
metric has a real worst case, so the span is well defined and the transform is
reversible — the registry stores the native value beside the percentage, and
`generate.py` could print either.

`F` is the **achievable floor** of an error metric, `C` the **achievable ceiling**
of a rate. Everything interesting is in where those come from.

## B2. The independence guard, and the control that fired

> A ceiling may only be derived from an artefact **independent of our own
> output** — a truth file, a render, an external engine.

Otherwise the pipeline grades itself against its own limitations and reaches 100
by standing still. This is the decision map's provenance rule (`source_kind`)
applied to the metric instead of to a decision.

The page-normalised truth passes: `page_normalise.py` rule 2 says the merge map
is `works.json`'s `staves[i].parts`, **hand-read off the scan**, and a row
without one raises rather than guessing. Human reading of the page is
independent of our output.

**But a rule is not a measurement, so tonight I measured it.** If the structural
charge is a property of the *fixture*, an unrelated OMR engine scored through the
same bridge must be charged the same amount.
`probe_ceiling_engine_independence.py` joins our per-row
`entire staff insert/delete` against Audiveris 5.11's on the ten scan rows both
engines completed. (Our column is read from `results-reconciliation.json`, the
canonical 20-row baseline, and from `results-restamp-composed.json`; the two
agree on every row in the table.)

| row | systems | Audiveris | ours | |
|---|--:|--:|--:|---|
| beethoven-575951-p1 | 1 | 513 | 513 | identical |
| beethoven-984073-p1 | 1 | 513 | 513 | identical |
| brahms-317803-p1 | 1 | 1001 | 1001 | identical |
| dvorak-405834-p5 | 1 | 0 | 0 | identical |
| dvorak-405834-p6 | 1 | 0 | 0 | identical |
| mahler-local-p2 | 1 | 649 | 649 | identical |
| mahler-local-p3 | 1 | 1674 | 1674 | identical |
| beethoven-575951-p2 | 2 | 401 | 1551 | **differs** |
| beethoven-984073-p2 | 2 | 682 | 1551 | **differs** |
| brahms-317803-p2 | 2 | 143 | 715 | **differs** |

**Seven of ten are bit-identical between two unrelated readers.** That is what a
ceiling should look like, and it is the first time this project has evidence that
the structural charge is not its own defect.

**The control fired**, which is the part that makes it trustworthy: three rows
are *not* engine-independent, and the split is perfectly predicted by a variable
nobody chose it for — **every identical row prints one system; every differing
row prints two** (10 of 10). A multi-system page is where the two engines'
part-stitching diverges, so the charge there is partly engine behaviour and the
ceiling does not hold. Those three rows are `scoreable: false` in the registry
with that reason.

⚠️ **CORRECTED IN ROUND 2 (§R1/D5) — this paragraph originally claimed the
Dvořák rows were "corroborated three ways" (Audiveris charges 0, we charge 0, the
transform is the identity). Those are ONE FACT SEEN THREE TIMES**: 15 reference
parts map to 15 printed staves, so there is nothing to condense, so no engine can
be charged for condensation and no transform has anything to do. It is one route.
What the row genuinely provides is a CONTROL on the transform, not evidence for
the ceiling.

## B3. The assumption-direction rule — why a missing ceiling cannot flatter

> Where a ceiling is unknown it is assumed at the value that **minimises** the
> score: `F = 0` for an error metric, `C = 1` for a rate.

Both defaults are conservative by arithmetic. For an error metric,
`pct(M, 0) = 100(1−M) ≤ 100(1−M)/(1−F)` for any `F ≥ 0`; for a rate,
`100·V ≤ 100·V/C` for any `C ≤ 1`. So **no missing ceiling can ever manufacture a
high number** — the worst a gap in the evidence can do is understate progress,
which is the failure this project would rather have.

The row still says so: `ceiling.status` is one of `measured`,
`measured_and_corroborated`, `measured_unreliable`, `assumed`, `unmeasured`, and
`metric-registry.json` reports the census. (Round-1 figures; §R8 has v0.2.0's.)
Over its 48 rows at v0.1.0: **25 measured, 1 measured-single-source, 1 measured-and-corroborated, 1 measured-unreliable,
17 assumed, 3 unmeasured**.

## B4. What a ceiling actually buys, on real rows

`pct-of-achievable-prototype.json`, computed against the canonical 20-row arm.
`floor_low` is the **minimum `entire staff` charge over every engine measured on
that row** — a charge no reader avoided, so a lower bound on the floor.
`floor_high` is everything the transform removed on that row — an upper bound,
since some of that is genuine error re-attributed rather than structural charge
lifted. The score uses `floor_low`, i.e. the conservative end.

| row | OMR-NED | floor (low–high) | **% of achievable** | naive (F=0) | tier |
|---|--:|--:|--:|--:|---|
| beethoven-984073-p1 | 0.7132 | 0.276–0.336 | **39.6** | 28.7 | A |
| beethoven-984073-p2 | 0.8696 | 0.130–0.374 | **15.0** | 13.0 | B |
| beethoven-984073-p3 | 0.8706 | 0.024–0.309 | **13.3** | 12.9 | B |
| beethoven-984073-p4 | 0.9010 | 0.260–0.373 | **13.4** | 9.9 | B |
| beethoven-575951-p1 | 0.7595 | 0.276–0.354 | **33.2** | 24.0 | A |
| beethoven-575951-p2 | 0.8704 | 0.077–0.472 | **14.0** | 13.0 | B |
| beethoven-575951-p3 | 0.8811 | 0.025–0.385 | **12.2** | 11.9 | B |
| beethoven-575951-p4 | 0.8816 | 0.260–0.404 | **16.0** | 11.8 | B |
| dvorak-405834-p5 | 0.4221 | 0.000–0.000 | **57.8** | 57.8 | A |
| dvorak-405834-p6 | 0.7221 | 0.000–0.000 | **27.8** | 27.8 | A |
| dvorak-405834-p7 | 0.7133 | 0.000–0.000 | **28.7** | 28.7 | B |
| brahms-317803-p1 | 0.9184 | 0.251–0.425 | **10.9** | 8.2 | A |
| brahms-317803-p2 | 0.9424 | 0.023–0.163 | **5.9** | 5.8 | B |
| brahms-317803-p3 | 0.8930 | 0.254–0.319 | **14.3** | 10.7 | B |
| brahms-317803-p4 | 0.8653 | 0.233–0.398 | **17.6** | 13.5 | B |
| **pool A — corroborated (5)** | **0.7473** | **0.152** | **29.8** | 25.3 | |
| **pool B — all normalisable (15)** | **0.8417** | **0.134** | **18.3** | 15.8 | |
| *(5 Mahler/Bach rows)* | | | *unscoreable* | | — |

**Tier A** is engine-corroborated: the floor is bit-identical for an independent
reader. **Tier B** is measured but single-source — the *quantity* is fixed by
(reference truth, hand-read page map), both independent of us, but the
*estimator* is the minimum `entire staff` charge over the engines measured on
that row, which is our own on ten of the fifteen. A pool's trust is the minimum
of its members', so pool B is `measured_single_source` and the full 20-row
headline, which contains five rows with no map at all, falls back to `F = 0`.

Read the Dvořák rows against the Beethoven ones. Raw OMR-NED says Dvořák p6
(0.7221) and Beethoven 984073-p1 (0.7132) are almost the same page — a hundredth
apart, and the Dvořák looks marginally the better read. They are not the same
page at all: Beethoven's number is more than a quarter structural charge and
Dvořák's is *none* (15 source parts, 15 output parts, transform is the identity,
both engines charge zero), so on the achievable scale Beethoven reads **39.6**
and Dvořák **27.8**. **The ranking inverts.** That inversion is the whole
argument for the unit — and note it is not a rescaling of a ranking, it is a
correction of one.

## B5. The five design questions, answered

**1 · What may be summed.** Only rows sharing a `pool_key`, and a pool is
**recomputed from the underlying counts, never averaged from percentages**. The
schema carries `summability_class` (what kind of quantity it is) and `pool_key`
(which pool it is actually in, `null` for none). Engraved and scan get different
pool keys **by construction**, so a single blended number is not expressible —
the board's standing warning that *"a single colour per stage would be a lie"*
becomes a schema property instead of a comment. Averaging percentages is what
would have given the 3-bar Dvořák excerpt equal weight with a 27-staff Brahms
page; recomputing from counts cannot.

A pool's trust is the **minimum** of its members' `ceiling.status`. One assumed
ceiling in a pool makes the pool assumed.

**2 · How the scale carries its own trustworthiness.** Every row carries `n` +
`n_unit`, `era_key`, `noise_floor` (with its own status), `ceiling.status`,
`ceiling.evidence` (artefact paths) and `ceiling.control` (the sentence saying
what would have falsified it). A guessed ceiling is *visibly* different from a
measured one: `assumed` vs `measured_and_corroborated`, and the dashboard should
render them differently — a solid bar for measured, a hatched one for assumed.

**3 · How cross-era differencing is refused.** `era_key` is a single string
composed of (benchmark name | row-set date | row count | configuration | commit),
and two scores may be differenced **only** if their `era_key` strings are equal
*and* their `ceiling.value` and `ceiling.evidence` are equal. That is the shape
`accuracy_record.check()` already has, extended to the ceiling — because a
recomputed ceiling silently changes what 100% means, which is a second era
boundary nobody has needed yet and will.

Note what this refuses today, correctly: `scan:omr_ned` (20 rows, F assumed 0),
`scan:omr_ned:ceiling_measured_15rows` (15 rows, F 0.134) and
`scan:omr_ned:ceiling_corroborated_subset` (5 rows, F 0.152) are three rows on
one arm with three row sets and three ceilings. None may be differenced against
another, and the 18.3 → 29.8 step between the last two is **not** progress: it is
the same predictions scored against a smaller, better-evidenced pool.

**4 · A stage with no ceiling evidence.** `scoreable: false`, a `why_not`
sentence, and it renders as **"unscoreable — the harness cannot see this stage"**
— never a number. A fabricated 100 is the worst outcome available and the
`visibility` kind exists to make it impossible: twelve of the registry's 46 rows
are unscoreable, and ten of those are stages with zero information rather than
poor performance. That distinction is currently only prose on the status board.

**5 · Does it hide direction of travel.** No, and it improves it — but only with
two guards. A legitimate delta requires **all four**:

1. equal `era_key`;
2. equal `ceiling.value` and `ceiling.evidence`;
3. magnitude greater than the row's own `noise_floor` (±6 edits on the 20-row
   pool is **0.007 percentage points** pooled — but on a single row the same 6
   edits are worth ~0.5 points, so the floor must be applied *per row*);
4. `companions.edits` moving in the same direction as the ratio (§A6).

What a delta then looks like: the engraved per-work spread reads **66.2 %
(Dvořák 9) to 97.9 % (Mahler 5)** where OMR-NED reads 0.3380 to 0.0209. Sixteen
times in the ratio is thirty-two points on the scale — same information, legible
at a glance, and it does not need the reader to remember which direction is good.

## B6. Which ceilings are populated tonight, and which are empty

| kind | status | evidence |
|---|---|---|
| **structural — engraved** | ✅ **measured, F = 0** | `engraved-normalise-noop.json`: the transform is a no-op on all 11 works. A control that could have failed. ⚠️ written at transform 1.0.0 against the `no_direction_text` arm; two copies now exist (§A7) |
| **structural — scan** | ✅ **measured on 15 of 20 rows; externally corroborated on 5** | hand-read map + `results-normalised-arm-20row.json` (canonical arm, transform 1.2.0) + engine independence (§B2). Pooled floor 0.134 (15 rows) / 0.152 (5 corroborated) |
| **render** | ✅ **measured, and already enacted** | `page_truth.render_fidelity` excludes the `accidental` family; including it would read F1 **0.8982** instead of **0.9192** — 2.1 points of fixture artefact |
| **visibility** | ✅ **enumerated, 10 cells** | 5 engraved stages, 3 scan stages, from the board's own cells |
| **competitive** | ✅ **measured, both families** | engraved: Audiveris 0.1252 → **87.5 %** vs our **88.8 %**. Scan: Audiveris 0.7919 → **20.8 %** vs our 0.8345 → 16.6 % on the same 10 rows — **it is ahead of us there**, recorded not hidden |
| **input** | ❌ **EMPTY** | nothing anywhere measures how much ink is genuinely unrecoverable. 68 printed half notes, 8 then 31 detected — but no denominator of *recoverable* ink exists, so `C = 1` is assumed on every scan detector row |
| **human cost** | ❌ **EMPTY** | one incidental measurement, no harness, no ceiling (§A9) |

The `input` gap is the consequential one. Every scan detector row in the registry
— `scan:pitch` 83.4 %, `scan:duration` 75.0 %, `scan:hairpin_detect` 1.0 % — is
scored against an assumed ceiling of 1.0, i.e. against the claim that a perfect
reader could recover every symbol from a bitonal 600 dpi scan of 1870 type. That
claim is almost certainly false and nothing measures how false. **A hairpin at
1.0 % of achievable may be a catastrophe or may be near a hard ceiling, and the
registry cannot currently tell Sean which.**

---

# PART C — wiring it into the dashboard (NOT done tonight)

`tools/dashboard/generate.py` is already 80 % of the way here and I changed none
of it. What it would take:

1. **`pipeline_metrics()` reads `metric-registry.json` instead of six artefacts.**
   Today it re-derives every figure inline; the registry is the same data with a
   ceiling and an era attached. `_resolve_cell` needs no change — a registry row
   *is* a cell.
2. **`_status()` collapses from two axes to one.** `rate`/`ned` and
   `RATE_GREEN`/`NED_GREEN` become `pct_of_achievable` and one threshold pair.
   Recommend keeping the *native* value in the tooltip so nothing is lost, and
   rendering `ceiling.status == "assumed"` with a hatched bar.
3. **Unscoreable cells stay grey and gain the `why_not` sentence.** They already
   render grey; the registry supplies the reason from one place rather than from
   hand-written `detail` strings.
4. **A delta column, gated.** Show a change only when the four conditions in §B5.5
   hold; otherwise show "—" with the reason on hover. This is where the value is
   for Sean's "quick read on whether we are improving" — and where a naive
   implementation would do the most damage.
5. **Two new refusals, in the shape `accuracy_record.check()` has**: a registry
   whose ceiling evidence file is missing fails the build; a delta across
   `era_key` raises rather than rendering.

⚠️ **Do not put a single top-line number on the board.** The engraved and scan
pools have different ceilings, different noise floors and different eras; the
registry makes them un-poolable on purpose. Two numbers, always.

---

## Confidence and limits

- Every figure is read from a committed artefact; the probes are re-runnable and
  print their sources.
- **No arm was run.** The corroborated pool is 5 of 20 rows and 3 of 6 works; the
  measured pool is 15 of 20 and 3 of 6. Both are on the canonical
  `.reconciliation` arm since the 2026-09-07 landing, and neither is the
  headline.
- The `floor_low` / `floor_high` band is an *estimate*. The exact floor would be
  scored by running musicdiff with the page-normalised truth as the *prediction*
  against the raw truth — one cheap run over fifteen small files, which this
  worktree cannot do (`derived-truth/` is gitignored and absent, and there is no
  `.venv-omrned` here). That is the single measurement that would turn the scan
  structural ceiling from an estimate into a number, and it is the round-2 item
  I would rank first.
- The engine-independence result rests on ten rows and one external engine. A
  second engine, or the same engine on the 20-row era, would strengthen it.

---

# ROUND 2 — the floor measured, the input ceiling opened, and four corrections

*Run permissions widened to musicdiff scoring. `scan_eval` and `orchestral_eval`
still embargoed and not run. Four symlinks made per CLAUDE.md; `OMRNED_PYTHON`
pointed at the main checkout's `.venv-omrned`.*

New artefacts:

| file | what |
|---|---|
| `probe/probe_structural_floor.py` → `structural-floor-measured.json` | the scan floor, **measured** |
| `probe/probe_input_ceiling_from_labels.py` → `input-ceiling-from-labels.json` | can the labeling corpus supply an `input` ceiling? |
| `probe/probe_retro_stamp.py` → `retro-stamp.json` + `stamped-copies/` | the era stamp `scan_eval` does not write, proposed and demonstrated on copies |
| `probe/probe_human_cost.py` → `human-cost-identity.json` | review cost on the identity axis |
| `metric-registry.json` **v0.2.0** (v0.1.0 kept as `metric-registry.v0.2.0.json` snapshot) | 55 rows, 38 scoreable |

## R1. The corrections first

**D4 — my count was wrong and the finding survives.** I wrote that *none* of the
scan results files records the commit. `results-condensation-arm.json` carries
`git_head`. `probe_retro_stamp.py` counts them properly: **20 files, 1 with a
commit, 19 without.** The corrected sentence is the one to quote.

**D5 — the one place I failed to apply my own standard to myself.** I called
Dvořák's zero structural charge *"corroborated three ways — Audiveris charges 0,
we charge 0, and the transform is the identity."* Those are **one fact seen three
times**: 15 reference parts map to 15 printed staves, so there is nothing to
condense, so no engine can be charged for condensation and no transform has
anything to do. I audited two other agents for shared substrate and missed it in
my own paragraph. **It is one route.** What genuinely corroborates it is
different and weaker: the row is an *identity* case, so it functions as a control
on the transform (§R2), not as three-way evidence for the ceiling.

**D6 — 46 vs 48.** Stale internal count from before the `OMR_CONDENSED_PARTS` and
15-row rows landed. The registry now reports its own row count and the prose
reads it from the file.

**M3 — the noise-floor corroboration is 8 of 11, not 10, and it localises rather
than weakens.** The eleven shared rows differ by −5, +2, 0, 0, +14, +10, +3, +1,
+1, +1, +572; eight are within ±6. The two above the floor (Dvořák p5 +14, p6
+10) are both in the Tier-A pool. **That does not touch the floor**, and the
reason is the structural point of round 2: `F` is measured with **no prediction
of ours in it at all** — it is a property of (reference encoding, hand-read page
map). Arm-to-arm noise moves `M`; it cannot move `F`. So the rule is: the
noise floor is a property of the numerator, and the comparability relation pins
`F` to its own evidence separately.

**And a correction of the coordinator's that I did not inherit:**
`condensed_parts.py` is *not* an orphan module — `players_for_label` has three
benchmark importers, making it a *production* orphan (`probe` by the map's own
legend). The `condensed_parts` **field** half of §A13 stands: read at
`export.py:3331`, written nowhere, so `OMR_CONDENSED_PARTS` is inert.

## R2. The scan structural floor, measured

The definition has always been exact and nobody had run it:

> A perfect page-faithful reader emits exactly the page-normalised truth. Score
> **that as the prediction** against the raw truth, and the number is the OMR-NED
> such a reader is charged.

15 rows, all on the canonical `.reconciliation` arm. **No output of ours appears
in the measurement.**

**Three controls, and the binding was checked rather than assumed:**

- every truth fixture's sha256 equals the one `results-normalised-arm-20row.json`
  scored — **20 of 20**, and the probe refuses to run otherwise;
- all 15 derived truths reproduce the committed control's **canonical** hashes
  (`derived-truth-bytes.json`) — 15 of 15, from a different worktree on a
  different music21;
- **the three identity-transform rows score EXACTLY 0 edits.** Dvořák is 15 parts
  into 15 staves, so the transform must change nothing; if that row moved, the
  transform would be distorting the truth and no other floor would mean anything.

⚠️ **Two of my own controls were mis-specified before one was right, and both
failed loudly**, which is why they are kept in the probe rather than tidied away:
`n_output_parts == page.n_staves` (wrong — `n_staves` is summed over systems,
22 = 2 × 11; failed all ten two-system rows) and `page.n_staves // n_systems`
(wrong — a printed score suppresses tacet staves so systems are *unequal*, 11+8
and 14+13, documented in `works.json`'s own `n_staves_note`; failed exactly those
three rows). The correct assertion is one part per hand-read staff slot.

⚠️ **A byte-determinism scare I raised and then refuted against myself.** The
derived truth is not byte-reproducible — music21 stamps a fresh 32-hex instrument
id on every write, 48 differing lines per file, and two writes in one process
disagree. `derived-truth-bytes.json` asserts `writer_is_deterministic: true`, and
I was one sentence from reporting that as a false committed control. It is not:
its `_canonical()` masks exactly those ids. **What *is* worth recording** is that
`results-normalised-arm-20row.json`'s `sha.normalised_truth` is a **raw** hash and
therefore cannot be used to verify reproduction, unlike its `sha.truth` and
`sha.pred` which can.

### The floor is a ladder, and only the bottom rung is unambiguous

| rung | what it counts | pooled F |
|---|---|--:|
| **unpaired parts** | `entire staff insert/delete` — a truth PART with no printed staff | **0.2123** |
| structural | + `entire measure insert/delete` — mostly the bars inside those parts | 0.4982 |
| total | + residue (`wrong lyric`, `wrong note`, …) | 0.6348 |

**A larger floor raises every score above it**, so the ladder is climbed only as
far as the evidence is unambiguous — the bottom rung. The residue is **21.5 % of
the total floor** (9,516 of 44,226 edits), which is precisely the overstatement
the coordinator warned of, and it is excluded.

**The measurement validates the round-1 estimate on 12 of 15 rows and corrects it
on 3 — all three upward.** `floor_low` was exact on beethoven p1/p2/p4,
575951 p1/p2/p4 and every Brahms row but p2; it was too low on
`beethoven-…-p3` (0.0238 → 0.2905), `575951-p3` (0.0246 → 0.2905) and
`brahms-p2` (0.1127 → 0.2573), i.e. exactly the rows where *our own*
`entire staff` charge was anomalously small. The estimator's self-reference bit
where predicted, and in the conservative direction.

**Result:** pooled over the 15 normalisable rows, OMR-NED 0.8417 against a
measured floor of 0.2123 → **20.09 % of achievable** (round 1's estimate gave
18.28 %).

### ⚠️ THE FLOOR IS CONSTRAINED, AND THIS CORRECTS MY OWN ROUND-1 FRAMING

I called `F` "the achievable floor". It is not the metric's floor. **The metric's
unconstrained floor is ZERO** — emit the *encoding* rather than the page and
score 0. That is exactly what `OMR_CONDENSED_PARTS` would harvest, and exactly
what CLAUDE.md and the headline-validity work call an **anti-feature**: improving
the number by making the output less faithful to the page.

So the honest name for the scan unit is **“% of achievable *under page
fidelity*”**, and the constraint is declared on the row
(`ceiling.constraint`). It is not a technicality: it is the difference between a
scale that rewards Sean's stated requirement — *"the ground truth should be the
scan as it is on the page"* — and one that would quietly reward abandoning it.

## R3. The `input` ceiling — the coordinator's suggestion, taken, and it answered the sharper question

The proposal holds, with the three hazards restricting the answer rather than
voiding it. Only **one** batch in the whole corpus carries a `completion` pass
(`omr-labeling-hollow2-2026-09-breitkopf-brahms1`, 55 cells) — every other batch
is a single-symbol sweep where the rest is unboxed by instruction, so hazard (b)
alone rules out ten of eleven batches. `inspected_passes` is exactly the field
that makes that decidable.

**Noteheads, 47 usable cells, real 1876 Breitkopf scan:** a human drew **201
noteheads against 207 reference notes = 0.971**.

⚠️ **That is an upper bound, not a ceiling to score against**, and it is a ratio
of *counts*, not a matched recall: grace notes are on the page and absent from
the encoding (0 in 28,579), so human boxes are inflated and the true figure is at
or below 0.971. It is recorded `scoreable: false`,
`ceiling.status: "bounded_above"`. What it establishes is worth having anyway:
**C = 1.0 is very nearly right for noteheads on this print**, so `scan:pitch` at
83.4 % is an achievement number and not a fixture artefact.

**And the sharper question got a clean answer.** The open question was whether
`scan:hairpin_detect` at **1.01 %** is a catastrophe or a hard ceiling. Counting
human-affirmed boxes across the 55 completion cells:

| class | human boxes |
|---|--:|
| noteheadBlack (on line / in space) | 186 |
| **tie** | **62** |
| augmentationDot | 54 |
| rest8th | 39 |
| **slur** | **27** |
| **dynamicCrescendoHairpin + dynamicDiminuendoHairpin** | **17** |

**A human found seventeen hairpins on 55 scanned cells.** The ink is visible to a
reader, so 1 of 99 is a **detector failure, not missing ink** — recorded as
`ceiling:input:hairpin:scan`, `status: "refuted_as_a_ceiling"`. The same sweep
drew 62 ties and 27 slurs, the other two families a fine-tune is documented to
delete to zero.

⚠️ Incidental, and someone else's to act on: those human boxes use
`dynamicLetterF`/`dynamicLetterP`/`dynamicLetterS` — the **coarse** spelling
CLAUDE.md records the exporter cannot read (`class_aliases.py`,
`COARSER_THAN_CANONICAL`). 26 boxes in this batch.

## R4. M2 — comparability is not one relation

The round-1 rule (`era_key` equality) **forbade the competitive comparison this
document prints.** We and Audiveris can never share an era key and are exactly
comparable on the same fixtures through the same scorer. Fixed in the schema:

| relation | condition | answers |
|---|---|---|
| `comparable_as.time_series` | equal key **and** equal `ceiling.value`/`evidence` **and** same arm | *are we improving?* |
| `comparable_as.head_to_head` | equal key — same fixtures, same scorer, same row set, **different system** | *are we better than them?* |
| neither | — | may not appear in one sentence with an arrow between them |

Worked: `engraved:omr_ned` **88.78** and `competitive:engraved:audiveris`
**87.48** share a head-to-head key and no time-series key — a valid head-to-head,
**not** a delta. `scan:omr_ned` and `scan:omr_ned:page_fidelity_15rows` share
neither.

## R5. M1 — three estates the round-1 registry omitted

**Calibration: `scoreable: false`, and forcing it would be the very defect this
unit exists to remove.** `pct = 100·(W−M)/(W−F)` needs a defensible **worst
case**. OMR-NED has one — predict nothing, score exactly 1. ECE does not: its
arithmetic maximum is 1.0, unreachable and meaningless, so a percentage against
it would be a number with no referent. A third transform kind would need an
*empirical* worst case (the ECE of a constant predictor on this corpus) that
nobody has measured. And the estate's own finding argues against scoring it at
all: ECE 0.1277 → 0.0204 across n=197 → 1571 is **not** calibration (Brier skill
vs a constant predictor +0.0004, 95.8 % of mass in one bin). Recorded with that
reason.

**The ledger-zone audit — the confusion Sean commissioned this unit to fix, live,
and the best demonstration available.** The parity auditor flags **7 of 102
(6.9 %)**; hand adjudication found **one** real error (**0.9 %**). A 7× gap, both
reported as percentages, in a project where 1.000 is sometimes the target and
sometimes a disaster.

The registry's answer is that these are **two rows and never one**:

| row | value | scoreable | why |
|---|--:|---|---|
| `labeling:ledger_zone:screening_rate` | 6.9 % | **false** | a SCREEN. It is a workload figure — how many candidates a human must adjudicate — and it is never an achievement number. |
| `labeling:ledger_zone:defect_rate` | 0.98 % | **true → 99.02 %** | a DEFECT rate, F = 0 assumed (a perfect pass has no defects). |

A dashboard printing either alone is wrong in a *named direction*: 6.9 %
overstates the defect sevenfold; 0.9 % understates the reviewer's workload
sevenfold. The defect row carries a flag requiring the screen beside it.
**A screening number and a quality number are different KINDS, and the unit's
job is to make a screen visibly unscoreable rather than to rescale it.**

**Pre-fill precision — and the most useful ceiling kind in the registry.**
`prefill:precision:blind_out_of_sample` is 0.915 against a ceiling of **0.97**
whose `status` is `pre_registered`: the admission bar was set *in advance*, the
cells were pre-registered at seed 20260903 with their status recorded before
labeling, and the pass was run blind. **94.33 % of achievable — and the control
fired**: the measurement came in under the bar and pre-filled verdicts stayed a
queue rather than becoming labels. This is a ceiling that is a *decision rule*
rather than a physical limit, which is the right kind for anything gated on human
trust, and it is the only pre-registered ceiling in the registry.

## R6. Item 2 — the era stamp, proposed and demonstrated on copies

`probe_retro_stamp.py`. **Nothing in `tools/omr/` or
`benchmarks/omr-scan-e2e-2026-09/` was modified**; twenty stamped copies are
written to `stamped-copies/` so the shape can be reviewed against the originals.

The stamp mirrors `accuracy_record`'s `benchmark` block: `name`, `since` (the
date the ROW SET last changed), `rows` (the ids, in order), `n_rows`, `commit`,
`arm` (which predictions), `flags` (the `protocol` block already written), and
the note saying a figure under a different row set is not a comparison. It needs
a `SCAN_ROWS` constant in code plus a `check()` that refuses a file whose
`benchmark.rows` disagrees — the exact mechanism that stops the engraved headline
crossing an era silently.

**The wasting asset is confirmed and still intact: 20 of 20 commits are
recoverable from `git log` today.** Four row-set eras live in one directory —
1 row (1 file), 5 rows (14), 11 rows (4), 20 rows (1) — distinguishable today
only by `len(rows)`.

⚠️ **A retro-fitted commit is weaker than a recorded one and the copies say so**
(`commit_source: "RETRO-FITTED … NOT recorded at measurement time"`).
`git log -1 -- <path>` gives the commit that last *touched* the file, which
equals the measurement commit only for a file committed once. `since` is left
`null` for a human to set: the date a row set changed is a decision, not a
derivation.

## R7. Item 3 — human review cost: measured, and it does not reproduce

`probe_human_cost.py`, over the committed `records.json` (1,571 records, 2 arms).
Definition taken from the harness rather than invented: a staff record costs a
human if it is **unnamed** or **contradicted by its own margin label**.

**It does not reproduce the project's only figure, and that is the finding.**
FINDINGS.md reports 197 over 3,543 records in four categories (150 contradicted-
only, 24 unnamed, 15 not-in-this-work, 8 both). The committed export holds 1,571
records in two arms, has **no `not-in-this-work` field** and **zero unnamed
records** (0 of 1,571). Only the `contradicted` component re-derives: **26 of
1,571 = 1.66 %**.

> The project's stated purpose is measured in exactly one place, and that place
> cannot be re-derived from the tree.

⚠️ **And its floor is open, not zero.** By this definition the floor computes to
**0**, which would say a perfect pipeline leaves a reviewer nothing to do —
contradicting the identity scope's own claim. The floor a `% of achievable` needs
is *staves unnameable from the page*, which requires the label-evidence channel
recorded per record — the same gap backlog §F names for clefs.

Recorded `scoreable: false` with the reproducible partial as a companion. **Not
scoring it is the right answer tonight and the wrong answer for the project.**

## R8. Where the numbers stand after round 2

| row | value | ceiling | **% of achievable** |
|---|--:|---|--:|
| `engraved:omr_ned` | 0.1122 | structural, measured, F=0 | **88.78** |
| `competitive:engraved:audiveris` | 0.1252 | head-to-head | 87.48 |
| `reading:POOLED` | F1 0.9192 | assumed C=1, render excluded | **91.92** |
| `scan:omr_ned` (20 rows) | 0.8444 | assumed F=0 | 15.56 |
| `scan:omr_ned:page_fidelity_15rows` | 0.8417 | **structural, measured directly, F=0.2123** | **20.09** |
| `scan:omr_ned:ceiling_corroborated_subset` (5) | 0.7473 | corroborated, F=0.152 | 29.80 |
| `competitive:scan:audiveris` (10 rows) | 0.7919 | head-to-head | 20.81 |
| `prefill:precision:blind_out_of_sample` | 0.915 | **pre-registered C=0.97** | **94.33** |
| `labeling:ledger_zone:defect_rate` | 0.0098 | assumed F=0 | 99.02 |

Ceiling census over 55 rows: 25 measured, 1 measured-directly, 1 corroborated,
1 single-source, 1 bounded-above, 1 refuted-as-a-ceiling, 1 pre-registered,
1 measured-unreliable, 1 not-a-defect-rate, 18 assumed, 4 unmeasured.
**38 scoreable, 17 not.**

## R9. What round 2 did not do

- **The `input` ceiling has a bound for noteheads and a refutation for hairpins;
  it still has no VALUE for any class.** Pairing human hairpin boxes to the
  reference's `<wedge>` positions on the same bars would give one, and the data
  is on disk.
- **One batch, one publisher.** The completion-pass corpus is 55 cells of
  Breitkopf Brahms. The other ten batches could each be given a completion pass
  cheaply — `inspected_passes` already makes coverage provable.
- **The five Mahler/Bach scan rows still have no floor**, because they have no
  hand-read staves map (backlog §A2's 57-slot confirmation pass would close four
  of them).
- **No delta was measured**, because measuring one needs an arm and arms are
  embargoed. Everything above is a level, not a direction.
- **`orchestral_eval` still has no repeat-run noise floor**, so no engraved row
  can carry one.

---

# ROUND 3 — a ceiling with a value, the purpose on the board, and two self-corrections

*`orchestral_eval` and `scan_eval` still embargoed and not run. musicdiff used
only where round 2 already used it.*

New artefacts: `probe/probe_hairpin_ceiling_value.py` →
`hairpin-ceiling-value.json`; `probe/_fixtureroot.py` (the shared guard);
`RUNBOOK-completion-passes.md`. `metric-registry.json` is now **v0.3.0, 55 rows,
39 scoreable**.

## S1. Corrections folded in

**The coarse-spelling incidental is CLOSED, not stale-and-dropped.** Verified
here: `class_aliases.ALIASES` maps `dynamicLetterF/P/S → dynamicF/P/S`, and the
module's docstring names this very campaign as the reason. The 26 boxes are
readable by the exporter. My round-2 note is withdrawn.

**The `sha.normalised_truth` defect is carried into the stamp as a REQUIREMENT.**
It is a defect in an existing artefact, not in my work, and the general form is
the useful part: *a stamped hash must be able to verify what it appears to
verify.* Raw sha256 for a byte-stable **input**; a **canonical** hash for
anything a writer re-randomises; and the stamp must say which kind it is. A hash
that cannot verify is worse than none, because it invites a check that silently
always fails.

**My own probes had the silent-fail hazard — three of them.**
`probe_input_ceiling_from_labels.py`, `probe_measurement_hygiene.py` and
`probe_retro_stamp.py` all globbed a directory and would have printed a clean
all-zero table at exit 0. `probe_structural_floor.py` carried a hard-coded
absolute path. The endorsed fix is applied in `probe/_fixtureroot.py`:
`OMR_FIXTURE_ROOT`, and `require_nonempty()` which exits **3** naming the path
and the pattern. Verified firing: a wrong fixture root exits **2** (the sha gate)
and an empty fixture directory exits **2**; all nine probes exit 0 on the real
tree. ⚠️ Checking the exit code through `| tail` reports 0 regardless — the same
trap CLAUDE.md records for git.

## S2. Item 1b — the matched comparison, and it is worse than the corpus rate

The refutation compared a human against a **corpus-level** 1-of-99 over eleven
pages. What the detector found on *those* cells was never asked. The batch
carries the pipeline's own read of the same three pages
(`transcription.json`), so the question is answerable directly:

| on the same three pages | count |
|---|--:|
| detections the pipeline made, all classes | **10,523** |
| of those, `dynamicCrescendoHairpin` + `dynamicDiminuendoHairpin` | **0** |
| hairpins a human drew across 55 completion-swept cells | **17** |

**Zero of 10,523.** The 1-of-99 is not a thin-sample artefact: on this edition it
is zero, on pages where the detector was otherwise productive.

⚠️ A page-level zero entails a per-cell zero, which is why no per-cell join was
needed. Had it been non-zero the join would have been required, and the probe
says so rather than leaving the shortcut implicit.

⚠️ Incidental, and it is a different fault from the one being measured: the
batch's own `detections/` are **56 files, 0 detections** — it was labeled
draw-from-scratch, so the batch cannot answer this question and the
transcription had to.

## S3. Item 1 — the ceiling has a value, and the obvious form of it is unusable

`reference.mxl` gives the encoding's hairpins in exactly the swept bars. Three
units are in play and conflating them is the whole trap:

- **encoding** — MusicXML writes a `<wedge>` at *each end*, so wedge STARTS are
  counted and one printed hairpin is one unit;
- **page** — the engraver draws one arc;
- **cell** — a measure cell *cuts* it, so one hairpin crossing a barline becomes
  **two** human boxes.

The naive ratio is therefore junk and is reported as such: **17 human boxes
against 11 reference starts = 1.545**, biased upward by barline cuts *and* by
multi-bar hairpins (one start drawn across three cells), against a reference
count biased downward for the same reason. Two biases, opposite directions,
neither quantified.

**The defensible form is bar-level, where there is no unit mismatch:**

> Of the swept bars where the encoding STARTS a hairpin, in how many did a human
> find hairpin ink? **4 of 5 — a human bar recall of 0.80.**

⚠️ **n = 5.** That is the entire sample the corpus can offer: one batch has a
completion pass, and only five of its 55 swept bars carry a reference hairpin
start. It is a bound worth having and not a point estimate worth quoting to three
places.

**What it licenses is exactly the conversion the coordinator asked for.**
`ceiling:input:hairpin:scan` moves from `refuted_as_a_ceiling` to
`bounded_below`, value **0.80**: the detector sits at ~0.01 of a ceiling that is
at least 0.80 — **roughly one part in eighty of what a reader recovers.** That is
a ceiling, not a refutation. The other 12 human boxes fall in bars the encoding
starts no hairpin in; they are continuations and barline cuts, not false
positives.

⚠️ **Quoted with the publisher named, every time: Breitkopf & Härtel, Brahms 1
mvt 1.** The single-edition limit is irreducible today, and the registry row and
the probe both carry that sentence.

## S4. Item 4 — human review cost is on the board, and my round-2 negative was wrong

**Withdrawn.** Round 2 reported that human cost "cannot be re-derived from the
tree" because `records.json` carries no `impossible` or `not-in-this-work` field.
**It does not need to.** `score.py` derives both from
`corpus.is_impossible(work, page, name)` and `corpus.is_never(work, name)`;
`work`, `page` and `emitted` are all on the record; and `corpus.py` is committed.
The fields were absent — **the information was not.** I checked which fields
existed and did not check how the missing ones were computed, which is a shallower
version of exactly the failure this audit keeps finding elsewhere.

Recomputed from committed artefacts alone, over 1,571 records in 2 arms:

| | records |
|---|--:|
| unnamed | 0 |
| impossible | 7 |
| not-in-this-work | 17 |
| contradicted | 26 |
| **costing a human (union)** | **46 of 1,571 = 2.93 %** |

**The Brahms 17 `not-in-this-work` reproduces the documented `Trombone → Tuba`
×17 residue exactly**, which is the corroboration that the recomputation matches
the harness rather than merely resembling it.

`human:review_cost:identity` is now **scoreable: 97.07 % of achievable**, with
`W = 1.0` (a pipeline that names nothing leaves every staff to the reviewer —
real, not a convention) and `F = 0` assumed and conservative.

⚠️⚠️ **AND IT CARRIES THE LOUDEST FLAG IN THE REGISTRY, because a 97 beside a
scan 20 is the most misleading pairing the board could print.** This scores staff
**naming**. The reviewer's larger load is note-level diffs and has **no harness
at all**. A high number here must never be read as "review is nearly free". If
only one caption survives to the dashboard, it is this one.

**And the floor is no longer merely open — it is LOCATED.** Zero records are
unnamed, so the floor is not there. It is in `contradicted`: the
label-contradiction check's documented structural false positive is a **condensed
staff** — `Violoncello e Basso` names one instrument in the margin and the slot
names the other and *both are right* — and that costs a reviewer a look no
pipeline work removes. Neither edition here condenses that way (0 of 158 in the
label-contradiction study), which is a fact about two publishers, not about the
floor. So the floor is measurable, has a name, and is not zero.

**What is still true from round 2**: 46 here cannot be FINDINGS' 197, because the
committed export is **2 of the harness's 59 arms**. That is a **coverage** gap,
not a schema gap — no harness change is needed, only more arms exported.

## S5. Item 2 — scoped, not attempted

`RUNBOOK-completion-passes.md`. The finding that shapes it: **the blocker is not
labeling effort.** Ten batches were swept for one symbol each and a completion
pass on any of them yields human boxes — but **not a ceiling**, because a ceiling
needs *human boxes vs what the encoding says is in those bars*, and only the
Brahms batch has a `reference.mxl`, a `prefill/` and a hand-confirmed window map.
Nine of ten lack all three, and every batch has **0 cell PNGs** (gitignored;
`recut_cells` is step 0, and its abort-on-frame-mismatch is a safety property not
to be flagged past).

Recommended first: **`hollow2-2026-09-peters-mahler5`** (different house,
different engraving weight, work in the reference library — ⚠️ confirm the
movement, the library holds mvts 1–3 and one existing batch is the Adagietto),
then `hollow3-2026-09-durand-lamer`. **Two editions disagreeing is the more
valuable outcome and the likelier one**: it would make the `input` ceiling a
property of the EDITION, and every scan detector percentage would need a
per-edition ceiling — the same lesson `OMR_WEIGHT_ROUTING` already learned about
weights.

## S6. Item 3 — stamp: proposal only, unchanged, plus the hash requirement

Nothing in `tools/omr/` touched. `stamped-copies/` holds twenty demonstrations.
The wasting asset is re-confirmed intact at **20 of 20** commits recoverable. The
`fixture_sha` requirement from §S1 is now part of the proposed shape.

## S7. Item 5 — the arm I would like authorised

**Shape:** `orchestral_eval --omr-ned` run **twice on one unchanged tree**, same
work set, same configuration, no flags differing; compare per-work `omr_ed`.
**Question:** is the engraved harness byte-deterministic, as the scan harness was
measured to be on its five-row era and measured *not* to be on its twenty-row
era (±6)?

**Why it matters more than it sounds.** `current-accuracy.json` carries no noise
floor, so **no engraved row in the registry can gate a delta** — condition 3 of
§B5.5 is unsatisfiable for eleven works. And there is positive reason to expect a
non-zero floor: CLAUDE.md records detector confidences moving between runs on
byte-identical code (0.83 → 0.69 on one Mahler hairpin), with the note that a
from-scratch rebuild reproduced a categorical result but *not* the pooled edit
count.

**Cost:** two full runs. I do not know the wall time and will not guess; the
committed rows carry `seconds` per row for `scan_eval` but `orchestral_eval`'s
are not in `current-accuracy.json`. **Cheaper alternative if the full pair is too
expensive:** two runs over `--works mahler-sym5-mvt1 brahms-sym1-mvt1` only — the
work with the known confidence jitter and the work with the most detections —
which would establish whether the floor is non-zero without pricing it for the
pool. I would take that as the first cut.

## S8. Where the numbers stand after round 3

| row | value | ceiling | **% of achievable** |
|---|--:|---|--:|
| `human:review_cost:identity` ⚠️ naming only | 2.93 % cost | assumed F=0, floor located not measured | **97.07** |
| `labeling:ledger_zone:defect_rate` | 0.98 % | assumed F=0 | 99.02 |
| `prefill:precision:blind_out_of_sample` | 0.915 | **pre-registered 0.97** | 94.33 |
| `reading:POOLED` | F1 0.9192 | assumed C=1, render excluded | 91.92 |
| `engraved:omr_ned` | 0.1122 | structural, measured, F=0 | **88.78** |
| `competitive:engraved:audiveris` | 0.1252 | head-to-head | 87.48 |
| `competitive:scan:audiveris` (10 rows) | 0.7919 | head-to-head | 20.81 |
| `scan:omr_ned:page_fidelity_15rows` | 0.8417 | structural, measured, F=0.2123 | **20.09** |
| `scan:omr_ned` (20 rows) | 0.8444 | assumed F=0 | 15.56 |
| `scan:hairpin_detect` | 1.01 % | **bounded below at 0.80** (Breitkopf) | 1.01 |

**Ceiling census, 55 rows** (generated — `metric-registry.json` `coverage`):
25 measured · 1 measured-directly · 1 corroborated · 1 single-source ·
1 bounded-above · 1 **bounded-below** · 1 pre-registered · 1
measured-unreliable · 1 not-a-defect-rate · 19 assumed · 3 unmeasured.
**39 scoreable, 16 not.**

## S9. What round 3 did not do

- **No delta measured.** Everything is a level. Gating a delta needs §S7.
- **The `input` ceiling remains one edition** for both classes it touches.
- **`scan:pitch` and `scan:duration` still carry assumed ceilings.** The notehead
  bound (≤ 0.971) is close enough to 1.0 that assuming C=1 is nearly harmless
  *for that class on that print*; nothing licenses it for durations.
- **The five Mahler/Bach scan rows still have no structural floor.**
- **Nothing was wired into the dashboard**, per the standing instruction.

---

# ROUND 4 — the authorised arm, and the caption made structural

## T1. The engraved noise floor: **ZERO, and byte-identical rather than equal-scoring**

Authorised in the cheaper form and run in exactly that form:
`orchestral_eval --omr-ned --no-direction-text` over `mahler-sym5-mvt1` and
`brahms-sym1-mvt1`, twice, **serially**, on one unchanged tree, each arm in its
own `--work-dir`. Recorded in `engraved-noise-floor.json`.

| | arm A | arm B |
|---|---|---|
| load (1-min) before launch | **4.97** | **3.57** |
| wall clock | **415 s** | **270 s** |
| `mahler-sym5-mvt1` | 0.0209 / **40 edits** | 0.0209 / **40 edits** |
| `brahms-sym1-mvt1` | 0.1292 / **518 edits** | 0.1292 / **518 edits** |

Both loads were under the ~6 hold threshold; neither arm was held.

**The anti-cache control, four ways, because two identical numbers from an arm
that never ran is the worst possible way to report a zero:**

1. **Wall clock differs** — 415 s vs 270 s. A cached arm returns in seconds.
2. **The pipeline's own `runtime` differs per work** — Mahler `total_s` 341.9 vs
   206.7, with `contextual_s` 284.9 vs 160.5 as the dominant term. Recorded
   *inside* each arm's `.omr.json`, so it is not my stopwatch.
3. **`orchestral_eval` has no cache guard** — verified by reading `run_work`,
   which calls `excerpt()` and `transcribe()` unconditionally. There is no
   `if pred.is_file() and not force: return` of the kind `scan_eval.run_pipeline`
   opens with. That difference between the two harnesses is worth knowing on its
   own.
4. Separate `--work-dir`s, so neither arm could see the other's files.

**Why the result is stronger than "the scores matched":** the exported
`.omr.musicxml` is **byte-identical** for both works, and every detection
confidence agrees — 971 and 1,725 detections, confidence sums identical to six
decimal places. So this is not two different reads that happened to score the
same; it is the same read.

⚠️ **What it does NOT license.** n = 2 works, direction text OFF, one tree, one
machine. **A floor is a property of the POOL as much as of the pipeline** — the
scan harness measured exactly 0 on its five-row era and ±6 on its twenty-row era.
So `engraved:omr_ned` now carries
`noise_floor.status = "measured_on_a_2_work_subset"`, and **a delta on the
eleven-work row still may not be gated.** The full arm is now worth scheduling
rather than guessing at: it would cost roughly 11/2 × 400 s ≈ 35 min per arm at
this load, twice.

⚠️ **And it says nothing about the DEFAULT configuration.** Direction text is on
by default and Surya's nondeterminism is a separate documented lead; that arm's
floor is unmeasured and is ≥ this one.

### A fixture non-determinism found on the way, and closed

The Mahler **truth** fixture differed between arms and Brahms's did not — which
would mean the two arms scored against different truths and the identical score
was luck. It is not: the difference is entirely music21's random ids. My first
canonicaliser masked only `"I…"` (`<score-instrument>`, `<midi-instrument>`) and
Mahler's truth also carries `<score-part id="P…">`. Widened to `"[IP]…"`, **both
truths are identical across arms.**

⚠️ **The same narrow mask is in the committed control.**
`benchmarks/omr-page-normalise-fixes-2026-09/probe_derived_truth_unmoved.py::_canonical`
masks `"I[0-9a-f]{32}"` only. Measured: across the 15 derived truths there are
**840 `I`-ids and 0 `P`-ids**, so it is **correct today and latently fragile** —
a derived truth that ever carried a `<score-part id="P…">` would break its
reproduction check silently. Not a defect; a hazard with a location. It sharpens
the round-3 stamp requirement: *a canonical hash must mask every id family the
writer randomises, and say which it masked.*

## T2. The caption is now a schema constraint, not a rendering convention

`rules.mandatory_caption` in **v0.3.0**, with `mandatory_caption` in the row
skeleton so it cannot be forgotten:

> A row carrying a non-null `mandatory_caption` **must** be rendered with that
> text visible beside the number — not in a tooltip, not on hover, not behind a
> disclosure. **A renderer that cannot show it must not show the row.**

Enforcement is on the schema, not the renderer: *if the renderer can drop the
caption, the schema is wrong.* A consumer that omits captions should fail its own
build rather than degrade silently. `build_metric_registry.py` raises if a
caption is set on an unscoreable row or is empty.

Three rows carry one today:

| row | caption |
|---|---|
| `human:review_cost:identity` | Staff **naming** only. The reviewer's larger load — note-level diffs — has no harness at all, so this is not a measure of how much review a score needs. |
| `engraved:structure` | These fixtures are 1:1 **by construction**; a conductor's page condenses and splits and this stage is never asked that question here. |
| `scan:hairpin_detect` | Scores the **detector** only; a classical-CV reader added later carries 118 of 198 `<wedge>` into the file. |

The case that forced it: 97.07 beside 15.56, in one unit, on one axis, in one
table, where the first scores naming and the second scores everything. **The
mistake is not made in the renderer**, which is why the fix is not in the
renderer. Handed to Fix Agent C with v0.3.0.

## T3. The runbook's first paragraph now says the expensive thing

Per the coordinator, the reframing is at the top, before anyone can skim past it:
**the ask is not more labeling, it is more PAIRED labeling.** A completion pass
yields human boxes; a ceiling needs those boxes measured against what the
encoding says is in those bars, which needs a `reference.mxl`, a `prefill/` and a
hand-confirmed window map. Only the Brahms batch has all three; nine of ten have
none. *A weekend spent completing the other nine batches without step 1 produces
~5,000 human boxes and zero ceilings.*

## T4. On the withdrawal — what actually saved it

Stated as the coordinator asked, because the distinction is the one this audit
has been enforcing on everyone else all night.

My round-2 negative ("human cost cannot be re-derived from the tree") was wrong,
and the thing that caught it was **not** a second look at the same artefact. It
was the recomputed Brahms **17 `not-in-this-work`** matching the independently
documented **`Trombone → Tuba` ×17** residue — a prior result, from a different
session, produced for a different purpose, arrived at by a different route.

Re-reading `records.json` would have shown me the same absent fields a second
time and confirmed me in the same error. **Corroboration by an independent prior
result is worth more than any number of confirmations from the substrate that
produced the claim** — which is exactly the standard
`feedback_corroboration_is_not_evidence` records, now demonstrated in my own
favour rather than against someone else's.

## T5. Where round 4 leaves the estate

- `metric-registry.json` **v0.3.0** — 55 rows, 39 scoreable, `mandatory_caption`
  on 3, `rules.mandatory_caption` enforced at build time.
- `engraved:omr_ned` is the **first row in the registry with a measured noise
  floor** (0 edits, 2-work subset). It still cannot gate a delta at pool scale,
  and the row says so.
- **Nothing in `tools/omr/`, `backend/` or `frontend/` was modified**, in any
  round.
- Ten probes, all exit 0 on the real tree; the four that glob refuse with a
  non-zero exit on an empty one.

(§T6 below was found after this section was written and is appended rather than
folded in, because the order it was discovered in is part of the finding.)

**What is still unmeasured, ranked:** the eleven-work noise floor (now cheap to
schedule and worth it); the same for the default direction-text configuration;
the `input` ceiling on a second edition; the condensed-staff rate that would give
human cost a floor; and the 57 remaining harness arms whose export would let the
project's own purpose be scored on more than two.

## T6. ⚠️ A committed control's hash reproduces on exactly one day — found live, tonight

My structural-floor probe passed its reproduction control **15 of 15 on
2026-09-06** and **0 of 15 on 2026-09-07**, on unchanged code, unchanged inputs
and an unchanged transform. The session crossed midnight.

`benchmarks/omr-page-normalise-fixes-2026-09/probe_derived_truth_unmoved.py::_canonical`
masks music21's random `"I…"` ids and hashes everything else — including
`<encoding-date>`, which music21 stamps **from the clock**. So
`derived-truth-bytes.json`'s canonical hashes are reproducible on the day they
were written and on no other day.

**The proof is exact**: re-inserting `<encoding-date>2026-09-06</encoding-date>`
into my freshly written derived truths reproduces the committed hash
`50e21c5b1aa978ef` **byte for byte, on all 15 rows.** Not "close" — identical.

**Why this is worse than a nuisance.** That control's job is to say *"the
transform did not move."* From today on it says the opposite, loudly and
falsely, and the next person to run it will read a 0-of-15 failure as evidence
that `page_normalise` changed. A control that cries wolf on a schedule is worse
than no control, because it will be believed once and then disabled.

**It is the third instance tonight of one family**, which is why it belongs in
the stamp requirement rather than in a bug list:

| # | artefact | the hash | what it cannot verify |
|---|---|---|---|
| 1 | `results-normalised-arm-20row.json` `sha.normalised_truth` | **raw** sha256 of a re-randomised file | anything — it can never match |
| 2 | `_canonical`, id mask | masks `"I…"` only | a `<score-part id="P…">`; 840 `I`-ids and 0 `P`-ids across the 15 derived truths today, so **correct today, latently fragile** |
| 3 | `_canonical`, date | does not mask `<encoding-date>` | **any day but the day it was written — live now** |

**The general rule, and it is the sharpened form of §S1's requirement:**

> A canonical hash must mask **every field the writer derives from its
> environment** — every random id family *and* the clock — and the stamp must
> **say which it masked.** A hash that silently depends on the wall clock is a
> provenance field that becomes a false alarm on a timer.

My own probe now masks both id families and the date, and additionally records
`reproduces_without_redating` (0 of 15) beside
`derived_truth_reproduces_committed_control` (15 of 15, re-dated to
2026-09-06) — so the finding is in the artefact and not only in this prose.

⚠️ **I did not modify the committed control.** It is not mine and `tools/` and
other agents' benchmarks are read-only tonight; the fix is a two-line change to
`_canonical` and belongs in its own review, alongside the `[IP]` widening.

**And it retro-justifies the round-2 near-miss.** In round 2 I was one sentence
from reporting `derived-truth-bytes.json`'s `writer_is_deterministic: true` as a
false claim, checked `_canonical`, found it masked the ids, and withdrew. That
was right. It also means I read that function and did not notice it hashes a
timestamp — the same shape as the round-3 human-cost error: I checked the thing I
suspected and not the thing beside it.


---

# ROUND 5 — the registry defects I found in my own file, fixed

Reviewing the renderer surfaced four faults in `metric-registry.json`, three of
them mine. **Fixed and frozen at v0.4.0; the renderer was not touched.**

| # | fault | fix |
|---|---|---|
| 1 | **One-sided `head_to_head`.** `engraved:omr_ned` carried a key; `competitive:engraved:audiveris` carried **no `comparable_as` at all** — a round-2 patch of mine silently did not apply. The pair had one member, so a renderer grouping on the key found nothing and fell back to grouping on `ceiling.kind == "competitive"`. | Both keys declared **once**, as `H2H_ENGRAVED` / `H2H_SCAN`, so the two sides cannot drift apart. |
| 2 | **The scan comparison had no second side.** Audiveris covers 10 rows of the retired 11-row era and the registry held no counterpart, so a renderer could only print `ours —`. ⚠️ Pairing it with the 20-row headline would have been a **false head-to-head across row sets**. | Added `scan:omr_ned:same_10_rows_as_audiveris` (0.8345, the figure the industry arm itself computed over exactly those rows), captioned as not-the-headline. |
| 3 | **`prefill:precision:blind_out_of_sample` was `ceiling.kind = "competitive"`.** It is a bar a human set in advance, not another system — which is how it got filed under a heading reading *"different system"*. **A category error in the data, not the renderer.** | New kind `decision_rule`, and `competitive` now documents that it means another system and nothing else. |
| 4 | **`ceiling.edition` was a field a consumer could simply not read** — and one did, so `Breitkopf` appeared **zero times** on a rendered page, against a standing rule that the hairpin ceiling is always quoted with its publisher. | **The edition clause**: any row whose `ceiling.edition` is set must name that edition in its `mandatory_caption`, enforced at build time. |

**The generalisation, which is the part worth keeping:** *a fact that must always
travel with a number belongs on the mechanism that cannot be dropped, not in a
field a consumer may not know about.* Fault 4 is fault 1 of the renderer review
seen from the data side.

**Three build-time guards, each mutation-tested red before being trusted:**

| guard | mutation | result |
|---|---|---|
| edition clause | replace `Breitkopf` in the caption | exit 1, names the row |
| caption non-empty | set a caption to `"   "` | exit 1, names the row |
| **one-sided head-to-head** | delete one side's key | exit 1, names the key and its lone member |

⚠️ The third is the one that matters most: **that defect survived two review
rounds because nothing checked it** — it was found only by reading a rendered
page. A registry that can be built with a one-sided key is a registry whose
comparability rule is advisory. It is now refused, with the reason: *a key with
one member is not a weaker comparison, it is a false claim that one exists.*

**Also relaxed, because the first version was wrong:** an **unscoreable** row may
carry a `mandatory_caption`. It still renders — as an explicit
`unscoreable — <reason>` — so its scope can still mislead.

**`consumer_contract` added** so a version gate has something to gate on: the
current version, the versions a conforming consumer understands, what each
superseded version drops, and the fields that may never be dropped.

**Stability:** the registry is **byte-identical across two builds**, all ten
probes exit 0, and nothing outside `benchmarks/omr-pipeline-audit-2026-09/` was
modified in any round.


---

# ROUND 6 — reviewing the rebuilt renderer, and the four defects it found in me

## U1. Priority one: no merged byte-identity claim rested on an empty comparison

`compare_arms.py` did have the defect — `for xml in sorted(before.glob(...))` over
an empty arm leaves `failures = 0` and prints `RESULT: PASS` at exit 0, *the
cached-A/B shape inside the instrument written to detect it.* **All three merged
claims are nonetheless sound**, and the check is not "the numbers look plausible":

- **Per-page lines can only print inside the loop body.** The serialise and
  cell-pad records carry them with byte counts (`64,552 B`, `165,617 B`) and the
  cell-pad record additionally carries per-staff structure counts
  (`21 / 147 unchanged`, `12 / 192 unchanged`) — all emitted from inside the
  loop. An empty run emits none of it.
- **The barline branch verified with `md5`, not with the comparator**, recording
  `89d8a316330a9fb29df7c4a89dd1e08a (64552 bytes)` and
  `d46bcb45cb1b8a56322e7f36e335aa76 (165617 bytes)`.
- **Those hashes match the artefacts a DIFFERENT branch committed.** I ran `md5`
  over `benchmarks/omr-serialise-evidence-2026-09/arm-after/` and got both
  values exactly.

**Two independent branches, two independent runs, converging on the same two
hashes.** An empty comparison cannot produce an MD5, and two empty comparisons
cannot agree on one. No re-run needed. ⚠️ What this establishes is that the
comparisons were *non-empty*; the byte-identity itself is corroborated by the
independent `md5` route rather than re-derived.

## U2. The renderer: APPROVED, and rule 1 verified at layout level

The rejection is encoded as a check: **no row identifier appears anywhere in the
828-line module** (verified against all 56 ids), and the only instance-shaped
string, `Breitkopf`, occurs three times — all in comments explaining the failure.
It solved the class.

**Rule 1, the one that sank the first build, verified in a real browser** — and
not by DOM assertion, which is what I criticised last time. For all five caption
rows: caption **and** its number each `elementFromPoint`-hit-test to themselves
(a hit test is a query against rendered, unoccluded layout), both on screen
simultaneously, same left edge, 20–38 px apart, 1010 px wide, `insideDetails:
false`, opacity 1. ⚠️ The browser pane's screenshot came back blank — a capture
artefact, since `elementFromPoint(400,200)` returns the text *"MUST BE READ WITH
THIS NUMBER"*. The hit test is the stronger evidence anyway.

Rules 2-6 all hold; the version gate's third clause (a `may-never-drop` field the
build does not handle) fires at exit 3, and the head-to-head **fallback** block
appears only when I re-created the pre-v0.4.0 one-sided-key defect by mutation.

## U3. `era_key` grouping is adjacency by coincidence — measured, not argued

The builder grouped by `era_key`, which puts the ledger screen/defect pair in one
bordered `eragroup` block, and asked whether that is the right generalisation of
my rule. **It is not**, and the page itself says so:

| measured on the rendered page | |
|---|---|
| same bordered block | **yes** |
| gap between the two numbers | **200 px**, with a full metadata row between |
| order | **defect (99.02 %) ABOVE screen (6.9 %)** |

So even the coincidence does not deliver "printed together": a reader meets
99.02 % first and the screen 200 px later. And the deeper objection is that
`era_key` means *"measured under the same conditions"* — a property of how a
number was **made**. Whether two numbers must be read together is a property of
how they may be **read**. They coincide here because both rows came out of one
audit run. **Re-measure either on another corpus, its `era_key` changes, the pair
separates, and nothing fails.** A rule whose enforcement evaporates when an
unrelated field moves is not a rule.

⚠️ The builder's counter-example is real and I am keeping it: era grouping also
pulls the five blind engraved stages inside the era that produces 88.78 %, which
prose about one pair would never have reached. That is a genuine benefit — but it
is *contextualising a family*, not *binding a pair*. Both can be true; only one
of them needs a field.

**So it gets a field, the way `mandatory_caption` did:** `render_with`, symmetric
and build-enforced.

## U4. Four defects in my own frozen file, all real, all fixed → **v0.5.0**

| # | defect | fix |
|---|---|---|
| 1 | **Doubled `%%`** in four `why_not` strings — a `%`-format artefact. The renderer normalised it at display time; the frozen file still carried it. | Fixed at **source** on the 7 non-interpolated lines. Normalising a defect at display is how it survives. |
| 2 | **Nine `ceiling.evidence` entries were prose**, not openable paths — including two that *looked* like paths and resolved to nothing. | Split into `evidence_prose`; `evidence` is now **checked for existence at build time**. ⚠️ This makes my README's claim true — it was not true at 0.4.0. |
| 3 | **Two rows carried `ceiling.kind: null`.** A consumer grouping on `kind` cannot tell null from unset. | `unreachable_configuration` and `none`, both documented; null is never legal. |
| 4 | **The ledger pair was held together by prose and by luck** (§U3). | `render_with`. |

**Both new guards mutation-tested red before being trusted:** a one-sided
`render_with` → exit 1 naming both sides; a nonexistent evidence path → exit 1
naming the row. That is now **five** build-time guards, every one of which I have
watched fail.

`render_with` is in `fields_a_consumer_may_never_drop`, so the v2 renderer —
which does not handle it — now **correctly refuses v0.5.0 at exit 3** with an
actionable message. The gate catching my own change is the mechanism working, not
a regression.

**Frozen at v0.5.0. Registry byte-stable across two builds; ten probes green;
nothing outside this directory touched.**
