# One shared ink map -- a plan (ROADMAP 2.194)

**Date:** 2026-10-22. **Path:** STAGED (GATHER files the map; ADJUDICATE decides ownership; readers consume). **Read from:** main
`1cd6413e0`; no code changed, no gather run. **Measurements:** `benchmarks/shared-ink-map-2026-10/FINDINGS.md` (every number below
is produced by a script there, on the frozen 8-page sample per plate, or cites a named FINDINGS). Sean, 2026-10-22: *"This is what I
was asking for with the ink claiming requests earlier."* Sean, 2026-10-21: *"the one mark one box was what I had in mind for
claiming ink. Each cell should claim its own and the one it belongs to should decide what it is not the other staff."*

## In plain words

Today about two hundred functions (205 by a strict count, 450 by a loose one) go back to the pixels and measure the ink themselves,
each with its own cut-offs (787 of them) and its own idea of where the staff lines are (ten implementations of "the lines at this
x"). So one stem is measured by seven readers, one beam by four, one notehead's hole by seven, one ledger rung by five -- and
nobody compares the readings. When they disagree, an adjudicator settles it with a rule written for that pair: "a rest whose stroke
runs into a head is a stem", "a box on another mark's ink", "two boxes on one ink, refuse both". There are about twenty-five such
rules, and they fire thousands of times a movement.

How often do the readers disagree? On the same ink, a third to a half of the time: the CV beam reader and the detector disagree
about whether a cell holds beams at all in 31% (Litolff) / 55% (Brahms) of cells; the detector's ledger ladder and the CV rung reader
disagree on 34% / 38% of far heads; the detector says "black head" where the ink window says "hollow" on 5.9% / 1.4%; the stem finder
finds a stem the reach ruler cannot see on 3.9% / 9.0%. When I looked at 18 of these in crops, the pattern was two things: one
reader plainly wrong (a flag boxed as a beam, three times; a stem the ruler read as 0.03 spaces), and -- in 5 of 18 -- a box that
was never a head at all (a dot, a stem sliver), so the two readers were measuring different ink under one wrong box. That second
pattern is the lesson: who OWNS the ink has to be settled before anyone measures it. 2.185 and 2.186 found the same thing one
level up, at the detector's boxes.

The idea is to measure each piece of ink ONCE, as a stroke -- its length, angle, thickness, curvature, fill, where it starts and ends
against the staff lines measured at its own x -- and file that on the record as a fact. A detector box then becomes a HYPOTHESIS
over strokes ("these three strokes are an eighth note"), a claim in the 2.181 register becomes a list of strokes, and ownership is
decided once per stroke, on evidence, by the cell of the staff it belongs to. Every reader that today re-measures (the stem readers,
the beam readers, the head-fill readers, the ledger readers, the rest tests) consumes the shared stroke instead, keeping its own
cut-off if it needs one. The twenty-five pair rules collapse into one question asked once: which mark owns this stroke, and does its
shape fit that mark.

Two things it does NOT do, so nobody expects them. It does not shrink the records by itself: the records are 1-9 GB because every
duration verdict cites every row of its cell (560 rows on average, `basis` is 64-77% of the bytes; the ink measurements are 30 MB
of 1,269 MB) -- a verdict that cites a few stroke ids instead will, and that is a step here, but it is bookkeeping, not reading. And
it does not read what the detector never boxed and the strokes cannot name alone: a stroke map says "a head-sized blob with a stem
stands here"; naming it a note still takes the detector or Sean (rule 6).

---

## 1. The cause, measured (FINDINGS §1-§5)

- **Who re-measures the same ink.** Stem: `stem` (cv_lines), `head_stem_reach`, `stem_tip_ink`, `notehead_ink.stem_bridge`,
  `stem_slash`, `beam_stem_join`, `beam_stem_levels`. Beam: `beam_stroke` filed by TWO readers (CV and detector), `beam_stroke_ink`,
  `beam_stem_levels`, `stem_tip_ink`. Head fill: `notehead_ink`, the 2.148 slit, the 2.159 located box, `notehead_recentre`,
  `stacked_head_fit`, `head_oval`, `head_line_cut`. Ledger rung: `glyph_ladder`, `ledger_rung_ink`, `ledger_ink_under`,
  `ledger_owner_density`, `far_head_owner_ledger`. Arc: `arc_box`, `arc_ink_shape`, `system_arc`. Each measures from the raster with
  its own binarisation (36 sites) and its own local staff lines (10 implementations).
- **How often they disagree** (frozen sample): beams present-or-not per cell 31% / 55%; ledger presence 34% / 38%; arc boxes no
  system arc traced 30% / 57%; head fill 5.9% / 1.4%; stem finder vs reach 3.9% / 9.0%; accidental shape vs detector winner (2.190)
  switch 30 of 80 / 85 of 321. The readers say so themselves: `beam_stem_join:ambiguous` 4,210 / 1,828 and `stem_tip_ink:ambiguous`
  2,721 / 1,827 abstentions on 8 pages; `stems_disagree` 796 / 350 and `beam_discounted_uncertain` 423 / 2,072 whole-movement.
- **Crop-checked** (18, my look, `out/print/2.194-ink-map/`): CV right on beams 4 of 6 (detector boxes on FLAGS), detector right 1,
  unclear 1; ink right on fill 2 of 2 real heads; finder right on stems 3 of 3 real heads; 5 of 18 were not heads (dots, a sliver):
  ownership, not measurement. 4 ledger tiles I could not call -- the remainder, and the right tiles for Sean.
- **Rules that exist only to settle reader disagreement** (fires, Litolff / Brahms, 8 pages): `stacked_head_duplicate` 253 / 53,
  `rest_is_a_duplicate_box` 60 / 241, `notehead_is_a_duplicate_box` 120 / 30, `rest_has_a_stem` 58 / 13, `rest_stroke_into_a_head`
  29 / 41, `rest_is_a_barline` 40 / 19, `tremolo_slash_crosses_stem` 43 / 47, `is_a_rest_twin` 12 / 21, `is_a_beam_piece` 13 / 3,
  `head_cut_piece` 10 / 7, `on_a_rest` 2 / 7; in duration `beam_discounted_uncertain` 180 / 614, `stem_tip_reads_no_beam` 88 / 534,
  `beams_ambiguous` 53 / 33, `head_fill_from_ink` 53 / 63, `hooks_counted` 14 / 41, `flags_disagree`, `tip_readers_disagree`,
  `open_head_flag_contradiction`; the 2.186 family merge and the 2.172 `production_stronger` view merge.
- **Record size.** Verdicts 88%, of which `basis` 64-77%; `duration` 70-80% of verdict bytes; each duration verdict cites ~560 rows,
  each observation row is cited ~31 (Litolff) / ~75 (Brahms) times. Ink measurement rows: ~2%.

**Process lesson (rule 3).** Every one of the twenty-five rules was a lane that found two readers disagreeing on one symbol kind and
wrote a cut-off for that pair on our two plates. The disagreement rate was never measured as a whole; it is a third to a half. A
rule that settles a pair hides the fact that the pair should not exist.

## 2. The design

### 2.1 What a stroke is
A **stroke** is one piece of ink in one cell, measured once on the staff-ERASED cell raster (the one the CV readers read; the
detector keeps reading the original -- `gather_cv_lines` docstring, never erase before the detector), and filed as one row of a new
quantity `Q.STROKE` on the CELL (one row per stroke, like `Q.SYSTEM_ARC`; not one row per cell holding a list -- a verdict must be
able to cite a stroke by id). A stroke is NOT a connected component: Litolff merges a head, an accidental and a beam into one
component and Breitkopf shatters one rest into three; a stroke is what run analysis separates -- a vertical run-stack (stem,
barline, accidental stem, ledger-crossing), a horizontal run-stack (beam, ledger rung, barline-crossing rest body), a blob (head,
rest body, accidental bowl, dot, letter), a traced curve (arc, hairpin line, flag hook). The existing finders already produce
exactly these populations (`detect_stems` step 3-4, `_column_stroke_bands`, `detect_beams`, `_ink_components`, `arcs_system`,
`head_oval`); the map is their union filed once, not a new vision algorithm.

Fields, all in staff spaces and page px, none a decision: `kind` (vertical / horizontal / blob / curve), page box, canonical box,
`length`, `angle_deg`, `thickness` (median run width, and its spread), `sagitta` (curvature), `fill` and `hole_share` (for blobs: the
2.148 slit and 2.23 window numbers both derivable), end points, `touches` (ids of strokes it meets, with the contact length), the
component it came from, and **the staff measured locally at its x**: the five line rows at the stroke's left and right x, the spacing
there, and the stroke's ends in staff steps (page-facts §3: ~1 px decides a near-boundary pitch; the ten local-line implementations
become one, `staff_at_x(cell, x)`, which the whole map and later every consumer calls). One binarisation (`preprocessing`'s), not 36.

### 2.2 A box is a hypothesis over strokes
`Q.GLYPH_STROKES`, one row per detector box (every pass: production, 2.172 views, 2.179 stem-end, rescues): the stroke ids whose
ink lies inside the box with the measured share of each (the `boxes_inside` shape of 2.181, turned around: per box, which strokes).
Filed in GATHER right after detection. Nothing is decided: it says what ink a box stands on. 2.186's "one ink, one mark" is then a
special case readable off the record -- two boxes with the same stroke set in one cell -- and 2.185's census becomes a query.

### 2.3 Ownership: a claim names strokes, and the owner cell decides
The 2.181 register is EXTENDED, not replaced: `Q.CLAIMED_AREA` already has `unit` (`area`) and the plan's own §2 reserved `ink` for
marks whose box is mostly paper over other marks (arcs, hairpins, letters, barlines, beams, stems). An `ink` claim's value is a list
of stroke ids. `claims.covering` gains one branch: a box is held by an `ink` claim where the claim's strokes are the box's strokes
(share from `Q.GLYPH_STROKES`). The area claims stay as they are (meter 2.177, clefs and header column 2.181, key signature
2.183/2.187): an area is the right unit where a convention says nothing else is printed there, and a stroke list where it is not.

A new ADJUDICATE decision, `adjudicate_stroke_owner`, one per stroke, runs after `glyph_owner` (the cross-staff contest: ladder,
range, distance -- page-facts §3) and before the notehead/rest precision rules. It answers "which mark owns this stroke" on evidence:
(1) another staff's cell owns the ink -> the stroke is `owned_by_another_staff` here and is no witness for anything in this cell
(Sean 2026-10-21: the neighbouring staff's crop is a second reading of the same raster, not a witness); (2) exactly one mark claims it
(one box, or one `ink`/`area` claim) -> DECIDED, that mark; (3) two marks of ONE family claim it -> the 2.186 rule (stronger box,
candidates carried, GUESSED/blue); (4) two marks of DIFFERENT families claim it -> the shape of the stroke is asked (is this stroke
beam-shaped? stem-shaped? a bowl?) using the measured fields against the convention for each family, and where the shape FOLLOWS for
one family it is DECIDED; where both still fit, the stroke is **contested**: ABSTAINED with both candidates and their margins,
counted, and no consumer may use it as a witness (rule 8: a contested stroke never turns "cannot tell" into "no beam" or "no stem").
Nothing picks by detector confidence across families (rules 6, 8; DECISIONS 2026-10-21). What a contested stroke means for the
written file is Sean's question (§6).

### 2.4 Where it sits in the stage model
GATHER: `gather_stroke_map` (after staff-line removal and geometry, before every CV reader; it reads only the raster and
`detections`, so by `gather.gather`'s one-sentence rule it may sit right after detection), `gather_glyph_strokes` (after it), and the
`ink` claims filed by the owners' readers. It decides nothing. ADJUDICATE: `adjudicate_stroke_owner` (ownership), then the existing
decisions CONSUME strokes (`ev.rows(Q.STROKE)` through `Q.GLYPH_STROKES`) instead of re-measuring -- `adjudicate_duration` reads a
head's stem as "the vertical stroke the head's blob touches on its engraving side", its beams as "the horizontal strokes that stroke
touches at its tip", its fill as the blob's `hole_share`. EVALUATE/INFER unchanged in kind: INFER may collapse a contested stroke only
among its own two candidates and labels it; EXPORT counts contested and unowned strokes under `unread_ink` beside `not_a_notehead:*`
(the accounting equality; `status_census` gets a partition over strokes with an `unaccounted` bucket a test requires empty).
A stroke's **standing**: READ where one owner is decided and the consumer's measurement is past its cut-off by its margin; GUESSED
where INFER collapsed a two-candidate ownership or shape, or the measurement is inside the margin (written blue with both); UNREAD
where contested or unowned (red mark, nothing invented). The 95% bar is per consumer and measured on Sean's tiles (CLAUDE §4).

### 2.5 The reading order survives
Sean's rule (2026-10-16): notehead -> stem -> beam/flag -> shared stem -> slash/other, a later step never overturning an earlier one.
The stroke map makes the order a walk over the `touches` graph: the blob first (fill), the vertical stroke it touches on the right
side going up or the left going down (page-facts §1), the horizontal strokes at that stroke's far end, the other blobs on the same
vertical stroke, then anything else touching. The order is the same; the measurements are read off one row instead of seven.

## 3. What it retires, and what must not change

**Retired, step by step, never first** (plan 2026-10-20 §5 migration order: file, consult, prove parity on the record, then delete,
keeping the reason string as an alias in the census): the duplicate measurements -- `head_stem_reach`, `stem_tip_ink`'s own column
scan, `beam_stroke_ink` and `local_line_thickness`'s per-column loops (2.191's 2.4-3.8 M `_ink_runs` calls), the detector's
`beam_stroke` rows as a second beam reader (they become `Q.GLYPH_STROKES` entries of beam boxes), `ledger_rung_ink` +
`ledger_ink_under` + `ledger_owner_density` (one horizontal-stroke reading at the ledger steps), `notehead_ink` + the 2.159 located
box + `notehead_recentre.fill` + `stacked_head_fit`'s ink (the blob's fields), `rest_ink_contact` and `unboxed_rest_shape`'s pieces,
`arc_ink_shape` (the curve stroke), `stem_slash` (a short diagonal stroke crossing the stem), nine of the ten local-staff-line
helpers, and 35 of 36 binarisations. The pair rules whose question becomes "who owns this stroke": `rest_has_a_stem` (58/13),
`rest_stroke_into_a_head` (29/41), `rest_is_a_barline` (40/19), `is_a_rest_twin` (12/21), `on_a_rest` (2/7), `is_a_beam_piece`
(13/3), `head_cut_piece` (10/7), `tremolo_slash_crosses_stem` (43/47), `is_an_arc_tail` (1/3), the different-class branch of
`_duplicate_box_refusal` (2.182a/2.184: 98 rest pairs), the 2.172 `production_stronger` merge, and `refuse_owned` in the stem finder
(the plan's step 6: 58 / 126 stems lost to false rest boxes). The duration narrowings `beam_discounted_uncertain` (180/614),
`beams_ambiguous`, `tip_readers_disagree` and `hooks_counted` stop being disagreements between readers and become one reading with
a margin. Expected: tens of bars per movement released (2.167c: two thirds of red bars are missing symbols and wrong values, and
wrong values ARE where these readers disagree -- the beam presence rate is the biggest single number in this plan).

**Stays:** shape rules on the box (`too_narrow`, `clipped_fragment`, `is_a_dot`, `off_staff_glyph`); the cross-staff contest
`glyph_owner`; same-family duplicates (`notehead_is_a_duplicate_box`, `stacked_head_duplicate`, `rest_is_a_duplicate_box` -- 2.186's
rule, now readable as "same stroke set"); the area claims; the detector as the one namer of classes (a stroke map never invents a
class: rule 6, 2.193); 2.190's accidental shape reader (it becomes a consumer of the blob's two corner strokes).

**Must not change:** every page fact (whole rest means the bar; stems up -> right; the ledger lines name the owner; measure locally;
only a clef before the key; cancelling naturals are the signature; Litolff merges, Breitkopf shatters); Sean's rulings (the reading
order; one ink one mark within a family, never across; the bar never moves a decided note; everything merged or inferred is blue;
"I don't want any hidden"); the register is consulted, never a raster erased (2.166's erase moved beam levels); nothing READ on a
cut-off tuned on two plates until a third plate or Sean's tiles confirm it (CLAUDE §4).

## 4. Risks, and what would falsify it

- **One measurement worse than several specialised ones.** A beam reader wants a smoothed thickness over a long run (`_median_filter_1d`
  over columns); a stem reader wants the thinnest column; a head-fill reader wants the hole at the box's centre, not the blob's. The
  plan keeps the MEASUREMENT shared and the CUT-OFF per consumer: a stroke carries the raw per-column widths (compact: the median,
  spread and the run profile at a fixed stride), and each consumer applies its own smoothing and cut to the same numbers. Where a
  consumer provably needs a different measurement (parity fails on the record and the crops say the old reader was right), it keeps
  its own reader and the stroke carries a `measured_by` pointer -- a specialised reader is retired only on parity, never on principle.
- **Litolff's blobs.** Run analysis separates a stem from the head it touches (different run widths), but a beam fused to a slur's
  tail or a flat's bowl fused to a head may stay one blob. Guard: the stroke carries its component id and a `fused` flag where the
  width profile is bimodal; consumers treat a fused blob as NARROWED, never as one mark (the hairpin and arc lessons).
- **Breitkopf's fragments.** A rest in three pieces is three strokes; ownership joins them under one box (the box is the hypothesis),
  never the other way round. Guard: `Q.GLYPH_STROKES` lists all three; a consumer asking "the rest's body" reads the union.
- **The map itself is wrong.** A stroke the map never drew has no owner and no consumer can repair it (the detector's own lesson, §7
  of CLAUDE). Guard, step 1: coverage parity -- every existing `Q.STEM`, `Q.BEAM_STROKE`, `Q.SYSTEM_ARC` and ledger rung must
  correspond to a stroke (>= 99%, the misses named and cropped) BEFORE any consumer switches.
- **Ownership becomes an argmax.** Guard: `adjudicate_stroke_owner` has no confidence branch across families; the contested bucket is
  counted and reported by every lane_report; Sean's tiles are drawn from contested and from newly-decided strokes alike.
- **Order inside GATHER.** The map must run before every CV reader and after geometry; `gather.gather`'s derived-edge rule and
  `GatherOrderError` catch a misorder; `reach.NOT_A_STAGE` must list the new pure module.
- **Record growth.** One row per stroke is ~20-60 rows a cell; Q.INK's per-component form cost 115 MB a page and was retired to one
  row a cell for that reason. Guard: measure bytes a page in step 1 against the ~0.6-3 MB Q.INK cost; cap fields; the `basis` slimming
  step pays for it many times over.
- **In-flight lanes on the same files**: 2.192 (phantom accidentals on rests), 2.193 (sub-floor naturals), 2.187 (key per system)
  edit `family_precision`, `yolo_detector`, `claims`/`key_object`. Fence by function name; step 1-2 touch only new functions.

**What would falsify the idea.** (1) Step 1 coverage parity fails on a plate (the strokes do not reproduce the finders' populations)
and the misses are not a fixable bug -- then a shared map cannot feed those readers and the plan shrinks to ownership over the
existing quantities (still worth having: §2.3 on `Q.GLYPH_STROKES` alone). (2) The first consumer switch (beams, step 3) does not
move the 31% / 55% disagreement into named decisions and contested strokes that Sean's tiles confirm -- then the disagreement is in
the ink, not in the readers, and the fix is detector or convention work. (3) A third plate prints strokes the field set cannot
describe (hand-engraved curves, double-thickness beams) -- then the map's fields are a cut-off, and consumers may only NARROW on them.

## 5. Build sequence (Sonnet lanes, one day each, OFF flag, the three measures of docs/measuring.md §0)

Each step: `python3 -m tools.omr.staged.lane_report --flag OMR_X --out DIR` on the frozen sample (what changed in the exported file;
a GATHER step is re-gathered with the 2.189 detector cache), Sean's 12 blind tiles drawn from the changes, judged right->wrong = 0.
Steps 1-2 change no verdict and are measured by parity and bytes; "NOTHING CHANGED" in the file is their pass. Biggest-and-safest
first: the two producer steps are safe by construction; the first consumer is the biggest disagreement (beams).

| # | step | flag | what it must show | Sean's question first |
|---|---|---|---|---|
| 1 | **`Q.STROKE` producer** (new module `stroke_map.py`, pure; `gather_stroke_map`; `staff_at_x`): strokes with fields from the erased cell raster, one row each; nothing reads it | `OMR_STROKE_MAP` | file byte-identical; coverage parity >= 99% against `Q.STEM`, `Q.BEAM_STROKE`, `Q.SYSTEM_ARC`, ledger rungs, each miss cropped; bytes a page; determinism (two gathers equal) | none |
| 2 | **`Q.GLYPH_STROKES`** per detector box (every pass) + the register's `unit: ink` branch in `claims.covering`; `check`'s census gains "two boxes, one stroke set" | same flag | file byte-identical; the 2.185 same-cell doubles (876 / 2,816 inks) re-found as shared stroke sets; the 98 2.184 rest pairs among them | none |
| 3 | **Beams from the stroke map**: `adjudicate_duration` reads a head's beam levels from the horizontal strokes touching its stem's tip; a detector beam box with no beam-shaped stroke under it NARROWS (blue), a beam-shaped stroke no box named is a candidate only (rule 6); `cv_beams`/`yolo_beams` become one reading with a margin | `OMR_BEAMS_FROM_STROKES` | on the file: values and red bars; tiles: 9 changed heads + 3 controls (2.170/2.153 tiles re-shown); the 31% / 55% cells become decided / narrowed / contested with counts | "When the detector draws a beam box on a flag (3 of my 6 crops), the stroke is hook-shaped and short: may the hook count as the flag it is, or only narrow?" |
| 4 | **Stem from the stroke map**: the head's stem is the vertical stroke its blob touches on the engraving side (2.161's bridge, 2.169's pair rule, 2.155's bar edge expressed on strokes); retires `head_stem_reach`, `stem_tip_ink`'s scan, `refuse_owned` (claimed-area step 6) | `OMR_STEMS_FROM_STROKES` | 2.167's 33-of-40 refused real stems; the 87 / 259 reach disagreements named; 2.150 tile 11 / 2.150b tile 20 re-shown | re-show those two tiles ("stems of quarter notes") |
| 5 | **`adjudicate_stroke_owner`** + contested bucket in export; subsumes the pair rules of §3 for rests and heads (`rest_has_a_stem`, `rest_stroke_into_a_head`, `rest_is_a_barline`, `is_a_rest_twin`, `on_a_rest`, `is_a_beam_piece`, `head_cut_piece`, the slash rule, the different-class duplicate branch) -- parity first, delete after | `OMR_STROKE_OWNER` | every box each old rule refused is refused or narrowed by ownership (named differences cropped); contested count per plate; tiles from contested strokes | §6 (contested ink: blue or red) |
| 6 | **Head fill from the blob** (hole share, slit, window all derivable): one measurement, the 2.148/2.159/2.23 consumers keep their cuts; the 303 / 77 disagreements named | `OMR_FILL_FROM_STROKES` | 2.148's 30 tiles re-scored; Litolff halves | none (2.148/2.159 rulings stand) |
| 7 | **Ledger rungs from horizontal strokes** at the ledger steps, measured locally; one reading replaces four; ownership (`glyph_owner`) reads it | `OMR_LEDGERS_FROM_STROKES` | the 34% / 38% presence disagreements named; `ledger_not_read` 2,211 / 4,713 abstentions down | the 4 ledger tiles of this plan, with a ruler: "which staff does each boxed head belong to?" |
| 8 | **Claimed-area steps 4, 5, 7 as `ink` claims naming strokes**: dynamic letters and words (the letter's own blob strokes), arcs and hairpins (the curve strokes, from `Q.SYSTEM_ARC` and the hairpin reader), within-bar marks (rest bodies, slashes); the plan's step 8 (rehearsal marks, bar numbers) last | per owner | the 2026-10-20 plan's §6 measures per owner; tails 10 / 10, beam boxes on arcs 75 / 78 (2.166) | the plan's own questions per owner |
| 9 | **Verdict basis cites strokes**: a duration verdict's `basis` lists its strokes and the rows it USED, the cell-level rows once per cell (a `pools` entry) | `OMR_SLIM_BASIS` | record bytes a page (target: verdicts under half); `trace` and `judged` still resolve every id; file byte-identical | none |
| 10 | **Retire** the duplicate measurements and helpers (§3) and the 2.191 hot loops they carried; speed measured as 2.191 did (CPU seconds, byte-identical file) | none (deletion) | byte-identical file; `check`'s open-findings number down | none |

Steps 1-4 are the first month; 5 is where the design can go wrong (Opus if Sean prefers, as the 2026-10-20 plan's steps 2 and 5);
6-7 are one owner each; 8 is the merge with the unbuilt claimed-area steps -- they are not built twice: an owner that would have
filed `unit: ink` with a mask now files stroke ids, and the one consult (`claimed_by.consult`) does not change shape. The area steps
already landed (2.177, 2.181, 2.183/2.187) are untouched.

## 6. One question for Sean

When one piece of ink is claimed by two marks of DIFFERENT kinds and the shape cannot settle it -- a stroke that could be a rest's
tail or a note's stem, a bowl that could be a flat or an eighth rest -- should we write BOTH readings blue (the stronger first, as
2.186 does within a family), or write NOTHING there and mark the spot red as unread ink? Rule 8 and your "I don't want any hidden"
point at red; 2.186's "stronger class blue" points at blue. It decides what the contested bucket (§2.3) looks like in your PDF.
