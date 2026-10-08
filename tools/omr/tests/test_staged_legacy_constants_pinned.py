"""Pin the LEGACY surface that STAGED depends on (roadmap 3.0b).

CLAUDE.md section 3: the legacy pipeline (`tools/omr/transcribe.py`,
`export.py`, `rhythm.py`, `voicing.py`, `contextual.py`) is FROZEN -- "bug
fixes only" -- and it is also STAGED's dependency. `tools/omr/staged/` imports
tuning constants and pure renderers from those modules instead of restating
them, so that the two cannot drift. The price is that a legacy "bug fix" to a
threshold (a 0.25 that becomes 0.3) or to a renderer's parameters moves a
STAGED verdict or a STAGED file byte with no staged test and no staged diff
to show for it.

This file is that diff. Every constant a staged module reads from a legacy
module is compared to the literal value it has today, and every legacy
function a staged module calls must still exist, still be callable, still
take the parameters staged passes, and (for the pure ones with an obvious
one-line call) still return the one example output pinned here. A failure
names the STAGED consumer, so the person who touched legacy sees who is
affected. Changing a pinned value is allowed -- but it is a decision about a
STAGED verdict, made here on purpose, with the staged consumer's own checks
re-run (CLAUDE.md rule 7: this test can fail; see the commit message for the
red run).

It imports modules and compares VALUES. It reads no source text.
"""
from __future__ import annotations

import importlib
import inspect
from types import SimpleNamespace

import pytest

_MODULES = {name: importlib.import_module(f"tools.omr.{name}")
            for name in ("transcribe", "export", "rhythm", "voicing",
                         "contextual")}

# (legacy module, name, value as it stands today, STAGED consumer)
CONSTANTS = [
    ("transcribe", "TIE_SAME_POSITION_MAX_SPACES", 0.25,
     "staged/adjudicators/ownership.py:adjudicate_tie_pair"),
    ("transcribe", "_ARTIC_MAX_DX_NOTEHEAD_WIDTHS", 0.75,
     "staged/adjudicators/ownership.py:adjudicate_articulation_owner"),
    ("transcribe", "_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS", 1.0,
     "staged/adjudicators/ownership.py:adjudicate_ornament_owner"),
    ("transcribe", "_CLIPPED_NOTEHEAD_MAX_SPACES", 0.6,
     "staged/adjudicators/notehead_precision.py:CLIPPED_NOTEHEAD_MAX_SPACES"),
    ("transcribe", "_UNLADDERED_NOTEHEAD_MAX_CONF", 0.65,
     "staged/adjudicators/notehead_precision.py:UNLADDERED_MAX_CONF"),
    ("transcribe", "_LEDGER_RUNG_EXPECTED_SLACK", 0.25,
     "staged/adjudicators/notehead_precision.py:LEDGER_RUNG_EXPECTED_SLACK"),
    ("transcribe", "_LEDGER_RUNG_Y_TOL_SPACES", 0.35,
     "staged/adjudicators/notehead_precision.py:LEDGER_RUNG_Y_TOL_SPACES"),
    ("transcribe", "_LEDGER_RUNG_MIN_X_OVERLAP", 0.25,
     "staged/adjudicators/notehead_precision.py:LEDGER_RUNG_MIN_X_OVERLAP"),
    ("transcribe", "DEFAULT_WEIGHTS", 'tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt',
     "staged/weight_routing.py:resolve_staged_weights"),
    ("export", "_ARC_RIVAL_MARGIN_SPACES", 0.5,
     "staged/adjudicators/ownership.py:adjudicate_arc_owner"),
    ("export", "_ARC_RIVAL_MIN_COVERED", 2,
     "staged/adjudicators/ownership.py:adjudicate_arc_owner"),
    ("export", "_ARC_RIVAL_NEAR_SPACES", 0.75,
     "staged/adjudicators/ownership.py:_arc_end_owner"),
    ("export", "_SLUR_ARC_PAD_NOTEHEADS", 0.25,
     "staged/adjudicators/ownership.py:adjudicate_arc_owner, _arc_end_owner"),
    ("export", "_SLUR_BOUNDARY_SPACES", 0.5,
     "staged/adjudicators/ownership.py:adjudicate_tie_pair"),
    ("export", "_MAX_WEDGE_NUMBER", 6,
     "staged/export.py:_place_wedges"),
    ("export", "_MAX_SLUR_NUMBER", 6,
     "staged/export.py:_pair_arcs"),
    ("export", "_MAX_DURATION_DENOMINATOR", 64,
     "staged/export.py:_divisions"),
    ("export", "_LILY_ORNAMENT", {
        "trill": "\\trill", "turn": "\\turn",
        "inverted-turn": "\\reverseturn", "mordent": "\\mordent"},
     "staged/lilypond.py:_tally"),
    ("rhythm", "_FLAG_DURATIONS", {
        "flag8thup": (0.5, "eighth"), "flag8thdown": (0.5, "eighth"),
        "flag16thup": (0.25, "sixteenth"), "flag16thdown": (0.25, "sixteenth"),
        "flag32ndup": (0.125, "thirty_second"),
        "flag32nddown": (0.125, "thirty_second"),
        "flag64thup": (0.0625, "sixty_fourth"),
        "flag64thdown": (0.0625, "sixty_fourth"),
        "flag128thup": (0.03125, "hundred_twenty_eighth"),
        "flag128thdown": (0.03125, "hundred_twenty_eighth")},
     "staged/adjudicators/rhythm.py:_flag_levels_table"),
]


