# `benchmarks/omr-local-staff-2026-09/` — FINDINGS

## ROADMAP 2.50 — a hollow head's centre is the centre of its white interior

Sean, 2026-10-01, on a contact sheet of 15 clean Litolff p3 heads
(`out/print/2.48/recipe/clean_heads_sheet.png`, unmerged `lane-2.48-recipe`):
*"The boxes look very centered. Only occasionally on the hollow heads do the
center look a bit high - but barely. The hollow heads should have a center
in the white of the head."* DECISIONS, same date: *"have a lane work on
making sure we know where the center of a hollow head is and that it is
labeled well. Small difference."*

### What was built

STAGED, GATHER only, one new quantity, `Q.HOLLOW_HEAD_CENTRE`
(`tools/omr/staged/record.py`), filed by `gather.gather_hollow_head_centre`
for every hollow-classed glyph (`geometry.is_hollow_notehead`:
`noteheadHalf*`/`noteheadWhole*`/`noteheadDoubleWhole*`, derived from
`class_aliases.vocabulary()` by prefix at runtime, never a hand-typed list
of the OnLine/InSpace/Small spellings).

The reading (`gather.hollow_head_hole_centre`): the connected component
(4-connectivity, flood fill) of NON-ink pixels strictly inside the glyph's
own detector box that does NOT touch the box's own border, off
`cell.image_no_staff` — the SAME staff-erased raster `Q.NOTEHEAD_RECENTRE`/
`Q.NOTEHEAD_INK` already read. Because the raster is already erased, a
line-note's own staff line crossing the hole is already gone by the time
this reader sees it — no separate masking step exists in this function, it
reuses the project's own standing erasure (CLAUDE.md rule 6, connect never
re-derive).

Value is the component's own CENTROID — the mean of its pixel coordinates,
**not the bounding-box midpoint**: a hole a staff line cut unevenly, or
whose ring is thinner on one side, has a centroid that follows where the
white actually sits, while a bbox centre follows only its most extreme
pixels.

Abstains (never falls back to the box centre, CLAUDE.md rule 8):
- `no_mask` — cell carries no `image_no_staff`.
- `no_staff_geometry` — box off the raster, or too small (< 3px either
  dimension) to carry a measured interior at all.
- `no_enclosed_hole` — zero, or more than one, non-border-touching
  component. A filled-in scan, a broken ring (the outside background
  leaks in through the gap, which reads as a border-touching component
  and is excluded), and a genuinely ambiguous multi-pocket merge are all
  the SAME fact from this reader's own vantage: it could not find exactly
  one hole, and guessing which candidate (or where) is exactly the guess
  rule 8 forbids.

`Q.HOLLOW_HEAD_CENTRE` does **not** touch `Q.NOTEHEAD_STAFF_POSITION` or
any other default this round — `reach --check` names it producer-only on
purpose (`reach.KNOWN_GAPS`), first consumer named there is next round's
work.

### Tests (RED → GREEN)

`tools/omr/tests/test_staged_hollow_head_centre.py`, 16 tests:
- pure-function controls on synthetic rasters: an open head in a space, an
  open head on a line (line drawn across the hole then erased back to
  background, matching the real `image_no_staff` convention — proves the
  reading is identical to the unobstructed case), a box shifted 3px (the
  reading follows the ink, not the box), a filled black head (not
  measured), a broken ring (abstains), off-the-raster and too-small boxes
  (`None`).
- `is_hollow_notehead` classification (half/whole/double-whole hollow,
  black is not hollow, unknown/`None` is not hollow).
- the GATHER reader wired into a `Log`: a hollow head in a space is
  observed; a regular black head gets NO row at all (ABSENT, never a
  guessed row for a class outside the gate); `no_mask`/`no_enclosed_hole`
  abstentions.

RED confirmed by `git stash` of `gather.py`/`geometry.py`/`record.py`/
`capture.py`/`reach.py` together (the five files this round touched) — all
16 tests fail (`AttributeError`/`ImportError` on the new names). GREEN on
this branch, all 16 pass. `pytest -m "not slow"`: 4,223 passed (base 4,207
+ 16), 0 failed, 3 skipped, 2 xfailed.

### `check`

