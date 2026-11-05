# 2.260 / 2.260a — The page is the ledger (STAGED; Sean 2026-11-03)

Plan: `docs/plan-2026-11-03-page-ledger.md` (finishes 2.240 steps 4-5). Filed by the manager from the
lane reports (a hook refuses report files from subagents).

## 2.260 step 1 — audit (no code)
- **No stage after GATHER reads pixels** (adjudicate/, evaluate, infer, export import no cv2/numpy except
  `consequences.py:1054`). GATHER files cell-framed records (detector boxes, Q.STROKE,
  Q.BEAM_STROKE_INK, Q.GLYPH_BOX) and later stages re-judge cut pieces ("is this stroke thin?",
  "are 2 heads under this box?").
- **Why page-wide readers did not take over:** the cell readers came first (pad 05-14, beam ink tests
  10-09, arc trace 10-17; claims 10-22..10-29); claims were added BESIDE old rules (deletion deferred to
  2.194 step 10, never done); a stroke carried no "cut by the cell edge" fact; the 10-29 "stays per cell"
  list held beams, stems and ledgers -- the marks a 4-6 sp pad cannot hold.
- Staff-barline ink split across two cells on ~80% of barlines (78% Litolff, 83% Brahms).

## 2.260 step 2 — design (see the plan)
**Process lesson:** a design step with no symptom of its own (the page stroke map) queued behind the
lanes that carry its symptoms (2.204 barline abstentions, 2.259 clipped beams, 2.258 arc pieces), which
kept paying for it one reader at a time.

## 2.260a M0-M2 (lane-2.260a-page-strokes cfcfc01cc; landed main a481c03e7)
- **M0 `OMR_STROKE_CUT_FACT` -- LANDED ON.** Cause: the cell crop cut tall beams and later readers judged
  the sliver as the mark. GATHER files a `cut` fact (cell-crop edges a stroke touches, page border
  ignored) on Q.STROKE / Q.BEAM_STROKE_INK; a beam cut at top/bottom is no longer refused `too_thin`;
  the stroke map's missing level says cannot-tell (`cut_abstains`), counted `beam_cut_kept`.
  Litolff p6+p16: notes +3, beams +4, accidental +1, value ~1, pitch ~1, red bars 0 -> 0, notes not
  written 774 -> 771; Brahms p5+p8 unchanged; judged right->wrong 0 (165 tiles), unwritten->wrong 0.
  The parked 2.259 patch gave notes +4, beams +4.
  Sean's tiles (answers-m0.json): "Tile 1 is a half note, tile 2 is an eighth note, tile 3 is an eighth
  note, tile 4 is a quarter note, tile 5 is an eighth note, tile 6 is an eighth note, tile 7th is an
  eighth note." -- 7/7 right (controls 1, 2, 4; tile 3 quarter -> eighth; 5-7 gained eighths).
  Gate: fast tier 9880 passed, 0 failed; real 2-page gather finished.
- **M1 `OMR_BARLINE_COLUMN_FACT` -- merged OFF.** Tilted column (slope + intercept) refit in
  `staged/barline_columns.py` with the extractor's own Theil-Sen (measure_extractor.py untouched), filed
  `Q.BARLINE_COLUMN_FIT`. Lesson: `Q.BARLINE_COLUMN` already existed and the first version silently
  redefined it. Litolff p6: 28 columns, 14 tilted >= 0.45 sp, one drifts 24.7 px over a system; Brahms
  p5: 20, none. Export byte-identical.
- **M2 `OMR_PAGE_STROKES` -- merged OFF, read by nothing.** `staged/page_strokes.py`: one raster from
  each staff's own erased band + page.binary outside the bands, M1 column carved first, the cell map's
  finders run once on the page; `Q.PAGE_STROKE`. Controls: same-frame parity Litolff p6 99.7% vs 19%
  with bands shifted 6 px; Brahms p5 84% vs 27% (noise floor 80.5%); rule-like barline strokes 0/308 L,
  1/280 B vs 85%/92% on the cell map; export byte-identical. Cost 4.0 s/page vs 6.8 s for the cell
  maps (Brahms 6.6 vs 9.9); canvas 11 MB (46 MB Brahms); record +6% L / +4% B; peak RSS unchanged.

## Not established
Brahms parity sits at its noise floor; the page map's split with real detector boxes untested; carve
widths and run lengths are untuned constants. M1/M2 matter only from M3 (claims name page strokes).