# (legacy module, name, parameter names staged relies on, STAGED consumer)
FUNCTIONS = [
    ("transcribe", "articulation_kind",
     ('class_name',),
     "staged/adjudicators/ownership.py:adjudicate_articulation_owner"),
    ("transcribe", "ornament_kind",
     ('class_name',),
     "staged/gather.py:_ornament_kind"),
    ("transcribe", "_stem_direction",
     ('stem', 'noteheads'),
     "staged/adjudicators/rhythm.py:_project (stem direction)"),
    ("transcribe", "_route_weights",
     ('pdf_path', 'pages', 'classify'),
     "staged/weight_routing.py:resolve_staged_weights"),
    ("transcribe", "_weight_routing_enabled",
     (),
     "staged/weight_routing.py:resolve_staged_weights"),
    ("transcribe", "_repo_root",
     (),
     "staged/weight_routing.py:resolve_staged_weights"),
    ("export", "_parse_pitch",
     ('pitch',),
     "staged/export.py:_sounding_pitch; consequences.py:_letter_octave; review/server.py:_note_facts"),
    ("export", "_lcm",
     ('a', 'b'),
     "staged/export.py:_divisions"),
    ("export", "_pitch_step",
     ('pitch',),
     "staged/export.py:_record_tie_spans"),
    ("export", "_xml_escape",
     ('s',),
     "staged/export.py:to_musicxml, _marked_empty_measure, _meter_return_direction_xml"),
    ("export", "_clef_to_lily",
     ('clef',),
     "staged/lilypond.py:_staff_block"),
    ("export", "_lily_key_name",
     ('key_sig',),
     "staged/lilypond.py:_staff_block"),
    ("export", "_measure_rest_beats",
     ('time_sig',),
     "staged/export.py:_bar_quarters"),
    ("export", "_dotted_duration_for_beats",
     ('beats',),
     "staged/export.py:_place_notes"),
    ("export", "_duration_to_lily_xml",
     ('duration_type', 'dots'),
     "staged/export.py:_measure_events_xml, _rest_xml"),
    ("export", "_lily_measure_rest",
     ('time_sig',),
     "staged/lilypond.py:_render_bar"),
    ("export", "_lily_measure",
     ('events', 'wedges'),
     "staged/lilypond.py:_render_bar"),
    ("export", "_lily_wedge_plan",
     ('lane',),
     "staged/lilypond.py:_staff_block"),
    ("export", "_lily_event",
     ('event', 'wedges'),
     "staged/lilypond.py (via _lily_measure)"),
    ("export", "_mxl_attributes_block",
     ('clef', 'key_sig', 'time_sig', 'divisions', 'indent', 'include_divisions', 'staff_lines'),
     "staged/export.py:_part_xml, _pad_tacet_span"),
    ("export", "_mxl_direction",
     ('item', 'indent'),
     "staged/export.py:_part_xml"),
    ("export", "_mxl_empty_measure",
     ('time_sig', 'divisions', 'directions', 'indent', 'fermata', 'wedges'),
     "staged/export.py:_marked_empty_measure, _pad_tacet_span"),
    ("export", "_mxl_note",
     ('event_pitch', 'lily_suffix', 'xml_type', 'dots', 'beats', 'divisions', 'is_chord', 'is_rest', 'indent', 'voice', 'tied_to_next', 'tied_from_prev', 'beam_states', 'slur_states', 'time_modification', 'tuplet_state', 'articulations', 'ornaments', 'fermata', 'accidental', 'measure_rest'),
     "staged/export.py:_measure_events_xml, _rest_xml"),
    ("export", "_mxl_ornament_elements",
     ('ornaments',),
     "staged/export.py:_measure_events_xml, _held_bar_marks"),
    ("export", "_mxl_pitch_block",
     ('pitch', 'indent'),
     "staged/export.py (via _mxl_note)"),
    ("export", "_mxl_wedge",
     ('number', 'kind', 'indent'),
     "staged/export.py:_measure_events_xml"),
    ("export", "_number_spans",
     ('spans', 'max_number'),
     "staged/export.py:_pair_arcs, _place_wedges"),
    ("export", "_paired_spans",
     ('measures', 'per_measure_boxes', 'spacings', 'tops', 'breaks', 'voice_of', 'reclass', 'order', 'x_probes'),
     "staged/export.py:_flatten_part, _pair_arcs"),
    ("export", "_merge_arcs_across_barlines",
     ('measures', 'per_measure_arcs', 'spacings', 'tops', 'system_breaks'),
     "staged/export.py:_arcs_by_kind"),
    ("export", "_score_partwise",
     ('result', 'part_list', 'parts_xml'),
     "staged/export.py:to_musicxml"),
    ("export", "annotate_beams",
     ('events', 'detections'),
     "staged/export.py:_annotate_beams_for"),
    ("export", "_wedge_anchors_from_candidates",
     ('candidates', 'widths', 'left', 'right', 'voice_of'),
     "staged/adjudicators/ownership.py:adjudicate_wedge_anchor"),
    ("rhythm", "_rest_duration",
     ('class_name',),
     "staged/adjudicators/rhythm.py:_rest_ruling"),
    ("voicing", "group_chords_in_measure",
     ('detections', 'chord_x_tolerance'),
     "staged/export.py:_bar_event_rows, _events, _flatten_part"),
    ("voicing", "split_events_into_voices",
     ('events',),
     "staged/adjudicators/rhythm.py:adjudicate_voices"),
    ("contextual", "_labels_for_page",
     ('pws', 'pdf_path', 'page_index', 'assist', 'budget', 'surya_fallback', 'ocr_fallback', 'tiers', 'sources', 'failures', 'review_dir'),
     "staged/gather.py:gather_margin_labels"),
]


