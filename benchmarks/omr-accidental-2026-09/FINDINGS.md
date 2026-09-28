# Roadmap 2.7 — the printed in-bar accidental: merged, measured, gate half-ready

**CONVENTION ASSUMED:** a printed accidental governs its own head and every later note of the same letter AND octave in the same bar (C21); a natural's cancellation is bar-scoped like any accidental (added by 2.7, NOT registered in `conventions.py`). Courtesy/cautionary accidentals are treated as ordinary accidentals: no `parentheses="yes"` is ever written. **WHAT WOULD FALSIFY IT:** a plate printing courtesy accidentals (parenthesised or small) that the detector boxes as `accidental*`; a plate expecting an alteration to carry across octaves. **NOT CONFIRMED:** Sean (2026-09-24) does not know how Litolff prints courtesy accidentals. Flagged, not decided.

## 1. The merge
`69d64d95` (cut from `848dda47`) MERGED onto `0e0f25da` (`5ad1cb99`); git reported no textual conflict. Semantic conflicts resolved by adapting 2.7 to today's mechanisms (`3d576bb6`): 3.4g refusal → owner abstains `refused_not_an_accidental`; refused / other-staff heads excluded (`heads_excluded`), carry skips heads owned elsewhere; `reads_beyond_cause` = the owned head's staff CLEF so `run_over` re-fires after `fill_clef_gap`; `respell_accidental`'s guard is the enforcement after `fill_part_key` (pinned); stale `reach.KNOWN_GAPS` entry deleted. Found by measuring (`ded9f27b`, `c30a8a5b`): 79 Litolff heads owned by glyphs that DISAGREE were resolved by firing order — now nothing is written (key stands, `heads_contradicted`); census partitions HEADS (`heads_owned = contradicted + applied − doubled copies + unowned`, `heads_balanced`). No convention registered → nothing to renumber. Tests 39 → 50 (7 RED first; inferred-key pin watched failing with the guard removed). Fast tier 3,264 passed / 3 skipped. `staged.check` 264 (origin/main 267): gather_coverage 20→19, reach 27→26, source_text_tests 47→46; no new entry.

## 2. Pricing a GATHER change on saved records
`probe/regather_accidentals.py` (written here; the branch had none) recomputes `Q.ACCIDENTAL_STAFF_POSITION` from `glyph_box`, `cell_staff_space.half_step` and the top line recovered from a notehead's filed position (exact identity), or `Q.STAFF_LINES` in a notehead-less cell. Against a real gather of Litolff p3 (`gather_vs_recompute.py`): 74/74 joined, 69/69 notehead-route rows exact to 1e-9, 5 page-route rows off by ≤1.02 positions (all in notehead-less cells → `no_candidate` by construction); 1% half_step perturbation → 0/74. Real base-vs-arm gather p3 (`real_gather_ab.py`): 1,928/1,928 glyph boxes identical, verdicts differ only in accidental quantities, `<note>` 549=549, `<accidental>` 0→29 (base provenance commit null — `git archive`; arm `3d576bb6` dirty=true from untracked probes, tools/ unchanged; re-decided on `ded9f27b`). Controls (`compare_arms.py`): origin/main == stage-disabled branch, byte-identical MusicXML and N/N standing verdicts — Litolff 119,947 (b332fa00), Breitkopf 286,235 (eea6dc93), engraved 5,545 (7eb02bdf).

## 3. Numbers (`out/measure/census-*-c30a8a5b.json`, `owner-fate-*.json`)
| | Litolff 7dbee148 | Breitkopf e5561c8b | engraved 23c01008 |
|---|--:|--:|--:|
| gathered | 1,531 | 6,533 | 22 |
| decided / ambiguous / no_candidate / refused | 712 / 20 / 799 / 0 | 4,516 / 43 / 1,974 / 0 | 20 / 0 / 2 / 0 |
| heads / contradicted | 603 / 79 | 3,571 / 734 | 20 / 0 |
| written / unowned (2.8 held) | 214 / 310 (213) | 233 / 2,604 (2,126) | 15 / 5 |
| `<accidental>` | 0 → 216 (2 doubled copies) | 0 → 233 | 0 → 15 |
| `<alter>` | 1,189 → 1,151 | 315 → 503 | 106 → 95 |
| `<note>` | 8,758 = | 7,872 = | 666 = |
| carried in bar | 152 | 667 | 11 |
Litolff alter transitions: −1→0 113, 0→−1 46, 0→+1 22, 0→+2 7, −1→+1 6, −1→+2 1. Breitkopf: 0→−1 161, 0→+1 58, −1→0 33, −1→+1 11, 0→+2 2, −1→+2 1. Engraved against the encoding (`engraved_encoding_check.py`): 15/15 sound the encoded alteration; one-part-shift control 4/15. ⚠️ 85 (Litolff) / 378 (Breitkopf) `accidentalDoubleSharp` detections are almost certainly misclassified. Header double use (`header_overlap.py`): accidental* glyphs also counted as key markers — Litolff 12 (no_candidate), Breitkopf 64 (2 decided).

## 4. Pairing tolerance
Re-running `gap_histogram.py` on the two records reproduces the branch's `anchor-control-*-0.715.json` byte for byte (dx per 0.25 sp: Litolff 500·519·116·30·15·14·14·4; Breitkopf 2269·2949·212·74·77·117·76·51; real p3 24·26·3·1·1·1·0·0). ⚠️ The 1.4-position dy bound was cut from the UNCORRECTED (`--anchor-flat 0.5`) histogram (the bins quoted in `ownership.py` are `gap-histogram-litolff.json`'s); at the 0.715 anchor GATHER applies there is no cliff at 1.4, and Litolff's flats measure 0.580 unbiased vs 0.715 applied. Decided owners by |dy| (`owner_dy.py`): Litolff 462 ≤0.5 / 168 0.5–1.0 / 82 1.0–1.4; Breitkopf 3,863 / 331 / 322. Bound NOT changed (print before default); crops carry dy.

## 5. THE GATE
Reach, ≥18 `<accidental>` on Litolff pdf-index 3: **15 on the acceptance record — NOT met** (39 owned heads on the page: 15 written, 18 bars held out by 2.8, 4 contradicted, 2 duration_narrowed); **29 on the one-page real gather**. 0 wrong, strings bars 49–56 (system 0 cells 0–7, staves 7–10): 38 glyphs, 25 decided, 13 no_candidate; 7 of 25 reach the file. `out/print/acc-01…28.png`: 25 decided + 3 abstained controls, shuffled, unlabelled; 600 dpi; glyph red, head blue, filed staff named + its 5 lines green; frame control contrast 152.5–184.7, `--break-frame` refuses 28/28. Key: `out/print/crop-manifest.json` (`VERDICT_none_yet: null`) and `prior-human-evidence-KEY.json` — read after adjudicating. Not claimed.

## 6. Human evidence reaches the owner
`regather_accidentals.py --sidecar …/sean-viola-p3/sean.sidecar.json`: refused_not_an_accidental 0 → 5, all staff/3/0/9 bars 49–56; two (glyph/3/0/9/5/3 human_not_a_symbol = acc-14, glyph/3/0/9/7/2 human_other_staff = acc-13) are DECIDED owners in the machine-only arm.

## 7. Caveats
Whole-movement records are 09-23 gathers re-decided on this tree; every comparison is base vs arm on one tree. Page-route recompute rows are harmless only by construction. Contradicted heads keep the key's alteration (counted, not read). Engraved check is of the sound, not the drawn glyph. `unowned` is dominated by 2.8's hold-out. No Breitkopf crops (the gate names Litolff).