## 2.260b — M3: claims name page strokes, arcs first (absorbs 2.258; NOT landed)
Lane `lane-2.260b-m3-claims` round 2 head f95ef29ea, `OMR_PAGE_CLAIMS` OFF (turns on M1 + M2). The 2.258 lane agent was stopped mid-run (likely by a user interrupt; see DECISIONS/memory) after building `OMR_ARC_ONE_CURVE`; its code was reused here.

**Reader table (step 1)** -- Q = the one traced page curve, B = detector boxes / cell pieces:
`_page_binding` ends Q (trace cut at box + 0.5 sp: right question, short answer); `_joins_not_at_a_barline` B -- WRONG question (where boxes stand, not what the trace proved), causes the 68; `adjudicate_arc_kind` OFF path / `_flank_search` / `_two_note_reading` B; `adjudicate_tie_pair` Q when bound else B; export `_place_arcs` / `_noteheads_under` B per cell piece; `_page_bound_slur_spans`, `_anchored_slur_spans` Q; `stroke_owner._arc_claims` cell strokes `[[cell, ordinal]]`; beam discount `_not_a_decided_arc` / `_strokes_on_a_system_arc` B; `_arc_tail_refusal`, `_arc_ink_refusal` B + cell edge; `claims.heading_blocks`, `page_owner.not_ledger_maker` Q.
**Cause:** the page-wide trace is already one curve; the binder re-asked the cell boxes. **Lesson:** a later reader must ask the claimed object, not re-derive it from the pieces the claim replaced.
**Counts (Litolff p10+11):** `joined_not_at_a_barline` 33 curves (30 twin boxes of ONE stroke in one cell, 3 a barline cut; 6/6 crops clean single arcs); `end_unbound` 72 curves / 117 ends (63 no head within 3 sp, 29 head ADJUDICATE left unusable, 19 head 1.6-2.6 sp past the window, 6 > 2.5 sp off in y).

**Round 1** (flat 3 sp end extension): STOPPED -- a Brahms p0 hand-truth tie (q1099) became a slur; Brahms ties -14.
**Round 2** (guard asks the page map/trace; an unbound end extends only along its own page stroke; an end bound OFF never moves): fast tier 9887 passed; Litolff p10+11 ties +2 slurs +10, `joined_not_at_a_barline` boxes 67 -> 6, bound ties 49 -> 53, slurs 30 -> 37; Brahms p0 hand truth unchanged (ties 28, slurs 27; q1099, q1233, q953, q1071, q1405 identical to OFF); judged right->wrong 0. Brahms "slurs -16": by exact span 8 instances, none a real loss (6 OFF duplicates, 1 OFF non-arc on staff lines, 1 re-bound to the long slur the print shows); 16 vs 8 not reconciled.
**Sean's tiles (answers-2.260b-r2.json): 9/12.** Tiles 2, 3, 9 are same-note ties written as SLURS. Tile 2 was a tie OFF -> RIGHT->WRONG (the judged scorer missed it: not a judged place). Cause for 2 and 9: the arc ties the UPPER head of a ledger dyad, which is never a usable bound head (`far_head_ledger_unread`); the binder binds neighbours, one end via a stem tip with an unread step, and `page_binding_different_pitch` reads unread-vs-read as "different". Tile 3 (Brahms p0): the slur does not come from the binder; untraced.
**Sean's ruling:** a tie is read from POSITION, not pitch (page-facts §1, DECISIONS 2026-11-03).
**Round 3 (next):** (1) the tie test compares the two end heads' staff POSITIONS measured locally (page map), never waits on a ledger count; unread pitch is doubt only where positions differ; (2) bind the dyad's upper head as the arc end; (3) trace tile 3's slur source; re-measure Litolff p10+11, Brahms p0+p5 (Brahms p0 hand truth unchanged, judged 0, and Sean's r2 tiles 2/3/9 re-read as ties); hairpin/barline/word claims stay on the next list.

