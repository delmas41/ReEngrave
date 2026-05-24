# Phase D — IMSLP catalog alignment summary

**Date:** 2026-05-24 (running overnight)

## What this is

The Phase C pipeline (PDF cell extraction + XML parsing + sequential alignment) anchored on a single (PDF, XML) pair: Beethoven 5 mvt 1 against the 1862 Breitkopf Werke edition (imslp-52624). Phase D scales it across the full IMSLP catalog Sean assembled: 65 PDF editions across Beethoven 1-9, with 53 Hauptstimme MusicXML files (Beethoven 1-9 + Brahms 1-4).

Per-PDF total alignment, run at 150 DPI for catalog-scale speed.

For each (work, edition), the script:
1. Sums XML measure counts across all `mvt-{N}.mxl` files for the work.
2. Runs `tools.omr` cell extraction on every page of the PDF (front matter contributes 0 cells, music pages contribute their measure cells).
3. Reports `delta = pdf_detected_measures - xml_total_measures`.

Per-movement alignment is deferred until movement-segmentation auto-detection is more reliable. The current `phase_d_segment_movements.py` heuristic generalizes poorly across edition layouts (false-positives on running-page headers, false-negatives on attacca transitions).

## Results

(Filled in by `phase_d_run_alignment.py`. See `phase-d-output/_catalog_summary.json` for the full raw data.)

### Aggregate

_TBD when run completes — placeholder section. Will include:_

- Total editions processed
- Mean / median / min / max delta percentage
- Count of editions within ±10%, ±20%, ±50%
- Count of editions that failed (PDF rendered but 0 measures detected — usually a scan-quality issue)

### Per-work breakdown

_Table per work showing each edition's XML total, PDF detected, delta_pct. Surface the per-edition delta as a quality signal — editions consistently within ±5% are catalog-ready for label generation; editions >±20% need investigation (likely scan quality, unusual layout, or an OMR pipeline edge case)._

### Known good editions

_Editions verified within ±5% delta — these are the safe starting points for Phase E label-generation work. Expected to skew toward the canonical 1862 Werke editions (consistent engraving conventions) and clean modern scans (Bärenreiter, Henle)._

### Known bad editions

_Editions with very high delta — flagged for follow-up. Common causes:_
- _Manuscript-style engravings the OMR pipeline can't read_
- _Very compressed pocket-score layouts (low staff line spacing)_
- _Damaged / faded scans (poor binarization)_
- _Unusual page layouts (e.g., piano-vocal reductions instead of full score)_

## What's next

Once this catalog summary is in, the next steps in Phase D / E:

1. **Per-movement segmentation for the ±5% editions.** With known-good editions identified, hand-curate per-movement page ranges for those specifically. Skip the rest until the segmentation auto-detector improves.
2. **Per-cell label generation.** For each correctly-aligned (PDF cell, XML measure) pair, generate the YOLO label set (barlines, clefs, time/key sigs, dynamics, notehead positions) using the pixel-perfect homography MVP that landed in Phase C.
3. **Catalog QA tool.** A web/CLI tool that lets you flip through measures with labels overlaid for visual review (per Phase E from PHASE_C_FINDINGS).
4. **YOLO training run.** Mix the new labeled data 50/50 with DSv2, warm-start from existing weights, retrain.
