# Verification of round 1 — Agent IV

**Adversarial re-check of `INFORMATION_LIFECYCLE.md` (I), `DECISION_TYPES.md` (II)
and `MEASUREMENT_SYSTEM.md` + its four JSONs (III), against the tree at
`ac88148e`.** Nothing in `tools/`, `backend/` or the three reports was edited.
Every figure below was recomputed by this session, from the artefact or the
source file named beside it; my own scripts are in `probe/verify/`.

**Headline: the reports are unusually accurate on their positive numbers and
their errors are concentrated in exactly one place — universals and negatives.**
Of ~48 distinct quantities I recomputed, **44 reproduced exactly**, several to
the last digit of a float. Of the 8 defects found, **6 are negative or universal
claims** ("none of them", "the only one", "0 are ever revisited", "imported only
by"). That is the same distribution the map's own verification pass found, and
it now has a second instance.

⚠️ **One defect is the coordinator's own**, stated to me as settled fact
(`players_for_label` "imported only by its own test"). It is false. It is
reported here in the same terms as the agents' — see D8.

---

## WHAT HELD

### Coverage

| report | lines | what I checked | verdict |
|---|--:|---|---|
| **I** — `INFORMATION_LIFECYCLE.md` | 592 | all 4 tier-1/tier-2 items in my brief + the shared-substrate question. **8 distinct quantities recomputed, 6 exact.** ~43 negative-shaped phrases in the report; I checked 3 | **sound; two defects, one of them a false universal** |
| **II** — `DECISION_TYPES.md` | 880 | all 7 tier-1 items + the truth adjudication + the veto reach + the `trace=` negative. **19 distinct quantities recomputed, 16 exact.** ~48 negative-shaped phrases; I checked 4 | **sound; three defects, one consequential** |
| **III** — `MEASUREMENT_SYSTEM.md` + 4 JSONs | 616 | all 3 tier-1 items + the whole of tier 3 (48 registry rows, both transforms, the assumption rule) + 6 sampled figures. **21 distinct quantities recomputed, 19 exact; 35/35 registry transforms exact.** | **sound; three defects, all minor, one a self-inconsistency of the kind the report is about** |

**All three probe families re-ran and reproduced byte-identically.** Agent III's
`probe_ceiling_engine_independence.py`, `probe_pct_of_achievable.py` and
`probe_measurement_hygiene.py` all rewrote their JSONs with `git diff` empty.
Agent I's `probe_confidence_by_class.py` and Agent II's
`probe_ownership_reversibility.py` / `probe_ownership_reach.py` reproduced their
committed `out/*.txt` figures.

### The cross-report hazard — resolved, and the reported discrepancy does not exist

This was the coordinator's first item. **Independently recomputed from the 20
`benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json` files**
(`probe/verify/verify_436.py`):

```
files 20   total contests 4521
class disagreements 436 = 0.0964
decided_by over disagreements: distance 434, ladder 2
```

- **4,521 and 436 and 434-by-distance: exact, both agents.** ✅
- **Agent I's five named pairs: exact.** beam/tie 118 · slur/tie 74 ·
  beam/slur 71 · dynamicF/dynamicP 22 · accidentalFlat/accidentalNatural 15.
- **Agent II's four family counts: exact.** arc 263 (both classes in
  {beam,tie,slur}) · flag 47 · dynamic 38 · accidental 31 — these are the
  `category` field, verbatim.

⚠️ **The "disagreement" the coordinator flagged (accidental 15 vs 31, dynamic 22
vs 38) is not a disagreement.** Agent I reports one *named class pair*; Agent II
reports the whole *category*. 15 ⊂ 31 and 22 ⊂ 38 by construction — I confirmed
the subsets: `accidentalFlat/accidentalNatural` 15 of 31 accidental-category
disagreements, `dynamicF/dynamicP` 22 of 38. Both are right, about different
questions. **There is nothing to adjudicate.**

**1 · Same substrate — yes, one observation.** Both agents read the same 20
`.contests.json` files. Agent I says so itself (§"§4.1 shares its dumps with
`benchmarks/omr-additive-vs-gated-2026-09`. Different column, same table — **not
corroboration**"). **The coordinator is right to state this as ONE finding.**

**2 · Is it new?** Yes. `grep` over
`benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md` finds `4,521` (twice) and
**no occurrence of 436, of `class_i`, or of any class-disagreement figure.** The
survey established the contest population; the class-disagreement column is
genuinely new work by round 1. Agent I's caveat is accurate and is not
self-deprecation — it correctly labels the *population* as shared and the
*column* as new.

**3 · Agent I's |Δconf| control survives.** Medians 0.1365 (disagree, n=436) vs
0.0590 (agree, n=4,085) — the report's "0.137 vs 0.059", exact. And the
within-category control holds in **all five** categories I tested (structural
0.185/0.117, dynamic 0.161/0.084, notehead 0.113/0.045, accidental 0.156/0.098,
flag 0.138/0.105), so it is not a category-mix artefact.

### Agent III — the load-bearing evidence

**The exact float match is real, and the mechanism is now established.**
`results-normalised-arm-20row.json`'s `pooled_raw_over_all_scored_rows` equals
`results-reconciliation.json`'s `pooled` **on every field**: `omr_ned`
0.8443958865999122, `omr_ed` 74968, truth 49846, pred 38937, and all 23 category
counts. This is neither coincidence nor a copy:

- `normalised_arm.py`'s docstring: *"Re-computed here rather than read out of
  `results-*.json`, so drift is visible"*;
- the rows' `raw.pred` paths point at
  `.claude/worktrees/reconciliation/.../fixtures/<row>.reconciliation.omr.musicxml`
  — the same prediction files the headline was scored from, re-scored through the
  same musicdiff bridge.

So it is an **independent recomputation from identical inputs by a deterministic
scorer**, which is the strongest of the three explanations available and does
license the "ceiling and headline share an arm" conclusion. ✅ *(Agent III states
the fact but not the mechanism; supplied here so the coordinator need not re-ask.)*

**Engine independence — holds, and the confound check is clean.** Re-read from
`categories-audiveris-scan11.json` and `results-restamp-composed.json`: 10
comparable rows, **7 bit-identical**, 3 differing; `n_systems` = 1 on all 7
identical and 2 on all 3 differing. I tested four alternative predictors and
**none separates**:

| candidate confound | identical rows | differing rows | separates? |
|---|---|---|---|
| page index | 0,1,0,4,5,1,2 | 1,2,1 | **no** (overlap) |
| work | beethoven, brahms, dvorak, mahler | beethoven, brahms | **no** |
| staves on page | 12,14,15,15 | 11,14 | **no** |
| our own `entire staff` magnitude | 0…1674 | 715…1551 | **no** (1674 > 1551) |
| **n_systems** | all 1 | all 2 | **yes, 10/10** |

Under random labelling the chance of a 3-of-10 binary variable matching exactly
is 1/120. ⚠️ **And it is better than the report claims**: Agent III calls it *"a
variable nobody chose it for"*, i.e. serendipitous. It is not — CLAUDE.md's
`OMR_SLOT_STITCH` entry documents precisely that `export._stitch_slots` refuses
on multi-system pages and emits per-system fragment parts, which is the stated
mechanism for this split, and the direction matches (our charge is 2–5× Audiveris's
on exactly those rows). **A predicted split is stronger evidence than a lucky
one**; the report undersells itself here.

**Everything in §A7 and §B4 reproduces exactly.** Pooled `entire staff`
11,927 → 2,236; the three rows where the transform makes its own target category
worse (87→484, 90→530, 715→1,222); `wrong lyric` 30→231; the Dvořák identity
(15 source parts → 15 output, raw `omr_ned` == norm `omr_ned` to 16 digits, both
engines charge 0); every one of the 15 per-row `% of achievable` values and both
pools. The ranking inversion arithmetic checks: Beethoven 984073-p1
100·(1−0.7132)/(1−0.2757) = **39.6**, Dvořák p6 100·(1−0.7221)/(1−0) = **27.8**.

**The registry survives a full audit.** All **35** scoreable rows'
`pct_of_achievable` recompute exactly from `value`, `native_worst` and
`ceiling.value` under the row's own stated transform (max deviation < 0.06 on the
rounding). The assumption-direction rule is **implemented, not merely asserted**:
every `assumed` error row carries `F = 0.0` and every `assumed` rate row carries
`C = 1.0` — zero violations. **No row scores 100 by having no ceiling**: the only
two rows at 100 (`scan:staves`, `scan:systems`) are genuine 20/20 counts against
a hand-read ceiling. The `by_ceiling_status` census in `coverage` matches a
recount of the rows exactly.

**Competitive figures check out**: Audiveris engraved 0.1252 and scan 0.7919 are
both in `benchmarks/omr-vs-industry-2026-09/FINDINGS.md`; 87.48/88.78/20.81/16.55
are the correct transforms.

### Agent II — the clef finding

Every quantity in §3.2 and §3.3 that I could recompute, did:

- **11 mid-staff clef flips across 193 scan staves, 0 across 224 engraved
  staves** — recounted independently over both fixture sets. Exact, both
  denominators.
- **All 11 `instrument_source` values** in the report's table match the
  transcriptions (`score_order` ×3, `label` ×7, `score_order_ambiguity` ×1).
