# % of achievable — every measurement, one unit, one direction

Generated from `metric-registry.json` v0.2.0 (round 2) by `tools/dashboard/registry_report.py`. **Do not hand-edit.**

**55 rows · 38 scoreable · 17 not.** Higher is better, everywhere.

⚠️ **There is no single top-line number here, deliberately.** Engraved and scan have different ceilings, different noise floors and different eras.

## The pair that must never be printed alone

| | native | % of achievable | verdict |
|---|--:|--:|---|
| **screen** — ledger-zone labels FLAGGED by the parity auditor | 6.9% | — | unscoreable: a workload figure, not an achievement |
| **defect** — ledger-zone labels ADJUDICATED wrong by a human | 0.98% | **99.02%** | scoreable |

They differ by **7×** and both are percentages. Printing either alone is wrong in a named direction: 6.9% overstates the defect sevenfold, 0.9% understates the reviewer's workload sevenfold.

## Digitally engraved input

| row | % achievable | native | ceiling | n | trust |
|---|--:|--:|---|--:|---|
| `reading:notehead` | **99.88** | 0.9988 | assumed | 856 | _assumed_ |
| `reading:time_signature_digit` | **99.72** | 0.9972 | assumed | 358 | _assumed_ |
| `reading:rest` | **99.25** | 0.9925 | assumed | 929 | _assumed_ |
| `reading:flag` | **99.16** | 0.9916 | assumed | 118 | _assumed_ |
| `engraved:omr_ned:mahler-sym5-mvt1` | **97.91** | 0.0209 | structural | 1 | **measured** |
| `engraved:omr_ned:beethoven-sym5-mvt1` | **97.07** | 0.0293 | structural | 1 | **measured** |
| `reading:clef` | **96.93** | 0.9693 | assumed | 226 | _assumed_ |
| `reading:augmentation_dot` | **96.19** | 0.9619 | assumed | 102 | _assumed_ |
| `engraved:omr_ned:tchaikovsky-sym4-mvt2` | **95.56** | 0.0444 | structural | 1 | **measured** |
| `reading:POOLED` | **91.92** | 0.9192 | assumed | 3220 | _assumed_ |
| `engraved:structure` | **90.91** | 0.9091 | structural | 11 | **measured** |
| `engraved:omr_ned:bruckner-sym5-mvt1` | **90.69** | 0.0931 | structural | 1 | **measured** |
| `engraved:omr_ned:brahms-sym1-mvt1` | **90.57** | 0.0943 | structural | 1 | **measured** |
| `engraved:omr_ned:mozart-sym41-mvt1` | **89.75** | 0.1025 | structural | 1 | **measured** |
| `engraved:omr_ned` | **88.78** | 0.1122 | structural | 11 | **measured** |
| `competitive:engraved:audiveris` | **87.48** | 0.1252 | competitive | 11 | **measured** |
| `engraved:omr_ned:beethoven-sym3-mvt1` | **87.06** | 0.1294 | structural | 1 | **measured** |
| `engraved:omr_ned:mozart-sym40-mvt1` | **85.85** | 0.1415 | structural | 1 | **measured** |
| `reading:key_accidental` | **83.89** | 0.8389 | assumed | 328 | _assumed_ |
| `engraved:omr_ned:tchaikovsky-sym6-mvt2` | **81.45** | 0.1855 | structural | 1 | **measured** |
| `engraved:omr_ned:brahms-sym4-mvt1` | **78.64** | 0.2136 | structural | 1 | **measured** |
| `reading:beam` | **75.34** | 0.7534 | assumed | 110 | _assumed_ |
| `engraved:omr_ned:dvorak-sym9-mvt4` | **66.20** | 0.3380 | structural | 1 | **measured** |
| `reading:dynamic_letter` | **55.15** | 0.5515 | assumed | 114 | _assumed_ |
| `reading:slur` | **51.77** | 0.5177 | assumed | 137 | _assumed_ |
| `reading:tie` | **26.02** | 0.2602 | assumed | 52 | _assumed_ |
| `engraved:stage10` | _unscoreable_ | — | visibility | 0 | **measured** |
| `engraved:stage11` | _unscoreable_ | — | visibility | 0 | **measured** |
| `engraved:stage2` | _unscoreable_ | — | visibility | 0 | **measured** |
| `engraved:stage3` | _unscoreable_ | — | visibility | 0 | **measured** |
| `engraved:stage9` | _unscoreable_ | — | visibility | 0 | **measured** |
| `reading:accidental` | _unscoreable_ | 0.4056 | render | 226 | _measured_unreliable_ |
| `reading:barline` | _unscoreable_ | — | visibility | 45 | **measured** |

