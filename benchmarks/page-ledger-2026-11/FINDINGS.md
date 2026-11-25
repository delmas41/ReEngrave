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

## 2.306 stems rounds 7-8, re-measured (2026-11-14) -- built OFF, `lane-2.306-stems-beams-page` 128ec0b7b; NOT landable: stems cannot stand alone yet

STAGED. Rounds 7 and 8 were built on the lane by another session from Sean's two rulings (DECISIONS
2026-11-13; page-facts): a stem is filed only with its own staff; in a second the higher note stands right
of the stem. The round-7 write-up is on the lane branch's copy of this file. This section is the independent
re-measure at the branch tip, pre-retire, fresh flag-ON gathers of the 8 frozen pages per plate.
**Built (checked in the code):** a crossing head joins two stem pieces only where it covers the gap
(<= 0.3 sp blank; `head_not_covering`); GATHER files a stem only where the head's owner is known, and
`rhythm._page_view_only_for_copies` (read by `_not_the_neighbours_beam`) ignores a filed stem whose heads all
belong to another staff; filed page stems get beam-join and beam-level rows; a head with no stem whose beam
strokes were discounted stays NARROWED, not a decided quarter (in the rule-8 area); r8: a stem runs through a
second.
**Lesson (measurement).** The OFF baseline moves when GATHER changes (Litolff OFF red bars 172 on the r6
gather, 162 on r8's -- both gathered with the flag ON, and the stem claims change what other readers can
claim): compare rounds by their OFF->ON pair on ONE gather, never OFF to OFF.
**Gate, OFF vs ON, same gather:** Litolff red bars 162 -> 152, notes +48 -40, flags +18 -21, ties +6 -2,
rests +1 -7, slurs +18 -14, not written 2187 -> 2164. Brahms red bars 143 -> 124, notes +43 -23, flags
+31 -16, ties +14 -17, rests +5 -25, slurs +33 -23, not written 3089 -> 3071. Judged right->wrong 0,
unwritten->wrong 0 on both (Litolff wrong->right 1). The ON arm reproduces the record exactly. Fast tier flag
ON, real worktree: 10,622 passed, 0 failed. check 229. judged_claims: the same 3 Litolff contradictions as r4
(two tremolo slashes, "CR" as a rest), Brahms none new (base = 11-12 main gathers, another tree).
**r6's two causes are gone:** notes lost to a neighbour-cell stem copy 8 -> 0; to a stem stitched across paper
5 -> 0 (runs bridging > 1 sp blank: 57 -> 1, 64 -> 2; filed page stems 623 -> 475, 748 -> 89).
**Sean's 12 r4 tile places now:** 3 and 11 recovered (eighths written); 1, 2, 4, 6, 8, 9, 10 right; **5** no
longer a wrong quarter but nothing is written (narrowed `beams_ambiguous`; its stem is still a stitched run
with ~0.44 sp of blank -- the head's BOX covers the gap, its ink does not: a lead); **7** still lost (EXPORT
`chord_value_undecided`); **12** still lost (bar-mates on page stems narrowed by the existing rule-8 guard).
**Notes written OFF and not ON, real losses:** Litolff 22 -> 18, Brahms 9 -> 15. By first cause (L / B): page
direction right, chord mate disagrees (EXPORT chord check) 7 / 3; filed page stem, reading changed 6 / 2;
the r7 no-stem guard 4 / 5 (+2 bar-mates); `beams_ambiguous` on a page stem 1 / 1; bar-mates - / 2.
**The r7 no-stem guard:** moves 14 (L) / 146 (B) heads decided -> narrowed, of which 7 / 140 are not real
notes (92 Brahms ones claimed by a barline); it removes 4 / 5 notes OFF wrote -- UNJUDGED (`6/0/1/10/6`,
`6/0/1/10/7`, `6/0/5/12/7`, `6/1/1/9/7`; `5/0/5/0/15`, `5/0/5/5/18`, `14/0/3/1/5`, `14/1/3/4/10`,
`14/1/9/7/7`); red bars with it 153 -> 152, 128 -> 124.
**Retire, re-measured** (old cell join removed for heads the page cannot stem): real heads losing a stem 259
(L; r1 266) and 66 (B; r1 76); red bars OFF / ON / retire 162 / 152 / 155 and 143 / 124 / 123; notes written
pre-retire and not with retire 27 (L, 28 gained) and 21 (B, 2 gained); right->wrong 0. **Stems cannot stand
alone yet**: the page reader still abstains on 259 / 66 real heads.
**The two owner filters would disagree** if both flags were on: 2.307's `owned_view` hides a copy's rows from
region queries, and r7's filter finds the heads naming a stem by exactly such a query -- it would find none
and treat the copy as the neighbour's stem again. One mechanism must replace the other before either lands.

## 2.306 stems round 9 (2026-11-14) -- two voices in one column: the upper head takes the up stem (lane 1dc2b5115; HANDED OVER, NOT MEASURED)

