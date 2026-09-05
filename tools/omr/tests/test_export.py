"""Unit tests for tools/omr/export.py — Phase 4d serializers.

Tests the pure helpers (pitch parsing, key sig mapping, duration table)
and structural correctness of small synthetic JSON inputs.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from tools.omr.voicing import group_chords_in_measure

from tools.omr.export import (
    annotate_beams,
    arbitrate_arcs_across_staves,
    annotate_fermatas,
    annotate_slurs_in_slot,
    annotate_slurs_in_staff,
    measure_dynamics,
    _compute_divisions,
    _direction_slots,
    _first_clef_bearing_measure,
    _tuplet_runs,
    _mxl_note,
    _DURATION_TABLE,
    _dotted_duration_for_beats,
    _duration_to_lily_xml,
    _LILY_ACCIDENTAL,
    _lily_event,
    _lily_key_for_sig,
    _lily_measure_rest,
    _measure_rest_beats,
    _mxl_measure_rest,
    _parse_pitch,
    _pitch_to_lily,
    _strip_dotted,
    to_lilypond,
    to_musicxml,
)


# ─── _parse_pitch ───────────────────────────────────────────────────────────


class TestParsePitch:
    @pytest.mark.parametrize("pitch, expected", [
        ("C4", ("C", "", 4)),
        ("F#5", ("F", "#", 5)),
        ("Bb3", ("B", "b", 3)),
        ("A##2", ("A", "##", 2)),
        ("Dbb1", ("D", "bb", 1)),
        ("G0", ("G", "", 0)),
    ])
    def test_valid_pitches(self, pitch, expected):
        assert _parse_pitch(pitch) == expected

    def test_invalid_letter(self):
        assert _parse_pitch("H4") is None

    def test_invalid_octave(self):
        assert _parse_pitch("Cx") is None

    def test_empty(self):
        assert _parse_pitch("") is None


# ─── _pitch_to_lily ─────────────────────────────────────────────────────────


class TestPitchToLily:
    @pytest.mark.parametrize("pitch, expected", [
        ("C3", "c"),
        ("C4", "c'"),         # middle C
        ("C5", "c''"),
        ("C2", "c,"),
        ("C1", "c,,"),
        ("F#4", "fis'"),
        ("Bb3", "bes"),
        ("A##2", "aisis,"),
        ("Dbb5", "deses''"),
    ])
    def test_pitches(self, pitch, expected):
        assert _pitch_to_lily(pitch) == expected

    def test_invalid_returns_none(self):
        assert _pitch_to_lily("X9") is None


# ─── _lily_key_for_sig ─────────────────────────────────────────────────────


class TestLilyKeyForSig:
    def test_c_major_returns_none(self):
        assert _lily_key_for_sig(0, 0) is None

    @pytest.mark.parametrize("sharps, expected", [
        (1, "g"), (2, "d"), (3, "a"), (4, "e"),
        (5, "b"), (6, "fis"), (7, "cis"),
    ])
    def test_sharp_keys(self, sharps, expected):
        assert _lily_key_for_sig(sharps, 0) == expected

    @pytest.mark.parametrize("flats, expected", [
        (1, "f"), (2, "bes"), (3, "ees"), (4, "aes"),
        (5, "des"), (6, "ges"), (7, "ces"),
    ])
    def test_flat_keys(self, flats, expected):
        assert _lily_key_for_sig(0, flats) == expected


# ─── _strip_dotted ─────────────────────────────────────────────────────────


class TestStripDotted:
    def test_no_dotted(self):
        assert _strip_dotted("quarter") == ("quarter", 0)

    def test_one_dot(self):
        assert _strip_dotted("dotted_quarter") == ("quarter", 1)

    def test_two_dot(self):
        assert _strip_dotted("2dotted_eighth") == ("eighth", 2)


# ─── _duration_to_lily_xml ──────────────────────────────────────────────────


class TestDurationToLilyXml:
    @pytest.mark.parametrize("dtype, expected_lily, expected_xml", [
        ("whole", "1", "whole"),
        ("half", "2", "half"),
        ("quarter", "4", "quarter"),
        ("eighth", "8", "eighth"),
        ("sixteenth", "16", "16th"),
        ("thirty_second", "32", "32nd"),
    ])
    def test_known_durations(self, dtype, expected_lily, expected_xml):
        lily, xml, dots = _duration_to_lily_xml(dtype, 0)
        assert lily == expected_lily
        assert xml == expected_xml
        assert dots == 0

    def test_dotted_quarter(self):
        lily, xml, dots = _duration_to_lily_xml("quarter", 1)
        assert lily == "4"
        assert xml == "quarter"
        assert dots == 1

    def test_dotted_prefix_and_dot_count_do_not_accumulate(self):
        # This test used to assert 2, "1 from prefix + 1 from arg", encoding
        # the exporter's stated assumption that transcribe sets only one of the
        # two. It does not: `rhythm._name_for_dots` builds `duration_type` FROM
        # the dot count, so a single-dotted quarter arrives as BOTH
        # "dotted_quarter" and dots=1, and summing wrote `4**` where the truth
        # has `4*` — 82 of Brahms's OMR-NED edits. See TestDotCounting.
        lily, xml, dots = _duration_to_lily_xml("dotted_quarter", 1)
        assert dots == 1


# ─── Empty-measure padding — time-signature-aware full-measure rests ──────


class TestMeasureRestBeats:
    def test_no_time_sig_falls_back_to_whole(self):
        assert _measure_rest_beats(None) == 4.0

    def test_missing_fields_falls_back_to_whole(self):
        assert _measure_rest_beats({}) == 4.0

    @pytest.mark.parametrize("num, den, expected", [
        (4, 4, 4.0),
        (3, 4, 3.0),
        (2, 4, 2.0),
        (6, 8, 3.0),
        (2, 2, 4.0),
        (3, 8, 1.5),
        (5, 4, 5.0),
    ])
    def test_common_meters(self, num, den, expected):
        time_sig = {"numerator": num, "denominator": den}
        assert _measure_rest_beats(time_sig) == pytest.approx(expected)


class TestDottedDurationForBeats:
    @pytest.mark.parametrize("beats, expected", [
        (4.0, ("whole", 0)),
        (3.0, ("half", 1)),      # dotted half = 3 beats (3/4, 6/8)
        (2.0, ("half", 0)),
        (1.5, ("quarter", 1)),   # dotted quarter (3/8)
        (1.0, ("quarter", 0)),
    ])
    def test_exact_matches(self, beats, expected):
        assert _dotted_duration_for_beats(beats) == expected

    def test_irregular_meter_returns_none(self):
        # 5/4 doesn't reduce to a single (possibly dotted) note value.
        assert _dotted_duration_for_beats(5.0) is None


class TestLilyMeasureRest:
    def test_no_time_sig_is_whole_rest(self):
        assert _lily_measure_rest(None) == "r1"

    def test_three_four_is_dotted_half(self):
        assert _lily_measure_rest({"numerator": 3, "denominator": 4}) == "r2."

    def test_six_eight_is_dotted_half(self):
        assert _lily_measure_rest({"numerator": 6, "denominator": 8}) == "r2."

    def test_two_four_is_half(self):
        assert _lily_measure_rest({"numerator": 2, "denominator": 4}) == "r2"

    def test_irregular_meter_uses_full_measure_rest_multiplier(self):
        # 5/4 = 5 quarter-note beats = 5/4 of a whole note — LilyPond's
        # full-measure rest 'R' with a duration multiplier always compiles.
        assert _lily_measure_rest({"numerator": 5, "denominator": 4}) == "R1*5/4"


class TestMxlMeasureRest:
    def test_no_time_sig_is_whole(self):
        assert _mxl_measure_rest(None) == (4.0, "whole", 0)

    def test_three_four_is_dotted_half(self):
        beats, xml_type, dots = _mxl_measure_rest({"numerator": 3, "denominator": 4})
        assert beats == pytest.approx(3.0)
        assert xml_type == "half"
        assert dots == 1

    def test_irregular_meter_keeps_exact_beats(self):
        # No clean dotted-note match for 5/4 — <duration> (the semantic
        # value) stays exact even though the cosmetic <type> falls back
        # to whole.
        beats, xml_type, dots = _mxl_measure_rest({"numerator": 5, "denominator": 4})
        assert beats == pytest.approx(5.0)
        assert xml_type == "whole"
        assert dots == 0


def _tiny_result_empty_measure(time_sig):
    """One staff, one EMPTY measure (no detections) — exercises the
    exporters' full-measure-rest padding path.
    """
    return {
        "source_pdf": "synthetic.pdf",
        "pages": [{
            "page_index": 0,
            "n_systems": 1,
            "systems": [{
                "system_index": 0,
                "n_staves": 1,
                "staves": [{
                    "staff_index": 0,
                    "clef": "treble",
                    "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
                    "time_signature": time_sig,
                    "n_measures": 1,
                    "measures": [{
                        "measure_index": 0,
                        "bbox_page_px": [0, 0, 100, 50],
                        "clef": "treble",
                        "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
                        "time_signature": time_sig,
                        "n_detections": 0,
                        "detections": [],
                    }],
                }],
            }],
        }],
    }


class TestEmptyMeasurePadding:
    def test_lilypond_three_four_uses_dotted_half_rest(self):
        out = to_lilypond(_tiny_result_empty_measure({"numerator": 3, "denominator": 4}))
        assert "r2. |" in out
        assert "r1 |" not in out

    def test_lilypond_no_time_sig_falls_back_to_whole_rest(self):
        out = to_lilypond(_tiny_result_empty_measure(None))
        assert "r1 |" in out

    def test_musicxml_three_four_has_correct_duration(self):
        out = to_musicxml(_tiny_result_empty_measure({"numerator": 3, "denominator": 4}))
        # divisions defaults to 4 (no detections force finer resolution):
        # 3 beats * 4 divisions = 12.
        assert "<duration>12</duration>" in out
        assert "<rest/>" in out
        assert "<type>half</type>" in out
        assert "<dot/>" in out

    def test_musicxml_no_time_sig_falls_back_to_whole(self):
        out = to_musicxml(_tiny_result_empty_measure(None))
        assert "<duration>16</duration>" in out  # 4 beats * 4 divisions
        assert "<type>whole</type>" in out


class TestTimeSignatureSymbol:
    """`4/4` and a common-time `C` are one bar length and two engravings.

    musicdiff charges the difference as `extrainfoedit`, a flat 3 edits per
    staff — 270 over 5 works of the widened corpus, and 0 on the three the
    benchmark used to be, all of which print digit meters. The detector reads
    both glyphs at confidence 0.89-0.96; only the export was dropping them.
    """

    def test_common_time_carries_its_symbol(self):
        out = to_musicxml(_tiny_result_empty_measure(
            {"numerator": 4, "denominator": 4, "symbol": "common"}))
        assert '<time symbol="common">' in out

    def test_cut_common_carries_its_symbol(self):
        out = to_musicxml(_tiny_result_empty_measure(
            {"numerator": 2, "denominator": 2, "symbol": "cut"}))
        assert '<time symbol="cut">' in out

    def test_a_digit_meter_gets_no_symbol(self):
        """Absent a reading the export must say nothing, not guess. A 4/4 set
        in digits and one set as C are different pages."""
        out = to_musicxml(_tiny_result_empty_measure(
            {"numerator": 4, "denominator": 4}))
        assert "<time>" in out
        assert "symbol=" not in out

    def test_raw_alone_does_not_produce_a_symbol(self):
        """`raw` is synthesised from the numbers by `_propagated_meter` ("C"
        for any 4/4), so it is not evidence that a C was printed. Only
        `symbol`, set where the glyph was detected, may reach the export."""
        out = to_musicxml(_tiny_result_empty_measure(
            {"numerator": 4, "denominator": 4, "raw": "C"}))
        assert "symbol=" not in out

    def test_an_unknown_symbol_is_refused(self):
        out = to_musicxml(_tiny_result_empty_measure(
            {"numerator": 4, "denominator": 4, "symbol": "single-number"}))
        assert "symbol=" not in out


class TestArticulations:
    """Detected on every page and exported from none of them until now.

    Mozart 40 fires exactly 102 `articStaccato*` and was charged exactly 102
    `insarticulation` edits, 28% of its budget. Both exporters carry every
    other mark the pipeline reads, so both carry these.
    """

    @staticmethod
    def _result(marks):
        r = _tiny_result()
        nh = (r["pages"][0]["systems"][0]["staves"][0]["measures"][0]
              ["detections"][0])
        nh["articulations"] = marks
        return r

    def test_musicxml_wraps_the_marks_in_one_articulations_element(self):
        out = to_musicxml(self._result(["staccato", "accent"]))
        assert "<articulations>" in out
        assert "<staccato/>" in out and "<accent/>" in out
        # One wrapper holding both, not one block per mark.
        assert out.count("<articulations>") == 1

    def test_marcato_is_musicxmls_strong_accent(self):
        out = to_musicxml(self._result(["marcato"]))
        assert "<strong-accent/>" in out
        assert "<marcato/>" not in out

    def test_a_score_with_no_marks_emits_no_articulations(self):
        assert "<articulations>" not in to_musicxml(_tiny_result())

    def test_an_unknown_mark_is_dropped_not_guessed(self):
        out = to_musicxml(self._result(["staccato", "bartok-pizzicato"]))
        assert "<staccato/>" in out
        assert "bartok" not in out

    def test_lilypond_carries_them_too(self):
        out = to_lilypond(self._result(["staccato"]))
        assert "-." in out

    def test_lilypond_marcato_and_tenuto(self):
        assert "-^" in to_lilypond(self._result(["marcato"]))
        assert "--" in to_lilypond(self._result(["tenuto"]))

    def test_lilypond_accent(self):
        """The one articulation this class had not pinned on the LilyPond
        side — and the one whose closure a stale CLAUDE.md sentence denied
        for two days ("nothing consumes them"). The MusicXML half is pinned
        above; the wiring's pin is a test, not a sentence.
        benchmarks/omr-export-gaps-2026-09/FINDINGS.md §1."""
        assert "->" in to_lilypond(self._result(["accent"]))


# ─── to_lilypond (smoke test on a tiny synthetic JSON) ─────────────────────


def _tiny_result():
    return {
        "source_pdf": "synthetic.pdf",
        "pages": [{
            "page_index": 0,
            "n_systems": 1,
            "systems": [{
                "system_index": 0,
                "n_staves": 1,
                "staves": [{
                    "staff_index": 0,
                    "clef": "treble",
                    "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
                    "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
                    "n_measures": 1,
                    "measures": [{
                        "measure_index": 0,
                        "bbox_page_px": [0, 0, 100, 50],
                        "clef": "treble",
                        "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
                        "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
                        "n_detections": 4,
                        "detections": [
                            {
                                "class": "noteheadBlackOnLine",
                                "category": "notehead",
                                "bbox": [10, 10, 5, 5],
                                "bbox_page": [10, 10, 5, 5],
                                "confidence": 0.9,
                                "pitch": "C4",
                                "duration_beats": 1.0,
                                "duration_type": "quarter",
                                "dots": 0,
                            },
                            {
                                "class": "noteheadBlackOnLine",
                                "category": "notehead",
                                "bbox": [30, 10, 5, 5],
                                "bbox_page": [30, 10, 5, 5],
                                "confidence": 0.9,
                                "pitch": "D4",
                                "duration_beats": 1.0,
                                "duration_type": "quarter",
                                "dots": 0,
                            },
                            {
                                "class": "noteheadBlackOnLine",
                                "category": "notehead",
                                "bbox": [50, 10, 5, 5],
                                "bbox_page": [50, 10, 5, 5],
                                "confidence": 0.9,
                                "pitch": "E4",
                                "duration_beats": 1.0,
                                "duration_type": "quarter",
                                "dots": 0,
                            },
                            {
                                "class": "noteheadBlackOnLine",
                                "category": "notehead",
                                "bbox": [70, 10, 5, 5],
                                "bbox_page": [70, 10, 5, 5],
                                "confidence": 0.9,
                                "pitch": "F4",
                                "duration_beats": 1.0,
                                "duration_type": "quarter",
                                "dots": 0,
                            },
                        ],
                    }],
                }],
            }],
        }],
    }


class TestToLilypond:
    def test_contains_version(self):
        out = to_lilypond(_tiny_result())
        assert '\\version "2.20.0"' in out

    def test_contains_clef(self):
        out = to_lilypond(_tiny_result())
        assert "\\clef treble" in out

    def test_contains_time_sig(self):
        out = to_lilypond(_tiny_result())
        assert "\\time 4/4" in out

    def test_contains_pitches(self):
        out = to_lilypond(_tiny_result())
        # All 4 notes should render
        for pitch_lily in ["c'", "d'", "e'", "f'"]:
            assert pitch_lily in out

    def test_score_block(self):
        out = to_lilypond(_tiny_result())
        assert "\\score {" in out
        assert "\\layout { }" in out


class TestToMusicXML:
    def test_valid_xml(self):
        out = to_musicxml(_tiny_result())
        # Should parse without error
        root = ET.fromstring(
            out.split("?>", 1)[1].split("<!DOCTYPE", 1)[0]
            + out.split("partwise.dtd\">", 1)[1]
        )
        assert root.tag == "score-partwise"

    def test_one_part_for_one_staff(self):
        out = to_musicxml(_tiny_result())
        # Strip the DTD line for ET.fromstring (it doesn't fetch external DTDs)
        xml_no_dtd = out.split("?>", 1)[1].split("<!DOCTYPE", 1)[0] + \
                     out.split("partwise.dtd\">", 1)[1]
        root = ET.fromstring(xml_no_dtd)
        parts = root.findall("part")
        assert len(parts) == 1

    def test_correct_pitch_steps(self):
        out = to_musicxml(_tiny_result())
        # Verify the C4 notehead made it through with step=C, octave=4
        assert "<step>C</step>" in out
        assert "<octave>4</octave>" in out


class TestPartNaming:
    """The exporter names a part by its instrument once one is known.

    Before the contextual pass was wired into `transcribe` nothing here HAD a
    name to use, so every part came out as its own grid reference — the
    "no persistent part identity" complaint. A staff the pass could not name
    must still fall back, so `--no-contextual` output is unchanged.
    """

    @staticmethod
    def _result(staff_extra):
        result = _tiny_result_empty_measure({"beats": 4, "beat_type": 4})
        result["pages"][0]["systems"][0]["staves"][0].update(staff_extra)
        return result

    def test_named_part_uses_the_instrument(self):
        xml = to_musicxml(self._result({"instrument": "Clarinet"}))
        assert "<part-name>Clarinet</part-name>" in xml
        assert "Staff p0-s0-0" not in xml

    def test_unnamed_part_keeps_the_coordinate_form(self):
        xml = to_musicxml(self._result({}))
        assert "<part-name>Staff p0-s0-0</part-name>" in xml

    def test_null_instrument_is_not_an_empty_name(self):
        """`instrument` is present-but-None on a staff the pass could not
        identify, which must not produce <part-name></part-name>."""
        xml = to_musicxml(self._result({"instrument": None}))
        assert "<part-name>Staff p0-s0-0</part-name>" in xml
        assert "<part-name></part-name>" not in xml

    def test_instrument_name_is_xml_escaped(self):
        xml = to_musicxml(self._result({"instrument": 'Horn & "Tuba"'}))
        assert "&amp;" in xml
        assert '<part-name>Horn & "Tuba"</part-name>' not in xml


class TestBeamAnnotation:
    """Beams are detected by Phase 4f and were dropped on export.

    Two signals do different jobs and the tests pin both: the beam BOX says
    which notes form one group (the CV merges primary and secondary beams into
    one box, so it gives extent), and `beam_levels` gives the level structure
    inside that extent.
    """

    @staticmethod
    def _note(x, levels, dur="eighth", beats=0.5):
        return {"kind": "note", "duration_type": dur, "duration_beats": beats,
                "dots": 0,
                "noteheads": [{"pitch": "C4", "beam_levels": levels,
                               "bbox_page": [x, 0, 10, 10]}]}

    @staticmethod
    def _beam(x0, x1):
        return {"category": "structural", "class": "beam",
                "bbox_page": [x0, 0, x1 - x0, 5]}

    def _states(self, events):
        return [e.get("beam_states") for e in events]

    def test_four_eighths_under_one_box(self):
        events = [self._note(x, 1) for x in (100, 120, 140, 160)]
        annotate_beams(events, [self._beam(95, 175)])
        assert self._states(events) == [
            {1: "begin"}, {1: "continue"}, {1: "continue"}, {1: "end"}]

    def test_levels_nest_inside_the_group(self):
        """Two sixteenths then three eighths: the primary beam spans all five,
        the secondary only the sixteenths."""
        events = ([self._note(100, 2, "16th", 0.25), self._note(115, 2, "16th", 0.25)]
                  + [self._note(x, 1) for x in (135, 155, 175)])
        annotate_beams(events, [self._beam(95, 190)])
        assert self._states(events) == [
            {1: "begin", 2: "begin"}, {1: "continue", 2: "end"},
            {1: "continue"}, {1: "continue"}, {1: "end"}]

    def test_two_boxes_are_two_groups(self):
        """Adjacency alone would merge these into one run of four — which is
        the error this exists to avoid on dense music."""
        events = [self._note(x, 1) for x in (100, 120, 300, 320)]
        annotate_beams(events, [self._beam(95, 135), self._beam(295, 335)])
        assert self._states(events) == [
            {1: "begin"}, {1: "end"}, {1: "begin"}, {1: "end"}]

    def test_a_lone_note_is_flagged_not_beamed(self):
        events = [self._note(100, 1)]
        annotate_beams(events, [self._beam(95, 115)])
        assert self._states(events) == [None]

    def test_a_single_note_at_a_level_becomes_a_hook(self):
        """Dotted eighth + sixteenth: the sixteenth's second beam is a hook,
        pointing back at the note it shares the primary beam with."""
        events = [self._note(100, 1, "eighth", 0.75),
                  self._note(130, 2, "16th", 0.25)]
        annotate_beams(events, [self._beam(95, 145)])
        assert events[0]["beam_states"] == {1: "begin"}
        assert events[1]["beam_states"] == {1: "end", 2: "backward hook"}

    def test_rests_and_unbeamed_notes_do_not_join_a_group(self):
        events = [self._note(100, 1),
                  {"kind": "rest", "duration_type": "eighth",
                   "duration_beats": 0.5, "dots": 0, "noteheads": []},
                  self._note(160, 1)]
        annotate_beams(events, [self._beam(95, 175)])
        # Both notes are under the same box, so they are still one group — the
        # rest does not split it, but it carries no beam of its own.
        assert events[1].get("beam_states") is None
        assert events[0]["beam_states"] == {1: "begin"}
        assert events[2]["beam_states"] == {1: "end"}

    def test_no_beam_data_emits_nothing(self):
        events = [self._note(x, 0) for x in (100, 120)]
        annotate_beams(events, [])
        assert self._states(events) == [None, None]

    def test_edge_note_within_a_notehead_width_joins_its_group(self):
        """The box bounds beam INK, which runs stem to stem — the edge note's
        centre sits up to a head's width outside it (stem-up first note,
        stem-down last). Unpadded this was 430 of the 449 `wrong flag/beam`
        edits on the 11-work benchmark: the edge note exported as a flag and
        the group closed one note early."""
        events = [self._note(x, 1) for x in (100, 120, 140, 160)]
        # Centres are 105..165; the box covers only 125 and 145 outright.
        annotate_beams(events, [self._beam(115, 158)])
        assert self._states(events) == [
            {1: "begin"}, {1: "continue"}, {1: "continue"}, {1: "end"}]

    def test_a_two_note_group_survives_the_pad(self):
        """Both notes of a 2-note group used to fall out — the orphan formed a
        synthetic run of one and the survivor was alone under its box, so both
        went flagged."""
        events = [self._note(100, 1), self._note(130, 1)]
        annotate_beams(events, [self._beam(112, 132)])
        assert self._states(events) == [{1: "begin"}, {1: "end"}]

    def test_stacked_stroke_boxes_do_not_fracture_the_group(self):
        """A sixteenth group's primary and secondary strokes arrive as two
        boxes over the same span. The group id is the box id, so any per-note
        choice between them splits the group (a narrowest-box rule cost
        Mozart 41 138 edits); they collapse into one."""
        events = [self._note(x, 2, "16th", 0.25) for x in (100, 120, 140)]
        strokes = [
            {"category": "structural", "class": "beam",
             "bbox_page": [95, 0, 55, 5]},
            {"category": "structural", "class": "beam",
             "bbox_page": [98, 12, 54, 5]},
        ]
        annotate_beams(events, strokes)
        assert self._states(events) == [
            {1: "begin", 2: "begin"}, {1: "continue", 2: "continue"},
            {1: "end", 2: "end"}]

    def test_divisi_rows_over_the_same_notes_are_one_group(self):
        """Two voices' beams over the same double stops overlap in x offset by
        one head width (Mozart 40's Viola, 354px apart in y). They collapse —
        deliberately with no y test, because chord events flip which head is
        first and a per-note y preference fractured the runs."""
        events = [self._note(x, 1) for x in (100, 120, 140, 160)]
        rows = [
            {"category": "structural", "class": "beam",
             "bbox_page": [93, 400, 62, 8]},   # stems-down voice, below
            {"category": "structural", "class": "beam",
             "bbox_page": [113, 40, 62, 8]},   # stems-up voice, above
        ]
        annotate_beams(events, rows)
        assert self._states(events) == [
            {1: "begin"}, {1: "continue"}, {1: "continue"}, {1: "end"}]

    def test_a_bar_wide_box_over_two_groups_is_suspect(self):
        """Brahms 1, Contrabass m4: a spurious 685px 'beam' (a hairpin) at the
        real beams' y spanned the whole bar and swallowed all six notes into
        one run. A box x-containing two disjoint boxes loses to them."""
        events = [self._note(x, 1) for x in (100, 120, 300, 320)]
        spurious = {"category": "structural", "class": "beam",
                    "bbox_page": [90, 8, 250, 5]}
        annotate_beams(events, [self._beam(95, 135), self._beam(295, 335),
                                spurious])
        assert self._states(events) == [
            {1: "begin"}, {1: "end"}, {1: "begin"}, {1: "end"}]

    def test_only_the_chords_first_note_is_beamed(self):
        result = _tiny_result_empty_measure({"beats": 4, "beat_type": 4})
        staff = result["pages"][0]["systems"][0]["staves"][0]
        staff["measures"][0]["detections"] = [
            {"category": "structural", "class": "beam", "bbox_page": [95, 0, 80, 5]},
            # `bbox` is CELL space and is what chord grouping reads; `bbox_page`
            # is page space and is what the beam boxes are measured in. Both are
            # needed, and giving only one is why this fixture first read as a
            # single three-note chord.
            {"category": "notehead", "class": "noteheadBlack", "pitch": "C4",
             "duration_type": "eighth", "duration_beats": 0.5, "dots": 0,
             "beam_levels": 1, "bbox": [100, 40, 10, 10],
             "bbox_page": [100, 40, 10, 10], "confidence": 0.9},
            {"category": "notehead", "class": "noteheadBlack", "pitch": "E4",
             "duration_type": "eighth", "duration_beats": 0.5, "dots": 0,
             "beam_levels": 1, "bbox": [100, 20, 10, 10],
             "bbox_page": [100, 20, 10, 10], "confidence": 0.9},
            {"category": "notehead", "class": "noteheadBlack", "pitch": "G4",
             "duration_type": "eighth", "duration_beats": 0.5, "dots": 0,
             "beam_levels": 1, "bbox": [160, 40, 10, 10],
             "bbox_page": [160, 40, 10, 10], "confidence": 0.9},
        ]
        xml = to_musicxml(result)
        # Three notes, one of them a chord member, but only two beam-carrying
        # notes: the chord is beamed once, through its first note.
        assert xml.count("<beam") == 2
        assert '<beam number="1">begin</beam>' in xml
        assert '<beam number="1">end</beam>' in xml


class TestDotCounting:
    """`duration_type` and `dots` are the same fact, not two to add up.

    `rhythm._name_for_dots` builds `duration_type` FROM the dot count, so a
    dotted quarter arrives as both `dotted_quarter` and `dots=1`. Summing them
    wrote a double-dotted quarter for every single-dotted one — 82 of Brahms's
    OMR-NED edits, each `pred [D6]4** | gt [D6]4*`.
    """

    def test_both_sources_agreeing_yields_one_dot(self):
        assert _duration_to_lily_xml("dotted_quarter", 1)[2] == 1

    def test_type_alone_still_counts(self):
        assert _duration_to_lily_xml("dotted_quarter", 0)[2] == 1

    def test_dots_field_alone_still_counts(self):
        """The Vision OMR path and older JSON set `dots` with a plain type."""
        assert _duration_to_lily_xml("quarter", 1)[2] == 1

    def test_double_dots_survive(self):
        assert _duration_to_lily_xml("2dotted_quarter", 2)[2] == 2
        assert _duration_to_lily_xml("2dotted_quarter", 0)[2] == 2
        assert _duration_to_lily_xml("quarter", 2)[2] == 2

    def test_undotted_stays_undotted(self):
        assert _duration_to_lily_xml("quarter", 0)[2] == 0

    def test_the_base_type_is_unaffected(self):
        assert _duration_to_lily_xml("dotted_quarter", 1)[1] == "quarter"
        assert _duration_to_lily_xml("dotted_eighth", 1)[1] == "eighth"

    def test_a_dotted_note_exports_exactly_one_dot(self):
        result = _tiny_result_empty_measure({"beats": 6, "beat_type": 8})
        staff = result["pages"][0]["systems"][0]["staves"][0]
        staff["measures"][0]["detections"] = [
            {"category": "notehead", "class": "noteheadBlack", "pitch": "D5",
             "duration_type": "dotted_quarter", "duration_beats": 1.5,
             "dots": 1, "bbox": [10, 10, 10, 10],
             "bbox_page": [10, 10, 10, 10], "confidence": 0.9},
        ]
        xml = to_musicxml(result)
        assert xml.count("<dot/>") == 1, "a single-dotted note wrote two dots"


class TestDynamicsAndSlurs:
    """Both are detected and were dropped on export, like beams before them.

    On the Brahms fixture the pipeline finds 118 slur arcs and 31 dynamic letter
    glyphs, and `export.py` mentioned neither. Truth carries 82 slurs and 19
    dynamics.
    """

    @staticmethod
    def _dyn(x, y, cls, w=10):
        return {"category": "dynamic", "class": cls, "bbox": [x, y, w, 12]}

    @staticmethod
    def _note(x, levels=0):
        return {"kind": "note", "duration_type": "quarter", "duration_beats": 1.0,
                "dots": 0, "x_position": x,
                "noteheads": [{"pitch": "C4", "beam_levels": levels,
                               "bbox": [x, 40, 10, 10], "bbox_page": [x, 40, 10, 10]}]}

    @staticmethod
    def _slur(x0, x1):
        return {"category": "structural", "class": "slur",
                "bbox": [x0, 20, x1 - x0, 8],
                "bbox_page": [x0, 20, x1 - x0, 8]}

    # ── dynamics: the detector spells them one letter at a time ──────────
    def test_a_single_letter_is_a_dynamic(self):
        assert measure_dynamics([self._dyn(100, 60, "dynamicF")]) == [(100, "dynamic", "f")]

    def test_adjacent_letters_join_into_one_word(self):
        """Two `dynamicF` a glyph apart are 'ff', not two 'f'."""
        out = measure_dynamics([self._dyn(100, 60, "dynamicF"),
                                self._dyn(112, 60, "dynamicF")])
        assert out == [(100, "dynamic", "ff")]

    def test_letters_far_apart_stay_separate(self):
        out = measure_dynamics([self._dyn(100, 60, "dynamicF"),
                                self._dyn(400, 60, "dynamicP")])
        assert out == [(100, "dynamic", "f"), (400, "dynamic", "p")]

    def test_letters_on_different_lines_stay_separate(self):
        """Two staves' dynamics can share an x; only vertical proximity joins."""
        out = measure_dynamics([self._dyn(100, 60, "dynamicF"),
                                self._dyn(112, 300, "dynamicP")])
        assert sorted(out) == [(100, "dynamic", "f"), (112, "dynamic", "p")]

    def test_a_letter_run_that_is_not_a_word_is_dropped(self):
        """'fzp' is not a dynamic; guessing at it is worse than saying nothing."""
        assert measure_dynamics([self._dyn(100, 60, "dynamicF"),
                                 self._dyn(110, 60, "dynamicZ"),
                                 self._dyn(120, 60, "dynamicP")]) == []

    # ── where a direction attaches ───────────────────────────────────────
    def _ev(self, x):
        return {"kind": "chord", "x_position": x, "duration_beats": 1.0,
                "duration_type": "quarter", "dots": 0, "noteheads": []}

    def test_a_mark_attaches_to_the_first_note_at_or_past_it(self):
        events = [self._ev(100), self._ev(200), self._ev(300)]
        assert _direction_slots(events, [(150, "dynamic", "f")]) == {
            1: [("dynamic", "f")]}

    def test_a_mark_never_moves_backwards_onto_a_rest(self):
        """Why the rule is not `nearest`. Beethoven 5's `ff` belongs to the
        note at beat 0.5 and is printed after an eighth REST at 0.0; it stands
        nearer the rest, and a nearest rule put it there — 14 edits."""
        rest = {"kind": "rest", "x_position": 100, "duration_beats": 0.5,
                "duration_type": "eighth", "dots": 0}
        events = [rest, self._ev(200)]
        assert _direction_slots(events, [(120, "dynamic", "ff")]) == {
            1: [("dynamic", "ff")]}

    def test_marks_on_one_note_keep_their_printed_order(self):
        events = [self._ev(200)]
        assert _direction_slots(events, [(120, "words", "legato"),
                                         (90, "dynamic", "f")]) == {
            0: [("dynamic", "f"), ("words", "legato")]}

    def test_a_mark_past_the_last_note_stays_in_the_measure(self):
        assert _direction_slots([self._ev(100)], [(500, "words", "legato")]) == {
            1: [("words", "legato")]}

    def test_a_mark_right_of_its_note_attaches_to_it_not_the_next(self):
        """Brahms's `pesante` begins 47 canonical px RIGHT of the note it
        belongs to. Taking the first note at or PAST its left edge skipped a
        beat, and musicdiff charged the whole word twice for it."""
        events = [self._ev(957), self._ev(1145), self._ev(1336),
                  self._ev(1514), self._ev(1701)]
        assert _direction_slots(events, [(1383, "words", "pesante")]) == {
            2: [("words", "pesante")]}

    def test_a_mark_left_of_its_note_still_attaches_to_it(self):
        """And the opposite bias on the same page: `legato` begins 48 px LEFT
        of its note. There is no consistent side to lean on."""
        events = [self._ev(958), self._ev(1517)]
        assert _direction_slots(events, [(1468, "words", "legato")]) == {
            1: [("words", "legato")]}

    def test_a_mark_past_every_note_is_not_pulled_back_to_the_only_one(self):
        """The clause that survived from the old rule, and it earns its place
        on a MISSED note: Brahms's Bassoon 2 detects one note where the truth
        has two, and its `legato` is printed under the second. Landing after
        what we detected is right; snapping back to the one note is not."""
        assert _direction_slots([self._ev(957)], [(1468, "words", "legato")]) == {
            1: [("words", "legato")]}

    def test_a_tie_goes_forward(self):
        events = [self._ev(100), self._ev(200)]
        assert _direction_slots(events, [(150, "words", "legato")]) == {
            1: [("words", "legato")]}

    def test_a_bar_of_only_rests_still_takes_its_mark(self):
        """Rests are not candidates — unless they are all there is, and then
        nearness among everything is all the rule has left."""
        def _rest(x):
            return {"kind": "rest", "x_position": x, "duration_beats": 2.0,
                    "duration_type": "half", "dots": 0}

        assert _direction_slots([_rest(100), _rest(300)],
                                [(110, "words", "legato")]) == {
            0: [("words", "legato")]}

    def test_with_no_notes_a_direction_goes_past_the_end(self):
        """An empty measure must not silently swallow its own markings."""
        assert _direction_slots([], [(100, "dynamic", "f")]) == {
            0: [("dynamic", "f")]}

    def test_no_directions_means_no_slots(self):
        assert _direction_slots([self._ev(100)], None) == {}

    def test_mf_and_sf_are_recognised(self):
        assert measure_dynamics([self._dyn(100, 60, "dynamicM"),
                                 self._dyn(110, 60, "dynamicF")]) == [(100, "dynamic", "mf")]

    def test_slur_and_tie_share_one_notations_block(self):
        """Two <notations> elements on one note is invalid MusicXML."""
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, False, False, "      ",
                        tied_to_next=True, slur_states=[(1, "start")])
        assert xml.count("<notations>") == 1
        assert '<tie type="start"/>' in xml
        assert '<slur number="1" type="start"/>' in xml


