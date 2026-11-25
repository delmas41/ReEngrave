"""ROADMAP 2.345: the LilyPond file draws the red words the MusicXML file already shows for an unread note (STAGED EXPORT, `lilypond.py`).

CAUSE: 2.333's spot mark and 2.343's seven arc marks were written by `export._part_xml` / `_measure_events_xml` as `<words color=red>` and
nothing in `lilypond.py` read the same data (2.333 left it, "outside this lane's fence"); the PDF hid what the MusicXML showed.

Controls are the REAL cases of 2.343 (Litolff p2 staff 7 bars 9-11 ties; p14 slur obs:564481; p1 kind-unread run obs:013999) and 2.333 (Litolff
viola p6 6/1/9/11, the upper head dropped, the half alone fills the bar), run through the module's own marking functions; every word the MusicXML
carries for a head must be drawn red by the LilyPond renderer, and nothing else may be (a read head draws nothing). Each fails on the old code.
"""
import collections
import json
import pathlib
import re

import pytest

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.tests import test_tie_unwritten_end_marked_2_343 as T343
from tools.omr.tests import test_dropped_head_marks_2_333 as T333

RED_WORDS = re.compile(r'\^\\markup \{ \\with-color #red "([^"]+)" \}')


def _event(head):
    return {"kind": "note", "noteheads": [head], "duration_beats": 2.0, "duration_type": "half", "dots": 0, "x_position": 100.0}


def _ly_words(head, counters=None):
    return RED_WORDS.findall(LY._lily_event_marked(_event(head), {}, None, counters))


def _xml_words(head):
    return re.findall(r'<words color="%s">([^<]+)</words>' % SX.UNREAD_BAR_MARK_COLOR, T343._xml(head))


def _tie_heads(written, drop_pitch_of=()):
    t = T343.TestTieWithAnUnwrittenNote()
    return t._run(written, drop_pitch_of)[0]


def _slur_heads(written, drop_pitch_of=()):
    t = T343.TestSlurAndUnreadKindArc()
    t.setUp()
    rec = T343._record("arc_unwritten_end_litolff_20261123.json", drop_pitch_of=drop_pitch_of)
    return t._slur(written, rec=rec)[0]


def _unread_heads(written):
    t = T343.TestSlurAndUnreadKindArc()
    t.setUp()
    return t._unread(written)[0]


CASES = {
    "tie from unread note": lambda: _tie_heads([T343.FIRST, T343.LAST])[T343.LAST],
    "tie to unread note": lambda: _tie_heads([T343.FIRST, T343.LAST])[T343.FIRST],
    "slur from unread note": lambda: _slur_heads([T343.SLUR_STOP])[T343.SLUR_STOP],
    "slur to unread note": lambda: _slur_heads([T343.SLUR_START])[T343.SLUR_START],
    "arc from unread note": lambda: _tie_heads([T343.FIRST, T343.LAST], (T343.MIDDLE,))[T343.LAST],
    "arc to unread note": lambda: _tie_heads([T343.FIRST, T343.LAST], (T343.MIDDLE,))[T343.FIRST],
    "arc: tie or slur unread": lambda: _unread_heads([T343.UNREAD_START, T343.UNREAD_STOP])[T343.UNREAD_START],
}


@pytest.mark.parametrize("word", sorted(CASES))
def test_each_2_343_word_is_drawn_red_as_the_musicxml_shows_it(word):
    head = CASES[word]()
    assert _xml_words(head) == [word]                  # the control is the real one: the MusicXML says it
    counters = collections.Counter()
    assert _ly_words(head, counters) == [word]         # the PDF says the same words, in red
    assert counters["arcs_marked_for_an_unread_note"] == 1


