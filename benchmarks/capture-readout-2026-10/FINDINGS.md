# ROADMAP 2.236 -- capture readout (STAGED tooling)

Branch `lane-2.236-capture-readout`. Written by the manager from the lane's report (the hook refused the lane's write). Tiles NOT yet judged by Sean.

## Cause and process lesson
"Claimed once" could not be counted at page level: strokes live per PADDED cell, so one page ink sits in two cells' maps -- 12.5% (Brahms) and 16.8% (Litolff) of per-cell stroke ink is the same ink counted twice. Every capture figure before this (the arc lane's 136/153, the word lane's 49/60) was a one-off script on box extents.

## Built
`python3 -m tools.omr.staged.claim_readout REC [--pages 0,4] [--truth auto] [--tiles DIR] [--out DIR] [--env OMR_ARC_CLAIM=0]`; `claim_readout controls REC --page N`. REC: `brahms:20261029-night` / `litolff:20261029-night` (lane-report slices), a slice dir, or a `.record.json` < 5 GB (cut once into `library/_shared-records/claim-readout-slices-*`; larger refused). Registered as plumbing (reach.NOT_A_STAGE, rule_kinds.INFRA). docs/measuring.md §0 and docs/running.md §2b updated.
States per page pixel (share of the page's own dark ink): unclaimed / one owner / twin (one kind, 2+ boxes) / contested (2+ kinds; settled vs open). Staff-line ink reported as the staff's own (~40% of ink). GUESSED/NARROWED area claims are "weak", never captured. Claims are the pipeline's own: `adjudicate_stroke_owner` re-run on saved GATHER rows (a claim whose shape does not fit its stroke does not count); detector stem/beam/flag boxes count; cv_lines stems/beams only on ink nothing else claims.
De-dup: master cells re-cut (`cell_map.load_prepared`), `map_strokes` re-run per cell and checked stroke-for-stroke against the record's `Q.STROKE` (2,034 Brahms and 5,343 Litolff cells matched exactly, 0 dropped); labels sampled onto each cell's page rect and unioned into one page canvas.

## Controls (each can fail)
- `OMR_ARC_CLAIM=0` on Brahms p0: register-claimed arc ink 292,857 px -> 0; Sean's arcs "right via the register" 135 -> 0 of 153 (the old one-off's 136 used box extent).
- Planted head+rest double claim: contested 258,734 -> 441,398 px (Brahms p0), 83,908 -> 225,999 (Litolff p4).
- Identical copy of the rows reads identically (both plates).
- Re-run stroke owner equals the record's saved verdicts on 330/330 Litolff p4 cells (Brahms slices hold no saved verdicts: not checked).

## Page-ink shares (staff-line ink excluded from the columns)
| plate | one owner | twin | contested (open) | unclaimed |
|---|---|---|---|---|
| Litolff, 16 pages | 41.4% | 3.5% | 3.3% (0.3%) | 10.8% |
| Brahms, 8 sample pages | 36.2% | 5.9% | 5.5% (0.3%) | 9.2% |

## Brahms p0 against Sean's labels (1,566 boxes, via the aligned file)
All: right 1,020, nothing 386, wrong kind 149, split 10 (1 unmapped). Black heads in space 80 right / 106 nothing of 190; on line 76 / 106 of 188 -- crop-checked on ONE head: head and stem are one `vertical` stroke and the head box covers under half of it, so the head owns nothing (probably many of the 212; not counted). Ledger lines 95 right / 98 wrong kind of 248 (probably the rung claimed as part of the head; not crop-checked). Stems 187/277; tremolo 0/16; double barline 0/3; flag8thDown 27/38; text 18/32; ties 76/85; slurs 60/68. Beams 50/50, dots 130/131, accidentals 41/41, clef/key/meter, half heads, whole and quarter rests nearly all right. A truth rect can hold a neighbour's ink, so some "wrong kind" are neighbours (shares in readout.json).

## GATHER's to-do list (top unclaimed/contested ink, share of plate ink; corrected after the manager's tile review)
The first run ranked "unclaimed horizontal" first (Brahms 4.0%, Litolff 2.3%) and its tiles boxed whole staff bands: it was mostly STAFF-LINE RESIDUE (line-shaped strokes within 0.2 sp of their cell's own staff line; measured against the cell's lines, not a per-x tilt fit): Brahms 3.7% residue + 0.4% real, Litolff 1.8% + 0.7% (per page: Brahms p5 91% residue, Litolff p4 63%, Brahms p0 only 11%). Now its own bucket `residue:horizontal`, the staff's, not a mark. "Unclaimed vertical" is NOT barlines (0-1% in the header column on Brahms p0, p5, Litolff p4); by crop it is the fused head+stem stroke.
| # | Litolff | Brahms |
|---|---|---|
| 1 | unclaimed vertical 3.5 | staff-line residue 3.7 |
| 2 | staff-line residue 1.8 | unclaimed vertical 2.1 |
| 3 | refused vertical 1.5 | contested arc+beam 1.7 |
| 4 | unclaimed blob 1.2 | twin beam 1.5 |
| 5 | weak (GUESSED) claims 1.2 | contested bracket+barline 1.2 |
| 6 | contested bracket+barline 0.9 | weak claims 1.0 |
| 7 | twin head 0.9 | twin arc 1.0 |
| 8 | twin word/dynamic 0.8 | twin accidental 0.9 |
| 9 | unclaimed horizontal 0.7 | twin head 0.9 |
| 10 | contested arc+beam 0.6 | twin word/dynamic 0.7 |
De-dup: 19.0% of per-cell stroke ink on the 8 Brahms pages is the same ink seen twice (12.5% was p0 only); Litolff 16.8%.