- **`MID_STAFF_CHANGE_VETOES` has exactly two entries**, the identity gate is
  `instrument_source == "label"` (`clef_correction.py:~475`), and
  `OMR_INSTRUMENT_CLEF_DEFAULT` defaults to `"0"` (`contextual.py:1003`). The
  reach chain **5 → 3 → 0** is arithmetically forced by those three facts and the
  eleven rows; I re-derived it and got the same three staves the report names.
- **`clef_final`: 20 of 193 staves carry it, 9 are stale** (`clef_final ==
  staff["clef"]` and every measure uniform). Exact.

**The truth adjudication is correct on all three checkable rows**, parsed from
the committed truth MusicXML:

| file | parts × measures | mid-part clef changes found |
|---|---|---|
| `beethoven-sym5-mvt1-984073-p1.truth.musicxml` | **18 × 16** | **0** ✅ |
| `brahms-sym1-mvt1-317803-p1.truth.musicxml` | 21 × 7 | **1: measure index 5, C4 → F4** ✅ |
| `mahler-sym5-mvt1-local-p3.truth.musicxml` | 38 × 8 | 1: measure index 4, F4 → C4 ✅ |

So "both 984073-p1 flips are WRONG" and "brahms p1 s12 tenor→bass at m5 is
CORRECT on index and target" both hold, and Agent II's refusal to adjudicate
Mahler (the part↔staff join is not established) is the right call — the truth
change *is* bass→tenor at m4, one measure off the two m3 flips.

**The `trace=` negative is a real consumer check, not a name grep.** ✅
`locate_clef`'s `trace` is declared **after `*`** (`clef_locator.py:646-652`), so
it is **keyword-only and cannot be passed positionally** — the trap named in my
brief is structurally unreachable here. Both production call sites
(`transcribe.py:1677`, `:4286`) pass no `trace`, and no other module in
`tools/omr/` references the parameter. Agent II's claim is exactly right and
robustly so.

**The 23.3% denominator is handled correctly.** The probe prints "30.4% of kept
detections"; the report converts to 2,592/(8,523+2,592) = 23.32% of detections
*made*, and the scan figure 1,446/(16,706+1,446) = 7.97% ≈ 8.0%. The conversion
is right and the report states the denominator rule explicitly. (One refinement
under WHAT DID NOT.)

**The reversibility table reproduces category-for-category** — 2,197 / 869 /
816 / 215 / 198 / 102 / 91 / 24 / 7 / 2, ladder 266 all inside `notehead`, 550
reversible = 12.2%, 3,971 irreversible = 87.8%. And **2,026 (44.8%) with 24
ties, |Δconf| median 0.064 / p95 0.343** — exact.

### Agent I — the information claims

- **`ledgerLine` confidence: exact on both pages.** beet5-p02 n=633, median
  0.337, 71.6% < 0.40; brahms1 n=768, median 0.344, 69.9%. And the two-weight-file
  claim is verified from the artefacts themselves: `beet5-p02-on.json` carries
  `weights: …hollow-graft-shift09…` with `weight_routing.verdict: "scanned"`, the
  Brahms carries `…imgsz2048-ft-30ep.pt` pinned. Two publishers, two checkpoints.
- **D23 is correctly overturned, and the argument is airtight.**
  `_overlaps_any_in_x` (`rhythm.py:815-829`) returns True on *any strictly
  positive* x-overlap, so a YOLO beam surviving the merge at `:1524` has **zero**
  x-overlap with every CV beam; `_deduplicate_beams` (`:769`) requires
  `overlap / b_w >= 0.6` before calling two beams duplicates. A CV/YOLO pair
  therefore cannot both be in the list and be comparable — in **every** branch
  (`extra_lines is None`, `cv_beams` empty, or the merge taken). And CV
  confidence is `1.0` by declaration (`line_detection.py:59`,
  `confidence: float = 1.0  # classical CV is deterministic; conf is arbitrary`),
  so the sort within the CV subset degenerates exactly as claimed. This overturns
  a documented finding and it is right to.

---

## WHAT DID NOT

Ranked by consequence.

### D1 — ⚠️ Agent II: *"0 of 4,521 ownership verdicts are ever revisited"* is false as written

§4.2, and it is the section's closing sentence — *"in the configuration that
actually runs, 0 of 4,521 ownership verdicts are ever revisited"*.

**`OMR_ARC_ATTRIBUTION` is default `move` (`export.py:1683`) and
`_arbitrate_arcs_in_system` (`export.py:1770`) re-decides which staff every slur
and tie belongs to**, "asked of every staff in the system, including ones that
never detected it" (CLAUDE.md). That is a shipped, on-by-default revisit of arc
**ownership**, downstream of `_dedupe_cross_staff_detections`. It reaches exactly
the population Agent II identifies as the largest class-disagreement group —
263 of the 436, and 2,197 structural contests overall.

**Corrected statement:** *the parking mechanism (`deferred`, `transcribe.py:2770`)
covers 550 of 4,521 pairs and its consumer `OMR_ROSTER_RANGE_VETO` is off, so **no
parked verdict is ever revisited as shipped**. A separate, on-by-default export
rule (`OMR_ARC_ATTRIBUTION=move`) does re-attribute arcs between staves, so
ownership of the arc classes — the single largest contested category — is not
final at dedup time.*

⚠️ **Agent II names the mechanism elsewhere** (§ item 2 of its summary table:
*"one exists in outline (`OMR_ARC_ATTRIBUTION`, already on, and 263 of the 436
class-disagreements are arcs)"*), so this is an internal inconsistency rather
than a missed consumer. But the §4.2 sentence is the quotable one, it is stated
as a universal, and it would be built on.

### D2 — ⚠️ Agent I: *"the only silent deletion rule in the pipeline with no counter at all"* is false

§ N16 and the S34 table. **At least four counterexamples, two of them in the same
function as the rule it is about:**

| deletion | site | counter reaching the output? |
|---|---|---|
| `_spans_the_whole_cell` drops YOLO beams | `rhythm.py:1419` | **none** — 5 lines *above* the rest filter |
| `_deduplicate_beams` deletes beam detections | `rhythm.py:1531` (def `:725`) | **none** — 50 lines *below* it |
| `_drop_close_outliers` deletes barlines | `measure_extractor.py:683` | **none** |
| `_reject_spacing_outliers` deletes staff groups | `staff_detector.py:1008` | **none** |

The three "siblings" Agent I compares against do write counters
(`n_clipped_notehead_fragments_dropped`, `n_unladdered_noteheads_dropped`,
`n_cross_staff_duplicates_removed`) — that half is right.

**Corrected statement:** *the spurious-rest filter deletes rest detections in
four `continue` branches with no count, no reason and no record. It is one of
several such rules — `_spans_the_whole_cell`, `_deduplicate_beams`,
`_drop_close_outliers` and `_reject_spacing_outliers` are equally silent — and
what distinguishes it is that its three nearest siblings in `transcribe.py` each
write a counter and it does not.*

The substance (it should have a counter) is untouched. The universal is not.
⚠️ Note also the report says **"three** `continue` branches" at N16 while its own
parenthetical at S34 correctly enumerates **four**.

### D3 — ⚠️ The coordinator's own claim: `players_for_label` is **not** imported only by its own test

Stated to me as independently confirmed and treatable as settled. It is not.

```
tools/omr/tests/test_condensed_parts.py:15          from tools.omr.condensed_parts import players_for_label
benchmarks/omr-staff-identity-2026-09/score_signals.py:410   from tools.omr import condensed_parts as C
benchmarks/omr-condensed-parts-2026-09/probe_real_labels.py:23
benchmarks/omr-condensed-parts-2026-09/run_arms.py:41
```

**Three benchmark consumers plus the test.** So it is a **production** orphan,
not an orphan — precisely the distinction `docs/architecture-decision-map.md`'s
own legend draws between `NOBODY` and `probe`, and precisely the error class the
map's verification pass found 11 of. It is **not stronger** than what either
agent claimed; it is the same claim with the qualifier dropped.

**What does hold, and is worth carrying:** the *field* `condensed_parts` is read
at `export.py:3331` and written **nowhere** in `tools/` or `backend/` outside
test fixtures — verified. Agent III's §A13 states this correctly and does not
over-reach.

### D4 — ⚠️ Agent III: *"None of them records the commit"* is false, and *"twenty"* is nineteen

§A1. `benchmarks/omr-scan-e2e-2026-09/` holds **19** `results-*.json`, not 20,
across four row sets (1, 5, 11, 20 — that part is right: {5:13, 11:4, 20:1, 1:1}).
And **one of them does carry a commit**:

```
results-condensation-arm.json   "git_head": "0bfe60d +uncommitted-tools"
```

The stamp is honest about the uncommitted tree, which *strengthens* the repair
Agent III proposes rather than weakening it — there is a working precedent in the
same directory. **Corrected statement:** *nineteen files, four row sets, and
exactly one carries a commit — `results-condensation-arm.json`, which shows the
shape works.*

### D5 — ⚠️ Agent III: "three independent routes" for Dvořák is one route observed three ways

§B2's closing ⚠️. The three are: Audiveris charges 0 · we charge 0 · the transform
is the identity (15 → 15).