# ─── Slurs, which outlive the measure they start in ─────────────────────────


def _slur_head(x, pitch="C4", width=10, y=40):
    """One pitched notehead at page-x `x`."""
    return {"category": "notehead", "class": "noteheadBlack", "pitch": pitch,
            "duration_type": "quarter", "duration_beats": 1.0, "dots": 0,
            "bbox": [x, y, width, 10], "bbox_page": [x, y, width, 10],
            "confidence": 0.9}


def _slur_arc(x0, x1, y=20):
    return {"category": "structural", "class": "slur",
            "bbox": [x0, y, x1 - x0, 8], "bbox_page": [x0, y, x1 - x0, 8]}


def _slur_staff(measures, spacing=10.0, top=40):
    """A staff whose cells tile [0,100), [100,200), … so a barline is a
    cell edge, which is what makes an arc's clipping visible.

    `top` is the staff's top line, so a second system can be placed further
    down the page — across a system break the only comparable height is the
    one relative to each staff's OWN lines."""
    return {
        "staff_index": 0,
        "clef": "treble",
        "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
        "time_signature": {"numerator": 4, "denominator": 4},
        "staff_geometry": {"line_ys_page": [top + d for d in (0, 10, 20, 30, 40)],
                           "line_spacing_px": spacing,
                           "x_start": 0, "x_end": 100 * len(measures)},
        "n_measures": len(measures),
        "measures": [{
            "measure_index": i,
            "bbox_page_px": [i * 100, top - 40, (i + 1) * 100, top + 50],
            "clef": "treble",
            "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
            "time_signature": {"numerator": 4, "denominator": 4},
            "n_detections": len(dets),
            "detections": dets,
        } for i, dets in enumerate(measures)],
    }