## 2.260b round 3 + landing (LANDED ON 2026-11-04, main 95f4d78ab)
`OMR_PAGE_CLAIMS` default ON (forces `OMR_BARLINE_COLUMN_FACT` + `OMR_PAGE_STROKES`, both now default ON too). Branch lane-2.260b-m3-r3 36d564fa3.
- **Cause (round 3):** the tie test compared box centres; it now compares each head's own local staff position, `Q.NOTEHEAD_STAFF_POSITION`, when a step is unread (Sean 11-03: a tie is read from position, not pitch). Tile 3 (Brahms p0) now a tie (10.09 vs 10.10). Tiles 2/9: the arc ties a ledger dyad's UPPER head, which the detector never boxed; a stem tip > 4.5 sp from its head (`TIP_MAX_SPACES`, not confirmed) never supports "different"; spurious slurs gone, tile 2 keeps OFF's correct tie.
- **Sean's r2 tiles re-scored with r3 ON:** 11 right, tile 9 unwritten, 0 wrong (answers-2.260b-r3-rescore.json).
- **Gate:** fast tier 9902 passed; real gather Brahms p0+p5 ON vs all three flags 0: ties +2, slurs +5 -16, accidentals -2, red bars 42 -> 42, judged right->wrong 0, unwritten->wrong 0; named hand arcs q1099, q1233, q953, q1071, q1405 identical; by a cruder matcher (the lane's 28/27 matcher was not saved) hand ties 50 -> 50, slurs 30 -> 31, four hand arcs differ, all gains (q632, q648, b4012, q1420).
- **COST -- open, must be fixed before the next whole-movement overnight:** `page_strokes.gather_page_strokes` added ~873 s to Brahms p5 (gather 419-501 s OFF -> 1311/1418 s ON); p0 +87 s; peak RSS +0.2 GB. 2.260a's isolated measure was 4.0-6.6 s/page, so something on Brahms p5 is pathological. Untraced.
- **Open (position-everywhere follow-up):** tile 9 unwritten (head positions 9.38 vs 10.12 -- head-position measurement); litolff_02 and the 11 overnight tie->slur arcs come from `_two_note_reading` + OMR_TALL_HEAD_SPLIT, not the binder.

## 2.262 — the page-map cost (built, NOT landed; branch lane-2.262-page-map-cost d014c2182)
- **Cause (STAGED GATHER):** not `gather_page_strokes` as such and not the arc binder: `stroke_map.merge_accidentals` (2.242), run inside `map_strokes` for the PAGE map. On Brahms p5, 413 accidental boxes each tested about 4,400 page pieces against the exclude rects (every head/stem/ledger/clef/key/meter box) BEFORE the cheap "wholly inside the glyph-sized region" test: 1.83 M `_inside_share` calls, ~1,336 s of the 1,393 s map step. **Fix:** the cheap predicates run first; all three are pure and joined by `and` (manager checked: `_inside_share` only reads), so the set is unchanged.
- **Lesson:** a cost of pieces x boxes x excludes is invisible per cell (each factor is small) and explodes page-wide; a new page-wide pass is timed on the heaviest acceptance page, not one page. Why 2.260a's 4-7 s/page missed it is not established (p0's map was already 131 s).
- **Measure (cProfile, absolute times inflated):** Brahms p5 wall ON 1908 s -> 557 s (OFF 502 s, +11%); map step 1393 -> 57 s; peak RSS 9.67 -> 9.73 GB (OFF 9.32). p0 map 131 -> 13 s, wall 880 -> 763 s (no p0 OFF arm). The ~55 s left over OFF is `map_strokes` itself, not pursued. Machine load uncontrolled (a 2.256b lane_report ran alongside).
- **Gate:** gather records of Brahms p0 and p5, claims ON, fixed vs pre-fix (`--through gather`): recursive JSON diff = provenance/timing fields only; no `Q.*` row, claim or detail differs. Export not run (records row-identical). Fast tier 9909 passed, 0 failed. New test `test_merge_accidentals_cost_2_262.py` (not shown to fail on old code -- it pins the set, not the time).
- **Round 2 (b5924fc33):** the remaining 57 s had the same shape -- `_merge_clefs` scanned `others` and `_cut_touching_all` scanned the accidental rects before their cheap region / bounding-box tests; both reordered (pure, same set; manager read the diff). Page-map step p5 57.4 -> 17.5 s, p0 13.4 -> 6.2 s. The 17.5 s left is genuine per-piece work (connected components, `_cut_touching` ~8 s over 7,048 strokes), not pursued. Wall (cProfile, `--through gather`): p5 ON 536 s vs OFF 502 (+7%); p0 ON 791 vs OFF 780 (noise). Peak RSS p5 9.74 vs 9.32 GB, p0 7.91 vs 7.73. Gate: p0+p5 records vs round 1 differ only in provenance/timing; fast tier 9910 passed. The round-1 accidental test FAILS on pre-fix code (9,997 `_inside_share` calls vs a limit of 200); the new `_merge_clefs` test not run on pre-fix code. Not established: no per-function breakdown after r2; MusicXML not compared; single runs on a shared box.

