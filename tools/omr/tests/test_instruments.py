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


def test_v_read_as_y_folds_to_the_string_it_is():
    """A printed "Violino II." OCR'd as "Yiolino II." — a V read as Y, surfaced
    2026-09-02 in a labelling batch. `y` folds to `v` the way the i/l/1 stroke
    group folds to `i`: rare enough in the vocabulary to be collision-free, and
    the whole V->Y family comes with it."""
    for label, expected in (("Yiolino II.", "Violin"), ("Yiola", "Viola"),
                            ("Yioloncello", "Cello"), ("Yni", "Violin")):
        m = lookup(label)
        assert m is not None, f"{label!r} did not match"
        assert m.instrument.name == expected, f"{label!r} -> {m.instrument.name}"
        # a match that needed the fold is a guess, so it is demoted like any other
        assert m.ocr_folded and m.confidence == "low", label


def test_the_two_y_instruments_resolve_before_the_fold_runs():
    """Folding y->v is safe only because `tympani` and `xylophone` — the sole
    aliases carrying a `y` — resolve on the EXACT pass, before the fold is ever
    reached. So they keep their high confidence and are never folded."""
    for label, expected in (("Tympani", "Timpani"), ("Xylophone", "Percussion")):
        m = lookup(label)
        assert m.instrument.name == expected, label
        assert not m.ocr_folded and m.confidence == "high", label


def test_the_ocr_fold_is_only_the_reviewed_rare_confusions():
    """The fold set is deliberately small: the i/l/1 stroke group, o/0, and v/y.

    COMMON-letter confusions are refused — folding a/u, b/h, c/e or n/m would
    merge distinct names and widen what garbage resolves, and a folded match
    still PINS a staff to a part (`dossier.join_parts_to_slots` pins on any
    unambiguous alias, folded or not). The margin corpora's own unread reads
    `Oh.`->`Ob.` (b/h) and `Fug.`->`Fag.` (a/u) are left unread rather than
    bought at that price. See
    benchmarks/omr-margin-labels-2026-08/OCR_CONFUSIONS_2026-09-02.md.

    Pinned so a new fold cannot be added without landing here and justifying it.
    The alias<->alias check below is a true invariant but NOT sufficient on its
    own: a common-letter fold does its damage by pulling GARBLED reads onto an
    alias, not by merging two aliases, so measured against this vocabulary a/u
    and b/h both score zero here — which is exactly why the set is pinned."""
    import re as _re
    from tools.omr.instruments import _OCR_FOLD, _fold_ocr, INSTRUMENTS

    sources = {chr(k) for k in _OCR_FOLD}
    assert sources == set("l1|!}{][0y"), f"fold sources changed: {sorted(sources)}"
    for common in "aubhcenm":
        assert common not in sources, f"{common!r} must not be folded"

    # The fold must not make one instrument's alias collide with another's when
    # it did not already (pre-existing substring nesting like flute<petite flute
    # is handled by the longest-alias-first index, so only NET-NEW counts).
    owner = {a: inst.name for inst in INSTRUMENTS for a in inst.aliases}

    def word_sub(needle, hay):
        return _re.search(rf"(?<![a-z]){_re.escape(needle)}(?![a-z])", hay) is not None

    for a in owner:
        for b in owner:
            if owner[a] == owner[b]:
                continue
            if word_sub(_fold_ocr(a), _fold_ocr(b)) and not word_sub(a, b):
                raise AssertionError(
                    f"fold makes {a!r}({owner[a]}) collide with {b!r}({owner[b]})")


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

def test_the_qualified_italian_abbreviations_beethoven_5_prints():
    """Beethoven 5's fourth movement, from its own margin — and every one of
    these read as a DIFFERENT instrument before, not merely as nothing.

    The trombone forms are the ones that cost: bare "Tr." is Trombe in this
    tradition, so the alias index (longest first) sent "Tr. Alt." and "Tr. Ten."
    to the VOICES and "Tr. Bas." to the trumpets, and those three staves carry
    the alto, tenor and bass clefs the dossier exists to supply.
    """
    for label, expected in (("Fl. Pic.", "Piccolo"), ("Fl./Pic.", "Piccolo"),
                            ("C. Fag.", "Contrabassoon"), ("C.Fag.", "Contrabassoon"),
                            ("Tr. Alt.", "Trombone"), ("Tr. Ten.", "Trombone"),
                            ("Tr. Bas.", "Trombone")):
        assert lookup(label).instrument.name == expected, label
    # Bare "Tr." is untouched: it is still the trumpets.
    assert lookup("Tr.").instrument.name == "Trumpet"