They are not independent. All three are consequences of **one** structural fact —
the Dvořák page prints one staff per truth part — and any engine emitting one part
per staff will score 0 on that row for that reason. (1) does add something beyond
(3): it establishes that Audiveris *also* emits one part per staff, which is a
fact about Audiveris. But (2) and (3) are the same observation from two sides.

**Corrected statement:** *the Dvořák floor of 0 rests on one structural fact —
1:1 parts to staves, established from the reference truth and the hand-read map,
both independent of us — and is consistent with two engines' behaviour. Two of
the five Tier-A rows are these zero-floor Dvořák rows, so the corroborated pool's
non-zero ceiling actually rests on three rows.*

⚠️ This matters because the report elsewhere invokes *"corroboration is not
evidence"* as a governing rule. It is the one place it does not apply it to itself.

### D6 — Agent III's own restated figures have gone stale inside one document

§B5.4: *"twelve of the registry's **46** rows are unscoreable, and **ten** of
those are stages with zero information."* The registry says **48 rows, 13
unscoreable, 9 of `kind: visibility`**, of which **8** are stage cells
(`reading:barline` is the ninth). §B3 and the artefact table both say 48
correctly, and §B6 says *"visibility ✅ enumerated, 10 cells"* against §A3's
5 + 3 = 8.

Three restatements of one generated quantity, two of them wrong — which is §A1's
and §A14's own thesis, arriving inside the document that argues it. Cheap to fix:
those sentences should read from `coverage` the way CLAUDE.md's accuracy block
reads from `current-accuracy.json`.

### D7 — Agent II: "only 17 are the expected `…OnLine`/`…InSpace` artefact" matches no reading I can reproduce

§4.3(b). Recomputed:

- disagreements whose two classes differ **only** in `OnLine`/`InSpace`
  (i.e. one glyph at two staff positions, the stated definition): **13** —
  all `noteheadBlackInSpace` / `noteheadBlackOnLine`;
- all disagreements touching an `OnLine`/`InSpace` class: **18**;
- all `notehead`-category disagreements: **18**.

**17 is none of these.** The probe that produced the rest of §4.3(b)
(`probe_ownership_reversibility.py`) does not compute it, so it was derived
elsewhere and I cannot trace it. Immaterial to the conclusion (13 vs 17 of 436),
but it is a number in a table.

### D8 — Agent II's 436 breakdown reads as a partition and is not one

§ summary item 5: *"436 … — 263 arc-class, 47 flag, 38 dynamic, 31 accidental"*.
263 + 47 + 38 + 31 = **379**, leaving **57** unnamed (32 structural pairs that are
not all-arc — chiefly `staff`/`tie` ×18 and `ledgerLine`/`tie` ×5 — plus 18
notehead, 3 ornament, 2 rest, 1 clef, 1 time-sig digit). Add "and 57 others" or
say "the four largest families". ⚠️ The `staff`/`tie` and `ledgerLine`/`tie`
pairs are arguably the most interesting residue — an arc contested against a
*staff line* — and they fall outside every named bucket.

### D9 — Agent I: `ledgerLine` is not *"the lowest-confidence class on the page"*

The opening blockquote. On both pages the `stem` **category** is lower
(median 0.277, n=6 on beet5-p02; 0.302, n=15 on brahms1), and on brahms1 `staff`
sits at 0.357 against `ledgerLine`'s 0.344 — close. **Within the `structural`
category**, `ledgerLine` is the lowest on both pages, which is what the report's
own table shows and what the argument needs.

**Corrected statement:** *the ladder is assembled from the lowest-confidence
structural class on the page.* The finding is unaffected; the superlative in the
headline is the quotable line and is wrong as written.

### D10 — Agent II's 23.3% is a small overstatement

`n_detections_total` is a **net** counter: incremented at `transcribe.py:4546`
then decremented by `n_unladdered` (`:4721`), `n_deduped` (`:4730`) and
`n_furniture_dets` (`:4744`); clipped fragments are removed inside the cell pass
(`:1585`) before it is incremented at all. So "made = kept + removed" understates
*made*: the true engraved denominator is at least 8,523 + 2,592 + 28 + 46 +
furniture, giving **≤ 23.2%**, and less again once furniture is counted. Sub-point
of a point; the claim "nearly a quarter" survives.

---

## UNVERIFIABLE

| claim | why | the run that would settle it |
|---|---|---|
| Agent III §B4's `floor_low` is *"a charge no reader avoided"* | The floor is `entire staff / (truth_raw + truth_norm)` — the OMR-NED a hypothetical *perfect page-faithful* reader would score. Whether **our** `entire staff` count is what a perfect reader would incur is untested: musicdiff's block DP could pair differently against a complete prediction | Agent III names it itself and it is the right round-2 item: score the page-normalised truth **as the prediction** against the raw truth, 15 small files. Needs `derived-truth/` (gitignored, absent here) and `.venv-omrned` |
| Agent III §A12's env-var census (30 literal / 41 any-token / 22 documented) | Not re-derived; my remaining budget went to tier 1–3. The four named constant-held names are individually plausible | `grep -c` under both patterns in a clean checkout — 2 minutes, not run |
| Whether a `ledgerLine` confidence floor would help (Agent I §6 item 5) | Agent I explicitly marks it UNMEASURED and names the reach probe first. I agree it cannot be settled from artefacts | an A/B on `scan_eval` with distinct `--tag=` per arm — embargoed |
| Whether the class disagreement predicts which side is right (Agent II §4.3b) | Agent II explicitly claims nothing and names the test. Correctly parked | the ladder-as-gold-standard probe on n=266, as confidence was tested |
| Agent III §A3's "8 of 28 stage-cells have no number" against the *live* board | I verified the registry's internal census, not `docs/progress-dashboard.content.json` | `python3 -m tools.dashboard.generate --check` |

---

## WHAT IS MISSING

Following the precedent that *what is missing outranks what is wrong*. Each item
is inside the report's own declared scope.

### M1 — ⚠️ Agent III's registry omits three whole measurement families, and they are the ones Sean's brief was about

Sean asked to *"convert or translate **all** the different numbering measurement
systems into a single internal measurement system … sometimes 1.000 is what we
are aiming for and other times it would be a horrible score."* The 48 rows cover
OMR-NED (engraved + scan), reading F1, three scan detector rates, structure counts
and the stage census. **Absent entirely:**

- **The identity / label estate.** `label_contradiction` (158 firings, 0.873
  export-wrong / 0.127 label-wrong), roster parse rate 0.9607, margin-label
  accuracy 800/807, the held-out identity arm. This family is the one where
  *"1.000 means four things"* actually bites: a **contradiction rate** where lower
  is better sits beside a **parse rate** where higher is better, both printed as
  a bare decimal.
- **Calibration.** `P(name)` ECE 0.1277 and `P(set)` 0.1301 — an error metric
  whose natural worst is **not 1.0**, so neither of the registry's two transforms
  applies to it. The schema currently cannot express a third shape, and the
  project's own standing rule (*an uncalibrated probability is worse than none*)
  is a rule about exactly this number.
- **The labeling / pre-fill estate.** Pre-fill precision 0.915, and the
  ledger-zone audit whose **raw flag rate is 6.9% and adjudicated rate ~0.9%** —
  a metric whose headline is 7× its true value, which is the single sharpest
  live instance of the confusion Sean described, and it is not in the registry.
- **Machine cost.** §A9 correctly puts human review cost on the board as
  `scoreable: false`. There is no row for wall clock at all, though the direction
  reader is ~75% of whole-work runtime and the project is a payment-gated product.

### M2 — the schema cannot express a competitive comparison, and the report makes one anyway

§B5.5 rule 1 requires **equal `era_key`** before two scores may be differenced.
`competitive:engraved:audiveris` carries
`orchestral-e2e|2026-09-02|11works|direction_text|**audiveris-5.11**` and
`engraved:omr_ned` carries `…|**6b230bd7**`. They differ in the last segment **by
construction** — a cross-engine comparison always will. Yet §B6 prints
*"Audiveris 0.1252 → 87.5 % vs our 88.8 %"*, which the rule forbids.

The rule is right for time-deltas and wrong for engine-deltas, and the schema has
no relation that says *"these two rows are comparable in this one dimension"*.
That is a design gap, not an arithmetic error, and it will bite the moment
Audiveris is re-run. ⚠️ Related: the two figures are also from **different
commits of our own pipeline** (`FINDINGS.md` records our engraved figure as
0.1176 on `bc58defb` when the Audiveris arm was taken; the registry uses 0.1122
on `6b230bd7`), which the era rule *would* have caught had it been applicable.

### M3 — nobody priced the ±6 noise floor against the per-row claims that depend on it

Agent III's §A2 argues the arm-mismatch deltas *"sit at or near the documented
±6-edit noise floor"*, and calls that independent corroboration for the floor.
Recomputed, the eleven deltas are **572, 14, 10, 5, 3, 2, 1, 1, 1, 0, 0**:
**eight** are ≤ 6, two are 1.7–2.3× the floor, one is 572. "Ten of eleven"
requires counting 10 and 14 as "near" 6.