def _where(consumer: str) -> str:
    return f"STAGED consumer: tools/omr/{consumer}"


@pytest.mark.parametrize("module,name,expected,consumer", CONSTANTS,
                         ids=[f"{c[0]}.{c[1]}" for c in CONSTANTS])
def test_constant_is_pinned(module, name, expected, consumer):
    mod = _MODULES[module]
    assert hasattr(mod, name), (
        f"tools.omr.{module}.{name} is gone. {_where(consumer)} imports it.")
    got = getattr(mod, name)
    assert got == expected, (
        f"tools.omr.{module}.{name} changed: {got!r} != pinned {expected!r}. "
        f"{_where(consumer)} reads it, so this moves a STAGED verdict. "
        f"If the change is intended, re-run that consumer's checks and update "
        f"this pin deliberately (roadmap 3.0b).")
    assert type(got) is type(expected), (
        f"tools.omr.{module}.{name} changed type: {type(got).__name__} vs "
        f"{type(expected).__name__}. {_where(consumer)}")


@pytest.mark.parametrize("module,name,params,consumer", FUNCTIONS,
                         ids=[f"{f[0]}.{f[1]}" for f in FUNCTIONS])
def test_function_exists_with_pinned_parameters(module, name, params, consumer):
    mod = _MODULES[module]
    fn = getattr(mod, name, None)
    assert fn is not None, (
        f"tools.omr.{module}.{name} is gone. {_where(consumer)} calls it.")
    assert callable(fn), (
        f"tools.omr.{module}.{name} is not callable. {_where(consumer)}")
    got = tuple(inspect.signature(fn).parameters)
    assert got == params, (
        f"tools.omr.{module}.{name} parameters changed: {got} != pinned "
        f"{params}. {_where(consumer)} passes these by position or keyword.")


