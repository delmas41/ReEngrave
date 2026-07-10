"""Tests for musicxml_builder — clef sign/line resolution.

Covers the fix for invalid MusicXML clef signs: `s.get("clef", "G")[0].upper()`
used to turn Claude Vision's "treble"/"alto"/"tenor" clef names into invalid
<sign> values ('T', 'A') by grabbing the first letter of the English name
instead of mapping to the MusicXML sign/line vocabulary.
"""

from xml.etree import ElementTree as ET

import pytest

from modules.musicxml_builder import (
    CLEF_NAME_TO_SIGN_LINE,
    MeasureData,
    PageAnalysis,
    StaffMeasure,
    _resolve_clef,
    build_musicxml,
    parse_header_json,
)


def _one_empty_measure(staff_id: int = 1) -> list[PageAnalysis]:
    """A single bar-1 measure with no notes — enough to make build_musicxml
    emit the <attributes>/<clef> block for the first measure.
    """
    measure = MeasureData(number=1, staves=[StaffMeasure(staff_id=staff_id, voices=[])])
    return [PageAnalysis(page_number=1, measures=[measure])]


# ---------------------------------------------------------------------------
# _resolve_clef (pure function)
# ---------------------------------------------------------------------------


class TestResolveClef:
    @pytest.mark.parametrize(
        "clef_name,expected",
        [
            ("treble", ("G", 2)),
            ("bass", ("F", 4)),
            ("alto", ("C", 3)),
            ("tenor", ("C", 4)),
            ("Treble", ("G", 2)),   # case-insensitive
            ("BASS", ("F", 4)),
            (" alto ", ("C", 3)),   # tolerate whitespace
        ],
    )
    def test_known_clef_names_resolve_correctly(self, clef_name, expected):
        assert _resolve_clef(clef_name) == expected

    def test_bare_sign_letters_also_resolve(self):
        assert _resolve_clef("G") == ("G", 2)
        assert _resolve_clef("F") == ("F", 4)
        assert _resolve_clef("C") == ("C", 3)

    def test_unknown_clef_falls_back_to_treble(self):
        assert _resolve_clef("percussion") == ("G", 2)
        assert _resolve_clef("nonsense") == ("G", 2)

    def test_missing_clef_falls_back_to_treble(self):
        assert _resolve_clef(None) == ("G", 2)
        assert _resolve_clef("") == ("G", 2)

    def test_never_emits_invalid_sign_letters(self):
        # The bug: [0].upper() on "treble"/"alto"/"tenor" produced 'T'/'A',
        # neither of which is a valid MusicXML <sign> value.
        valid_signs = {"G", "F", "C"}
        for clef_name in ["treble", "bass", "alto", "tenor"]:
            sign, _line = _resolve_clef(clef_name)
            assert sign in valid_signs


# ---------------------------------------------------------------------------
# parse_header_json — end-to-end from Claude Vision's JSON shape
# ---------------------------------------------------------------------------


class TestParseHeaderJson:
    def test_alto_clef_maps_to_c_line_3(self):
        header = parse_header_json({
            "title": "Viola Solo",
            "composer": "Anon",
            "staves": [{"staff_id": 1, "instrument_name": "Viola", "clef": "alto"}],
        })
        staff = header.staves[0]
        assert staff.clef_sign == "C"
        assert staff.clef_line == 3

    def test_tenor_clef_maps_to_c_line_4(self):
        header = parse_header_json({
            "title": "T",
            "composer": "C",
            "staves": [{"staff_id": 1, "instrument_name": "Cello", "clef": "tenor"}],
        })
        staff = header.staves[0]
        assert staff.clef_sign == "C"
        assert staff.clef_line == 4

    def test_bass_clef_maps_to_f_line_4(self):
        header = parse_header_json({
            "title": "T",
            "composer": "C",
            "staves": [{"staff_id": 1, "instrument_name": "Cello", "clef": "bass"}],
        })
        staff = header.staves[0]
        assert staff.clef_sign == "F"
        assert staff.clef_line == 4

    def test_treble_clef_maps_to_g_line_2(self):
        header = parse_header_json({
            "title": "T",
            "composer": "C",
            "staves": [{"staff_id": 1, "instrument_name": "Violin", "clef": "treble"}],
        })
        staff = header.staves[0]
        assert staff.clef_sign == "G"
        assert staff.clef_line == 2

    def test_missing_clef_key_falls_back_to_treble(self):
        header = parse_header_json({
            "title": "T",
            "composer": "C",
            "staves": [{"staff_id": 1, "instrument_name": "Piano"}],
        })
        staff = header.staves[0]
        assert staff.clef_sign == "G"
        assert staff.clef_line == 2


# ---------------------------------------------------------------------------
# End-to-end: build_musicxml must emit valid <sign>/<line> elements
# ---------------------------------------------------------------------------


class TestBuildMusicxmlClefOutput:
    def test_alto_clef_emits_valid_xml_clef_elements(self):
        header = parse_header_json({
            "title": "Viola Solo",
            "composer": "Anon",
            "staves": [{"staff_id": 1, "instrument_name": "Viola", "clef": "alto"}],
        })
        xml_str = build_musicxml(header, pages=_one_empty_measure())

        root = ET.fromstring(xml_str)
        clef_el = root.find(".//clef")
        assert clef_el is not None
        sign = clef_el.find("sign").text
        line = clef_el.find("line").text
        assert sign == "C"
        assert line == "3"
        # The old bug would have emitted <sign>A</sign> here — assert it's gone.
        assert sign != "A"

    def test_tenor_clef_emits_valid_xml_clef_elements(self):
        header = parse_header_json({
            "title": "T",
            "composer": "C",
            "staves": [{"staff_id": 1, "instrument_name": "Cello", "clef": "tenor"}],
        })
        xml_str = build_musicxml(header, pages=_one_empty_measure())

        root = ET.fromstring(xml_str)
        clef_el = root.find(".//clef")
        sign = clef_el.find("sign").text
        line = clef_el.find("line").text
        assert sign == "C"
        assert line == "4"
        # The old bug would have emitted <sign>T</sign> here — assert it's gone.
        assert sign != "T"


# ---------------------------------------------------------------------------
# CLEF_NAME_TO_SIGN_LINE table sanity
# ---------------------------------------------------------------------------


class TestClefTable:
    def test_all_values_are_valid_musicxml_signs(self):
        for name, (sign, line) in CLEF_NAME_TO_SIGN_LINE.items():
            assert sign in {"G", "F", "C"}, f"{name} -> invalid sign {sign!r}"
            assert isinstance(line, int)
