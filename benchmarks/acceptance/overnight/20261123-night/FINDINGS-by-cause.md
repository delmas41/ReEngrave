# 20261123-night vs 20261122-night: the changes sorted by the switch that caused them

Read-only agent look, 2026-11-24 (not truth; verdicts only where Sean's judged marks or hand labels
cover a place). Counts are Litolff / Brahms, whole movement, from the saved rows. All mechanisms STAGED.
PROVEN = one-switch re-run of Litolff pages (p6, p13; replay p6/7/13/15); INFERRED = reason words only.
Scripts and one crop: branch `lane-judged-still-wrong-20261124`, `by-cause/` beside this file.

## Process lessons
- A newly written rest moves every later note in its bar; `lane_report.diff_arms` then reports the
  same note as one lost and one gained (about 40 of Litolff's "notes +92 -100").
- Both nights were exported by one tree, so export-only switches (2.337, dropped-head spot marks)
  cannot show in this compare: zero by construction, not measured.
- 2-3 page re-gathers do not reproduce the overnight's letter names (145 of 1541 shared glyphs one
  letter off on p6/p13, missing document context); kind counts and the off-vs-on difference do.

## Per switch
- **2.336 `OMR_ACCIDENTAL_FUSED_INK`** (GATHER `page_accidental_ink`, ADJUDICATE `accidental_owner`,
  EVALUATE `apply_printed_accidental`). PROVEN. Accidentals +142 / +94; pitches changed by an
  accidental ~153 of 185 / ~97 of 191; blue +139 / +98; claims heads 33 / 27, ledger lines 17 / 1,
  arpeggiato boxes 11 / 3 (most of the "printed notes no longer written", with 2.335). Better where
  judged (Sean 12/12 tiles; right->wrong 0). One lost Litolff tie: p6 s1 staff 11 bars 160-161, a
  natural printed before both half notes, both now read, and `arc_kind` re-reads the arc as a slur
  because the stop head has a printed accidental -- disagrees with page-facts ("A tie carries its
  accidental across the barline", Sean 2026-10-30); put to Sean 2026-11-24.
- **2.335 `OMR_SLASH_STEM_CORE`** (GATHER `page_tremolo`). PROVEN small. Written heads taken 9 / 7;
  notes lost 4 / 5. Better on Brahms p0 by Sean's hand label (glyph/0/0/4/3/5 is his tremolo1 box).
- **2.334 + 2.339 rests boxed as other** (ADJUDICATE `family_precision`, `unboxed_rest`). PROVEN.
  Rests +31 +17 / +24 +1; replay: red bars 140 -> 116 with both, 127 -> 116 for 2.339 alone; most of
  the red-bar fall and of the onset-shift noise. Sean's 2.99-review tile 6 wrong -> right; else unjudged.
- **2.340 `OMR_ACCIDENTAL_BOXED_AS_OTHER`**. PROVEN in kind (replay -1 where the record expects -3,
  gap unexplained). Rests -10 / -6. No judged tile covers these.
- **2.341 `OMR_STEM_TIP_FLAG_WHEN_DECLINED`** (ADJUDICATE `rhythm`). PROVEN on Litolff (blue +7 as
  expected). Brahms: 30 quarters now written eighth, 16 blue cleared. Better by Sean's 12 tiles
  (DECISIONS 2026-11-23); 8 Litolff p15 notes decided -> narrowed `beams_ambiguous` unknown.
- **2.324 r11 clef + part-join repair** (no flag). INFERRED. Litolff staff/13/0/9 bass -> alto,
  Cello -> Viola; Brahms staff/3/1/11, staff/10/1/11 bass -> alto, staff/17/1/3 bass -> tenor;
  ~28 / ~76 pitches re-lettered; Litolff +2 unread bars are P11/P12 on p13 staff 10. Roster agrees;
  not judged by Sean.
- **2.342 `OMR_STROKE_SPACE_OWN_STAFF`**. PROVEN small (p6/p13: notes -2, accidentals -1).
- **`OMR_DOT_BY_HEAD_INK`**: no change on the Litolff replay; 10 Brahms dot-role changes INFERRED.

## Not attributed
- Arcs: Litolff slurs +11 -7, Brahms ties +12 -12, slurs +3 -11 have no verdict change at their
  glyph; 2.336 likely (an accidental newly seen at an arc end), proven for the one Litolff pair only.
- Brahms p6 system 1: meter carried 6/8 -> abstained (`carry_outweighed_by_the_bars`), so every part
  restates key/clef at bar 107 and time at bar 116 ("clefs +23, keys +23, meters +12"); bar not traced.
- Litolff P12 notes +36 -17 (copies of the cello staff); Brahms P5 unread marks -27; 10 pitch
  changes, 9 articulations, 7 blue marks with no row change.

## Judged index
- `2.164-review` tile 10 points at the right arc. Sean's 2026-10-17 "Tie" answered "is the box a
  note?" (scored "not a note"); the judged index turned it into an arc-kind claim. The 18 Set H arc
  entries share this; retyping them awaits Sean.
- `lane_report.compare_judged`: a tile narrowed without his answer on both nights is `still_wrong`
  (commit f6a561e68 on the branch above, unlanded).
