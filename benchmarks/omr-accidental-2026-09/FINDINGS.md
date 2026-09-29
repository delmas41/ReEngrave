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

**Path: STAGED.** Branch `claude/accidental-2.7b`: `d6a06308` rule + tests · `d56ab7c5` header reads the key's run · `96abccff` O(1) neighbour (the first arm was quadratic) · `09157d97` the head's own ledger is no rung. **CONVENTION (Sean, 2026-09-27, stated, not assumed):** *"notes should never be that far away from a staff unless there are ledger lines close to the staff connecting the note conceptually to the staff."* Base = `a5f7cf58`, arm = `09157d97`, both through `probe/regather_accidentals.py` on ONE record each (base vs arm on one tree, §6b). ⚠️ An interim commit (`478cddbe`, a coordinating session) recorded this lane as killed; it was not — this section supersedes that one.

## 2.7b.1 The five, measured (`probe/nearer_staff.py`, acceptance record 7dbee148 re-decided on a5f7cf58)

Control: the probe recomputes `Q.GLYPH_BAND_DISTANCE` from `Q.STAFF_LINES` + `bbox_page_px` — 12,026 / 12,026 rows exact (Litolff), 49,590 / 49,590 (Breitkopf), 260 / 260 (engraved); `--break-control` (spacing ×1.01) → 11,959 / 12,026 and 260 / 260 differ. Outputs `out/measure-2.7b/nearer-staff-*.json`.

| crop | head | filed staff | from filed (sp) | from staff ABOVE (sp) | twin on near staff | `glyph_owner` | `unladdered_signal` | kept rungs toward filed |
|--:|---|--:|--:|--:|---|---|---|--:|
| 26 | glyph/3/0/8/2/3 | 8 | 3.635 above | 2.291 | no | none | none (conf ≥ its gate) | 0 |
| 20 | glyph/3/0/8/6/12 | 8 | 3.550 above | 2.373 | no | none | would_fire (0 of 3) | 0 |
| 4 | glyph/3/0/9/2/6 | 9 | 3.670 above | 2.400 | no | none | none (conf ≥ its gate) | 0 |
| 23 | glyph/3/0/9/6/8 | 9 | 3.485 above | 2.588 | no | none | would_fire (0 of 3) | 0 |
| 13 | glyph/3/0/9/7/5 | 9 | 3.605 above | 2.466 | no | none | would_fire (0 of 3) | 0 |
| 2 (control) | glyph/3/0/8/7/1 | 8 | 3.605 above | 2.320 | **yes** | staff 7, `ladder` | none | 0 |

⚠️ **THE LEDGER'S DIRECTION IS INVERTED, AND THE TREE SETTLES IT.** ROADMAP 2.7 says the five are *"filed … on the staff ABOVE the true one"*. Every one stands **ABOVE its filed staff**, 2.3–2.6 spaces under the staff above — a low note on ledger lines UNDER the staff above, cut into the lower staff's cell by its 4–6-space pad. Sean's *"WRONG STAFF (the staff above)"* names the staff the note BELONGS to; they are filed one staff too LOW. The rule is symmetric; the wording is not.

No rung, kept or refused, stands between any of the six and its filed staff, nor toward the staff above in the SAME cell (those rungs are cut into the upper staff's cells). Sean's confirmed heads (18 heads, 21 crops) stand **0.000–2.440** spaces from their filed staff, each nearer its own staff than any other by ≥ 1.19; the five stand **3.485–3.670**.

⚠️⚠️ **ON A FRESH GATHER THE FIVE ARE ALREADY CLOSED BY 2.6, NOT BY THIS.** A real one-page gather of Litolff p3 on a5f7cf58 (`python3 -m tools.omr.staged <pdf> --pages 3 --no-surya --no-ocr --weights …hollow-graft-shift09…`) gives all six a twin on the staff above and `glyph_owner` awards each there (5 `distance`, crop 2 `ladder`); their accidentals abstain `no_candidate`, head `owned_by_another_staff`. The acceptance whole-movement records were gathered BEFORE 2.6's GATHER change (category + IoU 0.3), so the five had no twin there. **The acceptance records need a re-gather before the ownership figures on them describe today's reader** — not done here (GATHER; 12.8 h on Litolff).

## 2.7b.2 The population (grid over N, M; `nearer-staff-*.json`)

Signature = filed > N, the adjacent staff on the head's side ≤ M and nearer than the filed one, no KEPT rung (not the head's own line) toward the filed staff. The nearest other staff is always the adjacent one on the head's side (1,677 / 1,677 Litolff heads with filed > 2, near ≤ 3.5), which is all the rule reads.

