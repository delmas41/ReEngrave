# % of achievable

One unit, one direction: **higher is better, everywhere.** Registry v0.7.0. Generated — do not hand-edit.

## Head-to-head (grouped on `comparable_as.head_to_head` only)

**`engraved|orchestral-e2e-fixtures|11works|musicdiff-AllObjects|detail=AllObjects`**
- `engraved:omr_ned` — 88.78%
- `competitive:engraved:audiveris` — 87.48%

**`scan|scan-e2e-fixtures|10rows|musicdiff-AllObjects|detail=AllObjects`**
- `competitive:scan:audiveris` — 20.81%
- `scan:omr_ned:same_10_rows_as_audiveris` — 16.55%

## Cross-cutting — belongs to neither family

### sample `identity-harness|2026-09-07|1571 committed records|2 arms|clef-regime MIXED`

- **97.07% of achievable** — `human:review_cost:identity` — ⚠️ MUST BE READ WITH THIS NUMBER: Staff NAMING only. The reviewer's larger load — note-level diffs — has no harness at all, so this is not a measure of how much review a score needs.

## Digitally engraved input

### sample `orchestral-e2e|2026-09-02|11works|direction_text|6b230bd7`

- **unscoreable** — `engraved:stage2`
  - the harness cannot see this stage at all — not exercised. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- **unscoreable** — `engraved:stage3`
  - the harness cannot see this stage at all — not scoreable. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- **unscoreable** — `engraved:stage9`
  - the harness cannot see this stage at all — invisible to the metric. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- **unscoreable** — `engraved:stage10`
  - the harness cannot see this stage at all — not exercised. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- **unscoreable** — `engraved:stage11`
  - the harness cannot see this stage at all — no isolated figure. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.

### sample `page-truth|verovio-render|300dpi|tol0.5spaces|11works`

- **99.88% of achievable** — `reading:notehead`
- **99.72% of achievable** — `reading:time_signature_digit`
- **99.25% of achievable** — `reading:rest`
- **99.16% of achievable** — `reading:flag`
- **96.93% of achievable** — `reading:clef`
- **96.19% of achievable** — `reading:augmentation_dot`
- **91.92% of achievable** — `reading:POOLED`
- **90.91% of achievable** — `engraved:structure` — ⚠️ MUST BE READ WITH THIS NUMBER: These fixtures are 1:1 BY CONSTRUCTION — every truth part gets its own printed staff. A conductor's page condenses and splits; this stage is never asked that question here.
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **83.89% of achievable** — `reading:key_accidental`
- **75.34% of achievable** — `reading:beam`
- **55.15% of achievable** — `reading:dynamic_letter`
- **51.77% of achievable** — `reading:slur`
- **26.02% of achievable** — `reading:tie`
- **unscoreable** — `reading:accidental`
  - the FIXTURE is unreadable for this family — a score here measures Verovio, not the pipeline
- **unscoreable** — `reading:barline`
  - CV-detected in CELL-relative coordinates and never expressed in page coordinates — 45 printed against 0 comparable. A frame mismatch, not a miss.

### sample `orchestral-e2e|2026-09-02|11works|direction_text|6b230bd7|detail=AllObjects`

