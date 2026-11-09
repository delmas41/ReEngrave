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

## 2.278 -- beams and flags: why the value stays narrowed, and what will work (Sean 2026-11-08; diagnosis only, no pipeline code)
STAGED ADJUDICATE (`rhythm.adjudicate_duration`) narrows, STAGED EXPORT (`export._place_notes`) refuses. Records `library/_shared-records/{beethoven5-litolff,brahms1-breitkopf}-mvt1-whole-20261104-night.record.json`, exported by main ede3692d8 (the instrumented export reproduces the overnight's `notes_not_written_total`: Litolff 4,440). Probes `probe/2.278/` (`diag.py` one row per narrowed / chord-undecided head with the verdict's own detail; `causes.py`, `cdeep.py`, `tipvs.py`, `bfsdeep.py`, `barpos.py`, `chords.py`, `sheet.py` my look, `tiles.py` Sean's tiles). Plan: docs/plan-2026-11-08-beam-flag-reading.md.

### Cause and process lesson (open)
A beam is never an object. Every narrowed head asks five or six readers, in its own cell, whether a stroke over its stem is a beam; any disagreement becomes a "possible" level, ADJUDICATE narrows, EXPORT refuses. Every earlier effort improved one reader or one per-stroke refusal and measured the heads that rule touches; the page-level effort (M4) changed only where the strokes come from and kept the per-head vote. **Lesson:** read ONCE the unit that carries the decision (the beam group: one stroke, the stems under its width), not the unit that is cheapest to measure (the stroke, the head). Second lesson: 2.275's premise that `chord_value_undecided` is "a stem whose value stayed narrowed" is wrong (below); a bucket name is a claim to check.

### History table (verified against the tree; ON/OFF read from docs/flags-2026-09.md and main)
| effort | what | today | what it measured | why it stopped |
|---|---|---|---|---|
| LEGACY `export.annotate_beams` (omr-beam-gap-2026-09) | repaired how beam begin/continue/end are written over notes already read | frozen, ON in LEGACY only | wrong flag/beam edits 449 -> 31 | never read a beam from ink; reading was the STAGED path's job |
| 2.18, 2.18b, 2.18c, 2.25 | stroke counted by x range only; hairpin/slur/ledger/neighbour strokes counted as this note's beam; flag ink at a bare tip | merged, closed 2026-10-08 | narrowing classes named (omr-duration-narrowed) | per-stroke discount rules; what they could not tell stayed narrowed |
| 2.38, 2.38b, 2.38c | CV join witness: does this stroke join THIS stem | ON (2.38b), 2.38c withdrawn | NOT-JOINED-only decisions 165 on Brahms p1; 1 connection withdrawn | a second voter, not a decision |
| 2.43, 2.69, 2.74, 2.77, 2.82, 2.83, 2.104 | stray beam box must not undecide a clear note; count flag hooks; beam joins two stems and is thicker than a hairpin; thickness relative to the staff; flag shape at the tip; missed flags | ON | Sean's tiles 9/9 flags; 40 real beams | each decided a class (hooks, flags); beamed-group heads stayed per-head |
| 2.121, 2.126 | confirm the beam at the stem end; beam past a staff line | ON (2.126 ON) | hand truth: of 24 missed notes 19 bare, 4 beamed, 1 flagged | the premise (beams) was mostly bare stems; real beams 5 |
| 2.146 | clean stem tip means no beam | ON | Sean 33/33, hand truth 41/41 | decides BARE quarters only |
| 2.153 -> 2.154, 2.155, 2.162 | beam level needs a joined stem (OFF, parked); bar sum never picks from a narrowing (ON); join window at the barline edge (ON); a bar with an undecided note has no length (ON) | mixed | 3 right Litolff eighths made wrong by the bar sum | correct rules; they make each narrowing cost the note |
| 2.170 | beams on the shattering plate: refused strokes off the tip | ON | no beam at the tip 1,319 Brahms / 279 Litolff; shattered beams 17 / 10 | decides the bare quarters; beam-present rest remains |
| 2.202 (a-f) | beams from the stroke map (shared ink map step 3); beam owns stems under its width | ON (2.202f, 2026-10-28) | narrowed heads 236 -> 48 / 191 -> 33 on the frozen sample; judged right->wrong 0 | added one more voter; its disagreement with the cell reader is today's biggest bucket |
| 2.204 | stems from the stroke map | PARKED (stop rule) | right->wrong 0 but unwritten gained | stem rows still missing for 45 + 24 Litolff narrowed heads |
| 2.209, 2.213, 2.235, 2.243 | beam-end box sets another note's value; beam width from its own ink; tip readers and beam readers honour claims | ON | tiles 12/12, 8/8 | claims, not the decision |
| 2.219 | a box judged a beam piece still gets a duration | closed | 0 written | stale verdict, file clean |
| 2.259 | last head of a beamed group takes its beam | PARKED OFF (aa7a827a0) | cell cut the beam to a 0.26 sp sliver; patch Litolff +4 notes, judged 0 wrong | patched a downstream reader; folded into M4 |
| 2.260c M4a (+2.269) | one page beam reader on the page map, page claims name strokes | merged OFF | parity by place: Brahms 74/143, Litolff 172/221; no-slab false beams Brahms 31 -> 11, Litolff 74 -> 61 | filed slurs, staff-line residue, dynamic crossbars, head ink as beams until claims existed |
| 2.260c M4b | page beams replace cell reader A (flag `OMR_PAGE_BEAMS_RETIRE_A`) | OFF, not landed | Litolff notes +22 -63; Sean's tiles: fixes 5, breaks 3, loses 2 right 16ths; with M6 on +24 -59 | kept the per-head A + C + join vote on page strokes; the disagreement bucket came with it |
| 2.260e M6 | every head read once | merged OFF | Litolff notes +2 -2 | did not fix M4b's loss |
| 2.275 | census: duration narrowed is the biggest real-note loss | measured | Litolff 236, Brahms 696 distinct heads | named the cause "stem tip reading"; recommended chord_undecided shrinks with it (not so, below) |

### Litolff measurement (20261104-night)
- 256 boxes `duration_narrowed` (236 distinct ink). Beam family 219 (`beams_ambiguous` 122, `beam_discounted_uncertain` 89, `beam_certain_not_joined` 8); flag family 10; head fill / class 22; dot 5. (`probe/2.278/causes.py`)
- `beams_ambiguous` 122 by where the evidence was lost (`tipvs.py`, `cdeep.py`): cell reader counts a beam level but the stroke-map tip reading says no beam (before [1,1], after [0,1], boxes none) 49; no stem row, no tip read 45; tip reader says the stem is beamed but the cell reader has the stroke only as a candidate 11; first level certain, second only possible (eighth or sixteenth) 17.
- `beam_discounted_uncertain` 89: no own stem 24; with a stem 65: refused by `owned_by_another_mark` 23, `through_heads` about 24, `too_thin` 10, no recorded why 11.
- Stem direction of the narrowed heads: down 114, up 43, abstained 99; the head's place in its bar is NOT special (narrowed: first 29%, middle 45%, last 23%, only 5%; all written heads: 27 / 29 / 28 / 16): so "the last head of a group" (2.259) and "next to a barline" are instances, not the cause (`barpos.py`).
- Page beam rows (`Q.PAGE_BEAM`) are absent from the production record: `OMR_PAGE_BEAMS` is OFF, so nothing at page level reads a beam in production. Per-stem reader rows that exist: `stem` 8,540, `beam_stroke` 4,239, `beam_stroke_ink` 4,222, `beam_stem_join` 6,733, `beam_stem_levels` 8,540, `stem_tip_ink` 3,552, detector `flag` 297.
- **chord_value_undecided** 98 heads / 42 groups: heads on ONE stem in 1 group; two stems 21; a head with no stem 20 (`chords.py`, `chords_an.py`). Values: half versus quarter 30 groups, eighth versus quarter 11, eighth versus half 1. My look at 16 of 20 seeded crops: hollow halves beside a fused black head, flags and rest pieces boxed as heads, two voices grouped by x. Not a beam problem.
- My look (ours, not evidence) at 40 seeded narrowed Litolff heads (`sheet.py`): a clear printed beam over the stem 10 (cause buckets: `beams_ambiguous` certain<possible 5, no stem 1, certain-not-joined 1, all strokes refused 1, head fill 2), hollow half with clean tip 3, bare stem (quarter) 4, head glued into staff line or barline ink with no readable stem 17, unclear 6. Of 16 seeded heads from the 49-head disagree bucket, a beam stands at the far end of a long down-stem on about 6 (it lies below the staff, at the cell edge) and the rest are fused ink.
BRAHMS_FINDINGS_PLACEHOLDER
