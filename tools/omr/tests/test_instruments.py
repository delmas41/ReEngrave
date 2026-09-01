"""Instrument lexicon (tools/omr/instruments.py)."""
from __future__ import annotations

import pytest

from tools.omr.instruments import (
    candidates_for_alias,
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


def test_tp_is_timpani_not_trumpet():
    """Measured on Beethoven 1 (imslp-00074 p40), whose system reads
    Fl / Ob / Cl / Fag / Cor / Tr / Tp — "Tr." is trumpets and the "Tp." below
    it is timpani. The vision reader transcribed it correctly; the lexicon was
    what got it wrong."""
    assert lookup("Tp.").instrument.name == "Timpani"
    assert lookup("Tr.").instrument.name == "Trumpet"
    assert lookup("Tpt.").instrument.name == "Trumpet"


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


# ─── measured against real part lists ───────────────────────────────────────
#
# Every case below is a name the Gradus MusicXML library actually contains,
# found by scoring the lexicon against 2,345 part names from 111 orchestral
# works (`benchmarks/omr-score-order-2026-08/`). They are here rather than in
# that benchmark because the benchmark needs the library on disk and these do
# not.


def test_tenor_tuba_is_a_tuba_not_a_voice():
    """The alias index is longest-first, so "tenor" (5) beat "tuba" (4) and
    Holst's tenor tuba read as a TENOR VOICE — which took all eight movements
    of The Planets out of score order, a voice appearing among the brass."""
    assert lookup("Tenor Tuba in B♭").instrument.name == "Tuba"
    assert lookup("Tenor Trombone 1").instrument.name == "Trombone"
    assert lookup("Tenor").instrument.name == "Tenor"


def test_plural_and_german_part_names_resolve():
    for label, expected in (
        ("Violoncellos", "Cello"),
        ("Contrabasses", "Contrabass"),
        ("Violen", "Viola"),
        ("Drei Hoboen", "Oboe"),
        ("Contrafagotte", "Contrabassoon"),
        ("Kontrabaß", "Contrabass"),
        ("Violone", "Contrabass"),
    ):
        match = lookup(label)
        assert match is not None, f"{label} unread"
        assert match.instrument.name == expected, label


def test_the_percussion_battery_resolves():
    for label in ("Cymbal", "Tambourine", "Glockenspiel", "Xylophone",
                  "Tubular Bells", "Tam-tam", "Snare Drum"):
        match = lookup(label)
        assert match is not None, f"{label} unread"
        assert match.instrument.family == "percussion", label


def test_basso_is_ambiguous_rather_than_decided():
    """"Basso" is the contrabass at the foot of the strings and the bass voice
    under a vocal stave, and the word is identical — so the lexicon must OFFER
    both and let `score_layouts.resolve_ambiguous_label` settle it from where
    the staff sits. Deciding it here is what put Mozart 41 and Mahler 5 out of
    score order, a voice appearing below the cellos."""
    for alias in ("basso", "basse", "bass"):
        names = [i.name for i in candidates_for_alias(alias)]
        assert "Contrabass" in names and "Bass voice" in names, alias
    # the first entry stays the lexicon's own answer, so nothing moves when the
    # score-order prior has no opinion
    assert lookup("Basso").instrument.name == "Bass voice"


def test_a_longer_alias_still_wins_over_bare_bass():
    for label, expected in (("Bass Clarinet", "Bass clarinet"),
                            ("Bass Trombone", "Trombone"),
                            ("Bass Drum", "Percussion")):
        assert lookup(label).instrument.name == expected, label


def test_a_voice_word_does_not_beat_an_instrument_noun():
    """"Bb (basso) Horn 4" names a horn. It resolved to a bass VOICE, because
    the alias index is longest-first and "basso" is longer than "horn" — right
    for "Bass Clarinet" beating "Bass", wrong here, where the longer alias is
    the qualifier and not the noun. 31 part names across Beethoven 4 and 9."""
    for label in ("Bb (basso) Horn 4", "B basso Horn 2", "Basso Horn"):
        assert lookup(label).instrument.name == "Horn", label
    assert lookup("Bass Sarrusophone").instrument.name == "Sarrusophone"


def test_a_voice_word_alone_is_still_a_voice():
    """The other half, and the one a fix here can easily break: a chorale's
    "Bass" is a bass. The rule only fires when the label names something else
    on a DIFFERENT word — "Basso" matches `basso` for both the voice and the
    contrabass, one word and two readings, which is genuine ambiguity and stays
    with AMBIGUOUS_ALIASES."""
    for label, expected in (("Bass", "Bass voice"), ("Basso", "Bass voice"),
                            ("Bass solo", "Bass voice"), ("Alto", "Alto"),
                            ("Tenor", "Tenor"), ("Soprano", "Soprano")):
        assert lookup(label).instrument.name == expected, label


def test_size_qualified_instruments_are_unaffected():
    for label, expected in (("Bass Clarinet", "Bass clarinet"),
                            ("Alto Flute", "Flute"),
                            ("Tenor Trombone 1", "Trombone"),
                            ("Bass Drums", "Percussion")):
        assert lookup(label).instrument.name == expected, label


def test_tr_plus_a_register_is_a_trombone_not_a_voice_and_not_a_trumpet():
    """`Tr.` is Trombe AND Tromboni, and Beethoven 5 (IMSLP984073) p.47 prints
    both: `Tr.` over the trumpets and `Tr. Alt. / Tr. Ten. / Tr. Bas.` over the
    three trombones four staves below. Before this, the first two resolved to
    singers at HIGH confidence (`alt` and `ten` beat `tr` on length) and the
    third to a second Trumpet.

    The same convention is in the text layer of a different edition
    (imslp-575951 p.59), which is what makes it a printing convention rather
    than one scan's quirk."""
    for label in ("Tr. Alt.", "Tr. Ten.", "Tr. Bas.",
                  "Tr. Alto", "Tr. Tenore", "Tr. Basso",
                  "Tr. Ten", "Tr. Bas", "Tr Alt", "Tr. Bass.",
                  "Tr. Alt. I", "Tr. Alt. e Ten."):
        m = lookup(label)
        assert m is not None, label
        assert m.instrument.name == "Trombone", f"{label!r} -> {m.instrument.name}"


def test_a_bare_tr_is_still_the_trumpets():
    """The other half, and the one this fix could easily have broken: only a
    REGISTER qualifier moves `Tr.` to the trombones. A trumpet section is scored
    by number and key, and those readings must not move."""
    for label in ("Tr.", "Tr", "Tr. I", "Tr. II", "Trombe in C", "Tr. Es"):
        assert lookup(label).instrument.name == "Trumpet", label


def test_tr_b_is_a_trumpet_in_b_flat_not_a_bass_trombone():
    """Deliberately NOT an alias: "Tr. B." is a trumpet in B-flat far more often
    than a bass trombone — the same trap as "Cl. B." — so the register aliases
    stop at the spelled-out `bas` / `bass` / `basso`."""
    assert lookup("Tr. B.").instrument.name == "Trumpet"
    assert lookup("Tr. B").instrument.name == "Trumpet"


def test_a_bass_trumpet_keeps_its_own_noun():
    """"Tromba bassa" carries the trumpet noun, so it never reaches the `tr …`
    register aliases and stays a trumpet."""
    assert lookup("Tromba bassa").instrument.name == "Trumpet"


def test_abbreviated_register_words_do_not_beat_an_instrument_noun():
    """`_prefer_instrument_over_voice` was reachable only from the SPELLED-OUT
    register words, so an abbreviated `Alt.` / `Ten.` put a flute and a clarinet
    among the singers at high confidence."""
    for label, expected in (("Fl. Alt.", "Flute"),
                            ("Cl. Alt.", "Clarinet"),
                            ("Sax. Ten.", "Saxophone"),
                            ("Trb. Alt.", "Trombone"),
                            ("Trb. Tenore", "Trombone"),
                            ("Tbn. Basso", "Trombone"),
                            ("Pos. Alt.", "Trombone")):
        m = lookup(label)
        assert m is not None, label
        assert m.instrument.name == expected, f"{label!r} -> {m.instrument.name}"


def test_an_abbreviated_voice_alone_is_still_a_voice():
    """The half a wider qualifier set can break: a chorale's `Alt.` is an alto.
    The rule only fires when the label names something else on a DIFFERENT
    word."""
    for label, expected in (("Alt.", "Alto"), ("Ten.", "Tenor"),
                            ("Sopr.", "Soprano"), ("Tenore", "Tenor"),
                            ("Contralto", "Alto")):
        assert lookup(label).instrument.name == expected, label


def test_voice_qualifiers_are_derived_so_no_spelling_is_left_out():
    """The hand-listed set WAS the bug: it held `alto` and `tenor` and not the
    `alt` and `ten` real scores print. Deriving it from the voice aliases means
    a new register spelling cannot be added to one and forgotten in the other.

    `Chorus` is excluded — "Coro" names an ensemble, never a register."""
    from tools.omr.instruments import VOICE_QUALIFIERS

    for inst in INSTRUMENTS:
        if inst.family != "voice":
            continue
        for alias in inst.aliases:
            if inst.name == "Chorus":
                assert alias not in VOICE_QUALIFIERS, alias
            else:
                assert alias in VOICE_QUALIFIERS, alias
    assert {"alt", "ten", "sopr", "tenore"} <= VOICE_QUALIFIERS
    assert lookup("Coro").instrument.name == "Chorus"
