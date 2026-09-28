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

---

# §2.7b — a head filed on a staff it does not belong to; the header exclusion as a rule

**Path: STAGED.** Branch `claude/accidental-2.7b` (`d6a06308` rule + tests, `d56ab7c5` header run, `96abccff` O(1) neighbour). **CONVENTION (Sean, 2026-09-27, stated, not assumed):** *"notes should never be that far away from a staff unless there are ledger lines close to the staff connecting the note conceptually to the staff."* Base = `a5f7cf58`, arm = `96abccff`, both run by `probe/regather_accidentals.py` on ONE record each (base vs arm on one tree, §6b).

## 2.7b.1 The five, measured (`probe/nearer_staff.py`, acceptance record 7dbee148 re-decided on a5f7cf58)

Control: the probe recomputes `Q.GLYPH_BAND_DISTANCE` from `Q.STAFF_LINES` + `bbox_page_px` — 12,026 / 12,026 rows exact (Litolff), 260 / 260 (engraved); `--break-control` (spacing ×1.01) → 11,959 / 12,026 and 260 / 260 differ. Output `out/measure-2.7b/nearer-staff-litolff-base.json`.

| crop | head | filed staff | from filed (sp) | from staff ABOVE (sp) | twin on near staff | `glyph_owner` | `unladdered_signal` | kept rungs toward filed |
|--:|---|--:|--:|--:|---|---|---|--:|
| 26 | glyph/3/0/8/2/3 | 8 | 3.635 above | 2.291 | no | none | — (conf ≥ gate) | 0 |
| 20 | glyph/3/0/8/6/12 | 8 | 3.550 above | 2.373 | no | none | would_fire (0 of 3) | 0 |
| 4 | glyph/3/0/9/2/6 | 9 | 3.670 above | 2.400 | no | none | — (conf ≥ gate) | 0 |
| 23 | glyph/3/0/9/6/8 | 9 | 3.485 above | 2.588 | no | none | would_fire (0 of 3) | 0 |
| 13 | glyph/3/0/9/7/5 | 9 | 3.605 above | 2.466 | no | none | would_fire (0 of 3) | 0 |
| 2 (control) | glyph/3/0/8/7/1 | 8 | 3.605 above | 2.320 | **yes** | staff 7, `ladder` | — | 0 |

⚠️ **THE LEDGER'S DIRECTION IS INVERTED, AND THE TREE SETTLES IT.** ROADMAP 2.7 says the five are *"filed … on the staff ABOVE the true one"*. Every one of them stands **ABOVE its filed staff**, 2.3–2.6 spaces under the staff above — a low note on ledger lines UNDER the staff above, cut into the lower staff's cell by its 4–6-space pad. Sean's *"WRONG STAFF (the staff above)"* names the staff the note BELONGS to. They are filed one staff too LOW. The rule is symmetric and does not care; the wording does.