def _states(staff):
    """Every slur mark on the staff, as (measure, x, number, kind)."""
    out = []
    for m_idx, measure in enumerate(staff["measures"]):
        for det in measure["detections"]:
            for number, kind in det.get("slur_states") or []:
                out.append((m_idx, det["bbox_page"][0], number, kind))
    return sorted(out)


class TestSlursAcrossMeasures:
    """A slur crossing a barline is DETECTED AS TWO ARCS, because cells are cut
    per measure — 120 arcs on the Brahms fixture against 82 slurs in the truth.
    Rejoining them is the whole reason this pass works on a staff rather than
    on a measure.
    """

    def test_a_slur_inside_one_measure_marks_its_first_and_last_note(self):
        staff = _slur_staff([[
            _slur_head(10), _slur_head(30), _slur_head(50), _slur_head(70),
            _slur_arc(12, 78),
        ]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _states(staff) == [(0, 10, 1, "start"), (0, 70, 1, "stop")]

    def test_an_arc_over_one_note_is_dropped(self):
        """An unpaired <slur type="start"/> makes the file invalid, not merely
        wrong, so a lone note under an arc gets nothing."""
        staff = _slur_staff([[
            _slur_head(10), _slur_head(70), _slur_arc(8, 25),
        ]])
        assert annotate_slurs_in_staff(staff) == 0
        assert _states(staff) == []

    def test_two_arcs_meeting_at_a_barline_are_ONE_slur(self):
        """The arc is clipped exactly at the cell edge on both sides, so the
        slur opens in measure 0 and closes in measure 1 — one slur, not two.
        """
        staff = _slur_staff([
            [_slur_head(60), _slur_head(80), _slur_arc(66, 100)],
            [_slur_head(110), _slur_head(130), _slur_arc(100, 136)],
        ])
        assert annotate_slurs_in_staff(staff) == 1
        assert _states(staff) == [(0, 60, 1, "start"), (1, 130, 1, "stop")]

    def test_arcs_that_stop_short_of_the_barline_stay_two_slurs(self):
        """Only an arc CUT by the boundary continues past it; one that ends
        inside its own measure is a slur that ended there."""
        staff = _slur_staff([
            [_slur_head(20), _slur_head(60), _slur_arc(18, 75)],
            [_slur_head(120), _slur_head(160), _slur_arc(118, 175)],
        ])
        assert annotate_slurs_in_staff(staff) == 2
        assert _states(staff) == [
            (0, 20, 1, "start"), (0, 60, 1, "stop"),
            (1, 120, 1, "start"), (1, 160, 1, "stop"),
        ]

    def test_arcs_at_a_barline_but_different_heights_do_not_join(self):
        """Two staves' worth of arc can meet at one barline. An arc ABOVE the
        staff and one BELOW it are two slurs however well they line up in x —
        measured 8.05 staff spaces apart on the fixture against 0.53 for a
        genuine continuation.
        """
        staff = _slur_staff([
            [_slur_head(60), _slur_head(80), _slur_arc(66, 100, y=20)],
            [_slur_head(110), _slur_head(130), _slur_arc(100, 136, y=120)],
        ])
        assert annotate_slurs_in_staff(staff) == 2

    def test_a_slur_spanning_a_whole_measure_chains_through_it(self):
        """Three arcs, two barlines, one slur."""
        staff = _slur_staff([
            [_slur_head(80), _slur_arc(78, 100)],
            [_slur_head(150), _slur_arc(100, 200)],
            [_slur_head(210), _slur_arc(200, 215)],
        ])
        assert annotate_slurs_in_staff(staff) == 1
        assert _states(staff) == [(0, 80, 1, "start"), (2, 210, 1, "stop")]

    def test_the_arc_is_padded_because_it_is_narrower_than_its_run(self):
        """A slur is drawn between the noteheads, so its ink stops a hair
        inside the outer centres. Unpadded, the Contrabass read `n1 -> n4` in
        bars whose truth is `n0 -> n5`.
        """
        # centres at 15, 35, 55, 75; the arc's ink spans only 36..54
        staff = _slur_staff([[
            _slur_head(10), _slur_head(30), _slur_head(50), _slur_head(70),
            _slur_arc(36, 54),
        ]])
        annotate_slurs_in_staff(staff)
        # 30 and 50 are inside; 10 and 70 are more than a notehead away
        assert _states(staff) == [(0, 30, 1, "start"), (0, 50, 1, "stop")]

    def test_numbers_are_reused_once_a_slur_has_closed(self):
        """Consecutive slurs are all number 1 — a number only has to be unique
        among slurs open AT THE SAME TIME."""
        staff = _slur_staff([[
            _slur_head(10), _slur_head(30), _slur_head(60), _slur_head(80),
            _slur_arc(16, 34), _slur_arc(66, 84),
        ]])
        assert annotate_slurs_in_staff(staff) == 2
        assert {n for _m, _x, n, _k in _states(staff)} == {1}

    def test_overlapping_slurs_take_distinct_numbers(self):
        staff = _slur_staff([[
            _slur_head(10), _slur_head(30), _slur_head(50), _slur_head(70),
            _slur_arc(12, 52), _slur_arc(32, 72),
        ]])
        assert annotate_slurs_in_staff(staff) == 2
        assert {n for _m, _x, n, _k in _states(staff)} == {1, 2}

    def test_running_twice_does_not_stack_marks(self):
        """`to_musicxml` and `to_lilypond` may both be called on one result."""
        staff = _slur_staff([[
            _slur_head(10), _slur_head(30), _slur_head(50), _slur_arc(12, 52),
        ]])
        annotate_slurs_in_staff(staff)
        first = _states(staff)
        annotate_slurs_in_staff(staff)
        assert _states(staff) == first

    def test_a_staff_with_no_five_line_geometry_abstains(self):
        """Without the staff's own spacing there is no unit to measure the
        boundary in, and a rule in raw pixels means a different thing on every
        page."""
        staff = _slur_staff([[
            _slur_head(10), _slur_head(30), _slur_arc(12, 32),
        ]])
        staff["staff_geometry"] = None
        assert annotate_slurs_in_staff(staff) == 0

    def test_a_slur_whose_two_ends_share_one_chord_is_dropped(self):
        """A start and a stop on one note is a slur to nowhere. The drop
        happens in `group_chords_in_measure`, where the marks are lifted off
        the noteheads — the same place the tie flags are lifted."""
        head_a, head_b = _slur_head(10), _slur_head(11)
        head_a["slur_states"] = [(1, "start")]
        head_b["slur_states"] = [(1, "stop")]
        events = group_chords_in_measure([head_a, head_b])
        assert all("slur_states" not in e for e in events)


class TestSlurExport:
    def test_musicxml_carries_one_slur_across_a_barline(self):
        result = _tiny_result_empty_measure({"numerator": 4, "denominator": 4})
        staff = _slur_staff([
            [_slur_head(60), _slur_head(80), _slur_arc(66, 100)],
            [_slur_head(110), _slur_head(130), _slur_arc(100, 136)],
        ])
        result["pages"][0]["systems"][0]["staves"] = [staff]
        xml = to_musicxml(result)
        measures = ET.fromstring(xml).find("part").findall("measure")
        kinds = [[s.get("type") for s in m.iter("slur")] for m in measures]
        assert kinds == [["start"], ["stop"]], (
            "a slur crossing a barline must open in one measure and close in "
            "the next, not open and close in both"
        )

    def test_lilypond_carries_one_slur_across_a_barline(self):
        result = _tiny_result_empty_measure({"numerator": 4, "denominator": 4})
        staff = _slur_staff([
            [_slur_head(60), _slur_head(80), _slur_arc(66, 100)],
            [_slur_head(110), _slur_head(130), _slur_arc(100, 136)],
        ])
        result["pages"][0]["systems"][0]["staves"] = [staff]
        ly = to_lilypond(result)
        assert ly.count("(") == 1 and ly.count(")") == 1
        # the barline falls between the two, which is the whole point
        body = ly[ly.index("("):ly.index(")")]
        assert "|" in body

    def test_slurs_reach_the_stitched_multi_system_path(self):
        """A part is the same staff on every system, and `_staff_measures_xml`
        is where those measures are emitted — so that is where the staff-level
        slur pairing has to run. Every benchmark excerpt is single-system, so
        nothing else here would notice if the stitched path lost its slurs.
        """
        def _sys(n):
            return {"system_index": n, "n_staves": 3, "staves": [
                _slur_staff([
                    [_slur_head(60), _slur_head(80), _slur_arc(66, 100)],
                    [_slur_head(110), _slur_head(130), _slur_arc(100, 136)],
                ]),
                _slur_staff([
                    [_slur_head(20), _slur_head(60), _slur_arc(26, 66)],
                    [_slur_head(120), _slur_head(160)],
                ]),
                _slur_staff([[_slur_head(20)], [_slur_head(120)]]),
            ]}
        result = {"source_pdf": "synthetic.pdf", "pages": [
            {"page_index": 0, "n_systems": 2, "systems": [_sys(0), _sys(1)]}]}
        root = ET.fromstring(to_musicxml(result))
        parts = root.findall("part")
        assert len(parts) == 3, "the three staves should stitch into three parts"
        first = [[s.get("type") for s in m.iter("slur")]
                 for m in parts[0].findall("measure")]
        # four measures, and the slur still opens in one and closes in the next
        assert first == [["start"], ["stop"], ["start"], ["stop"]]

    def test_a_note_that_ends_one_slur_and_begins_the_next_closes_first(self):
        """LilyPond writes `d)(` — close what arrived, then open what leaves."""
        event = {"kind": "chord", "duration_type": "quarter",
                 "duration_beats": 1.0, "dots": 0,
                 "noteheads": [{"pitch": "C4"}],
                 "slur_states": [(2, "start"), (1, "stop")]}
        assert _lily_event(event).endswith(")\\=2(")


# ─── Tuplets ────────────────────────────────────────────────────────────────


def _tuplet_result():
    """One 3/4 bar: a half note, then a beamed eighth-note triplet.

    The shape of Mahler 5's opening trumpet call (there in 2/2 with a quarter
    rest between, dropped here so the fixture is only about the tuplet), which
    is where the cost of dropping tuplets was measured — 15 wrong durations,
    all of them a triplet read straight, 87 of that work's 154 OMR-NED edits.
    """
    def head(x, pitch, beats, dur_type, tuplet=False):
        nh = {"category": "notehead", "class": "noteheadBlackInSpace",
              "pitch": pitch, "duration_beats": beats,
              "duration_type": dur_type, "dots": 0,
              "bbox": [x, 100, 30, 20], "bbox_page": [x, 100, 30, 20]}
        if tuplet:
            nh["beam_levels"] = 1
            nh["tuplet"] = {"actual": 3, "normal": 2}
            nh["tuplet_group"] = 1
        return nh

    time_sig = {"numerator": 3, "denominator": 4}
    dets = [
        head(10, "D#4", 2.0, "half"),
        head(100, "D#4", 1 / 3, "eighth", tuplet=True),
        head(160, "D#4", 1 / 3, "eighth", tuplet=True),
        head(220, "D#4", 1 / 3, "eighth", tuplet=True),
    ]
    return {
        "source_pdf": "synthetic.pdf",
        "pages": [{
            "page_index": 0, "n_systems": 1,
            "systems": [{
                "system_index": 0, "n_staves": 1,
                "staves": [{
                    "staff_index": 0, "clef": "treble",
                    "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
                    "time_signature": time_sig, "n_measures": 1,
                    "measures": [{
                        "measure_index": 0, "bbox_page_px": [0, 0, 300, 50],
                        "clef": "treble",
                        "key_signature": {"sharps": 0, "flats": 0,
                                          "alterations": {}},
                        "time_signature": time_sig,
                        "n_detections": len(dets), "detections": dets,
                    }],
                }],
            }],
        }],
    }


class TestComputeDivisions:
    """`divisions` is an LCM, not a max, and that is what tuplets need.

    A triplet eighth is 1/3 of a quarter. The old ladder took the largest
    power of two, and 16 thirds is not a whole number, so every triplet got a
    rounded `<duration>` and the bar came out the wrong length.
    """

    @staticmethod
    def _with_beats(*beats):
        result = _tiny_result_empty_measure({"numerator": 4, "denominator": 4})
        measure = result["pages"][0]["systems"][0]["staves"][0]["measures"][0]
        measure["detections"] = [
            {"category": "notehead", "class": "noteheadBlackInSpace",
             "pitch": "C4", "duration_beats": b, "duration_type": "eighth",
             "dots": 0, "bbox": [i * 40, 100, 30, 20]}
            for i, b in enumerate(beats)
        ]
        return result

    @pytest.mark.parametrize("beats, expected", [
        ((1.0,), 4),
        ((0.5, 0.25), 4),
        ((0.125,), 8),
        ((0.0625,), 16),
        ((0.03125,), 32),
    ])
    def test_plain_note_values_are_unchanged(self, beats, expected):
        """Every power-of-two denominator: the LCM of powers of two IS their
        maximum, so scores without tuplets get exactly the old number."""
        assert _compute_divisions(self._with_beats(*beats)) == expected

    def test_a_third_forces_a_multiple_of_three(self):
        assert _compute_divisions(self._with_beats(1 / 3)) % 3 == 0

    def test_thirds_and_sixteenths_together(self):
        """max() would return 16 here and 16 thirds is not an integer."""
        divisions = _compute_divisions(self._with_beats(1 / 3, 0.0625))
        assert divisions % 3 == 0 and divisions % 16 == 0

    def test_noise_cannot_blow_divisions_up(self):
        assert _compute_divisions(self._with_beats(0.4999)) == 4


class TestTupletRuns:
    @staticmethod
    def _event(group=None):
        nh = {"pitch": "C4"}
        if group is not None:
            nh["tuplet"] = {"actual": 3, "normal": 2}
            nh["tuplet_group"] = group
        return {"kind": "chord", "duration_type": "eighth",
                "duration_beats": 1 / 3, "dots": 0, "noteheads": [nh]}

    def test_one_run(self):
        events = [self._event(), *[self._event(1) for _ in range(3)]]
        assert _tuplet_runs(events) == [(1, 3, {"actual": 3, "normal": 2})]

    def test_two_groups_are_two_runs(self):
        events = [*[self._event(1) for _ in range(3)],
                  *[self._event(2) for _ in range(3)]]
        assert [(a, b) for a, b, _ in _tuplet_runs(events)] == [(0, 2), (3, 5)]

    def test_a_plain_note_between_breaks_the_run(self):
        events = [self._event(1), self._event(), self._event(1)]
        assert [(a, b) for a, b, _ in _tuplet_runs(events)] == [(0, 0), (2, 2)]

    def test_no_tuplets_no_runs(self):
        assert _tuplet_runs([self._event(), self._event()]) == []

    def test_a_rest_carries_no_tuplet(self):
        rest = {"kind": "rest", "duration_type": "quarter",
                "duration_beats": 1.0, "dots": 0, "noteheads": []}
        assert _tuplet_runs([rest]) == []


class TestTupletExport:
    def test_musicxml_writes_the_ratio_on_every_note(self):
        xml = to_musicxml(_tuplet_result())
        assert xml.count("<time-modification>") == 3
        assert "<actual-notes>3</actual-notes>" in xml
        assert "<normal-notes>2</normal-notes>" in xml

    def test_musicxml_brackets_the_run_once(self):
        xml = to_musicxml(_tuplet_result())
        assert xml.count('<tuplet type="start" number="1"/>') == 1
        assert xml.count('<tuplet type="stop" number="1"/>') == 1

    def test_musicxml_keeps_the_written_note_value(self):
        """A triplet eighth is printed as an eighth; the ratio does the rest."""
        xml = to_musicxml(_tuplet_result())
        assert xml.count("<type>eighth</type>") == 3

    def test_musicxml_bar_is_the_right_length(self):
        """Half + three triplet eighths = 3 quarters, which is the 3/4 bar.
        Getting `divisions` wrong shows up here and nowhere else: at the old
        divisions=4 each triplet eighth rounds to 1 unit and the bar is short.
        """
        root = ET.fromstring(to_musicxml(_tuplet_result()))
        divisions = int(root.find(".//divisions").text)
        total = sum(int(d.text) for d in root.findall(".//note/duration"))
        assert total == 3 * divisions

    def test_musicxml_parses(self):
        ET.fromstring(to_musicxml(_tuplet_result()))

    def test_lilypond_wraps_the_run(self):
        out = to_lilypond(_tuplet_result())
        assert "\\tuplet 3/2 {" in out
        assert out.count("\\tuplet") == 1

    def test_lilypond_keeps_the_note_outside_the_run_outside(self):
        out = to_lilypond(_tuplet_result())
        line = next(ln for ln in out.splitlines() if "\\tuplet" in ln)
        assert line.index("dis'2") < line.index("\\tuplet")


class TestSlursAcrossSystemBreaks:
    """A part is the same staff on EVERY system, so a slur may run from the
    last bar of one system into the first bar of the next.

    The junction geometry is not the barline's. A barline cuts one arc and both
    halves end exactly on the cut; the resuming half of a system break begins
    well inside its cell, because that cell opens with a CLEF and a KEY
    SIGNATURE — measured at 5.28 staff spaces on the `systems` fixture. So the
    resuming half is anchored on the FIRST NOTE instead, which is what it
    attaches to and is independent of how wide the header is.
    """

    @staticmethod
    def _system_end(top):
        """A staff whose last cell holds an arc running off its right edge."""
        return _slur_staff([
            [_slur_head(20, y=top), _slur_head(60, y=top)],
            [_slur_head(150, y=top), _slur_arc(150, 200, y=top - 20)],
        ], top=top)

    @staticmethod
    def _system_start(top, arc=(10, 55)):
        """A staff whose first cell holds an arc running in from the margin."""
        return _slur_staff([
            [_slur_head(50, y=top), _slur_arc(arc[0], arc[1], y=top - 20)],
            [_slur_head(150, y=top)],
        ], top=top)

    def test_a_slur_joins_across_a_system_break(self):
        a, b = self._system_end(40), self._system_start(400)
        assert annotate_slurs_in_slot([a, b]) == 1
        assert a["measures"][1]["detections"][0]["slur_states"] == [(1, "start")]
        assert b["measures"][0]["detections"][0]["slur_states"] == [(1, "stop")]

    def test_one_staff_alone_never_makes_a_cross_system_slur(self):
        """`annotate_slurs_in_staff` is the single-staff case, and the LilyPond
        exporter uses it — a LilyPond slur cannot span two Staff contexts, so a
        cross-system slur there would be unpaired."""
        a, b = self._system_end(40), self._system_start(400)
        assert annotate_slurs_in_staff(a) == 0
        assert annotate_slurs_in_staff(b) == 0

    def test_an_arc_starting_ON_the_first_note_is_a_NEW_slur_not_a_resumption(self):
        """A resuming fragment runs in from the margin and ends on the first
        note; a slur that merely begins there runs the other way. The two are
        told apart by which side of the note the ink is on."""
        a = self._system_end(40)
        # arc spans from the first notehead rightwards, not into it
        b = self._system_start(400, arc=(55, 95))
        assert annotate_slurs_in_slot([a, b]) == 0

    def test_arcs_on_opposite_sides_of_their_staves_do_not_join(self):
        """One above its staff and one below is two slurs, however well they
        line up — the same rule the barline case uses, applied to a height
        relative to each staff's own lines."""
        a = self._system_end(40)
        b = _slur_staff([
            [_slur_head(50, y=400), _slur_arc(10, 55, y=400 + 60)],  # BELOW
            [_slur_head(150, y=400)],
        ], top=400)
        assert annotate_slurs_in_slot([a, b]) == 0

    def test_a_staff_with_no_geometry_breaks_the_chain_but_keeps_the_rest(self):
        """It cannot be measured, so nothing joins across it — but the slurs on
        the staves either side are still paired."""
        a = self._system_end(40)
        blind = self._system_start(400)
        blind["staff_geometry"] = None
        good = _slur_staff([[
            _slur_head(10, y=800), _slur_head(30, y=800), _slur_head(50, y=800),
            _slur_arc(12, 52, y=780),
        ]], top=800)
        assert annotate_slurs_in_slot([a, blind, good]) == 1
        assert good["measures"][0]["detections"][0]["slur_states"] == [(1, "start")]

    def test_musicxml_opens_in_one_system_and_closes_in_the_next(self):
        result = _tiny_result_empty_measure({"numerator": 4, "denominator": 4})
        page = result["pages"][0]
        page["systems"] = [
            {"system_index": 0, "n_staves": 2, "staves": [
                self._system_end(40), self._system_end(160)]},
            {"system_index": 1, "n_staves": 2, "staves": [
                self._system_start(400), self._system_start(520)]},
        ]
        root = ET.fromstring(to_musicxml(result))
        parts = root.findall("part")
        assert len(parts) == 2, "the two slots should stitch into two parts"
        kinds = [[s.get("type") for s in m.iter("slur")]
                 for m in parts[0].findall("measure")]
        # four measures: nothing, open at the end of system 1, close at the
        # start of system 2, nothing
        assert kinds == [[], ["start"], ["stop"], []]


# ─── the part's opening clef ────────────────────────────────────────────────


def _clef_det(x=6.0):
    return {"class": "cClefAlto", "category": "clef", "bbox": [x, 10, 8, 20],
            "bbox_page": [x, 10, 8, 20], "confidence": 0.8}


def _note_det(x, pitch="C4"):
    return {"class": "noteheadBlackOnLine", "category": "notehead",
            "bbox": [x, 10, 5, 5], "bbox_page": [x, 10, 5, 5],
            "confidence": 0.9, "pitch": pitch,
            "duration_beats": 1.0, "duration_type": "quarter", "dots": 0}


def _brace_det(x=2.0):
    return {"class": "brace", "category": "structural", "bbox": [x, 0, 3, 60],
            "bbox_page": [x, 0, 3, 60], "confidence": 0.33}


def _m(index, clef, dets):
    return {"measure_index": index, "bbox_page_px": [0, 0, 100, 50],
            "clef": clef,
            "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
            "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
            "n_detections": len(dets), "detections": dets}


def _staff_with(measures, clef="treble"):
    return {"staff_index": 0, "clef": clef,
            "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
            "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
            "n_measures": len(measures), "measures": measures}


def _one_staff_result(staff):
    return {"source_pdf": "synthetic.pdf",
            "pages": [{"page_index": 0, "n_systems": 1,
                       "systems": [{"system_index": 0, "n_staves": 1,
                                    "staves": [staff]}]}]}


class TestFirstClefBearingMeasure:
    """The Dvorak 9 mechanism: system furniture caught as measure 0 prints no
    clef, so the clef in EFFECT there is the positional default, and a part
    that takes its opening clef from measure 0 regardless exports as G2."""

    def test_a_clef_in_measure_zero_keeps_measure_zero(self):
        ms = [_m(0, "alto", [_clef_det(), _note_det(20)]),
              _m(1, "alto", [_note_det(20)])]
        assert _first_clef_bearing_measure(ms) == 0

    def test_a_leading_furniture_cell_defers_to_the_measure_that_read_one(self):
        ms = [_m(0, "treble", [_brace_det()]),
              _m(1, "alto", [_clef_det(), _note_det(20)])]
        assert _first_clef_bearing_measure(ms) == 1

    def test_an_utterly_empty_leading_cell_defers_too(self):
        """Four of Dvorak's fifteen leading cells hold no detection at all."""
        ms = [_m(0, "treble", []), _m(1, "bass", [_clef_det(), _note_det(20)])]
        assert _first_clef_bearing_measure(ms) == 1

    def test_two_leading_furniture_cells_both_defer(self):
        ms = [_m(0, "treble", [_brace_det()]), _m(1, "treble", []),
              _m(2, "bass", [_clef_det(), _note_det(20)])]
        assert _first_clef_bearing_measure(ms) == 2

    def test_a_leading_cell_that_holds_MUSIC_is_never_skipped(self):
        """The notes there were resolved under the clef in effect there, so
        overruling it would claim a clef the exported pitches do not belong to
        — even though no clef was detected in it."""
        ms = [_m(0, "treble", [_note_det(20)]),
              _m(1, "bass", [_clef_det(), _note_det(20)])]
        assert _first_clef_bearing_measure(ms) == 0

    def test_a_tacet_leading_bar_holds_its_whole_rest_and_is_music(self):
        rest = {"class": "restWhole", "category": "rest", "bbox": [20, 10, 6, 4],
                "bbox_page": [20, 10, 6, 4], "confidence": 0.8,
                "duration_beats": 4.0, "duration_type": "whole", "dots": 0}
        ms = [_m(0, "bass", [rest]), _m(1, "tenor", [_clef_det(), _note_det(20)])]
        assert _first_clef_bearing_measure(ms) == 0

    def test_nothing_qualifies_falls_back_to_measure_zero(self):
        ms = [_m(0, "treble", [_brace_det()]), _m(1, "treble", [])]
        assert _first_clef_bearing_measure(ms) == 0

    def test_no_measures_at_all(self):
        assert _first_clef_bearing_measure([]) == 0


class TestOpeningClefInExport:
    def test_musicxml_opens_on_the_read_clef_not_the_furniture_default(self):
        staff = _staff_with([
            _m(0, "treble", [_brace_det()]),
            _m(1, "alto", [_clef_det(), _note_det(20)]),
            _m(2, "alto", [_note_det(20)]),
        ])
        root = ET.fromstring(to_musicxml(_one_staff_result(staff)))
        clefs = [(m.get("number"), c.findtext("sign"), c.findtext("line"))
                 for m in root.iter("measure") for c in m.iter("clef")]
        # one clef, in the opening measure, and no spurious change after it
        assert clefs == [("1", "C", "3")]

    def test_a_genuine_mid_part_clef_change_is_untouched(self):
        staff = _staff_with([
            _m(0, "bass", [_clef_det(), _note_det(20)]),
            _m(1, "tenor", [_clef_det(), _note_det(20)]),
        ])
        root = ET.fromstring(to_musicxml(_one_staff_result(staff)))
        clefs = [(m.get("number"), c.findtext("sign"), c.findtext("line"))
                 for m in root.iter("measure") for c in m.iter("clef")]
        assert clefs == [("1", "F", "4"), ("2", "C", "4")]

    def test_lilypond_has_no_clef_change_to_recover_with(self):
        """`_lily_staff_block` emits one `\\clef` for the whole staff, so a
        leading furniture cell costs LilyPond the clef outright."""
        staff = _staff_with([
            _m(0, "treble", [_brace_det()]),
            _m(1, "alto", [_clef_det(), _note_det(20)]),
        ])
        assert "\\clef alto" in to_lilypond(_one_staff_result(staff))
# ─── Fermatas: detected since Phase 3.3, exported since 2026-09-01 ──────────
#
# `fermataAbove` is in the DSv2 class space and the detector reads it at 0.90 -
# 0.95 on the engraved Beethoven page. `grep -c fermata export.py` returned 0:
# the sixth signal in this file's history that was computed and then dropped on
# the way out. The commonest carrier on an orchestral page is a WHOLE-BAR REST,
# which is why pairing is by x against notes and rests alike.


def _head(x, w=40, pitch="C4"):
    return {"bbox_page": [x, 100, w, 40], "pitch": pitch}


def _note_event(x, w=40, pitch="C4"):
    return {"kind": "chord", "duration_beats": 1.0, "duration_type": "quarter",
            "dots": 0, "noteheads": [_head(x, w, pitch)], "rest": None,
            "x_position": x}


def _rest_event(x, w=60):
    return {"kind": "rest", "duration_beats": 2.0, "duration_type": "half",
            "dots": 0, "noteheads": [], "x_position": x,
            "rest": {"bbox_page": [x, 100, w, 30]}}


def _fermata(x, w=50):
    return {"class": "fermataAbove", "category": "ornament",
            "bbox_page": [x, 20, w, 30]}


class TestAnnotateFermatas:

    def test_a_fermata_over_a_rest_marks_the_rest(self):
        """The case that matters: 22 of the benchmark's 36 sit over rests."""
        events = [_rest_event(100)]
        assert annotate_fermatas(events, [_fermata(110)]) == 1
        assert events[0]["fermata"] is True

    def test_a_fermata_over_a_note_marks_the_note(self):
        events = [_note_event(100)]
        assert annotate_fermatas(events, [_fermata(105)]) == 1
        assert events[0]["fermata"] is True

    def test_the_mark_goes_to_the_event_it_sits_over(self):
        events = [_note_event(100), _note_event(400), _note_event(700)]
        annotate_fermatas(events, [_fermata(405)])
        assert [bool(e.get("fermata")) for e in events] == [False, True, False]

    def test_a_fermata_between_events_goes_to_the_nearer(self):
        # A fermata over a bar's only rest is engraved at the BAR's middle,
        # while the rest glyph sits at its own centre — so containment alone
        # would miss the commonest case of all.
        events = [_rest_event(100, w=60), _note_event(900)]
        annotate_fermatas(events, [_fermata(200)])
        assert events[0].get("fermata") and not events[1].get("fermata")

    def test_no_detections_marks_nothing(self):
        events = [_note_event(100)]
        assert annotate_fermatas(events, []) == 0
        assert "fermata" not in events[0]

    def test_two_fermatas_on_one_event_count_once(self):
        events = [_note_event(100)]
        assert annotate_fermatas(events, [_fermata(105), _fermata(108)]) == 1

    def test_it_is_safe_on_a_measure_with_no_events(self):
        assert annotate_fermatas([], [_fermata(100)]) == 0


class TestFermataReachesTheOutput:

    def test_musicxml_puts_it_in_notations(self):
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, is_chord=False,
                        is_rest=False, indent="  ", fermata=True)
        assert "<notations>" in xml and '<fermata type="upright"/>' in xml

    def test_musicxml_omits_it_when_absent(self):
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, is_chord=False,
                        is_rest=False, indent="  ")
        assert "fermata" not in xml

    def test_a_rest_can_carry_one(self):
        xml = _mxl_note(None, "", "half", 0, 2.0, 4, is_chord=False,
                        is_rest=True, indent="  ", fermata=True)
        assert "<rest/>" in xml and '<fermata type="upright"/>' in xml

    def test_the_notations_block_stays_single(self):
        """A second <notations> per note is invalid MusicXML."""
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, is_chord=False,
                        is_rest=False, indent="  ", fermata=True,
                        tied_to_next=True, slur_states=[(1, "start")])
        assert xml.count("<notations>") == 1
        for tag in ("<tied", "<slur", "<fermata"):
            assert tag in xml


