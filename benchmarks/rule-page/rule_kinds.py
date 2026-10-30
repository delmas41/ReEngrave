"""The HAND-KEPT half of the rule page (ROADMAP 2.207): what each code-derived rule MEANS and which KIND it is.

The list of rules is derived from the code by `build_rule_page.py`; this file only carries the judgement
about each one, keyed by (decision quantity, reason).  A reason the code declares and this file does not
name is printed on the page as UNSURE / unclassified -- never silently dropped, never guessed -- and a
key here that the code no longer declares fails the test (`test_ink_rules_page.py`).

KINDS (Sean, DECISIONS 2026-10-26, "every ink accounted for ONCE"):
  A  CONVENTION           a real engraving / reading fact; keep; the new path must carry it
  B  ERASURE WORKAROUND   exists because the staff-line eraser shaved or split ink; retires with 2.206
  C  DOUBLE-COUNT         exists because one ink was boxed or measured twice; retires with 2.205 (stroke
                          ownership) or the landed one-ink-one-mark / accidental family (2.186, 2.201)
  D  OTHER                subkind says what: D:honesty (a rule-8 "cannot tell" exit), D:bookkeeping (this
                          decision has nothing to decide here), D:passthrough (an earlier refusal handed on),
                          D:cutoff (a number measured on our two plates -- may only NARROW, CLAUDE s4),
                          D:lookup (catalog / roster / lexicon, not ink)
  U  UNSURE               I could not tell from the code and the docs; listed for Sean at the end
  ok POSITIVE EXIT        the rule reached an answer; not a refusal and not counted as a rule
Mixed cases are put under the kind the evidence favours and say so in the meaning ("also C ...").

Entry:  R(family, quantity, "reason,reason,...", kind, name, meaning, evidence, fate)
"""
from collections import namedtuple

R = namedtuple("R", "family quantity reasons kind name meaning evidence fate")

HEADS, STEMS, BEAMS, RESTS, ACCS = "heads", "stems", "beams and flags", "rests", "accidentals"
KEYS, ARCS, DOTS, TEXT, STRUCT = "key, clef, meter", "arcs", "dots", "text, dynamics and marks", "structure and identity"
FAMILIES = [HEADS, STEMS, BEAMS, RESTS, ACCS, KEYS, ARCS, DOTS, TEXT, STRUCT]

S_LEDGER = "Sean 2026-09-28/29 (page-facts s3)"
S_EIGHTH = "Sean 2026-10-12 (page-facts s1)"
S_ONESTEM = "Sean 2026-10-09, 2.78 (page-facts s1)"
S_STEMTILES = "Sean 2026-10-26, 2.204 tiles (page-facts s1)"
S_KEYORDER = "Sean 2026-10-12 (page-facts s2)"
S_ACCSTAFF = "Sean 2026-10-23 (page-facts s3)"
S_2201 = "Sean 2026-10-26, 2.201 tiles 8 of 9 right"
S_2186 = "Sean 2026-10-22, 2.186 tiles 6/9 vs 1/9"
S_PAIR = "2.205 FINDINGS (parity with the old pair rules 47% / 27%; old rules kept until parity)"
S_ERASE = "2.206 FINDINGS s2 (reader consumes the erased raster)"
S_NONE = "no Sean ruling found; code docstring only"
HUMAN = "Sean's stage-review verdict (3.4)"
RULE8 = "CLAUDE rule 8"