`python3 -m tools.omr.staged.check`: TOTAL 246 (base `origin/main` 245).
The one new finding is `reach`'s own producer-only entry for
`Q.HOLLOW_HEAD_CENTRE` — expected, and named in `reach.KNOWN_GAPS` exactly
as the brief asked ("if reach flags it as producer-only, say so"). Every
other sub-check (`wiring` 67, `capture` 18, `gather_coverage` 15,
`inventory` 10, `health` 0, `brakes` 9, `trace` 3) is unchanged at
baseline — `wiring`/`capture` needed one entry each
(`capture.UNSCORED["HOLLOW_HEAD_CENTRE"]`, `capture.READER_RASTER
["CV_HOLLOW_HEAD_CENTRE"]`) to stay at baseline rather than add two
findings apiece for the new quantity/reader.

### Real data — small re-gather, Litolff p3

`python3 -m tools.omr.acceptance_quick --doc beethoven5-litolff`
(GATHER+ADJUDICATE default, `--weights auto`, gathers pages 1-3 for the
meter/key carry, reports on page 3). Record:
`benchmarks/acceptance/quick/out/beethoven5-litolff/
beethoven5-litolff-p3.record.json`. Analysis script:
`benchmarks/omr-local-staff-2026-09/analyze_2_50.py` (reads the record's
own rows only — no re-measurement).

- **Population**: 77 of 352 hollow-classed glyphs measured (exactly one
  enclosed hole found); 275 abstained, all `no_enclosed_hole`. Litolff is
  the MERGING plate (CLAUDE.md §10) — at this DPI/weights most hollow
  heads do not print with a cleanly separated ring once rendered and
  binarized, which is a real population gap this reader reports honestly
  rather than guessing past.
- **Hole centre minus box centre**, canonical cell px, n=77: horizontal
  mean +2.73px (stdev 23.25px), vertical mean +1.42px (stdev 21.10px). The
  mean is modest and in the direction Sean named (hole sits lower/right of
  the box centre on average), but the SPREAD is roughly half a staff
  space (half_step measured 50px on this page) — a few of the 77 "clean"
  reads are likely a NEIGHBOURING glyph's hole (a chord-mate or an
  adjacent merged blob) rather than this glyph's own, visible as the
  largest outliers (`dy` up to ±57px, more than one half-step) in
  `analyze_2_50_output.json`. Flagged, not filtered — a later round
  should decide whether to gate on hole size/position before trusting it
  as a position signal.
- **Rounded staff position would change for 29 of the 77 measured heads**
  if the hole centre replaced the box centre (`analyze_2_50_output.json`,
  `rounded_position_changes`).
- **Right vs wrong against the reference encoding: NOT measured this
  round.** The small re-gather stops at ADJUDICATE (CLAUDE.md §6b, "every
  test for now is GATHER+ADJUDICATE only") — there is no pitch yet to
  compare. Matching a candidate position change to the reference
  note-by-note needs the `--full`/whole-movement EXPORT path (clef
  applied, notes ordered within the bar) and is next round's work
  alongside actually wiring `Q.HOLLOW_HEAD_CENTRE` into a consumer.

### Contact sheet

`out/print/2.50/hollow_head_centre_sheet.png` — 15 tiles, Litolff p3,
600dpi, ×3 scale (matching `out/print/2.48/recipe/clean_heads_sheet.png`).
Every head whose rounded position would change is included first, padded
to 15 with the remaining measured heads. Per tile: red box + red cross =
detector box and its centre; magenta cross = `Q.HOLLOW_HEAD_CENTRE`'s own
hole centroid (converted from the glyph's canonical cell frame to page
pixels via that SAME glyph's own box_canon→box_page affine — no second
measurement); green = the real 5 staff lines only, never extended; blue
ticks = every line/space half-step within the crop. Verified by PIXEL ROW
(not by eye) on 3 tiles before writing: every drawn green line row is
≥50% ink-covered within ±1px — PASS on all 3. Script:
`benchmarks/omr-local-staff-2026-09/hollow_head_centre_sheet.py`.

By eye: several tiles show the magenta cross sitting lower, inside the
visibly darker/open part of a merged blob, than the red cross — consistent
with Sean's own observation. Several others (the more heavily merged
Litolff ink) show both crosses close together, or the drawn box only
loosely tracking any visible ring at all — the `no_enclosed_hole`
population this round reports rather than guesses past.