# ─── Accidentals: the printed glyph, not the pitch ─────────────────────────
#
# The seventh instance of this file's recurring shape, and the one that hid the
# longest, because the signal was not merely detected — it was detected, paired
# to its notehead, USED to resolve the pitch, and then the fact that a glyph had
# been drawn was discarded. MusicXML separates `<alter>` (what sounds) from
# `<accidental>` (what is printed) and we had only ever emitted the first.
# Measured: 65 `<accidental>` elements in the benchmark truth, 0 in ours, and
# all 64 `wrong accidental` edits were `accidentins`.


class TestAccidentalIsThePrintedGlyph:

    @pytest.mark.parametrize("alteration, expected", [
        ("#", "sharp"),
        ("b", "flat"),
        ("natural", "natural"),
        ("##", "double-sharp"),
        ("bb", "flat-flat"),
    ])
    def test_each_alteration_maps_to_its_musicxml_name(self, alteration, expected):
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, is_chord=False,
                        is_rest=False, indent="  ", accidental=alteration)
        assert f"<accidental>{expected}</accidental>" in xml

    def test_no_accidental_emits_nothing(self):
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, is_chord=False,
                        is_rest=False, indent="  ")
        assert "<accidental>" not in xml

    def test_an_unknown_alteration_emits_nothing(self):
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, is_chord=False,
                        is_rest=False, indent="  ", accidental="?")
        assert "<accidental>" not in xml

    def test_a_natural_is_a_printed_glyph_on_an_unaltered_pitch(self):
        """The case that makes this a separate fact from the pitch.

        `<alter>` is absent or 0 and the engraver still drew a natural — which
        is exactly what every one of the benchmark's `accidentins` edits was.
        """
        xml = _mxl_note("C4", "", "quarter", 0, 1.0, 4, is_chord=False,
                        is_rest=False, indent="  ", accidental="natural")
        assert "<accidental>natural</accidental>" in xml
        assert "<alter>" not in xml

    def test_it_sits_after_the_dots_and_before_time_modification(self):
        """DTD order, and the order the truth files use."""
        xml = _mxl_note("C4", "", "quarter", 1, 1.5, 4, is_chord=False,
                        is_rest=False, indent="  ", accidental="sharp"
                        if False else "#",
                        time_modification={"actual": 3, "normal": 2})
        assert xml.index("<dot/>") < xml.index("<accidental>")
        assert xml.index("<accidental>") < xml.index("<time-modification>")

    def test_a_rest_never_carries_one(self):
        xml = _mxl_note(None, "", "half", 0, 2.0, 4, is_chord=False,
                        is_rest=True, indent="  ")
        assert "<accidental>" not in xml