STAGED GATHER, flag `OMR_PAGE_STEMS` OFF. **Sean's r8 tiles** (answers-2.306-r8.json): 11 of 12 right under ON; tile 10 wrong -- Brahms p14 bar 14/1/9/5,
a correct blue dotted quarter became unread. **Cause** (traced on a page-14 replay of the r8 record): the bar is two voices sharing each chord (Sean "Yes"); the
second chord's heads /7 and /12 BOTH read `two_voices` on the same pair of strokes (up 3729 at the right, down 3687 at the left -- gaps 0.54 vs 1.75 sp and 0.63
vs 1.67 sp) and abstained, so the cell join hung both on the down stem, and the one-voice bar sum could not settle them. The per-voice bar sum (ROADMAP 2.308,
claimed) is NOT the fix: Sean "Wait" -- 2.308 waits for a real bar that needs it. **Rule** (Sean 2026-11-14 "Always when it is 2 voices. Obviously chords are not
always multiple voices. One of the voices may not have stems if it has rests."; DECISIONS + page-facts on main 15fae22f): `page_stems._two_voices_pairs` settles a
column only where exactly two heads each read `two_voices` on the same up/down pair -- upper head up, lower head down (`how` = `two_voices_upper_takes_up`);
anything else stays abstained. **Control** on the real tile-10 window (fixture `two_voices_p14`): /12 -> 3729 up, /7 -> 3687 down; with /12 removed /7 stays
abstained; the first chord (/0 reads its own stem) untouched. 18 of 18 stem tests pass.
**Measurement: gathers only.** Re-gather of the frozen pages with the flag on finished (`/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/2306-gather/2306-r9-lit.record.json`, `2306-r9-bra.record.json`;
slices `/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/2306-slices9`; tree `/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/2306-tree-r7` = pre-retire + lane 1dc2b5115); the lane report was STOPPED at handover (Sean 2026-11-14) -- no r9 numbers.
Next for whoever takes the lane: `lane_report --flag OMR_PAGE_STEMS --from adjudicate --replay-gathered --tag <slices9>` per plate (r9.sh in that scratch is the
recipe), then confirm tile 10's bar writes /7 /12 as dotted quarters plain. **Process lesson** (Sean: "Are we doing unnecessary long gathers?" -- yes): r8 and
r9 were narrow changes already proven by a real-tile test; a one- or two-page gather of the affected pages proves them in minutes. The full frozen sample runs
once per round, before tiles go to Sean or a landing is proposed -- never per small fix.

## 2.306 stems round 9, measured (2026-11-15) -- `lane-2.306-stems-beams-page` 4efc39032; built OFF; the retire blocker is unchanged

STAGED. Replays of the saved r9 gathers (frozen pages, flag ON, pre-retire); the ON arm reproduces the record.
**Gate, OFF vs ON:** Litolff red bars 162 -> 154 (r8 152), notes +51 -42, flags +20 -21, ties +6 -4, slurs
+18 -14, not written 2187 -> 2161. Brahms red bars 143 -> 123 (r8 124), notes +49 -23, rests +10 -26, ties
+14 -17, slurs +42 -20, not written 3089 -> 3063. Judged right->wrong 0, unwritten->wrong 0 on both. Stem and
duration tests flag ON 149 passed; check 229. (r9 touched only `page_stems.py` and its tests.)
**Sean's tiles as the file writes them now:** r8 set 12 of 12 right (tile 10's bar: /12 G3 and /7 E-flat 3,
dotted quarters, PLAIN, two voices; not red). r4 set 9 right, 0 wrong, 3 unwritten (5 narrowed
`beams_ambiguous`; 7 dropped by EXPORT's chord check; 12 narrowed `beam_discounted_uncertain`). None wrong.
`_two_voices_pairs` settles 10 columns (Litolff) / 13 (Brahms); heads still abstaining as two voices 309 / 82.
**The retire blocker, by reason.** Real heads 4,692 / 4,810; with no page stem 698 / 171; of those the old
cell join stems 350 / 86; retire takes away **259 / 66** (two-voice heads keep theirs) -- the same as r8:
- no free vertical at the head's stem side: **214 / 49** -- of which a vertical lies NEAR but not at the
  engraving side 201 / 35, and a vertical there is already claimed by an accidental, barline, clef, key or
  word 13 / 14. On three Litolff crops the stem is plainly in the print (two half notes with short up-stems
  inside the staff; a quarter whose down-stem stands by a barline) -- the lane's look, a lead only;
- two candidates 19 / 2; one stroke read both ways 14 / 11; stroke fused into the head 8 / 3; stroke held by
  its head end 4 / 1.
So the blocker is ONE cause, not "stems fused into heads" as the manager had guessed: a stem that stands in
the print and that the reader does not accept as standing at the head's side. Next: why.

## 2.306 stems round 10 (2026-11-15) -- why "no free vertical at the head's stem side"; measurement only (`lane-2.306-stems-beams-page` 495fefbb6)

STAGED. The page stem reader re-run offline from the r9 gathers; it reproduces the gathered answer for 175 of
the 201 Litolff heads and all 35 Brahms heads (the other 26 left out). For each head: the nearest page-map
vertical on the side the old join names, and the FIRST of the reader's three tests it fails.
**There is no single cause.** First failing test (Litolff 175 / Brahms 35): stem starts more than 2 sp from
the head centre 70 / 1; vertical more than 0.4 sp INSIDE the head-box edge 66 / 15; more than 0.4 sp OUTSIDE
it 31 / 17; does not reach 1.5 sp past the head 5 / 2; no vertical near 3 / 0.
- **A. Chord heads stacked against a mate (Litolff 64 of the 70).** One other head of the chord sits between
  this head and where the stem starts; in 69 of 70 the stem column is inked all the way through. The stem is
  printed and continuous; the reader measures the gap from this head's own centre and does not let a touching
  chord mate carry the stem to it. 61 down stems, 9 up. Past the limit: 30 within 0.25 sp, 23 more within
  0.5. The reader's own head-end test.
- **B. Narrow ovals on half notes (Brahms 16 of 17 "outside"; Litolff 13).** The 2.290 head oval is 0.65-0.95
  sp wide, narrower than the printed head, so the real stem stands 0.45-0.60 sp outside it, just past the 0.4
  limit. The head reader's oval -- the stem reader's INPUT.
- **C. Verticals inside the box edge (66 / 15): mixed.** 46 of the 66 use a detector box, not an oval; some
  boxes span an accidental or a second head; some are cause A again; 43 Litolff heads miss the x limit by
  0.1 sp or less.
The "engraving side" is measured from the BOX edge (the 2.290 oval, else the strongest detector box), never
from the head's ink edge locally -- against page-facts "measure locally". Half notes with short stems: a
vertical is there and the side test refuses it 20 / 16; the stem is merged into the head as one blob stroke
12 / 7; none is cut into pieces by staff lines.
**Lesson.** A side test measured from a box inherits every fault of the box (too narrow an oval, a box over
an accidental); 43 near-misses of 0.1 sp say the cut is measuring the box, not the note.
Not built. 12 blind tiles (out/print/2.306-r10) go to Sean first.

## 2.306 round 11 (2026-11-15) -- the stem is read by contact with the head's ink

STAGED, flag `OMR_PAGE_STEMS` OFF, branch `lane-2.306-stems-beams-page` tip 18146253a. 2.310 rule 1.
**Cause.** The reader judged a stem by distance from the head's BOX edge with a tolerance; the page map had
already measured which strokes touch which. **Lesson.** Use the contact the page map has measured instead of
re-measuring it with a tolerance.
**Built.** (B) A head the edge test left bare reads a stem where the stem's column touches the head's own ink;
side from the column against the middle of that ink; touching at the middle abstains (`contact_at_middle`,
margin kept). (A) One chord rule (Sean: "long stems that connect chords"): a head hangs on a stem when the
column runs to it through a chord head or bare stem, never through another stem's pieces. Controls from real
cases, each failing on the old reader first: r10 tiles 1,5,6,7,8,10,11 read in Sean's direction; 4 and 12
abstain; wide chords (Litolff p10, Brahms p4 four heads over 6.3 sp) on one stem; two voices end to end stay
two stems.
**Measured (OFF vs ON, one gather per plate).** Red bars Litolff 172 -> 166, Brahms 143 -> 123; judged
right->wrong 0 / 0. The OFF arm moved between the r9 and r11 gathers (Litolff 162 -> 172: OCR word claims vary
by gather), so only the within-gather pair is clean; the like-for-like r9 -> r11 file comparison is the
two-page gathers: +3 notes Litolff, none Brahms. Before retire the file hardly moves because the old cell join
already stems these heads.
**Retire blocker (real heads that would lose their stem): Litolff 259 -> 129, Brahms 66 -> 50.** Left, by
reason (Litolff / Brahms): a vertical near but none at the head's side 53 / 12; stroke held by an accidental,
barline, word, clef or key claim 17 / 14; two candidates 19 / 2; contact at the middle 14 / 7; stroke read
both ways 12 / 11; fused into inked heads 9 / 3; head end 4 / 1. Two-voice heads (91 / 20) keep the old join
and are not counted.
**Sean's 36 judged places as written now.** r4 9 right, 3 unwritten (5, 7, 12); r8 12 right; r10 9 right,
2 unwritten (2, 8), 1 wrong (tile 4, the tremolo slash, written as a note in BOTH arms: the detector boxed it
0.37 and the old join stems it). Tile 12 (part of a p) is no longer written with the flag ON.
**Open.** r10 tiles 2, 3, 9 still abstain (second vertical at the middle; stroke right of the head running
down; stem fused into the head's blob). A non-note can gain a stem by contact (Litolff p10
`glyph/10/0/0/10/11`, accidental-shaped box; not checked whether written). Fast tier flag ON 10,628 passed;
check 229. Twelve blind tiles on the r9 -> r11 file changes (6 gained, 6 lost, all Litolff; only 14 notes
change) in `out/print/2.306-r11`, sent to Sean.

## 2.306 round 12 (2026-11-16) -- why r11 lost right notes and gained fakes

STAGED, flag `OMR_PAGE_STEMS` OFF, branch tip 25c244dac. Sean's r11 tiles: 4 real gained, 2 fakes, 6 right
notes lost (answers-2.306-r11.json).
**Cause.** Of the 8 lost + 6 gained notes in the touched bars, 3 losses and 1 fake were NOT the reader: the r9
code and the r11 code write them identically on ONE gather of pages 2/4/9; the two full gathers differed (OCR
staff identity -> EXPORT `staff_not_identified`; pitch context). The rest: contact tipped a stroke the page
reads both ways (3 lost, FIXED); contact met a sharp through the sharp's own bar (1 fake, FIXED: a stem meets
its head at the head; a crossing bar or arc carries no contact); contact stems whose tip the beam readers then
misread (2 lost, not fixed -- downstream tip reading).
**Process lesson.** A loss or gain between two full gathers is not a change until re-run on one gather. And a
number from our own look gets a print check before it is a rule (the lane's "ink must connect the pieces" rule,
0.44 sp of blank, was withdrawn when a print showed the stem continuous under slanted beams).
**Tile 12 (piece of an f) is not a stem-reader effect**: both readers write it on one gather. The fact that says
"not a note" exists at GATHER (`holds_another_marks_ink`: a dynamic box stands on it) and nothing connects it;
it belongs to the head reader (`notehead_is_not_a_notehead`); connecting it would refuse 3 Litolff + 8 Brahms
written boxes, all unjudged. Not built. `glyph/10/0/0/10/11` (accidental-shaped) is written by the OFF arm too.
**Measured.** Red bars OFF -> ON Litolff 172 -> 166, Brahms 143 -> 123; judged right->wrong 0 / 0. The 48 judged
places: 34 right, 2 wrong (tremolo slash, the f -- both written by both arms), 12 unwritten. Retire blocker
Litolff 259 -> 129 -> 136, Brahms 66 -> 50 -> 55 (one trade: r11 tiles 7 and 11, real eighths, no longer
gained -- their chord mate's ink is a horizontal fused with a staff line). Fast tier flag ON 10,636 passed;
check 229. Six tiles on the r11 -> r12 changes in `out/print/2.306-r12` (4 are places Sean already answered).

## 2.306 round 14 (2026-11-16) -- stems, flags, beams judged right / wrong / unread on Sean's swept Brahms p0

STAGED, `OMR_PAGE_STEMS` (still OFF). Branch `lane-2.306-r14` tip 5e4204ba4 (code 643c25248, f6294cb47). Agent's report,
checked against the tree (export.py +97, page_stems.py +21, tests from real marks).

CAUSE: the 19 wrong flags and 20 fake beams on p0 are the same 20 notes, printed flagged and written beamed. The
duration reader had already decided "flag attached, no beam joined" on 19 of them; EXPORT `annotate_beams` regrouped
notes under any filed beam stroke by x alone (a slur, the next staff's beams in the padded cell). Not the stem reader.
PROCESS LESSON: the value existed and nothing read it -- a wire that re-derives a fact must read the decided one first.
Second cause: the page stem reader's own rule let a detector accidental box hold a stem (14 of 15 such refusals on
Brahms were real stems; on p0 the detector boxed an eighth's stem+flag as a flat at 0.35).

BUILT behind the flag: (1) a note whose stem carries a flag is written flagged, never beamed (Sean 2026-10-22), except
under a beam another note of the same voice is joined to; (2) an accidental's box never holds a vertical that runs out of it.

judge.py, Brahms p0, wrong / right / unread (OFF | base ON | r14 ON; each a re-adjudicated gather):
stem 5/359/16 | 4/367/9 | 4/367/9; flag 19/32/0 | 19/32/0 | 5/48/0; beam 22/161/2 | 22/163/0 | 4/163/0;
value 4/369/9 | 4/371/7 | 4/371/7. Judged answers right->wrong: 0 (Brahms 395, Litolff 373). Fast tier flag OFF
10,642 passed, 0 failed. Tiles `out/print/2.306-r14` (seed 2306014), NOT YET ANSWERED.

The 4 "wrong" stems are the scorer's (judge.py attaches a stem label to the wrong head / infers direction from side):
agent's crop look, not Sean's; judge.py not fixed yet. Open for Sean: one vertical joining a black head above to a
hollow dotted half below (3 unread). Still stops the cell join being removed: two-voice heads (301 Litolff / 79 Brahms
by the r13 study), the cell stem rows the tip/beam readers measure on, real stems the page refuses.
Red-bar reasons with the flag ON (p0 / Litolff p10): chord_value_undecided 2 / 2, beam_discounted_uncertain 7 / 13,
beams_ambiguous 2 / 3; the page stems settle only 2 of them -- these are tip and BEAM reading questions.
Litolff flag changes (3) and the accidental result rest on the agent's look. One page per plate.

### 2.306 r14, after Sean's tiles (2026-11-16)

Tiles: flag right on 1, 3, 4, 5, 6, 7, 12; new stems 9, 10, 11 right; tile 2 "quarter note" written a flagged eighth.
Cause of tile 2: `rhythm._attached_flags` took the flag of the note BEFORE (a flag box wholly left of this stem), over
the stem tip's own "no flag". Rule built (flag ON only): a flag hangs from its own stem's tip to the right; a flag
wholly left of a stem is never that stem's. One note changes on p0, none on Litolff p10. judge.py p0 flag ON:
value 4/371 -> 3/372, flag 5/48 -> 4/48; judged right->wrong 0; fast tier 10,643 passed, 0 failed. Tip 7cc8c1836.
Tile 8 (Litolff p10): one hook on the print by the agent's crop, detector class says 16th; not built until Sean
confirms one flag. Like cases 1 Brahms p0, 2 Litolff p10. q975: the agent sees a flag on a note Sean labelled a
quarter -- a question for Sean, not touched.

## 2.306 round 15 -- a stem joins the head whose ink it touches (2026-11-21; branch `lane-2.306-r15` c1c91cb36; STAGED GATHER, `OMR_PAGE_STEMS` OFF; touched pages only)

**Why this round** (2.317 step 0b, `out/print/2.317-step0b/`, a count from the 2026-11-21 frozen-sample
records plus an agent's crops the manager looked at): of 9,555 printed notes 251 are held for want of a
value; about 73 have no stem joined; 68 more are held because chord members disagree, and 56 of those are
mates never joined to a stem (2.330, withdrawn at the cause). Every join on the STAGED path decides by box
overlap or box position. The 224 "too narrow" boxes are mostly dots, rest pieces and barline slivers.

**Cause (lane's look at full-size pixels, not Sean's).** The page stem reader loses printed stems to what
other steps hand it: (1) claims made by area, not ink -- the Litolff p6 barline claim sits about a space
left of the real barline and covers the bar's last stem (3 stems); the Brahms p4 C-clef claim is a
rectangle reaching the next note's stem (2 heads); a boxed accidental holds one stem; (2) the head's ink is
not claimed -- about 500 of 1,700 kept Litolff heads claim none of their own ink (head plus stem stub is
too tall for the head claim; a stem fused with its flag gives no upright stroke); (3) hollow heads measured
too narrow -- on Brahms half notes the outline covers the left two-thirds of the ring, so the stem stands
half a space off the head (3 of Sean's p0 stems unread); (4) ties settled by box, not contact -- fixed here.
Process lesson: before blaming a reader, check whether an earlier claim or the head's own measurement left
its ink available.

**Built.** Two strokes on one side of a head: the one whose ink touches the head's ink is its stem; both or
neither stays undecided; one up and one down is two voices, never narrowed. A stroke read up by one box and
down by another goes to the heads whose ink it touches. "Touch" is the page map's own contact; no new
numbers. A stacked-chord pass (any head whose ink touches the stem joins it) was built and WITHDRAWN: the
reader already stems the 2.317 dotted chords, and the pass's only new joins were a slur end, an accent, an
f and Litolff rests. Controls from Sean's swept Brahms p0 staff 4 (heads 199, 249) fail with the page
map's contacts removed.

**Touched pages ON vs OFF** (Litolff 2, 6, 16; Brahms 0, 4, 5; shared lane_report, same tree and pages).
Litolff: notes +25 -33, red bars 77 -> 72, not written 928 -> 931, judged right->wrong 0. Brahms: notes
+25 -4, red bars 47 -> 39, not written 1166 -> 1145, judged right->wrong 0. Heads the page reader stems
and the cell join does not: 54 / 63. Heads the cell join stems and the page reader refuses: 50 -> 45 /
19 -> 15 (Litolff mostly not notes by the lane's look), plus 107 / 38 two-voice heads still at the unison
rule. Sean's swept p0: 359 -> 361 right, 0 wrong, unread 13 -> 11 (3 hollow-head, 8 two-voice). Control
line NOT met: the report's arms are not the gathers the change was diagnosed on.

**Sheet** `out/print/2.306-r15/sheet.png` (manager's look: the boxed strokes are stems, tile 7 unclear).

**Between us and removing the cell join.** Barline and clef claims take only their ink; the head claims
its ink when fused with a stem stub; the hollow-head outline covers the whole ring; chords whose stem is
read both ways; the two-voice heads. Not verified: frozen sample, fast tier, the Litolff -33 notes by kind.

## 2.306 round 16 -- one stem-hiding claim fixed, two causes placed in the code (2026-11-21; `lane-2.306-r15` 4f11e244b; `OMR_PAGE_STEMS` OFF; touched pages only)

**Process lesson.** Every stem-hiding claim looked at was placed by a box or a system-wide x, never checked
against this staff's own ink.

**Owed from r15.** The Litolff -33 notes: 23 traced, 16 looked at -- about 8 not notes or unclear; 2 honest
(OFF wrote a quarter with no stem; ON joins the stem and its beam doubt marks the value); the rest are real
notes the page reader stems with the same value in both arms, lost when the file is written, cause NOT
traced. The control: one ON gather re-judged twice (flag off, flag on) gives Litolff +22 / -33 against
r15's +25 / -33, so the difference is the flag, not gather variation.

**Cause 1, the head claims none of its ink (NOT fixed).** `stroke_map._split_thin_wide` folds a stem piece
shorter than half a space back into the head (`STEM_PART_MIN_SPACES`); the head's piece is then taller
than its outline and the 2.290 claim (half the piece inside the outline, `CLAIM_SHARE_MIN`) takes nothing.
On the six pages: Litolff 133 head-sized + 128 head-plus-stub pieces unclaimed, Brahms 144 + 23. A stem
fused to its flag yields no thin upright at all. The cut is shared by every reader.

**Cause 2, hollow-head outline (NOT fixed).** On Sean's p0 half notes the outline is 0.66 space wide, the
detector box 1.3; guess, unverified: `head_ink.trim_head` keeps head-height columns and the staff-line
erase removes the ring's arc on the right. 3 of his p0 stems unread. 2.327's code.

**Cause 3, claims by area.** Barline FIXED: the claim sat on the system's x with no tilt per staff
(Litolff p6: the printed barline runs up to a space off that x); now it moves to this staff's barline ink
where the old area holds none; 2 stems freed, 1 on p2 remains; real-pixel control from the p6 crop. C clef:
with the clef lane -- in print the viola's stem TOUCHES the clef's bowl, so joining by ink does not
separate them. A false accidental box over a stem holds 1.

**Three arms** (Litolff 2, 6, 16; Brahms 0, 4, 5). Main -> fixes with the flag off: identical files. Flag
off -> on: Litolff notes +25 -33, red bars 77 -> 72; Brahms +25 -4, 47 -> 39; judged right->wrong 0 and
unwritten->wrong 0. Still refused by the page reader and stemmed by the cell join: Litolff 45 (mostly not
notes), Brahms 15 (6 not notes; 3 hollow outline, 2 clef claim, 3 chords read both ways, 1 other).
Two-voice heads 124 / 38: page-facts settles them (a head with a stem each way is a unison); the page
reader would file both stems and the unison rule read them.

**Not removable yet.** The stroke-map cut, the hollow outline and the clef claim first; the Litolff
export-time losses need a cause.

## 2.306 rounds 17-18 -- the chord is where the stem join is undone (2026-11-21/22; `lane-2.306-r15` 7f115715a; `OMR_PAGE_STEMS` OFF; six touched pages, re-adjudicated from one gather per plate)

**Cause (r17).** The notes lost with the flag ON were not wrong stems. EXPORT groups heads into a chord by
box-centre x, and a box with no stem defaulted to a quarter: a real stemmed head in line with a box the
page reader refused (a beam junction, a rest, a smudge) made a chord whose values disagree, and the whole
chord went unwritten (15 heads on Litolff 2, 6, 16). With the flag off the cell join stemmed those boxes
too and wrote them. Lesson: a join decided by box geometry in one stage undoes the ink join made earlier.

**Built and kept (r18).** A box the page reader joins to no stem gets NO value (`no_stem_joined`,
`no_value_without_a_stem`; record controls 16/0/8/2/4, 6/1/3/6/2, 6/1/7/6/15, failing with the rule off).
Flag off -> on: red bars Litolff 77 -> 55, Brahms 47 -> 31; judged right->wrong, lost and
unwritten->wrong all 0 (of 248 / 225). The named chords 16/0/8/2/3, 6/1/3/6/4, 6/1/7/6/2 and Brahms
5/1/9/7 are written again. Of a seeded 12 among 51 newly held Litolff heads: 8 not notes, 4 real (2 head
outline set off from its ink, 1 stem read both ways, 1 unclear). With the flag OFF, 76 Litolff / 16
Brahms notes are written on boxes that stand on no stem; of 12 looked at, 10 not notes.

**Built and WITHDRAWN (r18).** Splitting an x-grouped chord by stem id: heads on two stems at one x were
set one after another in one voice -- Brahms 5/1/10/7's G3 written a beat before its chord-mates, a
rhythm error written plain. Judged right->wrong was 0 only because no judged mark sits there. LESSON: a
change that regroups or reorders notes needs a look at the written bar against the print; the judged
gate cannot see where no judged mark stands. Two stems at one x are two voices sounding together.

**The four mixed-value groups** (`out/print/2.306-r18-mixed/sheet.png`, with Sean 2026-11-21, unanswered):
Brahms 5/1/10/7 (a dot read on three heads, not on the low G); Litolff 2/0/7/4 (hollow top head under a
fermata, three black heads filled in as quarters by `chord_mate_shares_the_stem`); 6/1/8/11 (beam read
differently head to head, one black head decided a half, two tremolo-slash boxes in the group); 6/0/8/0
(three beamed eighths and a box below the staff that looks like the p). All held and marked, none shared.
Research the same day (`one stem, one value`, second-hand sources): mixed values on one stem occur on
string staves and in keyboard music, and dotted beside undotted in chords; hollow beside filled or
different flag counts on a wind staff is almost certainly a misread. Sean's recorded words (2026-10-09
"yes, one stem one value, no exceptions", on mostly wind tiles) were generalised by us to every stem.

**Causes placed, not built (handed to fresh lanes).** Hollow-head outline: `head_extent.ink_extent`,
`x0, x1 = max(x0, cols[0]), min(x1, cols[1] + 1.0)` -- `cols` is the widest ink run through the head's
centre column, which on a hollow head stops at the hole (Sean's p0 heads 85, 148, 328: 2230-2274 cut to
2234-2254). Stroke-map cut: `stroke_map._split_thin_wide` folds a thin part under half a space
(`STEM_PART_MIN_SPACES`) into the head. Two-voice heads: the page reader files both strokes, the unison
rule reads them, the writer places them at the same onset in two voices.

## Batch 2 measured twice, and what is wrong in bars both stem readers write (2026-11-22; `batch-2` 258cf8fce, `batch-2-r2` 86d0e6f3b; flags OFF on main; six touched pages)

**Batch 2** = `lane-2.306-r15` + hollow ring + fused heads (`OMR_STACK_TWO_HEADS`) + two-voice filing, later
+ `lane-strings-mixed` (`OMR_STRING_STOPS_OWN_VALUE`). OFF -> ON, r2: Litolff notes +22 -62, red bars
77 -> 55, not written 928 -> 966; Brahms +23 -16, 47 -> 31, 1164 -> 1157. Judged right->wrong, lost and
unwritten->wrong 0 on both. `judged_claims`: 2 new Litolff contradictions on Sean's slash tiles (2.276 r2
#8, 2.290 r1 #3). Sean's swept Brahms p0 stems wrong/right/unread 5/359/16 -> 4/370/6. NOT safe to turn
on: the print reading of 42 changed bars (an agent's reading) found ON wrong where OFF was right or
silent in 4 (tremolo slashes read as heads or stem; a slash written as a C5 head).

**Fixed in r2.** A note with two stem candidates: a stroke whose far end stops at another head is that
head's ring, not a stem (`page_stems.drop_outlines`; Litolff 2/1/0/13 flute C6 written). A detector
accidental box that holds a head's own oval no longer holds its stem (`page_stems.box_holds_a_head`;
Brahms 5/0/11/3; the flag is still under the flat box). Sean's Beethoven chord: lengths right with the
strings rule (half over three quarters, one chord), but a sharp fused with the barline is boxed as two
heads and written as an A-flat4 half ahead of it.

**Three readings were wrong and were corrected by a closer look** (all agents' looks, none Sean's):
Brahms 5/1/10/7 written F#5/A4 is RIGHT (the chord is tied over the barline; a tie carries its
accidental -- the first reader read the key signature and missed the ties); Litolff 2/1/3/14 is not a
unison but two hollow halves a third apart on one stem with a natural, so ON's one voice is right (OFF
took the natural's vertical for a stem) and both arms write ONE note for two (fused hollow rings); tile
40's "both wrong" was ON right. LESSON: a print reading by an agent is a place to look, not a verdict;
read ties into the bar.

**The both-wrong bars sorted by cause** (`out/print/both-wrong-triage/`: sheet, key, triage.txt; 14
bars from six pages chosen because the stem reader changed them -- small and biased, a pointer not a
rate). Differences in main's file, hidden = plain in an unmarked bar: heads boxed but never written 8
(3 hidden; e.g. Brahms cello tile 29, an unwritten F2 eighth and an unjoined flag cancel in the bar
sum); an accidental boxed as a notehead 7 (2 hidden; e.g. Litolff cello tile 16, a sharp written as a
plain E-flat3 quarter and the real F#3 pushed to beat 2 without its sharp); an accidental not applied
to its note 5 (1 hidden) -- often the same mark doing both; flag or beam not joined 3; dot wrong 3; a
rest missed under a clef change 1; a head invented from non-note ink 1. Worst: Sean's string chord
(tile 13), dropped from an unmarked bar with two invented notes.

**Also found.** Sean's third hollow half note on Brahms p0 (staff 4 bar 3, x ~2712): head and stem read;
the bar is red because `rhythm.adjudicate_dot_role` places the dot against the detector's box (0.80
space above its centre, limit 0.75) -- against the head's ink it is 0.56. Lane `lane-dot-by-ink`.

## A dropped head can hide: the bar sum is the only check (2026-11-22; main de589b6c4; frozen-sample gathers of 2026-11-21 re-adjudicated and re-exported; STAGED EXPORT)

**Cause.** EXPORT decides whether a bar adds up from the notes it WROTE (`export._part_xml` ->
`_bar_holds_out`). The list of refused heads that may be real notes (`cell.unplaced`, filed by
`_attach_unplaced`) is read only after a bar has already failed, and heads refused
`owned_by_another_staff` are never on it. So a bar that still adds up without the dropped head -- or
whose second error cancels the first -- is written plain. The bar sum can only confirm (CLAUDE.md
section 4); here it is the only witness.

**The 8 triage cases, by the step that drops the head** (record trace): `duration_narrowed` from
`beams_ambiguous` (Litolff flute, marked; Brahms cello sixteenths, marked), from no stem joined
(Litolff viola, HIDDEN: the half alone fills the bar), from `flag_ink_unread` (Brahms cello F2, HIDDEN:
the chord written a quarter cancels it); `chord_value_undecided` (Sean's Beethoven chord, effectively
hidden: the note invented from the sharp makes the sum pass; Brahms violin I, marked);
`unread_gap_in_partial_bar` (marked); one no longer reproduces.

**Whole sample, notes not boxes (a computation; hidden = plain in an unmarked bar).** All candidate
lost notes: Litolff 66 hidden of 265, Brahms 207 of 376. By reason, hidden/total: too narrow 25/57 and
127/167; clipped fragment 10/19 and 18/23; owned by another staff 4/7 and 13/25; duration narrowed
9/64 and 2/58; chord value undecided 2/30 and 0/26. An agent's look at 12 crops each
(`out/print/boxed-not-written/`): too narrow -- 1 to 3 of 12 may be real heads (the rest dots, barline
slivers, a rest); clipped fragment -- 0 of 12 real; owned by another staff -- 7 of 12 real printed
heads (mostly Brahms tremolo halves near a neighbouring staff), 5 with no written head anywhere near.

**The safeguard, priced.** "A bar holding a boxed, unwritten head that may be a real note is never
written plain": applied to every candidate it adds 56 + 22 bars on Litolff (red today 153) and 170 + 21
on Brahms (130); leaving out bars whose only candidates are too-narrow or clipped boxes, 23 + 12 and
50 + 4. `owned_by_another_staff` must come off the "not a gap" list.

## Matched pairs: a dropped real note beside a look-alike we write (2026-11-22; main + `lane-2.333` in bar mode; frozen-sample gathers of 2026-11-21; `out/print/matched-pairs/`)

Sean, on 28 tiles of boxed, unwritten marks: "it just looks very similar to other places where we're
getting the readings correct." So each dropped real note was paired with a written twin and the first
differing fact named. The 66 marked boxes are a computation; the piles, owners and twins are an agent's
look at full size.

**Two piles.** Litolff 27 real notes / 9 not (4 letters, 3 beams, a written neighbour, 1 unclear).
Brahms 11 real / 19 not (6 clef parts, 6 tremolo slashes, 2 key flats, 2 flags, a beam, a letter, a
slur). By reason, real/not: owned by another staff 10/2 and 9/16; value not read 12/3 and 2/1; chord
value not read 5/1.

**First difference from the twin.** (1) NO BOX ON THE STAFF THAT OWNS THE NOTE, 11 (Brahms 8, Litolff
3): e.g. Brahms p12, the low dotted head of a horn chord 4.5 spaces below its staff; the twin is the
head 3 spaces higher on the same stem. Where staves stand 5.3-6.3 spaces apart (under the 6.5 that
lets a bar's crop reach 6 spaces) each bar is cropped 4 spaces past its staff, so the head falls
outside the owner's crop and only the neighbour saw it. The ink is identical. (2) BEAM COUNT NOT
SETTLED, 8 (Litolff): e.g. p6 bars 87 and 89, four beamed eighths with a sharp before and a natural
inside, the sharps themselves written as quarter notes; a head touching a beam on a staff line; a beam
stub at the stem. (3) NO PITCH AFTER A FALSE CLEF CHANGE, 6: Litolff p4 system 1 staff 3 -- the
page-wide clef reader (2.324) read a cluster of heads and naturals at bar 3 as a C clef with no line
read; about 20 heads after it on that line have no pitch. (4) Sean's Beethoven string chord, 4. (5) The
box swallows the stem or no head ink is read, 5. (6) The owner's own copy refused, 2.

**The owner is right.** All 19 real "owned by another staff" notes went to the right staff; each was
unwritten because the owner had no box (11), its copy was refused (7 after the false clef, a stacked
duplicate, a slash) or clipped at the crop's edge (1). Sean ruled this on 2026-10-06 ("All note heads
should be found and written on their staff"; "Let's do them both": relocate-at-export, a head owned by
a staff holding no twin is written there, pitch via `move_glyph`) -- `OMR_RELOCATE_AT_EXPORT` exists and
is OFF. 16 of the 25 Brahms owned boxes are NOT notes, so a relocation needs a passed head test and a
ledger reading.

## 2026-11-23 -- batch 4: every built-OFF flag merged and measured once (STAGED; bar readings are the agent's, not Sean's)

Pages Litolff 2,6,16 / Brahms 0,4,5. A = default, B = all ON, C = all but the stem reader (`OMR_PAGE_STEMS`, `OMR_STACK_TWO_HEADS`, `OMR_STRING_STOPS_OWN_VALUE`).
- B vs A: red bars Litolff 76 -> 53, Brahms 41 -> 31; notes Litolff +20 -58, Brahms +13 -17; accidentals Litolff +34. Judged right->wrong 0. `judged_claims`: 2 NEW contradictions on Litolff, a stem standing on Sean's slash tiles (2.290 r1 #3, 2.276 r2 #8). Brahms p0 hand labels (wrong/right/unread): stems 5/359/16 -> 4/371/5. Agent print reading of 32 random bars: 16 right, 12 wrong in both, 3 wrong where A was right or silent (Litolff 2/0/3/5 an eighth dropped in a plain bar; Brahms 5/1/9/7 a low D4 written dotted in a plain bar; Brahms 5/1/11/6 a printed dot missed, blue); Litolff 16/0/1/14 drops a real note in a plain bar.
- C vs A: red bars Litolff 76 -> 71, Brahms 41 -> 41; accidentals Litolff +33; judged losses 0; new claim contradictions 0. Agent reading of 22 bars: 10 right, 9 both wrong, 1 wrong where A was silent (Litolff 6/1/8/11 the slash written as a C4 half); Beethoven bar 21 shrinks to one quarter. Which C flag causes these: not traced.
- With everything ON the old cell join still decides 297 of 2,533 Litolff heads and 423 of 2,781 Brahms heads, mostly heads the page stem reader never read (145 / 391).
- Per flag (agent's reading): `OMR_DOT_BY_HEAD_INK` gains a dot on Brahms p0 and loses no judged mark; `OMR_DROPPED_HEAD_MARKS=spot` adds 33 / 9 marks and changes no note; stem flags, `OMR_SLASH_STEM_CORE`, `OMR_ACCIDENTAL_FUSED_INK` not ready; `OMR_RELOCATE_AT_EXPORT` and `OMR_FOLD_FAR_BY_LEDGER` show no isolated effect on these pages. Flags were NOT measured one at a time.

## 2026-11-23 -- 2.337: `OMR_RELOCATE_AT_EXPORT` and `OMR_FOLD_FAR_BY_LEDGER` on every page where they act (STAGED EXPORT; direction is the agent's look, not judged)

Cause batch 4 saw nothing: the cases are rare. Finder: every page of both 20261122-night records exported ON and OFF from the night's verdicts; touched pages Litolff 5,7,8,10,11,12,14 / Brahms 8,12,14,15,19,23 measured with `lane_report --from adjudicate` (both arms reproduce the record). Relocate: Brahms notes +8 (the same 8 heads as the 11-22 lane, p12 x5, p14, p19 x2, each joining an owner chord at its onset, each unwritten OFF), dots +7, red 128 -> 128; Litolff notes +1 (p7 viola bar 55, a side effect of a renamed refusal; the bar stays red, its mark changes from unread to does-not-add-up: red 168 -> 169). Fold: Litolff 5 pitches take their printed natural (A-flat5 -> A5 x4, B-flat5 -> B5), blue +2 -6; Brahms one G6 blue -> G-flat6 plain, blue -4; red unchanged. Judged right->wrong 0 on both; no judged mark or hand label covers a changed note. Agent's look: relocate 8/8 Brahms right (p12 horn head counted by its four ledger lines), fold 6/6 pitch changes right, of 5 blue->plain 3 right and 2 cannot tell. Open either way: Brahms p8 bar 32 lower head E6 of a two-head chord unwritten. Sheets `out/print/2.337/`.

## 2026-11-23 -- 2.336: `OMR_ACCIDENTAL_FUSED_INK` run alone (Litolff 2 and 6, gathered; STAGED; `lane-2.336` 5e8e51f98, no code change)

Cause of the two batch-4 "bad bars": the flag alone does produce both, but writes nothing wrong of its own. It refuses a false head on accidental ink (as Sean's tiles ask); the bar was silent or wrong before, and a mark main already reads wrongly then gets written. Lesson: a bar that "goes wrong" beside a silent baseline needs every box traced on both arms before a flag is blamed. Litolff 6/1/8/11: the "C4 half" is the narrow right piece of the tremolo slash, which `tremolo_slash_crosses_stem` does not refuse (decided notehead with the flag off too) -- passed to lane 2.335. Beethoven bar 21 (2/0/7/4): the A-flat4 box on the natural is refused (0.511 of its ink held against 0.5); the C5 box beside it holds 0.488 and stays, and falls from a half to a quarter because it took its half from the stem shared with the refused box; Sean's real chord is read as heads and written by neither arm (the page stem reader wrote it in batch-4 arm B). Flag alone, Litolff 2 and 6: accidentals +27, pitches ~26, notes +3 -13, blue +25 -1, red bars 62 -> 58; judged right->wrong 0 over 241 tiles; `judged_claims` 0 new contradictions. 22 of the 27 gains are covered by no judged tile; agent's look at 12 random gains: an accidental stands left of the note on 10, 2 unclear. Brahms not run alone. Sheet: lane worktree `out/lane-report/2.336-alone/acc-gains/tiles/sheet.png`.

## 2026-11-23 -- 2.306 r19: the four batch-4 bad bars and the "never read" heads (`lane-2.306-r19` 04f08b315, flags OFF; STAGED)

Causes: none of the four came from the page reader's join rule. (a) Litolff 2/0/3/5: `stroke_map` gave 66 vertical strokes on Litolff p2 a staff space of 11.8 px where the bar's lines are 15.8 apart, so a printed up stem measured too far from its head; FIXED in the lane by measuring a stem in the staff space of its head's own bar (the stroke map's line fit itself is unfixed). (b) Litolff 16/0/1/14: stem ink fused with a slur end, boxed by the detector as a flat; not fixed; with `OMR_DROPPED_HEAD_MARKS=spot` the bar now shows "unread note". (c) Brahms 5/1/9/7: one-stem-one-value handed a dot down a string chord; FIXED: on a string staff a head with no dot printed beside it never takes a stem-mate's dot plain, the stem is held (also holds 5/1/10/2 and 5/1/10/4; three triple stops, two heads right and one wrong, now none written: notes -9). (d) Brahms 5/1/11/6: the dot has no box; the note stays blue with the dotted length as a candidate. Lesson: check the measurement a reader was handed (space, box, class) before blaming it; a census of "the old join still decides" must ask whether that decision reaches the file. REACH: the 145 / 391 never-read heads are copies filed with another staff or boxes refused as heads; 0 are written through the cell join. The real gap is the page reader abstaining on "two voices" (33 heads Litolff 2+16, 2 Brahms 5); in 12 one stroke is another head's ring or stem and the page now reads the other as the stem (4 are real-pixel controls). Flags ON new vs old tree: Litolff 2,16 notes +1 -3, red 30 -> 30; Brahms 5 notes -9, red 23 -> 24; judged right->wrong 0. Unproven: the narrowed outline rule not re-gathered; Litolff 16/0/4/10 lost half untraced; no frozen sample. Next round in flight (confirmation run, stroke-map space test).

## 2026-11-23 -- 2.306 r19 round 2: confirmation run and the stroke map's staff space (`lane-2.306-r19` bacb60b13, flags OFF; STAGED)

Confirmation, three stem flags OFF -> ON on the merged tree: Litolff 2,6,16 red 76 -> 54, notes +22 -63, not written 928 -> 967; Brahms 0,4,5 red 41 -> 32, notes +9 -22, not written 1152 -> 1167; judged right->wrong 0 (of 248 / 225); `judged_claims` 2 new on Litolff (a stem on Sean's slashes 2.276 r2 #8, 2.290 r1 #3 -- since ruled not a contradiction, page-facts 2026-11-23); Brahms p0 hand labels stems wrong/right/unread 5/360/15 -> 4/371/5. Bars plain and different ON vs OFF: 13 Litolff, 9 Brahms (sheets `out/print/2.306-r19/plain_diff_*.png` in the lane worktree); agent's look: about 15 right; wrong: Brahms 5/1/10/3 B written B-flat4 (the tie from the held 5/1/10/2 chord lost), Litolff 6/0/3/7 two voices on one set of heads written as one; doubtful: Litolff 16/0/1/6 (a slash written as a C5 half?), 6/0/5/9; tie lost Brahms 5/1/10/5. Not ready to switch on.
Causes: the three held Brahms triple stops each carry a dot-sized box the detector also called a notehead; refused as too narrow, it stays joined to the stem and the string-stop rule stands aside whenever another box stands on the stem (5/1/10/2, 5/1/10/4: dots read exactly as printed). 5/1/9/7: the D5's dot is refused `wedge_without_a_head` by `rhythm.adjudicate_dot_role` because the D5 is also boxed as a whole note. Holding a chord loses the tie and carried accidental in the NEXT bar: a hold must be followed into the bar its tie reaches. Litolff 16/0/4/10: one half note; its ring's right side rose 1.49 sp (stem test 1.5) and the old join wrote it twice as two voices; now once.
STROKE MAP STAFF SPACE (read-only): strokes more than 10% off their staff's line spacing -- Litolff p2 323 (system 0 staves 1, 3), Litolff p6 642 (system 0 staves 1-3, system 1 staff 10); none on Litolff p16 or Brahms 0,4,5. They read 11.7-12.4 px where the staff's recorded lines stand 15.75 apart, from the clef to the end of the line. `page_strokes.PageStaff` builds one `stroke_map.LocalStaff` per staff; a stroke's space is the spread of that fit at the stroke. Re-running the fit from the RECORDED lines does not drift, so the lines handed in at gather probably differ (unconfirmed). Readers of that space: stems, beams, head claims, accidental ink, claim names, ink attachment, arc claims, stroke owner, flag/beam levels. ROADMAP 2.342.

## 2026-11-23 -- 2.306 r19 round 3 (`lane-2.306-r19` 06aa218dc, flags OFF; STAGED)

Fixed: (1) the three Brahms triple stops -- a box refused as too narrow (the dot also boxed as a notehead) no longer counts as standing on the stem for the string-stop rule (a refused tremolo slash still does); 5/1/10/2 and 5/1/10/4 written whole (top two dotted, bottom without a dot, blue), 5/1/10/3 back to B natural with its ties, 5/1/10/5 ties back. (2) Litolff 6/0/3/7: the lane's own outline rule took unison down stems 3.4-3.9 sp long for another note's ring; a ring's side reaches at most 2 sp past its head. Found, not fixed: EXPORT `export._record_tie_spans` skips any tie whose start note was not written, so the tied-to note loses its tie and carried accidental and is written PLAIN (should be marked). Brahms 5/1/9/7: `rhythm.adjudicate_dot_role` matches a dot against raw boxes, not the one head 2.290 `page_heads.OneHeads` folds two boxes into, so it refuses `wedge_without_a_head`. Litolff 16/0/1/6: a tremolo slash boxed as a filled notehead never refused, written a C5 half; not cured by lane-2.335. 6/0/5/9 looks right. ON vs OFF now leaves 17 bars plain and different (12 Litolff, 5 Brahms; sheets `out/print/2.306-r19/`); against switching on: 16/0/1/6; 6/0/1/12 an F#5 half written F5; LOST TIES at Brahms 5/0/1/0 and 5/0/11/6 that appeared after merging main's defaults switched on today (untraced -- may be a regression from one of today's six switches); the `_record_tie_spans` drop. Judged right->wrong 0.

## 2026-11-23 -- 2.342 built OFF (`lane-2.342` dc2fb0257, `OMR_STROKE_SPACE_OWN_STAFF`, STAGED GATHER)

Cause (reproduced offline on Litolff p2 at 600 dpi from the recorded lines 549/565/581/596/612; the lines handed in were fine): `stroke_map.LocalStaff` walks along the staff starting from the staff-wide average rows (on a tilted staff about 0.4 sp off at the left end, the edge of its window); its first windows fell inside the treble clef, where one column passed with lines 4 and 5 run together 2.4 px apart (spread 12 px against 15.75); that column seeded the next, no later column could match five separate lines (3 readings of 49 on p2 staff 1), and `lines_at` held the clef reading flat to the right end. Nothing compared a reading to the staff's own spacing. Lesson: the walk was written for one bar (2.195); moving it to the whole page (2.260a M2, 2026-11-03) let one bad clef column spoil a whole staff -- a walk where each step starts from the last needs a check on every step. Spread (20261122-night records): Litolff 6,416 of 59,311 strokes more than 10% off, 46 of 331 staves, 12 of 16 pages; Brahms 1,021 of 146,067, 8 staves, pages 2, 7, 9, 20; plus staves with right spacing but lines stuck up to 15-19 px off (Litolff p16 staves 0-3, p2 staves 2, 7, 21). Fix: a column's five lines are accepted only at the staff's own spacing (every gap within 0.5 of one recorded space, height within 15%; columns the old walk read well: 99% within 6%, worst 13%); if the walk fails the five recorded lines move together, at most 0.75 sp, to the ink; never two lines read as one, never a clef or brace column as a seed. OFF = identical to main on 145 staves; ON moves line positions on 33 of 145. Control from the real page (fails OFF). Gathered ON vs OFF: Litolff 2, 6, 16 off strokes 964 -> 0, gathered facts moved, EXPORTED FILE UNCHANGED, judged right->wrong 0, red 65 -> 65; Brahms 7, 20 off strokes 970 -> 144 (the rest on 7/0/5 whose recorded lines are ~10% short of the print), 68 gains on 7/0/7 are an OCR artifact between arms (Tesseract fallback vs Surya), judged right->wrong 0. Not proven: the effect with the stem readers ON; the whole movement.

## 2026-11-23 -- the two "lost ties" on Brahms p5 (5/0/1/0, 5/0/11/6): not reproduced at default flags

Re-adjudicated and exported the stem lane's default-flags Brahms record with all six of today's first switches forced off, then on: the same 197 tie-bearing notes on page 5 in both; 5/0/1/0 F5 quarter keeps its tie stop, 5/0/11/6 F3 quarter its tie start. So no switch acting from ADJUDICATE on drops them. Not covered: `OMR_ACCIDENTAL_FUSED_INK` at GATHER (the record predates it), and the stem lane's own arm -- its list was stem flags ON against OFF, so the loss most likely belongs to the stem reader's ON arm, to be checked in that lane before it is switched on.

## 2026-11-24 -- 2.306 r20 (round 4): the three faults left at r19, re-checked on main with the staff-spacing fix (`lane-2.306-r20`; stem flags OFF; STAGED)

**Cause and process lesson.** Of the three faults r19 left against switching the reader on, NONE is the stem reader's. (1) Litolff 6/0/1/12 (F#5 half written F5) is written wrong by main too: the sharp belongs to one of two boxes the detector drew on the one head, EXPORT writes the other box, and the in-bar carry skips it because it stands at the same x, not to the right -- a decision made on a BOX, read back on a different box of the same NOTE. The stem reader only made it visible: the old cell join read two stems there and marked the bar. (2) Brahms 5/0/1/0 and (3) 5/0/11/6 "lost ties" were a comparison fault: r19 round 3 set an OFF arm gathered on pages 0,4,5 (the r19 confirmation run, pre-merge tree) against an ON arm gathered on pages 0,5 on the merged tree. 5/0/1/0's tie comes from the last bar of page 4 -- it cannot exist in a file without page 4; with page 4 loaded both arms write it (r19 confirmation run, both arms). 5/0/11/6's arc runs to an F#3 (the sharp is printed; our look at the crop): different pitch, so not a tie (page-facts, Sean 2026-10-29); the old OFF "tie" read F3 because the sharp was not read before `OMR_ACCIDENTAL_FUSED_INK` went on (11-23). On the merged tree both arms read F#3 and write no tie. LESSONS: compare arms that loaded the SAME pages (lane_report checks the tree and the flags, not the page set of an arm borrowed from another run); and a fault seen "only with the flag on" must be checked in the flag-off file on the same tree before it is blamed on the flag -- here the flag had only removed the red mark that hid a wrong main already writes.

**Fixed at the source (flag `OMR_ACCIDENTAL_ON_THE_MARK`, default OFF; STAGED EVALUATE `consequences.apply_printed_accidental` + `_boxes_of_the_same_head`).** An accidental belongs to the note it stands before, whichever box the detector read that note with: the printed accidental is written on every box of the head's own one-head mark (2.290 `page_head` group), own staff, same pitch. Never another staff's view of the ink, never a group another identity made, never a box of another pitch. Control from the REAL record rows of 6/0/1/12 (`tools/omr/tests/test_accidental_on_the_mark_2_306_r20.py`, fixture cut from this round's gather), failing with the flag off. Measured alone (Litolff p6, gathered OFF vs ON): accidentals +3, pitches ~2, blue +2, red bars 38 -> 38, judged right->wrong 0. The three: 6/0/1/12 F#5 (blue: the sharp is read from its own ink), 6/0/0/12 A5 with its printed natural, 6/1/8/11 F#5 -- the last is Sean's r18 mixed tile 3 ("a couple of accidentals, a sharp and a n[atural]", 2026-11-21). Found, not ours: Brahms 5/0/11/6 -> 7, the arc to the F#3 is written as neither tie nor slur in either arm (arc lane 2.338).

**Touched pages, stem flags OFF -> ON on the merged tree** (`lane_report`, Litolff 6 + Brahms 5, context pages 1 / 0): Litolff notes +10 -28, red bars 38 -> 21, not written 408 -> 427; Brahms notes +6 -8, red 23 -> 18, not written 730 -> 731; judged right->wrong 0, unwritten->wrong 0 (194 / 222 tiles). Brahms "clefs -25, keys -25, meters +2 -12": restatements only -- system 5/0's meter is decided 6/8 from the bars ON (abstained `meter_return_not_read` OFF), so no attributes block is re-emitted; no clef, key or meter changes value. Bars plain and different ON vs OFF: Litolff 7 (p1 context 3, p6 4), Brahms 2 (0/0/11/1-2: two voices on one staff, stems up and down, written as two voices ON and as chords OFF -- ON right by our look).

**The full frozen sample, once, at the end of the round** (`lane_report`, merged tree incl. main 2.343, OFF = defaults, ON = `OMR_PAGE_STEMS` + `OMR_STACK_TWO_HEADS` + `OMR_STRING_STOPS_OWN_VALUE` + `OMR_ACCIDENTAL_ON_THE_MARK`; both arms re-gathered, cells from the master map; 3 h 52 min):
- Litolff 2,4,6,8,9,10,11,16: notes +53 -105, rests +2 -5, accidentals +13 -9, flags +22 -30, beams +52 -23 ~16, ties +6 -12, slurs +7 -13, values ~30, pitches ~8, blue +47 -78; red bars 125 -> 97; not written 2077 -> 2131.
- Brahms 0,4,5,8,12,14,19,25: notes +18 -49, rests +2 -18, dots +9 -28, flags +12 -4, ties +10 -11, slurs +30 -13, values ~15, pitches ~6, blue +57 -40; red bars 111 -> 81; not written 2968 -> 3000.
- Judged: right->wrong 0 and unwritten->wrong 0 on both (308 / 261 tiles); Litolff unwritten->right 1. `judged score` TOTAL right/wrong Litolff 134/10 -> 135/10, Brahms 88/3 -> 88/2. `judged_claims` contradictions: Litolff 8 -> 8, Brahms 4 -> 4, the same tiles in both arms (0 new); Brahms 2.288 r2 #3 (Sean: "a stem") is now claimed as a stem ON (50%, beside a beam claim) where OFF had no stem claim.
- 5/0/1/0 with page 4 loaded: tie stop written in BOTH arms (fault 2 closed). 6/0/1/12: F#5 half, blue, ON (fault 1 closed by the accidental rule; OFF still writes F5 plain).
- Bars plain and different ON vs OFF: Litolff 29 (incl. 3 on context page 1), Brahms 22 (`scratchpad` lists; no tiles cut). Our look at a handful (crops, nothing drawn; an agent's reading, not Sean's): right ON -- Litolff 8/1/0/2 (OFF's C6 was a slur end and a ledger, `no_head_ink`), 6/1/6/2 (one quarter, one rest), 6/0/1/12; Brahms 0/0/11/1-2 and 4/1/2/0 (two voices / one chord as printed). WRONG ON, plain, both NEW causes found this round and NOT fixed:
  - Brahms 25/1/7/1 (and 7/0): a printed tie G5 -> G5 lost. A 7x17 px box at the barline (`noteheadBlackInSpace`, the identity read no head ink; ADJUDICATE refuses it `claimed_by:barline`, share 1.0) is given a page stem at GATHER (stroke 2093, x_frac 1.86 -- right of the box); ADJUDICATE `Q.VOICES` then counts it as a second voice (`two_voices_same_beat`, voices [[10], [0, 1, 13]]); EXPORT writes the bar in one voice but `_voice_of_notehead` keeps the verdict's numbering, so `_record_tie_spans` refuses the written tie `tie_ends_in_two_voices`. Causes, in order: the page reader stems ink an earlier page claim (the barline) holds whole -- a later reader may mark claimed ink, never take it; `Q.VOICES` counts a box already refused as a note; the arc voice map is not the voice the file writes.
  - Brahms 8/0/1/8: printed F5 / Bb4 dotted quarters (stems up / down), then Eb5 / Cb5 dotted quarters (up / down). ON stems all four right, but the Cb5's down-stem tip reads a hook (`hooks_counted`, a dotted eighth: the slur under the chord passes the stem tip) and EXPORT writes the Bb4 in both voices. The stem-tip hook reading on a page-stem row does not ask whether the arc already claimed that ink.
- Not looked at: the other ~40 plain-and-different bars; Litolff 8/1/10/3-4 A-flat2 -> A2 (a natural applied by the accidental rule? not traced).

**What is left before the reader could be switched on:** the two new causes above (GATHER: a page stem never on a box whose ink another page claim holds whole; the stem-tip hook reader must not read arc-claimed ink), each with a real-pixel control; a print reading of the ~50 plain-and-different bars of the full sample (or tiles where we cannot tell); then the retire step (the cell join removed, Sean 11-13). `OMR_ACCIDENTAL_ON_THE_MARK` is independent of the stem reader and could be measured for switching on alone (Litolff p6: 3 accidentals, all right).
- Fast tier on the merged tree (flags at default): 11,334 passed, 3 failed -- all three this lane's paperwork (the new flag's doc row, the data-flow page), fixed in 768136e7a and re-run green. Process note: the round-3 OFF arm of r19 was borrowed from another run with a different page set; borrow an arm only through `--baseline shared`, which checks the pages.

## 2026-11-24 -- 2.306 r21: the two bars r20 found written wrong and plain, fixed at their source (`lane-2.306-r21`; stem flags OFF; STAGED)

**Cause and process lesson.** Both faults were a later reader taking ink that belongs to a mark read first -- but r20's one-line causes were each half right, and the crops corrected them before any code. (1) Brahms 25/1/7/1: the stroke the page stem reader gave the 7x17 px box on the barline is NOT barline ink; it is the left upright of the NATURAL that opens the next bar (page stroke 2093, `b25` crop `out/print/2.306-r21/brahms-25-1-7-1-barline.png`). The box itself holds no head ink (2.290 identity `no_head_ink`, ADJUDICATE refuses it `claimed_by:barline`), so the true fault is "a stem joined to a box that has no head of its own" -- a stem joins a head whose ink it touches, and there was no head ink to touch. (2) Brahms 8/0/1/8: the "slur passing the Cb5's stem tip" is a slur that STARTS at that stem (page arc run 124 begins 4 px right of the stem and runs 4.9 spaces on); no detector box was drawn on it, and the page arcs are read AFTER the stems (gather order: `gather_page_stems` before `gather_page_arcs`), so the tip reader could not leave the arc's ink out -- the 2.306 r7 lesson again: connected at ADJUDICATE. The Bb4 "in both voices" is not a second cause: the wrong eighth makes the bar's two streams unequal, the 2.90 divisi settle takes the stem directions off the bar, the F5 (up) and Bb4 (down) fuse into one chord, and the 2.323 unison rule hands the chord's lower note to voice 2 as a NOT-PRINTED copy (`print-object="no"`). With the Cb5 at its printed value (what-if on the r20 record) the bar is written F5/Eb5 voice 1, Bb4/Cb5 voice 2, nothing doubled. LESSON: a cause written from the record rows alone named the wrong stroke twice in one round; a 600-dpi crop of the stroke ids is a minute's work and goes before the rule is worded.

**Fix 1 (STAGED GATHER, inside `OMR_PAGE_STEMS`; `page_stems.stands_on_a_barline` / `barline_boxes`).** A box on a barline with no head ink of its own is the barline: it takes no stem and takes no part in the page's stem reading (reading word `barline_not_a_head`). "On a barline" is measured on the rule's own carved ink (its tilted centre line and measured width cover at least half the box's width at the box's rows, the register's 0.5 cut). Never: a head WITH its own ink on or beside a barline; a box off the rule. Reach on the r20 frozen sample (ON gathers): exactly one head, 25/1/7/1/10, on either plate.
**Fix 2 (STAGED ADJUDICATE, new flag `OMR_HOOK_NOT_ON_AN_ARC`, default OFF; `rhythm.arc_through_hook_window` / `_hooks_on_arcs`).** A flag hangs from the stem's free tip on the right and ends beside it; a slur that starts at the stem leaves it on the same side but runs on. A hook the tip reader counted where a page arc (`Q.PAGE_ARC`) STARTS inside the hook's window and runs at least one space past it is the slur's first stretch: the tip becomes disputed and the duration NARROWS between the head's value and the flagged one (reason `tip_hook_is_an_arc`, equal support), never decided. Never for an arc that comes in from the stem's other side or only passes by: the first wording ("an arc passes through the window") took a real eighth's flag at Brahms 25/1/8/3 (a slur from the left ends at that stem and the arc reader ran on down the flag) -- found on the p8+p25 re-adjudication, narrowed before any gather. Reach (r20 ON records, re-adjudicated with and without): Litolff file byte-identical; Brahms one head, 8/0/1/8/4. Main's OFF arm does not have the fault AT THIS BAR (its cell join puts the Cb5 on the Eb5's up stem, whose top tip is clean); the hook came through the 2.18c path (`none_over_this_note`), not 2.341's `OMR_STEM_TIP_FLAG_WHEN_DECLINED` branch. The rule sits at ADJUDICATE, so it covers either stem reader.
**Controls** (`tools/omr/tests/test_page_stems_2_306_r21.py`, fixture `fixtures/page_stems_2_306_r21.json` = verbatim rows of the r20 Brahms ON gather): the barline box, its stroke 2093, barline 6715 and the real G#5 beside it (r20's `read` stems the box -- the fault reproduced; the new selection drops it and the G#5 keeps stroke 1822; the same box with ink, or moved off the rule, is read as before); the Cb5's real tip row with arc runs 116/124 (hit on 124), the 25/1/8/3 eighth's real tip row with its arc (no hit), a shortened arc (no hit). Each new-rule test fails on r20's code.
**Second link, the tie check's voice numbering (EXPORT `_voice_of_notehead`).** It is a value computed two ways: its `Q.VOICES` branch numbers notes straight from the verdict, while the writer (`_recorded_voice_split`) refuses a split whose stream has no written note and writes one voice. Harmless at 25/1/7/1 once the barline box has no stem (the verdict is one voice). Not built: aligning it with the writer on the r20 sample changes exactly two ties, both arms -- gains the printed Eb5 tie Brahms 8/0/5/7 -> 8/0/5/8, loses the printed Eb4 tie 8/0/5/8 -> 8/0/5/9 (written today from a one-voice bar into voice 2 of a split bar; `out/print/2.306-r21/brahms-8-0-5-7to9-ties.png`). The right fix is "a tie may run from a one-voice bar into either voice of the next", its own small EXPORT item, not a guard here.

**Touched pages** (Brahms 8, 25, context 0; both arms gathered on this tree, `LANE_REPORT_SAMPLE` development control): notes +4 -7, ties +2, red bars 42 -> 33; judged right->wrong 0 (214 tiles). 25/1/7/1 G5 tie stop written ON; 8/0/1/8 ON is RED (Cb5 narrowed, not written; Bb4 no longer doubled) -- marked, not invented. The bar did not settle to blue: left for the bar-sum reconciliation, not this lane. Plain-and-different ON vs OFF: 10 bars, none wrong by our look.

**The full frozen sample, once** (merged tree, OFF = defaults, ON = `OMR_PAGE_STEMS` + `OMR_STACK_TWO_HEADS` + `OMR_STRING_STOPS_OWN_VALUE` + `OMR_ACCIDENTAL_ON_THE_MARK` + `OMR_HOOK_NOT_ON_AN_ARC`; both arms re-gathered; 3 h 57 min):
- Litolff 2,4,6,8,9,10,11,16: both arms' files byte-identical to r20's: notes +53 -105, rests +2 -5, accidentals +13 -9, flags +22 -30, beams +52 -23 ~16, ties +6 -12, slurs +7 -13, values ~30, pitches ~8, blue +47 -78; red bars 125 -> 97; not written 2077 -> 2131.
- Brahms 0,4,5,8,12,14,19,25: notes +18 -50, rests +2 -18, accidentals +6 -5, dots +9 -29, flags +11 -4, beams +4 -3 ~3, ties +10 -9, slurs +30 -13, values ~14, pitches ~6, blue +57 -40; red bars 111 -> 81; not written 2968 -> 3001 (r20: ties +10 -11, flags +12, notes -49).
- Judged: right->wrong 0 and unwritten->wrong 0 on both (308 / 261 tiles). `judged_claims`: Brahms 4 contradictions in ON, the same four tiles as r20 (0 new); Litolff files unchanged from r20 (8, same tiles, 0 new).
- Plain-and-different ON vs OFF: Litolff 29 (same list as r20), Brahms 20 (r20's 22 less 25/1/7/1 and 8/0/1/8).

**Print reading of the plain-and-different bars** (r20's sample output; crops from the print, nothing drawn; AN AGENT'S LOOK, not Sean's). Litolff 29: right 23, wrong 3, cannot tell 3 (4/1/9/5; P12 m19 and m267 carry no place). Brahms 22 (incl. the two fixed): right 18, wrong 2 (the two fixed here), cannot tell 2 (4/1/2/3, 8/0/1/9). Wrong, NOT fixed (new causes, listed only):
  - Litolff 1/0/9/6 (context page 1): an eighth rest boxed `noteheadBlackOnLine` (glyph 6) written as a D4 eighth, plain (OFF: D4 half, red). `out/print/2.306-r21/litolff-1-0-9-6.png`.
  - Litolff 10/1/2/0: Cl. F4/A4 half notes on ONE up stem written as two voices (F4 voice 1, A4 voice 2). The page reader took the stacked hollow heads' left ring sides (page stroke 404, 2.3 spaces) for a down stem (`two_voices_upper_takes_up`); the r19 ring-side bound (2 sp past ONE head) does not cover two stacked rings. `out/print/2.306-r21/litolff-10-1-2-0.png`. The printed ties to the next bar are missing in both arms.
  - Litolff 2/0/10/2: the C3 under the staff is a black quarter (stem down, then a quarter rest) written a HALF, plain (both arms half; OFF red). It is a stem-end head read from a `restWhole` box, fill read hollow (`hollow_head_bare_stem`, rows share 0.32) where a staff line crosses it. `out/print/2.306-r21/litolff-2-0-10-2.png`.
- Litolff 8/1/10/3-4 (A-flat2 written A2): traced -- a NATURAL is printed before the half note; ON's A2 is right, tied into 8/1/10/4; OFF's A-flat2 is the error. The `OMR_ACCIDENTAL_ON_THE_MARK` rule put the printed natural on the box EXPORT writes.
- Seen in passing, both arms: Brahms 14/1/9/3 the printed sharps on the second chord are written A-flat4/F4; Litolff 16/1/10/0 and 6/0/5/9 a lower-note tie missing.
- Found, not built: a page stem VIEW's tip is read with no head boxes and no blockers (`page_stems._cell_row_for` passes `()`), while the cell reader's is given both -- so the window runs into the head; its docstring says the view is read "as the cell reader's are". Worth a measured look before the reader is switched on (Brahms flags +11 ON).

**What still stands before the reader can be switched on:** the three Litolff wrongs above (rest boxed as a head and stemmed; stacked hollow rings read as a down stem; a stem-end head's fill), the tip-view parity gap, and the retire step (the cell join removed, Sean 11-13 -- today a page abstention still falls back to the cell join in `stem_value._page_stem_join`). `OMR_HOOK_NOT_ON_AN_ARC` is independent of the stem reader (ADJUDICATE) and could be measured alone. Fast tier on this tree: 11,342 passed, 5 failed -- all this lane's paperwork (the inventory's helper depth for the new `Q.PAGE_ARC` read, the ink-rules and data-flow pages), fixed in 685d13243 and those tests re-run green.

## 2026-11-25 -- 2.306 r22: the three Litolff wrongs r21's print read found, the page view's tip, and what still falls to the old join (`lane-2.306-r22`; stem flags OFF; STAGED)

**Cause and process lesson.** The three bars had three different owners, and only one was a page stem rule. (1) Litolff 10/1/2/0 (F4/A4 halves on one up stem written as two voices): the detector drew ONE tall box over the dyad and its stem; GATHER read it for the two heads inside it (2.252) and ADJUDICATE refuses it as the remainder -- but the page stem reader took it as a THIRD head. It paired with the A4 as "two voices in one column" (r9), and the pair handed the A4 page stroke 404 for a down stem. The 600-dpi stroke crop (`out/print/2.306-r22/litolff-10-1-2-0-strokes.png`) shows 404 is the two rings' left sides, from the top of the A4's ring to the bottom of the F4's; the r19 ring-side rule already refuses it once the remainder is out. Cause: one chord's ink counted twice. (2) Litolff 2/0/10/2 (a black quarter C3 written a half) is not the stem reader's: both arms write it. (3) Litolff 1/0/9/6 (an eighth rest boxed as a notehead, written a D4 eighth): the page reader rightly gave the rest no stem, but the DURATION reader still attached stems by box overlap (`_stem_joined`), so the rest took the next eighth's stem and EVALUATE shared the eighth's value with it as a chord mate. The page's reading had been connected to `own_stems` but not to `attached`, which the flag reader and the chord grouping read. LESSONS: before blaming a reader for a stroke, ask what it was handed as heads (here a box another reader had already resolved); and when a new reader replaces a join, find EVERY consumer of the old one (`own_stems` and `attached` were two copies of one answer).

**Fix 1 (STAGED GATHER, inside `OMR_PAGE_STEMS`; `page_stems.tall_remainders`, reading word `box_read_for_its_heads`).** A box the head reader already read for the heads inside it (a dyad of halves boxed as one) IS those heads, not one more: it takes no stem and no part in the page's stem reading. Never drops a box that is a head of its own (a box not read for heads, or a head the tall box was read into). Reach (r21 full-sample ON gathers): 18 Litolff remainders had a page stem, 3 through the two-voice pair rule; 0 Brahms. Control from the real rows (`tools/omr/tests/test_page_stems_2_306_r22.py`, fixture `fixtures/page_stems_2_306_r22.json` cut from the r21 Litolff ON gather): r21's call reproduces the fault (A4 -> stroke 404 down, `two_voices_upper_takes_up`); with the remainder out both heads stand on the up stem 524 and 404 is no stem.
**Fix 3 (STAGED ADJUDICATE, inside `OMR_PAGE_STEMS`; `rhythm.stems_the_head_stands_on`).** Where the page read a head, the stems it stands on -- the ones its flags hang from and the ones EVALUATE groups a chord by -- are the page's (its one stem, both voices' stems, or none); the box overlap only where the page has no reading. A head the page joined to no stem stands on none: never a neighbour's stem met only by box overlap. Control from the real rows: r21's box join puts the rest on the eighth's stem row obs:011488; the new call gives []; flag off unchanged. 2.334 (`OMR_REST_BOXED_AS_OTHER`) could not have caught it: it steps aside only for accidental- and clef-class boxes, and no unboxed-rest shape row exists for this ink. The rest boxed as a NOTEHEAD is the detector's and `notehead_is_not_a_notehead`'s (never refused; `notehead_is_a_whole_rest` asks only about whole rests) -- listed, not built.
**Fix 4 (STAGED GATHER, inside `OMR_PAGE_STEMS`; `gather.stem_tip_context`, the one shared place).** A page-supplied stem's tip is read with the blockers (the cell's beam strokes and the detector's other boxes) and the head boxes the cell reader's stems get; `gather_cv_lines` now calls the same function (unchanged for the cell reader). Measured on Litolff p2+p10 (r22 touched gather vs r21's): of 16 "hook found" reads on page views, 13 were the view's OWN HEAD END (now `occupied/head_at_this_end`). Wiring control (fails on r21's `()`); no real-pixel control of the tip itself (no cell raster in the fixture) -- its effect is in the full-sample numbers and print read below. Not given to views yet: the tremolo-slash blanking (`_observe_stem_slashes`) and the stroke's true edges (2.206d).
**Item 2, found and NOT fixed (not the stem reader's).** The fill is decided by `adjudicate_duration`'s 2.70 rule (`hollow_head_bare_stem`) from the 2.23 window reading (`Q.NOTEHEAD_INK`) on the DETECTOR BOX. The box came from the stem-end head rescue (`yolo_rescue_stem_head`, read from a `restWhole` box): 2.74 spaces wide, from the barline's ink to the head's right edge (`out/print/2.306-r22/litolff-2-0-10-2-strokes.png`). Its centre window sits on the paper between the barline and the stem, crossed by staff lines (0.55); its ring holds the barline and the head (0.83) -- "hollow". The head's own trimmed ink (`Q.HEAD_INK`) reads FILLED, as did the rescue's own ink read; the 2.70 rule's "one head box" checks height only. Reach on the r22 full sample (ON; OFF the same rule): 4 Litolff + 1 Brahms halves decided so on a box wider than one head (1.97-2.74 sp): 2/0/10/2/13 and Brahms 8/0/2/7/11 black heads (own ink filled) written halves; 2/0/1/4/7 a black head (own ink unread); 10/1/3/11/5 a real half (own ink hollow); 4/1/4/5/7 not clear. Proposed as its own item (both arms, needs a flag): "a head's fill is read from its own ink; a box's window never makes a head the ink reads filled hollow". `OMR_HOLLOW_HEAD_WINS` is the mirror case (box read black, own ink hollow) and never acts on a box not one head's size: it neither causes nor fixes this.

**Touched pages** (Litolff 1, 2, 10, both arms gathered on this tree; development control): notes +9 -33, red bars 33 -> 24, judged right->wrong 0, unwritten->wrong 0 (230 tiles). 10/1/2/0 ON = OFF (F4/A4 one chord); 1/0/9/6 ON red "unread" (no D4 eighth); 2/0/10/2 unchanged (C3 half, both arms). The printed ties out of 10/1/2/0 are still missing in both arms.

**The full frozen sample, once** (merged tree, OFF = defaults, ON = `OMR_PAGE_STEMS` + `OMR_STACK_TWO_HEADS` + `OMR_STRING_STOPS_OWN_VALUE` + `OMR_ACCIDENTAL_ON_THE_MARK` + `OMR_HOOK_NOT_ON_AN_ARC`; both arms re-gathered; 3 h 48 min):
- Litolff 2,4,6,8,9,10,11,16: notes +52 -109, rests +2 -5, accidentals +13 -9, flags +20 -33, beams +54 -26 ~15, ties +6 -12, slurs +7 -17, values ~29, pitches ~8, blue +50 -80; red bars 125 -> 96; not written 2077 -> 2137.
- Brahms 0,4,5,8,12,14,19,25: notes +20 -45, rests +2 -18, accidentals +8 -4, dots +10 -28, flags +14 -4, beams +4 -3 ~3, ties +14 -8, slurs +30 -11, values ~17, pitches ~7, blue +44 -42; red bars 111 -> 82; not written 2968 -> 2994.
- Judged: right->wrong 0 and unwritten->wrong 0 on both (309 / 263 tiles); Litolff unwritten->right 1. `judged_claims`: Litolff 8, Brahms 4 contradictions, the same tiles in both arms (0 new).
- Plain-and-different ON vs OFF: Litolff 39 (r21's 41 less 1/0/9/6 and 10/1/2/0), Brahms 38 (r21's 32 plus 6).

**Print reading** (bars changed since r21, plus r21's cannot-tells; crops `out/print/2.306-r22/bars/`, nothing drawn; AN AGENT'S LOOK, not Sean's). Right: Brahms 5/0/11/3 (F4 eighth, flagged), 25/0/12/9 (Bb3 eighth), 25/1/10/3 (F4 eighth) -- three OFF quarters that were wrong, now eighths read at the stem tip; 19/1/8/8 (tie stop kept). Wrong, plain: Brahms 8/0/1/8 (two voices right, but the printed DOTTED quarters written plain quarters; OFF also has no dots and is plain; r21 had it red through the hook rule) and 19/1/8/7 (printed dotted chords written quarters; the second chord written ON only). New cause, both bars, listed not fixed: a chord's augmentation dots not read (dot reader, not the stem reader; wrong in OFF too). Cannot tell: Brahms 4/1/2/3 (probably right), 8/0/1/9; Litolff 4/1/9/5 (crop too small), P12 m19 / m267 (no place).

**The retire step, measured (item 5, design only).** On the r22 full-sample ON gathers, kept heads whose stem join the OLD cell join still decides, by why the page reader did not answer:
- copies of a head filed with another staff (the page files a stem only with the head's own staff, r7): Litolff 158 (25 given a stem), Brahms 822 (156 given a stem) -- NONE written. Retiring the join for these costs nothing in the file.
- the page left a stem each way unresolved (`two_voices`; `_unison_heads` why): Litolff 124, Brahms 23. Given a stem by the old join AND written: Litolff 43 -- one stroke touches the head's ink and the other does not 20, a stroke ends at another head 14, one stem passes the head 3, no head ink on the map 3, a stroke shorter than a stem 2, a stroke holds another head 1; Brahms 16 -- one touches 15, passes the head 1. The rest are the unison rule's two-voice narrowings (no single stem).
- Crops, 3 per cause: `out/print/2.306-r22/retire/` (thin red box = the head). Our look: "one touches" are real two-voice columns and divisi seconds whose second stem's contact the map missed; "ends at another head" are dyads on one stem; "no head ink" are heads on stacks of ledger lines.
- Removing the old join TODAY costs about 43 Litolff + 16 Brahms written heads (their value becomes unread); the copies cost nothing. Order of work: (1) retire the join for copies now (no file change; control: a copy is never written); (2) `one_touches`, the biggest cause on both plates -- read the second stroke's contact through the touching heads of its chord (the r11 contact pass, for a stroke the edge test already found); (3) `ends_at_another_head` -- a dyad on one stem (the r19 outline rule, where the "outline" reaches a stem's length); (4) heads on ledger stacks (head ink upstream, 2.290); then remove the join.

**What still stands before the reader can be switched on:** the retire step (Sean 11-13: no old join beside the page reader) -- about 59 written heads to win back first; the chord dots (8/0/1/8, 19/1/8/7: wrong and plain ON, wrong in OFF too, not the stem reader's); the wide-box fill (item 2, both arms). No tile question arose: every change is settled by Sean's judged answers (0 right->wrong) or by the print; the two new wrongs are wrong in both arms. Fast tier on this tree (flags at default, after regenerating data-flow and the rule page; `wiring --check` 0 unaccounted): 11,401 passed, 0 failed.

## 2026-11-25 -- 2.306 r23: the retire step -- a head takes the stroke it touches when the other is another head's stem; copies stop asking the old join (`lane-2.306-r23`; stem flags OFF; STAGED)

**Cause and process lesson.** r22's biggest retire cause, "one stroke touches the head and the other does not" (20 Litolff + 15 Brahms written heads), was not a reading the page reader lacked: in 34 of the 35 the old cell join gave exactly the stroke the page map says the head's ink touches. The page reader stopped one step short because it asked only "do both strokes touch?" and never "whose is the stroke that does not?". At full size (crops `out/print/2.306-r23/causes/`, our look) the untouched stroke is, in 33 of the 35, ANOTHER head's stem that the page has already read: 22 are the next note's stem standing at this head's other edge, read the OTHER way by its own head (a neighbour's up stem at this head's left, a down stem at its right -- close-spaced eighths and chords); 11 are two voices a step or a third apart in one column, where the upper head's up stem stops at the upper head and the lower head's down stem at the lower (Sean 2026-11-14, r9: upper takes up, lower takes down). The other 3 are strokes no head stands on (a short piece below the staff; a stroke beside a beamed eighth; Brahms 8/0/3/1/10, where the map's contact even names the wrong stroke). The process lesson: a reader that abstains must ask about EACH candidate it refuses what that candidate IS -- here the answer was already on the page (another head's reading), one line away. And r22's census counted the right thing (written heads the old join decides), so the fix could be checked against it head by head (34/35 agree before building).

**Rule 1 (STAGED GATHER, inside `OMR_PAGE_STEMS`; `page_stems._untouched_is_anothers_stem`, reading word `other_stroke_is_anothers_stem`).** *A head with a stroke up at its right and a stroke down at its left whose ink touches only one: where the other is another head's stem, the one it touches is its stem.* The other is another head's stem where the page already stands another head on it and reads it the OTHER way (a stem points one way), or the same way from a head BEYOND this one in that direction (above it for an up stem: the stem stops at that head, short of this one). Never where no other head stands on the untouched stroke (it may be this head's own second voice whose contact the map missed); never where a head on it stands level with or on this head's own side (the stroke would pass this head: a chord stem); never where both strokes touch (two voices, or a stroke holding another head: left as before); never a stroke shorter than a stem (`UNISON_REACH_SP`, measured, narrows only) and never a stroke another head reads the other way (`_outline_leaves_one_stem`). Decides: the evidence is the ink contact (Sean 2026-11-18) and the page's own reading of the other stroke, not a cut-off.

**Rule 2 (item 4, the next cause `ends_at_another_head`, 14 written Litolff heads; `_is_the_stem_of_the_head_it_ends_at`, same reading word).** *Both strokes touch (Litolff merges); the one whose far end stops at another head is that head's stem where that head reads it pointing away from itself -- a stem has one head end -- so the other, a stem's length and read no other way, is this head's.* The other head must have its own head ink (the 2.290 oval): never a box at a stem's tip (Brahms 5/1/5/0's staccato dot, the r19 control, still passes). Our look: Litolff 4/1/8/5/5 the upper note's down stem runs past this head's right edge to the beam; 2/1/8/10/16 and 9/0/3/1/16 the middle head of chords on up stems, the stroke at its left the lower neighbour's up stem. Not reached: five short "ring side" strokes (four at 2.0-2.09 spaces, just past the r19 outline cut of < 2.0 -- a cut-off, left alone), heads whose other head has no oval (4/1/7/4/18), and a kept stroke another head reads the other way (2/0/7/1/5).

**Item 3 (STAGED GATHER + ADJUDICATE, inside `OMR_PAGE_STEMS`).** A copy of a head filed with another staff (r7: its stem is filed only with the staff its note belongs to) now says so: `Q.PAGE_STEM` abstention `on_another_staff` (new `ABSTAIN.ON_ANOTHER_STAFF`, how `copy_on_another_staff`), and `adjudicate_head_stem` abstains `page_stem_on_another_staff` instead of letting the old cell join answer; `rhythm.page_own_stems` gives the copy no stem. Proved, not assumed (`2306/r23_copy_proof.py`): the touched pages' ON gather re-adjudicated twice on this tree, copy rows kept vs dropped -- Litolff 246 copies (the old join gave 40 a stem), Brahms 146 (14): the exported MusicXML is identical apart from renumbered row ids in two guessed-word witnesses (diff after masking `obs:N`: 0 lines, both plates).

**Controls** (`tools/omr/tests/test_page_stems_2_306_r23.py`, fixture `page_stems_2_306_r23.json`: real page windows cut from the reader's exact inputs pickled during a gather of this tree, `2306/r23_gather_dump.py` + `r23_cut_window.py`). Rule 1: Litolff 2/0/7/16/8, 2/1/8/10/9, 9/0/1/1/10, 4/1/2/13/12, Brahms 0/0/11/2/4, 0/0/11/3/10, 0/0/12/4/0 read their stem; on r22's code (replayed from the r22 worktree) and with the rule off each is `two_voices`/`one_touches`. Never: Litolff 10/1/10/11/1 and Brahms 8/0/3/1/10 (untouched stroke holds no head) stay unresolved; Litolff 4/1/5/6/2 (both strokes touch, one holds another head) stays `stroke_holds_another_head` -- and the control can fail the other way: its up stroke IS another head's stem, so only the touch keeps the rule out. Rule 2: 4/1/8/5/5, 4/1/2/4/9, 2/1/8/10/16, 9/0/3/1/16 (fail on r22 and with the rule off); never 4/1/7/4/18 (no oval), which the rule takes once the box is given one. The r9 two-voice window test now expects Brahms 0/268 read `one:down` (its own expectation). Offline replay of the four Litolff and two Brahms dumped pages, r22 code vs r23: only the targeted heads change reading (Litolff p2/4/9/10: 18; Brahms p0/p8: 12), nothing cascades to another head.

**Touched pages** (both arms re-gathered on this tree; Litolff 1, 2, 4, 6, 8, 9, 10, 16 counted, Brahms 0, 8, 14; OFF = defaults, ON = the five r22 stem flags): Litolff notes +52 -103, red bars 115 -> 84, judged right->wrong 0, unwritten->wrong 0 (292 tiles); Brahms notes +9 -8, red bars 43 -> 33, right->wrong 0, unwritten->wrong 0 (216 tiles). The heads the r23 rules decided, against r22's frozen ON file (written note by glyph key; a cross-gather look, not a measure): Litolff 31 of 33 written the same, 2/0/1/5/0 an Ab eighth now plain (was blue), 8/1/1/15/3 an Ab eighth now written (blue); Brahms 13 of 18 the same, 0/0/11/4/12, 0/0/11/4/16, 14/1/9/2/11, 14/1/9/7/7 now written as the upper of two voices instead of a chord with the lower head, 8/0/1/3/3 an F5 quarter now written. Our look at the print (5 of the 7; 0/0/11/4/16 and 14/1/9/7/7 are the same pattern in the same bars, not looked at one by one): right -- two voices in one column, upper head up stem, lower down stem; 8/0/1/3/3 fills its 6/8 bar after a quarter and an eighth rest; the two Litolff eighths are beamed on up stems.

**The full frozen sample, once** (this tree, OFF = defaults, ON = the five r22 stem flags; both arms re-gathered; 3 h 54 min):
- Litolff 2,4,6,8,9,10,11,16: notes +52 -109, rests +2 -5, accidentals +13 -9, flags +20 -33, beams +54 -26 ~15, ties +6 -12, slurs +7 -17, values ~29, pitches ~8, blue +51 -81; red bars 125 -> 95; not written 2077 -> 2137.
- Brahms 0,4,5,8,12,14,19,25: notes +22 -45, rests +2 -18, accidentals +8 -4, dots +11 -28, flags +14 -7, beams +7 -3 ~3, ties +14 -8, slurs +41 -12, values ~17, pitches ~7, blue +44 -45; red bars 111 -> 82; not written 2968 -> 2992.
- Judged: right->wrong 0 and unwritten->wrong 0 on both (309 / 263 tiles); Litolff unwritten->right 1. `judged_claims`: Litolff 8 -> 8, Brahms 4 -> 4 contradictions, the same tiles in both arms (0 new; r22's counts).
- Against r22's full sample: Litolff the same but red 96 -> 95 and one blue mark; Brahms notes +20 -> +22, flags -4 -> -7, beams +4 -> +7, slurs +30 -> +41 (gather-to-gather variance in slurs and words is usual; not checked one by one).

**Found by the print read of the changed heads, fixed after the full sample (no re-gather; offline replay on every sample page).** Litolff 8/1/1/15/3 (our look at 3x): three eighths beamed above on up stems AND below on down stems -- the third head is shared by two voices. Its up stem is held by a stem-end box filed from the staff above on this head's own oval (the same ink, `page_head_alone`, not grouped), so rule 1 took the box for another head and gave this head only its down stem (written a blue Ab eighth; r22 wrote nothing there). Fix: never where a head on the untouched stroke is this note seen again (its head ink is this head's), and never where no head on it has ink of its own (the same guard on rule 2). Control from the real window (fails without the ink comparison). Reach, read offline from the reader's exact inputs pickled on all 17 sample pages (first build vs final): this one head changes, nothing else -- it goes back to the old join, unwritten as in r22. The full-sample numbers above are the first build's; with the fix Litolff loses that one blue eighth and nothing else moves.

**The retire table, re-counted** (full-sample ON gathers, `2306/r23_retire_census.py`, streamed; kept heads whose stem the OLD cell join still decides AND that are written): Litolff 43 -> 21: a stroke ends at another head 14 -> 10 (2/0/7/1/5 kept stroke read the other way; 4/1/7/4/18 the other head has no oval; five short "ring side" strokes the r19 outline rule still refuses -- four at 2.0-2.09 spaces, just past its < 2.0 cut, and 2/1/9/14/2 at 1.56 whose other head reads no stroke; 6/0/3/7/4, 6/0/8/12/1, 16/0/4/6/4 not looked at), head ink unread 3, one stem passes the head 3, a stroke shorter than a stem 2, one touches 20 -> 2 (6/1/3/1/1 and 10/1/10/11/1: the untouched stroke holds no head), a stroke holds another head 1; copies 25 unwritten -> 0. Brahms 16 -> 2: one touches 15 -> 1 (8/0/3/1/10, held), one stem passes the head 1; copies 156 unwritten -> 0. Plus Litolff 8/1/1/15/3 (unwritten) back with the old join after the fix.

**What still stands before the reader can be switched on:** 23 written heads the old join still decides (21 + 2) -- next: the ring-side strokes at 2.0-2.09 spaces (a cut-off question; needs a measured both-sides look, not a nudge), heads on ledger stacks (`head_ink_unread`, upstream 2.290), and the untouched strokes no head holds (where the map's contact is wrong, Brahms 8/0/3/1/10); the chord dots (2.350) and the wide-box fill (2.351), both arms. No tile question arose: every change is settled by Sean's judged answers (0 right->wrong, 0 unwritten->wrong) or by the print; the one wrong reading found was ours and is fixed. Fast tier on the final tree (flags at default; data-flow current, rule page regenerated, `wiring --check` 0 unaccounted, `check` total open 241): 11,430 passed, 0 failed.
