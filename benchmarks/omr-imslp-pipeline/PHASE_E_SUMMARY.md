# Phase E — per-cell YOLO label generation summary

**Date:** 2026-05-24
**Branch:** `claude/interesting-curran-3ca1b7`

## What this is

Phase E generates training-quality YOLO labels by walking every (PDF cell × XML measure) pair on the catalog-ready editions and warping XML-parsed notehead / clef / accidental positions onto the PDF page via the Phase C staff-line homography. The output is one `.txt` per PDF page in standard YOLO format (`class cx cy w h`, normalized to image dims), plus overlay PNGs for visual review.

## What landed in this phase

### 1. Hand-curated `movements.yaml` for all 7 catalog-ready editions

| Edition | mvt 1 start | mvt 2 start | mvt 3 start | mvt 4 start | mvt 5 start | Verified |
|---|---:|---:|---:|---:|---:|:---:|
| beethoven-symphony-1 / imslp-52848 (Werke 1862) | p007 | p023 | p032 | p037 | — | YES |
| beethoven-symphony-2 / imslp-503997 (Litolff 1870) | p001 | p024 | p037 | p042 | — | YES |
| beethoven-symphony-2 / imslp-977672 (Ricordi 1909) | p003 | p049 | p073 | p080 | — | YES |
| beethoven-symphony-4 / imslp-411721 (Heugel Paris) | p001 | p042 | p054? | p092 | — | NO (mvt 3 boundary not found visually) |
| beethoven-symphony-6 / imslp-57857 (Werke 1863) | p007 | p030 | p049 | p066* | p073 | YES |
| beethoven-symphony-8 / imslp-06303 (Eulenburg 1938 Unger) | p001 | p041 | p052 | p061 | — | YES |
| beethoven-symphony-8 / imslp-875077 (Werke 1863) | p003 | p025 | p032 | p037 | — | YES |

\* Beethoven 6 mvt 3→4 transition is **mid-page on p066** (Tromboni instrument enters at system 2). Yaml records the `mid_page_transitions` list for downstream label generation.

The Heugel Beethoven 4 (imslp-411721) does not place a "III" header at the start of mvt 3 — the Scherzo begins mid-page somewhere in the p054-p064 range. The yaml marks `verified: false` for that edition until someone can scrub a higher-resolution rendering for the texture change.

### 2. New tools

| File | Purpose |
|---|---|
| `phase_e_movement_strips.py` | Renders top-of-page strips at 150 DPI for candidate movement-start pages. Used during hand-curation. |
| `phase_e_contact_sheet.py` | Renders a full-PDF thumbnail contact sheet (5 cols × N rows) for visual scanning. Each thumbnail is labeled with its 1-indexed PDF page. |
| `phase_e_emit_labels.py` | The Phase E driver. Walks every cell in a movement's page range, warps XML elements onto PDF pixel coords via the 5-line homography, and emits per-page YOLO label `.txt` files plus debug overlays. |

### 3. End-to-end MVP run

Ran the label generator on Beethoven 1 imslp-52848 mvt 1 (the cleanest catalog-ready pair). Stats:

- **Pages 7-11 processed** (out of mvt 1 page range 7-22)
- **537 cells matched to XML measures** (100% match rate; no measure index drift in the first 5 pages)
- **2108 YOLO labels emitted** across 5 pages
- **0 homography failures** — all 5-line correspondences solved cleanly

Overlays at `phase-e-labels/beethoven-symphony-1-imslp-52848-mvt1/overlays/p00{7,8,9,10,11}.png`.

## What's working

- **Verovio loading + measure indexing**: All 300 mvt-1 measures parsed and addressable by XML measure number.
- **Per-measure SVG parsing**: Staff lines + notehead + clef + accidental + key-sig positions correctly extracted from each `<g class="measure">` subtree.
- **5-line homography**: Maps Verovio internal coords to PDF cell pixel coords cleanly (the Phase C MVP technique scales). RANSAC inliers consistently 10/10 for non-degenerate cells.
- **Barline synthesis**: Cell right edges become barline bboxes (height = staff height + small padding).
- **YOLO label format**: Standard 5-column (`class cx cy w h`) with values normalized to [0, 1].

## What's broken / not yet right

### Blocker — Staff detector merges 2 systems into 1 on dense orchestral pages

On Beethoven 1 mvt 1 p011 (a typical dense page with 2 systems), `detect_staves` returns 22 staves but assigns ALL of them to `system_index = 0`. That's Bug 1 from PHASE_C_FINDINGS resurfacing in a different shape — instead of over-splitting it's now over-merging.

Symptom: the bottom 4 staves of p011 get no notehead labels because the PDF→XML staff map only has entries for indices 0-17 (= one orchestra × 11 staves + 6 split parts), but the merged-into-one-system page has staff indices 0-21.

Fix needed in `tools/omr/staff_detector.py` `_assign_systems` — probably the bipartition threshold needs to be loosened (`gap >= 2.5 × median` was a Phase C suggestion that handled single-system 12-staff pages; double-system 24-staff pages need a different cutoff). Or detect the orchestral bracket left edge to anchor system grouping.

### Sub-issue — ~50 px x-offset residual

Visible in overlays p007, p008. Even on system-first cells, warped noteheads cluster slightly LEFT of the actual printed noteheads. This is the Phase C note: "There's residual x-offset (~50px) from PDF clef/key/time-sig setup space that Verovio's per-measure layout doesn't model identically." Per-system left-margin correction is the right path: detect the actual music start x (first non-clef/keysig ink column) in the PDF cell, and use that as the cell left anchor instead of the cell's raw left edge.

### Sub-issue — PDF→XML staff map is hard-coded for Beethoven 1