# ─── The glyph through the exporters end to end ─────────────────────────────
#
# The class above tests `_mxl_note` in isolation; these follow the field the
# whole way — through `group_chords_in_measure` (the event carries raw
# notehead dicts, which is what threads it) into `to_musicxml`, and through
# `_lily_event` into the LilyPond text. The LilyPond side is `!`, measured
# rather than assumed: LilyPond re-derives 62 of the benchmark's 65 recorded
# glyphs from the pitch stream on its own, and the 3 it drops are COURTESY
# accidentals — A-flats restating the key signature on three Brahms staves —
# which is exactly what `!` exists to force. Plain `!`, not `?`, because the
# page prints them plain and `?` parenthesizes.


class TestAccidentalReachesBothOutputs:
    def test_it_survives_to_musicxml_end_to_end(self):
        result = _tiny_result()
        dets = result["pages"][0]["systems"][0]["staves"][0]["measures"][0][
            "detections"]
        dets[0]["accidental"] = "natural"
        dets[1]["accidental"] = "#"
        xml = to_musicxml(result)
        assert "<accidental>natural</accidental>" in xml
        assert "<accidental>sharp</accidental>" in xml
        # The other two noteheads carried no glyph.
        assert xml.count("<accidental>") == 2

    def test_each_chord_member_keeps_its_own(self):
        """A chord can carry a glyph on any subset of its members — the one
        per-note mark that must NOT be first-note-only, and the reason
        `_mxl_voice_events` passes it per notehead rather than per event."""
        result = _tiny_result()
        measure = result["pages"][0]["systems"][0]["staves"][0]["measures"][0]
        # Stack the four noteheads at one x so they group as a single chord.
        for i, d in enumerate(measure["detections"]):
            d["bbox"] = [10, 10 + 8 * i, 5, 5]
            d["bbox_page"] = [10, 10 + 8 * i, 5, 5]
        measure["detections"][2]["accidental"] = "b"
        xml = to_musicxml(result)
        assert xml.count("<chord/>") == 3
        assert xml.count("<accidental>") == 1
        assert "<accidental>flat</accidental>" in xml

    def test_a_rest_never_carries_one_even_if_handed_one(self):
        xml = _mxl_note(None, "", "half", 0, 2.0, 4, is_chord=False,
                        is_rest=True, indent="  ", accidental="#")
        assert "<accidental>" not in xml

    def test_lilypond_forces_the_read_glyph(self):
        event = {"kind": "chord", "duration_beats": 1.0,
                 "duration_type": "quarter", "dots": 0,
                 "noteheads": [{"pitch": "Ab4", "accidental": "b"}],
                 "rest": None}
        assert _lily_event(event) == "aes'!4"

    def test_lilypond_leaves_unmarked_notes_alone(self):
        event = {"kind": "chord", "duration_beats": 1.0,
                 "duration_type": "quarter", "dots": 0,
                 "noteheads": [{"pitch": "Ab4"}], "rest": None}
        assert _lily_event(event) == "aes'4"

    def test_lilypond_chord_members_force_independently(self):
        event = {"kind": "chord", "duration_beats": 1.0,
                 "duration_type": "quarter", "dots": 0,
                 "noteheads": [{"pitch": "C4", "accidental": "natural"},
                               {"pitch": "E4"}],
                 "rest": None}
        assert _lily_event(event) == "<c'! e'>4"


