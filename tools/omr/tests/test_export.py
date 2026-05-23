"""Unit tests for tools/omr/export.py — Phase 4d serializers.

Tests the pure helpers (pitch parsing, key sig mapping, duration table)
and structural correctness of small synthetic JSON inputs.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from tools.omr.export import (
    _DURATION_TABLE,
    _duration_to_lily_xml,
    _LILY_ACCIDENTAL,
    _lily_event,
    _lily_key_for_sig,
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
