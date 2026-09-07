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