## 2.264 — position everywhere (built OFF, NOT landed; branch lane-2.264-position-everywhere 62482615e)
- **The premise was wrong.** The handoff said litolff_02 and "the 11 overnight tie->slur arcs" come from pitch compares in `_two_note_reading` / tall-head split. Diffing Litolff `arc_kind` 20261031 vs 20261103: 21 tie->slur arcs, none a pitch compare that position fixes -- 8 detector-"slur" arcs whose end positions really differ or sit in the unread 0.25-0.435 sp band; 3 are litolff_02's family (dyad ends where only the UPPER stop head is boxed, the arc ties the LOWER heads -- an unboxed head, so positions genuinely differ); the rest refused-not-an-arc, unbound ends >= 2 sp from any head, a fused end. Tile 9: the head box is drawn ~0.6 half-step high (9.38; its hole 10.51 refused off-grid; truth 10) -- head-position measurement, left alone (moving a head to fit a tie is forbidden).
- **Lesson:** fixing the binder looked like fixing the rule; the same relation lives in `_two_note_reading`, `adjudicate_tie_pair`, `arc_claim.kind_from_ends`. And a cause named in a handoff is a claim -- the census by verdict found it wrong.
- **Change** (`ownership.py`, flag `OMR_TIE_POSITION_EVERYWHERE` OFF): `_two_note_reading` and `adjudicate_tie_pair.one_position` compare local staff positions (one <= 0.25 sp, two >= 0.435 sp) where decisive.
- **lane_report (frozen sample, from adjudicate, control reproduces the record):** Litolff ties +4 -4, Brahms ties +8; red bars and notes-not-written unchanged; judged right->wrong 0. litolff_02 and tile 9 unchanged. **Two Litolff ties LOST that are clear ties on the print** (p2 2/0/9/6-7, p11 11/0/3/16-17): a duplicate box on the stop head reads position 8.0 and wins `adjudicate_tie_pair`, binding the tie to a box EXPORT does not write -- the `adjudicate_tie_pair` half is unsafe as built; `_two_note_reading` half is the safer one.
- 9 tiles (only 9 arcs changed) on the lane worktree `out/print/2.264-position/`; unanswered. The real causes (unboxed dyad heads, head position) belong to M6 heads/ledgers and NEXT 7.

## 2.260c M4a — page beams, file only (built OFF, NOT landed; lane-2.260c-m4a-page-beams c4da01bb9)
- **Built:** `staged/page_beams.py` (`read_page`, `gather_page_beams` after `gather_cv_lines`), rows `Q.PAGE_BEAM` / `Q.PAGE_BEAM_TIP`, one row per page stroke naming every cell that holds its stems (read once, handed to every cell). Reuses `beam_strokes.role_of` / `tip_reading` and landed cut-offs; no raster. No `Q.CLAIMED_AREA` beam claim yet (gap against "claim once"). Export byte-identical ON vs OFF (Litolff p6+p16, Brahms p0+p5); cost +0.1-0.3 s/page; RSS unchanged. Fast tier 9926 (3 doc/rule-page failures fixed).
- **Parity by place with the old cell read A:** Brahms 74 of 143 A slabs / 105 page beams at the same place; Litolff 172 of 221 / 246. Shifted 6 px: 3 / 6 (the control fails as it must). Page beams with no A slab: Brahms 31, Litolff 74.
- **Manager look at the 12 crops (not sent to Sean -- they fail the tile standard):** most show NO beam: a slur, a staff line, empty space under a stem, ink inside "cresc." and a trill; the Litolff crops are cut too small to answer. Together with the lane's own look (Brahms p5: a C clef and a ledger fragment filed as beams), the page reader is filing OTHER marks' ink as beams.
- **Cause:** claim order. On the page map only ARC claims name page strokes (M3); staff-line residue, clef/key/meter, words, hairpins and ledgers do not, so the page beam reader sees their strokes unclaimed and reads them by shape. The old cell reads were shielded by guards and detector boxes. **Lesson:** "read once, claim once" works only in claim order (CLAUDE §3): a later reader on the page map is only as clean as the earlier claims on it. M4 cannot go ahead of the page-wide claims it depends on.
- **Next (proposed):** before M4b, the page-wide marks that claim first (staff-line residue, clef/key/meter, words/dynamics, hairpins, ledgers) name page strokes, as arcs already do (M3's open list); then re-run M4a's parity and crops. Tile-making note: a crop must show the mark; a crop picked at random from disagreements must be looked at before it goes to Sean.
