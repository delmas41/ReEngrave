"""ROADMAP 2.139 (STAGED ADJUDICATE): a lexicon word is not also a dynamic.

Brahms p24: the plate prints *marc.*; the detector boxed the word as two low-score
`m` dynamic letters with no letter ink beside either, `adjudicate_dynamic` kept them
(`letters_alone_inside_a_word_box`) and the file got a blue `dyn.` next to the text
direction `marc.`. Flag `OMR_DYNAMIC_LEXICON_WORD`, default OFF.
"""
from __future__ import annotations

from tools.omr.tests.test_staged_letter_neighbours_2026_10_09 import _decide  # noqa: E501

ALONE = (False, False)
MARC_LETTERS = [("m", 1731, 1851), ("m", 1731, 1975)]
MARC = [("marc.", 1734, 1912)]
FLAG = "OMR_DYNAMIC_LEXICON_WORD"


def _verdict_reason(letters, words, neighbours):
    import tools.omr.staged.adjudicate as adjudicate  # noqa: F401
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Q
    from tools.omr.tests import test_staged_letter_neighbours_2026_10_09 as base
    holder = {}
    real = base.adjudicate.run
    def run(log):
        real(log)
        holder["v"] = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))
    base.adjudicate.run = run
    try:
        base._decide(letters, words, neighbours)
    finally:
        base.adjudicate.run = real
    return holder["v"]


def test_flag_off_marc_is_the_unspellable_dyn(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    v = _verdict_reason(MARC_LETTERS, MARC, {0: ALONE, 1: ALONE})
    assert v.reason == "unspellable"


def test_flag_on_marc_is_the_words_not_a_dynamic(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    v = _verdict_reason(MARC_LETTERS, MARC, {0: ALONE, 1: ALONE})
    assert v.reason == "no_letters"
    assert v.detail["letters_of_a_lexicon_word"] == 2


def test_CONTROL_flag_on_a_lone_p_in_a_word_box_is_still_piano(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    assert _decide([("p", 2398, 2429)], [("dolce", 2398, 2540)],
                   neighbours={0: ALONE}) == ["p"]


def test_CONTROL_flag_on_no_word_read_a_lone_m_is_not_dropped(monkeypatch):
    """No second reader says it is text: it stays what the detector said (rule 8)."""
    monkeypatch.setenv(FLAG, "1")
    v = _verdict_reason([("m", 1731, 1851)], [], {0: ALONE})
    assert v.reason != "no_letters"


def test_CONTROL_flag_on_a_real_dynamic_before_a_word_is_kept(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    assert _decide([("f", 1624, 1692), ("p", 1767, 1815)],
                   [("f espr. e legato", 1622, 2146)],
                   neighbours={0: (False, True), 1: (True, True)}) == ["f"]


# ── EXPORT: the word is the text direction in BOTH files ────────────────────

def _ly(counters_flag, monkeypatch, writable=True):
    from collections import Counter
    from tools.omr.staged import lilypond as LY
    if counters_flag:
        monkeypatch.setenv(FLAG, "1")
    else:
        monkeypatch.delenv(FLAG, raising=False)
    c = Counter()
    return LY._direction_suffix([(1734.0, "words", "marc.")], c, writable, "x"), c


def test_lilypond_flag_off_the_word_is_counted_and_dropped(monkeypatch):
    out, c = _ly(False, monkeypatch)
    assert out == "" and c["direction_words_not_renderable"] == 1


def test_lilypond_flag_on_the_word_is_written_as_text(monkeypatch):
    out, c = _ly(True, monkeypatch)
    assert '\\italic "marc."' in out and c["direction_words"] == 1
    assert c["direction_words_not_renderable"] == 0


def test_CONTROL_lilypond_flag_on_an_unwritable_bar_still_drops_it_counted(monkeypatch):
    out, c = _ly(True, monkeypatch, writable=False)
    assert out == "" and c["direction_words_not_renderable"] == 1


def test_musicxml_carries_the_word_as_words_never_dynamics():
    from tools.omr.staged import export as SX
    xml = SX._direction_xml("words", "marc.", "  ")
    assert "<words>marc.</words>" in xml and "<dynamics" not in xml