**Why the unscoreable rows are unscoreable**

- `engraved:stage10` — the harness cannot see this stage at all — not exercised. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage11` — the harness cannot see this stage at all — no isolated figure. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage2` — the harness cannot see this stage at all — not exercised. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage3` — the harness cannot see this stage at all — not scoreable. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage9` — the harness cannot see this stage at all — invisible to the metric. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `reading:accidental` — the FIXTURE is unreadable for this family — a score here measures Verovio, not the pipeline
- `reading:barline` — CV-detected in CELL-relative coordinates and never expressed in page coordinates — 45 printed against 0 comparable. A frame mismatch, not a miss.

## Scanned input

| row | % achievable | native | ceiling | n | trust |
|---|--:|--:|---|--:|---|
| `scan:staves` | **100.00** | 1.0000 | input | 20 | **measured** |
| `scan:systems` | **100.00** | 1.0000 | input | 20 | **measured** |
| `labeling:ledger_zone:defect_rate` | **99.02** | 0.0098 | assumed | 102 | _assumed_ |
| `prefill:precision:blind_out_of_sample` | **94.33** | 0.9150 | competitive | 141 | **pre_registered** |
| `scan:pitch` | **83.43** | 0.8343 | assumed | 4127 | _assumed_ |
| `scan:duration` | **74.98** | 0.7498 | assumed | 3153 | _assumed_ |
| `scan:omr_ned:ceiling_corroborated_subset` | **29.80** | 0.7473 | structural | 5 | **measured_and_corroborated** |
| `competitive:scan:audiveris` | **20.81** | 0.7919 | competitive | 10 | _assumed_ |
| `scan:omr_ned:page_fidelity_15rows` | **20.09** | 0.8417 | structural | 15 | **measured_directly** |
| `scan:omr_ned:ceiling_measured_15rows` | **18.28** | 0.8417 | structural | 15 | **measured_single_source** |
| `scan:omr_ned` | **15.56** | 0.8444 | assumed | 20 | _assumed_ |
| `scan:hairpin_detect` | **1.01** | 0.0101 | input | 99 | _assumed_ |
| `ceiling:input:hairpin:scan` | _unscoreable_ | — | input | 17 | _refuted_as_a_ceiling_ |
| `ceiling:input:notehead:scan` | _unscoreable_ | 0.9710 | input | 207 | _bounded_above_ |
| `flag:OMR_CONDENSED_PARTS:oracle_ceiling` | _unscoreable_ | — | — | None | _unmeasured_ |
| `identity:calibration:ECE` | _unscoreable_ | 0.1277 | — | 197 | _unmeasured_ |
| `labeling:ledger_zone:screening_rate` | _unscoreable_ | 0.0690 | visibility | 102 | _not_a_defect_rate_ |
| `scan:input_ceiling:hollow_noteheads` | _unscoreable_ | — | input | 68 | _unmeasured_ |
| `scan:stage11` | _unscoreable_ | — | visibility | 0 | **measured** |
| `scan:stage4` | _unscoreable_ | — | visibility | 0 | **measured** |
| `scan:stage5` | _unscoreable_ | — | visibility | 0 | **measured** |

**Why the unscoreable rows are unscoreable**

