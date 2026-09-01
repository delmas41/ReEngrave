"""Unit tests for tools/omr/export.py — Phase 4d serializers.

Tests the pure helpers (pitch parsing, key sig mapping, duration table)
and structural correctness of small synthetic JSON inputs.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from tools.omr.export import (
    annotate_beams,
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

    def test_dotted_prefix_with_extra_dots(self):
        # Both the prefix dot AND the explicit dot count should accumulate.
        lily, xml, dots = _duration_to_lily_xml("dotted_quarter", 1)
        assert dots == 2  # 1 from prefix + 1 from arg


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