- **97.91% of achievable** — `engraved:omr_ned:mahler-sym5-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **97.07% of achievable** — `engraved:omr_ned:beethoven-sym5-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **95.56% of achievable** — `engraved:omr_ned:tchaikovsky-sym4-mvt2` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **90.69% of achievable** — `engraved:omr_ned:bruckner-sym5-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **90.57% of achievable** — `engraved:omr_ned:brahms-sym1-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **89.75% of achievable** — `engraved:omr_ned:mozart-sym41-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **88.78% of achievable** — `engraved:omr_ned` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **87.06% of achievable** — `engraved:omr_ned:beethoven-sym3-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **85.85% of achievable** — `engraved:omr_ned:mozart-sym40-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **81.45% of achievable** — `engraved:omr_ned:tchaikovsky-sym6-mvt2` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **78.64% of achievable** — `engraved:omr_ned:brahms-sym4-mvt1` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **66.20% of achievable** — `engraved:omr_ned:dvorak-sym9-mvt4` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.

### sample `orchestral-e2e|2026-09-02|11works|direction_text|audiveris-5.11|detail=AllObjects`

- **87.48% of achievable** — `competitive:engraved:audiveris` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. On the scan gate, re-scoring the same files under `|Voicing` removes ~29% of the pooled edits; the share on this family is UNMEASURED. Accounting, not improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.

## Scanned input

### bound by `render_with` — read together, never apart

- **unscoreable** — `labeling:ledger_zone:screening_rate`
  - ⚠️ A SCREENING RATE IS NOT A DEFECT RATE, AND THIS IS THE CLEAREST CASE IN THE PROJECT OF THE CONFUSION THIS UNIT EXISTS TO FIX. The auditor flags 7 of 102 (6.9%); hand adjudication found ONE real error (~0.9%) — a 7x gap, and six of the seven share one mechanism (a printed ledger line print-merging into the notehead's connected component, pulling the centroid up to a half-step). Both numbers are percentages; only one is a quality figure. A dashboard that prints either alone is wrong: 6.9% overstates the defect sevenfold, and 0.9% understates the reviewer's workload sevenfold. The registry's answer is that they are TWO ROWS with different `stage` semantics — a SCREEN and a DEFECT — never one, and a screen is never scoreable on the achievement axis.
- **99.02% of achievable** — `labeling:ledger_zone:defect_rate`

### sample `(no era key declared)`

- **unscoreable** — `flag:OMR_CONDENSED_PARTS:oracle_ceiling`
  - ⚠️ THE CEILING GRADES A CONFIGURATION THAT CANNOT OCCUR. Verified in this tree 2026-09-07: `condensed_parts` is READ at export.py:3331 (`s.get("condensed_parts")`) and WRITTEN nowhere in tools/omr, so every staff reports 1 and the flag is inert even when set. The -4,557 figure was measured with ORACLE counts. A quoted ceiling for an unreachable configuration is the mirror image of a fabricated 100%: it makes a gap look bigger than the pipeline can act on.

### sample `ad-hoc|beethoven-sym5-mvt1-984073-p1`

- **unscoreable** — `scan:input_ceiling:hollow_noteheads`
  - the page prints 68 half notes and the detector found 8, now 31 — but NOTHING measures how many of those counters are actually closed at 600 dpi bitonal, so there is no denominator of 'recoverable ink'. An INPUT ceiling is the one kind this project has never measured.

### sample `labeling|breitkopf-brahms1|completion-pass|47 cells`

- **unscoreable** — `ceiling:input:notehead:scan`
  - an UPPER BOUND, not a ceiling to score against. 201 human noteheads against 207 reference notes is a ratio of COUNTS, not a matched recall: grace notes are on the page and absent from the encoding (0 in 28,579), so human boxes are inflated and the true figure is at or below 0.971. What it DOES establish is that C = 1.0 is very nearly right for noteheads on this print — so `scan:pitch` at 83.4% is an achievement number, not a fixture artefact. One batch, one publisher, density-selected cells.

### sample `labeling|breitkopf-brahms1|completion-pass|55 cells`

- **unscoreable** — `ceiling:input:hairpin:scan` — ⚠️ MUST BE READ WITH THIS NUMBER: Measured on ONE edition — Breitkopf & Härtel, Brahms 1 mvt 1 — and irreducibly so today: only one labeling batch in the corpus carries a completion pass. Not a claim about scans in general.
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
  - A BOUND, not a point, so it is not scored — but it is now a ceiling rather than a refutation. `scan:hairpin_detect` reads 1.01% against a ceiling measured at AT LEAST 0.80 on this edition, so the detector is at roughly one part in eighty of what a reader recovers. ⚠️ AND THE MATCHED COMPARISON IS WORSE THAN THE CORPUS RATE: on the SAME three pages the human swept, the transcription contains 10,523 detections and ZERO of either hairpin class. The 1-of-99 is not a thin-sample artefact — on this edition it is zero. n = 5 bars is the whole sample the corpus can offer; the same sweep drew 62 ties and 27 slurs, the other two families a fine-tune is documented to delete.

### sample `staff-identity-layer|2026-09-05|n197`

- **unscoreable** — `identity:calibration:ECE`
  - ⚠️ NEITHER TRANSFORM CAN EXPRESS THIS, and forcing it would be worse than omitting it. `pct = 100*(W-M)/(W-F)` needs a defensible WORST CASE. OMR-NED has one (predict nothing scores exactly 1). A calibration error has none: ECE's arithmetic maximum is 1.0 but that is unreachable in practice and carries no meaning, so a percentage against it would be a number with no referent — the exact defect this unit exists to remove. A THIRD transform kind would need an empirical worst case (e.g. the ECE of a constant predictor on this corpus), which nobody has measured. Note also that the estate's own finding is that the ECE improvement from n=197 to n=1571 is NOT calibration — Brier skill vs a constant predictor is +0.0004 and 95.8% of mass sits in one bin — so a score here would be worse than absent. Blocked on WORKS, not records (backlog D5).

### sample `hairpin-cv|11 scanned pages`

- **1.01% of achievable** — `scan:hairpin_detect` — ⚠️ MUST BE READ WITH THIS NUMBER: Scores the DETECTOR only — a classical-CV reader added later carries 118 of 198 <wedge> into the file, so this is not what reaches a user. The ceiling it is measured against (≥0.80) comes from ONE edition, Breitkopf & Härtel, Brahms 1.

### sample `scan-e2e|20rows|reconciliation|dpi600|no-dossier|UNSTAMPED-COMMIT|detail=AllObjects`

- **15.56% of achievable** — `scan:omr_ned` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. Re-scoring these same files under `|Voicing` removes ~29% of the pooled edits — a different accounting of identical output, not an improvement. — scored at `AllObjects`

### sample `scan-e2e|11rows|restamp-composed|10 rows Audiveris completed|detail=AllObjects`

- **16.55% of achievable** — `scan:omr_ned:same_10_rows_as_audiveris` — ⚠️ MUST BE READ WITH THIS NUMBER: A 10-row subset of the retired 11-row scan era, kept only so the Audiveris comparison has two sides. It is NOT the headline and may not be differenced against the 20-row figure. Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. Re-scoring these same files under `|Voicing` removes ~29% of the pooled edits — a different accounting of identical output, not an improvement. — scored at `AllObjects`

### sample `scan-e2e|20rows|reconciliation|normalised-transform1.2.0|afea84ba|detail=AllObjects`

- **20.09% of achievable** — `scan:omr_ned:page_fidelity_15rows` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. Re-scoring these same files under `|Voicing` removes ~29% of the pooled edits — a different accounting of identical output, not an improvement. — scored at `AllObjects`
  - ceiling measured under no flag recorded; invalidated when: NONE from pipeline configuration. This floor is (derived truth vs raw truth) and contains no output of ours, so no flag can move it. It is invalidated only by a change to the page-normalising TRANSFORM (currently 1.2.0) or to the hand-read staves map.
- **18.28% of achievable** — `scan:omr_ned:ceiling_measured_15rows` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. Re-scoring these same files under `|Voicing` removes ~29% of the pooled edits — a different accounting of identical output, not an improvement. — scored at `AllObjects` — ⚠️ CEILING IS FLAG-CONDITIONAL (its estimator reads our output)
  - ceiling measured under `OMR_CONDENSED_PARTS=0`, `OMR_SLOT_STITCH=0`; invalidated when: ⚠️ RE-MEASURE BEFORE QUOTING if OMR_SLOT_STITCH or OMR_CONDENSED_PARTS changes state. The estimator is min(ours, audiveris) over raw `entire staff`, so it reads our export. Measured: flipping OMR_SLOT_STITCH moves our charge 87 -> 1,062 and 90 -> 1,062 on the two Beethoven p3 rows, raising the floor and so raising every % of achievable above it.

### sample `scan-e2e|11rows|restamp-composed|audiveris-5.11|detail=AllObjects`

- **20.81% of achievable** — `competitive:scan:audiveris` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. Re-scoring these same files under `|Voicing` removes ~29% of the pooled edits — a different accounting of identical output, not an improvement. — scored at `AllObjects`

### sample `scan-e2e|20rows|reconciliation|ceiling-corroborated-5|transform1.2.0|afea84ba|detail=AllObjects`

- **29.80% of achievable** — `scan:omr_ned:ceiling_corroborated_subset` — ⚠️ MUST BE READ WITH THIS NUMBER: Scored under musicdiff `AllObjects`, which IGNORES CHORDS and pairs notes by pitch. Re-scoring these same files under `|Voicing` removes ~29% of the pooled edits — a different accounting of identical output, not an improvement. — scored at `AllObjects` — ⚠️ CEILING IS FLAG-CONDITIONAL (its estimator reads our output)
  - ceiling measured under `OMR_CONDENSED_PARTS=0`, `OMR_SLOT_STITCH=0`; invalidated when: ⚠️ RE-MEASURE BEFORE QUOTING if OMR_SLOT_STITCH or OMR_CONDENSED_PARTS changes state — same estimator as the 15-row row. Its five rows are the engine-corroborated subset, where ours and Audiveris agree TODAY; a flag that moves our charge can break that agreement and with it the corroboration.

### sample `scan-e2e|20rows|reconciliation|dpi600|no-dossier|UNSTAMPED-COMMIT`

- **100.00% of achievable** — `scan:staves`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **100.00% of achievable** — `scan:systems`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.
- **83.43% of achievable** — `scan:pitch`
- **74.98% of achievable** — `scan:duration`
- **unscoreable** — `scan:stage4`
  - the harness cannot see this stage at all — no ground truth. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- **unscoreable** — `scan:stage5`
  - the harness cannot see this stage at all — not isolated. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- **unscoreable** — `scan:stage11`
  - the harness cannot see this stage at all — no isolated figure. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.

### sample `prefill|brahms1-breitkopf|phase-C|blind|2026-09-03`

- **94.33% of achievable** — `prefill:precision:blind_out_of_sample`
  - ceiling measured under no flag recorded; invalidated when: no pipeline flag can move this — it is measured from a truth file, a render, a human's labels or another system. Invalidated by a change to that source, not by our configuration.

## What nothing here measures

16 of 56 rows carry no number at all.

- `reading:accidental` (render) — the FIXTURE is unreadable for this family — a score here measures Verovio, not the pipeline
- `reading:barline` (visibility) — CV-detected in CELL-relative coordinates and never expressed in page coordinates — 45 printed against 0 comparable. A frame mismatch, not a miss.
- `engraved:stage2` (visibility) — the harness cannot see this stage at all — not exercised. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage3` (visibility) — the harness cannot see this stage at all — not scoreable. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `scan:stage4` (visibility) — the harness cannot see this stage at all — no ground truth. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `scan:stage5` (visibility) — the harness cannot see this stage at all — not isolated. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage9` (visibility) — the harness cannot see this stage at all — invisible to the metric. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage10` (visibility) — the harness cannot see this stage at all — not exercised. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `engraved:stage11` (visibility) — the harness cannot see this stage at all — no isolated figure. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `scan:stage11` (visibility) — the harness cannot see this stage at all — no isolated figure. A ceiling of ZERO INFORMATION is not a score of 0 and not a score of 100.
- `ceiling:input:notehead:scan` (input) — an UPPER BOUND, not a ceiling to score against. 201 human noteheads against 207 reference notes is a ratio of COUNTS, not a matched recall: grace notes are on the page and absent from the encoding (0 in 28,579), so human boxes are inflated and the true figure is at or below 0.971. What it DOES establish is that C = 1.0 is very nearly right for noteheads on this print — so `scan:pitch` at 83.4% is an achievement number, not a fixture artefact. One batch, one publisher, density-selected cells.
- `ceiling:input:hairpin:scan` (input) — A BOUND, not a point, so it is not scored — but it is now a ceiling rather than a refutation. `scan:hairpin_detect` reads 1.01% against a ceiling measured at AT LEAST 0.80 on this edition, so the detector is at roughly one part in eighty of what a reader recovers. ⚠️ AND THE MATCHED COMPARISON IS WORSE THAN THE CORPUS RATE: on the SAME three pages the human swept, the transcription contains 10,523 detections and ZERO of either hairpin class. The 1-of-99 is not a thin-sample artefact — on this edition it is zero. n = 5 bars is the whole sample the corpus can offer; the same sweep drew 62 ties and 27 slurs, the other two families a fine-tune is documented to delete.
- `scan:input_ceiling:hollow_noteheads` (input) — the page prints 68 half notes and the detector found 8, now 31 — but NOTHING measures how many of those counters are actually closed at 600 dpi bitonal, so there is no denominator of 'recoverable ink'. An INPUT ceiling is the one kind this project has never measured.
- `flag:OMR_CONDENSED_PARTS:oracle_ceiling` (unreachable_configuration) — ⚠️ THE CEILING GRADES A CONFIGURATION THAT CANNOT OCCUR. Verified in this tree 2026-09-07: `condensed_parts` is READ at export.py:3331 (`s.get("condensed_parts")`) and WRITTEN nowhere in tools/omr, so every staff reports 1 and the flag is inert even when set. The -4,557 figure was measured with ORACLE counts. A quoted ceiling for an unreachable configuration is the mirror image of a fabricated 100%: it makes a gap look bigger than the pipeline can act on.
- `identity:calibration:ECE` (none) — ⚠️ NEITHER TRANSFORM CAN EXPRESS THIS, and forcing it would be worse than omitting it. `pct = 100*(W-M)/(W-F)` needs a defensible WORST CASE. OMR-NED has one (predict nothing scores exactly 1). A calibration error has none: ECE's arithmetic maximum is 1.0 but that is unreachable in practice and carries no meaning, so a percentage against it would be a number with no referent — the exact defect this unit exists to remove. A THIRD transform kind would need an empirical worst case (e.g. the ECE of a constant predictor on this corpus), which nobody has measured. Note also that the estate's own finding is that the ECE improvement from n=197 to n=1571 is NOT calibration — Brier skill vs a constant predictor is +0.0004 and 95.8% of mass sits in one bin — so a score here would be worse than absent. Blocked on WORKS, not records (backlog D5).
- `labeling:ledger_zone:screening_rate` (visibility) — ⚠️ A SCREENING RATE IS NOT A DEFECT RATE, AND THIS IS THE CLEAREST CASE IN THE PROJECT OF THE CONFUSION THIS UNIT EXISTS TO FIX. The auditor flags 7 of 102 (6.9%); hand adjudication found ONE real error (~0.9%) — a 7x gap, and six of the seven share one mechanism (a printed ledger line print-merging into the notehead's connected component, pulling the centroid up to a half-step). Both numbers are percentages; only one is a quality figure. A dashboard that prints either alone is wrong: 6.9% overstates the defect sevenfold, and 0.9% understates the reviewer's workload sevenfold. The registry's answer is that they are TWO ROWS with different `stage` semantics — a SCREEN and a DEFECT — never one, and a screen is never scoreable on the achievement axis.
