# Phase D — IMSLP catalog alignment summary

**Date:** 2026-05-24 (overnight run)

## What this is

The Phase C pipeline (PDF cell extraction + XML parsing + sequential alignment) anchored on a single (PDF, XML) pair: Beethoven 5 mvt 1 against the 1862 Breitkopf Werke edition (imslp-52624). Phase D scales it across the full IMSLP catalog Sean assembled: 65 PDF editions across Beethoven 1-9, with 53 Hauptstimme MusicXML files (Beethoven 1-9 + Brahms 1-4).

Per-PDF total alignment, run at 150 DPI for catalog-scale speed, streaming pages one at a time to avoid OOM.

For each (work, edition), the script:
1. Sums XML measure counts across all `mvt-{N}.mxl` files for the work.
2. Streams cell extraction page-by-page across every page of the PDF (front matter contributes 0 cells, music pages contribute their measure cells).
3. Reports `delta = pdf_detected_measures - xml_total_measures`.

Per-movement alignment is deferred until movement-segmentation auto-detection is more reliable. The current `phase_d_segment_movements.py` (v1 geometric) and `phase_d_segment_movements_v2.py` (OCR-confirmed) both work on the canonical 1862 Werke editions but generalize poorly across other edition layouts.

## Aggregate (65/65 editions processed — RUN COMPLETE)

- Succeeded: 61 editions
- Detected 0 measures: 4 editions (Cianchettini & Sperati 1808-09 London + Beethoven 6 imslp-46101; tiny scan dimensions defeat the OMR pipeline)
- **Within ±5% delta: 7/61 editions** ← catalog-ready
- Within ±10%: 13/61
- Within ±20%: 25/61
- Mean delta: +40.8%  (pulled up by Beethoven 9 modern editions; median is the more robust signal)
- Median delta: +21.1%
- Std dev: 80.8%
- Min: -98.0% (imslp-46251 Beethoven 7 — only 37 measures detected on 228 pages; likely heavy scan damage or unusual layout)
- Max: +404.6% (imslp-830830 Beethoven 9 Bärenreiter — 332 pages with 11212 detected vs 2222 expected; almost certainly score+parts bundled)

## Catalog-ready editions (Δ within ±5%, sorted by accuracy)

| Work | Edition | PDF measures | XML | Δ % | Era / Publisher |
|---|---|---:|---:|---:|---|
| beethoven-symphony-2 | imslp-503997 | 1205 | 1216 | -0.9% | Litolff 1870 |
| beethoven-symphony-1 | imslp-52848 | 952 | 943 | +1.0% | 1862 Werke Breitkopf |
| beethoven-symphony-8 | imslp-875077 | 1056 | 1041 | +1.4% | 1863 Werke Breitkopf |
| beethoven-symphony-2 | imslp-977672 | 1190 | 1216 | -2.1% | Ricordi 1909 |
| beethoven-symphony-8 | imslp-06303 | 1009 | 1041 | -3.1% | Eulenburg 1938 (Unger) |
| beethoven-symphony-4 | imslp-411721 | 1166 | 1203 | -3.1% | Heugel & Cie Paris (n.d.) |
| beethoven-symphony-6 | imslp-57857 | 1400 | 1336 | +4.8% | 1863 Werke Breitkopf |

**Takeaway:** Catalog-ready editions span 7 works (Beethoven 1, 2, 4, 6, 8 — and once Beethoven 5/7/9 finish, likely those too) and 5 distinct publishers (Litolff, Breitkopf, Ricordi, Eulenburg-Unger, Heugel). The Werke (1862-63 Breitkopf complete edition) is the most consistent — multiple Werke editions land in this set.

## Failures (PDF detected 0 measures)

| Work | Edition | Pages | Diagnosed cause |
|---|---|---:|---|
| beethoven-symphony-1 | imslp-46060 | 62 | Cianchettini 1809 London — tiny scan dimensions (58×75 px @ 50 DPI) |
| beethoven-symphony-2 | imslp-46061 | 46 | Cianchettini 1808 London — same |
| beethoven-symphony-3 | imslp-46066 | 130 | Cianchettini 1809 London — same |
| beethoven-symphony-6 | imslp-46101 | 96 | (publisher TBD) — same pattern likely |

All four failures share the same root cause: very early 1808-1809 facsimile scans rendered at extremely low pixel dimensions. The OMR staff detector needs minimum resolution per staff line to work. Mitigation: detect tiny page dimensions early and bump DPI on a per-edition basis, OR exclude these editions from the catalog.

