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

## 2.269 steps 0+1 — page-wide claims name page strokes (merged OFF 2026-11-04; lane-2.269-page-claim-names 10979b4ec, on top of M4a)
- **Step 0:** no M4a page beam lay on an arc-named stroke (0/246 L, 0/105 B) -- the slur-as-beam crops are slurs no arc claim holds; `page_beams` now skips any named stroke and takes the owner from claim order.
- **Step 1 (`OMR_PAGE_CLAIM_NAMES`, OFF):** `page_claim_names.gather_page_claim_names` names page strokes for word, key, clef, leading column, barline (incl. the M1-carved rule, via a column predicate -- the centre rule cannot name a system-tall rule), meter, hairpin claims; reads no raster; 0.02-0.04 s/page. Rows use `unit: page_ink` (not `ink`: `claims.covering` and `stem_end_heads.claims_holding` read `ink` rows as cell ordinals). Brackets name 0 strokes (the leading column, same layer, takes the ink first: contested). 9 Litolff barline rules stay unnamed.
- **Gate:** export byte-identical (M4a baseline / both flags off / both on); `claim_readout` and `claim_order` identical; Brahms p5 445 vs 433 s, RSS unchanged. **M4a page beams with no old slab: Brahms 31 -> 17, Litolff 74 -> 67** (taken by meter 11, clef 9, word 1); beams matching an old slab unchanged (nothing real taken).
- **What remains (lane's 12 crops, not sent to Sean):** dynamic-letter crossbars (6: `dynamicF` boxes whose claim is GUESSED, and only READ claims are named), hollow-head ink (4), title text (1), and one REAL beam the old cell reader missed (Brahms p0). Dynamics/heads are step 3 (boxed marks by ink share) and M6.
- Fast tier 9957 passed in the lane; after the merge to main the targeted, registration and wiring tests pass (134).

## 2.269 step 3 + 2.260c M4b (lane-2.269-step3-m4b, 2026-11-05; both OFF, NOT landed)
**Cause / lesson.** The narrowings (Litolff sample pages 6+16: 107 of 134, `beam_discounted_uncertain` 67 / `beams_ambiguous` 40) are decided by cell reader A and its ink measure C together: of the 67 discounted, `beams_not_by_ink` (C, `too_thin`/`through_heads`) 36, `beams_far_side` 25, `beams_neighbour_staff` 20, 39 have no CV beam at all (detector box only). So M4b = A+C (the plan's order stands). **A page reader is only as good as the claims and the heads under it (CLAUDE §3): on Litolff the plate merges beams into head blobs, which the page map cannot split until M6.**
**Step A (`OMR_PAGE_CLAIM_BOXES`, OFF; dynamics' letters, whole rests, repeat dots by ink share 0.5; ledgers/hollow-head ink left to M6).** M4a no-slab page beams: Litolff 67 -> 61 (p6+p16), Brahms 17 -> 11 (p0+p5). Litolff also lost 9 page beams that A matched: all 9 looked at -- 5 f/ff crossbars, 1 "ff" bar, 3 whole rests (all correct removals). Remaining 12/12 sampled Litolff no-slab are head ink (M6's); Brahms 11: 4 real beams A missed, 4 head pairs (M6), 1 meter numeral, 1 title text, 1 eighth rest. Export file-only: the flag changes only which page strokes the page reader skips; nothing else reads it (views are ignored with the retirement flag off).
**Step B (`OMR_PAGE_BEAMS_RETIRE_A`, OFF).** Page beams of role beam handed to each cell as `Q.BEAM_STROKE` (reader CV_PAGE_BEAMS, A's row shape), then C and the stem join run on them as on A's rows; A's rows are ignored where the page filed views. Frozen sample, one saved gather (tag `m4b-sample`, through adjudicate) replayed OFF/ON. Litolff: notes +22 -63, note values ~17, beams +24 -54, notes not written 2128 -> 2155 (NET LOSS: 9 heads became `is_a_beam_piece`; 54 decided -> narrowed against 17 narrowed -> decided). Brahms: notes +22 -16, beams +20 -40, notes not written 3102 -> 3093 (near neutral). Judged right->wrong 0 on both, unwritten->wrong 0; Litolff one judged answer right->narrowed (glyph/2/0/0/5/5, tile 9). Tried and reverted: not offering views of head-fused page beams (Litolff notes -128: the fused beams are real). Cause of the Litolff loss: A reads 50 of 221 slabs the page map does not give as beams (14 in blob strokes = beam merged into head), which is M6's ground. Control caveat: the replay's OFF arm differs from my through-adjudicate record (819/647 verdicts) because the replay also runs EVALUATE/INFER; the two arms agree with each other (identical when the flag changes nothing); not checked further. A silent no-op was found and fixed on the way: an undeclared `Q.PAGE_BEAM` read raised inside a try/except (first replay: 0 verdict differences).
**Not recommended to flip.** Brahms alone is near neutral; Litolff loses notes. Wait for M6 (heads split from beams), then re-measure.

## 2.260e M6a-c -- every head read once on the page (built OFF, NOT landed; lane-2.260e-m6-page-heads)
Flags `OMR_PAGE_HEADS` (M6a, file only), `OMR_PAGE_HEAD_VIEWS` (M6b), `OMR_PAGE_HEAD_CLAIM` (M6c), all default OFF. New `staged/page_heads.py`; call sites in `gather.py`: before `gather_notehead_positions`, after `gather_page_claim_names`, and `page_heads=` into `gather_far_head_ledger_positions`; `_head_claims` in `adjudicators/stroke_owner.py`.
- **Cause:** a head was a subject only if a detector box stood on it, in one padded cell: twin boxes were two heads, the far-head ledger read waited on the BOX's rounded position (tile 9: box 9.38 rounds 9, never asked), the claim was "a box holds half a cell stroke". **Lesson:** every head reader repaired its predecessor's miss and asked the box, never the ink.
- **M6a (Litolff 8-page sample):** 5,794 boxes -> 5,564 heads (230 folded); 617 heads (11%) with ink centre >= 0.5 step from the box; 104 twin pairs disagree >= 0.5 step; ink-only head-shaped blobs on a boxed head's stem: 57 (11 on a rung). Brahms p0+p5: 1,737 boxes -> 1,706 heads; 38 ink-vs-box >= 0.5 step; 3 ink-only. Export byte-identical ON/OFF (Litolff p10). Controls: planted double box folds (unit test, fails at IoU 0); tile 9 reads box 9.38 against ink 10.54 (strokes; the trim refused `too_wide`); Brahms p0 black heads 374/378 OFF and ON; the half-head plant drops whole heads 221 -> 2; planted double claim raises contested ink. Cost: reader 1.3-3.5 s a Litolff page, 4.7 s (p0) / 11.9 s (p5) Brahms; Brahms gather 1206 s OFF vs 1201 s ON, peak RSS 11.46 vs 11.57 GB.
- **M6b round 1 refuted a trigger:** asking the ledger lines when a ledger stub touches a first-space head read ONE end of a tie and not the other (p2: -2 vs -1): 5 ties -> slurs. Dropped (stubs are recorded, not a trigger; stubs must stand >= 1.5 steps outside the staff). Kept: box OR ink centre outside the first space. Tile 9 now reads ledger position 10 (pitch D4 -> C4); its wrong slur is gone, the tie it should be is still unwritten.
- **Three measures (Litolff 8 frozen pages, all three flags, re-gathered both arms):** notes +2 -2, flags +1 -1, beams +2 -1 ~1, slurs -4, pitches ~5, blue +1 -2; red bars 0 -> 0; judged right->wrong 0, unwritten->wrong 0, **right->narrowed 1** (2.154-review tile 1, glyph/11/1/0/9/3: duration `beams_ambiguous`; traced to M6c: with `OMR_PAGE_HEAD_CLAIM=0` it stays decided). Brahms p0+p5: NOTHING CHANGED, red bars 41 -> 41, judged 0 / 0. Misshapen ledger claims 64 -> 126 (stubs not level) and heads 141 -> 96 on Brahms p0.
- **Tile 20 (glyph/11/0/2/8/3) does NOT come back.** Its G4 is narrowed `whole_class_filled_on_a_stem` and the rescued E4 stem-mate is decided half: the missing step is every note on one stem sharing one written value (CLAUDE §4), a rhythm rule, not head reading. M6 changes neither head's position or pitch there.
- **Open:** `staged.check` 226 -> 228 (PAGE_HEAD declared-ungathered + producer-only, by design as PAGE_BEAM). M6d not built; see census above.

## 2.260c M4b with M6 ON (2026-11-05; measure-only, branch measure-m4b-m6, main 741d63f4f)
**Answer: NO. M6 does not fix M4b's Litolff loss.** STAGED. Litolff 8 frozen pages (2,4,6,8,9,10,11,16), Brahms p0+p5. Every arm RE-GATHERED (the M6 flags, `OMR_PAGE_BEAMS`, `OMR_PAGE_CLAIM_NAMES`, `OMR_PAGE_CLAIM_BOXES` all act in GATHER; only `OMR_PAGE_BEAMS_RETIRE_A` acts later), same tree, shared detector cache, tag 20261029-night, one large process at a time.
- **A (baseline):** `OMR_PAGE_HEADS`, `_HEAD_VIEWS`, `_HEAD_CLAIM` = 1; M4b flags 0. **B:** A + `OMR_PAGE_BEAMS`, `_CLAIM_NAMES`, `_CLAIM_BOXES`, `_BEAMS_RETIRE_A` = 1. **C:** B with `OMR_PAGE_HEAD_CLAIM=0`. Command: `lane_report --from gather --plates litolff --flag OMR_PAGE_HEADS=1:1 ... --flag OMR_PAGE_BEAMS_RETIRE_A=0:1` (B vs A); C = a direct `tools.omr.staged` gather with the flags in the environment, then `lane_report arm` + `rescore` against A's files.
- **First attempt at C was a no-op** (re-exporting B's saved gather with the claim flag off: byte-identical to B, because the head claim acts inside the gather's own ADJUDICATE). Redone as a real re-gather. Lesson: `--from gather` records carry their verdicts; a flag read in ADJUDICATE still needs its own gather.

| Litolff | B vs A | C vs A |
|---|---|---|
| notes | +24 -59 | +26 -59 |
| beams | +23 -51 ~20 | +24 -51 ~21 |
| flags / values / pitches | +5 -23 / ~21 / ~7 | same |
| blue marks | +3 -11 | +3 -11 |
| notes not written (A 2435) | 2461 (+26) | 2459 (+24) |
| red bars | 0 -> 0 | 0 -> 0 |
| judged right->wrong / unwritten->wrong | 0 / 0 | 0 / 0 |
| judged right->narrowed | 1 (glyph/2/0/0/5/5) | 1 (glyph/2/0/0/5/5) |

M4b alone measured notes +22 -63, not written +27: with M6 on it is +24 -59, +26. No change in kind.
- **glyph/2/0/0/5/5** (Sean: eighth): A decides eighth (`head_and_marks`, right); B and C narrow {0.5, 1.0} `beams_ambiguous`. Still right -> narrowed with M6 on, with or without the head claim. The answer stays inside the set, nothing is wrong, but M4b still loses a decided answer.
- **glyph/11/1/0/9/3** (Sean: quarter): A already narrowed it (`beams_ambiguous`: M6c's cost, baseline); B narrowed; C decided quarter (`stem_tip_reads_no_beam`, right). So `OMR_PAGE_HEAD_CLAIM` alone owns that loss, and C is the only arm that gets it back. judged score (Litolff, whole index): A right 100 / wrong 12 / narrowed 11; B 100/12/11; C 101/12/10.
- **Brahms p0+p5:** B vs A and C vs A are identical: notes +3 -6, beams +4 -12 ~4, slurs +3 -7, blue +8 -2, dots +3 -1, flags +7 -3; red bars 41 -> 40; notes not written 759 -> 762 (B), 759 -> 762 (C); judged right->wrong 0, right->narrowed 0, unwritten->wrong 0. Near neutral, as M4b alone.
- **Cause / lesson:** the loss is not (only) beams fused into head blobs. With heads read once on the page the Litolff note loss is unchanged (-59), so the page beam rows still disagree with reader A on Litolff slabs; the next step is to look at the crops of the 59 lost notes (not done here), not to flip. Not recommended to flip M4b; leave `OMR_PAGE_HEAD_CLAIM` OFF on Litolff too (C regains one answer B/A lose).
- Disk filled during the lane (manager notice): checked, no "No space left" in any log, all saved records load; nothing re-run for that reason.
- Work dirs (local, not committed): `out/m4b-m6/{lit,brh}-{B,C}/work`.

## 2.306 step 0 — stems and beams on the page: measurement only (2026-11-12)

STAGED. No code changed. Lane `lane-2.306-stems-beams-page` (local, nothing committed). Counts are the lane's;
"real beam" below means agreement with cell reader A, which is a lead, not truth. Crops were leads only.

**Cause.** The page beam reader (M4a, `OMR_PAGE_BEAMS`) runs in GATHER and can skip only ink a claim has already
named as page-stroke ids. Arcs, heads, rests, tremolos and accidental ink now do (130-527 strokes a page). Clef,
meter, word and dynamic claims still exist only as rectangles that the ledger (2.284) settles in ADJUDICATE --
too late for a GATHER reader. Stems are still read cell by cell, and the page beam reader joins the stems of
cell reader A. **Process lesson:** a page reader is only as clean as the claims made before it, in its own stage.

**(a) M4a re-run on main** (Litolff p6+p16, Brahms p0+p5; same pages as 11-04):
- Beams with no slab from the cell reader (false-beam pool): Litolff 54 (was 74), Brahms 28 (was 31).
  Owned by another mark per the ledger: Litolff 28 (heads 19, clef 6, dynamic 2, word 1); Brahms 18 (meter 11,
  dynamic 5, clef 2). Unclaimed: Litolff 18, Brahms 7.
- Beams of reader A the page reader misses: Litolff 50, Brahms 69. Head claim holds the ink 13 / 12; read as
  thin, hook or stub pieces 11 / 19; merged into a blob 8 / 7+; found at a slightly different place ~8 each.
  Many Brahms misses are reader A's own errors (12 slurs, 13 staff-wide slabs with no page stroke under them).
  Vertical reach and the cell edge are no longer the cause (3 Litolff slabs cut at the edge).
- Biggest blocker: at the stem tip the page reader and the cell level count (D) disagree on 269 of 768 Litolff
  stems and 311 of 516 Brahms stems, mostly page "no beam" where D reads one (158 / 260). Brahms p5: 37 beams
  but 278 hooks and 201 thin spans -- the shattering plate breaks under the 0.5 sp cut-off. NOT looked at on crops.

**(b) Size.** Litolff, 8 frozen pages, 4,560 real heads: 236 with no stem row (5.2%), 189 of them still written
plain as quarters or halves; 129 narrowed by beam doubt (51 `beams_ambiguous`, 78 `beam_discounted_uncertain`);
36 both. Brahms p0+p5, 1,190 heads: 43 no stem row (3.6%), 28 beam doubt (15 / 13); 12 of 39 red bars hold one.

**(c) Cell readers of stem and beam ink today.** GATHER: `gather_cv_lines` (+ `_observe_stem_tip_ink`,
`_observe_beam_stem_join`, `_observe_stem_slashes`, `_observe_dot_stroke_ink`), `_lowconf_rescue_witnesses`,
`gather_stroke_map`, `gather_head_stem_reach`, `gather_notehead_stem_cross_ink`, `gather_beam_stroke_ink` (C),
`gather_beam_stem_levels` (D), `gather_detector_beams`, `gather_stem_end_heads`. ADJUDICATE: `_beams_from_strokes`,
`_tips_from_strokes`, `_strokes_on_a_system_arc`, `_beams_on_owned_strokes` (the last two re-ask arc ownership
from boxes). No page stem reader exists.

**(d) Lane's proposal.** Stems on the page first: a stem is the page vertical stroke a page head (2.290) touches
on its engraving side, claimed once; retires the stem half of `gather_cv_lines`, the rescue stems and
`gather_head_stem_reach`; M4a then reads page stems. Beams wait: M4b (built, OFF) still loses Litolff notes
(+22 -63; -59 with page heads on) and the shattered-beam pieces need crops first. Controls from real judged
cases: Sean's Brahms p0 stem labels, 2.150 tile 11, 2.150b tile 20, the 2.300 tiles. The 2.280 r3 tiles were
never sent and are not controls.

**Not verified:** export identity with `OMR_PAGE_BEAMS=1`; owner counts (through cell-stroke links, 3-5 beams
have none); Brahms measured on p0+p5 only; red-bar count on Litolff (only p6+p16 exported).
**Prior work not to rebuild:** 2.204 stems from CELL strokes (parked: its "stem readers disagree" abstentions
cost 2-5.5% of notes), 2.259, hairpin-ink exclusion (2.25b), `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM`.

## 2.306 stems on the page, round 1 (2026-11-13) -- built OFF (`OMR_PAGE_STEMS`), NOT ready to land

STAGED. `lane-2.306-stems-beams-page`; pre-retire tip 40f7b5bf2, retire commit 171568282 (+3 small commits).
Code `tools/omr/staged/page_stems.py`, tests `tools/omr/tests/test_page_stems_2_306.py`, scripts
`benchmarks/page-ledger-2026-11/2306/`. Sean's tiles (out/print/2.306-r1) not yet answered.

**Cause.** A note's stem was decided three times by three cell readers (the head-to-stem join, the duration
reader's own box overlap, the stem-direction reader). The page reader answers once -- the page map's vertical
stroke at the head's engraving side (right edge up, left edge down; a second's displaced head sits on its
partner's stem) -- and hands that answer to all three. Two page facts only seen on real pages: the page map
splits a stem at its head (the stroke can stop ~2 sp from the head's centre); in divisi each head also meets
the other voice's stem ending ~0.7 sp away -- the stroke that ENDS at the head wins.
**Process lesson.** The stem join feeds voice split, chord grouping and arc binding; changing who owns a stem
moves ties, rests and slurs far downstream and no lane reads those effects first.

**File change, OFF vs ON, pre-retire** (frozen 8 pages; one flag-ON gather per plate, both arms replayed; the
control line warns neither arm reproduces the stored record -- expected, gathered ON):
Litolff notes +39 -33, flags +13 -26, ties +4 -2, rests +10 -3, red bars 172 -> 180, not written 2089 -> 2071.
Brahms notes +36 -23, flags +27 -14, ties +8 -54, rests +62 -8, slurs -38, red bars 143 -> 157, not written
3083 -> 3072. **The Brahms ties -54 / rests +62 / slurs -38 and Litolff flags -26 are UNEXPLAINED.**
"No stem row" heads: Litolff 240 -> 126 now stemmed, 114 abstain (109 no free vertical stroke beside the head
-- the plate fuses stem into head; 3 up-and-down; 1 two candidates; 1 held by a neighbour). Brahms 146 -> 107
stemmed, 39 abstain (30 no stroke, 8 two voices, 1 two candidates).
Sean's Brahms p0 stem labels: 261 of 277 right, 16 missed, 31 of ours not his (unchecked).
Judged right->wrong 0, unwritten->wrong 0 on both (one Litolff right->narrowed, 2.158 tile 11).
judged_claims: Litolff p6+p16 gain 2 contradictions (2.276 r2 #2, #8: tremolo slashes, the stem claim takes
31-34% of the box; the base has 4 of the same kind); Brahms not run. check 229 (one over: `gather_coverage`
counts `Q.PAGE_STEM` as ungathered, as PAGE_BEAM / PAGE_HEAD). Fast tier flag OFF 10,608 passed, 3 failed
(ink-rules page, regenerated, file passes; whole tier not re-run).

**Retire, measured.** Dropping the cell join where the page cannot stem a head: Litolff 266 stems lost, red
bars 172 -> 187; Brahms 76 lost, 143 -> 157; right->wrong still 0. NOT retired: the cell stem finder, rescue
stems, `gather_head_stem_reach` (flag, beam and tip readers still measure on the finder's rows).

**Controls.** Real-ink Brahms p0 fixture (14 of Sean's 17 stems in eight bars; mirrored page finds almost
none); 2.300 tile 2 (three chords on three stems; without the displaced-second rule the chord falls apart).
NOT done: 2.150 tile 11 / 2.150b tile 20 (Brahms p15 not gathered), the four 2.300 tiles on Brahms p19.
**Prior work.** 2.204 parked (reader-disagreement abstentions cost 2-5.5% of notes); 2.280 r3 (most no-stem
heads are a second's partner); 2.260c M4a (page readers file other marks' ink until claims name strokes).

## 2.306 stems round 2 (2026-11-13) -- cause of the r1 losses; no code changed (`lane-2.306-stems-beams-page` 59c64887d)

STAGED. **The page stems are not what goes wrong.** Two downstream readers relied on the old cell join
leaving stems unread or wrongly joined.
- **Twins in the wrong staff's chords (Brahms, top cause).** The page hands a head's one stem reading to every
  cell that shows the head, including the copy in the neighbouring staff's padded cell (a "twin", owned by
  another staff). The old join almost never stemmed those copies. ON, 533 twins (Brahms) / 454 (Litolff) gain
  a direction, and `adjudicate_event` (rhythm.py opposite-stems chord split) and `adjudicate_voices` group
  every notehead box in the cell, twins included: a twin splits a chord, the bar gets a second voice and stops
  adding up. Brahms: all 26 newly red bars hold such a twin (12 clear, net +14); 35 of the 54 lost ties and 57
  of the 60 gained rests are in those bars (the rests are real rest boxes now written in the voice the split
  made; none is filled in); 47 of the 54 tied notes are still written.
- **A wrong join hid a weak beam read (Litolff).** The old box-overlap join sometimes gave a head its
  neighbour's stem and the beam was read off that neighbour. On its own stem the tip reads 0 beam levels
  (`gather_beam_stem_levels`) where the beam starts a hair right of the tip, and `stem_tip_reads_no_beam`
  decides a quarter (real case `glyph/9/0/2/0/4`). Litolff: 14 new red bars (6 clear, net +8): 9 event/voice
  splits (5 twins, 4 own heads), 5 value changes; of 25 lost flags 16 are eighths now written beamed (same
  value), 6 eighth -> quarter, 3 notes gone.
**Process lesson.** A downstream reader that relied on "unknown" or on a wrong join breaks the moment the join
is right: list what READS a quantity before making it more correct.
Tile 3 (Litolff p10): not clef/key ink -- a free down stem under heads fused with their ledger lines; the
quarter became a half through the shared-stem value (Sean's tile decides). Tremolo contradictions: the stem
claim takes only the vertical stroke; Sean's slash box includes the stem pixels it crosses (31-34%, over the
30% line); main already has four of the same kind. Unresolved: `glyph/4/1/2/5/3` (page says down, the
direction reader says up). Numbers unchanged from r1; right->wrong 0; check 229.
**Proposed (not built):** `adjudicate_event` / `adjudicate_voices` skip heads owned by another staff; the
clean-tip rule abstains where the beam-level read may have missed a beam that does not touch the tip.

## 2.306 stems round 3 (2026-11-13) -- other-staff copies out of chord/voice grouping; built OFF (`lane-2.306-stems-beams-page` 00940d973, fix d1f632a80)

STAGED. `rhythm.adjudicate_event` (opposite-stems chord split) and `adjudicate_voices` ignore the stem
direction of a head whose `Q.GLYPH_OWNER` verdict names another staff -- the same test EXPORT uses to drop
those copies; only under `OMR_PAGE_STEMS`. The cell join had already stemmed ~13 Litolff / 22 Brahms copies
that were splitting chords BEFORE r1, so Brahms ends below OFF.
Controls from replayed real rows: Brahms p4 staff 11 bar 1 (r1 ON split `[14]` / `[2,3,4,12]`; r3 ON = OFF);
splits between a staff's own heads still happen (Litolff all 6; Brahms 42 OFF / 49 ON incl. the p0 staff 11
divisi); splits involving a copy: Litolff 13 OFF (52 r1) -> 3, Brahms 22 OFF -> 1.

**File change, pre-retire, OFF vs ON, same gathers (r1 -> r3):**
Litolff red bars 172->180 -> **172->173**; ties +6 -2; rests +1 -7; slurs +12 -10; flags +13 -25; notes
+41 -29; not written 2089 -> 2062.
Brahms red bars 143->157 -> **143->129**; ties +14 -17 (was +8 -54); rests +5 -25 (was +62 -8); slurs
+30 -20; flags +27 -14; notes +36 -16; not written 3083 -> 3065.
Judged right->wrong 0, unwritten->wrong 0 on both. check 229 (Q.PAGE_STEM counted ungathered). Full fast
tier NOT run this round.
**Remaining.** Brahms: 1 of r1's 26 new red bars remains, 15 clear; 17 lost ties (10 on notes whose only
change is the stem-join reason, 5 in bars with no direction change) and 25 rests no longer written are NOT
traced. Litolff: 10 new red bars remain (9 clear), all from the staff's OWN heads -- the page stem decides a
direction where the cell readers had "stems disagree" (4) or a beam-mate guess (4).
**Readers of stem direction / join that do NOT skip other-staff heads** (static grep, unchanged):
`stem_value.adjudicate_stem_value`, `adjudicate_head_stem`, `unison_two.adjudicate_unison_voices`,
`rhythm._second_evidence`, `_flag_direction`, `_own_stem_side`, `_direction_from_a_beam_mate`,
`ownership._long_chord_stem_tip` / `stem_of` / `both_ways`, `consequences._on_one_stem` / `_voice_count`,
`export._stem_facts_of` / `_settle_divisi_pairs` / `_voice_split`.
**Clean-tip rule, size only:** "a clean tip means no beam" decides 207 heads on Litolff (2 with beam-like ink
within 1 sp of the tip) and 927 on Brahms (29 on 24 stems). Not changed -- it changes written values.

## 2.306 stems round 4 (2026-11-13) -- a stem is the whole run; gate with the flag ON is MIXED (`lane-2.306-stems-beams-page` 39dc41788)

STAGED. Sean's r1 tiles: 12 of 12 are stems; tiles 6 and 7 stop short (answers/answers-2.306-r1.json).
**Cause.** The page map ends a stroke wherever another mark's ink crosses it (a head of the same chord, a
tremolo slash, an erased staff line); the reader took each piece as a whole stem. Measured first: 262 of
3,128 claimed stems (Litolff) and 207 of 3,393 (Brahms) were part of a longer run; the crossing was a chord
head 245 / 193 times, an erased line 19 / 20.
**Lesson.** The page map's unit is a stroke, not a mark: a reader that takes one stroke as one mark must say
where it stitches pieces together, and why.
**Built.** A stem = the whole run of vertical pieces in one column; a gap is bridged only by an erased line's
thickness (<= 0.3 sp), a head on ONE side of the stem, or a stroke crossing the column (slash, beam) -- never
empty paper (221 / 107 refused), never heads on both sides (two voices end to end, 15 / 4 refused). The stem
claims only its own vertical pieces. Controls from Sean's tiles, failing on r1 first: tile 7 (Litolff p10
`glyph/10/1/0/14/6`, one stem carrying both heads); tile 6 (Litolff p16, the run now reaches the half note --
but the head's own stem reading still abstains because the tremolo slash is boxed and claimed as a NOTEHEAD:
upstream); a real Brahms end-to-end pair not joined.
**Gate, pre-retire, OFF vs ON (fresh r4 gathers):** Litolff red bars 172 -> 176, ties +6 -2, slurs +12 -4,
flags +16 -30, notes +43 -32, not written 2156 -> 2130. Brahms red bars 143 -> 130, ties +18 -13, rests
+5 -25, slurs +30 -18, flags +25 -14, notes +41 -13, not written 3087 -> 3061. Judged right->wrong 0,
unwritten->wrong 0 on both. Sean's p0 labels 261 right / 16 missed / 30 not his (unchanged). check 229.
Fast tier flag ON 10,590 passed / 15 failed: 1 real break fixed (3845eddb5: voices read the owner verdict,
which a test forbids -- now via the chord-grouping verdict); 14 fail with the flag OFF too in the frozen copy
(no .git / gitignored files, stale ink-rules page, the lane's own retire test). NOT re-run after the fix.
judged_claims: the two tremolo contradictions unchanged; one new Litolff one (2.288 r1 #10, "CR" claimed as
a rest) arises before the stem read (believed OCR variation between gathers, not verified); Brahms none new.
**What remains.** Litolff's 11 new red bars all come from the staff's OWN heads taking the page direction (4
had "stems disagree", 4 a beam-mate guess); by the lane's look the page direction is right in the 10 it
looked at, and in 3 the stem-direction reader still reports the opposite because it works from cell rows
instead of taking the page's -- a hand-off bug, not fixed. Litolff flags: 16 eighths now beamed (same value),
7 eighth -> quarter (the clean-tip read), 5 notes gone. Brahms 13 lost ties (join reason only, or the next
bar's heads narrowed as "hollow head with a flag" / "beam doubt"; 3 notes gone); 23 rests no longer written
are second-voice rests of splits the r3 fix removed.
Tiles (12, on what the FILE changes): out/print/2.306-r4 -- not yet sent.

## 2.306 stems round 5 (2026-11-13) -- the page's direction is THE direction; red bars fall on both plates (`lane-2.306-stems-beams-page` 8a6b815f3, fix ea7337de0)

STAGED, flag OFF. **Cause.** The stem-direction reader worked the direction out a second time from cell rows
where the page had already read it; for three Litolff heads (`6/1/9/10/2`, `6/1/9/10/7`, `10/1/7/3/2`) the
second answer was the opposite. Where the page read a head's stem the direction is now the page's (reason
`page_stem`). **Lesson.** One answer, read once: handing a reading to a reader is not enough if that reader
still re-derives what the reading already says. Heads whose written direction changed r4 -> r5: Litolff 76,
Brahms 23.
**Gate, pre-retire, OFF vs ON (replays of the r4 gathers):** Litolff red bars **172 -> 167** (r4 176); notes
+50 -45, flags +22 -29, ties +6 -2, rests +1 -6, slurs +17 -7, not written 2156 -> 2136. Brahms red bars
**143 -> 129**; notes +41 -14, flags +27 -14, ties +18 -13, rests +5 -25, slurs +31 -19, not written
3087 -> 3062. Judged right->wrong 0, unwritten->wrong 0 on both. **Fast tier with `OMR_PAGE_STEMS` ON, real
worktree at the branch tip (retire commit active): 10,616 passed, 0 failed.** check not re-run (229 in r4).
Litolff: 9 new red bars remain, 14 clear -- 7 are own heads taking the page direction where cell rows read
another or "stems disagree" (`2/0/3/5`, `2/0/8/0`, `4/0/8/11`, `4/1/2/4`, `4/1/8/8`, `6/1/4/8`, `8/0/1/2`),
1 a head gaining a stem, 1 a stem newly touching a head. Unjudged.
**Tile 6's slash (report only).** The detector boxed the right half of the tremolo slash as
`noteheadBlackOnLine` (`glyph/16/0/9/6/0`); it is written as a phantom quarter note; the 2.290 page-head
reader claims that half's ink (stroke 1756) as a head, the left half (1727) has no owner, the tremolo reader
claims neither. That fake head is why the half note's stem reads both ways and abstains.
The r4 tiles stand unchanged (out/print/2.306-r4), not yet sent.

## 2.306 stems round 6 (2026-11-13) -- why real notes are lost with the page stem reader ON; no code changed (`lane-2.306-stems-beams-page` 9349f0d7e)

STAGED. Sean's r4 file-change tiles: 5 right, 1 wrong value, 4 real notes lost (answers/answers-2.306-r4.json).
Control: r5's lines reproduce exactly on the frozen pre-retire tree (172 -> 167, 143 -> 129; right->wrong 0).
**Cause. The stems are not wrong.** The losses come from what the page reader files BESIDES the stem, read by
cell-era rules:
1. **Copies of a stem filed in other staves' cells.** The reader files a stem row in every cell that shows
   the head, including the neighbour's padded cell where the head is only a copy: 519 of 623 filed copies
   (Litolff) and 669 of 748 (Brahms) exist only for heads the record gives to another staff.
   `rhythm._not_the_neighbours_beam` treats any stem row in the next staff's cell as that staff's stem and
   throws away this staff's own beam (97 / 115 heads lose beam strokes ON; in 94 / 112 the neighbour cell
   holds such a copy). The filed copies also get no beam-level rows (`gather_beam_stem_levels` reads only
   cell-reader rows: 0 of 623) and no beam-stem-join rows.
2. **Stems stitched across empty paper.** r4's "head on one side" exception accepts any head whose box merely
   touches the gap: stitched stems bridging more than 1 sp of blank paper are 57 of 133 (Litolff) and 64 of
   109 (Brahms). The reader's own fault; not the top cause.
3. **Downstream.** Where the page stem is right: EXPORT's chord check (`chord_value_undecided`), the duration
   reader's rule-8 guard (`beam_discounted_uncertain`), bar arithmetic that can no longer force a value.
The five tiles: 3 and 11 (Litolff) lose their beams to the neighbour-beam rule through a filed copy, then
EXPORT refuses `duration_narrowed`; 5 (Sean: wrong) -- two strokes discounted as the neighbour's beam and,
with no attached stem, the rule-8 guard does not apply, so a quarter is DECIDED; 7 (Brahms) -- a bar-mate
takes the page direction, chord mates disagree, EXPORT drops it `chord_value_undecided`; 12 -- bar-mates
gain a filed copy as their stem, are narrowed, and the bar is no longer forced.
Per glyph, real losses 22 (Litolff) and 9 (Brahms); the page reader's own side output accounts for about 20
of 29 changed notes on Litolff and 5 of 13 on Brahms; the rest downstream. (Not reconciled with the lane
report's by-place -45 / -14.)
**Process lesson.** A page reader's side output is read by cell-era rules as if a cell reader had filed it:
before handing a page reading to old readers, list what they ASSUME about a row filed in a cell, not only who
reads the quantity. This is the 2.307 cause again -- the cell as container -- now on the page reader's own rows.
**Proposed, not built:** a crossing head must cover the gap (at most 0.3 sp blank; controls `10/1/6/7/3`,
`9/0/2/1/0`); filed stems get the beam-level and beam-stem-join readings; a RULING on whether a page stem may
be filed in a cell for a head that belongs to another staff; tile 5's decided quarter on a head with no
attached stem (rule-8 guard). Unverified: page direction right in only the 4 cases looked at (leads).

## 2.306 stems round 7 (2026-11-13) -- Sean's ruling built: a stem is filed only with its own staff; a crossing must cover the gap (`lane-2.306-stems-beams-page` a4755ac78 + test pin)

STAGED, flag `OMR_PAGE_STEMS` OFF. Ruling (Sean 2026-11-13 "Yes", DECISIONS + page-facts on main f0cf19da): a stem is filed only with the staff its note belongs to.
**Cause found on the way (the process lesson).** GATHER cannot apply the ruling on most pages: the page owner's ledger answer for a head in the gap is DEFERRED to
the end of the run while the far-head ledger reader builds its size pool, so at stem time 134 Litolff p4 heads had no owner (tile 3's among them). A ruling is
applied in the stage where its fact exists: GATHER files only where the owner is known (page owner decided, else inside one staff); ADJUDICATE
(`rhythm._page_view_only_for_copies`, read by `_not_the_neighbours_beam`) ignores a page view named only by heads whose decided `Q.GLYPH_OWNER` is another staff.
Built: (1) the ruling, both stages; (2) a crossing mark joins two stem pieces only where it covers the gap (<= 0.3 sp blank) -- refuses `head_not_covering`;
(3) a filed page stem view gets `Q.BEAM_STEM_JOIN` / `Q.BEAM_STEM_LEVELS` rows by the cell readers; (4) with the flag on, a head with no stem whose strokes were
discounted stays narrowed (never a DECIDED quarter). Controls from real tiles: r6's two stitched-over-paper stems (p9 glyph/9/0/2/1/0, p10 glyph/10/1/6/7/3)
refused; tile 3's ledger head owned by staff 2 by the page owner, nobody without it, the other staff when the row is flipped; 175 copies beside tiles 3/5/11 not
filed; the view rule with a home owner / a cell reader's row / flag off.
**Measured** (r7 re-gather of the frozen pages with the flag on, `--replay-gathered`, scratch `r7/lr7c-*`): Litolff red bars 162 -> 152, notes +48 -44, judged
right->wrong 0, unwritten->wrong 0; Brahms red bars 143 -> 124 (r6 tree: 129), notes +43 -23, right->wrong 0, unwritten->wrong 0. Litolff control line says
neither arm reproduces the record: ADJUDICATE changed after the gather (ON 11 of 9107 duration verdicts) -- expected, the copy-view rule is ADJUDICATE.
Sean's r4 tiles: 11 (9/0/2/0) recovered; 5 (4/1/2/4) no longer an eighth made a quarter; 9/0/2/1 and 10/1/6/7 lose fewer. Tile 3 (4/1/2/5) still loses its
four eighths -- a DIFFERENT cause, older than r7: its stem runs through a SECOND (heads on both sides at Litolff p4 y 2458-2488) and `join_runs` refuses every
gap with heads on both sides (`heads_both_sides`, built for two voices end to end), so the page stem stops at the chord (58 px), never reaches its beam, and the
beam-join reading (3) reports "not joined" against a certain beam (`beam_certain_not_joined`). Geometry of the two real cases: tile 3 (a second) has the HIGHER
head on the RIGHT, centres 0.5 sp apart; the r4 divisi fixture (two voices end to end, Brahms) has the higher head on the LEFT, 1.5 sp apart. Question to Sean
before code (rule 3). Fast tier (cloud, 2 workers): flag OFF no new failure (12 environment failures fail on the base commit too); flag ON one real change --
`test_staged_duration` neighbour-beam test asserted the DECIDED quarter fix (4) removes; now pinned OFF = decided, ON = narrowed quarter/eighth.

## 2.306 stems round 8 (2026-11-13) -- a stem runs through its second (Sean: "in a second the higher note is always right of the stem")

STAGED, flag `OMR_PAGE_STEMS` OFF, lane ce7735cc6 (frozen pre-retire tree + lane diff; re-gather `2306-r8-*`, `--replay-gathered`, scratch `r7/lr8-*`).
**Cause** (r7): tile 3's stem runs through a second; `join_runs` refused every gap with heads on both sides. **Rule** (Sean 2026-11-13 "Yes, always", DECISIONS +
page-facts on main e02d32ad): heads on both sides a step apart (centres within `SECOND_STEP_SP` = 0.75 sp) with the HIGHER on the RIGHT are one second -- joined,
kind `second`; the higher on the LEFT is two voices -- refused. Control from the real tile-3 window (Litolff p4 strokes 1936 + 1938 through heads /9 and /16 to beam
1873), mirrored left-right it must refuse. **Measured:** Litolff red bars 162 -> 152, notes +48 -40 (r7: -44), right->wrong 0, unwritten->wrong 0, ON reproduces the
record; tile 3's bar 4/1/2/5 loses nothing now (r7: 4 eighths); 4/1/2/4 still loses one eighth. Brahms unchanged from r7: red bars 143 -> 124, notes +43 -23,
right->wrong 0. Sean's 12 blind tiles (6 Litolff + 6 Brahms from the lane report's cases, 2 controls): `out/print/2.306-r8/` (key outside), sent 2026-11-13.