def test_the_seven_words_are_the_exporters_own_strings():
    # one source of truth: the words drawn are the ones the heads carry, not a second list
    assert set(CASES) == {SX.TIE_FROM_UNREAD_NOTE_WORD, SX.TIE_TO_UNREAD_NOTE_WORD, SX.SLUR_FROM_UNREAD_NOTE_WORD, SX.SLUR_TO_UNREAD_NOTE_WORD,
                          SX.ARC_FROM_UNREAD_NOTE_WORD, SX.ARC_TO_UNREAD_NOTE_WORD, SX.ARC_KIND_UNREAD_WORD}
    assert '"tie from' not in open(LY.__file__).read()          # lilypond.py holds no copy of the strings


def test_a_read_head_draws_nothing():
    heads = _tie_heads([T343.FIRST, T343.MIDDLE, T343.LAST])         # both ends written: no word anywhere
    for h in heads.values():
        assert _ly_words(h) == []
        assert "unread" not in LY._lily_event_marked(_event(h), {})


def test_no_mark_where_the_head_was_not_written_and_nothing_is_invented():
    h = _tie_heads([T343.FIRST, T343.LAST])[T343.FIRST]
    text = LY._lily_event_marked(_event(h), {})
    assert text.count("markup") == 1 and "~" not in text           # one word; the tie itself is not written


def _viola_events(monkeypatch):
    got, _ = T333._file("litolff_viola", monkeypatch, "spot")
    assert got
    case = T333.FIX["litolff_viola"]
    written = [b for b in case["boxes"] if case["fates"].get(b["subject"]) == "written" and b["subject"].startswith("glyph/6/1/9/11/")]
    assert len(written) == 1                                          # the half note that fills the bar, the real one
    v = written[0]["value"]
    head = {"glyph": written[0]["subject"], "category": "notehead", "pitch": "F4", "duration_beats": 2.0, "duration_type": "half", "dots": 0}
    return got, [{"kind": "note", "noteheads": [head], "duration_beats": 2.0, "duration_type": "half", "dots": 0, "x_position": float(v[1]) + float(v[3]) / 2.0}]


def test_the_2_333_spot_is_drawn_red_on_the_event_standing_at_the_heads_onset(monkeypatch):
    dropped, events = _viola_events(monkeypatch)
    assert LY._attach_dropped_head_spots(dropped, None, events) == len(dropped)
    counters = collections.Counter()
    text = LY._lily_event_marked(events[0], {}, None, counters)
    assert RED_WORDS.findall(text) == [SX.DROPPED_HEAD_SPOT_WORD] * len(dropped)
    assert counters["dropped_head_spots_marked"] == len(dropped)
    # the MusicXML puts the same words at the same event (onset 0: nothing stands to its left)
    assert SX._dropped_head_onset(dropped[0], [events], 4) == 0


def test_the_spot_goes_where_the_xml_puts_it_when_events_stand_left():
    head = {"x": 300.0, "w": 30.0}
    stream = [{"kind": "note", "x_position": x, "duration_beats": 1.0, "duration_type": "quarter", "dots": 0, "noteheads": [{"pitch": "C4", "duration_beats": 1.0, "duration_type": "quarter", "dots": 0}]}
              for x in (100.0, 200.0, 300.0)]
    assert LY._attach_dropped_head_spots([head], None, stream) == 1
    assert [bool(e.get("unread_spot_words")) for e in stream] == [False, False, True]


def test_a_voice_with_nothing_printed_places_no_spot():
    skip = {"kind": next(iter(SX._NOT_A_PRINTED_MARK)), "x_position": 100.0, "units": 4}
    assert LY._attach_dropped_head_spots([{"x": 100.0, "w": 30.0}], None, [skip]) == 0


def test_the_whole_bar_rest_bar_carries_the_spot_words():
    bar = LY._Bar("empty", {"beats": 4, "beat_type": 4}, None, None, spot_words=(SX.DROPPED_HEAD_SPOT_WORD,))
    counters = collections.Counter()
    text = LY._render_bar(bar, {}, counters)
    assert RED_WORDS.findall(text) == ["unread note"] and counters["dropped_head_spots_marked"] == 1
