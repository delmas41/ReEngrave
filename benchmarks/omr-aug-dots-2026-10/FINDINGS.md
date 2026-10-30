# ROADMAP 2.127 -- augmentation dots that never lengthen a note (STAGED ADJUDICATE)

Records: `20261013-night` (Brahms 317803, Litolff 984073), gathered at ca46eae4. Truth: Sean's Brahms 317803 page 0
(`data/hand-truth/pages/imslp317803/0.json`: 131 `augmentationDot` boxes, 115 dotted heads). Flag `OMR_AUG_DOT_JOIN`,
**default OFF** until Sean's tiles (`out/print/2.127-review/dots-review.png`). Base: `origin/land-2.124` (the `dot` family).

## 1. The 1,108 are not 1,108 dotted notes written plain
`augmentation_decided_but_unattached` reproduced exactly (1,108), then split by the HEAD the dot names and that head's live duration:

| count | what it is |
|---|---|
| 555 | names a ghost head another staff owns (`owned_by_another_staff`); the real head elsewhere carries the dot in 385 |
| 377 | the SAME physical dot a head already carries from its OWN cell (value `dots: 1`); not lost |
| 149 | head's duration NARROWED (`beam_discounted_uncertain`); the note is not written |
| **16** | head's duration DECIDED with no dot: 8 are a neighbouring staff's flag curl boxed as a dot (inside a `flag8thUp` box), 8 real dots (foreign-cell dot the head's own strip never saw) |
| 11 | other (rest, not-a-note-mark) |

So "~390 dotted notes written undotted" was the ledger (a superseding verdict's `used` is empty; a dot counted from two cells), not the file. 2.124's 353 `head_and_marks` are the duplicates.
Page-geometry cross-check (nearest decided head, any cell): 4,275 served, 35 beside a decided undotted head (12 flag tips, ~20 real).

## 2. The real wrong rhythms
* **Dot never PLACED (`dot_role_ambiguous`)**: 596 Brahms dots; ~65 sit beside a decided-plain head (+8 `on_a_stroke`, not dots). Near misses of the role window (0.75 above / 0.25 below): dots 0.8-1.0 sp above a hollow head's box centre (half notes on a ledger), dots 0.3-0.4 sp BELOW the lower head of a second. On Sean's page 0: 7 of 131 truth dots, 4 of them beside a head written PLAIN.
* **One dot boxed twice counted twice**: Brahms `0/0/11/0/15` + `/24` (2 px apart) -> `0/0/11/0/10` written 1.75; Sean reads a single dot (2.121 tile). 9 notes carry twin boxes (6 decided, 3 narrowed).
* **A narrowing with no dotted candidate**: `0/0/11/0/4`, `/9` candidates {eighth, quarter}; INFER picks the plain quarter, Sean reads dotted quarters (2.121 tiles).
* Truth page 0, notes carrying truth dots: written dotted correctly 91; written PLAIN 5 (4.3% of dotted notes, silent); narrowed 19. One plain note is a dot the detector never boxed (`b4213`-class: truth dot at page (3140,4717), no box) -- reach, not this item.
* Litolff: of 154 `augmentationDot`-class boxes most are not dots at all (f/ff letter tips, slur ends, ledger pieces; 18 crops viewed); 15 augmentation is not a loss. The 39 -> staccato are mostly the same junk (a mis-role to show Sean, not a lengthening bug). No Litolff truth.
* Side find: 21 dotted heads read `beam_levels: 1` with `beam_evidence: none_over_this_note` (a dotted quarter as 0.75?) -- not this item.

## 3. Fix (`OMR_AUG_DOT_JOIN`, default ON since 2026-10-14)
* `adjudicators/aug_dot_join.reconcile_unjoined_dots` (called from `adjudicate.run` after `Q.DURATION`): a dot SEEN beside a decided-plain note -- a decided augmentation dot naming it from another cell, or a `dot_role_ambiguous` dot in a wider window (gap -0.1..1.2 sp, |dy| <= 1.3 sp, not centred over another head) -- supersedes the duration with NARROWED {as read, one dot} (equal support; nothing chosen); a narrowing with no dotted candidate gains them. A dot inside a detected flag box is the flag's curl and narrows nothing. It never lengthens a note: a flag curl, a neighbour's staccato and a dot are one box.
* `rhythm._attached_dots`: boxes within 0.3 sp of each other are one dot.
* `regather_report.FUNNELS`: a `dots` row (family `dot`, meaning `dot_role`); `articulations` no longer claims staccato dots.
* Tests `test_staged_aug_dot_join_2_127.py` (18; real Brahms numbers incl. Sean's chord tiles; flag-off and control for each rule).
* Not done: giving dots a staff position (`check` stays at the 2.124 level, 193).

## 4. Measured (re-export of the 20261013-night records; bar sums/INFER NOT re-run, so a narrowed note is held out, not collapsed)
* Brahms: 94 notes narrowed (67 unplaced dot, 27 decided dot from another cell) + 53 narrowings extended; notes written 10,311 -> 10,289, `duration_narrowed` 3,021 -> 3,115, 31 flag-curl dots refused. Litolff: 13 narrowed, notes 6,573 -> 6,567.
* Truth page 0 (115 dotted heads): written dotted 91 -> 91, written PLAIN 5 -> 1, narrowed 19 -> 23. All 6 notes the fix narrowed on page 0 carry a truth dot (6/6).
* `judged score` on the unchanged records (flag OFF, so identical): Litolff 107/12/4/1/13/97, Brahms 66/10/22/1/7/133. `check`: 193 (= 2.124 base). Targeted tests 90 pass; the full fast tier was not run to the end (hours; killed at 3%).
* Twin-box dedupe is only reproduced by tests (it is inside ADJUDICATE; needs a re-decide).

## 5. Open
Sean's tiles (15, 2 controls, hidden manifest `out/print/2.127-review/_hidden/manifest.json`) decide whether the window (1.2 / 1.3 sp) is right; then whether to widen the role window itself instead of narrowing. A re-decide of one page with the flag on would show INFER collapsing the narrowed notes.

## 6. Sean's 15 tiles (2026-10-14) -- manager's read, scored against `_hidden/manifest.json`
Answers in `out/print/2.127-review/answers.json` (his words in `sean`). Sean then said "Yes" to landing with the switch ON.
* **N2, ambiguous dot beside a plain head (tiles 5, 7, 9, 10, 13, 14): 6 of 6 truly dotted.** The fix narrows each to plain/dotted (blue); 0 over-flagged.
* **N1, "decided augmentation on a foreign head" (1, 2, 4, 6, 11): all staccato/staccatissimo, not dotted.** The head stays undotted (rhythm right) but the dot ROLE is wrong -- an articulation is called augmentation. Follow-up (role decision, not this lane).
* **N1, dot inside a flag box (3, 15): staccatos**, correctly refused.
* **Controls: 8 (plain) and 12 (dotted quarter) right.**
* **Follow-up, head value:** tiles 9, 10, 13 are dotted HALVES, which today export as a quarter (9) or a whole (10, 13) -- a head-value error beyond the dot (hollow-head work).
* Window (1.2 / 1.3 sp): no false narrowing seen on 15 tiles; still a measurement on one score.

## ROADMAP 2.234 (2026-10-30): "dots decided, never placed" -- the ranking row counts ABSTAINED dots; nothing decided is unplaced, no flag built
STAGED. Cause first. Replayed the 20261029-night frozen-sample slices (Litolff 8 pages + opening page, Brahms 8 + opening) through ADJUDICATE..EXPORT at this tree (scripts were scratch; `lane_report._live`-style replay, `export.to_musicxml` report).
* **The ranking row is `report["dot_role_not_placed"]["abstained_dot_role_ambiguous"]`** (`ranking/rank_table.py` line 43), not decided dots. Process lesson: a row named "decided, never placed" counted an ABSTENTION key; the label sent a lane after wiring that does not exist (rule 7: who says it is right -- the print).
* **Decided dots are placed.** Litolff sample pages (228 dot rows): decided augmentation 6, all attached to a duration (`used`); decided staccato 137, written 125, 15 `staccato_owning_notehead_not_written` (host head unwritten = lane 2.233's, not this lane's). Brahms (frozen sample, whole report): `augmentation_decided_but_unattached` 346 = the known ledger artifact (section 1 above); `staccato_owning_notehead_not_written` 78 (2.233's).
* **The 71 (Litolff) / 137 (Brahms) `dot_role_ambiguous` dots, by geometry** (nearest un-refused head in the system, gap/dy in head heights): no head in the dot window 59 L / 107 B; head in window with duration decided 6 L / 15 B (all but 6 L + 1 B already carry the dot); head narrowed (existing 2.127 `reconcile_unjoined_dots`) 4 L / 9 B; head owned by another staff 2 L / 5 B; inside a flag box 0 L / 1 B.
* **Print (24 crops, ours, not Sean's):** Litolff 12 of 12 from the biggest bucket are NOT dots: slur/hairpin end tips on a staff line (4), the curl of an *f* / *sf* (3), the full stop of "arco." / "pizz." / "min." (3), a stem tip (2). Litolff 12 of 12 "head in window" are slur-end tips near a half note, not dots. Brahms 12 of 12 from the biggest bucket: 3 are real dots (chord/mid-stem dots right of a head the dot window or head-ownership misses: `25/0/7/1/0`, `25/0/5/0/2`, `14/1/3/1/11`), 9 are not (full stops of "pizz.", *ff* curls, a stem-tip speck, an i-dot of "piu"). So the large majority of the row is JUNK INK boxed as a dot -- a claim-order fault (words, dynamics, arcs claim that ink first; ROADMAP 2.221/2.223), not a missing dot connection. Real unplaced dots are a few per Brahms page and one per ~8 Litolff pages.
* **Built: nothing.** There is no decided verdict that never reaches the file, so a flag would connect no decided answer; anything else would let a guess place a dot (rule 6) or lengthen a note on a slur tip. Existing guard (2.127 narrowing on a plain host) already covers the small real remainder and holds the Litolff slur-tip cases as "narrowed" (4 of 6 window hits seen narrowed are slur tips -- a false narrowing source to re-check under 2.223's arc claim).
* **Recommendation:** re-label ranking row 5 "dots abstained (ambiguous): mostly non-dot ink"; its owner is the page-wide claim (words' full stops, f/sf curls, slur ends claimed before the dot reader), measured as dots-never-boxed-as-dots after 2.223, not a dot connection lane. Count to re-run on the sample after 2.223 lands: `abstained_dot_role_ambiguous` should fall on the Litolff 71.
