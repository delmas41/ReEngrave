# ROADMAP 2.223 -- page-wide arc binding (STAGED)

Branch `lane-2.223-anchoring` 336ba6b0d, flag `OMR_ARC_BIND_PAGEWIDE` (default OFF). Written by the manager from the lane's report (the subagent's write was refused by the hook).

CONVENTION ASSUMED (NOT CONFIRMED with Sean): a tie needs both ends; an arc at a system edge binds to the edge and pairs across the break; a one-end slur inside a system is written only where GATHER recorded an end candidate at the other end, GUESSED, else abstains -- never an invented stop or an invalid file. An arc above joins the top note at each end, below the bottom (Sean 2.75). Lane addition: across a barline, a printed accidental on the start and none on the stop counts as the same pitch (the accidental carries through the tie). WHAT WOULD FALSIFY IT: a same-step arc across a barline Sean reads as a slur to the natural; a written arc Sean reads as joining other notes. AS BUILT: both ends must bind for any kind; edges are recorded but not yet paired across systems; nothing is written GUESSED.

## Cause and process lesson
Census of `arcs_not_written` (excluding `not_an_arc`) on 2-page slices: Brahms p0,4 215 boxes (118 `tie_pair_*`, 48 slurs binding < 2 notes); Litolff p2,4 250 (113 / 109). Against Brahms p0 hand truth (corrected scorer: the 10-29 `p0score.py` matched written ties to truth ties on other staves, so its "ties right 20" is not comparable), 37 of 84 truth ties fail. Crops of ~25 put the causes mostly upstream of binding:
1. head reading (8 boxes, staff 5): a ledger half boxed twice; the kept boxes in two bars sit 0.5 sp apart, so they cannot be one pitch (2.232's area);
2. detection (8): flat ties along a staff line refused `ink_is_a_staff_line`;
3. detector class (14): a tie written as a slur;
4. system edge (5): a courtesy 9/8 after the last barline became its own cell and hides the system end;
5. pitch spelling: bound ties refused because the stop head lacks the carried accidental (`tie_spelling_differs` 13 -> 19 with the flag).
Lessons: split a "binding" bucket by what is at the arc's ends before a binding lane opens. A page-wide curve is only as good as its join: 2.166 joins arcs meeting end to start at one note; the first build turned four ties into one long slur (p0 staff 12). Guard: a curve joined anywhere but a barline cut is not bound.

## Prior work
Hairpin §7c "one anchor is enough" is a HAIRPIN rule, never ruled for arcs, not used. Arc-recovery §5 (an arc with nothing to bind stays refused) kept; §6 (an arc is drawn to a stem) used as stem-tip end candidates. Arc-grammar §16.9 (Sean's top/bottom rule) used. Rounds 8-9 (anchors close bleed fakes; cheap inside the staff band): the binder only re-binds arcs ADJUDICATE kept and does not decide whether an arc is real. The arc claim's two OFF flags (kind-from-ends, slur-from-anchors) measured worse on the same scorer (ties 45, slurs 51), not used. `OMR_ARC_RECLASS` stays rejected: the binder decides a kind only where steps and boxes agree.

## Built
`arc_claim.py` pure helpers (bind_enabled, curve_side, bind_end, bind_curve, heads_between, stem_tips; 2.166's own anchor windows; column cut-offs set by hand, not swept). `adjudicators/ownership.py` `_page_binding` (both ends of `Q.SYSTEM_ARC` to the owner staff's usable heads; chord ends top/bottom; stem free ends as candidates via CV `Q.STEM`), `_joins_not_at_a_barline`, `BIND_DIFFERENT_POSITION_SPACES` 0.435; `adjudicate_arc_kind` (every piece takes the curve's kind); `adjudicate_tie_pair` reason `paired_by_page_binding`. `export.py` tie/slur functions only (`_place_arcs`, `_pair_arcs`, new `_page_bound_slur(s)`, `_page_bound_slur_spans`; counts `slur_bound_end_not_in_file`). 11 tests with twins (`test_arc_bind_2223.py`). Not built: cross-system pairing, GUESSED one-end slurs, anchoring of words/dynamics.

## Measures (lane's own; the combined test is the manager's)
2-page `LANE_REPORT_SAMPLE`, `--from adjudicate`, OFF and ON on one tree (both arms differ from the slices' own duration verdicts on 12-13 of ~2,400 because main moved): Litolff p2,4 ties +24, slurs +52 -10; Brahms p0,4 ties +12, slurs +22 -32; red bars and notes not written unchanged; judged right->wrong 0, unwritten->wrong 0, wrong->right 1 (Litolff). Arc ledger 250 -> 212 (L), 215 -> 204 (B).
Brahms p0 hand truth, corrected scorer, OFF -> ON: ties right kind 47 -> 47 of 84 (precision 0.91 both); slurs 58 -> 55 of 69, precision 0.59 -> 0.64, slurs covering no truth arc 26 -> 21. Two of the three lost slurs have a stop head never written (value undecided, 2.233). Truth arc b4057: the binder says tie, hand truth slur; under Sean's 10-09 rule the hand truth may be wrong -- needs Sean.
One-end-bound arcs: Brahms 53, Litolff 57; other end: nearest head within 2 sp past the window 22 / 27 (mostly in x reach, too far in y: the stem-end shape), system edge 21 / 12, a head 2+ sp past 10 / 13, two columns at the end - / 5. Stem-tip candidates bind 18 B / 29 L curves. Fast tier 9,376 passed; `staged.check` 198 unchanged.

## Risks for the combined test
Binding uses only heads ADJUDICATE leaves usable (2.232 changes ends and kinds; a tie needs positions within 0.25 sp). A bound slur whose end head is not written is lost and no longer offered to the old pairing (2.233 should recover these). More ties are bound than the export pitch check accepts (`tie_spelling_differs` up). The 2.166 trace/join is GATHER; a re-gather changes which curves pass the barline-join guard.
