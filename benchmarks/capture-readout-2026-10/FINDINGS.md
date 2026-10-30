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
