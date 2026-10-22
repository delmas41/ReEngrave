# ROADMAP 2.49 -- three-test redesign, real-data re-check

Sean's redesign (DECISIONS 2026-10-01): a tremolo slash is (1) a THICK
DIAGONAL stroke, not round, (2) crossing the stem with a REAL SHARE of the
glyph's own ink on BOTH sides (never a tiny bleed), (3) on the stem's
SHAFT, away from both ends. All three gates now read `Q.NOTEHEAD_STEM_
CROSS_INK`'s new `angle_deg`/`elongation`/`fill`/`left_share`/`right_share`
fields (GATHER, stem-column AND beam ink both excluded) plus the matched
`Q.STEM` row's own box (`Q.STEM` re-added to this decision's `wants`).

**Bug found and fixed in GATHER during this round**: computing shape over
the WHOLE box (stem column included) read the confirmed real slash
`glyph/13/1/10/2/0` at elongation 1.5 -- indistinguishable from a round
head -- because the stem's own thick, near-vertical stroke runs straight
through the box and dominates the moment calculation. The shape/share mask
is now the box with that same centre column blanked (the union of the
LEFT/RIGHT regions `_stem_cross_regions` already produces), never the raw
box.

**Threshold calibration**: a clean synthetic slash (35 degrees,
thickness-26px) reads elongation 5.87-6.07; a synthetic round head reads
1.3-1.4. Real scanned ink reads lower on both ends than the clean
synthetic: the confirmed-by-crop real slash `glyph/13/1/10/2/0` reads only
1.9 (anti-aliasing + fusion with nearby chord ink), and the confirmed real
heads sampled read 1.08-1.33. `SHAPE_MIN_ELONGATION` is set to **1.8** --
just below the lowest confirmed real slash, above every confirmed real
head measured so far. This is a narrower real margin than the synthetic
one suggested, which is why CROSSING (>=0.30 share each side) and POSITION
(>=0.5 box-heights from either stem end) carry real weight rather than
shape alone. `SHAPE_ANGLE_MIN/MAX_DEG` stay 20/70, `SHAPE_MAX_FILL` 0.55
(unchanged from the first build, both still clear of every real sample).

## Firing count

- **Count page (page 3) alone**: **2** of ~481 notehead-classed glyphs --
  down from **121-132** in the first build. (At the more conservative 2.5
  elongation floor the first build also tried, the count page's firings
  were already down to 0; loosening to 1.8 to catch the named real case
  reopens 2 new, both ambiguous -- see below.)
- **Across the small re-gather's full page range (pages 1-3)**: **6** total
  (of 496 notehead-classed glyphs that reached a stem and got a shape
  read).
- **The two named fixed cases** (fresh page-13 single-page gather): BOTH
  now fire correctly at the 1.8 floor. `glyph/13/1/10/2/0` (angle 23.7,
  elongation 1.9, fill 0.40, shares 0.35/0.65) -- confirmed real by crop.
  On the stacked shape at `cell/13/1/8/13`, `glyph/13/1/8/13/4` also now
  fires (angle 20.4, elongation 2.06, fill 0.51, shares 0.51/0.49) and the
  real open head `glyph/13/1/8/13/2` correctly does NOT (elongation 1.08,
  crossing share 0.03/0.97 -- a tiny bleed, fails crossing too).
  `glyph/13/1/8/13/5` (the index the roadmap text names) carries no stem
  match in this fresh single-page gather at all (glyph indices are not
  stable across re-gathers, noted in `review/index.md` already).

⚠️ Crop text shows STALE `shape_ok`/`would_fire` booleans for the two named
cases and `glyph/3/0/9/6/6`/`glyph/3/0/10/3/5` below -- those records were
generated with the elongation floor at 2.5 before the final 1.8 calibration;
the raw `angle_deg`/`elongation`/`fill`/`left_share`/`right_share` numbers
in each crop are current and correct, and the firing counts above are
recomputed by hand against the FINAL 1.8 floor, not read off the stale
booleans.

## Crops, looked at by hand

| crop | numbers | verdict: slash or not |
|---|---|---|
| `glyph_2_1_8_11_1.png` | angle 26.2, elong 2.79, fill 0.38, shares 0.59/0.41 | **REAL SLASH** -- clear thick diagonal stroke crossing the stem. |
| `glyph_2_1_8_11_4.png` | angle 26.6, elong 2.79, fill 0.35, shares 0.60/0.40 | **SAME MARK as `_11_1`**, boxed twice (2.42's own duplicate-box population) -- real slash. |
| `glyph_2_1_8_12_4.png` | angle 26.5, elong 2.55, fill 0.36, shares 0.51/0.49 | **REAL SLASH** -- same clear diagonal pattern, a different note. |
| `glyph_2_1_9_12_5.png` | angle 20.0, elong 2.05, fill 0.32, shares 0.55/0.45 | **REAL SLASH** -- same pattern again. |
| `glyph_3_0_9_6_6.png` | angle 25.3, elong 2.19, fill 0.51, shares 0.33/0.67 | **AMBIGUOUS / LIKELY NOT A SLASH** -- box sits on a staff line in a dense beamed cluster; looks like a note merged with the line, not a clean diagonal. A real diagonal mark is visible in the ink NEARBY (below the box) but the box's own content reads as borderline. |
| `glyph_3_0_10_3_5.png` | angle 20.0, elong 2.47, fill 0.46, shares 0.37/0.63 | **AMBIGUOUS / LIKELY NOT A SLASH** -- a small mark near the staff with `ff` dynamics printed above/below; a faint diagonal is visible just outside the box but the box's own ink is not unambiguously a thick diagonal stroke. |
| `glyph_13_1_10_2_0_NAMED.png` | angle 23.7, elong 1.9, fill 0.40, shares 0.35/0.65 | **REAL SLASH** (confirmed in `review/index.md` already; re-confirmed here with the new fields). |
| `glyph_13_1_8_13_4_NAMED.png` | angle 20.4, elong 2.06, fill 0.51, shares 0.51/0.49 | **LIKELY REAL SLASH** -- sits between two visible tremolo strokes in a tremolo-dense bar (see `review/index.md`'s own note on this bar). |
| `glyph_13_1_8_13_2_NAMED.png` | angle 68.5, elong 1.08, shares 0.03/0.97 | **CORRECTLY NOT FIRING** -- a real filled head, tiny crossing share, round shape. |
| `glyph_13_1_8_13_5_NAMED.png` | no stem match in this fresh gather | unusable for this check (index instability, see `review/index.md`). |

## Summary

Of 6 count-page-range firings: **4 confirmed real slashes by crop, 2
ambiguous** (borderline shape numbers, box content not unambiguously
diagonal). Both named fixed cases now fire correctly (or, for
`glyph/13/1/8/13/5`, cannot be re-tested in a fresh single-page gather due
to index instability already noted). This is an order of magnitude
improvement over the first build (121-132 -> 0-2 on the count page itself),
but the two ambiguous firings show the SHAPE floor is still right at the
edge of what real scanned ink separates cleanly -- not yet a result to
ship.

No change to shipping status: `TREMOLO_SLASH_SHIPS` stays `False`.