## Tiles and caveats
12 tiles per plate, biggest first, ONE connected piece per tile at its own extent (no joining across a staff; residue left out; pieces > 10 sp skipped), one staff, one thin box: `out/print/capture-readout-2.236/{litolff,brahms}/tiles`, keys beside the folders. Question: "what is this ink?". Caveats: truth is one page of one plate; CV hairpin reads are not claims (hairpins unclaimed); ~5 min for 16 Litolff pages, ~4 min for 8 Brahms pages.

## Sean's answers on the Brahms tiles (2026-10-30)
Every barline/bracket piece is "part of a bracket": the contested bracket+barline ink is the bracket's, so the page-wide barline claim over-reaches onto bracket ink. Every other tile is "a large orange box" around a whole group (beamed eighths, sixteenths on double beams, tied dotted-quarter thirds across a barline): one connected ink piece spans heads, stems, beams and ties, because the stroke map does not split fused ink at the joins -- the same cause as heads owning nothing. These two are GATHER's next items, biggest first: split fused ink at head/stem/beam/arc joins; keep bracket ink out of the barline claim.

# 2.239 -- split fused ink at the joins + bracket ink out of the barline claim (STAGED GATHER, flag `OMR_SPLIT_JOINS`, default OFF)

Branch `lane-2.239-split-joins` (origin/main c951ff1f0 merged: 2.232, 2.235 in both arms). Not landed.

