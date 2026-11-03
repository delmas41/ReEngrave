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

## Round 2 (lane-2.254-hairpin-reach, flag still OFF)

**Cause.** On Brahms p8 (round-1 slices), 13,677 of the 13,790 px in `word_dynamic -> stem_beam_flag` lie under both a detector `beam` box (0.27-0.93; two to five boxes on each arm) and a cv_lines `beam_stroke` read. The detector and the line reader both take a hairpin's thin straight arm for a beam. The CV hairpin read filed a `Q.WEDGE_BOX` and claimed no ink. Once round 1 shrank the word claim, the stroke owner had no claimant ahead of the consumers, and the beam took the arm. The OCR box that had read the wedge as an 'a' ('a dim') still counted as a word read of it. **Lesson:** freeing ink is a two-sided change. The mark that really owns the ink must claim it in the same step, or the latest consumer takes it. A reader that files no claim is invisible to the claim readout.

**Built.** (1) `gather.gather_hairpin_claim`: each CV reach read claims the strokes at least 50% along its two arms (`unit: ink`, owner `hairpin`). It does this in every cell it crosses, and the claim runs at tier 0 beside the arcs (`stroke_owner._hairpin_claims`, family `hairpin_trace`). The arms come from the read box: apex at the mid-height of the narrow end, band 0.2 sp. (2) The word reader's mask loses the arm pixels (`direction_text._blank_detections` `erase_entries`), never the rectangle. (3) With the flag on, a beam refused as `owned_by_another_mark` on a claimed arm counts as not a beam for the bare-stem INFER rule. Without that, one GUESSED dotted quarter on p19 went unwritten.

**Claim readout (OFF -> ON):** p8 ORDER-VIOLATION 0.62 -> 0.60 (round 1: 0.83); word->beam 0.27 -> 0 and word->arc_hairpin 0 -> 0.25. In the three words whose OCR box still overlaps the hairpin ('p espr', 'P dolce', 'pp cresc. molto'), the box is not cut to ink. ORDER-OK 7.41 -> 10.32. p19 0.39 -> 0.39, p25 0.34 -> 0.34, Litolff p9 0.15 -> 0.15, p16 0.06 -> 0.06. SPLIT is unchanged on every page.

**Spans vs Sean (answers-r1.json).** The named tiles 1, 3, 4, 10, 11 and 12 match by place. For tile 12, our bar 38 writes only its second dotted quarter, because the first is unread, so the onset count differs. Tile 2 is ambiguous ("the dotted quarter notes"): we wrote one dotted-quarter chord. Tiles 5-8 are NOT CONFIRMED (we wrote the tile-4/tile-3 shape). The binding was not changed.

**Costs seen.** Brahms p8 loses 2 READ 'dim' words. The tight 'dim.' crop beside a barline returns no OCR reading in either arm. OFF read it only through the crop that held the hairpin.

## Not verified

Raw reader counts without detector blanking: Brahms p19 0->27, p25 8->25, p5 0->22 (4 hairpins + 18 accents), p12 0->2. Litolff 5 new 1.6-4 sp reads (pages 2, 4, 11) unchecked. Two Brahms OFF arms lost staves to OCR timeouts under load (test noise; clean gathers re-adjudicated instead, `reuse_gathers.py`, `readjudicate.py`). Frozen sample not run. The shared `lane-report-slices-20261029-night` now holds only Brahms p0/p5 (re-cut by another lane).