| record | signature (N 3.0, M 2.75) | twin on near → `glyph_owner` decides | awarded to the near staff | already refused | **newly refused: no twin (the 2.6 "38" family)** |
|---|--:|--:|--:|--:|--:|
| Litolff whole (acceptance) | 1,434 | 772 | 767 (611 distance, 156 ladder; 3 `tied`, 2 `range_veto` kept on filed) | 373 (clipped 334, too_narrow 39) | **293** |
| Litolff p3, fresh gather | 38 | 28 | 28 | 9 (clipped) | **1** |
| engraved | 17 | 12 | 12 | 6 | **0** |
| Breitkopf whole (acceptance) | 3,124 | 1,881 | 1,828 | 890 | **421** |

The probe's prediction and the arm agree exactly on both scans (Litolff 293 = 293, Breitkopf 421 = 421). Litolff's 293: all 16 pages, 186 below their filed staff and 107 above; filed-distance histogram 3.0:5 · 3.25:44 · 3.5:117 · 3.75:88 · 5.25–5.75:36 (the pad's edge, then the 6-space pad); 206 of 293 are also what `unladdered` would flag. `glyph_owner` agrees with the signature wherever the near staff detected the ink: 767 of 772 twins go to the near staff (distance is a correlated witness here; the ladder, 156, is not). The probe's "wrong_staff_hit 1" on Breitkopf is a subject-key coincidence with a Litolff crop, not a Breitkopf adjudication.

**Bands.** N = **3.0** — the empty interval between the confirmed 2.440 and the wrong-staff 3.485; about half the ~5.9-space inter-staff air on this plate. M = **2.75** — wrong-staff max 2.588, next quarter. Neighbours (Litolff / Breitkopf newly refused): N 2.5 → 306 / 446, **3.0 → 293 / 421**, 3.25 → 273 / 389; M 2.5 → 281 / 408, **2.75 → 293 / 421**, 3.0 → 295 / 430 — flat, not on a slope. Confirmed heads reached: 0 of 18 at every N ≥ 2.5. `OWN_LEDGER_MAX_SPACES` = **0.5**: of 79 far heads the first cut kept on a rung, 43 were kept by a rung 0.00–0.37 spaces from the head — its own line (a trial crop showed a note on a ledger above the staff BELOW it, kept on the staff above) — and the rest stand at 0.63+ (`probe/kept_rungs.py`); 36 remain kept by a real rung.

**Why not `unladdered` re-enabled.** Its one witness is a rung, and that is the witness that failed (ledger recall; net negative on the print-confirmed join — `UNLADDERED_SHIPS`). It would also MISS 2 of the 5 (26, 4: confidence above its gate). The new rule adds the page's own staff geometry as a second witness from a different source — another staff near — so a real note far from its staff and near nothing is untouched, and it yields wherever the near staff detected the same ink.

## 2.7b.3 The rule (`notehead_precision.py`, after `too_narrow`)

`belongs_to_a_nearer_staff`: filed > `NEARER_STAFF_FILED_MIN_SPACES` (3.0); the adjacent staff on the head's side ≤ `NEARER_STAFF_NEAR_MAX_SPACES` (2.75) and nearer; no KEPT rung of the head's cell between it and the filed staff (the 3.4g-2 `ledger_is_not_a_ledger` VERDICT is read, never the box; a rung within `OWN_LEDGER_MAX_SPACES` of the head is its own line and counts for nobody); and no `Q.GLYPH_BAND_DISTANCE` row naming the near staff — else it yields to `glyph_owner` (`detail.nearer_staff_signal.yields_to_glyph_owner`). Dropped, never relocated; export counts `not_a_notehead:belongs_to_a_nearer_staff`. **The accidental follows its head:** where a glyph's best candidate is such a head, `accidental_owner` abstains `head_belongs_to_a_nearer_staff` instead of re-pairing (a sliver or a human's *nothing* still lets it re-pair, as 2.7 pinned). Both new reasons are census buckets; `unaccounted` stays 0.

