# Phase C — Beethoven 5 mvt 1 alignment: findings & next steps

**Date:** 2026-05-23
**Anchor pair:** Hauptstimme `beethoven-symphony-5/musicxml/mvt-1.mxl` (502 measures, 18 parts) ↔ IMSLP `imslp-52624` (Breitkopf & Härtel 1862 Werke, full score, pp.7-40 = mvt 1)

**Status update (later same day):** Bug 1 (`_assign_systems` over-splitting orchestral pages) is fixed and committed with regression tests covering pages 7/20/56 of the 1862 Breitkopf edition. After the fix, the cell-level alignment produces 604 PDF measures vs 502 XML, off by +102 — entirely from Bug 2 (barline false positives on dense pages) which is now the remaining blocker. Sections below describe both bugs as originally diagnosed; Bug 1's section is kept as the historical record of why the fix landed.

---

## TL;DR

- The alignment **approach** is sound: XML measure count, time signature, key, barline types, dynamics are all cleanly extractable; PDF staff detection finds the correct staves; per-cell bboxes are clean where the underlying OMR works.
- The alignment **doesn't yet run end-to-end** on this orchestral score because the existing `tools/omr/` pipeline has two production bugs that surface specifically on dense full-score orchestral pages.
- Both bugs are surgical, well-scoped fixes. Once they land, cell-level alignment should just work and pixel-perfect becomes feasible on top.

---

## What worked

### Phase A — IMSLP metadata scraping
64 / 65 PDFs auto-confirmed (publisher + year + plate + city + country). The one holdout is genuinely "n.d." on IMSLP itself (Heugel & Cie Paris, Beethoven 4 imslp-411721). Cache lives at `/tmp/imslp-scrape/`; script at [`scrape_imslp_metadata.py`](scrape_imslp_metadata.py). Re-runs offline against cache.

### Phase B — Movement segmentation
Beethoven 5 mvt 1 = PDF pages 7-40 in `imslp-52624`. Front matter: cover (p.1) + series catalog (p.2) + blanks (p.3-4) + volume title (p.5) + blank (p.6). Captured in [`pdfs/imslp-52624/movements.yaml`](../../tools/omr/training/data/imslp/beethoven-symphony-5/pdfs/imslp-52624/movements.yaml). Detection method was: render every page top at 120 DPI in a strip, scan visually for "new instrument labels" pattern. 30-second labor per edition. Hand-annotation across all 65 PDFs ≈ 30 min total.

### Phase C — XML parsing
Full XML parse works: 502 measures × 18 parts, time 2/4, key C minor (−3 fifths), final barline `light-heavy`, 1 repeat (the famous exposition repeat). Extracted per-measure: time-sig, key-sig, clef changes, barline type, dynamics, note count. See `phase-c-output/cell_alignment.json` for the manifest schema.

### Phase C — Per-staff cell extraction
Staff detection finds **all 12 instruments** on page 7 of this score (Flauti, Oboi, Clarinetti, Fagotti, Corni, Trombe, Timpani, Vn I, Vn II, Va, Vc, Bassi). Overlay: [`phase-c-output/page7-cell-overlay.png`](phase-c-output/page7-cell-overlay.png).

---

## What's blocking — two production OMR bugs

### Bug 1 — `_assign_systems` over-splits orchestral pages