# ─── Two-voice staves: the absent voice is invisible, not an echo ───────────
#
# From Phase 4h until 2026-09-02, a measure where `split_events_into_voices`
# found only ONE voice fed that voice to BOTH `\new Voice` blocks
# (`v2_events = voices[0]`), so every note in it printed twice — once per
# voice, each copy with its voice's forced stem. Measured on the Brahms
# benchmark page: 4 two-voice staves, 23 such measures, 62 noteheads drawn
# twice (73 forced-accidental tokens from 54 recorded glyphs, which is how it
# was noticed). The absent voice now takes a SPACER (`s`, invisible), because
# the page shows nothing there; a printed rest would be the same bug in rest
# form. And a lone voice whose stems all point DOWN is the second voice
# playing alone, so it is routed to `\voiceTwo` — which is what preserves its
# printed stem direction — 13 of the 23.

from tools.omr.export import (  # noqa: E402  (late, beside the tests that use them)
    _lily_measure_spacer,
    _lily_staff_block,
    _lone_voice_is_the_second,
)


def _nh(x, pitch, stem, dur=("quarter", 1.0)):
    return {"class": "noteheadBlackOnLine", "category": "notehead",
            "bbox": [x, 10, 5, 5], "bbox_page": [x, 10, 5, 5],
            "confidence": 0.9, "pitch": pitch, "duration_beats": dur[1],
            "duration_type": dur[0], "dots": 0, "stem_direction": stem}


