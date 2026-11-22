"""ROADMAP 2.319 r2 (STAGED ADJUDICATE + EXPORT): the two faults the first round's look found, pinned on REAL stroke rows
(`fixtures/one_beam_reader_2_319/r2_controls.json`, frozen-sample records of 2026-11-21; truth is the print at 600 dpi, our look).

* A flag hangs on the stem its ink meets (Sean 2026-11-18: join by ink, not by box). Brahms p25 0/3/1: the second of two flagged eighths stands
  under a false `clefF` box, the stem finder joined no stem to it, and its flag was never asked: written a quarter. The one beam count found its
  stem by ink; the flag box's ink touches that stem. Never the flag of the note before (its ink does not touch this stem).
* A note whose stem the one count could not find in the ink neither joins nor breaks a beam group ("cannot tell" is never "no beam", rule 8).
  Litolff p4 1/8/5: four beamed eighths; a box on the beam's end is read as a head with no stem, and cut the last eighth off the beam.

`TestTheControlCanFail` switches each rule off and shows its note read wrong."""
from __future__ import annotations

import json
import pathlib
from unittest import mock

from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import export as E
from tools.omr.staged.adjudicators import rhythm as RH
from tools.omr.tests.test_one_beam_reader_2_319 import count, ink, views

NOTES = json.loads((pathlib.Path(__file__).parent / "fixtures" / "one_beam_reader_2_319" / "r2_controls.json").read_text())["notes"]


def flag_joins(glyph, flag):
    note = NOTES[glyph]
    f = note["flags"][flag]
    got = count(note)
    way = RH._flag_class_direction(f["cls"])
    return RH.flag_ink_meets_stem(way, f["box"], f["covered"], {v.ordinal: v for v in views(note)}, got["stems"])


def test_the_flag_under_the_false_clef_box_hangs_on_the_stem_the_ink_found():
    got = count(NOTES["glyph/25/0/3/1/3"])
    assert got["state"] == "read" and got["certain"] == 0          # a stem, no beam: the flag reader's note
    assert flag_joins("glyph/25/0/3/1/3", "glyph/25/0/3/1/25")


def test_the_flag_of_the_note_before_does_not_hang_on_this_stem():
    for other in ("glyph/25/0/3/1/6", "glyph/25/0/3/1/7", "glyph/25/0/3/1/4"):
        assert not flag_joins("glyph/25/0/3/1/3", other), other
    assert not flag_joins("glyph/25/0/3/1/0", "glyph/25/0/3/1/25")  # ...and this flag is not the first note's


def test_a_flagged_eighth_after_the_barline_hangs_its_flag_on_its_ink_stem():
    assert flag_joins("glyph/4/1/1/12/1", "glyph/4/1/1/12/9")


def test_a_flag_box_over_only_the_heads_own_ink_never_joins():
    note = NOTES["glyph/25/0/3/1/3"]
    vs = {v.ordinal: v for v in views(note)}
    head_ink = [o for o, v in vs.items() if v.kind == "owned" and v.family == "head"]
    f = note["flags"]["glyph/25/0/3/1/25"]
    assert not RH.flag_ink_meets_stem("down", f["box"], head_ink, vs, count(note)["stems"])


def _bar_p4():
    order = ["glyph/4/1/8/5/5", "glyph/4/1/8/5/2", "glyph/4/1/8/5/3", "glyph/4/1/8/5/19", "glyph/4/1/8/5/0"]     # left to right on the page
    return order, [count(NOTES[g]) for g in order], [ink(NOTES[g]) for g in order]


def test_the_box_on_the_beams_end_has_no_stem_and_the_four_eighths_are_one_group():
    order, counts, inks = _bar_p4()
    assert [c["state"] for c in counts] == ["read", "read", "read", "silent", "read"]
    assert [c["certain"] for c in counts] == [1, 1, 1, None, 1]
    # the silent box is passed over as a rest is (EXPORT `_annotate_beams_for`): None
    assert E.groups_sharing_beam_ink([1, 1, 1, None, 1], inks) == [[0, 1, 2, 4]]


def test_a_note_with_a_stem_read_and_no_beam_still_breaks_the_group():
    _order, _counts, inks = _bar_p4()
    assert E.groups_sharing_beam_ink([1, 1, 1, 1, 1], inks[:3] + [frozenset()] + inks[4:]) == [[0, 1, 2]]


def test_beam_count_silent_reads_the_adjudicate_verdict():
    class Rec:
        def __init__(self, details):
            self.d = details

        def verdict(self, _q, g):
            return {"id": g, "detail": self.d[g]}

        def verdict_by_id(self, _i):
            return None
    rec = Rec({"a": {"beam_strokes": [], "one_beam_count": {"state": "silent"}},
               "b": {"beam_strokes": [], "one_beam_count": {"state": "read"}},
               "c": {"beam_strokes": [], "one_beam_count": {"state": "silent"}, "beam_evidence": "flag", "flags_attached": 1}})
    assert E._beam_count_silent(rec, {"noteheads": [{"glyph": "a"}]})
    assert not E._beam_count_silent(rec, {"noteheads": [{"glyph": "a"}, {"glyph": "b"}]})      # a chord: one head's stem read
    assert not E._beam_count_silent(rec, {"noteheads": [{"glyph": "c"}]})                      # a flag was read on its stem


class TestTheControlCanFail:
    def test_without_the_ink_join_the_flag_is_never_asked(self):
        with mock.patch.object(RH, "FLAG_ON_THE_INK_STEM", False):
            assert RH._flags_on_ink_stem(None, None, count(NOTES["glyph/25/0/3/1/3"])) == ([], 0, [])

    def test_without_passing_the_silent_box_over_the_last_eighth_falls_off_the_beam(self):
        _order, _counts, inks = _bar_p4()
        assert E.groups_sharing_beam_ink([1, 1, 1, 0, 1], inks) == [[0, 1, 2]]

    def test_without_the_stems_ink_the_flag_cannot_join(self):
        note = NOTES["glyph/25/0/3/1/3"]
        f = note["flags"]["glyph/25/0/3/1/25"]
        stems = [{**st, "stem_touches": []} for st in count(note)["stems"]]
        assert not RH.flag_ink_meets_stem("down", f["box"], f["covered"], {v.ordinal: v for v in views(note)}, stems)