No rung, kept or refused, stands between any of the six and its filed staff, and none toward the staff above in the SAME cell either (those rungs are cut into the upper staff's cells). Sean's confirmed heads (18 heads, 21 crops) stand **0.000–2.440** spaces from their filed staff, and every one is nearer its own staff than any other by ≥ 1.19 spaces; the five stand **3.485–3.670** from it.

⚠️⚠️ **ON A FRESH GATHER THE FIVE ARE ALREADY CLOSED BY 2.6, NOT BY THIS.** A real one-page gather of Litolff p3 on a5f7cf58 (`python3 -m tools.omr.staged … --pages 3 --no-surya --no-ocr`, hollow-graft-shift09) gives all six a twin on the staff above and `glyph_owner` awards each there (5 `distance`, crop 2 `ladder`); their accidentals abstain `no_candidate` with the head `owned_by_another_staff` (`out/measure-2.7b/nearer-staff-litolff-p3-real-gather.json`). The acceptance whole-movement records were gathered on 09-22/23 BEFORE 2.6's GATHER change (category + IoU 0.3), so the five had no twin there. **The acceptance records need a re-gather before the ownership figures on them mean today's reader** — not done here (GATHER, 12.8 h on Litolff).

## 2.7b.2 The population (`nearer-staff-*.json`, grid over N, M)

Signature = filed > N, another staff ≤ M and nearer than the filed one, no kept rung toward the filed staff. The nearest other staff is ALWAYS the adjacent one on the head's side (1,677 / 1,677 Litolff heads with filed > 2, near ≤ 3.5), which is what the rule reads.

| record | signature (N 3.0, M 2.75) | twin on near → `glyph_owner` decides | of which awarded to the near staff | already refused (clipped 331, too_narrow 39) | **newly refused, no twin (the 2.6 "38" family)** |
|---|--:|--:|--:|--:|--:|
| Litolff whole (acceptance) | 1,388 | 739 | 734 (603 distance, 131 ladder; 3 tied, 2 range_veto kept on filed) | 370 | **283** |
| Litolff p3, fresh gather | 38 | 28 | 28 | 18 | **1** |
| engraved | 17 | 12 | 12 | 6 | **0** |
| Breitkopf whole | _not run — the lane was killed before the Breitkopf arm_ |

The 283 spread over 16 pages; 182 below their filed staff, 101 above; filed-distance histogram 3.25:40 · 3.5:113 · 3.75:88 · 5.25–5.75:35 (a cliff below 3.25 — 4 heads in the 3.0 bin); 205 of 283 are ALSO what `unladdered` would flag.

**Bands.** N = **3.0** (the empty interval between confirmed 2.440 and wrong-staff 3.485; ~half the 5.9-space inter-staff air on this plate). M = **2.75** (wrong-staff max 2.588, next quarter). Population at the neighbours: N 2.5 → 295, 3.0 → 283, 3.25 → 264; M 2.5 → 271, 2.75 → 283, 3.0 → 284 — flat, not on a slope. Reach on the confirmed heads: 0 of 18 at every N ≥ 2.5.

**Why not `unladdered` re-enabled.** Its witness is one (a rung), and that is the witness that failed (ledger recall; net negative on the print-confirmed join, `UNLADDERED_SHIPS`). It would also MISS 2 of the 5 (crops 26, 4: confidence above its gate). The new rule adds the page's own staff geometry — another staff near — so a real note far from its staff and near nothing is untouched, and it yields to the ownership contest wherever the near staff detected the ink.

## 2.7b.3 The rule (in `notehead_precision.py`, after `too_narrow`)

`belongs_to_a_nearer_staff`: filed > 3.0 sp, adjacent staff on the head's side ≤ 2.75 sp and nearer, no KEPT rung (`ledger_is_not_a_ledger` not True — the verdict is read, not the box) of the head's cell between it and the filed staff, and no `Q.GLYPH_BAND_DISTANCE` row naming the near staff (else `yields_to_glyph_owner`, recorded in `detail.nearer_staff_signal`). Dropped, never relocated; export counts it `not_a_notehead:belongs_to_a_nearer_staff`. The accidental FOLLOWS its head: where the glyph's best candidate is such a head, `accidental_owner` abstains `head_belongs_to_a_nearer_staff` (the other refusals — a sliver, a human's *nothing* — still let it re-pair, as 2.7 pinned). Kept by the rung exception on Litolff: 79 heads past both bands.

## 2.7b.4 The header exclusion

Crop 7's glyph (`glyph/3/0/8/0/2`) abstains `no_candidate` on the acceptance record **and that was the wrong reason** — a geometry miss (4 heads in the cell, none in the window) that becomes a pairing the day a head stands at its height. The acceptance record has NO marker rows on that staff (`read_by: fitted_no_markers` — gathered before 2.12a). On the fresh p3 gather a marker row joins it exactly (x 664, y_center 428 vs 428.5) and on the arm it abstains **`is_a_key_signature_marker`**.