⚠️ And the two rows above the floor are **`dvorak-405834-p5` (+14) and `-p6`
(+10)** — both members of the five-row Tier-A corroborated pool. It does not touch
their `entire staff = 0`, but it means the pool the whole ceiling design rests on
contains the two least reproducible rows in the comparison, and no report says so.

### M4 — Agent II's six probes hard-code a different checkout

```
benchmarks/omr-pipeline-audit-2026-09/probe/probe_clef_argmax_contests.py:3
benchmarks/omr-pipeline-audit-2026-09/probe/probe_clef_winner_confidence.py:3
benchmarks/omr-pipeline-audit-2026-09/probe/probe_clef_midstaff_flips.py:2
benchmarks/omr-pipeline-audit-2026-09/probe/probe_ownership_reach.py:3
benchmarks/omr-pipeline-audit-2026-09/probe/probe_ownership_reversibility.py:3
benchmarks/omr-pipeline-audit-2026-09/probe/probe_unladdered_threshold_neighbourhood.py:3
        ROOT="/Users/seanjohnson/Desktop/ReEngrave"
```

**Today this is harmless** — I diffed `out/contests/` between the two trees and
they are byte-identical, and every figure reproduces. But these probes are
committed **into the audit tree** and will silently read the *other* checkout the
moment the trees diverge, which is the stale-tree incident this charter opens
with, installed into the audit's own instruments. Agent III's probes use
`Path(__file__).resolve().parents[3]` and are immune. `probe_clef_ladder_reach.py`
already has the escape (`os.environ.get("OMR_FIXTURE_ROOT", …)`); the other six
should adopt it.

### M5 — the era of Agent II's scan figures is never stated

"11 of **193** scan staves", "20 of 193 carry `clef_final`", "4,521 contests" and
"1,446 duplicates removed" are three *different* eras: the clef and reach figures
come from the **11-row `..graft09`** fixtures (the only `.omr.json` on disk here),
the contest dump from the **20-row** gate. Agent III's Part A is an argument that
this exact thing must be stamped; Agent II's numbers are unstamped in the same
document set. Neither is wrong — they are simply not differencable against each
other, and nothing says so.

### M6 — no report asks what the 436 costs the exported file

Both agents establish that an ownership rule silently settles 436 classification
disputes. Neither asks how many of the 436 **reach the MusicXML**. That is
cheap and it is the number a reader of these reports will want: a `beam`/`tie`
disagreement whose survivor is a `beam` may vanish into the rhythm layer and never
be exported at all, while an `accidentalFlat`/`accidentalNatural` disagreement
changes a printed pitch. Without it, "an ownership rule is settling a
classification dispute" is true and unpriced. *(And D1 above is why it is not
even a fixed 436 — arc attribution moves some of them again.)*

---

## Summary table

| # | report | claim | verdict |
|---|---|---|---|
| D1 | II | "0 of 4,521 ownership verdicts are ever revisited" | **FALSE** — `OMR_ARC_ATTRIBUTION=move` is default-on and re-attributes arcs |
| D2 | I | rest filter is "the only silent deletion rule with no counter" | **FALSE** — ≥4 counterexamples, two in the same function |
| D3 | *coordinator* | `players_for_label` "imported only by its own test" | **FALSE** — 3 benchmark importers; production orphan only |
| D4 | III | "twenty results files"; "none records the commit" | **FALSE** — 19 files; `results-condensation-arm.json` carries `git_head` |
| D5 | III | Dvořák floor "corroborated three independent ways" | **OVERSTATED** — one structural fact seen three ways |
| D6 | III | "twelve of 46 rows"; "ten stages"; "10 cells" | **FALSE** — 13 of 48; 9 visibility rows; 8 stage cells |
| D7 | II | "only 17 are the OnLine/InSpace artefact" | **UNREPRODUCIBLE** — 13 strict, 18 loose, never 17 |
| D8 | II | 436 = 263 + 47 + 38 + 31 | **INCOMPLETE** — sums to 379; 57 unnamed |
| D9 | I | `ledgerLine` "the lowest-confidence class on the page" | **IMPRECISE** — lowest *structural* class; `stem` is lower |
| D10 | II | dedup deletes 23.3% of engraved detections made | **SLIGHT OVERSTATEMENT** — ≤23.2%; denominator omits three removals |

**Everything else I checked held.** Including every load-bearing item in my
brief: the engine-independence result and its confound, the exact float match and
its mechanism, the ranking inversion, the `ledgerLine` measurement, the 436 and
its substrate, the clef flip counts and their truth adjudication, the veto reach
chain, the `trace=` negative, `clef_final`'s staleness, the reversibility table,
the 44.8% figure, and all 35 registry transforms.

### One note on the coordinator's inference-discipline memo