def test_staged_copies_of_legacy_thresholds_follow_the_pins():
    """notehead_precision re-exports five transcribe thresholds under its own
    names; the pinned legacy value must be the one STAGED actually holds."""
    from tools.omr.staged.adjudicators import notehead_precision as NP
    pairs = [
        ("CLIPPED_NOTEHEAD_MAX_SPACES", "_CLIPPED_NOTEHEAD_MAX_SPACES"),
        ("UNLADDERED_MAX_CONF", "_UNLADDERED_NOTEHEAD_MAX_CONF"),
        ("LEDGER_RUNG_EXPECTED_SLACK", "_LEDGER_RUNG_EXPECTED_SLACK"),
        ("LEDGER_RUNG_Y_TOL_SPACES", "_LEDGER_RUNG_Y_TOL_SPACES"),
        ("LEDGER_RUNG_MIN_X_OVERLAP", "_LEDGER_RUNG_MIN_X_OVERLAP"),
    ]
    for staged_name, legacy_name in pairs:
        assert getattr(NP, staged_name) == getattr(
            _MODULES["transcribe"], legacy_name), (
            f"staged notehead_precision.{staged_name} no longer equals "
            f"transcribe.{legacy_name}")


# One pinned example per pure function with an obvious one-line call. The
# outputs are what the tree returns today.
def _heads(y, h):
    return [SimpleNamespace(y_canonical=y, height_canonical=h)]


_STEM = SimpleNamespace(y_canonical=0, height_canonical=40)

