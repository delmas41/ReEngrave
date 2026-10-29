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