RULES = [
    # ================================================================================== HEADS (and the ownership of anything on a staff)
    R(HEADS, "notehead_is_not_a_notehead", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict outranks every rule",
      "a box Sean struck out in the stage review, or marked as another staff's, is refused first", HUMAN, "kept"),
    R(HEADS, "notehead_is_not_a_notehead", "notehead", "ok", "kept as a notehead", "the box survived every refusal", "-", "-"),
    R(HEADS, "notehead_is_not_a_notehead", "is_a_clef", "C", "clef read on this box's ink", "the clef locator read a clef on the very ink this notehead box sits on (one ink, two boxes)",
      "Sean 2026-09-23 (2.11)", "retires with 2.205 (claims by strokes); the claim register 2.181 covers it meanwhile"),
    R(HEADS, "notehead_is_not_a_notehead", "clipped_fragment", "U", "sliver against the crop edge",
      "a flat sliver flush with the cell's crop edge is a neighbour staff's ink bleeding into the padding, read as a hollow head",
      S_NONE + " (legacy `_drop_clipped_notehead_fragments`)", "open: C if the neighbour's ink is the cause (padded cells), A if it is only a crop edge"),
    R(HEADS, "notehead_is_not_a_notehead", "too_narrow", "U", "black head narrower than 1.0 space",
      "a filled-head box under 1.0 staff space wide is not a head (a head is ~1.3 sp); costs 0 of 103 confirmed heads",
      "page-facts s3 (omr-notehead-width-2026-09)", "open: D:cutoff on two publishers, or B if Brahms' narrow boxes are eraser-shaved (2.206)"),
    R(HEADS, "notehead_is_not_a_notehead", "is_a_dot,on_a_barline,on_the_staffs_leading_barline", "D:cutoff", "box is a dot / a barline",
      "a head-shaped box that is really a dot, a barline or the staff's leading barline", S_NONE, "open"),
    R(HEADS, "notehead_is_not_a_notehead", "tremolo_slash_crosses_stem", "A", "a tremolo slash is not a head",
      "a thick diagonal line crossing one stem is a slash, never an oval head, and it joins no other note (also C: a slash boxed as a head)",
      "Sean 2026-10-15 (page-facts s1, 2.137)", "convention kept; the pair rule retires with 2.205 (" + S_PAIR + ")"),
    R(HEADS, "notehead_is_not_a_notehead", "notehead_is_a_duplicate_box,stacked_head_duplicate", "C", "same head boxed twice",
      "two boxes of one class on one mark (or one head of a stacked group) are one head read twice; the stronger box stays",
      "2.30 / 2.42 measured; Sean 2026-09-30 \"a second is always on opposite sides of the stem\"", "retires with 2.205 (one owner per stroke)"),
    R(HEADS, "notehead_is_not_a_notehead", "same_side_second", "C", "second on the same side (not called)", "superseded by 2.42; no longer wired, kept for regression tests", "Sean 2026-09-30", "dead code; delete with 2.205"),
    R(HEADS, "notehead_is_not_a_notehead", "head_cut_piece", "C", "half note boxed as pieces",
      "a half note on a line is boxed as several pieces; one head keeps the box (also B: the line cuts the head)", "Sean 2026-10-09 (2.73)", "retires with 2.205 (" + S_PAIR + ")"),
    R(HEADS, "notehead_is_not_a_notehead", "belongs_to_a_nearer_staff", "C", "head far from its filed staff, near another",
      "a head far off its filed staff with no ledger rung joining it, and another staff nearer, is that staff's note (dropped, not moved)",
      "Sean 2026-09-28/29 ledger convention (2.7b)", "open: the padded-cell double detection stays until ownership is by strokes (2.205)"),
    R(HEADS, "notehead_is_not_a_notehead", "is_a_meter_digit,is_a_time_signature_digit,on_a_read_meter,inside_the_meter,claimed_by:meter,claim_narrowed:meter", "C", "ink belongs to the printed meter",
      "a head box on the ink of the time signature is the meter's, not a note",
      "Sean 2026-10-20 (meter as one object, 2.177); claim register 2.181", "retires with 2.205 (the meter claims its strokes first)"),
    R(HEADS, "notehead_is_not_a_notehead", "claimed_by:clef,claim_narrowed:clef,claimed_by:leading_column,claim_narrowed:leading_column,claimed_by:key_signature,claim_narrowed:key_signature",
      "C", "ink belongs to a clef / key / leading column", "a head box standing on ink another reading already owns is refused (narrowed when the owner is not sure)",
      "2.181 claimed-area register (default ON); Sean 2026-10-20", "retires with 2.205 (strokes are claimed once)"),
    R(HEADS, "notehead_is_not_a_notehead", "notehead_in_a_key_signature_slot", "A", "no note stands in the key slots",
      "only a clef stands before the key accidentals, so a head box in a key slot is a key accidental", S_KEYORDER, "kept"),
    R(HEADS, "notehead_is_not_a_notehead", "on_a_dynamic_letter", "C", "ink is a dynamic letter",
      "a head or rest box whose ink the second look reads as dynamic letters (sf, f, p) is text", "Sean 2026-10-13 (\"sf should be read as a dynamic - it is letters\", 2.107)", "retires with 2.205 (letters claim their strokes)"),
    R(HEADS, "notehead_is_not_a_notehead", "is_a_beam_piece,is_a_rest_twin,on_a_rest,is_a_rest_shape,is_an_arc_tail,on_another_symbols_box,off_staff_glyph", "C", "head box on ink that is another mark",
      "a head box that is really a beam piece, a rest's twin box, a rest, a tie tail, or any other box's ink", S_PAIR, "retires with 2.205"),
    R(HEADS, "notehead_is_not_a_notehead", "no_staff_geometry", "D:honesty", "no staff lines to measure against", "the cell has no staff geometry, so no geometric rule may speak", RULE8, "kept"),

    R(HEADS, "notehead_is_an_eighth_rest", "rest8th_shape", "ok", "narrow box is an eighth rest", "a box refused as too narrow whose own ink is an eighth rest's blob", "Sean 2026-10-11 (2.80b tile)", "-"),
    R(HEADS, "notehead_is_an_eighth_rest", "no_ink_under_box", "B", "no ink left under a narrow box",
      "the erased raster holds no ink under the box, so the rest cannot be recognised (eighth rests lose ink to the eraser: Brahms 714 -> 252 boxes)",
      "2.206 FINDINGS s1 table (eighth/16th rest row)", "retires with 2.206 (measure after the fix)"),
    R(HEADS, "notehead_is_an_eighth_rest", "claimed_by_another_class", "C", "ink already owned by another class", "the ink is another mark's, so it is not offered to the rest reader", "2.181", "retires with 2.205"),
    R(HEADS, "notehead_is_an_eighth_rest", "not_rest_shaped,ink_already_read_as_a_glyph,not_refused_as_too_narrow,no_shape_reading", "D:bookkeeping", "nothing for the narrow-rest rule to do",
      "the box was not refused as too narrow, or its ink is not rest-shaped / already read", S_NONE, "kept"),
    R(HEADS, "notehead_is_an_eighth_rest", "shape_cannot_tell", "D:honesty", "shape does not decide", "rest-shaped ink that is neither clearly a rest nor a head: abstain", RULE8, "kept"),

    R(HEADS, "glyph_owner", "human_owner", "A", "a human's owner verdict wins", "Sean's stage-review ownership verdict is final", HUMAN, "kept"),
    R(HEADS, "glyph_owner", "ledger_note_first,ledger_direction,ledger_owner_density,stem_toward_staff", "A", "the ledger lines name the owner",
      "a far note has ledgers toward its OWN staff and none toward the other; they are authoritative and nearness never overrides them", S_LEDGER, "kept"),
    R(HEADS, "glyph_owner", "ledger_witnesses_disagree,far_no_rungs,ledger_refuted,ledger_all_refuted", "A", "no far note without a ledger",
      "there is no far note with no ledger line, so 'no rungs either way' is OUR failure: abstain and count it", "Sean 2026-09-29 (page-facts s3)", "kept; the missed-rung cause is open (B if the eraser cut the rung)"),
    R(HEADS, "glyph_owner", "stem_disagrees", "D:honesty", "stem points the other way", "the stem direction contradicts the ledger winner: abstain", RULE8, "kept"),
    R(HEADS, "glyph_owner", "staff_band,staff_band_no_box,no_contest", "A", "inside one staff's band", "a glyph standing inside a staff's own band belongs to it", "page-facts s3 (cell pad, contest)", "kept"),
    R(HEADS, "glyph_owner", "hairpin_separates", "A", "a hairpin sits under its staff", "a note between a staff and the hairpin beneath it belongs to that staff", "page-facts s1", "kept"),
    R(HEADS, "glyph_owner", "ladder,range_veto", "A", "ledger completeness, then the instrument's range", "of two staves contesting a note, the one with the complete ledger ladder, then the one whose written range holds it", "page-facts s3", "kept"),
    R(HEADS, "glyph_owner", "distance", "D:cutoff", "nearest staff", "the last resort: the nearer staff wins (about 94% of contests resolve here)", "page-facts s3 (nearness is only a hint)", "open: the contest exists because cells are padded; ownership by strokes (2.205) should shrink it"),
    R(HEADS, "glyph_owner", "tied,no_evidence", "D:honesty", "staves tie / no evidence", "two staves tie on every witness: abstain", RULE8, "kept"),

    R(HEADS, "notehead_position", "ledger_position", "ok", "far head placed by its ledgers", "the head's step is counted off its printed ledger rungs", S_LEDGER, "-"),
    R(HEADS, "notehead_position", "ledger_not_read", "A", "ledgers not read: abstain and count",
      "a far head whose rungs we could not count is OUR failure, not 'no ledgers'; the rung ink is read on the erased raster so part of the cause is B",
      "Sean 2026-09-29 (page-facts s3)", "convention kept; the cause is open (2.206 may shrink it)"),
    R(HEADS, "notehead_position", "no_page_shape,no_staff_geometry,no_mask", "D:honesty", "no geometry to count against", "the page shape, staff geometry or mask is missing", RULE8, "kept"),

    R(HEADS, "ledger_is_not_a_ledger", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "a ledger box Sean struck out", HUMAN, "kept"),
    R(HEADS, "ledger_is_not_a_ledger", "ledger_line", "ok", "kept as a ledger line", "the box survived every refusal", "-", "-"),
    R(HEADS, "ledger_is_not_a_ledger", "inside_the_staff,on_a_staff_line", "A", "a ledger line stands outside the staff", "a box inside the staff or on a staff line is a staff line, not a rung; also C: the staff line boxed as a ledger", "page-facts s3; module docstring", "kept"),
    R(HEADS, "ledger_is_not_a_ledger", "tall_not_a_rung,no_head_on_the_rung,ink_under_the_rung", "D:cutoff", "rung shape / rung with no head / ink under it", "a rung is short, has a head on or through it, and no ink hides under it (measured on three records)", S_NONE, "open"),
    R(HEADS, "ledger_is_not_a_ledger", "rung_without_boxed_head", "A", "a rung without a boxed head", "a ledger line exists for a note; no boxed head means a note we did not see: abstain and count", "Sean 2026-10-01 (\"if there are stems then there are notes\", 2.179) by analogy", "kept"),
    R(HEADS, "ledger_is_not_a_ledger", "no_staff_geometry", "D:honesty", "no staff geometry", "cannot measure", RULE8, "kept"),

    R(HEADS, "head_ink_is_a_rest", "rest8th_head_ink,rest8th_head_ink_displaced,restQuarter_head_ink", "ok", "a head box on rest ink is a rest", "a head box refused as a rest shape: the ink cluster is read as the rest", "ROADMAP 2.145 (flag OFF)", "-"),
    R(HEADS, "head_ink_is_a_rest", "no_head_refused_on_the_ink", "D:bookkeeping", "no refused head on this ink", "the domain is every ink cluster; most have no refused head", "-", "kept"),

    R(HEADS, "notehead_is_a_whole_rest", "shape_and_position_agree", "ok", "a whole rest, not a head", "a filled rectangle hanging under a line is a whole rest", "Sean 2026-09-11 (\"an actual quarter note, not a quarter note rest\")", "-"),
    R(HEADS, "notehead_is_a_whole_rest", "not_rest_shaped,not_where_a_whole_rest_can_hang,no_page_frame,no_staff_geometry", "D:bookkeeping", "head is not a whole rest", "the box is an oval, or sits where no whole rest hangs (most noteheads)", "-", "kept"),

    R(HEADS, "unboxed_ink_is_a_rest", "rest8th_shape,restQuarter_shape", "ok", "unboxed ink is a rest", "rest-sized ink the detector never boxed is an eighth or quarter rest", "Sean 2.96 tiles 7-9 (2.99)", "-"),
    R(HEADS, "unboxed_ink_is_a_rest", "already_read_as_a_glyph", "D:bookkeeping", "ink already carries a box", "the common case: the 'unboxed' ink already has a box, so the rest reader has nothing to add. This is the one-ink-once test PASSING, not a workaround", "2.99", "kept; the claim becomes ownership at 2.205"),
    R(HEADS, "unboxed_ink_is_a_rest", "stem_stroke_not_a_rest,thin_stroke_not_a_rest", "B", "a stem or a thin stroke is not a rest",
      "thin rest strokes split by the eraser look like a stem; the shape test refuses them (UNBOXED_REST_SHAPE reads the erased raster)", S_ERASE, "retires with 2.206 (measure after the fix)"),
    R(HEADS, "unboxed_ink_is_a_rest", "claimed_by_another_class", "C", "ink claimed by another class", "claimed-area register", "2.181", "retires with 2.205"),
    R(HEADS, "unboxed_ink_is_a_rest", "in_the_header,head_beside_it", "A", "not a rest in the header / beside a head", "no rest stands in the header (clef, key, meter); a head beside it makes it a stem or part of the head", S_KEYORDER, "kept"),
    R(HEADS, "unboxed_ink_is_a_rest", "shape_cannot_tell,no_ink_reading,no_shape_reading", "D:honesty", "shape does not decide", "rest-sized ink whose shape is neither an eighth nor a quarter rest, or no reading was filed", RULE8, "kept"),

    R(HEADS, "empty_bar_whole_rest", "whole_rest_found_by_search", "ok", "whole rest found in a boxless bar", "a filled, whole-rest-shaped piece of ink hanging from a line, measured locally", "Sean 2026-10-12 (2.98 print-confirmed 12/12)", "-"),
    R(HEADS, "empty_bar_whole_rest", "not_found_by_search", "B", "search finds no whole rest",
      "an empty-looking bar where the search found no rest: whole-rest blocks are cut to a strip by the eraser (whole/half rest rows of the 2.206 table)", "2.206 FINDINGS s1 + s2 (EMPTY_BAR_REST_SEARCH)", "retires with 2.206 (measure after the fix); the bar stays marked unread until then"),
    R(HEADS, "empty_bar_whole_rest", "no_mask,no_staff_geometry", "D:honesty", "nothing to search", "no mask or geometry", RULE8, "kept"),

    R(HEADS, "unread_mark", "unread_mark", "ok", "bar holds ink nobody accounted for", "a corroborated column of ink with no box: the BAR is marked unread (red), nothing invented", "CLAUDE s1 definition of done; Sean 2026-10-13 \"I don't want any hidden\"", "kept"),
    R(HEADS, "unread_mark", "no_mark,no_ink_component_rows,no_onset_column,no_page_frame", "D:bookkeeping", "no unaccounted ink here", "the common case", "-", "kept"),

    # ================================================================================== STEMS
    R(STEMS, "head_stem", "one_stem,stem_by_reach,stem_by_side,stem_by_flush,stem_by_one_per_head", "ok", "which stem a head stands on", "the head touches one stem on its engraving side", S_STEMTILES, "-"),
    R(STEMS, "head_stem", "no_stem", "U", "head with no stem found",
      "Heads with no stem found are common (see fires). 2.167 found 33 of 40 sampled 'no stem' real notes had a stem the finder refused (C: a false rest/flag box ate it; B: stem cut at a staff line on the erased raster; A: a whole note has none)",
      "Sean 2026-10-18 (2.167); 2.169 landed", "open: mixed A / B / C; 2.204 stems-from-strokes waits for 2.205"),
    R(STEMS, "head_stem", "unison_two_voices,two_stems", "A", "a head with a stem each way is two notes", "a head carrying one stem up and one down is two voices on one head", "Sean 2026-10-19 (2.175), convention assumed", "kept"),
    R(STEMS, "head_stem", "no_evidence", "D:honesty", "no evidence", "-", RULE8, "kept"),

    R(STEMS, "stem_head_contact", "all_touch_a_head,some_touch_no_head", "ok", "does every stem touch a head", "a stem that touches no head is listed", "Sean 2026-10-11 (\"All stems should be connected to a notehead\", 2.87)", "-"),
    R(STEMS, "stem_head_contact", "no_stem,no_heads_read", "D:honesty", "no stem / no heads read", "the cell has strokes and no head box, or no stem: says nothing", RULE8, "kept"),

    R(STEMS, "stem_direction", "stem_projection,beam_mate", "ok", "stem up or down", "direction from the stem's tip beyond the outer head, or from the beam mate; up -> right, down -> left", S_STEMTILES, "-"),
    R(STEMS, "stem_direction", "no_stem", "D:passthrough", "no stem found", "passes on the head_stem refusal", "-", "follows head_stem"),
    R(STEMS, "stem_direction", "stems_disagree", "U", "readers disagree on direction", "the stem finders disagree; the stroke stem reader (2.204) is built to settle it", "Sean 2026-10-26 tiles: today's finder was right on chords", "open (2.204 after 2.205)"),
    R(STEMS, "stem_direction", "no_evidence", "D:honesty", "no evidence", "-", RULE8, "kept"),

    R(STEMS, "stem_value", "stem_agrees,stem_value_from_evidence", "ok", "one stem, one value", "every note on one stem shares one written value", S_ONESTEM, "-"),
    R(STEMS, "stem_value", "lone_head,not_a_member", "D:bookkeeping", "head not on a shared stem", "a head with no companions or not a member of the stem's group", "-", "kept"),
    R(STEMS, "stem_value", "no_stem", "D:passthrough", "no stem", "passes on the head_stem refusal", "-", "follows head_stem"),
    R(STEMS, "stem_value", "ambiguous_stem", "U", "stem ambiguous", "the head could be on either of two stems", S_NONE, "open"),
    R(STEMS, "stem_value", "stem_levels_unread,stem_values_open,stem_unread", "B", "stem's beam level not read",
      "the beam/flag levels on the stem were not read; reads stem-tip ink on the erased raster", S_ERASE, "retires with 2.206 (measure after the fix)"),
    R(STEMS, "stem_value", "hollow_head_on_a_beamed_stem,stem_dots_disagree", "A", "a hollow head cannot sit on a beamed stem", "a hollow head on a beamed stem, or members that disagree on dots, contradict one stem one value", S_ONESTEM, "kept"),

    R(STEMS, "unison_voices", "two_notes", "ok", "two notes on one head", "both voices read and agree", "Sean 2026-10-19 (2.175, assumed)", "-"),
    R(STEMS, "unison_voices", "not_a_unison", "D:bookkeeping", "not a unison head", "the domain is every head", "-", "kept"),
    R(STEMS, "unison_voices", "head_refused,duration_missing,dotted_head,in_a_tuplet,head_fill_disagrees,one_voice_unmarked,shared_flag,stems_not_read,voice_beams_range,flag_off", "D:honesty", "unison not fully read", "one voice unread, dotted, in a tuplet or sharing a flag: abstain with each voice's reading", RULE8, "kept"),

    R(STEMS, "voices", "one_voice,one_voice_sums,two_voices_same_beat,two_voices_separated_and_full", "A", "voices follow the bar", "the voice split is chosen so the bar math adds up; one voice when it sums", "Sean 2026-09-29 (\"obviously 1 voice because the measure math adds up\")", "kept"),
    R(STEMS, "voices", "no_voice_convention_fits,nothing_to_split", "D:honesty", "no voice rule fits", "-", RULE8, "kept"),
    R(STEMS, "event", "x_clustered", "A", "a chord is one onset", "glyphs of a bar that sound together are grouped by x", "ROADMAP Q.EVENT 2026-09-09", "kept"),
    R(STEMS, "event", "nothing_to_group", "D:bookkeeping", "nothing to group", "-", "-", "kept"),
    R(STEMS, "onset_column", "columns_read", "ok", "events of different staves at one instant", "records; never overturns", "-", "-"),
    R(STEMS, "onset_column", "single_staff,no_page_frame,nothing_to_align", "D:bookkeeping", "nothing to align", "-", "-", "kept"),

    # ================================================================================== BEAMS AND FLAGS (and the duration they decide)
    R(BEAMS, "duration", "head_and_marks", "ok", "value from head, flag and beam", "a note's length from its head class and the marks on its stem", S_EIGHTH, "-"),
    R(BEAMS, "duration", "stem_tip_reads_no_beam,hooks_counted,hollow_head_bare_stem", "ok", "no beam / hooks counted / bare hollow stem", "read at the stem tip", S_EIGHTH, "-"),
    R(BEAMS, "duration", "beam_discounted_uncertain", "U", "a beam box with no beam-shaped stroke",
      "narrowed to eighth|quarter when a detector beam box does not look like a beam. 2.202's cause on the 9 judged heads: 4 a beam thinned by the erase (B), 3 head/ledger/accidental ink read as a beam and 2 a slur start read as a hook (C). The biggest Brahms narrowing",
      "Sean 2026-10-25 milestone tiles, 2.202 cause (FINDINGS s5b)", "open: B and C both"),
    R(BEAMS, "duration", "beams_ambiguous,beam_certain_not_joined,tip_readers_disagree", "U", "beam present but not tied to this stem",
      "the beam-stem join reader (reads the erased raster) cannot tell; 2.155 fixed one cause (stem cut at a bar edge)", "Sean 2026-10-16 (2.155 \"there is no gap\")", "open: B suspected"),
    R(BEAMS, "duration", "flags_disagree,flag_ink_unread", "B", "flag ink unread / readers disagree",
      "the flag hook at the stem tip is read from stem-tip ink on the erased raster, with cut-offs tuned there (STEM_TIP_HOOKS_CLOSE heals 'thin stripes')", S_ERASE, "retires with 2.206 (measure after the fix)"),
    R(BEAMS, "duration", "head_fill_from_ink", "B", "filled or hollow decided from ink",
      "the head's fill is measured on the erased raster (`ink_net`); a head in a space loses its top 0.17-0.2 sp (Brahms 908 -> 13 boxes losing ink after the fix); 94 / 227 narrowed", S_ERASE, "retires with 2.206 (measure after the fix)"),
    R(BEAMS, "duration", "whole_class_filled_or_stemmed,whole_class_on_a_stem,whole_class_filled_on_a_stem", "A", "a whole note has no stem and is hollow", "a whole-class head that is filled or stemmed contradicts its class", "Sean 2026-10-09 (2.78: a whole note never has a stem)", "kept"),
    R(BEAMS, "duration", "open_head_flag_contradiction", "A", "a hollow head carries no flag", "an open head with a flag read on its stem is a contradiction: narrow", "page-facts s1", "kept"),
    R(BEAMS, "duration", "second_hollow_confirmed,second_hollow_unclear,second_only_hollow,second_hollow_refuted_by_ink,second_hollow_contradicted_by_marks,second_only_no_independent_evidence", "U", "second detector for hollow heads",
      "the second look for hollow heads (2.114) and how it is weighed against the first: two readings of one ink", "ROADMAP 2.114", "open: C-flavoured (a second reading of the same ink)"),
    R(BEAMS, "duration", "rest_class,unknown_head", "ok", "rest read from its class", "a rest's value comes straight from its class", "Sean 2026-10-12 (2.98)", "-"),
    R(BEAMS, "duration", "unreadable_rest,rest_slot_contradicts_class", "U", "rest class and slot disagree", "a rest whose class (8th, quarter) and the slot it hangs in disagree", S_NONE, "open"),
    R(BEAMS, "duration", "rest_stands_where_no_rest_hangs", "U", "rest where no rest hangs", "a box called a rest in a position no rest is printed", S_NONE, "open"),
    R(BEAMS, "duration", "owned_by_another_staff", "C", "the neighbour staff's padded crop boxed this note",
      "a cell is padded 4-6 spaces, so it boxes the next staff's note; the copy is dropped, never a witness. The biggest rule by firing",
      "Sean 2026-10-21 (2.186, \"each cell claims its own\"); page-facts s3", "partly landed 2.186 (owner-first for accidentals); heads and durations retire with 2.205"),
    R(BEAMS, "duration", "not_a_note_mark,refused_as_a_notehead", "D:passthrough", "box refused as a notehead", "passes on the notehead refusal", "-", "follows the notehead refusals"),
    R(BEAMS, "duration", "no_notehead", "D:bookkeeping", "no notehead", "-", "-", "kept"),

    R(BEAMS, "tuplet_ratio", "digit,bracket", "A", "a tuplet exists only where its marking is seen", "a printed 3 (or bracket) over a group makes it a tuplet; never from arithmetic", "Sean 2026-10-13 (page-facts s1)", "kept"),
    R(BEAMS, "tuplet_ratio", "wrong_member_count,ambiguous_bracket", "D:honesty", "marker does not fit the group", "-", RULE8, "kept"),
    R(BEAMS, "tuplet_ratio", "no_marker", "D:bookkeeping", "no marker", "-", "-", "kept"),
    R(BEAMS, "flag_is_not_a_flag", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(BEAMS, "flag_is_not_a_flag", "flag", "ok", "kept as a flag", "-", "-", "-"),
    R(BEAMS, "flag_is_not_a_flag", "in_a_key_signature_slot,claimed_by:key_signature", "A", "a flag box in the key slots is a key accidental", "-", S_KEYORDER, "kept"),
    R(BEAMS, "tuplet_marker_is_not_a_marker", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(BEAMS, "tuplet_marker_is_not_a_marker", "tuplet_marker", "ok", "kept as a tuplet marker", "-", "-", "-"),

    # ================================================================================== RESTS
    R(RESTS, "rest_is_not_a_rest", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(RESTS, "rest_is_not_a_rest", "rest", "ok", "kept as a rest", "-", "-", "-"),
    R(RESTS, "rest_is_not_a_rest", "rest_is_a_duplicate_box", "C", "same rest boxed twice", "two rest boxes on one mark are one rest read twice", "2.15 measured; 2.186 within a family", "landed 2.186 (one ink one mark); the old rule is kept for parity"),
    R(RESTS, "rest_is_not_a_rest", "one_ink_merged", "C", "two classes of one rest merged", "the stronger class stays, the weaker is carried as a candidate", S_2186, "landed 2.186"),
    R(RESTS, "rest_is_not_a_rest", "rest_has_a_stem,rest_stroke_into_a_head,rest_is_a_barline,rest_is_a_slashed_stem,rest_overlaps_a_notehead", "C", "rest box that is really a stem, a head or a barline",
      "a rest never has a stem; a box whose ink runs into a head, is a barline or a slashed stem is another mark's ink (rest_has_a_stem 124 / 45)", S_PAIR, "retires with 2.205 (parity 54 of 58 for rest_has_a_stem)"),
    R(RESTS, "rest_is_not_a_rest", "rest_touches_two_staff_lines,rest_off_center,rest_narrower_than_its_class", "A", "a rest hangs from or sits on ONE line, in the bar's middle",
      "a whole or half rest touches exactly one line; a whole rest is near the bar's centre; a rest has its class's width", "2.33 six refusals; Sean 2026-09-11", "kept"),
    R(RESTS, "rest_is_not_a_rest", "rest_outside_its_staff", "A", "a rest stays within its staff band", "farther outside the staff than the class is ever printed", "2.33", "kept"),
    R(RESTS, "rest_is_not_a_rest", "whole_rest_ink_not_a_block,claim_narrowed:arc", "C", "whole rest judged by its own ink (OMR_WHOLE_REST_HANGS)", "a whole rest is a block: a box whose only ink is a vertical or a curve is refused; a block-shaped stroke an arc box claims just as well is written GUESSED, never READ",
      "Sean 2026-10-29 (a displaced whole rest in a multi-voice bar is real: no staff-position band)", "convention kept (A); flag OFF by default"),
    R(RESTS, "rest_is_not_a_rest", "rest_clipped_by_crop", "U", "rest flush against the crop edge", "a notehead sliced by the cell's crop edge reads as a rest", S_NONE, "open: C if neighbour-staff bleed, A if only a crop edge"),
    R(RESTS, "rest_is_not_a_rest", "rest_on_a_dynamic_letter", "C", "rest on a dynamic letter", "letters read as a rest", "Sean 2026-10-13 (2.107)", "retires with 2.205"),
    R(RESTS, "rest_is_not_a_rest", "rest_in_a_key_signature_slot,rest_is_a_meter_digit,inside_the_meter,claimed_by:meter,claimed_by:clef,claimed_by:leading_column,claimed_by:key_signature,claim_narrowed:clef,claim_narrowed:meter,claim_narrowed:leading_column,claim_narrowed:key_signature", "C",
      "rest box on a clef, key or meter", "no rest stands in the key slots or where the time signature stands; the claimed-area register refuses a rest on that ink",
      "Sean 2026-10-12 (page-facts s2) for the convention; 2.181 register for the mechanism", "convention kept (A); the mechanism retires with 2.205"),

    # ================================================================================== ACCIDENTALS
    R(ACCS, "accidental_is_not_an_accidental", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(ACCS, "accidental_is_not_an_accidental", "accidental", "ok", "kept as an accidental", "-", "-", "-"),
    R(ACCS, "accidental_owner", "immediately_right_same_position", "A", "an accidental alters the note to its right at its own height", "the head stands to the accidental's right and at its height", "page-facts s3; Sean 2026-10-23", "kept"),
    R(ACCS, "accidental_owner", "owned_by_another_staff,head_belongs_to_a_nearer_staff", "C", "accidental on another staff", "the neighbour staff's padded crop boxed the same ink: a copy, not a second owner", S_ACCSTAFF + "; " + S_2186, "landed 2.186 / 2.201 (owner staff first)"),
    R(ACCS, "accidental_owner", "one_ink_absorbed", "C", "accidental box absorbed into its stronger twin", "one ink, one mark: this box's ink was merged into another accidental box", S_2186, "landed 2.186"),
    R(ACCS, "accidental_owner", "is_a_key_signature_marker", "A", "this accidental is in the key signature", "a mark after the clef in the fixed order is the key's, not a note's", S_2201 + "; " + S_KEYORDER, "landed 2.201 (role decided by position)"),
    R(ACCS, "accidental_owner", "on_a_rest", "C", "accidental on a rest's ink", "an eighth rest's bulb boxed as a double-sharp", "Sean 2026-10-22 (2.192): all 9 stopped were rests", "landed 2.192"),
    R(ACCS, "accidental_owner", "no_candidate,ambiguous_height,ownership_undecided,no_unit,no_evidence,refused_not_an_accidental", "D:honesty", "no single note to alter", "no head to the right at that height, or two equally near (372 / 677 no_candidate)", RULE8, "kept"),
    R(ACCS, "keysig_marker_is_not_a_marker", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(ACCS, "keysig_marker_is_not_a_marker", "keysig_marker", "ok", "kept as a key marker", "-", "-", "-"),

    # ================================================================================== KEY, CLEF, METER
    R(KEYS, "clef", "scored", "ok", "clef read", "-", "-", "-"),
    R(KEYS, "clef", "margin_below_floor,no_candidates,all_candidates_excluded", "D:honesty", "clef not sure enough", "no clef above the floor: narrowed or abstained; INFER may fill from other systems", RULE8, "kept"),
    R(KEYS, "key_signature", "markers,fitted_no_markers", "ok", "key read", "-", "-", "-"),
    R(KEYS, "key_signature", "needs_clef", "A", "only a clef stands before the key", "the key cannot be read without the clef (it moves the slots)", S_KEYORDER, "kept"),
    R(KEYS, "key_signature", "run_fits_no_slot_table,mixed_marker_kinds,natural_markers,too_many_markers,no_run,keysig_fit_unknown,no_cell_scale", "A", "accidentals in the fixed order",
      "key accidentals come in the fixed flat/sharp order; a slot out of order is a place to look again", S_KEYORDER, "kept; naturals at a change belong to the key (Sean 2026-10-20)"),
    R(KEYS, "key_signature", "disagrees_with_system,disagrees_with_document,disagrees_with_part", "A", "a key is a fact of the system; parts transpose", "a staff's key that disagrees with its system / part / document is held, not overwritten; transposing staves print their own key", "Sean 2026-09-23, 2026-10-22 (page-facts s2)", "kept"),
    R(KEYS, "key_signature", "no_evidence", "D:honesty", "no evidence", "-", RULE8, "kept"),
    R(KEYS, "part_key", "read", "ok", "key of a part", "-", "-", "-"),
    R(KEYS, "part_key", "no_staff_read_a_key", "D:honesty", "no staff read a key", "-", RULE8, "kept"),
    R(KEYS, "system_key", "read", "ok", "key of a system", "-", "-", "-"),
    R(KEYS, "system_key", "one_staff_only,no_staff_read_a_key", "D:honesty", "too few staves read a key", "-", RULE8, "kept"),
    R(KEYS, "meter", "voted,carried,carried_uncontested,derived_from_bars,change_only", "A", "a meter is printed on every staff and holds", "a meter change is printed at one bar on every staff and holds until the printed return", "Sean 2026-09-28 and 2026-09-30 (page-facts s1, s2)", "kept"),
    R(KEYS, "meter", "no_agreement,no_evidence,too_few_staves_read_it,carry_not_corroborated,carry_source_uncorroborated,bars_name_a_length_without_a_form,opening_disagrees_with_prior_cautionary,meter_return_not_read,meter_change_digits_misread,template_ocr_disagree", "D:honesty", "meter not agreed", "the staves disagree or only the bars speak: never switch silently", "Sean 2026-09-28 (a missed return: label and mark)", "kept"),
    R(KEYS, "meter", "carry_outweighed_by_the_bars", "A", "the bars overturn a carried meter", "the carry is weighed by the bars; where overturned a return was missed", "Sean 2026-09-28", "kept"),

    # ================================================================================== ARCS
    R(ARCS, "arc_is_not_an_arc", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(ARCS, "arc_is_not_an_arc", "arc", "ok", "kept as an arc", "-", "-", "-"),
    R(ARCS, "arc_is_not_an_arc", "ink_is_a_staff_line,ink_is_a_barline", "U", "an arc box that is a staff line or a barline", "a box with no curved ink and a staff line through it is a staff line; a narrow tall one is a barline. C if 2.205 makes lines and barlines owners of their strokes; otherwise a plain detector false positive (D)", "ROADMAP 2.60", "open"),
    R(ARCS, "arc_is_not_an_arc", "in_a_key_signature_slot,claimed_by:key_signature", "A", "an arc box in the key slots is a key accidental", "-", S_KEYORDER, "kept"),
    R(ARCS, "arc_kind", "tie,slur", "ok", "tie or slur", "of two stacked arcs the nearer the heads is the tie; a tie's heads are at one position", "page-facts s1 (2.75)", "-"),
    R(ARCS, "arc_kind", "same_pitch_accidental_unread,stack_slur_over_two_same_pitch_notes", "A", "same pitch needs the same accidental", "a tie needs two same-pitch heads, so an unread accidental stops the call", "Sean 2026-10-01 (tie convention)", "kept"),
    R(ARCS, "arc_kind", "no_arc_box,no_evidence", "D:honesty", "no arc box / evidence", "-", RULE8, "kept"),
    R(ARCS, "arc_owner", "hugs_noteheads,no_better_staff,no_rival_staff,ends_on_noteheads", "A", "an arc belongs to the staff whose heads it hugs", "an arc is over its notes, and the staff it hugs owns it", "page-facts s1; ROADMAP arc attribution", "kept"),
    R(ARCS, "arc_owner", "no_page_frame,no_evidence", "D:honesty", "-", "-", RULE8, "kept"),
    R(ARCS, "tie_pair", "paired,paired_by_system_arc", "ok", "tie joins two heads", "found by the heads just outside its two ends", "Sean 2026-10-01 (\"next to each other regardless of barlines and the same pitch\", 2.54)", "-"),
    R(ARCS, "tie_pair", "not_adjacent,no_pair_at_one_position,more_than_one_pair,no_start_head,no_stop_head,no_head_near_the_arc,spans_a_whole_bar", "A", "a tie joins adjacent same-pitch heads", "nothing between the heads in time, same staff position", "Sean 2026-10-01 (page-facts s1)", "kept"),
    R(ARCS, "tie_pair", "enters_from_previous_system,runs_off_the_system", "A", "a tie may cross a system break", "the other end is on the next / previous system", "page-facts s1", "kept"),
    R(ARCS, "tie_pair", "not_a_tie,not_an_arc", "D:bookkeeping", "arc is a slur or not an arc", "the domain is every arc (`not_an_arc` includes staff-line boxes)", "-", "kept"),
    R(ARCS, "tie_pair", "no_page_frame,no_evidence", "D:honesty", "-", "-", RULE8, "kept"),

    # ================================================================================== DOTS
    R(DOTS, "dot_role", "right_of_and_level_with_a_head,centred_and_offset_from_a_head,right_of_a_head_at_its_dot_step,wedge_pointing_at_a_head,beside_a_head_in_its_dot_space", "A", "augmentation right of the head, staccato above or below", "an augmentation dot stands right of its note in a SPACE; a staccato centred above/below", "Sean 2026-10-14 (\"Always in a space\", page-facts s1)", "kept"),
    R(DOTS, "dot_role", "dot_role_ambiguous,no_glyph_box,no_cell_staff_space,no_notehead_or_rest_in_cell,wedge_without_a_head,wedge_points_away", "D:honesty", "dot role not decided", "-", RULE8, "kept"),
    R(DOTS, "dot_role", "on_a_barline,on_a_stroke", "C", "dot on a barline or a stroke", "a dot box that is the end of a barline or another stroke", S_NONE, "retires with 2.205"),
    R(DOTS, "dot_role", "owned_by_another_staff", "C", "dot on another staff's note", "-", "2.186", "retires with 2.205"),

    # ================================================================================== TEXT, DYNAMICS, MARKS
    R(TEXT, "dynamic_is_not_a_dynamic", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(TEXT, "dynamic_is_not_a_dynamic", "dynamic", "ok", "kept as a dynamic letter", "-", "-", "-"),
    R(TEXT, "dynamic", "spelled,no_letters", "ok", "letters spelled into a dynamic", "-", "Sean 2026-10-13 (2.107 letters)", "-"),
    R(TEXT, "dynamic", "owned_elsewhere", "A", "a dynamic belongs to one staff band", "73% of letters stand in their staff's band, 24% in the band above: ownership is by the band", "dynamic ownership measurement (18 pages, 9 publishers)", "kept"),
    R(TEXT, "dynamic", "unspellable,no_page_frame,reader_unavailable", "D:honesty", "letters do not spell a word", "-", RULE8, "kept"),
    R(TEXT, "dynamic_anchor", "anchored,some_marks_unanchored,no_marks", "A", "a dynamic starts on a note", "if on a note it starts there; between notes it affects the next", "Sean 2026-10-09", "kept"),
    R(TEXT, "direction", "in_lexicon,no_words", "ok", "direction word in the lexicon", "only words the lexicon names are accepted", "CLAUDE: lexicon gate load-bearing", "-"),
    R(TEXT, "direction", "held_back,reader_unavailable,out_of_scope,no_detections", "D:honesty", "word not accepted", "-", RULE8, "kept"),
    R(TEXT, "printed_bar_number", "read", "ok", "bar number read", "-", "-", "-"),
    R(TEXT, "printed_bar_number", "no_reading,not_numeric,ambiguous_multiple_readings", "D:honesty", "bar number unread", "-", RULE8, "kept"),
    R(TEXT, "articulation_is_not_an_articulation", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(TEXT, "articulation_is_not_an_articulation", "articulation", "ok", "kept as an articulation", "-", "-", "-"),
    R(TEXT, "articulation_is_not_an_articulation", "ledger_between_staff_and_note,head_owner_unread,no_staff_geometry", "C", "a tenuto dash that is a ledger line", "a dash outside the staff with a head on or beyond it is that staff's ledger line", "ROADMAP 2.84", "retires with 2.205"),
    R(TEXT, "articulation_owner", "nearest_on_notehead_side,other_staff_bar_empty,stem_tip_of_long_chord", "A", "an articulation sits on the notehead side", "opposite the stem; with two voices, on the stem side", "Sean 2026-10-09 (page-facts s1, 2.12f)", "kept"),
    R(TEXT, "articulation_owner", "heads_about_equally_near,no_notehead,no_side_declared,no_evidence,level_with_head,stem_direction_unread,stem_contradicts_class_side", "D:honesty", "no single note", "-", RULE8, "kept"),
    R(TEXT, "articulation_owner", "owned_by_another_staff", "C", "mark on another staff's note", "-", "2.186", "retires with 2.205"),
    R(TEXT, "ornament_owner", "nearest_on_declared_side,nearest_either_side", "D:cutoff", "ornament goes to the nearest head", "within a distance constant its author declared unmeasured", "code docstring (`_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS`)", "open: a cut-off with no measurement"),
    R(TEXT, "ornament_owner", "no_notehead,no_evidence,owned_by_another_staff", "D:honesty", "-", "-", RULE8, "kept"),
    R(TEXT, "fermata_owner", "contains_the_mark,nearest_in_bar", "A", "a fermata belongs to what is sounding under it", "paired by x alone, never by pitch (Beethoven 5: 36 of 36)", "ROADMAP export gap 6", "kept"),
    R(TEXT, "fermata_owner", "no_carrier,no_evidence,owned_by_another_staff", "D:honesty", "-", "-", RULE8, "kept"),
    R(TEXT, "wedge_anchor", "nearest_either_side", "A", "a hairpin is between its notes", "a slur is drawn over notes, a hairpin between them", "page-facts s1", "kept"),
    R(TEXT, "wedge_anchor", "no_anchor,no_page_frame,no_evidence", "D:honesty", "-", "-", RULE8, "kept"),
    R(TEXT, "ottava_owner", "above,below", "A", "an ottava bracket belongs to the staff it hugs", "-", "PLACEMENT-CONVENTIONS.md", "kept"),
    R(TEXT, "ottava_owner", "no_staff_lines", "D:honesty", "-", "-", RULE8, "kept"),
    R(TEXT, "pedal_owner", "grand_staff_lower_staff", "A", "a pedal mark belongs to the lower staff of a grand staff", "-", "PLACEMENT-CONVENTIONS.md", "kept (inert on orchestral)"),
    R(TEXT, "pedal_owner", "no_brace", "D:honesty", "no brace", "-", RULE8, "kept"),
    R(TEXT, "arpeggiato_is_not_an_arpeggiato", "human_not_a_symbol,human_other_staff", "A", "a human's box verdict", "-", HUMAN, "kept"),
    R(TEXT, "arpeggiato_is_not_an_arpeggiato", "arpeggiato", "ok", "kept", "-", "-", "-"),
    R(TEXT, "arpeggiato_is_not_an_arpeggiato", "in_a_key_signature_slot,claimed_by:key_signature", "A", "an arpeggiato box in the key slots is a key accidental", "-", S_KEYORDER, "kept"),

    # ================================================================================== STRUCTURE AND IDENTITY
    R(STRUCT, "measure_partition", "read,cautionary_tail_not_a_bar", "A", "bars from barlines; a cautionary meter governs no bar", "-", "Sean 2026-09-28", "kept"),
    R(STRUCT, "measure_partition", "no_barline", "D:honesty", "-", "-", RULE8, "kept"),
    R(STRUCT, "staff_group", "bracket_block,block_unavailable", "A", "brackets group staves", "-", "page-facts s4", "kept"),
    R(STRUCT, "group_symbol", "brace_family,bracket", "A", "a brace needs one player on two staves", "a bracket block of two is not a grand staff; the instrument decides brace vs bracket", "page-facts s4 (Brahms wind pairs)", "kept"),
    R(STRUCT, "group_symbol", "no_identity,no_group", "D:honesty", "-", "-", RULE8, "kept"),
    R(STRUCT, "staff_ordinal", "read,no_evidence", "ok", "staff order", "-", "-", "-"),
    R(STRUCT, "system_membership", "counted,no_evidence", "ok", "which staves make a system", "-", "-", "-"),
    R(STRUCT, "system_staff_count", "counted,no_evidence", "ok", "staves in a system", "-", "-", "-"),
    R(STRUCT, "instrument", "label,roster,score_order,orchestral_bass", "A", "a staff is named by its label, roster and neighbours", "a worn label is named only from the catalog roster + the system's gap + one lexicon neighbour; never by widening the lexicon", "page-facts s4; Sean 2026-10-12", "kept"),
    R(STRUCT, "instrument", "not_in_lexicon,no_evidence,vetoed_by_the_work_roster", "D:lookup", "label not in the lexicon / roster", "-", "page-facts s4", "kept"),
    R(STRUCT, "part_partition", "slot,ordinal,deduced_anchor", "A", "a part is a slot; strings always five", "the string family always includes all five; four lines means the bass doubles or enters later", "Sean 2026-09-22 (page-facts s4)", "kept"),
    R(STRUCT, "part_partition", "no_evidence", "D:honesty", "-", "-", RULE8, "kept"),
    R(STRUCT, "slot_index", "full_lineup,named,paired_by_name,paired_by_crook,paired_by_bare_crook,family_block,forced_by_constraints", "A", "a word between braced staves names every staff", "the word names the WHOLE brace, each staff keeping its own crook", "Sean 2026-10-12 (\"the bracket makes them all horns\", page-facts s4)", "kept"),
    R(STRUCT, "slot_index", "no_reference,no_ordinal,reference_names_nothing,unnamed_in_short_system,not_in_reference,ambiguous_pairing,family_block_not_forced", "D:honesty", "slot not matched", "-", RULE8, "kept"),
    R(STRUCT, "movement_spans", "detected,human_spans_supplied", "ok", "movement boundary found", "-", "ROADMAP 4.2b; convention assumed", "-"),
    R(STRUCT, "movement_spans", "too_few_systems,no_boundary_detected", "D:honesty", "no boundary detected", "-", RULE8, "kept"),
    R(STRUCT, "endings", "read", "ok", "1st/2nd endings read", "-", "ROADMAP 2.85", "-"),
    R(STRUCT, "endings", "no_bracket,no_cell_boxes,span_not_at_barlines,numeral_unread,numeral_readers_disagree,no_first_and_second_ending,endings_not_adjacent", "A", "an ending is a hooked bracket at barlines with its numeral", "-", S_NONE, "kept"),
    R(STRUCT, "repeat_barline", "read", "ok", "repeat read", "-", "ROADMAP 2.85", "-"),
    R(STRUCT, "repeat_barline", "no_reading,no_staff_count,too_few_staves", "D:honesty", "too few staves saw the dots", "-", RULE8, "kept"),
]

STUB_REASON = "not_implemented"   # every decision carries a declared stub exit; never a rule


# ======================================================================================================
# EVALUATE rules (`evaluate.RULES`): what a settled fact FORCES.  Keyed by the rule function name, which is
# also the `decider` the record carries.
# Entry: name -> (family, kind, meaning, evidence, fate)
# ======================================================================================================
EVALUATE_RULES = {
    "restate_pitch": (HEADS, "A", "a pitch follows from the clef and the staff position", "page-facts s2 (clef then position)", "kept"),
    "size_measure_rest": (RESTS, "A", "a lone whole rest is the bar, sized to the meter", "Sean 2026-10-12 (2.98, 12 of 12)", "kept"),
    "share_stem_value": (STEMS, "A", "every note on one stem shares its written value", S_ONESTEM, "kept"),
    "reconcile_chord_duration": (BEAMS, "A", "a narrowed chord member takes the value of the one decided member", S_ONESTEM, "kept"),
    "size_reinstated_rest": (RESTS, "A", "a narrow box proved an eighth rest is sized as one", "Sean 2026-10-11 (2.80b)", "kept"),
    "size_unboxed_rest": (RESTS, "A", "unboxed rest ink proved an eighth / quarter rest is sized as one", "Sean 2.96 tiles 7-9 (2.99)", "kept"),
    "size_head_ink_rest": (RESTS, "A", "a head box proved rest ink is sized as a rest", "ROADMAP 2.145 (flag OFF)", "kept"),
    "reconcile_duration": (BEAMS, "A", "bar arithmetic may CONFIRM a value the page supports (+/-1 level, bar lands exactly), never supply one", "Sean 2026-10-12/17 (CLAUDE s4)", "kept"),
    "move_glyph": (HEADS, "C", "the loser of a cross-staff contest is dropped and the pitch restated on the winner", "page-facts s3 (a resolved contest drops the loser)", "retires with 2.205 (no contest if each stroke has one owner)"),
    "respell_accidental": (ACCS, "A", "a pitch's letter is respelled by the key in force", "page-facts s2", "kept"),
    "apply_printed_accidental": (ACCS, "A", "a printed accidental alters its note and later same-step notes in the bar", "page-facts s3", "kept"),
    "name_part": (STRUCT, "D:lookup", "a staff takes its name from its part", "page-facts s4", "kept"),
    "join_parts": (STRUCT, "D:lookup", "which staves are one part (declared stub)", "ROADMAP identity", "stub"),
    "reinstate_rest_between_staves": (RESTS, "C", "a rest refused as outside its staff but in a real cross-staff contest is reinstated", "2.33; 2.186", "retires with 2.205"),
    "pair_word_and_dynamic": (TEXT, "A", "a direction word and a dynamic in one cell form one marking", "Sean 2026-10-09 (dynamics)", "kept"),
}

# ======================================================================================================
# INFER rules (`infer.RULES`): what is most LIKELY -- always labelled blue (GUESSED).  Keyed by the
# inference value; the record decider is `infer:<value>`.
# ======================================================================================================
INFER_RULES = {
    "collapse_duration_by_column": (BEAMS, "D:infer", "other staves' notes at the same onset column vote a narrowed duration down to one of its own candidates", "Sean 2026-10-12 (INFER; blue)", "kept"),
    "collapse_duration_to_barline": (BEAMS, "D:infer", "a note that runs to the barline takes the value its column witnesses agree on", "Sean 2026-10-12 (INFER; blue)", "kept"),
    "collapse_narrowed_by_bar": (BEAMS, "D:infer", "the bar chooses among a narrowed note's own candidates when every other note is decided and the bar fills", "Sean 2026-10-17 (the two exceptions, CLAUDE s4)", "kept"),
    "collapse_bare_stem_by_bar": (BEAMS, "D:infer", "a bare stem narrowed by an uncertain beam takes the value that fills a bar of decided notes", "Sean 2026-10-17 (CLAUDE s4)", "kept"),
    "collapse_arc_ink_not_beam": (BEAMS, "C", "a stem tip whose only stroke is an arc's is unbeamed", "2.202 cause: slur starts read as hooks", "retires with 2.205 (the arc owns its stroke first)"),
    "collapse_slot_index_to_family_block": (STRUCT, "D:infer", "a short unnamed block takes the one slot left in the family", "Sean 2026-09-22 (strings always five)", "kept"),
    "fill_clef_gap": (KEYS, "D:infer", "an unread clef takes the clef its slot has in other systems", "Sean 2026-09-17 (identity)", "kept"),
    "fill_part_key": (KEYS, "D:infer", "an unread key takes the document majority, re-transposed by this staff's own offset", "Sean 2026-09-23; transposing staves 2026-10-22", "kept"),
    "collapse_dynamic_by_ink": (TEXT, "D:infer", "a dynamic with one unread letter takes the completion the ink supports", S_NONE, "kept"),
}

# ======================================================================================================
# Post-passes that run INSIDE adjudicate (not registered decisions) and stamp their own decider.
# ======================================================================================================
PASSES = {
    "reconcile_group_owners": (HEADS, "C", "one printed mark boxed twice has ONE owner: the copy in the owner's cell decides", "ROADMAP 2.58b (flag OMR_MARK_GROUPS)", "retires with 2.205"),
    "reconcile_articulation_twins": (TEXT, "C", "one printed articulation, two owners: the loser is dropped, never relocated", "Sean 2026-10-11 (2.12m)", "retires with 2.205"),
    "reconcile_dot_owners": (DOTS, "C", "a dot's owner is its note's owner", "ROADMAP 2.59 (flag OFF)", "retires with 2.205"),
    "reconcile_unjoined_dots": (DOTS, "A", "a dot SEEN beside a decided-plain note narrows the note instead of leaving it plain", "Sean 2026-10-14 (2.127 default ON)", "kept"),
}

# ======================================================================================================
# GUARD MODULES: staged/ and adjudicators/ files that are NOT registered decisions but hold readers and
# guards.  name -> (family, kind, meaning, evidence, fate)
# ======================================================================================================
MODULES = {
    "adjudicators/claimed_by.py": (HEADS, "C", "the ONE consult of the claimed-area register: a head or rest box on ink a clef / leading column / key already owns is refused", "Sean 2026-10-20 claimed-area plan (2.181, default ON)", "retires with 2.205"),
    "claims.py": (HEADS, "C", "the claimed-area register: who owns which ink (clef, leading column, key, meter)", "2.181", "retires with 2.205"),
    "adjudicators/inside_meter.py": (HEADS, "C", "a box on the printed meter's ink is the meter's", "Sean 2026-10-20 (2.177, flag OFF)", "retires with 2.205"),
    "meter_object.py": (KEYS, "C", "the printed meter measured as ONE object (two digits blocked out together)", "Sean 2026-10-20 (2.177)", "retires with 2.205"),
    "key_object.py": (KEYS, "C", "the printed key signature measured as ONE system object", "ROADMAP 2.187", "retires with 2.205"),
    "adjudicators/head_on_mark.py": (HEADS, "C", "a head box standing on ink another reading already owns", "ROADMAP 2.176 (default ON)", "retires with 2.205"),
    "adjudicators/letter_cover.py": (TEXT, "C", "a head or rest box whose ink the second look read as dynamic letters", "Sean 2026-10-13 (2.107)", "retires with 2.205"),
    "letter_look.py": (TEXT, "D:gather", "reads dynamic letters the detector never boxed (second look at head/rest ink)", "Sean 2026-10-13 (\"sf ... it is letters\")", "kept"),
    "one_ink.py": (ACCS, "C", "ONE INK, ONE MARK: two classes of one family on one ink merge, the stronger stays, the weaker is a candidate", S_2186, "landed 2.186"),
    "accidental_shape.py": (ACCS, "C", "a shape check on a merged accidental ink chooses among the detector's own candidates", "Sean 2026-10-22 (2.190 tiles 7/9)", "landed 2.190"),
    "adjudicators/key_slots.py": (KEYS, "A", "the key-signature SLOTS of a header and what may not stand in them (no rest or note before the key)", S_KEYORDER, "kept"),
    "adjudicators/aug_dot_join.py": (DOTS, "A", "a dot seen beside a note must not leave it written plain", "Sean 2026-10-14 (2.127)", "kept"),
    "adjudicators/unison_two.py": (STEMS, "A", "a head with a stem each way is TWO notes", "Sean 2026-10-19 (2.175), convention assumed", "kept"),
    "export_unison.py": (STEMS, "A", "EXPORT of a unison head as two notes", "Sean 2026-10-19 (2.175)", "kept"),
    "one_note.py": (BEAMS, "D:infer", "the one-note correction: a bar holding one event takes the value that fills it (blue)", "Sean 2026-10-17/18 (CLAUDE s4 exceptions)", "kept"),
    "arcs_system.py": (ARCS, "C", "arcs read ONCE per staff across the system, then their own stroke erased (a cell cuts an arc in two)", "Sean 2026-10-18 (2.166, default ON)", "retires with 2.205 (arcs own their strokes)"),
    "rest_ink.py": (RESTS, "C", "does a rest box's own ink run on into a notehead? (measure for the rest/head pair rule)", "Sean 2026-10-16 (2.150b)", "retires with 2.205"),
    "head_oval.py": (HEADS, "C", "does a notehead box hold a head-shaped oval? (boxes at a bar's left edge were tie ends or barlines)", "Sean 2026-10-17 (2.164)", "retires with 2.205"),
    "second_hollow.py": (HEADS, "U", "a SECOND detector at GATHER for hollow heads only", "ROADMAP 2.114", "open: a second reading of the same ink"),
    "stem_end_heads.py": (STEMS, "A", "a stem with no head is a note we have not seen: look at its end", "Sean 2026-10-01 (2.179 \"if there are stems then there are notes\")", "kept"),
    "detector_views.py": (HEADS, "D:gather", "the detector looks at each symbol family at its own size", "Sean 2026-10-19 (2.172)", "kept"),
    "geometry.py": (HEADS, "A", "the standard notehead box: all regular heads are the same size", "Sean 2026-09-29 (2.39)", "kept"),
    "bar_length.py": (BEAMS, "A", "a bar's length from the durations standing in it", "Sean 2026-10-17 (2.162/2.165)", "kept"),
    "movements.py": (STRUCT, "A", "a meter or key carry never crosses a movement boundary", "ROADMAP 4.2", "kept"),
    "margins.py": (STRUCT, "D:honesty", "every threshold refusal records how close it came", "Sean 2026-10-12 (inference principles)", "kept"),
    "groups.py": (STRUCT, "D:honesty", "several witnesses to ONE fact and whether they agree (a second witness must be from a different source)", "page-facts s2", "kept"),
}

# Files that are pipeline plumbing, derived checks, reports or the exporter -- they hold no ink rule.
INFRA = {
    "__init__.py", "__main__.py", "adjudicate.py", "brakes.py", "budget.py", "capture.py", "cell_map.py", "check.py", "claim_readout.py", "check_helpers.py",
    "consequences.py", "evaluate.py", "export.py", "gather.py", "gather_coverage.py", "health.py", "infer.py", "inferences.py",
    "inventory.py", "judged.py", "lane_report.py", "legacy.py", "letter_look_report.py", "lilypond.py", "meaning.py",
    "pipeline.py", "positions.py", "producers.py", "reach.py", "readout.py", "record.py", "record_coverage.py", "record_io.py",
    "record_slim.py", "regather_report.py", "trace.py", "weight_routing.py", "wiring.py",
}
