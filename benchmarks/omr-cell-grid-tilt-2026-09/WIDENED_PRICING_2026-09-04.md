# The widened scan gate PRICES the tilt fix — a −233-edit win that sits exactly on the exposure

**Question.** `RESULTS_TILT_COST.md` closed with "the fix is real and the
instrument is blind": localizing each cell's grid recovers every hand-traced
displacement, and the 5-row scan benchmark moved 2 edits of 7894 because 0.4%
of its cells carry the defect. Its §5 said the missing measurement is *a scored
page that actually tilts*. The gate has since widened to 11 verified rows
(`84a5ccac`), including second pages of the same editions — exactly where the
deep-page tilt was measured. This asks whether the widened gate contains the
pricing pages, prices the flag on it, re-verifies the engraved no-op, and
lands the named ship prerequisite (`recut_cells.frame_mismatch` comparing the
unlocalized grid).

**Answer, in one line: yes on all four.** The widened pool carries 8.6% of its
cells past the parity-flip line (was 0.4%), the A/B moves **pooled 0.8387 →
0.8345, −233 edits, with −217 of them on exactly the three tilted rows** and
the zero-exposure Brahms row unchanged to the edit; the engraved control is
byte-identical; the `frame_mismatch` change is in with tests.

Tree: `claude/tilt-pricing-widened` = the widened-gate line (`0487be1f`)
merged with the tilt line (`claude/tilt-crosscheck`) — the FIRST tree holding
both the 11-row gate and `OMR_CELL_LINE_TRACE`. Weights pinned to scan
production (`hollow-graft-shift09-2026-09-04`) via `OMR_SCAN_EVAL_WEIGHTS` for
both arms. The flag remains **default OFF** on this branch; flipping it is the
ship decision this document is input to.

```bash
# 1. exposure — the probe now reads the widened works.json (11 rows)
python3 benchmarks/omr-cell-grid-tilt-2026-09/probe_scan_corpus_offsets.py
# 2. the A/B, one variable, both arms on this tree
OMR_SCAN_EVAL_WEIGHTS=.../deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
  python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --tag wbase \
      --out benchmarks/omr-cell-grid-tilt-2026-09/results-widened-baseline.json
OMR_CELL_LINE_TRACE=1 OMR_SCAN_EVAL_WEIGHTS=... \
  python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --tag wtilt \
      --out benchmarks/omr-cell-grid-tilt-2026-09/results-widened-localized.json
# 3. where exactly the flag moved anything, cell by cell
python3 benchmarks/omr-cell-grid-tilt-2026-09/compare_ab_cells.py
```

---

## 1. Exposure: the widened gate CONTAINS the pricing pages

Share of five-line cells whose grid sits past the 0.25-space parity-flip line,
per row of the widened gate (`probe_scan_corpus_offsets.json`, refreshed over
the 11-row `works.json` — the committed 5-row-era figures survive in
RESULTS_TILT_COST.md §3):

| row | cells | past flip | share | max offset (sp) |
|---|--:|--:|--:|--:|
| beethoven-sym5-mvt1-984073-**p2** | 341 | 78 | **22.9%** | 0.688 |
| brahms-sym1-mvt1-317803-**p2** | 202 | 32 | **15.8%** | 0.734 |
| beethoven-sym5-mvt1-575951-**p2** | 352 | 41 | **11.6%** | 0.581 |
| mahler-sym5-mvt1-local-p2 | 153 | 5 | 3.3% | 0.350 |
| dvorak-sym9-mvt1-405834-p6 | 105 | 3 | 2.9% | 0.440 |
| mahler-sym5-mvt1-local-p3 | 117 | 2 | 1.7% | 0.466 |
| dvorak-sym9-mvt1-405834-p5 | 135 | 1 | 0.7% | 0.364 |
| beethoven-sym5-mvt1-984073-p1 | 192 | 1 | 0.5% | 0.254 |
| beethoven-sym5-mvt1-575951-p1 | 192 | 0 | 0.0% | 0.197 |
| brahms-sym1-mvt1-317803-p1 | 112 | 0 | 0.0% | 0.094 |
| bach-brandenburg3-mvt1-468678-p1 (stress, unpooled) | 359 | 0 | 0.0% | 0.222 |