⚠️ The first cut (any marker row at the glyph's point) was **wrong, and measured wrong before it was pushed**: on the fresh gather it took Sean's CONFIRMED crop 12 (Violino I's in-bar natural, boxed twice at x 1007/1008 as `accidentalFlat` + `accidentalNatural`; the flat box admitted as a 4th marker 2.8 spaces past the three-flat run) and staff 3's natural in a run the key reader refused as mixed kinds. The rule now reads `header.marker_run_members` — the same slot arithmetic `_marker_run` reads the key from (factored into `_slot_centres`), so only markers the reader COUNTED exclude — and the join requires the marker's `detector_class` to be the glyph's class. Fresh p3: 8 header glyphs `no_candidate` → `is_a_key_signature_marker`, 0 decided pairings lost, crop 12 unchanged. Whole Litolff record: 2 (it has almost no accidental-shaped markers).

## 2.7b.5 Base vs arm (`probe/compare_2_7b.py`; every changed verdict attributed, `unexplained` must be 0)

Controls: engraved base run twice → 5,574 / 5,574 standing verdicts identical, MusicXML byte-identical. Fixture tests RED first (below).

| | Litolff whole | Litolff p3 fresh gather | engraved | Breitkopf whole |
|---|--:|--:|--:|--:|
| heads refused `belongs_to_a_nearer_staff` | **283** | **1** | 0 | _not run — the lane was killed before the Breitkopf arm_ |
| accidental → `head_belongs_to_a_nearer_staff` | 42 | 1 | 0 | _not run — the lane was killed before the Breitkopf arm_ |
| accidental → `is_a_key_signature_marker` | 2 | 8 | 0 | _not run — the lane was killed before the Breitkopf arm_ |
| other changed verdicts | 26 `accidental` (25 on a refused head, 1 carry in its bar) | 1 `accidental` on the refused head | 0 | _not run — the lane was killed before the Breitkopf arm_ |
| unexplained | **0** | **0** | 0 | _not run — the lane was killed before the Breitkopf arm_ |
| `<note>` | 8,758 → 8,701 | 549 → 548 | 666 = | _not run — the lane was killed before the Breitkopf arm_ |
| `<accidental>` | 216 → 208 | 29 → 28 | 15 = | _not run — the lane was killed before the Breitkopf arm_ |
| `<alter>` | 1,151 → 1,120 | 111 → 110 | 95 = | _not run — the lane was killed before the Breitkopf arm_ |
| census `unaccounted` / `heads_balanced` | 0 / true | 0 / true | 0 / true | _not run — the lane was killed before the Breitkopf arm_ |

Litolff: 283 refused but only 57 fewer `<note>`: most were already held out by 2.8 (`bar_does_not_add_up` 5,195 → 5,050) or narrowed; 18 bars whose only notes were refused become padded empty measures (`empty_bars_padded` 844 → 862 — *we read nothing*, not silence). **pdf-index 3 (bars 49–82) on the acceptance record: `<accidental>` 15 → 14, `<note>` 564 → 562** — the one lost is crop 13's, the only one of the five that reached the file (P10, written a staff too low). The reach half of the 2.7 gate (≥ 18) is further away, not nearer: 2.7b removes wrong writes, it adds none.

**The gate (`out/measure-2.7b/sean-heads-litolff.json`, `probe/sean_heads_2_7b.py`):** of Sean's 28 crops exactly FIVE heads change — 4, 13, 20, 23, 26 → refused `belongs_to_a_nearer_staff`, each accidental → `head_belongs_to_a_nearer_staff`, none written on the staff below any more. The other 23 are unchanged verdict for verdict: **all 20 confirmed pairings kept, 0 confirmed heads lost**; crop 2 unchanged (the contest's); crop 3 still `too_narrow`.

## 2.7b.6 Print check (`probe/crop_nearer_staff.py`)

_Not cut — the lane was killed before the print check. `probe/crop_nearer_staff.py` is written; run it to cut 12 newly refused heads + 4 kept + Sean's five under `out/print/2.7b-*`._

## 2.7b.7 What this does not do

- Does not re-gather the acceptance records (the five are a pre-2.6 artefact there; on a fresh gather 2.6 already puts them on the right staff).
- The accidental of a head `glyph_owner` awards elsewhere still abstains `no_candidate` on the cut-from staff, and nothing puts it on the winner's twin (the twin staff's own accidental box does that, if it was detected) — noted, not changed: 2.7 pinned the re-pair behaviour for `owned_by_another_staff` and changing it is its own item.
- Kept by the rung exception: 79 Litolff heads. Rung recall is the known weak witness (`UNLADDERED_SHIPS`); a kept rung that is really the other staff's is not examined here — two such crops are in the print check.