def test_tromba_bassa_is_why_tr_bas_stays_ambiguous():
    """"Tr. Bas." is Trombone basso in the Italian tradition and Tromba bassa —
    the bass trumpet — in the German. The lexicon answers with the commoner
    reading, and listing it as ambiguous is what stops a staff being PINNED on
    it (`dossier.join_parts_to_slots`)."""
    from tools.omr.instruments import (AMBIGUOUS_ALIASES, candidates_for_alias,
                                       normalize_label)
    assert normalize_label("Tr. Bas.") == "tr bas"
    assert "tr bas" in AMBIGUOUS_ALIASES
    names = [i.name for i in candidates_for_alias("tr bas")]
    assert names == ["Trombone", "Trumpet"], "lexicon's own answer stays first"
    # The unqualified forms are NOT ambiguous — there is no tromba alta.
    assert "tr alt" not in AMBIGUOUS_ALIASES
    assert "tr ten" not in AMBIGUOUS_ALIASES


def test_a_hyphen_separates_words_in_a_printed_label():
    """German scores build abbreviations with hyphens, and keeping the hyphen
    defeats the word-boundary match — `kl` inside `a-klar` is followed by a
    letter, so nothing fires. Measured on Mahler 5 p.4, where it cost the
    clarinets, the trumpets and the contrabassoon."""
    from tools.omr.instruments import normalize_label
    assert normalize_label("A-Klar.") == "a klar"
    for label, expected in (("A-Klar.", "Clarinet"), ("B-Klar.", "Clarinet"),
                            ("Es-Klar.", "Clarinet"), ("B-Tromp.", "Trumpet"),
                            ("F-Hörner", "Horn"), ("Contraf.", "Contrabassoon")):
        assert lookup(label).instrument.name == expected, label


def test_the_german_drums_outrank_the_two_letter_brass():
    """"Gr. Tr." is the Grosse Trommel and "Kl. Tr." the Kleine Trommel. Before
    they were listed, Mahler 5 p.4 read its bass drum as a TRUMPET — on the
    strength of the two-letter `tr` — and its snare as a CLARINET, and the bass
    drum reading was confident enough to PIN a staff."""
    assert lookup("Gr. Tr.").instrument.name == "Percussion"
    assert lookup("Kl.Tr.").instrument.name == "Percussion"
    assert lookup("Gr.Tr.").instrument.name == "Percussion"
    # ...without disturbing the bare forms they have to out-rank.
    assert lookup("Tr.").instrument.name == "Trumpet"
    assert lookup("Kl.").instrument.name == "Clarinet"


def test_the_bare_string_abbreviations_mahler_prints():
    """"Erste Viol." / "Vcelle. get." — and `viol` must not fire inside the
    longer string names, which the word-boundary index guarantees."""
    for label, expected in (("Erste Viol.", "Violin"), ("Zweite Viol.", "Violin"),
                            ("Vcelle. get.", "Cello"), ("Violen.", "Viola"),
                            ("Viola", "Viola"), ("Violoncelle.", "Cello")):
        assert lookup(label).instrument.name == expected, label


