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
