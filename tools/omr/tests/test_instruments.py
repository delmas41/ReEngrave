"""Instrument lexicon (tools/omr/instruments.py)."""
from __future__ import annotations

import pytest

from tools.omr.instruments import (
    INSTRUMENTS,
    lookup,
    normalize_label,
    parse_in_key,
    takes_key,
)


@pytest.mark.parametrize("label,expected", [
    # Italian / German / French / English spellings of the same instruments.
    ("Fl.", "Flute"), ("2 Flauti", "Flute"), ("Flöten 1. 2.", "Flute"),
    ("Ob.", "Oboe"), ("Hautbois", "Oboe"), ("Oboen", "Oboe"),
    ("Cl.", "Clarinet"), ("Klarinetten", "Clarinet"), ("Clarinettes", "Clarinet"),
    ("Fag.", "Bassoon"), ("Fg.", "Bassoon"), ("Bassons", "Bassoon"),
    ("Cor.", "Horn"), ("Corni", "Horn"), ("Hörner", "Horn"),
    ("Tr.", "Trumpet"), ("Trombe", "Trumpet"), ("Trompeten", "Trumpet"),
    ("Posaunen", "Trombone"), ("Tromboni", "Trombone"),
    ("Timp.", "Timpani"), ("Pauken", "Timpani"),
    ("Vl. I", "Violin"), ("Violino I", "Violin"), ("Violinen", "Violin"),
    ("Vla.", "Viola"), ("Bratschen", "Viola"),
    ("Vc.", "Cello"), ("Violoncello", "Cello"),
    ("Cb.", "Contrabass"), ("Kontrabässe", "Contrabass"),
    ("Arpa", "Harp"), ("Corno inglese", "English horn"),
])
def test_standard_abbreviations_resolve(label, expected):
    m = lookup(label)
    assert m is not None, f"{label!r} did not match"
    assert m.instrument.name == expected


def test_family_and_default_clef_come_along():
    assert lookup("Vla.").instrument.default_clef == "alto"
    assert lookup("Fag.").instrument.default_clef == "bass"
    assert lookup("Fl.").instrument.family == "woodwind"
    assert lookup("Cor.").instrument.family == "brass"
    assert lookup("Vc.").instrument.family == "string"


# ── transposition ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("label,fifths", [
    ("2 Clarinetti in B", 2),      # German/Italian "B" = B-flat -> +2
    ("Klarinetten in A", -3),
    ("2 Corni in C", 0),
    ("Corni in Es", 3),
    ("2 Trombe in C", 0),
    ("Timpani in C.G", 0),
])
def test_explicit_in_key_sets_the_offset(label, fifths):
    assert lookup(label).fifths_offset == fifths


@pytest.mark.parametrize("label,fifths", [
    ("Cor. D.", -2),   # horn in D: written key = concert - 2 fifths
    ("Cor. B.", 2),
    ("Tr. Es", 3),
    ("Cor. (Es)", 3),
])
def test_bare_trailing_key_is_read_for_transposing_instruments(label, fifths):
    assert lookup(label).fifths_offset == fifths


def test_bare_key_is_not_read_for_non_transposing_instruments():
    """'Vl. I' must not read the part number as a key."""
    m = lookup("Vl. I")
    assert m.instrument.name == "Violin"
    assert m.fifths_offset == 0
    assert not takes_key(m.instrument)


def test_offset_identity_is_minus_fifths_of_the_named_key():
    # written key = concert key + offset, so offset = -fifths(key)
    assert parse_in_key("in G") == -1     # key of G is +1 fifth
    assert parse_in_key("in F") == 1      # key of F is -1 fifth
    assert parse_in_key("in Es") == 3     # key of E-flat is -3 fifths
    assert parse_in_key("Fl.") is None


def test_default_offset_when_no_key_is_printed():
    assert lookup("Cor.").fifths_offset == 1     # horn in F is the default
    assert lookup("Fl.").fifths_offset == 0


# ── guarding against wrong matches ──────────────────────────────────────────

def test_no_single_letter_aliases():
    """A one-character alias matches OCR noise; 'V}a.' (a garbled 'Vla.') used
    to resolve to Violin through a bare 'v'."""
    for inst in INSTRUMENTS:
        for alias in inst.aliases:
            assert len(alias) >= 2, f"{inst.name} has one-character alias {alias!r}"
    assert lookup("V}a.") is None


def test_cl_b_is_a_clarinet_in_b_flat_not_a_bass_clarinet():
    assert lookup("Cl. B").instrument.name == "Clarinet"
    assert lookup("B. Cl.").instrument.name == "Bass clarinet"
    assert lookup("Bassklarinette").instrument.name == "Bass clarinet"


def test_longest_alias_wins():
    assert lookup("Corno inglese").instrument.name == "English horn"
    assert lookup("Coro").instrument.name == "Chorus"      # not Horn via "cor"


def test_pure_noise_does_not_match():
    for junk in (",/\"", ")", "/A", ".", "t)", ""):
        assert lookup(junk) is None, f"{junk!r} should not match"


# ── confidence ──────────────────────────────────────────────────────────────

def test_clean_short_abbreviations_are_high_confidence():
    """Alias length is not the risk — Fl./Ob./Vc. are the standard forms."""
    for label in ("Fl.", "Ob.", "Vc.", "Vl. I", "Cl. B"):
        assert lookup(label).confidence == "high", label


def test_ocr_folded_matches_are_low_confidence():
    m = lookup(". Tlmp -")            # OCR 'l' for 'i'
    assert m.instrument.name == "Timpani"
    assert m.ocr_folded and m.confidence == "low"


def test_alias_buried_in_garbage_is_demoted():
    m = lookup("vc. '- eB-")
    assert m.instrument.name == "Cello"
    assert m.coverage < 0.6 and m.confidence == "medium"


def test_space_collapsed_probe_recovers_split_spans():
    """OCR splits one printed word across spans: 'Timp.' arrives as 'Tim p.'."""
    m = lookup("Tim p.")
    assert m.instrument.name == "Timpani"
    assert not m.ocr_folded


# ── misc ────────────────────────────────────────────────────────────────────

def test_normalize_label_strips_accents_and_punctuation():
    assert normalize_label("Flöten 1. 2.") == "floten 1 2"
    assert normalize_label("  Vl.   I  ") == "vl i"


def test_percussion_is_flagged_unpitched():
    m = lookup("Gran Cassa")
    assert m.instrument.unpitched
    assert not lookup("Timp.").instrument.unpitched   # timpani are pitched


def test_written_ranges_are_ordered_and_sane():
    for inst in INSTRUMENTS:
        lo, hi = inst.written_range
        assert 0 <= lo < hi <= 127, inst.name