def test_a_contra_qualifier_is_not_ignored_beside_a_bassoon_noun():
    """A contrabassoon is printed as a BASSOON name with a contra- qualifier,
    and the missing spellings did not abstain — the noun matched on its own and
    the qualifier was dropped, so `Contra-Fagott` and `Cont. Fag.` read as
    Bassoon and `C. Fagotto` as Bassoon at HIGH confidence, which is enough to
    pin a staff to the wrong part.

    Surfaced 2026-09-03 by `Contrafagott` on the Mahler 5 scan (scan_eval.py),
    which was one hole in a family of about twenty."""
    for label in ("Contrafagott", "Kontrafagott", "Contrafagotto", "Contrafagotti",
                  "Contrafagotte", "Kontrafagotte", "Kontrafagotti",
                  "Contra-Fagott", "Kontra-Fagott", "Contra Fagotto",
                  "C. Fagotto", "C.Fag.", "Contrafag.", "Kontrafag.",
                  "Contrabassoon", "Contra Bassoon", "Double Bassoon",
                  "Contrebasson", "Contrabasson", "Contre-basson",
                  "Cfg.", "Kfg.", "Cont. Fag.", "Contra Fg.", "Contraf."):
        m = lookup(label)
        assert m is not None, f"{label!r} did not match"
        assert m.instrument.name == "Contrabassoon", f"{label!r} -> {m.instrument.name}"


def test_the_plain_bassoon_is_untouched_by_the_contra_family():
    """The generated aliases are all LONGER than the bassoon alias inside them,
    so the longest-first index keeps an unqualified bassoon a bassoon."""
    for label in ("Fagotto", "Fagotti", "Fagott", "Fagotte", "Fag.", "Fg.",
                  "2 Fagotti", "Fag. I", "Bassoon", "Basson", "Bassons",
                  "Fagotti in B", "Fag. II."):
        m = lookup(label)
        assert m is not None, f"{label!r} did not match"
        assert m.instrument.name == "Bassoon", f"{label!r} -> {m.instrument.name}"


def test_the_contra_aliases_are_derived_so_no_spelling_is_left_out():
    """DERIVED from the bassoon's own aliases, the move `VOICE_QUALIFIERS`
    makes: a hand-list of a cross product is a bug with a slow fuse, and this
    one had six of its twenty-odd members.

    Pinned in both directions — every generated string is a real prefix plus a
    real bassoon stem, and every hand-listed alias the derivation replaced is
    still in the set — so a prefix cannot be added or a stem dropped without
    landing here."""
    from tools.omr.instruments import (_BASSOON_ALIASES, _CONTRA_ALIASES,
                                       _CONTRA_PREFIXES, INSTRUMENTS)

    # every previously hand-listed spelling survives the derivation
    for alias in ("contrabassoon", "double bassoon", "contrafagotto",
                  "contrafagotte", "kontrafagott", "contrebasson",
                  "cfag", "kfag", "c fag"):
        assert alias in _CONTRA_ALIASES, alias

    # and nothing else got in: each is prefix + optional space + bassoon stem
    for alias in _CONTRA_ALIASES:
        assert any(alias in (p + s + stem for s in ("", " "))
                   for p in _CONTRA_PREFIXES for stem in _BASSOON_ALIASES), alias

    cbsn = next(i for i in INSTRUMENTS if i.name == "Contrabassoon")
    # `contraf` is a TRUNCATION, not qualifier-plus-noun, so it is listed apart
    assert set(cbsn.aliases) == set(_CONTRA_ALIASES) | {"contraf"}


def test_the_contra_aliases_collide_with_no_other_instrument():
    """160 generated strings is a lot of new vocabulary, and the thing that
    makes it safe is that not one of them is word-contained in — or contains —
    another instrument's alias. `contrabassoon` sits inside no `contrabass`
    match because the word-boundary index refuses a letter on either side, and
    the longest-first order settles the rest."""
    import re as _re
    from tools.omr.instruments import _CONTRA_ALIASES, INSTRUMENTS

    others = {a: inst.name for inst in INSTRUMENTS
              if inst.name != "Contrabassoon" for a in inst.aliases}

    def word_sub(needle: str, hay: str) -> bool:
        return _re.search(rf"(?<![a-z]){_re.escape(needle)}(?![a-z])", hay) is not None

    for alias in _CONTRA_ALIASES:
        for other, owner in others.items():
            # a bassoon stem inside a contra alias is the POINT — the longer
            # alias wins — so only an exact collision or a foreign owner counts
            if owner == "Bassoon" and alias.endswith(other):
                continue
            assert not word_sub(other, alias), f"{other!r} ({owner}) fires inside {alias!r}"
            assert not word_sub(alias, other), f"{alias!r} fires inside {other!r} ({owner})"


