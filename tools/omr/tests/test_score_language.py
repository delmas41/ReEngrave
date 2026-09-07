"""The score-language reader: its boundary with the lexicon, and its refusals.

Every test here was run RED before it was run green — the assertions that
matter are the ones that fail when the thing they guard is removed, and three
of them guard faults that were live in this module's own first revision.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr import instruments, score_language as L

CORPUS = (Path(__file__).resolve().parents[3]
          / "benchmarks/omr-lexicon-2026-09/labels.json")


def _corpus_by_document() -> dict[str, list[str]]:
    if not CORPUS.is_file():                     # pragma: no cover - env guard
        pytest.skip(f"margin-label corpus not present: {CORPUS}")
    docs: dict[str, list[str]] = {}
    for rec in json.loads(CORPUS.read_text()):
        docs.setdefault(rec["source"], []).append(rec["text"])
    return docs


# ── the boundary with the lexicon ────────────────────────────────────────────

def test_language_never_decides_an_alias_the_lexicon_declared_ambiguous():
    """The composition rule, in the direction that prevents double-counting.

    A declared ambiguity is arbitrated by `contextual._resolve_ambiguous_labels`
    using the layout fit and the CLEF, which was measured worth 51 records on
    Beethoven 5. Both channels read the same labels, so two verdicts from one
    ancestor would be double-counting, not corroboration.
    """
    overlap = set(L.LANGUAGE_READINGS) & set(instruments.AMBIGUOUS_ALIASES)
    assert not overlap, (
        f"{sorted(overlap)} is arbitrated by the position channel already; "
        "move it to CORROBORATION_ONLY or declare why it needs a second owner")


def test_corroboration_entries_are_exactly_the_ones_owned_elsewhere():
    """…and the other direction, so the split cannot silently drift."""
    for alias in L.CORROBORATION_ONLY:
        assert alias in instruments.AMBIGUOUS_ALIASES, (
            f"{alias!r} is not declared ambiguous, so nothing else owns it — "
            "it belongs in LANGUAGE_READINGS, where it would actually decide")


def test_corroboration_table_is_never_consulted_by_the_decider():
    """`resolve_alias` must ignore it even when the language is read."""
    reading = L.LanguageReading("it", {"it": 9, "de": 0, "fr": 0, "en": 0}, 9, 9)
    assert L.resolve_alias("tp", reading) is None
    assert L.corroborating_reading("tp", reading) == "Timpani"


def test_a_decided_alias_never_votes_for_the_language_that_decides_it():
    """⚠️ THE NON-CIRCULARITY GUARANTEE, and it is structural, not conventional.

    Language is inferred FROM labels and then used to decide A label, which is
    the shape §4.1 of the architecture map refuses three times over: *"a message
    may be consumed only by a process whose own output did not contribute to
    it."*

    The loop is broken by construction rather than by care. The vote is cast
    only by aliases tagged with exactly ONE tradition; an alias this module
    decides is ambiguous BETWEEN traditions, so it is tagged with none and can
    never contribute to the reading that judges it. The two alias sets are
    disjoint, and this test is that disjointness.
    """
    voters = {a for a, langs in L._ALIAS_LANGUAGES.items() if len(langs) == 1}
    decided = set(L.LANGUAGE_READINGS) | set(L.EXTRA_AMBIGUOUS)
    assert not (voters & decided), (
        f"{sorted(voters & decided)} both votes for the language and is "
        "decided by it — the evidence has a cycle")


def test_every_tagged_spelling_is_a_real_alias_of_some_instrument():
    """The tagging is keyed on the lexicon, so it cannot invent vocabulary.

    Fails loudly if `instruments.py` renames or drops an alias this module
    tags — the fault mode where a language table quietly stops voting.
    """
    known = {a for inst in instruments.INSTRUMENTS
             for a in instruments.aliases_of(inst)}
    for lang, spellings in L._LANGUAGE_SPELLINGS.items():
        unknown = [s for s in spellings if s not in known]
        assert not unknown, f"{lang}: not aliases in instruments.py: {unknown}"


def test_extra_ambiguous_names_are_real_instruments():
    names = {inst.name for inst in instruments.INSTRUMENTS}
    for alias, candidates in L.EXTRA_AMBIGUOUS.items():
        assert set(candidates) <= names, alias
        assert alias in L.LANGUAGE_READINGS
    for alias, per_language in L.LANGUAGE_READINGS.items():
        assert set(per_language.values()) <= names, alias


def test_a_re_decided_instrument_never_transposes():
    """⚠️ What makes it safe for the consumer to carry `fifths_offset` across.

    `contextual._apply_score_language` moves `instrument` and leaves the offset
    parsed from the printed key suffix alone. That is right only while every
    reachable instrument is non-transposing — `Tb.` is a tuba or a trombone and
    neither transposes. A future entry naming, say, a horn would need the
    offset recomputed, and would fail here first.
    """
    for per_language in L.LANGUAGE_READINGS.values():
        for name in per_language.values():
            inst = L.instrument_named(name)
            assert inst is not None, name
            assert inst.chromatic == 0, (name, inst.chromatic)
            assert inst.default_fifths_offset == 0, name


def test_the_lexicon_itself_is_untouched():
    """This module reads the lexicon; it must never be a second lexicon.

    `Tb.` still resolves to Tuba, and `tb` is still undeclared, because that is
    a DEFAULT and this change does not move one.
    """
    match = instruments.lookup("Tb.")
    assert match is not None and match.instrument.name == "Tuba"
    assert "tb" not in instruments.AMBIGUOUS_ALIASES


# ── the two false tags the corpus caught, both live in revision 1 ────────────

def test_a_spelling_two_traditions_share_casts_no_vote():
    """⚠️ `flutes` was tagged English-only and voted English on Ravel.

    Normalization strips the circumflex, so French `Flûtes` and English
    `Flutes` are one string. Tagged both, it is inert.
    """
    assert L.languages_of_alias("flutes") == frozenset({"fr", "en"})
    assert not L.is_diagnostic("flutes")


def test_the_german_plural_of_bass_is_not_a_french_vote():
    """⚠️ Mahler 5's `Bässe` normalizes to `basse` — the French word.

    Twelve French votes on a German score, the largest false vote the corpus
    produced. The accent that carried the language is gone before this sees it.
    """
    assert instruments.normalize_label("Bässe") == "basse"
    assert L.languages_of_alias("basse") == frozenset({"de", "fr"})
    assert not L.is_diagnostic("basse")


def test_a_latin_consonant_skeleton_carries_no_language():
    """⚠️ `Trpt.` is printed on Brahms 1 / BREITKOPF — a German edition.

    It cast 8 English votes there before being untagged. `instruments.py`
    already records where that abbreviation appears; the tagging has to agree
    with it.
    """
    for alias in ("tpt", "trpt", "vln", "vla", "tbn"):
        assert not L.languages_of_alias(alias), alias


# ── detection: what it claims and what it refuses ────────────────────────────

def test_too_few_diagnostic_labels_abstains():
    reading = L.detect(["Fl.", "Ob.", "Cl.", "Fag.", "Cor.", "Tr.", "Tb."])
    assert reading.language is None
    assert reading.n_diagnostic < L.MIN_DIAGNOSTIC_VOTES


def test_a_near_even_mixture_abstains():
    reading = L.detect(["Flauti", "Oboi", "Clarinetti",
                        "Floten", "Oboen", "Klarinetten"])
    assert reading.votes["it"] == 3 and reading.votes["de"] == 3
    assert reading.language is None
    assert reading.is_mixed


def test_a_pool_of_many_documents_gets_no_language():
    """The reference part-name corpus is 1271 names from many works.

    A language is a property of ONE printing. Pooled evidence must abstain,
    and this is the shape that would otherwise launder four traditions into
    one confident answer.
    """
    pool = Path(__file__).resolve().parents[3] / (
        "benchmarks/omr-lexicon-2026-09/part-names.json")
    if not pool.is_file():                       # pragma: no cover - env guard
        pytest.skip("reference part-name corpus not present")
    reading = L.detect(json.loads(pool.read_text()))
    assert reading.n_diagnostic > 100            # plenty of evidence…
    assert reading.language is None              # …and no single answer
    assert reading.is_mixed


# ── the worked cases, on the real corpus ─────────────────────────────────────

def test_litolff_and_breitkopf_read_the_traditions_they_print():
    docs = _corpus_by_document()
    assert L.detect(docs["beethoven5-575951-textlayer"]).language == "it"
    assert L.detect(docs["brahms1-breitkopf-scan"]).language == "de"
    assert L.detect(docs["ravel-bolero-textlayer"]).language == "fr"
    assert L.detect(docs["mahler5-local-scan"]).language == "de"


def test_an_italian_score_reads_tb_as_the_trombone_it_is():
    """The commissioned fault: Litolff abbreviating `Tromboni`.

    The work's IMSLP roster (`source_kind: catalog`) lists 2 trombones and no
    tuba, so this is checkable against evidence independent of any encoding
    and of any page reading.
    """
    italian = L.LanguageReading("it", {"it": 7, "de": 0, "fr": 0, "en": 0}, 7, 52)
    assert L.resolve_alias("tb", italian) == "Trombone"
    _, decisions = L.resolve_document(["Tb.", "Fl.", "Cor."], italian)
    changed = [d for d in decisions if d.changed]
    assert [(d.alias, d.lexicon, d.language) for d in changed] == [
        ("tb", "Tuba", "Trombone")]


def test_a_german_score_keeps_its_tuba():
    german = L.LanguageReading("de", {"it": 0, "de": 9, "fr": 0, "en": 0}, 9, 20)
    assert L.resolve_alias("tb", german) == "Tuba"
    _, decisions = L.resolve_document(["Tb."], german)
    assert not any(d.changed for d in decisions)


def test_a_french_or_unread_document_abstains_on_tb():
    french = L.LanguageReading("fr", {"it": 0, "de": 0, "fr": 9, "en": 0}, 9, 20)
    assert L.resolve_alias("tb", french) is None
    assert L.resolve_alias("tb", L.detect([])) is None


# ── what it must not break ───────────────────────────────────────────────────

def test_handel_is_untouched_in_every_tradition():
    """⚠️ `BASSO` (the voice) and `Bassi` (the strings) print on ONE page.

    The current first answers are right for both. Language separates nothing
    here — the word is the same in Italian, French and English — so every
    reading must abstain, and a future entry that breaks this fails here.
    """
    for lang in L.LANGUAGES:
        reading = L.LanguageReading(lang, {k: (9 if k == lang else 0)
                                           for k in L.LANGUAGES}, 9, 20)
        for alias in ("basso", "bassi", "basse", "bass", "tr bas", "cor"):
            assert L.resolve_alias(alias, reading) is None, (lang, alias)


def test_no_document_in_the_corpus_has_a_bass_label_re_decided():
    docs = _corpus_by_document()
    for src, labels in docs.items():
        _, decisions = L.resolve_document(labels)
        for d in decisions:
            if d.changed:
                assert d.alias == "tb", (src, d)


def test_the_only_corpus_wide_change_is_the_nine_litolff_trombones():
    """The whole measured effect, pinned as a number.

    Margin labels alone; `beethoven6-504082` needs the head-page escalation to
    read its language, so its nine are not in this arm.
    """
    docs = _corpus_by_document()
    changed = 0
    for labels in docs.values():
        _, decisions = L.resolve_document(labels)
        changed += sum(1 for d in decisions if d.changed)
    assert changed == 0


# ── the consumer: contextual's document-scoped pass ──────────────────────────

def _italian_page():
    """One page of Litolff's Beethoven 6, as the reader hands it over."""
    from tools.omr.staff_labels import StaffLabel

    def lab(i, text):
        match = instruments.lookup(text)
        return StaffLabel(
            staff_index=i, text=text,
            instrument=None if match is None else match.instrument,
            fifths_offset=0 if match is None else match.fifths_offset,
            y_center_px=100.0 * i,
            confidence="none" if match is None else match.confidence,
            alias="" if match is None else match.alias)

    return [lab(0, "Flauti."), lab(1, "Oboi."), lab(2, "Clarinetti in B."),
            lab(3, "Fagotti."), lab(4, "Corni in F."), lab(5, "Trombe."),
            lab(6, "Tb."), lab(7, "Violino I."), lab(8, "Violoncello.")]