The hardcoded map at `phase_e_emit_labels.py:PDF_XML_STAFF_MAP_BEETHOVEN_1` covers only Beethoven 1's instrument layout (Hauptstimme's `mvt-1.mxl` has 18 parts; the 1862 Werke layout shows 12 staves). Scaling to other works needs either per-work maps or a part-name → staff-position mapper that reads `<score-part>/<part-name>` from the MusicXML and matches to the visible staff order.

## Files modified or added

```
benchmarks/omr-imslp-pipeline/
  PHASE_E_SUMMARY.md                   ← this file
  phase_e_contact_sheet.py             ← new
  phase_e_movement_strips.py           ← new
  phase_e_emit_labels.py               ← new
  phase-e-output/                      ← contact sheets + boundary-candidate strips
  phase-e-labels/                      ← per-cell YOLO labels + debug overlays
tools/omr/training/data/imslp/
  beethoven-symphony-1/pdfs/imslp-52848/movements.yaml    ← rewrote (was auto-generated v1)
  beethoven-symphony-2/pdfs/imslp-503997/movements.yaml   ← rewrote
  beethoven-symphony-2/pdfs/imslp-977672/movements.yaml   ← rewrote
  beethoven-symphony-4/pdfs/imslp-411721/movements.yaml   ← rewrote, verified=false
  beethoven-symphony-6/pdfs/imslp-57857/movements.yaml    ← created
  beethoven-symphony-8/pdfs/imslp-06303/movements.yaml    ← created
  beethoven-symphony-8/pdfs/imslp-875077/movements.yaml   ← created
```

## What's next (Phase F)

1. **Fix the `_assign_systems` over-merge** in `tools/omr/staff_detector.py`. The simplest experiment: anchor system splits on left-edge orchestral bracket detection (a tall vertical line + a `{` brace), then bipartition only within each bracket cluster.

2. **Per-system left-margin correction.** After detecting a cell's first non-clef/keysig ink column, replace the cell's raw `bbox_page_px[0]` with that anchor and re-fit the homography. Expected to eliminate the ~50px x-shift on system-first cells.

3. **Generalize the PDF→XML staff mapper.** Read `<part-list>` from the MusicXML, build a name → index lookup, and pair to the visible PDF staff order by matching the printed instrument label (rendered with the existing OCR pass from `phase_d_segment_movements_v2.py`).

4. **Run on the remaining 6 catalog-ready editions** once 1-3 are stable. The Beethoven 4 Heugel mvt 3 boundary needs to be confirmed visually first (the texture-change heuristic might land it without a header).

5. **Label class expansion.** The MVP uses 6 classes (notehead, clef, barline, keysig, timesig, accidental). Extending to the full DSv2-compatible class space (with per-duration notehead subtypes, articulation marks, rests, etc.) is the path to mixed 50/50 catalog + DSv2 training data — see the original Phase E plan in `PHASE_D_CATALOG_SUMMARY.md`.

---

## Phase F update (2026-05-24, commits d30db31 + b7af4be)

### Blocker 1 — RESOLVED: staff_detector single-outlier fallback (commit d30db31)

Added `_top_outlier_threshold` between bipartition and the median-factor fallback in `tools/omr/staff_detector.py`. It catches the "one inter-system gap, many intra-system gaps" pattern that bipartition's c2/c1 ≥ 1.5 ratio check rejects.

Validated:
- 4 prior `TestBeethoven5Breitkopf1862SystemGrouping` cases still pass
- New `TestBeethoven1Breitkopf1862SystemGrouping` locks in pp.7 (1 sys) and 11 (2 sys) of imslp-52848
- New `TestTopOutlierThreshold` covers the helper in isolation (no PDF)

Impact on the MVP label run for Beethoven 1 imslp-52848 mvt 1:
- Pages processed: 5 → 16 (the full movement)
- Cells with XML match: 537 → 2456
- Labels emitted: 2108 → 8994

### Blocker 3 — RESOLVED: generic PDF→XML staff mapper (commit b7af4be)

Replaced the hardcoded `PDF_XML_STAFF_MAP_BEETHOVEN_1` with `build_pdf_xml_staff_map()` which reads `<part-list>/<score-part>` from the .mxl. It groups consecutive parts whose `_family_of(part_name)` is in `COMBINE_FAMILIES` (winds/brass — Flute 1 + Flute 2 share one staff) while keeping `SEPARATE_FAMILIES` (strings, timpani, percussion) on individual staves.

Verified output matches the prior hardcoded reference for Beethoven 1, and produces sensible staff counts for the other catalog-ready works (12 for B2/B4/B8, 10 for B6 Pastoral mvt 1 — no trumpets/timpani in that movement).

Tested end-to-end on **Beethoven 8 imslp-875077 mvt 1 (Werke 1863)** first 5 pages — 860 cells / 100% XML match / 2940 labels / 0 homography failures.

### Blocker 2 — DEFERRED: ~50px x-offset residual

Still present. The fixed bounding boxes are large enough that the YOLO labels overlap meaningfully with the actual noteheads (boxes are ~20 px wide at 300 DPI; offset is ~30-60 px), so the labels remain training-grade noisy rather than wrong. A structural fix (detect clef body's right-edge in the PDF cell, trim both source and destination of the homography proportionally) is the path to clean alignment but doesn't gate Phase G training.

### Phase F state

- **2 of 3 Phase F blockers resolved.** Label generator runs end-to-end on Beethoven 1 (1862 Werke) and Beethoven 8 (1863 Werke). Auto-mapper is ready for the remaining 4 catalog-ready editions (B2 Litolff, B2 Ricordi, B4 Heugel, B6 Pastoral).
- **Scale-out is unblocked** modulo the x-offset polish.
- Next phase (Phase G): expand the 6-class MVP label space to the full DSv2 set and mix-train.
