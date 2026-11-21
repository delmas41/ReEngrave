# Data-flow audit, 2026-11-21 (ROADMAP 2.331)

Sean, 2026-11-21: "Do we have a single map somewhere that records where everything is read and where it
goes to? We've changed a lot of readers over the past week or two, so I'm worried that there may be other
steps where things might fall through the crack in a similar way."

STAGED path. Two read-only audits by agents READING THE CODE (plus scripts over the source, `qmap.py`,
`readers.py`). Nothing here is a measurement on pages; every item is a place to look, not a count of
wrong notes, until it is priced on real output. The first hand-written map is `reader_map_2331.txt`
(mark -> found from -> claims -> files -> read by -> written, with flag defaults); the generated page
replaces it (step 3).

## A. Clef consumers after 2.324

Fed, same meaning: the clef adjudicator, `restate_pitch`, `move_glyph`, `clef_in_force`, export's clef
changes and red "clef?" marks, the register's header column, `gather_key_object`, the family-block rule,
the staff-identity check, `fill_clef_gap`, the key adjudicator, head/rest refusals, the page accidental
reader's claim list, `lane_report`, the viewer. Traced on Litolff from reader row to the written file
(pitches and `<clef>`): start-of-staff bass 4/1/3, C clef 6/1/3 with a bass change, 11/0/2 with a tenor
change in bar 0, a bass change and an unread C clef (bars red, heads unwritten). Brahms and the print not
checked.

Gaps (handed to `lane-2.324-r8`, each to be verified in the code first):
1. A possible clef may not stop the clef in force: `_strong_g` can never fire (gather sets
   `strong = bool(mid_f and got["passed"])`); a neighbouring staff's box filed as a candidate can stop a
   carry on the wrong staff.
2. A box refused as not-a-clef still files a NARROWED claim that can refuse a stemless head (7 on
   Litolff); `gather_key_signature_claim` and `key_slots.claim_window` still bound the key run by detector
   clef boxes (Litolff 6/1/3 bar 93, off a refused box).
3. `page_accidental_ink.header_claims` keys on `cell == 0`, not the start-of-staff clef (four Litolff
   bar-0 clef changes).
4. The C clef's claim is a rectangle (Brahms p4, two stems held; found by 2.306 r15).
5. Smaller: `gather_key_signature` and the meter slot find the clef themselves before the page-wide pass;
   an undecided header clef leaves a read mid-line clef pitching nothing until INFER; the register's claim
   check covers heads and rests only; Litolff 2/1/3 measure 37, an F3 written plain with 53% of its ink
   inside the bass clef's claim (print not looked at).

## B. Every other reader replaced or changed since 2026-11-07

No second quantity is read while nothing files it. The gaps are one level down -- detail keys, reason
words and claims -- where the check does not look. Worst first:

1. A far head can be written at the wrong pitch, plain: `export._settle_folded_pitches` picks among twin
   boxes by ink position (`hole_ink_position`, `ink_centre_position_float`) and does not exclude far
   heads (page-facts: a far head is placed by its ledger lines only). About 8 folds on five pages.
2. Slurs can be written twice: four writers meet in `export._pair_arcs`; the 2026-11-18 exported files
   hold 17 of 217 Litolff and 55 of 759 Brahms slurs sharing both notes (tree that made them unknown).
3. Arc ink is claimed by a reader that no longer writes arcs: `gather_arc_claim` claims from the old
   `gather_system_arcs` traces; with `OMR_PAGE_LEDGER_OWNS` on those claims refuse heads and rests.
4. Letters inside a word are decided twice: `text.adjudicate_dynamic` never reads
   `claims.letters_of_the_word` (2.303).
5. The old bar-crop beam reader still decides part of the file: `beams_by_stem` feeds
   `export._value_from_its_own_flag`; the beam GROUPING comes from its strokes (2.319 is the open row).
6. `judged._written_subjects` scores a twin box the exporter dropped, so a lost note can score right.
7. Dead: every rule keyed on the reason `beam_discounted_uncertain` (INFER bare-stem rule,
   `bare_stem_confirmable`, `arc_ink_not_beam_decline`, 2.146, 2.170); `Q.PAGE_HEAD`; `Q.DYNAMIC_ANCHOR`;
   docstrings saying "default OFF" for readers that are ON.

Clean by the read: whole-bar rests (2.315), key flats (2.302), voices (2.314), unisons (2.323), one chord
(2.300), the head claim (2.290 step 4), the slash guard (2.327), own-ink accidentals (2.285), hairpins,
word/dynamic claims (2.296/2.301).

Old readers still running beside the new: beam readers A and C (A feeds item 5, C counts flag hooks);
`gather.cluster_marks` and `page_marks.link` (output thrown away); the per-cell head tier in the stroke
owner (overwritten); `gather_system_arcs` with its claim, per-box arc kind and tie-pair verdicts (dropped
at export); `accidental_owner one_ink_absorbed`.

## C. What the check misses, and the change that would catch this class

`reach.survey` counts a `wants` line or an abstention as a producer, so a fact read and declared with no
`observe()` shows as live (how `Q.CLEF_LOCATED` passed); `reach` works per quantity, never per detail key,
reason word or reader name; it counts a producer behind a default-off flag as live and skips the 70
`NOT_A_STAGE` modules; `claim_final` reads `MARK_ONLY` by regex, so its 4 findings describe the flag-off
setting. Change: every quantity that is read needs a real `observe` site live under the default flags,
and every literal reason word a consumer tests must be one its decider can still return.

Not verified anywhere above: nothing was re-adjudicated or re-exported; the review viewer and
`regather_report` were not traced in depth.