def test_hr_and_trpt_resolve_to_the_instrument_they_abbreviate():
    """Breitkopf's Brahms 1 prints horn and trumpet staves as `Hr.` and
    `Trpt.` — surfaced 2026-09-03 by scan_eval.py, 24 labels across 13 real
    strings, every one abstaining before this. `hr` is the German/English
    horn abbreviation (Hörner); `trpt` is a distinct 4-letter trumpet
    shorthand, not a typo of the `tpt` already in the table."""
    for label in ("Hr.", "(C) Hr.", "(C) Hr", "(E) Hr.", "(Es) Hr.", "(F) Hr.",
                  ". (C) Hr.", "Hr. (E)", "Hr. (Es)", "Hr. 1. (C) 2.",
                  "Hr. 1. (Es) 2.", "Hr.1. (Es)2."):
        m = lookup(label)
        assert m is not None, f"{label!r} did not match"
        assert m.instrument.name == "Horn", f"{label!r} -> {m.instrument.name}"
    for label in ("Trpt.", "Trpt. (C)"):
        m = lookup(label)
        assert m is not None, f"{label!r} did not match"
        assert m.instrument.name == "Trumpet", f"{label!r} -> {m.instrument.name}"


def test_hr_and_trpt_collide_with_no_other_alias():
    """`hr` cannot fire inside `hrf` (Harp) or `chor` (Chorus) — the
    word-boundary index refuses a letter on either side. Checked against the
    whole table, both directions, the same shape as the contra-alias test."""
    import re as _re
    from tools.omr.instruments import INSTRUMENTS

    owner = {a: inst.name for inst in INSTRUMENTS for a in inst.aliases}

    def word_sub(needle: str, hay: str) -> bool:
        return _re.search(rf"(?<![a-z]){_re.escape(needle)}(?![a-z])", hay) is not None

    for new, new_owner in (("hr", "Horn"), ("trpt", "Trumpet")):
        for other, other_owner in owner.items():
            if other == new:
                continue
            assert not word_sub(new, other), f"{new!r} fires inside {other!r} ({other_owner})"
            assert not word_sub(other, new), f"{other!r} ({other_owner}) fires inside {new!r}"


def test_a_trailing_key_after_hr_or_trpt_is_read_a_leading_one_is_not():
    """The bare-key parser only ever looked at what comes AFTER the alias
    (`_parse_bare_key`), a pre-existing limit shared by every key-taking
    instrument in this table — `A-Klar.` resolves to Clarinet with its
    default transposition, not with a parsed one, for the identical reason.
    Adding `hr`/`trpt` inherits that limit rather than introducing it:
    trailing keys resolve exactly, leading ones fall back to the instrument's
    positional default. Both are pinned so a future change to the parser is
    measured against both cases, not just the one that already worked."""
    trailing = lookup("Hr. (E)")
    assert trailing.instrument.name == "Horn" and trailing.fifths_offset == -4
    leading = lookup("(E) Hr.")
    assert leading.instrument.name == "Horn"
    assert leading.fifths_offset == leading.instrument.default_fifths_offset


# ── 2026-09-05: substring capture, plurals, and the ambiguity a Match carries ──


def test_a_match_carries_the_ambiguity_of_the_alias_that_fired():
    """`lookup` returns ONE answer and an ambiguous alias has more than one.

    `Basso` is the contrabasses at the foot of an orchestral score and the bass
    voice under a vocal stave; the lexicon names the commoner and a caller
    comparing `.instrument.name` to a printed label scores the other reading as
    an error. It cost three harnesses a correct `Contrabass` each — the join
    RESULTS, and two staff-identity probes — before the information was made to
    travel WITH the answer instead of beside it.

    `lookup`'s return value is unchanged; these are properties."""
    m = lookup("Basso")
    assert m.instrument.name == "Bass voice"          # unchanged
    assert m.is_ambiguous
    assert [i.name for i in m.alternatives] == ["Bass voice", "Contrabass"]
    assert lookup("Contrabasso").is_ambiguous is False
    assert lookup("Contrabasso").alternatives == ()
    # It is the ALIAS that is ambiguous, not the label — the same rule
    # `dossier.join_parts_to_slots` applies before letting a label pin.
    assert lookup("Bassi 1. 2.").is_ambiguous


