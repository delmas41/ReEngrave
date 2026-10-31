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
