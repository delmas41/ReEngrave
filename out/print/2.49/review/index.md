# ROADMAP 2.49 -- manager follow-up: big, boxed, stemmed, labelled crops

Manager's suspicion: the measurement itself is off (wrong stem x, box
centre instead of the matched `Q.STEM` row, or a canonical-cell vs
page-pixel mismatch). **Checked and refuted**: the canonical->page affine
derived from each glyph's own `Q.GLYPH_BOX` row (`bbox_page_px` paired with
its own canonical `x,y,w,h`) reproduces all 24 sibling glyphs' own stored
`bbox_page_px` in `cell/3/0/8/6` to the third decimal place -- there is no
frame bug. The `Q.STEM` row named in each `Q.NOTEHEAD_STEM_CROSS_INK` row's
own `detail["stem"]` genuinely, geometrically overlaps the notehead's own
box (checked numerically for `glyph/3/0/8/6/12`: stem canonical x 284-323
sits inside the box's own 186-336, near its right edge -- the shape a real
attached stem should have). Drawing confirms this for every crop below: the
blue line always lands on or at the edge of the red box, not somewhere
else entirely.

**The real cause, by crop**: on this MERGING, tremolo-heavy plate, the
LEFT/RIGHT split regions pick up ink that is genuinely present there but
belongs to something OTHER than this note's own stroke -- a neighbour's
stem or head, a slur arc, a beam the detector's own box doesn't fully
cover, or (on a narrow box) the two regions collapsing onto each other.
None of the 8 count-page samples is a stem-assignment or frame bug.

Rendered with `render_page_matching_gather` (one `render_page` call, no
second `deskew` -- lane-2.48-recipe's own finding), at the gather's own 600
dpi, upscaled x3 (all crops >= 600 px wide). Red = the notehead's own
`Q.GLYPH_BOX` (page px, straight from the record). Blue = the exact stem x
used (`Q.STEM` row named in the crop's own label), converted canonical ->
page the same way `gather._page_box` does. Green/orange translucent =
the LEFT/RIGHT regions `gather._stem_cross_regions` actually measured.
Text = left/right ink fractions, the 0.12 floor, `would_fire`, and whether
a `Q.BEAM_STROKE` box overlapped either region (`beam_excluded_overlap`).

## The two named fixed cases (page 13, single-page re-gather)

- **`glyph_13_1_10_2_0.png`** -- `glyph/13/1/10/2/0`. A real tremolo slash:
  the box shows a clear diagonal stroke crossing the stem. `would_fire=True`
  (0.83/0.43). CONFIRMED REAL.
- **`glyph_13_1_8_13_5.png`** -- `glyph/13/1/8/13/5`. ⚠️ In THIS re-gather
  this index IS a slash itself (the box shows a clean diagonal stroke, no
  head at all), already refused by 2.42's own `stacked_head_duplicate`
  with no tremolo rule needed. **Glyph indices are not stable across
  re-gathers** (detector output order can differ run to run) -- this is
  NOT the same physical box the original whole-movement record named "the
  real open head 2.42 lost to the slash". Re-confirming that exact shape
  needs the SAME committed record the roadmap row cites
  (`library/_shared-records/beethoven5-litolff-mvt1-whole-20261001.record.json`),
  not a fresh single-page gather.
- **`glyph_13_1_8_13_4.png`**, **`glyph_13_1_8_13_2.png`** -- the stacked
  group's other two members, both `would_fire=True`, shown because this is
  the only index-stable way to see the shape the roadmap text described.
  `_2` looks like a real filled head with a stem (shares `obs020462` with
  `_4`); `_4` sits between two visible tremolo strokes. This bar is dense
  with real tremolo figures -- consistent with the earlier crop-check
  finding that refusals here are sound, but it shows the SAME passage that
  motivated this rule is itself hard to split cleanly between "this note's
  ink" and "the next slash over".

## 8 refusals on the count page (page 3), random sample

| crop | left/right | cause |
|---|---|---|
| `glyph_3_0_8_6_12.png` | 0.84 / 0.28 | Box edge sliver: the "right" region is a ~12 canonical-px strip at the box's own trailing edge, wide enough to catch a few px of the next note's own ink. No beam, no slur -- plain neighbour bleed on a MERGING plate. |
| `glyph_3_1_7_4_0.png` | 0.79 / 0.64 | 3-note beamed run, boxes packed tight: the "right" region reaches into the ADJACENT note's own stem. `beam_excluded_overlap=False` -- this is a neighbour's STEM, not a beam, so today's exclusion can't touch it. |
| `glyph_3_1_0_6_0.png` | 0.76 / 0.62 | An isolated ledger note under a SLUR arc: the slur's own stroke crosses the box's upper rows on the right side. A foreign mark, not beam-classed, so not excluded. |
| `glyph_3_1_7_1_4.png` | 0.26 / 0.42 | Box itself is a thin sliver barely wider than the stem+guard -- the LEFT and RIGHT regions nearly coincide with the box's own edges rather than being a real split of anything. Measurement degenerates on a narrow box. |
| `glyph_3_1_4_0_10.png` | 0.24 / 1.00 | Note sits on a staff line, merged with a stroke below (barline or another stem) -- the box reads as solid ink. `right=1.0` is not "ink on both sides of a stem", it's "this box is entirely dark." |
| `glyph_3_0_10_2_1.png` | 0.79 / 0.34 | A SLANTED beam visibly crosses the box at the top, but `beam_excluded_overlap=False`: the detector's own `Q.BEAM_STROKE` box does not reach far enough along the slant to cover where it touches this particular note, so the exclusion built for 2.49 misses it. |
| `glyph_3_1_7_17_3.png` | 0.37 / 0.56 | Box sits flush against a dense cluster of overlapping stems immediately to its left (a chord/beam terminus) -- neighbour bleed. |
| `glyph_3_0_8_6_23.png` | 0.57 / 0.45 | Very crowded multi-voice passage; adjacent note blobs touch the box on both sides -- neighbour bleed. |

## Per-cause counts (8 count-page samples)

- **Neighbour notehead/stem ink bleeding across the split line** (dense/
  merged plate, not beam-classed): **4** -- `3_0_8_6_12`, `3_1_7_4_0`,
  `3_1_7_17_3`, `3_0_8_6_23`
- **Foreign mark not excluded (slur arc crossing the box)**: **1** --
  `3_1_0_6_0`
- **Narrow box -> regions degenerate onto the box itself**: **1** --
  `3_1_7_1_4`
- **Solid/merged ink (note on a staff line or fused with a stroke below)**:
  **1** -- `3_1_4_0_10`
- **Real beam, but the detector's own beam box doesn't cover the slant far
  enough for today's exclusion to catch it**: **1** -- `3_0_10_2_1`
- **Wrong stem matched, box-centre-not-stem, or canonical/page frame bug**:
  **0** -- checked directly (affine cross-check against 24 sibling glyphs,
  exact to 3 decimals; stem geometrically overlaps the box as designed)
  and visually (blue line lands on/at the box in every crop)

No code changes in this step; `TREMOLO_SLASH_SHIPS` stays `False`.