EXAMPLES = [
    ("export", "_parse_pitch", ("C4",), ("C", "", 4),
     "export.py:_sounding_pitch; consequences.py:_letter_octave"),
    ("export", "_parse_pitch", ("F#5",), ("F", "#", 5),
     "export.py:_sounding_pitch; consequences.py:_letter_octave"),
    ("export", "_parse_pitch", ("Bb3",), ("B", "b", 3),
     "export.py:_sounding_pitch; consequences.py:_letter_octave"),
    ("export", "_lcm", (4, 6), 12, "export.py:_divisions"),
    ("export", "_pitch_step", ("C#4",), "C4", "export.py:_record_tie_spans"),
    ("export", "_xml_escape", ("a<b&c",), "a&lt;b&amp;c",
     "export.py:to_musicxml"),
    ("export", "_clef_to_lily", ("treble",), "treble",
     "lilypond.py:_staff_block"),
    ("export", "_clef_to_lily", ("bass",), "bass", "lilypond.py:_staff_block"),
    ("export", "_lily_key_name", ({"sharps": 2},), "d",
     "lilypond.py:_staff_block"),
    ("export", "_lily_key_name", ({"flats": 1},), "f",
     "lilypond.py:_staff_block"),
    ("export", "_lily_key_name", ({},), "c", "lilypond.py:_staff_block"),
    ("export", "_measure_rest_beats", ({"numerator": 3, "denominator": 4},),
     3.0, "export.py:_bar_quarters"),
    ("export", "_measure_rest_beats", (None,), 4.0, "export.py:_bar_quarters"),
    ("export", "_dotted_duration_for_beats", (1.5,), ("quarter", 1),
     "export.py:_place_notes"),
    ("export", "_duration_to_lily_xml", ("quarter", 1), ("4", "quarter", 1),
     "export.py:_rest_xml"),
    ("export", "_duration_to_lily_xml", ("eighth", 0), ("8", "eighth", 0),
     "export.py:_rest_xml"),
    ("export", "_lily_measure_rest", ({"numerator": 3, "denominator": 4},),
     "r2.", "lilypond.py:_render_bar"),
    ("export", "_lily_measure", ([],), "", "lilypond.py:_render_bar"),
    ("export", "_lily_wedge_plan", ([],), {}, "lilypond.py:_staff_block"),
    ("export", "_mxl_pitch_block", ("F#5", ""),
     "<pitch>\n  <step>F</step>\n  <alter>1</alter>\n  <octave>5</octave>\n"
     "</pitch>", "export.py (via _mxl_note)"),
    ("export", "_mxl_direction", (("words", "dolce"), ""),
     '<direction placement="below">\n  <direction-type>\n'
     "    <words>dolce</words>\n  </direction-type>\n</direction>",
     "export.py:_part_xml"),
    ("export", "_mxl_wedge", (1, "crescendo", "  "),
     '  <direction placement="below">\n    <direction-type>\n'
     '      <wedge number="1" type="crescendo"/>\n    </direction-type>\n'
     "  </direction>", "export.py:_measure_events_xml"),
    ("export", "_mxl_ornament_elements", (None,), [],
     "export.py:_measure_events_xml"),
    ("export", "_number_spans", ([], 6), [], "export.py:_pair_arcs"),
    ("export", "_merge_arcs_across_barlines", ([], [], [], []), [],
     "export.py:_arcs_by_kind"),
    ("export", "annotate_beams", ([], []), None,
     "export.py:_annotate_beams_for"),
    ("rhythm", "_rest_duration", ("restWhole",), (4.0, "whole"),
     "adjudicators/rhythm.py:_rest_ruling"),
    ("rhythm", "_rest_duration", ("rest8th",), (0.5, "eighth"),
     "adjudicators/rhythm.py:_rest_ruling"),
    ("transcribe", "articulation_kind", ("articStaccatoAbove",),
     ("staccato", True), "adjudicators/ownership.py"),
    ("transcribe", "ornament_kind", ("ornamentTrill",), ("trill", None, True),
     "gather.py:_ornament_kind"),
    ("transcribe", "_stem_direction", (_STEM, _heads(30, 10)),
     "up", "adjudicators/rhythm.py:_project"),
    ("transcribe", "_stem_direction", (_STEM, _heads(0, 10)),
     "down", "adjudicators/rhythm.py:_project"),
    ("voicing", "split_events_into_voices", ([],), [[]],
     "adjudicators/rhythm.py:adjudicate_voices"),
    ("voicing", "group_chords_in_measure", ([],), [],
     "export.py:_flatten_part"),
]


@pytest.mark.parametrize("module,name,args,expected,consumer", EXAMPLES,
                         ids=[f"{e[0]}.{e[1]}#{i}"
                              for i, e in enumerate(EXAMPLES)])
def test_pure_function_example_is_pinned(module, name, args, expected,
                                         consumer):
    got = getattr(_MODULES[module], name)(*args)
    assert got == expected, (
        f"tools.omr.{module}.{name}{args!r} -> {got!r}, pinned {expected!r}. "
        f"{_where('staged/' + consumer)} reuses it unchanged.")