def test_a_basset_horn_is_a_woodwind_and_a_flugelhorn_is_not_a_horn():
    """CROSS-FAMILY capture by a shorter alias, the `Tr. Alt.` shape with the
    qualifier missing: the lexicon held no basset horn, so no alias was longer
    than the bare `horn` inside it and `_ALIAS_INDEX` had nothing to prefer.

    A staff-identity workstream measures family precision 0.955 against
    instrument 0.873, so a cross-family error corrupts the STRONGER level."""
    for label in ("Basset horn", "Bassetthorn", "Corno di bassetto"):
        m = lookup(label)
        assert m.instrument.name == "Basset horn", label
        assert m.instrument.family == "woodwind", label
    for label in ("Flugelhorn", "Flügelhorn", "Flügel Horn"):
        assert lookup(label).instrument.name == "Flugelhorn", label
    # and the real horn is untouched
    assert lookup("Corni").instrument.name == "Horn"
    assert lookup("Hörner in Es").instrument.name == "Horn"


def test_contrabass_is_a_size_word_as_well_as_an_instrument():
    """The mirror of the basset horn: here the QUALIFIER is the ten-letter
    alias and the noun is short, so all three compounds resolved to a STRING.
    `Contrabass tuba` did it at high confidence, which is what pins a staff."""
    assert lookup("Contrabass clarinet").instrument.family == "woodwind"
    assert lookup("Contrabass trombone").instrument.name == "Trombone"
    assert lookup("Contrabass tuba").instrument.name == "Tuba"
    # the plain instrument is unmoved
    assert lookup("Contrabass").instrument.name == "Contrabass"
    assert lookup("Kontrabässe").instrument.name == "Contrabass"


def test_a_conjunction_keeps_a_condensed_bass_staff_out_of_the_qualifier_rule():
    """⚠️ THE ADJACENCY TEST READS `norm`, NOT THE STRIPPED STRING, and that is
    the whole point. "Contrabass clarinet" is one instrument and "Contrabassi e
    Violoncelli" is two staves printed on one; `_STRIP_TOKENS` deletes the `e`
    and the two become word-for-word identical. Without adjacency the
    generalised rule turns every condensed bass staff into a cello."""
    for label in ("Violoncello e Contrabasso", "Contrabassi e Violoncelli",
                  "Celli e Bassi", "Violoncell u. Contrabass"):
        assert lookup(label).instrument.family == "string", label
    assert lookup("Contrabassi").instrument.name == "Contrabass"


def test_the_voice_half_of_the_qualifier_rule_needs_no_adjacency():
    """⚠️ MEASURED ASYMMETRY, not an oversight. A condensed staff pairs two
    INSTRUMENTS and never an instrument with a voice, so the voice half has
    nothing adjacency would protect and only loses reach to it: applied to
    both halves it regressed `Horn in B♭ basso` — a real reference part name —
    from Horn to a bass VOICE, because "in Bb" stands between the two."""
    assert lookup("Horn in B♭ basso").instrument.name == "Horn"
    assert lookup("Bb (basso) Horn 4").instrument.name == "Horn"
    assert lookup("Fl. Alt.").instrument.name == "Flute"
    assert lookup("Soprano Recorder").instrument.name == "Recorder"


def test_plurals_are_derived_because_the_hand_list_was_DIRECTIONAL():
    """A word-bounded alias cannot fire inside its own plural, so the table
    hand-listed plurals — for the short generic nouns and not for the long
    compounds containing them. Pluralising a label therefore DEFEATED the
    specific compound and handed the staff to the generic noun inside it, and
    two of the three known cases were cross-family."""
    assert lookup("English horns").instrument.family == "woodwind"
    assert lookup("cors anglais").instrument.name == "English horn"
    assert lookup("bass clarinets").instrument.name == "Bass clarinet"
    # the plain gaps the derivation closes
    for label, expected in (("oboes", "Oboe"), ("cellos", "Cello"),
                            ("harps", "Harp"), ("tubas", "Tuba"),
                            ("double basses", "Contrabass"),
                            ("piccolos", "Piccolo"), ("saxophones", "Saxophone")):
        assert lookup(label).instrument.name == expected, label


