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

## 3. Fix (`OMR_AUG_DOT_JOIN`, default OFF)
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