The memo says a near-50% split *"is what you would see if confidence were
unrelated to correctness."* Directionally right, and Agent II's framing is
already careful (it explicitly declines to argue confidence should decide, and
cites the survey's 0.617 ladder agreement against itself). For the record though,
**44.8% is not 50%**: n = 4,521 gives SE = 0.0074, so z ≈ **−7.0**. The survivor
is reliably, if weakly, the higher-confidence copy — which is what you would
expect if distance and confidence are mildly correlated, and is still not evidence
about *correctness*. Both halves of that are worth carrying: the effect is real
and it is not about being right.

---

# ROUND 2 — verification of `DECISION_TYPES.md` §R0–R7

**Appended 2026-09-07.** Agent II's round 2 (lines 889–1412), its seven new
probes and their `out/` captures, checked against the tree. `tools/` and
`backend/` are **unchanged since `350f0532`** (`git diff 350f0532..HEAD --
tools/ backend/` is empty), so every citation is against the tree the coordinator
named. My scripts are in `probe/verify/`.

**Round 2 is the most accurate work this audit has produced.** Of **31 distinct
quantities** I recomputed, **28 reproduced exactly** — including every headline
figure — and **19 of 19 spot-checked line numbers are exact**. Agent II
self-corrected two of its own round-1 claims before I reached them, and both
self-corrections are substantively right.

⚠️ The six defects are again concentrated: **one unit error inside the headline**,
one over-read negative, one arithmetic slip that *understates* its own case, and
the coordinator's M4 not actioned — with a **new and worse** failure mode
substituted for it.

## WHAT HELD (round 2)

### Tier 1 — the headline asymmetry: verified in code, and stronger than stated

**(a) Both defaults, from the code, not the docstrings.**

| | site | how it is gated | default |
|---|---|---|---|
| **METER** | `rhythm.drop_uncorroborated_meter_changes:597` | called at `rhythm.py:689` inside `backfill_page_time_signatures`, **with no flag of any kind**; that function is itself called unconditionally at `transcribe.py:4757` and `export.py:59` | **ON — and it is not a default, it is unconditional** |
| **CLEF** | `clef_correction.veto_implausible_clef_changes:460` | **one** production caller, `contextual.py:1518`, gated `if (instrument_clef_default and apply_clefs)`; `instrument_clef_default` is `os.environ.get("OMR_INSTRUMENT_CLEF_DEFAULT", "0")…not in ("0","","false","no","off")` at `contextual.py:1003` | **OFF** |

I traced every caller of both (`grep -rn` over `tools/` and `backend/`); the only
other references are tests. **The asymmetry is real and Agent II understates the
meter side** — "default ON" implies a flag that could be turned off, and there
is none. `_PROPAGATE_MIN_CHANGE_FRACTION = 0.5` (`rhythm.py:494`) confirms the
`max(2, 0.5 × n_staves)` quorum.

**(b) The 21 and the 11, recomputed** (`probe/verify/verify_r4_units.py`, written
from scratch against the artefacts):

```
scan:     11 pages, 193 staves
  meter MEASURES reverted (the field the guard writes) : 21
  meter CHANGES surviving in the artefact              : 0
  clef  CHANGES surviving in the artefact              : 11
engraved: 11 pages, 224 staves      →  0 / 0 / 0
```

Exact on every cell, **including the engraved control** — the fault is scan-only
in both channels, as claimed. Per-page, the 21 comes from three pages only:
Beethoven 984073-p1 (12), Brahms 317803-p1 (6), Mahler p2 (3). *(See D11 for the
unit problem this exposes.)*

**(c) The two sites are genuinely the same shape.** Read at
`transcribe.py:1592-1636`:

- **clef**, `:1604` `if d.confidence > best_clef_conf:` seeded `best_clef_conf =
  -1.0` at `:1594` — an argmax with **no floor** — then `:1616`
  `active_clef = best_clef_read.name + suffix`, unconditional on any resolvable
  clef detection;
- **meter**, `:1634` `new_time_sig = parse_time_signature(dets)` then `:1636`
  `active_time_sig = new_time_sig`, unconditional on non-None.

Both per-cell, both unconditional, both carried forward onto every later measure
of the staff. And I checked the one thing that could have broken the symmetry:
**`parse_time_signature` (`rhythm.py:206`) reads `confidence` nowhere** — it sorts
digit detections by x. So the meter site is not merely unfloored, it never forms
the quantity at all. **The shape claim holds, and holds more strongly than
written.**

**(d) The docstring quote is verbatim.** `rhythm.py:609-611` reads:

> *"It matters because a meter, once read, is carried forward onto every later
> measure of the staff, so a single false reading rewrites the rest of the staff
> and then votes for itself as many times as there are bars left."*

Agent II quotes it exactly, and the Beethoven 5 p.1 diagnosis that follows it in
the docstring (five `timeSig4` boxes on barline fragments, a 2/4 page shipped as
common time) is also as described. **The pipeline did write down this audit's
clef finding, for the meter, and then guarded only the meter.**

**R4.2's discipline holds throughout.** I read §R4.1–R4.3 and the R5 table
looking for any place the cross-staff meter witness is used to license a clef
change. There is none: R4.2 states the disanalogy explicitly, R5's R1 row repeats
the warning inline, and the three clef witnesses it lists (own header
contradiction, two-cell agreement, same part on another system) are all
staff-local. **No leakage.**

### Tier 2 — the negatives

| claim | recomputed | verdict |
|---|---|---|
| `accepted[0]` funnel: 139 → 134 → 20 → 20, **0 conflicts**, surya 19 / tesseract 1 | exact | ✅ *(see D12)* |
| `clef_weights: null` on every fixture → specialist reach **0 of 193, 0 of 224** | 0 non-null of 22 files | ✅ exact |
| ties: **1,459** scan / 298 both / 422 one / 739 none; engraved 155 / 70 / 30 / 55 | exact, and 298+422+739 = 1,459; 1,161/1,459 = **79.57%** | ✅ exact |
| tie `\|dy\|` median 0.42, p90 1.79, max 4.66; 122 of 298 > 0.5 nh; 199 of 298 differ in pitch | exact | ✅ |
| the bare `30` px floor **never binds** (median `avg_nh_h` 30.5 scan / 43.5 engraved) | `floor binds: {False: 1459}` / `{False: 155}` | ✅ exact |
| `time_signature_final` on **32 of 193** scan staves, **0** surviving meter changes; engraved 0 of 224 | exact | ✅ |
| Surya supplies **134 of 153 (87.6%)**; tiers 12 / 134 / 7 / 0 / 0; 132 labelled, 15 unresolved, 32 from score order | exact | ✅ |
| `_stitch_slots` refuses **2 of 11** scan, **0 of 11** engraved, **51** fragments; `brahms-317803-p2` = `[14, 13]`, Bach = `[12,3,3,3,1,2]` | exact | ✅ |
| lexicon refusals 71 / 50 / 10 / 2 / 2 = 135; **121 of 135 (89.6%)** carry no legal term | exact | ✅ |

**The tie replay is faithful, and I checked it line for line** against
`_pair_ties_in_staff` (`transcribe.py:2038-2123`). It reproduces all four
non-obvious details: notehead **centre** x rather than edges, a `w*3` window
using *each notehead's own* width, `avg_nh_h` as a **mean** not a median, the
`if not tie_list or len(nh_list) < 2: return 0` guard, and the
`best_left is not best_right` distinctness test. ⚠️ My own first-pass replay used
edges, a median and no `<2` guard and got **1,658 / 224 / 484 / 950** — a 199-tie
difference caused entirely by the `<2` guard. **Agent II's probe is right and
mine was not**; recorded because it is the kind of near-miss that would otherwise
read as a discrepancy.

**"Nothing counts them" is *stronger* than claimed.** `transcribe.py:4644` is
`_pair_ties_in_staff(staff_dict)` — the return value `n_new_pairs` is **discarded
at the call site**. So nothing counts the 1,161 unanchored ties *and* nothing
counts the 298 that anchored either. The only consumers of unpaired ties are
`export.py:2036`/`:2043`'s `tie_to_slur_unpaired_*` refusal reasons, which live
behind `OMR_ARC_RECLASS`, **default off** — which Agent II says.

**`time_signature_final`'s causal story checks out**: written at
`transcribe.py:4683` (`staff_dict["time_signature_final"] = (`) inside the staff
loop; `backfill_page_time_signatures` runs at `:4757` and `_reconcile_page_to_meter`
at `:4785`, both at page scope, both after. **Stale by construction**, as stated.

### Tier 3 — the self-corrections

**R0.1's withdrawal is right, and it is right for the reason given.** I
reproduced the additive survey's own figures from the shared dumps, on the
survey's own slices, exactly:

| slice | n (ties excl.) | P(winner conf > loser conf) | survey publishes |
|---|--:|--:|--:|
| distance-decided | 4,233 | **0.5452** | **0.545** ✅ |
| ladder-decided | 264 | **0.6174** | **0.617** ✅ |

So the two are measuring one quantity on one dataset and Agent II is right to
withdraw. *(The stated arithmetic identity is not exact — D15.)*

**The reversibility finding does not depend on confidence, as claimed.**
`probe_ownership_reversibility.py` computes `parked` as
`t == "distance" and cat == "notehead"` — the tier × category cross-tab and
nothing else. Confidence is computed further down and only *reported*. The
550 / 12.2% / 87.8% figures are untouched by R0.1. ✅

### Line numbers and the drift correction

**19 of 19 spot-checked citations are exact at HEAD**, and `tools/`/`backend/`
are byte-identical to `350f0532`: `rhythm.py:494, 597, 689, 1523` ·
`clef_correction.py:460` · `transcribe.py:1604, 1616, 1634, 1636, 2038, 2801,
4644, 4683, 4757, 4785` · `contextual.py:1003, 1518` · `direction_text.py:282,
614, 798, 801` · `export.py:1770, 1804`. The reported re-derivation was done
properly.

---

## WHAT DID NOT (round 2)

### D11 — ⚠️ The headline compares two different units: **21 MEASURES against 11 CHANGES**

`drop_uncorroborated_meter_changes` increments `reverted` **inside the per-measure
loop** (`rhythm.py:666`), and its own docstring says so: *"Returns how many
**measures** were reverted"*. The clef figure — 11 — counts **changes** (flips).
R4.1's table and R5's conclusion R1 put them side by side as though commensurable:
*"21 meter changes reverted and 0 surviving, against 0 reverted and 11 surviving
clef changes."*

**How large the error is cannot be recovered from the artefact**, because the
guard mutates in place and records only the measure count. The bound is
`3 ≤ changes ≤ 21`, and the per-page distribution makes the floor look likely:
12 reverted measures on a 16-measure Beethoven page, 6 on a 7-measure Brahms
page and 3 on Mahler p2 are each consistent with **exactly one** change per
page — because one change at measure index *k* reverts every measure from *k* to
the end of the staff. **So the true comparison may be as small as 3 reverted
against 11 surviving.**

**Corrected statement:** *the meter guard reverted **21 measures** across three
of eleven scan pages, leaving 0 surviving mid-staff meter changes; the clef guard
reverted **0** and left **11** surviving mid-staff clef changes. The number of
meter CHANGES reverted is between 3 and 21 and is not recoverable from the
committed artefacts.*

⚠️ **And this is Agent II's own thesis landing on Agent II's headline.** The
guard destroys the deciding quantity — it records the consequence (measures
rewritten) and not the decision (changes vetoed) — which is exactly the
"the margin is computed and discarded" pattern §R2.2 and §R4 are built around.
The asymmetry survives, comfortably. The number does not.

### D12 — ⚠️ "Zero conflicts" is true as the pipeline defines a conflict, and is read as more than that

I checked the bias the coordinator asked about, and the good news first: **it is
not a short-circuit artefact.** `direction_text.py:781-787` runs every reader over
every crop unconditionally, with a comment saying that is deliberate so
disagreement can surface. The conflict test at `:801-808` fires when ≥2 rungs are
**accepted** and their normalised texts differ.

**But `accepted` is post-lexicon.** A crop where Surya reads `legato` (accepted)
and Tesseract reads `f legato` (refused — and `f legato` appears **twice** in the
refusal list) is a real disagreement between the rungs and is **not a conflict**.
Worse, it is invisible: `info["rejected"]` is extended **only `if not accepted`**
(`:798`) — the asymmetry Agent II identifies four paragraphs later. The two
findings interlock, and the report does not join them.

**Corrected statement:** *`accepted[0]` has arbitrated zero times — on no crop did
two rungs both clear the lexicon with different readings, so the decision has
never had to choose. This is not evidence that the rungs agreed: a crop where one
rung is accepted and the other's reading is refused is not counted as a conflict
and, by the `:798` asymmetry, is not recorded at all.* The demotion is still
correct — `accepted[0]`'s reach really is 0.

### D13 — "ten lines apart" is twenty, or thirty

The overwrites are `transcribe.py:1616` (clef) and `:1636` (meter) — **20 lines**;
the cited lines `:1604` and `:1634` are **30**. Cosmetic, but it is a stated
quantity in the round's headline sentence and both line numbers are otherwise
exact.

### D14 — "Six of the ten PARTIAL refusals fail on `f`" is **seven**, and Agent II's own table says so

From `out/probe_direction_refusals.txt`, reproduced exactly:

```
x3  'F legato'   unknown=['f']
x2  'f legato'   unknown=['f']
x2  'f  legato'  unknown=['f']     →  3 + 2 + 2 = 7
x1  'F espr.e legato'  unknown=['f', 'espr.e']   (an eighth involving f)
```

**7 of 10 fail on `f` alone; 8 of 10 involve `f`.** The block quoted in §R1.3 is
the block that sums to 7. The slip **understates** the finding, which is the
harmless direction, but the arithmetic is visible in the report's own evidence.

### D15 — R0.1's arithmetic identity is not exact (the withdrawal still is)

R0.1 says the 44.8% *"is the arithmetic complement"* of the survey's 0.545, and
that *"Winner-higher 55.2% ⇔ loser-higher 44.8%"*. Three mismatches:

| | denominator | ties | P(winner > loser) | P(loser > winner) |
|---|--:|--:|--:|--:|
| **survey** (distance only) | 4,233 | excluded | **0.5452** | 0.4548 |
| **Agent II r1** (all tiers) | 4,521 | 24 **included** | 0.5466 | **0.4481** |

The complement of the survey's figure on the survey's own denominator is
**0.455**, not 0.448; and the complement of Agent II's 0.448 on *its* denominator
is **0.5466**, not the 0.552 R0.1 asserts (ties are neither). The numbers are
close because the ladder tier is only 266 pairs and the ties are 24.

**Corrected statement:** *the 44.8% and the survey's 0.545 are the same
measurement of the same quantity on overlapping data — one signal, not two — but
they are computed on different denominators (all 4,521 pairs with ties included,
against 4,233 distance-decided pairs with ties excluded) and are therefore not
arithmetic complements. On the survey's own slice I reproduce 0.5452 exactly.*
The withdrawal is correct and the credit assignment is correct; only the word
"complement" overstates the tightness.

### D16 — ⚠️ M4 is not actioned, and round 2 substituted a **worse** failure mode

All six round-1 probes still carry `ROOT="/Users/seanjohnson/Desktop/ReEngrave"`.
Only `probe_clef_ladder_reach.py` has the `OMR_FIXTURE_ROOT` escape.

**And the seven round-2 probes did not adopt the escape — they went
CWD-relative**, with `§R7` instructing `cd /Users/seanjohnson/Desktop/ReEngrave`
first. Run from anywhere else they **find nothing and exit 0**. Demonstrated,
from this worktree:

```
$ python3 …/probe_meter_guard_reach.py
=== scan: 0 pages, 0 measures
   uncorroborated meter changes REVERTED: 0
   measures carrying rhythm_sum_warning: 0 (0.0%)  severity {}
exit=0
```

That is a **believable wrong answer** — "the guard never fired, and no measure
anywhere fails its bar-sum" — where the absolute path at least always reads the
right tree. ⚠️ I hit this myself: my first `verify_r4_units.py` resolved ROOT to
the worktree and printed a clean all-zeros table before I noticed
`benchmarks/omr-scan-e2e-2026-09/fixtures/` **does not exist in this worktree at
all** (gitignored).

⚠️ **And the round-1 hard-coding was not laziness** — I said so too glibly. The
fixtures exist *only* in the main checkout, so a relative path genuinely cannot
work from here. The correct fix is neither: it is the `OMR_FIXTURE_ROOT` pattern
already in `probe_clef_ladder_reach.py`, **plus a non-zero exit on an empty
glob**. This is the same "an abstention and a failure look alike" fault Agent II
diagnoses for `_assign` in §R1.4, in the audit's own instruments.

---

## WHAT IS MISSING (round 2)

### M7 — ⚠️ The KEY SIGNATURE is the third instance of the same shape, and it sits **between** the two being compared

`transcribe.py:1629-1631`:

```python
new_key_sig = _detect_key_sig_from_cell(dets, cell, active_clef)
if new_key_sig is not None:
    active_key_sig = new_key_sig
```

Per-cell, unconditional on non-None, carried forward — **identical to both sites
R4.1 compares, and physically between them** (clef `:1616`, key `:1631`, meter
`:1636`). R4.1 says "the same fault, in the same function, ten lines apart"; it is
the same fault in the same function **three times**, twenty lines apart.

Measured: **no page-scope corroboration guard exists for it** —
`grep -rn "uncorroborated" tools/omr/` returns only the meter's. And the third
leg completes the `*_final` table R4.3 opens: **26 of 193 scan staves carry
`key_signature_final`** and **0 staves show a surviving mid-staff key change** on
either family (193 scan, 224 engraved), so it is stale at the same 100% rate as
the meter's. R4.3 names `key_signature_final` as the third stale field but does
not connect it to R4.1's symmetry, where it is the strongest available point:

> **guarded and corroborated: the meter. Guarded by an allowlist, default-off:
> the clef. Unguarded entirely: the key signature — currently inert, 0 surviving
> changes, which by this round's own reach-before-accuracy rule makes it a
> hazard to record rather than a defect to fix.**

*(I do not claim to know why the key channel is inert; `skip_key_sig_detection`
and the cross-page vote both suppress mid-staff key readings upstream and I did
not separate them.)*

### M8 — the reach that would price §R1.1's free fix is never computed

R1.1 correctly demotes `accepted[0]` and correctly identifies that the live
defect is `:798`'s asymmetry. But the number that would justify fixing it — **how
often exactly one rung was accepted while the other read something different** —
is not measured. Agent II gives only the upper bound ("up to 20").

⚠️ **And it cannot be measured from the current artefacts**, because that is
precisely what `:798` fails to record. Worth saying explicitly, because it
inverts the usual ordering: here the *fix must precede the measurement*, which is
unusual in this project and is the strongest argument for making a free change
without a prior number. Round 2 has the argument and does not make it.

### M9 — nothing checks whether the 21 reverted measures were reverted *correctly*

R4.1 uses the meter guard as the precedent that licenses the clef proposal. Its
reach is measured; its **accuracy** is not, on either side. The truth MusicXML for
all three affected pages is on disk and carries its own `<time>` elements, so
"did the reverted measures end up with the meter the truth prints" is answerable
from committed artefacts with no run — and it is the question that decides whether
the precedent is a good one. *(I did not run it: it is a round-3 item, not a
defect.)*

### M10 — R2.1's three-way cause split is named as the needed work and one leg is already measurable

R2.1 says the 1,161 unanchored ties are "spurious detection / missed head / head
deleted by the ownership rules" and that the three are not separable. **The third
leg is separable today**: the contest dumps record every deleted detection with
its staff, class and category, and 118 `beam`/`tie` plus 74 `slur`/`tie` plus 18
`staff`/`tie` plus 5 `ledgerLine`/`tie` disagreements are already enumerated in
round 1's §4.3. Joining the deleted noteheads to the unanchored ties by page
position is a probe over two committed artefacts. It would not separate the first
two legs, and Agent II is right that those need a run — but "not separable" is
stated of all three.

---

## Round 2 summary table

| # | claim | verdict |
|---|---|---|
| D11 | headline compares 21 **measures** to 11 **changes** | **UNIT ERROR** — true change count is 3–21, unrecoverable |
| D12 | "zero conflicts … the rungs produced no different readings" | **OVER-READ** — zero *accepted* conflicts; refused-side disagreement is unrecorded |
| D13 | "ten lines apart" | **FALSE** — 20 (overwrites) or 30 (cited lines) |
| D14 | "six of the ten PARTIAL refusals fail on `f`" | **FALSE** — seven; understates its own case |
| D15 | 44.8% is "the arithmetic complement" of 0.545 | **NOT EXACT** — different denominators and tie handling; the withdrawal itself is right |
| D16 | M4 (hard-coded probe roots) | **NOT ACTIONED**, and round 2 added a silent-empty variant |

**Everything else held.** Both guard defaults in code; the 21/0 and 0/11 and the
engraved 0/0 control; the identical unfloored per-cell shape at both sites and
`parse_time_signature` touching confidence nowhere; the docstring quoted verbatim;
R4.2's discipline maintained without leakage; the full direction funnel; the
specialist's reach of zero; the tie replay, verified faithful line-for-line; the
`*_final` staleness and its causal story; Surya's 87.6%; the stitch refusals; the
lexicon refusal table; the survey's 0.545 and 0.617 reproduced exactly; and 19 of
19 line numbers.

---

# ROUND 2 — Agent I (`INFORMATION_LIFECYCLE.md` §R0–R6)

**28 of 31 quantities reproduce exactly**, including both retraction tables and
every line number. ⚠️ **One retraction is wrong and I overturned it by widening
its own probe** (D17). Scripts in `probe/verify/`.

## WHAT HELD

### Retraction 1 — the ledger-ladder floor: CONFIRMED, and I strengthened it

The committed `probe_ladder_inversion.py` reproduces Q1/Q2 exactly: beet5-p02
626 noteheads / 398 inside / **0 inversions**, 633 rungs / 479 inside a band
(0.757); brahms1 4,260 / 3,059 / **0**, 768 / 302 (0.393). **Zero of 3,457.**

⚠️ **Q3 and Q4 — the two tables that carry the retraction — are produced by no
committed probe.** I rebuilt them from scratch (`verify_ladder_q3_q4.py`),
calling the real `_ledger_ladder` and re-using its own constants
(`_LEDGER_RUNG_EXPECTED_SLACK`, `_LEDGER_RUNG_Y_TOL_SPACES`,
`_LEDGER_RUNG_MIN_X_OVERLAP`). **Every cell matches:**

```
beet5-p02  outside 228  complete 26   using an impossible rung 0   matched rungs  31
           none→26(1.000)  0.30→22(.846)  0.40→15(.577)  0.50→4(.154)
brahms1    outside 1201 complete 222  using an impossible rung 0   matched rungs 297
           none→222(1.000) 0.30→184(.829) 0.40→94(.423)  0.50→34(.153)
```

**"Zero of 328 matched rungs"** — 31 + 297 = 328 ✅. **"A 0.40 floor destroys
42–58%"** — 1 − 0.577 = 0.423 and 1 − 0.423 = 0.577 ✅. And the coordinator's
specific worry is answered: **"complete ladder" is the same population in both
tables** (the 26 and the 222 are the denominators of each), which my single
reconstruction confirms by producing both from one definition.

⚠️ **I then measured the thing that makes the argument direct, and which neither
party computed** — the confidence of the *matched* rungs, i.e. the ones actually
load-bearing:

| | all `ledgerLine` | rungs INSIDE a band (impossible) | rungs MATCHED by a complete ladder |
|---|---|---|---|
| beet5-p02 | n=633 med **0.337**, 71.6% <0.40 | n=479 med 0.327, **74.9%** <0.40 | n=31 med **0.447**, **38.7%** <0.40 |
| brahms1 | n=768 med **0.344**, 69.9% <0.40 | n=309 med 0.313, **90.9%** <0.40 | n=297 med **0.400**, **49.8%** <0.40 |

**This is direct confirmation.** The ladder's geometry already selects rungs
better than the pool (0.447/0.400 against 0.337/0.344) and rejects the impossible
ones (which are 75–91% sub-0.40 and contribute 0 matches) — *and* **39–50% of the
rungs it does use still sit under 0.40**, which is precisely why a 0.40 floor
kills 42–58% of its verdicts. The two facts really are about different
populations, exactly as claimed. **Round-1 item 5 is correctly withdrawn.**

*(Immaterial: my independent count of impossible rungs on brahms1 is 309 against
the probe's 302 — a 7-detection band-edge boundary difference, 0.402 vs 0.393.
The headline range "39–76%" is unaffected.)*

### The rest

| claim | verdict |
|---|---|
| `Barline` has five fields, all coordinates (`types.py:107-115`), and the constructor at `measure_extractor.py:685-691` passes only those five | ✅ exact — `page_index, x, y_top, y_bottom, system_index`; `_drop_close_outliers` is typed `xs: list[int]` |
| a **fifth** `len(line_ys) >= 5` site at `_neighbour_room:849`, with `above = below = float("inf")` | ✅ exact — `if other is staff or len(other.line_ys) < 5: continue` |
| `_bands` (`transcribe.py:4711-4714`) is built from **all** `pws.staves` with no five-line filter → a one-line staff enters as a **zero-height band** | ✅ exact |
| `types.py:102` returns `nominal_line_spacing_px` when `len(line_ys) < 2` — the E1 property | ✅ exact |
| census **793 / 197 / 211**, per-file table, discarding share 0.248 | ✅ reproduces exactly |
| **18 drop sites, 14 writing no count (0.778)** | ✅ reproduces exactly |
| **S46** — `y_tolerance = max(avg_nh_h*3, 30)` at `:2251` applied *separately* to each end against the tie's own centre; `best_left_dx`/`best_right_dx` discarded; the only mutual test is `best_left is not best_right` at `:2279` | ✅ exact on every particular |
| R0-a and R0-b accept my D2 and D9 correctly, and R0-a converts the falsified universal into a mechanical `n of m` | ✅ the right repair |

## WHAT DID NOT

### D17 — ⚠️⚠️ N4 is **NOT unreachable**. I widened its own probe and the branch fires.

`probe_beam_bar_positions.py` renders pages and runs phase 1 — **no detector, no
weights** — so the sample is cheap to extend. I reproduced the committed census
exactly (277 components, 0 multi-bar) and then ran the identical probe over **ten
pages it did not include**:

| page | components | `n_bars ≥ 2` |
|---|--:|--:|
| brahms-317803-**p2** (scan) | 180 | **13** (7.2%) |
| bach-brandenburg3-p1 (scan) | 483 | **9** (1.9%) |
| mahler-local-**p3** (scan) | 68 | **4** (5.9%) |
| dvorak-405834-**p6** (scan) | 71 | **3** (4.2%) |
| brahms-317803-**p4** (scan) | 73 | **2** (2.7%) |
| beethoven-984073-p4 (scan) | 156 | 0 |
| bruckner 5 · mozart 40 · dvorak 9 · tchaikovsky 4 (engraved) | 51 | **0** |
| **new total** | **805** | **31** |

**The fabrication branch executes on 31 components, all of them on scans, none
engraved** — and `n_bars == 1` *is* the right test (`sub_h = h//1`, `y + 0*(h/1)`
is the box itself, so a 1-bar component fabricates nothing). The mechanism is
sound; the reach was measured on a sample that could not show it.

⚠️ **And the sample bias is identifiable, not bad luck: both of the original two
scan pages are `p1` rows — the two best-scoring, cleanest-print pages in the scan
gate.** Every multi-bar component appears on p2/p3/p4/p6 or Bach. Print-merged
beams live on the worse prints, and the sample excluded them.

⚠️ Note also: `columns disagreed with the median count: 0 of 13`, `0 of 9`, `0 of
4`, `0 of 3`, `0 of 2` — where `n_bars ≥ 2` fires, the columns **agree**, so these
are not median noise. Their median box fill is **0.472**, which is the docstring's
own signature for a *sloped single* bar (43–46%), so a second reading is open and
worse: some of the 31 may be one sloped bar being split into two fabricated
coordinates. **I did not adjudicate which**, and it should not be asserted either
way without looking at the ink.

**Corrected statement:** *`n_bars ≥ 2` fired 0 times in 277 components over five
pages, and **31 times in 805 components over ten further pages** — 1.9–7.2% of
accepted beam components on five of six additional scanned pages, and 0 on all
seven engraved fixtures measured. The fabrication branch is live on scans. N4 is
not unreachable; it was unsampled.*

⚠️ **Agent I's §R5 item 8 says the right thing** — *"Neither should be deleted on
these numbers — 5 pages … a null on a corpus without the defect is not
evidence"* — and the §R2.1 heading (**"UNREACHABLE"**) contradicts it. The
hedge was correct and the headline overrode it. ⚠️ **And the coordinator's stated
interest was in the item being real; it is real, and the retraction is what was
wrong.** My widened census is at
`probe/verify/beam-bar-census-WIDENED-16pages.json`; the committed
`beam-bar-census.json` was restored to its 277-record state (`git checkout`,
verified) after my run overwrote it.

### D18 — the census-vs-map comparison is not a valid comparison

§R3: *"**793 against the map's ~176 §5 rows for the whole pipeline** puts a number
on the coordinator's *what is missing outranks what is wrong*."*

They count different things and the numbers cannot be set against each other:

| | 793 | ~176 |
|---|---|---|
| unit | an AST node — `If`/`IfExp`/comprehension-filter containing a `Compare`, or a selector call | a hand-curated *conceptual* decision point, with type, blindness and consumers |
| scope | **seven files** | the whole pipeline (40+ modules) |
| granularity | one clef argmax is several nodes; a bounds guard is one node | one row |

A single map row maps to many census nodes and many census nodes map to no map
row *correctly*. Agent I hedges well two sentences earlier (*"a reproducible upper
bound on sites worth inspecting, not a defect count"*) and then makes the
comparison anyway — and the comparison is the quotable line. **The census is
valuable on its own terms** (mechanical, re-runnable, a real floor); it should be
quoted without the ratio.

### D19 — the D2-replacement table misnames one of its four false positives

§R3.1 lists the four functions hand-adjudicated out of the mechanical 14 as
*"`parse_pages`, `_ledger_rows`, `_window_blind_systems`, `_measure_x_boundaries`"*.
The probe's actual 14 contains `parse_pages`, `_ledger_rows`,
`_window_blind_systems` and **`_dedupe_cross_staff_detections`** —
`_measure_x_boundaries` is not in it. `_dedupe_cross_staff_detections` *does*
write a count (`n_cross_staff_duplicates_removed`), so it is a genuine false
positive of the rule and the report correctly puts it in the *accounts-for-its-
removals* column; only the parenthetical names the wrong function. **The
number (14, and 16 of 20 with the two stated misses) is unaffected.**

## WHAT IS MISSING (Agent I round 2)

- **M11 — the retraction's own evidence is not reproducible.** §R2.2's Q3 and Q4
  tables reach a conclusion the coordinator has already relayed to Sean, and no
  committed probe emits them; `probe_ladder_inversion.py` stops at Q2. By this
  audit's own standard (*a committed artefact, or it is not a claim*) the
  retraction was, until this pass, unverifiable. It now reproduces —
  `probe/verify/verify_ladder_q3_q4.py` — but that file is mine, not the
  reporting agent's.
- **M12 — the direct form of the argument was never computed.** The matched-rung
  confidence distribution (table above) settles the "different populations" claim
  in one line and is free from the same artefacts. §R2.2 argues it from the
  survival table instead, which is inference where measurement was available.
- **M13 — §R2.1's null needed exactly one more page and the report says so.**
  §R5 item 8 names the standard (*"a null on a corpus without the defect is not
  evidence"*) and §R6 lists the 5-page limit under UNMEASURED. The widening cost
  minutes and needed no weights. **A stated limit that is cheap to close should be
  closed, not declared.**

---

# ROUND 2 — Agent III (`MEASUREMENT_SYSTEM.md`, registry v0.2.0)

**All Tier-1 claims hold, including the three controls and the most consequential
negative in the audit.** One incidental is stale (D20).

## WHAT HELD

### The measured structural floor — all three controls pass, the third exactly

| control | verdict |
|---|---|
| all 20 truth fixtures sha-match the canonical arm | ✅ `controls.fixture_binding.all_match_canonical_arm: true`, and **the run refuses otherwise** — a control that can fail |
| all 15 derived truths reproduce the committed control's **canonical** hashes | ✅ `derived_truth_reproduces_committed_control` true on all 15 |
| the three identity-transform rows score **exactly 0 edits** | ✅ **`omr_ed_total = 0`, `omr_ned_total = 0.0`, unpaired 0, structural 0, residue 0** on all three Dvořák rows, each with `n_source_parts == n_output_parts == 15` |

The third is the strongest and it is exact: a transform that is the identity on a
1:1 page charges nothing, which is what a floor measured by scoring the derived
truth *as the prediction* must do or be discarded.

**The ladder arithmetic reproduces and the conservative rung is the one used:**

```
unpaired-parts 14791/69672 = 0.21229   →  100(1−0.8417)/(1−F) = 20.10
structural     34710/69672 = 0.49819   →  31.55
total          44226/69672 = 0.63477   →  43.34
residue share  9516/44226  = 0.21517
```

**A larger floor gives a larger score**, so taking 0.2123 rather than 0.6348 is
conservative by arithmetic, and the report's stated reason is exactly right. The
`0.8417 → 20.09%` headline checks out (20.10 on the rounded M; 20.09 on the
unrounded).

⚠️ **The self-consistency pattern is genuine and pre-registered rather than
post-hoc**, so far as the artefact can show: `control_history` records **two
earlier definitions of `n_output_parts` that were tried and failed** (`== page.n_staves`
failed 10 rows; `== n_staves // systems` failed 3), which is a falsification trail,
not a fitted result. The direction claim — corrections all *upward*, at rows where
our own `entire staff` charge was anomalously small — is consistent with round 1's
`floor_low` table (984073-p3 at 0.024 and 575951-p3 at 0.025 were the two
anomalously small estimates) and is the direction the estimator's self-reference
predicts. **I could not re-derive the 12-of-15 / 3-corrected split**, because
round 1's per-row `floor_low` and this run's per-row floors are on different
denominators; recorded as consistent-but-not-independently-recomputed.

### The `input` ceiling refutation — the counts are exact

Recounted directly from `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/verdicts/`,
over every verdict whose `inspected_passes` contains `completion`:

```
cells stamped completion : 55        human-drawn boxes : 554
dynamicCrescendoHairpin  : 13   }
dynamicDiminuendoHairpin :  4   }  = 17 hairpins
tie                      : 62        slur : 27        noteheads : 203
```

**Exact on all five figures.** The artefact's `counts` (207 reference notes, 201
human noteheads over the 47 *usable* cells, ratio 0.9710) is consistent with my
203 over all 55.

⚠️ **On the population question, which the coordinator asked me to press hardest:
the exclusion of the other ten batches is methodologically correct, not a
convenience.** `why_this_batch` states it: every other batch is a single-symbol
sweep, where everything outside the pass is unboxed *by instruction*, so a count
of human boxes there would measure the pass and not the ink. That is the same
reasoning `verdicts_to_yolo_labels`' `inspected_passes` mechanism exists for.
**So the limitation is irreducible with today's corpus rather than a shortcut —
and it is still one batch, one work, one publisher (Breitkopf, Brahms 1).** The
conclusion (a reader can see 17 hairpins where the detector finds ~1 per page
across eleven scan pages, so 1.01% is a catastrophe and not a ceiling) is very
likely right and rests on one edition. It should be quoted with the edition
named.

**The notehead-ratio refusal is correct, not over-cautious.** 201/207 = 0.971 is
a ratio of two *counts*, and grace notes are absent from both sides (the
transcription holds 0 `Small` detections and the reference holds 0 `<grace/>` —
CLAUDE.md records both). A count ratio near 1 therefore bounds nothing about what
a reader could recover; `bounded_above, scoreable: false` is the right verdict.

### The human-cost negative — verified precisely, and it is the audit's most consequential

| claim | verified |
|---|---|
| FINDINGS reports **197 over 3,543** records | ✅ `omr-identity-harness-2026-09/FINDINGS.md:226` |
| decomposed 150 contradicted-only / 24 unnamed / 15 not-in-this-work / 8 both | ✅ `:256-257` |
| the committed `out/records.json` holds **1,571 records in 2 arms** | ✅ `beet5/shipped` 807 + `brahms1/fit=search,spans=on` 764 |
| it carries **no `not-in-this-work` field** | ✅ fields are `arm, contradicted, correct, emitted, engraving, label_read, lineup, n_staves, named, ordinal, page, publisher, slot, source, system, truth, work` |
| only `contradicted` re-derives: **26 of 1,571 = 1.66%** | ✅ 15 + 11 = 26; 26/1571 = 0.01655 |

**So the project's stated purpose is measured in exactly one place, over 3,543
records, and the committed artefact holds 1,571 — 44.3% of them, per FINDINGS'
own pooled row — with two of the four decomposition categories unrepresentable.
The figure cannot be re-derived from the tree.** Confirmed.

**And the floor judgement is right.** 0 of 1,571 records are unnamed, so the
definition's floor computes to **0**, which would assert that a perfect pipeline
leaves a reviewer nothing to open — contradicting the identity scope's own claim.
Declaring the floor **open rather than zero** is the conservative call and the
correct one: under §B3's assumption-direction rule a floor of 0 for an error
metric is the *minimising* default, so recording it as measured would have been
the one case where the conservative default is substantively wrong.

### The two incidentals

- **`sha.normalised_truth` cannot verify reproduction — CONFIRMED, and it is a
  defect in an existing artefact, not in the audit.** `controls.derived_truth_note`
  diagnoses it correctly: music21 stamps a fresh 32-hex instrument id on every
  write, so the raw sha256 differs run to run; reproduction is checked against
  `derived-truth-bytes.json`'s canonical (id-masked) hash instead, and the arm's
  `sha.truth` / `sha.pred` — which *are* reproducible — are what the fixture
  binding uses. Correctly handled and correctly attributed elsewhere.

## WHAT DID NOT

### D20 — the coarse-spelling incidental is real in its count and **stale in its claim**

The count is exact: over the 55 completion cells, **26 human boxes carry the
coarse spelling** — `dynamicLetterF` 13 + `dynamicLetterP` 11 + `dynamicLetterS`
2 = 26. ✅

But *"the exporter cannot read"* is no longer true, and this is not an unclaimed
finding belonging to someone else. `tools/omr/class_aliases.py` maps all three:

```
"dynamicLetterP": "dynamicP",   "dynamicLetterF": "dynamicF",   "dynamicLetterS": "dynamicS",
```

and `class_aliases.py:21` names **this very campaign** as the reason the module
exists (*"campaign's hand-drawn boxes are classed `dynamicLetterF`/`P`/`S`"*).
CLAUDE.md records the fix and the residue.

**Corrected statement:** *26 of the campaign's human-drawn boxes use the coarse
`dynamicLetter*` spelling — exactly the population `class_aliases.py` was written
for and already renames. The live residue is on the LABELING side, where
`catalog.yaml` still carries the coarse ids 190–195, and CLAUDE.md already
records it.* Relay it as corroboration of a shipped fix, not as a new finding.

## WHAT IS MISSING (Agent III round 2)

- **M14 — the matched comparison for the hairpin refutation is not made.** The
  claim contrasts 17 human-drawn hairpins on 55 Brahms cells against a
  detector that finds ~1 hairpin across eleven *whole scan pages*. Those are
  different denominators. What the detector found **on those same 55 cells** is
  in the batch's own `detections/`, costs one pass, and would turn a strong
  argument into a controlled one.
- **M15 — the floor's ladder is measured on 15 rows and the headline is 20.** The
  five Mahler/Bach rows are correctly skipped (`no hand-read staves map — refusing
  to guess a condensation from the encoding`) and they carry
  `staves_a_human_would_read` 17/13/18/17/24 — i.e. the work needed to close the
  gap is enumerated in the artefact and is 89 staves. That number should sit
  beside the 20.09%, because the headline pool and the floor pool still differ.
- **M16 — nothing prices the arm-noise argument the comparability rule now rests
  on.** M3's defence (arm noise moves `M` and cannot move `F`, because `F`
  contains no prediction of ours) is **correct as stated** — I checked it against
  the artefact: `not_a_pipeline_figure` is literally true, the floor is scored
  derived-truth-against-raw-truth with no prediction in it. But it makes the
  *pair* (M, F) noisy only in M, which means the per-row noise floor must be
  applied to M alone — and the registry's `noise_floor` field is attached to the
  row, not to M. A one-line schema distinction, unstated.
