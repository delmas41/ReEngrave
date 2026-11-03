# 2.254 -- hairpin reach, and word boxes over hairpins (STAGED GATHER; Sean 2026-11-02)

Written by the manager from the lane report (lane-2.254-hairpin-reach ea379fc9e; the hook refused the lane's FINDINGS write). Flag `OMR_HAIRPIN_REACH`, default OFF. Does NOT land yet (claim-order gate failed on Brahms p8).

## Cause and process lesson

The CV wedge reader (`hairpin_detection.detect_hairpins`) keeps a hairpin only as a separate, straight-edged blob. On these orchestral plates a barline runs through the gap between bracketed staves, and stems, ledgered heads and slurs of the next staff reach into it; a hairpin touching any of them is one blob with it and is refused. Brahms p19 bars 352-358: every one of ~20 long hairpins refused this way (crossed by a barline or touching a stem). Lesson: the "stands on its own" test was set 2026-09 on pages where it told hairpins from beams and never re-measured where barlines cross the gap -- a test that depends on the page's other marks is re-measured wherever those marks differ.

## Built

- Reader: barlines and stems removed before the look, the gap rejoined; a second pass (finds >= 4 sp only) looks past a slur touching an arm; the two arms must meet and the opening grow steadily (stops beams and glued words). Never drops a plain-reader keep; adds nothing under 1.6 sp. Cut-offs set on Brahms p19/p25 -- NOT confirmed elsewhere.
- One-note wedge (`ownership._wedge_page_binding`): abstains `one_note_wedge` only when <= 3 sp. CONVENTION ASSUMED: an accent glyph is never wider than 3 sp. WHAT WOULD FALSIFY IT: an accent wider than 3 sp on Sean's tiles. NOT CONFIRMED. Without the limit p8 lost 9 written hairpins 3.9-6.7 sp held under one note.
- `ownership._hairpin_separates` (fenced by name): with the flag ON it checks the hairpin's x span, not height only (else a new cello hairpin gave the K.-B. flats two bars to its right to the cello, p25).
- Word claims cover only the ink left and right of a hairpin inside the OCR box.

## Measures (2 pages per plate; not the frozen sample)

- File: Brahms p19+p25 wedges +27, nothing else; p8 wedges +7; Litolff p9+p16 unchanged.
- Judged right->wrong 0, unwritten->wrong 0 on every run.
- Claim readout: Brahms p19/25 ORDER-VIOLATION 0.36->0.36, SPLIT 0.66->0.66; Litolff 0.10->0.10, 0.55->0.55 (flat because a CV hairpin read claims no strokes -- the readout cannot see the change). **Brahms p8 ORDER-VIOLATION 0.62 -> 0.83** (word->stem/beam/flag 0.27 -> 0.48): the ink freed from the word claim goes to a beam box and the word's OCR box still counts as reading it. Before landing: the hairpin read claims its own strokes, and the word reader's box leaves the hairpin out.

## Sean's hint (repeated hairpins across a system)

87 of 105 hairpins read (>= 4 sp, 7 Brahms pages) have a hairpin over the same bars on another staff of the same system. These are our reads, not the print, so the share is inflated. Measured, not built as a search.

## Tiles

`out/print/2.254-tiles/` (lane worktree; 12 + sheet.png; key `out/print/2.254-tiles-key.json`): 8 gained hairpins, 1 one-note wedge, 2 p8 word places, 1 control.

## Not verified

Raw reader counts without detector blanking: Brahms p19 0->27, p25 8->25, p5 0->22 (4 hairpins + 18 accents), p12 0->2. Litolff 5 new 1.6-4 sp reads (pages 2, 4, 11) unchecked. Two Brahms OFF arms lost staves to OCR timeouts under load (test noise; clean gathers re-adjudicated instead, `reuse_gathers.py`, `readjudicate.py`). Frozen sample not run. The shared `lane-report-slices-20261029-night` now holds only Brahms p0/p5 (re-cut by another lane).
