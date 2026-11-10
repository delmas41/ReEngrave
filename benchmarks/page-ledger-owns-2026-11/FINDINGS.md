# 2.284 — The page ledger owns the ink (2026-11-09/10)

STAGED, GATHER + ADJUDICATE; flag `OMR_PAGE_LEDGER_OWNS`, default OFF; branch `lane-2.284-page-ledger` (r4 8b2498598). Sean picked "Fix 2" after the 2.283 audit. Filed by the manager from the lane's report (the lane's Write was refused).

## Cause and process lesson

Ownership is settled per padded cell. A barline's area claim (centre rule) and an arc's `[[cell, ordinal]]` claim are filed for one cell, so the neighbour cell's copy of the same ink stands unclaimed and that cell's stem/beam/flag readers may take it. Almost all disagreement is "owner in one cell, none in the other"; two different owners is 0.1–0.3% of ink.

**Lesson:** a claim filed in one frame is invisible to every other frame that sees the same ink; readers reach it through a link, never re-derive it. A claim on a piece the cell edge cut is not a claim on the mark: only views that see a stroke whole settle it.

## Baseline (flag OFF, fresh gathers, master cell map)

Cross-cell owner disagreement (`disagree_probe.py`, share of non-staff ink): Brahms p0 2.74%; Litolff p2/p4/p6/p10 5.43 / 4.99 / 3.79 / 3.62%. All above the ~1% falsifier, so the build went ahead.

claim_readout Brahms p0: one owner 43.3%, twin 4.8%, contested 4.7%, unclaimed 7.6%; against Sean's labels 1291 right / 85 nothing / 181 wrong kind. Controls all behave (arc register 318,780 → 0 px with `OMR_ARC_CLAIM=0`; planted double claim raises contested 203,840 → 521,299 px; 112/112 cells re-run match).

## Built (flag ON only)

