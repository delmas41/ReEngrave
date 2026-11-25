"""ROADMAP 2.345 print check: three real bars (2.343 tie, 2.333 spot, 2.343 slur + kind-unread arc) rendered by lilypond.py's own `_render_bar`."""
import collections
import pathlib

import pytest

from tools.omr.staged import lilypond as LY
from tools.omr.tests import test_lilypond_unread_note_marks_2_345 as T
from tools.omr.tests import test_tie_unwritten_end_marked_2_343 as T343

OUT = pathlib.Path(__file__).parent
mp = pytest.MonkeyPatch()
c = collections.Counter()
meter = {"beats": 4, "beat_type": 4}


def ev(h, dt="half", bt=2.0):
    return {"kind": "note", "noteheads": [h], "duration_beats": bt, "duration_type": dt, "dots": 0, "x_position": 100.0}


heads = T._tie_heads([T343.FIRST, T343.LAST])
b1 = LY._Bar("single", meter, "treble", {"fifths": 0}, events=[ev(heads[T343.FIRST]), ev(heads[T343.LAST])])
dropped, events = T._viola_events(mp)
events[0]["duration_type"] = "whole"
events[0]["duration_beats"] = 4.0
events[0]["noteheads"][0]["duration_type"] = "whole"
events[0]["noteheads"][0]["duration_beats"] = 4.0
LY._attach_dropped_head_spots(dropped, None, events)
b2 = LY._Bar("single", meter, "treble", {"fifths": 0}, events=events)
slur = T._slur_heads([T343.SLUR_START])[T343.SLUR_START]
kind = T._unread_heads([T343.UNREAD_START, T343.UNREAD_STOP])[T343.UNREAD_START]
b3 = LY._Bar("single", meter, "treble", {"fifths": 0}, events=[ev(slur), ev(kind)])
body = " ".join(LY._render_bar(b, {}, c) for b in (b1, b2, b3))
(OUT / "fragment.ly").write_text(
    '\\version "2.24.0"\n'
    "guessedColor = #(rgb-color 0.12 0.44 0.92)\n"
    "\\paper { indent=0 paper-width=190\\mm paper-height=40\\mm tagline=##f }\n"
    "\\score { \\new Staff { \\clef treble \\time 4/4 " + body + " } \\layout { } }\n")
print(body)
print(dict(c))