**Pooled over the 10 pooled rows: 163 of 1901 cells past the flip line —
8.6%**, against the old 5-row benchmark's 0.4%. That is the "8.7% sampled
deeper into the same editions" population from RESULTS_TILT_COST.md §3,
arrived at by the gate's own widening rather than by a probe stepping outside
it: the three second-page rows the widening added are the tilted pages, at
11.6–22.9% each, and RESULTS §3's page-level table already named one of them
(Brahms 1 / Breitkopf page 1: 14.4% there, 15.8% under this tree's phase 1).
On `beethoven-984073-p2` essentially the whole page is affected (18 of 22
staves carry a ≥0.25-space cell, max offsets 0.44–0.69 sp); on Brahms p2 it is
the bottom third (staves 16–26 of 27); on 575951-p2 the top half (staves 0–12,
plus 20) — per-region warp, exactly the shape FINDINGS §2 describes.

Two cross-checks on the same numbers:

- **The read-only widened-graft fixtures agree staff for staff.** Reading
  `staff_geometry.line_wander_px` out of
  `scan-rebaseline/…/fixtures/*.widened-graft.omr.json` flags exactly the same
  staves per row (11/11 rows identical sets) as this probe's phase 1 — the
  exposure measured here is the geometry the recorded baselines actually saw,
  not an artifact of a drifted tree.
- **`Staff.line_wander_px` is a usable trigger on this corpus:** the
  wander-≥-quarter-space flag catches **51 of 51** affected staves, 0 missed,
  24 over-flagged (Bach's 8 flagged staves have distortion but no displaced
  cell — wander measures both). RESULTS §5 warned it saturates and
  understates; as a binary per-staff trigger it missed nothing here.

**So pricing is possible: this corpus can express the fault.** The old
benchmark's null was a fact about its pages, not about the fix.

## 2. The A/B: −233 edits, sitting exactly on the exposure

Same tree, one variable, both arms measured here.
**Reproduction control first:** the baseline arm reproduces the committed
widened-graft baseline (`results-widened-graft.json`, measured on the
scan-rebaseline tree) **to the digit** — pooled 0.8387022350396539, 29082
edits over 19828 truth + 14847 predicted — so the merged tree's flag-off
pipeline is bit-equivalent to the tree the gate's baselines were recorded on,
and the byte-determinism the harness measured (`19a24800`) held across the
merge.

| row | exposure | baseline | localized | Δ edits |
|---|--:|--:|--:|--:|
| beethoven-984073-p2 | 22.9% | 0.8833 (4449) | 0.8703 (4343) | **−106** |
| brahms-317803-p2 | 15.8% | 0.9459 (6610) | 0.9426 (6563) | **−47** |
| beethoven-575951-p2 | 11.6% | 0.8770 (4471) | 0.8708 (4407) | **−64** |
| mahler-local-p2 | 3.3% | 0.6882 (1117) | 0.6895 (1119) | +2 |
| dvorak-405834-p6 | 2.9% | 0.7279 (2611) | 0.7243 (2596) | −15 |
| mahler-local-p3 | 1.7% | 0.8873 (3069) | 0.8888 (3076) | +7 |
| dvorak-405834-p5 | 0.7% | 0.4306 (673) | 0.4310 (675) | +2 |
| beethoven-984073-p1 | 0.5% | 0.7152 (1286) | 0.7108 (1278) | −8 |
| beethoven-575951-p1 | 0.0% | 0.7626 (1362) | 0.7595 (1358) | −4 |
| brahms-317803-p1 | 0.0% | 0.9192 (3434) | 0.9192 (3434) | **0** |
| **pooled (10 rows)** | 8.6% | **0.8387 (29082)** | **0.8345 (28849)** | **−233** |
| bach (stress, unpooled) | 0.0% | 0.9241 (6735) | 0.9231 (6720) | −15 |

- **The win sits where the defect is: −217 of the −233 on the three tilted
  rows.** The one row with literally nothing past even the 0.05-space
  measurement floor on its scoring path (Brahms p1) does not move by an edit,
  and the worst adverse movement anywhere is +7 (mahler-p3).
- **Not dilution.** Predicted symbols FELL (14847 → 14742) alongside edits;
  had edits stayed put, the smaller denominator would read 0.8413, i.e. worse.
  The improvement is all numerator.
- **The category signature is re-pairing, which is what fixing a
  whole-bar-off grid should look like:** `entire measure insert/delete` −253
  and `entire staff` −48, while `wrong note` rises +55 — bars whose every note
  sat a step off used to fail alignment outright and be charged whole; on the
  localized grid they pair again and their residual errors are itemized.
  `wrong keysig` −15; small +6..+11 in timesig/clef/direction/dynamic.
- **Exact-pitch recall — the axis the defect lives on — moves hardest on the
  most-exposed edition** (per-staff multiset recall/precision, scan_eval's
  `notes` block): 984073-p1 R 0.578 → **0.626**, P 0.727 → **0.786**;
  984073-p2 R 0.646 → **0.694**, P 0.762 → **0.819** — five to six points of
  pitch from a geometry flag, on p1 mostly via sub-flip corrections (its 143
  moved cells sit under 0.25 sp, but a borderline notehead flips at half that).
  575951-p2 +0.5pt; dvorak-p6 +2.2pt; 575951-p1 is the one mixed row
  (R 0.605 → 0.578 while its OMR-NED still improves — a key-signature flip
  respelled a staff, see below). No `notes` block for brahms-p2 / mahler /
  bach: those rows carry **no `staves` table in works.json** (the field
  note-recall joins on), so the instrument abstains there by design — a
  works.json gap worth filling when those rows' lineups are next verified, not
  a harness defect.

### Where, exactly — and the one second-order path

`compare_ab_cells.py` (committed beside this) walks both arms' raw
transcriptions cell by cell (`widened_ab_cell_report.json`):

- Grid-moved counts per row equal the probe's moved counts (143/294/40/229/…)
  — the flag moved exactly the cells the exposure probe said it would.
- **Every reading change sits on a row with grid moves** (the script exits
  nonzero otherwise): no flag leak into rows the comb left alone.
- Cells whose reading changed WITHOUT their own grid moving are 2–6 per
  affected row, and each traces to one of the two legitimate staff-level
  paths: **key-signature propagation** (below) and slur/tie re-partnering
  next to a moved cell. Worked example: 984073-p1 staff 9 (Viola), cells m6/m7
  — grids identical, every Bb/Eb respelled B/E because the staff's key
  signature flipped.
- Brahms p1: 25 sub-flip moves change 25 readings and the export differs —
  and the score is identical to the edit (3434), i.e. the changes are
  score-neutral respellings.

⚠️ **The grid feeds the key-signature slot fit, so the flag's blast radius
includes per-staff key signatures — net positive here, but two-directional.**
The slot table is fitted against staff-line positions, and the staff-start
cell's grid is what localizes; 20 pooled staves flipped their key reading
(984073-p1: 2, 984073-p2: 6, 575951-p1: 1, 575951-p2: 11, brahms-p2: 3,
mahler-p2: 1, plus 6 on unpooled Bach). Both directions occur on one page:
984073-p1 staff 11 (bass) GAINED the three real flats and staff 9 (alto,
Viola) LOST them. Pooled `wrong keysig` improves 261 → 246, and the flipped
rows all improve overall — but a per-staff regression exists inside a winning
row, which is the honest shape of a vote re-run on better geometry rather
than a strict refinement.

## 3. The engraved control — byte-identical, on independently rebuilt fixtures

`orchestral_eval --works beethoven-sym5-mvt1 brahms-sym1-mvt1 --omr-ned`
(never `--record`), run twice with separate work-dirs, flag off then on:

- Predicted exports **byte-identical** across the flag for both works
  (`cmp` on the `.omr.musicxml` pairs) — and the two runs rebuilt their
  fixtures independently, so this is byte-identity across fixture
  regeneration, not across a shared file.
- Scores identical to each other and to the recorded per-work table:
  Beethoven 5 **0.0595 / 77** (655 truth / 640 pred), Brahms 1 **0.1196 /
  494** (2083 / 2047).

This re-verifies RESULTS §4's stronger 11-work control on the current tree:
the engraved side is a no-op by construction (the 0.05-space minimum-shift
gate refuses LilyPond pages' sub-pixel answers), not merely by measurement.

## 4. The ship prerequisite: `recut_cells` compares the frame, not the metadata

RESULTS_TILT_COST.md measured that the cutting frame is already unlocalized
(one frame, two grids — 360/360 images byte-identical) and named the narrow
fix: `frame_mismatch` compares the UNLOCALIZED grid. Landed (commit
`be884ff8`), in three pieces, because the measured invariant covers
`cell.image` and one derived image needed the same care:

- `measure_extractor._build_measure_cell` stashes
  `staff_line_ys_canonical_unlocalized` beside the localization provenance —
  the flag-off grid by the identical arithmetic, i.e. the frame's own rows.
- `recut_cells.cut_page` cuts with localization ON whatever the environment
  says (`localized_grid_on`), so every fresh cell carries BOTH grids and
  `frame_mismatch` recognises a manifest written under either flag state: the
  frame's rows (every existing batch) or the localized rows (a batch cut
  after the flag ships — `select_cells_orchestral` records
  `cell.staff_line_ys_canonical`, which is the localized grid under the
  flag). Re-cutting stops depending on `OMR_CELL_LINE_TRACE`.
- ⚠️ **`_nostaff.png` is grid-DERIVED, and the record's frame invariant does
  not cover it**: `staff_line_removal` erases at `staff_line_ys_canonical`,
  so a pre-flag batch re-cut under a localized grid would get subtly
  different staff-line removal on tilted cells — byte-different
  `_nostaff.png`, silently. `_restore_manifest_grid` puts the manifest's own
  rows back on each verified cell before anything is saved: the manifest is
  the one record of the grid the original images were made with, so it is
  the erasure authority. This is what makes the byte-identity claim hold for
  BOTH png variants in both directions.

Pinned by three tests in `test_recut_cells_e2e.py`, on a synthetic page whose
two staves ramp ±1.2pt in opposite directions (net skew ~zero, so deskew
cannot straighten it; 1.8pt loses the staves to detection entirely) — and the
page provably localizes (asserted, so the tests cannot pass vacuously):

- `test_one_frame_two_grids_and_the_fixture_actually_localizes` — flag-off
  and forced-on cuts agree on every byte of `cell.image`, bbox and scale, and
  the unlocalized stash equals the flag-off grid exactly;
- `test_a_localized_grid_batch_recuts_byte_identically` — a batch whose
  manifest records MOVED rows verifies and re-cuts byte-identically;
- `test_a_pre_flag_batch_recuts_under_a_flag_on_environment` — the hazard the
  record names: a pre-flag batch, re-cut with the flag on in the environment,
  byte-identical including `_nostaff.png`.

(Same commit: the widened works.json broke a tilt-side test's premise —
`work_id` no longer narrows Beethoven 5 to one edition, two Litolff scans'
pages collide — a seam neither branch could see alone; the loader's guard
fires as documented and the test now asserts exactly that.)

## 5. Verdict

**The widened gate prices the fix, and the price is a win.** −233 edits /
−0.42 points pooled, concentrated to 93% on exactly the three rows the
exposure probe ranks tilted, with the zero-exposure row unchanged to the edit,
worst adverse row +7, five-to-six points of exact-pitch recall and precision
on the most-exposed edition, and a byte-identical engraved side. The 5-row
era's "2 edits of 7894" was the corpus, not the fix — put the defect in front
of the instrument and the instrument sees it.

**Recommended ship shape: default ON, no domain gating.** The engraved side
needs no routing guard — the minimum-shift gate makes it a no-op by
construction, re-verified byte-identical here — so a scan-only gate would add
machinery to avoid something that provably does not happen. Keep
`OMR_CELL_LINE_TRACE` as the kill switch (flip the default in
`_cell_line_trace_enabled`, document in the knobs table). Two honest caveats
for the ship note: (1) the key-signature blast radius — net −15 here but
two-directional per staff; any future key-sig regression hunt should check
`key_signature_source` against the flag state; (2) three low-exposure rows
move +2..+7 — noise-scale, but not zero. Nothing here flips the default on
this branch: that is Sean's call on return, and this document is its input.

**If more pricing is ever wanted**, the record's §5 candidate stands
unchanged: Beethoven 5 / Litolff pages 5/17 (16.6–18.2% past flip) as a
future gate row — but the decision no longer waits on it.

## 6. Files

| file | what |
|---|---|
| `results-widened-baseline.json` | flag-off arm, this tree, graft weights, 11 rows |
| `results-widened-localized.json` | flag-on arm, same tree, same weights |
| `compare_ab_cells.py` / `widened_ab_cell_report.json` | per-cell localization of the A/B + the no-leak check |
| `probe_scan_corpus_offsets.json` | exposure, refreshed over the widened works.json |
| `results-baseline.json` / `results-localized.json` | the 5-row-era A/B (RESULTS_TILT_COST.md §2), kept |
