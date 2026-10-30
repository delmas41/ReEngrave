
## 2026-10-30 ROADMAP 2.238 -- one owner decides, with shape (flag `OMR_OWNER_SHAPE`, default OFF; STAGED ADJUDICATE)

Branch `lane-2.238-owner-shape`. Nothing deleted on principle.

**Cause / lesson.** `adjudicate_stroke_owner` (2.205) asks one thing of a claim: does each STROKE the box covers have a piece-shape its
family can leave (`shape_fit`: clear / could / no)? It never asks whether the BOX's ink, taken whole, has the class's shape. So a head box
on the foot of a quarter rest, the hook of an f, or a rest-classed box on a stem owns ink with "could" pieces, and the claim ORDER (heads
before rests) turns that into a decision: the rest beside it is refused `rest_ink_runs_into_a_head`. The box-level shape knowledge is in
the old pair rules, each read off a GATHER row the owner never consulted. Process lesson: a parity number between two deciders says nothing
about which is right; the 2.237 tiles did. Where a GATHER fact exists, the later stage reads it; it does not re-measure it or ignore it.

**Design (a: the evidence; every quantity is an existing GATHER row and every cut the old rule's own).**

| disputed old rule | shape evidence it uses | GATHER row | owner's veto (fit `no` on every stroke the box covers) | rival named for those strokes |
|---|---|---|---|---|
| head `on_a_dynamic_letter` (detector letter) | widest filled disc < 0.9 sp, or the head holds >= 0.4 of the letter's ink; head >= 0.4 inside the letter box; an f under 1.7 sp wide is not an f | `Q.NOTEHEAD_LETTER_INK` | `_on_a_dynamic_letter_refusal`'s test, verbatim | the letter box (often the next staff's cell) |
| head / rest `on_a_dynamic_letter` (2.107 second look) | >= 0.5 of the box's ink inside read letters | `Q.LETTER_LOOK_COVER` | `letter_cover.refuses` | the read letters |
| head `is_a_rest_shape` (2.145) | the ink cluster under a stemless head reads as an eighth / quarter rest | `Q.UNBOXED_REST_SHAPE` (+ `Q.STEM`, `Q.REST`, `Q.GLYPH_BOX`) | `head_rest_shape.read_head_ink` | the rest-shaped cluster |
| head `on_a_rest` (2.173, whole classes) | box overlap with a rest box (no shape) | `Q.GLYPH_STROKES` + the owner's own fits | NEW STRUCTURE, no number: a head box none of whose strokes is a CLEAR head piece shares a stroke with a rest box that has a CLEAR rest piece (a rest never touches a note: the claim order gives the head the shared ink only when the head has a head's shape) | that rest box |
| rest `rest_stroke_into_a_head` (2.150b) | a thin run >= 1.0 sp into >= 0.9 sp of solid blob or 0.4 sp^2 of standing head ink | `Q.REST_INK_CONTACT` | the old cuts, and only where the margin is at least the measured re-read noise 0.05 (2.232) | none: the stroke is a stem, the consumers read it |
| accidental `on_a_rest` (2.192) | IoU >= 0.5 with a rest box AND 2.190's corner shape not the class's family | `Q.ACCIDENTAL_STAFF_POSITION` detail `shape` | `accidental_shape.on_rest_verdict` keep=False, where the rest box has a CLEAR rest piece | that rest box |

HEAD_INK is not used as a veto: it reads tiles 1 and 9 as one filled head (it trims to the head-sized middle), so it does not separate them.
The eight head-ink quantities are not consolidated here (only read where a moved rule already read them).

**(b) How the owner uses it.** `own_strokes(..., vetoes=...)`: a vetoed claim's fit is `no` (why `veto:<rule>`) on every stroke it
covers, and the rival, where one is named, is a candidate on those strokes with fit `clear` (how `named`). Then the ordinary table runs:
the rival owns the stroke; with no rival the stroke is `refused_claims` (left to the consumers: tile 4's stem). A stroke two fitting families
still claim stays CONTESTED. The head-before-rest order is read after the vetoes, so a vetoed head no longer makes its rest "run into a
head". The precision rules, flag ON, read the box verdict ONCE: `refused` WITH A VETO ON THIS BOX (and not only an area claim's -- the
register already speaks for those) -> refused under the name of the evidence that decided it (`on_a_dynamic_letter`, `on_a_rest`,
`rest_on_a_dynamic_letter`, `rest_stroke_into_a_head`, accidental abstains `on_a_rest`; downstream readers key on those names, e.g.
`rhythm.NOT_A_NOTE_REFUSALS`; `is_a_rest_shape` is left to its own rule so 2.145's rest is still written at the cluster); `owns` -> the
covered rules below do not decide; `contested` / `no_ink` / a refusal with NO veto / no verdict -> the covered rules decide as before
(the owner cannot tell: rule 8, the old rule is the stopgap, never a guess).
**Revision after the first lane report (2026-10-30):** the first build let ANY owner refusal decide. 2.205's per-stroke fit alone then
refused 31 Litolff / 39 Brahms heads main keeps, one of them a quarter Sean judged twice (Brahms `glyph/5/0/2/3/2`, "4": right->wrong 2).
That is exactly the lesson of this lane -- the per-stroke fit is no box-level shape test -- so a refusal decides only where moved evidence
vetoed the box.

**The 50% cover share (Sean 2026-10-30: "sounds arbitrary").** In this build it is only the CANDIDATE FILTER: which strokes a box is a
claimant for at all (`Q.GLYPH_STROKES`, cut `stroke_map.COVER_SHARE_MIN = 0.5`, filed in GATHER, which this lane may not edit). It never
picks between claimants: between families the decider is `shape_fit` on the piece plus the vetoes above (box-level shape evidence), and
within one family nothing is picked (merged, 2.186's question). Where it still costs: a head whose piece is head+stem fused covers only
0.35-0.45 of it, so the head is no claimant of its own ink (it stays `partial`, joins only by the ATTACHED rule). The fix is not a lower
number: once 2.239 (`OMR_SPLIT_JOINS`) cuts fused ink at the joins, every stroke a box touches (cover or partial) should be a candidate
and the WHOLE piece's shape decides; 2.205 measured that widening as harmful on fused pieces (counting partial strokes refused 127 / 343
heads main kept), so it waits for whole pieces. Next step for the owner after 2.239, not built here.

**(c) Covered (stop deciding when the owner has a verdict):** head `on_a_dynamic_letter` (both readers), `is_a_rest_shape`, `on_a_rest`
(whole classes); rest `rest_on_a_dynamic_letter`, `rest_stroke_into_a_head`, `rest_overlaps_a_notehead`; accidental `on_a_rest`. NOT
covered (they answer another question): same-family duplicates (`notehead_is_a_duplicate_box`, `stacked_head_duplicate`, `head_cut_piece`,
`rest_is_a_duplicate_box` -- 2.186's which-box question; tiles 3, 6, 8, 12), `belongs_to_a_nearer_staff` (a staff question; tile 11),
the register (`claimed_by:*`), box-shape rules (`too_narrow`, `clipped_fragment`, `is_a_dot`), `rest_has_a_stem`, the slash rules.

**(d) Tile 10.** The old rule's column scan found a thin run of 1.01 sp against its 1.0 cut: margin 0.01, inside the 0.05 re-read noise.
The stroke map has the rest's three strokes (blob 1.35, vertical 1.62, blob 1.14) touching no head stroke, so the owner already gave them
to the rest. With the flag ON the 2.150b evidence vetoes only at margin >= 0.05 (tile 4: 0.69, the stem), and the near-tie is left to the
stroke map: the rest owns its ink and is kept.
**Measured (merged tree incl. 2.232 + 2.235; frozen sample, 20261029-night slices, adjudicate replay).**
- *Lane report* (`lane_report --flag OMR_OWNER_SHAPE --tag 20261029-night`, `out/print/2.238-tiles/lane-report.txt`): Litolff notes +1 -4,
  rests +7 -1, accidentals +1 -1, beams +1 -3 ~2, blue +1 -5, words +4 -5; red bars 199 -> 201. Brahms notes +2, rests +1, blue +1,
  words +2 -1; red bars 164 -> 165. Judged right->wrong 0 / 0, unwritten->wrong 0 / 0. Head moves: L 3 kept -> `on_a_rest` (the
  structural veto), 2 refused by another rule now under `on_a_dynamic_letter`; B 2 `on_a_rest` -> kept (the owner owns them; Sean's
  new tile 1 is one), 1 kept -> `on_a_rest`. Control line: neither arm reproduces the saved record (the tree moved since the night), so
  the OFF arm of the same run is the baseline.
- *Parity* (`owner_parity.py` + `rule_parity.py`: main's old refusals from 2.237's OFF dump against the ON owner; full table
  `parity-owner-shape-2.238.txt`). Covered rules, owner agrees (refuses) on L / B, before -> after: head `on_a_dynamic_letter` 1 -> 35
  of 38 / 0 -> 13 of 14 (the rest silent: no stroke); `is_a_rest_shape` 0 -> 11 of 11 / none; head `on_a_rest` 1 -> 1 of 1 / 0 -> 5 of 7
  (2 kept: the owner keeps whole-class boxes whose ink holds a clear head piece -- tiles); `rest_on_a_dynamic_letter` 1 -> 2 of 2;
  `rest_stroke_into_a_head` 16 -> 22 of 30 / 25 -> 34 of 41 (the 5 / 1 left are the near-ties under 0.05, kept by design: tile 10's
  kind); accidental `on_a_rest` 0 -> 10 of 10 / 3 -> 52 of 52. `rest_overlaps_a_notehead` 1 L fire, still disagrees.
- *Sean's 2.237 tiles, in the ON file:* all 12 as he answered -- 1 no head, the quarter rest written at the cluster; 2 the eighth rest
  written, the double sharp not applied; 3 one eighth rest written (the twin `.../28`); 4 no rest on the stem; 5, 7 no head on the f /
  ff; 6, 8 one half written at the place (`16/1/3/1/3`, `16/0/8/16/3`); 9 no head, the quarter rest written; 10 the eighth rest NOW
  WRITTEN (OFF: not); 11 no head (nearer-staff rule, not covered); 12 one dotted half written (`0/0/4/3/2`).
- *New tiles* `out/print/2.238-tiles/tiles` (key.json outside): 9 places where ON differs from main + 3 controls. Question: what is the
  ink in the box?
- **Candidates to retire** (after Sean's 2.238 tiles, each by a byte-identical file with the rule deleted): accidental `on_a_rest`
  (52/52, 10/10), head `is_a_rest_shape` as a decider (11/11; its reader stays, the owner calls it), head `on_a_dynamic_letter` both
  readers (35/38, 13/14), `rest_on_a_dynamic_letter`. NOT yet: `rest_stroke_into_a_head` (the owner differs by design on near-ties --
  Sean's tile 10 says the owner is right there), head `on_a_rest` (2 Brahms disagreements to judge), `rest_overlaps_a_notehead` (1).
- The 3 DEAD rows were NOT deleted: `is_a_clef` is the register-OFF fallback with its own tests, `same_side_second` has a pinned test
  file; each needs its tests retired with it and a byte-identical whole-movement check -- a deletion lane's job.

## 2026-10-30 ROADMAP 2.237 -- rule-page refresh on fresh fires (measure only; nothing deleted)

Branch `lane-2.237-rule-refresh`; written by the manager from the lane's report (the hook refused the lane's write). Method: current tree (2.232 ON) re-adjudicated on the saved GATHER rows of the 20261029-night frozen-sample slices (8 pages a plate, `replay_slice.py`, no re-gather); `build_rule_page.py --records 20261029-night` adds a "fresh L / B (sample)" column beside the 10-22 whole-movement column; `rule_parity.py` (parity + near-margin share, noise bar 0.05 on each verdict's own margin), `rule_lists.py`, `rule_tiles.py`. A 0 on an 8-page sample is a candidate, not proof.

**Cause / lesson.** The "retires with 2.205/2.206" rows were never re-measured; re-measured, all but 3 still fire and none reaches 95% parity with `adjudicate_stroke_owner`. The owner answers a different question: it gives ink to claimants, so twins MERGE rather than one being refused, and a box on ink another mark covers is "owned", not refused. Parity is low because the old rules refuse boxes the owner KEEPS. "Ownership decides, the rule goes" cannot be assumed; where they disagree Sean's tiles decide, and where the old rule is right the OWNER must change. The B (eraser) rows still fire at ~40-60% of the 10-22 rate on post-fix gathers: 2.206 did not retire them.

**DEAD** (0/0 fresh and 0/0 in 10-22): notehead `is_a_clef` [C], `same_side_second` (dead code) [C], dot_role `owned_by_another_staff` [C]; plus dead reasons inside live rows (on_the_staffs_leading_barline, is_a_meter_digit, is_a_time_signature_digit, inside_the_meter, claim_narrowed:meter/leading_column/arc, on_another_symbols_box, off_staff_glyph, stem_unread, stem_values_open, rest_is_a_meter_digit, accidental head_belongs_to_a_nearer_staff, head_owner_unread, articulation no_staff_geometry, ornament nearest_either_side).
**SAME AS THE OWNER (>=95%)**: none. Closest: accidental `one_ink_absorbed` L 77/82 (94%), B 360/362 (99%), nearly all merged; head `claimed_by:meter` B 13/14; rest_has_a_stem L 59/64, B 11/13; is_a_beam_piece L 13/16.
**DISAGREES** (fires L/B, biggest first): accidental owned_by_another_staff + head_belongs_to_a_nearer_staff 85/246 (a STAFF question the per-cell owner cannot answer); accidental on_a_rest 10/52 (Brahms owner keeps 47/52); head duplicate_box + stacked_head_duplicate 194/42 (124+31 merged; 0 of 94 on a margin < 0.05 -- 2.232 worked); rest stem/barline/slash/overlap family 126/73 (7 of 120 near margin); rest_is_a_duplicate_box 52/236; head on_a_dynamic_letter 38/14 (owner keeps 28/10 -- judge before any deletion); head claimed_by clef/key/leading_column 44/32; head on another mark 41/34; belongs_to_a_nearer_staff 19/14; head_cut_piece 10/7. Owner refuses/contests boxes main KEPT: L heads 36+40, rests 5+37, accidentals 322; B heads 41+32, rests 11+76, accidentals 448. No parity possible (owner has no claim): no_ink_under_box [B] 78/768, duration owned_by_another_staff 710/948, glyph_owner distance 2,621/5,190, and the unboxed-rest, stem_value, dot_role, articulation, ornament, ledger rules.
**Redundant head-ink measurements** (from code + fires, not proved by a byte-identical file): NOTEHEAD_INK (HEAD_INK already the fill reader); NOTEHEAD_LETTER_INK + LETTER_LOOK_COVER vs the page-wide word claims (but on_a_dynamic_letter disagrees: judge first); HEAD_OVAL vs the arc claim; HEAD_LINE_CUT an erasure workaround. STACKED_HEAD_FIT and NOTEHEAD_STEM_CROSS_INK not redundant yet; HEAD_INK the keeper.
**Tiles** `out/print/2.237-tiles/tiles` (key.json outside): 12 places where the old rule refused a box the owner KEEPS. Question: what is the ink in the orange box?
**Next for a deletion lane**: (1) delete the 3 DEAD rows after a byte-identical MusicXML check on a Litolff whole-movement re-adjudication; (2) trial `one_ink_absorbed` the same way; (3) Sean's answers on the 12 tiles before touching any disagreeing rule; (4) leave the B rows until measured on a full post-fix gather.

**Sean's answers (2026-10-30):** 1 part of 4 rest, 2 8 rest, 3 8 rest, 4 stem, 5 part of ff, 6 2, 7 part of f, 8 2, 9 part of 4 rest, 10 8 rest, 11 e of sempre, 12 dot 2. Old rule right / owner wrong 7 of 12 (1, 2, 4, 5, 7, 9, 11); old rule wrong 1 (10: a real eighth rest refused as rest_stroke_into_a_head); duplicates or pieces of real marks 4 (3, 6, 8, 12; right only if one copy is written -- to check). The stroke owner decides by claim alone, with no shape test of what the ink is; the old rules carry that shape knowledge. Next: move the old rules' shape evidence INTO the owner (owner refuses a claim whose ink does not have its class's shape), then retire each old rule only where the reworked owner matches it and Sean's tiles.
