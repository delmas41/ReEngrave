"""Guards for the condensed-staff part split.

⚠️ THE SCAN BENCHMARK IS THE ONLY CORPUS THAT CAN SEE THIS, AND IT IS NOT RUN
BY THE SUITE. Every engraved fixture is a single system with one part per
staff, so that benchmark is structurally blind to this change — proven
byte-identical, 11/11, by `probe_flag_off_identity.py`. These tests stand in
its place, the same arrangement `test_export_slot_stitching.py` documents.
"""
from __future__ import annotations

import os

import pytest

from tools.omr.condensed_parts import players_for_label
from tools.omr.export import to_musicxml


# ── the label reader ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("label,expected", [
    # A printed enumeration names the players on THIS staff.
    ("Corni I.II. in E", 2),
    ("Tromboni I.II.", 2),
    ("Fag. 1/2", 2),
    # ⚠️ The regression this was written for: `4` is the SECTION and `1./2.` is
    # the staff. A single-character separator class does not match `./`, and
    # the leading numeral then wins — reading Brahms's horn staff as four.
    ("4 Horner in C 1./2.", 2),
    ("4 Hörner in Es 3./4.", 2),
    # Two instrument nouns on one staff.
    ("Violoncello e Basso", 2),
    # A leading count, where nothing narrows it.
    ("2 Flöten", 2),
    ("Vier Flöten", 4),
    ("Drei Hoboen", 3),
    # Bare plurals.
    ("Flauti", 2),
    ("Trombe in C", 2),
    # Singulars and solo desks stay at one.
    ("Flauto", 1),
    ("Violino I", 1),
    ("1. Violine", 1),
    ("Kontrafagott", 1),
    ("Trombone basso", 1),
    ("Viola", 1),
    # `Timpani` is plural in form and one player by convention — it is
    # deliberately absent from the section lexicon.
    ("Timpani in C.G.", 1),
    # `u.G` is a key name, not a second instrument: the compound tier needs
    # three letters on both sides.
    ("Pauken in C u.G", 1),
])
def test_players_for_label(label, expected):
    assert players_for_label(label) == expected


def test_no_label_abstains():
    assert players_for_label(None) == 1
    assert players_for_label("") == 1
    assert players_for_label("   ") == 1


def test_tiers_can_be_restricted():
    # The plural tier is the one the Dvořák control falsifies; an arm must be
    # able to price the rule without it.
    assert players_for_label("Flauti") == 2
    assert players_for_label("Flauti", tiers=("explicit", "compound")) == 1
    # An enumeration survives the restriction, because it is printed evidence.
    assert players_for_label("Corni I.II.", tiers=("explicit",)) == 2


# ── the exporter ─────────────────────────────────────────────────────────────

def _page(staves):
    return {"pages": [{"page_index": 0, "systems": [
        {"system_index": 0, "staves": staves}]}]}


def _staff(idx, **kw):
    s = {
        "staff_index": idx, "clef": "treble", "slot_index": idx,
        "key_signature": {"sharps": 0, "flats": 0, "alterations": {}},
        "time_signature": {"beats": 4, "beat_type": 4},
        "measures": [{"measure_index": 0, "events": [], "detections": []}],
    }
    s.update(kw)
    return s


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("OMR_CONDENSED_PARTS", raising=False)
    monkeypatch.setenv("OMR_SLOT_STITCH", "0")


def test_flag_off_is_one_part_per_staff():
    result = _page([_staff(0, instrument="Flute", condensed_parts=2),
                    _staff(1, instrument="Viola")])
    assert to_musicxml(result).count("<score-part ") == 2


def test_flag_on_splits_only_where_the_count_says_so(monkeypatch):
    monkeypatch.setenv("OMR_CONDENSED_PARTS", "1")
    result = _page([_staff(0, instrument="Flute", condensed_parts=2),
                    _staff(1, instrument="Viola")])
    xml = to_musicxml(result)
    assert xml.count("<score-part ") == 3
    assert "<part-name>Flute 1</part-name>" in xml
    assert "<part-name>Flute 2</part-name>" in xml
    assert "<part-name>Viola</part-name>" in xml


def test_a_page_with_no_evidence_is_byte_identical(monkeypatch):
    """Abstention is the fallback — proven, not asserted in prose."""
    result = _page([_staff(0, instrument="Flute"), _staff(1, instrument="Viola")])
    off = to_musicxml(result)
    monkeypatch.setenv("OMR_CONDENSED_PARTS", "1")
    assert to_musicxml(result) == off


def test_each_player_gets_its_own_attributes(monkeypatch):
    """⚠️ `_staff_measures_xml` MUTATES the state dict it is given (running
    clef, key, meter). Sharing one across the players of a slot suppresses the
    attributes on every player after the first, so each takes a fresh dict."""
    monkeypatch.setenv("OMR_CONDENSED_PARTS", "1")
    result = _page([_staff(0, instrument="Flute", condensed_parts=2)])
    xml = to_musicxml(result)
    assert xml.count("<clef>") == 2
    assert xml.count("<key>") == 2


def test_disagreeing_systems_abstain(monkeypatch):
    """A slot whose systems disagree about how many players it holds is a
    contradiction, not evidence."""
    monkeypatch.setenv("OMR_CONDENSED_PARTS", "1")
    result = {"pages": [{"page_index": 0, "systems": [
        {"system_index": 0, "staves": [_staff(0, instrument="Flute",
                                              condensed_parts=2)]},
        {"system_index": 1, "staves": [_staff(0, instrument="Flute",
                                              condensed_parts=3)]},
    ]}]}
    assert to_musicxml(result).count("<score-part ") == 1


def test_fragments_are_not_split_by_default(monkeypatch):
    """⚠️ Where the ordinal join refuses, a part is already one fragment per
    system; splitting each fragment multiplies the fragmentation. Measured on
    Brahms 1 p.2: 27 fragments become 41 against a truth of 21, +904 edits.
    `all` is the opt-in that reproduces that finding."""
    monkeypatch.setenv("OMR_CONDENSED_PARTS", "1")
    result = {"pages": [{"page_index": 0, "systems": [
        {"system_index": 0, "staves": [_staff(0, instrument="Flute",
                                              condensed_parts=2),
                                       _staff(1, instrument="Viola")]},
        {"system_index": 1, "staves": [_staff(0, instrument="Flute",
                                              condensed_parts=2)]},
    ]}]}
    # Systems disagree on staff count, so `_stitch_slots` refuses and the
    # per-system path runs: 3 fragments, none split.
    assert to_musicxml(result).count("<score-part ") == 3
    monkeypatch.setenv("OMR_CONDENSED_PARTS", "all")
    assert to_musicxml(result).count("<score-part ") == 5