- `ceiling:input:hairpin:scan` — This row exists to record a REFUTATION, not a score. The open question was whether `scan:hairpin_detect` at 1.01%% is a catastrophe or a hard input ceiling. A human found 17 hairpins on 55 scanned cells, so it is a CATASTROPHE — a detector failure, not missing ink. The same sweep also drew 62 ties and 27 slurs, the other two families a fine-tune is documented to delete. The ceiling VALUE is still 
- `ceiling:input:notehead:scan` — an UPPER BOUND, not a ceiling to score against. 201 human noteheads against 207 reference notes is a ratio of COUNTS, not a matched recall: grace notes are on the page and absent from the encoding (0 in 28,579), so human boxes are inflated and the true figure is at or below 0.971. What it DOES establish is that C = 1.0 is very nearly right for noteheads on this print — so `scan:pitch` at 83.4%% is
- `flag:OMR_CONDENSED_PARTS:oracle_ceiling` — ⚠️ THE CEILING GRADES A CONFIGURATION THAT CANNOT OCCUR. Verified in this tree 2026-09-07: `condensed_parts` is READ at export.py:3331 (`s.get("condensed_parts")`) and WRITTEN nowhere in tools/omr, so every staff reports 1 and the flag is inert even when set. The -4,557 figure was measured with ORACLE counts. A quoted ceiling for an unreachable configuration is the mirror image of a fabricated 100
- `identity:calibration:ECE` — ⚠️ NEITHER TRANSFORM CAN EXPRESS THIS, and forcing it would be worse than omitting it. `pct = 100*(W-M)/(W-F)` needs a defensible WORST CASE. OMR-NED has one (predict nothing scores exactly 1). A calibration error has none: ECE's arithmetic maximum is 1.0 but that is unreachable in practice and carries no meaning, so a percentage against it would be a number with no referent — the exact defect thi
- `labeling:ledger_zone:screening_rate` — ⚠️ A SCREENING RATE IS NOT A DEFECT RATE, AND THIS IS THE CLEAREST CASE IN THE PROJECT OF THE CONFUSION THIS UNIT EXISTS TO FIX. The auditor flags 7 of 102 (6.9%%); hand adjudication found ONE real error (~0.9%%) — a 7x gap, and six of the seven share one mechanism (a printed ledger line print-merging into the notehead's connected component, pulling the centroid up to a half-step). Both numbers ar
- `scan:input_ceiling:hollow_noteheads` — the page prints 68 half notes and the detector found 8, now 31 — but NOTHING measures how many of those counters are actually closed at 600 dpi bitonal, so there is no denominator of 'recoverable ink'. An INPUT ceiling is the one kind this project has never measured.
- `scan:stage11` — the harness cannot see this stage at all — no isolated figure. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `scan:stage4` — the harness cannot see this stage at all — no ground truth. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `scan:stage5` — the harness cannot see this stage at all — not isolated. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.

## Cross-cutting

| row | % achievable | native | ceiling | n | trust |
|---|--:|--:|---|--:|---|
| `human:review_cost` | _unscoreable_ | — | — | None | _unmeasured_ |

**Why the unscoreable rows are unscoreable**

- `human:review_cost` — ⚠️ THE THING SEAN BUILT THIS PROJECT TO REDUCE, AND IT IS NOT ON THE BOARD. It has been measured exactly once, as a side result: between two identity passes accuracy moved 44 records and review cost moved 2 (197 -> 195). It has no ceiling, no era key, no harness of its own, and no artefact this registry can read. See backlog D4.

## Head-to-head — NOT a delta

- `competitive:engraved:audiveris` **87.48%** vs ours 88.78% — same fixtures, same scorer, different system. Says nothing about direction over time.
- `competitive:scan:audiveris` **20.81%** vs ours — — same fixtures, same scorer, different system. Says nothing about direction over time.
- `prefill:precision:blind_out_of_sample` **94.33%** vs ours — — same fixtures, same scorer, different system. Says nothing about direction over time.
