"""A part is the same staff on every system, not one staff on one system."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from tools.omr.export import _stitch_slots, to_musicxml


def _measure(index, *, clef="treble", key=None, time=None, pitch="C4"):
    return {
        "measure_index": index,
        "bbox_page_px": [0, 0, 100, 50],
        "clef": clef,
        "key_signature": key or {"sharps": 0, "flats": 0, "alterations": {}},
        "time_signature": time or {"numerator": 4, "denominator": 4, "raw": "4/4"},
        "n_detections": 1,
        "detections": [{
            "class": "noteheadBlackOnLine", "category": "notehead",
            "bbox": [10, 10, 5, 5], "bbox_page": [10, 10, 5, 5],
            "confidence": 0.9, "pitch": pitch, "duration_beats": 1.0,
            "duration_type": "quarter", "dots": 0,
        }],
    }


def _staff(index, n_measures, *, clef="treble"):
    return {
        "staff_index": index, "clef": clef,
        "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
        "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
        "n_measures": n_measures,
        "measures": [_measure(i, clef=clef) for i in range(n_measures)],
    }


def _result(systems, *, page_index=0):
    return {
        "source_pdf": "synthetic.pdf",
        "pages": [{
            "page_index": page_index,
            "n_systems": len(systems),
            "systems": [
                {"system_index": i, "n_staves": len(staves), "staves": staves}
                for i, staves in enumerate(systems)
            ],
        }],
    }


def _root(xml: str) -> ET.Element:
    body = xml.split("?>", 1)[1].split("<!DOCTYPE", 1)[0] + \
        xml.split("partwise.dtd\">", 1)[1]
    return ET.fromstring(body)


def _parts(xml: str):
    return _root(xml).findall("part")


TWO_SYSTEMS = [
    [_staff(0, 3), _staff(1, 3, clef="bass")],
    [_staff(2, 2), _staff(3, 2, clef="bass")],
]


class TestStitches:
    def test_two_systems_become_two_parts(self):
        parts = _parts(to_musicxml(_result(TWO_SYSTEMS)))
        assert len(parts) == 2, "one part per staff of the system, not per system"

    def test_a_part_holds_every_system_s_measures(self):
        parts = _parts(to_musicxml(_result(TWO_SYSTEMS)))
        assert [len(p.findall("measure")) for p in parts] == [5, 5]

    def test_measure_numbers_run_on_through_the_piece(self):
        parts = _parts(to_musicxml(_result(TWO_SYSTEMS)))
        numbers = [m.get("number") for m in parts[0].findall("measure")]
        assert numbers == ["1", "2", "3", "4", "5"]

    def test_across_pages_too(self):
        result = _result(TWO_SYSTEMS)
        second = _result(TWO_SYSTEMS, page_index=1)
        result["pages"].append(second["pages"][0])
        parts = _parts(to_musicxml(result))
        assert len(parts) == 2
        assert [len(p.findall("measure")) for p in parts] == [10, 10]

    def test_attributes_are_not_restated_at_a_system_boundary(self):
        # The whole point of carrying the state across systems: an attribute is
        # written where it CHANGES. Restating the clef every few bars is what a
        # per-system part model produced.
        parts = _parts(to_musicxml(_result(TWO_SYSTEMS)))
        with_attrs = [m for m in parts[0].findall("measure")
                      if m.find("attributes") is not None]
        assert len(with_attrs) == 1
        assert with_attrs[0].get("number") == "1"

    def test_a_piano_pair_is_braced_once(self):
        xml = to_musicxml(_result(TWO_SYSTEMS))
        assert xml.count("<group-symbol>brace</group-symbol>") == 1


class TestAbstains:
    def test_systems_of_different_heights_are_not_joined(self):
        # A printed orchestral score suppresses tacet staves, so its systems
        # genuinely differ — Beethoven 5 scan p.3 is 11 staves then 8. Joining
        # by position there would graft one instrument's music onto another.
        systems = [
            [_staff(0, 2), _staff(1, 2), _staff(2, 2)],
            [_staff(3, 2), _staff(4, 2)],
        ]
        assert _stitch_slots(_result(systems)) is None
        assert len(_parts(to_musicxml(_result(systems)))) == 5

    def test_a_fragmented_row_is_not_joined(self):
        systems = [[_staff(i, 1) for i in range(4)],
                   [_staff(i, 1) for i in range(4, 8)]]
        assert _stitch_slots(_result(systems)) is None

    def test_no_systems_at_all(self):
        assert _stitch_slots({"pages": []}) is None


class TestUnchangedForOneSystem:
    def test_single_system_still_one_part_per_staff(self):
        parts = _parts(to_musicxml(_result([[_staff(0, 3), _staff(1, 3)]])))
        assert len(parts) == 2
        assert [len(p.findall("measure")) for p in parts] == [3, 3]