def test_voting_off_the_alias_is_the_same_answer_as_voting_off_the_text():
    """⚠️ What makes the unconditional detection free — a 22-second fact.

    `instruments.lookup` costs 23-136 ms per string, so re-resolving a
    document's labels to vote its language costs 21.98 s on Ravel's 427. Every
    reader already resolved them and `StaffLabel.alias` holds the answer, so the
    consumer votes off a field it is holding. This asserts the two paths agree
    on every document of the corpus, which is what licenses using the cheap one.
    """
    for src, labels in _corpus_by_document().items():
        by_text = L.detect(labels)
        cache: dict[str, str | None] = {}
        aliases = []
        for text in labels:
            if text not in cache:
                m = instruments.lookup(text)
                cache[text] = None if m is None else m.alias
            aliases.append(cache[text])
        by_alias = L.detect_from_aliases(aliases, len(labels))
        assert by_alias.language == by_text.language, src
        assert by_alias.votes == by_text.votes, src


def test_the_document_pass_reads_the_language_off_the_whole_run():
    from tools.omr import contextual

    reading = contextual._read_score_language([_italian_page()])
    assert reading.language == "it"
    assert reading.share == 1.0


def test_the_document_pass_moves_the_instrument_and_never_the_text():
    from tools.omr import contextual

    page = _italian_page()
    reading = contextual._read_score_language([page])
    out, changes = contextual._apply_score_language([page], reading)

    assert [c["from"] for c in changes] == ["Tuba"]
    assert [c["to"] for c in changes] == ["Trombone"]
    # ⚠️ the reader's own string is untouched, and so is everything but the
    # instrument — the contract the roster pass states for the same reason.
    for before, after in zip(page, out[0]):
        assert before.text == after.text
        assert before.alias == after.alias
        assert before.confidence == after.confidence
        assert before.fifths_offset == after.fifths_offset
    assert out[0][6].instrument.name == "Trombone"
    assert page[6].instrument.name == "Tuba"          # the input is not mutated


def test_a_german_document_keeps_its_tuba_through_the_same_pass():
    from tools.omr import contextual
    from tools.omr.staff_labels import StaffLabel

    def lab(i, text):
        m = instruments.lookup(text)
        return StaffLabel(i, text, None if m is None else m.instrument,
                          0, 100.0 * i,
                          "none" if m is None else m.confidence,
                          "" if m is None else m.alias)

    page = [lab(0, "Flöten"), lab(1, "Oboen"), lab(2, "Klarinetten"),
            lab(3, "Fagotte"), lab(4, "Hörner"), lab(5, "Pauken"),
            lab(6, "Tb.")]
    reading = contextual._read_score_language([page])
    assert reading.language == "de"
    _, changes = contextual._apply_score_language([page], reading)
    assert changes == []


# ── the flag ─────────────────────────────────────────────────────────────────

def test_default_is_off(monkeypatch):
    monkeypatch.delenv("OMR_SCORE_LANGUAGE", raising=False)
    assert L.enabled() is False
    monkeypatch.setenv("OMR_SCORE_LANGUAGE", "1")
    assert L.enabled() is True
    monkeypatch.setenv("OMR_SCORE_LANGUAGE", "0")
    assert L.enabled() is False