## Cause and process lesson
The stroke map's vertical opening (`stroke_map.map_strokes`, a 1 px wide x 1.5 sp tall kernel) is a COLUMN test: any column run of ink 1.5 sp tall is "vertical", whatever its width. Two black heads a third apart touch, so their columns are ~2 sp tall across the whole oval: the pair and its stem come out as ONE `vertical` stroke of ~2.9 sp^2 (Brahms p0, crops `runs`-side, 12 looked at). The head box then holds ~0.35-0.45 of that stroke, under the register's 0.5 cover cut, so no box owns it: 197 of the 212 black heads that owned nothing on p0 sit in such a stroke; 19 more are a head whose middle rows passed the HORIZONTAL opening with a ledger rung; a few are a head fused to its tie in the remainder. It is not per-cell components and not a staff-line artefact: it is the openings measuring length and never width. Process lesson: a stroke kind decided by one axis (run length) needs the other axis (width) before anything downstream can own it; the capture readout against Sean's labels found in one page what eight weeks of per-reader rules worked around (2.204 "the stroke map fuses a beam group's first stem into its head", 2.233 "both readers miss the first stem's beam because the stroke map fuses head and stem" -- same cause).
The bracket half: `gather_barline_claim` filed a +-0.45 sp barline area on every interior column, including the column the bracket reader had already read as a whole left-edge mark (Brahms p0 x=1230, staves 9-13: `systemic_barline`, owner bracket) -- the same ink claimed twice (Sean's tiles: "part of a bracket").

## Prior work
2.204 stems-from-strokes (PARKED, benchmarks/shared-ink-map-2026-10 "2.204"): read stems off the map and met the head+stem fusion; 2.233 (benchmarks/value-undecided-2026-10): the fusion stops the beam reading; 2.220 head trim/fill (`head_ink`, line-only trim, 1.6 sp height cap -- the cap reused here, a test pins equality); 2.198 rest/head doubles; docs/ink-rules.md heads rows ("same head boxed twice", "black head narrower than 1.0 space") are later-stage workarounds over the same ink; page-facts §5: nothing about splitting strokes was tried and rejected (2.202/2.204 HELD, built on, not rebuilt).

## Built (flag `OMR_SPLIT_JOINS`, default OFF; docs/flags-2026-09.md row)
`stroke_map.split_pieces` (called by `map_strokes`; pure, reads only the piece's own ink, no detection):
- head|stem, stem|beam, stem|flag (`_split_vertical`): a vertical piece's rows whose run is wider than 0.5 sp (the widest plain stem 0.43 sp) are what is fused to the stem; cut where the stem leaves them; oval tips and blips are merged back (no part under 0.5 sp tall / 0.25 sp^2).
- head|head (`_cut_stack`): a wide part taller than one head (1.6 sp, `head_ink.MAX_HEIGHT_SPACES_V2`), 0.8-1.75 sp wide, at most 5 sp, is cut at the NOTCH where an edge steps in >= 0.12 sp from both ovals (edges read on the cell ink beside the part, rungs left out: the opening drops a notched column, and a rung between two heads fills the waist). No notch -> whole, counted `stack_no_waist`.
- ledger|head (`_split_horizontal`): a level rung (fit slope <= 0.05) whose column runs are > 0.35 sp thicker than its line over a head-wide stretch with the rung going on both sides; the head is the ink off the fitted line band. A sloped line (hairpin) is refused.
- arc|head (`_split_remainder`): a remainder piece with a body a 0.55 sp disk survives in (one head) and a thin tail >= 1.5 sp.
Every part is a stroke; each carries `joined_to` [(ordinal, join)] (filed in `Q.STROKE` detail), parts add up to the piece exactly (else whole, `parts_do_not_add_up`); refusals per cell in `cell_split_refused`.
`gather.gather_barline_claim`: with the flag, a column standing on a whole left-edge mark (`page_wide.system_rules` bracket / brace / systemic barline, which `gather_page_claims` claims as bracket) is not claimed as barline (abstains `why: bracket_ink`). Note 2.240: barlines reach the stroke map as two half strokes at the cell cut; this change is on the page-px claim area and does not depend on that.
Tests `tools/omr/tests/test_split_joins_2_239.py` (10; a notch no scan reaches leaves the stack whole). Fast tier 9,416 passed after the flag-table fix; `staged.check` 198 (no new finding).

## Capture OFF -> ON (claim_readout, both arms re-gathered on the merged tree, master cells, shared detector cache; Litolff p2+p4, Brahms p0+p5; every cell matched stroke for stroke, 0 mismatched)
Against Sean's Brahms p0 labels (OFF reproduces 2.236 exactly):
| class | OFF right | ON right |
|---|---|---|
| black heads (in space + on line) | 156 / 378 | **376 / 378** |
| stems | 187 / 277 | 227 / 277 |
| flag8thDown | 27 / 38 | 34 / 38 |
| ledger lines | 95 / 248 (55 nothing, 98 wrong kind) | 97 / 248 (15 nothing, **136 wrong kind**) |
| beams, ties, slurs, accidentals, dots, rests, half heads, brace, barlines | unchanged | unchanged |
| ALL | 1,020 / 1,566 | 1,289 / 1,566 |
Page-ink shares OFF -> ON: unclaimed vertical Litolff 3.20 -> 1.58%, Brahms 2.60 -> 1.04%; contested bracket+barline Litolff 1.04 -> 0.00%, Brahms 1.27 -> 0.33% (p5 0.84 -> 0.00, p0 2.09 -> 0.94); one-owner head Litolff 5.93 -> 7.19%, Brahms 6.27 -> 8.10%; all unclaimed (residue left out) Litolff 8.56 -> 6.82%, Brahms 7.02 -> 4.80%. Went up: unclaimed blob Litolff 1.21 -> 1.74% (split head parts no box covers: detector-missed heads, now visible), twin head Litolff 1.10 -> 1.67% (two padded cells' boxes on one now-owned head part -- the 2.240 double cut).
Right -> wrong kind: ledger lines 38 boxes "nothing" -> "wrong kind": a rung through a stack of heads stays with the head part (the vertical split keeps the rung rows inside the head columns). Not a lost mark, a rung owned as head: the next cut.
Residual bracket+barline on Brahms p0: the system's leading line on staves 0-8 (no left-edge mark there) is claimed by both the leading-column register and the barline column -- whether that line is header or barline is Sean's question, not changed here.

## The file veto (`lane_report --flag OMR_SPLIT_JOINS --from gather --cell-map master`, LANE_REPORT_SAMPLE runs/l239 2 pages a plate)
Litolff: NOTHING CHANGED. Brahms: notes +1, accidentals +1, beams ~1, slurs +2 -2, note values ~1, blue +1, words +1 -1; red bars 45 -> 45. Judged (188 + 219 tiles): right->wrong 0, right->gone 0, unwritten->wrong 0. No old later-stage rule turned the capture gain into a wrong answer on these pages (later stages read boxes, barely the stroke kinds).

## Tiles
`out/print/2.239-tiles/tiles/` (12, one piece each, thin box sized to it; key `out/print/2.239-tiles/key.json`): 4 heads cut off a stem, 2 head|head, 1 arc|head, 1 ledger|head, 2 stems, 2 bracket controls. My own look: 7 are what the join name says (heads, stems, a chord head); tile 2 (Brahms p5) and tile 5 (Litolff p2) are pieces of a CLEF the split cut (clef ink is claimed by the clef register area, so ownership is unchanged; the join name is geometry, not a reading); tile 10 is a barline stretch whose fused neighbour was cut off. Not yet judged by Sean.

## Risks
Join names are geometry, not readings (clefs, rests and letters get cut too; their register/box claims still cover all parts). A head on a rung is now 3-5 strokes (tips, lens halves) all inside its box. Ledger rows inside stacked-head columns are owned as head (36 more ledger boxes wrong kind). Thresholds (0.5 sp thin, 0.12 sp notch, 0.05 slope) are measured on two plates: NARROW-level, not conventions.

## 2.239 round 2 (after Sean's tiles: 6 "just the top of an eighth note on a ledger line", 9 "a part of a head but mostly the ledger line next to it", 2/5 clef pieces; and "I thought we had limits to box sizes")

### Cause
- Tile 6 (ledger|head): the rung's thickness was read as the 20th-percentile column run of the WHOLE horizontal piece. A head is wider than the rung's stubs, so that percentile fell on a head column, and the "line band" (fit ± half that thickness) took the oval's middle half. The cut then ran through the head and left its top and bottom as blobs.
- Tile 9 (vertical path): a rung crossing a head's top raised the wide part past the 1.6 sp one-head cap, and the rung's end looked like a notch. The stack cut took "rung + top of head" as one head (band 0.7 sp tall).
- Clefs: the stroke map is pure and knew nothing of the clef; the split cut thick clef bodies at their "stems".
- The test was blind to all three. claim_readout called a box RIGHT on a 50% kind share, never asking whether the ink is ONE piece or a plausible size. Sean's size limits lived only on detector boxes.
- Process lesson: a capture score must test the piece, not the pixel share. A test that cannot see a sliced head cannot fail on one.
- Brahms p0 bracket (the coordinator's crop): the bracket reader DID see the woodwind/brass bracket (levels: x 1234, staves 0-8). It skipped it as a mark because the closing fused the 16 px bracket line to the thin opening line 6 px to its right. The fused stroke's CENTRE then stood 0.55 sp right of the staves' start, over the 0.5 sp left-edge cut. Not its length, not the braces, not the hook test.

### Fix (same flag, `OMR_SPLIT_JOINS`)
- **ledger|head:**
  - The rung's thickness is read on its own end stubs (≥ 0.15 sp each side, else the piece stays whole).
  - The head is EVERY column of the oval, all rows (the rung through it included). Its edge is where the column run stops exceeding the rung by 0.2 sp.
  - The stubs beyond the oval on each side are `horizontal` ledger strokes. The rung must be level (stub fit ≤ 0.05).
- **Stack cut:** each band must be ≥ 0.8 sp tall (one head), so a rung plus the top of a head is never a head.
- **Clefs:** no piece mostly inside a clef/key/meter detector box is cut (`cell_keep_whole`, filed on the cell's first `Q.STROKE` row, so a re-run reproduces it).
- **Head slivers:** a small remainder blob touching a head part cut off a stem or rung, within 0.3 sp of it, rejoins it (the oval edge columns the opening dropped, and the tips).
- **Left edge:** `measure_extractor._left_edge_read(edge_by_left=True)` tests a stroke's LEFT side against the edge. It is called by `gather._left_edge_marks` only under the flag; the master's stored reading is untouched. Brahms p0 s0 now reads one left-edge mark over staves 0-13 (kind label `systemic_barline` -- the width is measured on the thin line -- but owner `bracket`). Other pages are unchanged.
- **Tests:** 12 in `test_split_joins_2_239.py`, including Sean's tile 9 shape and the clef keep-whole.

### claim_readout: ONE MARK, ONE PIECE (new columns; old outputs unchanged)
- Per truth box: the largest single same-kind piece's share of the box ink and the piece count. STRICT = right AND that share ≥ 0.85 AND that piece inside its kind's limits.
- The limits are the project's own:
  - head: `head_ink.MIN_SPACES` 0.6, `MAX_WIDTH_SPACES` 1.75, `MAX_HEIGHT_SPACES_V2` 1.6.
  - ledger: thick ≤ `stroke_map.CURVE_MAX_THICK_SPACES` 0.5, level ≤ `LEDGER_MAX_SLOPE`.
  - stem: wide ≤ `STEM_TRUE_WIDTH_MAX_SPACES` 0.7, ≥ 2.5 sp tall or touching (2.5 from the brief).
- A per-page MISSHAPEN list per kind, with page boxes. Beams and flags are not shape-tested yet.
- Control (f): heads planted cut in half -> Brahms p0 black heads whole 81 -> 0 (fragmented/misshapen 156). Controls (a)-(e) still behave.

### Re-measured (both arms re-gathered on main 81da8c84c + these commits; master cells; 0 cells mismatched)

Brahms p0 against Sean's labels:

| class | old 50% test OFF -> ON | STRICT whole OFF -> ON | fragmented OFF -> ON | misshapen OFF -> ON |
|---|---|---|---|---|
| black heads (378) | 156 -> **374** | 81 -> **221** | 21 -> 141 | 54 -> 12 |
| stems (277) | 187 -> 227 | 157 -> 150 | 30 -> 77 | 0 -> 0 |
| ledger lines (248) | 95 -> 98 (wrong kind 98 -> 133) | 61 -> 62 | 34 -> 34 | 0 -> 2 |
| flag8thDown (38) | 27 -> 33 | 0 -> 0 (flags are 2+ strokes; not shape-tested) | | |

Misshapen pieces (per-cell occurrences, padded duplicates included):
- Brahms p0: heads 399 -> 139, ledgers 26 -> 63, stems 1 -> 1.
- Litolff p4: heads 796 -> 768, ledgers 46 -> 66, stems 38 -> 10.

Reading:
- The heads' remaining fragmentation is mostly the neighbour head of a stack whose truth box overlaps (a third apart), and the stem's ink beside the oval.
- On-line heads OFF were "misshapen" because the staff-line erase halves them -- a GATHER cause outside this lane, in both arms.
- Stems fragment ON because the stem's truth box holds the oval beside it, now a head piece.
- The ledger "wrong kind" stays: by Sean's rule (b) the rung inside the oval is head ink, and a ledger truth box is mostly that oval. The stubs are claimed ledger.
- The ledger misshapen rise is the short stubs failing the level test (angle on a 0.2-0.4 sp piece is noise): a measurement limit, said here.

Page ink:
- Unclaimed vertical: Brahms 2.60% -> 1.04%, Litolff 3.20% -> 1.58%.
- Contested bracket+barline: Brahms 1.27% -> **0.00%** (p0 2.09 -> 0.00, p5 0.84 -> 0.00), Litolff 1.04% -> 0.00%.

### File veto (same 2-page sample)
- Litolff: blue marks -4, nothing else.
- Brahms: notes +1, accidentals +1, beams ~1, slurs +2 -2, values ~1, blue +1, words +1 -1; red bars 45 -> 45.
- Judged right->wrong 0, right->gone 0, unwritten->wrong 0.

### Tiles round 2
`out/print/2.239-tiles-r2/tiles/` (12; key `out/print/2.239-tiles-r2/key.json`): 6 heads on ledger lines (tile 2 is Sean's round-1 tile-9 place), 2 rung stubs, 2 clef controls (left whole), 2 other heads.

My look:
- Heads on ledger lines: tiles 2, 3, 4, 5, 8 and 11 are each the whole head. Tile 9 (a chord head) is also whole.
- Tiles 6 and 7 are clef pieces left whole.
- Tiles 1 and 10 are short rung stubs beside a head.
- Tile 12 is a small sliver of a head in a dense Litolff passage: a fragment the cut still leaves.
## 2.241 order check (claim-order in the capture readout; STAGED tooling, no pipeline change)
Branch `lane-2.241-order-check`, merged with main f6f5a5293 (2.238 OMR_OWNER_SHAPE ON) before the numbers below were taken (they moved by 0.01-0.07 points; the numbers on the pre-merge tree are not kept). `python3 -m tools.omr.staged.claim_order REC [--pages] [--tiles DIR]` (also `claim_readout order ...`), module `tools/omr/staged/claim_order.py`, tests `test_claim_order_2_241.py`. Reports and per-page numbers: `order-2.241/{brahms,litolff}.order.{txt,json}`. Tiles for Sean (NOT yet judged): `out/print/2.241-tiles/tiles`, key beside it.

### Cause and process lesson
Nothing in the tests asked WHICH layer owns a piece of ink. The stroke owner puts area claims first and the consumers last, but between the box families it only LISTS candidates and lets the stroke's shape pick one; and the stroke map cuts the ink before any claim stands. So "was the right layer first?" was answerable only as a count of states. The lesson: a claim order needs its own readout (per ink, who READ it, who OWNS it) or each lane tests it by hand. Result: where a layer's claim stands, the order is kept (violations 0.2-0.3% of ink); what breaks it is (1) the stroke map cutting a clef or bracket before the claim, (2) ink read but owned by nobody, (3) page-wide reads (a word box, a barline area) that the owner's centre test does not honour, (4) the plan's order not being the code's order for stems, accidentals and dots.

### The order as encoded (`LAYERS`, one place)
staff lines (plan §10 step 1) / barlines, brackets, braces (§10 step 1, §9) / clef, key, meter (§10 step 2) / words, dynamics, titles, tempo (§10 steps 3-4, §9 step 1) / arcs, hairpins (§9, §10 step 5) / whole rests (DECISIONS 2026-10-29) / heads and ledger lines (§2 row 3, §3) / stems, beams, flags (§3 head -> stem -> beam/flag) / accidentals, rests, dots and articulations (§2 row 3 open question 1). Where the plan disagrees with itself, the later Sean ruling is followed: §2 puts in-staff words and arcs AFTER heads, §9/§10 (2026-10-29) puts them page-wide BEFORE heads; whole rests go before heads (DECISIONS 2026-10-29), not after accidentals as the lane list had them. `stroke_owner.TIERS` differs from the plan for accidentals (before the consumers), dynamics (after arcs, heads) and arcs (after heads): each violation pair is printed with `code_agrees` False where the code's own order also differs, so a plan-vs-code difference is not read as a hidden bug.

### What is counted
Per page ink (the 2.236 canvas, staff lines left out): READ = every layer with a standing stroke-owner candidate (a refused shape is not a read), a consumer box, a cv_lines row, a READ area claim or a text reader row (`direction_word`, `printed_bar_number`) that holds at least half the stroke's ink; OWNER = the stroke owner's decided family (a consumer on an unclaimed stroke; an area for ink outside every cell). Classes: ORDER-OK (the earliest of two or more readers owns it), EARLIER-UNREAD (the owner is the only reader: the order is not tested there), ORDER-VIOLATION (a later layer owns ink an earlier read), OPEN (read, owned by nobody), SPLIT-ACROSS-CLAIM (a clef or bracket the stroke map cut into several strokes: all pieces but the largest, 20 px or more), NO-READER.

### Shares of page ink (staff lines out)
| plate (pages) | ORDER-OK | EARLIER-UNREAD | ORDER-VIOLATION | OPEN | SPLIT | NO-READER |
|---|---|---|---|---|---|---|
| Brahms (0,4,5,8,12,14,19,25) | 6.73% | 74.56% | 0.32% | 0.50% | 2.71% | 15.17% |
| Litolff (1,2,4,6,8,9,10,11,16) | 3.82% | 77.00% | 0.23% | 0.88% | 3.05% | 15.03% |
| Brahms p0 | 6.06% | 68.70% | 0.34% | 0.38% | 2.76% | 21.76% |
| Litolff p4 | 4.91% | 76.52% | 0.48% | 1.38% | 2.82% | 13.90% |

Top violation pairs (share of ink; Brahms / Litolff): stem->accidental 0.08 / 0.05; stem->dot 0.08 / 0.01; stem->rest 0.03 / 0.03; word->stem/beam/flag 0.03 / 0.03; word->accidental 0.03 / -; word->arc 0.02 / 0.04 (p4 0.27); head->dot 0.02 / 0.01; head->rest 0.01 / 0.02. SPLIT is clef 2.35 / 2.83 and bracket 0.30 / 0.14. Biggest OPEN: Brahms barline|none 0.13; Litolff barline|none 0.50, whole rest|head 0.07.

### What each pair tells a GATHER lane (tiles are my own look; Sean's answers decide)
- **SPLIT clef (2.4-2.8%, the largest order failure).** The clef claim stands, owns every piece, and the ink is still cut into several strokes (Sean's clef tiles). The control run on the 2.239 branch shows the r2 tile-7 tip is cut the same with the split OFF: the cut is the pre-existing stroke map (eraser, then vertical opening), not 2.239's cuts. Fix at the source: a READ clef (or bracket) claim must keep its ink as ONE stroke when the strokes are mapped (the claim comes before the cut, the order the plan wants).
- **stem->accidental, stem->dot, stem->rest (0.1-0.2% Brahms).** A flag or stem box read the stroke and a later layer owns it (tiles 3, 4: a flag piece owned by an accidental, a quarter rest's stem owned by the rest). `stroke_owner` ranks accidentals, dots and rests ahead of the consumers by design; the plan puts stems/flags first. A lane must decide which is right (the flag tile looks like a flag): either the accidental/dot reader refuses ink a flag or stem box holds, or the consumers move up.
- **word->stem/beam/flag (tile 6, the `<` of a `dolce`) and word->arc (tile 5, a slur under `pesante`).** The word's box reads strokes beside it (a hairpin wedge, a slur piece): the page-wide word read is too WIDE, or the hairpin has no claim and is taken as a beam. Hairpins must claim page-wide (Sean 2026-10-30) and a word must claim by its own ink components, not its box.
- **head->rest, head->accidental, head->dot.** A head box also fit a rest or a dot; the owner chose the later layer (on the pre-merge tile set one looked like an eighth rest; no tile of this pair is in the final 12). These are the detector's spurious head boxes, not an ownership bug; the order said "heads first" and the shape correctly overruled it. Count them as detector over-reach.
- **OPEN barline|none (Litolff 0.50%).** Interior barlines (two tiles looked at) that the barline area read but no one owns: the stroke owner's centre test does not give them to the area. Use the same "half the stroke's ink inside the claim" test as `claims.covering`.
- **clef_key_meter->arc (tile 7).** The top edge of a rehearsal-letter frame, owned as an arc: no reader reads rehearsal letters (plan §10a), so it is not an order violation but an unread mark.
- **EARLIER-UNREAD 74-77%**: most ink is read by one layer only, so the order is not tested on it; and **NO-READER 15%** is the 2.236 unclaimed ink. A GATHER lane that adds a reader should move ink out of these two, not only out of "violation".

### Controls (each can fail; `claim_order controls REC --page N`)
- (a) A head planted over every stroke the word layer owns: words->heads 0 -> 82,059 px (Brahms p0), 0 -> 38,404 (Litolff p4). On a page with no word-owned stroke the plant touches nothing and the control fails (unit test).
- (b) `OMR_CLAIM_WORDS_FIRST=0` (re-adjudicated rows, the word claim rows not filed because that flag is read at GATHER; the word reader's rows kept): words->heads does NOT rise (0 -> 0 on both pages): with the claim gone the ink is not taken by a head box, because the stroke owner refuses a head on a letter's shape and leaves it OPEN. What rises is word-read ink the word layer does not own (violations + OPEN): Brahms p0 4,654 -> 52,626 px, Litolff p4 6,997 -> 11,351. The control was changed from "words->heads rises" to this, said here, because the first form cannot rise in the real pipeline.
- (c) An identical copy of the rows reads identically (both plates).
- (d) On a gather of `origin/land-239-flip-wip` (Brahms p5, 2.239 split ON, run from that tree): tile 7's box (702,2747,729,2755) is 202 of 202 ink px SPLIT-ACROSS-CLAIM, 252 cells matched stroke for stroke. The same box on the split-OFF slice is also 202/202: the tip is cut by the original stroke map.
- (e) The order canvas lies on the 2.236 canvas (ink px equal, staff-line px the difference).

### Caveats
Reads are boxes and areas, with no confidence: a violation where the EARLIER read is wrong (tile 5) is the earlier reader's over-reach, not the owner's fault. Several cells see the same ink: the earliest owning layer is kept, which hides, never invents, a violation. The 50% share is the register's own cut, not tuned. SPLIT counts only clefs and READ brackets (one mark by convention); keys, meters and words are many marks. Only Brahms p0 has Sean's labels, and the tiles are not judged. The 8 Brahms and 9 Litolff pages are the 20261029-night lane-report slices; the 19.6 GB Brahms record was not opened.

## 2.239 round 3 (after Sean's round-2 tiles: 1 "part of a ledger line and a flat", 7 "tip cut of a G clef", 12 "a bit of a note, a flat and stem"; and Sean on clefs: "make sure the box is big enough to claim all the ink and it should be based off of shape and size")

Branch `lane-2.239-r3b` (on main after "Land 2.239"; same flag `OMR_SPLIT_JOINS`, no new flag). STAGED GATHER. Not landed: waits for Sean's tiles.

### Cause and process lesson
- **Touching marks (tile 1).** Every cut in rounds 1-2 reads a change of WIDTH inside one mark. Two different marks that merely touch have no such change. On Litolff p4 cell (4,0,8,10), the flat's bowl bottom rests on the rung left of the head. The ledger|head cut then made a left "stub" (x 106-187 canonical) that runs from inside the flat box (53-153) into the ledger box (155-372). Confirmed the same way on 26 pieces over the 4 pages (below). Almost all are ledger|head stubs running under an accidental.
- **Clefs (tile 7).** The manager's hypothesis was false. The ball of tile 7's G clef lies INSIDE the detector box (every one of its strokes reads clef 1.0). The cause is the stroke map's openings themselves: they cut a G clef into about 25 pieces, with the flag OFF as well (vertical / horizontal / remainder). Keep-whole only stopped the split from cutting further. It never put the openings' pieces back together. 2.241's order canvas (above, (d)) found the same independently: the tip is cut by the original stroke map.
- **Tile 12** is a flat the detector never boxed. It sits between two heads, and one horizontal piece joins the flat's bowl to both. With no accidental box there is no second witness for where the flat stops, so by rule 6 the piece stays whole.
- **Process lesson:** a hypothesis about ink must be checked against the strokes before it is built on ("outside the box" was wrong). A fix to one stage needs the downstream reader as its control. The first touch version merged the accidental's crumb into the touching accidental stroke, and the 2.201 family reading lost 4 naturals and a flat. Only the control showed it.

### Built (flag `OMR_SPLIT_JOINS`)
- **Touch cut** (`stroke_map._cut_touching` / `_cut_touching_all`):
  - It applies to a piece lying across an `accidental*` box AND a head / ledger / stem box, with each side holding at least 0.15 of its ink in its own box alone (and at least 0.02 sp²). Key signatures are never cut.
  - Seeds: ink in one side's boxes only. Ink in both boxes or in neither goes to the nearer seed, through the piece's own ink.
  - Where more than half the ink is in both boxes or in neither, the piece stays whole (`touch_boxes_undecided`).
  - The two sides are two strokes, linked `accidental|<head|ledger|stem>`.
  - The boxes are filed once per cell (`cell_touch_boxes`) so a re-run reproduces the cut.
  - The 2.201 family reading reads this map's own strokes, so it cannot steer the cut. It is the control after the cut.
- **Clef by shape and size** (`stroke_map._merge_clefs`, `clef_region`; gather `_split_keep_whole` tags `clef:G|F|C`):
  - A clef is read from its detector box OUTWARD:
    - the seed is every piece mostly inside the box;
    - a piece touching the clef (2 reduced px, the map's own contact rule) joins it.
  - No piece joins that does not lie wholly inside the clef's SIZE around the box. Any clef-sized rectangle that still holds the box counts, plus 0.125 sp of box-edge tolerance.
  - Sizes are the SMuFL reference glyph boxes (`tools/omr/annotate/static/bravura/bravura_metadata.json` glyphBBoxes): G 2.684 x 7.024 sp, F 2.756 x 3.588 sp with its dots, C 2.796 x 4.048 sp. `docs/symbol-dossiers/clefs.md` cites the same heights. Nothing was tuned here. The Brahms p0 G-clef boxes measure 2.7 x 7.2 sp, the SMuFL size.
  - A piece mostly inside a key or meter box is never the clef's: the key's first flat keeps its own strokes.
  - The clef is ONE stroke.
  - The clef's claimed AREA in the register grows from its box to that stroke (gather `_clef_area_by_ink`), bounded by the same size. The grown-from box is filed (`grown_from_box`).

### Left edge read once (the landing blocker, landed with 2.239 as 1a8f6e92e)
- The round-2 second scan of the left edge in gather is gone.
- The left-side edge test runs inside the ONE page-wide pass (`measure_extractor._left_edge_by_left(pws)`), STAGED pages only (`pws.staged_page_wide`). LEGACY is unchanged.
- The Brahms master was rebuilt after landing (cm-3ccd049d7c3c). `cell_map verify`: only system 0's stored left-edge reading differs; no cell box moved.
- Brahms p0 hand truth was re-aligned to it: boxes and cells identical, only the master id changed.
- Brahms p0 contested bracket+barline is still 0.

### Capture, round 2 ON -> round 3 ON (claim_readout STRICT; both arms re-gathered; master cells; 0 cells mismatched)
- **Touching pieces.** Pieces across an accidental box and a head / ledger / stem box, per-cell occurrences: 26 -> 7.
  - Litolff p4 10 -> 3, p2 2 -> 1, Brahms p0 3 -> 1, p5 11 -> 2.
  - Cuts made: 11 + 1 + 4 + 12.
  - Left whole as undecided: 2.
- **Accidental-touching groups by what touches what.** Accidental + ledger stub 14 -> 4. Accidental + head 12 -> 3 (the head's box holding the stub's start). Accidental + stem 0. Accidental + rest 1 -> 1 (not a family the cut reads).
- **Other multi-mark pieces counted (not cut here).** Head + ledger: Litolff p4 74, p2 62, Brahms p0 26, p5 41. These are where the ledger|head cut refused. Flag + head: Brahms p5 80, p0 17.
- **Sean's Brahms p0 labels, strict whole (round 2 -> round 3):**
  - clefG 0 -> **8 of 8**
  - clefF 0 -> **5 of 5**
  - clefCTenor 0 -> 1 of 1
  - clefCAlto 0 -> 0 of 1: still in pieces, largest 0.51 of the box
  - ledger lines 62 -> 62 whole, fragmented 34 -> 33
  - heads, stems unchanged
  - ALL whole 645 -> 660
- **Accidentals stay 0 of 41 whole.** The openings cut every accidental into 4-6 strokes (stem, bars, bowl), flag OFF as well. The 2.201 family reading is built on those strokes. Not changed here; the next item if Sean wants one piece per accidental.
- **Misshapen lists.**
  - Brahms p0+p5: head 370 -> 371, ledger 289 -> 294.
  - Litolff p2+p4: head 1220 -> 1223, ledger 113 -> 114.
  - The rise is the stubs freed from a flat. They are now one-kind ledger pieces and fail the level test on 0.2-0.4 sp (the measurement limit said in round 2). Before, they were contested and not listed.
- **Control, the 2.201 accidental family type on every accidental box** (round-2 map vs round-3 map, same boxes):
  - Brahms 224 -> 224 right, Litolff 98 -> 98.
  - One change: a Brahms p5 `accidentalDoubleSharp` box on an F clef's dot goes unclear -> unread. The dot is now the clef's.
  - The first version (accidental crumb joined to its stem) lost 4 naturals and a flat, plus 2 key flats to the clef. Both were fixed before this run.

### File veto (`lane_report --flag OMR_SPLIT_JOINS --from gather --cell-map master --tag 20261029-night`, LANE_REPORT_SAMPLE 2 pages a plate)
- Litolff: blue marks -1.
- Brahms: notes +1, accidentals +1, beams ~1, slurs +2 -2, values ~1, blue +1, words +1 -1; red bars 45 -> 45. Same as round 2.
- Judged right->wrong 0, right->gone 0, unwritten->wrong 0 (188 + 219 tiles).

### Tiles round 3
`out/print/2.239-tiles-r3/tiles/` (12; key `out/print/2.239-tiles-r3/key.json`), cut from the WRITTEN ON record:
- 5 clef claims, with the box drawn round the WHOLE claimed clef: tile 4 is Sean's round-2 tile 7 G clef, tile 12 his round-2 tile 6 G clef, tiles 3 and 10 F clefs (Brahms, Litolff), tile 1 a C alto clef.
- 5 accidental-touching pieces after the cut (2, 5, 6, 7, 11).
- 2 head controls (8, 9).

My look:
- Every clef box holds the whole clef: ball, curl, dots.
- The touch pieces are small: a flat's bowl edge or a natural's side, each now apart from the rung or head.
- Tile 2 looks like an eighth rest the detector boxed as an accidental: Sean's answer decides.
- The controls are whole heads.
