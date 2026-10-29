# Plan 2026-10-28: shared ink map step 6, FILL from the head's own strokes (ROADMAP 2.220)

STAGED GATHER + ADJUDICATE. Plan written on Opus; the build runs on Sonnet. Measurements:
`benchmarks/ink-map-fill-2026-10/FINDINGS.md`. Parent plan: `docs/plan-2026-10-22-shared-ink-map.md` §5, step 6.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a head is hollow if and only if its own ink encloses paper
(page-facts: "a hollow note with nothing on the stem is always a half"; 2.148/2.159 rulings stand). A head's position stays
its detector box centre (2.50 rejected; nothing here moves pitch). This is falsified if Sean's 8 tiles show filled heads
whose ink encloses paper (cracked plates) or hollow heads closed by the scan.

## 1. Cause first, and the process lesson

- **The stroke map has no head.** `map_strokes` claims verticals and horizontals before it looks for blobs. That cuts a hollow
  head's ring into 2-3 lunes plus horizontal rims, so `hole_share` is 0.0 on all 766 written halves, the same as on filled
  heads. Step 6 as planned on 10-22 ("hole share, slit, window all derivable from the blob") cannot work: there is no single
  blob to measure.
- **Fill is read in the detector's box, not on the head's ink.** The 2.148 slit runs only inside a box 1.1-1.9 x 0.9-1.8 sp.
  Outside that box it files `fill null, not_head_sized`, and the detector's black class is written unread. This is the
  biggest fill error at the file: 26 Litolff and 6 Brahms written black where the ink reads hollow. 7 of the 26 are
  slanted halves boxed 1.91-2.02 sp wide (2.204 tile 1).
- **Two smaller causes.** A line through the hole makes the 2.23 window say filled where the slit says hollow (26 of 40 on
  Litolff). A black head takes a half from its stem-mate (`stem_value_follows`: 15 / 7).
- **Process lesson.** The step 1 producer was proven by parity against the consumers it replaced first (stems, beams,
  arcs, ledgers), never against heads. "Derivable" was a claim nobody measured (rule 7: run the control where it can fail).
  From now on, each ink-map step opens by measuring its own field on the population it will serve, on a saved record,
  before anything is planned on it.

## 2. The design: one fill reading per printed head

**Producer `Q.HEAD_INK` (GATHER, one row per HEAD STROKE SET, not per box).**
- *Which strokes.* Start from `Q.GLYPH_STROKES`. Take the box's strokes minus those another mark owns: a `vertical`
  that runs past the head is the stem; a `horizontal` longer than about 2 sp is a beam or a ledger rung (the step 7 reader
  when it lands). Keep the rest of the head's pieces, the rim `horizontal` pieces included.
- *Repairing the ring.* Re-join those pieces on the unerased raster in the head's neighbourhood. Line rows come back only
  where they lie between the head's own pieces, which mends the eraser's cut and leaves the line outside alone.