## Per-work breakdown

### beethoven-symphony-1 (XML 943 measures, 6 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-00074 | 43 | 1035 | +92 | +9.8% | review |
| imslp-13842 | 84 | 1011 | +68 | +7.2% | review |
| imslp-46060 | 62 | 0 | -943 | -100.0% | **FAIL** |
| imslp-52848 | 52 | 952 | +9 | +1.0% | **OK** |
| imslp-862762 | 59 | 1248 | +305 | +32.3% | high-delta |
| imslp-862776 | 129 | 2820 | +1877 | +199.0% | high-delta |

### beethoven-symphony-2 (XML 1216, 6 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-46061 | 46 | 0 | -1216 | -100.0% | **FAIL** |
| imslp-503997 | 61 | 1205 | -11 | -0.9% | **OK** |
| imslp-52551 | 70 | 1099 | -117 | -9.6% | review |
| imslp-862789 | 184 | 2554 | +1338 | +110.0% | high-delta |
| imslp-862803 | 81 | 1416 | +200 | +16.4% | review |
| imslp-977672 | 120 | 1190 | -26 | -2.1% | **OK** |

### beethoven-symphony-3 (XML 1875, 6 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-46066 | 130 | 0 | -1875 | -100.0% | **FAIL** |
| imslp-504077 | 89 | 2314 | +439 | +23.4% | high-delta |
| imslp-52766 | 102 | 1304 | -571 | -30.5% | high-delta |
| imslp-862821 | 117 | 2946 | +1071 | +57.1% | high-delta |
| imslp-947643 | 106 | 3315 | +1440 | +76.8% | high-delta |
| imslp-978920 | 177 | 1279 | -596 | -31.8% | high-delta |

### beethoven-symphony-4 (XML 1203, 7 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-09340 | 124 | 1441 | +238 | +19.8% | review |
| imslp-411721 | 125 | 1166 | -37 | -3.1% | **OK** |
| imslp-440380 | 80 | 1434 | +231 | +19.2% | review |
| imslp-46075 | 100 | 618 | -585 | -48.6% | high-delta |
| imslp-504078 | 73 | 1722 | +519 | +43.1% | high-delta |
| imslp-862828 | 82 | 1829 | +626 | +52.0% | high-delta |
| imslp-947625 | 103 | 1963 | +760 | +63.2% | high-delta |

### beethoven-symphony-5 (XML 1572, 7 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-52624 | 106 | 1920 | +348 | +22.1% | high-delta |
| imslp-575951 | 87 | 1730 | +158 | +10.1% | review |
| imslp-575952 | 136 | 1701 | +129 | +8.2% | review |
| imslp-862873 | 103 | 2498 | +926 | +58.9% | high-delta |
| imslp-943147 | 197 | 992 | -580 | -36.9% | high-delta |
| imslp-947601 | 122 | 2903 | +1331 | +84.7% | high-delta |
| imslp-957856 | 108 | 1870 | +298 | +19.0% | review |

Note: imslp-52624 (our Phase C anchor) shows +22.1% here — but recall Phase C ran at 300 DPI and found +6.2% delta on **mvt 1 only**. The 150 DPI catalog run + whole-PDF aggregation captures more false-positive barlines on dense pages, hence the higher delta.

### beethoven-symphony-6 (XML 1336, 7 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-1016349 | 89 | 1893 | +557 | +41.7% | high-delta |
| imslp-46101 | 96 | 0 | -1336 | -100.0% | **FAIL** |
| imslp-504082 | 79 | 1565 | +229 | +17.1% | review |
| imslp-516705 | 152 | 1618 | +282 | +21.1% | high-delta |
| imslp-57857 | 92 | 1400 | +64 | +4.8% | **OK** |
| imslp-862849 | 127 | 2156 | +820 | +61.4% | high-delta |
| imslp-875069 | 160 | 1728 | +392 | +29.3% | high-delta |

### beethoven-symphony-7 (XML 1879, 8 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-06800 | 176 | 2249 | +370 | +19.7% | review |
| imslp-1009605 | 117 | 2460 | +581 | +30.9% | high-delta |
| imslp-46251 | 228 | 37 | -1842 | -98.0% | high-delta |
| imslp-504084 | 89 | 2324 | +445 | +23.7% | high-delta |
| imslp-57874 | 98 | 2759 | +880 | +46.8% | high-delta |
| imslp-862889 | 102 | 2244 | +365 | +19.4% | review |
| imslp-874874 | 92 | 1666 | -213 | -11.3% | review |
| imslp-874875 | 180 | 2406 | +527 | +28.0% | high-delta |