## 2.7b.4 The header exclusion

Crop 7's glyph (`glyph/3/0/8/0/2`) abstains `no_candidate` on the acceptance record, **and that is the wrong reason** — a geometry miss (4 heads in the cell, none in the window) that becomes a pairing the day a head stands at its height. That record has NO marker rows on the staff (`read_by: fitted_no_markers`: gathered before 2.12a), so no rule can name it there. On the fresh p3 gather a `Q.KEYSIG_MARKER` row joins it exactly (x 664, class `accidentalFlat`, y_center 428 vs 428.5), inside the run the key reader counted, and the arm abstains **`is_a_key_signature_marker`**.

⚠️ The first cut (any marker row at the glyph's point) was **wrong, and measured wrong before it was trusted**: on the fresh gather it took Sean's CONFIRMED crop 12 (Violino I's in-bar natural, boxed twice at x 1007/1008 as `accidentalFlat` + `accidentalNatural`; the flat box admitted as a 4th marker 2.8 spaces past the three-flat run) and staff 3's natural in a run the key reader refused as mixed kinds. The rule reads `header.marker_run_members` — the slot arithmetic `_marker_run` reads the key from, factored into `_slot_centres` so the two cannot drift — so only markers the reader COUNTED exclude, and the join requires the marker's `detector_class` to be the glyph's own. Fresh p3: 8 header glyphs `no_candidate` → `is_a_key_signature_marker`, 0 decided pairings lost, crop 12 unchanged. Litolff whole: 2. Breitkopf whole: 32. On neither whole record did a DECIDED pairing become a marker — all 34 were `no_candidate` before.

## 2.7b.5 Base vs arm (`probe/compare_2_7b.py`: every changed verdict attributed, `unexplained` must be 0)

Control: engraved base run twice → 5,574 / 5,574 standing verdicts identical, MusicXML byte-identical.

| | Litolff whole | Litolff p3 fresh gather | engraved | Breitkopf whole |
|---|--:|--:|--:|--:|
| heads refused `belongs_to_a_nearer_staff` | **293** | **1** | 0 | **421** |
| accidental → `head_belongs_to_a_nearer_staff` | 42 | 1 | 0 | 52 |
| accidental → `is_a_key_signature_marker` | 2 | 8 | 0 | 32 |
| other changed verdicts | 26 `accidental` (25 on a refused head, 1 in its bar) | 1 `accidental` on the refused head | 0 | 46 `accidental` (42 on a refused head, 4 in its bar) |
| unexplained | **0** | **0** | **0** | **0** |
| `<note>` | 8,758 → 8,697 | 549 → 548 | 666 = | 7,872 → 7,859 |
| `<accidental>` | 216 → 208 | 29 → 28 | 15 = | 233 → **234** |
| `<alter>` | 1,151 → 1,118 | 111 → 110 | 95 = | 503 → 498 |
| accidental census `unaccounted` / `heads_balanced` | 0 / true | 0 / true | 0 / true | 0 / true |

Litolff: 293 refused, 61 fewer `<note>` — most refused heads were already held out by 2.8 (`bar_does_not_add_up`) or `duration_narrowed`; bars whose only notes were refused become padded empty measures (*we read nothing*, not silence). **pdf-index 3 (bars 49–82) on the acceptance record: `<accidental>` 15 → 14, `<note>` 564 → 562** (`probe/count_in_bars.py`). The one `<accidental>` lost is crop 13's, the only one of the five that reached the file (P10, written a staff too low). **Breitkopf: 421 refused, `<note>` −13, `<accidental>` +1** — not a new reading (no `accidental` verdict turned printed on the arm): 38 bars stop being held out (`bars_held_out_sum` 4,532 → 4,494; `bar_does_not_add_up` 18,802 → 18,480 notes) once another staff's ink leaves them, and one of those bars carries an already-decided printed accidental. The reach half of the 2.7 gate (≥ 18) is further away, not nearer: 2.7b removes wrong writes and adds none.

**The gate (`out/measure-2.7b/sean-heads-litolff.json`, `probe/sean_heads_2_7b.py`):** of Sean's 28 crops exactly FIVE change — 4, 13, 20, 23, 26 → head refused `belongs_to_a_nearer_staff`, accidental → `head_belongs_to_a_nearer_staff`; none is written on the lower staff any more. The other 23 are unchanged verdict for verdict: **all 20 confirmed pairings kept, 0 confirmed heads lost**; crop 2 unchanged (the contest's, `ladder`); crop 3 still `too_narrow`; crop 7 still `no_candidate` on this record (no marker rows — see 2.7b.4).

## 2.7b.6 Print check (`probe/crop_nearer_staff.py`) — for Sean, NOT adjudicated

`out/print/2.7b-01…16.png` + `2.7b-crop-manifest.json` (`VERDICT_none_yet: null` on every crop): **12 newly refused + 4 kept** Litolff heads, shuffled and unlabelled, seed 277, Sean's five excluded (answered). 600 dpi; the FILED staff's five lines GREEN, the nearest other staff's ORANGE, the head BLUE-bracketed on its exact `bbox_page_px`, a spacing ruler at the left. Frame control (`crop_inferred._frame_ok`, both staves): 16 / 16 pass (contrast 33.8–214.7); `--break-frame` refuses 16 / 16. The four KEPT are all kept by the rung exception (no in-band candidate is recorded — the signal stops at the filed test); crop 04 is one that already looks like the orange staff's note (a head above the lower staff with its ledger under it, kept by a box between it and the upper staff) — the rung exception is the weakest part of the rule and these four are where to look. The one fresh-gather refusal (`glyph/3/1/1/14/5`, a flatted half note on a ledger above staff 2) is refused on the acceptance record too and is crop 05. Breitkopf supplement: `out/print/2.7b-brk-01…08.png` + `2.7b-brk-crop-manifest.json` — 6 refused + 2 kept (seed 277), frame control 8 / 8 pass (126.4–242.4), `--break-frame` refuses 8 / 8. Breitkopf pool: 420 refused (Sean's five excluded by subject key; one Breitkopf key coincides), 91 kept by a rung.

## 2.7b.7 What this does not do

- Does not re-gather the acceptance records (the five are a pre-2.6 artefact there; on a fresh gather 2.6 already puts them on the right staff).
- The accidental of a head `glyph_owner` awards elsewhere still abstains `no_candidate` on the cut-from staff, and nothing puts it on the winner's twin (the twin staff's own accidental box does that, if detected) — 2.7 pinned the re-pair behaviour for `owned_by_another_staff`; changing it is its own item.
- 36 Litolff heads past both bands are kept by a real rung toward the filed staff; rung recall is the known weak witness, and a kept rung that is really the other staff's is not examined beyond the four kept crops.
- Tests: `tools/omr/tests/test_staged_nearer_staff.py` (24) on `fixtures/nearer_staff_litolff_p3.json` (the measured geometry of all 25 adjudicated heads, `probe/extract_nearer_fixture.py`). RED first: 11 failed / 8 passed against a5f7cf58; 3 more (run, class, mixed) failed against d6a06308; the own-line test failed against 96abccff.

### §2.7b.8 — Sean's verdicts on the 24 recoloured crops (2026-09-28)

Raw: `1 G 2-9 O 10 N 11 O 12-13 O 14 G 15-17 O 18 G 19-24 O` (sheet #01–16 =
Litolff `2.7b-01..16`, #17–24 = Breitkopf `2.7b-brk-01..08`; verdicts written
into both manifests). Against the hidden key:

| the rule | Sean | n | reading |
|---|---|--:|---|
| refused (`belongs_to_a_nearer_staff`) | O | **18 / 18** | every refusal right; no real note lost |
| kept (a rung toward the filed staff) | G | 3 | right |
| kept | O | **2** (#4 `glyph/10/1/2/12/6`, #22 `glyph/4/1/2/8/31`) | missed — belongs to the nearer staff |
| kept | N | 1 (#10 `glyph/8/0/6/12/7`) | not a note |

**The refusal is sound; the rung EXCEPTION is not** — 3 of 6 heads it kept
were wrong. A rung credited as "toward the filed staff" for a head that
belongs to the other staff is the ledger-direction question of Sean's
convention (DECISIONS 2026-09-28: the ledger lines lie between a note and
ITS staff) → handed to 2.6c as RED cases. Sean also noted the colours swap
above/below between crops: colour follows ROLE (filed vs nearer), so green is
on top when the filed staff is the upper one; labels carry it.