- *What is measured on that one mask.*
  - `hole_share`: enclosed paper, measured after a 1-px close;
  - the slit (2.148's `rows_share`) and the centre/ring window, both centred on the mask's centroid instead of the box;
  - the extent in sp (width and height of the ink, not of the box);
  - `line_rows_restored`;
  - `stem_cut` (the head was cut at the stem side);
  - `n_pieces`.
- *Value.* `hollow` / `filled` / None, with the margin to the nearer cut. None says why: `not_one_head` (the extent is not
  one head's ink), `ring_open`, or `readers_split`.

**Consumer** (`OMR_FILL_FROM_STROKES`, default OFF). `adjudicate_duration` reads `Q.HEAD_INK` once, at the place 2.148's
first step sits now, for every class, black or hollow. The head-sized gate now tests the head's ink extent, not the box.
- Class and ink agree: decided as today.
- They disagree: narrowed to {filled, hollow} with both candidates, written GUESSED (blue) if INFER or the bar picks.
- Ink None: the class stands as today, filed as `fill_unread` and counted.

The ink None case is the one place this plan picks an answer, and it does not invent: the detector class is a reading.
That case goes to Sean if the count is large.

**What retires** (parity first, deleted in plan step 10):
- in ADJUDICATE: `_head_reads_hollow_first`, `_head_reads_hollow_on_located_box`, `_head_reads_hollow_on_bridged_box`, the
  ink half of `_head_is_open` (`_ink_reads_decisively_hollow`, `_hollow_readings`, `_raw_reads_firmly_hollow`), `_reads_filled`,
  `notehead_precision._hollow_ink_reading`, the box-size gate for fill;
- in GATHER: `notehead_recentre.fill`, `stacked_head_fit`'s hollow branch, the `interior_white*` details of `Q.NOTEHEAD_INK`.

The 2.148/2.159 cuts are kept as the consumer's cuts on the new measurement (plan 10-22 §4: the measurement is shared, the
cut stays per consumer).

**2.212, one subject per printed head.** Two head boxes whose owned stroke sets are the same, or where one covers at least 90%
of the other's ink, are ONE printed head. They share one `Q.HEAD_INK` row; the boxes keep their class candidates and point
at that row. The fill is read once, so no ink change can flip a keeper. 2.212 then merges the boxes on this key instead of
`_stacked_head_duplicate_refusal`'s ink comparison per box. Today there are 143 / 23 black+hollow twin pairs.

**2.214, the mark-isolated mask.** The same ownership pass that makes the head mask files, per non-stem mark, its own
pieces with stems and beams removed: ends, length, thickness profile and hole. A tremolo slash fused to a beam stub or a
ledger rung is a `horizontal` stroke 2.9-3.2 sp long (2.214 FINDINGS). The thickness profile splits it where the head's lens
(thick) meets the rung (thin); 2.214 reads its ends there.

**Rule 8.** No fallback turns "cannot read the fill" into filled or hollow: None plus the class is recorded as the class
alone. A red or blue mark follows only from the disagreement path.

## 3. Build order, each step proven cheaply (level named per CLAUDE §6)

| # | milestone | proof | level |
|---|---|---|---|
| 0 | Sean answers the 8 tiles (`out/print/2.220-plan/`) | how many of class A are real halves vs non-notes | print |
| 1 | `Q.HEAD_INK` producer, flag ON in GATHER, read by nothing. Fence: `stroke_map.py` new function `head_mask`, `gather.gather_head_ink` | small gather, 2 pages per plate (Litolff 4, 6; Brahms 5, 14), detector cache. (a) hole > 0 on >= 95% of written halves (base: 0% today); (b) agrees with the slit on head-sized boxes >= the slit-window rate (96.8% / 98.6%); (c) the exported file byte-identical OFF vs ON, same tree and pages | READER (a, b); FILE vs FILE (c) |
| 2 | Consumer in `adjudicate_duration`, behind `OMR_FILL_FROM_STROKES` | re-adjudicate milestone 1's saved gather OFF vs ON, same tree. `lane_report` control lines: judged right->wrong 0, unwritten->wrong 0, invented->removed counted; notes matched by place. Class A (26 / 6) and 2.204 tile 1 counted. 12 blind tiles | FILE vs FILE |
| 3 | Twin key for 2.212 (one `Q.HEAD_INK` per stroke set) | on the same saved gather: twin pairs sharing one row; the keeper unchanged when the eraser flags flip (2.206d's 4 lost + 7 pitch changes) | READER, then FILE vs FILE |
| 4 | Mark mask for 2.214 | 2.214's 8 answered tiles + 42 crops: slash vs fused head separated by ends on the mask | READER, against Sean's answers |
| 5 | Stem-mate check (class B, 15 / 7): a black-ink head on a hollow-ink head's stem narrows instead of following | re-adjudicate, as in milestone 2 | FILE vs FILE |
| 6 | Full frozen sample (fail-fast subset clean first), then hand over to the plan's step 10 retirement | `docs/measuring.md` §0, the three measures | FILE vs FILE |

Baselines always come from the same stages, the same pages and the same tree as the arm they are compared with. No arm's
verdict is set against another arm's file.

## 4. Sean's question

"Eight pictures, one orange box each (the box only shows where to look). For each: is it a half note, a filled note, or
not a note?"

## What earlier notehead / hollow work taught us

Form: lesson | source | how the plan respects it, or CONFLICT. All mechanisms are STAGED unless named LEGACY (none here is LEGACY).

1. **Identity before fill: most "wrong fill" boxes are not heads.** 2.159's two Brahms changes were an ff and tremolo slashes (DECISIONS 2026-10-17); 2.176's were brackets/clefs; 2.164's were tie tails; 2.220's own tiles: 2 of 8 are an ff and a flag (answers.json). | DECISIONS 2.159/2.164/2.176, FINDINGS ink-map-fill | RESPECTED in part (`not_one_head` -> None). CONFLICT: Sec.2 sends "disagree" to {filled, hollow}, and a non-note has a "fill". The consumer must test head-hood (2.159's guards: not on dynamic letter, not under slash ink, box holds the detector centre, own stem; 2.164 `Q.HEAD_OVAL`; 2.137 slash ends) BEFORE it asks fill.
2. **Size cannot decide fill.** The 5 real halves are 1.3-1.9 sp wide, the 3 non-heads larger, a quarter's box swallowed a sharp (2.15 sp). | answers.json 2026-10-28 | CONFLICT: Sec.2 "head-sized gate now tests the ink extent" is fine only if the extent excludes a sharp/flag/ff; "larger box = hollow" would invent 2 and miss 1 of 8.
3. **A solid first reading is not overturned by a late reader; a reading earlier in the order is not overturned by a later one.** | DECISIONS 2.148 (2026-10-16), reading-order ruling 2026-10-16 | CONFLICT: the consumer sits "where 2.148's first step sits" but makes ink/class disagreement a narrowing, i.e. the new reader overturns a decided black. Allowed only if the ink reading IS the notehead-first step (then the class is a candidate, not a verdict); say so, and keep "never calls a head black" (2.159) unless Sean rules otherwise.
4. **A located box is a different measurement, with its own guards.** 2.159 decides a half only if the located box holds the detector centre, the 2.23 window agrees, the head has its own stem, it is not on a dynamic letter/under slash ink. The slit separated hollow/black with 0 errors on his heads; the 2.23 window only ~0.93. | DECISIONS 2.159; head-fill FINDINGS Sec.16 | DUPLICATES 2.159 (`_head_reads_hollow_on_located_box`) and 2.161 (`head_stem_bridge`, `_head_reads_hollow_on_bridged_box`), both landed ON: retirement (plan step 10) needs parity on their tiles (2.159: 8, 2.161: Set G) first. CONSISTENCY: `stem_cut`/vertical ownership must match `head_stem_bridge` (left stem runs down, right stem runs up).
5. **A hollow with nothing on the stem is a half (always).** | page-facts 2026-10-09 | RESPECTED; class B (15/7 `stem_value_follows`) is the opposite direction (black ink following a stem-mate's half): milestone 5 must not turn that into a stem-mate overriding the head's own ink.
6. **Calibrate on the raster the consumer reads; the cell raster differs from the page.** 2.129: blob read 2.17-2.25 on the page, 1.74-2.23 on the cell raster, a 1.8 cut set on the page kept 2 of 5. 2.115 round 1's "stable on the page" centroid was a function of the window. | omr-stacked-heads Step 2; omr-head-recentre R2 | RESPECTED (unerased raster, milestone 1 on a saved gather). CONFLICT: centring the slit/window "on the mask centroid" repeats 2.115's unstable centroid (tile 13 moved 0.36 sp with the window); use the mask's own extent, not a centroid-from-window, or show it stable.
7. **A hollow head's position stays the detector box centre, not the hole.** | page-facts 2026-10-01 (2.50 rejected) | RESPECTED (pitch untouched); the mask centroid is for fill only. 2.212 re-centred unasked: do not repeat.
8. **Re-centring part-boxed heads is safe and inert (2.115, `OMR_RECENTRE_PART_BOXED`, OFF): no hollow gained at the file, tile 13 unfixed.** | omr-head-recentre | `notehead_recentre.fill` is on the retire list; it is OFF, so nothing to preserve, but tile 13 is a free control for `head_mask`.
9. **Stacked heads: a pair a third apart is two heads, an ink column two heads tall; true duplicates stay refused.** 2.129 (filled, ON) and 2.132 (hollow pair, OFF pending Sean's tiles; page raster, staff-line rows left out, ONE stem reaching both >= 1.5 sp past). | DECISIONS 2.129/2.132 | CONFLICT: the twin key "covers >= 90% of the other's ink" must not merge a stacked pair (the ink column of two heads contains each head); the fit must split by stack first. Retiring `stacked_head_fit`'s hollow branch would remove the 2.132 logic Sean has not yet ruled on: keep it unless he does. Also 2.132 leaves line rows OUT; the plan restores them: the two must agree on a staff line through a hole.
10. **A staff line through the hole makes the window say filled while the slit says hollow** (26 of 40 Litolff, FINDINGS ink-map-fill); on Litolff the hole is a thin slanted sliver. | page-facts Litolff halves; omr-head-fill | RESPECTED (slit is primary; ring repair restores lines only between the head's own pieces).
11. **The floor on a head's width must be priced on the population we read correctly.** A notehead is ~1.3-1.4 sp; the floor flagged 0 of 103 confirmed heads; 46 of 180 sampled "notehead" boxes were not heads. | omr-notehead-width-2026-09 | RESPECTED: gate on the ink extent; reuse that floor; Litolff merges and Breitkopf shatters (a mask is not a mark).
12. **A whole note is a HOLLOW head no stem touches; a filled or stem-touched whole-class box is never a whole.** 53 of 56 whole notes were digit loops, rest curls or whole-rest blocks. | DECISIONS 2.173 (2026-10-19) | CONFLICT: `hole_share` > 0 is also true of a digit loop and a rest curl, so a hole alone proves nothing for a whole-class box; Q.HEAD_INK "hollow" must not feed a whole value without 2.173's no-stem test and the meter-claim of 2.177.
13. **A tremolo slash is told by its ENDS, not slant.** | DECISIONS 2.137 (2026-10-15), page-facts 2026-10-27 | RESPECTED (plan step 4 / 2.214); 2.137's tile 9 (a deformed open half refused) is the known cost: accept as rare.
14. **A rate from another population is not a rate** (CLAUDE rule 7). | CLAUDE.md | Milestone 1's Litolff 4,6 / Brahms 5,14 sample is the acceptance plates; the 766 "halves" in FINDINGS are written halves only, i.e. exactly the population the gate already admits (selection bias: the 8 failures lie outside it).

### Proposed changes (for Sean)
- A. In Sec.2, add a head-hood check ahead of the fill read (2.159's guards + `Q.HEAD_OVAL` + slash ends), and let an ink extent that holds a sharp/flag/ff be `not_one_head` -> unread, nothing invented.
- B. Say that the consumer never calls a decided black head hollow-then-black by overturning: it either narrows (blue) or keeps 2.148/2.159's "never calls black" rule; ask Sean.
- C. Make the twin key split a stacked pair first (2.129/2.132) and leave `stacked_head_fit`'s hollow branch until the 2.132 tiles are answered.
- D. Do not centre windows on a centroid (2.115); centre on the mask extent or prove stability on tile 13.
- E. Retire 2.159/2.161 code only after parity on their own tiles (`out/print/2.159-review/`, `2.161-review/`).
- F. Whole-class boxes: HEAD_INK hollow never writes a whole without 2.173's tests.
