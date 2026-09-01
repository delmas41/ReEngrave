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
    annotate_slurs_in_staff,
    measure_dynamics,
    _compute_divisions,
    _direction_slots,
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


def _slur_head(x, pitch="C4", width=10):
    """One pitched notehead at page-x `x`."""
    return {"category": "notehead", "class": "noteheadBlack", "pitch": pitch,
            "duration_type": "quarter", "duration_beats": 1.0, "dots": 0,
            "bbox": [x, 40, width, 10], "bbox_page": [x, 40, width, 10],
            "confidence": 0.9}


def _slur_arc(x0, x1, y=20):
    return {"category": "structural", "class": "slur",
            "bbox": [x0, y, x1 - x0, 8], "bbox_page": [x0, y, x1 - x0, 8]}


def _slur_staff(measures, spacing=10.0):
    """A staff whose cells tile [0,100), [100,200), … so a barline is a
    cell edge, which is what makes an arc's clipping visible."""
    return {
        "staff_index": 0,
        "clef": "treble",
        "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
        "time_signature": {"numerator": 4, "denominator": 4},
        "staff_geometry": {"line_ys_page": [40, 50, 60, 70, 80],
                           "line_spacing_px": spacing,
                           "x_start": 0, "x_end": 100 * len(measures)},
        "n_measures": len(measures),
        "measures": [{
            "measure_index": i,
            "bbox_page_px": [i * 100, 0, (i + 1) * 100, 90],
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
