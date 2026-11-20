# 2.325 inventory: numeric cut-offs and shape constants in STAGED readers and the shared readers they call

Read-only audit, 2026-11-19, tree at `lane-2.324-clef-pagewide` 9932a136b (the worktree this ran in). Scratch file; nothing in the repository was changed.

**How this table was made.** An AST pass over `tools/omr/staged/**/*.py` (minus `staged/review/` and the measuring tools: check, readout, report, judged*, lane_report, trace, inventory, health, record_io/slim, reach, budget, *coverage, one_test, claim_readout, regather_report, lilypond, movements, __main__) and the shared readers staged imports (line_detection, clef_geometry, clef_locator, time_signature_locator, template_matcher, staff_header, measure_extractor, header_ink, pitch_resolver, staff_line_removal, key_signature_template/locator/geometry, key_consensus, hairpin_detection, direction_text, direction_lexicon, staff_detector, page_wide, voicing, instruments, input_domain, arcs_system, page_arcs). It collects every UPPER_CASE module or class constant holding a number or a tuple of numbers, and every numeric dataclass-config field. NOT collected: numbers written inline in code (105 float literals in comparisons other than 0/0.5/1 were counted, mostly in page_arcs / gather / measure_extractor, and not classified) and lowercase function defaults.

**Columns.** unit: sp = staff spaces (almost always the cell's or the staff's own measured spacing, so scale-free), px = pixels (E unless the comment says the frame is the reduced / canonical one), ratio = share of a box, of ink, or of another mark on the same page, count. plates = plates the comment names as the source (L Litolff/Beethoven 5, B Brahms/Breitkopf; blank = none named). cls / effect are ASSIGNED BY KEYWORD from the comment beside the constant (see the method note at the end) and are rough; the rows hand-checked for the ranked list are marked `*` and carry a hand verdict in `hand`.

## clef (90; B 13, C 59, D 8, E 1, n/a 9)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| clef_geometry.py:133 | `ClefGeometryConfig.max_residual = 0.35` | ? |  | C | ? | max_residual: float = 0.35 |  |
| clef_locator.py:85 | `ClefLocatorConfig.header_frac = 0.3` | ratio |  | B | ? | header_frac: float = 0.30 left fraction of the start cell to search |  |
| clef_locator.py:92 | `ClefLocatorConfig.max_start_spaces = 6.0` | sp |  | C | ? | max_start_spaces: float = 6.0 |  |
| clef_locator.py:96 | `ClefLocatorConfig.min_width_spaces = 0.55` | sp |  | C | ? | min_width_spaces: float = 0.55 | * rank 3: C, REFUSES (also stops the search) |
| clef_locator.py:97 | `ClefLocatorConfig.max_width_spaces = 4.5` | sp |  | C | ? | max_width_spaces: float = 4.5 |  |
| clef_locator.py:100 | `ClefLocatorConfig.min_height_spaces = 2.2` | sp |  | C | ? | min_height_spaces: float = 2.2 |  |
| clef_locator.py:101 | `ClefLocatorConfig.max_height_spaces = 5.0` | sp |  | C | ? | max_height_spaces: float = 5.0 |  |
| clef_locator.py:136 | `ClefLocatorConfig.clef_family_min_height_spaces = 3.3` | sp |  | C | ? | clef_family_min_height_spaces: float = 3.3 | * rank 3: D, NARROWS (occupancy veto); Litolff 22 / Breitkopf 60 / engraved 3, both sides counted |
| clef_locator.py:137 | `ClefLocatorConfig.clef_family_max_height_spaces = 4.7` | sp |  | C | ? | clef_family_max_height_spaces: float = 4.7 |  |
| clef_locator.py:138 | `ClefLocatorConfig.min_symmetry = 0.7` | ratio |  | B | ? | min_symmetry: float = 0.70 the C-clef signature — see _refine_symmetry_axis | * rank 3: C, REFUSES a C clef; 08-28 (46ca8c64b), Beethoven 5 Litolff sweep; feeds Q.CLEF today |
| clef_locator.py:156 | `ClefLocatorConfig.min_symmetry_mezzosoprano = 0.9` | ratio |  | B | ? | min_symmetry_mezzosoprano: float = 0.90 |  |
| clef_locator.py:160 | `ClefLocatorConfig.axis_refine_spaces = 0.35` | sp |  | C | ? | axis_refine_spaces: float = 0.35 |  |
| clef_locator.py:161 | `ClefLocatorConfig.min_ink_fraction = 0.1` | ratio |  | B | REFUSES | min_ink_fraction: float = 0.10 of the cluster's bbox — rejects stray rules |  |
| clef_locator.py:162 | `ClefLocatorConfig.cluster_gap_spaces = 0.6` | sp |  | C | DECIDES | cluster_gap_spaces: float = 0.6 x-gap that still counts as one glyph |  |
| clef_locator.py:218 | `ClefLocatorConfig.cluster_y_gap_spaces = 1.0` | sp |  | C | ? | cluster_y_gap_spaces: float / None = 1.0 |  |
| clef_locator.py:219 | `ClefLocatorConfig.min_component_area_spaces = 0.02` | sp |  | C | REFUSES | min_component_area_spaces: float = 0.02 speck filter, in (staff space)² |  |
| clef_locator.py:220 | `ClefLocatorConfig.vertical_rule_max_width_spaces = 0.5` | sp |  | C | REFUSES | vertical_rule_max_width_spaces: float = 0.5 thinner ⇒ a rule, not a glyph |  |
| clef_locator.py:221 | `ClefLocatorConfig.vertical_rule_min_height_spaces = 2.0` | sp |  | C | ? | vertical_rule_min_height_spaces: float = 2.0 |  |
| clef_locator.py:228 | `ClefLocatorConfig.heavy_rule_max_width_spaces = 1.2` | sp |  | C | ? | heavy_rule_max_width_spaces: float = 1.2 |  |
| clef_locator.py:229 | `ClefLocatorConfig.heavy_rule_min_height_spaces = 5.0` | sp |  | C | ? | heavy_rule_min_height_spaces: float = 5.0 |  |
| clef_locator.py:232 | `ClefLocatorConfig.min_ink_height_spaces = 0.2` | sp |  | C | ? | min_ink_height_spaces: float = 0.2 |  |
| clef_locator.py:236 | `ClefLocatorConfig.dot_min_size_spaces = 0.22` | sp |  | C | ? | dot_min_size_spaces: float = 0.22 |  |
| clef_locator.py:237 | `ClefLocatorConfig.dot_max_size_spaces = 0.75` | sp |  | C | ? | dot_max_size_spaces: float = 0.75 |  |
| clef_locator.py:248 | `ClefLocatorConfig.dot_max_height_spaces = 0.75` | sp |  | C | ? | dot_max_height_spaces: float = 0.75 |  |
| clef_locator.py:249 | `ClefLocatorConfig.dot_min_aspect = 0.65` | ratio |  | B | ? | dot_min_aspect: float = 0.65 |  |
| clef_locator.py:250 | `ClefLocatorConfig.dot_max_aspect = 1.5` | ratio |  | B | ? | dot_max_aspect: float = 1.5 |  |
| clef_locator.py:252 | `ClefLocatorConfig.dot_right_fraction = 0.55` | ratio |  | B | ? | dot_right_fraction: float = 0.55 dots sit right of the glyph's middle |  |
| clef_locator.py:284 | `ClefLocatorConfig.dot_clear_right_fraction = 1.0` | ratio |  | B | ? | dot_clear_right_fraction: float = 1.0 |  |
| clef_locator.py:285 | `ClefLocatorConfig.dot_clear_max_height_spaces = 1.25` | sp |  | C | ? | dot_clear_max_height_spaces: float = 1.25 |  |
| clef_locator.py:286 | `ClefLocatorConfig.dot_clear_max_aspect = 2.2` | ratio |  | B | ? | dot_clear_max_aspect: float = 2.2 |  |
| clef_locator.py:290 | `ClefLocatorConfig.dot_clear_min_aspect = 0.65` | ratio |  | B | ? | dot_clear_min_aspect: float = 0.65 |  |
| clef_locator.py:323 | `ClefLocatorConfig.dot_max_dx_spaces = 0.3` | sp |  | C | ? | dot_max_dx_spaces: float = 0.30 |  |
| clef_locator.py:324 | `ClefLocatorConfig.dot_min_dy_spaces = 0.6` | sp |  | C | ? | dot_min_dy_spaces: float = 0.60 |  |
| clef_locator.py:325 | `ClefLocatorConfig.dot_max_dy_spaces = 1.5` | sp |  | C | ? | dot_max_dy_spaces: float = 1.50 |  |
| clef_locator.py:339 | `ClefLocatorConfig.dot_search_right_spaces = 1.5` | sp |  | C | ? | dot_search_right_spaces: float = 1.5 |  |
| clef_locator.py:349 | `ClefLocatorConfig.analysis_spacing_px = 22.0` | px |  | E | ? | analysis_spacing_px: float = 22.0 |  |
| clef_locator.py:354 | `ClefLocatorConfig.staff_band_spaces = 2.2` | sp |  | C | ? | staff_band_spaces: float = 2.2 |  |
| clef_locator.py:384 | `ClefLocatorConfig.staff_line_min_length_spaces = 4.0` | sp |  | C | ? | staff_line_min_length_spaces: float = 4.0 |  |
| clef_locator.py:410 | `ClefLocatorConfig.staff_left_max_spaces = 4.0` | sp |  | C | ? | staff_left_max_spaces: float = 4.0 |  |
| key_signature_locator.py:154 | `KeySignatureLocatorConfig.max_start_after_clef_spaces = 2.0` | sp |  | C | ? | max_start_after_clef_spaces: float = 2.00 |  |
| key_signature_locator.py:157 | `KeySignatureLocatorConfig.clef_min_height_spaces = 3.6` | sp |  | C | ? | clef_min_height_spaces: float = 3.60 |  |
| key_signature_locator.py:175 | `KeySignatureLocatorConfig.clef_anchor_max_start_spaces = 5.5` | sp |  | C | ? | clef_anchor_max_start_spaces: float = 5.50 |  |
| key_signature_locator.py:176 | `KeySignatureLocatorConfig.clef_anchor_min_height_spaces = 1.8` | sp |  | C | ? | clef_anchor_min_height_spaces: float = 1.80 |  |
| key_signature_template.py:82 | `KeySignatureTemplateConfig.clef_min_score = 0.4` | ratio |  | B | ? | clef_min_score: float = 0.40 |  |
| staged/adjudicators/clef.py:61 | `CONF_HIGH = 0.6` | conf |  | C | ? | CONF_HIGH = 0.60 (A-CLEF-1) |  |
| staged/adjudicators/clef.py:62 | `CONF_LOW = 0.3` | conf |  | C | ? | CONF_LOW = 0.30 (A-CLEF-1) |  |
| staged/adjudicators/clef.py:64 | `W_DETECTOR_HIGH = 3.0` | ? |  | n/a | ? | W_DETECTOR_HIGH = 3.0 (A-CLEF-2) |  |
| staged/adjudicators/clef.py:65 | `W_DETECTOR_MID = 1.5` | ? |  | n/a | ? | W_DETECTOR_MID = 1.5 |  |
| staged/adjudicators/clef.py:66 | `W_DETECTOR_LOW = 0.4` | ? |  | n/a | ? | W_DETECTOR_LOW = 0.4 |  |
| staged/adjudicators/clef.py:67 | `W_LOCATOR = 2.0` | ? |  | n/a | DECIDES | W_LOCATOR = 2.0 the CV C-clef locator, per crop it read |  |
| staged/adjudicators/clef.py:68 | `W_SPECIALIST = 1.0` | ? |  | n/a | ? | W_SPECIALIST = 1.0 |  |
| staged/adjudicators/clef.py:69 | `W_CARRY = 1.5` | ? |  | n/a | ? | W_CARRY = 1.5 this part's own reading on another system |  |
| staged/adjudicators/clef.py:70 | `W_INSTRUMENT = 1.0` | ? |  | n/a | ? | W_INSTRUMENT = 1.0 the instrument's expected clef |  |
| staged/adjudicators/clef.py:71 | `W_DOSSIER = 4.0` | ? |  | n/a | ? | W_DOSSIER = 4.0 external truth, when admitted |  |
| staged/adjudicators/clef.py:102 | `W_C_FAMILY = 1.5` | ? |  | n/a | ? |  What a `clefC` detection is worth as support for a C clef the LOCATOR named. It cannot name one itself. (A-CLEF-5) W_C_FAMILY = 1.5 |  |
| staged/adjudicators/clef.py:519 | `MID_SYSTEM_CLEF_X_PX = 1000.0` | px |  | C | ? | MID_SYSTEM_CLEF_X_PX = 1000.0 45 staff spaces in the cell frame (22.4 px a space) | * rank 19: C (cell-frame px, ~45 sp per its comment), REFUSES a header vote; Litolff p6 case (e8197afaf) |
| staged/adjudicators/head_on_mark.py:53 | `CLEF_COVER_MIN = 0.9` | ratio |  | B | ? |  Share of the head box a clef box must cover. CLEF_COVER_MIN = 0.9 |  |
| staged/adjudicators/head_on_mark.py:55 | `CLEF_WINDOW_SPACES = 6.0` | sp |  | C | ? |  A clef box counts only where it starts within this many staff spaces of its cell's left edge. CLEF_WINDOW_SPACES = 6.0 |  |
| staged/adjudicators/key_slots.py:82 | `MAX_START_AFTER_CLEF_SPACES = 2.0` | sp |  | C | ? |  `key_signature_locator.max_start_after_clef_spaces` (2.00). MAX_START_AFTER_CLEF_SPACES = 2.0 |  |
| staged/box_kind.py:97 | `CLEF_BAR_SP = 0.35` | sp |  | C | ? | CLEF_BAR_SP = 0.35 |  |
| staged/box_kind.py:98 | `CLEF_BAR_LEN_SP = 2.5` | sp |  | C | ? | CLEF_BAR_LEN_SP = 2.5 |  |
| staged/box_kind.py:99 | `CLEF_NEAR_SP = 0.6` | sp |  | C | ? | CLEF_NEAR_SP = 0.6 |  |
| staged/claims.py:42 | `CLEF_BOX_MIN_HEIGHT_SPACES = 2.0` | sp |  | C | ? |  a detector clef box claims only where it is clef-sized (2.144: the short wide `clef*` boxes, 0.5-1.1 sp, lie on arcs and clutter) CLEF_BOX_MIN_HEIGHT_SPACES = 2.0 |  |
| staged/claims.py:47 | `CLEF_WINDOW_SPACES = 6.0` | sp | L | D | DECIDES |  a detector clef box is READ only in a system's FIRST bar, starting this close to the bar's left edge: a system opens with a clef (convention) and the detector boxed it t |  |
| staged/claims.py:59 | `CLEF_BOX_COVER_MIN = 0.9` | ratio |  | B | ? |  ... and a stemless head box this much inside a clef box that starts within `CLEF_WINDOW_SPACES` of its bar's left edge, scored by the detector at least as high as the he |  |
| staged/claims.py:98 | `CLEF_SLOT_REACH_SPACES = 4.0` | sp |  | C | ? |  the slot reaches this far above the top line and below the bottom line (a G clef's curl and a bass clef's dots; the detector's own clef-sized boxes measure 6-7 sp tall)  |  |
| staged/claims.py:100 | `CLEF_SLOT_PAD_SPACES = 0.75` | sp |  | C | REFUSES |  past the widest clef the system's other staves show (they stand at one x), the slot ends this far on (a clef wider than any sibling's still fits; past it stands a key ac |  |
| staged/claims.py:102 | `CLEF_SLOT_MIN_SPACES = 1.0` | sp |  | C | ? |  a slot narrower than this is no clef (a staff whose clef offset and key claim nearly touch) CLEF_SLOT_MIN_SPACES = 1.0 |  |
| staged/clef_pagewide.py:39 | `C_AXIS_SHIFT_SPACES = 0.45` | sp |  | C | REFUSES |  the named line is searched this close to the bar's middle (under half a space: never a neighbouring line) C_AXIS_SHIFT_SPACES = 0.45 |  |
| staged/clef_pagewide.py:41 | `C_BAR_MIN_WIDTH_SPACES = 0.45` | sp | L | D | ? |  the C clef's thick bar: this wide (staff spaces; a barline is ~0.3, a stem ~0.1; Litolff's small C clef bar measures 0.7-0.8) C_BAR_MIN_WIDTH_SPACES = 0.45 | * rank 2: D, REFUSES the C clef; Litolff only (7e8194dc9, 2.251); fails on Brahms 0.434/0.438 (2.324 r1) |
| staged/clef_pagewide.py:42 | `C_BAR_MAX_WIDTH_SPACES = 1.3` | sp |  | C | ? | C_BAR_MAX_WIDTH_SPACES = 1.3 |  |
| staged/clef_pagewide.py:44 | `C_BAR_MIN_RUN_SPACES = 3.0` | sp |  | C | ? |  ... each column holding one unbroken ink run this long (the small C clef spans 3.6-3.7 sp, a full one ~4.3) C_BAR_MIN_RUN_SPACES = 3.0 | * rank 2: D/C, REFUSES; Litolff small C clef 3.6-3.7 |
| staged/clef_pagewide.py:46 | `C_BAR_REACH_SPACES = 1.3` | sp |  | C | ? |  ... that starts and ends within this of the staff's top / bottom line (a barline or a bracket runs on to the next staff) C_BAR_REACH_SPACES = 1.3 |  |
| staged/clef_pagewide.py:48 | `C_GLYPH_GAP_SPACES = 0.35` | sp |  | C | ? |  the glyph ends at the first gap this wide (staff spaces) right of the bar (between the thick and thin bars stands at most ~0.3) C_GLYPH_GAP_SPACES = 0.35 |  |
| staged/clef_pagewide.py:56 | `G_REACH_SPACES = 0.6` | sp |  | C | ? |  a G clef box reaches past the staff by this much above and below G_REACH_SPACES = 0.6 |  |
| staged/clef_pagewide.py:58 | `G_PAST_SPACES = [1.4, 2.2]` | sp |  | C | NARROWS |  a bar candidate is a G clef's spine where ink stands in BOTH bands this far past the staff (staff spaces, from .. to) beside it G_PAST_SPACES = (1.4, 2.2) |  |
| staged/clef_pagewide.py:62 | `G_TAIL_SPACES = [0.6, 1.6]` | sp | L | D | ? |  ... or the G clef's tail: ink in the band this far below the bottom line (from .. to, staff spaces), beside the spine, at least this share (measured on Litolff pp. 2-16: |  |
| staged/clef_pagewide.py:65 | `F_TOP_REACH_SPACES = 1.0` | sp |  | C | ? |  an F clef box's top stands this close to the top line F_TOP_REACH_SPACES = 1.0 |  |
| staged/clef_pagewide.py:80 | `F_BODY_LEFT_REACH_SPACES = 0.6` | sp |  | C | ? |  the F body: pieces starting at most this far (staff spaces) left of its largest piece F_BODY_LEFT_REACH_SPACES = 0.6 |  |
| staged/clef_pagewide.py:459 | `F_SCAN_WINDOW_SPACES = 8.0` | sp | LB | D | ? |  -------------------------------------------------------------------------------------------------------------------------------------- 2.251 carry: an F clef with NO det |  |
| staged/clef_pagewide.py:554 | `F_TEMPLATE_SCALES = [0.8, 0.9, 1.0]` | ? |  | C | ? |  the template is tried at these sizes (a change is often printed smaller than the header's clef) ... F_TEMPLATE_SCALES = (0.8, 0.9, 1.0) |  |
| staged/clef_pagewide.py:556 | `F_TEMPLATE_SHIFT_SPACES = 0.35` | sp |  | C | ? |  ... and shifted this far (staff spaces) each way from where its own dots put it F_TEMPLATE_SHIFT_SPACES = 0.35 |  |
| staged/clef_pagewide.py:631 | `F_TEMPLATE_READ_SCORE = 0.65` | conf | LB | D | REFUSES |  pairs; every non-clef pair <= 0.61, the 2.251 count's no-box bass clefs 0.83 (bar 38), 0.75 (Vc bar 411)); Brahms pp. 1,3,4,5 every non-clef pair <= 0.42. A CUT-OFF on t |  |
| staged/clef_pagewide.py:634 | `F_TEMPLATE_CANDIDATE_SCORE = 0.5` | conf | L | D | NARROWS |  ... and at this score and above (but below READ) it is a CLEF-SHAPED CANDIDATE: claimed nothing, but a carried clef stops there (Litolff bars 115 0.66 and 111 0.55: real |  |
| staged/clef_pagewide.py:639 | `F_TEMPLATE_STRONG_SCORE = 0.65` | conf | L | D | NARROWS |  ... and at this score (dot pair AND body, below READ) a STRONG candidate: it stops the header's clef too, unless that is an F clef. Round 2: Sean's carry tile 11 (Vc bar |  |
| staged/clef_pagewide.py:643 | `F_BODY_SCAN_CANDIDATE_SCORE = 0.6` | conf | L | D | NARROWS |  the F body slid with NO dot witness (`f_body_scan`) makes a candidate at this score (one witness: a candidate, never READ). MEASURED on Litolff pp. 1-16, the staves hold |  |
| staged/clef_pagewide.py:645 | `SMALL_CLEF_BOX_MIN_SCORE = 0.5` | conf |  | C | NARROWS |  a `clef*` box too small for a clef-sized claim, at this detector score and above, is still a clef-shaped CANDIDATE (b) SMALL_CLEF_BOX_MIN_SCORE = 0.5 |  |
| staged/clef_pagewide.py:647 | `F_BODY_MAX_REACH_SPACES = 2.6` | sp |  | C | ? |  an F clef's body and dots span at most this far (staff spaces) left of its dots' left edge F_BODY_MAX_REACH_SPACES = 2.6 |  |
| staged/key_object.py:40 | `MAX_START_AFTER_CLEF_SPACES = 2.0` | sp |  | C | ? |  the first accidental starts within this many spaces of the clef's right edge (`key_slots.MAX_START_AFTER_CLEF_SPACES`) MAX_START_AFTER_CLEF_SPACES = 2.0 |  |
| staged/stroke_map.py:192 | `CLEF_CONTACT_PX = 2` | px |  | C | ? |  two pieces of a clef are one ink when within this many reduced px (the stroke map's own contact rule, `touches`: "within 2 px") CLEF_CONTACT_PX = 2 |  |

## key signature (66; A 8, B 9, C 43, D 4, E 1, n/a 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| instruments.py:143 | `Instrument.default_fifths_offset = 0` | ? |  | C | ? | default_fifths_offset: int = 0 used when the label names no key |  |
| key_consensus.py:105 | `MIN_WITNESSES = 3` | count |  | A | NARROWS |  Fewest concert-pitch staves that may establish a key. Below this the page has not corroborated anything and the module abstains. MIN_WITNESSES = 3 |  |
| key_consensus.py:125 | `NO_SIGNATURE_MIN_STAVES = 3` | count |  | A | ? |  ...over at least this many staves, so a two-staff misread cannot trip it. NO_SIGNATURE_MIN_STAVES = 3 |  |
| key_signature_geometry.py:147 | `KeySignatureFitConfig.max_residual = 0.5` | ? |  | C | ? | max_residual: float = 0.5 |  |
| key_signature_geometry.py:148 | `KeySignatureFitConfig.max_offset = 1.25` | ? |  | C | ? | max_offset: float = 1.25 |  |
| key_signature_geometry.py:151 | `KeySignatureFitConfig.max_inferred_ratio = 1.0` | ratio |  | B | ? | max_inferred_ratio: float = 1.0 |  |
| key_signature_geometry.py:152 | `KeySignatureFitConfig.max_outliers = 0` | count |  | A | ? | max_outliers: int = 0 |  |
| key_signature_locator.py:123 | `KeySignatureLocatorConfig.min_width_spaces = 0.3` | sp |  | C | ? | min_width_spaces: float = 0.30 |  |
| key_signature_locator.py:124 | `KeySignatureLocatorConfig.max_width_spaces = 1.7` | sp |  | C | ? | max_width_spaces: float = 1.70 |  |
| key_signature_locator.py:125 | `KeySignatureLocatorConfig.min_height_spaces = 1.1` | sp |  | C | ? | min_height_spaces: float = 1.10 |  |
| key_signature_locator.py:126 | `KeySignatureLocatorConfig.max_height_spaces = 3.6` | sp |  | C | ? | max_height_spaces: float = 3.60 |  |
| key_signature_locator.py:133 | `KeySignatureLocatorConfig.cluster_gap_spaces = 0.15` | sp |  | C | ? | cluster_gap_spaces: float = 0.15 |  |
| key_signature_locator.py:136 | `KeySignatureLocatorConfig.run_gap_spaces = 1.9` | sp |  | C | ? | run_gap_spaces: float = 1.90 |  |
| key_signature_locator.py:140 | `KeySignatureLocatorConfig.size_tolerance = 0.35` | ? |  | C | ? | size_tolerance: float = 0.35 |  |
| key_signature_locator.py:144 | `KeySignatureLocatorConfig.staff_band_spaces = 2.5` | sp |  | C | ? | staff_band_spaces: float = 2.50 |  |
| key_signature_locator.py:145 | `KeySignatureLocatorConfig.min_ink_fraction = 0.1` | ratio |  | B | ? | min_ink_fraction: float = 0.10 |  |
| key_signature_locator.py:146 | `KeySignatureLocatorConfig.min_component_area_spaces = 0.02` | sp |  | C | ? | min_component_area_spaces: float = 0.02 |  |
| key_signature_locator.py:149 | `KeySignatureLocatorConfig.max_run_length = 7` | ? |  | C | ? | max_run_length: int = 7 |  |
| key_signature_locator.py:185 | `KeySignatureLocatorConfig.tail_max_residual = 0.2` | ? |  | C | ? | tail_max_residual: float = 0.20 |  |
| key_signature_locator.py:197 | `KeySignatureLocatorConfig.tail_min_head_height_spaces = 2.0` | sp |  | C | ? | tail_min_head_height_spaces: float = 2.0 |  |
| key_signature_locator.py:243 | `FLAT_SHAPE_THRESHOLD = 0.62` | conf |  | A | DECIDES |  Above this share of ink below the middle, a glyph is a flat. Sharps and naturals measure close to 0.5 by construction (they are symmetric about their centre); a flat's b | * rank 7: C, DECIDES flat vs sharp by bowl share; 08-28 (d2af0da66) |
| key_signature_template.py:71 | `KeySignatureTemplateConfig.template_em_px = 120` | px |  | E | ? | template_em_px: int = 120 |  |
| key_signature_template.py:77 | `KeySignatureTemplateConfig.min_score = 0.55` | ratio |  | B | ? | min_score: float = 0.55 |  |
| key_signature_template.py:86 | `KeySignatureTemplateConfig.column_merge_spaces = 0.7` | sp |  | C | ? | column_merge_spaces: float = 0.7 |  |
| staged/accidental_family.py:52 | `FLAT_GLYPH_H_SP = 2.456` | sp |  | A | ? |  SMuFL (Bravura) `accidentalFlat` glyph: bBox height 2.456 sp; its bowl ~1.2 sp. The floor is 0.7 of each (2.242's share). FLAT_GLYPH_H_SP = 2.456 |  |
| staged/accidental_family.py:53 | `FLAT_BOWL_H_SP = 1.2` | sp |  | C | ? | FLAT_BOWL_H_SP = 1.2 |  |
| staged/accidental_family.py:86 | `SHARP_STAGGER_MAX_SP = 0.2` | sp |  | C | ? |  SHARP: neither end staggers by more than this; measured -0.19 .. 0.06. Between the two cut-offs the stems are `unclear`. SHARP_STAGGER_MAX_SP = 0.2 |  |
| staged/accidental_family.py:89 | `SHARP_STAGGER_REVERSE_MAX_SP = 0.45` | sp |  | C | DECIDES |  ... and neither end of a sharp has its right stem HIGHER than the left's by more than this (measured -0.19 at the most; tile 11 read -1.2 and -1.4: two neighbouring mark |  |
| staged/accidental_family.py:93 | `FLAT_STEM_X_FRACTION_MAX = 0.45` | ratio |  | B | ? |  FLAT: the one stem stands in the left part of the mark and its bowl (a piece to its right) lies in its lower part. FLAT_STEM_X_FRACTION_MAX = 0.45 |  |
| staged/accidental_family.py:94 | `FLAT_BOWL_MIN_FRACTION = 0.4` | ratio |  | B | ? | FLAT_BOWL_MIN_FRACTION = 0.40 |  |
| staged/adjudicators/clef.py:176 | `W_KEYSIG_FIT = 1.5` | ? |  | n/a | NARROWS |  What "the measured accidental run fits this clef's slot table" is worth. (A-CLEF-7) ⚠️ Contributed only when the fit DISCRIMINATES -- a run that fits every candidate say |  |
| staged/adjudicators/header.py:130 | `MARKER_SLOT_TOLERANCE_SPACES = 0.5` | sp |  | C | ? |  four `keyFlat` boxes at canonical x 375 / 461 / 463 / 545 with a cell staff space of 85 px — the printed slots stand 86 and 83 px apart (≈1.0 space) and the spurious pai |  |
| staged/adjudicators/header.py:138 | `MAX_FIFTHS = 7` | ? |  | A | REFUSES |  Circle-of-fifths limit. A run longer than this is not a key signature. MAX_FIFTHS = 7 |  |
| staged/adjudicators/key_slots.py:64 | `RUN_GAP_SPACES = 2.0` | sp |  | C | ? |  `header.MARKER_RUN_GAP_SPACES`, `header.MARKER_SLOT_TOLERANCE_SPACES` and `header.MAX_FIFTHS`, restated because `header` imports `clef`, which imports this package's oth |  |
| staged/adjudicators/key_slots.py:65 | `SLOT_TOLERANCE_SPACES = 0.5` | sp |  | C | ? | SLOT_TOLERANCE_SPACES = 0.5 |  |
| staged/adjudicators/key_slots.py:66 | `MAX_SLOTS = 7` | ? |  | C | ? | MAX_SLOTS = 7 |  |
| staged/adjudicators/key_slots.py:71 | `BRIDGE_GAP_SPACES = 2.8` | sp | L | D | ? |  Two slot pitches (a printed flat's left edge to the next one's is ~1.15 spaces; measured on Litolff p1-3) plus the slot tolerance: the farthest apart two KEY-class boxes | * rank 7: D, DECIDES a bridged key slot; Litolff p1-3 flat pitch 1.15 |
| staged/adjudicators/key_slots.py:79 | `NEXT_SLOT_TOL_SPACES = 0.2` | sp | L | D | ? |  last flat as a key class: Litolff p1 s0 staff 10, dx -0.07 spaces). The nearest real rests after a signature on the two count pages stand 0.42 and 1.32 spaces off the ne | * rank 7: D, DECIDES; ASSUMED NOT CONFIRMED (88619a03b, 2.100) |
| staged/adjudicators/key_slots.py:126 | `KeySlotWindow.next_tol = 0.0` | ? |  | C | ? | next_tol: float = 0.0 |  |
| staged/adjudicators/rhythm.py:10046 | `REST_SLOT_TOLERANCE_WHOLE = 1.35` | ? |  | C | NARROWS |  conservative side -- it NARROWS 24 rows a wider band would DECIDE, and a narrowing loses nothing (EXPORT refuses to argmax one) while a decision on ink no one has looked |  |
| staged/adjudicators/rhythm.py:10060 | `REST_SLOT_TOLERANCE_HALF = 0.5` | ? |  | A | DECIDES |  derived from three rows would be a number wearing a measurement's clothes. So this stays at the convention's own midpoint, unchanged from 2.12b, and says so. It is the n |  |
| staged/arcs_system.py:59 | `FLAT_SPACES = 0.35` | sp |  | C | NARROWS |  A trace this flat (spaces of y range over its whole length) whose columns mostly sit on staff-line rows is the residue of a staff line, not an arc (2.60's fakes): abstai |  |
| staged/gather.py:10926 | `STACKED_HEAD_MIN_SLOT_FILL = 0.4` | ratio |  | B | ? |  fraction to count as real ink, not blank paper -- `benchmarks/omr- notehead-width-2026-09/probe/measure_2.41.py`'s `two_head_fit`'s own `0.4` floor for `supports_two_hea |  |
| staged/gather.py:10985 | `STACKED_BLOB_MIN_SLOT_FILL = 0.75` | ratio |  | B | DECIDES |  Each of the pair's two slots must hold this much ink (the existing floor is 0.4 + margin; the twins' weaker slot reads 0.81-0.89, a head on blank paper or a neighbour's  |  |
| staged/gather.py:11077 | `STACKED_HOLLOW_SLOT_MARGIN = 0.1` | ? |  | C | DECIDES |  Two placements of the pair that both read hollow must differ by this much in (ring - centre) to choose between them; otherwise the slots are ambiguous. STACKED_HOLLOW_SL |  |
| staged/gather.py:13690 | `_MAX_KEYSIG_SLOTS = 7.0` | sp |  | C | ? |  Seven slots, about a staff space apart — `[C21]`, and the same bound `adjudicators/header.MAX_FIFTHS` states one stage on. Written here rather than imported because `adj |  |
| staged/key_kind_slots.py:46 | `KIND_TOL_STEPS = 1.0` | count | L | D | ? |  how far a slot's measured centre may stand from its feasible centres (the interval between the glyph anchors): a MEASUREMENT on Litolff's scan (the 2.187b tail judge use | * rank 7: D; Litolff scan only |
| staged/key_kind_slots.py:50 | `MIN_GAP_SPACES = 0.45` | sp | L | D | DECIDES |  one slot apart, centre to centre (`key_object.RUN_GAP_SPACES`; Litolff crushes to ~0.6); closer than this is one blob counted twice MIN_GAP_SPACES = 0.45 |  |
| staged/key_kind_slots.py:51 | `MAX_GAP_SPACES = 2.0` | sp |  | C | ? | MAX_GAP_SPACES = 2.0 |  |
| staged/key_kind_slots.py:52 | `MAX_SLOTS = 7` | ? |  | C | ? | MAX_SLOTS = 7 |  |
| staged/key_object.py:42 | `RUN_GAP_SPACES = 2.0` | sp |  | C | ? |  successive accidentals of one run: centre to centre (`key_slots.RUN_GAP_SPACES`) RUN_GAP_SPACES = 2.0 |  |
| staged/key_object.py:43 | `MAX_SLOTS = 7` | ? |  | C | ? | MAX_SLOTS = 7 |  |
| staged/key_object.py:45 | `WINDOW_REACH_SPACES = 11.0` | sp |  | C | ? |  how far past the clef the window reaches where the staff's meter is unknown (7 slots x 1.15 + a start gap) WINDOW_REACH_SPACES = 11.0 |  |
| staged/key_object.py:47 | `LEVEL_SPACES = 1.6` | sp |  | C | ? |  a piece's centre must lie within this many spaces of the staff's five lines (a neighbour staff's ink stands farther) LEVEL_SPACES = 1.6 |  |
| staged/key_object.py:49 | `BAND_SPACES = 2.2` | sp |  | C | DECIDES |  the band read above / below the staff BAND_SPACES = 2.2 |  |
| staged/key_object.py:53 | `COUNT_MIN_STAVES = 2` | count |  | C | REFUSES |  the run's count N is the largest k that at least this many staves of the system read IN FULL on their own (two independent printings of the same signature; measured: the |  |
| staged/key_object.py:55 | `PITCH_SPACES = [0.8, 1.7]` | sp |  | B | DECIDES |  the slot pitch used to place a slot a staff did not read: the median centre-to-centre of consecutive pieces over the system, within these PITCH_SPACES = (0.8, 1.7) |  |
| staged/key_object.py:464 | `SLOT_WIDTH_SPACES = 1.0` | sp |  | B | DECIDES |  a slot's own width in spaces where it is placed, not read SLOT_WIDTH_SPACES = 1.0 |  |
| staged/key_object.py:546 | `POS_TOL_STEPS = 0.5` | count |  | A | NARROWS |  Where the written key is not known the type is open (flat, sharp or natural all pass (a)) and the reach is the system's count (today's). CONVENTION: the fixed order is S |  |
| staged/key_object.py:547 | `SLOT_TOL_SPACES = 0.6` | sp |  | C | REFUSES | SLOT_TOL_SPACES = 0.6 key_slots.SLOT_TOLERANCE_SPACES (0.5) + 0.1: the box's ink centre, not a glyph edge |  |
| staged/key_object.py:548 | `SLOT_DRIFT_SPACES = 0.2` | sp |  | C | ? | SLOT_DRIFT_SPACES = 0.2 per placed slot beyond the first (MEASURED, see FINDINGS 2.187b) |  |
| staged/letter_look.py:93 | `SLOT_GAP_SPACES = 0.8` | sp |  | C | REFUSES |  Unread ink must stand this close to a read letter to be a slot of its word. SLOT_GAP_SPACES = 0.8 |  |
| staged/letter_look.py:467 | `SLOT_MIN_AREA_SPACES2 = 0.3` | sp |  | C | REFUSES |  Ink beside a read letter, off its core piece, must hold at least this much (square staff spaces) to be a letter of its own and not a fleck. SLOT_MIN_AREA_SPACES2 = 0.3 |  |
| staged/letter_look.py:471 | `SLOT_WEAK_LOOKS = 2` | ? |  | C | REFUSES |  ... and a weak letter hypothesis must stand over it on at least this many looks, so that a fragment of the read letter itself (a crossbar cut by a line) is not an unread |  |
| staged/page_arcs.py:72 | `FLAT_MAX_SP = 4.0` | sp |  | C | ? | FLAT_MAX_SP = 4.0 a run this narrow ... |  |
| staged/page_arcs.py:73 | `FLAT_SAG_SP = 0.12` | sp |  | C | DECIDES | FLAT_SAG_SP = 0.12 ... that bows less than this is a ledger line / head base / beam stub |  |

## meter (46; A 6, B 6, C 27, D 2, E 1, n/a 4)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| staged/adjudicators/key_slots.py:379 | `METER_COLUMN_MARGIN_SPACES = 0.3` | sp |  | C | ? |  A rest's centre may stand this many staff spaces outside the column of the sibling staves' digit boxes and still be that column's ink. METER_COLUMN_MARGIN_SPACES = 0.3 |  |
| staged/adjudicators/movement.py:81 | `METER_STATEMENT_MAJORITY = 0.6` | ? |  | B | ? |  "Nearly every staff" -- a meter glyph observed at CELL 0 (the system's own first bar; gather.py's own `frame_cell(0)`) on at least this share of the system's staves. NOT |  |
| staged/adjudicators/notehead_precision.py:305 | `METER_DIGIT_X_MAX_SPACES = 3.0` | sp |  | C | REFUSES |  How close to the cell's own left edge (the barline) a meter-change digit sits, in canonical staff spaces. Measured 1.48-2.20 on the fixture above; this is a comfortable  |  |
| staged/adjudicators/notehead_precision.py:309 | `METER_DIGIT_PAIR_X_TOL_SPACES = 0.25` | sp |  | C | ? |  The two digits of one meter change sit at nearly the SAME x -- a template glyph, not two independently-drawn noteheads. Measured x-gap 0.00-0.11. METER_DIGIT_PAIR_X_TOL_ |  |
| staged/adjudicators/notehead_precision.py:316 | `METER_DIGIT_PAIR_Y_GAP_MIN_SPACES = 0.3` | sp |  | C | ? |  numeral pair's own fixed proportions. Measured 0.42-0.86 on 13 of 14 staves of the one measured change; a real chord's interval is free to land here too (Sean's own risk |  |
| staged/adjudicators/notehead_precision.py:317 | `METER_DIGIT_PAIR_Y_GAP_MAX_SPACES = 1.2` | sp |  | C | ? | METER_DIGIT_PAIR_Y_GAP_MAX_SPACES = 1.20 |  |
| staged/adjudicators/notehead_precision.py:361 | `METER_DIGIT_QUORUM_MIN_STAVES = 2` | count |  | A | ? |  print omits. This keeps the one real witness (0.929) and excludes both real-world false ones (0.571) with margin on both sides. ───────────────────────────────────────── |  |
| staged/adjudicators/notehead_precision.py:362 | `METER_DIGIT_QUORUM_COVERAGE = 0.8` | ratio |  | B | ? | METER_DIGIT_QUORUM_COVERAGE = 0.8 |  |
| staged/adjudicators/notehead_precision.py:1050 | `METER_STACK_X_TOL_SPACES = 0.25` | sp | B | D | ? |  a printed meter is two numerals one above the other (6 over 8): its loops, boxed piecemeal, form a COLUMN of boxes at one x that spans more than a chord of whole notes c |  |
| staged/adjudicators/notehead_precision.py:1051 | `METER_STACK_LINK_MAX_SPACES = 3.0` | sp |  | C | ? | METER_STACK_LINK_MAX_SPACES = 3.0 |  |
| staged/adjudicators/notehead_precision.py:1052 | `METER_STACK_MIN_EXTENT_SPACES = 2.4` | sp |  | C | ? | METER_STACK_MIN_EXTENT_SPACES = 2.4 |  |
| staged/adjudicators/rhythm.py:7026 | `METER_AGREEMENT_FLOOR = 0.7` | ? |  | B | ? |  A meter must be agreed by this share of the staves that SPOKE. (A-METER-1) ⚠️ Not tuned here, but not arbitrary either: over an 11-source corpus every one of the 12 corr |  |
| staged/adjudicators/rhythm.py:7049 | `METER_COVERAGE_FLOOR = 0.5` | ratio |  | B | DECIDES |  3/11 = 0.27 against 12/12 = 1.0, so the floor separates them with room to spare. A meter is printed on EVERY staff of a system; a reading on a handful of them is a misre |  |
| staged/adjudicators/rhythm.py:7132 | `W_METER_CARRIED = 1.0` | ? |  | n/a | ? |  What the carry is worth alone: a real reading, voted by every staff of its system -- but on another system, and possibly in another movement. W_METER_CARRIED = 1.0 |  |
| staged/adjudicators/rhythm.py:7143 | `W_METER_BAR_FITS = 1.0` | ? |  | n/a | DECIDES |  a page whose meter is READ, only half the bars land exactly. The two pages available separate under every ratio tried, so the corpus cannot choose, and a constant a meas |  |
| staged/adjudicators/rhythm.py:7144 | `W_METER_BAR_CONTRADICTS = -1.0` | ? |  | n/a | ? | W_METER_BAR_CONTRADICTS = -1.0 |  |
| staged/adjudicators/rhythm.py:7158 | `METER_CARRY_FLOOR = 2.0` | ? | L | D | ? |  a page with nothing to check against does not carry (`W_METER_CARRIED` alone is 1.0 and falls short). Measured on Beethoven 5 / Litolff `984073` carrying `2/4`: page 2 ( |  |
| staged/adjudicators/rhythm.py:7176 | `METER_CARRY_MIN_BARS = 2` | count |  | A | REFUSES |  bar is not a system's worth of evidence -- the same argument `METER_COVERAGE_FLOOR` makes for readings ("two spurious readings that happen to agree are unanimous among t |  |
| staged/adjudicators/rhythm.py:7181 | `METER_CARRY_MIN_STAVES_PER_BAR = 3` | ? |  | C | REFUSES |  A bar needs this many staves reading it before it may vote on bar LENGTH. ⚠️ Two staves that agree are not a system; the same "unanimous among themselves" fault `METER_C |  |
| staged/adjudicators/rhythm.py:7250 | `METER_FROM_BARS_FLOOR = 4.0` | ? |  | C | REFUSES |  ⚠️ AT 4.0 THE FLOOR IS EXERCISED BY A REAL NEGATIVE. Reached systems score +10 (p.1, meter read, control), +6 and +7 (p.2, truth 2/4, both correct) and **-2** on the *An |  |
| staged/adjudicators/rhythm.py:7425 | `METER_CHANGE_FLOOR = 3.0` | ? |  | A | ? |  What a change needs before it is written into the meter's segments. ⚠️ At 3.0 a single staff reading a complete meter clears it and two contradicting bars sink it again  |  |
| staged/adjudicators/rhythm.py:7508 | `METER_CHANGE_MIN_STAVES = 2` | count |  | A | DECIDES |  printed at one bar on every staff of the system" is the convention this file already assumes for meter (2.12d's own CONVENTION ASSUMED note). See `_required_corroboratio |  |
| staged/adjudicators/rhythm.py:7516 | `METER_CHANGE_COVERAGE_FLOOR = 0.5` | ratio |  | B | REFUSES |  `drop_uncorroborated_meter_changes`, already uses `max(2, round(0.5 * n_staves))` — cited, never imported (LEGACY is frozen and may not be read from `tools/omr/staged/`, |  |
| staged/adjudicators/rhythm.py:8015 | `METER_TEMPLATE_AT_BAR_MIN_STAVES = 3` | count |  | C | REFUSES |  ⚠️ THE COST IS UNMEASURED AND IS ONE-SIDED: no page in reach prints a mid-staff meter change, so what this refuses has never been observed. A real change on a badly-read |  |
| staged/adjudicators/rhythm.py:8582 | `METER_RETURN_MARK_CELL = 1` | ? |  | n/a | ? | METER_RETURN_MARK_CELL = 1 |  |
| staged/gather.py:14296 | `METER_TEMPLATE_AT_BAR_WINDOW_SPACES = 4.0` | sp |  | C | ? |  over the same 1,612 windows the answer rate at the shipped floor runs **0.59% at 4 spaces, 1.34% at 6, 2.19% at 8**. Four spaces is also more than a meter needs — a digi |  |
| staged/gather.py:14312 | `METER_TEMPLATE_AT_BAR_MIN_CANDIDATE_STAVES = 1` | ? |  | C | NARROWS |  this pass asks 525 windows where the header pass asks 83. At 20 ms a window that is ~11 s for a three-page document. **The briefed assumption that a detection names a ha |  |
| staged/meter_object.py:32 | `NUMERAL_H_SPACES = [1.0, 2.7]` | sp |  | C | ? |  --- the numeral pair, in staff spaces (stated before the count; measured on the two plates, FINDINGS) --- one numeral piece: height / width windows (a bold digit is ~1.6 | * rank 8: C, REFUSES a numeral outside 1.0-2.7 sp |
| staged/meter_object.py:33 | `NUMERAL_W_SPACES = [0.35, 1.9]` | sp |  | C | ? | NUMERAL_W_SPACES = (0.35, 1.9) |  |
| staged/meter_object.py:35 | `PAIR_X_TOL_SPACES = 0.55` | sp |  | C | ? |  the two numerals' centres stand in one column PAIR_X_TOL_SPACES = 0.55 |  |
| staged/meter_object.py:37 | `PAIR_H_SPACES = [2.6, 4.8]` | sp |  | C | ? |  ... and the whole pair spans this many spaces (4 for a digit pair; a single C is shorter) PAIR_H_SPACES = (2.6, 4.8) |  |
| staged/meter_object.py:39 | `MERGED_H_SPACES = [3.0, 4.8]` | sp |  | C | ? |  a pair whose pieces fused (the staff-line erase leaves a thin join): one piece of this size, with a waist (see `_has_waist`) MERGED_H_SPACES = (3.0, 4.8) |  |
| staged/meter_object.py:40 | `MERGED_W_SPACES = [1.2, 2.8]` | sp |  | C | ? | MERGED_W_SPACES = (1.2, 2.8) |  |
| staged/meter_object.py:44 | `COMMON_H_SPACES = [1.8, 3.4]` | sp |  | C | ? |  one C / cut-C piece COMMON_H_SPACES = (1.8, 3.4) |  |
| staged/meter_object.py:45 | `COMMON_W_SPACES = [1.0, 2.4]` | sp |  | C | ? | COMMON_W_SPACES = (1.0, 2.4) |  |
| staged/meter_object.py:49 | `AREA_W_MAX_SPACES = 2.8` | sp |  | C | DECIDES |  a piece that fills more than this width is a merged neighbour (clef, key accidental, barline, bar's first note) AREA_W_MAX_SPACES = 2.8 |  |
| staged/meter_object.py:51 | `BAND_SPACES = 1.25` | sp |  | C | DECIDES |  the vertical band read: this far above the top line and below the bottom line BAND_SPACES = 1.25 |  |
| staged/meter_object.py:257 | `COLUMN_X_TOL_SPACES = 0.6` | sp |  | C | NARROWS |  a meter stands at one x on every staff of its system: candidates whose area centres lie within this many spaces are one column COLUMN_X_TOL_SPACES = 0.6 |  |
| staged/meter_object.py:260 | `COLUMN_MIN_STAVES = 2` | count |  | A | ? | COLUMN_MIN_STAVES = 2 |  |
| staged/meter_object.py:264 | `COLUMN_HINT_SPACES = 1.3` | sp |  | C | ? |  the window (spaces either side of the detector column's x) of the hinted second search COLUMN_HINT_SPACES = 1.3 |  |
| time_signature_locator.py:172 | `TimeSignatureLocatorConfig.template_em_px = 120` | px |  | E | ? | template_em_px: int = 120 |  |
| time_signature_locator.py:177 | `TimeSignatureLocatorConfig.min_score = 0.5` | ratio |  | B | ? | min_score: float = 0.50 | * rank 8: C, DECIDES/REFUSES a meter digit against BRAVURA templates (aa9b8d3ea, 08-31); comment: a Litolff 3 matches Bravura 6 |
| time_signature_locator.py:196 | `TimeSignatureLocatorConfig.min_staves = 2` | count |  | A | ? | min_staves: int = 2 |  |
| time_signature_locator.py:200 | `TimeSignatureLocatorConfig.band_pad_spaces = 0.5` | sp |  | C | ? | band_pad_spaces: float = 0.5 |  |
| time_signature_locator.py:224 | `TimeSignatureLocatorConfig.split_column_slack_spaces = 0.5` | sp |  | C | ? | split_column_slack_spaces: float = 0.5 |  |
| time_signature_locator.py:230 | `TimeSignatureLocatorConfig.split_centre_tol_spaces = 0.6` | sp |  | C | ? | split_centre_tol_spaces: float = 0.6 |  |

## tremolo (28; B 5, C 21, D 2)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| staged/adjudicators/family_precision.py:963 | `REST_SLASHED_MIN_HEIGHT_SPACES = 3.8` | sp | LB | D | ? |  tremolo slash on its stem makes it a stem. Plain quarter rests measured at 2.8 (median, Brahms p1) to 3.1 (Litolff p3, p6); the slashed stem boxed as a rest is 4.5 (Lito | * rank 4: D, DECIDES rest vs slashed stem; Brahms p1 2.8, Litolff 3.1, slashed 4.5 (Litolff p6, one case); NOT CONFIRMED |
| staged/adjudicators/notehead_precision.py:1817 | `SLASH_READ_COVER_MIN = 0.6` | ratio |  | B | REFUSES |  this many times the stroke's own area (length x thickness; a head with a slash across it is a bigger box and is not asked), and must sit away from both stem ends (the sa |  |
| staged/adjudicators/notehead_precision.py:1818 | `SLASH_READ_BOX_MAX_FOOTPRINTS = 4.0` | ? |  | C | ? | SLASH_READ_BOX_MAX_FOOTPRINTS = 4.0 |  |
| staged/adjudicators/rhythm.py:727 | `SLASH_STROKE_INSIDE_MIN = 0.6` | count |  | B | DECIDES |  A stroke is the slash's own ink where at least this share of its box lies inside the slash's footprint (padded by `SLASH_FOOTPRINT_PAD_SPACES`) AND it is no wider than t |  |
| staged/adjudicators/rhythm.py:728 | `SLASH_FOOTPRINT_PAD_SPACES = 0.3` | sp |  | C | ? | SLASH_FOOTPRINT_PAD_SPACES = 0.3 |  |
| staged/adjudicators/rhythm.py:729 | `SLASH_EXTRA_WIDTH_SPACES = 0.8` | sp |  | C | ? | SLASH_EXTRA_WIDTH_SPACES = 0.8 |  |
| staged/gather.py:6503 | `STEM_SLASH_MIN_REACH_SPACES = 0.35` | sp |  | C | ? |  A stroke must reach at least this far out from the stem on BOTH sides. STEM_SLASH_MIN_REACH_SPACES = 0.35 |  |
| staged/gather.py:6507 | `STEM_SLASH_MAX_REACH_SPACES = 1.9` | sp |  | C | REFUSES |  ... and no further than this before it is something longer than a slash (a beam, a tie, a staff-line residue): the tracker stops here and the stroke is refused `runs_on` |  |
| staged/gather.py:6511 | `STEM_SLASH_CONTACT_GAP_SPACES = 0.35` | sp |  | C | ? |  The left and right contact intervals (where the stroke meets the stem's edges) must lie within this far of overlapping: a straight stroke at 30 degrees shifts ~0.2 space |  |
| staged/gather.py:6521 | `STEM_SLASH_MIN_CONTACT_SPACES = 0.1` | sp | LB | D | REFUSES |  the stem measured 1.37 spaces on its left side and was refused here as a clump, so `Q.STEM_SLASH` read a stem Sean reads as slashed as `one_sided`. MEASURED across every |  |
| staged/gather.py:6522 | `STEM_SLASH_MAX_CONTACT_SPACES = 1.6` | sp |  | C | ? | STEM_SLASH_MAX_CONTACT_SPACES = 1.6 |  |
| staged/gather.py:6532 | `STEM_SLASH_START_SKIP_SPACES = 0.06` | sp |  | C | DECIDES |  half with a trem slash"*, read `one_sided` with a left reach of 0.0). The tracker may therefore start up to this far further out, in staff spaces, before it gives up. It |  |
| staged/gather.py:6534 | `STEM_SLASH_MAX_RESIDUAL_SPACES = 0.15` | sp |  | C | ? |  The tracked centre points of both sides lie on one line to within this. STEM_SLASH_MAX_RESIDUAL_SPACES = 0.15 |  |
| staged/gather.py:6537 | `STEM_SLASH_MIN_ANGLE_DEG = 12.0` | ? |  | C | DECIDES |  Off horizontal. A tremolo slash is drawn at an angle; a ledger line through a stem is level (0-5 degrees on the plates read). STEM_SLASH_MIN_ANGLE_DEG = 12.0 |  |
| staged/gather.py:6540 | `STEM_SLASH_MIN_THICKNESS_RATIO = 1.4` | ratio |  | B | DECIDES |  Thickness ACROSS the stroke over the staff line's thickness; a hairpin's line or a slur's tapering end reads 1.0-1.3, a slash 2.0 and over. STEM_SLASH_MIN_THICKNESS_RATI |  |
| staged/gather.py:6543 | `STEM_SLASH_HEAD_END_SPACES = 1.1` | sp |  | C | ? |  A notehead box whose centre is this near the stem's end, and whose rows hold the stroke, explains it (a chord's second puts a head on each side). STEM_SLASH_HEAD_END_SPA |  |
| staged/gather.py:6556 | `STEM_SLASH_BARE_WIDTH_FACTOR = 1.5` | ? |  | B | ? |  reader keeps what it measures, and the one decision that must tell a rest from a slashed stem (`family_precision`) asks the box's own HEIGHT as well. A row is "bare stem |  |
| staged/page_tremolo.py:54 | `NEIGHBOUR_SPACES = 6.0` | sp |  | C | DECIDES |  other stems near this one (spaces either side) that the finder's `joins_another_stem` test looks at NEIGHBOUR_SPACES = 6.0 |  |
| staged/page_tremolo.py:66 | `END_ZONE_SP = 1.4` | sp |  | C | DECIDES |  ROADMAP 2.276 r2 (Sean 2026-11-09: "could never be a trem slash because it is on the opposite side of the end of the stem"): the stem END test, from ink alone. A head en |  |
| staged/page_tremolo.py:67 | `END_WINDOW_SP = 1.7` | sp |  | C | ? | END_WINDOW_SP = 1.7 |  |
| staged/page_tremolo.py:68 | `END_ROW_SP = 0.6` | sp |  | C | ? | END_ROW_SP = 0.6 |  |
| staged/page_tremolo.py:69 | `END_MIN_ROWS_SP = 0.9` | sp |  | C | ? | END_MIN_ROWS_SP = 0.9 |  |
| staged/page_tremolo.py:70 | `END_MIN_AREA_SP2 = 1.0` | ? |  | C | ? | END_MIN_AREA_SP2 = 1.0 |  |
| staged/page_tremolo.py:71 | `END_MAX_REACH_SP = 1.69` | sp |  | C | ? | END_MAX_REACH_SP = 1.69 |  |
| staged/stroke_owner.py:198 | `SLASH_MIN_THICK_SP = 0.35` | sp |  | C | ? |  a tremolo slash: a thick diagonal (Sean 2026-10-15) crossing a stem -- thickness at least a beam's minus its spread, 15-60 degrees SLASH_MIN_THICK_SP = 0.35 |  |
| staged/stroke_owner.py:201 | `SLASH_MIN_ASPECT = 2.5` | ratio |  | B | DECIDES |  ... and a LINE, not an oval: length / thickness at least this (a tilted head oval is ~1.5; a slash 1.5 x 0.45 is 3.3). Measured 2.205: without it, real chord heads besid |  |
| staged/stroke_owner.py:202 | `SLASH_MIN_ANGLE = 15.0` | ? |  | C | ? | SLASH_MIN_ANGLE = 15.0 |  |
| staged/stroke_owner.py:203 | `SLASH_MAX_ANGLE = 60.0` | ? |  | C | ? | SLASH_MAX_ANGLE = 60.0 |  |

## hairpin (26; B 1, C 21, D 3, n/a 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| hairpin_detection.py:80 | `BAND_TOP_SPACES = 0.3` | sp |  | C | ? |  The band a hairpin is printed in, in staff spaces below the bottom staff line. ⚠️ Measured, not assumed: every hairpin in the engraved page truth sits below a staff and  |  |
| hairpin_detection.py:81 | `BAND_BOTTOM_SPACES = 6.0` | sp |  | C | ? | BAND_BOTTOM_SPACES = 6.0 |  |
| hairpin_detection.py:84 | `MIN_OPEN_SPACES = 0.5` | sp |  | C | ? |  The two arms must open by at least this much somewhere — a stroke never does. MIN_OPEN_SPACES = 0.5 |  |
| hairpin_detection.py:90 | `MAX_COMPONENT_GROWTH = 2.0` | ? |  | C | ? |  A component whose full-page extent is more than this multiple of its own is attached to something. The population is 1.0x against 3248x; any value in that gap gives the  |  |
| hairpin_detection.py:97 | `MIN_WIDTH_SPACES = 0.8` | sp |  | C | ? | MIN_WIDTH_SPACES = 0.8 |  |
| hairpin_detection.py:98 | `MAX_WIDTH_SPACES = 30.0` | sp |  | C | ? | MAX_WIDTH_SPACES = 30.0 |  |
| hairpin_detection.py:108 | `REACH_VERTICAL_SPACES = 1.2` | sp |  | C | REFUSES |  hairpins of bars 352-358 are refused 'outline' or 'isolated', every one crossed by a barline or touching a stem; crops, benchmarks/hairpin-reach-2026-11). REACH removes  |  |
| hairpin_detection.py:109 | `REACH_REJOIN_SPACES = 0.5` | sp |  | C | ? | REACH_REJOIN_SPACES = 0.5 |  |
| hairpin_detection.py:114 | `REACH_MAX_CLOSED_SPACES = 0.45` | sp | B | D | ? |  ...and, because a beam whose stems were removed is as isolated as a hairpin, a hairpin must CONVERGE: its two arms meet, so the narrowest columns are one arm thick and t |  |
| hairpin_detection.py:115 | `REACH_MIN_OPEN_OVER_CLOSED = 2.2` | ? |  | C | ? | REACH_MIN_OPEN_OVER_CLOSED = 2.2 |  |
| hairpin_detection.py:121 | `MAX_BLANK_WIDTH_SPACES = 3.0` | sp |  | C | ? | MAX_BLANK_WIDTH_SPACES = 3.0 |  |
| hairpin_detection.py:285 | `REACH_MIN_EXTENT_TREND = 0.7` | ? | B | D | ? |  ...and the rejoin can glue a word's letters into one straight-edged band ('cresc.', 'pizz.', 'arco': Brahms p25, trend 0.05-0.38), while a hairpin opens steadily (p25 lo | * rank 13: D, REFUSES a hairpin; Brahms p25 only, NOT CONFIRMED (1adf81efc, 2.254) |
| hairpin_detection.py:339 | `REACH_MIN_W_SP = 1.6` | sp |  | C | ? |  The reach passes add nothing narrower than a letter (2.245's `box_kind.HAIRPIN_MIN_W_SP`: 9 of 9 narrower CV 'hairpins' were letters). REACH_MIN_W_SP = 1.6 |  |
| hairpin_detection.py:477 | `CV_CONFIDENCE = 0.99` | conf |  | C | REFUSES |  A CV reading is not a probability, and pretending otherwise would let a confidence filter somewhere downstream silently drop it. Stated once, high enough to survive ever |  |
| staged/adjudicators/ownership.py:55 | `W_HAIRPIN_SEPARATES = 7.0` | ? |  | n/a | ? |  but ledger lines will be"), so it is now a GATE ahead of every weight: `ledger_direction` below returns before a single term is summed, and no accumulation of hairpin +  |  |
| staged/adjudicators/ownership.py:5515 | `_WEDGE_WINDOW_CELLS = 1` | ? |  | C | ? |  window, which that function's docstring justifies ("the truth's own crescendo on that page runs `m5 -> m6`, ending on the next bar's downbeat") and which is enforced the |  |
| staged/adjudicators/rhythm.py:2789 | `WEDGE_MIN_HW = 1.3` | ? |  | C | NARROWS |  detector's own staccatissimo boxes read h/w 1.45 (5th pct 1.2), taper (point end / base end) 0.58 (95th pct 0.9); its staccato boxes 1.0 and 0.91. A cut on one score: it |  |
| staged/adjudicators/rhythm.py:2790 | `WEDGE_MAX_TAPER = 0.8` | ? |  | C | ? | WEDGE_MAX_TAPER = 0.8 |  |
| staged/adjudicators/rhythm.py:2791 | `WEDGE_MIN_HEIGHT_SPACES = 0.4` | sp |  | C | ? | WEDGE_MIN_HEIGHT_SPACES = 0.40 |  |
| staged/adjudicators/rhythm.py:2792 | `WEDGE_MAX_HEIGHT_SPACES = 0.85` | sp |  | C | ? | WEDGE_MAX_HEIGHT_SPACES = 0.85 |  |
| staged/box_kind.py:581 | `HAIRPIN_MIN_W_SP = 1.6` | sp | LB | D | REFUSES |  4. A HAIRPIN IS WIDER THAN A LETTER. Every CV hairpin row narrower than this on the frozen sample is a letter ('c' of cresc., 'e' of legato, 'B' of Basso: 9 of 9 on crop | * rank 13: D, REFUSES; 9 of 9 letters on crops, both plates (9659a10bd) |
| staged/gather.py:941 | `WEDGE_RESCUE_FLOOR = 0.03` | ? |  | C | ? | WEDGE_RESCUE_FLOOR = 0.03 |  |
| staged/gather.py:943 | `WEDGE_RESCUE_SAME_MARK_SPACES = 0.35` | sp |  | C | ? |  two boxes on one mark: centres within this many staff spaces, or boxes overlapping by this IoU WEDGE_RESCUE_SAME_MARK_SPACES = 0.35 |  |
| staged/gather.py:944 | `WEDGE_RESCUE_SAME_MARK_IOU = 0.2` | ? |  | C | ? | WEDGE_RESCUE_SAME_MARK_IOU = 0.2 |  |
| staged/page_arcs.py:138 | `WEDGE = 1` | ? |  | C | DECIDES | WEDGE = 1 r4: a hairpin's leg is thick at one end and a point at the other; a slur is thin at BOTH ends. An ink-only run whose thickness at its two ends differs by more t |  |
| staged/page_arcs.py:139 | `WEDGE_RATIO = 1.8` | ratio |  | B | ? | WEDGE_RATIO = 1.8 |  |

## arc/tie/slur (147; A 2, B 19, C 108, D 9, E 6, n/a 3)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| line_detection.py:398 | `FLAG_CURVE_MIN_SHARE = 0.8` | ratio |  | B | DECIDES |  ROADMAP 2.126 (`pair_flag_curve`): the share of a vertical stroke that must lie inside a detector FLAG box for it to be the flag's own curve. The same 0.8 an accidental  |  |
| measure_extractor.py:1693 | `CELL_LINE_FIND_SEARCH_SPACES = 2.0` | sp |  | C | ? | CELL_LINE_FIND_SEARCH_SPACES = 2.0 |  |
| staff_line_removal.py:93 | `LINE_SEARCH_RADIUS_SPACES = 0.25` | sp |  | C | ? |  a cell and deskew leaves a residual tilt, so at the ends of a wide cell the ink can sit clear of the nominal row. Anchoring to the nearest ink within this radius erases  |  |
| staged/accidental_family.py:259 | `BOWL_SIDE_TOP_MIN_SP = 1.0` | sp | B | D | ? |  ROADMAP 2.247 r3 (Sean's r2 tiles): a flat's bowl side starts this far (spaces) below its stem's top, a natural's right upright less (it starts at the upper bar). Measur | * rank 20: D; Brahms, Sean's r2 tiles |
| staged/adjudicators/family_precision.py:2279 | `ARC_LINE_MIN_WIDTH_SPACES = 2.5` | sp |  | C | DECIDES |  read against, FIXED BEFORE ANY COUNT WAS TAKEN. A staff line is a straight horizontal stroke through the whole box; erased, it leaves nothing curved, so: a box at least  |  |
| staged/adjudicators/family_precision.py:2280 | `ARC_LINE_MAX_COVERAGE = 0.35` | ratio |  | B | ? | ARC_LINE_MAX_COVERAGE = 0.35 |  |
| staged/adjudicators/family_precision.py:2283 | `ARC_BARLINE_MAX_WIDTH_SPACES = 1.0` | sp |  | C | DECIDES |  A barline is a straight vertical stroke: a box no wider than a space and at least two spaces tall, most of whose columns are one tall vertical run. ARC_BARLINE_MAX_WIDTH |  |
| staged/adjudicators/family_precision.py:2284 | `ARC_BARLINE_MIN_HEIGHT_SPACES = 2.0` | sp |  | C | ? | ARC_BARLINE_MIN_HEIGHT_SPACES = 2.0 |  |
| staged/adjudicators/family_precision.py:2285 | `ARC_BARLINE_MIN_TALL_COLS = 0.6` | ? |  | C | ? | ARC_BARLINE_MIN_TALL_COLS = 0.6 |  |
| staged/adjudicators/notehead_precision.py:862 | `ARC_CUT_AT_BARLINE_SPACES = 0.4` | sp |  | C | NARROWS |  The previous bar's arc box ends this close to its own cell's right edge (staff spaces): the crop cut it. Measured 0.00-0.36 on the 226 candidates. ARC_CUT_AT_BARLINE_SPA |  |
| staged/adjudicators/notehead_precision.py:864 | `ARC_TAIL_ROW_SLACK_SPACES = 0.5` | sp |  | C | ? |  The arc's rows must overlap the head box's rows widened by this much. ARC_TAIL_ROW_SLACK_SPACES = 0.5 |  |
| staged/adjudicators/notehead_precision.py:866 | `ARC_TAIL_OVAL_MAX_SPACES = 0.625` | sp |  | A | ? |  Half a standard head's width (`head_oval`'s convention, 1.25 sp). ARC_TAIL_OVAL_MAX_SPACES = 0.625 |  |
| staged/adjudicators/notehead_precision.py:2095 | `STACKED_KEEPER_NEAR_TIE = 0.05` | ? | L | D | ? |  `gather.STACKED_HEAD_FIT_MARGIN` discipline, and measured: between the 10-22 and 10-29 Litolff gathers the SAME box's ink moved by > 0.05 for 6% of boxes (0.0111 at the  |  |
| staged/adjudicators/ownership.py:2366 | `ARC_MIN_WIDTH_HEADS = 1.5` | ? |  | C | REFUSES |  ends within `ARC_END_MAX_DX_HEADS` head widths of the head it is read as leaving / reaching. NOT swept: chosen by eye on the two small re-gathers' slivers (0.45 and 0.66 |  |
| staged/adjudicators/ownership.py:2374 | `ARC_END_MAX_DX_HEADS = 1.5` | ? |  | C | ? | ARC_END_MAX_DX_HEADS = 1.5 |  |
| staged/adjudicators/ownership.py:3732 | `TIE_FLANK_MAX_DX_HEAD_WIDTHS = 3.0` | ? |  | B | DECIDES |  own widths. RESTATED from `transcribe._pair_ties_in_staff` (the legacy reference reader), whose "3x notehead width" window is what lets a tie crossing a barline reach th |  |
| staged/adjudicators/ownership.py:3743 | `TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS = 1.0` | ? | L | D | ? |  Litolff `984073` p3: start-head centres 0.37-0.54 widths inside the box. One width admits those with room and cannot admit the far head of any arc longer than two widths |  |
| staged/adjudicators/ownership.py:3748 | `TIE_FLANK_MAX_DY_HEAD_HEIGHTS = 3.0` | sp |  | C | ? |  How far a flanking head's centre may sit from the arc's own y-centre, in average notehead heights (one staff space), with the legacy floor of 30 px. RESTATED from the sa |  |
| staged/adjudicators/ownership.py:3749 | `TIE_FLANK_MIN_DY_PX = 30.0` | px |  | E | ? | TIE_FLANK_MIN_DY_PX = 30.0 | * rank 23: E-suspect (legacy 30 px floor, frame not verified) |
| staged/adjudicators/ownership.py:3769 | `_Flank.arc_yc = 0.0` | ? |  | C | ? | arc_yc: float = 0.0 |  |
| staged/adjudicators/ownership.py:4293 | `ARTIC_TIE_HEAD_HEIGHTS = 0.25` | sp | B | D | DECIDES |  heads' gaps is ONE STAFF STEP (half a staff space) -- 0.38 of a head height at the ~1.3 heights-per-space the detector's boxes measure (Brahms, whole movement). A tolera |  |
| staged/arc_claim.py:46 | `BAND_SPACES = 0.12` | sp |  | B | DECIDES |  the band around a trace row, staff spaces (a trace row is the stroke's own thickness, `+- 1` px of a skewed raster) BAND_SPACES = 0.12 |  |
| staged/arc_claim.py:47 | `BAND_MIN_PX = 1.5` | px |  | E | ? | BAND_MIN_PX = 1.5 |  |
| staged/arc_claim.py:485 | `BIND_COLUMN_DX_WIDTHS = 0.6` | ? |  | B | ? |  heads whose centres lie within this many of their own widths in x are one COLUMN (a chord, or two voices at one onset) BIND_COLUMN_DX_WIDTHS = 0.6 |  |
| staged/arc_claim.py:493 | `BIND_SIDE_MIN_SPACES = 0.1` | sp |  | C | ? |  a curve whose middle third sits this far (spaces) above / below the line through its two ends is ABOVE / BELOW its notes BIND_SIDE_MIN_SPACES = 0.1 |  |
| staged/arc_strip.py:41 | `FAR_MIN_SPACES = 0.75` | sp |  | C | ? |  The strip box must end at least this many spaces past the barline (the trial's rule). FAR_MIN_SPACES = 0.75 |  |
| staged/arc_strip.py:49 | `TURN_PROMINENCE_SPACES = 0.35` | sp |  | C | ? |  A turn of the traced centre line (`turns`, a measurement only) needs this much rise (spaces). TURN_PROMINENCE_SPACES = 0.35 |  |
| staged/arc_strip.py:51 | `MAX_DET = 3000` | ? |  | C | ? |  The detector's box cap for a row (ultralytics' default 300 truncates a whole row; the trial's rows reached 230). MAX_DET = 3000 |  |
| staged/arcs_system.py:62 | `EXT_MAX_SLOPE = 1.0` | ? |  | C | ? |  Past its own box a trace may not climb steeper than this (dy/dx). EXT_MAX_SLOPE = 1.0 |  |
| staged/arcs_system.py:64 | `RAW_BRIDGE_COST = 0.25` | sp |  | C | ? |  A column bridged on the RAW page costs this much of a gap column (`GAP_MAX_SPACES`): at most ~3 sp along a line. RAW_BRIDGE_COST = 0.25 |  |
| staged/arcs_system.py:66 | `STRAIGHT_MIN_SPACES = 2.0` | sp |  | C | REFUSES |  A trace at least this long (spaces) that stays within `STRAIGHT_SPACES` of a straight line is not an arc. STRAIGHT_MIN_SPACES = 2.0 |  |
| staged/arcs_system.py:67 | `STRAIGHT_SPACES = 0.15` | sp |  | C | ? | STRAIGHT_SPACES = 0.15 |  |
| staged/arcs_system.py:72 | `THICK_FACTOR = 1.6` | px |  | E | ? |  A traced column is erased only where its run is at most this many times the trace's median stroke (+1 px). THICK_FACTOR = 1.6 |  |
| staged/arcs_system.py:75 | `THICK_CONTINUE_FACTOR = 1.6` | px |  | E | DECIDES |  Along a trace, a run thicker than this many times the stroke's recent median (+2 px) is the stroke merged with something else, and bridges as a gap (tile 11). THICK_CONT |  |
| staged/arcs_system.py:77 | `SEED_COLUMNS = 3` | ? |  | n/a | ? |  How many seed columns a trace tries (the best coverage wins). SEED_COLUMNS = 3 |  |
| staged/arcs_system.py:79 | `GAP_MAX_SPACES = 0.75` | sp |  | C | ? |  The trace may cross this many spaces of columns with no stroke (a barline, a removed staff line, a stem). GAP_MAX_SPACES = 0.75 |  |
| staged/arcs_system.py:81 | `CUT_EXTEND_SPACES = 3.0` | sp |  | C | ? |  How far past a box edge the CROP CUT (the box ends within `CUT_EDGE_SPACES` of its cell's edge) the trace may run. CUT_EXTEND_SPACES = 3.0 |  |
| staged/arcs_system.py:83 | `FREE_EXTEND_SPACES = 0.5` | sp |  | C | ? |  How far past an edge the crop did not cut. FREE_EXTEND_SPACES = 0.5 |  |
| staged/arcs_system.py:85 | `CUT_EDGE_SPACES = 0.4` | sp |  | C | NARROWS |  A box ends this close to its cell's edge -> the crop cut the arc there (2.164: all 226 candidates <= 0.357). CUT_EDGE_SPACES = 0.4 |  |
| staged/arcs_system.py:87 | `ROW_PAD_SPACES = 1.0` | sp |  | C | ? |  The rows a trace may use around its seed box. ROW_PAD_SPACES = 1.0 |  |
| staged/arcs_system.py:89 | `TOL_SPACES = 0.12` | sp |  | C | ? |  How far the next run's centre may sit from the predicted y. TOL_SPACES = 0.12 |  |
| staged/arcs_system.py:93 | `SAME_Y_SPACES = 0.12` | sp |  | C | ? |  Two traces are one curve where they share columns with centres this close. SAME_Y_SPACES = 0.12 |  |
| staged/arcs_system.py:95 | `SAME_MIN_COLS = 2` | count |  | A | ? |  ... at least this many columns. SAME_MIN_COLS = 2 |  |
| staged/arcs_system.py:97 | `END_JOIN_Y_SPACES = 0.35` | sp |  | C | ? |  One ends where the other begins: an x gap no wider than `GAP_MAX_SPACES` and the ends this close in y. END_JOIN_Y_SPACES = 0.35 |  |
| staged/arcs_system.py:101 | `END_JOIN_SLOPE = 0.35` | ? |  | C | ? |  End-to-start: the two end tangents (dy/dx) may differ by at most this. END_JOIN_SLOPE = 0.35 |  |
| staged/arcs_system.py:104 | `MERGE_MAX_SPACES = 1.5` | sp |  | C | DECIDES |  A merge (the stroke's run thicker than the stroke) is a run no taller than this; the erase keeps clear of it by `MERGE_KEEP_SPACES` on both sides. MERGE_MAX_SPACES = 1.5 |  |
| staged/arcs_system.py:105 | `MERGE_KEEP_SPACES = 1.0` | sp |  | C | ? | MERGE_KEEP_SPACES = 1.0 |  |
| staged/arcs_system.py:107 | `ERASE_RUN_MAX_SPACES = 0.75` | sp |  | C | ? |  Erase: a canonical ink run taller than this is not the stroke (a head, stem or barline it touches) and is kept. ERASE_RUN_MAX_SPACES = 0.75 |  |
| staged/arcs_system.py:112 | `PASS_THROUGH_SPACES = 1.3` | sp |  | B | ? |  A vertical run longer than this (spaces) passes THROUGH a box (a barline, a stem): not the box's own ink. PASS_THROUGH_SPACES = 1.3 |  |
| staged/arcs_system.py:114 | `ANCHOR_OUT_SPACES = 1.6` | sp |  | C | ? |  Anchors: a head's centre within this many spaces OUTSIDE an end, or this many inside it. ANCHOR_OUT_SPACES = 1.6 |  |
| staged/arcs_system.py:115 | `ANCHOR_IN_SPACES = 0.8` | sp |  | C | ? | ANCHOR_IN_SPACES = 0.8 |  |
| staged/arcs_system.py:117 | `ANCHOR_DY_SPACES = 2.5` | sp |  | C | ? |  ... and within this many spaces of the end in y. ANCHOR_DY_SPACES = 2.5 |  |
| staged/arcs_system.py:119 | `SAME_POSITION_SPACES = 0.25` | sp |  | C | ? |  A tie's two heads sit at one staff position (page-facts §1; the staged tolerance `TIE_SAME_POSITION_MAX_SPACES`). SAME_POSITION_SPACES = 0.25 |  |
| staged/arcs_system.py:133 | `ERASE_BOX_PAD_SPACES = 0.25` | sp |  | C | ? |  The erase is confined to the arc's own boxes padded by this (plus boxes holding nothing but its stroke). ERASE_BOX_PAD_SPACES = 0.25 |  |
| staged/box_kind.py:554 | `ARC_MIN_LEN_SP = 3.0` | sp |  | C | DECIDES |  3. AN ARC BOWS. A tie or slur is a curve; a straight trace 3+ spaces long is a hairpin's leg or a beam (Sean's 2.245 tiles 6, 7, 11: 3/3 "part of a hairpin"). Read by th |  |
| staged/box_kind.py:558 | `ARC_MIN_BOW_SP = 0.15` | sp | LB | D | REFUSES |  measured on the frozen sample (`benchmarks/wrong-kind-boxes-2026-10/straight_arcs.py`): 18 of the 19 Brahms traces under this bow over 3+ sp are hairpin legs (the 19th a | * rank 11: D, REFUSES a flat arc; frozen sample (18 of 19 Brahms traces) |
| staged/clef_pagewide.py:50 | `C_BOWL_REACH_SPACES = 2.2` | sp |  | C | ? |  the bowls: ink right of the bar within this reach (staff spaces from the bar's right edge) ... C_BOWL_REACH_SPACES = 2.2 |  |
| staged/clef_pagewide.py:52 | `C_BOWL_MIN_FILL = 0.3` | ratio |  | B | ? |  ... in BOTH halves (above and below the bar's middle) at least this share of the half's area (a repeat sign's dots are far below it) C_BOWL_MIN_FILL = 0.3 | * rank 2: C, REFUSES; no plate named, set with the 0.08 line band |
| staged/clef_pagewide.py:54 | `C_BOWL_MAX_ASYMMETRY = 0.5` | ? |  | C | ? |  ... and the two halves mirror images: /upper - lower/ / max at most this C_BOWL_MAX_ASYMMETRY = 0.5 | * rank 2: C, REFUSES; unknown source |
| staged/clef_pagewide.py:69 | `BOWL_LINE_HALF_SPACES = 0.08` | sp |  | C | ? |  ... and for the C clef's bowls, every row this close to the line measured at the clef (the bowls' fills were set with it) BOWL_LINE_HALF_SPACES = 0.08 |  |
| staged/gather.py:633 | `ARC_WITNESS_HALF_WIDTH_SPACES = 0.9` | sp |  | C | ? |  An arc is drawn OVER its notes (CLAUDE.md §10), so a tie/slur's own bottom edge, at each horizontal end, is where a head hangs just below. ARC_WITNESS_HALF_WIDTH_SPACES  |  |
| staged/gather.py:634 | `ARC_WITNESS_HALF_HEIGHT_SPACES = 0.9` | sp |  | C | ? | ARC_WITNESS_HALF_HEIGHT_SPACES = 0.9 below the arc's own bottom edge |  |
| staged/gather.py:9088 | `WHOLE_REST_SEARCH_MIN_WIDTH_SP = 1.2` | sp |  | C | NARROWS |  The narrowest a whole rest's ink is in a bar of its own, measured on the stroke map of Sean's answered rest tiles (2.288 real cases: his 9 whole rests are 1.33-1.56 sp w |  |
| staged/gather.py:9428 | `ARC_INK_CURVE_RUN_SPACES = 0.8` | sp |  | C | ? |  ink's longest vertical run is no longer than this many staff spaces. A tie/slur stroke is 0.1-0.35 sp thick and, even on a steep end, stays under it; a stem, a barline a |  |
| staged/gather.py:9431 | `ARC_INK_TALL_RUN_SHARE = 0.8` | ratio |  | B | ? |  A column is part of a TALL VERTICAL STROKE when one run covers this share of the box's height (a barline, a stem). ARC_INK_TALL_RUN_SHARE = 0.8 |  |
| staged/gather.py:9434 | `ARC_INK_LINE_PAD_SPACES = 0.15` | sp |  | C | ? |  A staff line "passes through" the box within this many spaces of its rows, and its stroke is taken to be this many spaces either side of its ink row. ARC_INK_LINE_PAD_SP |  |
| staged/gather.py:9435 | `ARC_INK_LINE_STROKE_SPACES = 0.1` | sp |  | C | ? | ARC_INK_LINE_STROKE_SPACES = 0.1 |  |
| staged/gather.py:9438 | `ARC_INK_LINE_SNAP_SPACES = 0.3` | sp |  | B | ? |  A staff line is SNAPPED to the page's own ink row (local, never the staff's global value) only where this share of the box's columns are ink there. ARC_INK_LINE_SNAP_SPA |  |
| staged/gather.py:9439 | `ARC_INK_LINE_SNAP_MIN_FILL = 0.5` | ratio |  | B | ? | ARC_INK_LINE_SNAP_MIN_FILL = 0.5 |  |
| staged/gather.py:9441 | `ARC_INK_LINE_MAX_HALF_STROKE_SPACES = 0.4` | sp |  | C | ? |  ...and a line's stroke is grown at most this far either side of the row. ARC_INK_LINE_MAX_HALF_STROKE_SPACES = 0.4 |  |
| staged/gather.py:9443 | `ARC_INK_MIN_COLUMN_PX = 2` | px |  | E | ? |  A column holds ink only with at least this many ink pixels in it. ARC_INK_MIN_COLUMN_PX = 2 |  |
| staged/gather.py:9449 | `ARC_INK_LINE_LOCAL_REACH_SPACES = 0.6` | sp | L | D | DECIDES |  run through it where the staff tilts (Litolff p3 staff `3/1/5`: skew 6 px; at x 1150 its lines stand 6-8 px below the staff's values, and a 5 px "tie" box lying on the f |  |
| staged/gather.py:9450 | `ARC_INK_LINE_LOCAL_MIN_FILL = 0.85` | ratio |  | B | ? | ARC_INK_LINE_LOCAL_MIN_FILL = 0.85 |  |
| staged/gather.py:9458 | `ARC_INK_LINE_THICKNESS_SLACK_PX = 1` | px | L | D | REFUSES |  measured line (`Staff.line_thickness_px`, GATHER), never grown by how full the box's rows are. A tie lying ON a line (Litolff: thick ties along a line, Sean's 2.252 tile |  |
| staged/gather.py:10933 | `STACKED_HEAD_SEARCH_MARGIN_POSITIONS = 1` | ? |  | B | REFUSES |  the group's own observed box span -- a bounded search around the group's own ink, never an unbounded scan of the staff (the same discipline `reading_c`'s own comment giv |  |
| staged/gather.py:11269 | `TIE_SCORE_EPS = 1e-06` | conf |  | C | ? |  silently shifted BOTH heads up one diatonic step (F6/D6 -> G6/E6). The raw DETECTOR centres for this exact cell (`Q.NOTEHEAD_STAFF_POSITION` -7.4 / -5.56) were already c |  |
| staged/meter_object.py:262 | `COLUMN_SEARCH_SPACES = 1.8` | sp |  | C | ? |  a staff with no pair of its own is searched again inside the column, this many spaces either side of the column's centre COLUMN_SEARCH_SPACES = 1.8 |  |
| staged/page_arc_bind.py:60 | `GAP_SPLIT_SP = 2.0` | sp |  | C | ? |  ROADMAP 2.274 step 2 round 2 (cause b, measured on the develop pages before this was written; FINDINGS "2.274 step 2 round 2"): the tracker BRIDGES stretches of columns  |  |
| staged/page_arc_bind.py:69 | `INNER_MEMBER_DY_SPACES = 1.2` | sp |  | B | ? |  (cause c) three or more members: the end's own height may name an inner member only within this many spaces of it. INNER_MEMBER_DY_SPACES = 1.2 |  |
| staged/page_arc_bind.py:77 | `END_REACH_SPACES = 4.0` | sp | LB | D | NARROWS |  (measured on the 1552 written ends of the ten pages: 99% stand within 4.02) means the head the ink really ends at was never boxed (Litolff p13 run 80: 6.49; Brahms p11 r | * rank 12: D, REFUSES a binding; 99th pct of OUR written ends (e9644f634) |
| staged/page_arc_bind.py:108 | `MEET_DIP_SPACES = 0.5` | sp | L | D | NARROWS |  ROADMAP 2.305 r2 (two arcs MEETING at a head, Sean's r1 tile 8 "it's two ties"): how deep (spaces) the traced ink must dip toward its notes at a head between its ends, b |  |
| staged/page_arc_bind.py:111 | `MEET_INSIDE_SPACES = 2.0` | sp |  | C | REFUSES |  a meeting head stands at least this far (spaces) inside both ends of the run (an end at a head is the arc's own end, not a meeting) MEET_INSIDE_SPACES = 2.0 |  |
| staged/page_arc_bind.py:214 | `LAND_GAP_SPACES = 0.5` | sp |  | C | ? |  ROADMAP 2.305 r2: the gap (spaces) between the traced ink's near side and a head's near edge within which the ink LANDS on that head LAND_GAP_SPACES = 0.5 |  |
| staged/page_arcs.py:44 | `TARGET_SP_PX = 16.0` | sp |  | C | ? | TARGET_SP_PX = 16.0 |  |
| staged/page_arcs.py:45 | `RUN_MAX_SP = 0.62` | sp |  | C | REFUSES | RUN_MAX_SP = 0.62 a column run thicker than this is not arc ink (arc middles ~0.15-0.35 sp; a steep arc end is cut off here) |  |
| staged/page_arcs.py:46 | `TOL_SP = 0.3` | sp |  | C | ? | TOL_SP = 0.30 how far from the predicted centre the next run may lie |  |
| staged/page_arcs.py:47 | `GAP_SP = 1.25` | sp |  | C | ? | GAP_SP = 1.25 the widest hole a track bridges (a carved rule ~0.2 sp, a blanked stem ~0.3 sp, a head box ~1.3 sp) |  |
| staged/page_arcs.py:48 | `SLOPE_SP = 1.5` | sp |  | C | ? | SLOPE_SP = 1.5 the stretch of its own recent points a track predicts from |  |
| staged/page_arcs.py:49 | `MIN_WIDTH_SP = 1.4` | sp |  | C | ? | MIN_WIDTH_SP = 1.4 |  |
| staged/page_arcs.py:51 | `EXT_ALL = 1` | ? |  | C | REFUSES | EXT_ALL = 1 the extension runs through every claim (a head too): an arc's end is carried on to the note it stops at |  |
| staged/page_arcs.py:52 | `EXT_MIN_SP = 1.0` | sp |  | C | ? | EXT_MIN_SP = 1.0 a run shorter than this is not extended |  |
| staged/page_arcs.py:53 | `EXT_TOL_SP = 0.2` | sp |  | C | ? | EXT_TOL_SP = 0.2 the extension takes ink this close to the end's tangent |  |
| staged/page_arcs.py:54 | `EXT_FIT_SP = 4.0` | sp |  | C | ? | EXT_FIT_SP = 4.0 the extension follows the quadratic fitted to this much of the run's end |  |
| staged/page_arcs.py:55 | `EXT_THICK = 1.5` | px |  | E | ? | EXT_THICK = 1.5 ... no thicker than this many times the run's own median thickness (+1 px) |  |
| staged/page_arcs.py:56 | `EXT_MAX_SP = 4.0` | sp |  | C | ? | EXT_MAX_SP = 4.0 ... for at most this long a stretch |  |
| staged/page_arcs.py:63 | `JAG_SHORT_SP = 0.035` | sp |  | C | ? | JAG_SHORT_SP = 0.035 a run under two smoothing windows is measured against its own quadratic, which a clean arc follows to 0.01-0.025 and a head's rim or a letter does no |  |
| staged/page_arcs.py:64 | `SHORT_RUN_SP = 4.0` | sp |  | C | ? | SHORT_RUN_SP = 4.0 |  |
| staged/page_arcs.py:65 | `SHORT_THICK_SP = 0.5` | sp |  | C | DECIDES | SHORT_THICK_SP = 0.5 a short run this thick at its middle is a head's base or a beam stub (develop pages: 1 under a detector arc box, 14 under none) |  |
| staged/page_arcs.py:66 | `JAG_SP = 0.08` | sp |  | C | ? | JAG_SP = 0.08 rms off the 1-sp running mean |  |
| staged/page_arcs.py:69 | `CUSP_SP = 0.75` | sp |  | C | DECIDES | CUSP_SP = 0.75 the stretch each side of a hole the slope is read over |  |
| staged/page_arcs.py:70 | `CUSP_GAP_SP = 0.3` | sp |  | C | ? | CUSP_GAP_SP = 0.3 a bridged hole at least this wide (a blanked head is ~1.2 sp) |  |
| staged/page_arcs.py:71 | `HUG_SP = 0.3` | sp |  | C | ? | HUG_SP = 0.3 a run's body this close to a compact claimed mark's box is its rim |  |
| staged/page_arcs.py:77 | `FERMATA_MAX_SP = 4.5` | sp |  | C | ? | FERMATA_MAX_SP = 4.5 a fermata's hump is at most this wide |  |
| staged/page_arcs.py:79 | `CORNER_TURN = 0.35` | ? |  | C | ? | CORNER_TURN = 0.35 the change of slope that makes a corner where two touching arcs meet |  |
| staged/page_arcs.py:80 | `BOW_SP = 4.0` | sp |  | C | DECIDES | BOW_SP = 4.0 the stretch each side of a hole the pieces' own bow is read over |  |
| staged/page_arcs.py:81 | `CUSP_SLOPE = 0.15` | ? |  | C | ? | CUSP_SLOPE = 0.15 both sides at least this steep, opposite signs |  |
| staged/page_arcs.py:83 | `STRAIGHT_SAG_SP = 0.1` | sp |  | C | ? | STRAIGHT_SAG_SP = 0.10 a run straighter than this ... |  |
| staged/page_arcs.py:84 | `MIN_THICK_SP = 0.1` | sp |  | B | DECIDES | MIN_THICK_SP = 0.10 median thickness under this is a staff line's residue (a staff line is ~0.1 sp) |  |
| staged/page_arcs.py:85 | `STRAIGHT_REL = 0.02` | ratio |  | B | DECIDES | STRAIGHT_REL = 0.02 a run whose bow is under this share of its width is a line: a slur's bow grows with its length (measured: lines 0.005, the flattest tie 0.05) |  |
| staged/page_arcs.py:86 | `STRAIGHT_LONG_REL = 0.047` | ratio |  | B | DECIDES | STRAIGHT_LONG_REL = 0.047 a run over STRAIGHT_MAX_SP whose bow is under this share of its width is a line (round-1 measurement on 5 pages: 12 lines at 0.023-0.045, the fl |  |
| staged/page_arcs.py:87 | `STRAIGHT_MAX_SP = 4.0` | sp |  | C | DECIDES | STRAIGHT_MAX_SP = 4.0 ... and longer than this is a line, not an arc |  |
| staged/page_arcs.py:89 | `POINT_STEP_SP = 0.25` | sp |  | C | ? | POINT_STEP_SP = 0.25 one filed point per this many staff spaces |  |
| staged/page_arcs.py:93 | `ARC_NOMINAL_SP = 0.25` | sp |  | C | ? | ARC_NOMINAL_SP = 0.25 r3: an arc's depth when it leaves the line on one side only (the rest lies in the line) |  |
| staged/page_arcs.py:102 | `THICK_PASS = 1` | ? |  | C | REFUSES | THICK_PASS = 1 r3: a heavy slur's middle (thicker than RUN_MAX_SP) is read as a thick run, never a hole |  |
| staged/page_arcs.py:103 | `THICK_MAX_SP = 1.3` | sp |  | C | ? | THICK_MAX_SP = 1.3 ... up to this thick (a head is as tall, and no wider than ~1.3 sp: a thick track must be longer than THICK_MIN_SP) |  |
| staged/page_arcs.py:104 | `THICK_MIN_SP = 3.0` | sp |  | C | ? | THICK_MIN_SP = 3.0 |  |
| staged/page_arcs.py:109 | `TRIM_MIN_SP = 1.0` | sp |  | C | ? | TRIM_MIN_SP = 1.0 |  |
| staged/page_arcs.py:111 | `ARC_IN_WORD = 1` | ? |  | C | ? | ARC_IN_WORD = 1 r3: an arc-shaped component inside a word's rectangle is not the word's |  |
| staged/page_arcs.py:112 | `ARC_COMP_MIN_SP = 3.0` | sp |  | C | ? | ARC_COMP_MIN_SP = 3.0 |  |
| staged/page_arcs.py:113 | `RAGGED_TRIM = 1` | ? |  | C | ? | RAGGED_TRIM = 1 r3: cut the junction points off an arc fused with a stem / flag / beam, and judge what is left |  |
| staged/page_arcs.py:114 | `RAGGED_DEV_SP = 0.2` | sp |  | C | ? | RAGGED_DEV_SP = 0.2 |  |
| staged/page_arcs.py:120 | `LINK_BOW_REL = 0.03` | ratio |  | B | ? | LINK_BOW_REL = 0.03 the joint curve's bow, as a share of its width, at least (the flattest real tie measured 0.05, lines 0.005) |  |
| staged/page_arcs.py:121 | `TAPER_SLUR = 1` | ? |  | C | REFUSES | TAPER_SLUR = 1 r4: a long flat slur is a lens: thinner at both ends than in the middle. A run over STRAIGHT_MAX_SP that bows at least STRAIGHT_REL of its width and tapers |  |
| staged/page_arcs.py:122 | `TAPER_MID_MAX_SP = 0.5` | sp |  | C | ? | TAPER_MID_MAX_SP = 0.5 ... whose middle is no thicker than this (a beam is ~0.6-0.9 sp, a staff line ~0.1; develop pages: real flat slurs 0.25-0.5) |  |
| staged/page_arcs.py:123 | `TAPER_END_RATIO = 0.9` | ratio |  | B | REFUSES | TAPER_END_RATIO = 0.9 ... and whose end thickness (mean of the outer 12% each side) is at most this share of the mean of the middle 30% (develop pages: 31 of 41 refused-s |  |
| staged/page_arcs.py:124 | `FIT_MAX_SP = 5.0` | sp |  | C | DECIDES | FIT_MAX_SP = 5.0 ... on a run no wider than this (a longer run that joins an arc to a head or a stem is judged by its jag; 2 real arcs were lost to this on long runs) |  |
| staged/page_arcs.py:125 | `FIT_RMS_SP = 0.12` | sp |  | C | DECIDES | FIT_RMS_SP = 0.12 r4: a run that stays further than this (rms) off its own smooth fit (quadratic, quartic over 8 sp) is a zig-zag through letters, not an arc ("piu f" rea |  |
| staged/page_arcs.py:126 | `GLYPH_COMP = 1` | ? |  | C | DECIDES | GLYPH_COMP = 1 r4: a small ink component that no detector mark overlaps and that is not one thin bowed stroke is a glyph (a digit, a letter, a rehearsal frame): page mark |  |
| staged/page_arcs.py:127 | `GLYPH_MAX_W_SP = 5.5` | sp |  | C | ? | GLYPH_MAX_W_SP = 5.5 |  |
| staged/page_arcs.py:128 | `GLYPH_MAX_H_SP = 4.5` | sp |  | C | ? | GLYPH_MAX_H_SP = 4.5 |  |
| staged/page_arcs.py:129 | `GLYPH_MIN_H_SP = 0.9` | sp |  | C | ? | GLYPH_MIN_H_SP = 0.9 shorter than this it can be a tie's piece or a dash |  |
| staged/page_arcs.py:130 | `ERASED_EXT = 0` | ? |  | C | ? | ERASED_EXT = 0 r4 EXPERIMENT, OFF (tried and removed, see FINDINGS r4; delete when the round closes): an arc's thin tail can lie INSIDE a staff line's erased band (Sean's |  |
| staged/page_arcs.py:131 | `ERASED_GAP_SP = 2.5` | sp |  | C | ? | ERASED_GAP_SP = 2.5 |  |
| staged/page_arcs.py:132 | `ERASED_TOL_SP = 0.35` | sp |  | C | ? | ERASED_TOL_SP = 0.35 |  |
| staged/page_arcs.py:133 | `ERASED_FIT_SP = 1.5` | sp |  | C | ? | ERASED_FIT_SP = 1.5 |  |
| staged/page_arcs.py:134 | `ERASED_MIN_SLOPE = 0.1` | ? |  | C | ? | ERASED_MIN_SLOPE = 0.1 |  |
| staged/page_arcs.py:135 | `WIDE_BOX = 1` | ? |  | C | DECIDES | WIDE_BOX = 1 r4: a detector box of a class that is one note-space wide (accidental, head, dot, flag) that is wider than WIDE_BOX_SP is not that mark (round-2 tile 9: a 4- |  |
| staged/page_arcs.py:136 | `WIDE_BOX_SP = 2.5` | sp |  | C | ? | WIDE_BOX_SP = 2.5 |  |
| staged/page_arcs.py:1330 | `SEED_PAD_SP = 0.5` | sp |  | n/a | ? | SEED_PAD_SP = 0.5 |  |
| staged/page_arcs.py:1331 | `SEED_MIN_WIDTH_SP = 0.9` | sp |  | n/a | ? | SEED_MIN_WIDTH_SP = 0.9 |  |
| staged/page_heads.py:502 | `CURVE_MAX_LEN_SP = 2.0` | sp |  | C | REFUSES |  a curve longer than this is an arc piece, not a head's outline (`stroke_owner.shape_fit` head_outline_piece) CURVE_MAX_LEN_SP = 2.0 |  |
| staged/page_owner.py:89 | `ARC_MIN_BOW_SP = 0.15` | sp |  | C | REFUSES |  ledger line, a beam or a hairpin leg the detector boxed as a tie/slur, not curve ink -- and its rows are no reason to drop a ledger rung. The number is 2.245's `box_kind | * rank 11: D, REFUSES a flat arc; frozen sample (18 of 19 Brahms traces) |
| staged/stroke_map.py:49 | `CURVE_MIN_SPACES = 1.5` | sp |  | C | ? | CURVE_MIN_SPACES = 1.5 |  |
| staged/stroke_map.py:50 | `CURVE_MAX_THICK_SPACES = 0.5` | sp |  | C | ? | CURVE_MAX_THICK_SPACES = 0.5 |  |
| staged/stroke_map.py:51 | `CURVE_MIN_ASPECT = 2.0` | ratio |  | B | ? | CURVE_MIN_ASPECT = 2.0 |  |
| staged/stroke_map.py:56 | `LINE_SEARCH_SPACES = 0.4` | sp |  | C | ? | LINE_SEARCH_SPACES = 0.4 |  |
| staged/stroke_owner.py:184 | `ARC_MAX_THICK_SP = 0.5` | sp |  | C | ? | ARC_MAX_THICK_SP = 0.5 2.202: an arc / hairpin remnant is 0.06-0.44, a beam >= 0.55 |  |

## beam (77; A 5, B 13, C 44, D 14, E 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| line_detection.py:1341 | `BEAM_OWN_EXTENT_MIN_THICK = 0.6` | ? |  | C | ? | BEAM_OWN_EXTENT_MIN_THICK = 0.6 |  |
| line_detection.py:1508 | `BEAM_RESCUE_THICKNESS_LINES = 1.75` | ? | LB | D | DECIDES |  too-tall component is re-opened with (`detect_beams(rescue_tall=True)`). A hairpin's line is about one line thick; Brahms p0-1 and Litolff p1-3's beams read 2.0 or more  |  |
| line_detection.py:1511 | `BEAM_RESCUE_BAND_COVER = 0.5` | ratio |  | B | DECIDES |  A row belongs to a rescued beam's own band where at least this share of the stroke's width is inked on it. BEAM_RESCUE_BAND_COVER = 0.5 |  |
| staged/adjudicators/notehead_precision.py:752 | `BEAM_PIECE_COVER_MIN = 0.7` | ratio |  | B | DECIDES |  The share of the box that must lie inside ONE read beam stroke. BEAM_PIECE_COVER_MIN = 0.7 |  |
| staged/adjudicators/notehead_precision.py:754 | `BEAM_PIECE_HEIGHT_MAX_SPACES = 0.9` | sp |  | C | ? |  The box is no taller than this many staff spaces. BEAM_PIECE_HEIGHT_MAX_SPACES = 0.9 |  |
| staged/adjudicators/rhythm.py:433 | `BEAM_EDGE_TOLERANCE_WIDTHS = 1.0` | ? |  | C | DECIDES |  ⚠️ A beam stroke ends at the last stem it joins, so a note at the end of a group sits within a notehead's width of the end and the reading is genuinely *"under it, possi |  |
| staged/adjudicators/rhythm.py:1073 | `BEAM_THICKNESS_RATIO_MIN = 1.75` | ratio |  | B | DECIDES |  (hairpin lines, slur and tie arcs, staff-line residue) read 1.75 or less on both. 1.75 sits in the empty interval of both plates (it is the midpoint of the thin populati | * rank 6: B (local line thicknesses), DECIDES beam vs line; both plates (4fc81f652, 2.74; Sean 10-09) |
| staged/adjudicators/rhythm.py:1084 | `BEAM_CORE_HEAD_REACH_SPACES = 5.5` | sp | L | D | REFUSES |  slack. ⚠️ MEASURED, `FINDINGS.md` 2.82: on Litolff's merging plate a thick staff line between a bar's barlines or lattice verticals "stands on a stem at each end" by the |  |
| staged/adjudicators/rhythm.py:1085 | `BEAM_CORE_HEAD_X_SPACES = 0.4` | sp |  | C | ? | BEAM_CORE_HEAD_X_SPACES = 0.4 |  |
| staged/adjudicators/rhythm.py:1138 | `BEAM_ONE_STEM_HEAD_COLUMNS_MIN = 2` | count |  | A | REFUSES |  ROADMAP 2.82 (Sean, 2026-10-10: *"The 'doesn't touch more than one stem' is off"*). A stroke is refused `one_stem` only where the record POSITIVELY says no second note s |  |
| staged/adjudicators/rhythm.py:1140 | `BEAM_HEAD_COLUMN_SEPARATION_SPACES = 0.7` | sp |  | C | ? |  Two head boxes closer than this (spaces, centre to centre) are one column (a chord). BEAM_HEAD_COLUMN_SEPARATION_SPACES = 0.7 |  |
| staged/adjudicators/rhythm.py:1242 | `BEAM_SAGITTA_MAX_SPACES = 0.4` | sp |  | C | REFUSES |  slur strokes read 0.18-0.26. The populations overlap, so a cut that keeps the fused beam cannot refuse a slur by its bow alone -- the thickness rule does that work. What |  |
| staged/adjudicators/rhythm.py:1247 | `BEAM_BEAMLET_GAP_SPACES = 1.0` | sp |  | C | ? |  How far (staff spaces) a one-stem stroke may lie from a stroke that stands on two stems and still be that beam group's own secondary level (a beamlet). A secondary beam  |  |
| staged/adjudicators/rhythm.py:1262 | `BEAM_THROUGH_HEADS_MIN = 0.5` | count | L | D | ? |  Litolff p1-3 the ones over 0.5 are rows of heads and ledger lines through them; a beam stands at the far end of its stems and runs BETWEEN them. The cut sits in the gap  |  |
| staged/adjudicators/rhythm.py:1271 | `BEAM_HEAD_BOX_MAX_SPACES = 2.2` | sp |  | C | REFUSES |  (`FINDINGS.md` §16): a `noteheadWholeOnLine` box 3.2 spaces wide stood over a real stem-down beam (cell 1/0/0/4) and would have refused it as "the heads' ink" -- so a bo |  |
| staged/adjudicators/rhythm.py:1435 | `BEAM_STEMS_ENDING_MIN = 2` | px |  | E | REFUSES |  the page crops (a sloped beam's end window misses its stem; 4 of the 5 are detector boxes); the dynamic letter's foot bar 2.77 was built to refuse has none (its stems en |  |
| staged/adjudicators/rhythm.py:1439 | `BEAM_STEMS_ENDING_SEPARATION_SPACES = 0.4` | sp |  | C | DECIDES |  Two read stems closer than this (staff spaces, centre to centre) are one stem read twice (a stem fused to a head and cut in two), not two stems. BEAM_STEMS_ENDING_SEPARA |  |
| staged/adjudicators/rhythm.py:1488 | `BEAM_STEM_RUNS_PAST_MAX_SPACES = 2.5` | sp | L | D | REFUSES |  2nd level starts ~0.9 space from the tip, the 3rd ~1.8, the 4th ~2.7. A stroke the stem runs past by more than this is at the 5th level or deeper, i.e. not a beam of thi |  |
| staged/adjudicators/rhythm.py:1494 | `BEAM_DOUBLE_THICKNESS_RATIO_MIN = 1.8` | ratio |  | A | NARROWS |  ROADMAP 2.141h fix 1. A stroke at least this many times as thick as ANOTHER kept stroke of the same cell (measured at the strokes' own columns, `Q.BEAM_STROKE_INK` `thic |  |
| staged/adjudicators/rhythm.py:1551 | `BEAM_STACK_BOX_EXCESS_MIN = 0.6` | count | B | D | ? |  single beam over a box that wide would be: the box bounds the STACK, so two levels stand ~one more beam taller. A single sloped beam's box grows with its slope; that ris |  |
| staged/adjudicators/rhythm.py:1554 | `BEAM_STACK_BOX_NEAR_MISS = 0.05` | ? | L | D | NARROWS |  ROADMAP 2.140 round 2 (CLAUDE.md section 4: a cut-off tuned on our plates may only NARROW; a refusal says how close it came). A box witness within this of its cut is a n |  |
| staged/adjudicators/rhythm.py:1593 | `BEAM_STEM_RUN_UNIT_RATIO_MIN = 0.7` | ratio | LB | D | REFUSES |  ROADMAP 2.140. A page stroke counts only if it is at least this fraction of ONE beam's thickness (the cell's CV strokes' median `thickness_spaces`): a clearly thinner ru |  |
| staged/adjudicators/rhythm.py:4055 | `OPEN_ON_STEM_BEAMED_CENTER_MAX = 0.8` | count |  | A | DECIDES | OPEN_ON_STEM_BEAMED_CENTER_MAX = 0.80 strokes joined to the stem: the head must read clearly hollow to be decided |  |
| staged/adjudicators/stem_value.py:709 | `BEAM_END_TIP_MAX_SP = 1.0` | sp | B | D | DECIDES |  lane report cannot confirm it: tiles can). MEASURED on the 2.202strokes records, every stem with >= 2 heads whose direction is decided (Brahms pp.0,4,5,8,12,14,19,25; 1, |  |
| staged/adjudicators/stem_value.py:710 | `BEAM_END_OTHER_MIN_SP = 2.5` | sp |  | C | ? | BEAM_END_OTHER_MIN_SP = 2.5 |  |
| staged/arcs_system.py:70 | `STRAIGHT_BEAM_THICK_SPACES = 0.4` | sp | B | D | REFUSES |  ... and only a straight trace at least this thick (a beam's stroke) is refused: a long flat slur is straight but thin, and left on the page the beam reader takes it for  | * rank 11: D, REFUSES; one Brahms case |
| staged/arcs_system.py:129 | `BEAM_TWIN_IOU = 0.6` | ? |  | C | ? | BEAM_TWIN_IOU = 0.6 |  |
| staged/arcs_system.py:131 | `BEAM_TWIN_OVERLAP = 0.5` | ? |  | B | ? |  A beam box can hold nothing but the stroke only where this share of it lies inside one of the arc's own boxes. BEAM_TWIN_OVERLAP = 0.5 |  |
| staged/beam_strokes.py:47 | `BEAM_MIN_THICKNESS_SP = 0.5` | sp |  | C | ? |  A beam's thickness, staff spaces. Measured gap between the two thickness populations of the strokes that span >= 2 stems (module doc). BEAM_MIN_THICKNESS_SP = 0.5 |  |
| staged/beam_strokes.py:53 | `BEAM_DOUBT_MIN_THICKNESS_SP = 0.4375` | sp | LB | D | NARROWS |  between the two populations and thickness cannot tell a beam from a thin span. Measured on the frozen sample, horizontal strokes touching >= 2 stems, sixteenths of a spa | * rank 6: D, NARROWS below; both plates frozen sample (1a4d7c554, 2.202f); absolute sp |
| staged/beam_strokes.py:63 | `LEVEL_MIN_SEPARATION_SPACES = 0.4` | sp |  | C | ? |  Two strokes touching one stem whose centres are closer than this (staff spaces) are one level (a stroke cut in two by a crossing). LEVEL_MIN_SEPARATION_SPACES = 0.4 |  |
| staged/beam_strokes.py:69 | `FUSED_DOUBLE_MIN_THICKNESS_SPACES = 1.0` | sp |  | B | DECIDES |  tip window above is built on: level pitch ~0.75 sp). A slab that spans the stems and is this thick is TWO levels fused by the scan, not one beam (a single beam is 0.5-0. |  |
| staged/beam_strokes.py:71 | `FUSED_MAX_THICKNESS_SPACES = 1.75` | sp |  | C | ? | FUSED_MAX_THICKNESS_SPACES = 1.75 |  |
| staged/beam_strokes.py:72 | `FUSED_LOCAL_MIN_SPACES = 0.8` | sp |  | C | DECIDES | FUSED_LOCAL_MIN_SPACES = 0.8 2.202e: the cut on the thickness AT THIS STEM's x (the 12-sample profile is coarse: a second beam that STARTS at this stem reads 0.96; measur |  |
| staged/beam_strokes.py:73 | `FUSED_OUTER_EDGE_SPACES = 0.6` | sp |  | C | ? | FUSED_OUTER_EDGE_SPACES = 0.6 |  |
| staged/beam_strokes.py:76 | `JOIN_MAX_GAP_SPACES = 0.5` | sp |  | C | REFUSES |  ROADMAP 2.202b. A beam-role stroke that does not TOUCH the head's stem stroke but ends within this many staff spaces of it (box to box: the scan cuts a beam where it mee |  |
| staged/beam_strokes.py:78 | `JOIN_OUTER_EDGE_SPACES = 0.6` | sp |  | C | ? |  ...and the joining beam's OUTER edge lies within this many staff spaces of the stem's tip (the first level of a beam). JOIN_OUTER_EDGE_SPACES = 0.6 |  |
| staged/beam_strokes.py:166 | `FACE_JOIN_MAX_SPACES = 1.0` | sp |  | A | REFUSES |  2.202f: how far short of the beam's face a stem may stop and still be the beam's (Sean 2026-10-28: "the beam covers the width of where those notes with stems occur ... t |  |
| staged/beam_strokes.py:204 | `END_JOIN_LEVEL_SPACES = 0.3` | sp |  | C | ? | END_JOIN_LEVEL_SPACES = 0.3 |  |
| staged/beam_strokes.py:251 | `CLOT_BAND_SLACK_SPACES = 0.5` | sp |  | C | ? | CLOT_BAND_SLACK_SPACES = 0.5 |  |
| staged/beam_strokes.py:256 | `OUTER_LEVEL_MAX_SPACES = 1.35` | sp |  | C | ? | OUTER_LEVEL_MAX_SPACES = 1.35 |  |
| staged/beam_strokes.py:625 | `ONE_FUSED_MIN_WIDTH_SPACES = 0.6` | sp | L | D | ? |  A vertical stroke wider than this has head ink fused to it (Litolff merges): its stem stands at the far end (`stem_strokes.FUSED_MIN_WIDTH_SPACES`). ONE_FUSED_MIN_WIDTH_ |  |
| staged/beam_strokes.py:839 | `END_ON_MIN_LENGTH_SPACES = 2.0` | sp | L | D | ? |  ...and only a stroke long enough to be the free part of a stem: the nine bridged stems are 2.4-4.6 sp long; a 1.6 sp upright over a head between ledger lines was the nex |  |
| staged/beam_strokes.py:1014 | `BEAM_ONE_MAX_THICKNESS_SPACES = 0.8` | sp |  | C | ? |  A beam-shaped stroke: flat, as thick as a beam (`BEAM_DOUBT_MIN_THICKNESS_SP` up to what one beam is: `BEAM_ONE_MAX_THICKNESS_SPACES`) and long enough to span two stems. |  |
| staged/beam_strokes.py:1015 | `BEAM_SHAPE_MIN_LENGTH_SPACES = 2.0` | sp |  | C | ? | BEAM_SHAPE_MIN_LENGTH_SPACES = 2.0 |  |
| staged/beam_strokes.py:1016 | `BEAM_SHAPE_MAX_ANGLE = 25.0` | ? |  | C | ? | BEAM_SHAPE_MAX_ANGLE = 25.0 |  |
| staged/beam_strokes.py:1133 | `THICK_REACH_SPACES = 2.0` | sp | B | D | ? |  stem. MEASURED on the tile pages, every stem under a stroke that is double over part of its run (Brahms p17, p4: a group whose second beam covers only some notes; the pr |  |
| staged/beam_strokes.py:1160 | `STUB_FIRST_LEVEL_SPACES = 0.6` | sp |  | C | ? | STUB_FIRST_LEVEL_SPACES = 0.6 |  |
| staged/gather.py:7282 | `BEAM_STEM_JOIN_GAP_TOLERANCE_THICKNESS_MULT = 1.0` | ? |  | A | DECIDES |  every scan at every DPI. A staff line and a beam stroke are drawn with comparable engraving weight, so a break the width of ONE line is the largest gap a shattering plat |  |
| staged/gather.py:7286 | `BEAM_STEM_JOIN_DEFAULT_THICKNESS_SPACES = 0.09` | sp |  | B | ? |  Where a cell's own line thickness was never traced (mirrors `LEDGER_ RUNG_INK_DEFAULT_THICKNESS_SPACES` -- same fallback, same reason: no cell on either of this lane's o |  |
| staged/gather.py:12673 | `BEAM_INK_END_STEM_SPACES = 1.5` | sp |  | C | ? |  How far past the stroke's own band a vertical run must reach to be a stem standing at that end, in staff spaces. A beam's stems run at least this far from it (a stem is  |  |
| staged/gather.py:12676 | `BEAM_INK_END_WINDOW_SPACES = 0.4` | sp |  | C | ? |  How wide an end window is searched for that stem, in staff spaces either side of the stroke's end. BEAM_INK_END_WINDOW_SPACES = 0.4 |  |
| staged/gather.py:12678 | `BEAM_INK_MIN_COVER = 0.5` | ratio |  | B | ? |  A stroke needs ink in at least this share of its own columns to be measured. BEAM_INK_MIN_COVER = 0.5 |  |
| staged/gather.py:12681 | `BEAM_INK_END_TRIM_SPACES = 0.5` | sp |  | C | ? |  The curvature fit ignores this many spaces at each end, where a stem or head can bulge the run. BEAM_INK_END_TRIM_SPACES = 0.5 |  |
| staged/gather.py:12682 | `BEAM_INK_THRESHOLD = 180` | conf |  | C | ? | BEAM_INK_THRESHOLD = 180 |  |
| staged/gather.py:12685 | `BEAM_INK_LINE_FLANK_SPACES = 3.0` | sp |  | B | DECIDES |  How far either side of a stroke the staff lines are read, in staff spaces, so a beam lying ON a line does not set the line's own thickness. BEAM_INK_LINE_FLANK_SPACES =  |  |
| staged/gather.py:12709 | `BEAM_INK_CORE_RATIO = 1.75` | ratio |  | B | ? | BEAM_INK_CORE_RATIO = 1.75 |  |
| staged/gather.py:12712 | `BEAM_INK_CORE_MIN_SPACES = 2.0` | sp |  | C | DECIDES |  A stretch shorter than this is a head, a stem's foot or a blot. A notehead is ~1.3 spaces wide, and the beam between two stems of the closest-set group is longer. BEAM_I |  |
| staged/gather.py:12713 | `BEAM_INK_CORE_SMOOTH_SPACES = 0.3` | sp |  | C | ? | BEAM_INK_CORE_SMOOTH_SPACES = 0.3 |  |
| staged/gather.py:13086 | `BEAM_STEM_COLUMN_OFFSET_SPACES = 0.45` | sp |  | B | DECIDES |  Distance of the read column from the stem's centre line, staff spaces (clear of the stem's own width, inside a beam). BEAM_STEM_COLUMN_OFFSET_SPACES = 0.45 |  |
| staged/gather.py:13088 | `BEAM_STEM_WINDOW_IN_SPACES = 2.4` | sp |  | C | ? |  The tip window, staff spaces: this far from the tip toward the head, and this far past it. BEAM_STEM_WINDOW_IN_SPACES = 2.4 |  |
| staged/gather.py:13089 | `BEAM_STEM_WINDOW_OUT_SPACES = 0.3` | sp |  | C | ? | BEAM_STEM_WINDOW_OUT_SPACES = 0.3 |  |
| staged/gather.py:13091 | `BEAM_STEM_RUN_MIN_SPACES = 0.36` | sp |  | C | ? |  A stroke is at least this thick (a staff line is ~0.2; a beam ~0.5-0.7 on the plates measured). BEAM_STEM_RUN_MIN_SPACES = 0.36 |  |
| staged/gather.py:13093 | `BEAM_STEM_RUN_REACH_MIN_SPACES = 1.6` | sp |  | C | ? |  ...and its ink continues sideways, away from the stem, at least this far (a notehead is ~1.2 wide). BEAM_STEM_RUN_REACH_MIN_SPACES = 1.6 |  |
| staged/gather.py:13097 | `BEAM_STEM_RUN_LINE_RATIO_MIN = 1.75` | sp | L | D | ? |  ...and at least this many staff-line thicknesses (measured locally, `local_line_thickness`): the existing convention that a beam is thicker than a line (`rhythm.BEAM_THI |  |
| staged/page_arcs.py:140 | `BEAM_RAW = 1` | ? |  | B | DECIDES | BEAM_RAW = 1 r4: a run that lies on RAW ink (nothing erased or blanked) taller than BEAM_RAW_SP in at least BEAM_RAW_SHARE of its points and that does not thin toward its |  |
| staged/page_arcs.py:141 | `BEAM_RAW_SP = 0.45` | sp |  | C | ? | BEAM_RAW_SP = 0.45 (develop pages, 5 pages: 16 of 109 NEW runs and 0 of 553 witnessed runs) |  |
| staged/page_arcs.py:142 | `BEAM_RAW_SHARE = 0.9` | ratio |  | B | ? | BEAM_RAW_SHARE = 0.9 |  |
| staged/page_arcs.py:143 | `BEAM_RAW_ENDS = 0.85` | ? |  | C | ? | BEAM_RAW_ENDS = 0.85 |  |
| staged/page_arcs.py:144 | `BEAM_STEM_NEAR_SP = 0.8` | sp |  | C | ? | BEAM_STEM_NEAR_SP = 0.8 (a stem within this of the run's end) |  |
| staged/page_arcs.py:145 | `BEAM_STEM_SP = 2.0` | sp |  | C | ? | BEAM_STEM_SP = 2.0 ... and standing on stems: raw ink at least this tall at both ends of the run |  |
| staged/page_arcs.py:146 | `BEAM_LIKE_SP = 0.5` | sp |  | C | DECIDES | BEAM_LIKE_SP = 0.5 r3: a run this thick at its middle that does not taper (end / middle thickness above BEAM_TAPER) is a beam |  |
| staged/page_arcs.py:147 | `BEAM_TAPER = 0.75` | ? |  | C | ? | BEAM_TAPER = 0.75 |  |
| staged/page_beams.py:48 | `GRID_SPACES = 8.0` | sp |  | C | ? |  A position grid: strokes are registered in every bin their box touches, bins this many staff spaces on a side. GRID_SPACES = 8.0 |  |
| staged/page_beams.py:51 | `NEIGHBOUR_SPACES = 1.5` | sp |  | C | ? |  The strokes a role is judged against: those whose box meets this stroke's box grown by this many spaces (a stem hangs up to FACE_JOIN_MAX_SPACES = 1.0 below a beam's fac |  |
| staged/page_heads.py:499 | `BEAM_MIN_W_SP = 1.8` | sp |  | C | DECIDES |  a horizontal piece at least this wide and this flat is a beam piece, not head ink (2.284 r7's bar test, `rhythm._head_owned_bar`) BEAM_MIN_W_SP = 1.8 |  |
| staged/page_heads.py:500 | `BEAM_MIN_ASPECT = 2.5` | ratio |  | B | ? | BEAM_MIN_ASPECT = 2.5 |  |

## flag (72; A 8, B 7, C 44, D 12, n/a 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| staged/adjudicators/ownership.py:4406 | `ARTIC_STEM_TIP_MAX_GAP_SPACES = 1.0` | sp |  | C | DECIDES |  neighbour). One space is twice the larger padding plus a half-space quantum and is still less than the 2-space gap at which a mark reads as unattached. WHAT WOULD FALSIF |  |
| staged/adjudicators/ownership.py:4412 | `ARTIC_STEM_TIP_MAX_DX_HEAD_WIDTHS = 1.0` | ? |  | C | ? |  The mark's x-centre within this many NOTEHEAD WIDTHS of the stem's centre. A stem-side mark is centred on the stem (staccato: Dorico, LilyPond `toward-stem-shift 1.0`) o |  |
| staged/adjudicators/rhythm.py:3890 | `BARE_STEM_TIP_SPACES = 0.6` | sp |  | C | ? |  far across the stem it may lie (spaces). Phase 1's PROBE definition (`benchmarks/omr-missing-notes-2026-09/probe/l281_population.py:: stroke_at_tip`) -- Sean's blind til |  |
| staged/adjudicators/rhythm.py:4478 | `TIP_START_SPACES = 0.6` | sp |  | A | DECIDES |  A stroke is AT a stem's tip when its tip-side edge is at most this far inward of the stem's end (the first hook / beam level starts there); each further level within `TI |  |
| staged/adjudicators/rhythm.py:4479 | `TIP_LEVEL_GAP_SPACES = 1.1` | sp |  | C | ? | TIP_LEVEL_GAP_SPACES = 1.1 |  |
| staged/adjudicators/rhythm.py:4486 | `TIP_BAR_MIN_SPACES = 1.8` | sp | L | D | DECIDES |  ROADMAP 2.284 r7 (`OMR_PAGE_LEDGER_OWNS`): a BAR (wider than any head, a flat run) that a HEAD box owns is not "another mark's ink" at a stem tip. Litolff p2 2/1/5/13/0: |  |
| staged/adjudicators/rhythm.py:4487 | `TIP_BAR_ASPECT_MIN = 2.5` | ratio |  | B | ? | TIP_BAR_ASPECT_MIN = 2.5 |  |
| staged/arc_claim.py:933 | `TIP_MAX_SPACES = 4.5` | sp | LB | D | DECIDES |  stem is 3.5 spaces from the head, Gould; measured on Litolff p10-11 + Brahms p0/p5, 2408 tips: the modal tip stands 3-3.5 sp from its head's centre, 172 at 4-4.5, 72 at  | * rank 12: D; Gould 3.5 + 2408 tips both plates |
| staged/beam_strokes.py:55 | `HOOK_MAX_SPACES = 1.6` | sp |  | C | DECIDES |  A flag's hook is at most this long (staff spaces) to be DECIDED a hook; up to `+ HOOK_NEAR_MISS_SPACES` it is `hook_or_stub`. HOOK_MAX_SPACES = 1.6 |  |
| staged/beam_strokes.py:56 | `HOOK_NEAR_MISS_SPACES = 0.8` | sp |  | C | ? | HOOK_NEAR_MISS_SPACES = 0.8 |  |
| staged/beam_strokes.py:60 | `TIP_OUTWARD_SPACES = 0.5` | sp |  | A | DECIDES |  The window at a stem's tip in which a stroke counts as one of its beam levels / hooks: from this far BEYOND the tip (the beam's outer edge past the stem end) to this far |  |
| staged/beam_strokes.py:61 | `TIP_INWARD_SPACES = 3.3` | sp |  | C | ? | TIP_INWARD_SPACES = 3.3 |  |
| staged/gather.py:5558 | `STEM_TIP_INK_NEAR_SPACES = -0.3` | sp |  | C | NARROWS |  `found False` NOTHING hangs from the tip (attached ink under `STEM_TIP_INK_EMPTY_AREA` square spaces). `found None` ink hangs there that is not flag-shaped (a beam or a  |  |
| staged/gather.py:5559 | `STEM_TIP_INK_FAR_SPACES = 3.6` | sp |  | C | ? | STEM_TIP_INK_FAR_SPACES = 3.6 |  |
| staged/gather.py:5563 | `STEM_TIP_INK_MIN_DEPTH_SPACES = 1.2` | sp |  | C | ? |  The window starts this far PAST the tip (a rounded tip, a flag root drawn over the stem's end) and runs back this far, but never into the stem's own head (`head_edge`):  |  |
| staged/gather.py:5566 | `STEM_TIP_INK_WIDTH_SPACES = 0.9` | sp |  | C | DECIDES |  The width of the density bands reported as `right` / `left` (the 2.18c numbers, kept as a MEASURE for the trace and the print checks; they decide nothing now), and how f |  |
| staged/gather.py:5567 | `STEM_TIP_INK_REACH_SPACES = 2.6` | sp |  | C | ? | STEM_TIP_INK_REACH_SPACES = 2.6 |  |
| staged/gather.py:5570 | `STEM_TIP_INK_SEED_SPACES = 1.0` | sp |  | n/a | REFUSES |  The stem's own ink in the first spaces from the tip seeds the connected ink. A stem box is a little thinner than its ink: ink within this far of the box is the stem's ow |  |
| staged/gather.py:5571 | `STEM_TIP_INK_EDGE_SPACES = 0.15` | sp |  | C | ? | STEM_TIP_INK_EDGE_SPACES = 0.15 |  |
| staged/gather.py:5579 | `STEM_TIP_INK_OUT_MIN_SPACES = 0.33` | sp | L | D | NARROWS |  25: 8 of 82 stems the cuts declined, every one a flag on the print) and a big Litolff flag whose ink starts 1.33 spaces from the tip -- so a flag is read as EITHER a thi | * rank 5: D, DECIDES flag; Litolff flag 1.33 + Sean's 21 flags |
| staged/gather.py:5580 | `STEM_TIP_INK_OUT_MAX_SPACES = 1.5` | sp |  | C | ? | STEM_TIP_INK_OUT_MAX_SPACES = 1.5 |  |
| staged/gather.py:5581 | `STEM_TIP_INK_ARM_MIN_SPACES = 0.4` | sp |  | C | ? | STEM_TIP_INK_ARM_MIN_SPACES = 0.40 |  |
| staged/gather.py:5582 | `STEM_TIP_INK_ARM_U_SPACES = 0.35` | sp |  | C | ? | STEM_TIP_INK_ARM_U_SPACES = 0.35 |  |
| staged/gather.py:5583 | `STEM_TIP_INK_ROOT_MAX_SPACES = 1.2` | sp |  | C | ? | STEM_TIP_INK_ROOT_MAX_SPACES = 1.2 |  |
| staged/gather.py:5584 | `STEM_TIP_INK_BIG_OUT_SPACES = 0.8` | sp |  | C | ? | STEM_TIP_INK_BIG_OUT_SPACES = 0.8 |  |
| staged/gather.py:5585 | `STEM_TIP_INK_BIG_ARM_SPACES = 1.0` | sp |  | C | ? | STEM_TIP_INK_BIG_ARM_SPACES = 1.0 |  |
| staged/gather.py:5586 | `STEM_TIP_INK_ROOT_BIG_SPACES = 1.6` | sp |  | C | ? | STEM_TIP_INK_ROOT_BIG_SPACES = 1.6 |  |
| staged/gather.py:5594 | `STEM_TIP_INK_PAST_TIP_MIN_SPACES = -0.15` | sp | L | D | NARROWS |  square spaces of it, under `STEM_TIP_COVER_AREA_MIN`) -- or a stem whose CV box stops short of its printed end. CANNOT TELL, never a flag. MEASURED: Sean's 21 flags with |  |
| staged/gather.py:5597 | `STEM_TIP_INK_LEFT_AREA_MAX = 0.08` | count | B | D | REFUSES |  Attached ink on the stem's LEFT beyond its own edge (square spaces): a flag hangs from one side only. A speck under this is the stem's own noise (Brahms pdf 21 `glyph/21 | * rank 5: D, REFUSES flag; one Brahms case (pdf 21) |
| staged/gather.py:5598 | `STEM_TIP_INK_EMPTY_AREA = 0.02` | ? |  | C | ? | STEM_TIP_INK_EMPTY_AREA = 0.02 |  |
| staged/gather.py:5601 | `STEM_TIP_COVER_AREA_MIN = 0.05` | ratio | B | D | ? |  A detection box explains the attached ink only where it COVERS at least this much of it (square spaces): detector boxes are loose, and a neighbouring rest's box edge gra | * rank 5: D; one Brahms case (pdf 25) |
| staged/gather.py:5612 | `STEM_TIP_FRAG_GAP_SPACES = 0.35` | sp | LB | D | NARROWS |  SAME shape test and covered by the SAME blockers, so a beam fragment runs on, a detection's ink makes the tip `occupied`, and a ledger stub has no arm. MEASURED: of 34 + |  |
| staged/gather.py:5613 | `STEM_TIP_FRAG_T_MAX_SPACES = 1.6` | sp |  | C | ? | STEM_TIP_FRAG_T_MAX_SPACES = 1.6 |  |
| staged/gather.py:5614 | `STEM_TIP_FRAG_AREA_MIN = 0.25` | count |  | A | ? | STEM_TIP_FRAG_AREA_MIN = 0.25 |  |
| staged/gather.py:5615 | `STEM_TIP_FRAG_WIDTH_MIN_SPACES = 0.3` | sp |  | C | ? | STEM_TIP_FRAG_WIDTH_MIN_SPACES = 0.3 |  |
| staged/gather.py:5620 | `STEM_TIP_FRAG_EXPLAINED = 0.5` | ? | LB | D | REFUSES |  A fragment at least this share of which stands under ANOTHER mark's detection box (`blockers`; a rest, a beam stroke, a head) is that mark's ink, not a piece of the flag |  |
| staged/gather.py:5629 | `STEM_TIP_LINE_NEAR_U_SPACES = 0.3` | sp |  | C | NARROWS |  (a ledger line is ~0.3 spaces thick; the legs of a tip standing ON a line are why 2.73 existed); a thicker run is a BAR (a beam crossing the tip measures 0.46 .. 0.62) a |  |
| staged/gather.py:5630 | `STEM_TIP_LINE_FAR_U_SPACES = 0.9` | sp |  | C | ? | STEM_TIP_LINE_FAR_U_SPACES = 0.90 |  |
| staged/gather.py:5631 | `STEM_TIP_LINE_FILL = 0.6` | ratio |  | B | ? | STEM_TIP_LINE_FILL = 0.6 |  |
| staged/gather.py:5632 | `STEM_TIP_LINE_MAX_THICK_SPACES = 0.45` | sp |  | C | ? | STEM_TIP_LINE_MAX_THICK_SPACES = 0.45 |  |
| staged/gather.py:5638 | `STEM_TIP_BLOCKER_TOLERANCE_SPACES = 0.1` | sp | L | D | DECIDES |  ROADMAP 2.73 (applied to the ink since 2.83). A detection box counts as explaining the ink at the tip only if it covers that ink by more than this much (staff spaces) in |  |
| staged/gather.py:5874 | `STEM_TIP_WINDOW_NEAR_SPACES = 1.0` | sp |  | A | NARROWS |  CONVENTION ASSUMED / WHAT WOULD FALSIFY IT: the window's `True` is a witness of low recall (1 of Sean's 21 flags) but not of bad precision (0 of his 46 bare stems, 1 of  |  |
| staged/gather.py:5875 | `STEM_TIP_WINDOW_FAR_SPACES = 2.5` | sp |  | C | ? | STEM_TIP_WINDOW_FAR_SPACES = 2.5 |  |
| staged/gather.py:5876 | `STEM_TIP_WINDOW_WIDTH_SPACES = 0.9` | sp |  | C | ? | STEM_TIP_WINDOW_WIDTH_SPACES = 0.9 |  |
| staged/gather.py:5877 | `STEM_TIP_WINDOW_DENSE = 0.3` | ? |  | C | ? | STEM_TIP_WINDOW_DENSE = 0.30 |  |
| staged/gather.py:5878 | `STEM_TIP_WINDOW_BACKGROUND_MAX = 0.2` | count |  | A | ? | STEM_TIP_WINDOW_BACKGROUND_MAX = 0.20 |  |
| staged/gather.py:5879 | `STEM_TIP_WINDOW_LINE_PROBE_SPACES = 0.6` | sp |  | C | ? | STEM_TIP_WINDOW_LINE_PROBE_SPACES = 0.6 |  |
| staged/gather.py:5880 | `STEM_TIP_WINDOW_LINE_ROW_FILL = 0.7` | ratio |  | B | ? | STEM_TIP_WINDOW_LINE_ROW_FILL = 0.7 |  |
| staged/gather.py:5881 | `STEM_TIP_WINDOW_LINE_ROWS_MAX_LOST = 0.5` | ? |  | C | ? | STEM_TIP_WINDOW_LINE_ROWS_MAX_LOST = 0.5 |  |
| staged/gather.py:5976 | `STEM_TIP_HOOKS_REACH_SPACES = 3.4` | sp |  | C | ? |  How far along the stem from its tip the hook band reaches, in spaces. Three hooks fit with room to spare; the band is cut earlier at the first notehead it would run into |  |
| staged/gather.py:5979 | `STEM_TIP_HOOKS_NEAR_SPACES = 0.1` | sp |  | B | ? |  The counted band's distance from the stem's right edge, in spaces: far enough out to skip the stem's own thickness, far enough in to hold a curl. STEM_TIP_HOOKS_NEAR_SPA |  |
| staged/gather.py:5980 | `STEM_TIP_HOOKS_FAR_SPACES = 0.4` | sp |  | C | ? | STEM_TIP_HOOKS_FAR_SPACES = 0.4 |  |
| staged/gather.py:5982 | `STEM_TIP_HOOKS_LEFT_SPACES = 1.2` | sp |  | C | ? |  The LEFT guard's own band: the mirrored 1.2 spaces beside the stem. STEM_TIP_HOOKS_LEFT_SPACES = 1.2 |  |
| staged/gather.py:5986 | `STEM_TIP_HOOKS_CLOSE_SPACES = 0.06` | sp | B | D | ? |  Healing of the staff-erase's thin stripes (they split ONE stroke into two), a run's minimum thickness and the minimum paper between two runs, in spaces. NOT CONFIRMED be | * rank 5: D, DECIDES; Brahms p1 only |
| staged/gather.py:5987 | `STEM_TIP_HOOKS_MIN_THICK_SPACES = 0.12` | sp |  | C | ? | STEM_TIP_HOOKS_MIN_THICK_SPACES = 0.12 |  |
| staged/gather.py:5988 | `STEM_TIP_HOOKS_MIN_GAP_SPACES = 0.12` | sp |  | C | ? | STEM_TIP_HOOKS_MIN_GAP_SPACES = 0.12 |  |
| staged/gather.py:5992 | `STEM_TIP_HOOKS_SUPPORT = 0.4` | ? |  | B | REFUSES |  A count of k needs k runs in at least this fraction of the INKED columns; more than this share of columns showing k+1 runs means the band is not clean (a stroke touching |  |
| staged/gather.py:5993 | `STEM_TIP_HOOKS_GLITCH = 0.12` | ? |  | C | ? | STEM_TIP_HOOKS_GLITCH = 0.12 |  |
| staged/gather.py:5996 | `STEM_TIP_HOOKS_MIN_COVERAGE = 0.5` | ratio |  | B | ? |  A band where fewer than this share of columns hold ANY attached ink is too broken a stroke to say how many there are. STEM_TIP_HOOKS_MIN_COVERAGE = 0.5 |  |
| staged/gather.py:5999 | `STEM_TIP_HOOKS_LEFT_MAX = 0.05` | count |  | A | ? |  Component ink to the stem's LEFT above this density means the stroke crosses the stem (a slash, a slur), which a flag hook never does. STEM_TIP_HOOKS_LEFT_MAX = 0.05 |  |
| staged/gather.py:6005 | `STEM_TIP_HOOKS_FIRST_MAX_SPACES = 0.8` | sp | B | D | ? |  spaces of the tip, and consecutive hooks leave it this far apart (spaces). NOT CONFIRMED against a two-hook print on this plate (Brahms p1 holds none); argued from Bravu | * rank 5: D, DECIDES hook count; NOT CONFIRMED beyond Brahms p1 (6c14783ec, 2.69); argued from Bravura |
| staged/gather.py:6006 | `STEM_TIP_HOOKS_SPACING_MIN = 0.4` | count |  | A | ? | STEM_TIP_HOOKS_SPACING_MIN = 0.4 |  |
| staged/gather.py:6007 | `STEM_TIP_HOOKS_SPACING_MAX = 1.1` | count |  | A | ? | STEM_TIP_HOOKS_SPACING_MAX = 1.1 |  |
| staged/gather.py:6010 | `STEM_TIP_HOOKS_MAX_LEVEL = 3` | ? |  | C | ? |  The longest uncounted bracket this reader will name (levels), so a noisy band never opens the narrowing to a 64th. STEM_TIP_HOOKS_MAX_LEVEL = 3 |  |
| staged/gather.py:6220 | `STEM_TIP_OWN_FLAG_X_SPACES = 0.6` | sp |  | C | ? |  detector's `flag8thUp`/`flag16thUp` boxes over one flag start a hair INSIDE the stem (left edge +0.1 spaces from its left) and 0.2-0.3 spaces under the tip. NOT CONFIRME |  |
| staged/gather.py:6221 | `STEM_TIP_OWN_FLAG_TIP_SPACES = 0.8` | sp |  | C | ? | STEM_TIP_OWN_FLAG_TIP_SPACES = 0.8 |  |
| staged/gather.py:7353 | `LINE_ROW_PAST_FLAG_NEAR_SPACES = [0.1, 0.5]` | sp | B | D | REFUSES |  Where a straight line leaves a stem's RIGHT edge far past any flag: a flag reaches about 0.85 space from its stem (Brahms p0), so ink filling this flank, with the near f |  |
| staged/gather.py:7354 | `LINE_ROW_PAST_FLAG_FAR_SPACES = [0.9, 1.2]` | sp |  | C | ? | LINE_ROW_PAST_FLAG_FAR_SPACES = (0.9, 1.2) |  |
| staged/gather.py:7355 | `LINE_ROW_PAST_FLAG_FILL = 0.85` | ratio |  | B | ? | LINE_ROW_PAST_FLAG_FILL = 0.85 |  |
| staged/inferences.py:1719 | `BarOutcome.tip_not_clean = 0` | ? |  | C | ? | tip_not_clean: int = 0 members the arithmetic forces but whose tip was not SEEN clean |  |
| staged/page_beams.py:53 | `TIP_REACH_SPACES = 2.5` | sp |  | C | DECIDES |  The strokes a stem end is read against: its box grown by this many spaces (the tip window reaches 0.5 out and 3.3 in; the face join 1.0 + a beam). TIP_REACH_SPACES = 2.5 |  |
| staged/stroke_map.py:158 | `LEDGER_TIP_MAX_SP2 = 0.35` | ? |  | C | ? |  an oval tip the horizontal opening left to the remainder is smaller than this LEDGER_TIP_MAX_SP2 = 0.35 |  |

## stem (80; A 4, B 3, C 55, D 17, E 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| hairpin_detection.py:348 | `STEM_JOIN_MIN_SPACES = 1.2` | sp | L | D | DECIDES |  find's own rows (in spaces); a find with a stem at BOTH ends is a beam between two stems (the reach removes every vertical stroke of 1.2+ spaces before the look, which l |  |
| hairpin_detection.py:349 | `STEM_JOIN_END_SPACES = 0.4` | sp |  | C | ? | STEM_JOIN_END_SPACES = 0.4 |  |
| line_detection.py:122 | `STEM_KERNEL_MARGIN = 0.8` | ? |  | C | ? |  The stem-isolating opening kernel, as a fraction of `min_height_lines` (see detect_stems). Anything at or above 0.8 gives the same answer on the reference sheet at every |  |
| line_detection.py:170 | `STEM_MAX_HEIGHT_LINES = 8.0` | ? |  | B | ? |  The stem ground truth (`benchmarks/omr-phase4-lines`, 48 stems engraved by LilyPond at four line thicknesses) is UNCHANGED at every value tried — its music has no long s |  |
| line_detection.py:190 | `STEM_STROKE_AGREE_SPACES = 0.25` | sp | LB | D | DECIDES |  Litolff and 397 at every value on Breitkopf, while the positive control (re-finding the strokes `detect_stems` already accepts) reads 98.8 / 98.2 / 98.2 / 98.2 / 97.6 an |  |
| line_detection.py:269 | `STEM_PAIR_TALLER_THAN_ACCIDENTAL_SPACES = 3.5` | sp |  | A | NARROWS |  A stroke at least this tall (staff spaces) that runs through a head's columns is a chord stem, not an accidental's stroke (a sharp/natural is about 2.5-3 spaces tall, Go |  |
| line_detection.py:320 | `STEM_AT_BAR_EDGE_END_SLACK_SPACES = 0.25` | sp |  | C | DECIDES |  Slack (staff spaces) on the head box's vertical extent for the run's end: the stem's own end lies inside its head, the head box is the detector's (or the standard) box,  |  |
| line_detection.py:368 | `THIN_STEM_PROTRUDE_SPACES = 0.8` | sp |  | C | REFUSES |  The empty interval (staff spaces) between the stem's columns and the heads' columns in the run's sorted column extents. Two heads a third apart are ~2 spaces of ink, so  |  |
| line_detection.py:374 | `THIN_STEM_PROTRUDE_STACK_SPACES = 0.7` | sp | B | D | DECIDES |  own columns climb across its width on a slanted scan: Brahms 317803 p0 q110/q118 (cell 0/0/0/5) protrudes 75 canonical px = 0.75 space against the shipped 80 (the widest |  |
| staff_detector.py:45 | `MAX_SYSTEM_GAP_FACTOR = 6.0` | ? |  | C | ? | MAX_SYSTEM_GAP_FACTOR = 6.0 fallback if auto-bipartition fails |  |
| staff_detector.py:56 | `SYSTEM_BREAK_GAP_FACTOR = 2.5` | ? |  | C | ? | SYSTEM_BREAK_GAP_FACTOR = 2.5 gap this many × the typical within-system gap = a break |  |
| staged/accidental_family.py:70 | `STEM_MIN_SP = 0.5` | sp |  | C | DECIDES |  A stroke is a stem of the mark at or above this length (staff spaces). A natural's hanging stem can be cropped to ~0.8 and still read. STEM_MIN_SP = 0.5 |  |
| staged/accidental_family.py:73 | `STEM_MAX_SP = 3.7` | sp |  | C | DECIDES |  ... and a stem the mark OWNS is at most this long: an accidental's longest stroke is a sharp's 3.5; the strokes the map found 4.1-7.4 long were an accidental's stem fuse |  |
| staged/accidental_family.py:81 | `STEM_GAP_MIN_SP = 0.3` | sp |  | C | ? |  the two stems of a natural / sharp stand this far apart (x centre to centre, spaces): measured 0.44-0.63. STEM_GAP_MIN_SP = 0.3 |  |
| staged/adjudicators/ownership.py:333 | `STEM_REACH_BAND_SPACES = 1.0` | sp |  | C | ? |  A stem "reaches" a staff when its tip stands within this many of THAT staff's spaces of its outer line (or past it): INTO the lines, or ending in the band a space either |  |
| staged/adjudicators/ownership.py:342 | `STEM_MIN_OUTSIDE_SPACES = 0.9` | sp |  | C | ? |  may point at the neighbour for reasons that have nothing to do with ownership (a beamed group, a second voice), and the replay found ten such heads on the first draft of |  |
| staged/adjudicators/rhythm.py:477 | `STEM_JOIN_TOLERANCE_SPACES = 0.8` | sp |  | C | REFUSES |  gets zero (flags back to overlap, and no beyond-the-tip rule at all). ⚠️ IT DOES NOT WIDEN THE STEM->BEAM JOIN -- measured and refused, see `_stem_joined`. STEM_JOIN_TOL |  |
| staged/adjudicators/rhythm.py:3419 | `REACH_STEM_MIN_SPACES = 2.0` | sp |  | C | REFUSES |  (`stem_projection`) and whose ruler read up or down, the ruler agrees with that direction on **306 of 307 at 2.0 spaces or more** (100% at 2.0-2.5, 100% at 2.5-3.0, 208  |  |
| staged/adjudicators/rhythm.py:3891 | `BARE_STEM_ACROSS_SPACES = 0.3` | sp |  | C | ? | BARE_STEM_ACROSS_SPACES = 0.3 |  |
| staged/adjudicators/rhythm.py:4053 | `OPEN_STEM_MIN_SPACES = 2.0` | sp |  | C | ? | OPEN_STEM_MIN_SPACES = 2.0 |  |
| staged/adjudicators/stem_value.py:99 | `STEM_DUPLICATE_MIN_OVERLAP = 0.5` | ? | LB | D | ? |  least this share of the NARROWER extent on both axes. ⚠️ MEASURED, not assumed: on Litolff p1-3 and Brahms p0-1, 12 and 5 multi-head stems were the same head-set reached |  |
| staged/adjudicators/stem_value.py:111 | `STEM_MIN_REACH_SPACES = 0.8` | sp | L | D | ? |  restated here only because ADJUDICATE may not import a GATHER constant's module-level name into a decision's behaviour without saying so. Used ONLY to break a tie betwee |  |
| staged/adjudicators/stem_value.py:118 | `STEM_FLUSH_MAX = 0.3` | count |  | A | DECIDES |  the head's width of one of the head's sides (CLAUDE.md §10: "a stem stands at the SIDE of its head"). Used ONLY to break a tie between two stems that both touch a head;  |  |
| staged/adjudicators/stem_value.py:531 | `ONE_STEM_PER_HEAD_MIN_APART_HEADS = 0.5` | px |  | E | DECIDES |  Another head stands at a DIFFERENT staff position (so it is a second note, not the same note boxed twice) when its centre is at least this many of the head's own heights |  |
| staged/beam_strokes.py:45 | `STEM_MAX_SPACES = 8.0` | sp | L | D | DECIDES |  A vertical stroke is a STEM only up to this long (staff spaces). Measured on Litolff pp.2-16 (the 2.202 milestone gather): the 4,260 vertical strokes that coincide with  | * rank 10: D, DECIDES barline-not-stem past 8 sp; Litolff pp2-16 only (96d3ddc67, 2.202) |
| staged/beam_strokes.py:80 | `STEM_MATCH_X_SLACK_SPACES = 0.35` | sp |  | C | ? |  A vertical stroke is THIS stem when it overlaps the stem's x-span (within this slack) and y-range. STEM_MATCH_X_SLACK_SPACES = 0.35 |  |
| staged/beam_strokes.py:82 | `STEM_HEAD_X_SLACK_SPACES = 0.35` | sp |  | C | ? |  How far (staff spaces) beyond the head's half-width a stem's far end may stand and still be the head's stem (the stem finder's own 0.35). STEM_HEAD_X_SLACK_SPACES = 0.35 |  |
| staged/beam_strokes.py:84 | `STEM_PAST_HEAD_MIN_SPACES = 0.0` | sp |  | C | ? |  How far (staff spaces) past the head's box edge a stem's far end must stand to be the head's stem in that direction. STEM_PAST_HEAD_MIN_SPACES = 0.0 |  |
| staged/beam_strokes.py:623 | `ONE_STEM_MAX_SPACES = 9.0` | sp | L | D | ? |  2.318 r6: the longest upright that can be THIS head's stem where its ink touches the head's ink. `STEM_MAX_SPACES` (8.0) was measured for strokes nothing ties to a head  | * rank 10: D; Litolff |
| staged/beam_strokes.py:628 | `ONE_STEM_COLLINEAR_X_SPACES = 0.3` | sp |  | C | ? |  Two pieces of one stem cut by a crossing (a beam, a ledger rung): within this of one x-column and this far apart vertically (the numbers `stem_strokes.COLLINEAR_X_SPACES |  |
| staged/beam_strokes.py:629 | `ONE_STEM_BREAK_MAX_GAP_SPACES = 0.6` | sp |  | C | ? | ONE_STEM_BREAK_MAX_GAP_SPACES = 0.6 |  |
| staged/beam_strokes.py:668 | `ONE_STEM_REACH_HOPS = 2` | ? | L | D | ? |  How many strokes of the head's own ink (a head the scan or the claim order cut in pieces, a stem's fused foot) the contact may pass through on its way from the head to i |  |
| staged/beam_strokes.py:792 | `ONE_STEM_BRIDGE_MAX_GAP_SPACES = 0.35` | sp | B | D | NARROWS |  A stem a scan has parted from its head by a hair of paper (Breitkopf SHATTERS) is still the head's stem: the vertical stands within this many staff spaces of the head's  |  |
| staged/beam_strokes.py:801 | `SHORT_STEM_SPACES = 2.5` | sp |  | C | ? | SHORT_STEM_SPACES = 2.5 |  |
| staged/beam_strokes.py:1107 | `STEP_AT_STEM_SPACES = 0.15` | sp |  | C | DECIDES |  2.318 r4: how much thicker (staff spaces) this stem's stretch of a beam is than the thin part of the same beam (the lower quartile of its profile) before a second beam f |  |
| staged/box_kind.py:96 | `STEM_MIN_SP = 2.5` | sp |  | C | ? | STEM_MIN_SP = 2.5 |  |
| staged/dyad_head_rescue.py:45 | `STEM_AT_EDGE_SPACES = 0.25` | sp |  | C | NARROWS |  the candidate's box covers the stem's x to within this (a stem drawn through a head's edge) STEM_AT_EDGE_SPACES = 0.25 |  |
| staged/export.py:3331 | `ACROSS_SYSTEMS_EDGE_SPACES = 4.0` | sp | LB | D | DECIDES |  ROADMAP 2.271 step 3: an arc's trace end this close (spaces) to its run's own edge (the last cell's right edge / the first cell's left edge) is "at the system's edge". T |  |
| staged/gather.py:629 | `STEM_WITNESS_HALF_WIDTH_SPACES = 0.9` | sp |  | C | NARROWS |  needs the very head this search is looking for. Both ends of the stem are therefore treated as candidate attachment points, and the window straddles BOTH sides of the st |  |
| staged/gather.py:630 | `STEM_WITNESS_HALF_HEIGHT_SPACES = 0.6` | sp |  | C | ? | STEM_WITNESS_HALF_HEIGHT_SPACES = 0.6 around the stem's own end |  |
| staged/gather.py:9958 | `RECENTRE_PART_STEM_RUN_SPACES = 1.7` | sp |  | C | DECIDES |  Ink in a column whose vertical run is longer than this is a STEM, left out. RECENTRE_PART_STEM_RUN_SPACES = 1.7 |  |
| staged/gather.py:10631 | `STEM_BRIDGE_MAX_HEAD_WIDTH_SPACES = 1.9` | sp |  | C | REFUSES |  ROADMAP 2.161: a head with its ink bridge to a stem stays one head wide -- 2.148's own head-sized width ceiling (`rhythm.HEAD_BOX_MAX_WIDTH_SPACES`), restated here and p |  |
| staged/gather.py:11071 | `STACKED_HOLLOW_STEM_EXT_MIN_SPACES = 1.5` | sp | B | D | ? |  The stem must run at least this many spaces past the OUTER edge of the pair's slots (either end). Real chords 2.22-3.98 (Brahms, 19 pairs), the "8" 0.15, a bass clef 0.1 |  |
| staged/gather.py:11493 | `STACKED_HOLLOW_STEM_EDGE_TOL_SPACES = 0.5` | sp |  | C | ? |  How far (staff spaces) a stem row's centre may stand from the head's edge on the stem's own side and still be THE pair's stem (a stem stands on the head's edge, half a h |  |
| staged/gather.py:11780 | `NOTEHEAD_STEM_CROSS_GUARD_PX = 1.0` | px |  | C | REFUSES |  on "the other side" of itself. A whole pixel, not a fraction of the stem width: `Q.STEM` boxes run 2-4 canonical px wide on both acceptance documents, and a sub-pixel gu |  |
| staged/gather.py:12049 | `HEAD_STEM_MIN_EXT_SPACES = 0.8` | sp |  | C | ? |  A vertical run beside a head must stand this far (staff spaces) past the head's own edge to count as a stem. A head is ~1.0-1.5 sp tall and a stem is at least ~2.5 sp, s |  |
| staged/gather.py:12054 | `HEAD_STEM_WINDOW_SPACES = 0.18` | sp |  | C | DECIDES |  The column the run is read in: a stem is ~0.15-0.25 sp wide and its OUTER edge is flush with the head's edge (down -> left, up -> right, CLAUDE.md §10), so the window sl |  |
| staged/gather.py:12055 | `HEAD_STEM_SLIDE_OUT_SPACES = 0.15` | sp |  | C | ? | HEAD_STEM_SLIDE_OUT_SPACES = 0.15 |  |
| staged/gather.py:12056 | `HEAD_STEM_SLIDE_IN_SPACES = 0.3` | sp |  | C | ? | HEAD_STEM_SLIDE_IN_SPACES = 0.30 |  |
| staged/gather.py:12059 | `HEAD_STEM_GAP_SPACES = 0.3` | sp |  | C | DECIDES |  a run bridges a white gap this long (a staff line erased or thinned, a broken scan) but NO longer: the gap between two staff lines is a whole space HEAD_STEM_GAP_SPACES  |  |
| staged/gather.py:12060 | `HEAD_STEM_ROW_FRACTION = 0.85` | ratio |  | B | ? | HEAD_STEM_ROW_FRACTION = 0.85 |  |
| staged/gather.py:12061 | `HEAD_STEM_MAX_RUN_SPACES = 9.0` | sp |  | C | ? | HEAD_STEM_MAX_RUN_SPACES = 9.0 |  |
| staged/geometry.py:168 | `STEM_ATTACH_TOLERANCE_HEADS = 0.12` | ? | B | D | ? |  no empty interval to put it in: on Brahms 317803 p0 the stem-to-head gaps run continuously from 0 to 0.5 head heights; the four found-but-not-attached heads stand at 0.0 | * rank 10: D, DECIDES attach; Brahms p0, no empty interval (c13cdf569, 2.84) |
| staged/geometry.py:193 | `STEM_CONTACT_TOLERANCE_HEADS = 0.3` | ? |  | A | ? |  detected head within 0.3 (FINDINGS hand-truth-score section 9.6); the two that do not are partial strokes that attach to no head anyway. CONVENTION (Sean 2026-10-11): ev |  |
| staged/inferences.py:1632 | `BARE_STEM_MAX_UNKNOWNS = 24` | ? |  | C | NARROWS |  How many unknown events one bar may hold before the rule declines. The DP below is linear in it; the cap is not for speed, it is that a bar with more than this many unde |  |
| staged/key_object.py:68 | `STEM_RUN_SPACES = [2.0, 3.9]` | sp | L | D | DECIDES |  a flat's stem is a thin vertical stroke: its longest vertical ink run (spaces) and its width (spaces). Measured on Litolff p2-p16 (3-stem staves, 56 stems: run 2.1-3.5,  | * rank 7: D, DECIDES a flat's stem; Litolff 56 stems (cce4d4842, 2.256b); already failed on crushed flats (2.299/2.302) |
| staged/key_object.py:69 | `STEM_MAX_W_SPACES = 0.5` | sp |  | C | ? | STEM_MAX_W_SPACES = 0.5 |  |
| staged/key_object.py:71 | `STEM_MIN_GAP_SPACES = 0.55` | sp | L | D | ? |  successive flats stand 0.55-2.0 spaces apart (Litolff crushes to 0.6) centre to centre (`RUN_GAP_SPACES`; a sharp's two strokes stand closer and are not flats) STEM_MIN_ |  |
| staged/key_object.py:159 | `STEM_RUN_SPACES_V2 = [1.4, 4.2]` | sp |  | C | REFUSES |  a crushed scan breaks a flat's stem (measured on Sean's judged staff starts: stems of 1.46 / 1.48 / 1.52 spaces where the print stands 2.6): the floor drops from `STEM_R | * rank 7: D, DECIDES; widened 1.4-4.2 after the crushed flats (17b02420d, 2.302) |
| staged/page_heads.py:70 | `STEM_MIN_LEN_SP = 1.5` | sp |  | C | ? |  a stem stroke: vertical, at least this long (sp) STEM_MIN_LEN_SP = 1.5 |  |
| staged/page_owner.py:66 | `STEM_MIN_OUTSIDE_SPACES = 0.9` | sp |  | C | NARROWS |  the stem speaks only for a head at least this far outside every candidate's lines (`ownership.STEM_MIN_OUTSIDE_SPACES`, the same word) STEM_MIN_OUTSIDE_SPACES = 0.9 |  |
| staged/page_owner.py:68 | `STEM_REACH_BAND_SPACES = 1.0` | sp |  | C | ? |  a stem tip "reaches" a staff within this many of its spaces of the near outer line (`ownership.STEM_REACH_BAND_SPACES`) STEM_REACH_BAND_SPACES = 1.0 |  |
| staged/page_tremolo.py:50 | `STEM_MIN_LEN_SP = 1.5` | sp |  | C | DECIDES |  a vertical page stroke is a stem for this reader from this length (`page_heads.STEM_MIN_LEN_SP`: 1.5) STEM_MIN_LEN_SP = 1.5 |  |
| staged/stem_end_heads.py:40 | `FLOOR = 0.05` | ? |  | C | DECIDES |  the detector is re-read at this floor on a cell holding an orphan stem (2.172's `READ_FLOOR`; 2.179 census: welded heads 0.05-0.25) FLOOR = 0.05 |  |
| staged/stem_end_heads.py:43 | `ORPHAN_HALF_WIDTH_SPACES = 0.9` | sp |  | C | ? |  a head ALREADY at a stem end (makes it not an orphan): staff spaces either side of the stem / along it from the end (a stem is drawn past its head's centre: 2.179 debug  |  |
| staged/stem_end_heads.py:44 | `ORPHAN_HALF_HEIGHT_SPACES = 1.0` | sp |  | C | ? | ORPHAN_HALF_HEIGHT_SPACES = 1.0 |  |
| staged/stem_end_heads.py:47 | `SIDE_SPACES = 1.1` | sp |  | A | NARROWS |  a candidate head's centre at a stem end: across the stem on the convention's side (OWN side up to this far, the other side up to `CROSS_SPACES` for a stem drawn through  |  |
| staged/stem_end_heads.py:48 | `CROSS_SPACES = 0.25` | sp |  | C | ? | CROSS_SPACES = 0.25 |  |
| staged/stem_end_heads.py:49 | `END_SPACES = 1.0` | sp |  | C | ? | END_SPACES = 1.0 |  |
| staged/stem_end_heads.py:53 | `BESIDE_ACROSS_SPACES = 0.6` | sp |  | C | NARROWS |  a candidate whose centre is this close to a head already seen (across / along, staff spaces) is that head boxed again, or its neighbour in the slot the stacked-head fit  |  |
| staged/stem_end_heads.py:54 | `BESIDE_ALONG_SPACES = 1.1` | sp |  | C | ? | BESIDE_ALONG_SPACES = 1.1 |  |
| staged/stem_strokes.py:40 | `BRIDGE_MAX_GAP_SPACES = 0.35` | sp |  | C | ? | BRIDGE_MAX_GAP_SPACES = 0.35 |  |
| staged/stem_strokes.py:43 | `BREAK_MAX_GAP_SPACES = 0.6` | sp |  | C | ? | BREAK_MAX_GAP_SPACES = 0.6 |  |
| staged/stem_strokes.py:46 | `FUSED_MIN_WIDTH_SPACES = 0.6` | sp |  | B | ? |  A "vertical" stroke wider than this has head ink fused to it; its stem stands at the tip end (median error 0.09 sp against the finder's stem on the 446 fused strokes, ag |  |
| staged/stem_strokes.py:49 | `FLUSH_SPACES = 0.45` | sp | L | D | REFUSES |  A stem's outer edge stands at most this far INSIDE the detector box's side edge (boxes are loose by a quarter space on one side). Measured 2.204, Litolff, the finder's o | * rank 10: D, REFUSES; Litolff, against the finder's OWN stems, not judged marks (8f74ab70e, 2.204) |
| staged/stroke_map.py:126 | `STEM_THIN_SPACES = 0.5` | sp | LB | D | ? |  a row run of a vertical stroke no wider than this is STEM (or barline) ink; wider is something fused to it (a head's oval, a beam). Litolff's widest plain stem 0.43 sp,  |  |
| staged/stroke_map.py:128 | `STEM_PART_MIN_SPACES = 0.5` | sp |  | C | ? |  a thin part shorter than this is an oval's tip or a stem's stub beside a head: it goes back to the wide part it touches STEM_PART_MIN_SPACES = 0.5 |  |
| staged/stroke_map.py:1508 | `STEM_TRUE_END_MARGIN_SPACES = 1.5` | sp | B | D | REFUSES |  ROADMAP 2.206d (flag `OMR_STEM_TIP_TRUE_EDGE`, default ON since 2026-10-27). The stem finder's box can be a thin core of a thick stem (Brahms p14: 4 px of a 25 px stem); |  |
| staged/stroke_map.py:1509 | `STEM_TRUE_WIDTH_MAX_SPACES = 0.7` | sp |  | C | ? | STEM_TRUE_WIDTH_MAX_SPACES = 0.7 |  |
| staged/stroke_owner.py:180 | `ACC_STEM_MAX_SP = 3.7` | sp |  | C | ? | ACC_STEM_MAX_SP = 3.7 2.201 STEM_MAX_SP |  |

## rest (59; A 8, B 3, C 42, D 5, E 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| staged/accidental_shape.py:175 | `ON_REST_IOU = 0.5` | ? |  | C | DECIDES |  Two boxes in one cell contest ONE ink when their IoU is at least this (checked on crops: 10 of 10 double sharps at >= .5 were an eighth rest; the kept-rest overlap of re |  |
| staged/adjudicators/family_precision.py:350 | `REST_DUPLICATE_IOU_MIN = 0.02` | count |  | A | REFUSES |  GATHER, never off a beats figure this decision cannot see -- which is also why this is not the second rest-slot geometry the module docstring warns against: it never ask |  |
| staged/adjudicators/family_precision.py:578 | `REST_VERTICAL_WIDE_BEYOND_SPACES = 2.5` | sp |  | C | ? |  not observed one of these classes go as far as a displaced 8th rest. Unknown/unlisted classes fall back to MEDIUM -- the tightest tier still named, now that `restQuarter |  |
| staged/adjudicators/family_precision.py:579 | `REST_VERTICAL_MEDIUM_BEYOND_SPACES = 1.5` | sp |  | C | ? | REST_VERTICAL_MEDIUM_BEYOND_SPACES = 1.5 |  |
| staged/adjudicators/family_precision.py:611 | `REST_NOTEHEAD_OVERLAP_IOU_MIN = 0.3` | count |  | A | DECIDES |  physical mark reads as centred on itself, in ANY pair of overlapping classes) and raises the IoU floor itself to 0.3 -- "substantial overlap", not the near-zero floor th |  |
| staged/adjudicators/family_precision.py:1116 | `REST_BARLINE_MAX_WIDTH_SPACES = 0.8` | sp |  | C | REFUSES |  boxes are 0.2-0.4 sp wide and flush on a cell edge, and every one of the 23 flush ones at 0.4-0.8 sp that was cropped is a barline too. A cut-off measured on one plate:  |  |
| staged/adjudicators/family_precision.py:1220 | `REST_BARLINE_MIN_HEIGHT_SPACES = 2.0` | sp |  | C | ? | REST_BARLINE_MIN_HEIGHT_SPACES = 2.0 |  |
| staged/adjudicators/family_precision.py:1221 | `REST_BARLINE_EDGE_TOL_SPACES = 0.15` | sp |  | C | ? | REST_BARLINE_EDGE_TOL_SPACES = 0.15 |  |
| staged/adjudicators/family_precision.py:1336 | `REST_STROKE_MIN_SP = 1.0` | sp |  | C | NARROWS |  real rests' blob <= 0.70 and head-box ink 0.0) -- a cut on two plates, so it sits behind its flag. READS `Q.REST_INK_CONTACT` (GATHER, off the staff-erased raster) and N |  |
| staged/adjudicators/family_precision.py:1337 | `REST_HEAD_BLOB_MIN_SP = 0.9` | sp |  | C | ? | REST_HEAD_BLOB_MIN_SP = 0.9 ... and a solid blob at least this long in the piece, OR |  |
| staged/adjudicators/family_precision.py:1338 | `REST_HEAD_INK_MIN_SP2 = 0.4` | ? |  | C | ? | REST_HEAD_INK_MIN_SP2 = 0.4 ... this much of the piece's ink in a standing head box outside the rest box |  |
| staged/adjudicators/narrow_rest.py:56 | `REST8TH_WIDTH_SPACES = [0.9, 1.6]` | sp | LB | D | NARROWS |  `rest8th` boxes of Brahms p0-1 and Litolff p1-3 (`FINDINGS` 2.80b): 1.2-1.4 wide, 1.9-2.4 tall; the staff step of its centre (bottom line = 0) has a median of 3.9 and th |  |
| staged/adjudicators/narrow_rest.py:57 | `REST8TH_HEIGHT_SPACES = [1.6, 2.6]` | sp |  | C | ? | REST8TH_HEIGHT_SPACES = (1.6, 2.6) |  |
| staged/adjudicators/narrow_rest.py:58 | `REST8TH_MAX_PIECES = 3` | ? |  | C | ? | REST8TH_MAX_PIECES = 3 |  |
| staged/adjudicators/narrow_rest.py:59 | `REST8TH_STEP_CENTRE = 4.0` | ? |  | C | ? | REST8TH_STEP_CENTRE = 4.0 |  |
| staged/adjudicators/narrow_rest.py:60 | `REST8TH_STEP_TOLERANCE = 1.0` | ? |  | C | ? | REST8TH_STEP_TOLERANCE = 1.0 |  |
| staged/adjudicators/narrow_rest.py:63 | `DECISIVELY_NOT_WIDTH_SPACES = [0.5, 2.0]` | sp |  | C | REFUSES |  Outside these the ink is decisively not an eighth rest (a lone crumb, a head-with-stem, a quarter rest, a beam), not a close call. DECISIVELY_NOT_WIDTH_SPACES = (0.5, 2. |  |
| staged/adjudicators/narrow_rest.py:64 | `DECISIVELY_NOT_HEIGHT_SPACES = [1.0, 3.2]` | sp |  | C | ? | DECISIVELY_NOT_HEIGHT_SPACES = (1.0, 3.2) |  |
| staged/adjudicators/notehead_precision.py:951 | `REST_TWIN_COVER_MIN = 0.8` | ratio | L | D | ? |  Share of the SMALLER box the two boxes must share: the floor `consequences.TWIN_BOX_MIN_OVERLAP` (2.98) measured on 30 Litolff pairs at 0.93-1.0. Restated, with its sour |  |
| staged/adjudicators/notehead_precision.py:1023 | `WHOLE_ON_REST_COVER_MIN = 0.3` | ratio | B | D | ? |  share of the SMALLER box a rest box must cover: the rest-curl population measured 0.47-0.79 on 13 Brahms curls (a few as low as 0.05-0.25); a real whole's box never shar |  |
| staged/adjudicators/rhythm.py:6337 | `WHOLE_REST_HANG_TOL_SP = 0.25` | sp | L | D | ? |  edge-to-line tolerance in staff spaces (measured on Litolff hanging rests 0.0-0.25) and the rest's own size window. WHOLE_REST_HANG_TOL_SP = 0.25 |  |
| staged/adjudicators/rhythm.py:6338 | `WHOLE_REST_HANG_W_SP = [0.9, 2.0]` | sp |  | C | ? | WHOLE_REST_HANG_W_SP = (0.9, 2.0) |  |
| staged/adjudicators/rhythm.py:6339 | `WHOLE_REST_HANG_H_SP = [0.35, 1.0]` | sp |  | C | ? | WHOLE_REST_HANG_H_SP = (0.35, 1.0) |  |
| staged/adjudicators/rhythm.py:9983 | `WHOLE_REST_INK_MAX_HEIGHT_SPACES = 0.84` | sp |  | C | ? |  same 25 glyphs; 0.90 admits two more and 0.75 loses eight. The two it admits were cropped and are ambiguous ink in bars that hold real notes, so the cut is LOAD-BEARING  |  |
| staged/adjudicators/rhythm.py:9986 | `WHOLE_REST_INK_MIN_ASPECT = 1.63` | ratio |  | B | DECIDES |  ⚠️ Also narrow: 1.40 admits two more (both ambiguous), 1.80 loses two real whole rests. There is no plateau here at all; it is the document's own p05. WHOLE_REST_INK_MIN |  |
| staged/adjudicators/rhythm.py:9993 | `WHOLE_REST_INK_MAX_ASPECT = 3.09` | ratio |  | B | REFUSES |  is a 5.49 sliver of line residue. Anywhere in 2.40-4.50 gives the identical answer. It exists because that sliver is not a whole rest EITHER, and a decision may only cla |  |
| staged/adjudicators/rhythm.py:9999 | `WHOLE_REST_STEP = 5.5` | count |  | A | DECIDES |  the bottom line 0 and one step per half space its body spans step 6 down to step 5, so its centre is 5.5. ⚠️ NOT TUNED -- it is the engraving convention, and it is an ob |  |
| staged/adjudicators/rhythm.py:10076 | `WHOLE_REST_STEP_TOLERANCE = 1.0` | px |  | E | DECIDES |  `Q.STAFF_LINES` models a staff as five ideal rows while a scanned staff tilts and bows 8-17 page px across its width (CLAUDE.md, `OMR_CELL_LINE_TRACE`), which on this pl |  |
| staged/adjudicators/rhythm.py:10082 | `WHOLE_REST_NEIGHBOUR_BARS = 2` | ? |  | C | DECIDES |  SHORT: a tacet part prints a whole rest in every bar, so a real one always has a neighbour within a bar or two, while a long reach would let one distant rest vouch for i |  |
| staged/adjudicators/rhythm.py:10086 | `WHOLE_REST_NEIGHBOUR_STEPS = 1.5` | count |  | A | ? |  How closely the neighbour's height must agree, in staff steps. Plateau 1.0-3.0; below 1.0 it loses a real catch. It can be loose precisely because it is only ever the SE |  |
| staged/adjudicators/rhythm.py:10131 | `WHOLE_REST_INK_MAX_TRIMMED_HEIGHT_SP = 0.92` | sp |  | C | DECIDES |  Measured on Sean's 16 marks: the ink-trimmed height of his 8 whole rests is 0.44-0.83 sp; of the filled non-rests 1.02-1.59 sp (hollow ones are vetoed by their fill). A  |  |
| staged/adjudicators/rhythm.py:10133 | `WHOLE_REST_STRADDLE_MIN_SHARE = 0.25` | ratio |  | B | REFUSES |  the least ink share on BOTH sides of a stem for the mark to be a slash across it, not a head beside it (gap 0.03-0.41 on 5 marks). WHOLE_REST_STRADDLE_MIN_SHARE = 0.25 |  |
| staged/adjudicators/rhythm.py:10135 | `WHOLE_REST_INK_MIN_WIDTH_SP = 0.9` | sp |  | C | ? |  the narrowest ink a head or a whole rest can be (gap 0.62 -- the half sharp -- to 1.27 sp on Sean's marks). WHOLE_REST_INK_MIN_WIDTH_SP = 0.9 |  |
| staged/adjudicators/rhythm.py:10393 | `REST_VOICE_DISPLACEMENT_MIN_STEPS = 1.5` | count |  | A | DECIDES |  "outside its own staff" bound `_rest_slot` already reports (step < 0 or > 8), so a genuinely displaced rest is never confused with cross-staff bleed -- CLAUDE.md's own r |  |
| staged/adjudicators/unboxed_rest.py:57 | `EIGHTH_WIDTH_SPACES = [1.1, 1.6]` | sp |  | C | ? |  table): 17 standing `rest8th` (w 1.31-1.46, h 1.81-2.35, step 3.4-4.0, mass_y 0.34-0.48), 81+ standing `restQuarter` (w 1.08-1.34, h 2.7-3.4, step 4.4-5.0) and the flats |  |
| staged/adjudicators/unboxed_rest.py:58 | `EIGHTH_HEIGHT_SPACES = [1.5, 2.5]` | sp |  | C | ? | EIGHTH_HEIGHT_SPACES = (1.5, 2.5) | * rank 4: C, DECIDES an unboxed eighth rest by size (2.99) |
| staged/adjudicators/unboxed_rest.py:59 | `EIGHTH_STEP = [3.2, 4.4]` | ? |  | C | ? | EIGHTH_STEP = (3.2, 4.4) |  |
| staged/adjudicators/unboxed_rest.py:61 | `EIGHTH_MAX_MASS_Y = 0.5` | ? |  | C | ? |  An eighth rest's ink sits in its UPPER half (the blob, then the tail). EIGHTH_MAX_MASS_Y = 0.50 |  |
| staged/adjudicators/unboxed_rest.py:62 | `QUARTER_WIDTH_SPACES = [1.0, 1.45]` | sp |  | C | ? | QUARTER_WIDTH_SPACES = (1.0, 1.45) |  |
| staged/adjudicators/unboxed_rest.py:63 | `QUARTER_HEIGHT_SPACES = [2.65, 3.5]` | sp |  | C | ? | QUARTER_HEIGHT_SPACES = (2.65, 3.5) | * rank 4: C, DECIDES an unboxed quarter rest by size (8b69501f3, 2.99, Brahms tiles) |
| staged/adjudicators/unboxed_rest.py:64 | `QUARTER_STEP = [3.7, 5.3]` | ? |  | C | ? | QUARTER_STEP = (3.7, 5.3) |  |
| staged/adjudicators/unboxed_rest.py:65 | `REST_MAX_PIECES = 3` | ? |  | C | ? | REST_MAX_PIECES = 3 |  |
| staged/adjudicators/unboxed_rest.py:72 | `EIGHTH_LEFT_BINS_MAX = 0.65` | count |  | A | ? | EIGHTH_LEFT_BINS_MAX = 0.65 the two left slices |  |
| staged/adjudicators/unboxed_rest.py:77 | `QUARTER_RIGHT_BIN_MAX = 0.65` | count |  | A | ? |  A sharp or a natural is TWO strokes: its right slices fill again. A quarter rest's right side is thin (0.09-0.63 on the 100 standing ones). QUARTER_RIGHT_BIN_MAX = 0.65 |  |
| staged/adjudicators/unboxed_rest.py:78 | `QUARTER_FOURTH_BIN_MAX = 0.85` | count |  | A | ? | QUARTER_FOURTH_BIN_MAX = 0.85 |  |
| staged/consequences.py:2166 | `REST_BAR_SUM_EPS = 1e-06` | ? |  | C | ? |  Two floating-point bar sums (target vs. standing total) are compared exactly, the same tolerance `reconcile_duration`'s own landing test uses. REST_BAR_SUM_EPS = 1e-6 |  |
| staged/gather.py:8843 | `_UNBOXED_REST_GLYPH_BASE = 350000` | ? |  | C | ? |  `_VERTICAL_RUN_GLYPH_BASE` (300k) and BELOW the human-evidence base (400k): `test_stage_review_evidence` holds every gather base under it (the first draft used 400k and  |  |
| staged/gather.py:8850 | `UNBOXED_REST_WIDTH_SPACES = [0.5, 2.4]` | sp |  | C | REFUSES |  eighth rest measures 1.2-1.4 x 1.9-2.4 and a quarter rest about 1 x 2.6-3, a head is ~1.3 x 1, a stem-and-head or a beam group is far taller or wider. Wider than the dec |  |
| staged/gather.py:8851 | `UNBOXED_REST_HEIGHT_SPACES = [1.2, 3.8]` | sp |  | C | ? | UNBOXED_REST_HEIGHT_SPACES = (1.2, 3.8) |  |
| staged/gather.py:8855 | `UNBOXED_REST_STEP_RANGE = [1.0, 7.0]` | ? |  | C | NARROWS |  A candidate's centre lies between these staff steps (bottom line = 0, top line = 8). A rest hangs in the middle of the staff; anything found past the outer lines is a le |  |
| staged/gather.py:8857 | `UNBOXED_REST_NEIGHBOUR_SPACES = 3.0` | sp |  | C | ? |  How far right of a cluster a notehead is still reported as its neighbour. UNBOXED_REST_NEIGHBOUR_SPACES = 3.0 |  |
| staged/rest_ink.py:36 | `CLOSE_SP = 0.25` | sp |  | C | ? | CLOSE_SP = 0.25 vertical closing, spaces: bridges erased-staff-line gaps in a stem |  |
| staged/rest_ink.py:37 | `COLUMN_SLACK_SP = 0.2` | sp |  | C | ? | COLUMN_SLACK_SP = 0.2 columns searched beyond the box's own x-range |  |
| staged/rest_ink.py:39 | `THIN_SP = 0.45` | sp |  | C | DECIDES | THIN_SP = 0.45 a row where the piece's widest horizontal run is at most this is a "thin" row |  |
| staged/rest_ink.py:42 | `ROW_SLACK_SP = 1.2` | sp |  | C | ? | ROW_SLACK_SP = 1.2 columns searched beyond the box's own x-range when taking a row's widest run |  |
| staged/rest_ink.py:43 | `WINDOW_X_SP = 2.0` | sp |  | C | ? | WINDOW_X_SP = 2.0 |  |
| staged/rest_ink.py:44 | `WINDOW_Y_SP = 4.5` | sp |  | C | ? | WINDOW_Y_SP = 4.5 |  |
| staged/stroke_owner.py:191 | `REST_MAX_LEN_SP = 3.8` | sp | LB | D | REFUSES |  a rest's longest stroke. 2.71's measured cut between a plain rest (2.8-3.1 sp) and a slashed stem boxed as a rest (4.5): `family_precision.REST_SLASHED_MIN_HEIGHT_SPACES | * rank 4: D, REFUSES a rest owner past 3.8 sp; both plates (2.205) |
| staged/stroke_owner.py:192 | `REST_BLOCK_MAX_W_SP = 1.6` | sp |  | C | ? | REST_BLOCK_MAX_W_SP = 1.6 a whole / half rest block ~1.1 x 0.5 |  |

## dot (36; A 2, B 2, C 29, D 3)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| staged/adjudicators/aug_dot_join.py:74 | `DOT_LINE_BAND = 0.2` | ? |  | C | DECIDES |  against Sean's labels: every one of 120 truth dots lies >= 0.31 steps from a line centre (the nearest, `0/0/3/1/6`, is a dotted quarter's dot Sean confirmed, standing 0. |  |
| staged/adjudicators/aug_dot_join.py:75 | `DOT_SPACE_BAND = 0.3` | sp |  | C | ? | DOT_SPACE_BAND = 0.3 |  |
| staged/adjudicators/aug_dot_join.py:188 | `DOT_SHAPED_MAX_SPACES = 0.75` | sp |  | C | REFUSES |  A refused box no larger than this on BOTH sides, in staff spaces, is dot-sized (`notehead_precision.DOT_SIZED_MAX_SPACES`; restated as a literal so this light module doe |  |
| staged/adjudicators/aug_dot_join.py:191 | `TWIN_DOT_MAX_SPACES = 0.3` | sp |  | C | REFUSES |  A dot-shaped refused box whose centre lies within this of a dot-class box's is the same ink boxed twice (`rhythm.DOT_TWIN_MAX_SPACES`, 2.127). TWIN_DOT_MAX_SPACES = 0.3 |  |
| staged/adjudicators/aug_dot_join.py:266 | `UNRESOLVED_MAX_GAP_SPACES = 1.2` | sp |  | C | NARROWS |  `overnight-20261013-night` (the role window itself is gap <= ~0.7 sp, 0.75 above / 0.25 below; the 596 refused dots lie mostly in -0.75..-0.25 and 0.75..1.0, the two nea |  |
| staged/adjudicators/aug_dot_join.py:267 | `UNRESOLVED_MIN_GAP_SPACES = -0.1` | sp |  | C | ? | UNRESOLVED_MIN_GAP_SPACES = -0.1 |  |
| staged/adjudicators/aug_dot_join.py:268 | `UNRESOLVED_MAX_DY_SPACES = 1.3` | sp |  | C | ? | UNRESOLVED_MAX_DY_SPACES = 1.3 |  |
| staged/adjudicators/aug_dot_join.py:271 | `STACCATO_CENTRED_MAX_SPACES = 0.5` | sp |  | C | ? |  The role decision's own staccato window (`rhythm.STACCATO_*`), in spaces. STACCATO_CENTRED_MAX_SPACES = 0.5 |  |
| staged/adjudicators/aug_dot_join.py:272 | `STACCATO_OFFSET_MIN_SPACES = 0.75` | sp |  | C | ? | STACCATO_OFFSET_MIN_SPACES = 0.75 |  |
| staged/adjudicators/aug_dot_join.py:273 | `STACCATO_MAX_GAP_SPACES = 2.0` | sp |  | C | ? | STACCATO_MAX_GAP_SPACES = 2.0 |  |
| staged/adjudicators/notehead_precision.py:698 | `DOT_SIZED_MAX_SPACES = 0.75` | sp |  | C | REFUSES |  (CLAUDE.md §10) and `too_narrow`'s floor is 1.0 sp. 0.75 sp sits in the gap, and the test needs BOTH sides small so a real head clipped to a sliver (short but >= 1.0 wid |  |
| staged/adjudicators/ownership.py:6392 | `DOT_TWIN_OVERLAP_MIN = 0.5` | count | B | D | DECIDES |  than DOT_TWIN_MAX_RATIO x the dot box on either side. ⚠️ Containment, not the group rule's IoU 0.3: a dot clipped by the cell edge is a fragment of the whole dot (Brahms |  |
| staged/adjudicators/ownership.py:6393 | `DOT_TWIN_MAX_RATIO = 1.35` | ratio |  | B | ? | DOT_TWIN_MAX_RATIO = 1.35 |  |
| staged/adjudicators/ownership.py:6410 | `DOT_STACK_MAX_SPACES = 2.0` | sp |  | B | DECIDES |  shifted head of a chord's second sits at 0.5-0.76 sp -- the span's EDGE. A lengthening dot sits to the RIGHT of its head at the head's own height (in the space, or the s |  |
| staged/adjudicators/ownership.py:6411 | `DOT_STACK_CENTRED_MAX_SPACES = 0.5` | sp |  | C | ? | DOT_STACK_CENTRED_MAX_SPACES = 0.5 |  |
| staged/adjudicators/rhythm.py:86 | `DOT_ABOVE_NOTE_MAX_SPACES = 0.75` | sp |  | C | DECIDES |  either way: one horn's dotted half read as a half in bars 1 and 5 and as a dotted half in bars 2, 3, 4 and 6. Measured over 116 dots the signed offsets are BIMODAL and n |  |
| staged/adjudicators/rhythm.py:87 | `DOT_BELOW_NOTE_MAX_SPACES = 0.25` | sp |  | C | ? | DOT_BELOW_NOTE_MAX_SPACES = 0.25 |  |
| staged/adjudicators/rhythm.py:2411 | `STACCATO_CENTRED_MAX_SPACES = 0.5` | sp |  | A | ? |  [1.00, 1.25) -- 970. The cut below is taken in that valley. CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: Sean has not adjudicated a print crop of this fam |  |
| staged/adjudicators/rhythm.py:2414 | `FOREIGN_DOT_MAX_GAP_SPACES = 0.75` | sp |  | C | ? |  ROADMAP 2.59: widest gap, head edge to dot, at which a dot may follow a note owned by ANOTHER staff (`OMR_DOT_FOLLOWS_NOTE`). FOREIGN_DOT_MAX_GAP_SPACES = 0.75 |  |
| staged/adjudicators/rhythm.py:2415 | `STACCATO_OFFSET_MIN_SPACES = 0.75` | sp |  | C | ? | STACCATO_OFFSET_MIN_SPACES = 0.75 |  |
| staged/adjudicators/rhythm.py:2447 | `STACCATO_MAX_GAP_SPACES = 2.0` | sp |  | C | ? |  `STACCATO_OFFSET_MIN_SPACES`), plus a REACH the home window never had: the dot lies no farther than `STACCATO_MAX_GAP_SPACES` from the head's nearest edge (= `ownership. |  |
| staged/adjudicators/rhythm.py:2775 | `DOT_TWIN_MAX_SPACES = 0.3` | sp |  | C | ? |  Two dot boxes this close (cell frame, in staff spaces) are one dot. DOT_TWIN_MAX_SPACES = 0.3 |  |
| staged/adjudicators/rhythm.py:2780 | `DOT_ON_STROKE_MIN = 0.5` | count | B | D | REFUSES |  A dot box whose ink is at least this share elongated stroke is not a dot (Sean 2026-10-09: "mostly overlap"). Real dots read 0.0 on Brahms p1. DOT_ON_STROKE_MIN = 0.5 |  |
| staged/clef_pagewide.py:78 | `DOT_STROKE_CLEAR_SPACES = 1.8` | sp |  | C | DECIDES |  a column of the dot window holding an unbroken raw ink run this long (staff spaces) is a stem / barline: cleared before the dots DOT_STROKE_CLEAR_SPACES = 1.8 |  |
| staged/clef_pagewide.py:82 | `DOT_NOT_A_STROKE_SPACES = 1.5` | sp |  | C | NARROWS |  a dot candidate whose centre column holds an unbroken ink run this long (staff spaces, lines included) is a stroke's piece DOT_NOT_A_STROKE_SPACES = 1.5 |  |
| staged/clef_pagewide.py:465 | `NOBOX_DOT_MAX_WIDTH_SPACES = 0.9` | sp | L | D | DECIDES |  a no-box dot may be this wide (staff spaces; the header locator allows 0.75): the body's tip touches the upper dot (Litolff bar 38, 0.76 sp fused) -- the body template i |  |
| staged/clef_pagewide.py:467 | `DOT_LINE_RUN_SPACES = 1.2` | sp |  | C | DECIDES |  a horizontal ink run this long (staff spaces) is a staff line or a beam, never part of a dot DOT_LINE_RUN_SPACES = 1.2 |  |
| staged/clef_pagewide.py:649 | `F_DOT_WIDTH_SPACES = 0.45` | sp |  | C | ? |  a dot's width (staff spaces): the template's dots start this far left of the dot pair's right edge `f_line` reports F_DOT_WIDTH_SPACES = 0.45 |  |
| staged/gather.py:4038 | `DOT_LINE_WINDOW_SPACES = 3.0` | sp |  | C | REFUSES |  The window of page columns the five lines are re-found in around a dot's own x, each side, in staff spaces (>= `CELL_LINE_MIN_WIDTH_SPACES` / 2 so the finder accepts it) |  |
| staged/gather.py:4045 | `DOT_OFF_STAFF_STEPS = 8.0` | count |  | A | NARROWS |  (abstains `off_staff` with the signed distance). CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: four spaces is more than any ledgered note's dot stands from |  |
| staged/gather.py:6918 | `DOT_STROKE_LINE_DOT_WIDTHS = 3.0` | ? |  | C | ? | DOT_STROKE_LINE_DOT_WIDTHS = 3.0 |  |
| staged/gather.py:6919 | `DOT_STROKE_LINE_MIN_SPACES = 1.0` | sp |  | C | ? | DOT_STROKE_LINE_MIN_SPACES = 1.0 |  |
| staged/gather.py:6920 | `DOT_STROKE_GROW_SPACES = 0.15` | sp |  | C | ? | DOT_STROKE_GROW_SPACES = 0.15 |  |
| staged/gather.py:6921 | `DOT_STROKE_ANGLES = [45, 90, 135]` | ? |  | C | ? | DOT_STROKE_ANGLES = (45, 90, 135) |  |
| staged/page_arcs.py:75 | `DOT_MIN_SP = 0.2` | sp |  | C | ? | DOT_MIN_SP = 0.2 |  |
| staged/page_arcs.py:76 | `DOT_MAX_SP = 0.75` | sp |  | C | ? | DOT_MAX_SP = 0.75 |  |

## accidental (30; A 3, B 2, C 19, D 4, E 2)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| direction_text.py:138 | `BandConfig.min_glyph_height_spaces = 0.18` | sp |  | C | ? | min_glyph_height_spaces: float = 0.18 |  |
| direction_text.py:139 | `BandConfig.max_glyph_height_spaces = 2.0` | sp |  | C | ? | max_glyph_height_spaces: float = 2.00 |  |
| staged/accidental_family.py:54 | `GLYPH_MIN_FRAC = 0.7` | ratio |  | B | ? | GLYPH_MIN_FRAC = 0.7 |  |
| staged/accidental_family.py:60 | `FAINT_LOWER_REVERSE_SP = 0.25` | sp |  | C | REFUSES |  a two-stem reading whose right stem's TOP is lower (natural-like) but whose BOTTOM ends this far above the left stem's bottom: the right upright's lower stroke is faint/ |  |
| staged/accidental_family.py:75 | `MAX_MARK_H_SP = 3.9` | sp |  | C | ? |  the mark is at most this tall after growing (a sharp is 3.0-3.5 spaces) MAX_MARK_H_SP = 3.9 |  |
| staged/accidental_family.py:84 | `NATURAL_STAGGER_MIN_SP = 0.45` | sp |  | C | ? |  NATURAL: the right stem's top (or bottom) is at least this much LOWER than the left's; measured 0.69-1.69 on the naturals (one at 0.37 had a cropped top, its bottom stag |  |
| staged/accidental_family.py:91 | `STAGGER_REVERSE_MAX_SP = 0.25` | sp |  | C | REFUSES |  ... and a natural's other end is never HIGHER than the left's by more than this (a mirrored natural is not a natural). STAGGER_REVERSE_MAX_SP = 0.25 |  |
| staged/accidental_family.py:101 | `NATURAL_READ_MARGIN = 0.25` | ? |  | A | DECIDES |  ROADMAP 2.263b (flag `OMR_NATURAL_READ`, default ON, deny-list: "0"/"false"/"no"/"off" turns it off; Sean 2026-11-04 12/12 tiles "All 12 are naturals"): a NATURAL read f |  |
| staged/accidental_shape.py:36 | `WINDOW_W = 0.45` | ? |  | C | ? |  Window size, as a fraction of the glyph's tight ink box: the outer 45% of the width by the outer 20% of the height (a sharp's stems stand at about a quarter and three qu |  |
| staged/accidental_shape.py:37 | `WINDOW_H = 0.2` | ? |  | C | ? | WINDOW_H = 0.20 |  |
| staged/accidental_shape.py:39 | `PRESENT_MIN = 0.6` | count |  | A | ? |  Stem strength (see above) at or above which a corner clearly holds a stem, and at or below which it clearly does not. PRESENT_MIN = 0.60 |  |
| staged/accidental_shape.py:40 | `ABSENT_MAX = 0.25` | count |  | A | ? | ABSENT_MAX = 0.25 |  |
| staged/accidental_shape.py:42 | `MIN_SIDE_PX = 6` | px |  | E | REFUSES |  The smallest ink box (px) the check will read at all; below it the box is a speck and the answer is `unread`. MIN_SIDE_PX = 6 |  |
| staged/adjudicators/ownership.py:2392 | `ACC_NEAR_DX_HEAD_WIDTHS = 3.0` | ? |  | C | REFUSES |  when its right edge stands within this many head widths LEFT of the head and within this many head heights of its centre -- a looser READ of "something stands there" tha |  |
| staged/adjudicators/ownership.py:2393 | `ACC_NEAR_DY_HEAD_HEIGHTS = 1.5` | ? |  | C | ? | ACC_NEAR_DY_HEAD_HEIGHTS = 1.5 |  |
| staged/adjudicators/ownership.py:5019 | `_ACC_MAX_DX_SPACES = 1.75` | sp | L | D | REFUSES |  Both fall to their lowest bin at **[1.75, 2.0)** and then flatten onto a roughly uniform background -- the population with no accidental of its own, which has no window  |  |
| staged/adjudicators/ownership.py:5036 | `_ACC_MAX_DY_POSITIONS = 1.4` | ? | LB | D | REFUSES |  off a cliff at the same place on both plates: Litolff … 1.2:58 · 1.3:32 · **1.4:10** · 1.5:12; Breitkopf … 1.2:277 · 1.3:189 · **1.4:67** · 1.5:25. A 3.2x and a 2.8x dro |  |
| staged/adjudicators/ownership.py:5047 | `_ACC_AMBIGUOUS_MARGIN_POSITIONS = 0.5` | ? |  | C | ? |  is 0.5 from each and the difference is 0 -- the case this abstention exists for. A glyph sitting ON one of them is 0.0 and 1.0, a difference of 1.0. Anything under half  |  |
| staged/gather.py:637 | `ACCIDENTAL_WITNESS_HALF_WIDTH_SPACES = 1.3` | sp |  | C | ? |  An accidental sits at the SAME staff position as its note, immediately to the accidental's right. ACCIDENTAL_WITNESS_HALF_WIDTH_SPACES = 1.3 how far right to look |  |
| staged/gather.py:638 | `ACCIDENTAL_WITNESS_HALF_HEIGHT_SPACES = 0.6` | sp |  | C | ? | ACCIDENTAL_WITNESS_HALF_HEIGHT_SPACES = 0.6 around the accidental's own y |  |
| staged/key_object.py:34 | `ACC_H_SPACES = [1.6, 4.4]` | sp |  | C | ? |  --- one accidental piece, in staff spaces (a printed flat is ~1.0 wide and ~2.7 tall; a sharp ~1.2 x 3.2; a natural ~0.8 x 2.8) --- ACC_H_SPACES = (1.6, 4.4) |  |
| staged/key_object.py:35 | `ACC_W_SPACES = [0.45, 1.9]` | sp |  | C | ? | ACC_W_SPACES = (0.45, 1.9) |  |
| staged/key_object.py:38 | `ACC_FILL_MIN = 0.28` | px |  | E | DECIDES |  ink pixels / box pixels (flats ~0.45, sharps ~0.35; a stemmed note is a thin stem plus a head, ~0.2): keeps the first note of a system with no key signature from being r |  |
| staged/page_accidental_ink.py:68 | `GLYPH_BASE = 360000` | ? |  | C | ? |  glyph ordinals of the accidentals this reader files a row for (ROADMAP 2.285 r2): past `gather._UNBOXED_REST_GLYPH_BASE` (350k) and every other gather base, BELOW `recor |  |
| staged/page_accidental_ink.py:82 | `GLYPH_H_MAX_FRAC = 1.3` | ratio | B | D | NARROWS |  the tallest ink that is ONE accidental, as a share of its glyph's height: Breitkopf prints ~10% larger than the font (`stroke_map`: the first try lost 15 of 21 naturals  | * rank 20: D, REFUSES taller ink; 'Breitkopf prints ~10% larger than the font' (f503d0b8b, 2.285) |
| staged/stroke_map.py:229 | `ACC_WHOLE_MIN_H_FRAC = 0.7` | sp | B | D | NARROWS |  "whole". CONVENTION (engraving, a prior): a sharp / natural is ~2.7-2.8 sp tall and a flat ~2.5 (SMuFL `ACCIDENTAL_SIZE_SPACES`), and the glyph's ink fills most of that. |  |
| staged/stroke_map.py:230 | `ACC_WHOLE_MIN_W_FRAC = 0.5` | ratio |  | B | ? | ACC_WHOLE_MIN_W_FRAC = 0.5 |  |
| staged/stroke_owner.py:181 | `ACC_BAR_MAX_LEN_SP = 1.8` | sp |  | C | ? | ACC_BAR_MAX_LEN_SP = 1.8 a sharp's crossbar / a natural's square side ~1.0-1.3 |  |
| staged/stroke_owner.py:182 | `ACC_BLOB_MAX_W_SP = 1.4` | sp |  | C | ? | ACC_BLOB_MAX_W_SP = 1.4 |  |
| staged/stroke_owner.py:183 | `ACC_BLOB_MAX_H_SP = 2.2` | sp |  | C | ? | ACC_BLOB_MAX_H_SP = 2.2 |  |

## ledger line (45; A 10, B 9, C 19, D 3, E 3, n/a 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| staged/adjudicators/family_precision.py:219 | `RUNG_STEP_TOL_SPACES = 0.25` | sp |  | C | ? |  How close to a whole number of spaces beyond the outer line a rung must sit, for `not_at_a_rung_step`. ⚠️ THE RULE IS HELD BACK — see `RUNG_STEP_SHIPS` — and this consta |  |
| staged/adjudicators/family_precision.py:292 | `LEDGER_INK_KEPT_MIN = 0.55` | count |  | A | DECIDES |  rung-thick and has no boxed head — the population where a head-sized blot of ink is least likely to be anything else. RED (the windows swapped, background read as `under |  |
| staged/adjudicators/family_precision.py:293 | `LEDGER_INK_KEPT_CONTRAST_MIN = 0.1` | count |  | A | ? | LEDGER_INK_KEPT_CONTRAST_MIN = 0.10 |  |
| staged/adjudicators/family_precision.py:294 | `LEDGER_INK_REFUSED_MAX = 0.05` | count |  | A | REFUSES | LEDGER_INK_REFUSED_MAX = 0.05 |  |
| staged/adjudicators/ownership.py:40 | `W_LADDER_COMPLETE = 4.0` | ? |  | n/a | ? |  ⚠️ ASSUMED WEIGHTS (A-OWN-1). Ordered to match the tiers the existing code already applies in this order; none is measured. W_LADDER_COMPLETE = 4.0 an unbroken run of le |  |
| staged/adjudicators/ownership.py:97 | `RUNG_GRID_TOLERANCE_SPACES = 0.5` | sp |  | C | DECIDES |  GATHER's own grid tolerance (`gather._observe_ladder`: `abs(ry - want) <= spacing * 0.5`), so a rung this walk matches at step k is the rung GATHER would have counted th |  |
| staged/adjudicators/ownership.py:100 | `LADDER_MAX_MISSING = 1` | ? | B | D | ? |  A ladder may be ONE rung short and still be a ladder. Breitkopf brk-02 (`glyph/9/0/11/0/1`, Sean: the filed staff) has rungs 2 and 3 and not 1. LADDER_MAX_MISSING = 1 |  |
| staged/adjudicators/ownership.py:105 | `LADDER_REACH_SPACES = 1.0` | sp | L | D | DECIDES |  ... and must END at the note: the head within this many spaces of the outermost rung found (0 on the rung, 0.5 in the space beyond it; 1.0 would be the NEXT line, whose  | * rank 16: D; Litolff #1 |
| staged/adjudicators/ownership.py:110 | `FAR_MIN_RUNGS = 2` | count |  | A | NARROWS |  A contest is FAR -- and abstains `far_no_rungs` when no rung is found toward any candidate -- only where EVERY candidate needs at least this many rungs (GATHER's arithme |  |
| staged/adjudicators/ownership.py:198 | `LEDGER_OWNER_RATIO_MIN = 2.0` | ratio |  | B | NARROWS |  candidate's own reading by at least this ratio to decide ownership -- "clearly more", not merely more. Self-calibrating per plate: the ratio is between the two candidate |  |
| staged/adjudicators/ownership.py:201 | `LEDGER_OWNER_FLOOR = 0.15` | ? |  | C | ? |  ...and the WINNING side's own reading must clear this floor, or two near-empty readings could satisfy the ratio by noise alone. LEDGER_OWNER_FLOOR = 0.15 |  |
| staged/adjudicators/ownership.py:1100 | `LadderSide.n_toward = 0` | count |  | A | ? | n_toward: int = 0 |  |
| staged/adjudicators/ownership.py:4394 | `ARTIC_LEDGER_POSITION_BELOW = 9.5` | ? |  | A | ? |  in `Q.NOTEHEAD_STAFF_POSITION`'s half-steps (top line 0, bottom line 8) the first ledger below is 10 and above is -2, so the cut is half a step inside each -- a head in  |  |
| staged/adjudicators/ownership.py:4395 | `ARTIC_LEDGER_POSITION_ABOVE = -1.5` | ? |  | C | ? | ARTIC_LEDGER_POSITION_ABOVE = -1.5 |  |
| staged/gather.py:2470 | `LEDGER_ROUND_UP = 0.25` | px |  | E | REFUSES |  ⚠️ `+ 0.25` before truncation is NOT a fudge: a note sitting ON the first ledger measures ~0.994 spacings, and plain truncation read that as needing NO rung -- so the sa |  |
| staged/gather.py:3111 | `LEDGER_RUNG_INK_WIDTH_HEAD_MULT = 1.75` | ? |  | C | ? |  falsified by a print-confirmed rung narrower than 1.5 head widths, or a real gap (beam, stem, unrelated ink) this wide passing as one. NOT CONFIRMED -- argued from CLAUD |  |
| staged/gather.py:3116 | `LEDGER_RUNG_INK_OVERHANG_HEAD_FRAC = 0.25` | ratio |  | B | ? |  How far past the head's own edge, in HEAD WIDTHS, the CONTEXT window reaches (used for the crop/background bands, not the overhang test itself -- see `LEDGER_RUNG_INK_OV |  |
| staged/gather.py:3134 | `LEDGER_RUNG_INK_OVERHANG_TEST_FRAC = 0.2` | ratio |  | A | REFUSES |  end of CLAUDE.md's "1.5-2 head widths" convention (0.25-0.5 each side) without reaching the blank paper past a real one -- falsified by a confirmed rung whose wing is sh |  |
| staged/gather.py:3141 | `LEDGER_RUNG_INK_THICKNESS_PAD_SPACES = 0.12` | sp |  | C | NARROWS |  thickness_px` attribute `gather_geometry` files it from -- one measurement, two readers), padded this many spaces each side, mirroring `LEDGER_INK_ STROKE_PAD_SPACES`. N |  |
| staged/gather.py:3145 | `LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES = 0.09` | sp |  | A | NARROWS |  Where a staff's own thickness was never traced (`Q.STAFF_SKEW` abstained): this fraction of a staff space stands in. CONVENTION ASSUMED, NOT CONFIRMED -- no crop this la |  |
| staged/gather.py:3150 | `LEDGER_RUNG_INK_DENSE = 0.55` | ? | LB | D | DECIDES |  A window at or above this ink fraction counts as "inked". NOT CONFIRMED against a print; falsified by a real rung whose window reads under this on a scan this bitonal (L | * rank 16: D, DECIDES an inked rung; NOT CONFIRMED (24967d799, 2.6d) |
| staged/gather.py:3156 | `LEDGER_RUNG_INK_ADJACENT_MAX = 0.35` | count |  | A | DECIDES |  band further up AND down must read BELOW this fraction, or the "thin" stroke found is really a tall one. Does NOT guard a slanted beam crossing at a shallow angle within |  |
| staged/gather.py:3179 | `LEDGER_RUNG_INK_SLANT_MAX_HALF_H = 0.2` | ? |  | B | ? |  (slant 11.3-12.1 against a half-height around 26.7, i.e. ~0.42-0.45 -- comfortably under 0.6). Retuned to 0.2: still four times the real rung's own measured slant (1.0)  |  |
| staged/gather.py:3195 | `LEDGER_RUNG_INK_TRUE_EDGE_DENSE = 0.5` | ? |  | B | DECIDES |  SAME row band the overhang test itself reads, still counts as the head's own ink; walking in from each padded edge toward the centre until a column crosses it finds wher |  |
| staged/gather.py:3558 | `LEDGER_OWNER_RATIO_MIN = 2.0` | ratio |  | B | NARROWS |  A candidate's reading must beat the other's by at least this ratio to decide ownership -- "clearly more", not merely more. LEDGER_OWNER_RATIO_MIN = 2.0 |  |
| staged/gather.py:3561 | `LEDGER_OWNER_FLOOR = 0.15` | ? |  | C | ? |  ...and the WINNING side's own reading must clear this floor, or two near-empty readings could satisfy the ratio by noise alone. LEDGER_OWNER_FLOOR = 0.15 |  |
| staged/gather.py:3565 | `LEDGER_OWNER_WIDTH_PAD_FRAC = 0.15` | ratio |  | B | NARROWS |  The tested x-span is the head's own true ink width (`_true_ink_span`), widened by this fraction each side -- "the same x-span" both candidates are read over, Sean's own  |  |
| staged/gather.py:3569 | `LEDGER_OWNER_ON_TOLERANCE_SPACES = 0.15` | sp |  | B | DECIDES |  A step whose position is within this many spaces of an INTEGER (the head sits almost exactly ON that rung's own row) is the head's own ink, not an independent witness -- |  |
| staged/gather.py:9273 | `LEDGER_INK_WINDOW_SPACES = [1.3, 1.0]` | sp |  | C | DECIDES |  ⚠️ THE WINDOW IS A NOTEHEAD, (width, height) in STAFF SPACES. 1.3 is the notehead width `notehead_precision` measured (the width floor costs 0 of 103 confirmed heads --  |  |
| staged/gather.py:9284 | `LEDGER_INK_STROKE_PAD_SPACES = 0.1` | sp |  | B | DECIDES |  ⚠️ THE RUNG'S OWN STROKE: the box's rows, padded by this many spaces each side, across the WHOLE window width -- a rung is a horizontal stroke wider than any head, and a |  |
| staged/head_ink.py:42 | `LEDGER_MIN_SPACES = 1.7` | sp |  | C | ? |  A ledger: a horizontal run at least this long (a head is <= ~1.5 sp wide on its ink; a ledger ~1.8-2.5 sp). LEDGER_MIN_SPACES = 1.7 |  |
| staged/page_arcs.py:106 | `LEDGER_THIN = 0` | ? |  | C | ? | LEDGER_THIN = 0 r3: a ledger box does not claim a column whose ink is much thicker than the box |  |
| staged/page_arcs.py:107 | `LEDGER_THIN_PX = 3` | px |  | E | ? | LEDGER_THIN_PX = 3 |  |
| staged/page_heads.py:63 | `LEDGER_MAX_THICK_SP = 0.35` | sp |  | C | ? |  a ledger stub: level, thin, short (`stroke_owner.LEDGER_MAX_*`) LEDGER_MAX_THICK_SP = 0.35 |  |
| staged/page_heads.py:64 | `LEDGER_MAX_LEN_SP = 3.5` | sp |  | C | ? | LEDGER_MAX_LEN_SP = 3.5 |  |
| staged/page_heads.py:68 | `RUNG_OUTSIDE_STEPS = 1.5` | count |  | A | ? |  a ledger stub's centre is at least this many half steps beyond the outer staff line (the first ledger is 2 half steps out; residue of the line itself is 0) RUNG_OUTSIDE_ |  |
| staged/page_owner.py:76 | `NOT_LEDGER_ROW_SLACK_PX = 1.5` | px |  | E | NARROWS |  a rung (a candidate ledger row at the head's x) lies ON an arc's traced ink when it is within this many px of the trace's rows at a column within `NOT_LEDGER_COLS` of th |  |
| staged/page_owner.py:77 | `NOT_LEDGER_COLS = 3` | ? |  | C | ? | NOT_LEDGER_COLS = 3 |  |
| staged/stroke_map.py:151 | `LEDGER_HEAD_EXCESS_SPACES = 0.35` | sp |  | B | DECIDES |  head/ledger: a horizontal stroke's column run this much thicker than its own line is a head on the rung LEDGER_HEAD_EXCESS_SPACES = 0.35 |  |
| staged/stroke_map.py:152 | `LEDGER_HEAD_MIN_WIDTH_SPACES = 0.6` | sp |  | C | ? | LEDGER_HEAD_MIN_WIDTH_SPACES = 0.6 |  |
| staged/stroke_map.py:154 | `LEDGER_STUB_MIN_SPACES = 0.15` | sp |  | C | ? |  ... and the rung sticks out at least this far beyond the oval on BOTH sides (a head at a rung's end, or a beam, is left whole) LEDGER_STUB_MIN_SPACES = 0.15 |  |
| staged/stroke_map.py:156 | `LEDGER_EDGE_EXCESS_SPACES = 0.2` | sp |  | C | DECIDES |  a column belongs to the oval while its run is this much thicker than the rung's (the oval's edge, 2.239 tiles 6 and 9) LEDGER_EDGE_EXCESS_SPACES = 0.2 |  |
| staged/stroke_map.py:162 | `LEDGER_MAX_SLOPE = 0.05` | ? |  | C | ? |  a ledger rung is level: its thin columns' centres fit a line no steeper than this (rise over run; ~3 degrees) LEDGER_MAX_SLOPE = 0.05 |  |
| staged/stroke_owner.py:178 | `LEDGER_MAX_THICK_SP = 0.35` | sp |  | C | ? | LEDGER_MAX_THICK_SP = 0.35 a ledger is as thin as a staff line (~0.12-0.2); a beam is >= 0.5 (2.202) |  |
| staged/stroke_owner.py:179 | `LEDGER_MAX_LEN_SP = 3.5` | sp |  | C | ? | LEDGER_MAX_LEN_SP = 3.5 |  |

## dynamic and word (120; A 8, B 12, C 67, D 20, E 3, n/a 10)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| direction_lexicon.py:137 | `MAX_PHRASE_TOKENS = 6` | ? |  | n/a | DECIDES |  A phrase longer than this is a title, a copyright line or an OCR run-on, not a direction. Measured against the corpus this exists for: the longest true direction on the  |  |
| direction_lexicon.py:344 | `CONNECTIVE_MAX_LETTERS = 4` | ? |  | C | REFUSES |  A single `general` library word this short or shorter is a connective and never a direction alone (`ein`, `und`, `sehr`, `avec`). CONNECTIVE_MAX_LETTERS = 4 |  |
| direction_lexicon.py:347 | `OTHER_LANGUAGE_MIN_LETTERS = 5` | count |  | A | ? |  A word outside the scope's languages is admitted only this long (folded). OTHER_LANGUAGE_MIN_LETTERS = 5 |  |
| direction_text.py:101 | `BandConfig.above_spaces = 8.0` | sp |  | C | ? | above_spaces: float = 8.0 |  |
| direction_text.py:122 | `BandConfig.below_spaces = 5.0` | sp |  | C | ? | below_spaces: float = 5.0 was 3.0: Brahms p12 `dim.` printed 3.4 spaces under a system's last staff (2026-10-08) |  |
| direction_text.py:125 | `BandConfig.clearance_spaces = 0.1` | sp |  | C | ? | clearance_spaces: float = 0.10 was 0.25: Brahms p12 `dim.` printed 0.2 spaces under its staff (2026-10-08) |  |
| direction_text.py:140 | `BandConfig.max_glyph_width_spaces = 2.0` | sp |  | C | ? | max_glyph_width_spaces: float = 2.00 |  |
| direction_text.py:159 | `BandConfig.word_gap_spaces = 2.2` | sp |  | C | ? | word_gap_spaces: float = 2.20 |  |
| direction_text.py:162 | `BandConfig.min_components = 3` | ? |  | C | ? | min_components: int = 3 |  |
| direction_text.py:164 | `BandConfig.min_word_width_spaces = 0.9` | sp |  | C | ? | min_word_width_spaces: float = 0.9 |  |
| direction_text.py:171 | `BandConfig.min_word_height_spaces = 0.55` | sp |  | C | ? | min_word_height_spaces: float = 0.55 |  |
| direction_text.py:176 | `BandConfig.detection_pad_spaces = 0.18` | sp |  | C | ? | detection_pad_spaces: float = 0.18 |  |
| direction_text.py:197 | `BandConfig.inside_word_gap_spaces = 0.9` | sp |  | C | DECIDES | inside_word_gap_spaces: float = 0.9 was 0.5: Brahms p7 `espr.` letters read as dynamics, 0.5-0.9 sp apart; a real dynamic stands 1.7 clear (2026-10-08) |  |
| direction_text.py:218 | `BandConfig.max_blank_width_spaces = 4.0` | sp |  | C | ? | max_blank_width_spaces: float = 4.0 |  |
| direction_text.py:223 | `BandConfig.fused_word_max_width_spaces = 7.0` | sp |  | C | ? | fused_word_max_width_spaces: float = 7.0 |  |
| direction_text.py:224 | `BandConfig.fused_word_min_height_spaces = 0.9` | sp |  | C | ? | fused_word_min_height_spaces: float = 0.9 |  |
| direction_text.py:225 | `BandConfig.fused_word_min_fill = 0.45` | ratio |  | B | ? | fused_word_min_fill: float = 0.45 |  |
| direction_text.py:226 | `BandConfig.fused_word_weight = 3` | ? |  | C | ? | fused_word_weight: int = 3 |  |
| direction_text.py:233 | `BandConfig.word_initial_gap_spaces = 0.35` | sp |  | C | ? | word_initial_gap_spaces: float = 0.35 |  |
| direction_text.py:238 | `BandConfig.tempo_strip_max_glyph_spaces = 3.6` | sp |  | C | ? | tempo_strip_max_glyph_spaces: float = 3.6 |  |
| direction_text.py:239 | `BandConfig.a_due_gap_spaces = 0.8` | sp |  | C | ? | a_due_gap_spaces: float = 0.8 |  |
| direction_text.py:619 | `STUB_MAX_WIDTH_SPACES = 0.45` | sp | L | D | DECIDES |  `Adagio` joined the word, stretched its box down into the notes, and the OCR read `nee`; Litolff p15: the stem over `Vcl.` made the box and the reading `val.`). What sep |  |
| direction_text.py:621 | `STUB_MIN_HEIGHT_SPACES = 0.6` | sp |  | C | REFUSES |  ...and at least this tall; a dot-sized speck is left to the letter tests. STUB_MIN_HEIGHT_SPACES = 0.6 |  |
| direction_text.py:623 | `STUB_TOUCH_PX = 2` | px |  | E | ? |  How far past the stroke's top or bottom row erased ink must lie, in px. STUB_TOUCH_PX = 2 |  |
| direction_text.py:658 | `GROW_STRIP_SPACES = 0.5` | sp |  | C | ? |  is cut where it leaves and the beams it reaches are not part of the piece; it must straddle the word's centre line, touch the word within `GROW_GAP_SPACES`, be at least  |  |
| direction_text.py:659 | `GROW_GAP_SPACES = 0.6` | sp |  | C | ? | GROW_GAP_SPACES = 0.6 |  |
| direction_text.py:663 | `GROW_MIN_WIDTH_SPACES = 1.0` | sp | LB | D | REFUSES |  A letter's width, not a stroke's. A scanned barline or stem is 8-9 px, 0.51- 0.61 spaces (Litolff p9 x2, Brahms p24: the three it grew over on the 10 review pages); the  |  |
| direction_text.py:671 | `GROW_MAX_DYNAMIC_COVER = 0.9` | ratio | L | D | DECIDES |  `f` of `più f` (99% inside) made Surya read `p rinf`, which the lexicon accepts; the `p` of `pizz.` beside `Basso` (100%) cost `Basso`. The `pi` of Litolff p9's `pizz.`  |  |
| direction_text.py:678 | `GROW_MAX_HEIGHT_SPACES = 3.6` | sp |  | C | ? | GROW_MAX_HEIGHT_SPACES = 3.6 = `tempo_strip_max_glyph_spaces`, the largest letter we admit anywhere |  |
| direction_text.py:679 | `GROW_MAX_WIDTH_SPACES = 4.0` | sp |  | C | DECIDES | GROW_MAX_WIDTH_SPACES = 4.0 = `max_blank_width_spaces`: wider is a span, not glyphs |  |
| direction_text.py:1029 | `CROP_PAD_X_SPACES = 1.3` | sp |  | C | REFUSES |  was dropped — an `l` fused into the slur above it, an `f` blanked with the dynamic it touches — arrives cut off at the left. `legato` read as `egato` is a lexicon miss,  |  |
| direction_text.py:1030 | `CROP_PAD_Y_SPACES = 0.45` | sp |  | C | ? | CROP_PAD_Y_SPACES = 0.45 |  |
| direction_text.py:1047 | `MIN_CROP_SPACING_PX = 80.0` | px |  | E | ? |  Expressed in staff spaces rather than pixels because that is what makes it independent of `--dpi`: at 600 dpi a space is 41 px and this doubles it, while a 300-dpi page  |  |
| direction_text.py:1048 | `MAX_CROP_UPSCALE = 4.0` | ? |  | C | ? | MAX_CROP_UPSCALE = 4.0 |  |
| direction_text.py:1143 | `TIGHT_PAD_X_SPACES = 0.25` | sp | LB | D | DECIDES |  the barline, the neighbouring notehead and staff-line stubs -- `cresc.` between two barlines came back from Surya as '' or as `CRESC. CRESC. CRESC.` and from the same bo |  |
| direction_text.py:1144 | `TIGHT_PAD_Y_SPACES = 0.2` | sp |  | C | ? | TIGHT_PAD_Y_SPACES = 0.2 |  |
| direction_text.py:1231 | `SCAN_MAX_DRAWINGS = 8` | ? |  | C | REFUSES |  populations do not touch and this sits in the gap -- it is READ OFF the measurement in `page_is_engraved`'s own docstring, not chosen. An OCR text layer someone attached |  |
| direction_text.py:1308 | `DIRECTION_CROP_TIMEOUT_S = 20.0` | ? |  | n/a | DECIDES |  Belt-and-braces wall-time guard per crop (s): a crop still silent after this reads as "" and the next crop goes on. Normal crops take 0.1-3 s. DIRECTION_CROP_TIMEOUT_S = |  |
| direction_text.py:1319 | `DIRECTION_CAP_BASE = 32` | ? | B | n/a | REFUSES |  held-out scan pages (benchmarks/omr-local-staff-2026-09 FINDINGS, 2026-10-08): reading time 355 s -> 148 s, no word lost against the uncapped reader. A FIXED 64-token ca |  |
| direction_text.py:1320 | `DIRECTION_CAP_PER_SPACE = 4` | sp |  | C | ? | DIRECTION_CAP_PER_SPACE = 4 |  |
| direction_text.py:1339 | `TIGHT_CAP_BASE = 8` | sp |  | n/a | REFUSES |  A TIGHT crop holds one word and white margin, so Surya's output ceiling can be lower still: about 2 characters a staff space is generous for an italic word (`cresc.` is  |  |
| direction_text.py:1340 | `TIGHT_CAP_PER_SPACE = 2` | sp |  | C | ? | TIGHT_CAP_PER_SPACE = 2 |  |
| direction_text.py:1556 | `RETRY_MIN_LETTERS = 3` | count |  | A | DECIDES |  A crop is worth the slow reader's time on the retry only if the cheap one saw LETTERS in it: at least this many alphabetic characters. Staff-line debris and beamed notes |  |
| direction_text.py:1562 | `SLOW_WIDE_BUDGET_S = 17.0` | ? | B | n/a | NARROWS |  Wall time (s) after which the slow rung stops taking the STANDARD crop of candidates its tight crop failed on. The tight pass has run on every lettered crop by then; thi |  |
| direction_text.py:1568 | `SIBLING_X_SLACK_SPACES = 3.0` | sp | L | D | ? |  How far, in staff spaces, a sibling word may sit from the word it echoes and still be "at the same x": the same cresc. is engraved in the same bar on every staff but not |  |
| direction_text.py:1653 | `DYNAMIC_LINK_REACH_SPACES = 1.5` | sp |  | C | ? | DYNAMIC_LINK_REACH_SPACES = 1.5 |  |
| direction_text.py:1728 | `CUT_TAIL_REACH_SPACES = 0.9` | sp | L | D | REFUSES |  marking, not a word followed by a dynamic: the `p` is the `p` of `più`, and the `iù` after it is boxed as a dynamic and so was never part of the box (Litolff p8, 2026-10 |  |
| direction_text.py:1775 | `WIDE_BOX_SPACES_PER_LETTER = 2.0` | sp | B | D | DECIDES |  longer string only has to begin with the accepted words; what it adds only has to be letters. 2.0 sits above 117 of 119 accepted readings on the 11 review pages (median  |  |
| staged/adjudicators/notehead_precision.py:2935 | `DYNAMIC_LETTER_HEAD_ON_MIN = 0.4` | count |  | A | ? |  Fraction of the HEAD box's area that lies inside a letter box. DYNAMIC_LETTER_HEAD_ON_MIN = 0.4 |  |
| staged/adjudicators/notehead_precision.py:2937 | `DYNAMIC_LETTER_STROKE_DISC_SPACES = 0.9` | sp |  | C | DECIDES |  Widest filled disc (staff spaces) below which a head's ink is a stroke. DYNAMIC_LETTER_STROKE_DISC_SPACES = 0.9 |  |
| staged/adjudicators/notehead_precision.py:2940 | `DYNAMIC_LETTER_BODY_SHARE = 0.4` | ratio |  | B | DECIDES |  Share of the letter box's ink the head box holds, at or above which the head is the letter's body. DYNAMIC_LETTER_BODY_SHARE = 0.4 |  |
| staged/adjudicators/notehead_precision.py:2942 | `DYNAMIC_F_MIN_W_SPACES = 1.7` | sp |  | C | REFUSES |  An `f` box narrower than this is not an `f`. DYNAMIC_F_MIN_W_SPACES = 1.7 |  |
| staged/adjudicators/notehead_precision.py:2949 | `DYNAMIC_LETTER_INSIDE_MIN = 0.5` | count | LB | D | REFUSES |  disc is below `DYNAMIC_LETTER_INSIDE_DISC_SPACES` is the letter's own curl or hook, never a note. Measured on real marks (Litolff 20261029 slices, our look at the crops) |  |
| staged/adjudicators/notehead_precision.py:2950 | `DYNAMIC_LETTER_INSIDE_DISC_SPACES = 1.1` | sp |  | C | ? | DYNAMIC_LETTER_INSIDE_DISC_SPACES = 1.1 |  |
| staged/adjudicators/stem_value.py:323 | `CROP_EDGE_PX = 3.0` | px | B | D | ? |  A stroke end within this many canonical px of the crop's top or bottom edge is cut by it. MEASURED: on Brahms 317803 p0-1 the cut stems' ends stand within 1 px of the ed |  |
| staged/adjudicators/text.py:37 | `DYNAMIC_OWN_BAND_MIN_SPACES = -0.52` | sp |  | C | NARROWS |  `DYNAMIC_OWN_BAND_MIN_SPACES` is this staff's own; one at or below `DYNAMIC_ABOVE_BAND_MAX_SPACES` is decisively the staff above's; the gap between the two is left exact |  |
| staged/adjudicators/text.py:38 | `DYNAMIC_ABOVE_BAND_MAX_SPACES = -3.04` | sp |  | C | ? | DYNAMIC_ABOVE_BAND_MAX_SPACES = -3.04 |  |
| staged/adjudicators/text.py:95 | `SAME_LETTER_SHARE = 0.5` | ratio | B | D | ? |  printed letter cut from two cells (`gather._same_ink_boxes`' own 0.5). Not IoU: the same `f` boxed tall from one cell and as its lower half from the other overlaps at Io |  |
| staged/adjudicators/text.py:150 | `SINGLE_LETTER_MAX_WIDTH_SPACES = 2.9` | sp |  | C | DECIDES |  letters the ink can HOLD can. WHAT WOULD FALSIFY IT: a plate whose single `f` is wider than 2.9 spaces collapsing nothing it should (a double stays), or a printed `ff` s |  |
| staged/adjudicators/text.py:153 | `LETTER_MIN_HEIGHT_SPACES = 0.8` | sp | B | D | REFUSES |  A dynamic letter is at least this tall (spaces); a thinner box is a sliver of one, never a letter of its own (Brahms p1 `p` slivers 14 px = 0.4 spaces). LETTER_MIN_HEIGH | * rank 14: D, REFUSES a letter; Brahms p1 slivers (2d76c8668, 2.68) |
| staged/adjudicators/text.py:292 | `SIBLING_WIDTH_RATIO = [0.7, 1.5]` | ratio |  | B | ? | SIBLING_WIDTH_RATIO = (0.7, 1.5) |  |
| staged/adjudicators/text.py:294 | `UNREAD_LINE_MIN_LETTERS = 2` | count |  | A | REFUSES |  an unread line is a TEXT line only where the DETECTOR (a reader of its own, not the OCR) boxed at least this many dynamic letters inside it; one lone letter is piano (Se |  |
| staged/adjudicators/text.py:297 | `UNREAD_OWN_WORD_X_SHARE = 0.2` | ratio | L | D | NARROWS |  a candidate whose x-range shares this much of ITS OWN width with a word the same staff READ (y-ranges touching) is that word's own sibling window, not an unread line (Li |  |
| staged/adjudicators/text.py:300 | `UNREAD_LINE_MIN_WIDTH_LETTERS = 4.0` | px | L | D | REFUSES |  a text line is wider than its detector letters: its width is at least this many times its MEDIAN letter box (a twin box of one letter can be twice as wide). A line a lon |  |
| staged/adjudicators/text.py:1087 | `HALVES_TOUCH_SPACES = 0.25` | sp |  | B | ? |  Two pieces of ink standing no further apart than this share of a staff space, in two different cells, are touching. HALVES_TOUCH_SPACES = 0.25 |  |
| staged/adjudicators/text.py:1257 | `INSIDE_READ_WORD_SHARE = 0.5` | ratio |  | B | DECIDES |  A letter box with at least this share of its area inside a word box is one of the word's letters (ROADMAP 2.68). INSIDE_READ_WORD_SHARE = 0.5 |  |
| staged/claims.py:248 | `WORD_BAND_OVERLAP_MAX = 0.25` | count |  | B | ? |  a word / dynamic is OUTSIDE the staves when at most this share of its box's height lies inside any staff's line band (top line to bottom line, +- `WORD_BAND_PAD_SPACES`) |  |
| staged/claims.py:249 | `WORD_BAND_PAD_SPACES = 0.5` | sp |  | C | ? | WORD_BAND_PAD_SPACES = 0.5 |  |
| staged/claims.py:252 | `LETTER_JOIN_GAP_SPACES = 0.6` | sp | L | D | ? |  two detector dynamic letters belong to ONE printed dynamic when the gap between their boxes is at most this (staff spaces) and their boxes overlap vertically by at least | * rank 14: D, DECIDES one dynamic; Litolff p4 ff |
| staged/claims.py:253 | `LETTER_ROW_OVERLAP_MIN = 0.5` | count |  | A | ? | LETTER_ROW_OVERLAP_MIN = 0.5 |  |
| staged/claims.py:255 | `LETTER_TWIN_SHARE = 0.5` | ratio |  | B | ? |  two letter boxes are the SAME ink (a twin) when they overlap by this share of the smaller box (gather `_same_ink_boxes`' cut) LETTER_TWIN_SHARE = 0.5 |  |
| staged/claims.py:291 | `LETTER_TWIN_CENTRE_SHARE = 0.4` | ratio | L | D | DECIDES |  ROADMAP 2.284b r2: two boxes that overlap by `LETTER_TWIN_SHARE` are one ink boxed twice only when their CENTRES also lie within this share of the narrower box's width - |  |
| staged/claims.py:293 | `LETTER_WIDE_SHARE = 1.5` | ratio |  | B | DECIDES |  a single slot wider than this share of the system's median letter-box width is a word of unknown length (see `spell_letter_runs`) LETTER_WIDE_SHARE = 1.5 |  |
| staged/claims.py:439 | `DYNAMIC_INK_GROW_SPACES = 0.5` | sp | L | D | ? |  ROADMAP 2.296: a detector letter box is TIGHT (a `p`'s descender ends past it: Litolff p8 `sempre piu p`, box bottom 1607, ink to 1613), so a claim of the box's rectangl |  |
| staged/claims.py:462 | `WORD_INK_GROW_SPACES = 0.5` | sp |  | C | ? | WORD_INK_GROW_SPACES = 0.5 |  |
| staged/claims.py:464 | `WORD_STROKE_SLACK_SPACES = 0.1` | sp | LB | D | ? |  the stroke map's box lies up to this far past the ink it holds (1.5 px = 0.05 sp on Brahms p0); the claim keeps this much past its ink (0.1 sp = 3 px Brahms, 1.6 px Lito |  |
| staged/claims.py:466 | `WORD_LINE_WIDTH_SPACES = 4.0` | sp |  | C | REFUSES |  a clipped component this wide and this thin is a staff or ledger line, not a letter's stroke WORD_LINE_WIDTH_SPACES = 4.0 |  |
| staged/claims.py:467 | `WORD_LINE_THICK_SPACES = 0.4` | sp |  | C | ? | WORD_LINE_THICK_SPACES = 0.4 |  |
| staged/claims.py:482 | `WORD_TOKEN_REACH_CHARS = 1.0` | ? |  | n/a | DECIDES |  a run's letter is the word's only where the word's text puts that spot outside every dynamic token's stretch of the box plus this many characters either side (the layout |  |
| staged/claims.py:484 | `WORD_LETTER_SHARE = 0.5` | ratio |  | B | DECIDES |  a letter box with at least this share of its area inside the word's box is one of the word's letters (the same share `adjudicators.text.INSIDE_READ_WORD_SHARE` uses) WOR |  |
| staged/claims.py:553 | `TEMPO_NOTE_GAP_SPACES = 3.0` | sp | L | D | DECIDES |  ROADMAP 2.221 word coverage -- the geometry of the extra word claims. All of it reads rows and rasters GATHER already holds. a metronome note stands this far right of it |  |
| staged/claims.py:555 | `TEMPO_TAIL_GAP_SPACES = 2.0` | sp |  | C | ? |  ... and its `= 108` ink continues until a gap this wide, at most this far from the note TEMPO_TAIL_GAP_SPACES = 2.0 |  |
| staged/claims.py:556 | `TEMPO_TAIL_MAX_SPACES = 10.0` | sp |  | C | ? | TEMPO_TAIL_MAX_SPACES = 10.0 |  |
| staged/consequences.py:2435 | `INSIDE_WORD_SHARE = 0.5` | ratio | B | D | REFUSES |  one of the WORD's letters the detector also boxed as a dynamic -- the `p` of `più` (Brahms p3 staff 13: `dynamicP` 4781-4830 inside `più` 4782-4908) -- not a dynamic pri |  |
| staged/gather.py:4695 | `LETTER_LINE_SPACES = 2.0` | sp |  | C | REFUSES |  A horizontal run this long (staff spaces) is a staff or ledger line, not a letter: no letter's stroke runs 2 spaces without bending. LETTER_LINE_SPACES = 2.0 |  |
| staged/gather.py:4698 | `LETTER_SPECK_SPACES2 = 0.08` | sp |  | B | REFUSES |  Ink under this share of a square staff space is a speck, not a part of the letter. LETTER_SPECK_SPACES2 = 0.08 |  |
| staged/gather.py:4766 | `LETTER_GAP_SPACES = 0.5` | sp |  | B | ? |  How close letter ink must stand to a dynamic letter, on its own line, for the letter to have a NEIGHBOUR: the space between two letters of one word. A dynamic beside a w |  |
| staged/gather.py:12222 | `HEAD_ON_LETTER_FILE_FLOOR = 0.2` | ? |  | C | ? |  A head box is measured against a letter only where at least this fraction of the HEAD box's area lies inside the letter's box. Below it the two boxes merely touch; ADJUD |  |
| staged/gather.py:12400 | `LETTER_COVER_FILE_FLOOR = 0.2` | ratio |  | B | REFUSES |  A head or rest box needs at least this share of its own ink inside the read letters' boxes to get a `Q.LETTER_LOOK_COVER` row (ADJUDICATE refuses at its own, higher bar  |  |
| staged/gather.py:14926 | `_VOLTA_SURYA_PAD = 60` | px | B | n/a | DECIDES |  measured on Brahms p10: unpadded native-size crops read "" for both brackets, padded 60 px and 2x upscaled read "1." and "2." (deterministic over repeat runs). The token |  |
| staged/gather.py:14927 | `_VOLTA_SURYA_SCALE = 2` | ? |  | C | ? | _VOLTA_SURYA_SCALE = 2 |  |
| staged/gather.py:14928 | `_VOLTA_SURYA_MAX_TOKENS = 16` | ? |  | n/a | ? | _VOLTA_SURYA_MAX_TOKENS = 16 |  |
| staged/gather.py:14929 | `_VOLTA_SURYA_TIMEOUT_S = 60.0` | ? |  | n/a | ? | _VOLTA_SURYA_TIMEOUT_S = 60.0 |  |
| staged/gather.py:17119 | `_DIRECTION_GLYPH_BASE = 90000` | ? |  | C | ? |  space. Same guard and same reason as `_CV_GLYPH_BASE`: a collision would not raise -- it would silently merge two readers' rows into one subject, which is precisely the  |  |
| staged/letter_look.py:62 | `LOOK_CONF_FLOOR = 0.05` | conf |  | C | DECIDES |  The floor the detector is asked at; everything above it is recorded, only `STRONG_CONF` at `STRONG_MIN_SCALES` looks counts as a reading. LOOK_CONF_FLOOR = 0.05 |  |
| staged/letter_look.py:70 | `PROBE_CONF = 0.3` | conf |  | C | ? | PROBE_CONF = 0.3 |  |
| staged/letter_look.py:71 | `STRONG_CONF = 0.7` | conf |  | C | ? | STRONG_CONF = 0.7 |  |
| staged/letter_look.py:72 | `STRONG_MIN_SCALES = 4` | count |  | A | ? | STRONG_MIN_SCALES = 4 |  |
| staged/letter_look.py:79 | `WEAK_CONF = 0.15` | conf |  | n/a | ? | WEAK_CONF = 0.15 |  |
| staged/letter_look.py:84 | `LETTER_H_MAX_SPACES = 3.4` | sp |  | C | DECIDES |  A piece of ink is a LETTER's only within these sizes (staff spaces): an `f` is ~2.9 tall (Sean's 12 hand-labelled: 2.4-2.6), a stem is >= 3.0 and thin, a beam is wider t |  |
| staged/letter_look.py:85 | `LETTER_W_MAX_SPACES = 6.5` | sp |  | C | ? | LETTER_W_MAX_SPACES = 6.5 |  |
| staged/letter_look.py:86 | `LETTER_SPECK_SPACES2 = 0.08` | ? |  | C | REFUSES | LETTER_SPECK_SPACES2 = 0.08 |  |
| staged/letter_look.py:91 | `GROUP_GAP_SPACES = 0.6` | sp |  | C | ? |  Letters of one word stand this close (the 2.68 neighbour gap is 0.5). GROUP_GAP_SPACES = 0.6 |  |
| staged/letter_look.py:106 | `MAX_STRINGS = 64` | ? |  | C | ? | MAX_STRINGS = 64 |  |
| staged/letter_look.py:146 | `ERASE_SLACK_TIGHT_PX = 1` | px |  | E | REFUSES |  The two erasures a letter must read the same under (`read_group`): the line thickness plus a fifth of a space (the default) and plus ONE pixel. Free ink is the same unde |  |
| staged/letter_look.py:192 | `Comp.label = 0` | ? |  | C | ? | label: int = 0 |  |
| staged/letter_look.py:327 | `Region.conf = 0.0` | ? |  | C | ? | conf: float = 0.0 |  |
| staged/letter_look.py:328 | `Region.scales_seen = 0` | ? |  | C | ? | scales_seen: int = 0 |  |
| staged/letter_look.py:341 | `PAIR_CONF = 0.5` | conf |  | C | ? |  A same-class pair at one scale counts only if both boxes are this confident. PAIR_CONF = 0.5 |  |
| staged/letter_look.py:343 | `PAIR_MIN_SCALES = 3` | count |  | A | ? |  ... on at least this many scales. PAIR_MIN_SCALES = 3 |  |
| staged/letter_look.py:560 | `REMNANT_MIN_H_SPACES = 1.0` | sp | B | D | REFUSES |  is a letter nobody read (Sean, 2.107 tile 8: Brahms `ff`, the look read ONE `f` and decided `f`). It must be this big (staff spaces) and stand beside a read letter on it |  |
| staged/letter_look.py:561 | `REMNANT_MIN_W_SPACES = 0.7` | sp |  | C | ? | REMNANT_MIN_W_SPACES = 0.7 |  |
| staged/letter_look.py:562 | `REMNANT_MIN_AREA_SPACES2 = 0.5` | ? |  | C | ? | REMNANT_MIN_AREA_SPACES2 = 0.5 |  |
| staged/letter_look.py:563 | `REMNANT_BOX_PAD_SPACES = 0.15` | sp |  | C | ? | REMNANT_BOX_PAD_SPACES = 0.15 |  |
| staged/letter_look.py:660 | `GroupReading.n_hypotheses = 0` | count |  | A | ? | n_hypotheses: int = 0 |  |
| staged/letter_look.py:833 | `WINDOW_PAD_X_SPACES = 8.0` | sp |  | C | ? |  where, around a seed, to look for the pieces of its group (staff spaces) WINDOW_PAD_X_SPACES = 8.0 |  |
| staged/letter_look.py:834 | `WINDOW_PAD_Y_SPACES = 6.0` | sp |  | C | ? | WINDOW_PAD_Y_SPACES = 6.0 |  |
| staged/letter_look.py:836 | `GROUP_MIN_H_SPACES = 0.8` | sp |  | C | ? |  a group must be this big to be a letter group at all (staff spaces) GROUP_MIN_H_SPACES = 0.8 |  |
| staged/letter_look.py:837 | `GROUP_MIN_W_SPACES = 0.5` | sp |  | C | ? | GROUP_MIN_W_SPACES = 0.5 |  |
| staged/stroke_owner.py:185 | `LETTER_MAX_LEN_SP = 3.0` | sp |  | C | ? | LETTER_MAX_LEN_SP = 3.0 a dynamic letter's longest stroke |  |

## voices (2; B 1, C 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| staged/adjudicators/rhythm.py:10524 | `VOICE_SUM_EPSILON_QUARTERS = 1e-06` | ? |  | C | REFUSES |  A sum within this many quarter-notes of the meter's own length counts as "the bar" -- floating rational arithmetic on dotted/tuplet beats, not a musical tolerance. Micro |  |
| staged/adjudicators/stem_value.py:518 | `UNISON_TOUCH_RATIO = 2.0` | ratio |  | B | ? |  ROADMAP 2.175: how many times further than its touch past the head a unison stem must run away from it. UNISON_TOUCH_RATIO = 2.0 |  |

## notehead and fill (210; A 21, B 25, C 135, D 25, E 3, n/a 1)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| direction_text.py:145 | `BandConfig.min_fill_ratio = 0.16` | ratio |  | B | ? | min_fill_ratio: float = 0.16 |  |
| direction_text.py:680 | `GROW_MIN_FILL = 0.3` | ratio |  | B | ? | GROW_MIN_FILL = 0.30 `Ad` 0.47; a slur's box is ~0.03 |  |
| header_ink.py:157 | `MAX_HEADER_LINE_SHIFT_SPACES = 0.6` | sp | L | D | DECIDES |  Beethoven 5 p.15: three staves are off by 0.36-0.47 spaces there, and every staff whose key signature the pipeline managed to read is off by less than 0.08. Half a space |  |
| header_ink.py:160 | `MIN_HEADER_SHIFT_GAIN = 1.05` | ? |  | C | ? |  The shift has to buy this much more line ink than staying put, so a cell whose lines are already right is left alone rather than nudged onto a glyph. MIN_HEADER_SHIFT_GA |  |
| header_ink.py:449 | `WANDER_QUANTILE = 99.0` | px |  | E | ? |  Bach WTC p.1, whose lines are straight to within half a pixel, the maximum reports 13.5 px and this quantile reports 0.5. A line that genuinely bends bends across many c |  |
| staff_header.py:82 | `HEADER_MEASURE_INDEX = -1` | ? |  | n/a | REFUSES |  A header cell is not a measure. It overlaps measure 0 and would corrupt any per-measure bookkeeping that keyed on it, so it carries a measure_index that cannot collide w |  |
| staff_header.py:106 | `HeaderWindowConfig.gap_tolerance_spaces = 0.25` | sp |  | C | ? | gap_tolerance_spaces: float = 0.25 |  |
| staff_header.py:107 | `HeaderWindowConfig.left_margin_spaces = 0.5` | sp |  | C | ? | left_margin_spaces: float = 0.5 |  |
| staff_header.py:108 | `HeaderWindowConfig.min_width_spaces = 3.0` | sp |  | C | ? | min_width_spaces: float = 3.0 |  |
| staff_header.py:109 | `HeaderWindowConfig.max_width_spaces = 16.0` | sp |  | C | ? | max_width_spaces: float = 16.0 |  |
| staged/adjudicators/aug_dot_join.py:76 | `HEAD_MAX_RESIDUAL = 0.25` | ? |  | C | ? | HEAD_MAX_RESIDUAL = 0.25 |  |
| staged/adjudicators/aug_dot_join.py:83 | `HEAD_MAX_OUTSIDE_STEPS = 4.0` | count | B | D | DECIDES |  ledger-counted verdict owns it), so its step is not read here. Measured on Brahms 317803 p.0 against Sean's OnLine/InSpace labels: parity of the geometry position agrees |  |
| staged/adjudicators/family_precision.py:256 | `HEAD_NEAR_TOL_SPACES = 2.75` | sp |  | C | DECIDES |  outermost, so the innermost is two spaces from the only head that x-overlaps it. The p95 is "how long is a ledger run on this plate", not "how thick is a notehead". And  |  |
| staged/adjudicators/head_on_mark.py:51 | `LEADING_EDGE_SPACES = 0.5` | sp |  | C | ? |  A head box whose left edge is this close to the left edge of the system's first cell (staff spaces). LEADING_EDGE_SPACES = 0.5 |  |
| staged/adjudicators/head_rest_shape.py:64 | `HEAD_INK_COVER_MIN = 0.5` | ratio | LB | D | NARROWS |  Share of the SMALLER of {head box, ink cluster} the two share for the cluster to be the head's ink. Measured: Litolff/Brahms head boxes inside their clusters (the 16 can |  |
| staged/adjudicators/head_rest_shape.py:67 | `HEAD_INK_COVERAGE_MIN = 0.3` | ratio |  | B | ? |  A cluster the head box (or any notehead box) accounts for at least this much. Below `unboxed_rest.TOUCHED_SHARE` the ink is not the head's at all. HEAD_INK_COVERAGE_MIN  |  |
| staged/adjudicators/header.py:135 | `MARKER_RUN_GAP_SPACES = 2.0` | sp |  | C | ? |  Two slots further apart than this are not one RUN. A signature's accidentals stand about ONE space apart; a mark this far right of the last one is in the first BAR, not  |  |
| staged/adjudicators/header.py:256 | `ORDER_TOL_STEPS = 0.6` | count |  | A | ? |  how far a marker's centre may stand from its slot's fixed step: the positional fitter's `max_residual` (`key_signature_geometry`), after the glyph-anchor offset; both an |  |
| staged/adjudicators/header.py:684 | `CHANGE_MIN_WITNESSES = 2` | count |  | A | DECIDES |  that (`key_signature_corroboration.MIN_WITNESSES`, default ON since 2026-09-07, 7 of 7 spurious flips stopped) and the staged METER mirror asserts equality with it (`rhy |  |
| staged/adjudicators/header.py:709 | `CHANGE_MIN_RUN = 2` | ? |  | C | DECIDES |  number is `part_sim.py --sweep`; the figures are in FINDINGS.md §2.9b. ⚠️ A run of ONE is not "no persistence rule", it is the rule switched off, and the sweep prices th |  |
| staged/adjudicators/notehead_precision.py:154 | `TOO_NARROW_MIN_SPACES = 1.0` | sp |  | C | REFUSES |  `noteheadBlack*`: the FINDINGS' own §6 measures the under-floor count as ZERO for every Half and Whole class on both plates — the contamination there is a class-identity |  |
| staged/adjudicators/notehead_precision.py:1195 | `NOTEHEAD_DUPLICATE_IOU_MIN = 0.02` | count |  | A | REFUSES |  imported: `family_precision` imports FROM this module (`HUMAN_OTHER_STAFF`, `HUMAN_REFUSAL_REASONS`), so the reverse import would be a cycle. A test pins the two constan |  |
| staged/adjudicators/notehead_precision.py:1210 | `NOTEHEAD_DUPLICATE_MAX_DY_STAFF_SPACES = 0.25` | sp |  | C | ? |  mark" and "the closest interval print actually uses"; 0.5 head widths is the matching horizontal half-tolerance. NOT CONFIRMED with Sean; falsified by a real duplicate c |  |
| staged/adjudicators/notehead_precision.py:1211 | `NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS = 0.5` | ? |  | C | ? | NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS = 0.5 |  |
| staged/adjudicators/notehead_precision.py:1265 | `NOTEHEAD_SAME_SIDE_MAX_DY_STAFF_SPACES = 0.75` | sp |  | C | REFUSES |  Halfway between a second (0.5 sp) and a third (1.0 sp), in half-steps: 1.5 half-steps = 0.75 staff spaces. Sean set the boundary ("opposite sides of the stem") rather th |  |
| staged/adjudicators/notehead_precision.py:1602 | `SHAPE_ANGLE_MIN_DEG = 20.0` | ? |  | C | DECIDES |  diagonal reads 44.3°; a horizontal ledger-like stroke reads 0.0°; a vertical stem-like stroke reads 89.2° -- the band is wide because a real slash is drawn at varying st |  |
| staged/adjudicators/notehead_precision.py:1603 | `SHAPE_ANGLE_MAX_DEG = 70.0` | ? |  | C | ? | SHAPE_ANGLE_MAX_DEG = 70.0 |  |
| staged/adjudicators/notehead_precision.py:1616 | `SHAPE_MIN_ELONGATION = 1.8` | ? |  | C | ? |  lowest confirmed real slash and above every confirmed real head measured so far -- a narrower real margin than the synthetic one, which is why CROSSING and POSITION carr |  |
| staged/adjudicators/notehead_precision.py:1624 | `SHAPE_MAX_FILL = 0.55` | ratio |  | B | DECIDES |  diagonal stroke reads 0.22 (a thin stroke drawn inside a box sized to the DETECTOR's extent, not to the stroke's own width, fills much less of it). Set below the head's  |  |
| staged/adjudicators/notehead_precision.py:1640 | `POSITION_MIN_END_RATIO_BOX_HEIGHTS = 0.5` | px |  | E | REFUSES |  centred AT the end it attaches to (distance ~0); a slash sits along the shaft, clearly away from both ends. One box-height is the same unit `NOTEHEAD_DUPLICATE_MAX_DY_ST |  |
| staged/adjudicators/notehead_precision.py:1677 | `NOT_OVAL_ANGLE_MIN_DEG = 10.0` | ? |  | C | REFUSES |  degrees off horizontal. A slash crosses a stem sideways: the confirmed ones read 10.3-34.8; a quarter rest's zigzag reads 64-67 and is not asked. NOT_OVAL_ANGLE_MIN_DEG  |  |
| staged/adjudicators/notehead_precision.py:1678 | `NOT_OVAL_ANGLE_MAX_DEG = 45.0` | ? |  | C | ? | NOT_OVAL_ANGLE_MAX_DEG = 45.0 |  |
| staged/adjudicators/notehead_precision.py:1681 | `NOT_OVAL_MIN_FILL = 0.15` | ratio |  | B | REFUSES |  "thick": a thin slur or beam sliver boxed as a head fills ~0.07; the confirmed slashes fill 0.26-0.55. NOT_OVAL_MIN_FILL = 0.15 |  |
| staged/adjudicators/notehead_precision.py:2020 | `FILLED_CENTER_MIN = 0.9` | ratio | B | D | DECIDES |  A head reads FILLED where every raster reading's centre window is at least this solid -- above Sean's filled Brahms floor (0.85) and below the solid mode (>= 0.95) of bo | * rank 1: D, DECIDES filled; Brahms floor 0.85 (2.73) |
| staged/adjudicators/notehead_precision.py:2403 | `HEAD_SHAPE_MARGIN = 0.15` | sp |  | C | DECIDES |  two differ by less than this -- then the INK decides, as before. 0.15: a box 0.7 sp tall (half a ring) scores about 0.55 against a whole box's 0.9-1.0; neither number is |  |
| staged/adjudicators/notehead_precision.py:2409 | `SAME_HEAD_MAX_GAP_SPACES = 0.15` | sp |  | C | DECIDES |  Two boxes are on ONE head only if they overlap or stand no farther apart than this (staff spaces) in either axis -- the halves of a cut head abut at the line. A box on t |  |
| staged/adjudicators/notehead_precision.py:2415 | `HEAD_CUT_WHOLE_MAX_DY_SPACES = 0.25` | sp |  | A | ? |  A whole detector box on a cut head: its centre lies this near the rebuilt head's centre vertically (a chord's neighbour a second away is 0.5 sp off, and is another head) |  |
| staged/adjudicators/notehead_precision.py:2416 | `HEAD_CUT_PARTIAL_MAX_DY_SPACES = 0.35` | sp |  | C | ? | HEAD_CUT_PARTIAL_MAX_DY_SPACES = 0.35 |  |
| staged/adjudicators/notehead_precision.py:2437 | `PLAUSIBLE_HEAD_WIDTH_SPACES = [0.8, 2.1]` | sp | LB | D | ? |  A box a notehead could be: 0.8-2.1 staff spaces wide, 0.5-1.6 tall. The detector's real heads sit well inside (Brahms and Litolff medians 1.3-1.5 sp wide; the 99th perce | * rank 9: C, REFUSES |
| staged/adjudicators/notehead_precision.py:2438 | `PLAUSIBLE_HEAD_HEIGHT_SPACES = [0.5, 1.6]` | sp |  | C | ? | PLAUSIBLE_HEAD_HEIGHT_SPACES = (0.5, 1.6) |  |
| staged/adjudicators/ownership.py:2358 | `STACK_MAX_GAP_SPACES = 4.0` | sp |  | C | ? |  Two stacked arcs are "one over the other" only if the gap between their boxes is under this many staff spaces. NOT swept; the S6 dose-response (benchmarks/omr-arc-gramma |  |
| staged/adjudicators/ownership.py:2373 | `TALL_BOX_HEAD_HEIGHTS = 1.4` | ? | L | D | NARROWS |  (a second a step apart, merged by a thick scan): its centre is neither head's, so its two head-sized ends are offered as candidate partners. NOT swept; the two tiles Sea |  |
| staged/adjudicators/ownership.py:4299 | `ARTIC_COLUMN_HEAD_WIDTHS = 1.1` | ? |  | C | DECIDES |  ROADMAP 2.12f ROUND 2. Heads within this many NOTEHEAD WIDTHS of one another in x are ONE COLUMN, for deciding whether two voices share it (opposite stems). DERIVED: a s |  |
| staged/adjudicators/rhythm.py:109 | `HEAD_FILL_HOLLOW_CENTER_MAX = 0.75` | ratio | L | D | DECIDES |  0.08-0.84), and on Litolff p3 207 of 228 black-class kept heads read >= 0.95 (`benchmarks/omr-head-fill-2026-09/FINDINGS.md` §8). 0.75 is under both floors; the engraved | * rank 1: D, DECIDES/NARROWS hollow; both plates (18ba26713, 2.73), both sides measured (Sean's Litolff halves 0.51-0.72, Brahms black >= 0.85) |
| staged/adjudicators/rhythm.py:125 | `HEAD_FILL_HOLLOW_RING_GAP_MIN = 0.1` | ratio |  | B | NARROWS |  rather than its hole. This test therefore CANNOT separate a genuine WHOLE head from BLACK by ink alone; it catches the HALF-read-as-BLACK population (which is what §17b' |  |
| staged/adjudicators/rhythm.py:138 | `HEAD_BOX_MAX_SPACES = 1.8` | sp |  | A | REFUSES |  and `glyph/3/0/8/7/8` 2.37), and the genuine hollow heads looked at are 0.8-1.5 spaces. 2.70 DECIDES a half only on a box this tall or less; taller, the ink is not about | * rank 1/9: C, DECIDES a half only on a box <= 1.8 sp; p90 Litolff detector boxes |
| staged/adjudicators/rhythm.py:150 | `HEAD_HOLLOW_MIN_READINGS = 2` | count |  | A | REFUSES |  the hollow reading must hold on at least `HEAD_HOLLOW_MIN_READINGS` of the three rasters, the box must be head-shaped (not a sliver, not a cluster), and the tip must be  |  |
| staged/adjudicators/rhythm.py:158 | `HEAD_RAW_CENTER_FLOOR = 0.2` | ? | B | D | REFUSES |  admitted an alto clef (tile 5: raw centre 0.76 -- thirteen thousandths over the cut -- net 0.56 / off-line 0.52 hollow) and a ledger-line patch (tile 10: centre 0.07 / 0 | * rank 1: D, REFUSES hollow; Sean's 2.88 tiles, thin margin stated (0.013) |
| staged/adjudicators/rhythm.py:159 | `HEAD_RAW_RING_GAP_MIN = 0.15` | count |  | A | ? | HEAD_RAW_RING_GAP_MIN = 0.15 |  |
| staged/adjudicators/rhythm.py:297 | `HEAD_BOX_MIN_SPACES = 0.9` | sp |  | C | ? | HEAD_BOX_MIN_SPACES = 0.9 |  |
| staged/adjudicators/rhythm.py:298 | `HEAD_BOX_MAX_WIDTH_SPACES = 1.9` | sp |  | C | ? | HEAD_BOX_MAX_WIDTH_SPACES = 1.9 |  |
| staged/adjudicators/rhythm.py:3547 | `HEAD_INTERIOR_WHITE_HOLLOW_MIN = 0.18` | count | B | D | NARROWS |  A BLACK-classed head whose middle rows hold white between ink on at least this share is HOLLOW. ⚠️ MEASURED on ONE plate (Sean's Brahms pdf 0 hand truth): filled <= 0.06 | * rank 1: D, DECIDES hollow at the first step; Brahms p0 hand truth only (594e2e1d9, 2.148); filled side 0.06 and hollow side 0.18 both measured, on ONE plate |
| staged/adjudicators/rhythm.py:3548 | `HEAD_INTERIOR_WHITE_FILLED_MAX = 0.06` | ratio |  | B | ? | HEAD_INTERIOR_WHITE_FILLED_MAX = 0.06 | * rank 1: D, DECIDES filled; Brahms p0 only |
| staged/adjudicators/rhythm.py:3551 | `HEAD_FIRST_MIN_WIDTH_SPACES = 1.1` | sp | LB | D | DECIDES |  The narrowest box read as ONE head at the first step (staff spaces). Sean's 2.148 tiles: a key flat (1.06) and a C-clef piece (1.01) were boxed as heads; Litolff halves  | * rank 9: D, REFUSES at the first step; Sean's 2.148 tiles (flat 1.06, C-clef piece 1.01), Litolff 1.43-1.99, Brahms ~1.3 (2e67a790f); Bravura's black head is 1.18 |
| staged/adjudicators/rhythm.py:4054 | `HEAD_FILLED_CENTER_MIN = 0.85` | ratio |  | B | ? | HEAD_FILLED_CENTER_MIN = 0.85 |  |
| staged/adjudicators/stem_value.py:122 | `HOLLOW_BASE_MIN = 2.0` | count |  | A | ? |  The head base (beats, before any beam, flag or dot) at or above which a head is HOLLOW: a half note is 2.0, a whole 4.0, a black head 1.0. HOLLOW_BASE_MIN = 2.0 |  |
| staged/adjudicators/stem_value.py:127 | `WHOLE_BASE = 4.0` | ? |  | C | REFUSES |  The head base of a WHOLE note. RULE, CONFIRMED (Sean, DECISIONS 2026-10-09, tiles 5 and 9: *"Whole notes never have stems"*): no stem carries a head of this base or more |  |
| staged/adjudicators/unboxed_rest.py:83 | `QUARTER_HEAD_BESIDE_SPACES = 1.0` | sp |  | C | REFUSES |  A quarter rest is followed by no notehead this close (0 of 100 standing ones have one within 3 spaces), but an arpeggio line -- the same zigzag -- stands against its cho |  |
| staged/adjudicators/unboxed_rest.py:84 | `QUARTER_HEAD_BESIDE_DY_SPACES = 2.5` | sp |  | C | ? | QUARTER_HEAD_BESIDE_DY_SPACES = 2.5 |  |
| staged/arc_claim.py:491 | `BIND_CHORD_MIN_SPACES = 1.0` | sp |  | A | REFUSES |  two heads of one chord COLUMN stand at least this many staff spaces apart (a third, 2 staff steps): a smaller step is a second, which an engraver sets in two columns (a  |  |
| staged/barline_columns.py:30 | `RULE_FILL_MIN = 0.8` | ratio |  | B | DECIDES |  a column belongs to the rule when its ink fills this share of the staff's span (lines alone ~0.1; a rule ~1.0, a scan's broken one ~0.8) RULE_FILL_MIN = 0.8 |  |
| staged/beam_strokes.py:393 | `STACK_FIRST_SPACES = 1.0` | sp |  | C | ? | STACK_FIRST_SPACES = 1.0 the first level's outer edge lies within this of the tip (a sloped beam's box edge is off by <= 0.5) |  |
| staged/beam_strokes.py:394 | `STACK_GAP_SPACES = 0.75` | sp |  | C | ? | STACK_GAP_SPACES = 0.75 the next level starts within this of the previous level's inner edge (pitch 0.75 sp, gap 0.25) |  |
| staged/beam_strokes.py:638 | `HEAD_OUTLINE_SLACK_SPACES = 0.7` | sp | L | D | REFUSES |  2.318 r5: a vertical piece shorter than a stem (`SHORT_STEM_SPACES`) that stands within this many staff spaces of the head's own extent is the head's outline (a Litolff  |  |
| staged/beam_strokes.py:705 | `CHAIN_THROUGH_HEAD_MAX_GAP_SPACES = 2.0` | sp |  | C | ? | CHAIN_THROUGH_HEAD_MAX_GAP_SPACES = 2.0 |  |
| staged/beam_strokes.py:813 | `FOOT_MAX_PAST_HEAD_SPACES = 0.75` | sp |  | C | ? | FOOT_MAX_PAST_HEAD_SPACES = 0.75 |  |
| staged/beam_strokes.py:815 | `HEAD_AT_END_SLACK_SPACES = 0.3` | sp |  | C | ? |  Another head's ink "sits at" a stem's end where it touches the stroke and its extent holds the end, within this (a head is ~1.2 sp tall). HEAD_AT_END_SLACK_SPACES = 0.3 |  |
| staged/box_kind.py:86 | `HEAD_BLOB_W_SP = [0.9, 1.9]` | sp |  | C | ? | HEAD_BLOB_W_SP = (0.9, 1.9) | * rank 9: C |
| staged/box_kind.py:87 | `HEAD_BLOB_H_SP = [0.7, 1.5]` | sp |  | C | ? | HEAD_BLOB_H_SP = (0.7, 1.5) |  |
| staged/box_kind.py:88 | `HEAD_FILL_MIN = 0.6` | ratio |  | B | ? | HEAD_FILL_MIN = 0.6 |  |
| staged/box_kind.py:89 | `HEAD_ASPECT = [0.9, 2.2]` | ? |  | C | ? | HEAD_ASPECT = (0.9, 2.2) |  |
| staged/box_kind.py:132 | `HOLE_MAX_SP2 = 0.6` | sp | L | D | REFUSES |  a hollow head's hole is at most this big (staff spaces^2 / side): only holes this small are filled -- the paper a beam, two stems and a row of heads enclose is NOT a hea |  |
| staged/box_kind.py:133 | `HOLE_MAX_SIDE_SP = 1.1` | sp |  | C | ? | HOLE_MAX_SIDE_SP = 1.1 |  |
| staged/box_kind.py:368 | `HOLE_W_MAX_SP = 1.3` | sp | L | D | ? |  a piece of a hollow head's hole (a slit or oval, smaller than the head; staff spaces): measured on Litolff halves (probe_holes, 2.252) HOLE_W_MAX_SP = 1.3 |  |
| staged/box_kind.py:369 | `HOLE_H_MAX_SP = 0.9` | sp |  | C | ? | HOLE_H_MAX_SP = 0.9 |  |
| staged/box_kind.py:370 | `HOLE_AREA_SP2 = [0.04, 0.6]` | sp |  | C | ? | HOLE_AREA_SP2 = (0.04, 0.6) |  |
| staged/box_kind.py:373 | `HOLE_LINE_CUT_SP = 0.42` | sp |  | C | ? |  two pieces either side of one staff line, each within this of it (sp), are one slit the line cut (measured: a head on a line leaves its pieces 0.26-0.36 sp from the line |  |
| staged/box_kind.py:375 | `HOLE_SAME_SP = 0.25` | sp |  | C | ? |  two pieces whose centres are this close in height (sp) are one slit HOLE_SAME_SP = 0.25 |  |
| staged/box_kind.py:377 | `HOLE_GRID_TOL_STEPS = 0.35` | count |  | A | ? |  a hole's centre within this many half-steps of a line or space position HOLE_GRID_TOL_STEPS = 0.35 |  |
| staged/box_kind.py:379 | `HOLE_MIN_STEPS = 1.6` | count |  | A | ? |  two heads of one column are at least a third apart (2 half-steps); a second is set in two columns HOLE_MIN_STEPS = 1.6 |  |
| staged/box_kind.py:482 | `HEAD_BOX_H_SP = 1.3` | sp |  | C | DECIDES |  a head box made for a head read off its hole is this tall (staff spaces) unless the cell's one-head boxes say otherwise HEAD_BOX_H_SP = 1.3 |  |
| staged/claims.py:563 | `HEADING_CLEAR_SPACES = 5.0` | sp |  | C | ? |  heading text (title, composer, plate number): ink above the first staff by `HEADING_CLEAR_SPACES`, or below the last by `FOOTER_CLEAR_SPACES` (notes on ledger lines reac |  |
| staged/claims.py:565 | `HEADING_MAX_COMPONENT_SPACES = 8.0` | sp |  | C | ? | HEADING_MAX_COMPONENT_SPACES = 8.0 |  |
| staged/claims.py:566 | `HEADING_JOIN_SPACES = 2.5` | sp |  | C | ? | HEADING_JOIN_SPACES = 2.5 |  |
| staged/clef_pagewide.py:59 | `G_PAST_MIN_FILL = 0.05` | ratio |  | B | ? | G_PAST_MIN_FILL = 0.05 |  |
| staged/clef_pagewide.py:63 | `G_TAIL_MIN_FILL = 0.3` | ratio |  | B | ? | G_TAIL_MIN_FILL = 0.3 |  |
| staged/clef_pagewide.py:70 | `LINE_ROW_MIN_FILL = 0.5` | ratio |  | B | ? | LINE_ROW_MIN_FILL = 0.5 |  |
| staged/clef_pagewide.py:84 | `HEADER_WINDOW_SPACES = 6.0` | sp |  | C | DECIDES |  a clef starting within this many staff spaces of the staff's first cell's left edge is the system's header clef HEADER_WINDOW_SPACES = 6.0 |  |
| staged/consequences.py:1411 | `CLEAN_HEAD_OFF_STAFF_SPACES = 1.6` | sp |  | C | DECIDES |  How far (staff spaces) beyond its outer line a head may stand and still be read as THIS staff's own without ledger evidence. CLEAN_HEAD_OFF_STAFF_SPACES = 1.6 |  |
| staged/consequences.py:1413 | `CLEAN_HEAD_DUPLICATE_IOU = 0.3` | ? |  | C | ? |  Two boxes over the same ink: IoU above this. CLEAN_HEAD_DUPLICATE_IOU = 0.3 |  |
| staged/dyad_head_rescue.py:32 | `FLOOR = 0.05` | ? |  | C | DECIDES |  the detector is read at the stem-end rescue's own floor (one shared run, `_rescue_detect`'s floor_memo) FLOOR = 0.05 |  |
| staged/dyad_head_rescue.py:34 | `CUT = 0.25` | ? |  | C | NARROWS |  the production cut: a candidate at or above it is a production box, not this rescue's CUT = 0.25 |  |
| staged/dyad_head_rescue.py:36 | `STEP_SPACES = 0.4` | sp |  | C | DECIDES |  a step along the stem is half a space; a third is a full space (see the module docstring) STEP_SPACES = 0.4 |  |
| staged/dyad_head_rescue.py:37 | `ALONG_SPACES = 0.9` | sp |  | C | ? | ALONG_SPACES = 0.9 |  |
| staged/dyad_head_rescue.py:39 | `ACROSS_SPACES = 0.9` | sp |  | C | ? |  a displaced second stands about a head's width (1.3 sp) across; 0.9 leaves room for the box's own error ACROSS_SPACES = 0.9 |  |
| staged/dyad_head_rescue.py:41 | `TOUCH_ACROSS_SPACES = 0.9` | sp |  | C | ? |  a boxed head touches a stem when its centre is within this of the stem's x (the stem-end rescue's own window) TOUCH_ACROSS_SPACES = 0.9 |  |
| staged/dyad_head_rescue.py:43 | `TOUCH_ALONG_SPACES = 1.0` | sp |  | C | ? |  ... and its centre is within the stem's span, this far past either end (the stem-end rescue's own window) TOUCH_ALONG_SPACES = 1.0 |  |
| staged/gather.py:7310 | `LINE_ROW_FLANK_FILL = 0.7` | ratio |  | B | ? | LINE_ROW_FLANK_FILL = 0.7 |  |
| staged/gather.py:8331 | `FAMILY_HEAD_GAP_SPACES = 1.0` | sp |  | C | DECIDES |  A notehead to the right of an accidental-family mark, at most this many staff spaces away (box edge to box edge), whose centre stands within `FAMILY_HEAD_DY_STEPS` half- |  |
| staged/gather.py:8332 | `FAMILY_HEAD_DY_STEPS = 1.0` | count |  | A | ? | FAMILY_HEAD_DY_STEPS = 1.0 |  |
| staged/gather.py:9701 | `RECENTRE_MIN_FILL = 0.55` | ratio |  | B | NARROWS |  rather than guess (rule 8): a thin stem fills a head-sized window only ~15-20%, and a hollow head's own interior reads comparably sparse, so neither should be read as "t |  |
| staged/gather.py:9969 | `RECENTRE_PART_HOLLOW_FLOOR = 0.2` | ? |  | C | REFUSES |  ... and a BLANK window is not a hollow reading (2.88's `HEAD_RAW_CENTER_FLOOR`, restated for the same reason): under this the box is not on a head at all and may be move |  |
| staged/gather.py:10188 | `HEAD_CUT_MAX_BOX_HEIGHT_SPACES = 0.95` | sp | B | D | NARROWS |  `STANDARD_HEAD_HEIGHT_SPACES` (1.1); the cut halves measured on Brahms 317803 pdf 0 are 0.58-0.89 sp, and the detector's whole boxes on Sean's space heads 1.06-1.31. Bet |  |
| staged/gather.py:10190 | `HEAD_CUT_MIN_BOX_WIDTH_SPACES = 0.9` | sp |  | C | ? |  ... and at least this wide: a half-ring is as wide as the head. HEAD_CUT_MIN_BOX_WIDTH_SPACES = 0.9 |  |
| staged/gather.py:10192 | `HEAD_CUT_EDGE_ON_LINE_SPACES = 0.3` | sp |  | C | ? |  The box edge must lie within this of the line's centre (staff spaces). HEAD_CUT_EDGE_ON_LINE_SPACES = 0.3 |  |
| staged/gather.py:10194 | `HEAD_CUT_WINDOW_HALF_WIDTH_SPACES = 0.9` | sp |  | C | ? |  The search window around the box's centre, in staff spaces. HEAD_CUT_WINDOW_HALF_WIDTH_SPACES = 0.9 |  |
| staged/gather.py:10195 | `HEAD_CUT_WINDOW_HALF_HEIGHT_SPACES = 1.0` | sp |  | C | ? | HEAD_CUT_WINDOW_HALF_HEIGHT_SPACES = 1.0 |  |
| staged/gather.py:10198 | `HEAD_CUT_HOLE_AREA_SPACES2 = [0.02, 0.45]` | sp |  | C | ? |  A half-hole: enclosed white, between these areas (staff spaces squared) and no bigger than this in either extent (a head's whole hole is ~0.2 sp^2). HEAD_CUT_HOLE_AREA_S |  |
| staged/gather.py:10199 | `HEAD_CUT_HOLE_MAX_WIDTH_SPACES = 0.95` | sp |  | C | ? | HEAD_CUT_HOLE_MAX_WIDTH_SPACES = 0.95 |  |
| staged/gather.py:10200 | `HEAD_CUT_HOLE_MAX_HEIGHT_SPACES = 0.7` | sp |  | C | ? | HEAD_CUT_HOLE_MAX_HEIGHT_SPACES = 0.7 |  |
| staged/gather.py:10202 | `HEAD_CUT_AREA_RATIO = [0.4, 2.5]` | ratio |  | B | ? |  The two holes are alike in size ... HEAD_CUT_AREA_RATIO = (0.4, 2.5) |  |
| staged/gather.py:10204 | `HEAD_CUT_HOLE_SEPARATION_SPACES = [0.25, 1.1]` | sp |  | C | ? |  ... stand this far apart vertically (their centres) ... HEAD_CUT_HOLE_SEPARATION_SPACES = (0.25, 1.1) |  |
| staged/gather.py:10207 | `HEAD_CUT_MAX_DX_SPACES = 0.5` | sp |  | C | ? |  ... and their common centre lies this near the detector box's own centre horizontally. HEAD_CUT_MAX_DX_SPACES = 0.5 |  |
| staged/gather.py:10213 | `HEAD_CUT_LINE_BAND_SPACES = [0.78, 0.98]` | sp |  | C | DECIDES |  pair's centre (staff spaces from it), on the line's own rows. A ledger line runs past the head; a slash or a stem does not. The longer side must read at least the first  |  |
| staged/gather.py:10214 | `HEAD_CUT_LINE_FILL = [0.75, 0.4]` | ratio |  | B | ? | HEAD_CUT_LINE_FILL = (0.75, 0.4) |  |
| staged/gather.py:10390 | `NOTEHEAD_INK_CENTER_SHRINK = 0.3` | ? |  | A | REFUSES |  empty for a HOLLOW one (half/whole) by construction — which is exactly why `center` alone must never gate a refusal (`ring` is the hollow head's own witness). ROADMAP 2. |  |
| staged/gather.py:10554 | `HEAD_LINE_ROW_BAND_SPACES = [0.78, 0.98]` | sp | B | D | DECIDES |  staff spaces either side of the head's centre, at least this fraction in each. A staff or ledger line through a hollow head's hole reads as fill on every window that inc |  |
| staged/gather.py:10555 | `HEAD_LINE_ROW_FILL = 0.6` | ratio |  | B | ? | HEAD_LINE_ROW_FILL = 0.6 |  |
| staged/gather.py:10558 | `HEAD_LINE_ROWS_MAX_LOST = 0.5` | ? |  | C | NARROWS |  ... and a head whose box loses more than this fraction of its rows to lines has no window left to read: declined, never defaulted. HEAD_LINE_ROWS_MAX_LOST = 0.5 |  |
| staged/gather.py:10909 | `STACKED_HEAD_MIN_GAP_POSITIONS = 2` | sp |  | C | DECIDES |  in staff spaces; this is the position-unit form the fit's integer grid needs, restated (not imported -- `notehead_precision` imports THIS module, so the reverse import w |  |
| staged/gather.py:10919 | `STACKED_HEAD_FIT_MARGIN = 0.05` | ? |  | C | NARROWS |  margin discipline `Q.NOTEHEAD_RECENTRE`'s own `RECENTRE_MIN_MARGIN` uses for an analogous "is the winner clearly ahead" test, not independently fitted here. Where two co |  |
| staged/gather.py:10955 | `STACKED_BLOB_HALF_WIDTH_SPACES = 0.28` | sp |  | C | DECIDES |  Half width of the column band read for the blob's height, in staff spaces either side of the heads' x -- 0.2 of the standard head width, the middle of the head, clear of |  |
| staged/gather.py:10958 | `STACKED_BLOB_ROW_FILL = 0.3` | px |  | E | ? |  A row is blob ink where this fraction of the band's pixels are ink. STACKED_BLOB_ROW_FILL = 0.3 |  |
| staged/gather.py:10962 | `STACKED_BLOB_BRIDGE_SPACES = 0.2` | sp |  | C | ? |  A gap of this many spaces inside the blob is bridged (the tangent between two touching ellipses; a staff-line removal that cut a head across). STACKED_BLOB_BRIDGE_SPACES |  |
| staged/gather.py:10972 | `STACKED_BLOB_MIN_FRACTION = 0.8` | ratio | B | D | DECIDES |  so a 1.8 cut calibrated on the page lost 3 of the 5 -- and the pairs that are not two heads read 0.6-1.3 on the page. A head with a ledger line or a slur touching it rea |  |
| staged/gather.py:10980 | `STACKED_BOX_SPREAD_MIN_POSITIONS = 1.5` | count | B | D | NARROWS |  the twins' boxes read 1.89-2.12 apart, the two false near-misses on Brahms pdf 1 -- one head boxed twice, plus a ledger line -- 0.38 and 0.40). The first witness: the fi |  |
| staged/gather.py:10988 | `STACKED_BLOB_WINDOW_SPACES = 2.5` | sp |  | C | DECIDES |  How far above and below the pair's midpoint the column is read (spaces). STACKED_BLOB_WINDOW_SPACES = 2.5 |  |
| staged/gather.py:11011 | `STACKED_HEAD_BOX_STEP_POSITIONS = 1.0` | ? | L | D | ? |  stands on. Measured on the Litolff 20261029-night sample pages (benchmarks/ acceptance FINDINGS 2026-10-30, 2.232): of 141 hollow k=1 groups 22 sit at >= 1.0, of 48 fill |  |
| staged/gather.py:11063 | `STACKED_HOLLOW_CENTER_MAX = 0.75` | count |  | A | DECIDES |  `rhythm.HEAD_FILL_HOLLOW_CENTER_MAX` / `HEAD_FILL_HOLLOW_RING_GAP_MIN` (2.23), restated (`rhythm` imports this module): a slot reads hollow where the interior is no dens |  |
| staged/gather.py:11064 | `STACKED_HOLLOW_RING_GAP_MIN = 0.1` | count |  | A | ? | STACKED_HOLLOW_RING_GAP_MIN = 0.10 |  |
| staged/gather.py:11067 | `STACKED_HOLLOW_RING_MIN = 0.55` | count |  | A | DECIDES |  ... and the ring is real ink, not paper: the 19 pairs read 0.58-0.78 at their slots, a slot moved a half-step reads 0.2-0.5. STACKED_HOLLOW_RING_MIN = 0.55 |  |
| staged/gather.py:11074 | `STACKED_HOLLOW_MAX_SPREAD_POSITIONS = 3.0` | ? |  | C | REFUSES |  The group's own boxes: lowest to highest at most this many half-steps apart (a third is 2; a chord of THREE heads is 4 and is not a pair). STACKED_HOLLOW_MAX_SPREAD_POSI |  |
| staged/geometry.py:39 | `STANDARD_HEAD_WIDTH_SPACES = 1.4` | sp |  | C | ? |  See this module's own docstring for the measurement and its scope. STANDARD_HEAD_WIDTH_SPACES = 1.4 |  |
| staged/geometry.py:40 | `STANDARD_HEAD_HEIGHT_SPACES = 1.1` | sp |  | C | ? | STANDARD_HEAD_HEIGHT_SPACES = 1.1 |  |
| staged/head_extent.py:32 | `MAX_PASSES = 4` | sp |  | B | ? |  How many times the trimmed extent is fed back as the seed (each pass reaches 0.45 sp past the last). MAX_PASSES = 4 |  |
| staged/head_extent.py:40 | `BOUNDARY_STEPS = 0.15` | count |  | A | DECIDES |  r2 (Sean's tile 7, -2.50 -> -2.51): an ink centre this close (in steps) to the half-way point between two positions decides nothing -- never flip on a coin toss. BOUNDAR |  |
| staged/head_extent.py:44 | `MIN_KEPT_SPACES = 0.6` | sp |  | C | ? | MIN_KEPT_SPACES = 0.6 |  |
| staged/head_hole_position.py:31 | `REACH_SPACES = 0.25` | sp |  | C | REFUSES |  how far past the box's top and bottom (staff spaces) a hole's centre may stand (a clipped box can stop at the hole) REACH_SPACES = 0.25 |  |
| staged/head_hole_position.py:75 | `ONE_HEAD_TALL_SPACES = 1.35` | sp |  | B | DECIDES |  r5: a head's own ink at most this tall (staff spaces) is ONE head even where an arc's end makes it too wide (2.248's own cut-off) ONE_HEAD_TALL_SPACES = 1.35 |  |
| staged/head_ink.py:40 | `SLACK_SPACES = 0.5` | sp |  | C | ? |  How far past the detector's box the head's ink is looked for (a box drawn off its own head, 2.115's part-boxed heads). SLACK_SPACES = 0.5 |  |
| staged/head_ink.py:44 | `ROW_REACH_SPACES = 2.0` | sp |  | C | ? |  How far above / below the box the crop reaches (the staff-line window and the slack rows fit inside it). ROW_REACH_SPACES = 2.0 |  |
| staged/head_ink.py:48 | `ROW_SLACK_SPACES = 0.45` | sp |  | C | DECIDES |  ... read in the box's rows widened by this each way (2.115's tile 13: a box on the upper rim alone, the head 0.3 sp lower; a stack's next head is then clipped, fix C). R |  |
| staged/head_ink.py:55 | `MAX_WIDTH_SPACES = 1.75` | sp | L | D | NARROWS |  Fix A: ONE head's ink is at most this wide / tall, and at least `MIN_SPACES` both ways (filed with its margin; the consumer cuts). A CUT-OFF MEASURED ON OUR TWO PLATES ( |  |
| staged/head_ink.py:56 | `MAX_HEIGHT_SPACES = 1.5` | sp |  | C | ? | MAX_HEIGHT_SPACES = 1.5 |  |
| staged/head_ink.py:57 | `MIN_SPACES = 0.6` | sp |  | C | ? | MIN_SPACES = 0.6 |  |
| staged/head_ink.py:59 | `STACK_CLIP_SPACES = 0.15` | sp |  | C | ? |  Fix C: the clip around a head-sized box's own rows when its column is two heads tall. STACK_CLIP_SPACES = 0.15 |  |
| staged/head_ink.py:66 | `SLIT_HOLLOW_MIN = 0.18` | count |  | A | ? |  2.148's cuts on the slit (`rhythm.HEAD_INTERIOR_WHITE_HOLLOW_MIN` / `_FILLED_MAX`), restated only for the producer's own margin. SLIT_HOLLOW_MIN = 0.18 |  |
| staged/head_ink.py:67 | `SLIT_FILLED_MAX = 0.06` | ratio |  | B | ? | SLIT_FILLED_MAX = 0.06 |  |
| staged/head_ink.py:85 | `MAX_HEIGHT_SPACES_V2 = 1.6` | sp | L | D | ? |  Head-trim fix 2 (2026-10-29, default ON, Sean "Let's go with 1.6 for now"; explicit 0/false/no/off disables; needs `OMR_HEAD_TRIM_LINE_ONLY` too): the height cap of a he | * rank 9 (cap): D, Sean 'Let's go with 1.6 for now' (4f886f509) |
| staged/head_oval.py:43 | `HEAD_TALL_SPACES = 0.5` | sp |  | C | ? |  A head's top and bottom edges stand ~0.9-1.0 sp apart; a column across its middle spans at least half a space. A tie stroke is ~0.1-0.3 sp thick. (The head's own size, h |  |
| staged/head_oval.py:48 | `SLACK_SPACES = 0.25` | sp |  | C | DECIDES |  How far past the detector's box the columns and rows are read (a box drawn a little off its own head). SLACK_SPACES = 0.25 |  |
| staged/head_oval.py:53 | `LEFT_EDGE_SPACES = 0.5` | sp |  | C | ? |  The box at a bar's left edge: it starts within this many staff spaces of the cell's left edge (2.160's geometry). LEFT_EDGE_SPACES = 0.5 |  |
| staged/meter_object.py:42 | `MERGED_FILL_MIN = 0.4` | px | L | D | ? |  ink pixels / box pixels of a fused pair (measured Litolff 2/4: 0.66; flats 0.46, stemmed notes ~0.2) MERGED_FILL_MIN = 0.4 | * rank 8: D, DECIDES a fused pair; Litolff 2/4 0.66 (d39014b4b, 2.177) |
| staged/one_chord.py:33 | `SECOND_DX = [0.7, 1.35]` | ? |  | C | DECIDES |  Centre-to-centre horizontal offset of a second's heads, in head widths (a second's heads touch side by side: 1.0; boxes are ~+-0.3 loose). Below the low end the x groupi |  |
| staged/one_chord.py:35 | `SECOND_DY = [0.3, 0.8]` | ? |  | C | ? |  Centre-to-centre vertical offset, in head heights: one step is half a staff space, a head is about one space tall. SECOND_DY = (0.3, 0.8) |  |
| staged/page_accidental_ink.py:54 | `HEAD_GAP_MAX_SP = 3.6` | sp |  | C | DECIDES |  the notehead box that is the note an accidental is BY: its left edge stands at most this far right of the cluster's right edge (spaces) -- a chord's third column of acci |  |
| staged/page_accidental_ink.py:55 | `HEAD_DY_MAX_SP = 3.1` | sp |  | C | ? | HEAD_DY_MAX_SP = 3.1 |  |
| staged/page_accidental_ink.py:64 | `REAL_HEAD_CONF = 0.5` | conf |  | C | NARROWS |  a notehead box at least this confident holds a REAL head: its blob strokes are a head's, never an accidental's bowl. A box under it (the five sharps: 0.25-0.46) holds no |  |
| staged/page_accidental_ink.py:84 | `SOLID_HEAD_AREA_SP2 = 0.9` | ? |  | C | DECIDES |  a solid blob this large and this filled is a head, whatever box stands on it (an accidental's bowl is a ring; page_heads.HEAD_MIN_AREA_SP2 is 0.25) SOLID_HEAD_AREA_SP2 = |  |
| staged/page_accidental_ink.py:85 | `SOLID_HEAD_FILL = 0.8` | ratio |  | B | ? | SOLID_HEAD_FILL = 0.8 |  |
| staged/page_arc_bind.py:64 | `END_BEYOND_HEAD_SPACES = 2.0` | sp | L | D | NARROWS |  (cause d, FINDINGS) the end stands more than this many spaces on the arc's own side of the head it bound to (Litolff p4 runs 1, 12, 20, 99: the head nearest the ink was  | * rank 12: D, REFUSES; Litolff p4 runs |
| staged/page_arc_bind.py:67 | `HEAD_BEHIND_END_SPACES = 1.6` | sp | B | D | NARROWS |  (cause d, FINDINGS) the ink of an arc often ends PAST its note's centre (on the head's far edge, a stem): Brahms p5 runs 14 and 86 ended 1.1 spaces past the centre of th | * rank 12: D; Brahms p5 runs |
| staged/page_arc_bind.py:109 | `MEET_NEAR_HEAD_SPACES = 1.0` | sp |  | C | ? | MEET_NEAR_HEAD_SPACES = 1.0 |  |
| staged/page_arcs.py:62 | `MAX_CHORD_DEG = 40.0` | ? |  | C | ? | MAX_CHORD_DEG = 40.0 |  |
| staged/page_arcs.py:67 | `HOLE_MIN_SP = 0.1` | sp |  | C | DECIDES | HOLE_MIN_SP = 0.1 a gap between two inked columns at least this wide is a bridged hole |  |
| staged/page_arcs.py:68 | `HOLE_PAD_SP = 0.3` | sp |  | C | ? | HOLE_PAD_SP = 0.3 the jag is not measured this close to a hole |  |
| staged/page_arcs.py:115 | `HEADER_INK = 1` | ? |  | C | ? | HEADER_INK = 1 r3: a run hugs a header claim by the claimed INK, not the claim's rectangle |  |
| staged/page_arcs.py:151 | `HEADER_BOX_NEEDS_CLAIM = 1` | ? |  | C | ? | HEADER_BOX_NEEDS_CLAIM = 1 r10 (2.305): a detector clef / key / meter box blanks ink only where a page-wide header claim holds it (blank_mask) |  |
| staged/page_heads.py:59 | `HEAD_MIN_AREA_SP2 = 0.25` | sp |  | C | ? |  a head-shaped blob (`stroke_owner` HEAD_*): area at least this (sp^2) and at most this wide / tall (sp) HEAD_MIN_AREA_SP2 = 0.25 |  |
| staged/page_heads.py:60 | `HEAD_MAX_W_SP = 3.0` | sp |  | C | ? | HEAD_MAX_W_SP = 3.0 |  |
| staged/page_heads.py:61 | `HEAD_MAX_H_SP = 1.6` | sp |  | C | ? | HEAD_MAX_H_SP = 1.6 |  |
| staged/page_heads.py:487 | `HEAD_INK_MIN_SP2 = 0.1` | sp |  | C | ? |  a notehead box holding less head ink than this (sp^2) stands on no head: a tenth of a filled head (~1.0 sp^2, `stroke_owner.HEAD_MIN_AREA_SP2` doc) HEAD_INK_MIN_SP2 = 0. |  |
| staged/page_heads.py:494 | `OVAL_DX_SP = 0.65` | sp |  | A | REFUSES |  ... and the centres of their head ink lie inside one oval (staff spaces): across, half a head's width (~1.3 sp); along, under a THIRD (1 sp). A convention, not a cut tun |  |
| staged/page_heads.py:495 | `OVAL_DY_SP = 0.75` | sp |  | C | ? | OVAL_DY_SP = 0.75 |  |
| staged/page_heads.py:497 | `ANCHOR_MAX_DY_SP = 0.9` | sp |  | C | ? |  two boxes on one head-sized stroke are one head unless their ink centres stand a third apart (then the stroke holds two heads' pieces) ANCHOR_MAX_DY_SP = 0.9 |  |
| staged/page_heads.py:504 | `OVAL_W_SP = 1.3` | sp |  | C | ? |  a printed head's size (sp), for the oval where the trim cannot cut one head out (`stroke_owner`: "a notehead ~1.3 x 1.0") OVAL_W_SP = 1.3 |  |
| staged/page_heads.py:505 | `OVAL_H_SP = 1.0` | sp |  | C | ? | OVAL_H_SP = 1.0 |  |
| staged/page_heads.py:507 | `HOLLOW_PIECE_MAX_LEN_SP = 1.6` | sp |  | C | DECIDES |  a THIN horizontal no longer than this is a hollow head's top or bottom (a head ~1.3 sp wide; a ledger rung sticks out both sides, ~2 sp) HOLLOW_PIECE_MAX_LEN_SP = 1.6 |  |
| staged/page_heads.py:509 | `HOLLOW_PIECE_MAX_W_SP = 1.9` | sp |  | C | ? |  ... and its box no wider than a head can print (`head_ink.MAX_WIDTH_SPACES` 1.75, plus the anti-alias edge) HOLLOW_PIECE_MAX_W_SP = 1.9 |  |
| staged/page_heads.py:511 | `BLOB_MIN_SIDE_SP = 0.3` | sp |  | C | DECIDES |  a blob's shorter side must be at least this (sp): thinner is a stem piece BLOB_MIN_SIDE_SP = 0.3 |  |
| staged/page_heads.py:518 | `OTHER_HEAD_MAX = 0.2` | count |  | B | ? |  ... and no other head's oval holds this share of it (fused with another head: plan step 5) OTHER_HEAD_MAX = 0.2 |  |
| staged/page_heads.py:526 | `BOX_CENTRES_A_THIRD_SP = 0.9` | sp |  | C | DECIDES |  heads stand either side of the stem (page-facts, Sean 2026-10-26); a twin box is the detector's second drawing of ONE head and is off it by less (measured: the farthest  |  |
| staged/page_heads.py:548 | `TRIM_CENTRES_APART_SP = 0.8` | sp | L | D | ? |  the same ink: on the five sample pages the 8 groups whose boxes write different pitches have member centres within 0.1 sp of one another. Members on TWO printed heads tr |  |
| staged/page_heads.py:549 | `TRIM_CENTRES_APART_X_SP = 0.9` | sp |  | C | ? | TRIM_CENTRES_APART_X_SP = 0.9 |  |
| staged/page_heads.py:550 | `CUT_THROUGH_CONTACT_MIN_SP = 0.9` | sp |  | C | ? | CUT_THROUGH_CONTACT_MIN_SP = 0.9 |  |
| staged/page_heads.py:551 | `CUT_THROUGH_CONTACT_MAX_SP = 1.7` | sp |  | C | ? | CUT_THROUGH_CONTACT_MAX_SP = 1.7 |  |
| staged/page_ledger.py:49 | `WHOLE_VIEW_MIN = 0.8` | sp | L | D | REFUSES |  a cell SEES a page stroke WHOLE when its piece holds at least this share of the page stroke's ink: where some cell sees it whole, only the whole views' claims are pooled |  |
| staged/page_owner.py:83 | `HEAD_BOX_MAX_W_SP = 3.0` | sp |  | C | NARROWS |  inward along x, and the rows either side), measured in the head's staff spaces; a head on the wrong side of the curve is no candidate (an arc is OVER its notes, page-fac |  |
| staged/rest_ink.py:40 | `BLOB_WIDTH_SP = 0.7` | sp |  | C | DECIDES | BLOB_WIDTH_SP = 0.7 a row where it is at least this wide is a "solid" row |  |
| staged/second_hollow.py:35 | `SAME_HEAD_IOU = 0.3` | ? |  | A | REFUSES |  Two boxes are the same head at or above this overlap (IoU, canonical frame) -- the cut `readout.match_glyphs` and the 2.110 scorers use. A convention of the scorer, not  |  |
| staged/stem_end_heads.py:248 | `HEAD_WIDTH_SPACES = 1.3` | sp |  | A | ? |  the convention's head (benchmarks/omr-notehead-width-2026-09: 1.3-1.4 sp wide, one space tall); the seed only -- the ink trims it HEAD_WIDTH_SPACES = 1.3 |  |
| staged/stem_end_heads.py:249 | `HEAD_HEIGHT_SPACES = 1.0` | sp |  | C | ? | HEAD_HEIGHT_SPACES = 1.0 |  |
| staged/stem_strokes.py:41 | `END_IN_HEAD_SLACK_SPACES = 0.3` | sp |  | C | ? | END_IN_HEAD_SLACK_SPACES = 0.3 |  |
| staged/stroke_map.py:133 | `HEAD_HEIGHT_CAP_SPACES = 1.6` | sp |  | C | DECIDES |  the height cap of ONE head (`head_ink.MAX_HEIGHT_SPACES_V2`, 2.220 fix 2, Sean "1.6"; a test pins that they are equal) and its width cap (`head_ink.MAX_WIDTH_SPACES`): a |  |
| staged/stroke_map.py:134 | `HEAD_WIDTH_CAP_SPACES = 1.75` | sp |  | C | ? | HEAD_WIDTH_CAP_SPACES = 1.75 |  |
| staged/stroke_map.py:136 | `HEAD_MIN_WIDTH_SPACES = 0.8` | sp |  | C | ? |  a stack is at least a head wide (a black head is >= 1.0 sp wide; a bracket's or thick barline's line <= 0.7) and at most four heads tall HEAD_MIN_WIDTH_SPACES = 0.8 |  |
| staged/stroke_map.py:137 | `STACK_MAX_SPACES = 5.0` | sp |  | C | ? | STACK_MAX_SPACES = 5.0 |  |
| staged/stroke_map.py:142 | `STACK_NOTCH_SPACES = 0.12` | sp |  | C | ? |  ... or at a row where one edge steps in by at least this from both ovals' extremes (a notch; ~2 reduced px, above the +-1 px scan edge) STACK_NOTCH_SPACES = 0.12 |  |
| staged/stroke_map.py:144 | `STACK_BAND_MIN_SPACES = 0.8` | sp |  | C | REFUSES |  each band of a cut stack is at least this tall: a head (~1 sp), never a rung with the top of a head (2.239 tile 9, Sean "ledger line") STACK_BAND_MIN_SPACES = 0.8 |  |
| staged/stroke_map.py:146 | `STACK_EDGE_PAD_SPACES = 0.3` | sp |  | C | REFUSES |  the oval edges of a stack are read on the cell's ink this far beside the part (the opening drops a notched column to the remainder) STACK_EDGE_PAD_SPACES = 0.3 |  |
| staged/stroke_map.py:148 | `HEAD_BODY_SPACES = 0.55` | sp |  | C | ? |  head/arc: a disk this wide survives in a head's body (a black head is ~1 sp tall) and not in a tie or slur (<= `CURVE_MAX_THICK_SPACES`) HEAD_BODY_SPACES = 0.55 |  |
| staged/stroke_map.py:149 | `HEAD_BODY_MIN_SP2 = 0.4` | ? |  | C | ? | HEAD_BODY_MIN_SP2 = 0.4 |  |
| staged/stroke_map.py:160 | `HEAD_EDGE_PAD_SPACES = 0.3` | sp |  | C | ? |  ... and lies no further than this outside the head part's box (the oval's edge columns; a dot stands clear of the head) HEAD_EDGE_PAD_SPACES = 0.3 |  |
| staged/stroke_owner.py:174 | `HEAD_MAX_W_SP = 3.0` | sp |  | C | ? |  ── the shapes ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── HEAD_MAX_W_SP = 3.0 a head 1.3 |  |
| staged/stroke_owner.py:175 | `HEAD_MAX_H_SP = 1.6` | sp |  | C | ? | HEAD_MAX_H_SP = 1.6 |  |
| staged/stroke_owner.py:176 | `HEAD_MIN_AREA_SP2 = 0.25` | sp |  | C | ? | HEAD_MIN_AREA_SP2 = 0.25 a filled head ~1.0 sp^2; a hollow head's ring ~0.5 |  |
| staged/stroke_owner.py:177 | `HEAD_CLUSTER_MAX_H_SP = 3.4` | sp |  | C | ? | HEAD_CLUSTER_MAX_H_SP = 3.4 up to three heads of a chord stacked a step apart (~1 sp each, overlapping) |  |
| staged/stroke_owner.py:475 | `HEAD_BODY_THICK_SP = 0.55` | sp |  | B | REFUSES |  * a BLOB whose median run is a head's body (`HEAD_BODY_THICK_SP`, the stroke map's `HEAD_BODY_SPACES`: a disk a head holds and a tie or an accidental's line does not) th |  |
| time_signature_locator.py:206 | `TimeSignatureLocatorConfig.cut_stroke_min_fill = 0.75` | ratio |  | B | ? | cut_stroke_min_fill: float = 0.75 |  |
| time_signature_locator.py:240 | `TimeSignatureLocatorConfig.bar_head_half_floor = 0.5` | ? |  | C | ? | bar_head_half_floor: float = 0.50 |  |

## staff/system/barline (148; A 10, B 29, C 81, D 16, E 9, n/a 3)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| direction_text.py:520 | `BASELINE_SPLIT_GAP_SPACES = 0.25` | sp |  | C | ? | BASELINE_SPLIT_GAP_SPACES = 0.25 |  |
| direction_text.py:521 | `BASELINE_SPLIT_DROP_SPACES = 0.55` | sp |  | C | ? | BASELINE_SPLIT_DROP_SPACES = 0.55 |  |
| direction_text.py:1062 | `THROUGH_LINE_V_SPACES = 2.0` | sp | L | D | NARROWS |  letter can lie ON the line (Litolff p9: the `p` of `pizz.` stands on a barline and went with it, `pizz.` -> '222'), so the cleaned crop is only ever a RETRY for a candid |  |
| direction_text.py:1063 | `THROUGH_LINE_H_SPACES = 3.0` | sp |  | C | ? | THROUGH_LINE_H_SPACES = 3.0 |  |
| direction_text.py:1145 | `TIGHT_MARGIN_SPACES = 1.0` | sp |  | C | ? | TIGHT_MARGIN_SPACES = 1.0 |  |
| hairpin_detection.py:86 | `MAX_OUTLINE_RMS_SPACES = 0.1` | sp |  | C | ? |  ...and both outlines must fit a straight line this closely. MAX_OUTLINE_RMS_SPACES = 0.10 |  |
| hairpin_detection.py:282 | `REACH_OUTLINE_TRIM = 0.15` | sp | B | D | REFUSES |  ROADMAP 2.254: a long hairpin on a scan is straight but not ruler-straight, and the rejoin can glue a dot or a letter's serif to one end -- the plain rms over every colu |  |
| hairpin_detection.py:332 | `REACH_LINE_SPACES = 1.5` | sp |  | C | ? |  ROADMAP 2.254, the second cause: a SLUR (or a ledger-lined head) that touches a hairpin arm makes one component of both. Keeping only ink that lies along a straight, nea |  |
| hairpin_detection.py:333 | `REACH_LINE_MAX_DEG = 15.0` | ? |  | C | ? | REACH_LINE_MAX_DEG = 15.0 |  |
| hairpin_detection.py:334 | `REACH_LINE_STEP_DEG = 3.0` | ? |  | C | ? | REACH_LINE_STEP_DEG = 3.0 |  |
| hairpin_detection.py:337 | `REACH_LINE_MIN_W_SP = 4.0` | sp | LB | D | ? |  ...trusted only for a find at least this long (Litolff p16: a fermata and an 'ff' made straight-edged at 3.2-3.4 sp; the Brahms hairpins only the straight-run pass finds | * rank 13: D, REFUSES; Litolff p16 + Brahms |
| header_ink.py:438 | `LINE_ONLY_HEIGHT_MULT = 2.0` | ? |  | C | REFUSES |  count as the bare line. A notehead or stem sitting on the line makes a run many times taller — but `_run_extent` stops at the search window, so some arrive CLIPPED to a  |  |
| line_detection.py:59 | `LineDetection.confidence = 1.0` | ? |  | C | ? | confidence: float = 1.0 classical CV is deterministic; conf is arbitrary |  |
| measure_extractor.py:37 | `CANONICAL_STAFF_SPAN_PX = 400` | px |  | C | ? |  Canonical sizing for extracted measure cells. Plan calls for "as high as possible": ~400px staff span, ~2048px max cell width. CANONICAL_STAFF_SPAN_PX = 400 |  |
| measure_extractor.py:38 | `MAX_CELL_WIDTH_PX = 2048` | px |  | E | ? | MAX_CELL_WIDTH_PX = 2048 |  |
| measure_extractor.py:44 | `PAD_ABOVE_STAFF_LINES = 4` | ? |  | C | ? |  Padding around a measure cell (in units of staff line spacing — so it scales with score size). Above the staff: ledger lines / dynamics. Below the staff: ledger lines /  |  |
| measure_extractor.py:45 | `PAD_BELOW_STAFF_LINES = 4` | ? |  | C | ? | PAD_BELOW_STAFF_LINES = 4 |  |
| measure_extractor.py:66 | `PAD_MAX_STAFF_LINES = 6` | ? |  | C | ? |  small change in it moves DETECTIONS, not just the crop. Measured: growing the authored `ensemble` fixture's pad from 4.0 to 4.6 spaces, because its staves happen to sit  |  |
| measure_extractor.py:70 | `CELL_NEIGHBOUR_CLEARANCE_SPACES = 0.5` | sp |  | C | ? |  How close a grown cell may come to the NEIGHBOURING staff's nearest line. Half a space clears a printed line and its wander at every DPI measured here. CELL_NEIGHBOUR_CL |  |
| measure_extractor.py:78 | `BARLINE_MIN_HEIGHT_FRAC = 0.8` | ratio |  | B | ? |  - covers at least BARLINE_MIN_HEIGHT_FRAC × staff_span - is thinner than BARLINE_MAX_WIDTH_LINESPACINGS × line spacing This filters out note stems (too short), beams (wr |  |
| measure_extractor.py:91 | `BARLINE_MAX_WIDTH_LINESPACINGS = 0.7` | ? |  | C | REFUSES |  proper fix needs cross-staff-system connectivity analysis, not a single threshold. Sticking with 0.80 for now and using the `phase1_warning` flag on outlier-wide cells ( |  |
| measure_extractor.py:92 | `BARLINE_MIN_DISTANCE_PX = 60` | px |  | E | ? | BARLINE_MIN_DISTANCE_PX = 60 neighbouring barlines must be ≥60px apart | * rank 17: E, REFUSES a second barline within 60 PAGE px; first commit 19caa533d 2026-05-14, never scaled |
| measure_extractor.py:98 | `SPAN_TOUCH_TOLERANCE_PX = 6` | px |  | E | NARROWS |  staff band's actual top/bottom edge to count as "spans the staff" in `_dedup_barline_candidates(prefer="spanning")` — a real barline is drawn to the line, not a fraction | * rank 17: E, DECIDES spanning; page px |
| measure_extractor.py:104 | `SPAN_MIN_INK = 0.9` | ? |  | C | REFUSES |  How much of the weakest band of a column must be ink before it counts as spanning the system (`_spans_system`). Measured over four braced piano systems of WTC I: every r | * rank 17: C, DECIDES; measured on WTC (engraved) |
| measure_extractor.py:133 | `VOTE_REGULARITY_FRACTION = 0.65` | ratio |  | B | ? |  majority already established. Not yet measured against a real scan for a false negative (a genuinely sparse system where the median itself is thin and one further-thin r |  |
| measure_extractor.py:134 | `VOTE_REGULARITY_MIN_SAMPLE = 4` | ? |  | C | ? | VOTE_REGULARITY_MIN_SAMPLE = 4 |  |
| measure_extractor.py:1611 | `CELL_LINE_MAX_SHIFT_SPACES = 0.75` | sp |  | C | ? |  How far the comb may slide. Bounded BELOW one spacing on purpose — that is what makes aliasing unreachable rather than merely unlikely — and above the 0.65 spaces of the |  |
| measure_extractor.py:1619 | `CELL_LINE_MIN_ROW_COVERAGE = 0.45` | ratio |  | B | NARROWS |  that replaces per-line matching's missing one: it asserts that printed staff lines really are there, so a cell whose profile is dominated by a beam or a chord — one stro |  |
| measure_extractor.py:1632 | `CELL_LINE_MIN_ROWS_COVERED = 4` | ratio |  | B | REFUSES |  there; phase 1's fit is itself distorted, and a rigid comb inherits that. Four rows agreeing at 1.00 is overwhelming evidence of a staff either way. This does not reopen |  |
| measure_extractor.py:1642 | `CELL_LINE_MIN_SHIFT_SPACES = 0.05` | sp |  | C | REFUSES |  0.024 spaces, which is exactly 1 px at that spacing. Refusing those is what makes the engraved control a no-op that can be PROVED rather than hoped for, and it forfeits  |  |
| measure_extractor.py:1656 | `CELL_LINE_MIN_WIDTH_SPACES = 4.0` | sp |  | C | REFUSES |  `benchmarks/omr-scan-e2e-2026-09/RESULTS.md` §1 measures at 2.2 spaces. The shift bound already refuses a full-spacing alias; this refuses the partial ones it would let  |  |
| measure_extractor.py:1690 | `CELL_LINE_FIND_TALL_COLUMN_SPACES = 4.5` | sp |  | C | ? | CELL_LINE_FIND_TALL_COLUMN_SPACES = 4.5 |  |
| measure_extractor.py:1691 | `CELL_LINE_FIND_SPACING_TOLERANCE = 0.08` | ? |  | C | ? | CELL_LINE_FIND_SPACING_TOLERANCE = 0.08 |  |
| measure_extractor.py:1692 | `CELL_LINE_FIND_LINE_COVERAGE = 0.7` | ratio |  | B | ? | CELL_LINE_FIND_LINE_COVERAGE = 0.70 |  |
| measure_extractor.py:1694 | `CELL_LINE_FIND_KEEP_PX = 1` | px |  | E | ? | CELL_LINE_FIND_KEEP_PX = 1 |  |
| measure_extractor.py:2197 | `RESEGMENT_MIN_HEIGHT_FRAC = 0.6` | ratio |  | B | DECIDES |  Deliberately more lenient than the global BARLINE_MIN_HEIGHT_FRAC (0.80) because a faint/partially-obscured barline is a plausible reason Phase 1 missed it in the first  |  |
| measure_extractor.py:2202 | `RESEGMENT_MIN_VOTE_FRAC = 0.3` | ratio |  | B | NARROWS |  Minimum fraction of staves in the system that must vote for a candidate column (vs. up to 0.80 for the global per-system vote in detect_barlines). Safe to relax because  |  |
| measure_extractor.py:2206 | `RESEGMENT_MIN_CONNECTIVITY = 0.5` | ? |  | C | NARROWS |  Minimum inter-staff-gap ink continuity (see _intersystem_connectivity) a candidate column must show. A genuine barline is drawn through the whitespace between staves; a  |  |
| measure_extractor.py:2209 | `RESEGMENT_WIDTH_WARN_FACTOR = 2.0` | ? |  | B | NARROWS |  Matches the >2x-median check transcribe.py uses to set phase1_warning — a cell is only a re-segmentation CANDIDATE if it's already flagged there. RESEGMENT_WIDTH_WARN_FA |  |
| measure_extractor.py:2223 | `RESEGMENT_STEER_WIDTH_FACTOR = 1.5` | ? |  | C | REFUSES |  guard (MAX_PIECE_FRAC) is dropped under steering — the known count overrides the "still an outlier" heuristic — but the sliver floor (MIN_PIECE_FRAC) is always kept, and |  |
| staff_detector.py:41 | `MIN_PEAK_DISTANCE_PX = 4` | px |  | E | ? | MIN_PEAK_DISTANCE_PX = 4 staff lines won't be closer than this | * rank 18: E, raw px; first commit 05-14 |
| staff_detector.py:42 | `MIN_LINE_LENGTH_FRAC = 0.35` | ratio |  | B | ? | MIN_LINE_LENGTH_FRAC = 0.35 staff line spans >= 35% of page width |  |
| staff_detector.py:43 | `PEAK_PROMINENCE_FRAC = 0.3` | ratio |  | B | ? | PEAK_PROMINENCE_FRAC = 0.30 peak must be 30% of (max - min) profile range |  |
| staff_detector.py:44 | `GROUP_LINE_SPACING_TOLERANCE = 0.3` | ? |  | C | ? | GROUP_LINE_SPACING_TOLERANCE = 0.30 ±30% gap variation within a 5-line group |  |
| staff_detector.py:46 | `STAFF_LINE_MAX_GAP_SPACES = 1.0` | sp |  | C | ? | STAFF_LINE_MAX_GAP_SPACES = 1.0 a break this wide is still the same staff line |  |
| staff_detector.py:51 | `STAFF_LINE_BAND_SPACES = 0.35` | sp | L | D | ? |  How far above and below its nominal row a printed staff line is looked for, in staff spaces. It has to cover the line's own thickness plus how far it wanders — measured  |  |
| staff_detector.py:55 | `STAFF_EXTENT_MIN_LINES = 3` | count |  | A | ? |  How many of a staff's five lines must carry ink in a column for it to count as part of the staff. Two is not enough: an instrument name in the margin crosses two line ro |  |
| staff_detector.py:57 | `MAX_LINE_INK_RUNS_PER_SPACE = 1.7` | sp |  | C | DECIDES | MAX_LINE_INK_RUNS_PER_SPACE = 1.7 above this the "lines" are rows of text, not staff lines |  |
| staff_detector.py:71 | `STAFF_COMB_POOL_FRAC = 0.3` | ratio | L | D | ? |  Boléro p.31, La Mer p.25, Kirchhoff p.10): every value in 0.20-0.35 gives identical, correct counts on all seven pages; below 0.20 false staves appear (Beethoven 5 p.2 g |  |
| staff_detector.py:74 | `STAFF_COMB_TOLERANCE = 0.25` | sp |  | A | ? |  How far a line may sit from the position the comb predicts, in staff spaces. Engraving is regular; this only has to absorb rasterisation and a scan's skew. STAFF_COMB_TO |  |
| staff_detector.py:79 | `STAFF_SPACING_OUTLIER_FACTOR = 1.6` | ? |  | C | REFUSES |  A group whose line spacing is a large multiple of the page's spacing is not a staff — it is one line borrowed from each of several staves (see `_reject_spacing_outliers` |  |
| staff_detector.py:89 | `SINGLE_LINE_CLEARANCE_SPACES = 4.0` | sp |  | C | DECIDES |  staff whose others were never detected, which is a far commoner page than a percussion part. Precision matters more than recall here, because a staff invented between tw |  |
| staff_detector.py:93 | `SINGLE_LINE_MIN_WIDTH_FRAC = 0.5` | ratio |  | B | ? |  The rule must also be a staff's worth of line: this fraction of the page's median staff width, and overlapping the x-window the page's staves occupy. A hairpin, a bracke |  |
| staff_detector.py:94 | `SINGLE_LINE_MIN_OVERLAP_FRAC = 0.6` | ratio |  | B | ? | SINGLE_LINE_MIN_OVERLAP_FRAC = 0.6 |  |
| staff_detector.py:102 | `SINGLE_LINE_NEIGHBOUR_RUN_FRAC = 0.5` | ratio |  | B | ? |  survivor is alone, full width, and between its neighbours — indistinguishable from a percussion rule by every property of the row itself. The other four lines are still  |  |
| staff_detector.py:123 | `SINGLE_LINE_CLUSTER_WIDTH_FRAC = 0.9` | ratio |  | B | ? |  RELATIVELY, so an interloper is judged against the rules it is interfering with rather than against the page. 0.9 because the real rules on these pages agree to within 0 |  |
| staff_detector.py:146 | `MISFIT_THICKNESS_RATIO = 2.5` | ratio | B | D | DECIDES |  Brahms staff 8 is exactly that, and must not be touched. Thickness ratio against the group's median: 19 of the 21 staves on that page sit at 1.0-1.8, the two outliers at |  |
| staff_detector.py:149 | `MISFIT_MIN_RUN_FRAC = 0.5` | ratio |  | B | ? |  The replacement row must actually carry a printed line, judged the same way the first pass judges one: a long horizontal run at the staff's own width. MISFIT_MIN_RUN_FRA |  |
| staff_detector.py:193 | `MISFIT_MAX_SHIFT = 2` | ? |  | C | DECIDES |  A window three or more spaces off shares no line with the true staff, so there is no evidence it is the same staff; the measured cases are 1 and 2. MISFIT_MAX_SHIFT = 2 |  |
| staff_line_removal.py:70 | `MAX_LINE_THICKNESS_SPACES = 0.35` | sp | L | D | ? |  A printed staff line is never thicker than this share of a staff space. Used to cap the measured thickness, so a line buried under symbols for its whole length cannot ta |  |
| staff_line_removal.py:76 | `LINE_CROSSING_FACTOR = 2.0` | ? |  | B | DECIDES |  A vertical ink run taller than this multiple of the line's own thickness is something crossing the line, not the line. Wide margin on purpose: the smallest real crossing |  |
| staff_line_removal.py:85 | `MAX_ERASABLE_RUN_SPACES = 0.45` | sp |  | C | REFUSES |  crosses. Measured, this cap changes almost nothing (Mahler 5 p.11 beam count 239 with or without it, and it does not bind at all on WTC or Boléro) — it is insurance agai |  |
| staged/adjudicators/clef.py:85 | `MARGIN_FLOOR = 1.0` | ? |  | C | ? |  runner-up is 0, so this is also an ABSOLUTE floor on a lone reading -- a solitary clef at confidence 0.05 with nothing corroborating it does not take a staff. That is de |  |
| staged/adjudicators/clef.py:118 | `W_ON_THIS_STAFF = 1.5` | ? |  | n/a | NARROWS |  It must EXCEED `MARGIN_FLOOR`, because the population it is for is an exact tie: five of those six score 3.0 against 3.0, two clef glyphs at high confidence on one staff |  |
| staged/adjudicators/clef.py:128 | `ON_STAFF_MIN_STEPS = -2.0` | count |  | C | DECIDES |  ⚠️ WIDE ON PURPOSE. The separation measured is 8 steps clear on the near side, so nothing here needs a tight band; a tight one would start deciding cases the evidence do |  |
| staged/adjudicators/clef.py:129 | `ON_STAFF_MAX_STEPS = 10.0` | count |  | A | ? | ON_STAFF_MAX_STEPS = 10.0 |  |
| staged/adjudicators/clef.py:321 | `_STEPS_PER_LINE_SPACING = 2.0` | ? |  | C | REFUSES |  line spacing, `half_step` 20px, the middle line at position 4.0. `clef_geometry.DEFAULT_CONFIG.max_residual` is in units of one FULL line spacing, i.e. two of these step |  |
| staged/adjudicators/family_precision.py:185 | `_LINE_STEPS = [0.0, 2.0, 4.0, 6.0, 8.0]` | ? |  | C | ? |  A staff's five lines as STAFF STEPS in `_staff_step`'s frame. _LINE_STEPS = (0.0, 2.0, 4.0, 6.0, 8.0) |  |
| staged/adjudicators/family_precision.py:204 | `ON_A_STAFF_LINE_TOL_SPACES = 0.25` | sp |  | C | REFUSES |  `rhythm.py` measures on this plate is a whole STEP (0.5 spaces), still half the distance to the first rung. The positive control the tests pin is exactly that box: a run |  |
| staged/adjudicators/key_slots.py:86 | `EDGE_MARGIN_SPACES = 0.3` | sp |  | C | DECIDES |  How far past the run's last box a centre may stand and still be in its column: a flat is ~1.1 spaces wide and a box edge is a detector's. EDGE_MARGIN_SPACES = 0.3 |  |
| staged/adjudicators/key_slots.py:91 | `LEVEL_MARGIN_SPACES = 1.0` | sp |  | C | ? |  Level with the signature: a centre within this many spaces of the run's own vertical extent. A neighbour staff's ink padded into the cell stands farther than this from e |  |
| staged/adjudicators/notehead_precision.py:143 | `CELL_EDGE_TOLERANCE_PAGE_PX = 1.0` | px |  | E | DECIDES |  is comfortably larger than the floating-point residual the affine map leaves (0.0000-0.0142 staff spaces, i.e. well under a page pixel at any DPI this project reads) and |  |
| staged/adjudicators/notehead_precision.py:202 | `_STAFF_BOTTOM_POSITION = 8.0` | ? |  | C | ? |  Above this staff position (half-step units, top line = 0), a note is standing on the bottom line of a normal 5-line staff. _STAFF_BOTTOM_POSITION = 8.0 |  |
| staged/adjudicators/notehead_precision.py:232 | `NEARER_STAFF_FILED_MIN_SPACES = 3.0` | sp |  | C | ? |  on this plate, about half the gap between two staves (~5.9 spaces), so past it a head is on the other staff's side of the air. The population that crosses it falls off a |  |
| staged/adjudicators/notehead_precision.py:243 | `NEARER_STAFF_NEAR_MAX_SPACES = 2.75` | sp |  | C | DECIDES |  above, not ink inside it — so the bound must pass 2.588; 2.75 is the quarter-space above it. The confirmed heads are nearer their own staff than any other by at least 1. |  |
| staged/adjudicators/ownership.py:93 | `OWN_LINE_MAX_SPACES = 0.5` | sp |  | C | DECIDES |  `notehead_precision.OWN_LEDGER_MAX_SPACES` (2.7b, measured there: of 79 far heads the first cut kept on a rung, 43 were kept by a rung 0.00-0.37 spaces from the head and |  |
| staged/adjudicators/ownership.py:444 | `STAFF_BESIDE_SLACK_SPACES = 2.0` | sp |  | C | ? |  a staff's x extent, plus this many spaces for a cell's pad, is "beside" it STAFF_BESIDE_SLACK_SPACES = 2.0 |  |
| staged/adjudicators/ownership.py:3771 | `_Flank.cell_index = 0` | ? |  | C | ? | cell_index: int = 0 |  |
| staged/adjudicators/ownership.py:6418 | `BARLINE_COLUMN_TOL_SPACES = 0.15` | sp | B | D | REFUSES |  cells are cut AT the barlines (`Q.CELL_BOX` edges; the cells of a staff are contiguous, Brahms p5 staff 1: 1330 / 1804 / 2271), the precedent is `unread_mark._touches_a_ |  |
| staged/adjudicators/repeats.py:32 | `SPAN_TOL_SPACES = 0.75` | sp | B | D | ? |  A bracket's end stands at a barline: within this many staff spaces of a cell edge. Measured on Brahms p10: 7 px and 6 px off (0.25 spaces); the open 2nd ending ended exa |  |
| staged/adjudicators/repeats.py:49 | `MIN_STAFF_FRACTION = 0.5` | ratio | B | D | DECIDES |  A repeat sign is printed on every staff of the system; a dot pair on a few staves is a column of dotted notes. Decided where at least this fraction of the system's stave |  |
| staged/adjudicators/rhythm.py:10381 | `STAFF_MIDDLE_LINE_STEP = 4.0` | count |  | A | DECIDES |  ESTABLISHED practice, a rest pushed above the staff's own MIDDLE LINE belongs to the upper (stem-up) voice, one pushed below to the lower (stem-down) voice. `_staff_step |  |
| staged/adjudicators/text.py:287 | `UNREAD_LINE_X_SHARE = 0.1` | ratio | L | D | NARROWS |  candidate windows of ONE staff are one text line where their x-ranges overlap by this share of the narrower and their y-ranges by `UNREAD_LINE_Y_SHARE` of the shorter (t |  |
| staged/adjudicators/text.py:288 | `UNREAD_LINE_Y_SHARE = 0.5` | ratio |  | B | REFUSES | UNREAD_LINE_Y_SHARE = 0.5 |  |
| staged/adjudicators/text.py:291 | `SIBLING_SPAN_SHARE = 0.5` | ratio |  | A | NARROWS |  a READ word on ANOTHER staff of the system is a witness for an unread line where it covers this share of the WITNESS's own width of the line's x-range and the two widths |  |
| staged/adjudicators/unboxed_rest.py:74 | `QUARTER_PEAK_SHARE = 0.85` | ratio |  | B | ? | QUARTER_PEAK_SHARE = 0.85 |  |
| staged/adjudicators/unread_mark.py:170 | `BARLINE_TOUCH_TOLERANCE_SPACES = 0.5` | sp |  | A | NARROWS |  ⚠️ NOT PRINT-MEASURED -- see the module docstring's CONVENTION ASSUMED note. Half a staff space, well inside the notehead-sized window, so it narrows the population rath |  |
| staged/adjudicators/unread_mark.py:179 | `STAFF_LINE_SLIVER_MAX_HEIGHT_SPACES = 0.5` | sp |  | B | REFUSES |  line_and_thin_is_excluded` raised `KeyError` on an empty `excluded_by_ guard`, not on a wrong verdict). 0.5 is comfortably inside the notehead window and comfortably sho |  |
| staged/adjudicators/unread_mark.py:180 | `STAFF_LINE_SLIVER_Y_TOLERANCE_SPACES = 0.15` | sp |  | C | REFUSES | STAFF_LINE_SLIVER_Y_TOLERANCE_SPACES = 0.15 |  |
| staged/arc_claim.py:152 | `BOX_ON_LINE_MIN = 0.85` | sp | L | D | REFUSES |  letter is never a stretch of a curve, whatever its share (measured on Litolff p2/4/6/10 with the first cut 0.5 and every class: 7 half-note heads at 0.52-0.77, 4 dots, 3 |  |
| staged/arc_claim.py:487 | `BIND_COLUMN_MARGIN_SPACES = 0.5` | sp |  | C | ? |  at one end, a second column whose distance is within this many staff spaces of the nearest one makes the end ambiguous BIND_COLUMN_MARGIN_SPACES = 0.5 |  |
| staged/arcs_system.py:56 | `RAW_LINE_ALLOWANCE_SPACES = 0.35` | sp |  | C | ? |  On the RAW page (staff lines in) a stroke's run may be this much taller than `STROKE_MAX_SPACES` (the stroke crossing a staff line). A stem or barline the staff-line rem |  |
| staged/arcs_system.py:60 | `ON_LINE_SHARE = 0.6` | ratio |  | B | ? | ON_LINE_SHARE = 0.6 |  |
| staged/barline_columns.py:32 | `WINDOW_SPACES = 1.5` | sp | L | D | ? |  the search window either side of the mean x, staff spaces (the largest drift measured, 21 px over a system on Litolff p6 = ~0.5 sp per staff) WINDOW_SPACES = 1.5 |  |
| staged/beam_strokes.py:633 | `STAFF_LINE_THICKNESS_SPACES = 0.25` | sp | LB | D | NARROWS |  A staff line's own thickness, staff spaces, taken out of a beam's thickness where the beam lies on a line at the stem. MEASURED, NARROWS ONLY: the median of `Q.STAFF_SKE | * rank 6: D, NARROWS; a median over two plates used instead of the local line |
| staged/beam_strokes.py:1024 | `THIN_LINE_FIRST_LEVEL_SPACES = 0.6` | sp |  | C | DECIDES |  2.318 r4: how far inward of the stem's tip a thin line's outer edge may lie and still be where the first beam level would start. A beam's first level lies at the tip (`S |  |
| staged/box_kind.py:81 | `LINE_GAP_SP = 0.3` | sp |  | C | ? | LINE_GAP_SP = 0.3 |  |
| staged/claims.py:258 | `BRACKET_MAX_OFFSET_SPACES = 0.5` | sp |  | C | DECIDES |  a bracket / brace stroke claims only at or left of the system's staff start (`Stroke.offset_spacings`, the systemic barline stands AT it; a tall stem to its right is a n |  |
| staged/claims.py:259 | `BRACKET_MIN_HEIGHT_SPACES = 4.0` | sp |  | C | ? | BRACKET_MIN_HEIGHT_SPACES = 4.0 |  |
| staged/clef_pagewide.py:67 | `LINE_HALF_SPACES = 0.3` | sp |  | B | ? |  staff-line rows are cleared within this of each line (staff spaces) where a row's ink runs across this share of the window LINE_HALF_SPACES = 0.3 |  |
| staged/clef_pagewide.py:72 | `LOCAL_LINE_REACH_SPACES = 0.6` | sp |  | B | ? |  the local line search: rows within this of the nominal line, over this many columns left of the clef LOCAL_LINE_REACH_SPACES = 0.6 |  |
| staged/clef_pagewide.py:73 | `LOCAL_LINE_WINDOW_SPACES = 4.0` | sp |  | B | ? | LOCAL_LINE_WINDOW_SPACES = 4.0 |  |
| staged/counted_marks.py:98 | `_CELL = 64.0` | px |  | n/a | ? | _CELL = 64.0 px grid for the neighbour search (a head box is ~20-45 px at 600 dpi) |  |
| staged/export.py:787 | `StaffRun.n_measures = 0` | count |  | A | ? | n_measures: int = 0 |  |
| staged/export.py:1403 | `_CLIPPED_PIECE_OF_NEXT_STAFF_MIN_SP = 3.0` | sp | L | D | REFUSES |  ROADMAP 2.315 (Litolff p1 m51). A piece of a head cut off at the edge of the bar's cell, standing three spaces or more beyond this staff with no ledger line between it a |  |
| staged/gather.py:2493 | `PAGE_EDGE_MARGIN_SPACES = 0.8` | sp | LB | D | ? |  (`Q.NOTEHEAD_STAFF_POSITION`, the cell's own grid) over every notehead on the 10-06 records -- max 0.775 sp (Litolff) / 0.73 sp (Breitkopf), p99 0.64 / 0.36. Inside the  |  |
| staged/gather.py:4871 | `VLINE_SPACES = 4.0` | sp |  | C | ? |  Taller than any letter (an `f` is ~2.9 spaces): a barline, a stem. VLINE_SPACES = 4.0 |  |
| staged/gather.py:7308 | `LINE_ROW_FLANK_NEAR_SPACES = 0.1` | sp |  | C | DECIDES |  A row is a LINE row at a stem where the RAW page inks both flanks of the stem: this wide, this far out (staff spaces), at least this much. LINE_ROW_FLANK_NEAR_SPACES = 0 |  |
| staged/gather.py:7309 | `LINE_ROW_FLANK_FAR_SPACES = 0.5` | sp |  | C | ? | LINE_ROW_FLANK_FAR_SPACES = 0.5 |  |
| staged/gather.py:7312 | `LINE_RUN_MIN_SHARE = 0.75` | ratio |  | B | DECIDES |  A run of attached ink counts as a line when at least this share of its rows are line rows (a ledger line's soft edges are not). LINE_RUN_MIN_SHARE = 0.75 |  |
| staged/gather.py:9705 | `RECENTRE_MIN_MARGIN = 0.08` | ? |  | C | NARROWS |  The winning window's own lead over the best NON-OVERLAPPING rival window — so a tie between two chord noteheads' own windows (each a real, dense head) DECLINES rather th |  |
| staged/geometry.py:266 | `OFF_STAFF_REACH_SPACES = 6.0` | sp |  | C | REFUSES |  REFUSES a box nothing else vouches for: a ledger-rung ladder reaching the box (`ownership.ledger_direction`'s own question, asked by the decider) keeps it whatever its d |  |
| staged/head_extent.py:34 | `LINE_OVERHANG_SPACES = 0.15` | sp |  | C | ? |  r2: a line row reaches past both sides of the head's middle rows and is at least this much wider than the widest of them. LINE_OVERHANG_SPACES = 0.15 |  |
| staged/head_oval.py:46 | `SPAN_WINDOW_SPACES = 1.3` | sp |  | C | ? |  Two ink pixels count toward one column's span only when no more than this apart (a head is ~1 sp tall: an unrelated mark further off in the same column is not the head's |  |
| staged/head_oval.py:50 | `LINE_ROW_SHARE = 0.8` | ratio |  | B | DECIDES |  A row is a staff/ledger line where ink covers this share of a window `LINE_WINDOW_SPACES` either side of the box. LINE_ROW_SHARE = 0.80 |  |
| staged/head_oval.py:51 | `LINE_WINDOW_SPACES = 3.0` | sp |  | C | ? | LINE_WINDOW_SPACES = 3.0 |  |
| staged/inferences.py:2364 | `INK_PICK_MARGIN = 0.15` | ? |  | C | ? | INK_PICK_MARGIN = 0.15 |  |
| staged/ink_attachment.py:24 | `LINE_FLANK_PX = 5` | px |  | E | DECIDES |  a pixel row of a stroke is a STAFF-LINE row when the raw raster is dark in this many columns just left AND just right of the stroke (>= LINE_FLANK_SHARE of them) LINE_FL |  |
| staged/ink_attachment.py:25 | `LINE_FLANK_SHARE = 0.8` | ratio |  | B | ? | LINE_FLANK_SHARE = 0.8 |  |
| staged/key_kind_slots.py:48 | `MIN_MARGIN_STEPS = 1.0` | count |  | A | ? |  on average over the slots, the rival order must miss by this many steps MORE than the fitting one (the margin the reading reports) MIN_MARGIN_STEPS = 1.0 |  |
| staged/key_object.py:460 | `EDGE_MARGIN_SPACES = 0.3` | sp |  | C | ? |  the area reaches this far past the last slot's right edge (`key_slots.EDGE_MARGIN_SPACES`) EDGE_MARGIN_SPACES = 0.3 |  |
| staged/key_object.py:462 | `LEVEL_MARGIN_SPACES = 1.0` | sp |  | C | ? |  ... and this far above and below the staff's own pieces (`key_slots.LEVEL_MARGIN_SPACES`) LEVEL_MARGIN_SPACES = 1.0 |  |
| staged/letter_look.py:88 | `LINE_REMNANT_H_SPACES = 0.45` | sp |  | C | ? |  A staff-line remnant: flat and long. LINE_REMNANT_H_SPACES = 0.45 |  |
| staged/letter_look.py:89 | `LINE_REMNANT_W_SPACES = 1.2` | sp |  | C | ? | LINE_REMNANT_W_SPACES = 1.2 |  |
| staged/letter_look.py:285 | `CANVAS_MARGIN_PX = 40` | px |  | n/a | ? | CANVAS_MARGIN_PX = 40 |  |
| staged/meter_object.py:53 | `LINE_RUN_SLACK_PX = 2` | px |  | E | ? |  a pixel run lying wholly within this many pixels of a staff line, at most this long, is bare line (not numeral ink) LINE_RUN_SLACK_PX = 2 |  |
| staged/meter_object.py:54 | `LINE_TILT_PX = 3` | px |  | E | ? | LINE_TILT_PX = 3 |  |
| staged/page_arcs.py:57 | `LINE_GAP_SP = 0.25` | sp |  | C | ? | LINE_GAP_SP = 0.25 the widest erased staff-line band an arc's two halves are joined across |  |
| staged/page_arcs.py:82 | `LINE_STUB_SP = 0.14` | sp |  | C | DECIDES | LINE_STUB_SP = 0.14 a run whose centre sits this close to a staff line row over most of its length is the eraser's leftover |  |
| staged/page_arcs.py:90 | `LINE_WIN_SP = 2.0` | sp |  | B | REFUSES | LINE_WIN_SP = 2.0 r3: the line's own thickness is the median over this much each side (never above LINE_THICK_CAP x its page median) |  |
| staged/page_arcs.py:91 | `LINE_THICK_CAP = 1.25` | ? |  | C | ? | LINE_THICK_CAP = 1.25 |  |
| staged/page_arcs.py:92 | `LINE_EXCESS_SP = 0.12` | sp |  | B | ? | LINE_EXCESS_SP = 0.12 r3: a raw run on a staff line at least this much thicker than the line's own thickness there is an arc on the line |  |
| staged/page_arcs.py:108 | `TRIM_LINE = 0` | ? |  | C | DECIDES | TRIM_LINE = 0 r3: an arc's end that runs along a staff line row is the line's, not the arc's |  |
| staged/page_arcs.py:110 | `LINE_RESIDUE = 1` | ? |  | C | DECIDES | LINE_RESIDUE = 1 r3: ink wholly inside a staff line's own band is the line's |  |
| staged/page_arcs.py:148 | `LINE_WAIT = 0` | ? |  | C | ? | LINE_WAIT = 0 r3 experiment: a track waits through a line band |  |
| staged/page_arcs.py:149 | `LINE_PAD_SP = 0.1` | sp |  | C | ? | LINE_PAD_SP = 0.1 r3: a line's band for the wait-through |  |
| staged/page_heads.py:1074 | `CASE_MARGIN_SP = 4.0` | sp |  | C | ? |  the crop around a case's box, staff spaces each side CASE_MARGIN_SP = 4.0 |  |
| staged/page_strokes.py:45 | `BAND_MARGIN_SPACES = 0.5` | sp |  | C | ? | BAND_MARGIN_SPACES = 0.5 |  |
| staged/page_strokes.py:55 | `LINE_RUN_MIN_SPACES = 3.0` | sp |  | C | DECIDES |  a level run at least this long (spaces) in a band no cell covers is a staff line, taken out LINE_RUN_MIN_SPACES = 3.0 |  |
| staged/page_strokes.py:59 | `STAFF_REACH_SPACES = 3.0` | sp |  | C | DECIDES |  a PageStaff owns the rows this many spaces beyond its lines; a stroke further than that from every staff takes the nearest STAFF_REACH_SPACES = 3.0 |  |
| staged/positions.py:195 | `BOTTOM_LINE_STEP = 8.0` | count |  | A | REFUSES |  Staff steps of the BOTTOM line, in the STEP frame. Five lines, four gaps, two steps per gap. ⚠️ DERIVED FROM THE GRID, not a convention: `_cell_grid` returns the mean ga |  |
| staged/positions.py:198 | `MIDDLE_LINE_STEP = 4.0` | count |  | A | ? |  The middle line, which is what separates a meter's two halves. MIDDLE_LINE_STEP = 4.0 |  |
| staged/rest_ink.py:38 | `OUTSIDE_MARGIN_SP = 0.2` | sp |  | C | ? | OUTSIDE_MARGIN_SP = 0.2 the rest box is grown by this before "outside the box" ink is counted |  |
| staged/rest_ink.py:41 | `ROW_MARGIN_SP = 0.7` | sp |  | C | ? | ROW_MARGIN_SP = 0.7 rows searched beyond the box's top and bottom |  |
| staged/stem_strokes.py:42 | `COLLINEAR_X_SPACES = 0.3` | sp |  | C | ? | COLLINEAR_X_SPACES = 0.3 |  |
| staged/stem_strokes.py:53 | `CELL_EDGE_SPACES = 0.3` | sp |  | C | ? |  A vertical stroke whose edge is within this of the cell's edge is "at the bar's edge" (2.155). CELL_EDGE_SPACES = 0.3 |  |
| staged/stroke_map.py:57 | `LINE_MIN_INK = 0.5` | ? |  | C | ? | LINE_MIN_INK = 0.5 |  |
| time_signature_locator.py:192 | `TimeSignatureLocatorConfig.min_staff_fraction = 0.7` | ratio |  | B | ? | min_staff_fraction: float = 0.70 |  |

## claims (190; A 11, B 73, C 79, D 14, E 11, n/a 2)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| direction_text.py:677 | `THROUGH_STROKE_INK = 0.95` | ? | L | D | ? |  word's line) when ONE unbroken run of ink covers this share of the line strip's rows. Unbroken, not merely dense: the `d` of `Adagio` over the stem stub beneath it cover |  |
| direction_text.py:1238 | `SCAN_MIN_TOTAL_COVER = 0.95` | ratio |  | B | ? |  so the one-image test above cannot prove it. Taken from `OMR_WEIGHT_ROUTING`'s own measured rule -- "total coverage >= 0.95 on every scan measured, incl. one tiled into  |  |
| hairpin_detection.py:95 | `_INK_FRACTION_CEILING = 0.5` | ratio |  | B | REFUSES |  A page whose "ink" exceeds this after inversion was handed the wrong polarity. Not a tuned number — a printed orchestral page is a few percent ink, and the ceiling only  |  |
| header_ink.py:39 | `InkMaskConfig.vertical_rule_max_width_spaces = 0.5` | sp |  | C | REFUSES | vertical_rule_max_width_spaces: float = 0.5 thinner ⇒ a rule, not a glyph |  |
| header_ink.py:40 | `InkMaskConfig.vertical_rule_min_height_spaces = 2.0` | sp |  | C | ? | vertical_rule_min_height_spaces: float = 2.0 |  |
| header_ink.py:44 | `InkMaskConfig.heavy_rule_max_width_spaces = 1.2` | sp |  | C | ? | heavy_rule_max_width_spaces: float = 1.2 |  |
| header_ink.py:45 | `InkMaskConfig.heavy_rule_min_height_spaces = 5.0` | sp |  | C | ? | heavy_rule_min_height_spaces: float = 5.0 |  |
| header_ink.py:46 | `InkMaskConfig.min_ink_height_spaces = 0.2` | sp |  | C | ? | min_ink_height_spaces: float = 0.2 |  |
| input_domain.py:37 | `SCAN_TOTAL_RASTER_COVERAGE = 0.5` | ratio |  | B | ? |  Nearest measured populations: 0.000 (engraved) / 0.95 (sparsest scan page). SCAN_TOTAL_RASTER_COVERAGE = 0.5 |  |
| key_consensus.py:117 | `MAJORITY_SHARE = 0.6` | ratio |  | B | NARROWS |  the witnesses split 7 to 6, a strict majority admitted it, the winning side was the WRONG one (the movement's second subject is in D major, and the six reading 2 sharps  |  |
| key_consensus.py:123 | `NO_SIGNATURE_SHARE = 0.8` | ratio |  | B | REFUSES |  A score prints no key signatures when this share of the staves that SHOULD show one printed nothing instead. Deliberately high: the cost of a false positive here is sile |  |
| line_detection.py:1762 | `SAME_STROKE_DEFAULT_THICKNESS_SPACES = 0.09` | sp |  | C | ? |  Where a cell's own staff-line thickness was never traced (mirrors `gather.BEAM_STEM_JOIN_DEFAULT_THICKNESS_SPACES`). SAME_STROKE_DEFAULT_THICKNESS_SPACES = 0.09 |  |
| measure_extractor.py:2214 | `RESEGMENT_MIN_PIECE_FRAC = 0.5` | ratio |  | B | REFUSES |  Acceptance band (guardrail c): every resulting sub-measure's width must land within [MIN_PIECE_FRAC, MAX_PIECE_FRAC] x the staff's median measure width, or the whole spl |  |
| measure_extractor.py:2215 | `RESEGMENT_MAX_PIECE_FRAC = 1.75` | ratio |  | B | ? | RESEGMENT_MAX_PIECE_FRAC = 1.75 |  |
| staff_detector.py:190 | `MISFIT_COVERAGE_FRAC = 0.35` | ratio |  | B | REFUSES |  ink profile; both of the next two are correctly placed staves on faint scans (lamer's last row is 2px off its line, not a space). RELATIVE to the staff's own median rath |  |
| staged/accidental_family.py:78 | `COVER_SHARE_MIN = 0.5` | ratio |  | B | DECIDES |  a vertical stroke with at least this share of its ink in the box is the mark's (the register's cut, `stroke_map.COVER_SHARE_MIN`, is 0.5); a PARTLY covered stroke (grown |  |
| staged/accidental_family.py:79 | `GROW_SHARE_MIN = 0.15` | ratio |  | B | ? | GROW_SHARE_MIN = 0.15 |  |
| staged/adjudicators/head_rest_shape.py:82 | `OWN_STROKE_SLACK_SPACES = 0.2` | sp |  | B | DECIDES |  ROADMAP 2.206b. A stem on a head leaves the HEAD sticking out past its end (half a head, ~0.4 sp, even when the head sits flush); the ink's full height is stem + that. A |  |
| staged/adjudicators/header.py:693 | `CHANGE_MIN_SHARE = 0.5` | ratio |  | A | ? |  a change is printed *on EVERY staff of it*. Two staves out of twenty-four is not that sentence; it is two staves misreading. The absolute floor stays because a system ma |  |
| staged/adjudicators/inside_meter.py:31 | `INSIDE_SHARE_MIN = 0.5` | ratio |  | B | REFUSES |  share of the box's own ink that must lie inside the area (stated before the count: a digit loop is wholly inside, ~1.0; a head beside the numerals shares at most a slive |  |
| staged/adjudicators/letter_cover.py:39 | `COVER_REFUSE_SHARE = 0.5` | ratio |  | B | REFUSES | COVER_REFUSE_SHARE = 0.5 |  |
| staged/adjudicators/movement.py:85 | `LABEL_COVERAGE_MIN = 0.5` | ratio |  | B | REFUSES |  A margin-label "reset" needs labels on at least this share of the system's staves before it counts at all -- a lone label is not a reset. LABEL_COVERAGE_MIN = 0.5 |  |
| staged/adjudicators/notehead_precision.py:1632 | `CROSSING_MIN_SHARE = 0.3` | ratio |  | B | REFUSES |  -- Sean: "a tiny bleed" must fail even where the sliver itself is dense. A real slash splits roughly evenly across the stem it crosses; 0.30 requires each side to carry  |  |
| staged/adjudicators/ownership.py:41 | `W_RANGE_IMPOSSIBLE = -6.0` | ? |  | n/a | ? | W_RANGE_IMPOSSIBLE = -6.0 a veto on the IMPOSSIBLE, never on the unlikely |  |
| staged/adjudicators/ownership.py:42 | `W_DISTANCE = 0.5` | ? |  | n/a | ? | W_DISTANCE = 0.5 the tie-break, and only that |  |
| staged/adjudicators/ownership.py:161 | `OWN_STRUCTURE_TOLERANCE_SPACES = 0.2` | sp |  | C | NARROWS |  nine §2.6c.3 contests or the six §2.6c.2/2.7b.8 fixture heads is this; NOT CONFIRMED beyond them. This check never compares a side against ITS OWN `anchor_y` (a candidat |  |
| staged/adjudicators/ownership.py:2917 | `BIND_DIFFERENT_POSITION_SPACES = 0.435` | sp |  | C | ? |  ROADMAP 2.223: two heads of one staff this far apart in y (spaces) are at two positions -- the top of the empty interval page-facts s1 records between one position (<= 0 |  |
| staged/adjudicators/ownership.py:3765 | `_Flank.ax0 = 0.0` | ? |  | C | ? | ax0: float = 0.0 |  |
| staged/adjudicators/ownership.py:3766 | `_Flank.ay0 = 0.0` | ? |  | C | ? | ay0: float = 0.0 |  |
| staged/adjudicators/ownership.py:3767 | `_Flank.ax1 = 0.0` | ? |  | C | ? | ax1: float = 0.0 |  |
| staged/adjudicators/ownership.py:3768 | `_Flank.ay1 = 0.0` | ? |  | C | ? | ay1: float = 0.0 |  |
| staged/adjudicators/ownership.py:3773 | `_Flank.avg_h = 0.0` | ? |  | C | ? | avg_h: float = 0.0 |  |
| staged/adjudicators/ownership.py:4332 | `ARTIC_TWIN_IOU_MIN = 0.3` | count |  | A | ? |  ROADMAP 2.12f ROUND 2. Two detections of ONE physical glyph (a mark standing in the gap between two staves is cut into BOTH staves' padded cells) share most of their pag |  |
| staged/adjudicators/stroke_owner.py:238 | `REREAD_NOISE = 0.05` | ? |  | B | DECIDES |  ── ROADMAP 2.238 (`OMR_OWNER_SHAPE`, default OFF): the old pair rules' SHAPE evidence, read off their own GATHER rows ─────────────────── The measured re-read noise on a |  |
| staged/adjudicators/text.py:134 | `SAME_INK_SHARE_OF_LARGER = 0.4` | px | L | D | DECIDES |  is a small box (14 x 26 px) tucked inside the `f`'s (42 x 48): shared area 0.05-0.2 of the larger on 84 same-cell pairs, and those are TWO letters (the 37 `sf` of Litolf |  |
| staged/adjudicators/text.py:1005 | `AT_NOTE_MIN_OVERLAP = 0.25` | ? |  | A | REFUSES |  between. CONVENTION ASSUMED (the share is not measured on a corpus; a quarter of a head is a touch, not a position) / WHAT WOULD FALSIFY IT: Sean calling an `at_note` an |  |
| staged/adjudicators/text.py:1008 | `EQUALLY_PLAUSIBLE_SHARE = 0.8` | ratio |  | B | NARROWS |  Two columns whose overlap with the mark is within this share of each other are equally plausible, and the anchor abstains (rule 8). EQUALLY_PLAUSIBLE_SHARE = 0.8 |  |
| staged/adjudicators/unboxed_rest.py:71 | `STROKE_SHARE = 0.9` | ratio |  | B | DECIDES |  each of six equal-width slices, as a share of its height. A flat or a natural is a stem with a bowl: the LEFT slices are (nearly) full and the rest are not. A sharp is t |  |
| staged/adjudicators/unboxed_rest.py:73 | `EIGHTH_MAX_COLUMN_SHARE = 0.92` | ratio |  | B | ? | EIGHTH_MAX_COLUMN_SHARE = 0.92 |  |
| staged/adjudicators/unboxed_rest.py:87 | `COVERED_SHARE = 0.5` | ratio |  | B | DECIDES |  Covered by standing boxes by this much or more = already read; between the two bounds = a claim this decision cannot see past. COVERED_SHARE = 0.5 |  |
| staged/adjudicators/unboxed_rest.py:92 | `THIN_STROKE_MAX_COLUMN_SHARE = 0.45` | ratio | B | D | DECIDES |  A rest has a body: the tallest ink column of the 140 standing Brahms rests is at least 49% of their height. Ink with no column above this is a thin stroke -- the END OF  | * rank 4: D, REFUSES; 140 Brahms rests (d0e2230b1) |
| staged/adjudicators/unboxed_rest.py:93 | `TOUCHED_SHARE = 0.1` | ratio |  | B | ? | TOUCHED_SHARE = 0.1 |  |
| staged/arc_claim.py:44 | `ON_TRACE_SHARE_MIN = 0.5` | ratio |  | B | DECIDES |  a stroke is the arc's when at least this share of its ink lies on the traced curve (the register's one cut, `stroke_map.COVER_SHARE_MIN`) ON_TRACE_SHARE_MIN = 0.5 |  |
| staged/arc_claim.py:142 | `CROSSING_BOX_SHARE = 0.25` | px |  | E | DECIDES |  stroke pixels inside that mark's detector box, over all of the cell's stroke pixels inside it) is a CROSSING -- the slur passes through the head, ledger, dot or letter a |  |
| staged/arc_claim.py:466 | `ONE_STROKE_MIN_SPACES = 1.0` | sp |  | C | ? |  two boxes whose traces AGREE (one y, `SAME_Y_SPACES`) over at least this many spaces are one stroke seen twice (a head's width is ~1.3 sp; two arcs that MEET at a note a |  |
| staged/arc_strip.py:43 | `REACH_BACK_SHARE = 0.5` | ratio |  | B | ? |  ... and reach back over at least this share of the cut box's width. REACH_BACK_SHARE = 0.5 |  |
| staged/arc_strip.py:45 | `Y_OVERLAP_MIN = 0.5` | count |  | B | ? |  y bands overlap by at least this share of the shorter. Y_OVERLAP_MIN = 0.5 |  |
| staged/arc_strip.py:47 | `INSIDE_SHARE = 0.8` | ratio |  | B | NARROWS |  A cell arc box is inside the candidate where this share of its area is. INSIDE_SHARE = 0.8 |  |
| staged/arc_strip.py:62 | `PIECE_MIN_SPACES = 0.75` | sp |  | C | ? |  A clipped piece narrower than this (spaces) is not filed. PIECE_MIN_SPACES = 0.75 |  |
| staged/arcs_system.py:53 | `STROKE_MAX_SPACES = 0.6` | sp | L | D | NARROWS |  A column's ink run no taller than this is a candidate for an arc's stroke. A tie's middle is 0.3-0.46 sp thick on Litolff; a notehead is ~1 sp tall and a beam ~0.5 sp, s | * rank 11: D, REFUSES to follow a thicker run; Litolff tie middle 0.3-0.46 (731065492, 2.166) |
| staged/arcs_system.py:91 | `MIN_COVER = 0.5` | ratio |  | B | NARROWS |  A trace must ink at least this share of its own box's columns to be read; under it the box abstains (no erase). MIN_COVER = 0.5 |  |
| staged/arcs_system.py:99 | `SAME_SHARE = 0.6` | ratio |  | B | ? |  Over the columns two traces share, at least this share must agree in y for them to be one curve. SAME_SHARE = 0.6 |  |
| staged/arcs_system.py:110 | `STROKE_ONLY_RESIDUAL_SPACES2 = 0.06` | sp |  | C | ? |  A notehead box whose ink OFF the traced stroke is under this (square spaces) holds nothing but the stroke -- a tail boxed as a head -- and is not protected. A real fille |  |
| staged/beam_strokes.py:250 | `CLOT_PIECE_MAX_SPACES = 1.6` | sp |  | C | ? | CLOT_PIECE_MAX_SPACES = 1.6 |  |
| staged/beam_strokes.py:798 | `INK_SIDE_MIN_SPACES = 1.0` | sp |  | C | ? | INK_SIDE_MIN_SPACES = 1.0 |  |
| staged/box_kind.py:85 | `REMAINDER_INK_MIN = 0.3` | count |  | A | DECIDES |  ... and the ink in that core's box is a head's (a ring is ~half ink; a slur closed onto a line remnant encloses mostly paper) REMAINDER_INK_MIN = 0.3 |  |
| staged/box_kind.py:94 | `RUN_SHARE_MIN = 0.6` | ratio |  | B | ? | RUN_SHARE_MIN = 0.6 |  |
| staged/claim_final.py:37 | `CUT = 0.5` | ? |  | B | REFUSES |  the share of a box's own ink a claim of another kind must hold for the claim to refuse it (the register's cut, `claims.INSIDE_SHARE_MIN`) CUT = 0.5 |  |
| staged/claim_final.py:39 | `NEAR_MIN = 0.25` | count |  | A | REFUSES |  boxes held at least this much are RECORDED (a refusal says how close it came: near misses become tiles) NEAR_MIN = 0.25 |  |
| staged/claim_final.py:124 | `COPY_IOU_MIN = 0.7` | count | L | D | ? |  two boxes are COPIES BY POSITION (one head's ink drawn twice) only where their boxes overlap at least this much (intersection over union). A MEASUREMENT on the Litolff s |  |
| staged/claim_order.py:102 | `NO_OWNER = 255` | ? |  | C | ? | NO_OWNER = 255 |  |
| staged/claim_order.py:104 | `CR_INSIDE_SHARE = 0.5` | ratio |  | B | DECIDES |  a READ area reads a stroke when this share of the stroke's ink lies inside it (`claims.INSIDE_SHARE_MIN`, the register's one cut) CR_INSIDE_SHARE = 0.5 |  |
| staged/claim_order.py:107 | `SPLIT_PIECE_MIN_PX = 20` | px |  | E | ? | SPLIT_PIECE_MIN_PX = 20 |  |
| staged/claims.py:40 | `INSIDE_SHARE_MIN = 0.5` | ratio |  | B | REFUSES |  share of a box's own ink (bare staff-line runs left out) that must lie inside a claim for the claim to hold the box (the 2.177 meter cut, one cut for every owner: a mark |  |
| staged/claims.py:49 | `COLUMN_LEFT_REACH_SPACES = 2.0` | sp |  | C | ? |  the header column reaches this far left of the staff's start (the bracket and brace stand left of the system barline) COLUMN_LEFT_REACH_SPACES = 2.0 |  |
| staged/claims.py:51 | `THROUGH_COVER_MIN = 0.9` | ratio |  | B | ? |  the line test: a column of the box's ink covering this share of the box's own rows ... THROUGH_COVER_MIN = 0.9 |  |
| staged/claims.py:53 | `THROUGH_BEYOND_SPACES = 0.5` | sp |  | C | REFUSES |  ... that goes on past the box's top or bottom edge for this many staff spaces (a barline / bracket / brace stroke runs on; a head stops) THROUGH_BEYOND_SPACES = 0.5 |  |
| staged/claims.py:56 | `LEADING_EDGE_SPACES = 0.5` | sp |  | C | NARROWS |  2.176's two tests, kept as REFUSALS through the register (Sean 2026-10-20, 2.176 tiles 9/9 and 2.181 tiles 1 and 11: a bracket and a clef written blue are wrong): a box  |  |
| staged/claims.py:560 | `LABEL_MAX_COMPONENT_SPACES = 4.0` | sp |  | C | DECIDES |  an instrument name's ink is a component at most this tall (staff spaces): a brace, bracket or barline is taller LABEL_MAX_COMPONENT_SPACES = 4.0 |  |
| staged/claims.py:564 | `FOOTER_CLEAR_SPACES = 8.0` | sp |  | C | ? | FOOTER_CLEAR_SPACES = 8.0 |  |
| staged/clef_pagewide.py:460 | `F_SCAN_OVERLAP_SPACES = 3.0` | sp |  | C | ? | F_SCAN_OVERLAP_SPACES = 3.0 |  |
| staged/consequences.py:560 | `TWIN_BOX_MIN_OVERLAP = 0.8` | ? | L | D | ? |  How much of the smaller box the overlap must cover for two boxes to be the same ink. The 30 Litolff pairs overlap at 0.93-1.0 of the smaller box. TWIN_BOX_MIN_OVERLAP =  |  |
| staged/consequences.py:972 | `INK_PIECE_THIN_SPACES = 0.3` | sp |  | C | REFUSES |  A piece narrower than this (staff spaces) is a stem or a barline crumb -- never a head, a rest or a flag half (an eighth rest's thinnest half measures 0.62; a stem 0.1-0 |  |
| staged/consequences.py:975 | `INK_PIECE_EXPLAINED_SHARE = 0.5` | ratio |  | B | ? |  A piece with at least this share of its box inside the standing glyphs' boxes is explained by them. INK_PIECE_EXPLAINED_SHARE = 0.5 |  |
| staged/consequences.py:979 | `INK_EXPLAINER_MAX_WIDTH_SPACES = 8.0` | sp |  | C | DECIDES |  A glyph box wider than this (staff spaces) is a staff, a slur's rectangle or a hairpin -- mostly paper, so no account of the ink inside it (the same rule `gather._explai |  |
| staged/consequences.py:983 | `INK_PIECE_TALL_SPACES = 4.5` | sp |  | C | DECIDES |  A piece at least this tall and no wider than the next constant is a barline (a staff is 4 spaces; no rest or head is taller than 3.1) -- the cell is cut at its barlines  |  |
| staged/consequences.py:984 | `INK_PIECE_TALL_THIN_SPACES = 0.8` | sp |  | C | ? | INK_PIECE_TALL_THIN_SPACES = 0.8 |  |
| staged/consequences.py:989 | `INK_PIECE_MERGED_MIN_BOX_SP2 = 3.5` | sp |  | C | REFUSES |  A piece whose BOX is larger than this (staff spaces squared) is a merge of several marks, not a rest: the largest rest piece measured is 1.25 x 2.4 = 3.0 (a quarter rest |  |
| staged/detector_views.py:70 | `SAME_INK_IOU = 0.3` | ? |  | C | ? |  two boxes of one family on one piece of ink: IoU at least this, or either centre inside the other box SAME_INK_IOU = 0.3 |  |
| staged/dyad_head_rescue.py:47 | `COVERED_SHARE = 0.5` | ratio |  | B | NARROWS |  the candidate's ink is covered by a head box when this share of it lies inside the box COVERED_SHARE = 0.5 |  |
| staged/export.py:2402 | `SAME_INK_IOU = 0.3` | ? |  | C | ? |  The overlap above which two boxes of one family are ONE physical mark (the same figure `gather` groups on for ROADMAP 2.58b). SAME_INK_IOU = 0.3 |  |
| staged/gather.py:2463 | `CONTEST_IOU = 0.3` | ? | B | D | REFUSES |  distinct neighbours, and it drops three correctly-matched notes on Brahms. A clipped copy at IoU 0.1 is not a contest anyone can win, and a clipping-tolerant overlap mea |  |
| staged/gather.py:2570 | `MARK_GROUP_IOU = 0.3` | px |  | E | DECIDES |  The overlap (page pixels) above which two boxes of one family are ONE mark. The same figure the legacy `_CROSS_STAFF_DUPLICATE_IOU` was swept to (the lowest value costin |  |
| staged/gather.py:7757 | `_INK_GLYPH_BASE = 200000` | ? |  | C | ? |  ⚠️ Glyph indices for ink components, offset past both the detector's ordinals and `_CV_GLYPH_BASE`, so three readers can never collide in one cell's key space. A collisi |  |
| staged/gather.py:8436 | `INK_PIECE_MIN_AREA_SP2 = 0.1` | sp | B | D | REFUSES |  A piece smaller than this (staff spaces SQUARED) is speckle or a staff-line crumb, not a head/rest/flag. Measured on Brahms pdf 1 s0 staff 13 bar 5: the halves of an eig |  |
| staged/gather.py:8439 | `INK_PIECE_MAX_WIDTH_SPACES = 8.0` | sp |  | C | DECIDES |  A piece wider than this is a slur, a tie, a beam, a stave remnant -- never one symbol of a rest's or a head's size. INK_PIECE_MAX_WIDTH_SPACES = 8.0 |  |
| staged/gather.py:8443 | `INK_PIECE_BAND_SPACES = 1.5` | sp |  | C | NARROWS |  How far above/below the outer staff lines a piece's centre may lie and still be a candidate (rests stand inside the staff; heads, flags and ledger notes within a space o |  |
| staged/gather.py:9710 | `RECENTRE_OVERLAP_FRAC = 0.3` | px |  | E | NARROWS |  Two candidate windows are the "same" head once their boxes share more than this fraction of the smaller one's own area — the runner-up search skips these so it is not co |  |
| staged/gather.py:9960 | `RECENTRE_PART_MIN_INK_SPACES2 = 0.15` | ? |  | C | ? |  Ink needed in the window (staff-space squares) before a centroid is trusted. RECENTRE_PART_MIN_INK_SPACES2 = 0.15 |  |
| staged/gather.py:11870 | `SHAPE_MIN_INK_PX = 12` | px |  | E | NARROWS |  A shape read on fewer ink pixels than this is not trustworthy (a handful of anti-aliased edge pixels has no stable principal axis) -- `None`, not a guessed angle/elongat |  |
| staged/geometry.py:112 | `TIMESIG_DIGIT_DUPLICATE_IOU_MIN = 0.9` | count |  | B | DECIDES |  is read as another box's own ink, boxed a second time under a different class. Measured 0.94-0.96 on the two crop-verified instances above; 0.9 leaves margin below both  |  |
| staged/head_extent.py:28 | `MAX_INK_HEIGHT_SPACES = 1.35` | sp | L | D | NARROWS |  A head's own ink at most this tall to move its position (SMuFL 1.0 sp; Litolff tilted heads to ~1.3; two stacked heads a second apart measure ~1.5). A cut-off from two p |  |
| staged/head_extent.py:30 | `MATE_OVERLAP_SPACES = 0.15` | sp |  | C | DECIDES |  Another notehead box of the cell overlapping the ink rows by more than this (sp) is a chord-mate the ink ran into. MATE_OVERLAP_SPACES = 0.15 |  |
| staged/head_extent.py:43 | `EDGE_BAND_SHARE = 0.3` | ratio |  | B | ? |  r2: line rows are looked for in this share of the extent's height at each end (a stem or tail may run past the ledger), and stripping must leave at least `MIN_KEPT_SPACE |  |
| staged/head_extent.py:46 | `MIDDLE_SHARE = 0.4` | ratio |  | B | DECIDES |  r2: the head's own columns are read over this middle share of the extent's rows. MIDDLE_SHARE = 0.4 |  |
| staged/head_hole_position.py:33 | `MIN_INK_WIDTH_SPACES = 1.0` | sp | LB | D | REFUSES |  the head's own ink at least this wide (staff spaces; a Litolff/Brahms head is 1.3-1.7 wide): a narrower mark is not a head MIN_INK_WIDTH_SPACES = 1.0 | * rank 9: D, REFUSES; Litolff/Brahms heads 1.3-1.7 |
| staged/head_ink.py:46 | `CORE_SHARE = 0.4` | ratio |  | B | ? |  The head's columns are the run of head-tall columns that overlaps the box's own core (its middle `CORE_SHARE` across) ... CORE_SHARE = 0.4 |  |
| staged/head_ink.py:50 | `ROW_WIDE_SHARE = 0.5` | ratio |  | B | ? |  A head row: its ink, first to last, spans at least this share of the head's run of columns. ROW_WIDE_SHARE = 0.5 |  |
| staged/head_ink.py:62 | `FOREIGN_SHARE = 0.25` | ratio |  | B | ? |  Fix A: the head's ink lying inside a foreign box (accidental / key / flag / dynamic) whose own centre stands inside the trimmed head, at this share or more, is that mark |  |
| staged/inferences.py:2363 | `INK_PICK_MIN_SCORE = 0.3` | conf |  | A | NARROWS |  CONVENTION ASSUMED -- not measured on a corpus -- and NOT CONFIRMED by Sean; WHAT WOULD FALSIFY THEM: a blue dynamic that is the wrong letter on a print the margin would |  |
| staged/ink_attachment.py:29 | `SIDE_MIN_SP = 0.25` | sp | B | D | DECIDES |  ink on a side of the line counts as a SIDE when it is at least this tall (staff spaces): half of a rest block's own height (a block is at most half a space, `stroke_owne | * ROBUST example: B/A, both populations measured with a gap (Brahms whole rests vs heads on a line) |
| staged/ink_attachment.py:87 | `PAIR_OVERLAP_MIN = 0.5` | sp |  | B | ? |  two long verticals are "side by side" when their vertical extents overlap by at least this share of the shorter one (a sharp's two verticals overlap ~1.0; a natural's st |  |
| staged/ink_attachment.py:88 | `PAIR_GAP_SP = 1.0` | sp |  | C | ? | PAIR_GAP_SP = 1.0 |  |
| staged/ink_attachment.py:91 | `PAIR_BARS_MIN = 2` | count | B | D | ? |  ... and CROSSED: an accidental's verticals are joined by two bars (a sharp's two slanted bars, a natural's two), which the stroke map keeps as the pieces lying in the ga |  |
| staged/ink_attachment.py:94 | `PAIR_THICK_MIN_SP = 0.15` | sp | B | D | REFUSES |  ... and DRAWN: each vertical is a pen stroke, at least this thick (staff spaces). Measured on the 17 real accidentals Sean named with two long verticals on the four page | * rank 20: D; 17 accidentals Sean named, both plates |
| staged/ink_attachment.py:95 | `GAP_SLACK_PX = 2.0` | px |  | E | ? | GAP_SLACK_PX = 2.0 |  |
| staged/judged_claims.py:65 | `AGREE_MIN = 0.5` | count |  | A | ? | AGREE_MIN = 0.5 |  |
| staged/judged_claims.py:66 | `CONTRA_MIN = 0.3` | count |  | A | ? | CONTRA_MIN = 0.3 |  |
| staged/judged_claims.py:67 | `MIN_INK = 8` | ? |  | C | ? | MIN_INK = 8 |  |
| staged/letter_look.py:96 | `ALREADY_BOXED_SHARE = 0.3` | ratio |  | B | NARROWS |  Below this share of a candidate group's ink inside a DETECTOR dynamic box, the group is not already boxed. ALREADY_BOXED_SHARE = 0.3 |  |
| staged/letter_look.py:99 | `COVER_SHARE = 0.5` | ratio |  | B | REFUSES |  A head/rest box whose ink lies this much inside the read letters' boxes is the letters' ink (the refusal ADJUDICATE makes reads this share). COVER_SHARE = 0.5 |  |
| staged/letter_look.py:422 | `EVIDENCE_COVER = 0.3` | ratio |  | B | ? |  How much of a slot's box a hypothesis's box must cover for the hypothesis to be about THAT ink (the second `f` of an `ff` is boxed wider than its ink). EVIDENCE_COVER =  |  |
| staged/meter_object.py:47 | `PAD_STROKES = 1.0` | ? |  | B | ? |  the area is padded by this many staff-line thicknesses PAD_STROKES = 1.0 |  |
| staged/meter_object.py:259 | `COLUMN_MIN_SHARE = 0.4` | ratio |  | B | ? |  the column is real when this share of the system's staves (and at least `COLUMN_MIN_STAVES`) have a pair in it COLUMN_MIN_SHARE = 0.4 |  |
| staged/one_ink.py:51 | `ONE_INK_IOU_MIN = 0.5` | count |  | A | REFUSES |  The overlap that means "the same ink". 2.185 checked it on crops (20/20 random crops at >= 0.5 real doubles; the 0.3-0.5 band was half neighbours). A convention checked  |  |
| staged/page_accidental_ink.py:57 | `OWN_BOX_SHARE = 0.5` | ratio |  | B | DECIDES |  a head box overlapped this much by the cluster is the cluster's own box (a sharp boxed as a head), not the note it is by (the register's cover cut) OWN_BOX_SHARE = 0.5 |  |
| staged/page_accidental_ink.py:59 | `BOXED_SHARE_MIN = 0.5` | ratio |  | B | ? |  a detector box of an accidental / key class holds a stroke when this share of the stroke's box lies in it (the register's cover cut, `stroke_map.COVER_SHARE_MIN`) BOXED_ |  |
| staged/page_accidental_ink.py:61 | `BOXED_OVERLAP_MIN = 0.25` | count |  | B | ? |  the cluster's ink and a detector accidental / key box overlap by this share of EITHER: the detector boxed this mark (its box may sit off the ink, 2.247 r2) BOXED_OVERLAP |  |
| staged/page_arc_bind.py:71 | `MIN_PIECE_SP = 3.0` | sp |  | C | REFUSES |  a stretch of tracked ink shorter than this (spaces of x) between a bridge and the run's end is a TAIL, not an arc: dropped. Two longer stretches are two arcs (each bound |  |
| staged/page_arc_bind.py:216 | `LAND_OUTER_SHARE = 0.25` | ratio |  | B | REFUSES |  ... and only in the outer share of the run's width at that end (the landing is the arc's END, not a note it passes over) LAND_OUTER_SHARE = 0.25 |  |
| staged/page_arcs.py:58 | `CLAIM_GAP_SP = 6.0` | sp |  | C | ? | CLAIM_GAP_SP = 6.0 the longest stretch a track waits inside a blanked region (a dynamic, a word, a head cluster) on its own slope |  |
| staged/page_arcs.py:59 | `CLAIM_TOL_PER_SP = 0.05` | sp |  | C | ? | CLAIM_TOL_PER_SP = 0.05 the tolerance for the ink that comes out grows this much per space of blanked stretch crossed |  |
| staged/page_arcs.py:60 | `MIN_OWN_INKED = 0.45` | ? |  | C | ? | MIN_OWN_INKED = 0.45 inked columns that are the run's own (not counted as claimed by another mark) / span |  |
| staged/page_arcs.py:61 | `MIN_INKED = 0.6` | ? |  | C | ? | MIN_INKED = 0.6 inked columns / span |  |
| staged/page_arcs.py:78 | `HUG_SHARE = 0.5` | ratio |  | B | ? | HUG_SHARE = 0.5 (share of the body) |  |
| staged/page_arcs.py:88 | `WITNESS_SHARE = 0.5` | sp |  | B | ? | WITNESS_SHARE = 0.5 a detector arc box witnesses a run when the run covers this share of the box's width inside the box (grown 0.5 sp) |  |
| staged/page_arcs.py:94 | `LINK = 1` | ? |  | C | ? | LINK = 1 r3: join fragments of one arc that a joint curve fit and the raw ink under the gap explain |  |
| staged/page_arcs.py:95 | `LINK_GAP_SP = 6.0` | sp |  | C | ? | LINK_GAP_SP = 6.0 the widest gap two fragments are joined across |  |
| staged/page_arcs.py:96 | `LINK_MIN_SP = 0.6` | sp |  | C | ? | LINK_MIN_SP = 0.6 the shortest fragment that is joined |  |
| staged/page_arcs.py:97 | `LINK_RES_SP = 0.08` | sp |  | C | ? | LINK_RES_SP = 0.08 rms of the joint fit over both fragments |  |
| staged/page_arcs.py:98 | `LINK_DEV_SP = 0.25` | sp |  | C | ? | LINK_DEV_SP = 0.25 the largest deviation of either fragment's points from the joint fit |  |
| staged/page_arcs.py:99 | `LINK_SUPPORT = 0.7` | ? |  | B | ? | LINK_SUPPORT = 0.7 the share of the gap's columns that carry raw ink within LINK_SUP_SP of the fit |  |
| staged/page_arcs.py:100 | `LINK_SUP_SP = 0.3` | sp |  | C | ? | LINK_SUP_SP = 0.3 |  |
| staged/page_arcs.py:101 | `LINK_YNEAR_SP = 2.5` | sp |  | C | ? | LINK_YNEAR_SP = 2.5 fragments whose facing ends lie further apart than this are not tried |  |
| staged/page_arcs.py:105 | `THICK_SHARE = 0.25` | ratio |  | B | ? | THICK_SHARE = 0.25 ... and at least this share of its columns thicker than RUN_MAX_SP |  |
| staged/page_arcs.py:117 | `LINK_PLAIN_GAP_SP = 1.3` | sp |  | C | ? | LINK_PLAIN_GAP_SP = 1.3 a gap this short needs only the raw ink under it (a carved rule, a stem); a longer one must lie in what claims / hides ink |  |
| staged/page_arcs.py:118 | `LINK_EXPL_SHARE = 0.8` | ratio |  | B | ? | LINK_EXPL_SHARE = 0.8 |  |
| staged/page_arcs.py:119 | `LINK_QUAD_SP = 8.0` | sp |  | C | DECIDES | LINK_QUAD_SP = 8.0 the joint fit is a quadratic up to this wide, a quartic beyond |  |
| staged/page_claim_names.py:56 | `WHOLLY_INSIDE_SLACK_PX = 1.0` | px |  | E | DECIDES |  a page-wide claim owns a stroke only wholly inside it, this many px of slack (`adjudicators/stroke_owner._areas`: "+1 px") WHOLLY_INSIDE_SLACK_PX = 1.0 |  |
| staged/page_heads.py:55 | `FOLD_IOU = 0.5` | ? |  | C | ? |  two notehead boxes are one head at this IoU (unison / second neighbours are ~0; a double box is >0.5) FOLD_IOU = 0.5 |  |
| staged/page_heads.py:57 | `COVER_SHARE_MIN = 0.5` | ratio |  | B | ? |  the register's one cover cut (`stroke_map.COVER_SHARE_MIN`) COVER_SHARE_MIN = 0.5 |  |
| staged/page_heads.py:489 | `SHARE_MIN = 0.5` | px |  | E | ? |  two boxes share a head when the pixels they share are at least this share of the smaller one's head ink (the register's one cut, `page_marks.SHARE_MIN`) SHARE_MIN = 0.5 |  |
| staged/page_heads.py:513 | `CLAIM_SHARE_MIN = 0.5` | ratio |  | B | DECIDES |  a stroke is the head's claimed ink when this share of it lies in the head's oval ... CLAIM_SHARE_MIN = 0.5 |  |
| staged/page_heads.py:515 | `CLAIM_MAX_W_SP = 3.0` | sp |  | C | ? |  ... it is no bigger than a head (`stroke_owner.HEAD_MAX_W_SP` / `HEAD_MAX_H_SP`) ... CLAIM_MAX_W_SP = 3.0 |  |
| staged/page_heads.py:516 | `CLAIM_MAX_H_SP = 1.6` | sp |  | C | ? | CLAIM_MAX_H_SP = 1.6 |  |
| staged/page_heads.py:534 | `CLAIM_UNION_MIN_SP = 0.6` | sp |  | C | REFUSES |  quarter note" 0.38 x 1.52 sp); a taller one is more than one head's ink ("half of a quarter note rest", 1.02 x 1.59 sp: the detector boxed the rest as a notehead and no  |  |
| staged/page_heads.py:535 | `CLAIM_UNION_MAX_H_SP = 2.0` | sp |  | C | ? | CLAIM_UNION_MAX_H_SP = 2.0 |  |
| staged/page_ledger.py:44 | `LINK_SHARE_MIN = 0.8` | ratio |  | B | DECIDES |  a cell stroke joins a page stroke when at least this share of its own ink lies on that one page stroke (module doc) LINK_SHARE_MIN = 0.8 |  |
| staged/page_marks.py:52 | `SHARE_MIN = 0.5` | ratio |  | B | ? |  the share of the smaller box's ink the two boxes must share (module doc: the register's one cut, not tuned) SHARE_MIN = 0.5 |  |
| staged/page_owner.py:64 | `INSIDE_SPACES = 0.75` | sp |  | C | ? |  a mark whose centre is no more than this many of the staff's own spaces beyond its outer line stands IN that staff's band (on a line, between lines, or in the space just |  |
| staged/page_owner.py:70 | `SAME_TRACE_SHARE = 0.5` | ratio |  | B | ? |  two traces / two wedge boxes are ONE mark when they cover the same page ink for this share of the smaller (the register's one cut) SAME_TRACE_SHARE = 0.5 |  |
| staged/page_owner.py:72 | `BOXED_AS_SHARE = 0.5` | ratio |  | B | ? |  a page mark's box lies inside a wedge when this share of its box area is inside the wedge's box BOXED_AS_SHARE = 0.5 |  |
| staged/page_strokes.py:47 | `CARVE_PAD_PX = 1` | px |  | E | REFUSES |  the carve is the rule's own measured width (+ this many px each side), never a fixed fraction of a space: a head touching the rule keeps its ink CARVE_PAD_PX = 1 |  |
| staged/page_strokes.py:49 | `CARVE_CORE_PX = 2` | px |  | E | ? |  how far from the fitted line the rule's core is looked for (px either side of the line), and the widest run that can still be a rule (spaces) CARVE_CORE_PX = 2 |  |
| staged/page_strokes.py:50 | `CARVE_MAX_WIDTH_SPACES = 0.9` | sp |  | C | ? | CARVE_MAX_WIDTH_SPACES = 0.9 |  |
| staged/page_strokes.py:52 | `CARVE_RUN_MIN_SPACES = 1.0` | sp |  | C | DECIDES |  a carved stretch is a rule only in runs this long (a slur crossing the column is ink on the line for a few rows); gaps up to this are bridged CARVE_RUN_MIN_SPACES = 1.0 |  |
| staged/page_strokes.py:53 | `CARVE_GAP_BRIDGE_SPACES = 0.25` | sp |  | C | ? | CARVE_GAP_BRIDGE_SPACES = 0.25 |  |
| staged/page_strokes.py:57 | `BOX_DEDUP_PX = 2` | px |  | E | ? |  twin detector boxes (the same mark boxed by two cells) closer than this many px at every edge are one box for the splitter BOX_DEDUP_PX = 2 |  |
| staged/page_tremolo.py:52 | `OWN_SHARE_MIN = 0.5` | ratio |  | B | DECIDES |  a stroke the slash's box holds this much of (its own box's area inside the slash's box) is the slash's (the register's cover cut, `claims.INSIDE_SHARE_MIN`) OWN_SHARE_MI |  |
| staged/page_tremolo.py:62 | `HELD_SHARE_MIN = 0.5` | ratio |  | B | ? | HELD_SHARE_MIN = 0.5 |  |
| staged/record.py:49 | `STROKE_GLYPH_BASE = 375000` | ? |  | C | ? |  ROADMAP 2.195/2.198: glyph ordinals from here (below `human_evidence.HUMAN_GLYPH_BASE`, 400,000) number the STROKES of a cell (`Q.STROKE`). `Log.subjects(Kind.GLYPH)` do |  |
| staged/second_hollow.py:37 | `DUPLICATE_IOU = 0.5` | ? |  | C | ? |  Two boxes of the SECOND detector this close are one head boxed twice (Half and Whole classes are not suppressed across classes). DUPLICATE_IOU = 0.5 |  |
| staged/stem_end_heads.py:57 | `OWNED_SHARE = 0.5` | ratio | B | D | REFUSES |  a CV stem standing inside another mark's box for at least this share of its length is that mark's own upright (the body of a Breitkopf quarter rest, a flat's stem, a cle |  |
| staged/stem_end_heads.py:251 | `CLAIM_FLOOR = 0.25` | ? |  | C | REFUSES |  the production floor: another mark's box below it is not a claim on the ink CLAIM_FLOOR = 0.25 |  |
| staged/stem_end_heads.py:378 | `CLAIM_SHARE_MIN = 0.5` | ratio |  | B | ? |  share of the box held by a claim (`claims.INSIDE_SHARE_MIN`, the register's one cut, restated: this module imports nothing) CLAIM_SHARE_MIN = 0.5 |  |
| staged/stem_strokes.py:51 | `MIN_VERTICAL_OVERLAP_SHARE = 0.4` | ratio |  | B | ? |  A stroke must share at least this share of the head box's height to be beside the head at all. MIN_VERTICAL_OVERLAP_SHARE = 0.4 |  |
| staged/stroke_map.py:42 | `TARGET_SP_PX = 16.0` | sp |  | C | ? | TARGET_SP_PX = 16.0 |  |
| staged/stroke_map.py:44 | `COVER_THRESHOLD = 96` | px |  | C | ? |  A reduced pixel is ink when this much (of 255) of its source was. A tie's end / ledger rung is ~2 px thick at this scale. COVER_THRESHOLD = 96 |  |
| staged/stroke_map.py:45 | `V_MIN_SPACES = 1.5` | sp |  | C | ? | V_MIN_SPACES = 1.5 |  |
| staged/stroke_map.py:46 | `H_MIN_SPACES = 1.0` | sp |  | C | ? | H_MIN_SPACES = 1.0 |  |
| staged/stroke_map.py:48 | `H_MIN_ASPECT = 2.5` | ratio |  | B | ? |  length^2 / area of a horizontal piece: beam 5-30, rung 8+, filled head's lens 1.3-1.8. H_MIN_ASPECT = 2.5 |  |
| staged/stroke_map.py:52 | `MIN_AREA_SP2 = 0.05` | ? |  | C | ? | MIN_AREA_SP2 = 0.05 |  |
| staged/stroke_map.py:53 | `PROFILE_SAMPLES = 12` | ? |  | C | ? | PROFILE_SAMPLES = 12 |  |
| staged/stroke_map.py:54 | `ANCHOR_STRIDE_SPACES = 3.0` | sp |  | C | ? | ANCHOR_STRIDE_SPACES = 3.0 |  |
| staged/stroke_map.py:55 | `ANCHOR_HALF_WINDOW_SPACES = 1.5` | sp |  | C | ? | ANCHOR_HALF_WINDOW_SPACES = 1.5 |  |
| staged/stroke_map.py:130 | `WIDE_PART_MIN_SP2 = 0.25` | ? |  | C | REFUSES |  a wide part smaller than this is a blip on a stem (an erase scar), not a mark fused to it: it goes back to the stem WIDE_PART_MIN_SP2 = 0.25 |  |
| staged/stroke_map.py:140 | `WAIST_SHARE_MAX = 0.75` | ratio |  | B | ? |  a stack is cut only at a row this much narrower than the narrower of its two halves' widest rows (a real neck between two ovals); a stack with no such row stays whole (` |  |
| staged/stroke_map.py:173 | `TOUCH_SIDE_MIN_SHARE = 0.15` | ratio |  | B | ? |  a piece is cut along the two boxes' boundary only when each side holds at least this share of its ink in its own box ALONE TOUCH_SIDE_MIN_SHARE = 0.15 |  |
| staged/stroke_map.py:175 | `TOUCH_SIDE_MIN_SP2 = 0.02` | sp |  | C | REFUSES |  ... and at least this much ink (staff spaces^2, ~5 reduced px: under it the side is a scan edge, not a mark's ink) TOUCH_SIDE_MIN_SP2 = 0.02 |  |
| staged/stroke_map.py:184 | `TOUCH_UNDECIDED_MAX_SHARE = 0.5` | ratio |  | B | NARROWS |  ink in both boxes or in neither goes to the side it is nearer to, through the piece's own ink; more of it than this and the boxes do not tell where one mark stops: the p |  |
| staged/stroke_map.py:272 | `Stroke.component_n_strokes = 1` | ? |  | C | ? | component_n_strokes: int = 1 |  |
| staged/stroke_map.py:432 | `COVER_SHARE_MIN = 0.5` | ratio |  | B | REFUSES |  A box COVERS a stroke when at least this share of the stroke's ink lies inside the box. Not tuned: it is the register's one cut (`claims.INSIDE_SHARE_MIN`, 2.177: "a mar |  |
| staged/stroke_owner.py:59 | `COVER_SHARE_MIN = 0.5` | ratio |  | B | ? |  A box COVERS a stroke when at least this share of the stroke's ink lies inside it (`stroke_map.COVER_SHARE_MIN`, the register's cut). COVER_SHARE_MIN = 0.5 |  |
| staged/stroke_owner.py:61 | `ATTACH_SHARE_MIN = 0.15` | ratio |  | B | DECIDES |  A stroke partly inside a mark's box (at least this share) that touches >= `ATTACH_MIN_TOUCHES` strokes the mark owns joins the mark. ATTACH_SHARE_MIN = 0.15 |  |
| staged/stroke_owner.py:62 | `ATTACH_MIN_TOUCHES = 2` | count |  | A | ? | ATTACH_MIN_TOUCHES = 2 |  |
| staged/stroke_owner.py:144 | `Ink.angle = 0.0` | ? |  | C | ? | angle: float = 0.0 principal axis, degrees (0 horizontal, 90 vertical) |  |
| staged/stroke_owner.py:186 | `MARK_MAX_AREA_SP2 = 0.8` | ? |  | C | ? | MARK_MAX_AREA_SP2 = 0.8 a dot, a staccato, a fermata's dot |  |
| staged/stroke_owner.py:187 | `MARK_MAX_LEN_SP = 2.5` | sp |  | C | ? | MARK_MAX_LEN_SP = 2.5 a fermata's arc, a tenuto |  |
| staged/stroke_owner.py:196 | `BLOCK_MAX_H_SP = 1.0` | sp |  | A | REFUSES |  ... a block is half a space thick nominally; MEASURED 2.205 (owner_shape_sizes.py, the blobs under KEPT whole / half rest boxes): median 0.76, p95 0.88 sp on both plates |  |
| time_signature_locator.py:211 | `TimeSignatureLocatorConfig.cut_stroke_centre_frac = 0.1` | ratio |  | B | ? | cut_stroke_centre_frac: float = 0.10 |  |

## other (63; A 4, B 6, C 43, D 4, E 2, n/a 4)

| file:line | constant = value | unit | plates | cls | effect | comment (excerpt) | hand |
|---|---|---|---|---|---|---|---|
| input_domain.py:40 | `ENGRAVED_MIN_DRAWINGS = 50` | count |  | C | ? |  Nearest measured populations: 4 (busiest scan page) / 428 (lightest engraved music page). ENGRAVED_MIN_DRAWINGS = 50 |  |
| input_domain.py:44 | `DEFAULT_CLASSIFY_PAGES = 12` | ? |  | C | ? |  Verdict pages examined when the caller does not name pages. Any-scan-wins means extra pages only ever flip the verdict TOWARD scanned, and 12 covers every cover-sheet/bl |  |
| input_domain.py:75 | `DomainClassification.ms = 0.0` | ? |  | C | ? | ms: float = 0.0 |  |
| instruments.py:142 | `Instrument.chromatic = 0` | ? |  | C | ? | chromatic: int / None = 0 sounding = written + chromatic; None = key-dependent |  |
| staged/adjudicators/family_precision.py:187 | `_BAND_TOP_STEP = 8.0` | count |  | A | ? |  The staff band, in the same frame. A ledger line cannot be inside it. _BAND_TOP_STEP = 8.0 |  |
| staged/adjudicators/family_precision.py:213 | `TALL_MIN_HEIGHT_SPACES = 0.5` | sp |  | C | DECIDES |  an embarrassment: the height distribution is p50 0.28, p95 0.37, p99 0.41 on all three records, so 0.5 sits well past the population's own tail and catches only ink that |  |
| staged/adjudicators/identity.py:875 | `FAMILY_BLOCK_MAX_DEFICIT = 1` | ? |  | C | REFUSES |  ⚠️ A block of 1-2 staves is refused by this same number rather than by a separate floor, which matters because that case is UNMEASURED -- this plate never prints one. FA |  |
| staged/adjudicators/identity.py:1110 | `_MAX_ASSIGNMENTS = 200000` | ? |  | C | NARROWS |  A system this ambiguous is a "cannot tell", not a slow one. _MAX_ASSIGNMENTS = 200000 |  |
| staged/adjudicators/movement.py:92 | `LABEL_LENGTH_RATIO = 1.5` | ratio |  | B | ? |  label length, OR this many more characters outright -- "Violoncello" vs "Vc." is both; "Fl. II" vs "Fl." is neither, which is deliberate: a continuation system that keep |  |
| staged/adjudicators/movement.py:93 | `LABEL_LENGTH_DELTA = 4` | ? |  | C | ? | LABEL_LENGTH_DELTA = 4 |  |
| staged/adjudicators/movement.py:97 | `INDENT_RATIO = 1.15` | ratio |  | B | ? |  The top staff's own left edge (`Q.STAFF_EXTENT[0]`) at least this much wider than the document's OWN median indent. INDENT_RATIO = 1.15 |  |
| staged/adjudicators/movement.py:101 | `MIN_CUES_REQUIRED = 2` | ? |  | C | ? |  CLAUDE.md's brief: "Require at least 2-3 cues." Two, not three -- see the module docstring's WHAT WOULD FALSIFY IT. MIN_CUES_REQUIRED = 2 |  |
| staged/adjudicators/repeats.py:50 | `MIN_STAVES = 2` | count |  | A | ? | MIN_STAVES = 2 |  |
| staged/adjudicators/rhythm.py:6769 | `EVENT_X_TOLERANCE_WIDTHS = 0.6` | px |  | E | ? |  default, reproduced so the record's grouping and the exporter's are ONE rule rather than two that can drift. Adaptive rather than a pixel count: 0.6 of the MEAN notehead |  |
| staged/adjudicators/rhythm.py:6773 | `EVENT_X_TOLERANCE_FALLBACK_PX = 30.0` | px |  | E | ? |  Fallback when the bar holds no notehead to measure a width from — the same number, and the same reason, as the legacy fallback. EVENT_X_TOLERANCE_FALLBACK_PX = 30.0 | * rank 23: E-suspect (legacy fallback) |
| staged/adjudicators/rhythm.py:7409 | `W_CHANGE_GLYPH_PAIR = 3.0` | ? |  | n/a | DECIDES |  One staff that reads a COMPLETE meter (a numerator over a denominator) at a mid-staff bar. Alone it clears `METER_CHANGE_FLOOR` -- which is Sean's ordering taken literal |  |
| staged/adjudicators/rhythm.py:7413 | `W_CHANGE_GLYPH_LOOSE = 0.5` | ? |  | n/a | ? |  A digit at that bar that does NOT pair into a meter. Weak, and deliberately so: it says "something meter-shaped is printed here" without saying what. W_CHANGE_GLYPH_LOOS |  |
| staged/adjudicators/rhythm.py:7418 | `W_CHANGE_BAR_FITS = 1.0` | ? |  | n/a | ? |  Each subsequent bar whose length matches the proposed new meter, and each that does not. ⚠️ "for how long - the longer the more likely" is expressed by these ACCUMULATIN |  |
| staged/adjudicators/rhythm.py:7419 | `W_CHANGE_BAR_CONTRADICTS = -1.0` | ? |  | n/a | ? | W_CHANGE_BAR_CONTRADICTS = -1.0 |  |
| staged/adjudicators/rhythm.py:9501 | `ONSET_COLUMN_TOLERANCE_SPACES = 0.1` | sp |  | B | ? |  reshuffle of the same events inside the same bar span gives 0.122. The separation is ~4x at the median and holds at every density, while the mere EXISTENCE of a near nei |  |
| staged/adjudicators/rhythm.py:9504 | `ONSET_COLUMN_MIN_WITNESSES = 2` | count |  | A | DECIDES |  Below this many staves a "column" is not corroboration, it is one reading. ONSET_COLUMN_MIN_WITNESSES = 2 |  |
| staged/bar_length.py:36 | `EPS = 1e-06` | ? |  | C | ? | EPS = 1e-6 |  |
| staged/box_kind.py:80 | `OPEN_SP = 0.7` | sp |  | C | ? | OPEN_SP = 0.7 |  |
| staged/box_kind.py:83 | `REMAINDER_CLOSE_SP = 0.45` | sp |  | C | ? |  the remainder's harder look: a hollow head's ring opened on both sides by the staff-line erase closes at this size REMAINDER_CLOSE_SP = 0.45 |  |
| staged/box_kind.py:91 | `BAND_MIN_H_SP = 0.9` | sp |  | C | ? |  a band cut into merged heads must be at least this tall (a filled head ~1.0+ sp; a beam, even merged with a line remnant, ~0.8) BAND_MIN_H_SP = 0.9 |  |
| staged/box_kind.py:93 | `RUN_SIDE_SP = 0.6` | sp |  | C | ? |  the run test: the ink beside a blob (this far each side) over its own rows; a beam piece measured 0.82 / 0.91 RUN_SIDE_SP = 0.6 |  |
| staged/box_kind.py:95 | `GRID_TOL_STEPS = 0.3` | count |  | A | ? | GRID_TOL_STEPS = 0.3 |  |
| staged/box_kind.py:366 | `TALL_MIN_H_SP = 1.8` | sp | L | D | ? |  a head box at least this tall (staff spaces) may hold two heads: one head ~1.0-1.1 sp printed, a detector box over one head measured 1.23-1.65 sp on Litolff (2.250 censu | * D; Litolff 2.250 census |
| staged/box_kind.py:590 | `GLYPH_BOX_MAX_K = 1.5` | sp | LB | D | DECIDES |  printed at its SMuFL size (`glyphBBoxes`; double sharp 0.99 x 1.01 sp); a box more than `GLYPH_BOX_MAX_K` x that in either axis holds more than the glyph (2.247: Litolff |  |
| staged/consequences.py:2411 | `MARKING_MAX_GAP_SPACES = 1.5` | sp |  | C | ? |  How far apart a word and a dynamic may stand and still be one marking, in staff spaces (Sean 2026-10-08: "same line, close" -- about one and a half spaces, the reach `di |  |
| staged/detector_views.py:66 | `READ_FLOOR = 0.05` | ? |  | B | DECIDES |  a view box is READ at this floor so a phase that scores 0.05-0.25 still counts toward the median READ_FLOOR = 0.05 |  |
| staged/detector_views.py:68 | `KEEP_FLOOR = 0.25` | ? |  | B | REFUSES |  the median over phases must clear the production GATHER floor (`OMR_CONF_THRESHOLD`, 0.25) -- not a new cut KEEP_FLOOR = 0.25 |  |
| staged/export.py:109 | `RELOCATE_COLLISION_SPACES = 0.75` | sp |  | C | REFUSES |  A relocated head within this many staff spaces (page pixels, both axes) of a head the owner's cell already holds is the SAME ink, not a second note. RELOCATE_COLLISION_S |  |
| staged/gather.py:584 | `RESCUE_CONF_FLOOR = 0.1` | conf | L | D | ? |  only on a cell that already failed both the production pass and 2.52's own ink search. ROADMAP 2.53 measured it: a `--conf 0.10` rerun recovered a notehead/rest box in 2 |  |
| staged/gather.py:4425 | `_CV_GLYPH_BASE = 100000` | ? |  | C | ? |  index so the two readers can never collide in one cell's key space. A collision here would not raise -- it would silently merge a CV reading and a detector reading into  |  |
| staged/gather.py:5138 | `_VERTICAL_RUN_GLYPH_BASE = 300000` | ? |  | C | NARROWS |  would silently merge a candidate row and some other reader's row into one subject -- and a subject's last coordinate being a positional index is exactly how `omr-ink-ext |  |
| staged/gather.py:8523 | `NARROW_BOX_JOIN_GAP_SPACES = 0.25` | sp |  | C | DECIDES |  A piece joins the ink under a narrow box when it lies within this many staff spaces of what is already joined (staff-line erasure splits an eighth rest into a blob and a |  |
| staged/gather.py:8526 | `NARROW_BOX_JOIN_MAX_HEIGHT_SPACES = 3.5` | sp |  | C | REFUSES |  A piece taller than this is never joined (a stem, a beam, a slur): it is not a rest's tail, and joining it would grow the ink without limit. NARROW_BOX_JOIN_MAX_HEIGHT_S |  |
| staged/gather.py:9688 | `RECENTRE_MAX_DY_SPACES = 0.6` | sp |  | C | REFUSES |  horizontally"). Not grown past what a measured sliver needs (`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §18: the 8-of-8 sampled slivers are 0.29-0.4 sp wide aga |  |
| staged/gather.py:9689 | `RECENTRE_MAX_DX_SPACES = 0.4` | sp |  | C | ? | RECENTRE_MAX_DX_SPACES = 0.4 |  |
| staged/gather.py:9694 | `RECENTRE_STEP_SPACES = 0.1` | sp |  | C | ? |  The search grid's own step. Fine enough that a real head's peak fill is not skipped between two tested offsets; coarse enough that the ~2,347- 3,337 regular noteheads pe |  |
| staged/gather.py:9822 | `RECENTRE_BOX_SIZE_GATE = 0.7` | sp | B | D | REFUSES |  11.2% of Brahms's 765 -- falls under 0.7. That decile is where the genuine slivers CLAUDE.md §10 names live (a confirmed Brahms sliver measured 0.24 sp tall against a 1. |  |
| staged/gather.py:9946 | `RECENTRE_PART_SIZE_GATE = 0.9` | ? |  | C | NARROWS |  A box is a candidate only where it is clearly short of a head in width OR height (the smaller of the two ratios to the standard head under this). RECENTRE_PART_SIZE_GATE |  |
| staged/gather.py:9949 | `RECENTRE_PART_MIN_SHIFT_SPACES = 0.15` | sp |  | C | DECIDES |  ... and only where the head's ink centre sits at least this far (staff spaces, vertical) from the box's centre; closer is a box already on its head. RECENTRE_PART_MIN_SH |  |
| staged/gather.py:9956 | `RECENTRE_PART_HALF_WINDOW_SPACES = 0.8` | sp |  | C | ? |  The ink window the centroid is taken over: half-height/half-width in staff spaces around the box centre (a head is ~1.1 x 1.4; 0.7 keeps a neighbouring line or head out; |  |
| staged/gather.py:9966 | `RECENTRE_PART_ONLY_ABOVE_CENTRE = 0.75` | ? |  | C | ? |  smaller centre reading (raw / line rows left out) is above this. Restates `rhythm.HEAD_FILL_HOLLOW_CENTER_MAX` (2.23/2.73; `rhythm` imports this module, so the reverse i |  |
| staged/gather.py:9981 | `RECENTRE_PART_WINDOWS = [0.75, 0.8, 0.85, 0.9]` | ? |  | C | ? |  (0.38 / 0.36 / 0.36 at 0.75 / 0.8 / 0.9). Windows 0.75-0.9 are the ones that contain a whole head; MEASURED, not derived: five window sets x two spread cuts on Sean's tr |  |
| staged/gather.py:9982 | `RECENTRE_PART_MAX_SPREAD_SPACES = 0.1` | sp |  | C | ? | RECENTRE_PART_MAX_SPREAD_SPACES = 0.1 |  |
| staged/gather.py:9983 | `RECENTRE_PART_ITERATIONS = 40` | ratio |  | B | ? | RECENTRE_PART_ITERATIONS = 40 |  |
| staged/gather.py:9984 | `RECENTRE_PART_CONVERGED_SPACES = 0.01` | sp |  | C | ? | RECENTRE_PART_CONVERGED_SPACES = 0.01 |  |
| staged/inferences.py:57 | `COLUMN_MIN_INDEPENDENT_WITNESSES = 2` | ? |  | C | REFUSES |  different question (forming vs believing). What carries the weight here is not the floor but the UNANIMITY requirement below: a single dissenting witness refuses the who |  |
| staged/inferences.py:1712 | `BarOutcome.members = 0` | ? |  | C | ? | members: int = 0 bare-stem narrowings in the bar |  |
| staged/inferences.py:1713 | `BarOutcome.unknowns = 0` | ? |  | C | DECIDES | unknowns: int = 0 events with more than one admitted length |  |
| staged/inferences.py:1714 | `BarOutcome.landings = 0` | ? |  | C | DECIDES | landings: int = 0 assignments of the unknowns that land the bar |  |
| staged/inferences.py:1715 | `BarOutcome.forced = 0` | ? |  | C | ? | forced: int = 0 bare-stem members the arithmetic forces |  |
| staged/inferences.py:1716 | `BarOutcome.ambiguous = 0` | ? |  | C | ? | ambiguous: int = 0 members two landings disagree about |  |
| staged/inferences.py:1717 | `BarOutcome.lengthening_unwitnessed = 0` | ? |  | C | ? | lengthening_unwitnessed: int = 0 2.97: forced, but longer than the reader's best and the bar's ink is not wholly explained |  |
| staged/inferences.py:1718 | `BarOutcome.shortened_refused = 0` | ? |  | C | REFUSES | shortened_refused: int = 0 forced to the shorter length, refused (Sean 2026-10-12) |  |
| staged/page_marks.py:54 | `NEAR_MISS = 0.05` | ? |  | C | REFUSES |  a refused pair this close under the cut is a NEAR MISS, recorded as a margin only (step 2: never tuned on two plates) NEAR_MISS = 0.05 |  |
| staged/record.py:50 | `HUMAN_GLYPH_BASE_FLOOR = 400000` | ? |  | C | ? | HUMAN_GLYPH_BASE_FLOOR = 400_000 |  |
| staged/record.py:3467 | `SPELLED_KEEP_IDS = 20000000` | ? |  | C | ? |  ROADMAP 2.249: spelled-out `LazyBasis` tuples kept, by ids held, least recently used out first -- speed only. SPELLED_KEEP_IDS = 20_000_000 |  |
| staged/record.py:3699 | `RECORD_FORMAT = 2` | ? |  | C | DECIDES |  ⚠️ ROADMAP 2.249 m8 (Sean 2026-11-02, "change the record format"): the record FILE format. 1 (no `format` key): every verdict's `basis` is spelled out. 2: an ADJUDICATE  |  |
| staged/record.py:3704 | `CLOSURE_MEMO_MAX_IDS = 60000000` | ? |  | C | ? |  ROADMAP 2.249: the closure memo holds at most this many ids in all (~2-3 GB of frozensets), least recently used out first. Speed only. CLOSURE_MEMO_MAX_IDS = 60_000_000 |  |

## Method note on the class and effect columns

cls: D if the comment names Litolff/Beethoven or Brahms/Breitkopf as the source; E if a pixel unit not in a reduced/canonical frame; A if the comment names a convention, SMuFL/Bravura, Gould, or the notation; B if a ratio/share or the comment says local / own / median / line thicknesses; C otherwise (an absolute figure in staff spaces, a detector score, or an unexplained number). n/a: weights, env names, time and token budgets, grid sizes. C is therefore a catch-all and over-counts: some C rows are geometry the notation fixes (half a space from a line to its space) and are really A. effect: NARROWS if the comment says narrows / candidate / abstain / cannot tell / declines; REFUSES if refuse / drop / not a / reject / sliver / unread; DECIDES if decide / is a / reads / belongs / owns / joins; ? otherwise. 1,004 of 1,535 comments say none of these, so the effect of most constants is NOT known from this table.
## Hand-checked findings (summary; the final report carries the ranked list)

- Readers branching on a plate name, document id or page number: **none**. The only code that tests for `litolff` / `brahms` / `breitkopf` / `317803` is the measuring tools (`judged.py:289-291`, `judged_claims.py:277,554`, `lane_report.py:1642`). Weights route by input DOMAIN (scan vs engraved, `staged/weight_routing.py`, `input_domain.py`), not by publisher.
- Shape templates: the meter and key readers match **Bravura** (SMuFL font) templates (`time_signature_locator.py`, `key_signature_template.py`), not a plate; the page-wide F-clef second witness uses **the page's own** read F clef as its template (`clef_pagewide.f_template`) -- the robust pattern.
- Lexicons: `direction_lexicon.py` is Italian with a handful of German (`ausdrucksvoll zart getragen gestopft Dämpfer`) and French (`doux chanté expressif`) words; "No direction in this repertoire is English". `instruments.py` holds Italian, German, French and English names.
- Raw page-pixel figures that reach a decision: `measure_extractor.BARLINE_MIN_DISTANCE_PX = 60` and `SPAN_TOUCH_TOLERANCE_PX = 6` (from the first commit, 2026-05-14), `staff_detector.MIN_PEAK_DISTANCE_PX = 4`; the legacy floors restated in staged (`ownership.TIE_FLANK_MIN_DY_PX = 30`, `rhythm.EVENT_X_TOLERANCE_FALLBACK_PX = 30`) -- frame not verified.
