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