def _two_voice_staff(measures):
    return {"staff_index": 0, "clef": "treble",
            "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
            "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
            "n_measures": len(measures),
            "measures": [
                {"measure_index": i, "bbox_page_px": [0, 0, 100, 50],
                 "n_detections": len(dets), "detections": dets}
                for i, dets in enumerate(measures)]}


class TestTwoVoiceStaffDoesNotEcho:
    # A genuinely two-voice measure, to force the staff onto the two-voice
    # path: four quarters up, four quarters down.
    SPLIT = ([_nh(x, "C5", "up") for x in (10, 30, 50, 70)]
             + [_nh(x, "E4", "down") for x in (12, 32, 52, 72)])

    def test_a_single_voice_measure_renders_once(self):
        # Measure 2 is voice 1 alone: its four notes must appear exactly once.
        solo = [_nh(x, "G4", "up") for x in (10, 30, 50, 70)]
        out = _lily_staff_block(_two_voice_staff([self.SPLIT, solo]))
        assert out.count("g'4 g'4 g'4 g'4") == 1
        assert "s1 |" in out  # the absent voice, invisible

    def test_the_absent_voice_is_a_spacer_not_a_printed_rest(self):
        solo = [_nh(x, "G4", "up") for x in (10, 30, 50, 70)]
        out = _lily_staff_block(_two_voice_staff([self.SPLIT, solo]))
        v2 = out[out.index("\\voiceTwo"):]
        assert "s1 |" in v2
        assert "r1" not in v2  # nothing printed where the page shows nothing

    def test_a_lone_all_stem_down_measure_is_the_second_voice(self):
        solo_down = [_nh(x, "E4", "down") for x in (10, 30, 50, 70)]
        out = _lily_staff_block(_two_voice_staff([self.SPLIT, solo_down]))
        v1 = out[out.index("\\voiceOne"):out.index("\\voiceTwo")]
        v2 = out[out.index("\\voiceTwo"):]
        assert "e'4 e'4 e'4 e'4" in v2  # keeps its printed stem direction
        assert "e'4 e'4 e'4 e'4" not in v1
        assert "s1 |" in v1

    def test_an_empty_measure_prints_one_rest_not_two(self):
        out = _lily_staff_block(_two_voice_staff([self.SPLIT, []]))
        v1 = out[out.index("\\voiceOne"):out.index("\\voiceTwo")]
        v2 = out[out.index("\\voiceTwo"):]
        assert "r1 |" in v1   # the page's whole-bar rest, once
        assert "s1 |" in v2

    def test_single_voice_staves_are_untouched(self):
        solo = [_nh(x, "G4", "up") for x in (10, 30, 50, 70)]
        out = _lily_staff_block(_two_voice_staff([solo, solo]))
        assert "\\voiceOne" not in out and "s1" not in out

    @pytest.mark.parametrize("time_sig, expected", [
        ({"numerator": 4, "denominator": 4}, "s1"),
        ({"numerator": 3, "denominator": 4}, "s2."),
        ({"numerator": 5, "denominator": 4}, "s1*5/4"),
        (None, "s1"),
    ])
    def test_spacer_matches_the_measure_rest_arithmetic(self, time_sig, expected):
        assert _lily_measure_spacer(time_sig) == expected

    def test_lone_voice_routing_needs_unanimous_down_stems(self):
        down = [{"kind": "chord", "stem_direction": "down"}]
        mixed = [{"kind": "chord", "stem_direction": "down"},
                 {"kind": "chord", "stem_direction": None}]
        rests_only = [{"kind": "rest"}]
        assert _lone_voice_is_the_second(down)
        assert not _lone_voice_is_the_second(mixed)
        assert not _lone_voice_is_the_second(rests_only)
        assert not _lone_voice_is_the_second([])


# ─── Arc reclassification (OMR_ARC_RECLASS) ─────────────────────────────────
# A tie and a slur are the same glyph; the notes they connect tell them apart
# (docs/position-grammar-confusables-2026-09-04.md §2 ARC, rule R3: veto the
# impossible, abstain otherwise). Off by default; every test that wants it on
# says so through the environment.


def _tie_arc(x0, x1, y=41):
    """A detector tie arc. Sits at notehead height, unlike `_slur_arc`'s
    default, because a tie is drawn between its heads and the flank pairing
    has a y-gate."""
    return {"category": "structural", "class": "tie",
            "bbox": [x0, y, x1 - x0, 8], "bbox_page": [x0, y, x1 - x0, 8]}


def _rest_at(x, y=40):
    return {"category": "rest", "class": "restQuarter",
            "duration_beats": 1.0, "duration_type": "quarter", "dots": 0,
            "bbox": [x, y, 10, 10], "bbox_page": [x, y, 10, 10],
            "confidence": 0.9}


def _tie_flags(staff):
    """Every tie flag on the staff, as (measure, x, flag)."""
    out = []
    for m_idx, measure in enumerate(staff["measures"]):
        for det in measure["detections"]:
            for key in ("tied_to_next", "tied_from_prev"):
                if det.get(key):
                    out.append((m_idx, det["bbox_page"][0], key))
    return sorted(out)


@pytest.fixture
def arc_reclass_on(monkeypatch):
    monkeypatch.setenv("OMR_ARC_RECLASS", "1")
    from tools.omr import export as _export
    _export.reset_arc_reclass_stats()
    yield
    _export.reset_arc_reclass_stats()