**File:** [`tools/omr/staff_detector.py:165-222`](../../tools/omr/staff_detector.py#L165)

The current grouping uses three heuristics:
1. Bipartition (1D Lloyd's k-means) on inter-staff gaps
2. MAD-style secondary threshold (`gap >= median * 2.0`)
3. X-overlap < 50% between adjacent staves

On a Beethoven 5 page with 12 instrument staves having gaps of 96-137 px (median 119, std ~15):
- The bipartition's "is it really bimodal?" check accepts a spurious split because `2 × intra_spread` is small (~18 px) and any minor cluster separation passes
- The 50%-overlap rule fires on adjacent staves whose `x_start` differs only because of varying instrument-label widths (e.g. "Oboi." vs "Violoncello.")

Result: a page that should be one 12-staff system gets split into 8 sub-systems. Downstream `extract_measures` then computes measure indices within each sub-system, accumulating wrong totals.

**Quick fix tried** (in [`phase_c_cell_align.py:regroup_orchestral_staves`](phase_c_cell_align.py)): replace the production grouping with `gap >= 2.5 × median`. Improves things — page 7 collapses back to 1 system × 12 staves correctly — but doesn't generalize: pages with two genuine orchestral systems (page 20 has 24 staves) get incorrectly merged because the inter-system gap isn't always > 2.5× the intra-system median.

**Proper fix candidates** (in order of preference):

1. **Detect the orchestral bracket on the left edge.** The `[` brace that joins instruments into a system is the most reliable signal. Quick template-match or vertical-line-detection above and below the staff cluster.
2. **Tighten the bipartition's "really bimodal" check** — require `(c2 - c1) > 4 × intra_spread` (was `2 ×`), AND require the cluster sizes to be similar (a single-outlier cluster shouldn't trigger a split).
3. **Replace x-overlap-frac heuristic with overlap on the actual staff-line extent** instead of the bracket-margin-inclusive extent.

### Bug 2 — Barline detection drops on dense orchestral pages

After regrouping, the alignment still mismatches: XML 502 vs PDF 306 measures. Sample evidence from page renders:

| PDF page | Detected measures (regrouped) | Plausible actual count |
|---|---|---|
| 7  | 14 | ~7-8 (first music page with title + key/time on first system) |
| 20 | 3 (× 24 stave merge artifact) | ~10-12 |
| 29 | 1 | several |
| 36 | 1 | several |

Both **false-positive** barlines (stem groups hallucinated as bar lines, see page 7's 14 instead of 7) and **false-negative** dropouts (page 29-36 with sparse detections) are present. The classical-CV barline detector in `measure_extractor._detect_barlines_per_staff` was tuned on Bach WTC piano (2 staves, clean spacing). On dense 12-stave orchestral pages with heavy chord stems, it overfires; on pages with rests and sparse activity, it underfires.

**Proper fix candidates:**
1. **YOLO-assisted barline detection.** Phase 3.4 already showed barlines need to be a YOLO class to be reliable. That work was paused due to catastrophic forgetting; with the IMSLP × XML pipeline now in place, we can generate enough auto-labeled barline examples to retry properly.
2. **System-wide barline arbitration.** A real orchestral barline runs through ALL 12 instruments at the same X coordinate. Cross-check candidates across the system — accept only barlines that fire on ≥80% of staves at the same X. Drops most stem false positives.
3. **Confidence-weighted accumulation across editions.** Once we have 5-8 IMSLP editions per work aligned, a barline that exists in the XML at measure N must exist on the PDF at the same X in every edition. Use the consensus across editions to fix individual misses.

---

## Pixel-perfect — why it's deferred

The pixel-perfect plan (render XML via Verovio, image-register the rendering onto each PDF cell via 5-staff-line homography) needs **the same XML-measure↔PDF-cell mapping** that the cell-level approach depends on. The homography is per-measure-per-staff; without knowing which XML measure each PDF cell represents, there's no anchor to compute the transform.

So the path is: fix Bugs 1 & 2 → cell-level alignment runs end-to-end → use the resulting measure-cell mapping as the basis for the per-cell homography → pixel-perfect labels.

A standalone pixel-perfect approach that bypasses cell mapping (e.g., full-page Verovio render → SIFT match to PDF page) is theoretically possible but the PDF and Verovio output have very different page breaks and system layouts; matching is messy. Better to fix the foundation.

---

## What we have, as catalog assets

- **65 PDFs** organized at `tools/omr/training/data/imslp/beethoven-symphony-{1..9}/pdfs/imslp-{ID}/score.pdf` (~1.8 GB)
- **65 metadata.yaml** files with publisher + year + plate + city + country (64 auto-confirmed, 1 truly n.d.)
- **53 .mxl** files at `beethoven-symphony-{1..9}/musicxml/mvt-{N}.mxl` and `brahms-symphony-{1..4}/musicxml/mvt-{N}.mxl` (~14 MB)
- **1 movements.yaml** for Beethoven 5 imslp-52624 (mvt 1 page range complete; mvt 2-4 partially marked)
- **Phase A scraper** (committable, idempotent, cached)
- **Phase C cell-alignment harness** ([`phase_c_cell_align.py`](phase_c_cell_align.py)) — works against any (PDF, XML) pair once page range is known; would produce a correct manifest once Bugs 1 & 2 are fixed

---

## Recommended next move

```
Step 1 (engineering, ~half-day):  Fix bug 1 in tools/omr/staff_detector.py
                                  using bracket detection OR tightened bipartition.
                                  Validate: page 7 = 1 system × 12 staves;
                                            page 20 = 2 systems × 12 staves.

Step 2 (engineering, ~1 day):     Fix bug 2 — add system-wide barline arbitration
                                  in tools/omr/measure_extractor.py.
                                  Validate: page 7 cell count = ~7;
                                            mvt 1 total = 502 ± anacrusis.

Step 3:                           Re-run phase_c_cell_align.py — confirm 502 match.
                                  Generate overlay PNGs for visual review.

Step 4:                           Build the pixel-perfect homography step on top.

Step 5 (Phase D):                 Scale to all 9 Beethoven symphonies × 6-9 editions each.
```

Steps 1 + 2 are the unlock. They're production-pipeline fixes that benefit ReEngrave's web app too, not just this training-data project.