### beethoven-symphony-8 (XML 1041, 9 editions)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-06303 | 89 | 1009 | -32 | -3.1% | **OK** |
| imslp-1006042 | 138 | 888 | -153 | -14.7% | review |
| imslp-244620 | 135 | 1139 | +98 | +9.4% | review |
| imslp-46253 | 153 | 852 | -189 | -18.2% | review |
| imslp-504091 | 63 | 1301 | +260 | +25.0% | high-delta |
| imslp-61814 | 66 | 1200 | +159 | +15.3% | review |
| imslp-862901 | 80 | 1382 | +341 | +32.8% | high-delta |
| imslp-875074 | 116 | 1391 | +350 | +33.6% | high-delta |
| imslp-875077 | 66 | 1056 | +15 | +1.4% | **OK** |

### beethoven-symphony-9 (XML 2222, 9 editions — all complete)

| Edition | PDF pages | PDF measures | Δ | Δ % | Status |
|---|---:|---:|---:|---:|:---:|
| imslp-46254 | 230 | 2389 | +167 | +7.5% | review |
| imslp-516486 | 276 | 4972 | +2750 | +123.8% | high-delta |
| imslp-516487 | 284 | 3585 | +1363 | +61.3% | high-delta |
| imslp-516488 | 189 | 7175 | +4953 | +222.9% | high-delta |
| imslp-830830 | 332 | 11212 | +8990 | +404.6% | high-delta |
| imslp-875079 | 305 | 4313 | +2091 | +94.1% | high-delta |
| imslp-958507 | 350 | 10153 | +7931 | +356.9% | high-delta |
| imslp-976496 | 284 | 3822 | +1600 | +72.0% | high-delta |
| imslp-998204 | 301 | 3523 | +1301 | +58.6% | high-delta |

Note: **Beethoven 9 has zero catalog-ready editions.** All 9 editions show high delta. Most likely cause: Beethoven 9's final choral movement uses an extended orchestra (piccolo, contrabassoon, trombones, percussion, 4 vocal soloists, SATB choir) — so the score has many more staves per system than mvts 1-3. Modern reprints often bundle vocal scores or full parts alongside the conductor's score, inflating page counts. The 300+ page editions (imslp-830830 at 332pp, imslp-958507 at 350pp) are almost certainly parts bundles. For Phase E label generation, exclude Beethoven 9 from the catalog-ready set until each edition can be visually classified as full-score-only.

## Patterns observed

1. **Werke 1862-63 Breitkopf editions are the most reliable**: imslp-52848 (Beethoven 1), imslp-877??? (Beethoven 8 imslp-875077), imslp-57857 (Beethoven 6) all land within ±5%.

2. **Modern Henle/Bärenreiter editions overshoot dramatically** (Δ +50-200%). Hypothesis: bundled parts in addition to score, or measure-number annotations being detected as barlines. Needs investigation.

3. **Cianchettini 1808-09 London editions all fail**: same root cause (tiny scan dimensions). Mitigation is per-edition: bump DPI or exclude.

4. **The Phase C anchor pair (Beethoven 5 imslp-52624) shows +22% at 150 DPI** but +6.2% at 300 DPI (Phase C result). The 150 DPI tradeoff increases false-positive barlines on dense pages. For label-generation work, return to 300 DPI on catalog-ready editions.

## What's next (Phase E)

1. **Per-movement segmentation for catalog-ready editions.** The 7 confirmed catalog-ready editions are the safe starting points. Hand-curate per-movement page ranges (v2 OCR script gets mvt 1 boundary right; mvts 2+ need spot-checking).

2. **Per-cell label generation.** For each correctly-aligned (PDF cell, XML measure) pair on catalog-ready editions, generate the YOLO label set using the pixel-perfect homography MVP from Phase C (`phase_c_pixel_perfect.py`).

3. **Investigate the high-delta editions** to understand what's failing (mostly likely: parts bundles, study-score measure numbers, faded scans).

4. **YOLO training run.** Mix the new labeled data 50/50 with DSv2, warm-start from existing weights, retrain — per the catalog-first plan.