class TestArcReclassOff:
    """The default. Nothing moves, whatever the configuration says."""

    def test_a_two_note_same_pitch_slur_stays_a_slur(self, monkeypatch):
        monkeypatch.delenv("OMR_ARC_RECLASS", raising=False)
        staff = _slur_staff([[
            _slur_head(10, pitch="C4"), _slur_head(30, pitch="C4"),
            _slur_arc(12, 38),
        ]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []

    def test_an_impossible_tie_keeps_its_flags(self, monkeypatch):
        monkeypatch.delenv("OMR_ARC_RECLASS", raising=False)
        a = _slur_head(10, pitch="C4")
        b = _slur_head(40, pitch="E4")
        a["tied_to_next"] = True
        b["tied_from_prev"] = True
        staff = _slur_staff([[a, b, _tie_arc(20, 40)]])
        annotate_slurs_in_staff(staff)
        assert _tie_flags(staff) == [
            (0, 10, "tied_to_next"), (0, 40, "tied_from_prev")]
        assert _states(staff) == []


class TestSlurToTie:
    """An arc classed `slur` whose ends land on exactly two adjacent
    same-pitch noteheads is a tie — the duration-semantic reading, the safer
    error where print alone cannot decide."""

    def test_two_adjacent_same_pitch_heads_become_a_tie(self, arc_reclass_on):
        staff = _slur_staff([[
            _slur_head(10, pitch="C4"), _slur_head(30, pitch="C4"),
            _slur_arc(12, 38),
        ]])
        assert annotate_slurs_in_staff(staff) == 0
        assert _states(staff) == []
        assert _tie_flags(staff) == [
            (0, 10, "tied_to_next"), (0, 30, "tied_from_prev")]

    def test_the_canonical_tie_crosses_a_barline_as_two_fragments(
            self, arc_reclass_on):
        """Cells are cut per measure, so the commonest tie in real music —
        last note of one bar to first of the next — arrives as two slur
        fragments. The veto must see the MERGED arc or it can never fire on
        the configuration it exists for."""
        staff = _slur_staff([
            [_slur_head(80, pitch="G4"), _slur_arc(86, 100)],
            [_slur_head(110, pitch="G4"), _slur_arc(100, 116)],
        ])
        assert annotate_slurs_in_staff(staff) == 0
        assert _tie_flags(staff) == [
            (0, 80, "tied_to_next"), (1, 110, "tied_from_prev")]

    def test_different_pitches_stay_a_slur(self, arc_reclass_on):
        staff = _slur_staff([[
            _slur_head(10, pitch="C4"), _slur_head(30, pitch="D4"),
            _slur_arc(12, 38),
        ]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []

    def test_three_heads_stay_a_slur_even_on_one_pitch(self, arc_reclass_on):
        staff = _slur_staff([[
            _slur_head(10, pitch="C4"), _slur_head(30, pitch="C4"),
            _slur_head(50, pitch="C4"), _slur_arc(12, 58),
        ]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []

    def test_a_rest_between_the_heads_stays_a_slur(self, arc_reclass_on):
        """A tie cannot cross a rest, so same-pitch heads with one between
        them are not the tie configuration — the rest spends an event ordinal
        and the two heads stop being adjacent."""
        staff = _slur_staff([[
            _slur_head(10, pitch="C4"), _rest_at(30),
            _slur_head(50, pitch="C4"), _slur_arc(12, 58),
        ]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []

    def test_a_pair_the_transcription_already_tied_loses_nothing(
            self, arc_reclass_on):
        """Both a tie and a slur detected over one pair: the veto agrees with
        the tie and adds no duplicate bookkeeping."""
        a = _slur_head(10, pitch="C4")
        b = _slur_head(30, pitch="C4")
        a["tied_to_next"] = True
        b["tied_from_prev"] = True
        staff = _slur_staff([[a, b, _slur_arc(12, 38)]])
        annotate_slurs_in_staff(staff)
        assert _tie_flags(staff) == [
            (0, 10, "tied_to_next"), (0, 30, "tied_from_prev")]
        assert not a.get("arc_reclass_added")


class TestTieToSlur:
    """An arc classed `tie` spanning more than two note events, or whose two
    heads carry different pitches, cannot be a tie."""

    @staticmethod
    def _flagged_pair_staff(pitch_b="E4"):
        a = _slur_head(10, pitch="C4")
        b = _slur_head(40, pitch=pitch_b)
        a["tied_to_next"] = True
        b["tied_from_prev"] = True
        return a, b, _slur_staff([[a, b, _tie_arc(20, 40)]])

    def test_a_different_pitch_pair_becomes_a_slur(self, arc_reclass_on):
        a, b, staff = self._flagged_pair_staff()
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []
        # The slur joins the SAME two notes the impossible tie claimed —
        # the arc is widened to the flanked centres, or a flanking arc
        # covers nothing and the promised slur degrades to a deletion.
        assert _states(staff) == [(0, 10, 1, "start"), (0, 40, 1, "stop")]

    def test_a_same_pitch_pair_is_a_legal_tie_and_stands(self, arc_reclass_on):
        a, b, staff = self._flagged_pair_staff(pitch_b="C4")
        assert annotate_slurs_in_staff(staff) == 0
        assert _tie_flags(staff) == [
            (0, 10, "tied_to_next"), (0, 40, "tied_from_prev")]

    def test_a_tie_arc_over_three_events_becomes_a_slur(self, arc_reclass_on):
        """Same pitch throughout, so only the span refutes it — a tie joins
        two adjacent notes and nothing else."""
        a = _slur_head(10, pitch="C4")
        mid = _slur_head(40, pitch="C4")
        c = _slur_head(70, pitch="C4")
        a["tied_to_next"] = True
        c["tied_from_prev"] = True
        staff = _slur_staff([[a, mid, c, _tie_arc(20, 70)]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []
        assert _states(staff) == [(0, 10, 1, "start"), (0, 70, 1, "stop")]

    def test_an_unpaired_tie_arc_over_a_run_becomes_a_slur(
            self, arc_reclass_on):
        """An arc classed tie that never paired — a real tie spans a gap and
        covers nothing, so three covered events are decisively slur-shaped."""
        staff = _slur_staff([[
            _slur_head(10, pitch="C4"), _slur_head(30, pitch="D4"),
            _slur_head(50, pitch="E4"), _slur_head(70, pitch="F4"),
            _tie_arc(12, 78, y=20),
        ]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _states(staff) == [(0, 10, 1, "start"), (0, 70, 1, "stop")]

    def test_an_unpaired_arc_over_nothing_abstains(self, arc_reclass_on):
        """No heads under it, none flanking it: nothing is decidable, and the
        arc exports what it always exported — nothing."""
        staff = _slur_staff([[
            _slur_head(10, pitch="C4"), _tie_arc(60, 90),
        ]])
        assert annotate_slurs_in_staff(staff) == 0
        assert _tie_flags(staff) == []
        assert _states(staff) == []


class TestArcReclassBookkeeping:
    def test_flag_off_after_flag_on_restores_the_transcription(
            self, monkeypatch):
        """The annotate pass must take back what an earlier flag-on pass did
        — added tie flags come off, removed ones go back on — so one result
        dict can be exported under either configuration in either order."""
        a = _slur_head(10, pitch="C4")
        b = _slur_head(40, pitch="E4")
        a["tied_to_next"] = True
        b["tied_from_prev"] = True
        staff = _slur_staff([[a, b, _tie_arc(20, 40),
                              _slur_head(60, pitch="G4"),
                              _slur_head(80, pitch="G4"),
                              _slur_arc(62, 88)]])
        monkeypatch.setenv("OMR_ARC_RECLASS", "1")
        annotate_slurs_in_staff(staff)
        assert _tie_flags(staff) == [
            (0, 60, "tied_to_next"), (0, 80, "tied_from_prev")]
        monkeypatch.setenv("OMR_ARC_RECLASS", "0")
        annotate_slurs_in_staff(staff)
        assert _tie_flags(staff) == [
            (0, 10, "tied_to_next"), (0, 40, "tied_from_prev")]
        assert _states(staff) == [(0, 60, 1, "start"), (0, 80, 1, "stop")]

    def test_flag_on_annotation_is_idempotent(self, arc_reclass_on):
        a = _slur_head(10, pitch="C4")
        b = _slur_head(40, pitch="E4")
        a["tied_to_next"] = True
        b["tied_from_prev"] = True
        staff = _slur_staff([[a, b, _tie_arc(20, 40)]])
        annotate_slurs_in_staff(staff)
        first = (_states(staff), _tie_flags(staff))
        annotate_slurs_in_staff(staff)
        assert (_states(staff), _tie_flags(staff)) == first

    def test_the_conversion_reaches_musicxml(self, arc_reclass_on):
        result = _tiny_result_empty_measure({"numerator": 4, "denominator": 4})
        staff = _slur_staff([[
            _slur_head(10, pitch="C4", width=20),
            _slur_head(50, pitch="C4", width=20),
            _slur_arc(15, 55),
        ]])
        result["pages"][0]["systems"][0]["staves"] = [staff]
        xml = to_musicxml(result)
        assert '<tie type="start"/>' in xml and '<tie type="stop"/>' in xml
        assert "<slur" not in xml

    def test_flank_pair_mirrors_transcribes_pairing(self):
        """`_tie_flank_pair` re-derives the pair `_pair_ties_in_staff` flags,
        on the same bbox_page data — mirrored rather than imported, because
        transcribe drags the whole detection stack in with it. If the two
        ever disagree, the veto would clear one pair's flags and the export
        would keep another's."""
        from tools.omr import transcribe as tr
        from tools.omr.export import _tie_flank_pair
        heads = [_slur_head(x, pitch=p) for x, p in
                 ((10, "C4"), (40, "E4"), (70, "F4"))]
        staff = _slur_staff([[*heads, _tie_arc(20, 40)]])
        tr._pair_ties_in_staff(staff)
        flagged = {(det["bbox_page"][0], key)
                   for m in staff["measures"] for det in m["detections"]
                   for key in ("tied_to_next", "tied_from_prev")
                   if det.get(key)}
        pair = _tie_flank_pair([20, 41, 20, 8], heads)
        assert pair is not None
        left, right = pair
        assert flagged == {(left["bbox_page"][0], "tied_to_next"),
                           (right["bbox_page"][0], "tied_from_prev")}


class TestArcReclassStepKey:
    """The veto compares STAFF STEPS, never spelled pitches — measured on the
    engraved A/B, where every losing veto was a same-step pair differing only
    in accidental (`F#4 -> F4`): the far head of a cross-barline tie does not
    restate its accidental and the resolver spells it plain. The conversion
    direction keeps the STRICT key: acting needs strong evidence both ways."""

    def test_a_same_step_different_accidental_tie_stands(self, arc_reclass_on):
        a = _slur_head(10, pitch="F#4")
        b = _slur_head(40, pitch="F4")
        a["tied_to_next"] = True
        b["tied_from_prev"] = True
        staff = _slur_staff([[a, b, _tie_arc(20, 40)]])
        assert annotate_slurs_in_staff(staff) == 0
        assert _tie_flags(staff) == [
            (0, 10, "tied_to_next"), (0, 40, "tied_from_prev")]

    def test_a_step_apart_tie_is_still_vetoed(self, arc_reclass_on):
        a = _slur_head(10, pitch="F#4")
        b = _slur_head(40, pitch="G4")
        a["tied_to_next"] = True
        b["tied_from_prev"] = True
        staff = _slur_staff([[a, b, _tie_arc(20, 40)]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []

    def test_slur_to_tie_still_needs_the_full_pitch_to_agree(
            self, arc_reclass_on):
        """A slur over F#4 -> F4 is a chromatic-neighbour slur, real music;
        step equality is not enough to assert tie-ness."""
        staff = _slur_staff([[
            _slur_head(10, pitch="F#4"), _slur_head(30, pitch="F4"),
            _slur_arc(12, 38),
        ]])
        assert annotate_slurs_in_staff(staff) == 1
        assert _tie_flags(staff) == []


# ---------------------------------------------------------------------------
# Cross-staff arc attribution
# ---------------------------------------------------------------------------

def _arc_staff(top, heads_y, *, spacing=10.0, n_measures=1, arcs=()):
    """A one-system staff whose cells tile [0,100), … with heads at `heads_y`.

    `arcs` are `(x0, y0, x1, y1)` page boxes dropped into measure 0, which is
    where a padding-caught neighbour's arc lands.
    """
    measures = []
    for i in range(n_measures):
        dets = [{"category": "notehead", "class": "noteheadBlack", "pitch": "C4",
                 "duration_type": "quarter", "duration_beats": 1.0, "dots": 0,
                 "confidence": 0.9,
                 "bbox": [i * 100 + x, heads_y, 10, 10],
                 "bbox_page": [i * 100 + x, heads_y, 10, 10]}
                for x in (10, 30, 50, 70)]
        if i == 0:
            for (x0, y0, x1, y1) in arcs:
                dets.append({"category": "structural", "class": "slur",
                             "bbox": [x0, y0, x1 - x0, y1 - y0],
                             "bbox_page": [x0, y0, x1 - x0, y1 - y0]})
        measures.append({"measure_index": i,
                         "bbox_page_px": [i * 100, top - 60, (i + 1) * 100, top + 60],
                         "detections": dets})
    return {"staff_index": 0, "clef": "treble",
            "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
            "time_signature": {"numerator": 4, "denominator": 4},
            "staff_geometry": {
                "line_ys_page": [top + d for d in (0, 10, 20, 30, 40)],
                "line_spacing_px": spacing, "x_start": 0,
                "x_end": 100 * n_measures},
            "n_measures": n_measures, "measures": measures}


def _arc_result(staves):
    return {"pages": [{"page_index": 0, "systems": [{"staves": staves}]}]}


def _arc_classes(staff):
    return [d["class"] for m in staff["measures"]
            for d in m["detections"] if d["category"] == "structural"]


class TestArcAttribution:
    """An arc belongs to the staff whose NOTEHEADS it hugs, not the staff whose
    cell padding happened to catch it.

    The Brahms 1 shape: Violin 1 plays four ledger lines above its staff, so
    its slurs are drawn high in the wide gap below the Timpani — inside the
    Timpani's grown padding and above the top of Violin 1's own cell, so the
    arc exists ONLY in the wrong staff and no duplicate-resolution rule can
    reach it.
    """

    @staticmethod
    def _bled():
        """Upper staff holds an arc that hugs the LOWER staff's ledger notes."""
        upper = _arc_staff(100, 120, arcs=[(10, 185, 90, 195)])
        lower = _arc_staff(300, 200)
        return upper, lower

    def test_an_arc_hugging_the_neighbour_moves_to_it(self):
        upper, lower = self._bled()
        assert arbitrate_arcs_across_staves(_arc_result([upper, lower])) == 1
        assert _arc_classes(upper) == []
        assert _arc_classes(lower) == ["slur"]
        moved = [d for m in lower["measures"] for d in m["detections"]
                 if d["category"] == "structural"][0]
        assert moved["arc_reattributed_from_staff"] == 0

    def test_an_arc_hugging_its_own_notes_stays(self):
        """The rival covers it in x just as well; what it does not do is hug
        it. Distance to the staff LINES is the trap this avoids — the arc sits
        outside its own staff, which is where slurs go."""
        upper = _arc_staff(100, 120, arcs=[(10, 105, 90, 113)])
        lower = _arc_staff(300, 200)
        assert arbitrate_arcs_across_staves(_arc_result([upper, lower])) == 0
        assert _arc_classes(upper) == ["slur"]
        assert _arc_classes(lower) == []

    def test_a_rival_that_is_near_but_not_nearer_does_not_win(self):
        """Both staves' heads sit close to the arc. Ownership needs a decisive
        margin, not a photo finish — otherwise a divisi pair would trade arcs
        on rounding."""
        upper = _arc_staff(100, 145, arcs=[(10, 160, 90, 168)])
        lower = _arc_staff(300, 175)
        assert arbitrate_arcs_across_staves(_arc_result([upper, lower])) == 0
        assert _arc_classes(upper) == ["slur"]

    def test_a_one_staff_system_is_never_arbitrated(self):
        upper = _arc_staff(100, 120, arcs=[(10, 185, 90, 195)])
        assert arbitrate_arcs_across_staves(_arc_result([upper])) == 0
        assert _arc_classes(upper) == ["slur"]

    def test_the_flag_off_is_a_no_op(self, monkeypatch):
        monkeypatch.setenv("OMR_ARC_ATTRIBUTION", "off")
        upper, lower = self._bled()
        assert arbitrate_arcs_across_staves(_arc_result([upper, lower])) == 0
        assert _arc_classes(upper) == ["slur"]

    def test_drop_mode_removes_without_regifting(self, monkeypatch):
        monkeypatch.setenv("OMR_ARC_ATTRIBUTION", "drop")
        upper, lower = self._bled()
        assert arbitrate_arcs_across_staves(_arc_result([upper, lower])) == 1
        assert _arc_classes(upper) == []
        assert _arc_classes(lower) == []

    def test_it_is_idempotent(self):
        """Exporting a result twice must not shuttle an arc back and forth: the
        moved arc's new staff is the one that hugs it, so the pass is a fixed
        point, and the stamp makes that cheap as well as true."""
        upper, lower = self._bled()
        result = _arc_result([upper, lower])
        assert arbitrate_arcs_across_staves(result) == 1
        assert arbitrate_arcs_across_staves(result) == 0
        assert _arc_classes(upper) == []
        assert _arc_classes(lower) == ["slur"]

    def test_the_moved_arc_becomes_the_new_staff_s_slur(self):
        """End to end: the arc pairs on the staff it moved to, and on nothing
        else. Pairing is what the move is FOR."""
        upper, lower = self._bled()
        arbitrate_arcs_across_staves(_arc_result([upper, lower]))
        assert annotate_slurs_in_staff(upper) == 0
        assert annotate_slurs_in_staff(lower) == 1

    def test_an_arc_over_a_lone_rival_notehead_is_not_claimed(self):
        """A rival must cover at least two of its own heads: one stray head
        under a long arc is not a run being bound."""
        upper = _arc_staff(100, 120, arcs=[(10, 185, 90, 195)])
        lower = _arc_staff(300, 200)
        for m in lower["measures"]:
            m["detections"] = [d for d in m["detections"]
                               if d["bbox_page"][0] >= 70]
        assert arbitrate_arcs_across_staves(_arc_result([upper, lower])) == 0
        assert _arc_classes(upper) == ["slur"]