def test_a_register_words_plural_is_not_derived_because_french_reuses_it():
    """⚠️ The derivation is switched OFF for the voices, and the corpus is why:
    in French an orchestra's `Altos` are the VIOLAS and its `Basses` are the
    double basses. 23 of the 1422-label margin corpus's `Altos` are Ravel's
    violas and not one is a singer, so deriving `altos` from the voice `alto`
    would invent a cross-family error on the commonest French string label."""
    from tools.omr.instruments import aliases_of

    for inst in INSTRUMENTS:
        if inst.family == "voice" and inst.name != "Chorus":
            assert aliases_of(inst) == inst.aliases, inst.name
    m = lookup("Altos")
    assert m.instrument.name == "Viola"
    # and it is declared ambiguous, so it may not PIN a staff — a chorus
    # really does have altos.
    assert m.is_ambiguous
    assert [i.name for i in m.alternatives] == ["Viola", "Alto"]


def test_an_ambiguous_alias_stays_ambiguous_in_the_plural():
    """An ambiguity is a property of the WORD, not of its number.
    `dossier.join_parts_to_slots` reads `AMBIGUOUS_ALIASES` as the set that may
    not pin, so a plural missing from it is a WRONG pin, not a missing one."""
    from tools.omr.instruments import (AMBIGUOUS_ALIASES,
                                       _DECLARED_AMBIGUOUS_ALIASES)

    assert "basses" in AMBIGUOUS_ALIASES
    assert AMBIGUOUS_ALIASES["basses"] == AMBIGUOUS_ALIASES["basse"]
    # a declared entry always beats a derived one
    for alias, names in _DECLARED_AMBIGUOUS_ALIASES.items():
        assert AMBIGUOUS_ALIASES[alias] == names, alias


def test_no_derived_plural_collides_with_another_instruments_alias():
    """The gate is not widened — a generated string still has to appear in the
    label word-bounded, exactly — but a generated string that happens to BE
    another instrument's alias would silently re-point it."""
    from tools.omr.instruments import aliases_of

    declared: dict[str, set[str]] = {}
    for inst in INSTRUMENTS:
        for alias in inst.aliases:
            declared.setdefault(alias, set()).add(inst.name)
    for inst in INSTRUMENTS:
        for alias in aliases_of(inst):
            if alias in inst.aliases:
                continue
            assert inst.name in declared.get(alias, {inst.name}), \
                f"derived {alias!r} collides with {declared.get(alias)}"


def test_a_cornet_section_can_be_encoded_at_all():
    """Trumpet -> Cornet was unencodable: the French and Russian repertoire
    (Berlioz, Franck, Tchaikovsky) prints trumpets and cornets on separate
    staves, and `2 cornets` was the single largest line in the IMSLP
    instrumentation residual — 14 of 99 fragments on one missing entry.

    It ABSTAINED rather than misresolving, so nothing that resolved before
    moves: `cor` is blocked by the `n`, `corno` by the `e`."""
    for label in ("Cornet", "2 cornets", "Cornets à pistons", "Kornett"):
        assert lookup(label).instrument.name == "Cornet", label
    assert lookup("Cor.").instrument.name == "Horn"
    assert lookup("Corno").instrument.name == "Horn"
    assert lookup("Corno inglese").instrument.name == "English horn"


def test_the_absent_instruments_that_were_CAPTURED_rather_than_abstaining():
    """The survey behind this batch: an instrument the lexicon does not hold is
    harmless when it ABSTAINS and dangerous when a shorter alias captures it.
    Every name here was captured cross-family before; the ones that abstained
    are gaps and were filled without changing anything that already resolved."""
    for label, family in (("Basset horn", "woodwind"),
                          ("Corno di bassetto", "woodwind"),
                          ("Contrabass clarinet", "woodwind"),
                          ("Contrabass trombone", "brass"),
                          ("Contrabass tuba", "brass"),
                          ("English horns", "woodwind"),
                          ("cors anglais", "woodwind")):
        assert lookup(label).instrument.family == family, label