- `tools/omr/staged/page_ledger.py`: `link_cell_strokes` (cell stroke → page stroke, filed as `page_stroke` on `Q.STROKE`), `pool` (join at ≥ 0.8 of ink on one page stroke; only whole views pooled where one exists), `apply`.
- `adjudicators/stroke_owner.py`: `_cell_view` / `_settle_view`; `_page_ledger` settles once per page (memoised, cleared in `adjudicate.py`); verdicts record `detail.page_ledger`. Consumers unchanged.
- Arcs: `arc_claim.on_trace_share` / `claim_strokes`, `gather._arc_skip_head_boxes`, `ARC_SKIP_NOT` — the arc never counts pixels inside a non-arc mark box (the arc eraser's protected boxes, 2.166, minus stem/flag/beam/tremolo and barline/brace/bracket). `claim_final.mark_only()` drops `arc`/`arc_trace` under the flag; hairpins stay mark-only. `bind_end` untouched.
- Registered: `reach.py`, `docs/flags-2026-09.md`, `docs/ink-rules.md`. Nothing deleted.

Rules owning the values: owner = the 2.205 claim tiers; arc ink = plan 2026-10-28 §9-10 with the 2.166 protected boxes. **CONVENTION ASSUMED:** one page stroke is one mark's ink. **WHAT WOULD FALSIFY IT:** a page stroke the page map fused but a cell cut apart (it then reads contested). **NOT CONFIRMED** by Sean.

## Measures (r4, dev samples Litolff p2/p4/p6/p10 + Brahms p0, fresh `lane_report --from gather --cell-map master` both arms)

- Disagreement ON: Brahms p0 0.43%; Litolff 1.53 / 1.60 / 1.40 / 1.21%.
- Sean's p0 labels: right 1291 → 1297, nothing 85 → 77, wrong kind 181 → 183 (`barlineSingle` 21 → 26). Twin 4.8 → 5.5%, contested 4.7 → 5.6% (the readout ORs cells; neighbour copies now carry an owner).
- File: Brahms rests −1, words −1, red bars 6 → 5; Litolff notes +2 −3, flags −2, beams +1 −1 ~2, blue +2.
- Judged right→wrong **1**: 2.78-phase2 tile 11, Litolff p6 6/1/10/9 (eighth). Correct barline ownership makes claim_final refuse a `noteheadWholeInSpace` twin box standing on the rule; the note was hosted on it and the black-head box does not take over. Unwritten→wrong 0.
- `check` 229 = 229 (main). Fast tier 10087 passed. New tests: `test_page_ledger_2_284.py` (9 pure), `test_page_ledger_real_page_2_284.py` (slow; real p0 links ≥ 0.8, a planted 2-sp shift loses them).

## Arc falsifier (`arc_held_probe.py`, Litolff p2/p4/p6/p10)

Boxes held ≥ 0.5 by an arc claim: 22 → 8; head boxes 8 → 2 (all 4 hollow half heads freed). Still held: 2 black heads (`glyph/2/0/9/15/4` 0.55, `glyph/2/1/5/12/2` 0.62), 3 ledgers, 1 dot, 1 dynamic F, 1 fermata (new, 0.51). `held_share` is on strokes, not pixels; with MARK_ONLY dropped these can now be refused.

## Sean's tiles (2026-11-10, c59334487)

"1-4. 8 note 5. Barline 6. 8 note 7. Space on the staff in between a barline and a note 8. Half note". ON right 4 (eighth gained p2, half gained p4, false rest on a barline removed, false beam on empty space removed); wrong 2 (two more real eighths lost, Litolff p6 tiles 3–4); tiles 1 and 6 are beam-role changes on real eighths (role not asked). Three real eighths lost on Litolff p6 in all.

Sean (2026-11-10): "I think we are on the right path. The issue is not what is built but what still needs to be built." → r5 overnight.

## Not built at r4

1. One consult replacing `claimed_by.consult`, `claim_final.finding`, `stroke_owner.box_says`, covering the dynamic, flag, articulation, tuplet, dot and mark deciders.
2. Single-letter dynamics and in-staff words claimed page-wide before heads (`gather_page_claims` dynamic claim; a lone letter in a staff's line band is skipped as "milestone 4").
3. `held_share` on pixels; stopping the arc trace at its bound head (`bind_end`, 2.281).
4. The twin-host note loss.
5. Residual disagreement: Litolff head/none 0.6–0.9% (fused pieces under the 0.8 link share); Brahms barline/none 0.23% (no cell sees the rule whole).
6. Provenance gap: other cells' rows appear in a verdict's `used` but not its `considered`.

## Round 5 (2026-11-10, lane-2.284-r5-core 22ed06d00)

Cause and process lesson. Of the three "lost eighths": 2.78-phase2 tile 11 (6/1/10/9) is no note -- box 9 is a noteheadWhole box over the barline and the stem with no head ink (print checked); Sean's eighth is box 5, still written; ON removes an invented head and the scorer counts it right->wrong because the tile lists both ids. Tiles 3-4 (6/1/8/10) are one real chord (boxes 3/13) lost because the PAGE map fused a dynamic f with a beam-stem blob the CELL keeps apart; the f's claim reached the blob through the page stroke, the chord's beam read went ambiguous. Lesson: r4 asserted a mechanism (a twin host) without the print or the export trace; and a page stroke is one mark only where every frame splits it alike.

Built (flag ON only; OFF byte-identical on Litolff p2/4/6/10 re-adjudicated against the base tree):
- page_ledger.is_view: a link counts only where the piece sees its page stroke whole or the cell edge cut it (the stroke map's cut fact; no new cut). Restores the chord.
- adjudicators/ink_consult.py, the ONE consult: detail.ink_consult on each cell's stroke-owner verdict (every box's own ink held by an EARLIER 2.205 tier, from the page ledger's one owner); consult() = register rule table + ledger finding + owner shape. Heads/rests read its parts where the three old consults stood; ledger/accidental/arpeggiato its ledger finding; dynamic, articulation, flag, tuplet marker refuse claimed_by:barline|page_claim|earlier_mark; dots beside 2.243; arcs/tuplet brackets recorded only (spanner boxes). Refusals only by area/layer claims and a whole rest (box-vs-box refusal took a real quarter rest a misdrawn head box claimed, Litolff 2/0/8/2/4). Unconsulted families 6 -> 0 (ink_consult.unconsulted, a check a planted gap fails). Key-signature marker exempt: it runs before the stroke owner and is the key claim's own ink.
- Evidence.considered_from_another_frame: other cells' rows used by the page settle enter `considered`.

CONVENTION ASSUMED: a box mostly on an earlier claim's ink, owning none of its own, is not a mark of its kind. WHAT WOULD FALSIFY IT: a print-confirmed flag/dynamic/articulation/tuplet refused claimed_by:* (tiles out/print/2.284-r5). NOT CONFIRMED.

Measures (sample r2, fresh gathers both arms, master cell map):
- File: Litolff notes +5 -1 (the -1 = phantom box 9), flags -2, beams +1 -1 ~2, ties +2, articulations +1, values ~2, blue +3, words -1; not written 1401 -> 1397. Brahms rests -1 (Sean r4: barline), words -1, red bars 6 -> 5.
- Judged right->wrong 1 (tile 11, phantom; scorer artifact); unwritten->wrong 0.
- Disagreement ON (OFF): Brahms p0 0.54% (2.74); Litolff 2.02/2.04/1.78/1.65% (5.43/4.99/3.82/3.63). Up from r4 (0.43; 1.53/1.60/1.40/1.21): the price of is_view. Residual Litolff head/none 0.66-1.0%, Brahms barline/none 0.23% -- not fixed (needs pixel-level page labels per piece).
- claim_readout Brahms p0: right 1291 -> 1297, nothing 85 -> 77, wrong kind 183; twin 4.8 -> 5.4%, contested 4.7 -> 5.7%.
- check 229 (main's figure from r4; main not re-run this round). Fast tier 10095 passed.
- 12 blind tiles out/print/2.284-r5/ (key.json outside tiles/).

Cross-fence (2.284b): dropping hairpin from claim_final.MARK_ONLY_LEDGER follows from this design but only on the merged tree with 2.284b's pixel hairpin claim; one line at merge: MARK_ONLY_LEDGER = frozenset().

## 2.284b — arcs claim only their own pixels; dynamics claimed page-wide (2026-11-10, lane-2.284b-arcs-dynamics 2674e0f20, flag OMR_PAGE_LEDGER_OWNS OFF)
Cause: r4's 8 still-held boxes were held through NEIGHBOUR views (the padded neighbour cell / neighbour staff boxed nothing there), pooled by the page ledger — the skip set was per cell, the ink per page. Lesson: a rule protecting a mark's pixels names the mark by page position, never by which cell boxed it.
Built (flag ON): arc_claim.claim_pixels_on (page-wide mark boxes skipped; a stroke holding >= 0.25 (= claim_final.NEAR_MIN) of a mark's ink is a CROSSING, marked not taken; rows carry `pixels`, `crossings`); hairpin claim through the same rule (GATHER half; still MARK_ONLY in claim_final); gather_page_claims: lone dynamic letters (in/out of staff), in-staff spelled dynamics and in-staff READ words claim READ page-wide, sparing note-family boxes (DYNAMIC_SPARES). Not built: claim_final hairpin MARK_ONLY drop (fence); arc page_strokes skip.
Measures (sample-r2, fresh gathers): file changes = r4's (none from these pieces); judged right->wrong 1 = r4's (Litolff p6 tile 11, barline twin host); arc_held_probe >= 0.5: 22 OFF / 8 r4 / 0 now (near 54 -> 3); arc register px Litolff 194,061 / 262,730 / 244,795, Brahms p0 318,780 / 317,317 / 316,775; 17 crossings (flats 7, ledgers 3, double flats 2, p 2, natural, half head, dot); word_dynamic px Litolff 54,518 / 71,234 / 126,453, Brahms 73,152 / 112,886 / 119,756; Brahms truth right 1297 (=r4), via register 281 -> 286; hairpin 448 -> 170; check 229 = 229; fast tier 10094 passed; tests test_arcs_dynamics_claim_2_284b.py (7 pure), test_arcs_dynamics_real_page_2_284b.py (slow, OFF control fails).
Tiles: out/print/2.284b (8 in-staff letter claims, 4 crossings), key.json beside; unanswered.

## Round 6 — the two halves merged (2026-11-10, lane-2.284-r6-merged 6fc1fa93c, flag OFF)

Merged r5 core (22ed06d00) + 2.284b (2674e0f20) + main; only docs/flags-2026-09.md conflicted (both texts kept). `claim_final.MARK_ONLY_LEDGER = frozenset()`: under the flag the hairpin is no longer mark-only, since 2.284b claims its pixels in GATHER. OFF unchanged (`mark_only()` returns MARK_ONLY).

Measures (sample-r2, `--from gather --cell-map master`, both arms fresh on the merged tree; summaries in out/r6/):
- File: Litolff p2/4/6/10 notes +5 -1, flags -2, beams +1 -1 ~2, ties +2, articulations +1, values ~2, blue +3, words -1; red 0 -> 0; not written 1401 -> 1397. Brahms p0 rests -1, words -1, red 6 -> 5; not written 83 -> 84. Same as r5's own report.
- Judged right->wrong 1 (2.78-phase2 tile 11, the phantom whole-note box over the barline; Sean's eighth, box 5, still written); unwritten->wrong 0 on both plates.
- arc_held_probe >= 0.5: 22 OFF -> 0 ON (near 54 -> 3).
- Disagreement ON (fam-vs-fam): Litolff p2 2.00% (0.22), p4 2.04% (0.12), p6 1.82% (0.22), p10 1.68% (0.24); Brahms p0 0.59% (0.15).
- check TOTAL 229 = main 229. Fast tier 10103 passed, 0 failed.
- 20 Litolff + 1 Brahms changed places no tile of Sean's covers (out/r6/unjudged.txt).

## Round 7 — core tiles 2 and 3 (2026-11-10, lane-2.284-r7 cc2e10888, flag OFF)

Cause. Tile 2 (Litolff p2 2/1/5/13/0): the print has two stems joined by a beam, so Sean's eighth is right; the tile did not show the beam. A `noteheadDoubleWholeInSpace` box over the printed beam (2/1/4/13/4, 2.1 x 0.56 sp) is a head claim the page ledger carries into the neighbour staff's cell; the 2.235 tip reader skips owned ink, so the tip read clean and a quarter was decided. OFF keeps the tip "occupied" and the value narrowed. Tile 3 (10/1/3/2): ON is right. A false flag on an arc tip (box 10) narrowed a real half note OFF (open_head_flag_contradiction); ON refuses the flag, decides the half, and the tie start binds to it.

Process lesson. An owner label says nothing about shape. "Ignore owned ink" assumed every owned stroke is a round head; a claim carried in from another frame turned "cannot tell" into "clean". A tile must show what the answer needs (Sean, follow-up).

Built (flag ON only): `rhythm._head_owned_bar` — a bar (>= 1.8 sp wide, aspect >= 2.5) owned by a head stays at the tip, so the word stays "occupied" (rule 8). Test test_tip_bar_owned_by_head_2_284_r7.py (fails with the cut at 1800).

Measures (sample-r2, fresh gathers both arms; baseline reproduces r6): Litolff notes +4 -1 (r6 +5 -1: the tile-2 quarter is back to unwritten), blue +2, not written 1401 -> 1398; Brahms unchanged from r6. Judged right->wrong 1 (the phantom, as r6); unwritten->wrong 0. Fast tier 10106 passed. check not re-run (229 = 229 at r6).

Open, at the source: the phantom doubleWhole head box over a printed beam is still decided as a head in BOTH arms (8 beats; an invented note OFF). r7 is a downstream guard; the source is that box.
